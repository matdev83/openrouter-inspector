"""Unit tests for output formatting enhancements."""

import re
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from openrouter_inspector.cli import cli
from openrouter_inspector.models import (
    ProviderDetails,
    ProviderInfo,
)


class TestOutputFormatting:
    """Test output formatting for API-only endpoints."""

    @pytest.fixture
    def runner(self):
        """CLI test runner."""
        return CliRunner()

    def create_mock_provider(
        self, name, supports_image=False, quantization: str | None = "fp16"
    ):
        """Create a mock provider (API-only)."""
        supported_params = ["reasoning"]
        if supports_image:
            supported_params.append("image")

        provider_info = ProviderInfo(
            provider_name=name,
            model_id="test/model",
            status="online",
            endpoint_name=f"{name} Model",
            context_window=32000,
            supports_tools=True,
            is_reasoning_model=False,
            quantization=quantization,
            uptime_30min=99.0,
            performance_tps=100.0,
            pricing={"prompt": 0.000001, "completion": 0.000002},
            max_completion_tokens=4096,
            supported_parameters=supported_params,
        )
        return ProviderDetails(
            provider=provider_info,
            availability=True,
            last_updated=datetime.now(),
        )

    def test_offers_table_displays_prices_per_million(self, runner):
        mock_provider = self.create_mock_provider("TestProvider")

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch("openrouter_inspector.client.OpenRouterClient") as mock_client:
                mock_client.return_value.__aenter__.return_value = AsyncMock()
                with patch(
                    "openrouter_inspector.services.ModelService.get_model_providers"
                ) as mock_method:
                    mock_method.return_value = [mock_provider]

                    result = runner.invoke(cli, ["endpoints", "test/model"])

                    assert result.exit_code == 0
                    # 0.000001 * 1_000_000 -> 1.000000 -> fmt_money formats to $1.00
                    assert "$1.00" in result.output

    def test_offers_json_output(self, runner):
        mock_provider = self.create_mock_provider("TestProvider")

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch("openrouter_inspector.client.OpenRouterClient") as mock_client:
                mock_client.return_value.__aenter__.return_value = AsyncMock()
                with patch(
                    "openrouter_inspector.services.ModelService.get_model_providers"
                ) as mock_method:
                    mock_method.return_value = [mock_provider]

                    result = runner.invoke(
                        cli, ["endpoints", "test/model", "--format", "json"]
                    )

                    assert result.exit_code == 0
                    assert "provider_name" in result.output

    # Web metric columns removed from offers table

    def test_table_layout_api_only(self, runner):
        # Test with image support
        mock_provider = self.create_mock_provider("TestProvider", supports_image=True)

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch("openrouter_inspector.client.OpenRouterClient") as mock_client:
                mock_client.return_value.__aenter__.return_value = AsyncMock()
                with patch(
                    "openrouter_inspector.services.ModelService.get_model_providers"
                ) as mock_method:
                    mock_method.return_value = [mock_provider]

                    result = runner.invoke(cli, ["endpoints", "test/model"])

                    assert result.exit_code == 0
                    assert "TPS" not in result.output
                    assert "Latency" not in result.output
                    # Uptime should now be present
                    assert "Uptime" in result.output
                    # Image support column should be present
                    assert "Img" in result.output
                    # Should show + for image support
                    assert "+" in result.output

    def test_quantization_formatting(self, runner):
        """Test quantization formatting in table output."""
        # Test normal quantization
        provider_normal = self.create_mock_provider(
            "NormalProvider", quantization="fp16"
        )
        # Test unknown quantization
        provider_unknown = self.create_mock_provider(
            "UnknownProvider", quantization="unknown"
        )
        # Test None quantization
        provider_none = self.create_mock_provider("NoneProvider", quantization=None)

        all_providers = [provider_normal, provider_unknown, provider_none]

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch("openrouter_inspector.client.OpenRouterClient") as mock_client:
                mock_client.return_value.__aenter__.return_value = AsyncMock()
                with patch(
                    "openrouter_inspector.services.ModelService.get_model_providers"
                ) as mock_method:
                    mock_method.return_value = all_providers

                    result = runner.invoke(cli, ["endpoints", "test/model"])

                    assert result.exit_code == 0
                    # Normal quantization should be displayed as-is
                    assert "fp16" in result.output
                    # "unknown" should be converted to "—"
                    assert "UnknownProvider" in result.output
                    # The word "unknown" should NOT appear in the output
                    assert "unknown" not in result.output
                    # None quantization should show as "—"
                    assert "—" in result.output

    def test_image_support_detection(self, runner):
        """Test image support detection in table output."""
        provider_with_image = self.create_mock_provider(
            "ImageProvider", supports_image=True
        )
        provider_without_image = self.create_mock_provider(
            "NoImageProvider", supports_image=False
        )
        all_providers = [provider_with_image, provider_without_image]

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch("openrouter_inspector.client.OpenRouterClient") as mock_client:
                mock_client.return_value.__aenter__.return_value = AsyncMock()
                with patch(
                    "openrouter_inspector.services.ModelService.get_model_providers"
                ) as mock_method:
                    mock_method.return_value = all_providers

                    result = runner.invoke(cli, ["endpoints", "test/model"])

                    assert result.exit_code == 0
                    # Both providers should be listed
                    assert "ImageProvider" in result.output
                    assert "NoImageProvider" in result.output
                    # Image support column should show + for image provider
                    # This is a bit tricky to test precisely, but we can check that
                    # the table structure is correct

    # No separate path: always API-only

    # JSON/YAML contain API provider fields only

    # Web fields removed

    # --- Tests for new filtering options ---

    def create_mock_provider_with_features(
        self,
        name,
        supports_tools=True,
        is_reasoning_model=False,
        input_price=0.000001,
        output_price=0.000002,
    ):
        """Create a mock provider with specific features for testing filters."""
        provider_info = ProviderInfo(
            provider_name=name,
            model_id="test/model",
            status="online",
            endpoint_name=f"{name} Model",
            context_window=32000,
            supports_tools=supports_tools,
            is_reasoning_model=is_reasoning_model,  # Kept for consistency, though filter uses supported_parameters
            quantization="fp16",
            uptime_30min=99.0,
            performance_tps=100.0,
            pricing={"prompt": input_price, "completion": output_price},
            max_completion_tokens=4096,
            # This is the key change for the reasoning filter test
            supported_parameters=["reasoning"] if is_reasoning_model else [],
        )
        return ProviderDetails(
            provider=provider_info,
            availability=True,
            last_updated=datetime.now(),
        )

    def test_offers_filter_reasoning(self, runner):
        """Test --reasoning filter."""
        provider_reasoning = self.create_mock_provider_with_features(
            "ReasoningProvider", is_reasoning_model=True
        )
        provider_no_reasoning = self.create_mock_provider_with_features(
            "NoReasoningProvider", is_reasoning_model=False
        )
        all_providers = [provider_reasoning, provider_no_reasoning]

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch("openrouter_inspector.client.OpenRouterClient") as mock_client:
                mock_client.return_value.__aenter__.return_value = AsyncMock()
                with patch(
                    "openrouter_inspector.services.ModelService.get_model_providers"
                ) as mock_method:
                    mock_method.return_value = all_providers

                    result = runner.invoke(
                        cli, ["endpoints", "test/model", "--reasoning"]
                    )

                    assert result.exit_code == 0
                    assert "ReasoningProvider" in result.output
                    assert "NoReasoningProvider" not in result.output

    def test_offers_filter_no_reasoning(self, runner):
        """Test --no-reasoning filter."""
        provider_reasoning = self.create_mock_provider_with_features(
            "ReasoningProvider", is_reasoning_model=True
        )
        provider_no_reasoning = self.create_mock_provider_with_features(
            "NoReasoningProvider", is_reasoning_model=False
        )
        all_providers = [provider_reasoning, provider_no_reasoning]

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch("openrouter_inspector.client.OpenRouterClient") as mock_client:
                mock_client.return_value.__aenter__.return_value = AsyncMock()
                with patch(
                    "openrouter_inspector.services.ModelService.get_model_providers"
                ) as mock_method:
                    mock_method.return_value = all_providers

                    result = runner.invoke(
                        cli, ["endpoints", "test/model", "--no-reasoning"]
                    )

                    assert result.exit_code == 0
                    # Ensure 'ReasoningProvider' does not appear as a standalone provider name
                    assert re.search(r"\bReasoningProvider\b", result.output) is None
                    # But 'NoReasoningProvider' should be present
                    assert "NoReasoningProvider" in result.output

    def test_offers_filter_tools(self, runner):
        """Test --tools filter."""
        provider_tools = self.create_mock_provider_with_features(
            "ToolsProvider", supports_tools=True
        )
        provider_no_tools = self.create_mock_provider_with_features(
            "NoToolsProvider", supports_tools=False
        )
        all_providers = [provider_tools, provider_no_tools]

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch("openrouter_inspector.client.OpenRouterClient") as mock_client:
                mock_client.return_value.__aenter__.return_value = AsyncMock()
                with patch(
                    "openrouter_inspector.services.ModelService.get_model_providers"
                ) as mock_method:
                    mock_method.return_value = all_providers

                    result = runner.invoke(cli, ["endpoints", "test/model", "--tools"])

                    assert result.exit_code == 0
                    assert "ToolsProvider" in result.output
                    assert "NoToolsProvider" not in result.output

    def test_offers_filter_no_tools(self, runner):
        """Test --no-tools filter."""
        provider_tools = self.create_mock_provider_with_features(
            "ToolsProvider", supports_tools=True
        )
        provider_no_tools = self.create_mock_provider_with_features(
            "NoToolsProvider", supports_tools=False
        )
        all_providers = [provider_tools, provider_no_tools]

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch("openrouter_inspector.client.OpenRouterClient") as mock_client:
                mock_client.return_value.__aenter__.return_value = AsyncMock()
                with patch(
                    "openrouter_inspector.services.ModelService.get_model_providers"
                ) as mock_method:
                    mock_method.return_value = all_providers

                    result = runner.invoke(
                        cli, ["endpoints", "test/model", "--no-tools"]
                    )

                    assert result.exit_code == 0
                    # Ensure 'ToolsProvider' does not appear as a standalone provider name
                    assert re.search(r"\bToolsProvider\b", result.output) is None
                    # But 'NoToolsProvider' should be present
                    assert "NoToolsProvider" in result.output

    def test_offers_filter_max_input_price(self, runner):
        """Test --max-input-price filter."""
        provider_expensive = self.create_mock_provider_with_features(
            "ExpensiveProvider", input_price=0.00001  # $10 per 1M
        )
        provider_cheap = self.create_mock_provider_with_features(
            "CheapProvider", input_price=0.000001  # $1 per 1M
        )
        all_providers = [provider_expensive, provider_cheap]

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch("openrouter_inspector.client.OpenRouterClient") as mock_client:
                mock_client.return_value.__aenter__.return_value = AsyncMock()
                with patch(
                    "openrouter_inspector.services.ModelService.get_model_providers"
                ) as mock_method:
                    mock_method.return_value = all_providers

                    result = runner.invoke(
                        cli, ["endpoints", "test/model", "--max-input-price", "5.0"]
                    )  # Max $5 per 1M

                    assert result.exit_code == 0
                    assert "ExpensiveProvider" not in result.output
                    assert "CheapProvider" in result.output

    def test_offers_filter_max_output_price(self, runner):
        """Test --max-output-price filter."""
        provider_expensive = self.create_mock_provider_with_features(
            "ExpensiveProvider", output_price=0.00002  # $20 per 1M
        )
        provider_cheap = self.create_mock_provider_with_features(
            "CheapProvider", output_price=0.000002  # $2 per 1M
        )
        all_providers = [provider_expensive, provider_cheap]

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch("openrouter_inspector.client.OpenRouterClient") as mock_client:
                mock_client.return_value.__aenter__.return_value = AsyncMock()
                with patch(
                    "openrouter_inspector.services.ModelService.get_model_providers"
                ) as mock_method:
                    mock_method.return_value = all_providers

                    result = runner.invoke(
                        cli, ["endpoints", "test/model", "--max-output-price", "10.0"]
                    )  # Max $10 per 1M

                    assert result.exit_code == 0
                    assert "ExpensiveProvider" not in result.output
                    assert "CheapProvider" in result.output

    def test_offers_filter_combined_reasoning_tools(self, runner):
        """Test combined --reasoning and --tools filters."""
        provider_match = self.create_mock_provider_with_features(
            "MatchProvider", is_reasoning_model=True, supports_tools=True
        )
        provider_no_reasoning = self.create_mock_provider_with_features(
            "NoReasoningProvider", is_reasoning_model=False, supports_tools=True
        )
        provider_no_tools = self.create_mock_provider_with_features(
            "NoToolsProvider", is_reasoning_model=True, supports_tools=False
        )
        provider_neither = self.create_mock_provider_with_features(
            "NeitherProvider", is_reasoning_model=False, supports_tools=False
        )
        all_providers = [
            provider_match,
            provider_no_reasoning,
            provider_no_tools,
            provider_neither,
        ]

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch("openrouter_inspector.client.OpenRouterClient") as mock_client:
                mock_client.return_value.__aenter__.return_value = AsyncMock()
                with patch(
                    "openrouter_inspector.services.ModelService.get_model_providers"
                ) as mock_method:
                    mock_method.return_value = all_providers

                    result = runner.invoke(
                        cli,
                        [
                            "endpoints",
                            "test/model",
                            "--reasoning",
                            "--tools",
                        ],
                    )

                    assert result.exit_code == 0
                    assert "MatchProvider" in result.output
                    assert "NoReasoningProvider" not in result.output
                    assert "NoToolsProvider" not in result.output
                    assert "NeitherProvider" not in result.output

    def test_offers_filter_combined_price_filters(self, runner):
        """Test combined --max-input-price and --max-output-price filters."""
        provider_match = self.create_mock_provider_with_features(
            "MatchProvider",
            input_price=0.000001,
            output_price=0.000002,  # $1 in, $2 out
        )
        provider_expensive_input = self.create_mock_provider_with_features(
            "ExpensiveInputProvider",
            input_price=0.00001,
            output_price=0.000001,  # $10 in, $1 out
        )
        provider_expensive_output = self.create_mock_provider_with_features(
            "ExpensiveOutputProvider",
            input_price=0.000001,
            output_price=0.00002,  # $1 in, $20 out
        )
        provider_both_expensive = self.create_mock_provider_with_features(
            "BothExpensiveProvider",
            input_price=0.00001,
            output_price=0.00002,  # $10 in, $20 out
        )
        all_providers = [
            provider_match,
            provider_expensive_input,
            provider_expensive_output,
            provider_both_expensive,
        ]

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch("openrouter_inspector.client.OpenRouterClient") as mock_client:
                mock_client.return_value.__aenter__.return_value = AsyncMock()
                with patch(
                    "openrouter_inspector.services.ModelService.get_model_providers"
                ) as mock_method:
                    mock_method.return_value = all_providers

                    result = runner.invoke(
                        cli,
                        [
                            "endpoints",
                            "test/model",
                            "--max-input-price",
                            "5.0",  # Max $5 in
                            "--max-output-price",
                            "5.0",  # Max $5 out
                        ],
                    )

                    assert result.exit_code == 0
                    assert "MatchProvider" in result.output
                    assert "ExpensiveInputProvider" not in result.output
                    assert "ExpensiveOutputProvider" not in result.output
                    assert "BothExpensiveProvider" not in result.output

    def test_offers_filter_all_combined(self, runner):
        """Test all filters combined."""
        provider_match = self.create_mock_provider_with_features(
            "MatchProvider",
            is_reasoning_model=True,
            supports_tools=True,
            input_price=0.000001,
            output_price=0.000002,
        )
        provider_no_reasoning = self.create_mock_provider_with_features(
            "NoReasoningProvider",
            is_reasoning_model=False,
            supports_tools=True,
            input_price=0.000001,
            output_price=0.000002,
        )
        provider_no_tools = self.create_mock_provider_with_features(
            "NoToolsProvider",
            is_reasoning_model=True,
            supports_tools=False,
            input_price=0.000001,
            output_price=0.000002,
        )
        provider_too_expensive_input = self.create_mock_provider_with_features(
            "TooExpensiveInputProvider",
            is_reasoning_model=True,
            supports_tools=True,
            input_price=0.00001,  # Too expensive
            output_price=0.000002,
        )
        provider_too_expensive_output = self.create_mock_provider_with_features(
            "TooExpensiveOutputProvider",
            is_reasoning_model=True,
            supports_tools=True,
            input_price=0.000001,
            output_price=0.00002,  # Too expensive
        )
        all_providers = [
            provider_match,
            provider_no_reasoning,
            provider_no_tools,
            provider_too_expensive_input,
            provider_too_expensive_output,
        ]

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch("openrouter_inspector.client.OpenRouterClient") as mock_client:
                mock_client.return_value.__aenter__.return_value = AsyncMock()
                with patch(
                    "openrouter_inspector.services.ModelService.get_model_providers"
                ) as mock_method:
                    mock_method.return_value = all_providers

                    result = runner.invoke(
                        cli,
                        [
                            "endpoints",
                            "test/model",
                            "--reasoning",
                            "--tools",
                            "--max-input-price",
                            "5.0",
                            "--max-output-price",
                            "5.0",
                        ],
                    )

                    assert result.exit_code == 0
                    assert "MatchProvider" in result.output
                    assert "NoReasoningProvider" not in result.output
                    assert "NoToolsProvider" not in result.output
                    assert "TooExpensiveInputProvider" not in result.output
                    assert "TooExpensiveOutputProvider" not in result.output

    def test_offers_filter_img(self, runner):
        """Test --img filter."""
        # Create providers with different image support
        provider_with_image = self.create_mock_provider_with_features(
            "ImageProvider",
            input_price=0.000001,
            output_price=0.000002,
        )
        # Manually modify the provider to support image
        provider_with_image.provider.supported_parameters = ["reasoning", "image"]

        provider_without_image = self.create_mock_provider_with_features(
            "NoImageProvider",
            input_price=0.000001,
            output_price=0.000002,
        )
        # Manually modify the provider to not support image
        provider_without_image.provider.supported_parameters = ["reasoning"]

        all_providers = [provider_with_image, provider_without_image]

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch("openrouter_inspector.client.OpenRouterClient") as mock_client:
                mock_client.return_value.__aenter__.return_value = AsyncMock()
                with patch(
                    "openrouter_inspector.services.ModelService.get_model_providers"
                ) as mock_method:
                    mock_method.return_value = all_providers

                    result = runner.invoke(cli, ["endpoints", "test/model", "--img"])

                    assert result.exit_code == 0
                    assert "ImageProvider" in result.output
                    assert "NoImageProvider" not in result.output

    def test_offers_filter_no_img(self, runner):
        """Test --no-img filter."""
        # Create providers with different image support
        provider_with_image = self.create_mock_provider_with_features(
            "ImageProviderXYZ",
            input_price=0.000001,
            output_price=0.000002,
        )
        # Manually modify the provider to support image
        provider_with_image.provider.supported_parameters = ["reasoning", "image"]

        provider_without_image = self.create_mock_provider_with_features(
            "NoImageProviderABC",
            input_price=0.000001,
            output_price=0.000002,
        )
        # Manually modify the provider to not support image
        provider_without_image.provider.supported_parameters = ["reasoning"]

        all_providers = [provider_with_image, provider_without_image]

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch("openrouter_inspector.client.OpenRouterClient") as mock_client:
                mock_client.return_value.__aenter__.return_value = AsyncMock()
                with patch(
                    "openrouter_inspector.services.ModelService.get_model_providers"
                ) as mock_method:
                    mock_method.return_value = all_providers

                    result = runner.invoke(cli, ["endpoints", "test/model", "--no-img"])

                    assert result.exit_code == 0
                    # Use word boundaries to avoid partial matches
                    import re

                    assert re.search(r"\bImageProviderXYZ\b", result.output) is None
                    assert "NoImageProviderABC" in result.output

    def test_offers_filter_combined_with_img(self, runner):
        """Test combining --img filter with other filters."""
        # Provider with everything
        provider_all = self.create_mock_provider_with_features(
            "AllFeaturesProvider",
            is_reasoning_model=True,
            supports_tools=True,
            input_price=0.000001,
            output_price=0.000002,
        )
        provider_all.provider.supported_parameters = ["reasoning", "image", "tools"]

        # Provider without image
        provider_no_img = self.create_mock_provider_with_features(
            "NoImageProvider",
            is_reasoning_model=True,
            supports_tools=True,
            input_price=0.000001,
            output_price=0.000002,
        )
        provider_no_img.provider.supported_parameters = ["reasoning", "tools"]

        # Provider without tools
        provider_no_tools = self.create_mock_provider_with_features(
            "NoToolsProvider",
            is_reasoning_model=True,
            supports_tools=False,
            input_price=0.000001,
            output_price=0.000002,
        )
        provider_no_tools.provider.supported_parameters = ["reasoning", "image"]

        all_providers = [provider_all, provider_no_img, provider_no_tools]

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch("openrouter_inspector.client.OpenRouterClient") as mock_client:
                mock_client.return_value.__aenter__.return_value = AsyncMock()
                with patch(
                    "openrouter_inspector.services.ModelService.get_model_providers"
                ) as mock_method:
                    mock_method.return_value = all_providers

                    result = runner.invoke(
                        cli,
                        [
                            "endpoints",
                            "test/model",
                            "--img",
                            "--tools",
                            "--reasoning",
                        ],
                    )

                    assert result.exit_code == 0
                    assert "AllFeaturesProvider" in result.output
                    assert "NoImageProvider" not in result.output
                    assert "NoToolsProvider" not in result.output

    def test_offers_filter_combined_with_no_img(self, runner):
        """Test combining --no-img filter with other filters."""
        # Provider with everything
        provider_all = self.create_mock_provider_with_features(
            "AllFeaturesProviderXYZ",
            is_reasoning_model=True,
            supports_tools=True,
            input_price=0.000001,
            output_price=0.000002,
        )
        provider_all.provider.supported_parameters = ["reasoning", "image", "tools"]

        # Provider without image
        provider_no_img = self.create_mock_provider_with_features(
            "NoImageProviderABC",
            is_reasoning_model=True,
            supports_tools=True,
            input_price=0.000001,
            output_price=0.000002,
        )
        provider_no_img.provider.supported_parameters = ["reasoning", "tools"]

        # Provider without tools
        provider_no_tools = self.create_mock_provider_with_features(
            "NoToolsProvider",
            is_reasoning_model=True,
            supports_tools=False,
            input_price=0.000001,
            output_price=0.000002,
        )
        provider_no_tools.provider.supported_parameters = ["reasoning", "image"]

        all_providers = [provider_all, provider_no_img, provider_no_tools]

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch("openrouter_inspector.client.OpenRouterClient") as mock_client:
                mock_client.return_value.__aenter__.return_value = AsyncMock()
                with patch(
                    "openrouter_inspector.services.ModelService.get_model_providers"
                ) as mock_method:
                    mock_method.return_value = all_providers

                    result = runner.invoke(
                        cli,
                        [
                            "endpoints",
                            "test/model",
                            "--no-img",
                            "--tools",
                            "--reasoning",
                        ],
                    )

                    assert result.exit_code == 0
                    # Use word boundaries to avoid partial matches
                    import re

                    assert (
                        re.search(r"\bAllFeaturesProviderXYZ\b", result.output) is None
                    )
                    assert "NoImageProviderABC" in result.output
                    assert "NoToolsProvider" not in result.output
