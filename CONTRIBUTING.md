# Contributing to OpenRouter Inspector

## Development Setup

- Python >=3.10 (source of truth: `pyproject.toml` → `[project].requires-python`)
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

### Windows without `make`

If `make` is not installed on your Windows machine, use one of the following:

- Option A (install make):
  ```powershell
  choco install make
  # Re-open shell or run `refreshenv`
  make ci-qa
  ```

- Option B (run underlying commands directly):
  ```powershell
  # Ensure venv is active and dev deps are installed
  .\.venv\Scripts\python.exe -m pip install -U pip
  .\.venv\Scripts\python.exe -m pip install -e ".[dev,build,test]"

  # CI-equivalent quality checks
  ruff check --output-format=github .
  black --check --diff .
  mypy openrouter_inspector
  vulture --min-confidence 80 openrouter_inspector

  # CI-equivalent tests
  pytest --cov=openrouter_inspector --cov-report=xml --cov-report=term --junitxml=pytest.xml

  # CI-equivalent security checks
  bandit -r openrouter_inspector -f json -o bandit-report.json --severity-level medium --confidence-level high
  safety check --output json > safety-report.json

  # Build and validate (pre-publish)
  python -m build
  twine check dist/*
  ```

- Option C (Hatch, cross-platform task runner):
  ```powershell
  .\.venv\Scripts\python.exe -m pip install -U pip
  .\.venv\Scripts\python.exe -m pip install hatch

  # QA bundle (format-check, lint, type-check, vulture, tests)
  hatch run qa

  # Or run specific steps
  hatch run format-check
  hatch run lint
  hatch run type-check
  hatch run vulture-check
  hatch run test-cov

  # Build and validate
  hatch run -e build clean
  python -m build
  twine check dist/*
  ```

## Install from Source

For users building from a local clone instead of PyPI:

```bash
# Standard install
pip install .

# Editable/development install
pip install -e .
```

## OpenRouter Inspector - SOLID-Compliant Hint Architecture

The OpenRouter Inspector now implements a SOLID-compliant architecture for command hints, separating concerns and making the system more maintainable and extensible.

### 1. Interfaces (`openrouter_inspector/interfaces/`)

#### `HintProvider` Protocol
```python
class HintProvider(Protocol):
    def get_hints(self, context: Any) -> list[str]:
        """Get command hints for the given context."""
```

#### `HintsCapable` Abstract Base Class
```python
class HintsCapable(ABC):
    @abstractmethod
    def supports_hints(self) -> bool:
        """Check if this command supports displaying hints."""
    
    @abstractmethod
    def get_hint_context(self, **kwargs: Any) -> Any:
        """Get the context object needed for hint generation."""
```

### 2. Hint System (`openrouter_inspector/hints/`)

#### `HintContext`
Data class that carries context information for hint generation:
- `command_name`: Name of the command
- `model_id`: Model ID (optional)
- `provider_name`: Provider name (optional)
- `example_model_id`: Example model for hints (optional)
- `data`: Additional data (optional)

#### `HintService`
Central service that manages hint providers and generates hints:
- Registers hint providers for different commands
- Routes hint requests to appropriate providers
- Supports dynamic provider registration

#### Hint Providers
Specialized providers for each command:
- `ListHintProvider`: Generates hints for the list command
- `EndpointsHintProvider`: Generates hints for the endpoints command
- `DetailsHintProvider`: Generates hints for the details command
- `SearchHintProvider`: Generates hints for the search command

### 3. Command Mixins (`openrouter_inspector/commands/mixins.py`)

#### `HintsMixin`
Mixin class that provides hint functionality to commands:
- Implements `HintsCapable` interface
- Provides `_format_output_with_hints()` method
- Handles hint context creation
- Integrates with the hint service

### 4. Updated Commands

Commands that support hints now inherit from both `BaseCommand` and `HintsMixin`:
- `EndpointsCommand`
- `DetailsCommand`
- `ListCommand`

## SOLID Principles Implementation

### Single Responsibility Principle (SRP)
- **Commands**: Handle business logic only
- **Hint Providers**: Generate hints for specific commands only
- **Hint Service**: Manage hint providers and routing only
- **Formatters**: Format output only (no longer handle hints)

### Open/Closed Principle (OCP)
- New commands can add hint support by inheriting from `HintsMixin`
- New hint providers can be added without modifying existing code
- Hint providers can be registered dynamically

### Liskov Substitution Principle (LSP)
- Any `HintProvider` can be substituted for another
- Commands with `HintsMixin` can be used wherever `BaseCommand` is expected

### Interface Segregation Principle (ISP)
- `HintProvider` protocol is focused only on hint generation
- `HintsCapable` interface is separate from base command functionality
- Commands only implement interfaces they need

### Dependency Inversion Principle (DIP)
- Commands depend on `HintProvider` abstraction, not concrete implementations
- Hint service depends on `HintProvider` protocol, not specific providers
- High-level modules don't depend on low-level modules

## Usage Examples

### Adding Hints to a New Command

1. **Make the command inherit from `HintsMixin`:**
```python
class MyCommand(HintsMixin, BaseCommand):
    async def execute(self, **kwargs):
        # Business logic
        content = self.formatter.format_data(data)
        
        # Add hints using the mixin
        return self._format_output_with_hints(
            content,
            show_hints=not kwargs.get('no_hints', False),
            model_id=kwargs.get('model_id'),
            data=data
        )
```

2. **Create a hint provider:**
```python
class MyCommandHintProvider:
    def get_hints(self, context: HintContext) -> list[str]:
        return [
            "Helpful command:",
            f"  openrouter-inspector other-command {context.model_id}"
        ]
```

3. **Register the provider:**
```python
# In the hint service initialization
self._providers["mycommand"] = MyCommandHintProvider()
```

### CLI Integration

All commands that support hints automatically get the `--no-hints` flag:
```bash
# Show hints (default)
openrouter-inspector endpoints model/id

# Hide hints
openrouter-inspector endpoints model/id --no-hints
```

## Benefits

1. **Maintainability**: Clear separation of concerns makes code easier to maintain
2. **Extensibility**: New commands and hint providers can be added easily
3. **Testability**: Each component can be tested in isolation
4. **Consistency**: All hint-capable commands behave consistently
5. **Flexibility**: Hint providers can be customized or replaced without affecting commands
6. **Reusability**: The hint system can be reused across different commands

## Migration from Old System

The old system had hints hardcoded in formatters, violating SRP and making the code tightly coupled. The new system:

1. **Moved hint logic** from formatters to command layer
2. **Created abstractions** for hint providers and hint-capable commands
3. **Centralized hint management** in the hint service
4. **Maintained backward compatibility** with existing CLI flags
5. **Improved testability** by making components more focused

## Testing

The new architecture includes comprehensive tests:
- Unit tests for each hint provider
- Tests for the hint service
- Tests for the command mixin
- Integration tests for CLI commands
- Tests ensuring formatters no longer handle hints

This ensures the system works correctly and maintains its benefits over time.

## Branching and contribution flow

- The default development branch is `dev`.
- Collaborators must push their work and open pull requests against `dev` (not `main`).
- Avoid pushing directly to `main`. Maintainers will merge `dev` into `main` as part of a release.
- Releases are cut by creating a version tag `vX.Y.Z` on the release commit; CI and publish pipelines run only on version tags.
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

### CI-equivalent local checks

The following targets mirror the GitHub CI workflows so you can validate locally before publishing:

```bash
# Quality: ruff (GitHub format), black --check --diff, mypy, vulture
make ci-qa

# Tests: coverage XML + JUnit XML output (pytest.xml)
make ci-test

# Security: bandit (JSON report), safety (JSON report)
make ci-security

# All of the above, then clean, build, and validate artifacts (twine check)
make pre-publish
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
