"""Table output formatter using Rich."""

from decimal import Decimal
from typing import Any, List, Optional, Union

from rich import box
from rich.console import Console
from rich.table import Table

from ..models import ModelInfo, ProviderDetails
from .base import BaseFormatter


class TableFormatter(BaseFormatter):
    """Formats output as Rich tables."""

    def __init__(self, console: Optional[Console] = None):
        """Initialize the table formatter.

        Args:
            console: Rich console instance. If None, creates a new one.
        """
        self.console = console or Console(width=200)

    def format_models(self, models: List[ModelInfo], **kwargs: Any) -> str:
        """Format models as a Rich table.

        Args:
            models: List of ModelInfo objects to format
            **kwargs: Additional options:
                - with_providers: bool - Include provider count column
                - provider_counts: List[int] - Provider counts per model (if with_providers=True)

        Returns:
            Formatted table string
        """
        with_providers = kwargs.get("with_providers", False)
        provider_counts = kwargs.get("provider_counts", [])

        table = Table(title="OpenRouter Models", box=box.SIMPLE_HEAVY)
        table.add_column(
            "Name", style="white", no_wrap=False, overflow="ellipsis", max_width=25
        )
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Context", justify="right", max_width=8)
        table.add_column("Input", justify="right", max_width=9)
        table.add_column("Output", justify="right", max_width=9)

        if with_providers:
            table.add_column("Providers", justify="right", max_width=10)

        for i, model in enumerate(models):
            input_price = model.pricing.get("prompt")
            output_price = model.pricing.get("completion")
            input_price_str = (
                self._fmt_price(input_price) if input_price is not None else "—"
            )
            output_price_str = (
                self._fmt_price(output_price) if output_price is not None else "—"
            )

            row_data = [
                model.name,
                model.id,
                self._fmt_k(model.context_length),
                input_price_str,
                output_price_str,
            ]

            if with_providers and i < len(provider_counts):
                row_data.append(str(provider_counts[i]))

            table.add_row(*row_data)

        # Capture table output as string
        with self.console.capture() as capture:
            self.console.print(table)
        return capture.get()

    def format_providers(self, providers: List[ProviderDetails], **kwargs: Any) -> str:
        """Format provider details as a Rich table.

        Args:
            providers: List of ProviderDetails objects to format
            **kwargs: Additional options:
                - model_id: str - Model ID for table title

        Returns:
            Formatted table string
        """
        model_id = kwargs.get("model_id", "Unknown Model")

        table = Table(title=f"Offers for {model_id}", box=box.SIMPLE_HEAVY)
        table.add_column("Provider", style="cyan")
        table.add_column(
            "Model", style="white", no_wrap=False, overflow="ellipsis", max_width=30
        )
        table.add_column("Reason", justify="center")
        table.add_column("Img", justify="center")
        table.add_column("Tools", justify="center")
        table.add_column("Quant", justify="left")
        table.add_column("Context", justify="right")
        table.add_column("Max Out", justify="right")
        table.add_column("Input", justify="right", no_wrap=True)
        table.add_column("Output", justify="right", no_wrap=True)
        table.add_column("Uptime", justify="right")

        for provider_detail in providers:
            p = provider_detail.provider

            # Per 1M tokens pricing
            price_in = p.pricing.get("prompt") if p.pricing else None
            price_out = p.pricing.get("completion") if p.pricing else None
            price_in = None if price_in is None else price_in * 1_000_000.0
            price_out = None if price_out is None else price_out * 1_000_000.0
            price_in_str = "—" if price_in is None else f"${self._fmt_money(price_in)}"
            price_out_str = (
                "—" if price_out is None else f"${self._fmt_money(price_out)}"
            )

            # Reasoning support inferred from supported_parameters
            reasoning_supported = self._check_reasoning_support(p.supported_parameters)

            # Image support detection
            image_supported = self._check_image_support(p.supported_parameters)

            # Use provider's endpoint/model name; strip provider prefix if duplicated
            model_cell = p.endpoint_name or "—"
            if (
                model_cell not in (None, "—")
                and p.provider_name
                and model_cell.lower().startswith(p.provider_name.lower())
            ):
                trimmed = model_cell[len(p.provider_name) :].lstrip(" -_|:\t")
                model_cell = trimmed or model_cell

            # Tools support
            tools_supported = p.supports_tools

            # Uptime
            uptime_str = f"{p.uptime_30min:.1f}%"

            # Prepare row
            table.add_row(
                p.provider_name,
                model_cell,
                "+" if reasoning_supported else "-",
                "+" if image_supported else "-",
                "+" if tools_supported else "-",
                (
                    "—"
                    if not p.quantization or p.quantization.lower() == "unknown"
                    else p.quantization
                ),
                self._fmt_k(p.context_window),
                self._fmt_k(p.max_completion_tokens),
                price_in_str,
                price_out_str,
                uptime_str,
            )

        # Capture table output as string
        with self.console.capture() as capture:
            self.console.print(table)
        return capture.get()

    def _fmt_money(self, value: Union[Decimal, float]) -> str:
        """Format a monetary value to 2 decimal places."""
        return f"{Decimal(value).quantize(Decimal('0.01')):.2f}"

    def _fmt_k(self, value: Optional[int]) -> str:
        """Format a numeric value to thousands with K suffix."""
        if value is None:
            return "—"
        return f"{int(round(value / 1000))}K"

    def _fmt_price(self, value: float) -> str:
        """Format a price value to dollar amount with 2 decimal places."""
        # Convert per-token price to per-million tokens price
        price_per_million = value * 1_000_000.0
        return f"${price_per_million:.2f}"

    def _check_reasoning_support(self, supported_parameters: Any) -> bool:
        """Check if reasoning is supported based on supported_parameters."""
        if isinstance(supported_parameters, list):
            return any(
                isinstance(x, str) and (x == "reasoning" or x.startswith("reasoning"))
                for x in supported_parameters
            )
        elif isinstance(supported_parameters, dict):
            return bool(supported_parameters.get("reasoning", False))
        return False

    def _check_image_support(self, supported_parameters: Any) -> bool:
        """Check if image input is supported based on supported_parameters."""
        if isinstance(supported_parameters, list):
            return any(
                isinstance(x, str) and (x == "image" or x.startswith("image"))
                for x in supported_parameters
            )
        elif isinstance(supported_parameters, dict):
            return bool(supported_parameters.get("image", False))
        return False
