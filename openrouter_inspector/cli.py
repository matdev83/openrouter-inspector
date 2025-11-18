"""Command-line interface for OpenRouter CLI using Click."""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import suppress
from pathlib import Path
from typing import Any

import click

from . import utils
from ._version import __version__
from .cli_decorators import (
    async_command_with_error_handling,
    common_filter_options,
    common_format_options,
    common_sort_options,
    extended_format_options,
    model_provider_argument_parser,
)
from .commands import (
    BenchmarkCommand,
    CheckCommand,
    DetailsCommand,
    EndpointsCommand,
    ListCommand,
    PingCommand,
)
from .exceptions import (
    APIError,
    AuthenticationError,
    RateLimitError,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Click helpers
# ---------------------------------------------------------------------------


class DefaultCommandGroup(click.Group):
    """A Click group that defaults to a configured command when the first token
    is *not* a known sub-command.

    This allows calls such as ``openrouter-inspector glm-4.5`` to be treated
    as ``openrouter-inspector list glm-4.5``.

    The implementation is adapted from the *click-default-group* recipe but
    kept self-contained to avoid an extra dependency.
    """

    def __init__(
        self, *args: Any, default_cmd_name: str | None = None, **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.default_cmd_name = default_cmd_name

    def resolve_command(
        self, ctx: click.Context, args: list[str]
    ) -> tuple[str | None, click.Command | None, list[str]]:
        """Try to resolve *args* to a command.

        If the first argument is *not* a registered command, rewrite the
        argument list to insert the *default_cmd_name* at position 0 and let
        the base implementation handle the rest.  This preserves Click's
        standard parsing semantics for options and arguments while providing
        the desired fallback behaviour.
        """

        # Try the normal resolution first.
        try:
            return super().resolve_command(ctx, args)
        except click.exceptions.UsageError:
            # Only attempt the fallback if we actually have a default command
            # configured and there *is* at least one token (otherwise Click's
            # original error is still appropriate).
            if self.default_cmd_name and args:
                # Prepend the default command name and try again.
                new_args: list[str] = [self.default_cmd_name, *args]
                return super().resolve_command(ctx, new_args)

            # Re-raise the original error if we cannot handle the situation.
            raise


# Use the custom group class that falls back to the *list* command.
@click.group(
    cls=DefaultCommandGroup,
    default_cmd_name="list",
    invoke_without_command=True,
    add_help_option=True,
    context_settings={
        "allow_extra_args": True,
        "ignore_unknown_options": True,
    },
)
@click.version_option(version=__version__)
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
    "--reasoning",
    "reasoning_flag",
    is_flag=True,
    default=None,
    help="Filter to models supporting reasoning features",
)
@click.option(
    "--no-reasoning",
    "no_reasoning_flag",
    is_flag=True,
    default=None,
    help="Filter to models without reasoning support",
)
@click.option(
    "--img",
    "img_flag",
    is_flag=True,
    default=None,
    help="Filter to models supporting image input",
)
@click.option(
    "--no-img",
    "no_img_flag",
    is_flag=True,
    default=None,
    help="Filter to models without image input support",
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
    "--no-hints",
    is_flag=True,
    help="Do not display helpful command hints below the table output",
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
def cli(  # pylint: disable=too-many-arguments,too-many-locals,too-complex
    ctx: click.Context,
    list_flag: bool,
    tools_flag: bool | None,
    no_tools_flag: bool | None,
    reasoning_flag: bool | None,
    no_reasoning_flag: bool | None,
    img_flag: bool | None,
    no_img_flag: bool | None,
    output_format: str,
    with_providers: bool,
    no_hints: bool,
    sort_by: str,
    desc: bool,
    log_level: str | None,
) -> None:
    """OpenRouter Inspector - A lightweight CLI for exploring OpenRouter AI models.

    Subcommands:
      - list: list models
      - endpoints: detailed endpoints for a model
      - details: show detailed model parameters and features for a specific provider
      - check: check provider endpoint status (Functional/Degraded/Disabled)
      - ping: test model connectivity via chat completion
      - benchmark: measure throughput (TPS) of a model endpoint (supports --prompt-file to override default prompt)

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
        if reasoning_flag is True and no_reasoning_flag is True:
            raise click.UsageError(
                "--reasoning and --no-reasoning cannot be used together"
            )
        if img_flag is True and no_img_flag is True:
            raise click.UsageError("--img and --no-img cannot be used together")

        async def _run_lightweight() -> None:
            client, model_service, table_formatter, json_formatter = (
                utils.create_command_dependencies(api_key)
            )

            async with client as c:
                # Ensure service uses the entered client (tests patch __aenter__)
                with suppress(AttributeError):
                    model_service.client = c
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
                    reasoning=reasoning_flag,
                    no_reasoning=no_reasoning_flag,
                    img=img_flag,
                    no_img=no_img_flag,
                    output_format=output_format,
                    with_providers=with_providers,
                    no_hints=no_hints,
                    sort_by=sort_by,
                    desc=desc,
                )
                click.echo(output, nl=False)

        try:
            asyncio.run(_run_lightweight())
        except (AuthenticationError, RateLimitError, APIError) as e:
            raise click.ClickException(str(e)) from e
        except click.exceptions.Exit as e:
            # Propagate click's exit exception without wrapping it
            raise e
        except SystemExit as e:
            # Preserve SystemExit to avoid wrapping in ClickException
            raise e
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
@common_filter_options
@common_format_options
@click.option(
    "--with-providers",
    is_flag=True,
    help="Show count of active providers per model (extra API calls)",
)
@common_sort_options
@click.pass_context
def list_models(  # pylint: disable=too-many-arguments,too-many-locals
    ctx: click.Context,
    filters: tuple[str, ...],
    min_context: int | None,
    tools: bool | None,
    no_tools: bool | None,
    reasoning: bool | None,
    no_reasoning: bool | None,
    img: bool | None,
    no_img: bool | None,
    output_format: str,
    with_providers: bool,
    no_hints: bool,
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
    if reasoning is True and no_reasoning is True:
        raise click.UsageError("--reasoning and --no-reasoning cannot be used together")
    if img is True and no_img is True:
        raise click.UsageError("--img and --no-img cannot be used together")

    @async_command_with_error_handling
    async def _run() -> None:
        client, model_service, table_formatter, json_formatter = (
            utils.create_command_dependencies(api_key)
        )

        async with client as c:
            with suppress(AttributeError):
                model_service.client = c
            list_cmd = ListCommand(c, model_service, table_formatter, json_formatter)

            output = await list_cmd.execute(
                filters=filters,
                min_context=min_context,
                tools=tools,
                no_tools=no_tools,
                reasoning=reasoning,
                no_reasoning=no_reasoning,
                img=img,
                no_img=no_img,
                output_format=output_format,
                with_providers=with_providers,
                no_hints=no_hints,
                sort_by=sort_by,
                desc=desc,
            )
            click.echo("\n" + output + "\n\n", nl=False)

    _run()


@cli.command("endpoints")
@click.argument("model_id", required=True)
@common_format_options
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
    "--no-hints",
    is_flag=True,
    help="Do not display helpful command hints below the table output",
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
@click.pass_context
def endpoints(  # pylint: disable=too-many-arguments,too-many-locals
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
    no_hints: bool,
    log_level: str | None,
) -> None:
    """Show detailed provider endpoints for an exact model id (author/slug).

    API-only. Fails if the model id is not exact or if no endpoints are returned.
    """
    utils.configure_logging(log_level)
    api_key: str = ctx.obj["api_key"]

    @async_command_with_error_handling
    async def _run() -> None:
        client, model_service, table_formatter, json_formatter = (
            utils.create_command_dependencies(api_key)
        )

        async with client as c:
            with suppress(AttributeError):
                model_service.client = c
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
                no_hints=no_hints,
            )
            click.echo(output, nl=False)

    _run()


@cli.command("details")
@click.argument("model_id", required=True)
@click.argument("provider_name", required=False)
@click.option(
    "--no-hints",
    is_flag=True,
    help="Do not display helpful command hints below the table output",
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
@model_provider_argument_parser
@click.pass_context
def details_command(
    ctx: click.Context,
    model_id: str,
    provider_name: str | None,
    no_hints: bool,
    log_level: str | None,
) -> None:
    """Display detailed model parameters and features for a specific provider endpoint.

    Examples:
      openrouter-inspector details tngtech/deepseek-r1t2-chimera:free Chutes
      openrouter-inspector details tngtech/deepseek-r1t2-chimera:free@Chutes

    Note: On Windows PowerShell, quote the @ syntax:
      openrouter-inspector details "tngtech/deepseek-r1t2-chimera:free@Chutes"
    """
    utils.configure_logging(log_level)
    api_key: str = ctx.obj["api_key"]

    if not provider_name:
        raise click.ClickException(
            "Provider name is required. Use either:\n"
            "  openrouter-inspector details MODEL_ID PROVIDER_NAME\n"
            "  openrouter-inspector details MODEL_ID@PROVIDER_NAME"
        )

    @async_command_with_error_handling
    async def _run() -> None:
        client, model_service, table_formatter, json_formatter = (
            utils.create_command_dependencies(api_key)
        )

        async with client as c:
            with suppress(AttributeError):
                model_service.client = c
            details_cmd = DetailsCommand(
                c, model_service, table_formatter, json_formatter
            )

            output = await details_cmd.execute(
                model_id=model_id,
                provider_name=provider_name,
                no_hints=no_hints,
            )
            click.echo(output, nl=False)

    _run()


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

    @async_command_with_error_handling
    async def _run() -> None:
        client, model_service, table_formatter, json_formatter = (
            utils.create_command_dependencies(api_key)
        )

        async with client as c:
            with suppress(AttributeError):
                model_service.client = c
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

    _run()


@cli.command("search")
@click.argument("filters", nargs=-1, required=False)
@common_format_options
@click.option(
    "--with-providers",
    is_flag=True,
    help="Show count of active providers per model (extra API calls)",
)
@click.option(
    "--no-hints",
    is_flag=True,
    help="Do not display helpful command hints below the table output",
)
@common_sort_options
@click.pass_context
def search_command(  # pylint: disable=too-many-arguments,too-many-locals
    ctx: click.Context,
    filters: tuple[str, ...],
    output_format: str,
    with_providers: bool,
    no_hints: bool,
    sort_by: str,
    desc: bool,
    log_level: str | None,
) -> None:
    """Alias that forwards to list with the given filters."""
    utils.configure_logging(log_level)
    api_key: str = ctx.obj["api_key"]

    @async_command_with_error_handling
    async def _run() -> None:
        client, model_service, table_formatter, json_formatter = (
            utils.create_command_dependencies(api_key)
        )
        async with client as c:
            with suppress(AttributeError):
                model_service.client = c
            list_cmd = ListCommand(c, model_service, table_formatter, json_formatter)
            output = await list_cmd.execute(
                filters=filters,
                output_format=output_format,
                with_providers=with_providers,
                no_hints=no_hints,
                sort_by=sort_by,
                desc=desc,
            )
            click.echo(output, nl=False)

    _run()


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
    "-n",
    "-c",
    "--count",
    "count",
    type=int,
    default=3,
    show_default=True,
    help="Number of ping requests to send.",
)
@click.option(
    "--filthy-rich",
    is_flag=True,
    help="Allow sending more than 10 pings, confirming you are aware of potential costs.",
)
@click.option(
    "--debug-response",
    is_flag=True,
    help="Print the full JSON response from the API for debugging.",
)
@extended_format_options
@model_provider_argument_parser
@click.pass_context
def ping_command(  # pylint: disable=too-many-arguments
    ctx: click.Context,
    model_id: str,
    provider_name: str | None,
    timeout_seconds: int,
    count: int,
    filthy_rich: bool,
    debug_response: bool,
    log_level: str | None,
    output_format: str | None = None,
) -> None:
    """Ping a model or a specific provider endpoint via chat completion.

    Examples:
      openrouter-inspector ping openai/o4-mini
      openrouter-inspector ping deepseek/deepseek-chat-v3-0324:free Chutes
    """
    utils.configure_logging(log_level)
    api_key: str = ctx.obj["api_key"]

    if timeout_seconds <= 0:
        timeout_seconds = 60

    if count <= 0:
        raise click.ClickException("Number of tries (-n) must be a positive integer.")

    if count > 10 and not filthy_rich:
        raise click.ClickException(
            "To send more than 10 pings, you must use the --filthy-rich flag "
            "to acknowledge potential API costs."
        )

    @async_command_with_error_handling
    async def _run() -> None:
        client, model_service, table_formatter, json_formatter = (
            utils.create_command_dependencies(api_key)
        )

        async with client as c:
            from contextlib import suppress

            with suppress(Exception):
                model_service.client = c
            cmd = PingCommand(c, model_service, table_formatter, json_formatter)

            # Emit each line as it becomes available
            def _emit(line: str) -> None:
                if line is None:
                    return
                # Ensure a blank line separation is preserved by the command
                click.echo(line)

            await cmd.execute(
                model_id=model_id,
                provider_name=provider_name,
                timeout_seconds=timeout_seconds,
                count=count,
                debug_response=debug_response,
                on_progress=_emit,
            )
            # When streaming, output already printed. Ensure blank lines only if missing
            # The returned value remains available (useful for tests), but we don't re-print it here
            if cmd.last_all_success is False:
                ctx.exit(1)

    _run()


@cli.command("benchmark")
@click.argument("model_id", required=True)
@click.argument("provider_name", required=False)
@click.option(
    "--timeout",
    "timeout_seconds",
    type=int,
    default=120,
    show_default=True,
    help="Timeout in seconds for the benchmark request",
)
@click.option(
    "--max-tokens",
    "max_tokens",
    type=int,
    default=3000,
    show_default=True,
    help="Maximum output tokens allowed (safety limit)",
)
@click.option(
    "--debug-response",
    is_flag=True,
    help="Print the full JSON response from the API for debugging.",
)
@click.option(
    "--prompt-file",
    "prompt_file",
    type=click.Path(
        exists=True, file_okay=True, dir_okay=False, readable=True, path_type=str
    ),
    help=(
        "Path to a custom benchmark prompt file. If provided, overrides the default throughput prompt."
    ),
)
@click.option(
    "--min-tps",
    "min_tps",
    type=click.FloatRange(1, 10000),
    help="Minimum TPS threshold (1-10000). Only enforced when --format text.",
)
@extended_format_options
@model_provider_argument_parser
@click.pass_context
def benchmark_command(  # pylint: disable=too-many-arguments,too-many-locals,too-complex
    ctx: click.Context,
    model_id: str,
    provider_name: str | None,
    timeout_seconds: int,
    max_tokens: int,
    debug_response: bool,
    prompt_file: str | None,
    output_format: str,
    min_tps: float | None,
    log_level: str | None,
) -> None:
    """Benchmark throughput (TPS) of a model or specific provider endpoint.

    Measures tokens per second by sending a prompt designed to generate a long response.

    Examples:
      openrouter-inspector benchmark openai/gpt-4o-mini
      openrouter-inspector benchmark deepseek/deepseek-chat-v3-0324:free Chutes
      openrouter-inspector benchmark anthropic/claude-3.5-sonnet@anthropic
    """
    utils.configure_logging(log_level)
    api_key: str = ctx.obj["api_key"]

    if timeout_seconds <= 0:
        timeout_seconds = 120

    @async_command_with_error_handling
    async def _run() -> int | None:  # pylint: disable=too-many-locals
        client, model_service, table_formatter, json_formatter = (
            utils.create_command_dependencies(api_key)
        )

        async with client as c:
            from contextlib import suppress

            with suppress(AttributeError):
                model_service.client = c
            cmd = BenchmarkCommand(c, model_service, table_formatter, json_formatter)

            throughput_prompt_override: str | None = None
            if prompt_file:
                # Read custom prompt file (validated by Click for existence/readability)
                try:
                    content = Path(prompt_file).read_text(encoding="utf-8").strip()
                    lines = content.split("\n")
                    if lines and lines[0].startswith("# "):
                        lines = lines[1:]
                    throughput_prompt_override = "\n".join(lines).strip()
                except (OSError, UnicodeDecodeError) as e:
                    # Treat as invalid parameter for proper exit code 2
                    raise click.BadParameter(
                        f"Cannot read prompt file: {e}", param_hint="--prompt-file"
                    ) from e

            # Run once to produce metrics for formatting and threshold check
            result = await cmd._benchmark_once(
                model_id=model_id,
                provider_name=provider_name,
                timeout_seconds=timeout_seconds,
                max_tokens=max_tokens,
                debug_response=debug_response,
                throughput_prompt_override=throughput_prompt_override,
            )

            fmt = (output_format or "table").lower()
            if fmt == "json":
                import json as _json

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
                click.echo(_json.dumps(payload, indent=2, default=str))
            elif fmt == "text":
                click.echo(f"TPS: {result.tokens_per_second:.2f}")
                if min_tps is not None:
                    return 0 if result.tokens_per_second >= min_tps else 1
            else:
                output = table_formatter.format_benchmark_result(
                    result=result, model_id=model_id, provider_name=provider_name
                )
                click.echo(output)
        return None

    exit_code = _run()
    if exit_code is not None:
        ctx.exit(exit_code)
