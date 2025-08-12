# Makefile for OpenRouter CLI development

.PHONY: help install install-dev test test-cov lint format type-check qa clean build publish publish-test release

# Default target
help:
	@echo "Available targets:"
	@echo "  install      - Install the package"
	@echo "  install-dev  - Install in development mode with dev dependencies"
	@echo "  test         - Run tests"
	@echo "  test-cov     - Run tests with coverage"
	@echo "  lint         - Run linting with ruff"
	@echo "  format       - Format code with black"
	@echo "  type-check   - Run type checking with mypy"
	@echo "  qa           - Run all quality assurance checks"
	@echo "  clean        - Clean build artifacts"
	@echo "  build        - Build the package (sdist + wheel)"
	@echo "  publish      - Upload dist/* to PyPI (requires TWINE env vars)"
	@echo "  publish-test - Upload dist/* to TestPyPI (requires TWINE env vars)"
	@echo "  release      - Clean, build, check and publish to PyPI"

# Installation targets
install:
	pip install .

install-dev:
	pip install -e .[dev]

# Testing targets
test:
	pytest

test-cov:
	pytest --cov=openrouter_inspector --cov-report=html --cov-report=term

# Quality assurance targets
lint:
	ruff check --fix .

format:
	black .

type-check:
	mypy openrouter_inspector

qa: format lint type-check test-cov
	@echo "All quality assurance checks completed"

# Build and clean targets
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean
	python -m build

# Publish helpers (set TWINE_USERNAME=token and TWINE_PASSWORD=your-token before running)
publish-test:
	python -m pip install -U build twine
	python -m twine check dist/*
	python -m twine upload --repository testpypi dist/*

publish:
	python -m pip install -U build twine
	python -m twine check dist/*
	python -m twine upload dist/*

release: clean build
	python -m pip install -U twine
	python -m twine check dist/*
	python -m twine upload dist/*

# Virtual environment setup
setup-dev:
	python setup_dev.py