"""OpenRouter API client with async HTTP support and retry logic."""

import asyncio
import logging
from datetime import datetime
from types import TracebackType
from typing import Any
from urllib.parse import urljoin

import httpx
from pydantic import ValidationError as PydanticValidationError

from .exceptions import (
    APIError,
    AuthenticationError,
    RateLimitError,
    ValidationError,
)
from .interfaces.client import APIClient
from .models import (
    ModelInfo,
    ProviderDetails,
    ProviderInfo,
)

# CacheManager removed; inline simple no-op cache interface if needed


logger = logging.getLogger(__name__)


class OpenRouterClient(APIClient):
    """Async HTTP client for OpenRouter API with retry logic and error handling."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
        timeout: int = 30,
    ):
        """Initialize the OpenRouter client.

        Args:
            api_key: OpenRouter API key for authentication.
            base_url: Base URL for the OpenRouter API.
            timeout: Request timeout in seconds.
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

        # HTTP client configuration
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "openrouter-inspector/0.1.0",
        }

        self.client = httpx.AsyncClient(
            headers=headers,
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )
        # Simple no-op cache
        self._cache = None

        # Retry configuration
        self.max_retries = 3
        self.base_delay: float = 1.0  # Base delay for exponential backoff
        self.max_delay: float = 60.0  # Maximum delay between retries

    @staticmethod
    def _parse_datetime(  # pylint: disable=too-many-return-statements,too-complex
        value: Any,
    ) -> datetime:
        """Parse various datetime representations robustly.

        Accepts ISO strings (with optional trailing 'Z'), integer/float timestamps in
        seconds or milliseconds, and falls back to current time when parsing fails.
        """
        if isinstance(value, str):
            s = value
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            try:
                return datetime.fromisoformat(s)
            except ValueError:
                # Try numeric string timestamp
                try:
                    tsf = float(s)
                except ValueError:
                    return datetime.now()
                if tsf > 1_000_000_000_000:  # ms
                    tsf = tsf / 1000.0
                try:
                    return datetime.fromtimestamp(tsf)
                except (OverflowError, OSError, ValueError):
                    return datetime.now()
        if isinstance(value, int | float):
            tsf = float(value)
            if tsf > 1_000_000_000_000:  # ms
                tsf = tsf / 1000.0
            try:
                return datetime.fromtimestamp(tsf)
            except (OverflowError, OSError, ValueError):
                return datetime.now()
        return datetime.now()

    async def __aenter__(self) -> "OpenRouterClient":
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Async context manager exit."""
        # Silence unused variable warnings - these are required for context manager protocol
        _ = exc_type, exc_val, exc_tb
        await self.close()

    async def close(self) -> None:
        """Close the HTTP client and clean up resources."""
        if self.client:
            await self.client.aclose()

    async def _make_request(  # pylint: disable=too-many-branches,too-many-statements,too-complex
        self,
        method: str,
        endpoint: str,
        *,
        retries_enabled: bool = True,
        silent_rate_limit: bool = False,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make HTTP request with retry logic and error handling.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            retries_enabled: Whether to retry failed requests
            silent_rate_limit: If True, don't log warnings for rate limits
            **kwargs: Additional arguments for httpx request

        Returns:
            httpx.Response: HTTP response object

        Raises:
            AuthenticationError: For 401/403 status codes
            RateLimitError: For 429 status codes
            APIError: For other HTTP errors
        """
        url = urljoin(self.base_url + "/", endpoint.lstrip("/"))

        max_attempts = self.max_retries + 1 if retries_enabled else 1

        for attempt in range(max_attempts):
            try:
                logger.debug(
                    f"Making {method} request to {url} (attempt {attempt + 1})"
                )
                response = await self.client.request(method, url, **kwargs)

                # Handle specific HTTP status codes
                if response.status_code == 401:
                    raise AuthenticationError(
                        "Invalid API key. Please check your OpenRouter API key.",
                        status_code=401,
                    )
                elif response.status_code == 403:
                    raise AuthenticationError(
                        "Access forbidden. Please check your API key permissions.",
                        status_code=403,
                    )
                elif response.status_code == 429:
                    if attempt < self.max_retries:
                        delay = min(self.base_delay * (2**attempt), self.max_delay)
                        if not silent_rate_limit:
                            logger.warning(f"Rate limited. Retrying in {delay:.1f}s...")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        raise RateLimitError(
                            "Rate limit exceeded. Please try again later.",
                            status_code=429,
                        )
                elif response.status_code >= 500:
                    if attempt < self.max_retries:
                        delay = min(self.base_delay * (2**attempt), self.max_delay)
                        if not silent_rate_limit:
                            logger.warning(
                                f"Server error {response.status_code}. Retrying in {delay:.1f}s..."
                            )
                        await asyncio.sleep(delay)
                        continue
                    else:
                        raise APIError(
                            f"Server error: {response.status_code} {response.reason_phrase}",
                            status_code=response.status_code,
                        )
                elif not response.is_success:
                    try:
                        error_data = response.json()
                        error_message = error_data.get("error", {}).get(
                            "message", "Unknown error"
                        )
                    except Exception:
                        error_message = (
                            f"HTTP {response.status_code}: {response.reason_phrase}"
                        )

                    raise APIError(error_message, status_code=response.status_code)

                # Success - return response
                return response

            except httpx.TimeoutException:
                if attempt < self.max_retries:
                    delay = min(self.base_delay * (2**attempt), self.max_delay)
                    logger.debug(f"Request timeout. Retrying in {delay:.1f}s...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise APIError(
                        "Request timeout. Please check your connection."
                    ) from None

            except httpx.ConnectError:
                if attempt < self.max_retries:
                    delay = min(self.base_delay * (2**attempt), self.max_delay)
                    logger.debug(f"Connection error. Retrying in {delay:.1f}s...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise APIError(
                        "Connection error. Please check your internet connection."
                    ) from None

            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                if attempt < self.max_retries:
                    delay = min(self.base_delay * (2**attempt), self.max_delay)
                    logger.debug(f"Request error: {e}. Retrying in {delay:.1f}s...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise APIError(f"Request failed: {e}") from e

        # This should never be reached, but just in case
        raise APIError("Maximum retries exceeded")

    async def create_chat_completion(  # pylint: disable=too-many-arguments,too-many-locals
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
        """Call OpenRouter chat completions endpoint.

        Args:
            model: Model ID (author/slug).
            messages: OpenAI-compatible messages list.
            provider_order: Optional explicit provider order to try.
            allow_fallbacks: When False, do not allow fallback providers.
            timeout_seconds: Per-request timeout override.
            extra_headers: Optional headers to include.
            extra_body: Optional extra body fields to merge.
            retries_enabled: Whether to retry failed requests.
            silent_rate_limit: If True, don't log warnings for rate limits.

        Returns:
            Tuple of (response_json, response_headers).
        """
        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
        }
        if provider_order is not None or allow_fallbacks is not None:
            provider_pref: dict[str, Any] = {}
            if provider_order is not None:
                provider_pref["order"] = provider_order
            if allow_fallbacks is not None:
                provider_pref["allow_fallbacks"] = allow_fallbacks
            body["provider"] = provider_pref
        if extra_body:
            body.update(extra_body)

        headers: dict[str, str] = {}
        if extra_headers:
            headers.update(extra_headers)

        request_kwargs: dict[str, Any] = {"json": body}
        if headers:
            request_kwargs["headers"] = headers
        if timeout_seconds is not None:
            # httpx.Timeout validates values; if invalid, let httpx raise at request time
            request_kwargs["timeout"] = httpx.Timeout(timeout_seconds)

        response = await self._make_request(
            "POST",
            "/chat/completions",
            retries_enabled=retries_enabled,
            silent_rate_limit=silent_rate_limit,
            **request_kwargs,
        )
        try:
            return response.json(), dict(response.headers)
        except (ValueError, TypeError) as e:
            raise APIError(f"Invalid JSON response: {e}") from e

    async def create_chat_completion_stream(  # pylint: disable=too-many-arguments
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
        """Call OpenRouter chat completions endpoint with streaming.

        Args:
            model: Model ID (author/slug).
            messages: OpenAI-compatible messages list.
            provider_order: Optional explicit provider order to try.
            allow_fallbacks: When False, do not allow fallback providers.
            timeout_seconds: Per-request timeout override.
            extra_headers: Optional headers to include.
            extra_body: Optional extra body fields to merge.
            retries_enabled: Whether to retry failed requests.
            silent_rate_limit: If True, don't log warnings for rate limits.

        Returns:
            Tuple of (async_generator, response_headers).
        """
        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": True,
        }
        if provider_order is not None or allow_fallbacks is not None:
            provider_pref: dict[str, Any] = {}
            if provider_order is not None:
                provider_pref["order"] = provider_order
            if allow_fallbacks is not None:
                provider_pref["allow_fallbacks"] = allow_fallbacks
            body["provider"] = provider_pref
        if extra_body:
            body.update(extra_body)

        headers: dict[str, str] = {}
        if extra_headers:
            headers.update(extra_headers)

        request_kwargs: dict[str, Any] = {"json": body}
        if headers:
            request_kwargs["headers"] = headers
        if timeout_seconds is not None:
            request_kwargs["timeout"] = httpx.Timeout(timeout_seconds)

        response = await self._make_request(
            "POST",
            "/chat/completions",
            retries_enabled=retries_enabled,
            silent_rate_limit=silent_rate_limit,
            **request_kwargs,
        )

        return response, dict(response.headers)

    async def get_models(  # pylint: disable=too-many-branches,too-many-locals,too-complex
        self,
    ) -> list[ModelInfo]:
        """Retrieve all available models from OpenRouter API.

        Returns:
            List[ModelInfo]: List of available models

        Raises:
            APIError: If the API request fails
            ValidationError: If response data is invalid
        """
        try:
            # Cache key for models listing
            cache_key = "models:list"
            if self._cache is not None:
                cached = self._cache.get(cache_key)
                if isinstance(cached, list):
                    return cached
            response = await self._make_request("GET", "/models")
            data: dict[str, Any] = response.json()

            # Parse response data
            if "data" in data:
                models_data = data["data"]
            else:
                models_data = data.get("models", [])

            models: list[ModelInfo] = []
            for model_data in models_data:
                try:
                    # Transform API response to match our ModelInfo structure
                    created_raw = (
                        model_data.get("created")
                        or model_data.get("created_at")
                        or model_data.get("released")
                        or datetime.now().isoformat()
                    )

                    # Sanitize pricing: coerce to float, drop negative/invalid
                    raw_pricing = model_data.get("pricing", {}) or {}
                    pricing: dict[str, float] = {}
                    for k, v in raw_pricing.items():
                        f_val = None
                        try:
                            f_val = float(v)
                        except (TypeError, ValueError):
                            f_val = None
                        if f_val is not None and f_val >= 0:
                            pricing[k] = f_val

                    model_info = ModelInfo(
                        id=model_data["id"],
                        name=model_data.get("name", model_data["id"]),
                        description=model_data.get("description"),
                        context_length=model_data.get("context_length")
                        or model_data.get("context_window")
                        or model_data.get("context", 1),
                        pricing=pricing,
                        created=self._parse_datetime(created_raw),
                    )
                    models.append(model_info)
                except (KeyError, ValueError, TypeError) as e:
                    logger.debug(f"Skipping invalid model data: {e}")
                    continue

            logger.debug(f"Retrieved {len(models)} models from OpenRouter API")
            if self._cache is not None:
                self._cache.set(cache_key, models)
            return models

        except PydanticValidationError as e:
            raise ValidationError(f"Invalid response data: {e}") from e
        except Exception as e:
            if isinstance(e, APIError | AuthenticationError | RateLimitError):
                raise
            raise APIError(f"Failed to retrieve models: {e}") from e

    async def get_model_providers(  # pylint: disable=too-many-branches,too-many-locals,too-many-nested-blocks,too-many-statements,too-complex
        self, model_name: str
    ) -> list[ProviderDetails]:
        """Get all providers for a specific model.

        Args:
            model_name: Name or ID of the model to query

        Returns:
            List[ProviderDetails]: List of provider details for the model

        Raises:
            APIError: If the API request fails
            ValidationError: If response data is invalid
        """
        if not model_name or not model_name.strip():
            raise ValueError("Model name cannot be empty")

        try:
            cache_key = f"providers:{model_name}"
            if self._cache is not None:
                cached = self._cache.get(cache_key)
                if isinstance(cached, list):
                    return cached
            # Use correct /endpoints endpoint according to documentation
            # If empty, fall back to providers embedded in /models payload
            response = await self._make_request(
                "GET", f"/models/{model_name}/endpoints"
            )
            data: dict[str, Any] = response.json()
            # Handle different API response structures
            providers_data = []
            if isinstance(data, dict):
                # Check for endpoints in data.data.endpoints
                if (
                    "data" in data
                    and isinstance(data["data"], dict)
                    and "endpoints" in data["data"]
                ):
                    providers_data = data["data"]["endpoints"]
                # Fallback to providers at top level
                elif "providers" in data:
                    providers_data = data["providers"]
                # Fallback to data itself
                elif "data" in data:
                    providers_data = data["data"]
            # If still empty, try to get providers directly from data if it's a list
            elif isinstance(data, list):
                providers_data = data

            if not providers_data:
                models_response = await self._make_request("GET", "/models")
                models_data: dict[str, Any] = models_response.json()
                for model_data in models_data.get(
                    "data", models_data.get("models", [])
                ):
                    if (
                        model_data.get("id") == model_name
                        or model_data.get("name") == model_name
                    ):
                        providers_data = model_data.get("providers", [])
                        break
            # If still empty, propagate empty list (caller can decide)

            providers: list[ProviderDetails] = []
            for provider_data in providers_data:
                try:
                    sp = provider_data.get("supported_parameters")
                    tools_supported = False
                    reasoning_supported = False
                    image_supported = False
                    image_aliases = {
                        "image",
                        "images",
                        "image_input",
                        "input_image",
                        "input_images",
                        "vision",
                        "vision_input",
                        "multimodal",
                        "multimodal_vision",
                    }
                    if isinstance(sp, list):
                        normalized_params = [
                            x.lower() for x in sp if isinstance(x, str)
                        ]
                        tools_supported = "tools" in normalized_params
                        reasoning_supported = any(
                            param.startswith("reasoning") or param == "reasoning"
                            for param in normalized_params
                        )
                        image_supported = any(
                            param in image_aliases
                            or param.startswith("image")
                            or param.startswith("vision")
                            for param in normalized_params
                        )
                    elif isinstance(sp, dict):
                        tools_supported = bool(sp.get("tools", False))
                        reasoning_supported = bool(sp.get("reasoning", False))
                        for key, value in sp.items():
                            if (
                                isinstance(key, str)
                                and key.lower() in image_aliases
                                and bool(value)
                            ):
                                image_supported = True
                                break

                    # Legacy boolean field support
                    if not tools_supported:
                        tools_supported = bool(
                            provider_data.get("supports_tools", False)
                        )
                    if not reasoning_supported:
                        reasoning_supported = bool(
                            provider_data.get("is_reasoning_model", False)
                        )
                    if not image_supported:
                        image_supported = any(
                            bool(provider_data.get(field))
                            for field in [
                                "supports_images",
                                "supports_image_input",
                                "image_input",
                                "vision",
                                "vision_support",
                                "multimodal",
                                "image_support",
                            ]
                        )

                    # Pricing may be numeric strings; coerce to float where possible
                    raw_pricing = provider_data.get("pricing", {}) or {}
                    pricing: dict[str, float] = {}
                    for k, v in raw_pricing.items():
                        f_val = None
                        try:
                            f_val = float(v)
                        except (TypeError, ValueError):
                            f_val = None
                        if f_val is not None:
                            pricing[k] = f_val

                    # Uptime could be a fraction (0..1) or percentage (0..100)
                    uptime_val = provider_data.get("uptime_last_30m")
                    if uptime_val is None:
                        uptime_val = provider_data.get(
                            "uptime_30min"
                        ) or provider_data.get("uptime")
                    if isinstance(uptime_val, int | float) and uptime_val <= 1.5:
                        uptime_pct = float(uptime_val) * 100.0
                    else:
                        try:
                            uptime_pct = float(uptime_val)
                        except (TypeError, ValueError):
                            uptime_pct = 100.0

                    # Normalize status to string label when numeric
                    raw_status = provider_data.get("status")
                    status_str: str | None
                    if isinstance(raw_status, int | float):
                        status_str = (
                            "offline" if int(raw_status) == 0 else str(int(raw_status))
                        )
                    else:
                        status_str = raw_status if isinstance(raw_status, str) else None

                    provider_name = provider_data.get(
                        "provider_name"
                    ) or provider_data.get("provider", "Unknown")

                    # Endpoint name best-effort extraction from legacy payloads
                    endpoint_name = (
                        provider_data.get("endpoint_name")
                        or provider_data.get("name")
                        or None
                    )

                    provider_info = ProviderInfo(
                        provider_name=provider_name,
                        model_id=model_name,
                        status=status_str,
                        endpoint_name=endpoint_name,
                        context_window=provider_data.get("context_length")
                        or provider_data.get("context_window", 0),
                        supports_tools=tools_supported,
                        is_reasoning_model=reasoning_supported,
                        supports_image_input=image_supported,
                        quantization=provider_data.get("quantization"),
                        uptime_30min=uptime_pct,
                        performance_tps=provider_data.get("performance_tps")
                        or provider_data.get("tps"),
                        pricing=pricing,
                        max_completion_tokens=provider_data.get("max_completion_tokens")
                        or provider_data.get("max_output_tokens"),
                        supported_parameters=provider_data.get("supported_parameters"),
                    )

                    last_updated_raw = (
                        provider_data.get("last_updated")
                        or provider_data.get("updated_at")
                        or provider_data.get("refreshed_at")
                        or data.get("updated_at")
                        or datetime.now().isoformat()
                    )

                    provider_details = ProviderDetails(
                        provider=provider_info,
                        availability=(
                            (provider_data.get("status") != "offline")
                            if provider_data.get("status") is not None
                            else provider_data.get("availability", True)
                        ),
                        last_updated=self._parse_datetime(last_updated_raw),
                    )
                    providers.append(provider_details)

                except (KeyError, ValueError, TypeError) as e:
                    logger.debug(
                        f"Skipping invalid provider data for {model_name}: {e}"
                    )
                    continue

            logger.debug(
                f"Retrieved {len(providers)} providers for model '{model_name}'"
            )
            if self._cache is not None:
                self._cache.set(cache_key, providers)
            return providers

        except PydanticValidationError as e:
            raise ValidationError(f"Invalid provider response data: {e}") from e
        except Exception as e:
            if isinstance(e, APIError | AuthenticationError | RateLimitError):
                raise
            raise APIError(
                f"Failed to retrieve providers for model '{model_name}': {e}"
            ) from e

    async def health_check(self) -> bool:
        """Check if the OpenRouter API is accessible.

        Returns:
            bool: True if API is accessible, False otherwise
        """
        try:
            # Perform a simple, non-retrying request for health check to avoid teardown issues in tests
            url = urljoin(self.base_url + "/", "models")
            response = await self.client.get(url, params={"limit": 1})
            return response.is_success
        except Exception as e:
            logger.debug(f"Health check failed: {e}")
            return False
