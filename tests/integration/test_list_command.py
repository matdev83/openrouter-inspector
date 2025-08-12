"""Integration tests for the list command with multiple search keywords."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from openrouter_inspector import cli as root_cli
from openrouter_inspector.models import ModelInfo


class TestListCommandMultipleFilters:
    """Test cases for list command with multiple search keywords (AND logic)."""

    @pytest.fixture
    def runner(self):
        """CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_models(self):
        """Mock models data for testing."""
        created_time = datetime(2024, 1, 1, 0, 0, 0)
        return [
            ModelInfo(
                id="meta/llama-3",
                name="Meta Llama 3",
                description="Meta's Llama 3 model",
                context_length=8192,
                pricing={"prompt": 0.000001, "completion": 0.000002},
                created=created_time,
            ),
            ModelInfo(
                id="meta/llama-3-free",
                name="Meta Llama 3 Free",
                description="Free version of Meta's Llama 3",
                context_length=8192,
                pricing={"prompt": 0.0, "completion": 0.0},
                created=created_time,
            ),
            ModelInfo(
                id="openai/gpt-4",
                name="GPT-4",
                description="OpenAI's GPT-4 model",
                context_length=8192,
                pricing={"prompt": 0.03, "completion": 0.06},
                created=created_time,
            ),
            ModelInfo(
                id="anthropic/claude-3",
                name="Claude 3",
                description="Anthropic's Claude 3 model",
                context_length=200000,
                pricing={"prompt": 0.015, "completion": 0.075},
                created=created_time,
            ),
        ]

    def test_list_single_filter(self, runner, mock_models, monkeypatch):
        """Test list command with single filter."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

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
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None

            # Mock the model service search_models method
            mock_model_service.search_models.return_value = mock_models
            mock_table_formatter.format_models.return_value = (
                "Meta Llama 3\nMeta Llama 3 Free"
            )

            result = runner.invoke(root_cli, ["list", "meta"])

            assert result.exit_code == 0
            assert "Meta Llama 3" in result.output
            assert "Meta Llama 3 Free" in result.output

    def test_list_multiple_filters_and_logic(self, runner, mock_models, monkeypatch):
        """Test list command with multiple filters using AND logic."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

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
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None

            mock_model_service.search_models.return_value = mock_models
            mock_table_formatter.format_models.return_value = "Meta Llama 3 Free"

            # Should match models containing BOTH "meta" AND "free"
            result = runner.invoke(root_cli, ["list", "meta", "free"])

            assert result.exit_code == 0
            assert "Meta Llama 3 Free" in result.output

    def test_list_multiple_filters_case_insensitive(
        self, runner, mock_models, monkeypatch
    ):
        """Test list command with multiple filters is case-insensitive."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        with patch("openrouter_inspector.client.OpenRouterClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get_models.return_value = mock_models

            # Should work with different cases
            result = runner.invoke(root_cli, ["list", "META", "FREE"])

            assert result.exit_code == 0
            assert "Meta Llama 3 Free" in result.output
            assert (
                "Meta Llama 3\n" not in result.output
            )  # Has "meta" but not "free" - check for line break to avoid substring match

    def test_list_multiple_filters_no_matches(self, runner, mock_models, monkeypatch):
        """Test list command with multiple filters that match nothing."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        with patch("openrouter_inspector.client.OpenRouterClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get_models.return_value = mock_models

            # Should match nothing (no model has both "nonexistent" and "xyz")
            result = runner.invoke(root_cli, ["list", "nonexistent", "xyz"])

            assert result.exit_code == 0
            # Should show empty table or no results message
            assert "OpenRouter Models" in result.output  # Table title still shown

    def test_list_multiple_filters_all_match_same_model(
        self, runner, mock_models, monkeypatch
    ):
        """Test list command where all filters match the same model."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        with patch("openrouter_inspector.client.OpenRouterClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get_models.return_value = mock_models

            # Both terms should match "Meta Llama 3 Free"
            result = runner.invoke(root_cli, ["list", "meta", "llama"])

            assert result.exit_code == 0
            assert "Meta Llama 3 Free" in result.output
            assert "Meta Llama 3" in result.output  # Also matches both terms
            assert "GPT-4" not in result.output  # Doesn't match either term

    def test_list_no_filters_shows_all_models(self, runner, mock_models, monkeypatch):
        """Test list command with no filters shows all models."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

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
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None

            mock_model_service.search_models.return_value = mock_models
            mock_table_formatter.format_models.return_value = (
                "Meta Llama 3\nMeta Llama 3 Free\nGPT-4\nClaude 3"
            )

            result = runner.invoke(root_cli, ["list"])

            assert result.exit_code == 0
            assert "Meta Llama 3" in result.output
            assert "GPT-4" in result.output
            assert "Claude 3" in result.output

    def test_list_with_providers_multiple_filters(
        self, runner, mock_models, monkeypatch
    ):
        """Test list command with --with-providers and multiple filters."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        with patch("openrouter_inspector.client.OpenRouterClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get_models.return_value = mock_models
            mock_client.get_model_providers.return_value = (
                []
            )  # No providers for simplicity

            result = runner.invoke(
                root_cli, ["list", "--with-providers", "meta", "free"]
            )

            assert result.exit_code == 0
            assert "Meta Llama 3 Free" in result.output
            assert "Providers" in result.output  # Should show providers column

    def test_list_table_output_format(self, runner, mock_models, monkeypatch):
        """Test that list command with multiple filters shows proper table format."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        with patch("openrouter_inspector.client.OpenRouterClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get_models.return_value = mock_models

            result = runner.invoke(root_cli, ["list", "meta", "free"])

            assert result.exit_code == 0

            # Check table structure
            assert "Name" in result.output
            assert "ID" in result.output
            assert "Context" in result.output
            assert "Input" in result.output
            assert "Output" in result.output

            # Check specific model with pricing
            assert "Meta Llama 3 Free" in result.output
            assert "meta/llama-3-free" in result.output
            assert "8K" in result.output  # Context formatting
            assert "$0.00" in result.output  # Free model pricing

    def test_list_json_output_with_multiple_filters(
        self, runner, mock_models, monkeypatch
    ):
        """Test list command with multiple filters and JSON output."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        with patch("openrouter_inspector.client.OpenRouterClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get_models.return_value = mock_models

            result = runner.invoke(
                root_cli, ["list", "--format", "json", "meta", "free"]
            )

            assert result.exit_code == 0
            assert "meta/llama-3-free" in result.output
            assert "Meta Llama 3 Free" in result.output
            assert (
                '"id": "meta/llama-3",' not in result.output
            )  # Should not be included - check for exact JSON field
