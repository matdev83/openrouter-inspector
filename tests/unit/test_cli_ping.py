"""Unit tests for the ping command variants and behavior."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from click.testing import CliRunner

from openrouter_inspector import cli as root_cli


def _make_client_mocks():
    mock_client = AsyncMock()
    mock_model_service = AsyncMock()
    mock_table_formatter = AsyncMock()
    mock_json_formatter = AsyncMock()

    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    return (
        mock_client,
        mock_model_service,
        mock_table_formatter,
        mock_json_formatter,
    )


def test_ping_model_only_uses_headers_provider(monkeypatch):
    runner = CliRunner()
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    with patch("openrouter_inspector.utils.create_command_dependencies") as mock_deps:
        (
            mock_client,
            mock_model_service,
            mock_table_formatter,
            mock_json_formatter,
        ) = _make_client_mocks()
        mock_deps.return_value = (
            mock_client,
            mock_model_service,
            mock_table_formatter,
            mock_json_formatter,
        )

        mock_client.create_chat_completion = AsyncMock(
            return_value=(
                {
                    "choices": [{"message": {"content": "Pong!"}}],
                    "usage": {"prompt_tokens": 5, "completion_tokens": 3},
                },
                {"x-openrouter-provider": "Chutes"},
            )
        )

        result = runner.invoke(root_cli, ["ping", "openai/o4-mini"])
        assert result.exit_code == 0
        out = result.output
        assert (
            "Pinging https://openrouter.ai/api/v1/chat/completions/openai/o4-mini@Chutes with 5 input tokens:"
            in out
        )
        assert (
            "Reply from: https://openrouter.ai/api/v1/chat/completions/openai/o4-mini@Chutes tokens: 3"
            in out
        )
        assert "TTL=60s" in out


def test_ping_with_provider_positional(monkeypatch):
    runner = CliRunner()
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    with patch("openrouter_inspector.utils.create_command_dependencies") as mock_deps:
        mock_client, mock_model_service, mock_table_formatter, mock_json_formatter = (
            _make_client_mocks()
        )
        mock_deps.return_value = (
            mock_client,
            mock_model_service,
            mock_table_formatter,
            mock_json_formatter,
        )

        mock_client.create_chat_completion = AsyncMock(
            return_value=(
                {
                    "choices": [{"message": {"content": "Pong!"}}],
                    "usage": {"prompt_tokens": 2, "completion_tokens": 1},
                },
                {"x-openrouter-provider": "Chutes"},
            )
        )

        result = runner.invoke(
            root_cli, ["ping", "deepseek/deepseek-chat-v3-0324:free", "Chutes"]
        )
        assert result.exit_code == 0
        # Ensure routing args passed to client
        args, kwargs = mock_client.create_chat_completion.call_args
        assert kwargs["model"] == "deepseek/deepseek-chat-v3-0324:free"
        assert kwargs["provider_order"] == ["Chutes"]
        assert kwargs["allow_fallbacks"] is False


def test_ping_with_at_shorthand(monkeypatch):
    runner = CliRunner()
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    with patch("openrouter_inspector.utils.create_command_dependencies") as mock_deps:
        mock_client, mock_model_service, mock_table_formatter, mock_json_formatter = (
            _make_client_mocks()
        )
        mock_deps.return_value = (
            mock_client,
            mock_model_service,
            mock_table_formatter,
            mock_json_formatter,
        )

        mock_client.create_chat_completion = AsyncMock(
            return_value=(
                {
                    "choices": [{"message": {"content": "Pong."}}],
                    "usage": {"prompt_tokens": 7, "completion_tokens": 4},
                },
                {"x-openrouter-provider": "Chutes"},
            )
        )

        result = runner.invoke(
            root_cli, ["ping", "deepseek/deepseek-chat-v3-0324:free@Chutes"]
        )
        assert result.exit_code == 0
        # Ensure routing args passed correctly
        args, kwargs = mock_client.create_chat_completion.call_args
        assert kwargs["model"] == "deepseek/deepseek-chat-v3-0324:free"
        assert kwargs["provider_order"] == ["Chutes"]
        assert kwargs["allow_fallbacks"] is False


def test_ping_error_path_prints_message(monkeypatch):
    runner = CliRunner()
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    with patch("openrouter_inspector.utils.create_command_dependencies") as mock_deps:
        mock_client, mock_model_service, mock_table_formatter, mock_json_formatter = (
            _make_client_mocks()
        )
        mock_deps.return_value = (
            mock_client,
            mock_model_service,
            mock_table_formatter,
            mock_json_formatter,
        )

        mock_client.create_chat_completion = AsyncMock(
            side_effect=Exception("Not Found")
        )

        result = runner.invoke(root_cli, ["ping", "openai/o4-mini"])
        assert result.exit_code == 0
        assert "error: Not Found" in result.output


def test_ping_provider_from_json_meta_when_no_header(monkeypatch):
    runner = CliRunner()
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    with patch("openrouter_inspector.utils.create_command_dependencies") as mock_deps:
        mock_client, mock_model_service, mock_table_formatter, mock_json_formatter = (
            _make_client_mocks()
        )
        mock_deps.return_value = (
            mock_client,
            mock_model_service,
            mock_table_formatter,
            mock_json_formatter,
        )

        mock_client.create_chat_completion = AsyncMock(
            return_value=(
                {
                    "provider": "MetaProv",
                    "choices": [{"message": {"content": "Pong!"}}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1},
                },
                {},
            )
        )

        result = runner.invoke(root_cli, ["ping", "openai/o4-mini"])
        assert result.exit_code == 0
        assert "@MetaProv" in result.output


def test_ping_timeout_option_and_print(monkeypatch):
    runner = CliRunner()
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    with patch("openrouter_inspector.utils.create_command_dependencies") as mock_deps:
        mock_client, mock_model_service, mock_table_formatter, mock_json_formatter = (
            _make_client_mocks()
        )
        mock_deps.return_value = (
            mock_client,
            mock_model_service,
            mock_table_formatter,
            mock_json_formatter,
        )

        mock_client.create_chat_completion = AsyncMock(
            return_value=(
                {
                    "choices": [{"message": {"content": "Pong!"}}],
                    "usage": {"prompt_tokens": 3, "completion_tokens": 2},
                },
                {"x-openrouter-provider": "Chutes"},
            )
        )

        result = runner.invoke(root_cli, ["ping", "openai/o4-mini", "--timeout", "5"])
        assert result.exit_code == 0
        # Ensure call used timeout_seconds=5
        args, kwargs = mock_client.create_chat_completion.call_args
        assert kwargs["timeout_seconds"] == 5
        assert "TTL=5s" in result.output
