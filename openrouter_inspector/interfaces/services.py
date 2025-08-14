"""Service interfaces for dependency inversion."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import ModelInfo, ProviderDetails, SearchFilters


class ModelServiceInterface(ABC):
    """Abstract interface for model service operations."""

    @abstractmethod
    async def list_models(self) -> list[str]:
        """Return distinct model names in sorted order.

        Returns:
            List of model names
        """
        pass

    @abstractmethod
    async def search_models(
        self, query: str, filters: SearchFilters | None = None
    ) -> list[ModelInfo]:
        """Search models by substring match and optional filters.

        Args:
            query: Case-insensitive substring in either id or name
            filters: Optional search filters

        Returns:
            List of matching models
        """
        pass

    @abstractmethod
    async def get_model_providers(self, model_name: str) -> list[ProviderDetails]:
        """Return detailed provider information for a given model id/name.

        Args:
            model_name: Model name or ID

        Returns:
            List of provider details
        """
        pass
