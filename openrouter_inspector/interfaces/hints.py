"""Interfaces for command hints functionality."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Protocol


class HintProvider(Protocol):
    """Protocol for objects that can provide command hints."""

    def get_hints(self, context: Any) -> list[str]:
        """Get command hints for the given context.

        Args:
            context: Context object containing relevant information for generating hints

        Returns:
            List of hint strings to display
        """
        ...


class HintsCapable(ABC):
    """Abstract base class for commands that can display hints."""

    @abstractmethod
    def supports_hints(self) -> bool:
        """Check if this command supports displaying hints.

        Returns:
            True if the command can display hints, False otherwise
        """
        pass

    @abstractmethod
    def get_hint_context(self, **kwargs: Any) -> Any:
        """Get the context object needed for hint generation.

        Args:
            **kwargs: Command execution arguments

        Returns:
            Context object to pass to hint providers
        """
        pass


class HintFormatter(ABC):
    """Abstract base class for formatting hints in output."""

    @abstractmethod
    def format_with_hints(
        self, content: str, hints: list[str], show_hints: bool = True
    ) -> str:
        """Format content with optional hints section.

        Args:
            content: Main content to display
            hints: List of hint strings
            show_hints: Whether to include hints in output

        Returns:
            Formatted output with optional hints section
        """
        pass
