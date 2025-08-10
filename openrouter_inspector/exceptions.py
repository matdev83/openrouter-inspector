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


# Web scraping exceptions removed
