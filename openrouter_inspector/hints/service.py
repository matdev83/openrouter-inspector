"""Service for managing command hints."""

from __future__ import annotations

from ..interfaces.hints import HintProvider
from .context import HintContext
from .providers import (
    DetailsHintProvider,
    EndpointsHintProvider,
    ListHintProvider,
    SearchHintProvider,
)


class HintService:
    """Service for generating and managing command hints."""

    def __init__(self) -> None:
        """Initialize the hint service with default providers."""
        self._providers: dict[str, HintProvider] = {
            "list": ListHintProvider(),
            "endpoints": EndpointsHintProvider(),
            "details": DetailsHintProvider(),
            "search": SearchHintProvider(),
        }

    def register_provider(self, command_name: str, provider: HintProvider) -> None:
        """Register a hint provider for a command.

        Args:
            command_name: Name of the command
            provider: Hint provider instance
        """
        self._providers[command_name] = provider

    def get_hints(self, context: HintContext) -> list[str]:
        """Get hints for the given context.

        Args:
            context: Context containing command and data information

        Returns:
            List of hint strings
        """
        provider = self._providers.get(context.command_name)
        if provider:
            return provider.get_hints(context)
        return []

    def supports_hints(self, command_name: str) -> bool:
        """Check if a command supports hints.

        Args:
            command_name: Name of the command

        Returns:
            True if the command has a registered hint provider
        """
        return command_name in self._providers
