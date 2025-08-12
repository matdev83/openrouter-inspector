"""Unit tests for handler classes."""

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from openrouter_inspector.handlers import EndpointHandler, ModelHandler, ProviderHandler
from openrouter_inspector.models import (
    ModelInfo,
    ProviderDetails,
    ProviderInfo,
    SearchFilters,
)


class TestModelHandler:
    """Test cases for ModelHandler."""

    @pytest.fixture
    def mock_model_service(self):
        """Create a mock ModelService."""
        return AsyncMock()

    @pytest.fixture
    def model_handler(self, mock_model_service):
        """Create a ModelHandler with mocked dependencies."""
        return ModelHandler(mock_model_service)

    @pytest.fixture
    def sample_models(self):
        """Create sample ModelInfo objects for testing."""
        return [
            ModelInfo(
                id="meta/llama-3",
                name="Meta Llama 3",
                description="Meta's Llama 3 model",
                context_length=8192,
                pricing={"prompt": 0.00001, "completion": 0.00002},
                created=datetime(2024, 1, 1),
            ),
            ModelInfo(
                id="openai/gpt-4",
                name="GPT-4",
                description="OpenAI's GPT-4 model",
                context_length=32768,
                pricing={"prompt": 0.00003, "completion": 0.00006},
                created=datetime(2024, 1, 1),
            ),
        ]

    @pytest.mark.asyncio
    async def test_list_models_basic(
        self, model_handler, mock_model_service, sample_models
    ):
        """Test basic model listing functionality."""
        mock_model_service.search_models.return_value = sample_models
        filters = SearchFilters()

        result = await model_handler.list_models(filters)

        assert result == sample_models
        mock_model_service.search_models.assert_called_once_with("", filters)

    @pytest.mark.asyncio
    async def test_list_models_with_text_filters(
        self, model_handler, mock_model_service, sample_models
    ):
        """Test model listing with text filters."""
        mock_model_service.search_models.return_value = sample_models
        filters = SearchFilters()
        text_filters = ["meta"]

        result = await model_handler.list_models(filters, text_filters)

        # Should only return models matching the text filter
        assert len(result) == 1
        assert result[0].id == "meta/llama-3"

    @pytest.mark.asyncio
    async def test_search_models(
        self, model_handler, mock_model_service, sample_models
    ):
        """Test model searching functionality."""
        mock_model_service.search_models.return_value = sample_models
        filters = SearchFilters()
        query = "test query"

        result = await model_handler.search_models(query, filters)

        assert result == sample_models
        mock_model_service.search_models.assert_called_once_with(query, filters)

    def test_sort_models_by_id(self, model_handler, sample_models):
        """Test sorting models by ID."""
        result = model_handler._sort_models(sample_models, "id")

        # Should be sorted by ID (meta comes before openai)
        assert result[0].id == "meta/llama-3"
        assert result[1].id == "openai/gpt-4"

    def test_sort_models_by_context(self, model_handler, sample_models):
        """Test sorting models by context length."""
        result = model_handler._sort_models(sample_models, "context")

        # Should be sorted by context length (8192 < 32768)
        assert result[0].context_length == 8192
        assert result[1].context_length == 32768


class TestProviderHandler:
    """Test cases for ProviderHandler."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock OpenRouterClient."""
        return AsyncMock()

    @pytest.fixture
    def provider_handler(self, mock_client):
        """Create a ProviderHandler with mocked dependencies."""
        return ProviderHandler(mock_client)

    @pytest.fixture
    def sample_provider_details(self):
        """Create sample ProviderDetails for testing."""
        provider_info = ProviderInfo(
            provider_name="TestProvider",
            model_id="test/model",
            endpoint_name="Test Model",
            context_window=8192,
            supports_tools=True,
            is_reasoning_model=False,
            quantization="fp16",
            uptime_30min=99.5,
            pricing={"prompt": 0.00001, "completion": 0.00002},
            max_completion_tokens=4096,
            supported_parameters=[],
            status="active",
            performance_tps=100.0,
        )
        return [
            ProviderDetails(
                provider=provider_info,
                availability=True,
                last_updated=datetime.now(),
            )
        ]

    @pytest.mark.asyncio
    async def test_get_model_providers(
        self, provider_handler, mock_client, sample_provider_details
    ):
        """Test getting providers for a model."""
        mock_client.get_model_providers.return_value = sample_provider_details
        model_id = "test/model"

        result = await provider_handler.get_model_providers(model_id)

        assert result == sample_provider_details
        mock_client.get_model_providers.assert_called_once_with(model_id)

    def test_count_active_providers(self, provider_handler, sample_provider_details):
        """Test counting active providers."""
        result = provider_handler._count_active_providers(sample_provider_details)

        assert result == 1

    def test_count_active_providers_offline(self, provider_handler):
        """Test counting active providers with offline provider."""
        provider_info = ProviderInfo(
            provider_name="OfflineProvider",
            model_id="test/model",
            endpoint_name="Test Model",
            context_window=8192,
            supports_tools=True,
            is_reasoning_model=False,
            quantization="fp16",
            uptime_30min=99.5,
            pricing={"prompt": 0.00001, "completion": 0.00002},
            max_completion_tokens=4096,
            supported_parameters=[],
            status="offline",
            performance_tps=100.0,
        )
        offline_provider = ProviderDetails(
            provider=provider_info,
            availability=False,
            last_updated=datetime.now(),
        )

        result = provider_handler._count_active_providers([offline_provider])

        assert result == 0


class TestEndpointHandler:
    """Test cases for EndpointHandler."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock OpenRouterClient."""
        return AsyncMock()

    @pytest.fixture
    def mock_model_service(self):
        """Create a mock ModelService."""
        return AsyncMock()

    @pytest.fixture
    def endpoint_handler(self, mock_client, mock_model_service):
        """Create an EndpointHandler with mocked dependencies."""
        return EndpointHandler(mock_client, mock_model_service)

    @pytest.fixture
    def sample_provider_details(self):
        """Create sample ProviderDetails for testing."""
        provider_info = ProviderInfo(
            provider_name="TestProvider",
            model_id="test/model",
            endpoint_name="Test Model",
            context_window=8192,
            supports_tools=True,
            is_reasoning_model=False,
            quantization="fp16",
            uptime_30min=99.5,
            pricing={"prompt": 0.00001, "completion": 0.00002},
            max_completion_tokens=4096,
            supported_parameters=["reasoning", "image"],
            status="active",
            performance_tps=100.0,
        )
        return [
            ProviderDetails(
                provider=provider_info,
                availability=True,
                last_updated=datetime.now(),
            )
        ]

    @pytest.mark.asyncio
    async def test_resolve_and_fetch_endpoints_exact_match(
        self, endpoint_handler, mock_model_service, sample_provider_details
    ):
        """Test resolving endpoints with exact model ID match."""
        mock_model_service.get_model_providers.return_value = sample_provider_details
        model_id = "test/model"

        resolved_id, offers = await endpoint_handler.resolve_and_fetch_endpoints(
            model_id
        )

        assert resolved_id == model_id
        assert offers == sample_provider_details

    def test_filter_endpoints_basic(self, endpoint_handler, sample_provider_details):
        """Test basic endpoint filtering."""
        result = endpoint_handler.filter_endpoints(sample_provider_details)

        assert result == sample_provider_details

    def test_filter_endpoints_with_reasoning_required(
        self, endpoint_handler, sample_provider_details
    ):
        """Test filtering endpoints with reasoning requirement."""
        result = endpoint_handler.filter_endpoints(
            sample_provider_details, reasoning_required=True
        )

        # Should pass since sample provider supports reasoning
        assert result == sample_provider_details

    def test_filter_endpoints_with_reasoning_excluded(
        self, endpoint_handler, sample_provider_details
    ):
        """Test filtering endpoints excluding reasoning."""
        result = endpoint_handler.filter_endpoints(
            sample_provider_details, no_reasoning_required=True
        )

        # Should be empty since sample provider supports reasoning
        assert result == []

    def test_sort_endpoints_by_provider(
        self, endpoint_handler, sample_provider_details
    ):
        """Test sorting endpoints by provider name."""
        result = endpoint_handler.sort_endpoints(sample_provider_details, "provider")

        assert result == sample_provider_details  # Single item, no change

    def test_sort_endpoints_api_order(self, endpoint_handler, sample_provider_details):
        """Test keeping API order (default)."""
        result = endpoint_handler.sort_endpoints(sample_provider_details, "api")

        assert result == sample_provider_details
