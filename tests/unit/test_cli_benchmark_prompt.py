from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, patch

from click.testing import CliRunner

from openrouter_inspector import cli as root_cli


def test_benchmark_with_custom_prompt_file(monkeypatch):
    runner = CliRunner()
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    with TemporaryDirectory() as td:
        p = Path(td) / "custom.md"
        p.write_text("# Heading\nThis is a custom prompt.", encoding="utf-8")

        with patch(
            "openrouter_inspector.utils.create_command_dependencies"
        ) as mock_deps:
            mock_client = AsyncMock()
            mock_model_service = AsyncMock()
            mock_table_formatter = AsyncMock()
            mock_json_formatter = AsyncMock()

            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None

            mock_deps.return_value = (
                mock_client,
                mock_model_service,
                mock_table_formatter,
                mock_json_formatter,
            )

            # Intercept _benchmark_once to assert prompt override flows through
            with patch(
                "openrouter_inspector.commands.benchmark_command.BenchmarkCommand._benchmark_once",
                new=AsyncMock(
                    return_value=type(
                        "R",
                        (),
                        {
                            "tokens_per_second": 1.23,
                            "elapsed_ms": 1.0,
                            "input_tokens": 1,
                            "output_tokens": 1,
                            "total_tokens": 2,
                            "cost": 0.0,
                            "success": True,
                            "output_str": "",
                            "tokens_exceeded": False,
                            "actual_output_tokens": 1,
                        },
                    )()
                ),
            ) as mock_once:
                result = runner.invoke(
                    root_cli,
                    [
                        "benchmark",
                        "some/model",
                        "--prompt-file",
                        str(p),
                        "--format",
                        "text",
                    ],
                )

                assert result.exit_code == 0
                # Ensure we passed the sanitized prompt (header removed)
                assert mock_once.await_args is not None
                _, kwargs = mock_once.await_args
                assert (
                    kwargs.get("throughput_prompt_override")
                    == "This is a custom prompt."
                )


def test_benchmark_with_missing_prompt_file_exits_2(monkeypatch):
    runner = CliRunner()
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    # File does not exist → Click should exit with code 2 during parsing/validation
    result = runner.invoke(
        root_cli,
        [
            "benchmark",
            "some/model",
            "--prompt-file",
            "C:/path/does/not/exist.md",
            "--format",
            "text",
        ],
    )

    assert result.exit_code == 2
