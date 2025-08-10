"""Service layer providing business logic atop the API client."""

from __future__ import annotations

import asyncio
from typing import Iterable, List, Sequence

from .client import OpenRouterClient
from .models import ModelInfo, ProviderDetails, SearchFilters


class ModelService:
    """High-level operations for listing, searching, and inspecting models."""

    def __init__(self, client: OpenRouterClient) -> None:
        self.client = client

    async def list_models(self) -> List[str]:
        """Return distinct model names in sorted order.

        Falls back to model id when a name isn't available.
        """
        models: List[ModelInfo] = await self.client.get_models()
        names = {m.name or m.id for m in models}
        return sorted(names)

    async def search_models(self, query: str, filters: SearchFilters | None = None) -> List[ModelInfo]:
        """Search models by substring match and optional filters.

        - query: case-insensitive substring in either id or name
        - filters.min_context: include models with context_length >= value
        - filters.max_price_per_token: include models where any pricing entry <= value
        - filters.supports_tools / filters.reasoning_only: include models that have at least one
          provider satisfying those capabilities (requires provider lookup per candidate model)
        """
        if filters is None:
            filters = SearchFilters(min_context=None, supports_tools=None, reasoning_only=None, max_price_per_token=None)

        all_models: List[ModelInfo] = await self.client.get_models()
        lowered = query.lower().strip() if query else ""

        def matches_basic(model: ModelInfo) -> bool:
            if lowered and lowered not in model.id.lower() and lowered not in model.name.lower():
                return False
            if filters.min_context is not None and model.context_length < filters.min_context:
                return False
            if filters.max_price_per_token is not None and model.pricing:
                min_price = min(model.pricing.values()) if model.pricing else None
                if min_price is None or min_price > filters.max_price_per_token:
                    return False
            return True

        candidates: List[ModelInfo] = [m for m in all_models if matches_basic(m)]

        # If provider-dependent filters are set, fetch providers per candidate
        requires_providers = (filters.supports_tools is not None) or (filters.reasoning_only is True)
        if not requires_providers:
            return candidates

        results: List[ModelInfo] = []
        for model in candidates:
            providers: List[ProviderDetails] = await self.client.get_model_providers(model.id)
            if not providers:
                continue
            any_ok = False
            for pd in providers:
                if filters.supports_tools is not None and pd.provider.supports_tools != filters.supports_tools:
                    continue
                if filters.reasoning_only is True and not pd.provider.is_reasoning_model:
                    continue
                any_ok = True
                break
            if any_ok:
                results.append(model)
        return results

    async def get_model_providers(self, model_name: str) -> List[ProviderDetails]:
        """Return detailed provider information for a given model id/name."""
        return await self.client.get_model_providers(model_name)
