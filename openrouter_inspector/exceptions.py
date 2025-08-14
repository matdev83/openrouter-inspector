"""Custom exception hierarchy for OpenRouter Inspector."""

from __future__ import annotations


class OpenRouterError(Exception):
    """Base exception for OpenRouter Inspector."""


class APIError(OpenRouterError):
    """API-related errors."""

    def __init__(self, message: str, status_code: int | None = None):
        self.status_code = status_code
        super().__init__(message)


class AuthenticationError(APIError):
    """Authentication failures (401/403)."""


class RateLimitError(APIError):
    """Rate limiting errors (429)."""


class ValidationError(OpenRouterError):
    """Data validation errors within the client/service layers."""


class ModelNotFoundError(OpenRouterError):
    """Model not found error."""

    def __init__(self, model_id: str, message: str | None = None):
        self.model_id = model_id
        super().__init__(message or f"Model '{model_id}' not found")


class ProviderNotFoundError(OpenRouterError):
    """Provider not found for a specific model."""

    def __init__(
        self,
        model_id: str,
        provider_name: str,
        available_providers: list[str] | None = None,
        message: str | None = None,
    ):
        self.model_id = model_id
        self.provider_name = provider_name
        self.available_providers = available_providers or []

        if message:
            super().__init__(message)
        elif available_providers:
            providers_list = ", ".join(available_providers)
            super().__init__(
                f"Provider '{provider_name}' not found for model '{model_id}'. "
                f"Available providers: {providers_list}"
            )
        else:
            super().__init__(
                f"Provider '{provider_name}' not found for model '{model_id}'"
            )


# Web scraping exceptions removed
