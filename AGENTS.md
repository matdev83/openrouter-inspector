# AGENTS.md

## Purpose

This file provides instructions and best practices for coding agents (AI assistants, automation tools, or code-generation bots) contributing to or operating on this repository.

---

## CRITICAL: Python Execution in WSL Environment

**WINDOWS VIRTUAL ENVIRONMENT DETECTED**: This project uses a Windows Python virtual environment (.venv) inside WSL. **ALWAYS** use the Windows Python executable for all Python commands:

- **Correct**: `./.venv/Scripts/python.exe -c "print('hello')"`
- **Correct**: `./.venv/Scripts/python.exe script.py`
- **Correct**: `./.venv/Scripts/python.exe -m pytest tests/`
- **Correct**: `./.venv/Scripts/python.exe -m pip install package`
- **Incorrect**: `python script.py` (system Python)
- **Incorrect**: `source .venv/bin/activate` (Linux virtual environment activation)

This approach works because WSL can execute Windows binaries directly. The virtual environment contains Windows .exe files that must be used instead of trying to activate the virtual environment in the traditional Linux way.

## Essential Commands

- **Setup**: `./.venv/Scripts/python.exe -m venv .venv && ./.venv/Scripts/python.exe -m pip install -e .`
- **Linting**: `./.venv/Scripts/python.exe -m ruff check src tests`
- **Type checking**: `./.venv/Scripts/python.exe -m mypy src`
- **Run all tests**: `./.venv/Scripts/python.exe -m pytest tests/ -v`
- **Run single test**: `./.venv/Scripts/python.exe -m pytest tests/path/to/test_file.py::test_function_name -v`
- **Run test category**: `./.venv/Scripts/python.exe -m pytest tests/unit/ -v` (or integration, system)

---

## Coding Standards

- **Language:** Python 3.10+
- **Formatting:** Ruff with Google docstring convention
- **Architecture**: Modular, layered, object-oriented design with a focus on SOLID, DRY, and high testability through separation of concerns.
- **Naming:** snake_case for functions/variables, PascalCase for classes
- **Type Hints:** Required for all function signatures and class attributes
- **Docstrings:** Google style for all public functions and classes
- **Logging:** Use `logging` module, not print statements
- **Error Handling:** Use exceptions and logging for error reporting

---

## Agent Development Principles

- **PEP8 Compliance**: All Python code must adhere to the PEP8 style guide.
- **Follow Pythonic Conventions**
- **Virtual Environment**: The project's virtual environment is located in the `.venv/` directory. **DO NOT** try to activate it using `source .venv/bin/activate`. Instead, **ALWAYS** prepend `./.venv/Scripts/python.exe` to all Python commands.
- **Dependency Management**: Agents are **NOT ALLOWED** to install packages directly using `pip`, `npm`, or any other package manager. All dependencies must be managed by editing the `pyproject.toml` file. After editing, the project must be re-installed in editable mode using `./.venv/Scripts/python.exe -m pip install -e .[dev]`. This is the only permitted use of `pip`.
- **Verification**: Before marking a task as complete, an agent **MUST** verify its work. This includes running specific tests related to the changes and executing the full test suite to ensure no regressions were introduced.
- **Codebase Integrity**: Agents are expected to only make changes that improve the codebase. This includes adding new functions/methods, improving existing ones, performing maintenance tasks (improving the shape of the code), and adding new functionalities. Agents are **NOT ALLOWED** to degrade the project's shape by removing functions, functionalities, files, or features, unless **EXPLICITLY** requested by the user.
- **Architectural Principles**: Adhere to the following software design principles:
  - **TDD (Test-Driven Development)**: Write tests before code
  - **SOLID**: Respect SOLID principles and design patterns like Single Responsibility, Open-Closed, Liskov Substitution, Interface Segregation, and Dependency Inversion.
  - **DIP**: Depend on abstractions, not concrete implementations
  - **DRY (Don't Repeat Yourself)**:  Avoid code duplication
  - **KISS (Keep It Simple, Stupid)**: Do not overengineer
  - **Convention over Configuration**: Prefer configuration over code, provide sane and well thought default values
  - **YAGNI (You Aren't Gonna Need It)**: Don't add functionality until it's needed

## Proper Python interpreter file

To run all Python commands inside this project use the `.venv/Scripts/python.exe` file.

---

## Actions AFTER Each File Edit

After each completed file Python (*.py) edit, agents MUST run the following QA (quality-assurance commands). This applies only to Python files. Do not use this QA command for files other than Python source files:

```bash
./.venv/Scripts/python.exe -m ruff check --fix <modified_filename> && ./.venv/Scripts/python.exe -m black <modified_filename> && ./.venv/Scripts/python.exe -m mypy <modified_filename> && ./.venv/Scripts/python.exe -m pylint --disable=all --load-plugins=pylint.extensions.mccabe --enable=too-complex,too-many-branches,too-many-statements,too-many-nested-blocks,too-many-return-statements,too-many-boolean-expressions,too-many-arguments,too-many-locals,too-many-instance-attributes,too-many-public-methods,too-many-parents --max-complexity=10 --max-branches=12 --max-statements=50 --max-returns=6 --max-bool-expr=5 --max-args=5 --max-locals=15 --max-attributes=7 --max-public-methods=20 --max-parents=7 <modified_filename> && ./.venv/Scripts/python.exe -m vulture <modified_filename> --min-confidence 90
```

Notes:

- Always use the Windows venv interpreter path shown above.
- Replace `<modified_filename>` with the exact path to the changed file.
- Run these before proceeding to additional edits or committing.
- If you need to split this one-liner QA commands into smaller steps, follow this order: 
 - `ruff check --fix ...`
 - `black`
 - `mypy`
 - `pylint` with only complexity checks
 - `vulture`

---

## No Premature False Success Claims

Never summarize a task or claim a success or summarize task completion unless you:
- created or checked related tests and ensured they all pass,
- proved the test suite is 100% green,
- proved the end-to-end functioning by running commands utilising related code