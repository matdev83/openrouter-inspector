"""Unit tests for ping command helper behavior via CLI injection."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from openrouter_inspector.commands.ping_command import PingCommand


@pytest.mark.asyncio
async def test_ping_command_success_basic():
    client = AsyncMock()
    model_service = AsyncMock()
    table_formatter = MagicMock()
    json_formatter = MagicMock()

    cmd = PingCommand(client, model_service, table_formatter, json_formatter)

    client.create_chat_completion = AsyncMock(
        return_value=(
            {
                "choices": [
                    {"message": {"content": "Pong!"}},
                ],
                "usage": {"prompt_tokens": 5, "completion_tokens": 3},
            },
            {"x-openrouter-provider": "Chutes"},
        )
    )

    out = await cmd.execute(model_id="deepseek/deepseek-chat-v3-0324:free")
    assert "Pinging" in out
    assert "Reply from:" in out
    assert "tokens:" in out
