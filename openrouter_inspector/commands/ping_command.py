"""Ping command implementation."""

from __future__ import annotations

import asyncio
import json
import statistics
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .base_command import BaseCommand


@dataclass
class PingResult:
    """Dataclass to store the result of a single ping."""

    success: bool
    elapsed_ms: float
    cost: float | None
    output_str: str


class PingCommand(BaseCommand):
    """Command to ping a model or a specific provider endpoint via chat completion."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._last_all_success: bool | None = None

    def _load_ping_prompt(self) -> str:
        """Load the ping prompt from the config file."""
        prompt_path = Path("config/prompts/ping.md")
        try:
            if prompt_path.exists():
                return prompt_path.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeDecodeError):
            # Ignore file I/O/encoding errors and fall back to default prompt
            ...
        # Fallback to default prompt if file doesn't exist or can't be read
        return "Respond exactly with Pong. No punctuation, no additional text, no explanations. Output only: Pong"

    @property
    def last_all_success(self) -> bool | None:
        return self._last_all_success

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

    async def _ping_once(
        self,
        *,
        model_id: str,
        provider_name: str | None = None,
        timeout_seconds: int = 60,
        debug_response: bool = False,
    ) -> PingResult:
        """Execute a single ping.

        Returns:
            A PingResult object with the outcome.
        """
        # Prepare request body
        ping_prompt = self._load_ping_prompt()
        messages = [
            {
                "role": "user",
                "content": ping_prompt,
            }
        ]

        provider_order = [provider_name] if provider_name else None

        # Format the target URL for display
        base_url = "https://openrouter.ai/api/v1/chat/completions/"
        target = f"{base_url}{model_id}"
        if provider_name:
            target += f"@{provider_name}"

        # Measure latency
        start_ns = time.perf_counter_ns()
        try:
            response_json, response_headers = await self.client.create_chat_completion(
                model=model_id,
                messages=messages,
                provider_order=provider_order,
                allow_fallbacks=False if provider_name else None,
                timeout_seconds=timeout_seconds,
                extra_headers={},
                extra_body={
                    "temperature": 0,
                    "top_p": 0,
                    "response_format": {"type": "text"},
                    # Keep reasoning to minimal and exclude it from the visible output
                    "reasoning": {"effort": "minimal", "exclude": True},
                    "include_reasoning": False,
                    "max_tokens": 64,
                },
                retries_enabled=False,
                silent_rate_limit=True,
            )
            elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
            if debug_response:
                print("\n--- DEBUG RESPONSE ---")
                print(json.dumps(response_json, indent=2))
                print("--- END DEBUG ---\n")

            # Extract provider and token usage
            served_provider = (
                response_headers.get("x-openrouter-provider")
                or response_headers.get("x-provider")
                or response_json.get("provider")
                or response_json.get("meta", {}).get("provider")
            )

            # Usage tokens and cost
            usage = response_json.get("usage", {})
            completion_tokens = int(usage.get("completion_tokens", 0))
            cost = usage.get("total_cost") or usage.get("cost")

            # Extract text and validate Pong
            text_content = self._extract_message_text(response_json)
            ok = "pong" in (text_content or "").lower()
            if not ok:
                # Fallback: consider success if the model produced any completion tokens
                # (some reasoning providers may hide content while still responding)
                ok = completion_tokens > 0

            # Format the display provider
            provider_for_print = (provider_name or served_provider or "auto").strip()
            target_with_provider = f"{target.replace('@'+provider_name if provider_name else '', '')}@{provider_for_print}"

            # Format the time string
            time_str = (
                f"{elapsed_ms/1000:.2f}s"
                if elapsed_ms >= 1000.0
                else f"{int(elapsed_ms)}ms"
            )

            # Format the cost display
            cost_display = f"{cost:.6f}" if cost is not None else "0.00"
            cost_part = f" cost: ${cost_display}"

            # Successful ping output
            output_str = f"Reply from: {target_with_provider} tokens: {completion_tokens}{cost_part} time={time_str} TTL={timeout_seconds}s"

            return PingResult(
                success=ok,
                elapsed_ms=elapsed_ms,
                cost=float(cost or 0.0),
                output_str=output_str,
            )

        except Exception as e:
            # Failed ping - don't show response time
            output_str = f"Request failed: {target} (error: {e})"

            return PingResult(
                success=False,
                elapsed_ms=(time.perf_counter_ns() - start_ns) / 1_000_000.0,
                cost=0.0,
                output_str=output_str,
            )

    async def execute(
        self,
        *,
        model_id: str,
        provider_name: str | None = None,
        timeout_seconds: int = 60,
        count: int = 3,
        debug_response: bool = False,
        on_progress: Callable[[str], Any] | None = None,
        **_: Any,
    ) -> str:
        """Execute the ping command multiple times and gather statistics."""
        results: list[PingResult] = []
        all_output_parts: list[str] = []

        # Construct the target URL for display
        base_url = "https://openrouter.ai/api/v1/chat/completions/"
        target = f"{base_url}{model_id}"
        if provider_name:
            target += f"@{provider_name}"

        # Show initial ping message
        ping_header = f"Pinging {target} with OpenRouter API:"
        all_output_parts.append(ping_header)
        if on_progress is not None:
            await self._maybe_await(on_progress(ping_header))

        for i in range(count):
            result = await self._ping_once(
                model_id=model_id,
                provider_name=provider_name,
                timeout_seconds=timeout_seconds,
                debug_response=debug_response,
            )
            results.append(result)

            # Display the result
            if result.success:
                # For successful pings, show the full output with time
                output_line = result.output_str
            else:
                # For failed pings, just show the error message without time
                output_line = result.output_str

            all_output_parts.append(output_line)
            if on_progress is not None:
                await self._maybe_await(on_progress(output_line))

            if i < count - 1:
                await asyncio.sleep(1)  # Pause between pings

        # --- Statistics ---
        sent = len(results)
        received = sum(1 for r in results if r.success)
        lost = sent - received
        loss_percent = (lost / sent) * 100 if sent > 0 else 0

        successful_times_ms = [r.elapsed_ms for r in results if r.success]
        total_cost = sum(r.cost for r in results if r.cost is not None)

        stats_parts = [
            f"\nPing statistics for {model_id}@{provider_name or 'auto'}:",
            f"    Packets: Sent = {sent}, Received = {received}, Lost = {lost} ({loss_percent:.0f}% loss),",
        ]

        if successful_times_ms:
            successful_times_s = [t / 1000.0 for t in successful_times_ms]
            stats_parts.extend(
                [
                    "Approximate round trip times in seconds:",
                    f"    Minimum = {min(successful_times_s):.2f}s, Maximum = {max(successful_times_s):.2f}s, Average = {statistics.mean(successful_times_s):.2f}s",
                ]
            )

        stats_parts.append(f"Total API cost for this run: ${total_cost:.6f}")

        all_output_parts.extend(stats_parts)
        all_output_parts.append("")  # End with a newline

        # Stream final stats if requested
        if on_progress is not None:
            await self._maybe_await(on_progress("\n".join(stats_parts)))
            await self._maybe_await(on_progress(""))

        # Store success flag for CLI to read
        self._last_all_success = lost == 0

        return "\n".join(all_output_parts)
