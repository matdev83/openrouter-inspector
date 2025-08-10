"""Unit tests for OpenRouter API client."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from openrouter_inspector.client import (
    APIError,
    AuthenticationError,
    OpenRouterClient,
    RateLimitError,
    ValidationError,
)
from openrouter_inspector.exceptions import OpenRouterError


@pytest.fixture
def test_api_key():
    """Test API key fixture."""
    return "test-api-key"


@pytest.fixture
def sample_models_response():
    """Sample models API response."""
    return {
        "data": [
            {
                "id": "openai/gpt-4",
                "name": "GPT-4",
                "description": "OpenAI's GPT-4 model",
                "context_length": 8192,
                "pricing": {"prompt": 0.03, "completion": 0.06},
                "created": "2023-03-14T00:00:00Z",
            },
            {
                "id": "anthropic/claude-3-opus",
                "name": "Claude 3 Opus",
                "description": "Anthropic's Claude 3 Opus model",
                "context_length": 200000,
                "pricing": {"prompt": 0.015, "completion": 0.075},
                "created": "2024-02-29T00:00:00Z",
            },
        ]
    }


@pytest.fixture
def sample_providers_response():
    """Sample providers API response."""
    return {
        "providers": [
            {
                "provider_name": "OpenAI",
                "context_window": 8192,
                "supports_tools": True,
                "is_reasoning_model": False,
                "quantization": None,
                "uptime_30min": 99.5,
                "performance_tps": 50.0,
                "availability": True,
                "last_updated": "2024-01-15T10:30:00Z",
            },
            {
                "provider_name": "Azure OpenAI",
                "context_window": 8192,
                "supports_tools": True,
                "is_reasoning_model": False,
                "quantization": None,
                "uptime_30min": 98.2,
                "performance_tps": 45.0,
                "availability": True,
                "last_updated": "2024-01-15T10:30:00Z",
            },
        ]
    }


class TestOpenRouterClient:
    """Test cases for OpenRouterClient."""

    @pytest.mark.asyncio
    async def test_client_initialization(self, test_api_key):
        """Test client initialization with API key."""
        client = OpenRouterClient(test_api_key)

        assert client.api_key == test_api_key
        assert client.base_url == "https://openrouter.ai/api/v1"
        assert client.max_retries == 3
        assert client.base_delay == 1.0
        assert client.max_delay == 60.0

        # Check headers
        assert "Authorization" in client.client.headers
        assert client.client.headers["Authorization"] == "Bearer test-api-key"
        assert client.client.headers["Content-Type"] == "application/json"
        assert "openrouter-inspector" in client.client.headers["User-Agent"]

        await client.close()

    @pytest.mark.asyncio
    async def test_context_manager(self, test_api_key):
        """Test client as async context manager."""
        async with OpenRouterClient(test_api_key) as client:
            assert client.client is not None

        # Client should be closed after context exit
        # Note: We can't easily test this without accessing private attributes

    @pytest.mark.asyncio
    async def test_get_models_success(
        self, test_api_key, sample_models_response, httpx_mock
    ):
        """Test successful models retrieval."""
        httpx_mock.add_response(
            method="GET",
            url="https://openrouter.ai/api/v1/models",
            json=sample_models_response,
            status_code=200,
        )

        async with OpenRouterClient(test_api_key) as client:
            models = await client.get_models()

        assert len(models) == 2

        # Check first model
        assert models[0].id == "openai/gpt-4"
        assert models[0].name == "GPT-4"
        assert models[0].description == "OpenAI's GPT-4 model"
        assert models[0].context_length == 8192
        assert models[0].pricing == {"prompt": 0.03, "completion": 0.06}

        # Check second model
        assert models[1].id == "anthropic/claude-3-opus"
        assert models[1].name == "Claude 3 Opus"
        assert models[1].context_length == 200000

    @pytest.mark.asyncio
    async def test_get_models_alternative_response_format(
        self, test_api_key, httpx_mock
    ):
        """Test models retrieval with alternative response format."""
        response_data = {
            "models": [
                {
                    "id": "test/model",
                    "name": "Test Model",
                    "context_length": 4096,
                    "pricing": {},
                    "created": "2024-01-01T00:00:00Z",
                }
            ]
        }

        httpx_mock.add_response(
            method="GET",
            url="https://openrouter.ai/api/v1/models",
            json=response_data,
            status_code=200,
        )

        async with OpenRouterClient(test_api_key) as client:
            models = await client.get_models()

        assert len(models) == 1
        assert models[0].id == "test/model"
        assert models[0].name == "Test Model"

    @pytest.mark.asyncio
    async def test_get_models_invalid_data(self, test_api_key, httpx_mock):
        """Test models retrieval with invalid model data."""
        response_data = {
            "data": [
                {
                    "id": "valid/model",
                    "name": "Valid Model",
                    "context_length": 4096,
                    "pricing": {},
                    "created": "2024-01-01T00:00:00Z",
                },
                {
                    # Missing required fields
                    "name": "Invalid Model"
                },
            ]
        }

        httpx_mock.add_response(
            method="GET",
            url="https://openrouter.ai/api/v1/models",
            json=response_data,
            status_code=200,
        )

        async with OpenRouterClient(test_api_key) as client:
            models = await client.get_models()

        # Should only return valid models
        assert len(models) == 1
        assert models[0].id == "valid/model"

    @pytest.mark.asyncio
    async def test_get_model_providers_success(
        self, test_api_key, sample_providers_response, httpx_mock
    ):
        """Test successful provider retrieval."""
        httpx_mock.add_response(
            method="GET",
            url="https://openrouter.ai/api/v1/models/openai/gpt-4/endpoints",
            json=sample_providers_response,
            status_code=200,
        )

        async with OpenRouterClient(test_api_key) as client:
            providers = await client.get_model_providers("openai/gpt-4")

        assert len(providers) == 2

        # Check first provider
        provider1 = providers[0]
        assert provider1.provider.provider_name == "OpenAI"
        assert provider1.provider.model_id == "openai/gpt-4"
        assert provider1.provider.context_window == 8192
        assert provider1.provider.supports_tools is True
        assert provider1.provider.is_reasoning_model is False
        assert provider1.provider.uptime_30min == 99.5
        assert provider1.provider.performance_tps == 50.0
        assert provider1.availability is True

        # Check second provider
        provider2 = providers[1]
        assert provider2.provider.provider_name == "Azure OpenAI"
        assert provider2.provider.uptime_30min == 98.2

    @pytest.mark.asyncio
    async def test_get_model_providers_fallback_to_models_endpoint(
        self, test_api_key, sample_models_response, httpx_mock
    ):
        """Test provider retrieval fallback when specific endpoint fails."""
        # Modify sample response to include provider data
        models_with_providers = {
            "data": [
                {
                    "id": "openai/gpt-4",
                    "name": "GPT-4",
                    "context_length": 8192,
                    "pricing": {},
                    "created": "2024-01-01T00:00:00Z",
                    "providers": [
                        {
                            "provider_name": "OpenAI",
                            "context_window": 8192,
                            "supports_tools": True,
                            "is_reasoning_model": False,
                            "uptime_30min": 99.5,
                            "availability": True,
                            "last_updated": "2024-01-15T10:30:00Z",
                        }
                    ],
                }
            ]
        }

        # First request to specific providers endpoint returns empty
        httpx_mock.add_response(
            method="GET",
            url="https://openrouter.ai/api/v1/models/openai/gpt-4/endpoints",
            json={"providers": []},
            status_code=200,
        )

        # Fallback to models endpoint
        httpx_mock.add_response(
            method="GET",
            url="https://openrouter.ai/api/v1/models",
            json=models_with_providers,
            status_code=200,
        )

        async with OpenRouterClient(test_api_key) as client:
            providers = await client.get_model_providers("openai/gpt-4")

        assert len(providers) == 1
        assert providers[0].provider.provider_name == "OpenAI"

    @pytest.mark.asyncio
    async def test_get_model_providers_model_not_found(self, test_api_key, httpx_mock):
        """Test provider retrieval for non-existent model."""
        httpx_mock.add_response(
            method="GET",
            url="https://openrouter.ai/api/v1/models/nonexistent/model/endpoints",
            json={"providers": []},
            status_code=200,
        )

        httpx_mock.add_response(
            method="GET",
            url="https://openrouter.ai/api/v1/models",
            json={"data": []},
            status_code=200,
        )

        async with OpenRouterClient(test_api_key) as client:
            providers = await client.get_model_providers("nonexistent/model")

        assert len(providers) == 0

    @pytest.mark.asyncio
    async def test_get_model_providers_empty_model_name(self, test_api_key):
        """Test provider retrieval with empty model name."""
        async with OpenRouterClient(test_api_key) as client:
            with pytest.raises(ValueError, match="Model name cannot be empty"):
                await client.get_model_providers("")

            with pytest.raises(ValueError, match="Model name cannot be empty"):
                await client.get_model_providers("   ")

    @pytest.mark.asyncio
    async def test_authentication_error_401(self, test_api_key, httpx_mock):
        """Test handling of 401 authentication error."""
        httpx_mock.add_response(
            method="GET", url="https://openrouter.ai/api/v1/models", status_code=401
        )

        async with OpenRouterClient(test_api_key) as client:
            with pytest.raises(AuthenticationError) as exc_info:
                await client.get_models()

            assert exc_info.value.status_code == 401
            assert "Invalid API key" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_authentication_error_403(self, test_api_key, httpx_mock):
        """Test handling of 403 forbidden error."""
        httpx_mock.add_response(
            method="GET", url="https://openrouter.ai/api/v1/models", status_code=403
        )

        async with OpenRouterClient(test_api_key) as client:
            with pytest.raises(AuthenticationError) as exc_info:
                await client.get_models()

            assert exc_info.value.status_code == 403
            assert "Access forbidden" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_rate_limit_error_with_retry(self, test_api_key, httpx_mock):
        """Test handling of rate limit error with retry logic."""
        # First request returns 429
        httpx_mock.add_response(
            method="GET", url="https://openrouter.ai/api/v1/models", status_code=429
        )

        # Second request succeeds
        httpx_mock.add_response(
            method="GET",
            url="https://openrouter.ai/api/v1/models",
            json={"data": []},
            status_code=200,
        )

        async with OpenRouterClient(test_api_key) as client:
            # Mock sleep to speed up test
            with patch("asyncio.sleep", new_callable=AsyncMock):
                models = await client.get_models()

            assert models == []

    @pytest.mark.asyncio
    async def test_rate_limit_error_max_retries(self, test_api_key, httpx_mock):
        """Test rate limit error after max retries."""
        # All requests return 429
        for _ in range(4):  # max_retries + 1
            httpx_mock.add_response(
                method="GET", url="https://openrouter.ai/api/v1/models", status_code=429
            )

        async with OpenRouterClient(test_api_key) as client:
            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(RateLimitError) as exc_info:
                    await client.get_models()

                assert exc_info.value.status_code == 429
                assert "Rate limit exceeded" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_server_error_with_retry(self, test_api_key, httpx_mock):
        """Test handling of server error with retry logic."""
        # First request returns 500
        httpx_mock.add_response(
            method="GET", url="https://openrouter.ai/api/v1/models", status_code=500
        )

        # Second request succeeds
        httpx_mock.add_response(
            method="GET",
            url="https://openrouter.ai/api/v1/models",
            json={"data": []},
            status_code=200,
        )

        async with OpenRouterClient(test_api_key) as client:
            with patch("asyncio.sleep", new_callable=AsyncMock):
                models = await client.get_models()

            assert models == []

    @pytest.mark.asyncio
    async def test_server_error_max_retries(self, test_api_key, httpx_mock):
        """Test server error after max retries."""
        # All requests return 500
        for _ in range(4):  # max_retries + 1
            httpx_mock.add_response(
                method="GET", url="https://openrouter.ai/api/v1/models", status_code=500
            )

        async with OpenRouterClient(test_api_key) as client:
            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(APIError) as exc_info:
                    await client.get_models()

                assert exc_info.value.status_code == 500
                assert "Server error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_client_error_4xx(self, test_api_key, httpx_mock):
        """Test handling of 4xx client errors."""
        error_response = {"error": {"message": "Bad request: invalid parameters"}}

        httpx_mock.add_response(
            method="GET",
            url="https://openrouter.ai/api/v1/models",
            json=error_response,
            status_code=400,
        )

        async with OpenRouterClient(test_api_key) as client:
            with pytest.raises(APIError) as exc_info:
                await client.get_models()

            assert exc_info.value.status_code == 400
            assert "Bad request: invalid parameters" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_timeout_error_with_retry(self, test_api_key, httpx_mock):
        """Test handling of timeout error with retry logic."""
        # First request times out
        httpx_mock.add_exception(httpx.TimeoutException("Request timeout"))

        # Second request succeeds
        httpx_mock.add_response(
            method="GET",
            url="https://openrouter.ai/api/v1/models",
            json={"data": []},
            status_code=200,
        )

        async with OpenRouterClient(test_api_key) as client:
            with patch("asyncio.sleep", new_callable=AsyncMock):
                models = await client.get_models()

            assert models == []

    @pytest.mark.asyncio
    async def test_timeout_error_max_retries(self, test_api_key, httpx_mock):
        """Test timeout error after max retries."""
        # All requests time out
        for _ in range(4):  # max_retries + 1
            httpx_mock.add_exception(httpx.TimeoutException("Request timeout"))

        async with OpenRouterClient(test_api_key) as client:
            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(APIError) as exc_info:
                    await client.get_models()

                assert "Request timeout" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_connection_error_with_retry(self, test_api_key, httpx_mock):
        """Test handling of connection error with retry logic."""
        # First request has connection error
        httpx_mock.add_exception(httpx.ConnectError("Connection failed"))

        # Second request succeeds
        httpx_mock.add_response(
            method="GET",
            url="https://openrouter.ai/api/v1/models",
            json={"data": []},
            status_code=200,
        )

        async with OpenRouterClient(test_api_key) as client:
            with patch("asyncio.sleep", new_callable=AsyncMock):
                models = await client.get_models()

            assert models == []

    @pytest.mark.asyncio
    async def test_connection_error_max_retries(self, test_api_key, httpx_mock):
        """Test connection error after max retries."""
        # All requests have connection errors
        for _ in range(4):  # max_retries + 1
            httpx_mock.add_exception(httpx.ConnectError("Connection failed"))

        async with OpenRouterClient(test_api_key) as client:
            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(APIError) as exc_info:
                    await client.get_models()

                assert "Connection error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_health_check_success(self, test_api_key, httpx_mock):
        """Test successful health check."""
        httpx_mock.add_response(
            method="GET",
            url="https://openrouter.ai/api/v1/models?limit=1",
            json={"data": []},
            status_code=200,
        )

        async with OpenRouterClient(test_api_key) as client:
            result = await client.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, test_api_key, httpx_mock):
        """Test failed health check."""
        httpx_mock.add_response(
            method="GET",
            url="https://openrouter.ai/api/v1/models?limit=1",
            status_code=500,
        )

        async with OpenRouterClient(test_api_key) as client:
            result = await client.health_check()

        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_exception(self, test_api_key, httpx_mock):
        """Test health check with exception."""
        httpx_mock.add_exception(httpx.ConnectError("Connection failed"))

        async with OpenRouterClient(test_api_key) as client:
            result = await client.health_check()

        assert result is False

    @pytest.mark.asyncio
    async def test_exponential_backoff_delay_calculation(self, test_api_key):
        """Test exponential backoff delay calculation."""
        client = OpenRouterClient(test_api_key)

        # Test delay calculation
        assert client.base_delay == 1.0
        assert client.max_delay == 60.0

        # Simulate delay calculations
        delays = []
        for attempt in range(4):
            delay = min(client.base_delay * (2**attempt), client.max_delay)
            delays.append(delay)

        assert delays == [1.0, 2.0, 4.0, 8.0]

        await client.close()

    @pytest.mark.asyncio
    async def test_url_construction(self, test_api_key):
        """Test URL construction for different endpoints."""
        client = OpenRouterClient(test_api_key)

        # Test base URL normalization
        assert client.base_url == "https://openrouter.ai/api/v1"

        await client.close()

    @pytest.mark.asyncio
    async def test_custom_base_url(self):
        """Test client with custom base URL."""
        client = OpenRouterClient(
            api_key="test-key",
            base_url="https://custom.api.com/v2/",  # With trailing slash
        )
        assert client.base_url == "https://custom.api.com/v2"

        await client.close()


class TestExceptionHierarchy:
    """Test exception hierarchy and error handling."""

    def test_exception_inheritance(self):
        """Test that exceptions inherit correctly."""
        assert issubclass(APIError, OpenRouterError)
        assert issubclass(AuthenticationError, APIError)
        assert issubclass(RateLimitError, APIError)
        assert issubclass(ValidationError, OpenRouterError)

    def test_api_error_with_status_code(self):
        """Test APIError with status code."""
        error = APIError("Test error", status_code=400)
        assert str(error) == "Test error"
        assert error.status_code == 400

    def test_api_error_without_status_code(self):
        """Test APIError without status code."""
        error = APIError("Test error")
        assert str(error) == "Test error"
        assert error.status_code is None

    def test_authentication_error(self):
        """Test AuthenticationError."""
        error = AuthenticationError("Auth failed", status_code=401)
        assert str(error) == "Auth failed"
        assert error.status_code == 401
        assert isinstance(error, APIError)

    def test_rate_limit_error(self):
        """Test RateLimitError."""
        error = RateLimitError("Rate limited", status_code=429)
        assert str(error) == "Rate limited"
        assert error.status_code == 429
        assert isinstance(error, APIError)

    def test_validation_error(self):
        """Test ValidationError."""
        error = ValidationError("Validation failed")
        assert str(error) == "Validation failed"
        assert isinstance(error, OpenRouterError)
