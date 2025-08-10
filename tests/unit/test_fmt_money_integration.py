"""Test integration of fmt_money function in CLI output formatting."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from openrouter_inspector.cli import cli
from openrouter_inspector.models import ProviderDetails, ProviderInfo


class TestFmtMoneyIntegration:
    """Test that fmt_money is properly integrated into the offers table."""

    @pytest.fixture
    def runner(self):
        """CLI test runner."""
        return CliRunner()

    def create_mock_provider_with_prices(
        self, name, input_price=12.3456789, output_price=5.567891
    ):
        """Create a mock provider with specific prices to test formatting.

        These prices will be converted to per-million format:
        - input_price (per token) * 1M = input_price_per_million
        - output_price (per token) * 1M = output_price_per_million

        Then formatted with fmt_money to 2 decimal places.
        """
        provider_info = ProviderInfo(
            provider_name=name,
            model_id="test/model",
            status="online",
            endpoint_name=f"{name} Model",
            context_window=32000,
            supports_tools=True,
            is_reasoning_model=False,
            quantization="fp16",
            uptime_30min=99.0,
            performance_tps=100.0,
            pricing={
                "prompt": input_price / 1_000_000.0,
                "completion": output_price / 1_000_000.0,
            },
            max_completion_tokens=4096,
            supported_parameters=[],
        )
        return ProviderDetails(
            provider=provider_info,
            availability=True,
            last_updated=datetime.now(),
        )

    def test_fmt_money_used_for_input_column(self, runner):
        """Test that fmt_money formats Input column prices correctly."""
        # Price will be 12.3456789 per million tokens, formatted to "12.35"
        mock_provider = self.create_mock_provider_with_prices(
            "TestProvider", input_price=12.3456789
        )

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch("openrouter_inspector.client.OpenRouterClient") as mock_client:
                mock_client.return_value.__aenter__.return_value = AsyncMock()
                with patch(
                    "openrouter_inspector.services.ModelService.get_model_providers"
                ) as mock_method:
                    mock_method.return_value = [mock_provider]

                    result = runner.invoke(cli, ["endpoints", "test/model"])

                    assert result.exit_code == 0
                    # Should be formatted to 2 decimal places: $12.35
                    assert "$12.35" in result.output
                    # Should NOT contain the raw unformatted value
                    assert "12.3456789" not in result.output

    def test_fmt_money_used_for_output_column(self, runner):
        """Test that fmt_money formats Output column prices correctly."""
        # Price will be 5.567891 per million tokens, formatted to "5.57"
        mock_provider = self.create_mock_provider_with_prices(
            "TestProvider", output_price=5.567891
        )

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch("openrouter_inspector.client.OpenRouterClient") as mock_client:
                mock_client.return_value.__aenter__.return_value = AsyncMock()
                with patch(
                    "openrouter_inspector.services.ModelService.get_model_providers"
                ) as mock_method:
                    mock_method.return_value = [mock_provider]

                    result = runner.invoke(cli, ["endpoints", "test/model"])

                    assert result.exit_code == 0
                    # Should be formatted to 2 decimal places: $5.57
                    assert "$5.57" in result.output
                    # Should NOT contain the raw unformatted value
                    assert "5.567891" not in result.output

    def test_fmt_money_handles_rounding(self, runner):
        """Test that fmt_money properly rounds to 2 decimal places."""
        # Input: 12.345 -> should round to 12.35 (round up)
        # Output: 12.344 -> should round to 12.34 (round down)
        mock_provider = self.create_mock_provider_with_prices(
            "RoundingProvider", input_price=12.345, output_price=12.344
        )

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch("openrouter_inspector.client.OpenRouterClient") as mock_client:
                mock_client.return_value.__aenter__.return_value = AsyncMock()
                with patch(
                    "openrouter_inspector.services.ModelService.get_model_providers"
                ) as mock_method:
                    mock_method.return_value = [mock_provider]

                    result = runner.invoke(cli, ["endpoints", "test/model"])

                    assert result.exit_code == 0
                    assert "$12.35" in result.output  # Input rounded up
                    assert "$12.34" in result.output  # Output rounded down

    def test_fmt_money_handles_integers(self, runner):
        """Test that fmt_money formats integer prices correctly with .00."""
        mock_provider = self.create_mock_provider_with_prices(
            "IntegerProvider", input_price=10, output_price=5
        )

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch("openrouter_inspector.client.OpenRouterClient") as mock_client:
                mock_client.return_value.__aenter__.return_value = AsyncMock()
                with patch(
                    "openrouter_inspector.services.ModelService.get_model_providers"
                ) as mock_method:
                    mock_method.return_value = [mock_provider]

                    result = runner.invoke(cli, ["endpoints", "test/model"])

                    assert result.exit_code == 0
                    assert "$10.00" in result.output  # Input formatted with .00
                    assert "$5.00" in result.output  # Output formatted with .00

    def test_fmt_money_handles_none_prices(self, runner):
        """Test that missing prices are handled correctly with em dash."""
        provider_info = ProviderInfo(
            provider_name="NoPriceProvider",
            model_id="test/model",
            status="online",
            endpoint_name="No Price Model",
            context_window=32000,
            supports_tools=True,
            is_reasoning_model=False,
            quantization="fp16",
            uptime_30min=99.0,
            performance_tps=100.0,
            pricing={},  # Empty pricing dictionary - no pricing information
            max_completion_tokens=4096,
            supported_parameters=[],
        )
        mock_provider = ProviderDetails(
            provider=provider_info,
            availability=True,
            last_updated=datetime.now(),
        )

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch("openrouter_inspector.client.OpenRouterClient") as mock_client:
                mock_client.return_value.__aenter__.return_value = AsyncMock()
                with patch(
                    "openrouter_inspector.services.ModelService.get_model_providers"
                ) as mock_method:
                    mock_method.return_value = [mock_provider]

                    result = runner.invoke(cli, ["endpoints", "test/model"])

                    assert result.exit_code == 0
                    # Should show em dashes for both Input and Output columns
                    assert "—" in result.output

    def test_all_price_cells_match_two_decimal_format(self, runner):
        """Test that every price cell in CLI output matches 2-decimal format regex.

        This test validates that all monetary values displayed in the CLI output
        match the pattern r"\b\\d+\\.\\d{2}\b" (digits followed by exactly 2 decimal places).
        """
        import re

        # Create providers with various price patterns to test comprehensive formatting
        providers = [
            self.create_mock_provider_with_prices(
                "Provider1", input_price=1.2345, output_price=2.6789
            ),
            self.create_mock_provider_with_prices(
                "Provider2", input_price=10, output_price=5.0
            ),
            self.create_mock_provider_with_prices(
                "Provider3", input_price=123.456789, output_price=0.999
            ),
        ]

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch("openrouter_inspector.client.OpenRouterClient") as mock_client:
                mock_client.return_value.__aenter__.return_value = AsyncMock()
                with patch(
                    "openrouter_inspector.services.ModelService.get_model_providers"
                ) as mock_method:
                    mock_method.return_value = providers

                    result = runner.invoke(cli, ["endpoints", "test/model"])

                    assert result.exit_code == 0

                    # Find all price values in the output using comprehensive regex
                    # Look for dollar signs followed by digits and exactly 2 decimal places
                    price_pattern = r"\$\d+\.\d{2}\b"
                    price_matches = re.findall(price_pattern, result.output)

                    # Should find multiple price matches (input and output for each provider)
                    assert (
                        len(price_matches) >= 6
                    ), f"Expected at least 6 prices, found: {price_matches}"

                    # Every price should match the 2-decimal format
                    numeric_pattern = r"\b\d+\.\d{2}\b"
                    for price_match in price_matches:
                        # Extract just the numeric part (without $)
                        numeric_part = price_match[1:]  # Remove $ prefix
                        assert re.match(
                            numeric_pattern, numeric_part
                        ), f"Price {price_match} doesn't match 2-decimal format"

                    # Verify specific expected values are formatted correctly
                    assert "$1.23" in result.output  # 1.2345 -> $1.23
                    assert "$2.68" in result.output  # 2.6789 -> $2.68
                    assert "$10.00" in result.output  # 10 -> $10.00
                    assert "$5.00" in result.output  # 5.0 -> $5.00
                    assert "$123.46" in result.output  # 123.456789 -> $123.46
                    assert "$1.00" in result.output  # 0.999 -> $1.00

                    # Ensure no prices with more than 2 decimal places exist
                    invalid_pattern = r"\$\d+\.\d{3,}"
                    invalid_matches = re.findall(invalid_pattern, result.output)
                    assert (
                        len(invalid_matches) == 0
                    ), f"Found prices with more than 2 decimals: {invalid_matches}"
