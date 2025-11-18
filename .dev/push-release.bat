@echo off
setlocal enabledelayedexpansion

REM Check for --dry-run parameter
set "IS_DRY_RUN="
if "%1"=="--dry-run" (
  set "IS_DRY_RUN=1"
  echo [DRY RUN] This is a dry run. No changes will be made.
)

REM Ensure we are in a git repo
git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
  echo This directory is not a Git repository.
  exit /b 1
)

REM Fetch latest tags from origin
git fetch --tags --force --prune >nul 2>&1

REM Determine latest semver tag starting with v
set "LATEST_TAG="
for /f "usebackq delims=" %%i in (`git tag --list "v*" --sort=-version:refname`) do (
  set "LATEST_TAG=%%i"
  goto :got_latest
)

:got_latest
if not defined LATEST_TAG (
  echo No existing release tags found. Starting from v0.1.0.
  set "MAJOR=0"
  set "MINOR=1"
  set "PATCH=0"
  goto :compute_new
)

echo Latest tag found: %LATEST_TAG%
set "VER=%LATEST_TAG%"
set "VER=%VER:v=%"

for /f "tokens=1-3 delims=." %%a in ("%VER%") do (
  set "MAJOR=%%a"
  set "MINOR=%%b"
  set "PATCH=%%c"
)

if not defined MAJOR set MAJOR=0
if not defined MINOR set MINOR=1
if not defined PATCH set PATCH=0

:compute_new
REM Convert to numbers to ensure proper increment
set /a MAJOR=%MAJOR% >nul
set /a MINOR=%MINOR% >nul
set /a PATCH=%PATCH% >nul
set /a PATCH=PATCH+1 >nul
set "NEW_TAG=v%MAJOR%.%MINOR%.%PATCH%"

REM Prevent accidental retagging
git rev-parse -q --verify "refs/tags/%NEW_TAG%" >nul 2>&1
if not errorlevel 1 (
  echo Tag %NEW_TAG% already exists. Aborting.
  exit /b 1
)

echo Current version: %LATEST_TAG%
echo New version: %NEW_TAG%

if defined IS_DRY_RUN (
  echo.
  echo [DRY RUN] Would create version %NEW_TAG% from %LATEST_TAG%
  echo [DRY RUN] No changes will be made to the repository.
  exit /b 0
)

echo Preparing release %NEW_TAG%

REM Stage all changes
git add -A

REM If there are staged changes, ask for a commit message and commit
git diff --cached --quiet
if errorlevel 1 (
  set /p COMMIT_MSG=Enter commit message [default: chore: prep release %NEW_TAG%]: 

  REM Trim spaces-only messages
  set "_TMP=%COMMIT_MSG%"
  set "_TRIM=!_TMP: =!"
  if "!_TRIM!"=="" set "COMMIT_MSG=chore: prep release %NEW_TAG%"

  git commit -m "%COMMIT_MSG%"
  if errorlevel 1 (
    echo Commit failed. You may have commit hooks enforcing a format.
    echo Retrying with default message: chore: prep release %NEW_TAG%
    git commit -m "chore: prep release %NEW_TAG%"
    if errorlevel 1 (
      echo Commit failed again. Aborting.
      exit /b 1
    )
  )
) else (
  echo No staged changes to commit. Continuing.
)

REM Push current HEAD to origin main (fast-forward or create if needed)
git push origin HEAD:main
if errorlevel 1 (
  echo Push to origin main failed. Aborting.
  exit /b 1
)

REM Create annotated tag at current commit
git tag -a "%NEW_TAG%" -m "Release %NEW_TAG%"
if errorlevel 1 (
  echo Tag creation failed. Aborting.
  exit /b 1
)

REM Push the tag
git push origin "%NEW_TAG%"
if errorlevel 1 (
  echo Tag push failed. Aborting.
  exit /b 1
)

echo.
echo Release %NEW_TAG% pushed. GitHub Actions will build and publish from the tag.
echo Check: https://github.com/%GITHUB_USER%/%GITHUB_REPOSITORY%/actions (or your repo Actions page)
exit /b 0