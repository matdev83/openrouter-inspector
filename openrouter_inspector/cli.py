"""Command-line interface for OpenRouter CLI using Click."""

from __future__ import annotations

import asyncio
import logging
import os

import click

from . import utils
from .commands import CheckCommand, EndpointsCommand, ListCommand, PingCommand
from .exceptions import APIError, AuthenticationError, RateLimitError

logger = logging.getLogger(__name__)


@click.group(
    invoke_without_command=True,
    add_help_option=True,
    context_settings={
        "allow_extra_args": True,
        "ignore_unknown_options": True,
    },
)
# Global lightweight mode: support --list as alternative to subcommands
@click.option(
    "--list",
    "list_flag",
    is_flag=True,
    help="List models",
)
@click.option(
    "--tools",
    "tools_flag",
    is_flag=True,
    default=None,
    help="Filter to models supporting tool calling",
)
@click.option(
    "--no-tools",
    "no_tools_flag",
    is_flag=True,
    default=None,
    help="Filter to models NOT supporting tool calling",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json"], case_sensitive=False),
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
    tools_flag: bool | None,
    no_tools_flag: bool | None,
    output_format: str,
    with_providers: bool,
    sort_by: str,
    desc: bool,
    log_level: str | None,
) -> None:
    """OpenRouter Inspector - A lightweight CLI for exploring OpenRouter AI models.

    Subcommands:
      - list: list models
      - endpoints: detailed endpoints for a model
      - check: health check a provider endpoint (Functional/Degraded/Disabled)

    Or use lightweight flags:
      - --list to list models

    Quick search:
      - Run without a subcommand to search models: openrouter-inspector openai gpt
      - Any arguments without a recognized command are treated as search filters

    Authentication:
      Set OPENROUTER_API_KEY environment variable with your API key.
    """
    # Logging
    utils.configure_logging(log_level, default_to_warning=True)

    # If no subcommand, no lightweight flags, show help
    if ctx.invoked_subcommand is None and not list_flag and not ctx.args:
        click.echo(ctx.get_help())
        ctx.exit()

    # Get search terms from args if no subcommand recognized
    search_terms = None
    if ctx.invoked_subcommand is None and ctx.args:
        search_terms = ctx.args
        # Remove the search terms from args so they don't confuse Click
        ctx.args = []

    # Get API key from environment when needed (commands or lightweight mode)
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise click.ClickException(
            "OPENROUTER_API_KEY is required. Set it in your environment and try again."
        )

    ctx.obj = {"api_key": api_key}

    # Lightweight mode if no subcommand provided but we have flags or search terms
    if ctx.invoked_subcommand is None and (list_flag or search_terms):
        # Validate mutually exclusive flags
        if tools_flag is True and no_tools_flag is True:
            raise click.UsageError("--tools and --no-tools cannot be used together")

        async def _run_lightweight() -> None:
            client, model_service, table_formatter, json_formatter = (
                utils.create_command_dependencies(api_key)
            )

            async with client as c:
                # Ensure service uses the entered client (tests patch __aenter__)
                try:
                    model_service.client = c
                except Exception:
                    pass
                # Use ListCommand for list functionality with entered client
                list_cmd = ListCommand(
                    c, model_service, table_formatter, json_formatter
                )

                # Convert search_terms to tuple if it's a list
                filters_tuple = tuple(search_terms) if search_terms else None

                output = await list_cmd.execute(
                    filters=filters_tuple,
                    tools=tools_flag,
                    no_tools=no_tools_flag,
                    output_format=output_format,
                    with_providers=with_providers,
                    sort_by=sort_by,
                    desc=desc,
                )
                click.echo(output, nl=False)

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
@click.argument("filters", nargs=-1, required=False)
@click.option("--min-context", type=int, help="Minimum context window size")
@click.option(
    "--tools",
    is_flag=True,
    default=None,
    help="Filter to models supporting tool calling",
)
@click.option(
    "--no-tools",
    is_flag=True,
    default=None,
    help="Filter to models NOT supporting tool calling",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json"], case_sensitive=False),
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
    filters: tuple[str, ...],
    min_context: int | None,
    tools: bool | None,
    no_tools: bool | None,
    output_format: str,
    with_providers: bool,
    sort_by: str,
    desc: bool,
    log_level: str | None,
) -> None:
    """List all available models. Optionally filter by multiple substrings (AND logic), minimum context size, and tool calling support."""
    utils.configure_logging(log_level)
    api_key: str = ctx.obj["api_key"]

    # Validate mutually exclusive flags
    if tools is True and no_tools is True:
        raise click.UsageError("--tools and --no-tools cannot be used together")

    async def _run() -> None:
        client, model_service, table_formatter, json_formatter = (
            utils.create_command_dependencies(api_key)
        )

        async with client as c:
            try:
                model_service.client = c
            except Exception:
                pass
            list_cmd = ListCommand(c, model_service, table_formatter, json_formatter)

            output = await list_cmd.execute(
                filters=filters,
                min_context=min_context,
                tools=tools,
                no_tools=no_tools,
                output_format=output_format,
                with_providers=with_providers,
                sort_by=sort_by,
                desc=desc,
            )
            click.echo("\n" + output + "\n\n", nl=False)

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
    type=click.Choice(["table", "json"], case_sensitive=False),
    default="table",
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
    utils.configure_logging(log_level)
    api_key: str = ctx.obj["api_key"]

    async def _run() -> None:
        client, model_service, table_formatter, json_formatter = (
            utils.create_command_dependencies(api_key)
        )

        async with client as c:
            try:
                model_service.client = c
            except Exception:
                pass
            endpoints_cmd = EndpointsCommand(
                c, model_service, table_formatter, json_formatter
            )

            output = await endpoints_cmd.execute(
                model_id=model_id,
                output_format=output_format,
                sort_by=sort_by,
                desc=desc,
                min_quant=min_quant,
                min_context=min_context,
                reasoning_required=reasoning_required,
                no_reasoning_required=no_reasoning_required,
                tools_required=tools_required,
                no_tools_required=no_tools_required,
                img_required=img_required,
                no_img_required=no_img_required,
                max_input_price=max_input_price,
                max_output_price=max_output_price,
            )
            click.echo(output, nl=False)

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
    utils.configure_logging(log_level)
    api_key: str = ctx.obj["api_key"]

    async def _run() -> None:
        client, model_service, table_formatter, json_formatter = (
            utils.create_command_dependencies(api_key)
        )

        async with client as c:
            try:
                model_service.client = c
            except Exception:
                pass
            check_cmd = CheckCommand(c, model_service, table_formatter, json_formatter)

            try:
                status = await check_cmd.execute(
                    model_id=model_id,
                    provider_name=provider_name,
                    endpoint_name=endpoint_name,
                )
                click.echo(status)
            except Exception as e:
                raise click.ClickException(str(e)) from e

    try:
        asyncio.run(_run())
    except (AuthenticationError, RateLimitError, APIError) as e:
        raise click.ClickException(str(e)) from e
    except Exception as e:
        raise click.ClickException(f"Unexpected error: {e}") from e


@cli.command("search")
@click.argument("filters", nargs=-1, required=False)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json"], case_sensitive=False),
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
)
@click.option("--desc", is_flag=True, help="Sort in descending order")
@click.pass_context
def search_command(
    ctx: click.Context,
    filters: tuple[str, ...],
    output_format: str,
    with_providers: bool,
    sort_by: str,
    desc: bool,
) -> None:
    """Alias that forwards to list with the given filters."""
    api_key: str = ctx.obj["api_key"]

    async def _run() -> None:
        client, model_service, table_formatter, json_formatter = (
            utils.create_command_dependencies(api_key)
        )
        async with client as c:
            try:
                model_service.client = c
            except Exception:
                pass
            list_cmd = ListCommand(c, model_service, table_formatter, json_formatter)
            output = await list_cmd.execute(
                filters=filters,
                output_format=output_format,
                with_providers=with_providers,
                sort_by=sort_by,
                desc=desc,
            )
            click.echo(output, nl=False)

    try:
        asyncio.run(_run())
    except (AuthenticationError, RateLimitError, APIError) as e:
        raise click.ClickException(str(e)) from e
    except Exception as e:
        raise click.ClickException(f"Unexpected error: {e}") from e


@cli.command("ping")
@click.argument("model_id", required=True)
@click.argument("provider_name", required=False)
@click.option(
    "--timeout",
    "timeout_seconds",
    type=int,
    default=60,
    show_default=True,
    help="Timeout in seconds for the ping request",
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
def ping_command(
    ctx: click.Context,
    model_id: str,
    provider_name: str | None,
    timeout_seconds: int,
    log_level: str | None,
) -> None:
    """Ping a model or a specific provider endpoint via chat completion.

    Examples:
      openrouter-inspector ping openai/o4-mini
      openrouter-inspector ping deepseek/deepseek-chat-v3-0324:free Chutes
    """
    utils.configure_logging(log_level)
    api_key: str = ctx.obj["api_key"]

    # Support model@provider shorthand when provider_name not given
    if provider_name is None and "@" in model_id:
        parts = model_id.split("@", 1)
        model_id = parts[0].strip()
        provider_name = parts[1].strip() or None

    # Validate timeout; default to 60 when invalid
    if not isinstance(timeout_seconds, int) or timeout_seconds <= 0:
        timeout_seconds = 60

    async def _run() -> None:
        client, model_service, table_formatter, json_formatter = (
            utils.create_command_dependencies(api_key)
        )

        async with client as c:
            try:
                model_service.client = c
            except Exception:
                pass
            cmd = PingCommand(c, model_service, table_formatter, json_formatter)
            output = await cmd.execute(
                model_id=model_id,
                provider_name=provider_name,
                timeout_seconds=timeout_seconds,
            )
            # Print with a blank line before and after, ensuring proper line endings
            click.echo("")
            click.echo(output)
            click.echo("")

    try:
        asyncio.run(_run())
    except (AuthenticationError, RateLimitError, APIError) as e:
        raise click.ClickException(str(e)) from e
    except Exception as e:
        raise click.ClickException(f"Unexpected error: {e}") from e
