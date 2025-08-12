"""List command implementation."""

from __future__ import annotations

from typing import Any, cast

from ..cache import ListCommandCache
from ..models import SearchFilters
from .base_command import BaseCommand


class ListCommand(BaseCommand):
    """Command for listing models with filtering and sorting."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the list command with cache support."""
        super().__init__(*args, **kwargs)
        self.cache = ListCommandCache()

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

        # Create cache key from all parameters
        cache_params = {
            "filters": filters,
            "min_context": min_context,
            "tools": tools,
            "no_tools": no_tools,
            "output_format": output_format,
            "with_providers": with_providers,
            "sort_by": sort_by,
            "desc": desc,
        }

        # Get previous response from cache for comparison
        previous_data = self.cache.get_previous_response(**cache_params)

        # Get models using handler
        text_filters = list(filters) if filters else None
        models = await self.model_handler.list_models(
            search_filters, text_filters, sort_by, desc
        )

        # Store current response in cache
        self.cache.store_response(models, **cache_params)

        # Compare with previous response if available
        new_models: list[Any] = []
        pricing_changes: list[tuple[str, str, Any, Any]] = []
        if previous_data:
            new_models, pricing_changes = self.cache.compare_responses(
                models, previous_data
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
                models,
                with_providers=True,
                provider_counts=provider_counts,
                pricing_changes=pricing_changes,
                new_models=new_models,
            )
            return cast(str, await self._maybe_await(formatted))
        else:
            # For table format, pass comparison data
            if output_format.lower() == "table":
                formatted = self.table_formatter.format_models(
                    models,
                    pricing_changes=pricing_changes,
                    new_models=new_models,
                )
            else:
                formatted = self._format_output(models, output_format)
            return cast(str, await self._maybe_await(formatted))
