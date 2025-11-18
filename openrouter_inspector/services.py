"""Service layer providing business logic atop the API client."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .interfaces.client import APIClient
from .interfaces.services import ModelServiceInterface
from .models import (
    ModelInfo,
    ProviderDetails,
    SearchFilters,
)

# Import WebScrapingService with TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class ModelService(ModelServiceInterface):
    """High-level operations for listing, searching, and inspecting models."""

    def __init__(self, client: APIClient) -> None:
        self.client = client

    async def list_models(self) -> list[str]:
        """Return distinct model names in sorted order.

        Falls back to model id when a name isn't available.
        """
        models: list[ModelInfo] = await self.client.get_models()
        names = {m.name or m.id for m in models}
        return sorted(names)

    async def search_models(
        self, query: str, filters: SearchFilters | None = None
    ) -> list[ModelInfo]:
        """Search models by substring match and optional filters.

        - query: case-insensitive substring in either id or name
        - filters.min_context: include models with context_length >= value
        - filters.max_price_per_token: include models where any pricing entry <= value
        - filters.supports_tools / filters.reasoning_only: include models that have at least one
          provider satisfying those capabilities (requires provider lookup per candidate model)
        """
        if filters is None:
            filters = SearchFilters(
                min_context=None,
                supports_tools=None,
                reasoning_only=None,
                supports_image_input=None,
                max_price_per_token=None,
            )

        all_models: list[ModelInfo] = await self.client.get_models()
        lowered = query.lower().strip() if query else ""

        def matches_basic(model: ModelInfo) -> bool:
            if (
                lowered
                and lowered not in model.id.lower()
                and lowered not in model.name.lower()
            ):
                return False
            if (
                filters.min_context is not None
                and model.context_length < filters.min_context
            ):
                return False
            if filters.max_price_per_token is not None and model.pricing:
                min_price = min(model.pricing.values()) if model.pricing else None
                if min_price is None or min_price > filters.max_price_per_token:
                    return False
            return True

        candidates: list[ModelInfo] = [m for m in all_models if matches_basic(m)]

        # If provider-dependent filters are set, fetch providers per candidate
        requires_providers = any(
            value is not None
            for value in (
                filters.supports_tools,
                filters.reasoning_only,
                filters.supports_image_input,
            )
        )
        if not requires_providers:
            return candidates

        results: list[ModelInfo] = []
        for model in candidates:
            if await self._providers_match_filters(model, filters):
                results.append(model)
        return results

    async def get_model_providers(self, model_name: str) -> list[ProviderDetails]:
        """Return detailed provider information for a given model id/name."""
        return await self.client.get_model_providers(model_name)

    async def _providers_match_filters(
        self,
        model: ModelInfo,
        filters: SearchFilters,
    ) -> bool:
        """Return True if the model has at least one provider matching the filters."""
        providers: list[ProviderDetails] = await self.client.get_model_providers(
            model.id
        )
        if not providers:
            return False

        for pd in providers:
            provider = pd.provider
            if (
                filters.supports_tools is not None
                and provider.supports_tools != filters.supports_tools
            ):
                continue
            if (
                filters.reasoning_only is not None
                and provider.is_reasoning_model != filters.reasoning_only
            ):
                continue
            if (
                filters.supports_image_input is not None
                and provider.supports_image_input != filters.supports_image_input
            ):
                continue
            return True
        return False

    # All web-scraping-related methods removed

    def _normalize_provider_name(self, provider_name: str) -> str:
        """
        Normalize provider name for matching between API and web data.

        Args:
            provider_name: Raw provider name

        Returns:
            Normalized provider name for consistent matching
        """
        if not provider_name:
            return ""

        # Convert to lowercase and strip whitespace
        normalized = provider_name.strip().lower()

        # Handle common variations in provider names
        # Remove common suffixes/prefixes that might differ between API and web
        suffixes_to_remove = [
            " corporation",
            " company",
            " corp",
            " inc",
            " llc",
            " ltd",
            " ai",
            " co",
            ".ai",
            ".com",
            ".io",
        ]

        # Sort by length (longest first) to avoid partial matches
        suffixes_to_remove.sort(key=len, reverse=True)

        # Keep removing suffixes until no more can be removed
        changed = True
        while changed:
            changed = False
            for suffix in suffixes_to_remove:
                if normalized.endswith(suffix):
                    normalized = normalized[: -len(suffix)].strip()
                    changed = True
                    break

        # Replace multiple spaces with single space and strip again
        import re

        normalized = re.sub(r"\s+", " ", normalized).strip()

        return normalized
