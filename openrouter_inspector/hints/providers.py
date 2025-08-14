"""Hint providers for different commands."""

from __future__ import annotations

from .context import HintContext


class ListHintProvider:
    """Provides hints for the list command."""

    def get_hints(self, context: HintContext) -> list[str]:
        """Get hints for the list command."""
        hints = []

        if context.example_model_id:
            hints.extend(
                [
                    "Show provider endpoints for a model:",
                    f"  openrouter-inspector endpoints {context.example_model_id}",
                ]
            )

        return hints


class EndpointsHintProvider:
    """Provides hints for the endpoints command."""

    def get_hints(self, context: HintContext) -> list[str]:
        """Get hints for the endpoints command."""
        hints = []

        if context.model_id and context.data:
            # Get first provider as example
            providers = context.data
            if providers and hasattr(providers[0], "provider"):
                first_provider = providers[0].provider.provider_name
                model_provider = f"{context.model_id}@{first_provider}"

                hints.extend(
                    [
                        "Show detailed parameters for a provider:",
                        f"  openrouter-inspector details {model_provider}",
                        "",
                        "Check latency:",
                        f"  openrouter-inspector ping {model_provider}",
                        "",
                        "Benchmark throughput:",
                        f"  openrouter-inspector benchmark {model_provider}",
                    ]
                )

        return hints


class DetailsHintProvider:
    """Provides hints for the details command."""

    def get_hints(self, context: HintContext) -> list[str]:
        """Get hints for the details command."""
        hints = []

        if context.model_id and context.provider_name:
            model_provider = f"{context.model_id}@{context.provider_name}"

            hints.extend(
                [
                    "Check latency:",
                    f"  openrouter-inspector ping {model_provider}",
                    "",
                    "Benchmark throughput:",
                    f"  openrouter-inspector benchmark {model_provider}",
                ]
            )

        return hints


class SearchHintProvider:
    """Provides hints for the search command."""

    def get_hints(self, context: HintContext) -> list[str]:
        """Get hints for the search command."""
        hints = []

        if context.example_model_id:
            hints.extend(
                [
                    "Show provider endpoints for a model:",
                    f"  openrouter-inspector endpoints {context.example_model_id}",
                ]
            )

        return hints
