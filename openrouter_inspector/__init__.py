"""OpenRouter Inspector - A command-line tool for exploring OpenRouter AI models and providers."""

__version__ = "0.1.0"
__author__ = "OpenRouter Inspector Team"
__email__ = "support@example.com"

# Re-export the click group as package-level entry point while keeping module importable for patching
from .__main__ import main
from .cli import cli

__all__ = ["cli", "main", "__version__"]
