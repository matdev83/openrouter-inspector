"""Benchmark command implementation."""

from __future__ import annotations

import json
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import tiktoken

from .base_command import BaseCommand


@dataclass
class BenchmarkResult:
    """Dataclass to store the result of a benchmark test."""

    success: bool
    elapsed_ms: float
    input_tokens: int
    output_tokens: int
    total_tokens: int
    tokens_per_second: float
    cost: float | None
    output_str: str
    tokens_exceeded: bool = False
    actual_output_tokens: int = 0


class BenchmarkCommand(BaseCommand):
    """Command to benchmark throughput (TPS) of a model or specific provider endpoint."""

    def _count_tokens(self, text: str, model_name: str = "gpt-4") -> int:
        """Count tokens in text using tiktoken.

        Args:
            text: Text to count tokens for
            model_name: Model name for encoding (defaults to gpt-4)

        Returns:
            Number of tokens
        """
        try:
            # Try to get encoding for the specific model
            if "gpt" in model_name.lower():
                encoding = tiktoken.encoding_for_model("gpt-4")
            elif "claude" in model_name.lower():
                encoding = tiktoken.encoding_for_model("gpt-4")  # Use gpt-4 as fallback
            else:
                encoding = tiktoken.get_encoding("cl100k_base")  # Default encoding
        except Exception:
            # Fallback to default encoding if model-specific fails
            encoding = tiktoken.get_encoding("cl100k_base")

        return len(encoding.encode(text))

    def _load_throughput_prompt(self) -> str:
        """Load the throughput test prompt from the config file."""
        prompt_path = Path("config/prompts/throughput.md")
        try:
            if prompt_path.exists():
                content = prompt_path.read_text(encoding="utf-8").strip()
                # Remove the markdown header if present
                lines = content.split("\n")
                if lines and lines[0].startswith("# "):
                    lines = lines[1:]
                return "\n".join(lines).strip()
        except (OSError, UnicodeDecodeError):
            # Ignore file I/O/encoding errors and use default prompt
            ...
        # Fallback to default prompt if file doesn't exist or can't be read
        return (
            "Explain in detail how to learn a new skill from complete beginner to expert level. "
            "Include specific steps, common mistakes, practice methods, resources, timeline expectations, "
            "and real examples from different fields like music, sports, programming, cooking, and art. "
            "Cover the psychology of learning, motivation techniques, and how to overcome plateaus."
        )

    def _extract_message_text(self, response_json: dict[str, Any]) -> str:
        """Extract plain text from a chat completion response in a robust way."""
        try:
            choices = response_json.get("choices") or []
            if not choices:
                return ""
            choice = choices[0] or {}
            # Standard OpenAI format
            message = choice.get("message") or {}
            content = message.get("content")

            if isinstance(content, str):
                return content

            # Handle dictionary content, e.g., {"text": "..."}
            if isinstance(content, dict):
                text_from_dict = content.get("text")
                if isinstance(text_from_dict, str):
                    return text_from_dict

            # Handle segmented list content
            if isinstance(content, list):
                segments: list[str] = []
                for part in content:
                    if isinstance(part, str):
                        segments.append(part)
                    elif isinstance(part, dict):
                        text_val = part.get("text") or part.get("content")
                        if isinstance(text_val, str):
                            segments.append(text_val)
                return "".join(segments)

            # Fallback for non-standard choice-level text
            text_fallback = choice.get("text")
            if isinstance(text_fallback, str):
                return text_fallback
        except Exception:
            return ""
        return ""

    async def _benchmark_once(
        self,
        *,
        model_id: str,
        provider_name: str | None = None,
        timeout_seconds: int = 120,
        max_tokens: int = 3000,
        debug_response: bool = False,
        throughput_prompt_override: str | None = None,
    ) -> BenchmarkResult:
        """Execute a single benchmark test.

        Returns:
            A BenchmarkResult object with the outcome.
        """
        # Prepare request body
        throughput_prompt = (
            throughput_prompt_override
            if throughput_prompt_override
            else self._load_throughput_prompt()
        )
        messages = [
            {
                "role": "user",
                "content": throughput_prompt,
            }
        ]

        provider_order = [provider_name] if provider_name else None

        # Measure latency
        start_ns = time.perf_counter_ns()
        tokens_exceeded = False
        actual_output_tokens = 0
        collected_text = ""

        try:
            response, response_headers = (
                await self.client.create_chat_completion_stream(
                    model=model_id,
                    messages=messages,
                    provider_order=provider_order,
                    allow_fallbacks=False if provider_name else None,
                    timeout_seconds=timeout_seconds,
                    extra_headers={},
                    extra_body={
                        "temperature": 0.7,  # Allow some creativity for longer responses
                        "max_tokens": max_tokens,  # Use the safety limit
                    },
                    retries_enabled=False,
                )
            )

            # Process streaming response
            async for line in response.aiter_lines():
                if not line.strip():
                    continue

                if line.startswith("data: "):
                    data_str = line[6:]  # Remove "data: " prefix
                    if data_str.strip() == "[DONE]":
                        break

                    try:
                        chunk = json.loads(data_str)
                        if debug_response:
                            print(f"Chunk: {json.dumps(chunk, indent=2)}")

                        # Extract content from chunk
                        choices = chunk.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                collected_text += content

                                # Count tokens in collected text so far
                                actual_output_tokens = self._count_tokens(
                                    collected_text, model_id
                                )

                                # Check if we've exceeded the limit
                                if actual_output_tokens > max_tokens:
                                    tokens_exceeded = True
                                    # Cancel the request by breaking the loop
                                    break

                    except json.JSONDecodeError:
                        continue

            elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0

            # Create a mock response_json for compatibility
            response_json = {
                "choices": [{"message": {"content": collected_text}}],
                "usage": {
                    "prompt_tokens": self._count_tokens(throughput_prompt, model_id),
                    "completion_tokens": actual_output_tokens,
                    "total_tokens": self._count_tokens(throughput_prompt, model_id)
                    + actual_output_tokens,
                },
            }

            if debug_response:
                print("\n--- DEBUG FINAL RESPONSE ---")
                print(json.dumps(response_json, indent=2))
                print("--- END DEBUG ---\n")

        except Exception as e:
            elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
            base_url = "https://openrouter.ai/api/v1/chat/completions/"
            target = f"{base_url}{model_id}"
            if provider_name:
                target += f"@{provider_name}"
            time_str = (
                f"{elapsed_ms/1000:.2f}s"
                if elapsed_ms >= 1000.0
                else f"{int(elapsed_ms)}ms"
            )
            output_str = f"Benchmarking {target}:\n" f"Error: {e} (time={time_str})"
            return BenchmarkResult(
                success=False,
                elapsed_ms=elapsed_ms,
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                tokens_per_second=0.0,
                cost=0.0,
                output_str=output_str,
                tokens_exceeded=False,
                actual_output_tokens=0,
            )

        # Extract provider and token usage
        headers: Mapping[str, Any]
        if isinstance(response_headers, dict):
            headers = response_headers
        else:
            try:
                headers = cast(Mapping[str, Any], response_headers)
            except Exception:
                headers = {}
        headers_dict: dict[str, Any] = (
            dict(headers) if isinstance(headers, Mapping) else {}
        )
        response_json_typed: dict[str, Any] = cast(dict[str, Any], response_json)
        served_provider = (
            headers_dict.get("x-openrouter-provider")
            or headers_dict.get("x-provider")
            or response_json_typed.get("provider")
            or response_json_typed.get("meta", {}).get("provider")
        )

        # Usage tokens and cost
        usage = response_json_typed.get("usage", {})
        input_tokens = int(usage.get("prompt_tokens", 0))
        output_tokens = int(usage.get("completion_tokens", 0))
        total_tokens = input_tokens + output_tokens
        cost = usage.get("total_cost") or usage.get("cost")

        # Calculate tokens per second
        elapsed_seconds = elapsed_ms / 1000.0
        tokens_per_second = (
            output_tokens / elapsed_seconds if elapsed_seconds > 0 else 0.0
        )

        # Extract text content
        text_content = self._extract_message_text(response_json_typed)
        success = output_tokens > 0 and bool(text_content.strip())

        base_url = "https://openrouter.ai/api/v1/chat/completions/"
        target = f"{base_url}{model_id}"
        provider_for_print = str(provider_name or served_provider or "auto").strip()
        target_with_provider = f"{target}@{provider_for_print}"

        time_str = (
            f"{elapsed_seconds:.2f}s"
            if elapsed_seconds >= 1.0
            else f"{int(elapsed_ms)}ms"
        )
        # Format cost to two decimals for consistency
        cost_value = float(cost or 0.0)
        cost_display = f"{cost_value:.2f}"

        output_str = (
            f"Benchmarking {target_with_provider}:\n"
            f"Input tokens: {input_tokens}\n"
            f"Output tokens: {output_tokens}\n"
            f"Total tokens: {total_tokens}\n"
            f"Time: {time_str}\n"
            f"Throughput: {tokens_per_second:.2f} TPS (tokens per second)\n"
            f"Cost: ${cost_display}"
        )

        return BenchmarkResult(
            success=success,
            elapsed_ms=elapsed_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            tokens_per_second=tokens_per_second,
            cost=float(cost or 0.0),
            output_str=output_str,
            tokens_exceeded=tokens_exceeded,
            actual_output_tokens=actual_output_tokens,
        )

    async def execute(
        self,
        *,
        model_id: str,
        provider_name: str | None = None,
        timeout_seconds: int = 120,
        max_tokens: int = 3000,
        debug_response: bool = False,
        output_format: str = "table",
        throughput_prompt_override: str | None = None,
        **_: Any,
    ) -> str:
        """Execute the benchmark command once and return throughput metrics."""
        result = await self._benchmark_once(
            model_id=model_id,
            provider_name=provider_name,
            timeout_seconds=timeout_seconds,
            max_tokens=max_tokens,
            debug_response=debug_response,
            throughput_prompt_override=throughput_prompt_override,
        )
        fmt = (output_format or "table").lower()
        if fmt == "json":
            payload = {
                "model_id": model_id,
                "provider": provider_name or "Auto-selected",
                "status": "SUCCESS" if result.success else "FAILED",
                "duration_ms": result.elapsed_ms,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "total_tokens": result.total_tokens,
                "tps": result.tokens_per_second,
                "cost_usd": float(result.cost or 0.0),
                "tokens_exceeded": getattr(result, "tokens_exceeded", False),
                "actual_output_tokens": getattr(result, "actual_output_tokens", 0),
            }
            # Serialize using the existing JSON formatter for consistency
            import json as _json

            return _json.dumps(payload, indent=2, default=str)
        if fmt == "text":
            return f"TPS: {result.tokens_per_second:.2f}"

        # Use rich table formatting for beautiful output
        from ..formatters.table_formatter import TableFormatter

        if isinstance(self.table_formatter, TableFormatter):
            return self.table_formatter.format_benchmark_result(
                result=result, model_id=model_id, provider_name=provider_name
            )
        else:
            return f"Benchmark completed: {result.tokens_per_second:.2f} TPS"
