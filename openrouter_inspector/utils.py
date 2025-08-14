"""Shared utilities for OpenRouter CLI."""

from __future__ import annotations

import logging
from typing import Any

from rich.console import Console

from . import client as client_mod
from . import services as services_mod
from .formatters import JsonFormatter, TableFormatter

# Use a wider console to avoid cell truncation in tests
console = Console(width=200)


def configure_logging(
    level_name: str | None, *, default_to_warning: bool = False
) -> None:
    """Configure root logging level.

    Defaults to WARNING if not provided or invalid.

    Args:
        level_name: The logging level name (e.g., 'DEBUG', 'INFO', 'WARNING').
        default_to_warning: Whether to default to WARNING level if level_name is None.
    """
    if level_name is None:
        if not default_to_warning:
            return
        level_value = logging.WARNING
    else:
        try:
            level_value = getattr(logging, level_name.upper())
            if not isinstance(level_value, int):
                level_value = logging.WARNING
        except Exception:
            level_value = logging.WARNING
    root_logger = logging.getLogger()
    if root_logger.handlers:
        root_logger.setLevel(level_value)
    else:
        logging.basicConfig(level=level_value)


def create_command_dependencies(
    api_key: str,
) -> tuple[
    client_mod.OpenRouterClient,
    services_mod.ModelService,
    TableFormatter,
    JsonFormatter,
]:
    """Create and return command dependencies for dependency injection.

    Args:
        api_key: The OpenRouter API key.

    Returns:
        Tuple of (client, model_service, table_formatter, json_formatter).

    Note:
        Returns concrete implementations that satisfy the abstract interfaces
        used by BaseCommand. This maintains backward compatibility while
        allowing dependency inversion in the command layer.
    """
    client = client_mod.OpenRouterClient(api_key)
    model_service = services_mod.ModelService(client)
    table_formatter = TableFormatter(console)
    json_formatter = JsonFormatter()

    return client, model_service, table_formatter, json_formatter


def normalize_string(s: str | None) -> str:
    """Normalize a string for comparison purposes.

    Args:
        s: The string to normalize.

    Returns:
        Normalized string (lowercase and stripped).
    """
    return (s or "").strip().lower()


def parse_quantization_bits(q: str | None) -> float:
    """Parse quantization string to numeric bits value.

    Args:
        q: Quantization string (e.g., 'fp8', 'bf16', '4bit').

    Returns:
        Numeric bits value, with unspecified treated as best (inf).
    """
    if not q:
        return float("inf")  # treat unspecified as best
    s = q.lower()
    if "bf16" in s:
        return 16
    # extract first integer in string
    num = ""
    for ch in s:
        if ch.isdigit():
            num += ch
    try:
        return float(num) if num else 0.0
    except Exception:
        return 0.0


def parse_context_threshold(v: str | None) -> int:
    """Parse context threshold string to integer value.

    Args:
        v: Context threshold string (e.g., '128K', '131072').

    Returns:
        Integer context threshold value.
    """
    if v is None:
        return 0
    s = str(v).strip()
    try:
        if s.lower().endswith("k"):
            return int(float(s[:-1]) * 1000)
        return int(float(s))
    except Exception:
        return 0


def check_parameter_support(supported_parameters: Any, parameter: str) -> bool:
    """Check if a parameter is supported based on supported_parameters.

    Args:
        supported_parameters: The supported parameters (list or dict).
        parameter: The parameter name to check for.

    Returns:
        True if the parameter is supported, False otherwise.
    """
    if isinstance(supported_parameters, list):
        return any(
            (isinstance(x, str) and (x == parameter or x.startswith(parameter)))
            for x in supported_parameters
        )
    elif isinstance(supported_parameters, dict):
        return bool(supported_parameters.get(parameter, False))
    return False
