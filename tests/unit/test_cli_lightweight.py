"""CLI registration smoke test for ping command."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from openrouter_inspector.cli import cli
from openrouter_inspector.models import ModelInfo, ProviderDetails, ProviderInfo


def test_cli_has_ping_command_registered():
    assert "ping" in cli.commands


"""Unit tests for CLI lightweight mode functionality."""


class TestCliLightweightMode:
    """Test cases for CLI lightweight mode (--list flag)."""

    @pytest.fixture
    def runner(self):
        """CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def sample_models(self):
        """Sample model data."""
        return [
            ModelInfo(
                id="model1",
                name="Model One",
                description="First model for testing",
                context_length=8192,
                pricing={"prompt": 0.00001, "completion": 0.00002},
                created=datetime.now(),
            ),
            ModelInfo(
                id="model2",
                name="Model Two",
                description="Second model for testing",
                context_length=16384,
                pricing={"prompt": 0.00002, "completion": 0.00003},
                created=datetime.now(),
            ),
            ModelInfo(
                id="another-model",
                name="Another Model",
                description="Third model for testing",
                context_length=32768,
                pricing={"prompt": 0.00003, "completion": 0.00004},
                created=datetime.now(),
            ),
        ]

    def test_list_flag_basic(self, runner, sample_models):
        """Test basic --list functionality."""
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch(
                "openrouter_inspector.client.OpenRouterClient"
            ) as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value.__aenter__.return_value = mock_client
                mock_client.get_models.return_value = sample_models

                result = runner.invoke(cli, ["--list"])

                assert result.exit_code == 0
                assert "Model One" in result.output
                assert "Model Two" in result.output
                assert "Another Model" in result.output
                mock_client.get_models.assert_called_once()

    def test_list_with_sorting(self, runner, sample_models):
        """Test --list with sorting options."""
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch(
                "openrouter_inspector.client.OpenRouterClient"
            ) as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value.__aenter__.return_value = mock_client
                mock_client.get_models.return_value = sample_models

                # Test sorting by name
                result = runner.invoke(cli, ["--list", "--sort-by", "name"])

                assert result.exit_code == 0
                mock_client.get_models.assert_called_once()

                # Test sorting by context
                mock_client.reset_mock()
                result = runner.invoke(cli, ["--list", "--sort-by", "context"])

                assert result.exit_code == 0
                mock_client.get_models.assert_called_once()

    def test_list_with_descending_sort(self, runner, sample_models):
        """Test --list with descending sort order."""
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch(
                "openrouter_inspector.client.OpenRouterClient"
            ) as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value.__aenter__.return_value = mock_client
                mock_client.get_models.return_value = sample_models

                result = runner.invoke(cli, ["--list", "--sort-by", "name", "--desc"])

                assert result.exit_code == 0
                mock_client.get_models.assert_called_once()

    def test_list_json_format(self, runner, sample_models):
        """Test --list with JSON output format."""
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch(
                "openrouter_inspector.client.OpenRouterClient"
            ) as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value.__aenter__.return_value = mock_client
                mock_client.get_models.return_value = sample_models

                result = runner.invoke(cli, ["--list", "--format", "json"])

                assert result.exit_code == 0
                # Should be valid JSON output (check for array brackets)
                assert result.output.strip().startswith("[")
                assert result.output.strip().endswith("]")

    def test_list_with_providers_count(self, runner, sample_models):
        """Test --list with --with-providers flag."""
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch(
                "openrouter_inspector.client.OpenRouterClient"
            ) as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value.__aenter__.return_value = mock_client
                mock_client.get_models.return_value = [sample_models[0]]

                # Mock provider data
                provider_details = ProviderDetails(
                    provider=ProviderInfo(
                        provider_name="TestProvider",
                        model_id="model1",
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
                    ),
                    availability=True,
                    last_updated=datetime.now(),
                )
                mock_client.get_model_providers.return_value = [provider_details]

                result = runner.invoke(cli, ["--list", "--with-providers"])

                assert result.exit_code == 0
                assert "Providers" in result.output
                mock_client.get_models.assert_called_once()
                mock_client.get_model_providers.assert_called_once_with("model1")

    def test_list_with_providers_and_sorting(self, runner, sample_models):
        """Test --list with --with-providers and sorting by providers count."""
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch(
                "openrouter_inspector.client.OpenRouterClient"
            ) as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value.__aenter__.return_value = mock_client
                mock_client.get_models.return_value = [sample_models[0]]

                # Mock provider data
                provider_details = ProviderDetails(
                    provider=ProviderInfo(
                        provider_name="TestProvider",
                        model_id="model1",
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
                    ),
                    availability=True,
                    last_updated=datetime.now(),
                )
                mock_client.get_model_providers.return_value = [provider_details]

                result = runner.invoke(
                    cli, ["--list", "--with-providers", "--sort-by", "providers"]
                )

                assert result.exit_code == 0
                mock_client.get_models.assert_called_once()
                mock_client.get_model_providers.assert_called_once_with("model1")

    def test_list_with_tools_flag(self, runner, sample_models):
        """Test --list with --tools flag."""
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
                    mock_service.search_models.return_value = sample_models

                    result = runner.invoke(cli, ["--list", "--tools"])

                    assert result.exit_code == 0
                    # Verify that search_models was called with the correct filters
                    mock_service.search_models.assert_called_once()
                    call_args = mock_service.search_models.call_args
                    assert call_args[0][1].supports_tools is True

    def test_list_with_no_tools_flag(self, runner, sample_models):
        """Test --list with --no-tools flag."""
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
                    mock_service.search_models.return_value = sample_models

                    result = runner.invoke(cli, ["--list", "--no-tools"])

                    assert result.exit_code == 0
                    # Verify that search_models was called with the correct filters
                    mock_service.search_models.assert_called_once()
                    call_args = mock_service.search_models.call_args
                    assert call_args[0][1].supports_tools is False

    def test_list_with_reasoning_flag(self, runner, sample_models):
        """Test --list with --reasoning flag."""
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
                    mock_service.search_models.return_value = sample_models

                    result = runner.invoke(cli, ["--list", "--reasoning"])

                    assert result.exit_code == 0
                    call_args = mock_service.search_models.call_args
                    assert call_args[0][1].reasoning_only is True

    def test_list_with_no_reasoning_flag(self, runner, sample_models):
        """Test --list with --no-reasoning flag."""
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
                    mock_service.search_models.return_value = sample_models

                    result = runner.invoke(cli, ["--list", "--no-reasoning"])

                    assert result.exit_code == 0
                    call_args = mock_service.search_models.call_args
                    assert call_args[0][1].reasoning_only is False

    def test_list_with_img_flag(self, runner, sample_models):
        """Test --list with --img flag."""
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
                    mock_service.search_models.return_value = sample_models

                    result = runner.invoke(cli, ["--list", "--img"])

                    assert result.exit_code == 0
                    call_args = mock_service.search_models.call_args
                    assert call_args[0][1].supports_image_input is True

    def test_list_with_no_img_flag(self, runner, sample_models):
        """Test --list with --no-img flag."""
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
                    mock_service.search_models.return_value = sample_models

                    result = runner.invoke(cli, ["--list", "--no-img"])

                    assert result.exit_code == 0
                    call_args = mock_service.search_models.call_args
                    assert call_args[0][1].supports_image_input is False

    def test_list_with_tools_and_no_tools_error(self, runner):
        """Test that using both --tools and --no-tools flags raises an error."""
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            result = runner.invoke(cli, ["--list", "--tools", "--no-tools"])

            assert result.exit_code != 0
            assert "--tools and --no-tools cannot be used together" in result.output

    def test_list_with_reasoning_and_no_reasoning_error(self, runner):
        """Test that using both reasoning flags raises an error."""
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            result = runner.invoke(cli, ["--list", "--reasoning", "--no-reasoning"])

            assert result.exit_code != 0
            assert (
                "--reasoning and --no-reasoning cannot be used together"
                in result.output
            )

    def test_list_with_img_and_no_img_error(self, runner):
        """Test that using both image flags raises an error."""
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            result = runner.invoke(cli, ["--list", "--img", "--no-img"])

            assert result.exit_code != 0
            assert "--img and --no-img cannot be used together" in result.output
