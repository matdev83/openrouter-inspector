"""Unit tests for ModelService functionality."""

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from openrouter_inspector.models import (
    ProviderDetails,
    ProviderInfo,
)
from openrouter_inspector.services import ModelService


class TestModelService:
    """Test cases for ModelService functionality."""

    @pytest.fixture
    def mock_client(self):
        """Mock OpenRouter client."""
        client = AsyncMock()
        return client

    @pytest.fixture
    def sample_api_providers(self):
        """Sample API provider data."""
        return [
            ProviderDetails(
                provider=ProviderInfo(
                    provider_name="DeepInfra",
                    model_id="qwen/qwen-2.5-coder-32b-instruct",
                    status="online",
                    endpoint_name="DeepInfra | qwen-2.5-coder-32b-instruct",
                    context_window=32768,
                    supports_tools=True,
                    is_reasoning_model=False,
                    quantization="fp8",
                    uptime_30min=99.2,
                    performance_tps=15.2,
                    pricing={"prompt": 0.06, "completion": 0.15},
                    max_completion_tokens=16384,
                    supported_parameters=["reasoning"],
                ),
                availability=True,
                last_updated=datetime.now(),
            ),
            ProviderDetails(
                provider=ProviderInfo(
                    provider_name="Lambda Labs",
                    model_id="qwen/qwen-2.5-coder-32b-instruct",
                    status="online",
                    endpoint_name="Lambda Labs | qwen-2.5-coder-32b-instruct",
                    context_window=32768,
                    supports_tools=False,
                    is_reasoning_model=False,
                    quantization="bf16",
                    uptime_30min=98.5,
                    performance_tps=12.8,
                    pricing={"prompt": 0.07, "completion": 0.16},
                    max_completion_tokens=None,
                    supported_parameters=[],
                ),
                availability=True,
                last_updated=datetime.now(),
            ),
        ]

    def test_init_without_web_scraper(self, mock_client):
        """Test ModelService initialization without web scraper."""
        service = ModelService(mock_client)
        assert service.client == mock_client

    def test_normalize_provider_name_basic(self, mock_client):
        """Test basic provider name normalization."""
        service = ModelService(mock_client)

        assert service._normalize_provider_name("DeepInfra") == "deepinfra"
        assert service._normalize_provider_name("  Lambda Labs  ") == "lambda labs"
        assert service._normalize_provider_name("") == ""

    def test_normalize_provider_name_with_suffixes(self, mock_client):
        """Test provider name normalization with common suffixes."""
        service = ModelService(mock_client)

        assert service._normalize_provider_name("OpenAI Inc") == "openai"
        assert service._normalize_provider_name("Anthropic AI") == "anthropic"
        assert service._normalize_provider_name("Cohere.ai") == "cohere"
        assert service._normalize_provider_name("Mistral.com") == "mistral"
        assert service._normalize_provider_name("Together AI Corp") == "together"

    def test_normalize_provider_name_multiple_spaces(self, mock_client):
        """Test provider name normalization with multiple spaces."""
        service = ModelService(mock_client)

        assert service._normalize_provider_name("Lambda    Labs") == "lambda labs"
        assert service._normalize_provider_name("  Deep   Infra  ") == "deep infra"
