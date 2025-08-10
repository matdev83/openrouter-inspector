# Makefile for OpenRouter CLI development

.PHONY: help install install-dev test test-cov lint format type-check qa clean build

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
	@echo "  build        - Build the package"

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

# Virtual environment setup
setup-dev:
	python setup_dev.py