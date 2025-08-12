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
- Makefile commands (automation shortcuts):

  - `make help`: Show all available targets.
  - `make setup-dev`: Run local dev setup script (creates config, etc.).
  - `make install`: Install the package into the active environment.
  - `make install-dev`: Editable install with dev dependencies (`.[dev]`).
  - `make test`: Run the test suite (network tests are skipped by default).
  - `make test-cov`: Run tests with coverage and generate HTML report in `htmlcov/`.
  - `make lint`: Run Ruff linting (with `--fix`).
  - `make format`: Run Black formatting over the repository.
  - `make type-check`: Run MyPy type checking on `openrouter_inspector`.
  - `make qa`: Convenience target that runs format, lint, type-check, and test-cov.
  - `make clean`: Remove build artifacts, caches, and coverage output.
  - `make build`: Clean and build sdist + wheel (uses `python -m build`).
  - `make publish-test`: Upload `dist/*` to TestPyPI. Requires environment variables for Twine:
    - `TWINE_USERNAME=token`
    - `TWINE_PASSWORD=<your-pypi-token>`
  - `make publish`: Upload `dist/*` to PyPI (same Twine env vars as above).
  - `make release`: Clean, build, run Twine checks, and upload to PyPI.

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
