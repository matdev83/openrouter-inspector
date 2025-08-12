# Contributing to OpenRouter Inspector

## Development Setup

- Python 3.10+
- Create and activate a virtual environment:
  - Windows (PowerShell):
    ```powershell
    python -m venv .venv
    ./.venv/Scripts/Activate.ps1
    ```
  - Unix/macOS:
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```
- Install the project with all dev tools:
  ```bash
  pip install -e ".[dev]"
  ```
- Optional Make targets:
  ```bash
  make setup-dev
  make install-dev
  make test
  make qa
  ```

## Quality Assurance

The repository enforces:
- Black (formatting)
- Ruff (linting, pyupgrade)
- MyPy (type checking)
- Pytest (unit + integration)
- Bandit (security linting)
- Safety (dependency vulnerabilities)

Run locally:
```bash
black .
ruff check --fix .
mypy openrouter_inspector
pytest
```

## GitHub Actions

- CI runs tests across OS/Python versions, quality checks, and security scans.
- A minimal “Tests” workflow provides a dynamic tests badge.
- Coverage is uploaded to Codecov on ubuntu-latest + Python 3.11.

## Pre-commit

Install hooks (optional):
```bash
pre-commit install
pre-commit run --all-files
```

## Coding Standards

- Prefer built-in generics (list, dict) and PEP 604 unions (X | Y).
- Avoid broad `except Exception` blocks; log or narrow where possible.
- Keep functions short, clear, and typed. See Ruff and MyPy for guidance.

## Release (future)

When publishing to PyPI, add the standard PyPI badges to README and ensure
`pyproject.toml` metadata is up to date.

## Questions / Issues

Please open an issue on the GitHub tracker for bugs or feature requests.
