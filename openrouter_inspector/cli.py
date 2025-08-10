"""Command-line interface for OpenRouter CLI using Click."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Optional

import click
import yaml
from rich.console import Console
import logging
from rich.table import Table
from rich import box

from .client import OpenRouterClient
from .config import Config
from .models import SearchFilters, ModelInfo, ProviderDetails
from .services import ModelService
from .exceptions import AuthenticationError, APIError, RateLimitError, OpenRouterError


console = Console()


def _print_models(models: list[ModelInfo], output_format: str) -> None:
    if output_format == "json":
        click.echo(json.dumps([m.model_dump() for m in models], indent=2, default=str))
        return
    if output_format == "yaml":
        click.echo(yaml.safe_dump([m.model_dump() for m in models], sort_keys=False))
        return

    table = Table(title="OpenRouter Models")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Context", justify="right")
    for m in models:
        # Context column: model-level advertised context length (from /models). Per-provider context may differ.
        table.add_row(m.id, m.name, str(m.context_length))
    console.print(table)


def _print_providers(providers: list[ProviderDetails], output_format: str, per_1k: bool = False) -> None:
    if output_format == "json":
        click.echo(json.dumps([p.model_dump() for p in providers], indent=2, default=str))
        return
    if output_format == "yaml":
        click.echo(yaml.safe_dump([p.model_dump() for p in providers], sort_keys=False))
        return

    table = Table(title="Providers")
    table.add_column("Provider", style="cyan")
    table.add_column("Status", justify="left")
    table.add_column("Uptime 30m", justify="right")
    table.add_column("Context", justify="right")
    table.add_column("Max Out", justify="right")
    table.add_column("Tools", justify="center")
    table.add_column("Reasoning", justify="center")
    table.add_column("Quant", justify="left")
    table.add_column("Price In", justify="right")
    table.add_column("Price Out", justify="right")
    for d in providers:
        p = d.provider
        price_in = p.pricing.get("prompt") if p.pricing else None
        price_out = p.pricing.get("completion") if p.pricing else None
        if per_1k:
            price_in = None if price_in is None else price_in * 1000.0
            price_out = None if price_out is None else price_out * 1000.0
        price_in_str = "—" if price_in is None else f"${price_in:.6f}/1K" if per_1k else f"${price_in:.8f}"
        price_out_str = "—" if price_out is None else f"${price_out:.6f}/1K" if per_1k else f"${price_out:.8f}"

        table.add_row(
            p.provider_name,
            p.status or "—",
            f"{p.uptime_30min:.1f}%",
            str(p.context_window),
            "—" if p.max_completion_tokens is None else str(p.max_completion_tokens),
            "✓" if p.supports_tools else "—",
            "✓" if p.is_reasoning_model else "—",
            p.quantization or "—",
            price_in_str,
            price_out_str,
        )
    console.print(table)


@click.group(invoke_without_command=True)
@click.option("--config-file", type=click.Path(path_type=Path), help="Path to config file (json/toml)")
# Global lightweight mode: support --list and/or --search as alternative to subcommands
@click.option("--list", "list_flag", is_flag=True, help="List models (optionally filter with --search)")
@click.option("--search", "search_query", type=str, help="Search term. With --list filters the list; alone runs search")
@click.option("--format", "output_format", type=click.Choice(["table", "json", "yaml"], case_sensitive=False), default="table")
@click.option("--with-providers", is_flag=True, help="Show count of active providers per model (extra API calls)")
@click.option(
    "--sort-by",
    type=click.Choice(["id", "name", "context", "providers"], case_sensitive=False),
    default="id",
    help="Sort column for list output (default: id). 'providers' requires --with-providers",
)
@click.option("--desc", is_flag=True, help="Sort in descending order")
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.pass_context
def cli(ctx: click.Context, config_file: Optional[Path], list_flag: bool, search_query: Optional[str], output_format: str, with_providers: bool, sort_by: str, desc: bool, debug: bool) -> None:
    """OpenRouter CLI tool for querying AI models and providers.

    You can use subcommands (list/search/providers) or lightweight flags:
      - --list [--search QUERY] to list models, optionally filtered
      - --search QUERY to run a basic search
    """
    # Logging
    # Configure root logger; default to WARNING to be quiet unless --debug
    logging.basicConfig(level=logging.DEBUG if debug else logging.WARNING)

    config: Config
    try:
        if config_file is not None:
            # from_sources handles precedence; pass-through for convenience
            config = Config.from_sources(config_file=config_file)
        else:
            # Environment/defaults
            config = Config.from_sources()
    except ValueError:
        raise click.ClickException(
            "OPENROUTER_API_KEY is required. Set it in your environment and try again."
        )

    ctx.obj = {
        "config": config
    }

    # Lightweight mode if no subcommand provided
    if ctx.invoked_subcommand is None and (list_flag or search_query):
        async def _run_lightweight() -> None:
            async with OpenRouterClient(config) as client:
                service = ModelService(client)
                if list_flag:
                    models = await client.get_models()
                    # Optional filter via --search
                    if search_query:
                        q = search_query.lower()
                        models = [m for m in models if q in m.id.lower() or q in m.name.lower()]
                    # Sorting (default by id ascending)
                    key_fn = (
                        (lambda m: m.id.lower()) if sort_by.lower() == "id" else
                        (lambda m: m.name.lower()) if sort_by.lower() == "name" else
                        (lambda m: m.context_length) if sort_by.lower() == "context" else
                        None
                    )
                    if key_fn is not None:
                        models = sorted(models, key=key_fn, reverse=desc)

                    if output_format.lower() == "table" and with_providers:
                        rows = []
                        for m in models:
                            providers = await client.get_model_providers(m.id)
                            active = [p for p in providers if p.availability and (p.provider.status != "offline")]
                            rows.append((m, len(active)))

                        # Sorting by providers if requested
                        if sort_by.lower() == "providers":
                            rows.sort(key=lambda t: t[1], reverse=desc)
                        elif sort_by.lower() in ("id", "name", "context"):
                            # keep the earlier sort on models list order
                            pass

                        table = Table(title="OpenRouter Models")
                        table.add_column("ID", style="cyan")
                        table.add_column("Name", style="white")
                        table.add_column("Context", justify="right")
                        table.add_column("Providers", justify="right")
                        for m, cnt in rows:
                            table.add_row(m.id, m.name, str(m.context_length), str(cnt))
                        console.print(table)
                    else:
                        _print_models(models, output_format.lower())
                else:
                    # search_query provided without --list: run semantic search
                    filters = SearchFilters(min_context=None, supports_tools=None, reasoning_only=None, max_price_per_token=None)
                    models = await service.search_models(search_query or "", filters)
                    _print_models(models, output_format.lower())

        try:
            asyncio.run(_run_lightweight())
        except (AuthenticationError, RateLimitError, APIError) as e:
            raise click.ClickException(str(e))
        except Exception as e:
            raise click.ClickException(f"Unexpected error: {e}")
        # Exit after running lightweight mode
        ctx.exit()
    elif ctx.invoked_subcommand is None:
        # No flags and no subcommand: show help for better UX
        click.echo(ctx.get_help())
        ctx.exit()


@cli.command("list")
@click.argument("filter", required=False)
@click.option("--format", "output_format", type=click.Choice(["table", "json", "yaml"], case_sensitive=False), default="table")
@click.option("--with-providers", is_flag=True, help="Show count of active providers per model (extra API calls)")
@click.option(
    "--sort-by",
    type=click.Choice(["id", "name", "context", "providers"], case_sensitive=False),
    default="id",
    help="Sort column for list output (default: id). 'providers' requires --with-providers",
)
@click.option("--desc", is_flag=True, help="Sort in descending order")
@click.pass_context
def list_models(ctx: click.Context, filter: Optional[str], output_format: str, with_providers: bool, sort_by: str, desc: bool) -> None:
    """List all available models. Optionally filter by substring."""
    config: Config = ctx.obj["config"]

    async def _run() -> None:
        async with OpenRouterClient(config) as client:
            service = ModelService(client)
            models = await client.get_models()
            if filter:
                q = filter.lower()
                models = [m for m in models if q in m.id.lower() or q in m.name.lower()]
            # Sorting before optional providers counting
            key_fn = (
                (lambda m: m.id.lower()) if sort_by.lower() == "id" else
                (lambda m: m.name.lower()) if sort_by.lower() == "name" else
                (lambda m: m.context_length) if sort_by.lower() == "context" else
                None
            )
            if key_fn is not None:
                models = sorted(models, key=key_fn, reverse=desc)
            if output_format.lower() == "table" and with_providers:
                # Fetch provider counts (active only) per model
                rows = []
                for m in models:
                    providers = await client.get_model_providers(m.id)
                    # Active providers: status not offline and availability True
                    active = [p for p in providers if p.availability and (p.provider.status != "offline")]
                    rows.append((m, len(active)))
                if sort_by.lower() == "providers":
                    rows.sort(key=lambda t: t[1], reverse=desc)

                table = Table(title="OpenRouter Models")
                table.add_column("ID", style="cyan")
                table.add_column("Name", style="white")
                table.add_column("Context", justify="right")
                table.add_column("Providers", justify="right")
                for m, cnt in rows:
                    table.add_row(m.id, m.name, str(m.context_length), str(cnt))
                console.print(table)
            else:
                _print_models(models, output_format.lower())

    try:
        asyncio.run(_run())
    except (AuthenticationError, RateLimitError, APIError) as e:
        raise click.ClickException(str(e))
    except Exception as e:
        raise click.ClickException(f"Unexpected error: {e}")


@cli.command()
@click.argument("query", required=True)
@click.option("--min-context", type=int)
@click.option("--supports-tools", is_flag=True, default=None, flag_value=True)
@click.option("--no-supports-tools", is_flag=True, default=None, flag_value=False)
@click.option("--reasoning-only", is_flag=True, default=False)
@click.option("--format", "output_format", type=click.Choice(["table", "json", "yaml"], case_sensitive=False), default="table")
@click.pass_context
def search(ctx: click.Context, query: str, min_context: Optional[int], supports_tools: Optional[bool], no_supports_tools: Optional[bool], reasoning_only: bool, output_format: str) -> None:
    """Search for models with optional filters."""
    config: Config = ctx.obj["config"]

    # Resolve mutually exclusive supports-tools flags
    st_value: Optional[bool]
    if supports_tools is True and no_supports_tools is True:
        raise click.UsageError("--supports-tools and --no-supports-tools cannot be used together")
    st_value = True if supports_tools else (False if no_supports_tools else None)

    filters = SearchFilters(
        min_context=min_context,
        supports_tools=st_value,
        reasoning_only=reasoning_only or None,
        max_price_per_token=None,
    )

    async def _run() -> None:
        async with OpenRouterClient(config) as client:
            service = ModelService(client)
            models = await service.search_models(query, filters)
            _print_models(models, output_format.lower())

    try:
        asyncio.run(_run())
    except (AuthenticationError, RateLimitError, APIError) as e:
        raise click.ClickException(str(e))
    except Exception as e:
        raise click.ClickException(f"Unexpected error: {e}")


@cli.command()
@click.argument("model_name", required=True)
@click.option("--format", "output_format", type=click.Choice(["table", "json", "yaml"], case_sensitive=False), default="table")
@click.option("--per-1k", is_flag=True, help="Display prices per 1K tokens for prompt/completion")
@click.option("--provider", "provider_filter", multiple=True, help="Filter to provider slug(s)")
@click.option("--tools", "tools_required", is_flag=True, help="Require tool calling support")
@click.option("--reasoning", "reasoning_required", is_flag=True, help="Require reasoning support")
@click.pass_context
def providers(ctx: click.Context, model_name: str, output_format: str, per_1k: bool, provider_filter: tuple[str, ...], tools_required: bool, reasoning_required: bool) -> None:
    """Show all providers for a specific model."""
    config: Config = ctx.obj["config"]

    async def _run() -> None:
        async with OpenRouterClient(config) as client:
            service = ModelService(client)
            provs = await service.get_model_providers(model_name)
            # In-memory filtering
            filtered = []
            for d in provs:
                p = d.provider
                if provider_filter and p.provider_name not in provider_filter:
                    continue
                if tools_required and not p.supports_tools:
                    continue
                if reasoning_required and not p.is_reasoning_model:
                    continue
                filtered.append(d)
            _print_providers(filtered, output_format.lower(), per_1k=per_1k)

    try:
        asyncio.run(_run())
    except (AuthenticationError, RateLimitError, APIError) as e:
        raise click.ClickException(str(e))
    except Exception as e:
        raise click.ClickException(f"Unexpected error: {e}")


@cli.command("offers")
@click.argument("model_id", required=True)
@click.option("--format", "output_format", type=click.Choice(["table", "json", "yaml"], case_sensitive=False), default="table")
@click.option("--per-1m", is_flag=True, help="Scale prices to per 1M tokens for prompt/completion (default)")
@click.option("--min-quant", type=str, help="Minimum quantization (e.g., fp8). Unspecified quant is included.")
@click.option("--min-context", type=str, help="Minimum context window (e.g., 128K or 131072)")
@click.option(
    "--sort-by",
    type=click.Choice(["api", "provider", "model", "quant", "context", "maxout", "price_in", "price_out"], case_sensitive=False),
    default="api",
    help="Sort column for offers output (default: api = keep OpenRouter order)",
)
@click.option("--desc", is_flag=True, help="Sort in descending order")
@click.pass_context
def offers(ctx: click.Context, model_id: str, output_format: str, per_1m: bool, sort_by: str, desc: bool, min_quant: Optional[str], min_context: Optional[str]) -> None:
    """Show detailed provider offers for an exact model id (author/slug).

    Fails if the model id is not exact or if no offers are returned.
    """
    config: Config = ctx.obj["config"]

    async def _resolve_and_fetch(client: OpenRouterClient, mid: str) -> tuple[str, list[ProviderDetails]]:
        """Try exact model id, otherwise attempt a unique partial match from /models."""
        # Try exact
        try:
            off = await client.get_model_providers(mid)
            if off:
                return mid, off
        except Exception:
            pass

        # Search for candidates by substring
        all_models = await client.get_models()
        # Exact id not found; find partials
        s = mid.lower()
        candidates = [m for m in all_models if s in m.id.lower() or s in m.name.lower()]
        # If exactly one candidate, use it
        if len(candidates) == 1:
            resolved = candidates[0].id
            off = await client.get_model_providers(resolved)
            if off:
                return resolved, off
            raise click.ClickException(f"Model '{resolved}' has no provider offers.")
        # Multiple candidates: suggest list
        if len(candidates) > 1:
            suggestions = "\n".join(f"- {m.id}  ({m.name})" for m in candidates[:20])
            raise click.ClickException(
                "Model id not found. Did you mean one of these?\n" + suggestions
            )
        # None
        raise click.ClickException(f"Model id '{mid}' not found.")

    async def _run() -> None:
        async with OpenRouterClient(config) as client:
            resolved_id, offers = await _resolve_and_fetch(client, model_id)

            # Filtering helpers
            def parse_quant_bits(q: Optional[str]) -> float:
                if not q:
                    return float('inf')  # treat unspecified as best
                s = q.lower()
                if 'bf16' in s:
                    return 16
                # extract first integer in string
                num = ''
                for ch in s:
                    if ch.isdigit():
                        num += ch
                try:
                    return float(num) if num else 0.0
                except Exception:
                    return 0.0

            def parse_context_threshold(v: Optional[str]) -> int:
                if v is None:
                    return 0
                s = str(v).strip()
                try:
                    if s.lower().endswith('k'):
                        return int(float(s[:-1]) * 1000)
                    return int(float(s))
                except Exception:
                    return 0

            min_bits = parse_quant_bits(min_quant) if min_quant else None
            min_ctx = parse_context_threshold(min_context) if min_context else 0

            def offer_passes(d: ProviderDetails) -> bool:
                p = d.provider
                if min_bits is not None:
                    if parse_quant_bits(p.quantization) < min_bits:
                        return False
                if min_ctx and (p.context_window or 0) < min_ctx:
                    return False
                return True

            offers = [o for o in offers if offer_passes(o)]

            if output_format.lower() == "json":
                click.echo(json.dumps([o.model_dump() for o in offers], indent=2, default=str))
                return
            if output_format.lower() == "yaml":
                click.echo(yaml.safe_dump([o.model_dump() for o in offers], sort_keys=False))
                return

            # Sorting of offers (default preserves API order)
            if sort_by.lower() != "api":
                def key_offer(o: ProviderDetails):
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

            table = Table(title=f"Offers for {resolved_id}", box=box.SIMPLE_HEAVY)
            table.add_column("Provider", style="cyan")
            table.add_column("Model", style="white")
            table.add_column("Reason", justify="center")
            table.add_column("Quant", justify="left")
            table.add_column("Context", justify="right")
            table.add_column("Max Out", justify="right")
            table.add_column("Input Price", justify="right")
            table.add_column("Output Price", justify="right")

            for d in offers:
                p = d.provider
                def fmt_k(v: Optional[int]) -> str:
                    if v is None:
                        return "—"
                    return f"{int(round(v/1000))}K"

                # Per 1M tokens pricing
                price_in = p.pricing.get("prompt") if p.pricing else None
                price_out = p.pricing.get("completion") if p.pricing else None
                # Default: show per 1M tokens; if not explicit, still scale (per requirement)
                if per_1m or True:
                    price_in = None if price_in is None else price_in * 1_000_000.0
                    price_out = None if price_out is None else price_out * 1_000_000.0
                # Show raw USD value with scaling applied, no suffix
                price_in_str = "—" if price_in is None else f"${price_in:.6f}"
                price_out_str = "—" if price_out is None else f"${price_out:.6f}"

                # Reasoning support inferred from supported_parameters (list or dict)
                sp = p.supported_parameters
                reasoning_supported = False
                if isinstance(sp, list):
                    reasoning_supported = any((isinstance(x, str) and (x == "reasoning" or x.startswith("reasoning"))) for x in sp)
                elif isinstance(sp, dict):
                    reasoning_supported = bool(sp.get("reasoning", False))

                # Derive provider's endpoint/model name for display
                model_cell = p.endpoint_name or "—"
                if isinstance(model_cell, str):
                    s = model_cell.strip()
                    # common patterns: "Provider | something", "something via Provider"
                    if "|" in s:
                        parts = [part.strip() for part in s.split("|")]
                        # prefer the part that does not equal provider name
                        if len(parts) >= 2:
                            pick = parts[-1]
                            if pick.lower() == (p.provider_name or "").lower() and len(parts) > 1:
                                pick = parts[0]
                            s = pick
                    if " via " in s:
                        s = s.split(" via ", 1)[0].strip()
                    model_cell = s or (p.endpoint_name or "—")

                table.add_row(
                    p.provider_name,
                    model_cell,
                    "+" if reasoning_supported else "-",
                    p.quantization or "—",
                    fmt_k(p.context_window),
                    fmt_k(p.max_completion_tokens),
                    price_in_str,
                    price_out_str,
                )

            console.print(table)

    try:
        asyncio.run(_run())
    except (AuthenticationError, RateLimitError, APIError) as e:
        raise click.ClickException(str(e))
    except Exception as e:
        raise click.ClickException(f"Unexpected error: {e}")
