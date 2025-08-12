"""JSON output formatter."""

import json
from typing import Any

from ..models import ModelInfo, ProviderDetails
from .base import BaseFormatter


class JsonFormatter(BaseFormatter):
    """Formats output as JSON."""

    def format_models(self, models: list[ModelInfo], **kwargs: Any) -> str:
        """Format models as JSON.

        Args:
            models: List of ModelInfo objects to format
            **kwargs: Additional formatting options (unused for JSON)

        Returns:
            JSON formatted string
        """
        return json.dumps([m.model_dump() for m in models], indent=2, default=str)

    def format_providers(self, providers: list[ProviderDetails], **kwargs: Any) -> str:
        """Format provider details as JSON.

        Args:
            providers: List of ProviderDetails objects to format
            **kwargs: Additional formatting options (unused for JSON)

        Returns:
            JSON formatted string
        """
        return json.dumps([p.model_dump() for p in providers], indent=2, default=str)
