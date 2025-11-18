"""Unit tests for ModelService basic functionality."""

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from openrouter_inspector.models import (
    ModelInfo,
    ProviderDetails,
    ProviderInfo,
    SearchFilters,
)
from openrouter_inspector.services import ModelService


class TestModelService:
    """Test cases for basic ModelService functionality."""

    @pytest.fixture
    def mock_client(self):
        """Mock OpenRouter client."""
        client = AsyncMock()
        return client

    @pytest.fixture
    def sample_models(self):
        """Sample model data."""
        return [
            ModelInfo(
                id="model1",
                name="Model One",
                description="First model",
                context_length=8192,
                pricing={"prompt": 0.00001, "completion": 0.00002},
                created=datetime.now(),
            ),
            ModelInfo(
                id="model2",
                name="Model Two",
                description="Second model",
                context_length=16384,
                pricing={"prompt": 0.00002, "completion": 0.00003},
                created=datetime.now(),
            ),
            ModelInfo(
                id="model3",
                name="",  # No name - should fall back to id
                description="Third model",
                context_length=32768,
                pricing={"prompt": 0.00003, "completion": 0.00004},
                created=datetime.now(),
            ),
        ]

    @pytest.fixture
    def sample_providers(self):
        """Sample provider data."""
        return [
            ProviderDetails(
                provider=ProviderInfo(
                    provider_name="Provider A",
                    model_id="model1",
                    endpoint_name="Model One A",
                    context_window=8192,
                    supports_tools=True,
                    is_reasoning_model=True,
                    supports_image_input=True,
                    quantization="fp16",
                    uptime_30min=99.5,
                    pricing={"prompt": 0.00001, "completion": 0.00002},
                    max_completion_tokens=4096,
                    supported_parameters=["tools", "reasoning", "image"],
                    status="active",
                    performance_tps=100.0,
                ),
                availability=True,
                last_updated=datetime.now(),
            ),
            ProviderDetails(
                provider=ProviderInfo(
                    provider_name="Provider B",
                    model_id="model1",
                    endpoint_name="Model One B",
                    context_window=16384,
                    supports_tools=False,
                    is_reasoning_model=False,
                    quantization="q4",
                    uptime_30min=98.0,
                    pricing={"prompt": 0.000005, "completion": 0.00001},
                    max_completion_tokens=2048,
                    supported_parameters=[],
                    status="active",
                    performance_tps=50.0,
                ),
                availability=True,
                last_updated=datetime.now(),
            ),
        ]

    @pytest.mark.asyncio
    async def test_list_models_basic(self, mock_client, sample_models):
        """Test basic list_models functionality."""
        mock_client.get_models.return_value = sample_models
        service = ModelService(mock_client)

        result = await service.list_models()

        assert len(result) == 3
        assert result == [
            "Model One",
            "Model Two",
            "model3",
        ]  # model3 has no name, so uses id
        mock_client.get_models.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_models_empty(self, mock_client):
        """Test list_models with empty model list."""
        mock_client.get_models.return_value = []
        service = ModelService(mock_client)

        result = await service.list_models()

        assert result == []
        mock_client.get_models.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_models_basic(self, mock_client, sample_models):
        """Test basic search_models functionality."""
        mock_client.get_models.return_value = sample_models
        service = ModelService(mock_client)

        # Search for "model"
        result = await service.search_models("model")

        assert len(result) == 3
        assert all(
            "model" in (m.id.lower() or "") or "model" in (m.name.lower() or "")
            for m in result
        )

    @pytest.mark.asyncio
    async def test_search_models_case_insensitive(self, mock_client, sample_models):
        """Test search_models is case insensitive."""
        mock_client.get_models.return_value = sample_models
        service = ModelService(mock_client)

        # Search for "MODEL" (uppercase)
        result = await service.search_models("MODEL")

        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_search_models_no_match(self, mock_client, sample_models):
        """Test search_models with no matches."""
        mock_client.get_models.return_value = sample_models
        service = ModelService(mock_client)

        result = await service.search_models("nonexistent")

        assert result == []

    @pytest.mark.asyncio
    async def test_search_models_min_context_filter(self, mock_client, sample_models):
        """Test search_models with min_context filter."""
        mock_client.get_models.return_value = sample_models
        service = ModelService(mock_client)

        # Filter for models with at least 16384 context
        filters = SearchFilters(
            min_context=16384,
            supports_tools=None,
            reasoning_only=None,
            max_price_per_token=None,
        )
        result = await service.search_models("", filters)

        assert len(result) == 2  # model2 (16384) and model3 (32768)
        assert all(m.context_length >= 16384 for m in result)

    @pytest.mark.asyncio
    async def test_search_models_max_price_filter(self, mock_client, sample_models):
        """Test search_models with max_price_per_token filter."""
        mock_client.get_models.return_value = sample_models
        service = ModelService(mock_client)

        # Filter for models with max price <= 0.00002
        filters = SearchFilters(
            min_context=None,
            supports_tools=None,
            reasoning_only=None,
            max_price_per_token=0.00002,
        )
        result = await service.search_models("", filters)

        assert len(result) == 2  # model1 (0.00001) and model2 (0.00002)
        for model in result:
            min_price = min(model.pricing.values()) if model.pricing else float("inf")
            assert min_price <= 0.00002

    @pytest.mark.asyncio
    async def test_search_models_supports_tools_filter(
        self, mock_client, sample_models, sample_providers
    ):
        """Test search_models with supports_tools filter."""
        mock_client.get_models.return_value = sample_models
        mock_client.get_model_providers.return_value = sample_providers
        service = ModelService(mock_client)

        # Filter for models with providers that support tools
        filters = SearchFilters(
            min_context=None,
            supports_tools=True,
            reasoning_only=None,
            max_price_per_token=None,
        )
        await service.search_models("", filters)

        # Should call get_model_providers for each candidate
        assert mock_client.get_model_providers.call_count >= 1
        # model1 should match because it has providers that support tools

    @pytest.mark.asyncio
    async def test_search_models_reasoning_only_filter(
        self, mock_client, sample_models, sample_providers
    ):
        """Test search_models with reasoning_only filter."""
        mock_client.get_models.return_value = sample_models
        mock_client.get_model_providers.return_value = sample_providers
        service = ModelService(mock_client)

        # Filter for models with reasoning capability
        filters = SearchFilters(
            min_context=None,
            supports_tools=None,
            reasoning_only=True,
            supports_image_input=None,
            max_price_per_token=None,
        )
        await service.search_models("", filters)

        # Should call get_model_providers for each candidate
        assert mock_client.get_model_providers.call_count >= 1
        # model1 should match because it has reasoning providers

    @pytest.mark.asyncio
    async def test_search_models_non_reasoning_filter(
        self, mock_client, sample_models, sample_providers
    ):
        """Test search_models with reasoning_only set to False."""
        mock_client.get_models.return_value = sample_models
        reasoning_only_list = [sample_providers[0]]
        mock_client.get_model_providers.side_effect = [
            sample_providers,
            reasoning_only_list,
            reasoning_only_list,
        ]
        service = ModelService(mock_client)

        filters = SearchFilters(
            min_context=None,
            supports_tools=None,
            reasoning_only=False,
            supports_image_input=None,
            max_price_per_token=None,
        )
        results = await service.search_models("", filters)

        assert len(results) == 1
        assert results[0].id == "model1"
        mock_client.get_model_providers.side_effect = None
        mock_client.get_model_providers.return_value = sample_providers

    @pytest.mark.asyncio
    async def test_search_models_supports_image_filter(
        self, mock_client, sample_models, sample_providers
    ):
        """Test search_models with supports_image_input filter."""
        mock_client.get_models.return_value = sample_models
        no_image_list = [sample_providers[1]]
        mock_client.get_model_providers.side_effect = [
            sample_providers,
            no_image_list,
            no_image_list,
        ]
        service = ModelService(mock_client)

        filters = SearchFilters(
            min_context=None,
            supports_tools=None,
            reasoning_only=None,
            supports_image_input=True,
            max_price_per_token=None,
        )
        results = await service.search_models("", filters)

        assert len(results) == 1
        assert results[0].id == "model1"
        mock_client.get_model_providers.side_effect = None
        mock_client.get_model_providers.return_value = sample_providers

    @pytest.mark.asyncio
    async def test_get_model_providers(self, mock_client, sample_providers):
        """Test get_model_providers functionality."""
        mock_client.get_model_providers.return_value = sample_providers
        service = ModelService(mock_client)

        result = await service.get_model_providers("model1")

        assert len(result) == 2
        assert result[0].provider.provider_name == "Provider A"
        assert result[1].provider.provider_name == "Provider B"
        mock_client.get_model_providers.assert_called_once_with("model1")

    def test_normalize_provider_name_basic(self, mock_client):
        """Test basic provider name normalization."""
        service = ModelService(mock_client)

        assert service._normalize_provider_name("OpenAI") == "openai"
        assert service._normalize_provider_name("  Anthropic  ") == "anthropic"
        assert service._normalize_provider_name("") == ""

    def test_normalize_provider_name_with_suffixes(self, mock_client):
        """Test provider name normalization with common suffixes."""
        service = ModelService(mock_client)

        assert service._normalize_provider_name("OpenAI Inc") == "openai"
        assert service._normalize_provider_name("Anthropic AI") == "anthropic"
        assert service._normalize_provider_name("Google LLC") == "google"
        assert service._normalize_provider_name("Microsoft Corporation") == "microsoft"

    def test_normalize_provider_name_multiple_spaces(self, mock_client):
        """Test provider name normalization with multiple spaces."""
        service = ModelService(mock_client)

        assert service._normalize_provider_name("OpenAI    Inc") == "openai"
        assert service._normalize_provider_name("  Deep    Infra  ") == "deep infra"
