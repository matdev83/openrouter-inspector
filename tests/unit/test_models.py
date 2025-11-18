"""Unit tests for data models."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from openrouter_inspector.models import (
    ModelInfo,
    ModelsResponse,
    ProviderDetails,
    ProviderInfo,
    ProvidersResponse,
    SearchFilters,
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
            "status": "online",
            "endpoint_name": "Test Endpoint",
            "context_window": 4096,
            "supports_tools": True,
            "is_reasoning_model": False,
            "quantization": "int8",
            "uptime_30min": 99.5,
            "performance_tps": 150.0,
            "max_completion_tokens": 4096,
            "supported_parameters": ["tools", "reasoning"],
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
            "status": "online",
            "endpoint_name": "Test Endpoint",
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
            "supports_image_input": True,
            "max_price_per_token": 0.01,
        }

        filters = SearchFilters(**filters_data)
        assert filters.min_context == 4096
        assert filters.supports_tools is True
        assert filters.supports_image_input is True
        assert filters.max_price_per_token == 0.01

    def test_empty_search_filters(self):
        """Test SearchFilters with no filters set."""
        filters = SearchFilters()
        assert filters.min_context is None
        assert filters.supports_tools is None
        assert filters.reasoning_only is None
        assert filters.supports_image_input is None
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
        assert "supports_image_input" not in json_data
        assert "max_price_per_token" not in json_data
