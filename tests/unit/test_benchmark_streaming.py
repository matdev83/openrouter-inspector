"""Tests for benchmark command streaming functionality."""

import json
from unittest.mock import patch

import pytest

from openrouter_inspector.client import OpenRouterClient
from openrouter_inspector.commands.benchmark_command import (
    BenchmarkCommand,
    BenchmarkResult,
)
from openrouter_inspector.formatters.json_formatter import JsonFormatter
from openrouter_inspector.formatters.table_formatter import TableFormatter
from openrouter_inspector.services import ModelService


class MockStreamResponse:
    """Mock streaming response for testing."""

    def __init__(self, chunks: list[str]):
        self.chunks = chunks
        self.headers = {"x-openrouter-provider": "TestProvider"}

    async def aiter_lines(self):
        """Async iterator for streaming lines."""
        for chunk in self.chunks:
            yield chunk


@pytest.fixture
def benchmark_command():
    """Create a benchmark command instance for testing."""
    client = OpenRouterClient("test-key")
    model_service = ModelService(client)
    table_formatter = TableFormatter()
    json_formatter = JsonFormatter()
    return BenchmarkCommand(client, model_service, table_formatter, json_formatter)


class TestBenchmarkStreaming:
    """Test streaming functionality in benchmark command."""

    def test_count_tokens_basic(self, benchmark_command):
        """Test basic token counting functionality."""
        text = "Hello world, this is a test."
        tokens = benchmark_command._count_tokens(text)
        assert isinstance(tokens, int)
        assert tokens > 0
        assert tokens < 20  # Should be reasonable for this short text

    def test_count_tokens_empty(self, benchmark_command):
        """Test token counting with empty text."""
        tokens = benchmark_command._count_tokens("")
        assert tokens == 0

    def test_count_tokens_different_models(self, benchmark_command):
        """Test token counting with different model names."""
        text = "Test message for token counting."

        # Test with different model types
        gpt_tokens = benchmark_command._count_tokens(text, "openai/gpt-4")
        claude_tokens = benchmark_command._count_tokens(text, "anthropic/claude-3")
        other_tokens = benchmark_command._count_tokens(text, "google/gemini-pro")

        # All should return positive integers
        assert all(
            isinstance(t, int) and t > 0
            for t in [gpt_tokens, claude_tokens, other_tokens]
        )

    @pytest.mark.asyncio
    async def test_streaming_with_token_limit_exceeded(self, benchmark_command):
        """Test streaming behavior when token limit is exceeded."""
        # Mock streaming chunks that would exceed token limit
        chunks = [
            "",  # Empty line
            "data: "
            + json.dumps(
                {
                    "choices": [
                        {
                            "delta": {
                                "content": "This is a long response that will exceed "
                            }
                        }
                    ]
                }
            ),
            "data: "
            + json.dumps(
                {
                    "choices": [
                        {
                            "delta": {
                                "content": "the token limit we set for testing purposes. "
                            }
                        }
                    ]
                }
            ),
            "data: "
            + json.dumps(
                {
                    "choices": [
                        {
                            "delta": {
                                "content": "It should be cancelled when limit reached."
                            }
                        }
                    ]
                }
            ),
            "data: [DONE]",
        ]

        mock_response = MockStreamResponse(chunks)

        with patch.object(
            benchmark_command.client, "create_chat_completion_stream"
        ) as mock_stream:
            mock_stream.return_value = (mock_response, mock_response.headers)

            # Set a very low token limit to trigger cancellation
            result = await benchmark_command._benchmark_once(
                model_id="test/model",
                max_tokens=5,  # Very low limit to trigger cancellation
            )

            assert isinstance(result, BenchmarkResult)
            assert result.success is True  # Should still be successful
            assert result.actual_output_tokens > 0

    @pytest.mark.asyncio
    async def test_streaming_normal_completion(self, benchmark_command):
        """Test streaming behavior with normal completion."""
        chunks = [
            "data: "
            + json.dumps({"choices": [{"delta": {"content": "Short response."}}]}),
            "data: [DONE]",
        ]

        mock_response = MockStreamResponse(chunks)

        with patch.object(
            benchmark_command.client, "create_chat_completion_stream"
        ) as mock_stream:
            mock_stream.return_value = (mock_response, mock_response.headers)

            result = await benchmark_command._benchmark_once(
                model_id="test/model", max_tokens=100  # High enough limit
            )

            assert isinstance(result, BenchmarkResult)
            assert result.success is True
            assert result.tokens_exceeded is False
            # Check that the collected text contains our content (not in output_str which is the summary)
            # We can verify this by checking the token count is reasonable
            assert result.actual_output_tokens > 0

    @pytest.mark.asyncio
    async def test_streaming_with_malformed_json(self, benchmark_command):
        """Test streaming behavior with malformed JSON chunks."""
        chunks = [
            "data: {invalid json}",  # Malformed JSON should be skipped
            "data: "
            + json.dumps({"choices": [{"delta": {"content": "Valid content."}}]}),
            "data: [DONE]",
        ]

        mock_response = MockStreamResponse(chunks)

        with patch.object(
            benchmark_command.client, "create_chat_completion_stream"
        ) as mock_stream:
            mock_stream.return_value = (mock_response, mock_response.headers)

            result = await benchmark_command._benchmark_once(
                model_id="test/model", max_tokens=100
            )

            assert isinstance(result, BenchmarkResult)
            assert result.success is True
            # The malformed JSON should be skipped, but valid content should be processed
            assert result.actual_output_tokens > 0

    @pytest.mark.asyncio
    async def test_streaming_error_handling(self, benchmark_command):
        """Test error handling during streaming."""
        with patch.object(
            benchmark_command.client, "create_chat_completion_stream"
        ) as mock_stream:
            mock_stream.side_effect = Exception("Network error")

            result = await benchmark_command._benchmark_once(
                model_id="test/model", max_tokens=100
            )

            assert isinstance(result, BenchmarkResult)
            assert result.success is False
            assert "Network error" in result.output_str

    @pytest.mark.asyncio
    async def test_execute_with_max_tokens_parameter(self, benchmark_command):
        """Test execute method with max_tokens parameter."""
        chunks = [
            "data: "
            + json.dumps({"choices": [{"delta": {"content": "Test response"}}]}),
            "data: [DONE]",
        ]

        mock_response = MockStreamResponse(chunks)

        with patch.object(
            benchmark_command.client, "create_chat_completion_stream"
        ) as mock_stream:
            mock_stream.return_value = (mock_response, mock_response.headers)

            output = await benchmark_command.execute(
                model_id="test/model", max_tokens=50, timeout_seconds=30
            )

            assert isinstance(output, str)
            assert "test/model" in output
            assert "TPS" in output

    def test_benchmark_result_with_new_fields(self):
        """Test BenchmarkResult dataclass with new fields."""
        result = BenchmarkResult(
            success=True,
            elapsed_ms=1000.0,
            input_tokens=10,
            output_tokens=20,
            total_tokens=30,
            tokens_per_second=20.0,
            cost=0.001,
            output_str="Test output",
            tokens_exceeded=True,
            actual_output_tokens=25,
        )

        assert result.tokens_exceeded is True
        assert result.actual_output_tokens == 25
        assert result.success is True

    @pytest.mark.asyncio
    async def test_streaming_chunks_without_content(self, benchmark_command):
        """Test streaming with chunks that don't contain content."""
        chunks = [
            "data: "
            + json.dumps({"choices": [{"delta": {"role": "assistant"}}]}),  # No content
            "data: "
            + json.dumps({"choices": [{"delta": {"content": "Actual content"}}]}),
            "data: [DONE]",
        ]

        mock_response = MockStreamResponse(chunks)

        with patch.object(
            benchmark_command.client, "create_chat_completion_stream"
        ) as mock_stream:
            mock_stream.return_value = (mock_response, mock_response.headers)

            result = await benchmark_command._benchmark_once(
                model_id="test/model", max_tokens=100
            )

            assert isinstance(result, BenchmarkResult)
            assert result.success is True
            # Content should be processed correctly
            assert result.actual_output_tokens > 0
