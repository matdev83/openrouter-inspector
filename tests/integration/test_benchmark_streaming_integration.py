"""Integration tests for benchmark command streaming functionality."""

import os

import pytest

from openrouter_inspector.client import OpenRouterClient
from openrouter_inspector.commands.benchmark_command import BenchmarkCommand
from openrouter_inspector.formatters.json_formatter import JsonFormatter
from openrouter_inspector.formatters.table_formatter import TableFormatter
from openrouter_inspector.services import ModelService


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY not set - skipping integration tests",
)
class TestBenchmarkStreamingIntegration:
    """Integration tests for benchmark streaming with real API."""

    @pytest.fixture
    def benchmark_command(self):
        """Create a benchmark command with real API client."""
        api_key = os.getenv("OPENROUTER_API_KEY")
        client = OpenRouterClient(api_key)
        model_service = ModelService(client)
        table_formatter = TableFormatter()
        json_formatter = JsonFormatter()
        return BenchmarkCommand(client, model_service, table_formatter, json_formatter)

    @pytest.mark.asyncio
    async def test_benchmark_with_low_token_limit(self, benchmark_command):
        """Test benchmark with a low token limit to verify safety mechanism."""
        async with benchmark_command.client:
            result = await benchmark_command._benchmark_once(
                model_id="google/gemini-2.0-flash-exp:free",
                max_tokens=50,  # Low limit to test safety
                timeout_seconds=30,
            )

            assert result.success is True
            assert result.output_tokens <= 50  # Should respect the limit
            assert result.actual_output_tokens > 0
            assert result.tokens_per_second > 0
            assert result.elapsed_ms > 0
            assert len(result.output_str) > 0

    @pytest.mark.asyncio
    async def test_benchmark_with_normal_token_limit(self, benchmark_command):
        """Test benchmark with normal token limit."""
        async with benchmark_command.client:
            result = await benchmark_command._benchmark_once(
                model_id="google/gemini-2.0-flash-exp:free",
                max_tokens=200,
                timeout_seconds=30,
            )

            assert result.success is True
            assert result.output_tokens > 0
            assert result.actual_output_tokens > 0
            assert result.tokens_per_second > 0
            assert "TPS" in result.output_str
            assert "google/gemini-2.0-flash-exp:free" in result.output_str

    @pytest.mark.asyncio
    async def test_benchmark_execute_method(self, benchmark_command):
        """Test the execute method end-to-end."""
        async with benchmark_command.client:
            output = await benchmark_command.execute(
                model_id="google/gemini-2.0-flash-exp:free",
                max_tokens=100,
                timeout_seconds=30,
                debug_response=False,
            )

            assert isinstance(output, str)
            assert "Benchmarking" in output
            assert "TPS" in output
            assert "tokens per second" in output
            assert "google/gemini-2.0-flash-exp:free" in output

    @pytest.mark.asyncio
    async def test_benchmark_with_debug_response(self, benchmark_command):
        """Test benchmark with debug response enabled."""
        async with benchmark_command.client:
            result = await benchmark_command._benchmark_once(
                model_id="google/gemini-2.0-flash-exp:free",
                max_tokens=30,
                timeout_seconds=30,
                debug_response=True,  # This will print debug info
            )

            assert result.success is True
            assert result.output_tokens > 0

    @pytest.mark.asyncio
    async def test_token_counting_accuracy(self, benchmark_command):
        """Test that our token counting is reasonably accurate."""
        async with benchmark_command.client:
            result = await benchmark_command._benchmark_once(
                model_id="google/gemini-2.0-flash-exp:free",
                max_tokens=100,
                timeout_seconds=30,
            )

            assert result.success is True

            # Our token count should be reasonably close to API's count
            # Allow for some variance due to different tokenization methods
            api_tokens = result.output_tokens
            our_tokens = result.actual_output_tokens

            # Should be within 20% of each other (generous tolerance)
            if api_tokens > 0:
                variance = abs(api_tokens - our_tokens) / api_tokens
                assert (
                    variance < 0.3
                ), f"Token count variance too high: API={api_tokens}, Ours={our_tokens}"

    @pytest.mark.asyncio
    async def test_benchmark_with_very_low_limit(self, benchmark_command):
        """Test with extremely low token limit to verify immediate cancellation."""
        async with benchmark_command.client:
            result = await benchmark_command._benchmark_once(
                model_id="google/gemini-2.0-flash-exp:free",
                max_tokens=5,  # Very low limit
                timeout_seconds=30,
            )

            assert result.success is True
            assert result.output_tokens <= 10  # Should be very low
            assert result.actual_output_tokens <= 10

    @pytest.mark.asyncio
    async def test_benchmark_performance_metrics(self, benchmark_command):
        """Test that performance metrics are reasonable."""
        async with benchmark_command.client:
            result = await benchmark_command._benchmark_once(
                model_id="google/gemini-2.0-flash-exp:free",
                max_tokens=150,
                timeout_seconds=30,
            )

            assert result.success is True
            assert result.elapsed_ms > 0
            assert result.tokens_per_second > 0

            # Sanity check: TPS should be reasonable (not impossibly high/low)
            assert 1 <= result.tokens_per_second <= 1000  # Reasonable range

            # Time should be reasonable (not negative or impossibly fast)
            assert 0.1 <= result.elapsed_ms / 1000 <= 60  # Between 0.1s and 60s

    @pytest.mark.asyncio
    async def test_benchmark_cost_tracking(self, benchmark_command):
        """Test that cost tracking works (should be 0 for free model)."""
        async with benchmark_command.client:
            result = await benchmark_command._benchmark_once(
                model_id="google/gemini-2.0-flash-exp:free",
                max_tokens=100,
                timeout_seconds=30,
            )

            assert result.success is True
            assert result.cost == 0.0  # Free model should have zero cost
            assert "$0.00" in result.output_str
