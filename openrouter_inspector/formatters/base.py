"""Base formatter abstract class."""

from abc import ABC, abstractmethod
from typing import Any, List

from ..models import ModelInfo, ProviderDetails


class BaseFormatter(ABC):
    """Abstract base class for output formatters."""

    @abstractmethod
    def format_models(self, models: List[ModelInfo], **kwargs: Any) -> str:
        """Format a list of models for output.

        Args:
            models: List of ModelInfo objects to format
            **kwargs: Additional formatting options

        Returns:
            Formatted string ready for output
        """
        pass

    @abstractmethod
    def format_providers(self, providers: List[ProviderDetails], **kwargs: Any) -> str:
        """Format a list of provider details for output.

        Args:
            providers: List of ProviderDetails objects to format
            **kwargs: Additional formatting options

        Returns:
            Formatted string ready for output
        """
        pass
