"""Handler for endpoint resolution and filtering operations."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from ..interfaces.client import APIClient
from ..interfaces.services import ModelServiceInterface
from ..models import ProviderDetails
from ..utils import (
    check_parameter_support,
    parse_context_threshold,
    parse_quantization_bits,
)

logger = logging.getLogger(__name__)


class EndpointHandler:
    """Handles endpoint resolution, filtering, and sorting operations."""

    def __init__(self, client: APIClient, model_service: ModelServiceInterface) -> None:
        """Initialize the EndpointHandler.

        Args:
            client: The API client instance to use for API operations.
            model_service: The model service instance to use for model operations.
        """
        self.client = client
        self.model_service = model_service

    async def resolve_and_fetch_endpoints(
        self, model_id: str
    ) -> tuple[str, list[ProviderDetails]]:
        """Resolve model ID and fetch endpoints.

        Tries exact model ID first, then attempts partial matching if not found.

        Args:
            model_id: The model ID to resolve and fetch endpoints for.

        Returns:
            Tuple of (resolved_model_id, list_of_provider_details).
        """
        # Try exact match first
        try:
            api_offers = await self.model_service.get_model_providers(model_id)
            return model_id, (api_offers or [])
        except Exception as e:
            logger.debug(f"Exact match providers fetch failed for '{model_id}': {e}")

        # Search for candidates by substring
        try:
            all_models = await self.client.get_models()
        except Exception as e:
            logger.debug(f"Failed to get models list: {e}")
            return model_id, []

        # Find partial matches
        s = model_id.lower()
        candidates = [m for m in all_models if s in m.id.lower() or s in m.name.lower()]

        # Check for exact match in candidates (case-insensitive)
        exact_matches = [m for m in candidates if m.id.lower() == s]
        if exact_matches:
            resolved = exact_matches[0].id
            try:
                api_offers = await self.model_service.get_model_providers(resolved)
                return resolved, (api_offers or [])
            except Exception as e:
                logger.debug(
                    f"Exact-match resolved providers fetch failed for '{resolved}': {e}"
                )
                return resolved, []

        # If multiple candidates, try each one until we find one that works
        if len(candidates) > 1:
            # Prefer non-free versions if available
            non_free_candidates = [m for m in candidates if ":free" not in m.id.lower()]
            if non_free_candidates:
                candidates = non_free_candidates

            # If still multiple, sort by ID length (prefer shorter IDs)
            candidates.sort(key=lambda m: len(m.id))

            # Try each candidate until we find one that works
            for candidate in candidates:
                try:
                    api_offers = await self.model_service.get_model_providers(
                        candidate.id
                    )
                    return candidate.id, (api_offers or [])
                except Exception as e:
                    logger.debug(f"Failed to get offers for {candidate.id}: {e}")
                    continue

            # If none worked, return empty with candidate info for error handling
            return model_id, []

        # If exactly one candidate, use it
        if len(candidates) == 1:
            resolved = candidates[0].id
            try:
                api_offers = await self.model_service.get_model_providers(resolved)
                return resolved, (api_offers or [])
            except Exception as e:
                logger.debug(
                    f"Single-candidate providers fetch failed for '{resolved}': {e}"
                )
                return resolved, []

        # No matches found
        return model_id, []

    def filter_endpoints(
        self,
        offers: list[ProviderDetails],
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
    ) -> list[ProviderDetails]:
        """Filter endpoints based on various criteria.

        Args:
            offers: List of ProviderDetails to filter.
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

        Returns:
            Filtered list of ProviderDetails.
        """
        min_bits = parse_quantization_bits(min_quant) if min_quant else None
        min_ctx = parse_context_threshold(min_context) if min_context else 0

        filtered_offers = []
        for offer in offers:
            if self._offer_passes_filters(
                offer,
                min_bits,
                min_ctx,
                reasoning_required,
                no_reasoning_required,
                tools_required,
                no_tools_required,
                img_required,
                no_img_required,
                max_input_price,
                max_output_price,
            ):
                filtered_offers.append(offer)

        return filtered_offers

    def sort_endpoints(
        self,
        offers: list[ProviderDetails],
        sort_by: str = "api",
        desc: bool = False,
    ) -> list[ProviderDetails]:
        """Sort endpoints by the specified field.

        Args:
            offers: List of ProviderDetails to sort.
            sort_by: Field to sort by.
            desc: Whether to sort in descending order.

        Returns:
            Sorted list of ProviderDetails.
        """
        if sort_by.lower() == "api" or not offers:
            return offers

        key_fn = self._get_endpoint_sort_key_function(sort_by)
        if key_fn is not None:
            return sorted(offers, key=key_fn, reverse=desc)
        return offers

    def _offer_passes_filters(
        self,
        offer: ProviderDetails,
        min_bits: float | None,
        min_ctx: int,
        reasoning_required: bool | None,
        no_reasoning_required: bool | None,
        tools_required: bool | None,
        no_tools_required: bool | None,
        img_required: bool | None,
        no_img_required: bool | None,
        max_input_price: float | None,
        max_output_price: float | None,
    ) -> bool:
        """Check if an offer passes all the specified filters."""
        p = offer.provider

        # Quantization filter
        if min_bits is not None:
            if parse_quantization_bits(p.quantization) < min_bits:
                return False

        # Context filter
        if min_ctx and (p.context_window or 0) < min_ctx:
            return False

        # Reasoning filters
        if reasoning_required is not None or no_reasoning_required is not None:
            reasoning_supported = check_parameter_support(
                p.supported_parameters, "reasoning"
            )
            if reasoning_required and not reasoning_supported:
                return False
            if no_reasoning_required and reasoning_supported:
                return False

        # Tools filters
        if tools_required is not None or no_tools_required is not None:
            if tools_required and not p.supports_tools:
                return False
            if no_tools_required and p.supports_tools:
                return False

        # Image filters
        if img_required is not None or no_img_required is not None:
            image_supported = check_parameter_support(p.supported_parameters, "image")
            if img_required and not image_supported:
                return False
            if no_img_required and image_supported:
                return False

        # Price filters
        if max_input_price is not None:
            price_in = p.pricing.get("prompt") if p.pricing else None
            if price_in is not None:
                price_in_per_million = price_in * 1_000_000.0
                if price_in_per_million > max_input_price:
                    return False

        if max_output_price is not None:
            price_out = p.pricing.get("completion") if p.pricing else None
            if price_out is not None:
                price_out_per_million = price_out * 1_000_000.0
                if price_out_per_million > max_output_price:
                    return False

        return True

    def _get_endpoint_sort_key_function(
        self, sort_by: str
    ) -> Callable[[ProviderDetails], Any] | None:
        """Get the appropriate sort key function for endpoints."""
        key = sort_by.lower()
        if key == "provider":
            return lambda o: (o.provider.provider_name or "").lower()
        elif key == "model":
            return lambda o: (o.provider.endpoint_name or "").lower()
        elif key == "quant":
            return lambda o: (o.provider.quantization or "").lower()
        elif key == "context":
            return lambda o: o.provider.context_window or 0
        elif key == "maxout":
            return lambda o: o.provider.max_completion_tokens or 0
        elif key == "price_in":
            return lambda o: (o.provider.pricing or {}).get("prompt", float("inf"))
        elif key == "price_out":
            return lambda o: (o.provider.pricing or {}).get("completion", float("inf"))
        return None
