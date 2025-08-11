"""Ping command implementation."""

from __future__ import annotations

import time
from typing import Any

from .base_command import BaseCommand


class PingCommand(BaseCommand):
    """Command to ping a model or a specific provider endpoint via chat completion."""

    async def execute(
        self,
        *,
        model_id: str,
        provider_name: str | None = None,
        timeout_seconds: int = 60,
        **_: Any,
    ) -> str:
        """Execute the ping command.

        Args:
            model_id: Model ID to test.
            provider_name: Optional specific provider to target.
            timeout_seconds: Timeout for the HTTP request in seconds.

        Returns:
            A single-line ping-like result string.
        """
        # Prepare request body
        messages = [
            {
                "role": "user",
                "content": "Hi! Let's play a game: when I say Ping, you reply with Pong. I say: Ping",
            }
        ]

        provider_order = [provider_name] if provider_name else None

        # Measure latency
        start_ns = time.perf_counter_ns()
        try:
            response_json, response_headers = await self.client.create_chat_completion(
                model=model_id,
                messages=messages,
                provider_order=provider_order,
                allow_fallbacks=False if provider_name else None,
                timeout_seconds=timeout_seconds,
                extra_headers={
                    # Optional attribution headers per OpenRouter docs
                    # Users may set environment-specific values at runtime
                },
                extra_body={
                    # Minimize/disable reasoning per OpenRouter unified interface
                    # https://openrouter.ai/docs/use-cases/reasoning-tokens
                    "reasoning": {"effort": "low", "exclude": True},
                    # Legacy compatibility flag
                    "include_reasoning": False,
                    # Cap completion to minimal expected size for Pong
                    "max_tokens": 4,
                },
            )
            elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
        except Exception as e:
            elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
            # Emit ping-like failure message
            base_url = "https://openrouter.ai/api/v1/chat/completions/"
            target = f"{base_url}{model_id}"
            if provider_name:
                target += f"@{provider_name}"
            # Dynamic time formatting (ms under 1s, else seconds with 2 decimals)
            time_str = (
                f"{elapsed_ms/1000:.2f}s"
                if elapsed_ms >= 1000.0
                else f"{int(elapsed_ms)}ms"
            )
            return (
                f"Pinging {target} with 0 input tokens:\n"
                f"Reply from: {target} tokens: 0 time={time_str} TTL={timeout_seconds}s (error: {e})"
            )

        # Extract provider and token usage
        # Provider might be present in headers or response meta; best-effort extraction
        served_provider = None
        try:
            # Some OpenRouter deployments include provider in headers
            served_provider = (
                response_headers.get("x-openrouter-provider")
                or response_headers.get("X-OpenRouter-Provider")
                or response_headers.get("x-provider")
                or response_headers.get("X-Provider")
                or response_headers.get("openrouter-provider")
                or response_headers.get("OpenRouter-Provider")
            )
        except Exception:
            served_provider = None

        if not served_provider:
            try:
                served_provider = response_json.get("provider") or response_json.get(
                    "meta", {}
                ).get("provider")
            except Exception:
                served_provider = None

        # Usage tokens and cost
        input_tokens = 0
        completion_tokens = 0
        cost_str: str | None = None
        try:
            usage = response_json.get("usage") or {}
            input_tokens = int(
                usage.get("prompt_tokens") or usage.get("input_tokens") or 0
            )
            completion_tokens = int(
                usage.get("completion_tokens") or usage.get("output_tokens") or 0
            )
            # Try total cost from JSON if available
            total_cost_val = usage.get("total_cost") or usage.get("cost")
            if total_cost_val is not None:
                cost_str = str(total_cost_val)
        except Exception:
            pass

        # Try provider cost from meta fields
        if cost_str is None:
            try:
                meta = response_json.get("meta") or {}
                cost_obj = meta.get("cost") or {}
                total_meta_cost = cost_obj.get("total") or cost_obj.get("usd")
                if total_meta_cost is not None:
                    cost_str = str(total_meta_cost)
            except Exception:
                pass

        # Try headers for cost
        if cost_str is None:
            try:
                cost_str = (
                    response_headers.get("x-openrouter-cost")
                    or response_headers.get("X-OpenRouter-Cost")
                    or response_headers.get("x-total-cost")
                    or response_headers.get("X-Total-Cost")
                )
            except Exception:
                cost_str = None

        # Extract text and validate Pong
        text_content = ""
        try:
            choices = response_json.get("choices") or []
            if choices:
                msg = choices[0].get("message") or {}
                text_content = str(msg.get("content") or "")
        except Exception:
            text_content = ""

        ok = "pong" in text_content.lower()

        base_url = "https://openrouter.ai/api/v1/chat/completions/"
        target = f"{base_url}{model_id}"
        provider_for_print = (provider_name or served_provider or "auto").strip()
        target_with_provider = f"{target}@{provider_for_print}"

        # Dynamic time formatting (ms under 1s, else seconds with 2 decimals)
        time_str = (
            f"{elapsed_ms/1000:.2f}s"
            if elapsed_ms >= 1000.0
            else f"{int(elapsed_ms)}ms"
        )

        # Build cost display: always include, even when free (show $0.00)
        cost_display = "0.00"
        if cost_str not in (None, ""):
            try:
                from decimal import Decimal

                dec = Decimal(str(cost_str))
                if dec == 0:
                    cost_display = "0.00"
                else:
                    # Preserve as-provided without rounding; use original string
                    cost_display = str(cost_str)
            except Exception:
                # If parsing fails but we have a string, use it as-is
                cost_display = str(cost_str)
        cost_part = f" cost: ${cost_display}"
        return (
            f"Pinging {target_with_provider} with {input_tokens} input tokens:\n"
            f"Reply from: {target_with_provider} tokens: {completion_tokens}{cost_part} time={time_str} TTL={timeout_seconds}s"
            + ("" if ok else "")
        )
