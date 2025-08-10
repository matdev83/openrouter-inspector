"""Unit tests for data models."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from openrouter_inspector.models import (
    EnhancedProviderDetails,
    ModelInfo,
    ModelsResponse,
    ProviderDetails,
    ProviderInfo,
    ProvidersResponse,
    SearchFilters,
    WebProviderData,
    WebScrapedData,
)


class TestModelInfo:
    """Tests for ModelInfo model."""

    def test_valid_model_info(self):
        """Test creating a valid ModelInfo instance."""
        model_data = {
            "id": "test-model-1",
            "name": "Test Model",
            "description": "A test model",
            "context_length": 4096,
            "pricing": {"input": 0.001, "output": 0.002},
            "created": datetime.now(),
        }

        model = ModelInfo(**model_data)
        assert model.id == "test-model-1"
        assert model.name == "Test Model"
        assert model.context_length == 4096
        assert model.pricing["input"] == 0.001

    def test_model_info_without_optional_fields(self):
        """Test ModelInfo with only required fields."""
        model_data = {
            "id": "test-model-2",
            "name": "Minimal Model",
            "context_length": 2048,
            "created": datetime.now(),
        }

        model = ModelInfo(**model_data)
        assert model.description is None
        assert model.pricing == {}

    def test_invalid_context_length(self):
        """Test validation error for invalid context length."""
        model_data = {
            "id": "test-model-3",
            "name": "Invalid Model",
            "context_length": 0,  # Invalid: must be > 0
            "created": datetime.now(),
        }

        with pytest.raises(ValidationError) as exc_info:
            ModelInfo(**model_data)

        assert "Input should be greater than 0" in str(exc_info.value)

    def test_negative_pricing_validation(self):
        """Test validation error for negative pricing."""
        model_data = {
            "id": "test-model-4",
            "name": "Negative Price Model",
            "context_length": 4096,
            "pricing": {"input": -0.001},  # Invalid: negative price
            "created": datetime.now(),
        }

        with pytest.raises(ValidationError) as exc_info:
            ModelInfo(**model_data)

        assert "must be non-negative" in str(exc_info.value)


class TestProviderInfo:
    """Tests for ProviderInfo model."""

    def test_valid_provider_info(self):
        """Test creating a valid ProviderInfo instance."""
        provider_data = {
            "provider_name": "TestProvider",
            "model_id": "test-model-1",
            "context_window": 4096,
            "supports_tools": True,
            "is_reasoning_model": False,
            "quantization": "int8",
            "uptime_30min": 99.5,
            "performance_tps": 150.0,
        }

        provider = ProviderInfo(**provider_data)
        assert provider.provider_name == "TestProvider"
        assert provider.supports_tools is True
        assert provider.uptime_30min == 99.5

    def test_provider_info_with_defaults(self):
        """Test ProviderInfo with default values."""
        provider_data = {
            "provider_name": "MinimalProvider",
            "model_id": "test-model-2",
            "context_window": 2048,
            "uptime_30min": 95.0,
        }

        provider = ProviderInfo(**provider_data)
        assert provider.supports_tools is False  # Default
        assert provider.is_reasoning_model is False  # Default
        assert provider.quantization is None  # Default
        assert provider.performance_tps is None  # Default

    def test_invalid_uptime_range(self):
        """Test validation error for uptime outside valid range."""
        provider_data = {
            "provider_name": "InvalidProvider",
            "model_id": "test-model-3",
            "context_window": 4096,
            "uptime_30min": 150.0,  # Invalid: > 100
        }

        with pytest.raises(ValidationError) as exc_info:
            ProviderInfo(**provider_data)

        assert "Input should be less than or equal to 100" in str(exc_info.value)

    def test_negative_performance_tps(self):
        """Test validation error for negative performance TPS."""
        provider_data = {
            "provider_name": "NegativeProvider",
            "model_id": "test-model-4",
            "context_window": 4096,
            "uptime_30min": 99.0,
            "performance_tps": -10.0,  # Invalid: negative
        }

        with pytest.raises(ValidationError) as exc_info:
            ProviderInfo(**provider_data)

        assert "Input should be greater than or equal to 0" in str(exc_info.value)


class TestProviderDetails:
    """Tests for ProviderDetails model."""

    def test_valid_provider_details(self):
        """Test creating a valid ProviderDetails instance."""
        provider_info = ProviderInfo(
            provider_name="TestProvider",
            model_id="test-model-1",
            context_window=4096,
            uptime_30min=99.5,
        )

        details_data = {
            "provider": provider_info,
            "availability": True,
            "last_updated": datetime.now(),
        }

        details = ProviderDetails(**details_data)
        assert details.provider.provider_name == "TestProvider"
        assert details.availability is True

    def test_provider_details_with_defaults(self):
        """Test ProviderDetails with default availability."""
        provider_info = ProviderInfo(
            provider_name="DefaultProvider",
            model_id="test-model-2",
            context_window=2048,
            uptime_30min=95.0,
        )

        details_data = {
            "provider": provider_info,
            "last_updated": datetime.now(),
        }

        details = ProviderDetails(**details_data)
        assert details.availability is True  # Default


class TestSearchFilters:
    """Tests for SearchFilters model."""

    def test_valid_search_filters(self):
        """Test creating valid SearchFilters."""
        filters_data = {
            "min_context": 4096,
            "supports_tools": True,
            "reasoning_only": False,
            "max_price_per_token": 0.01,
        }

        filters = SearchFilters(**filters_data)
        assert filters.min_context == 4096
        assert filters.supports_tools is True
        assert filters.max_price_per_token == 0.01

    def test_empty_search_filters(self):
        """Test SearchFilters with no filters set."""
        filters = SearchFilters()
        assert filters.min_context is None
        assert filters.supports_tools is None
        assert filters.reasoning_only is None
        assert filters.max_price_per_token is None

    def test_invalid_min_context_too_large(self):
        """Test validation error for excessively large min_context."""
        filters_data = {
            "min_context": 2000000,  # Invalid: > 1M
        }

        with pytest.raises(ValidationError) as exc_info:
            SearchFilters(**filters_data)

        assert "cannot exceed 1,000,000 tokens" in str(exc_info.value)

    def test_invalid_min_context_zero(self):
        """Test validation error for zero min_context."""
        filters_data = {
            "min_context": 0,  # Invalid: must be > 0
        }

        with pytest.raises(ValidationError) as exc_info:
            SearchFilters(**filters_data)

        assert "Input should be greater than 0" in str(exc_info.value)

    def test_invalid_max_price_negative(self):
        """Test validation error for negative max_price_per_token."""
        filters_data = {
            "max_price_per_token": -0.01,  # Invalid: must be > 0
        }

        with pytest.raises(ValidationError) as exc_info:
            SearchFilters(**filters_data)

        assert "Input should be greater than 0" in str(exc_info.value)


class TestModelsResponse:
    """Tests for ModelsResponse model."""

    def test_valid_models_response(self):
        """Test creating a valid ModelsResponse."""
        model1 = ModelInfo(
            id="model-1",
            name="Model 1",
            context_length=4096,
            created=datetime.now(),
        )
        model2 = ModelInfo(
            id="model-2",
            name="Model 2",
            context_length=8192,
            created=datetime.now(),
        )

        response_data = {
            "models": [model1, model2],
            "total_count": 2,
        }

        response = ModelsResponse(**response_data)
        assert len(response.models) == 2
        assert response.total_count == 2

    def test_empty_models_response(self):
        """Test ModelsResponse with no models."""
        response_data = {
            "models": [],
            "total_count": 0,
        }

        response = ModelsResponse(**response_data)
        assert len(response.models) == 0
        assert response.total_count == 0

    def test_mismatched_total_count(self):
        """Test validation error when total_count doesn't match models list."""
        model1 = ModelInfo(
            id="model-1",
            name="Model 1",
            context_length=4096,
            created=datetime.now(),
        )

        response_data = {
            "models": [model1],
            "total_count": 5,  # Invalid: doesn't match list length
        }

        with pytest.raises(ValidationError) as exc_info:
            ModelsResponse(**response_data)

        assert "must match the number of models" in str(exc_info.value)


class TestProvidersResponse:
    """Tests for ProvidersResponse model."""

    def test_valid_providers_response(self):
        """Test creating a valid ProvidersResponse."""
        provider_info = ProviderInfo(
            provider_name="TestProvider",
            model_id="test-model-1",
            context_window=4096,
            uptime_30min=99.5,
        )

        provider_details = ProviderDetails(
            provider=provider_info,
            last_updated=datetime.now(),
        )

        response_data = {
            "model_name": "test-model-1",
            "providers": [provider_details],
            "last_updated": datetime.now(),
        }

        response = ProvidersResponse(**response_data)
        assert response.model_name == "test-model-1"
        assert len(response.providers) == 1

    def test_empty_providers_response(self):
        """Test ProvidersResponse with no providers."""
        response_data = {
            "model_name": "unavailable-model",
            "providers": [],
            "last_updated": datetime.now(),
        }

        response = ProvidersResponse(**response_data)
        assert response.model_name == "unavailable-model"
        assert len(response.providers) == 0


class TestModelSerialization:
    """Tests for model serialization and deserialization."""

    def test_model_info_json_serialization(self):
        """Test ModelInfo JSON serialization."""
        model = ModelInfo(
            id="test-model",
            name="Test Model",
            context_length=4096,
            pricing={"input": 0.001},
            created=datetime(2024, 1, 1, 12, 0, 0),
        )

        json_data = model.model_dump()
        assert json_data["id"] == "test-model"
        assert json_data["name"] == "Test Model"
        assert json_data["pricing"]["input"] == 0.001

    def test_model_info_json_deserialization(self):
        """Test ModelInfo JSON deserialization."""
        json_data = {
            "id": "test-model",
            "name": "Test Model",
            "context_length": 4096,
            "pricing": {"input": 0.001},
            "created": "2024-01-01T12:00:00",
        }

        model = ModelInfo(**json_data)
        assert model.id == "test-model"
        assert model.name == "Test Model"
        assert model.pricing["input"] == 0.001

    def test_search_filters_partial_serialization(self):
        """Test SearchFilters with partial data serialization."""
        filters = SearchFilters(min_context=4096, supports_tools=True)

        json_data = filters.model_dump(exclude_none=True)
        assert json_data == {"min_context": 4096, "supports_tools": True}
        assert "reasoning_only" not in json_data
        assert "max_price_per_token" not in json_data


class TestWebProviderData:
    """Tests for WebProviderData model."""

    def test_valid_web_provider_data(self):
        """Test creating a valid WebProviderData instance."""
        web_data = {
            "provider_name": "TestProvider",
            "throughput_tps": 15.2,
            "latency_seconds": 0.85,
            "uptime_percentage": 99.5,
        }

        provider = WebProviderData(**web_data)
        assert provider.provider_name == "TestProvider"
        assert provider.throughput_tps == 15.2
        assert provider.latency_seconds == 0.85
        assert provider.uptime_percentage == 99.5
        assert isinstance(provider.last_scraped, datetime)

    def test_web_provider_data_with_optional_fields_none(self):
        """Test WebProviderData with optional fields as None."""
        web_data = {
            "provider_name": "MinimalProvider",
            "throughput_tps": None,
            "latency_seconds": None,
            "uptime_percentage": None,
        }

        provider = WebProviderData(**web_data)
        assert provider.provider_name == "MinimalProvider"
        assert provider.throughput_tps is None
        assert provider.latency_seconds is None
        assert provider.uptime_percentage is None

    def test_web_provider_data_minimal_required_only(self):
        """Test WebProviderData with only required fields."""
        web_data = {
            "provider_name": "RequiredOnlyProvider",
        }

        provider = WebProviderData(**web_data)
        assert provider.provider_name == "RequiredOnlyProvider"
        assert provider.throughput_tps is None
        assert provider.latency_seconds is None
        assert provider.uptime_percentage is None

    def test_invalid_throughput_negative(self):
        """Test validation error for negative throughput."""
        web_data = {
            "provider_name": "InvalidProvider",
            "throughput_tps": -5.0,  # Invalid: negative
        }

        with pytest.raises(ValidationError) as exc_info:
            WebProviderData(**web_data)

        assert "Input should be greater than or equal to 0" in str(exc_info.value)

    def test_invalid_throughput_too_high(self):
        """Test validation error for excessively high throughput."""
        web_data = {
            "provider_name": "InvalidProvider",
            "throughput_tps": 15000.0,  # Invalid: > 10k
        }

        with pytest.raises(ValidationError) as exc_info:
            WebProviderData(**web_data)

        assert "cannot exceed 10,000 TPS" in str(exc_info.value)

    def test_invalid_latency_negative(self):
        """Test validation error for negative latency."""
        web_data = {
            "provider_name": "InvalidProvider",
            "latency_seconds": -1.0,  # Invalid: negative
        }

        with pytest.raises(ValidationError) as exc_info:
            WebProviderData(**web_data)

        assert "Input should be greater than or equal to 0" in str(exc_info.value)

    def test_invalid_latency_too_high(self):
        """Test validation error for excessively high latency."""
        web_data = {
            "provider_name": "InvalidProvider",
            "latency_seconds": 400.0,  # Invalid: > 300
        }

        with pytest.raises(ValidationError) as exc_info:
            WebProviderData(**web_data)

        assert "cannot exceed 300 seconds" in str(exc_info.value)

    def test_invalid_uptime_negative(self):
        """Test validation error for negative uptime."""
        web_data = {
            "provider_name": "InvalidProvider",
            "uptime_percentage": -5.0,  # Invalid: negative
        }

        with pytest.raises(ValidationError) as exc_info:
            WebProviderData(**web_data)

        assert "Input should be greater than or equal to 0" in str(exc_info.value)

    def test_invalid_uptime_over_100(self):
        """Test validation error for uptime over 100%."""
        web_data = {
            "provider_name": "InvalidProvider",
            "uptime_percentage": 105.0,  # Invalid: > 100
        }

        with pytest.raises(ValidationError) as exc_info:
            WebProviderData(**web_data)

        assert "Input should be less than or equal to 100" in str(exc_info.value)

    def test_web_provider_data_edge_values(self):
        """Test WebProviderData with edge case values."""
        web_data = {
            "provider_name": "EdgeProvider",
            "throughput_tps": 0.0,  # Valid: exactly 0
            "latency_seconds": 300.0,  # Valid: exactly at limit
            "uptime_percentage": 100.0,  # Valid: exactly 100%
        }

        provider = WebProviderData(**web_data)
        assert provider.throughput_tps == 0.0
        assert provider.latency_seconds == 300.0
        assert provider.uptime_percentage == 100.0


class TestWebScrapedData:
    """Tests for WebScrapedData model."""

    def test_valid_web_scraped_data(self):
        """Test creating a valid WebScrapedData instance."""
        provider1 = WebProviderData(
            provider_name="Provider1",
            throughput_tps=15.2,
            latency_seconds=0.85,
            uptime_percentage=99.5,
        )
        provider2 = WebProviderData(
            provider_name="Provider2",
            throughput_tps=12.8,
            latency_seconds=1.20,
            uptime_percentage=98.9,
        )

        scraped_data = {
            "model_id": "test/model",
            "providers": [provider1, provider2],
            "source_url": "https://openrouter.ai/test/model",
        }

        data = WebScrapedData(**scraped_data)
        assert data.model_id == "test/model"
        assert len(data.providers) == 2
        assert data.source_url == "https://openrouter.ai/test/model"
        assert isinstance(data.scraped_at, datetime)

    def test_web_scraped_data_empty_providers(self):
        """Test WebScrapedData with empty providers list."""
        scraped_data = {
            "model_id": "empty/model",
            "providers": [],
            "source_url": "https://openrouter.ai/empty/model",
        }

        data = WebScrapedData(**scraped_data)
        assert data.model_id == "empty/model"
        assert len(data.providers) == 0
        assert data.source_url == "https://openrouter.ai/empty/model"

    def test_invalid_source_url_no_protocol(self):
        """Test validation error for source URL without protocol."""
        scraped_data = {
            "model_id": "test/model",
            "providers": [],
            "source_url": "openrouter.ai/test/model",  # Invalid: no protocol
        }

        with pytest.raises(ValidationError) as exc_info:
            WebScrapedData(**scraped_data)

        assert "must be a valid HTTP/HTTPS URL" in str(exc_info.value)

    def test_invalid_source_url_wrong_protocol(self):
        """Test validation error for source URL with wrong protocol."""
        scraped_data = {
            "model_id": "test/model",
            "providers": [],
            "source_url": "ftp://openrouter.ai/test/model",  # Invalid: wrong protocol
        }

        with pytest.raises(ValidationError) as exc_info:
            WebScrapedData(**scraped_data)

        assert "must be a valid HTTP/HTTPS URL" in str(exc_info.value)

    def test_valid_source_url_http(self):
        """Test WebScrapedData with HTTP source URL."""
        scraped_data = {
            "model_id": "test/model",
            "providers": [],
            "source_url": "http://openrouter.ai/test/model",  # Valid: HTTP
        }

        data = WebScrapedData(**scraped_data)
        assert data.source_url == "http://openrouter.ai/test/model"

    def test_valid_source_url_https(self):
        """Test WebScrapedData with HTTPS source URL."""
        scraped_data = {
            "model_id": "test/model",
            "providers": [],
            "source_url": "https://openrouter.ai/test/model",  # Valid: HTTPS
        }

        data = WebScrapedData(**scraped_data)
        assert data.source_url == "https://openrouter.ai/test/model"


class TestEnhancedProviderDetails:
    """Tests for EnhancedProviderDetails model."""

    def test_valid_enhanced_provider_details_with_web_data(self):
        """Test creating EnhancedProviderDetails with web data."""
        provider_info = ProviderInfo(
            provider_name="TestProvider",
            model_id="test-model-1",
            context_window=4096,
            uptime_30min=99.5,
        )

        web_data = WebProviderData(
            provider_name="TestProvider",
            throughput_tps=15.2,
            latency_seconds=0.85,
            uptime_percentage=99.5,
        )

        enhanced_data = {
            "provider": provider_info,
            "availability": True,
            "last_updated": datetime.now(),
            "web_data": web_data,
        }

        enhanced = EnhancedProviderDetails(**enhanced_data)
        assert enhanced.provider.provider_name == "TestProvider"
        assert enhanced.availability is True
        assert enhanced.web_data is not None
        assert enhanced.web_data.throughput_tps == 15.2

    def test_valid_enhanced_provider_details_without_web_data(self):
        """Test creating EnhancedProviderDetails without web data."""
        provider_info = ProviderInfo(
            provider_name="TestProvider",
            model_id="test-model-1",
            context_window=4096,
            uptime_30min=99.5,
        )

        enhanced_data = {
            "provider": provider_info,
            "availability": True,
            "last_updated": datetime.now(),
            "web_data": None,
        }

        enhanced = EnhancedProviderDetails(**enhanced_data)
        assert enhanced.provider.provider_name == "TestProvider"
        assert enhanced.availability is True
        assert enhanced.web_data is None

    def test_enhanced_provider_details_with_defaults(self):
        """Test EnhancedProviderDetails with default values."""
        provider_info = ProviderInfo(
            provider_name="DefaultProvider",
            model_id="test-model-2",
            context_window=2048,
            uptime_30min=95.0,
        )

        enhanced_data = {
            "provider": provider_info,
            "last_updated": datetime.now(),
        }

        enhanced = EnhancedProviderDetails(**enhanced_data)
        assert enhanced.availability is True  # Default
        assert enhanced.web_data is None  # Default

    def test_enhanced_provider_details_matching_provider_names(self):
        """Test EnhancedProviderDetails with matching provider names."""
        provider_info = ProviderInfo(
            provider_name="MatchingProvider",
            model_id="test-model-1",
            context_window=4096,
            uptime_30min=99.5,
        )

        web_data = WebProviderData(
            provider_name="MatchingProvider",  # Same name
            throughput_tps=15.2,
        )

        enhanced_data = {
            "provider": provider_info,
            "last_updated": datetime.now(),
            "web_data": web_data,
        }

        enhanced = EnhancedProviderDetails(**enhanced_data)
        assert enhanced.provider.provider_name == "MatchingProvider"
        assert enhanced.web_data.provider_name == "MatchingProvider"

    def test_enhanced_provider_details_allows_mismatched_names(self):
        """Test that EnhancedProviderDetails allows mismatched provider names for fuzzy matching."""
        provider_info = ProviderInfo(
            provider_name="ProviderA",
            model_id="test-model-1",
            context_window=4096,
            uptime_30min=99.5,
        )

        web_data = WebProviderData(
            provider_name="ProviderB",  # Different name - should be allowed for fuzzy matching
            throughput_tps=15.2,
        )

        enhanced_data = {
            "provider": provider_info,
            "last_updated": datetime.now(),
            "web_data": web_data,
        }

        # This should not raise an error - fuzzy matching is handled at the service layer
        enhanced_provider = EnhancedProviderDetails(**enhanced_data)
        assert enhanced_provider.provider.provider_name == "ProviderA"
        assert enhanced_provider.web_data.provider_name == "ProviderB"


class TestWebScrapingModelsSerialization:
    """Tests for web scraping models serialization and deserialization."""

    def test_web_provider_data_json_serialization(self):
        """Test WebProviderData JSON serialization."""
        web_data = WebProviderData(
            provider_name="TestProvider",
            throughput_tps=15.2,
            latency_seconds=0.85,
            uptime_percentage=99.5,
            last_scraped=datetime(2024, 1, 1, 12, 0, 0),
        )

        json_data = web_data.model_dump()
        assert json_data["provider_name"] == "TestProvider"
        assert json_data["throughput_tps"] == 15.2
        assert json_data["latency_seconds"] == 0.85
        assert json_data["uptime_percentage"] == 99.5

    def test_web_scraped_data_json_serialization(self):
        """Test WebScrapedData JSON serialization."""
        provider = WebProviderData(
            provider_name="TestProvider",
            throughput_tps=15.2,
        )

        scraped_data = WebScrapedData(
            model_id="test/model",
            providers=[provider],
            source_url="https://openrouter.ai/test/model",
            scraped_at=datetime(2024, 1, 1, 12, 0, 0),
        )

        json_data = scraped_data.model_dump()
        assert json_data["model_id"] == "test/model"
        assert len(json_data["providers"]) == 1
        assert json_data["source_url"] == "https://openrouter.ai/test/model"

    def test_enhanced_provider_details_json_serialization(self):
        """Test EnhancedProviderDetails JSON serialization."""
        provider_info = ProviderInfo(
            provider_name="TestProvider",
            model_id="test-model-1",
            context_window=4096,
            uptime_30min=99.5,
        )

        web_data = WebProviderData(
            provider_name="TestProvider",
            throughput_tps=15.2,
        )

        enhanced = EnhancedProviderDetails(
            provider=provider_info,
            availability=True,
            last_updated=datetime(2024, 1, 1, 12, 0, 0),
            web_data=web_data,
        )

        json_data = enhanced.model_dump()
        assert json_data["provider"]["provider_name"] == "TestProvider"
        assert json_data["availability"] is True
        assert json_data["web_data"]["throughput_tps"] == 15.2

    def test_enhanced_provider_details_json_serialization_no_web_data(self):
        """Test EnhancedProviderDetails JSON serialization without web data."""
        provider_info = ProviderInfo(
            provider_name="TestProvider",
            model_id="test-model-1",
            context_window=4096,
            uptime_30min=99.5,
        )

        enhanced = EnhancedProviderDetails(
            provider=provider_info,
            availability=True,
            last_updated=datetime(2024, 1, 1, 12, 0, 0),
            web_data=None,
        )

        json_data = enhanced.model_dump()
        assert json_data["provider"]["provider_name"] == "TestProvider"
        assert json_data["availability"] is True
        assert json_data["web_data"] is None
