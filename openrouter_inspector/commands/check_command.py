"""Check command implementation."""

from __future__ import annotations

from typing import Any

from ..utils import normalize_string
from .base_command import BaseCommand


class CheckCommand(BaseCommand):
    """Command for checking model endpoint status."""

    async def execute(
        self,
        model_id: str,
        provider_name: str,
        endpoint_name: str,
        **kwargs: Any,
    ) -> str:
        """Execute the check command.

        Args:
            model_id: Model ID to check.
            provider_name: Provider name to check.
            endpoint_name: Endpoint name to check.
            **kwargs: Additional arguments.

        Returns:
            Status string ("Functional" or "Disabled").

        Raises:
            Exception: If provider/endpoint not found or other errors occur.
        """

        # Get providers for the model
        providers = await self.provider_handler.get_model_providers(model_id)
        if not providers:
            raise Exception(f"No providers found for model '{model_id}'.")

        # Find the target provider/endpoint combination
        target = None
        pn = normalize_string(provider_name)
        en = normalize_string(endpoint_name)

        for pd in providers:
            p = pd.provider
            if (
                normalize_string(p.provider_name) == pn
                and normalize_string(p.endpoint_name) == en
            ):
                target = pd
                break

        if target is None:
            # Provide helpful error messages with suggestions
            candidates = [
                pd.provider.endpoint_name or "—"
                for pd in providers
                if normalize_string(pd.provider.provider_name) == pn
            ]
            if candidates:
                suggestions = ", ".join(sorted(set(candidates))[:10])
                raise Exception(
                    f"Endpoint '{endpoint_name}' not found for provider '{provider_name}'. Candidates: {suggestions}"
                )
            raise Exception(
                f"Provider '{provider_name}' not found for model '{model_id}'."
            )

        # Check status
        status_val = (target.provider.status or "").strip().lower()
        is_error = status_val in ("disabled", "offline") or not target.availability

        return "Disabled" if is_error else "Functional"
