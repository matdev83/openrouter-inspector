"""Dependency injection utilities."""

from __future__ import annotations

from rich.console import Console

from .. import client as client_mod
from .. import services as services_mod
from ..formatters import JsonFormatter, TableFormatter

# Use a wider console to avoid cell truncation in tests
console = Console(width=200)


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
