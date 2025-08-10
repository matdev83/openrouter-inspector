"""Unit tests for the web scraping service."""

import pytest
import httpx
from datetime import datetime
from unittest.mock import Mock, AsyncMock

from openrouter_inspector.web_scraper import WebScrapingService, URLMapper
from openrouter_inspector.config import Config
from openrouter_inspector.cache import CacheManager
from openrouter_inspector.exceptions import (
    WebScrapingError, 
    PageNotFoundError, 
    ParseError, 
    WebTimeoutError
)
from openrouter_inspector.models import WebScrapedData, WebProviderData


class TestWebScrapingService:
    """Test cases for WebScrapingService."""

    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        config = Config(
            api_key="test-key",
            base_url="https://openrouter.ai/api/v1"
        )
        # Add web scraping specific attributes
        config.web_timeout = 10
        config.web_user_agent = "test-agent"
        return config

    @pytest.fixture
    def cache_manager(self):
        """Create a test cache manager."""
        return CacheManager(ttl=300)

    @pytest.fixture
    def web_service(self, config, cache_manager):
        """Create a WebScrapingService instance."""
        return WebScrapingService(config, cache_manager)

    @pytest.fixture
    def sample_html(self):
        """Sample HTML content for testing."""
        return """
        <html>
        <body>
            <table class="provider-table">
                <tr>
                    <th>Provider</th>
                    <th>Quantization</th>
                    <th>Context</th>
                    <th>Max Output</th>
                    <th>Throughput</th>
                    <th>Latency</th>
                    <th>Uptime</th>
                </tr>
                <tr>
                    <td>DeepInfra</td>
                    <td>fp8</td>
                    <td>33K</td>
                    <td>16K</td>
                    <td>15.2 TPS</td>
                    <td>0.85s</td>
                    <td>99.5%</td>
                </tr>
                <tr>
                    <td>Lambda</td>
                    <td>bf16</td>
                    <td>33K</td>
                    <td>33K</td>
                    <td>12.8 TPS</td>
                    <td>1.20s</td>
                    <td>98.9%</td>
                </tr>
            </table>
        </body>
        </html>
        """

    def test_init_with_config(self, config):
        """Test WebScrapingService initialization with config."""
        service = WebScrapingService(config)
        
        assert service.config == config
        assert service.timeout == 10
        assert service.cache is None
        assert service.session is not None

    def test_init_with_cache(self, config, cache_manager):
        """Test WebScrapingService initialization with cache."""
        service = WebScrapingService(config, cache_manager)
        
        assert service.config == config
        assert service.cache == cache_manager
        assert service.session is not None

    def test_init_with_default_timeout(self):
        """Test WebScrapingService initialization with default timeout."""
        config = Config(api_key="test-key")
        service = WebScrapingService(config)
        
        assert service.timeout == 10  # Default timeout

    def test_model_id_to_web_url_valid(self, web_service):
        """Test URL generation for valid model IDs."""
        test_cases = [
            ("qwen/qwen-2.5-coder-32b-instruct", "https://openrouter.ai/qwen/qwen-2.5-coder-32b-instruct"),
            ("openai/gpt-4", "https://openrouter.ai/openai/gpt-4"),
            ("anthropic/claude-3-opus", "https://openrouter.ai/anthropic/claude-3-opus"),
        ]
        
        for model_id, expected_url in test_cases:
            url = web_service._model_id_to_web_url(model_id)
            assert url == expected_url

    def test_model_id_to_web_url_with_special_chars(self, web_service):
        """Test URL generation with special characters."""
        model_id = "test/model with spaces"
        url = web_service._model_id_to_web_url(model_id)
        assert "test" in url
        assert "model%20with%20spaces" in url

    def test_model_id_to_web_url_invalid(self, web_service):
        """Test URL generation with invalid model IDs."""
        invalid_ids = ["", "no-slash", "  ", None]
        
        for invalid_id in invalid_ids:
            with pytest.raises(ValueError, match="Invalid model ID format"):
                web_service._model_id_to_web_url(invalid_id)

    @pytest.mark.asyncio
    async def test_get_model_web_data_empty_model_id(self, web_service):
        """Test get_model_web_data with empty model ID."""
        with pytest.raises(ValueError, match="Model ID cannot be empty"):
            await web_service.get_model_web_data("")

    @pytest.mark.asyncio
    async def test_get_model_web_data_cached(self, web_service):
        """Test get_model_web_data with cached data."""
        model_id = "test/model"
        cached_data = WebScrapedData(
            model_id=model_id,
            providers=[],
            source_url="https://openrouter.ai/test/model"
        )
        
        # Set up cache
        web_service.cache.set(f"web_data:{model_id}", cached_data)
        
        result = await web_service.get_model_web_data(model_id)
        assert result == cached_data

    @pytest.mark.asyncio
    async def test_fetch_html_success(self, web_service, sample_html):
        """Test successful HTML fetching."""
        # Mock the HTTP client
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = sample_html
        mock_response.raise_for_status = Mock()
        
        web_service.session.get = AsyncMock(return_value=mock_response)
        
        result = await web_service._fetch_html("https://example.com")
        assert result == sample_html

    @pytest.mark.asyncio
    async def test_fetch_html_404_error(self, web_service):
        """Test HTML fetching with 404 error."""
        mock_response = Mock()
        mock_response.status_code = 404
        
        web_service.session.get = AsyncMock(return_value=mock_response)
        
        with pytest.raises(PageNotFoundError, match="Model page not found"):
            await web_service._fetch_html("https://example.com")

    @pytest.mark.asyncio
    async def test_fetch_html_timeout_error(self, web_service):
        """Test HTML fetching with timeout error."""
        web_service.session.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
        
        with pytest.raises(WebTimeoutError, match="Request timed out"):
            await web_service._fetch_html("https://example.com")

    @pytest.mark.asyncio
    async def test_fetch_html_network_error(self, web_service):
        """Test HTML fetching with network error."""
        web_service.session.get = AsyncMock(side_effect=httpx.NetworkError("Network error"))
        
        with pytest.raises(WebScrapingError, match="Network error"):
            await web_service._fetch_html("https://example.com")

    @pytest.mark.asyncio
    async def test_fetch_html_rate_limit_retry(self, web_service, sample_html):
        """Test HTML fetching with rate limit and successful retry."""
        # First response: rate limited
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        
        # Second response: success
        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.text = sample_html
        mock_response_200.raise_for_status = Mock()
        
        web_service.session.get = AsyncMock(side_effect=[mock_response_429, mock_response_200])
        
        result = await web_service._fetch_html("https://example.com")
        assert result == sample_html
        assert web_service.session.get.call_count == 2

    @pytest.mark.asyncio
    async def test_fetch_html_rate_limit_persistent(self, web_service):
        """Test HTML fetching with persistent rate limiting."""
        mock_response = Mock()
        mock_response.status_code = 429
        
        web_service.session.get = AsyncMock(return_value=mock_response)
        
        with pytest.raises(WebScrapingError, match="Rate limited after retry"):
            await web_service._fetch_html("https://example.com")

    @pytest.mark.asyncio
    async def test_get_model_web_data_success(self, web_service, sample_html):
        """Test successful web data scraping."""
        model_id = "test/model"
        
        # Mock HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = sample_html
        mock_response.raise_for_status = Mock()
        
        web_service.session.get = AsyncMock(return_value=mock_response)
        
        result = await web_service.get_model_web_data(model_id)
        
        assert result is not None
        assert result.model_id == model_id
        assert len(result.providers) == 2
        assert result.source_url == "https://openrouter.ai/test/model"
        
        # Check first provider
        provider1 = result.providers[0]
        assert provider1.provider_name == "DeepInfra"
        assert provider1.quantization == "fp8"
        assert provider1.context_window == 33000
        assert provider1.max_completion_tokens == 16000
        assert provider1.throughput_tps == 15.2
        assert provider1.latency_seconds == 0.85
        assert provider1.uptime_percentage == 99.5

    @pytest.mark.asyncio
    async def test_get_model_web_data_parse_error(self, web_service):
        """Test web data scraping with parse error."""
        model_id = "test/model"
        
        # Mock HTTP response with invalid HTML
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "invalid html"
        mock_response.raise_for_status = Mock()
        
        web_service.session.get = AsyncMock(return_value=mock_response)
        
        # This should not raise an error but return empty providers list
        result = await web_service.get_model_web_data(model_id)
        assert result is not None
        assert len(result.providers) == 0

    @pytest.mark.asyncio
    async def test_get_model_web_data_caching(self, web_service, sample_html):
        """Test that web data is properly cached."""
        model_id = "test/model"
        
        # Mock HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = sample_html
        mock_response.raise_for_status = Mock()
        
        web_service.session.get = AsyncMock(return_value=mock_response)
        
        # First call should fetch and cache
        result1 = await web_service.get_model_web_data(model_id)
        assert web_service.session.get.call_count == 1
        
        # Second call should use cache
        result2 = await web_service.get_model_web_data(model_id)
        assert web_service.session.get.call_count == 1  # No additional call
        assert result1.model_id == result2.model_id

    @pytest.mark.asyncio
    async def test_get_model_web_data_unexpected_error(self, web_service):
        """Test web data scraping with unexpected error."""
        model_id = "test/model"
        
        web_service.session.get = AsyncMock(side_effect=Exception("Unexpected error"))
        
        with pytest.raises(WebScrapingError, match="Failed to scrape web data"):
            await web_service.get_model_web_data(model_id)

    @pytest.mark.asyncio
    async def test_close(self, web_service):
        """Test closing the web service."""
        web_service.session.aclose = AsyncMock()
        
        await web_service.close()
        web_service.session.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager(self, config):
        """Test using WebScrapingService as async context manager."""
        async with WebScrapingService(config) as service:
            assert service.session is not None
        
        # Session should be closed after exiting context


class TestURLMapper:
    """Test cases for URLMapper utility class."""

    def test_model_id_to_web_url_valid(self):
        """Test URL generation for valid model IDs."""
        test_cases = [
            ("qwen/qwen-2.5-coder-32b-instruct", "https://openrouter.ai/qwen/qwen-2.5-coder-32b-instruct"),
            ("openai/gpt-4", "https://openrouter.ai/openai/gpt-4"),
            ("anthropic/claude-3-opus", "https://openrouter.ai/anthropic/claude-3-opus"),
            ("Test/Model", "https://openrouter.ai/test/model"),  # Case normalization
        ]
        
        for model_id, expected_url in test_cases:
            url = URLMapper.model_id_to_web_url(model_id)
            assert url == expected_url

    def test_model_id_to_web_url_with_special_chars(self):
        """Test URL generation with special characters."""
        model_id = "test/model with spaces"
        url = URLMapper.model_id_to_web_url(model_id)
        assert "test" in url
        assert "model%20with%20spaces" in url

    def test_model_id_to_web_url_invalid(self):
        """Test URL generation with invalid model IDs."""
        invalid_ids = ["", "no-slash", "  ", None]
        
        for invalid_id in invalid_ids:
            with pytest.raises(ValueError, match="Invalid model ID format"):
                URLMapper.model_id_to_web_url(invalid_id)

    def test_normalize_model_slug(self):
        """Test model slug normalization."""
        test_cases = [
            ("Test Model", "test-model"),
            ("test_model", "test-model"),
            ("  Test  Model  ", "test-model"),
            ("already-normalized", "already-normalized"),
            ("", ""),
        ]
        
        for input_slug, expected in test_cases:
            result = URLMapper.normalize_model_slug(input_slug)
            assert result == expected


class TestWebScrapingServiceIntegration:
    """Integration tests for WebScrapingService with real-like scenarios."""

    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        config = Config(api_key="test-key")
        config.web_timeout = 5  # Shorter timeout for tests
        return config

    @pytest.mark.asyncio
    async def test_full_scraping_workflow(self, config):
        """Test the complete scraping workflow."""
        service = WebScrapingService(config, CacheManager(ttl=60))
        
        # Mock a complete HTML response
        html_content = """
        <html>
        <body>
            <table>
                <tr>
                    <th>Provider</th>
                    <th>Throughput</th>
                    <th>Latency</th>
                    <th>Uptime</th>
                </tr>
                <tr>
                    <td>TestProvider</td>
                    <td>10.5 TPS</td>
                    <td>1.2s</td>
                    <td>98.5%</td>
                </tr>
            </table>
        </body>
        </html>
        """
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = html_content
        mock_response.raise_for_status = Mock()
        
        service.session.get = AsyncMock(return_value=mock_response)
        
        try:
            result = await service.get_model_web_data("test/model")
            
            assert result is not None
            assert result.model_id == "test/model"
            assert len(result.providers) == 1
            
            provider = result.providers[0]
            assert provider.provider_name == "TestProvider"
            assert provider.throughput_tps == 10.5
            assert provider.latency_seconds == 1.2
            assert provider.uptime_percentage == 98.5
            
        finally:
            await service.close()

    @pytest.mark.asyncio
    async def test_error_handling_workflow(self, config):
        """Test error handling in the complete workflow."""
        service = WebScrapingService(config)
        
        # Test 404 error
        mock_response_404 = Mock()
        mock_response_404.status_code = 404
        service.session.get = AsyncMock(return_value=mock_response_404)
        
        try:
            with pytest.raises(PageNotFoundError):
                await service.get_model_web_data("nonexistent/model")
        finally:
            await service.close()

    @pytest.mark.asyncio
    async def test_no_cache_workflow(self, config):
        """Test workflow without caching."""
        service = WebScrapingService(config)  # No cache manager
        
        html_content = "<html><body><p>No provider table</p></body></html>"
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = html_content
        mock_response.raise_for_status = Mock()
        
        service.session.get = AsyncMock(return_value=mock_response)
        
        try:
            result = await service.get_model_web_data("test/model")
            
            assert result is not None
            assert result.model_id == "test/model"
            assert len(result.providers) == 0  # No providers found
            
        finally:
            await service.close()