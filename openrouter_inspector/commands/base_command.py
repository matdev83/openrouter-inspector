"""Base command class for CLI commands."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Any

from ..formatters.base import BaseFormatter
from ..handlers import EndpointHandler, ModelHandler, ProviderHandler
from ..interfaces.client import APIClient
from ..interfaces.services import ModelServiceInterface


class BaseCommand(ABC):
    """Abstract base class for CLI commands."""

    def __init__(
        self,
        client: APIClient,
        model_service: ModelServiceInterface,
        table_formatter: BaseFormatter,
        json_formatter: BaseFormatter,
    ) -> None:
        """Initialize the base command with required dependencies.

        Args:
            client: The API client instance.
            model_service: The model service instance.
            table_formatter: The table formatter instance.
            json_formatter: The JSON formatter instance.
        """
        self.client = client
        self.model_service = model_service
        self.table_formatter = table_formatter
        self.json_formatter = json_formatter

        # Initialize handlers
        self.model_handler = ModelHandler(model_service)
        self.provider_handler = ProviderHandler(client)
        self.endpoint_handler = EndpointHandler(client, model_service)

    @abstractmethod
    async def execute(self, *args: Any, **kwargs: Any) -> str:
        """Execute the command with the given arguments.

        Args:
            *args: Positional arguments.
            **kwargs: Command-specific arguments.

        Returns:
            Formatted output string.
        """
        pass

    def _format_output(
        self, data: Any, output_format: str, **format_kwargs: Any
    ) -> str:
        """Format output using the appropriate formatter.

        Args:
            data: Data to format.
            output_format: Output format ('table' or 'json').
            **format_kwargs: Additional formatting arguments.

        Returns:
            Formatted output string.
        """
        if output_format.lower() == "json":
            if hasattr(data, "__iter__") and not isinstance(data, str):
                # Handle list of models or providers
                if data and hasattr(data[0], "id"):  # ModelInfo objects
                    return self.json_formatter.format_models(data)
                elif data and hasattr(data[0], "provider"):  # ProviderDetails objects
                    return self.json_formatter.format_providers(data)
            return self.json_formatter.format_models(data)
        else:
            if hasattr(data, "__iter__") and not isinstance(data, str):
                if data and hasattr(data[0], "id"):  # ModelInfo objects
                    return self.table_formatter.format_models(data, **format_kwargs)
                elif data and hasattr(data[0], "provider"):  # ProviderDetails objects
                    return self.table_formatter.format_providers(data, **format_kwargs)
            return self.table_formatter.format_models(data, **format_kwargs)

    async def _maybe_await(self, value: Any) -> Any:
        """Return awaited value when a coroutine is provided; otherwise value unchanged."""
        if asyncio.iscoroutine(value):
            return await value
        return value
