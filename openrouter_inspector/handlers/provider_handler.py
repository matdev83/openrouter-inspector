"""Handler for provider processing operations."""

from __future__ import annotations

import logging

from ..interfaces.client import APIClient
from ..models import ModelInfo, ProviderDetails

logger = logging.getLogger(__name__)


class ProviderHandler:
    """Handles provider counting, filtering, and data enrichment operations."""

    def __init__(self, client: APIClient) -> None:
        """Initialize the ProviderHandler with an API client instance.

        Args:
            client: The API client instance to use for API operations.
        """
        self.client = client

    async def get_active_provider_counts(
        self, models: list[ModelInfo]
    ) -> list[tuple[ModelInfo, int]]:
        """Get active provider counts for a list of models.

        Args:
            models: List of ModelInfo objects to get provider counts for.

        Returns:
            List of tuples containing (ModelInfo, active_provider_count).
        """
        rows = []
        for model in models:
            providers = await self.client.get_model_providers(model.id)
            active_count = self._count_active_providers(providers)
            rows.append((model, active_count))
        return rows

    async def get_model_providers(self, model_id: str) -> list[ProviderDetails]:
        """Get provider details for a specific model.

        Args:
            model_id: The model ID to get providers for.

        Returns:
            List of ProviderDetails objects.
        """
        return await self.client.get_model_providers(model_id)

    def _count_active_providers(self, providers: list[ProviderDetails]) -> int:
        """Count active providers from a list of provider details.

        Args:
            providers: List of ProviderDetails objects.

        Returns:
            Number of active providers.
        """
        return len(
            [
                p
                for p in providers
                if p.availability and (p.provider.status != "offline")
            ]
        )

    def sort_models_by_provider_count(
        self,
        model_provider_pairs: list[tuple[ModelInfo, int]],
        desc: bool = False,
    ) -> list[tuple[ModelInfo, int]]:
        """Sort model-provider pairs by provider count.

        Args:
            model_provider_pairs: List of (ModelInfo, provider_count) tuples.
            desc: Whether to sort in descending order.

        Returns:
            Sorted list of (ModelInfo, provider_count) tuples.
        """
        return sorted(model_provider_pairs, key=lambda t: t[1], reverse=desc)

    def extract_models_and_counts(
        self, model_provider_pairs: list[tuple[ModelInfo, int]]
    ) -> tuple[list[ModelInfo], list[int]]:
        """Extract separate lists of models and provider counts.

        Args:
            model_provider_pairs: List of (ModelInfo, provider_count) tuples.

        Returns:
            Tuple of (models_list, provider_counts_list).
        """
        models = [m for m, _ in model_provider_pairs]
        provider_counts = [cnt for _, cnt in model_provider_pairs]
        return models, provider_counts
