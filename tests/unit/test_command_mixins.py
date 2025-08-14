"""Tests for command mixins."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from openrouter_inspector.commands.base_command import BaseCommand
from openrouter_inspector.commands.mixins import HintsMixin


class MockCommand(HintsMixin, BaseCommand):
    """Mock command for testing the HintsMixin."""

    async def execute(self, *args, **kwargs):
        """Mock execute method."""
        return "test output"


class TestHintsMixin:
    """Test cases for HintsMixin."""

    @pytest.fixture
    def test_command(self):
        """Create a test command with mocked dependencies."""
        mock_client = AsyncMock()
        mock_service = AsyncMock()
        mock_table_formatter = MagicMock()
        mock_json_formatter = MagicMock()

        return MockCommand(
            mock_client, mock_service, mock_table_formatter, mock_json_formatter
        )

    def test_supports_hints(self, test_command):
        """Test that the mixin correctly identifies hint support."""
        # MockCommand -> "mock" command name
        assert (
            test_command.supports_hints() is False
        )  # No provider registered for "mock"

    def test_get_hint_context(self, test_command):
        """Test hint context generation."""
        context = test_command.get_hint_context(
            model_id="test/model",
            provider_name="TestProvider",
            example_model_id="example/model",
        )

        assert context.command_name == "mock"
        assert context.model_id == "test/model"
        assert context.provider_name == "TestProvider"
        assert context.example_model_id == "example/model"

    def test_format_output_with_hints_disabled(self, test_command):
        """Test output formatting with hints disabled."""
        content = "test content"

        result = test_command._format_output_with_hints(content, show_hints=False)

        assert result == content

    def test_format_output_with_hints_no_support(self, test_command):
        """Test output formatting when command doesn't support hints."""
        content = "test content"

        result = test_command._format_output_with_hints(content, show_hints=True)

        # Should return original content since "mock" command has no hint provider
        assert result == content

    def test_format_output_with_hints_enabled(self):
        """Test output formatting with hints enabled for supported command."""

        mock_client = AsyncMock()
        mock_service = AsyncMock()
        mock_table_formatter = MagicMock()
        mock_json_formatter = MagicMock()

        # Create a real command that supports hints
        from openrouter_inspector.commands.endpoints_command import EndpointsCommand

        command = EndpointsCommand(
            mock_client, mock_service, mock_table_formatter, mock_json_formatter
        )

        # Create mock provider data for the endpoints hint provider
        from datetime import datetime

        from openrouter_inspector.models import ProviderDetails, ProviderInfo

        provider_info = ProviderInfo(
            provider_name="TestProvider",
            model_id="test/model",
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
        )
        provider_data = [
            ProviderDetails(
                provider=provider_info,
                availability=True,
                last_updated=datetime.now(),
            )
        ]

        content = "test content"

        result = command._format_output_with_hints(
            content, show_hints=True, model_id="test/model", data=provider_data
        )

        # Should include hints section
        assert "💡 Quick Commands:" in result
        assert content in result
