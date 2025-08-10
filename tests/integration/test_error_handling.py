"""Integration tests for error handling and graceful degradation."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

pytest.skip("web scraping error handling removed", allow_module_level=True)

# These imports are needed for the skipped tests
# from openrouter_inspector.models import ProviderDetails, ProviderInfo
# from openrouter_inspector.services import WebScrapingService
# from openrouter_inspector.exceptions import PageNotFoundError, WebScrapingError, WebTimeoutError
# from openrouter_inspector.cli import cli


class TestErrorHandlingAndGracefulDegradation:
    """Web scraping removed; only API error handling remains elsewhere."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock config for testing."""
        return Config(api_key="test-key")

    @pytest.fixture
    def mock_api_provider(self):
        """Mock API provider data for fallback scenarios."""
        return ProviderDetails(
            provider=ProviderInfo(
                provider_name="TestProvider",
                model_id="test/model",
                endpoint_name="Test Model",
                context_window=32000,
                supports_tools=True,
                is_reasoning_model=False,
                quantization="fp16",
                uptime_30min=99.0,
                pricing={"prompt": 0.000001, "completion": 0.000002},
            ),
            availability=True,
            last_updated=datetime.now(),
        )

    # Web scraping tests removed

    @pytest.mark.asyncio
    async def test_non_retryable_errors_not_retried(self, mock_config):
        """Test that non-retryable errors (404, etc.) are not retried."""
        from openrouter_inspector.cache import WebCacheManager

        service = WebScrapingService(mock_config, WebCacheManager(ttl=1800))

        with patch.object(service, "session") as mock_session:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_session.get.return_value = mock_response

            with pytest.raises(PageNotFoundError):
                await service._fetch_html_with_retry("https://test.com")

            # Should only be called once (no retries for 404)
            assert mock_session.get.call_count == 1

    @pytest.mark.asyncio
    async def test_max_retries_exhausted(self, mock_config):
        """Test behavior when max retries are exhausted."""
        from openrouter_inspector.cache import WebCacheManager

        service = WebScrapingService(mock_config, WebCacheManager(ttl=1800))

        with patch.object(service, "session") as mock_session:
            # Always return 500 error
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.raise_for_status.side_effect = Exception("Server error")
            mock_session.get.return_value = mock_response

            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(WebScrapingError):
                    await service._fetch_html_with_retry("https://test.com")

                # Should be called max_retries + 1 times (initial + retries)
                assert mock_session.get.call_count == mock_config.web_max_retries + 1

    def test_cli_fallback_to_api_only_on_web_error(self, mock_api_provider):
        """Test CLI gracefully falls back to API-only mode when web scraping fails."""
        runner = CliRunner()

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch(
                "openrouter_inspector.services.ModelService.get_model_providers_enhanced"
            ) as mock_enhanced_method:
                with patch(
                    "openrouter_inspector.client.OpenRouterClient"
                ) as mock_client_class:
                    # Setup client mock
                    mock_client = AsyncMock()
                    mock_client_class.return_value.__aenter__.return_value = mock_client

                    # Mock enhanced method to raise web scraping error
                    mock_enhanced_method.side_effect = WebScrapingError(
                        "Web scraping failed", url="https://test.com"
                    )

                    # Mock fallback to API-only data
                    mock_client.get_model_providers.return_value = [mock_api_provider]
                    mock_client.get_models.return_value = []

                    result = runner.invoke(cli, ["endpoints", "test/model"])

                    # Should succeed with fallback
                    assert result.exit_code == 0
                    # Should not show web data columns
                    assert "TPS" not in result.output
                    assert (
                        "Latency" not in result.output and "Late" not in result.output
                    )
                    assert "Uptime" not in result.output and "Upt" not in result.output
                    # Should show API data
                    assert "TestProvider" in result.output

    def test_cli_timeout_handling(self, mock_api_provider):
        """Test CLI handles timeout errors gracefully."""
        runner = CliRunner()

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch(
                "openrouter_inspector.services.ModelService.get_model_providers_enhanced"
            ) as mock_enhanced_method:
                with patch(
                    "openrouter_inspector.client.OpenRouterClient"
                ) as mock_client_class:
                    # Setup client mock
                    mock_client = AsyncMock()
                    mock_client_class.return_value.__aenter__.return_value = mock_client

                    # Mock enhanced method to raise timeout error
                    mock_enhanced_method.side_effect = WebTimeoutError(
                        "Request timed out", url="https://test.com", timeout_seconds=10
                    )

                    # Mock fallback to API-only data
                    mock_client.get_model_providers.return_value = [mock_api_provider]
                    mock_client.get_models.return_value = []

                    result = runner.invoke(cli, ["endpoints", "test/model"])

                    # Should succeed with fallback
                    assert result.exit_code == 0
                    # Should show API data without web columns
                    assert "TestProvider" in result.output
                    assert "TPS" not in result.output

    @pytest.mark.asyncio
    async def test_retryable_error_detection(self, mock_config):
        """Test detection of retryable vs non-retryable errors."""
        from openrouter_inspector.cache import WebCacheManager

        service = WebScrapingService(mock_config, WebCacheManager(ttl=1800))

        # Test retryable errors
        retryable_errors = [
            WebScrapingError("Rate limited", context={"status_code": 429}),
            WebScrapingError("Server error", context={"status_code": 500}),
            WebScrapingError("Bad gateway", context={"status_code": 502}),
            WebScrapingError("Service unavailable", context={"status_code": 503}),
            WebScrapingError("Gateway timeout", context={"status_code": 504}),
            WebScrapingError("Network error", context={"error_type": "network"}),
            WebScrapingError("Connection timeout", context={"error_type": "timeout"}),
        ]

        for error in retryable_errors:
            assert service._is_retryable_error(error), f"Should be retryable: {error}"

        # Test non-retryable errors
        non_retryable_errors = [
            WebScrapingError("Not found", context={"status_code": 404}),
            WebScrapingError("Forbidden", context={"status_code": 403}),
            WebScrapingError("Bad request", context={"status_code": 400}),
            WebScrapingError("Parse error", context={"error_type": "parse"}),
        ]

        for error in non_retryable_errors:
            assert not service._is_retryable_error(error), (
                f"Should not be retryable: {error}"
            )

    def test_debug_logging_for_web_errors(self, mock_api_provider, caplog):
        """Test that web scraping errors are logged at debug level."""
        import logging

        runner = CliRunner()

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch(
                "openrouter_inspector.services.ModelService.get_model_providers_enhanced"
            ) as mock_enhanced_method:
                with patch(
                    "openrouter_inspector.client.OpenRouterClient"
                ) as mock_client_class:
                    # Setup client mock
                    mock_client = AsyncMock()
                    mock_client_class.return_value.__aenter__.return_value = mock_client

                    # Mock enhanced method to raise web scraping error
                    mock_enhanced_method.side_effect = WebScrapingError(
                        "Web scraping failed", url="https://test.com"
                    )

                    # Mock fallback to API-only data
                    mock_client.get_model_providers.return_value = [mock_api_provider]
                    mock_client.get_models.return_value = []

                    with caplog.at_level(logging.DEBUG):
                        result = runner.invoke(
                            cli, ["--log-level", "DEBUG", "endpoints", "test/model"]
                        )

                    # Should succeed with fallback
                    assert result.exit_code == 0

                    # Check that debug logging occurred
                    debug_messages = [
                        record.message
                        for record in caplog.records
                        if record.levelno == logging.DEBUG
                    ]
                    assert any(
                        "fallback" in msg.lower() or "web" in msg.lower()
                        for msg in debug_messages
                    )

    @pytest.mark.asyncio
    async def test_circuit_breaker_pattern(self, mock_config):
        """Test circuit breaker-like behavior for repeated failures."""
        from openrouter_inspector.cache import WebCacheManager

        service = WebScrapingService(mock_config, WebCacheManager(ttl=1800))

        # Simulate multiple consecutive failures
        with patch.object(service, "session") as mock_session:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.raise_for_status.side_effect = Exception("Server error")
            mock_session.get.return_value = mock_response

            with patch("asyncio.sleep", new_callable=AsyncMock):
                # Multiple calls should all fail after retries
                for _ in range(3):
                    with pytest.raises(WebScrapingError):
                        await service._fetch_html_with_retry("https://test.com")

                # Total calls should be (max_retries + 1) * number_of_attempts
                expected_calls = (mock_config.web_max_retries + 1) * 3
                assert mock_session.get.call_count == expected_calls

    def test_fallback_output_format_consistency(self, mock_api_provider):
        """Test that fallback output format is consistent with API-only mode."""
        runner = CliRunner()

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            # Test 1: Explicit --no-web-scraping
            with patch(
                "openrouter_inspector.services.ModelService.get_model_providers_enhanced"
            ) as mock_enhanced_method:
                with patch(
                    "openrouter_inspector.client.OpenRouterClient"
                ) as mock_client_class:
                    mock_client = AsyncMock()
                    mock_client_class.return_value.__aenter__.return_value = mock_client
                    mock_client.get_model_providers.return_value = [mock_api_provider]
                    mock_client.get_models.return_value = []

                    result_no_web = runner.invoke(
                        cli, ["endpoints", "test/model", "--no-web-scraping"]
                    )

            # Test 2: Web scraping failure fallback
            with patch(
                "openrouter_inspector.services.ModelService.get_model_providers_enhanced"
            ) as mock_enhanced_method:
                with patch(
                    "openrouter_inspector.client.OpenRouterClient"
                ) as mock_client_class:
                    mock_client = AsyncMock()
                    mock_client_class.return_value.__aenter__.return_value = mock_client
                    mock_enhanced_method.side_effect = WebScrapingError("Failed")
                    mock_client.get_model_providers.return_value = [mock_api_provider]
                    mock_client.get_models.return_value = []

                    result_fallback = runner.invoke(cli, ["endpoints", "test/model"])

            # Both should succeed and have similar output structure
            assert result_no_web.exit_code == 0
            assert result_fallback.exit_code == 0

            # Both should exclude web data columns
            for result in [result_no_web, result_fallback]:
                assert "TPS" not in result.output
                assert "Latency" not in result.output and "Late" not in result.output
                assert "Uptime" not in result.output and "Upt" not in result.output
                assert "TestProvider" in result.output
