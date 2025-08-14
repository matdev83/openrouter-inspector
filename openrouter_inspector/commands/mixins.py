"""Mixins for command functionality."""

from __future__ import annotations

from typing import Any

from ..hints import HintService
from ..hints.context import HintContext
from ..interfaces.hints import HintsCapable


class HintsMixin(HintsCapable):
    """Mixin for commands that support displaying hints."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the hints mixin."""
        super().__init__(*args, **kwargs)
        self._hint_service = HintService()

    def supports_hints(self) -> bool:
        """Check if this command supports displaying hints."""
        command_name = self.__class__.__name__.lower().replace("command", "")
        return self._hint_service.supports_hints(command_name)

    def get_hint_context(self, **kwargs: Any) -> HintContext:
        """Get the context object needed for hint generation."""
        command_name = self.__class__.__name__.lower().replace("command", "")
        return HintContext(
            command_name=command_name,
            model_id=kwargs.get("model_id"),
            provider_name=kwargs.get("provider_name"),
            example_model_id=kwargs.get("example_model_id"),
            data=kwargs.get("data"),
        )

    def _format_output_with_hints(
        self, content: str, show_hints: bool = True, **hint_kwargs: Any
    ) -> str:
        """Format output with optional hints.

        Args:
            content: Main content to display
            show_hints: Whether to show hints
            **hint_kwargs: Arguments for hint context generation

        Returns:
            Formatted output with optional hints
        """
        if not show_hints or not self.supports_hints():
            return content

        context = self.get_hint_context(**hint_kwargs)
        hints = self._hint_service.get_hints(context)

        if not hints:
            return content

        # Format hints section
        hints_section = "\n\n💡 Quick Commands:\n\n" + "\n".join(hints)
        return content + hints_section
