import pytest
from click.testing import CliRunner

from openrouter_inspector import cli as root_cli


def test_cli_help_shows_without_args():
    runner = CliRunner()
    result = runner.invoke(root_cli, [])
    assert result.exit_code == 0
    assert "OpenRouter Inspector" in result.output


def test_missing_api_key_shows_friendly_error(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    runner = CliRunner()
    result = runner.invoke(root_cli, ["list"])  # any command
    assert result.exit_code != 0
    assert "OPENROUTER_API_KEY is required" in result.output


def test_offers_partial_match_resolves(httpx_mock, monkeypatch):
    # Set a fake API key
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    # Mock models list with a single matching candidate
    httpx_mock.add_response(
        method="GET",
        url="https://openrouter.ai/api/v1/models",
        json={
            "data": [
                {
                    "id": "deepseek/deepseek-r1",
                    "name": "DeepSeek R1",
                    "context_length": 163840,
                    "pricing": {},
                    "created": "2024-01-01T00:00:00Z",
                }
            ]
        },
        status_code=200,
    )

    # Mock the exact model ID lookup failing initially (to trigger partial match logic)
    httpx_mock.add_response(
        method="GET",
        url="https://openrouter.ai/api/v1/models/deepseek-r1/endpoints",
        status_code=404,
    )

    # Endpoints for resolved id
    httpx_mock.add_response(
        method="GET",
        url="https://openrouter.ai/api/v1/models/deepseek/deepseek-r1/endpoints",
        json={
            "data": {
                "id": "deepseek/deepseek-r1",
                "endpoints": [
                    {
                        "provider_name": "DeepInfra",
                        "name": "DeepInfra | deepseek-r1-default",
                        "context_length": 163840,
                        "max_completion_tokens": 32768,
                        "pricing": {"prompt": "0.0000004", "completion": "0.000002"},
                        "supported_parameters": ["reasoning"],
                        "status": 1,
                    }
                ],
            }
        },
        status_code=200,
    )

    runner = CliRunner()
    # Use a partial id to trigger resolution
    result = runner.invoke(
        root_cli, ["endpoints", "deepseek-r1"], catch_exceptions=False
    )
    assert result.exit_code == 0
    assert "Offers for deepseek/deepseek-r1" in result.output
    # Provider name may be trimmed from endpoint name; just assert core fields exist
    assert "Reason" in result.output
    assert "$" in result.output
    assert "+" in result.output  # Reason column shows +
