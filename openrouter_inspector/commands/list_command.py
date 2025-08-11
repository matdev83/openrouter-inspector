"""List command implementation."""

from __future__ import annotations

from typing import Any

from ..models import SearchFilters
from .base_command import BaseCommand


class ListCommand(BaseCommand):
    """Command for listing models with filtering and sorting."""

    async def execute(
        self,
        filters: tuple[str, ...] | None = None,
        min_context: int | None = None,
        tools: bool | None = None,
        no_tools: bool | None = None,
        output_format: str = "table",
        with_providers: bool = False,
        sort_by: str = "id",
        desc: bool = False,
        **kwargs: Any,
    ) -> str:
        """Execute the list command.

        Args:
            filters: Text filters to apply (AND logic).
            min_context: Minimum context window size.
            tools: Filter to models supporting tool calling.
            no_tools: Filter to models NOT supporting tool calling.
            output_format: Output format ('table' or 'json').
            with_providers: Show count of active providers per model.
            sort_by: Sort column ('id', 'name', 'context', 'providers').
            desc: Sort in descending order.
            **kwargs: Additional arguments.

        Returns:
            Formatted output string.
        """
        # Resolve tool support filter value
        tool_support_value: bool | None = None
        if tools is True:
            tool_support_value = True
        elif no_tools is True:
            tool_support_value = False

        # Build search filters
        search_filters = SearchFilters(
            min_context=min_context,
            supports_tools=tool_support_value,
            reasoning_only=None,
            max_price_per_token=None,
        )

        # Get models using handler
        text_filters = list(filters) if filters else None
        models = await self.model_handler.list_models(
            search_filters, text_filters, sort_by, desc
        )

        # Handle provider counts if requested
        if output_format.lower() == "table" and with_providers:
            model_provider_pairs = (
                await self.provider_handler.get_active_provider_counts(models)
            )

            # Sort by providers if requested
            if sort_by.lower() == "providers":
                model_provider_pairs = (
                    self.provider_handler.sort_models_by_provider_count(
                        model_provider_pairs, desc
                    )
                )

            # Extract models and counts for formatting
            models, provider_counts = self.provider_handler.extract_models_and_counts(
                model_provider_pairs
            )

            formatted = self.table_formatter.format_models(
                models, with_providers=True, provider_counts=provider_counts
            )
            return await self._maybe_await(formatted)
        else:
            formatted = self._format_output(models, output_format)
            return await self._maybe_await(formatted)
