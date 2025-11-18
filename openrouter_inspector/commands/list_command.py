"""List command implementation."""

from __future__ import annotations

from typing import Any, cast

from ..cache import ListCommandCache
from ..models import SearchFilters
from .base_command import BaseCommand
from .mixins import HintsMixin


class ListCommand(HintsMixin, BaseCommand):
    """Command for listing models with filtering and sorting."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the list command with cache support."""
        super().__init__(*args, **kwargs)
        self.cache = ListCommandCache()

    async def execute(  # pylint: disable=too-many-arguments,too-many-locals
        self,
        filters: tuple[str, ...] | None = None,
        min_context: int | None = None,
        tools: bool | None = None,
        no_tools: bool | None = None,
        reasoning: bool | None = None,
        no_reasoning: bool | None = None,
        img: bool | None = None,
        no_img: bool | None = None,
        output_format: str = "table",
        with_providers: bool = False,
        sort_by: str = "id",
        desc: bool = False,
        no_hints: bool = False,
        **kwargs: Any,
    ) -> str:
        """Execute the list command.

        Args:
            filters: Text filters to apply (AND logic).
            min_context: Minimum context window size.
            tools: Filter to models supporting tool calling.
            no_tools: Filter to models NOT supporting tool calling.
            reasoning: Filter to models supporting reasoning features.
            no_reasoning: Filter to models without reasoning features.
            img: Filter to models supporting image input.
            no_img: Filter to models without image input support.
            output_format: Output format ('table' or 'json').
            with_providers: Show count of active providers per model.
            sort_by: Sort column ('id', 'name', 'context', 'providers').
            desc: Sort in descending order.
            **kwargs: Additional arguments.

        Returns:
            Formatted output string.
        """
        (
            search_filters,
            cache_params,
        ) = self._prepare_search_filters_and_cache_params(
            filters=filters,
            min_context=min_context,
            tools=tools,
            no_tools=no_tools,
            reasoning=reasoning,
            no_reasoning=no_reasoning,
            img=img,
            no_img=no_img,
            output_format=output_format,
            with_providers=with_providers,
            sort_by=sort_by,
            desc=desc,
        )

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
                show_endpoints_hint=False,  # Disable formatter hints
                example_model_id=models[0].id if models else None,
            )
            content = cast(str, await self._maybe_await(formatted))

            # Add hints using the hint system
            return self._format_output_with_hints(
                content,
                show_hints=not no_hints,
                example_model_id=models[0].id if models else None,
            )
        else:
            # For table format, pass comparison data
            if output_format.lower() == "table":
                formatted = self.table_formatter.format_models(
                    models,
                    pricing_changes=pricing_changes,
                    new_models=new_models,
                    show_endpoints_hint=False,  # Disable formatter hints
                    example_model_id=models[0].id if models else None,
                )
                content = cast(str, await self._maybe_await(formatted))

                # Add hints using the hint system
                return self._format_output_with_hints(
                    content,
                    show_hints=not no_hints,
                    example_model_id=models[0].id if models else None,
                )
            else:
                formatted = self._format_output(models, output_format)
                return cast(str, await self._maybe_await(formatted))

    def _prepare_search_filters_and_cache_params(  # pylint: disable=too-many-arguments,too-many-locals
        self,
        *,
        filters: tuple[str, ...] | None,
        min_context: int | None,
        tools: bool | None,
        no_tools: bool | None,
        reasoning: bool | None,
        no_reasoning: bool | None,
        img: bool | None,
        no_img: bool | None,
        output_format: str,
        with_providers: bool,
        sort_by: str,
        desc: bool,
    ) -> tuple[SearchFilters, dict[str, Any]]:
        """Build the Pydantic filter object and cache parameters map."""
        tool_support_value = self._resolve_flag_pair(tools, no_tools)
        reasoning_filter_value = self._resolve_flag_pair(reasoning, no_reasoning)
        image_support_value = self._resolve_flag_pair(img, no_img)

        search_filters = SearchFilters(
            min_context=min_context,
            supports_tools=tool_support_value,
            reasoning_only=reasoning_filter_value,
            supports_image_input=image_support_value,
            max_price_per_token=None,
        )

        cache_params = {
            "filters": filters,
            "min_context": min_context,
            "tools": tools,
            "no_tools": no_tools,
            "reasoning": reasoning,
            "no_reasoning": no_reasoning,
            "img": img,
            "no_img": no_img,
            "output_format": output_format,
            "with_providers": with_providers,
            "sort_by": sort_by,
            "desc": desc,
        }
        return search_filters, cache_params

    @staticmethod
    def _resolve_flag_pair(
        include_flag: bool | None, exclude_flag: bool | None
    ) -> bool | None:
        """Resolve mutually exclusive include/exclude flags into a tri-state value."""
        if include_flag is True:
            return True
        if exclude_flag is True:
            return False
        return None
