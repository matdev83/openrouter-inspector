"""Endpoints command implementation."""

from __future__ import annotations

from typing import Any, cast

from .base_command import BaseCommand
from .mixins import HintsMixin


class EndpointsCommand(HintsMixin, BaseCommand):
    """Command for showing detailed provider endpoints for a model."""

    async def execute(
        self,
        model_id: str,
        output_format: str = "table",
        sort_by: str = "api",
        desc: bool = False,
        min_quant: str | None = None,
        min_context: str | None = None,
        reasoning_required: bool | None = None,
        no_reasoning_required: bool | None = None,
        tools_required: bool | None = None,
        no_tools_required: bool | None = None,
        img_required: bool | None = None,
        no_img_required: bool | None = None,
        max_input_price: float | None = None,
        max_output_price: float | None = None,
        no_hints: bool = False,
        **kwargs: Any,
    ) -> str:
        """Execute the endpoints command.

        Args:
            model_id: Model ID to get endpoints for.
            output_format: Output format ('table' or 'json').
            sort_by: Sort column for offers output.
            desc: Sort in descending order.
            min_quant: Minimum quantization requirement.
            min_context: Minimum context window requirement.
            reasoning_required: Whether reasoning support is required.
            no_reasoning_required: Whether reasoning support should be excluded.
            tools_required: Whether tool support is required.
            no_tools_required: Whether tool support should be excluded.
            img_required: Whether image support is required.
            no_img_required: Whether image support should be excluded.
            max_input_price: Maximum input token price (per million USD).
            max_output_price: Maximum output token price (per million USD).
            no_hints: Do not display helpful command hints below the table output.
            **kwargs: Additional arguments.

        Returns:
            Formatted output string.
        """
        # Resolve model ID and fetch endpoints
        resolved_id, offers = await self.endpoint_handler.resolve_and_fetch_endpoints(
            model_id
        )

        # Apply filters
        filtered_offers = self.endpoint_handler.filter_endpoints(
            offers,
            min_quant=min_quant,
            min_context=min_context,
            reasoning_required=reasoning_required,
            no_reasoning_required=no_reasoning_required,
            tools_required=tools_required,
            no_tools_required=no_tools_required,
            img_required=img_required,
            no_img_required=no_img_required,
            max_input_price=max_input_price,
            max_output_price=max_output_price,
        )

        # Apply sorting
        sorted_offers = self.endpoint_handler.sort_endpoints(
            filtered_offers, sort_by, desc
        )

        # Format output
        if output_format.lower() == "json":
            formatted = self.json_formatter.format_providers(sorted_offers)
            return cast(str, await self._maybe_await(formatted))
        else:
            # Format table without hints in the formatter
            formatted = self.table_formatter.format_providers(
                sorted_offers, model_id=resolved_id, no_hints=True
            )
            content = cast(str, await self._maybe_await(formatted))

            # Add hints using the hint system
            return self._format_output_with_hints(
                content,
                show_hints=not no_hints,
                model_id=resolved_id,
                data=sorted_offers,
            )
