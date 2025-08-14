"""Context objects for hint generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class HintContext:
    """Context information for generating command hints."""

    command_name: str
    model_id: str | None = None
    provider_name: str | None = None
    example_model_id: str | None = None
    data: Any = None

    def with_model(self, model_id: str) -> HintContext:
        """Create a new context with the specified model ID."""
        return HintContext(
            command_name=self.command_name,
            model_id=model_id,
            provider_name=self.provider_name,
            example_model_id=self.example_model_id,
            data=self.data,
        )

    def with_provider(self, provider_name: str) -> HintContext:
        """Create a new context with the specified provider name."""
        return HintContext(
            command_name=self.command_name,
            model_id=self.model_id,
            provider_name=provider_name,
            example_model_id=self.example_model_id,
            data=self.data,
        )

    def with_data(self, data: Any) -> HintContext:
        """Create a new context with the specified data."""
        return HintContext(
            command_name=self.command_name,
            model_id=self.model_id,
            provider_name=self.provider_name,
            example_model_id=self.example_model_id,
            data=data,
        )
