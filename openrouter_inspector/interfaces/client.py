"""Client interface for dependency inversion."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..models import ModelInfo, ProviderDetails


class APIClient(ABC):
    """Abstract interface for API client operations."""

    @abstractmethod
    async def get_models(self) -> list[ModelInfo]:
        """Retrieve all available models from the API.

        Returns:
            List of available models
        """
        pass

    @abstractmethod
    async def get_model_providers(self, model_name: str) -> list[ProviderDetails]:
        """Get all providers for a specific model.

        Args:
            model_name: Name or ID of the model to query

        Returns:
            List of provider details for the model
        """
        pass

    @abstractmethod
    async def create_chat_completion(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        provider_order: list[str] | None = None,
        allow_fallbacks: bool | None = None,
        timeout_seconds: int | None = None,
        extra_headers: dict[str, str] | None = None,
        extra_body: dict[str, Any] | None = None,
        retries_enabled: bool = True,
        silent_rate_limit: bool = False,
    ) -> tuple[dict[str, Any], dict[str, str]]:
        """Call API chat completions endpoint.

        Args:
            model: Model ID (author/slug)
            messages: OpenAI-compatible messages list
            provider_order: Optional explicit provider order to try
            allow_fallbacks: When False, do not allow fallback providers
            timeout_seconds: Per-request timeout override
            extra_headers: Optional headers to include
            extra_body: Optional extra body fields to merge
            retries_enabled: Whether to enable retry logic
            silent_rate_limit: If True, don't log warnings for rate limits

        Returns:
            Tuple of (response_json, response_headers)
        """
        pass

    @abstractmethod
    async def create_chat_completion_stream(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        provider_order: list[str] | None = None,
        allow_fallbacks: bool | None = None,
        timeout_seconds: int | None = None,
        extra_headers: dict[str, str] | None = None,
        extra_body: dict[str, Any] | None = None,
        retries_enabled: bool = True,
        silent_rate_limit: bool = False,
    ) -> tuple[Any, dict[str, str]]:
        """Call API chat completions endpoint with streaming.

        Args:
            model: Model ID (author/slug)
            messages: OpenAI-compatible messages list
            provider_order: Optional explicit provider order to try
            allow_fallbacks: When False, do not allow fallback providers
            timeout_seconds: Per-request timeout override
            extra_headers: Optional headers to include
            extra_body: Optional extra body fields to merge
            retries_enabled: Whether to enable retry logic
            silent_rate_limit: If True, don't log warnings for rate limits

        Returns:
            Tuple of (async_generator, response_headers)
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the client and clean up resources."""
        pass

    @abstractmethod
    async def __aenter__(self) -> APIClient:
        """Async context manager entry."""
        pass

    @abstractmethod
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        pass
