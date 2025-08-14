"""Tests for CLI command factory."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from openrouter_inspector.command_factory import CLICommandFactory
from openrouter_inspector.commands.endpoints_command import EndpointsCommand


class TestCLICommandFactory:
    """Test cases for CLICommandFactory."""

    @pytest.fixture
    def factory(self):
        """Create a command factory with test API key."""
        return CLICommandFactory("test-api-key")

    @pytest.mark.asyncio
    async def test_create_and_execute_command(self, factory):
        """Test creating and executing a command through the factory."""
        with patch(
            "openrouter_inspector.command_factory.create_command_dependencies"
        ) as mock_deps:
            # Set up mocks
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

            # Mock command execution
            with patch.object(
                EndpointsCommand, "execute", new_callable=AsyncMock
            ) as mock_execute:
                mock_execute.return_value = "test output"

                # Execute command through factory
                result = await factory.create_and_execute_command(
                    EndpointsCommand, model_id="test/model", output_format="table"
                )

                # Verify results
                assert result == "test output"
                mock_deps.assert_called_once_with("test-api-key")
                mock_execute.assert_called_once_with(
                    model_id="test/model", output_format="table"
                )

    def test_run_command_sync(self, factory):
        """Test synchronous command execution."""
        with patch.object(
            factory, "create_and_execute_command", new_callable=AsyncMock
        ) as mock_async:
            mock_async.return_value = "sync test output"

            result = factory.run_command_sync(EndpointsCommand, model_id="test/model")

            assert result == "sync test output"
            mock_async.assert_called_once_with(EndpointsCommand, model_id="test/model")

    @pytest.mark.asyncio
    async def test_client_lifecycle_management(self, factory):
        """Test that client lifecycle is properly managed."""
        with patch(
            "openrouter_inspector.command_factory.create_command_dependencies"
        ) as mock_deps:
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

            # Mock command execution
            with patch.object(
                EndpointsCommand, "execute", new_callable=AsyncMock
            ) as mock_execute:
                mock_execute.return_value = "output"

                await factory.create_and_execute_command(
                    EndpointsCommand, model_id="test"
                )

                # Verify client context manager was used
                mock_client.__aenter__.assert_called_once()
                mock_client.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_service_client_assignment(self, factory):
        """Test that model service client is properly assigned."""
        with patch(
            "openrouter_inspector.command_factory.create_command_dependencies"
        ) as mock_deps:
            mock_client = AsyncMock()
            mock_service = MagicMock()  # Use MagicMock to allow attribute assignment
            mock_table_formatter = MagicMock()
            mock_json_formatter = MagicMock()

            mock_deps.return_value = (
                mock_client,
                mock_service,
                mock_table_formatter,
                mock_json_formatter,
            )

            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with patch.object(
                EndpointsCommand, "execute", new_callable=AsyncMock
            ) as mock_execute:
                mock_execute.return_value = "output"

                await factory.create_and_execute_command(
                    EndpointsCommand, model_id="test"
                )

                # Verify service client was assigned
                assert mock_service.client is mock_client
