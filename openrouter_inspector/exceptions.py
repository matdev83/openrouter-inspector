"""Custom exception hierarchy for OpenRouter Inspector."""

from __future__ import annotations

from typing import Optional


class OpenRouterError(Exception):
    """Base exception for OpenRouter Inspector."""


class APIError(OpenRouterError):
    """API-related errors."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        self.status_code = status_code
        super().__init__(message)


class AuthenticationError(APIError):
    """Authentication failures (401/403)."""


class RateLimitError(APIError):
    """Rate limiting errors (429)."""


class ValidationError(OpenRouterError):
    """Data validation errors within the client/service layers."""


class WebScrapingError(OpenRouterError):
    """Base exception for web scraping errors."""


class PageNotFoundError(WebScrapingError):
    """Model page not found on web interface."""


class ParseError(WebScrapingError):
    """HTML parsing failed."""


class WebTimeoutError(WebScrapingError):
    """Web request timed out."""
