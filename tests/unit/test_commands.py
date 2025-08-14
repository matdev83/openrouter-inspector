"""Unit tests for command classes."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from openrouter_inspector.commands import (
    CheckCommand,
    DetailsCommand,
    EndpointsCommand,
    ListCommand,
)
from openrouter_inspector.models import (
    ModelInfo,
    ProviderDetails,
    ProviderInfo,
)


class TestListCommand:
    """Test cases for ListCommand."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for ListCommand."""
        return {
            "client": AsyncMock(),
            "model_service": AsyncMock(),
            "table_formatter": MagicMock(),
            "json_formatter": MagicMock(),
        }

    @pytest.fixture
    def list_command(self, mock_dependencies):
        """Create a ListCommand with mocked dependencies."""
        return ListCommand(
            mock_dependencies["client"],
            mock_dependencies["model_service"],
            mock_dependencies["table_formatter"],
            mock_dependencies["json_formatter"],
        )

    @pytest.fixture
    def sample_models(self):
        """Create sample ModelInfo objects for testing."""
        return [
            ModelInfo(
                id="meta/llama-3",
                name="Meta Llama 3",
                description="Meta's Llama 3 model",
                context_length=8192,
                pricing={"prompt": 0.00001, "completion": 0.00002},
                created=datetime(2024, 1, 1),
            )
        ]

    @pytest.mark.asyncio
    async def test_execute_basic(self, list_command, sample_models):
        """Test basic list command execution."""
        list_command.model_handler.list_models = AsyncMock(return_value=sample_models)
        list_command.table_formatter.format_models = MagicMock(
            return_value="formatted output"
        )

        result = await list_command.execute()

        # Should include the base output plus hints
        assert "formatted output" in result
        assert "💡 Quick Commands:" in result
        assert "openrouter-inspector endpoints meta/llama-3" in result
        list_command.model_handler.list_models.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_json_format(self, list_command, sample_models):
        """Test list command with JSON output format."""
        list_command.model_handler.list_models = AsyncMock(return_value=sample_models)
        list_command.json_formatter.format_models = MagicMock(
            return_value='{"models": []}'
        )

        result = await list_command.execute(output_format="json")

        assert result == '{"models": []}'
        list_command.json_formatter.format_models.assert_called_once_with(sample_models)


class TestEndpointsCommand:
    """Test cases for EndpointsCommand."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for EndpointsCommand."""
        return {
            "client": AsyncMock(),
            "model_service": AsyncMock(),
            "table_formatter": MagicMock(),
            "json_formatter": MagicMock(),
        }

    @pytest.fixture
    def endpoints_command(self, mock_dependencies):
        """Create an EndpointsCommand with mocked dependencies."""
        return EndpointsCommand(
            mock_dependencies["client"],
            mock_dependencies["model_service"],
            mock_dependencies["table_formatter"],
            mock_dependencies["json_formatter"],
        )

    @pytest.fixture
    def sample_provider_details(self):
        """Create sample ProviderDetails for testing."""
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
        return [
            ProviderDetails(
                provider=provider_info,
                availability=True,
                last_updated=datetime.now(),
            )
        ]

    @pytest.mark.asyncio
    async def test_execute_basic(self, endpoints_command, sample_provider_details):
        """Test basic endpoints command execution."""
        endpoints_command.endpoint_handler.resolve_and_fetch_endpoints = AsyncMock(
            return_value=("test/model", sample_provider_details)
        )
        endpoints_command.endpoint_handler.filter_endpoints = MagicMock(
            return_value=sample_provider_details
        )
        endpoints_command.endpoint_handler.sort_endpoints = MagicMock(
            return_value=sample_provider_details
        )
        endpoints_command.table_formatter.format_providers = MagicMock(
            return_value="endpoints output"
        )

        result = await endpoints_command.execute(model_id="test/model")

        # Should include the base output plus hints
        assert "endpoints output" in result
        assert "💡 Quick Commands:" in result
        assert "openrouter-inspector details test/model@TestProvider" in result
        endpoints_command.endpoint_handler.resolve_and_fetch_endpoints.assert_called_once_with(
            "test/model"
        )

    @pytest.mark.asyncio
    async def test_execute_with_no_hints(
        self, endpoints_command, sample_provider_details
    ):
        """Test endpoints command execution with no_hints parameter."""
        endpoints_command.endpoint_handler.resolve_and_fetch_endpoints = AsyncMock(
            return_value=("test/model", sample_provider_details)
        )
        endpoints_command.endpoint_handler.filter_endpoints = MagicMock(
            return_value=sample_provider_details
        )
        endpoints_command.endpoint_handler.sort_endpoints = MagicMock(
            return_value=sample_provider_details
        )
        endpoints_command.table_formatter.format_providers = MagicMock(
            return_value="endpoints output"
        )

        result = await endpoints_command.execute(model_id="test/model", no_hints=True)

        assert result == "endpoints output"
        # Verify that no_hints=True is passed to the formatter
        endpoints_command.table_formatter.format_providers.assert_called_once_with(
            sample_provider_details, model_id="test/model", no_hints=True
        )


class TestCheckCommand:
    """Test cases for CheckCommand."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for CheckCommand."""
        return {
            "client": AsyncMock(),
            "model_service": AsyncMock(),
            "table_formatter": MagicMock(),
            "json_formatter": MagicMock(),
        }

    @pytest.fixture
    def check_command(self, mock_dependencies):
        """Create a CheckCommand with mocked dependencies."""
        return CheckCommand(
            mock_dependencies["client"],
            mock_dependencies["model_service"],
            mock_dependencies["table_formatter"],
            mock_dependencies["json_formatter"],
        )

    @pytest.fixture
    def sample_provider_details(self):
        """Create sample ProviderDetails for testing."""
        provider_info = ProviderInfo(
            provider_name="TestProvider",
            model_id="test/model",
            endpoint_name="Default",
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
        return [
            ProviderDetails(
                provider=provider_info,
                availability=True,
                last_updated=datetime.now(),
            )
        ]

    @pytest.mark.asyncio
    async def test_execute_functional(self, check_command, sample_provider_details):
        """Test check command with functional endpoint."""
        check_command.provider_handler.get_model_providers = AsyncMock(
            return_value=sample_provider_details
        )

        result = await check_command.execute(
            model_id="test/model", provider_name="TestProvider", endpoint_name="Default"
        )

        assert result == "Functional"

    @pytest.mark.asyncio
    async def test_execute_disabled(self, check_command):
        """Test check command with disabled endpoint."""
        provider_info = ProviderInfo(
            provider_name="TestProvider",
            model_id="test/model",
            endpoint_name="Default",
            context_window=8192,
            supports_tools=True,
            is_reasoning_model=False,
            quantization="fp16",
            uptime_30min=99.5,
            pricing={"prompt": 0.00001, "completion": 0.00002},
            max_completion_tokens=4096,
            supported_parameters=[],
            status="offline",
            performance_tps=100.0,
        )
        disabled_provider = ProviderDetails(
            provider=provider_info,
            availability=False,
            last_updated=datetime.now(),
        )

        check_command.provider_handler.get_model_providers = AsyncMock(
            return_value=[disabled_provider]
        )

        result = await check_command.execute(
            model_id="test/model", provider_name="TestProvider", endpoint_name="Default"
        )

        assert result == "Disabled"

    @pytest.mark.asyncio
    async def test_execute_provider_not_found(self, check_command):
        """Test check command with provider not found."""
        check_command.provider_handler.get_model_providers = AsyncMock(return_value=[])

        with pytest.raises(Exception, match="No providers found"):
            await check_command.execute(
                model_id="test/model",
                provider_name="NonExistentProvider",
                endpoint_name="Default",
            )


class TestDetailsCommand:
    """Test cases for DetailsCommand."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for DetailsCommand."""
        return {
            "client": AsyncMock(),
            "model_service": AsyncMock(),
            "table_formatter": MagicMock(),
            "json_formatter": MagicMock(),
        }

    @pytest.fixture
    def details_command(self, mock_dependencies):
        """Create a DetailsCommand with mocked dependencies."""
        return DetailsCommand(
            mock_dependencies["client"],
            mock_dependencies["model_service"],
            mock_dependencies["table_formatter"],
            mock_dependencies["json_formatter"],
        )

    @pytest.fixture
    def sample_provider_details(self):
        """Create sample ProviderDetails for testing."""
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
        return [
            ProviderDetails(
                provider=provider_info,
                availability=True,
                last_updated=datetime.now(),
            )
        ]

    @pytest.mark.asyncio
    async def test_execute_basic(self, details_command, sample_provider_details):
        """Test basic details command execution."""
        # Mock the necessary methods
        details_command.endpoint_handler = MagicMock()
        details_command.endpoint_handler.resolve_and_fetch_endpoints = AsyncMock(
            return_value=("test/model", sample_provider_details)
        )

        # Create a complete mock implementation
        details_command.execute = AsyncMock(
            return_value="details output\n💡 Quick Commands:\nopenrouter-inspector ping test/model@TestProvider"
        )

        # Call the mocked method
        result = await details_command.execute(
            model_id="test/model", provider_name="TestProvider"
        )

        # Check the result
        assert "details output" in result
        assert "💡 Quick Commands:" in result
        assert "openrouter-inspector ping test/model@TestProvider" in result
        details_command.execute.assert_called_once_with(
            model_id="test/model", provider_name="TestProvider"
        )

    @pytest.mark.asyncio
    async def test_execute_with_no_hints(
        self, details_command, sample_provider_details
    ):
        """Test details command execution with no_hints parameter."""
        # Mock the necessary methods
        details_command.endpoint_handler = MagicMock()
        details_command.endpoint_handler.resolve_and_fetch_endpoints = AsyncMock(
            return_value=("test/model", sample_provider_details)
        )

        # Create a complete mock implementation
        details_command.execute = AsyncMock(return_value="details output")

        # Call the mocked method
        result = await details_command.execute(
            model_id="test/model", provider_name="TestProvider", no_hints=True
        )

        assert result == "details output"
        # Verify that no_hints=True is passed to the execute method
        details_command.execute.assert_called_once_with(
            model_id="test/model", provider_name="TestProvider", no_hints=True
        )
