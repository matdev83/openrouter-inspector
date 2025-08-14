"""Command factory for CLI dependency injection and execution."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import Any, TypeVar

from .commands.base_command import BaseCommand
from .utils import create_command_dependencies

T = TypeVar("T", bound=BaseCommand)


class CLICommandFactory:
    """Factory for creating and executing CLI commands with proper dependency injection."""

    def __init__(self, api_key: str) -> None:
        """Initialize the command factory.

        Args:
            api_key: OpenRouter API key for authentication
        """
        self.api_key = api_key

    async def create_and_execute_command(
        self,
        command_class: type[T],
        **kwargs: Any,
    ) -> str:
        """Create a command instance and execute it with proper dependency injection.

        Args:
            command_class: The command class to instantiate
            **kwargs: Arguments to pass to the command's execute method

        Returns:
            Command output string

        Raises:
            APIError: If API request fails
            AuthenticationError: If authentication fails
            RateLimitError: If rate limit is exceeded
        """
        # Create dependencies
        client, model_service, table_formatter, json_formatter = (
            create_command_dependencies(self.api_key)
        )

        # Execute command with proper client lifecycle management
        async with client as c:
            # Ensure service uses the entered client (tests may patch __aenter__)
            with suppress(AttributeError):
                model_service.client = c

            # Create and execute command
            command = command_class(c, model_service, table_formatter, json_formatter)
            return await command.execute(**kwargs)

    def run_command_sync(
        self,
        command_class: type[T],
        **kwargs: Any,
    ) -> str:
        """Synchronously run a command (wrapper around async execution).

        Args:
            command_class: The command class to instantiate
            **kwargs: Arguments to pass to the command's execute method

        Returns:
            Command output string

        Raises:
            APIError: If API request fails
            AuthenticationError: If authentication fails
            RateLimitError: If rate limit is exceeded
        """
        return asyncio.run(self.create_and_execute_command(command_class, **kwargs))
