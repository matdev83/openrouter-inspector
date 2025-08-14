"""Unit tests for CLI details command."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from openrouter_inspector.cli import cli
from openrouter_inspector.exceptions import ModelNotFoundError, ProviderNotFoundError
from openrouter_inspector.models import ProviderDetails, ProviderInfo


class TestCliDetails:
    """Test cases for CLI details command."""

    @pytest.fixture
    def runner(self):
        """CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def sample_provider(self):
        """Sample provider data for testing."""
        return ProviderDetails(
            provider=ProviderInfo(
                provider_name="TestProvider",
                model_id="test/model",
                endpoint_name="Test Model Endpoint",
                context_window=8192,
                supports_tools=True,
                is_reasoning_model=True,
                quantization="fp16",
                uptime_30min=99.5,
                pricing={"prompt": 0.00001, "completion": 0.00002},
                max_completion_tokens=4096,
                supported_parameters=["tools", "reasoning", "image"],
                status="active",
                performance_tps=100.0,
            ),
            availability=True,
            last_updated=datetime.now(),
        )

    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"})
    @patch("openrouter_inspector.utils.create_command_dependencies")
    def test_details_command_success(self, mock_deps, runner, sample_provider):
        """Test successful details command execution."""
        # Mock dependencies
        mock_client = AsyncMock()
        mock_model_service = AsyncMock()
        mock_table_formatter = AsyncMock()
        mock_json_formatter = AsyncMock()

        mock_deps.return_value = (
            mock_client,
            mock_model_service,
            mock_table_formatter,
            mock_json_formatter,
        )

        # Mock the endpoint handler methods
        with patch(
            "openrouter_inspector.commands.details_command.DetailsCommand.execute"
        ) as mock_execute:
            mock_execute.return_value = "Mocked details output"

            result = runner.invoke(cli, ["details", "test/model", "TestProvider"])

            assert result.exit_code == 0
            assert "Mocked details output" in result.output
            mock_execute.assert_called_once()

    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"})
    def test_details_command_missing_provider(self, runner):
        """Test details command with missing provider name."""
        result = runner.invoke(cli, ["details", "test/model"])

        assert result.exit_code != 0
        assert "Provider name is required" in result.output

    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"})
    def test_details_command_shorthand_syntax(self, runner):
        """Test details command with model@provider shorthand syntax."""
        with patch(
            "openrouter_inspector.utils.create_command_dependencies"
        ) as mock_deps:
            mock_client = AsyncMock()
            mock_model_service = AsyncMock()
            mock_table_formatter = AsyncMock()
            mock_json_formatter = AsyncMock()

            mock_deps.return_value = (
                mock_client,
                mock_model_service,
                mock_table_formatter,
                mock_json_formatter,
            )

            with patch(
                "openrouter_inspector.commands.details_command.DetailsCommand.execute"
            ) as mock_execute:
                mock_execute.return_value = "Mocked details output"

                result = runner.invoke(cli, ["details", "test/model@TestProvider"])

                assert result.exit_code == 0
                mock_execute.assert_called_once()

    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"})
    @patch("openrouter_inspector.utils.create_command_dependencies")
    def test_details_command_model_not_found(self, mock_deps, runner):
        """Test details command with non-existent model."""
        # Mock dependencies
        mock_client = AsyncMock()
        mock_model_service = AsyncMock()
        mock_table_formatter = AsyncMock()
        mock_json_formatter = AsyncMock()

        mock_deps.return_value = (
            mock_client,
            mock_model_service,
            mock_table_formatter,
            mock_json_formatter,
        )

        # Mock the command to raise ModelNotFoundError
        with patch(
            "openrouter_inspector.commands.details_command.DetailsCommand.execute"
        ) as mock_execute:
            mock_execute.side_effect = ModelNotFoundError(
                "nonexistent-model", "No providers found for model 'nonexistent-model'"
            )

            result = runner.invoke(
                cli, ["details", "nonexistent-model", "SomeProvider"]
            )

            assert result.exit_code != 0
            assert "No providers found for model 'nonexistent-model'" in result.output

    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"})
    @patch("openrouter_inspector.utils.create_command_dependencies")
    def test_details_command_provider_not_found(self, mock_deps, runner):
        """Test details command with non-existent provider."""
        # Mock dependencies
        mock_client = AsyncMock()
        mock_model_service = AsyncMock()
        mock_table_formatter = AsyncMock()
        mock_json_formatter = AsyncMock()

        mock_deps.return_value = (
            mock_client,
            mock_model_service,
            mock_table_formatter,
            mock_json_formatter,
        )

        # Mock the command to raise ProviderNotFoundError
        with patch(
            "openrouter_inspector.commands.details_command.DetailsCommand.execute"
        ) as mock_execute:
            mock_execute.side_effect = ProviderNotFoundError(
                model_id="test/model",
                provider_name="WrongProvider",
                available_providers=["CorrectProvider", "AnotherProvider"],
            )

            result = runner.invoke(cli, ["details", "test/model", "WrongProvider"])

            assert result.exit_code != 0
            assert (
                "Provider 'WrongProvider' not found for model 'test/model'"
                in result.output
            )
            assert (
                "Available providers: CorrectProvider, AnotherProvider" in result.output
            )

    def test_details_command_missing_api_key(self, runner):
        """Test details command without API key."""
        # Clear any existing API key from environment
        import os

        old_key = os.environ.pop("OPENROUTER_API_KEY", None)
        try:
            result = runner.invoke(cli, ["details", "test/model", "TestProvider"])

            assert result.exit_code != 0
            assert "OPENROUTER_API_KEY is required" in result.output
        finally:
            # Restore the old key if it existed
            if old_key:
                os.environ["OPENROUTER_API_KEY"] = old_key

    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"})
    @patch("openrouter_inspector.utils.create_command_dependencies")
    def test_details_command_with_hints(self, mock_deps, runner, sample_provider):
        """Test details command shows hints by default."""
        # Mock dependencies
        mock_client = AsyncMock()
        mock_service = AsyncMock()
        mock_table_formatter = MagicMock()
        mock_json_formatter = MagicMock()

        mock_deps.return_value = (
            mock_client,
            mock_service,
            mock_table_formatter,
            mock_json_formatter,
        )

        # Mock the async context manager
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        # Mock the execute method directly
        with patch(
            "openrouter_inspector.commands.details_command.DetailsCommand.execute"
        ) as mock_execute:
            mock_execute.return_value = "mocked details with hints"

            result = runner.invoke(cli, ["details", "test/model", "TestProvider"])

            assert result.exit_code == 0
            assert "mocked details with hints" in result.output
            mock_execute.assert_called_once()

    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"})
    @patch("openrouter_inspector.utils.create_command_dependencies")
    def test_details_command_with_no_hints(self, mock_deps, runner, sample_provider):
        """Test details command with --no-hints flag."""
        # Mock dependencies
        mock_client = AsyncMock()
        mock_service = AsyncMock()
        mock_table_formatter = MagicMock()
        mock_json_formatter = MagicMock()

        mock_deps.return_value = (
            mock_client,
            mock_service,
            mock_table_formatter,
            mock_json_formatter,
        )

        # Mock the async context manager
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        # Mock the execute method directly
        with patch(
            "openrouter_inspector.commands.details_command.DetailsCommand.execute"
        ) as mock_execute:
            mock_execute.return_value = "mocked details without hints"

            result = runner.invoke(
                cli, ["details", "test/model", "TestProvider", "--no-hints"]
            )

            assert result.exit_code == 0
            assert "mocked details without hints" in result.output
            # Verify that no_hints=True is passed to the execute method
            mock_execute.assert_called_once()
            call_args = mock_execute.call_args
            assert call_args[1]["no_hints"] is True
