from datetime import datetime
from unittest.mock import AsyncMock, patch

from click.testing import CliRunner

from openrouter_inspector.cli import cli as root_cli


def test_check_help():
    runner = CliRunner()
    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
        result = runner.invoke(root_cli, ["check", "--help"])
    assert result.exit_code == 0
    # Web-related check options removed


def test_check_disabled_when_offline():
    runner = CliRunner()
    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
        with patch("openrouter_inspector.client.OpenRouterClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            from openrouter_inspector.models import ProviderDetails, ProviderInfo

            provider = ProviderInfo(
                provider_name="DeepInfra",
                model_id="author/model",
                status="offline",
                endpoint_name="Default",
                context_window=32000,
                supports_tools=False,
                is_reasoning_model=False,
                quantization=None,
                uptime_30min=99.0,
                pricing={},
            )
            mock_instance.get_model_providers.return_value = [
                ProviderDetails(
                    provider=provider, availability=False, last_updated=datetime.now()
                )
            ]
            result = runner.invoke(
                root_cli, ["check", "author/model", "DeepInfra", "Default"]
            )
    assert result.exit_code == 0
    assert result.output.strip() == "Disabled"


def test_check_functional_when_online():
    runner = CliRunner()
    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
        with patch("openrouter_inspector.client.OpenRouterClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            from openrouter_inspector.models import ProviderDetails, ProviderInfo

            provider = ProviderInfo(
                provider_name="DeepInfra",
                model_id="author/model",
                status="online",
                endpoint_name="Default",
                context_window=32000,
                supports_tools=False,
                is_reasoning_model=False,
                quantization=None,
                uptime_30min=99.0,
                pricing={},
            )
            mock_instance.get_model_providers.return_value = [
                ProviderDetails(
                    provider=provider, availability=True, last_updated=datetime.now()
                )
            ]
            result = runner.invoke(
                root_cli, ["check", "author/model", "DeepInfra", "Default"]
            )
    assert result.exit_code == 0
    assert result.output.strip() == "Functional"


    # Web-metric-based checks removed
