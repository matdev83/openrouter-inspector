"""Regression test for offers endpoint URL format."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def test_api_key():
    """Test API key fixture."""
    return "test-api-key"


@pytest.fixture
def sample_offers_response():
    """Sample offers API response."""
    return {
        "providers": [
            {
                "provider_name": "OpenAI",
                "endpoint_name": "openai-gpt-4",
                "context_window": 8192,
                "supports_tools": True,
                "quantization": None,
                "uptime_30min": 99.5,
                "pricing": {"prompt": 0.00003, "completion": 0.00006},
                "max_completion_tokens": 4096,
                "supported_parameters": ["tools"],
                "status": "active",
                "availability": True,
                "last_updated": "2024-01-15T10:30:00Z",
            },
            {
                "provider_name": "Azure OpenAI",
                "endpoint_name": "azure-gpt-4",
                "context_window": 8192,
                "supports_tools": True,
                "quantization": None,
                "uptime_30min": 98.2,
                "pricing": {"prompt": 0.00003, "completion": 0.00006},
                "max_completion_tokens": 4096,
                "supported_parameters": ["tools"],
                "status": "active",
                "availability": True,
                "last_updated": "2024-01-15T10:30:00Z",
            },
        ]
    }


class TestOffersEndpointRegression:
    """Regression test for offers endpoint URL format."""

    @pytest.mark.asyncio
    async def test_offers_url_format_regression(
        self, test_api_key, sample_offers_response
    ):
        """Regression test for offers endpoint URL format.

        This test verifies the URL format used by get_model_providers.
        It ensures the correct URL format is used: /models/{model}/endpoints
        """
        from openrouter_inspector.client import OpenRouterClient
        from openrouter_inspector.services import ModelService

        # Patch the _make_request method to track the actual URL called
        with patch.object(
            OpenRouterClient, "_make_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = MagicMock(
                json=MagicMock(return_value=sample_offers_response)
            )

            async with OpenRouterClient(test_api_key) as client:
                service = ModelService(client)

                # This should trigger the request
                await service.get_model_providers("test-model")

                # Verify the call was made
                assert mock_request.called
                call_args = mock_request.call_args[0]
                method, endpoint = call_args

                # Verify the correct URL format is used
                assert endpoint.endswith("/models/test-model/endpoints"), (
                    f"Expected URL ending with '/models/test-model/endpoints', "
                    f"but got '{endpoint}'. URL format is incorrect."
                )

    @pytest.mark.asyncio
    async def test_client_layer_uses_correct_endpoint_url(
        self, test_api_key, sample_offers_response, httpx_mock
    ):
        """Verify the client layer calls the correct endpoint URL.

        This test confirms that the HTTP client implementation in OpenRouterClient
        makes requests to the expected URL format: `/models/{model}/endpoints`.
        """
        test_model = "anthropic/claude-3-opus"
        expected_url = f"https://openrouter.ai/api/v1/models/{test_model}/endpoints"

        # Mock the HTTP response
        httpx_mock.add_response(
            method="GET",
            url=expected_url,
            json=sample_offers_response,
            status_code=200,
        )

        # Import and test the actual function used by the CLI
        from openrouter_inspector.client import OpenRouterClient
        from openrouter_inspector.services import ModelService

        async with OpenRouterClient(test_api_key) as client:
            service = ModelService(client)
            providers = await service.get_model_providers(test_model)

            # Verify that providers were returned (confirms URL was called correctly)
            assert len(providers) == 2
            assert providers[0].provider.provider_name == "OpenAI"
            assert providers[1].provider.provider_name == "Azure OpenAI"
