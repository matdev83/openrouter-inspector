"""Unit tests for enhanced ModelService with web scraping integration."""

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

pytest.skip("web scraping removed", allow_module_level=True)

# These imports are needed for the skipped tests
# from openrouter_inspector.models import (
#     EnhancedProviderDetails,
#     ProviderDetails,
#     ProviderInfo,
#     WebProviderData,
#     WebScrapedData,
# )
# from openrouter_inspector.services import ModelService
# from openrouter_inspector.exceptions import WebScrapingError


class TestModelServiceEnhanced:
    """Test cases for enhanced ModelService functionality."""

    @pytest.fixture
    def mock_client(self):
        """Mock OpenRouter client."""
        client = AsyncMock()
        return client

    @pytest.fixture
    def mock_web_scraper(self):
        """Mock web scraping service."""
        scraper = AsyncMock()
        return scraper

    @pytest.fixture
    def sample_api_providers(self):
        """Sample API provider data."""
        return [
            ProviderDetails(
                provider=ProviderInfo(
                    provider_name="DeepInfra",
                    model_id="qwen/qwen-2.5-coder-32b-instruct",
                    context_window=32768,
                    supports_tools=True,
                    is_reasoning_model=False,
                    quantization="fp8",
                    uptime_30min=99.2,
                    pricing={"prompt": 0.06, "completion": 0.15},
                    max_completion_tokens=16384,
                ),
                availability=True,
                last_updated=datetime.now(),
            ),
            ProviderDetails(
                provider=ProviderInfo(
                    provider_name="Lambda Labs",
                    model_id="qwen/qwen-2.5-coder-32b-instruct",
                    context_window=32768,
                    supports_tools=False,
                    is_reasoning_model=False,
                    quantization="bf16",
                    uptime_30min=98.5,
                    pricing={"prompt": 0.07, "completion": 0.16},
                ),
                availability=True,
                last_updated=datetime.now(),
            ),
        ]

    @pytest.fixture
    def sample_web_data(self):
        """Sample web-scraped data."""
        return WebScrapedData(
            model_id="qwen/qwen-2.5-coder-32b-instruct",
            providers=[
                WebProviderData(
                    provider_name="DeepInfra",
                    throughput_tps=15.2,
                    latency_seconds=0.85,
                    uptime_percentage=99.5,
                ),
                WebProviderData(
                    provider_name="Lambda Labs",
                    throughput_tps=12.8,
                    latency_seconds=1.20,
                    uptime_percentage=98.9,
                ),
            ],
            source_url="https://openrouter.ai/qwen/qwen-2.5-coder-32b-instruct",
        )

    def test_init_without_web_scraper(self, mock_client):
        """Test ModelService initialization without web scraper."""
        service = ModelService(mock_client)
        assert service.client == mock_client
        assert service.web_scraper is None

    def test_init_with_web_scraper(self, mock_client, mock_web_scraper):
        """Test ModelService initialization with web scraper."""
        service = ModelService(mock_client, mock_web_scraper)
        assert service.client == mock_client
        assert service.web_scraper == mock_web_scraper

    @pytest.mark.asyncio
    async def test_get_model_providers_enhanced_api_only(
        self, mock_client, sample_api_providers
    ):
        """Test enhanced method with API-only data (no web scraping)."""
        mock_client.get_model_providers.return_value = sample_api_providers
        service = ModelService(mock_client)

        result = await service.get_model_providers_enhanced(
            "test-model", include_web_data=False
        )

        assert len(result) == 2
        assert all(isinstance(p, EnhancedProviderDetails) for p in result)
        assert all(p.web_data is None for p in result)
        assert result[0].provider.provider_name == "DeepInfra"
        assert result[1].provider.provider_name == "Lambda Labs"

    @pytest.mark.asyncio
    async def test_get_model_providers_enhanced_no_web_scraper(
        self, mock_client, sample_api_providers
    ):
        """Test enhanced method when web scraping is requested but no scraper available."""
        mock_client.get_model_providers.return_value = sample_api_providers
        service = ModelService(mock_client)

        result = await service.get_model_providers_enhanced(
            "test-model", include_web_data=True
        )

        assert len(result) == 2
        assert all(isinstance(p, EnhancedProviderDetails) for p in result)
        assert all(p.web_data is None for p in result)

    @pytest.mark.asyncio
    async def test_get_model_providers_enhanced_with_web_data(
        self, mock_client, mock_web_scraper, sample_api_providers, sample_web_data
    ):
        """Test enhanced method with successful web scraping."""
        mock_client.get_model_providers.return_value = sample_api_providers
        mock_web_scraper.get_model_web_data.return_value = sample_web_data
        service = ModelService(mock_client, mock_web_scraper)

        result = await service.get_model_providers_enhanced(
            "test-model", include_web_data=True
        )

        assert len(result) == 2
        assert all(isinstance(p, EnhancedProviderDetails) for p in result)

        # Check that web data was merged correctly
        deepinfra_provider = next(
            p for p in result if p.provider.provider_name == "DeepInfra"
        )
        assert deepinfra_provider.web_data is not None
        assert deepinfra_provider.web_data.throughput_tps == 15.2
        assert deepinfra_provider.web_data.latency_seconds == 0.85
        assert deepinfra_provider.web_data.uptime_percentage == 99.5

        lambda_provider = next(
            p for p in result if p.provider.provider_name == "Lambda Labs"
        )
        assert lambda_provider.web_data is not None
        assert lambda_provider.web_data.throughput_tps == 12.8

    @pytest.mark.asyncio
    async def test_get_model_providers_enhanced_web_scraping_fails(
        self, mock_client, mock_web_scraper, sample_api_providers
    ):
        """Test enhanced method when web scraping fails gracefully."""
        mock_client.get_model_providers.return_value = sample_api_providers
        mock_web_scraper.get_model_web_data.side_effect = WebScrapingError(
            "Network error"
        )
        service = ModelService(mock_client, mock_web_scraper)

        result = await service.get_model_providers_enhanced(
            "test-model", include_web_data=True
        )

        assert len(result) == 2
        assert all(isinstance(p, EnhancedProviderDetails) for p in result)
        assert all(p.web_data is None for p in result)  # Should fall back to API-only

    @pytest.mark.asyncio
    async def test_get_model_providers_enhanced_api_fails(
        self, mock_client, mock_web_scraper
    ):
        """Test enhanced method when API call fails."""
        mock_client.get_model_providers.side_effect = Exception("API error")
        service = ModelService(mock_client, mock_web_scraper)

        with pytest.raises(Exception, match="API error"):
            await service.get_model_providers_enhanced(
                "test-model", include_web_data=True
            )

    @pytest.mark.asyncio
    async def test_get_model_providers_enhanced_web_returns_none(
        self, mock_client, mock_web_scraper, sample_api_providers
    ):
        """Test enhanced method when web scraping returns None."""
        mock_client.get_model_providers.return_value = sample_api_providers
        mock_web_scraper.get_model_web_data.return_value = None
        service = ModelService(mock_client, mock_web_scraper)

        result = await service.get_model_providers_enhanced(
            "test-model", include_web_data=True
        )

        assert len(result) == 2
        assert all(p.web_data is None for p in result)

    def test_merge_provider_data_no_web_data(self, mock_client, sample_api_providers):
        """Test merging when no web data is available."""
        service = ModelService(mock_client)

        result = service._merge_provider_data(sample_api_providers, None)

        assert len(result) == 2
        assert all(p.web_data is None for p in result)

    def test_merge_provider_data_empty_web_data(
        self, mock_client, sample_api_providers
    ):
        """Test merging when web data is empty."""
        service = ModelService(mock_client)
        empty_web_data = WebScrapedData(
            model_id="test-model", providers=[], source_url="https://example.com"
        )

        result = service._merge_provider_data(sample_api_providers, empty_web_data)

        assert len(result) == 2
        assert all(p.web_data is None for p in result)

    def test_merge_provider_data_successful_match(
        self, mock_client, sample_api_providers, sample_web_data
    ):
        """Test successful merging of API and web data."""
        service = ModelService(mock_client)

        result = service._merge_provider_data(sample_api_providers, sample_web_data)

        assert len(result) == 2

        # Check DeepInfra match
        deepinfra = next(p for p in result if p.provider.provider_name == "DeepInfra")
        assert deepinfra.web_data is not None
        assert deepinfra.web_data.throughput_tps == 15.2

        # Check Lambda Labs match
        lambda_labs = next(
            p for p in result if p.provider.provider_name == "Lambda Labs"
        )
        assert lambda_labs.web_data is not None
        assert lambda_labs.web_data.throughput_tps == 12.8

    def test_merge_provider_data_partial_match(self, mock_client, sample_api_providers):
        """Test merging when only some providers have web data."""
        service = ModelService(mock_client)

        # Web data with only one provider
        partial_web_data = WebScrapedData(
            model_id="test-model",
            providers=[
                WebProviderData(
                    provider_name="DeepInfra",
                    throughput_tps=15.2,
                    latency_seconds=0.85,
                    uptime_percentage=99.5,
                )
            ],
            source_url="https://example.com",
        )

        result = service._merge_provider_data(sample_api_providers, partial_web_data)

        assert len(result) == 2

        # DeepInfra should have web data
        deepinfra = next(p for p in result if p.provider.provider_name == "DeepInfra")
        assert deepinfra.web_data is not None

        # Lambda Labs should not have web data
        lambda_labs = next(
            p for p in result if p.provider.provider_name == "Lambda Labs"
        )
        assert lambda_labs.web_data is None

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

    def test_merge_provider_data_case_insensitive_matching(self, mock_client):
        """Test that provider matching is case-insensitive."""
        service = ModelService(mock_client)

        # API provider with different case
        api_providers = [
            ProviderDetails(
                provider=ProviderInfo(
                    provider_name="DEEPINFRA",  # Uppercase
                    model_id="test-model",
                    context_window=1000,
                    uptime_30min=99.0,
                    pricing={},
                ),
                availability=True,
                last_updated=datetime.now(),
            )
        ]

        # Web data with lowercase
        web_data = WebScrapedData(
            model_id="test-model",
            providers=[
                WebProviderData(
                    provider_name="deepinfra",
                    throughput_tps=15.2,  # Lowercase
                )
            ],
            source_url="https://example.com",
        )

        result = service._merge_provider_data(api_providers, web_data)

        assert len(result) == 1
        assert result[0].web_data is not None
        assert result[0].web_data.throughput_tps == 15.2

    def test_merge_provider_data_suffix_normalization_matching(self, mock_client):
        """Test that provider matching works with suffix normalization."""
        service = ModelService(mock_client)

        # API provider with suffix
        api_providers = [
            ProviderDetails(
                provider=ProviderInfo(
                    provider_name="OpenAI Inc",  # With suffix
                    model_id="test-model",
                    context_window=1000,
                    uptime_30min=99.0,
                    pricing={},
                ),
                availability=True,
                last_updated=datetime.now(),
            )
        ]

        # Web data without suffix
        web_data = WebScrapedData(
            model_id="test-model",
            providers=[
                WebProviderData(
                    provider_name="OpenAI",
                    throughput_tps=20.5,  # Without suffix
                )
            ],
            source_url="https://example.com",
        )

        result = service._merge_provider_data(api_providers, web_data)

        assert len(result) == 1
        assert result[0].web_data is not None
        assert result[0].web_data.throughput_tps == 20.5
