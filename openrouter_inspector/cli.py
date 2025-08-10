"""Command-line interface for OpenRouter CLI using Click."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from decimal import Decimal
from typing import Union

import click
import yaml
from rich import box
from rich.console import Console
from rich.table import Table

from . import client as client_mod
from . import services as services_mod
from .exceptions import APIError, AuthenticationError, RateLimitError
from .models import ModelInfo, ProviderDetails, SearchFilters

# Use a wider console to avoid cell truncation in tests
console = Console(width=200)
logger = logging.getLogger(__name__)


def fmt_money(value: Union[Decimal, float]) -> str:
    """Format a monetary value to 2 decimal places.

    Args:
        value: The monetary value to format (Decimal or float)

    Returns:
        A formatted string with exactly 2 decimal places
    """
    return f"{Decimal(value).quantize(Decimal('0.01')):.2f}"


def fmt_k(value: int) -> str:
    """Format a numeric value to thousands with K suffix.
    
    Args:
        value: The numeric value to format
        
    Returns:
        A formatted string with K suffix (e.g., 128000 -> 128K)
    """
    return f"{int(round(value / 1000))}K"


def fmt_price(value: float) -> str:
    """Format a price value to dollar amount with 2 decimal places.
    
    Args:
        value: The price value to format (per token)
        
    Returns:
        A formatted string with dollar sign and 2 decimal places (e.g., 0.000001 -> $1.00)
    """
    # Convert per-token price to per-million tokens price
    price_per_million = value * 1_000_000.0
    return f"${price_per_million:.2f}"


def _configure_logging(
    level_name: str | None, *, default_to_warning: bool = False
) -> None:
    """Configure root logging level.

    Defaults to WARNING if not provided or invalid.
    """
    if level_name is None:
        if not default_to_warning:
            return
        level_value = logging.WARNING
    else:
        try:
            level_value = getattr(logging, level_name.upper())
            if not isinstance(level_value, int):
                level_value = logging.WARNING
        except Exception:
            level_value = logging.WARNING
    root_logger = logging.getLogger()
    if root_logger.handlers:
        root_logger.setLevel(level_value)
    else:
        logging.basicConfig(level=level_value)


def _print_models(models: list[ModelInfo], output_format: str) -> None:
    if output_format == "json":
        click.echo(json.dumps([m.model_dump() for m in models], indent=2, default=str))
        return
    if output_format == "yaml":
        click.echo(yaml.safe_dump([m.model_dump() for m in models], sort_keys=False))
        return

    table = Table(title="OpenRouter Models", box=box.SIMPLE_HEAVY)
    table.add_column("Name", style="white", no_wrap=False, overflow="ellipsis", max_width=30)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Context", justify="right", max_width=8)
    table.add_column("Input", justify="right", max_width=9)
    table.add_column("Output", justify="right", max_width=9)
    for m in models:
        # Context column: model-level advertised context length (from /models). Per-provider context may differ.
        input_price = m.pricing.get("prompt")
        output_price = m.pricing.get("completion")
        input_price_str = fmt_price(input_price) if input_price is not None else "—"
        output_price_str = fmt_price(output_price) if output_price is not None else "—"
        table.add_row(m.name, m.id, fmt_k(m.context_length), input_price_str, output_price_str)
    console.print(table)


@click.group(invoke_without_command=True)
# Global lightweight mode: support --list and/or --search as alternative to subcommands
@click.option(
    "--list",
    "list_flag",
    is_flag=True,
    help="List models (optionally filter with --search)",
)
@click.option(
    "--search",
    "search_query",
    type=str,
    help="Search term. With --list filters the list; alone runs search",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json", "yaml"], case_sensitive=False),
    default="table",
)
@click.option(
    "--with-providers",
    is_flag=True,
    help="Show count of active providers per model (extra API calls)",
)
@click.option(
    "--sort-by",
    type=click.Choice(["id", "name", "context", "providers"], case_sensitive=False),
    default="id",
    help="Sort column for list output (default: id). 'providers' requires --with-providers",
)
@click.option("--desc", is_flag=True, help="Sort in descending order")
@click.option(
    "--log-level",
    "log_level",
    type=click.Choice(
        [
            "CRITICAL",
            "ERROR",
            "WARNING",
            "INFO",
            "DEBUG",
            "NOTSET",
        ],
        case_sensitive=False,
    ),
    help="Set logging level",
    envvar="OPENROUTER_LOG_LEVEL",
)
@click.pass_context
def cli(
    ctx: click.Context,
    list_flag: bool,
    search_query: str | None,
    output_format: str,
    with_providers: bool,
    sort_by: str,
    desc: bool,
    log_level: str | None,
) -> None:
    """OpenRouter Inspector - A lightweight CLI for exploring OpenRouter AI models.

    Subcommands:
      - list: list models
      - search: search models with filters
      - endpoints: detailed endpoints for a model
      - check: health check a provider endpoint (Functional/Degraded/Disabled)

    Or use lightweight flags:
      - --list [--search QUERY] to list models (optionally filtered)
      - --search QUERY to run a basic search

    Authentication:
      Set OPENROUTER_API_KEY environment variable with your API key.
    """
    # Logging
    _configure_logging(log_level, default_to_warning=True)

    # If no subcommand and no lightweight flags, show help without requiring config
    if ctx.invoked_subcommand is None and not (list_flag or search_query):
        click.echo(ctx.get_help())
        ctx.exit()

    # Get API key from environment when needed (commands or lightweight mode)
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise click.ClickException(
            "OPENROUTER_API_KEY is required. Set it in your environment and try again."
        )

    ctx.obj = {"api_key": api_key}

    # Lightweight mode if no subcommand provided
    if ctx.invoked_subcommand is None and (list_flag or search_query):

        async def _run_lightweight() -> None:
            async with client_mod.OpenRouterClient(api_key) as client:
                service = services_mod.ModelService(client)
                if list_flag:
                    models = await client.get_models()
                    # Optional filter via --search
                    if search_query:
                        q = search_query.lower()
                        models = [
                            m
                            for m in models
                            if q in m.id.lower() or q in m.name.lower()
                        ]
                    # Sorting (default by id ascending)
                    key_fn = (
                        (lambda m: m.id.lower())
                        if sort_by.lower() == "id"
                        else (
                            (lambda m: m.name.lower())
                            if sort_by.lower() == "name"
                            else (
                                (lambda m: m.context_length)
                                if sort_by.lower() == "context"
                                else None
                            )
                        )
                    )
                    if key_fn is not None:
                        models = sorted(models, key=key_fn, reverse=desc)

                    if output_format.lower() == "table" and with_providers:
                        rows = []
                        for m in models:
                            providers = await client.get_model_providers(m.id)
                            active = [
                                p
                                for p in providers
                                if p.availability and (p.provider.status != "offline")
                            ]
                            rows.append((m, len(active)))

                        # Sorting by providers if requested
                        if sort_by.lower() == "providers":
                            rows.sort(key=lambda t: t[1], reverse=desc)
                        elif sort_by.lower() in ("id", "name", "context"):
                            # keep the earlier sort on models list order
                            pass

                        table = Table(title="OpenRouter Models", box=box.SIMPLE_HEAVY)
                        table.add_column("Name", style="white", no_wrap=False, overflow="ellipsis", max_width=25)
                        table.add_column("ID", style="cyan", no_wrap=True)
                        table.add_column("Context", justify="right", max_width=8)
                        table.add_column("Input", justify="right", max_width=9)
                        table.add_column("Output", justify="right", max_width=9)
                        table.add_column("Providers", justify="right", max_width=10)
                        for m, cnt in rows:
                            input_price = m.pricing.get("prompt")
                            output_price = m.pricing.get("completion")
                            input_price_str = fmt_price(input_price) if input_price is not None else "—"
                            output_price_str = fmt_price(output_price) if output_price is not None else "—"
                            table.add_row(m.name, m.id, fmt_k(m.context_length), input_price_str, output_price_str, str(cnt))
                        console.print(table)
                    else:
                        _print_models(models, output_format.lower())
                else:
                    # search_query provided without --list: run semantic search
                    filters = SearchFilters(
                        min_context=None,
                        supports_tools=None,
                        reasoning_only=None,
                        max_price_per_token=None,
                    )
                    models = await service.search_models(search_query or "", filters)
                    _print_models(models, output_format.lower())

        try:
            asyncio.run(_run_lightweight())
        except (AuthenticationError, RateLimitError, APIError) as e:
            raise click.ClickException(str(e)) from e
        except Exception as e:
            raise click.ClickException(f"Unexpected error: {e}") from e
        # Exit after running lightweight mode
        ctx.exit()
    elif ctx.invoked_subcommand is None:
        # Should not reach here due to early help exit above
        click.echo(ctx.get_help())
        ctx.exit()


@cli.command("list")
@click.argument("filter", required=False)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json", "yaml"], case_sensitive=False),
    default="table",
)
@click.option(
    "--with-providers",
    is_flag=True,
    help="Show count of active providers per model (extra API calls)",
)
@click.option(
    "--sort-by",
    type=click.Choice(["id", "name", "context", "providers"], case_sensitive=False),
    default="id",
    help="Sort column for list output (default: id). 'providers' requires --with-providers",
)
@click.option("--desc", is_flag=True, help="Sort in descending order")
@click.option(
    "--log-level",
    "log_level",
    type=click.Choice(
        ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"],
        case_sensitive=False,
    ),
    help="Set logging level",
    envvar="OPENROUTER_LOG_LEVEL",
)
@click.pass_context
def list_models(
    ctx: click.Context,
    filter: str | None,
    output_format: str,
    with_providers: bool,
    sort_by: str,
    desc: bool,
    log_level: str | None,
) -> None:
    """List all available models. Optionally filter by substring."""
    _configure_logging(log_level)
    api_key: str = ctx.obj["api_key"]

    async def _run() -> None:
        async with client_mod.OpenRouterClient(api_key) as client:
            services_mod.ModelService(client)
            models = await client.get_models()
            if filter:
                q = filter.lower()
                models = [m for m in models if q in m.id.lower() or q in m.name.lower()]
            # Sorting before optional providers counting
            key_fn = (
                (lambda m: m.id.lower())
                if sort_by.lower() == "id"
                else (
                    (lambda m: m.name.lower())
                    if sort_by.lower() == "name"
                    else (
                        (lambda m: m.context_length)
                        if sort_by.lower() == "context"
                        else None
                    )
                )
            )
            if key_fn is not None:
                models = sorted(models, key=key_fn, reverse=desc)
            if output_format.lower() == "table" and with_providers:
                # Fetch provider counts (active only) per model
                rows = []
                for m in models:
                    providers = await client.get_model_providers(m.id)
                    # Active providers: status not offline and availability True
                    active = [
                        p
                        for p in providers
                        if p.availability and (p.provider.status != "offline")
                    ]
                    rows.append((m, len(active)))
                if sort_by.lower() == "providers":
                    rows.sort(key=lambda t: t[1], reverse=desc)

                table = Table(title="OpenRouter Models", box=box.SIMPLE_HEAVY)
                table.add_column("Name", style="white", no_wrap=False, overflow="ellipsis", max_width=25)
                table.add_column("ID", style="cyan", no_wrap=True)
                table.add_column("Context", justify="right", max_width=8)
                table.add_column("Input", justify="right", max_width=9)
                table.add_column("Output", justify="right", max_width=9)
                table.add_column("Providers", justify="right", max_width=10)
                for m, cnt in rows:
                    input_price = m.pricing.get("prompt")
                    output_price = m.pricing.get("completion")
                    input_price_str = fmt_price(input_price) if input_price is not None else "—"
                    output_price_str = fmt_price(output_price) if output_price is not None else "—"
                    table.add_row(m.name, m.id, fmt_k(m.context_length), input_price_str, output_price_str, str(cnt))
                console.print(table)
            else:
                _print_models(models, output_format.lower())

    try:
        asyncio.run(_run())
    except (AuthenticationError, RateLimitError, APIError) as e:
        raise click.ClickException(str(e)) from e
    except Exception as e:
        raise click.ClickException(f"Unexpected error: {e}") from e


@cli.command()
@click.argument("query", required=True)
@click.option("--min-context", type=int)
@click.option("--supports-tools", is_flag=True, default=None, flag_value=True)
@click.option("--no-supports-tools", is_flag=True, default=None, flag_value=False)
@click.option("--reasoning-only", is_flag=True, default=False)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json", "yaml"], case_sensitive=False),
    default="table",
)
@click.option(
    "--log-level",
    "log_level",
    type=click.Choice(
        ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"],
        case_sensitive=False,
    ),
    help="Set logging level",
    envvar="OPENROUTER_LOG_LEVEL",
)
@click.pass_context
def search(
    ctx: click.Context,
    query: str,
    min_context: int | None,
    supports_tools: bool | None,
    no_supports_tools: bool | None,
    reasoning_only: bool,
    output_format: str,
    log_level: str | None,
) -> None:
    """Search for models with optional filters."""
    _configure_logging(log_level)
    api_key: str = ctx.obj["api_key"]

    # Resolve mutually exclusive supports-tools flags
    st_value: bool | None
    if supports_tools is True and no_supports_tools is True:
        raise click.UsageError(
            "--supports-tools and --no-supports-tools cannot be used together"
        )
    st_value = True if supports_tools else (False if no_supports_tools else None)

    filters = SearchFilters(
        min_context=min_context,
        supports_tools=st_value,
        reasoning_only=reasoning_only or None,
        max_price_per_token=None,
    )

    async def _run() -> None:
        async with client_mod.OpenRouterClient(api_key) as client:
            service = services_mod.ModelService(client)
            models = await service.search_models(query, filters)
            _print_models(models, output_format.lower())

    try:
        asyncio.run(_run())
    except (AuthenticationError, RateLimitError, APIError) as e:
        raise click.ClickException(str(e)) from e
    except Exception as e:
        raise click.ClickException(f"Unexpected error: {e}") from e


@cli.command("endpoints")
@click.argument("model_id", required=True)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json", "yaml"], case_sensitive=False),
    default="table",
)
@click.option(
    "--per-1m",
    is_flag=True,
    help="Scale prices to per 1M tokens for prompt/completion (default)",
)
@click.option(
    "--min-quant",
    type=str,
    help="Minimum quantization (e.g., fp8). Unspecified quant is included.",
)
@click.option(
    "--min-context", type=str, help="Minimum context window (e.g., 128K or 131072)"
)
@click.option(
    "--reasoning",
    "reasoning_required",
    is_flag=True,
    default=None,
    help="Filter to offers supporting reasoning.",
)
@click.option(
    "--no-reasoning",
    "no_reasoning_required",
    is_flag=True,
    default=None,
    help="Filter to offers NOT supporting reasoning.",
)
@click.option(
    "--tools",
    "tools_required",
    is_flag=True,
    default=None,
    help="Filter to offers supporting tool calling.",
)
@click.option(
    "--no-tools",
    "no_tools_required",
    is_flag=True,
    default=None,
    help="Filter to offers NOT supporting tool calling.",
)
@click.option(
    "--img",
    "img_required",
    is_flag=True,
    default=None,
    help="Filter to offers supporting image input.",
)
@click.option(
    "--no-img",
    "no_img_required",
    is_flag=True,
    default=None,
    help="Filter to offers NOT supporting image input.",
)
@click.option(
    "--max-input-price",
    type=float,
    help="Maximum input token price (per million, USD).",
)
@click.option(
    "--max-output-price",
    type=float,
    help="Maximum output token price (per million, USD).",
)
@click.option(
    "--sort-by",
    type=click.Choice(
        [
            "api",
            "provider",
            "model",
            "quant",
            "context",
            "maxout",
            "price_in",
            "price_out",
        ],
        case_sensitive=False,
    ),
    default="api",
    help="Sort column for offers output (default: api = keep OpenRouter order)",
)
@click.option("--desc", is_flag=True, help="Sort in descending order")
@click.option(
    "--log-level",
    "log_level",
    type=click.Choice(
        ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"],
        case_sensitive=False,
    ),
    help="Set logging level",
    envvar="OPENROUTER_LOG_LEVEL",
)
@click.pass_context
def endpoints(
    ctx: click.Context,
    model_id: str,
    output_format: str,
    per_1m: bool,
    sort_by: str,
    desc: bool,
    min_quant: str | None,
    min_context: str | None,
    reasoning_required: bool | None,
    no_reasoning_required: bool | None,
    tools_required: bool | None,
    no_tools_required: bool | None,
    img_required: bool | None,
    no_img_required: bool | None,
    max_input_price: float | None,
    max_output_price: float | None,
    log_level: str | None,
) -> None:
    """Show detailed provider endpoints for an exact model id (author/slug).

    API-only. Fails if the model id is not exact or if no endpoints are returned.
    """
    _configure_logging(log_level)
    api_key: str = ctx.obj["api_key"]

    from typing import Sequence, cast

    async def _resolve_and_fetch(
        client: client_mod.OpenRouterClient,
        service: services_mod.ModelService,
        mid: str,
    ) -> tuple[str, list[ProviderDetails]]:
        """Try exact model id, otherwise attempt a unique partial match from /models."""
        # Try exact
        try:
            api_offers = await service.get_model_providers(mid)
            return mid, (api_offers or [])
        except Exception:
            pass

        # Search for candidates by substring
        try:
            all_models = await client.get_models()
        except Exception as e:
            logger.debug(f"Failed to get models list: {e}")
            return mid, []

        # Exact id not found; find partials
        s = mid.lower()
        candidates = [m for m in all_models if s in m.id.lower() or s in m.name.lower()]

        # Check for exact match in candidates (case-insensitive)
        exact_matches = [m for m in candidates if m.id.lower() == s]
        if exact_matches:
            resolved = exact_matches[0].id
            try:
                api_offers = await service.get_model_providers(resolved)
                return resolved, (api_offers or [])
            except Exception:
                return resolved, []

        # If multiple candidates, try each one until we find one that works
        if len(candidates) > 1:
            # Prefer non-free versions if available
            non_free_candidates = [m for m in candidates if ":free" not in m.id.lower()]
            if non_free_candidates:
                candidates = non_free_candidates

            # If still multiple, sort by ID length (prefer shorter IDs)
            candidates.sort(key=lambda m: len(m.id))

            # Try each candidate until we find one that works
            for candidate in candidates:
                try:
                    api_offers = await service.get_model_providers(candidate.id)
                    return candidate.id, (api_offers or [])
                except Exception as e:
                    logger.debug(f"Failed to get offers for {candidate.id}: {e}")
                    continue

            # If none worked, raise exception with all candidates
            candidate_names = "\n".join(
                f"- {m.id}  ({m.name})" for m in candidates[:20]
            )
            raise click.ClickException(
                f"No offers found for any of the candidate models:\n{candidate_names}"
            )

        # If exactly one candidate, use it
        if len(candidates) == 1:
            resolved = candidates[0].id
            try:
                api_offers = await service.get_model_providers(resolved)
                return resolved, (api_offers or [])
            except Exception:
                return resolved, []

        # None
        return mid, []

    async def _run() -> None:
        async with client_mod.OpenRouterClient(api_key) as client:
            service = services_mod.ModelService(client)
            resolved_id, offers = await _resolve_and_fetch(client, service, model_id)

            # Filtering helpers
            def parse_quant_bits(q: str | None) -> float:
                if not q:
                    return float("inf")  # treat unspecified as best
                s = q.lower()
                if "bf16" in s:
                    return 16
                # extract first integer in string
                num = ""
                for ch in s:
                    if ch.isdigit():
                        num += ch
                try:
                    return float(num) if num else 0.0
                except Exception:
                    return 0.0

            def parse_context_threshold(v: str | None) -> int:
                if v is None:
                    return 0
                s = str(v).strip()
                try:
                    if s.lower().endswith("k"):
                        return int(float(s[:-1]) * 1000)
                    return int(float(s))
                except Exception:
                    return 0

            min_bits = parse_quant_bits(min_quant) if min_quant else None
            min_ctx = parse_context_threshold(min_context) if min_context else 0

            from typing import Any as _Any

            def offer_passes(d: _Any) -> bool:
                p = d.provider

                # Existing filters
                if min_bits is not None:
                    if parse_quant_bits(p.quantization) < min_bits:
                        return False
                if min_ctx and (p.context_window or 0) < min_ctx:
                    return False

                # Reasoning filters
                if reasoning_required is not None or no_reasoning_required is not None:
                    sp = p.supported_parameters
                    reasoning_supported = False
                    if isinstance(sp, list):
                        reasoning_supported = any(
                            (
                                isinstance(x, str)
                                and (x == "reasoning" or x.startswith("reasoning"))
                            )
                            for x in sp
                        )
                    elif isinstance(sp, dict):
                        reasoning_supported = bool(sp.get("reasoning", False))

                    if reasoning_required and not reasoning_supported:
                        return False
                    if no_reasoning_required and reasoning_supported:
                        return False

                # Tools filters
                if tools_required is not None or no_tools_required is not None:
                    if tools_required and not p.supports_tools:
                        return False
                    if no_tools_required and p.supports_tools:
                        return False

                # Image filters
                if img_required is not None or no_img_required is not None:
                    sp = p.supported_parameters
                    image_supported = False
                    if isinstance(sp, list):
                        image_supported = any(
                            isinstance(x, str)
                            and (x == "image" or x.startswith("image"))
                            for x in sp
                        )
                    elif isinstance(sp, dict):
                        image_supported = bool(sp.get("image", False))

                    if img_required and not image_supported:
                        return False
                    if no_img_required and image_supported:
                        return False

                # Price filters
                if max_input_price is not None:
                    price_in = p.pricing.get("prompt") if p.pricing else None
                    if price_in is not None:
                        # Price is per token, convert to per million
                        price_in_per_million = price_in * 1_000_000.0
                        if price_in_per_million > max_input_price:
                            return False

                if max_output_price is not None:
                    price_out = p.pricing.get("completion") if p.pricing else None
                    if price_out is not None:
                        # Price is per token, convert to per million
                        price_out_per_million = price_out * 1_000_000.0
                        if price_out_per_million > max_output_price:
                            return False

                return True

            offers = [o for o in offers if offer_passes(o)]

            if output_format.lower() == "json":
                click.echo(
                    json.dumps([o.model_dump() for o in offers], indent=2, default=str)
                )
                return
            if output_format.lower() == "yaml":
                click.echo(
                    yaml.safe_dump([o.model_dump() for o in offers], sort_keys=False)
                )
                return

                # Sorting of offers (default preserves API order)
            if sort_by.lower() != "api" and offers:
                from typing import Any as _Any

                def key_offer(o: _Any) -> _Any:
                    p = o.provider
                    key = sort_by.lower()
                    if key == "provider":
                        return (p.provider_name or "").lower()
                    if key == "model":
                        return (p.endpoint_name or "").lower()
                    if key == "quant":
                        return (p.quantization or "").lower()
                    if key == "context":
                        return p.context_window or 0
                    if key == "maxout":
                        return p.max_completion_tokens or 0
                    if key == "price_in":
                        return (p.pricing or {}).get("prompt", float("inf"))
                    if key == "price_out":
                        return (p.pricing or {}).get("completion", float("inf"))
                    return (p.provider_name or "").lower()

                offers = sorted(offers, key=key_offer, reverse=desc)

            # Create table with appropriate title (API-only metrics)
            table = Table(title=f"Offers for {resolved_id}", box=box.SIMPLE_HEAVY)
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

            from typing import Any as _Any

            for d in cast(Sequence[_Any], offers):
                p = d.provider

                def fmt_k(v: int | None) -> str:
                    if v is None:
                        return "—"
                    return f"{int(round(v/1000))}K"

                # Per 1M tokens pricing
                price_in = p.pricing.get("prompt") if p.pricing else None
                price_out = p.pricing.get("completion") if p.pricing else None
                price_in = None if price_in is None else price_in * 1_000_000.0
                price_out = None if price_out is None else price_out * 1_000_000.0
                price_in_str = "—" if price_in is None else f"${fmt_money(price_in)}"
                price_out_str = "—" if price_out is None else f"${fmt_money(price_out)}"

                # Reasoning support inferred from supported_parameters (list or dict)
                sp = p.supported_parameters
                reasoning_supported = False
                if isinstance(sp, list):
                    reasoning_supported = any(
                        (
                            isinstance(x, str)
                            and (x == "reasoning" or x.startswith("reasoning"))
                        )
                        for x in sp
                    )
                elif isinstance(sp, dict):
                    reasoning_supported = bool(sp.get("reasoning", False))

                # Use provider's endpoint/model name; strip provider prefix if duplicated
                model_cell = p.endpoint_name or "—"
                if (
                    model_cell not in (None, "—")
                    and p.provider_name
                    and model_cell.lower().startswith(p.provider_name.lower())
                ):
                    trimmed = model_cell[len(p.provider_name) :].lstrip(" -_|:\t")
                    model_cell = trimmed or model_cell

                # Image support detection
                image_supported = False
                if isinstance(sp, list):
                    image_supported = any(
                        isinstance(x, str) and (x == "image" or x.startswith("image"))
                        for x in sp
                    )
                elif isinstance(sp, dict):
                    image_supported = bool(sp.get("image", False))

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
                    fmt_k(p.context_window),
                    fmt_k(p.max_completion_tokens),
                    price_in_str,
                    price_out_str,
                    uptime_str,
                )

            console.print(table)

    try:
        asyncio.run(_run())
    except (AuthenticationError, RateLimitError, APIError) as e:
        raise click.ClickException(str(e)) from e
    except Exception as e:
        raise click.ClickException(f"Unexpected error: {e}") from e


@cli.command("check")
@click.argument("model_id", required=True)
@click.argument("provider_name", required=True)
@click.argument("endpoint_name", required=True)
@click.option(
    "--log-level",
    "log_level",
    type=click.Choice(
        ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"],
        case_sensitive=False,
    ),
    help="Set logging level",
    envvar="OPENROUTER_LOG_LEVEL",
)
@click.pass_context
def check_command(
    ctx: click.Context,
    model_id: str,
    provider_name: str,
    endpoint_name: str,
    log_level: str | None,
) -> None:
    """Check model endpoint status via OpenRouter API flags only.

    Returns "OK" if the offer is not disabled or deprecated, "Error" otherwise.
    Exits with 0 for OK, 1 for Error.
    """
    _configure_logging(log_level)
    api_key: str = ctx.obj["api_key"]

    async def _run() -> None:
        def _norm(s: str | None) -> str:
            return (s or "").strip().lower()

        async with client_mod.OpenRouterClient(api_key) as client:
            providers = await client.get_model_providers(model_id)
            if not providers:
                raise click.ClickException(
                    f"No providers found for model '{model_id}'."
                )

            target = None
            pn = _norm(provider_name)
            en = _norm(endpoint_name)
            for pd in providers:
                p = pd.provider
                if _norm(p.provider_name) == pn and _norm(p.endpoint_name) == en:
                    target = pd
                    break

            if target is None:
                candidates = [
                    pd.provider.endpoint_name or "—"
                    for pd in providers
                    if _norm(pd.provider.provider_name) == pn
                ]
                if candidates:
                    suggestions = ", ".join(sorted(set(candidates))[:10])
                    raise click.ClickException(
                        f"Endpoint '{endpoint_name}' not found for provider '{provider_name}'. Candidates: {suggestions}"
                    )
                raise click.ClickException(
                    f"Provider '{provider_name}' not found for model '{model_id}'."
                )

            status_val = (target.provider.status or "").strip().lower()
            # Consider 'disabled', 'offline', or not available as an error state.
            # Assuming "deprecated" is reflected in one of these states.
            is_error = status_val in ("disabled", "offline") or not target.availability

            if is_error:
                click.echo("Disabled")
            else:
                click.echo("Functional")

    try:
        asyncio.run(_run())
    except (AuthenticationError, RateLimitError, APIError) as e:
        raise click.ClickException(str(e)) from e
    except Exception as e:
        raise click.ClickException(f"Unexpected error: {e}") from e
