"""Details command implementation."""

from __future__ import annotations

from typing import Any, cast

from ..exceptions import ModelNotFoundError, ProviderNotFoundError
from .base_command import BaseCommand
from .mixins import HintsMixin


class DetailsCommand(HintsMixin, BaseCommand):
    """Command for showing detailed model parameters and features for a specific provider endpoint."""

    async def execute(
        self,
        model_id: str,
        provider_name: str,
        no_hints: bool = False,
        **kwargs: Any,
    ) -> str:
        """Execute the details command.

        Args:
            model_id: Model ID to get details for.
            provider_name: Provider name to get details for.
            no_hints: Do not display helpful command hints below the table output.
            **kwargs: Additional arguments.

        Returns:
            Formatted output string.
        """
        # Parse model@provider shorthand if provided
        if "@" in model_id and not provider_name:
            parts = model_id.split("@", 1)
            model_id = parts[0].strip()
            provider_name = parts[1].strip()

        # Resolve model ID and fetch endpoints
        resolved_id, offers = await self.endpoint_handler.resolve_and_fetch_endpoints(
            model_id
        )

        # Find the specific provider endpoint
        matching_offer = None
        for offer in offers:
            if offer.provider.provider_name.lower() == provider_name.lower():
                matching_offer = offer
                break

        if not matching_offer:
            # List available providers for helpful error message
            available_providers = [offer.provider.provider_name for offer in offers]
            if available_providers:
                raise ProviderNotFoundError(
                    model_id=resolved_id,
                    provider_name=provider_name,
                    available_providers=available_providers,
                )
            else:
                raise ModelNotFoundError(
                    model_id=resolved_id,
                    message=f"No providers found for model '{resolved_id}'",
                )

        # Format output using table formatter without hints
        from ..formatters.table_formatter import TableFormatter

        if isinstance(self.table_formatter, TableFormatter):
            formatted = self.table_formatter.format_model_details(
                matching_offer,
                model_id=resolved_id,
                provider_name=provider_name,
                no_hints=True,
            )
        else:
            formatted = self.table_formatter.format_providers([matching_offer])
        content = cast(str, await self._maybe_await(formatted))

        # Add hints using the hint system
        return self._format_output_with_hints(
            content,
            show_hints=not no_hints,
            model_id=resolved_id,
            provider_name=provider_name,
        )
