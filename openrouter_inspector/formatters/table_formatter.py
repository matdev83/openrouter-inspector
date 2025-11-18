"""Table output formatter using Rich."""

from decimal import Decimal
from typing import Any

from rich import box
from rich.console import Console
from rich.table import Table

from ..models import ModelInfo, ProviderDetails
from .base import BaseFormatter


class TableFormatter(BaseFormatter):
    """Formats output as Rich tables."""

    def __init__(self, console: Console | None = None):
        """Initialize the table formatter.

        Args:
            console: Rich console instance. If None, creates a new one.
        """
        self.console = console or Console(width=200)

    def format_models(  # pylint: disable=too-many-locals,too-many-branches,too-many-statements,too-complex
        self, models: list[ModelInfo], **kwargs: Any
    ) -> str:
        """Format models as a Rich table.

        Args:
            models: List of ModelInfo objects to format
            **kwargs: Additional options:
                - with_providers: bool - Include provider count column
                - provider_counts: List[int] - Provider counts per model (if with_providers=True)
                - pricing_changes: List[tuple] - List of pricing changes for highlighting
                - new_models: List[ModelInfo] - List of new models to show separately

        Returns:
            Formatted table string
        """
        with_providers = kwargs.get("with_providers", False)
        provider_counts = kwargs.get("provider_counts", [])
        pricing_changes = kwargs.get("pricing_changes", [])
        new_models = kwargs.get("new_models", [])
        show_endpoints_hint: bool = kwargs.get("show_endpoints_hint", False)
        example_model_id: str | None = kwargs.get("example_model_id")

        # Create a set of model IDs with pricing changes for quick lookup
        pricing_change_models: dict[str, dict[str, tuple[Any, Any]]] = {}
        for model_id, field, old_val, new_val in pricing_changes:
            if model_id not in pricing_change_models:
                pricing_change_models[model_id] = {}
            pricing_change_models[model_id][field] = (old_val, new_val)

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

            # Check for pricing changes and apply highlighting
            input_style = None
            output_style = None
            if model.id in pricing_change_models:
                changes = pricing_change_models[model.id]
                if "prompt" in changes:
                    input_style = "bold yellow"
                if "completion" in changes:
                    output_style = "bold yellow"

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
                (
                    f"[{input_style}]{input_price_str}[/{input_style}]"
                    if input_style
                    else input_price_str
                ),
                (
                    f"[{output_style}]{output_price_str}[/{output_style}]"
                    if output_style
                    else output_price_str
                ),
            ]

            if with_providers and i < len(provider_counts):
                row_data.append(str(provider_counts[i]))

            table.add_row(*row_data)

        # Capture main table output as string
        output = ""
        with self.console.capture() as capture:
            self.console.print(table)
        output += capture.get()

        # Add new models table if there are any
        if new_models:
            output += "\n"
            new_table = Table(
                title="🆕 New Models Since Last Run", box=box.SIMPLE_HEAVY
            )
            new_table.add_column(
                "Name", style="white", no_wrap=False, overflow="ellipsis", max_width=25
            )
            new_table.add_column("ID", style="cyan", no_wrap=True)
            new_table.add_column("Context", justify="right", max_width=8)
            new_table.add_column("Input", justify="right", max_width=9)
            new_table.add_column("Output", justify="right", max_width=9)

            if with_providers:
                new_table.add_column("Providers", justify="right", max_width=10)

            for i, model in enumerate(new_models):
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
                    # For new models, provider counts might not be available
                    row_data.append("—")

                new_table.add_row(*row_data)

            with self.console.capture() as capture:
                self.console.print(new_table)
            output += capture.get()

        # Optional hint section (after tables)
        if show_endpoints_hint and models:
            # Choose an example model id when not provided
            model_example = example_model_id or models[0].id
            with self.console.capture() as capture:
                self.console.print()
                self.console.print("[bold]💡 Quick Commands:[/bold]")
                self.console.print()
                self.console.print("[dim]Show provider endpoints for a model:[/dim]")
                self.console.print(
                    f"  [cyan]openrouter-inspector endpoints {model_example}[/cyan]"
                )
            output += capture.get()

        return output

    def format_providers(  # pylint: disable=too-many-locals
        self, providers: list[ProviderDetails], **kwargs: Any
    ) -> str:
        """Format provider details as a Rich table.

        Args:
            providers: List of ProviderDetails objects to format
            **kwargs: Additional options:
                - model_id: str - Model ID for table title
                - no_hints: bool - Do not display helpful command hints below the table output

        Returns:
            Formatted table string
        """
        model_id = kwargs.get("model_id", "Unknown Model")
        kwargs.get("no_hints", False)

        table = Table(
            title=f"Endpoints for {model_id}",
            box=box.SIMPLE_HEAVY,
            expand=True,
            pad_edge=False,
        )
        table.add_column(
            "Provider",
            style="cyan",
            min_width=12,
            overflow="fold",
        )
        table.add_column(
            "Model",
            style="white",
            no_wrap=False,
            overflow="fold",
            min_width=18,
            max_width=40,
        )
        table.add_column("Reason", justify="center", min_width=6, no_wrap=True)
        table.add_column("Img", justify="center", min_width=3, no_wrap=True)
        table.add_column("Tools", justify="center", min_width=5, no_wrap=True)
        table.add_column("Quant", justify="left", min_width=6, overflow="fold")
        table.add_column("Context", justify="right", min_width=7)
        table.add_column("Max Out", justify="right", min_width=8)
        table.add_column("Input", justify="right", no_wrap=True, min_width=8)
        table.add_column("Output", justify="right", no_wrap=True, min_width=8)
        table.add_column("Uptime", justify="right", min_width=6)
        table.add_column("Status", justify="center", min_width=8)

        summary_lines: list[str] = []
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

            # Status formatting
            status_str, status_style = self._format_status(p.status, p.uptime_30min)

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
                (
                    f"[{status_style}]{status_str}[/{status_style}]"
                    if status_style
                    else status_str
                ),
            )

            summary_lines.append(
                " - ".join(
                    [
                        f"Provider {p.provider_name}",
                        f"Model '{model_cell}'",
                        f"Input {price_in_str}",
                        f"Output {price_out_str}",
                        f"Uptime {uptime_str}",
                        f"Status {status_str}",
                    ]
                )
            )

        # Capture table output as string
        with self.console.capture() as capture:
            self.console.print(table)
            # Add status legend
            self.console.print()
            self.console.print(
                "[dim]Status: [green]●[/green] Excellent (99%+), [yellow]●[/yellow] Good (95-99%), [red]●[/red] Poor (<95%), [red]✗[/red] Error[/dim]"
            )

        summary_text = ""
        if summary_lines:
            summary_text = (
                "\n"
                + f"Endpoints for {model_id}\n"
                + "Plain summary:\n"
                + "\n".join(f"  {line}" for line in summary_lines)
                + "\n"
            )

        return capture.get() + summary_text

    def format_benchmark_result(
        self, result: Any, model_id: str, provider_name: str | None = None
    ) -> str:
        """Format benchmark result as a Rich table.

        Args:
            result: BenchmarkResult object
            model_id: Model ID that was benchmarked
            provider_name: Provider name if specified

        Returns:
            Formatted table string
        """
        # Create main results table
        table = Table(title=f"Benchmark Results: {model_id}", box=box.ROUNDED)
        table.add_column("Metric", style="bold cyan", width=20)
        table.add_column("Value", style="bold white", width=25)
        table.add_column("Details", style="dim", width=40)

        # Format time display
        elapsed_seconds = result.elapsed_ms / 1000.0
        time_str = (
            f"{elapsed_seconds:.2f}s"
            if elapsed_seconds >= 1.0
            else f"{int(result.elapsed_ms)}ms"
        )

        # Format cost display in USD with two decimals (consistent app-wide)
        cost_str = f"${self._fmt_money(result.cost)}"
        cost_color = "green" if result.cost == 0 else "yellow"

        # Format TPS with color coding
        tps_color = (
            "green"
            if result.tokens_per_second > 50
            else "yellow" if result.tokens_per_second > 20 else "red"
        )

        # Success indicator
        status_text = "SUCCESS" if result.success else "FAILED"
        status_color = "green" if result.success else "red"

        # Provider info
        provider_display = provider_name or "Auto-selected"

        # Add rows to table
        table.add_row(
            "Status",
            f"[{status_color}]{status_text}[/{status_color}]",
            f"Provider: {provider_display}",
        )
        table.add_row("Duration", f"[bold]{time_str}[/bold]", "Total processing time")
        table.add_row(
            "Input Tokens",
            f"[cyan]{result.input_tokens:,}[/cyan]",
            "Prompt tokens consumed",
        )
        table.add_row(
            "Output Tokens",
            f"[cyan]{result.output_tokens:,}[/cyan]",
            "Response tokens generated",
        )
        table.add_row(
            "Total Tokens",
            f"[bold cyan]{result.total_tokens:,}[/bold cyan]",
            "Combined token usage",
        )
        table.add_row(
            "Throughput",
            f"[{tps_color}]{result.tokens_per_second:.2f} TPS[/{tps_color}]",
            "tokens per second",
        )
        table.add_row(
            "Cost", f"[{cost_color}]{cost_str}[/{cost_color}]", "API usage cost"
        )

        # Add safety information if applicable
        if hasattr(result, "tokens_exceeded") and result.tokens_exceeded:
            table.add_row(
                "Safety Limit",
                "[red]EXCEEDED[/red]",
                f"Stopped at {result.actual_output_tokens} tokens",
            )

        # Capture table output
        with self.console.capture() as capture:
            # Add a simple preface line for compatibility with tests and CLI expectations
            provider_display_for_prefix = provider_display or "Auto-selected"
            self.console.print(f"Benchmarking {model_id}@{provider_display_for_prefix}")
            self.console.print(table)

        return capture.get()

    def _fmt_money(self, value: Decimal | float) -> str:
        """Format a monetary value to 2 decimal places."""
        return f"{Decimal(value).quantize(Decimal('0.01')):.2f}"

    def _fmt_k(self, value: int | None) -> str:
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

    def format_model_details(  # pylint: disable=too-many-locals
        self,
        provider_detail: Any,
        model_id: str,
        provider_name: str,
        no_hints: bool = False,
    ) -> str:
        """Format detailed model parameters and features as a Rich table.

        Args:
            provider_detail: ProviderDetails object containing the endpoint information
            model_id: Model ID for display
            provider_name: Provider name for display
            no_hints: Do not display helpful command hints below the table output

        Returns:
            Formatted table string with details and command hints
        """
        del no_hints  # Handled by command layer via hint system
        p = provider_detail.provider

        # Create main details table
        table = Table(
            title=f"Model Details: {model_id} @ {provider_name}",
            box=box.ROUNDED,
            show_header=True,
        )
        table.add_column("Parameter", style="bold cyan", width=25)
        table.add_column("Value", style="bold white", width=30)
        table.add_column("Description", style="dim", width=50)

        # Basic model information
        table.add_row("Model ID", f"[cyan]{model_id}[/cyan]", "Unique model identifier")
        table.add_row(
            "Provider", f"[cyan]{p.provider_name}[/cyan]", "Hosting provider name"
        )

        # Endpoint name if available
        if p.endpoint_name and p.endpoint_name != "—":
            table.add_row(
                "Endpoint Name",
                f"[white]{p.endpoint_name}[/white]",
                "Provider's internal model name",
            )

        # Context and token limits
        table.add_row(
            "Context Window",
            f"[bold green]{self._fmt_k(p.context_window)}[/bold green]",
            "Maximum input context size",
        )

        if p.max_completion_tokens:
            table.add_row(
                "Max Output Tokens",
                f"[bold green]{self._fmt_k(p.max_completion_tokens)}[/bold green]",
                "Maximum output tokens per request",
            )

        # Pricing information
        if p.pricing:
            input_price = p.pricing.get("prompt")
            output_price = p.pricing.get("completion")

            if input_price is not None:
                price_per_million = input_price * 1_000_000.0
                table.add_row(
                    "Input Price",
                    f"[yellow]${self._fmt_money(price_per_million)}[/yellow]",
                    "Cost per million input tokens (USD)",
                )

            if output_price is not None:
                price_per_million = output_price * 1_000_000.0
                table.add_row(
                    "Output Price",
                    f"[yellow]${self._fmt_money(price_per_million)}[/yellow]",
                    "Cost per million output tokens (USD)",
                )

        # Model capabilities
        reasoning_supported = self._check_reasoning_support(p.supported_parameters)
        image_supported = self._check_image_support(p.supported_parameters)
        tools_supported = p.supports_tools

        table.add_row(
            "Reasoning Support",
            f"[{'green' if reasoning_supported else 'red'}]{'✓ Yes' if reasoning_supported else '✗ No'}[/{'green' if reasoning_supported else 'red'}]",
            "Supports reasoning/chain-of-thought",
        )

        table.add_row(
            "Tool Calling",
            f"[{'green' if tools_supported else 'red'}]{'✓ Yes' if tools_supported else '✗ No'}[/{'green' if tools_supported else 'red'}]",
            "Supports function/tool calling",
        )

        table.add_row(
            "Image Input",
            f"[{'green' if image_supported else 'red'}]{'✓ Yes' if image_supported else '✗ No'}[/{'green' if image_supported else 'red'}]",
            "Supports multimodal image inputs",
        )

        # Technical details
        if p.quantization and p.quantization.lower() not in ["unknown", "—"]:
            table.add_row(
                "Quantization",
                f"[magenta]{p.quantization}[/magenta]",
                "Model quantization method",
            )

        # Performance and reliability
        table.add_row(
            "Uptime (30min)",
            f"[{'green' if p.uptime_30min >= 99 else 'yellow' if p.uptime_30min >= 95 else 'red'}]{p.uptime_30min:.1f}%[/{'green' if p.uptime_30min >= 99 else 'yellow' if p.uptime_30min >= 95 else 'red'}]",
            "Recent availability percentage",
        )

        if p.performance_tps:
            table.add_row(
                "Performance",
                f"[cyan]{p.performance_tps:.1f} TPS[/cyan]",
                "Reported tokens per second",
            )

        # Status
        status_str, status_style = self._format_status(p.status, p.uptime_30min)
        table.add_row(
            "Status",
            (
                f"[{status_style}]{status_str}[/{status_style}]"
                if status_style
                else status_str
            ),
            "Current endpoint status",
        )

        # Capture table output
        with self.console.capture() as capture:
            self.console.print(table)
            self.console.print()

            # Note: Hints are now handled by the command layer using the hint system

        return capture.get()

    def _format_status(  # pylint: disable=too-many-return-statements
        self, status: str | None, uptime: float
    ) -> tuple[str, str | None]:
        """Format endpoint status with appropriate styling.

        Args:
            status: The status string from the API (e.g., "offline", "-5", etc.)
            uptime: The uptime percentage for additional context

        Returns:
            Tuple of (status_text, style_name) where style_name can be None
        """
        if not status:
            return "—", None

        # Normalize status for comparison
        status_lower = status.lower().strip()

        # Handle different status values
        if status_lower == "offline":
            # For "offline" status, use uptime as the primary indicator
            if uptime >= 99.0:
                return "●", "green"  # Excellent uptime despite "offline" status
            elif uptime >= 95.0:
                return "●", "yellow"  # Good uptime, minor issues
            elif uptime >= 80.0:
                return "●", "red"  # Moderate uptime, concerning
            else:
                return "●", "bright_red"  # Poor uptime, major issues
        elif status_lower == "online":
            return "●", "bright_green"  # Explicitly online - excellent
        elif status_lower.startswith("-") or (
            status_lower.isdigit() and status_lower != "0"
        ):
            # Error codes (like "-5")
            return "✗", "red"  # Error status
        elif status_lower in ["available", "active", "ready", "up"]:
            return "●", "green"  # Available variants
        elif status_lower in ["unavailable", "inactive", "down", "error"]:
            return "●", "red"  # Unavailable variants
        else:
            # Unknown status - show as-is with neutral styling
            return status[:3], "dim"  # Truncate to 3 chars max
