"""Tests to verify dependency inversion principle implementation."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from openrouter_inspector.commands.endpoints_command import EndpointsCommand
from openrouter_inspector.formatters.base import BaseFormatter
from openrouter_inspector.interfaces.client import APIClient
from openrouter_inspector.interfaces.services import ModelServiceInterface


class MockAPIClient(APIClient):
    """Mock implementation of APIClient for testing."""

    async def get_models(self):
        return []

    async def get_model_providers(self, model_name: str):
        return []

    async def create_chat_completion(self, **kwargs):
        return {}, {}

    async def create_chat_completion_stream(self, **kwargs):
        return AsyncMock(), {}

    async def close(self):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class MockModelService(ModelServiceInterface):
    """Mock implementation of ModelServiceInterface for testing."""

    async def list_models(self):
        return []

    async def search_models(self, query: str, filters=None):
        return []

    async def get_model_providers(self, model_name: str):
        return []


class MockFormatter(BaseFormatter):
    """Mock implementation of BaseFormatter for testing."""

    def format_models(self, models, **kwargs):
        return "mock models output"

    def format_providers(self, providers, **kwargs):
        return "mock providers output"


class TestDependencyInversion:
    """Test cases to verify dependency inversion principle."""

    def test_base_command_accepts_interfaces(self):
        """Test that BaseCommand can be instantiated with interface implementations."""
        # This should work without any issues if DIP is properly implemented
        mock_client = MockAPIClient()
        mock_service = MockModelService()
        mock_table_formatter = MockFormatter()
        mock_json_formatter = MockFormatter()

        # Create a concrete command with mock dependencies
        command = EndpointsCommand(
            client=mock_client,
            model_service=mock_service,
            table_formatter=mock_table_formatter,
            json_formatter=mock_json_formatter,
        )

        # Verify the command was created successfully
        assert command is not None
        assert isinstance(command.client, APIClient)
        assert isinstance(command.model_service, ModelServiceInterface)
        assert isinstance(command.table_formatter, BaseFormatter)
        assert isinstance(command.json_formatter, BaseFormatter)

    def test_command_works_with_mock_dependencies(self):
        """Test that commands work with completely mocked dependencies."""
        mock_client = MagicMock(spec=APIClient)
        mock_service = MagicMock(spec=ModelServiceInterface)
        mock_table_formatter = MagicMock(spec=BaseFormatter)
        mock_json_formatter = MagicMock(spec=BaseFormatter)

        # Create command with mocked dependencies
        command = EndpointsCommand(
            client=mock_client,
            model_service=mock_service,
            table_formatter=mock_table_formatter,
            json_formatter=mock_json_formatter,
        )

        # Verify that the command stores the dependencies correctly
        assert command.client is mock_client
        assert command.model_service is mock_service
        assert command.table_formatter is mock_table_formatter
        assert command.json_formatter is mock_json_formatter

    def test_handlers_use_interfaces(self):
        """Test that handlers are created with interface dependencies."""
        mock_client = MagicMock(spec=APIClient)
        mock_service = MagicMock(spec=ModelServiceInterface)
        mock_table_formatter = MagicMock(spec=BaseFormatter)
        mock_json_formatter = MagicMock(spec=BaseFormatter)

        command = EndpointsCommand(
            client=mock_client,
            model_service=mock_service,
            table_formatter=mock_table_formatter,
            json_formatter=mock_json_formatter,
        )

        # Verify that handlers are created with the interface dependencies
        assert command.model_handler.model_service is mock_service
        assert command.provider_handler.client is mock_client
        assert command.endpoint_handler.client is mock_client
        assert command.endpoint_handler.model_service is mock_service

    @pytest.mark.asyncio
    async def test_command_execution_with_mocks(self):
        """Test that command execution works with fully mocked dependencies."""
        from datetime import datetime

        from openrouter_inspector.models import ProviderDetails, ProviderInfo

        # Create mock provider data
        provider_info = ProviderInfo(
            provider_name="MockProvider",
            model_id="mock/model",
            endpoint_name="Mock Model",
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
        mock_providers = [
            ProviderDetails(
                provider=provider_info,
                availability=True,
                last_updated=datetime.now(),
            )
        ]

        # Set up mocks
        mock_client = MagicMock(spec=APIClient)
        mock_service = MagicMock(spec=ModelServiceInterface)
        mock_table_formatter = MagicMock(spec=BaseFormatter)
        mock_json_formatter = MagicMock(spec=BaseFormatter)

        mock_table_formatter.format_providers.return_value = "mock table output"

        command = EndpointsCommand(
            client=mock_client,
            model_service=mock_service,
            table_formatter=mock_table_formatter,
            json_formatter=mock_json_formatter,
        )

        # Mock the handler methods
        command.endpoint_handler.resolve_and_fetch_endpoints = AsyncMock(
            return_value=("mock/model", mock_providers)
        )
        command.endpoint_handler.filter_endpoints = MagicMock(
            return_value=mock_providers
        )
        command.endpoint_handler.sort_endpoints = MagicMock(return_value=mock_providers)

        # Execute the command
        result = await command.execute(model_id="mock/model", no_hints=True)

        # Verify it worked
        assert "mock table output" in result
        mock_table_formatter.format_providers.assert_called_once()

    def test_interfaces_are_properly_defined(self):
        """Test that interfaces define the expected methods."""
        # Test APIClient interface
        api_client_methods = {
            "get_models",
            "get_model_providers",
            "create_chat_completion",
            "create_chat_completion_stream",
            "close",
            "__aenter__",
            "__aexit__",
        }
        assert api_client_methods.issubset(dir(APIClient))

        # Test ModelServiceInterface
        model_service_methods = {"list_models", "search_models", "get_model_providers"}
        assert model_service_methods.issubset(dir(ModelServiceInterface))

        # Test BaseFormatter interface
        formatter_methods = {"format_models", "format_providers"}
        assert formatter_methods.issubset(dir(BaseFormatter))
