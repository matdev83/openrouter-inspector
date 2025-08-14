"""Unit tests for CLI endpoints command filtering functionality."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from openrouter_inspector.cli import cli
from openrouter_inspector.models import ProviderDetails, ProviderInfo


class TestCliEndpointsFiltering:
    """Test cases for CLI endpoints command filtering options."""

    @pytest.fixture
    def runner(self):
        """CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def sample_providers(self):
        """Sample provider data with various characteristics."""
        return [
            ProviderDetails(
                provider=ProviderInfo(
                    provider_name="Provider A",
                    model_id="test-model",
                    endpoint_name="Model A",
                    context_window=8192,
                    supports_tools=True,
                    is_reasoning_model=True,
                    quantization="fp16",
                    uptime_30min=99.5,
                    pricing={"prompt": 0.00001, "completion": 0.00002},
                    max_completion_tokens=4096,
                    supported_parameters=["tools", "reasoning"],
                    status="active",
                    performance_tps=100.0,
                ),
                availability=True,
                last_updated=datetime.now(),
            ),
            ProviderDetails(
                provider=ProviderInfo(
                    provider_name="Provider B",
                    model_id="test-model",
                    endpoint_name="Model B",
                    context_window=16384,
                    supports_tools=False,
                    is_reasoning_model=False,
                    quantization="q4",
                    uptime_30min=98.0,
                    pricing={"prompt": 0.000005, "completion": 0.00001},
                    max_completion_tokens=2048,
                    supported_parameters=["image"],
                    status="active",
                    performance_tps=50.0,
                ),
                availability=True,
                last_updated=datetime.now(),
            ),
            ProviderDetails(
                provider=ProviderInfo(
                    provider_name="Provider C",
                    model_id="test-model",
                    endpoint_name="Model C",
                    context_window=32768,
                    supports_tools=True,
                    is_reasoning_model=False,
                    quantization="bf16",
                    uptime_30min=95.0,
                    pricing={"prompt": 0.000015, "completion": 0.000025},
                    max_completion_tokens=8192,
                    supported_parameters=["tools", "image"],
                    status="active",
                    performance_tps=75.0,
                ),
                availability=True,
                last_updated=datetime.now(),
            ),
        ]

    def test_endpoints_basic(self, runner, sample_providers):
        """Test basic endpoints functionality."""
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch(
                "openrouter_inspector.client.OpenRouterClient"
            ) as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value.__aenter__.return_value = mock_client

                with patch(
                    "openrouter_inspector.services.ModelService"
                ) as mock_service_class:
                    mock_service = AsyncMock()
                    mock_service_class.return_value = mock_service
                    mock_service.get_model_providers.return_value = sample_providers

                    result = runner.invoke(cli, ["endpoints", "test-model"])

                    assert result.exit_code == 0
                    assert "Provider A" in result.output
                    assert "Provider B" in result.output
                    assert "Provider C" in result.output

    def test_endpoints_with_min_quantization(self, runner, sample_providers):
        """Test endpoints with minimum quantization filter."""
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch(
                "openrouter_inspector.client.OpenRouterClient"
            ) as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value.__aenter__.return_value = mock_client

                with patch(
                    "openrouter_inspector.services.ModelService"
                ) as mock_service_class:
                    mock_service = AsyncMock()
                    mock_service_class.return_value = mock_service
                    mock_service.get_model_providers.return_value = sample_providers

                    result = runner.invoke(
                        cli, ["endpoints", "test-model", "--min-quant", "fp16"]
                    )

                    assert result.exit_code == 0
                    # Should include Provider A (fp16) and Provider C (bf16, which is better than fp16)
                    # Should exclude Provider B (q4, which is worse than fp16)

    def test_endpoints_with_min_context(self, runner, sample_providers):
        """Test endpoints with minimum context filter."""
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch(
                "openrouter_inspector.client.OpenRouterClient"
            ) as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value.__aenter__.return_value = mock_client

                with patch(
                    "openrouter_inspector.services.ModelService"
                ) as mock_service_class:
                    mock_service = AsyncMock()
                    mock_service_class.return_value = mock_service
                    mock_service.get_model_providers.return_value = sample_providers

                    result = runner.invoke(
                        cli, ["endpoints", "test-model", "--min-context", "16K"]
                    )

                    assert result.exit_code == 0
                    # Should include Provider B (16384) and Provider C (32768)
                    # Should exclude Provider A (8192)

    def test_endpoints_with_reasoning_required(self, runner, sample_providers):
        """Test endpoints with reasoning required filter."""
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch(
                "openrouter_inspector.client.OpenRouterClient"
            ) as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value.__aenter__.return_value = mock_client

                with patch(
                    "openrouter_inspector.services.ModelService"
                ) as mock_service_class:
                    mock_service = AsyncMock()
                    mock_service_class.return_value = mock_service
                    mock_service.get_model_providers.return_value = sample_providers

                    result = runner.invoke(
                        cli, ["endpoints", "test-model", "--reasoning"]
                    )

                    assert result.exit_code == 0
                    # Should include only Provider A (supports reasoning)
                    # Should exclude Provider B and C (don't support reasoning)

    def test_endpoints_with_no_reasoning_required(self, runner, sample_providers):
        """Test endpoints with no reasoning required filter."""
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch(
                "openrouter_inspector.client.OpenRouterClient"
            ) as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value.__aenter__.return_value = mock_client

                with patch(
                    "openrouter_inspector.services.ModelService"
                ) as mock_service_class:
                    mock_service = AsyncMock()
                    mock_service_class.return_value = mock_service
                    mock_service.get_model_providers.return_value = sample_providers

                    result = runner.invoke(
                        cli, ["endpoints", "test-model", "--no-reasoning"]
                    )

                    assert result.exit_code == 0
                    # Should include Provider B and C (don't require reasoning)
                    # Should exclude Provider A (requires reasoning)

    def test_endpoints_with_tools_required(self, runner, sample_providers):
        """Test endpoints with tools required filter."""
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch(
                "openrouter_inspector.client.OpenRouterClient"
            ) as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value.__aenter__.return_value = mock_client

                with patch(
                    "openrouter_inspector.services.ModelService"
                ) as mock_service_class:
                    mock_service = AsyncMock()
                    mock_service_class.return_value = mock_service
                    mock_service.get_model_providers.return_value = sample_providers

                    result = runner.invoke(cli, ["endpoints", "test-model", "--tools"])

                    assert result.exit_code == 0
                    # Should include Provider A and C (support tools)
                    # Should exclude Provider B (doesn't support tools)

    def test_endpoints_with_no_tools_required(self, runner, sample_providers):
        """Test endpoints with no tools required filter."""
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch(
                "openrouter_inspector.client.OpenRouterClient"
            ) as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value.__aenter__.return_value = mock_client

                with patch(
                    "openrouter_inspector.services.ModelService"
                ) as mock_service_class:
                    mock_service = AsyncMock()
                    mock_service_class.return_value = mock_service
                    mock_service.get_model_providers.return_value = sample_providers

                    result = runner.invoke(
                        cli, ["endpoints", "test-model", "--no-tools"]
                    )

                    assert result.exit_code == 0
                    # Should include only Provider B (doesn't support tools)
                    # Should exclude Provider A and C (support tools)

    def test_endpoints_with_image_required(self, runner, sample_providers):
        """Test endpoints with image input required filter."""
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch(
                "openrouter_inspector.client.OpenRouterClient"
            ) as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value.__aenter__.return_value = mock_client

                with patch(
                    "openrouter_inspector.services.ModelService"
                ) as mock_service_class:
                    mock_service = AsyncMock()
                    mock_service_class.return_value = mock_service
                    mock_service.get_model_providers.return_value = sample_providers

                    result = runner.invoke(cli, ["endpoints", "test-model", "--img"])

                    assert result.exit_code == 0
                    # Should include Provider B and C (support image input)
                    # Should exclude Provider A (doesn't support image input)

    def test_endpoints_with_max_price_filters(self, runner, sample_providers):
        """Test endpoints with maximum price filters."""
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch(
                "openrouter_inspector.client.OpenRouterClient"
            ) as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value.__aenter__.return_value = mock_client

                with patch(
                    "openrouter_inspector.services.ModelService"
                ) as mock_service_class:
                    mock_service = AsyncMock()
                    mock_service_class.return_value = mock_service
                    mock_service.get_model_providers.return_value = sample_providers

                    # Test max input price filter
                    result = runner.invoke(
                        cli, ["endpoints", "test-model", "--max-input-price", "0.01"]
                    )

                    assert result.exit_code == 0

                    # Test max output price filter
                    result = runner.invoke(
                        cli, ["endpoints", "test-model", "--max-output-price", "0.02"]
                    )

                    assert result.exit_code == 0

    def test_endpoints_with_sorting(self, runner, sample_providers):
        """Test endpoints with sorting options."""
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch(
                "openrouter_inspector.client.OpenRouterClient"
            ) as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value.__aenter__.return_value = mock_client

                with patch(
                    "openrouter_inspector.services.ModelService"
                ) as mock_service_class:
                    mock_service = AsyncMock()
                    mock_service_class.return_value = mock_service
                    mock_service.get_model_providers.return_value = sample_providers

                    # Test sorting by provider name
                    result = runner.invoke(
                        cli, ["endpoints", "test-model", "--sort-by", "provider"]
                    )

                    assert result.exit_code == 0

                    # Test sorting by context window
                    result = runner.invoke(
                        cli, ["endpoints", "test-model", "--sort-by", "context"]
                    )

                    assert result.exit_code == 0

                    # Test sorting by price
                    result = runner.invoke(
                        cli, ["endpoints", "test-model", "--sort-by", "price_in"]
                    )

                    assert result.exit_code == 0

    def test_endpoints_with_descending_sort(self, runner, sample_providers):
        """Test endpoints with descending sort order."""
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch(
                "openrouter_inspector.client.OpenRouterClient"
            ) as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value.__aenter__.return_value = mock_client

                with patch(
                    "openrouter_inspector.services.ModelService"
                ) as mock_service_class:
                    mock_service = AsyncMock()
                    mock_service_class.return_value = mock_service
                    mock_service.get_model_providers.return_value = sample_providers

                    result = runner.invoke(
                        cli,
                        ["endpoints", "test-model", "--sort-by", "context", "--desc"],
                    )

                    assert result.exit_code == 0

    def test_endpoints_with_no_hints(self, runner, sample_providers):
        """Test endpoints with --no-hints flag."""
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch(
                "openrouter_inspector.client.OpenRouterClient"
            ) as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value.__aenter__.return_value = mock_client

                with patch(
                    "openrouter_inspector.services.ModelService"
                ) as mock_service_class:
                    mock_service = AsyncMock()
                    mock_service_class.return_value = mock_service
                    mock_service.get_model_providers.return_value = sample_providers

                    with patch(
                        "openrouter_inspector.formatters.table_formatter.TableFormatter.format_providers"
                    ) as mock_format_providers:
                        mock_format_providers.return_value = "mocked output"

                        result = runner.invoke(
                            cli, ["endpoints", "test-model", "--no-hints"]
                        )

                        assert result.exit_code == 0
                        # Verify that no_hints=True is passed to the formatter
                        mock_format_providers.assert_called_once()
                        call_args = mock_format_providers.call_args
                        assert call_args[1]["no_hints"] is True
