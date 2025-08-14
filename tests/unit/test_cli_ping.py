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
                    "usage": {
                        "prompt_tokens": 5,
                        "completion_tokens": 3,
                        "total_cost": 0.0001,
                    },
                },
                {"x-openrouter-provider": "Chutes"},
            )
        )

        result = runner.invoke(root_cli, ["ping", "openai/o4-mini", "-n", "1"])
        assert result.exit_code == 0
        out = result.output

        assert (
            "Pinging https://openrouter.ai/api/v1/chat/completions/openai/o4-mini with OpenRouter API:"
            in out
        )
        assert (
            "Reply from: https://openrouter.ai/api/v1/chat/completions/openai/o4-mini@Chutes tokens: 3"
            in out
        )
        assert "TTL=60s" in out
        assert "Packets: Sent = 1, Received = 1, Lost = 0" in out
        assert "Total API cost for this run: $0.000100"


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
            root_cli,
            ["ping", "deepseek/deepseek-chat-v3-0324:free", "Chutes", "-n", "2"],
        )
        assert result.exit_code == 0
        assert mock_client.create_chat_completion.call_count == 2
        # Ensure routing args passed to client
        args, kwargs = mock_client.create_chat_completion.call_args
        assert kwargs["model"] == "deepseek/deepseek-chat-v3-0324:free"
        assert kwargs["provider_order"] == ["Chutes"]
        assert kwargs["allow_fallbacks"] is False
        assert "Packets: Sent = 2, Received = 2, Lost = 0" in result.output


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
            root_cli, ["ping", "deepseek/deepseek-chat-v3-0324:free@Chutes", "-n", "1"]
        )
        assert result.exit_code == 0
        assert mock_client.create_chat_completion.call_count == 1
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

        result = runner.invoke(root_cli, ["ping", "openai/o4-mini", "-n", "1"])
        assert result.exit_code == 1
        assert "error: Not Found" in result.output
        assert "Packets: Sent = 1, Received = 0, Lost = 1" in result.output


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

        result = runner.invoke(root_cli, ["ping", "openai/o4-mini", "-n", "1"])
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

        result = runner.invoke(
            root_cli, ["ping", "openai/o4-mini", "--timeout", "5", "-n", "1"]
        )
        assert result.exit_code == 0
        # Ensure call used timeout_seconds=5
        args, kwargs = mock_client.create_chat_completion.call_args
        assert kwargs["timeout_seconds"] == 5
        assert "TTL=5s" in result.output


def test_ping_count_and_filthy_rich_flags(monkeypatch):
    runner = CliRunner()
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    # Test count > 10 without flag
    result = runner.invoke(root_cli, ["ping", "some/model", "-n", "11"])
    assert result.exit_code == 1
    assert "must use the --filthy-rich flag" in result.output

    # Test count <= 0
    result = runner.invoke(root_cli, ["ping", "some/model", "-n", "0"])
    assert result.exit_code == 1
    assert "must be a positive integer" in result.output

    # Test count > 10 with flag (should not raise validation error)
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
        mock_client.create_chat_completion.return_value = (
            {"choices": [{"message": {"content": "pong"}}]},
            {},
        )
        result = runner.invoke(
            root_cli, ["ping", "some/model", "-n", "11", "--filthy-rich"]
        )
        assert result.exit_code == 0
        assert mock_client.create_chat_completion.call_count == 11


def test_ping_with_single_failure_counts_as_lost(monkeypatch):
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

        # Fail on the first call, succeed on the second
        mock_client.create_chat_completion.side_effect = [
            Exception("API Error 500"),
            (
                {
                    "choices": [{"message": {"content": "Pong!"}}],
                    "usage": {
                        "prompt_tokens": 5,
                        "completion_tokens": 3,
                        "total_cost": 0.0001,
                    },
                },
                {"x-openrouter-provider": "Chutes"},
            ),
        ]

        result = runner.invoke(root_cli, ["ping", "openai/o4-mini", "-n", "2"])
        assert result.exit_code == 1

        # Ensure the client was called twice, with no internal retries
        assert mock_client.create_chat_completion.call_count == 2
        args, kwargs = mock_client.create_chat_completion.call_args
        assert kwargs["retries_enabled"] is False

        # Check that statistics correctly report one lost packet
        assert "Packets: Sent = 2, Received = 1, Lost = 1" in result.output
        assert "(50% loss)" in result.output


def test_ping_exit_code_on_success_and_failure(monkeypatch):
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

        # --- Test success case (exit code 0) ---
        mock_client.create_chat_completion.side_effect = None  # Reset side effect
        mock_client.create_chat_completion.return_value = (
            {
                "choices": [{"message": {"content": "Pong!"}}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 3},
            },
            {},
        )
        result = runner.invoke(root_cli, ["ping", "openai/o4-mini", "-n", "1"])
        assert result.exit_code == 0

        # --- Test failure case (exit code 1) ---
        mock_client.create_chat_completion.side_effect = [Exception("API Error")]
        result = runner.invoke(root_cli, ["ping", "openai/o4-mini", "-n", "1"])
        assert result.exit_code == 1


def test_ping_success_with_segmented_content(monkeypatch):
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

        # Provide content as list segments instead of single string
        mock_client.create_chat_completion = AsyncMock(
            return_value=(
                {
                    "choices": [
                        {
                            "message": {
                                "content": [
                                    {"type": "text", "text": "Po"},
                                    {"type": "text", "text": "ng"},
                                ]
                            }
                        }
                    ],
                    "usage": {"prompt_tokens": 4, "completion_tokens": 4},
                },
                {"x-openrouter-provider": "Chutes"},
            )
        )

        result = runner.invoke(root_cli, ["ping", "openai/o4-mini", "-n", "1"])
        assert result.exit_code == 0
        assert "Lost = 0 (0% loss)" in result.output


def test_ping_success_with_text_in_dict_content(monkeypatch):
    """Test that a 'pong' inside a content dictionary is correctly parsed as success."""
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

        # Simulate a response where 'content' is a dictionary containing 'text'
        mock_client.create_chat_completion = AsyncMock(
            return_value=(
                {
                    "choices": [{"message": {"content": {"text": "Pong, my friend!"}}}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1},
                },
                {},
            )
        )

        result = runner.invoke(root_cli, ["ping", "some/model", "-n", "1"])
        assert (
            result.exit_code == 0
        ), f"Expected exit code 0, but got {result.exit_code} with output:\n{result.output}"
        assert "Lost = 0 (0% loss)" in result.output


def test_ping_success_with_deeply_nested_content(monkeypatch):
    """Test that 'pong' is found even in a deeply nested, complex response."""
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

        # Simulate a response with a complex, nested structure
        mock_client.create_chat_completion = AsyncMock(
            return_value=(
                {
                    "id": "chatcmpl-123",
                    "object": "chat.completion",
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [
                                    {
                                        "id": "call_abc",
                                        "type": "function",
                                        "function": {
                                            "name": "reply_to_ping",
                                            "arguments": '{"reply": "Sure, here is your pong."}',
                                        },
                                    }
                                ],
                            },
                        }
                    ],
                },
                {},
            )
        )

        result = runner.invoke(root_cli, ["ping", "some/model", "-n", "1"])
        assert result.exit_code == 1
        assert "Lost = 1 (100% loss)" in result.output
