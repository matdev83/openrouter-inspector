"""Handler for model listing and searching operations."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from ..interfaces.services import ModelServiceInterface
from ..models import ModelInfo, SearchFilters

logger = logging.getLogger(__name__)


class ModelHandler:
    """Handles model listing, searching, filtering, and sorting operations."""

    def __init__(self, model_service: ModelServiceInterface) -> None:
        """Initialize the ModelHandler with a model service instance.

        Args:
            model_service: The model service instance to use for API operations.
        """
        self.model_service = model_service

    async def list_models(
        self,
        filters: SearchFilters,
        text_filters: list[str] | None = None,
        sort_by: str = "id",
        desc: bool = False,
    ) -> list[ModelInfo]:
        """List models with filtering and sorting.

        Args:
            filters: SearchFilters object with API-level filters.
            text_filters: Optional list of text filters to apply (AND logic).
            sort_by: Field to sort by ('id', 'name', 'context').
            desc: Whether to sort in descending order.

        Returns:
            List of filtered and sorted ModelInfo objects.
        """
        # Get models using service layer with API filters
        models = await self.model_service.search_models("", filters)

        # Apply text filters with AND logic if provided
        if text_filters:
            filter_terms = [f.lower() for f in text_filters]
            models = [
                m
                for m in models
                if all(
                    term in m.id.lower() or term in m.name.lower()
                    for term in filter_terms
                )
            ]

        # Apply sorting
        models = self._sort_models(models, sort_by, desc)

        return models

    async def search_models(
        self,
        query: str,
        filters: SearchFilters,
        sort_by: str = "id",
        desc: bool = False,
    ) -> list[ModelInfo]:
        """Search models with a query and filters.

        Args:
            query: Search query string.
            filters: SearchFilters object with additional filters.
            sort_by: Field to sort by ('id', 'name', 'context').
            desc: Whether to sort in descending order.

        Returns:
            List of matching and sorted ModelInfo objects.
        """
        models = await self.model_service.search_models(query, filters)
        return self._sort_models(models, sort_by, desc)

    async def filter_models_by_query(
        self,
        models: list[ModelInfo],
        query: str,
    ) -> list[ModelInfo]:
        """Filter a list of models by a search query.

        Args:
            models: List of ModelInfo objects to filter.
            query: Search query to match against model ID and name.

        Returns:
            Filtered list of ModelInfo objects.
        """
        if not query:
            return models

        q = query.lower()
        return [m for m in models if q in m.id.lower() or q in m.name.lower()]

    def _sort_models(
        self,
        models: list[ModelInfo],
        sort_by: str,
        desc: bool = False,
    ) -> list[ModelInfo]:
        """Sort models by the specified field.

        Args:
            models: List of ModelInfo objects to sort.
            sort_by: Field to sort by ('id', 'name', 'context').
            desc: Whether to sort in descending order.

        Returns:
            Sorted list of ModelInfo objects.
        """
        key_fn = self._get_sort_key_function(sort_by)
        if key_fn is not None:
            return sorted(models, key=key_fn, reverse=desc)
        return models

    def _get_sort_key_function(self, sort_by: str) -> Callable[[ModelInfo], Any] | None:
        """Get the appropriate sort key function for the given field.

        Args:
            sort_by: Field to sort by.

        Returns:
            Sort key function or None if field is not supported.
        """
        sort_by_lower = sort_by.lower()

        if sort_by_lower == "id":
            return lambda m: m.id.lower()
        elif sort_by_lower == "name":
            return lambda m: m.name.lower()
        elif sort_by_lower == "context":
            return lambda m: m.context_length

        return None
