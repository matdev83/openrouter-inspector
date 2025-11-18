"""Tests for the list command caching functionality."""

import tempfile
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from openrouter_inspector.commands.list_command import ListCommand
from openrouter_inspector.models import ModelInfo


class TestListCommandCache:
    """Test cases for ListCommand caching functionality."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create a temporary directory for cache testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for ListCommand."""
        client = AsyncMock()
        model_service = AsyncMock()
        table_formatter = MagicMock()
        json_formatter = MagicMock()
        return client, model_service, table_formatter, json_formatter

    @pytest.fixture
    def sample_models(self):
        """Sample models for testing."""
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
                id="openai/gpt-4",
                name="GPT-4",
                description="OpenAI's GPT-4 model",
                context_length=8192,
                pricing={"prompt": 0.03, "completion": 0.06},
                created=created_time,
            ),
        ]

    @pytest.fixture
    def list_command(self, mock_dependencies, temp_cache_dir):
        """Create a ListCommand instance with mocked dependencies."""
        client, model_service, table_formatter, json_formatter = mock_dependencies

        with patch(
            "openrouter_inspector.commands.list_command.ListCommandCache"
        ) as mock_cache_class:
            from openrouter_inspector.cache import ListCommandCache

            mock_cache_class.return_value = ListCommandCache(cache_dir=temp_cache_dir)

            command = ListCommand(
                client, model_service, table_formatter, json_formatter
            )
            return command

    @pytest.mark.asyncio
    async def test_first_run_no_cache(
        self, list_command, mock_dependencies, sample_models
    ):
        """Test first run with no existing cache."""
        client, model_service, table_formatter, json_formatter = mock_dependencies

        # Mock model handler
        list_command.model_handler.list_models = AsyncMock(return_value=sample_models)
        table_formatter.format_models.return_value = "formatted output"

        result = await list_command.execute(filters=("test",), no_hints=True)

        # Should call format_models with empty new_models and pricing_changes
        table_formatter.format_models.assert_called_once()
        call_args = table_formatter.format_models.call_args
        assert call_args[1]["pricing_changes"] == []
        assert call_args[1]["new_models"] == []
        assert result == "formatted output"

    @pytest.mark.asyncio
    async def test_second_run_with_new_models(
        self, list_command, mock_dependencies, sample_models
    ):
        """Test second run detecting new models."""
        client, model_service, table_formatter, json_formatter = mock_dependencies
        created_time = datetime(2024, 1, 1, 0, 0, 0)

        # First run with subset of models
        list_command.model_handler.list_models = AsyncMock(
            return_value=sample_models[:1]
        )
        table_formatter.format_models.return_value = "first run output"

        await list_command.execute(filters=("test",))

        # Second run with additional model
        new_model = ModelInfo(
            id="anthropic/claude-3",
            name="Claude 3",
            description="Anthropic's Claude 3 model",
            context_length=200000,
            pricing={"prompt": 0.015, "completion": 0.075},
            created=created_time,
        )
        all_models = sample_models + [new_model]

        list_command.model_handler.list_models = AsyncMock(return_value=all_models)
        table_formatter.format_models.return_value = "second run output"

        await list_command.execute(filters=("test",))

        # Should detect new models
        assert table_formatter.format_models.call_count == 2
        second_call_args = table_formatter.format_models.call_args
        new_models = second_call_args[1]["new_models"]
        assert len(new_models) == 2  # gpt-4 and claude-3 are new
        assert any(model.id == "openai/gpt-4" for model in new_models)
        assert any(model.id == "anthropic/claude-3" for model in new_models)

    @pytest.mark.asyncio
    async def test_pricing_changes_detection(
        self, list_command, mock_dependencies, sample_models
    ):
        """Test detection of pricing changes."""
        client, model_service, table_formatter, json_formatter = mock_dependencies

        # First run
        list_command.model_handler.list_models = AsyncMock(return_value=sample_models)
        table_formatter.format_models.return_value = "first run output"

        await list_command.execute(filters=("test",))

        # Second run with modified pricing
        modified_models = []
        for model in sample_models:
            model_dict = model.model_dump()
            if model.id == "meta/llama-3":
                model_dict["pricing"]["prompt"] = 0.000002  # Changed
                model_dict["pricing"]["completion"] = 0.000003  # Changed
            modified_models.append(ModelInfo(**model_dict))

        list_command.model_handler.list_models = AsyncMock(return_value=modified_models)
        table_formatter.format_models.return_value = "second run output"

        await list_command.execute(filters=("test",))

        # Should detect pricing changes
        assert table_formatter.format_models.call_count == 2
        second_call_args = table_formatter.format_models.call_args
        pricing_changes = second_call_args[1]["pricing_changes"]
        assert len(pricing_changes) == 2  # prompt and completion changed

        changes_dict = {
            (change[0], change[1]): (change[2], change[3]) for change in pricing_changes
        }
        assert ("meta/llama-3", "prompt") in changes_dict
        assert ("meta/llama-3", "completion") in changes_dict

    @pytest.mark.asyncio
    async def test_different_parameters_separate_cache(
        self, list_command, mock_dependencies, sample_models
    ):
        """Test that different parameters create separate cache entries."""
        client, model_service, table_formatter, json_formatter = mock_dependencies

        # First run with one set of parameters
        list_command.model_handler.list_models = AsyncMock(
            return_value=sample_models[:1]
        )
        table_formatter.format_models.return_value = "output1"

        await list_command.execute(filters=("test1",), min_context=1000)

        # Second run with different parameters
        list_command.model_handler.list_models = AsyncMock(
            return_value=sample_models[1:]
        )
        table_formatter.format_models.return_value = "output2"

        await list_command.execute(filters=("test2",), min_context=2000)

        # Third run with first parameters again - should use first cache
        list_command.model_handler.list_models = AsyncMock(return_value=sample_models)
        table_formatter.format_models.return_value = "output3"

        await list_command.execute(filters=("test1",), min_context=1000)

        # Should detect new model for first parameter set
        assert table_formatter.format_models.call_count == 3
        third_call_args = table_formatter.format_models.call_args
        new_models = third_call_args[1]["new_models"]
        assert len(new_models) == 1  # gpt-4 is new for this parameter set
        assert new_models[0].id == "openai/gpt-4"

    @pytest.mark.asyncio
    async def test_with_providers_caching(
        self, list_command, mock_dependencies, sample_models
    ):
        """Test caching works with provider counts."""
        client, model_service, table_formatter, json_formatter = mock_dependencies

        # Mock provider handler
        list_command.provider_handler.get_active_provider_counts = AsyncMock(
            return_value=[(model, 3) for model in sample_models]
        )
        list_command.provider_handler.extract_models_and_counts = MagicMock(
            return_value=(sample_models, [3, 3])
        )

        # First run
        list_command.model_handler.list_models = AsyncMock(
            return_value=sample_models[:1]
        )
        table_formatter.format_models.return_value = "first run output"

        await list_command.execute(filters=("test",), with_providers=True)

        # Second run with additional model
        list_command.model_handler.list_models = AsyncMock(return_value=sample_models)
        table_formatter.format_models.return_value = "second run output"

        await list_command.execute(filters=("test",), with_providers=True)

        # Should detect new model and pass provider info
        assert table_formatter.format_models.call_count == 2
        second_call_args = table_formatter.format_models.call_args
        assert second_call_args[1]["with_providers"] is True
        assert "provider_counts" in second_call_args[1]
        new_models = second_call_args[1]["new_models"]
        assert len(new_models) == 1
        assert new_models[0].id == "openai/gpt-4"

    @pytest.mark.asyncio
    async def test_json_output_no_comparison(
        self, list_command, mock_dependencies, sample_models
    ):
        """Test that JSON output doesn't include comparison data."""
        client, model_service, table_formatter, json_formatter = mock_dependencies

        # Mock _format_output once for both calls
        format_output_mock = MagicMock(side_effect=["json output", "json output 2"])
        list_command._format_output = format_output_mock

        # First run
        list_command.model_handler.list_models = AsyncMock(
            return_value=sample_models[:1]
        )

        await list_command.execute(filters=("test",), output_format="json")

        # Second run with additional model
        list_command.model_handler.list_models = AsyncMock(return_value=sample_models)

        result = await list_command.execute(filters=("test",), output_format="json")

        # Should use _format_output for JSON, not table formatter with comparison
        assert format_output_mock.call_count == 2
        assert result == "json output 2"

    @pytest.mark.asyncio
    async def test_cache_storage_called(
        self, list_command, mock_dependencies, sample_models
    ):
        """Test that cache storage is called after each run."""
        client, model_service, table_formatter, json_formatter = mock_dependencies

        # Mock the cache methods
        list_command.cache.store_response = MagicMock()
        list_command.cache.get_previous_response = MagicMock(return_value=None)
        list_command.cache.compare_responses = MagicMock(return_value=([], []))

        list_command.model_handler.list_models = AsyncMock(return_value=sample_models)
        table_formatter.format_models.return_value = "output"

        await list_command.execute(filters=("test",), min_context=1000)

        # Verify cache methods were called
        list_command.cache.get_previous_response.assert_called_once()
        list_command.cache.store_response.assert_called_once_with(
            sample_models,
            filters=("test",),
            min_context=1000,
            tools=None,
            no_tools=None,
            reasoning=None,
            no_reasoning=None,
            img=None,
            no_img=None,
            output_format="table",
            with_providers=False,
            sort_by="id",
            desc=False,
        )
