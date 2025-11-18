"""Common CLI decorators to reduce boilerplate in cli.py."""

from __future__ import annotations

import asyncio
import functools
from collections.abc import Callable
from typing import Any, TypeVar

import click

from .exceptions import (
    APIError,
    AuthenticationError,
    ModelNotFoundError,
    ProviderNotFoundError,
    RateLimitError,
)

F = TypeVar("F", bound=Callable[..., Any])


def common_format_options(f: F) -> F:
    """Add common format and logging options to a command."""
    f = click.option(
        "--format",
        "output_format",
        type=click.Choice(["table", "json"], case_sensitive=False),
        default="table",
    )(f)
    f = click.option(
        "--log-level",
        "log_level",
        type=click.Choice(
            ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"],
            case_sensitive=False,
        ),
        help="Set logging level",
        envvar="OPENROUTER_LOG_LEVEL",
    )(f)
    return f


def extended_format_options(f: F) -> F:
    """Add extended format options including text format for ping/benchmark commands."""
    f = click.option(
        "--format",
        "output_format",
        type=click.Choice(["table", "json", "text"], case_sensitive=False),
        default="table",
    )(f)
    f = click.option(
        "--log-level",
        "log_level",
        type=click.Choice(
            ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"],
            case_sensitive=False,
        ),
        help="Set logging level",
        envvar="OPENROUTER_LOG_LEVEL",
    )(f)
    return f


def common_filter_options(f: F) -> F:
    """Add common filtering options for list-like commands."""
    f = click.option(
        "--tools",
        is_flag=True,
        default=None,
        help="Filter to models supporting tool calling",
    )(f)
    f = click.option(
        "--no-tools",
        is_flag=True,
        default=None,
        help="Filter to models NOT supporting tool calling",
    )(f)
    f = click.option(
        "--reasoning",
        is_flag=True,
        default=None,
        help="Filter to models supporting reasoning features",
    )(f)
    f = click.option(
        "--no-reasoning",
        is_flag=True,
        default=None,
        help="Filter to models without reasoning support",
    )(f)
    f = click.option(
        "--img",
        is_flag=True,
        default=None,
        help="Filter to models supporting image input",
    )(f)
    f = click.option(
        "--no-img",
        is_flag=True,
        default=None,
        help="Filter to models without image input support",
    )(f)
    f = click.option(
        "--no-hints",
        is_flag=True,
        help="Do not display helpful command hints below the table output",
    )(f)
    return f


def common_sort_options(f: F) -> F:
    """Add common sorting options."""
    f = click.option(
        "--sort-by",
        type=click.Choice(["id", "name", "context", "providers"], case_sensitive=False),
        default="id",
        help="Sort column for list output (default: id). 'providers' requires --with-providers",
    )(f)
    f = click.option("--desc", is_flag=True, help="Sort in descending order")(f)
    return f


def async_command_with_error_handling(
    async_func: Callable[..., Any],
) -> Callable[..., None]:
    """Decorator to handle async execution and common error patterns for CLI commands."""

    @functools.wraps(async_func)
    def wrapper(*args: Any, **kwargs: Any) -> None:
        # Execute the async function with error handling
        try:
            asyncio.run(async_func(*args, **kwargs))
        except click.exceptions.Exit as e:
            # Preserve intended exit code for scripting scenarios
            raise e
        except SystemExit as e:
            # Allow SystemExit to propagate without wrapping
            raise e
        except (ModelNotFoundError, ProviderNotFoundError) as e:
            # Handle model/provider not found errors with clean messages
            raise click.ClickException(str(e)) from e
        except (AuthenticationError, RateLimitError, APIError) as e:
            raise click.ClickException(str(e)) from e
        except Exception as e:
            raise click.ClickException(f"Unexpected error: {e}") from e

    return wrapper


def model_provider_argument_parser(f: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to add model@provider parsing logic to commands that support it."""

    @functools.wraps(f)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # For functions with positional arguments, we need to handle both cases
        # Check if we have positional args (typical for test functions)
        if args and len(args) >= 1:
            model_id = args[0]
            provider_name = args[1] if len(args) > 1 else kwargs.get("provider_name")

            # Support model@provider shorthand when provider_name not given
            if provider_name is None and model_id and "@" in model_id:
                parts = model_id.split("@", 1)
                new_args = list(args)
                new_args[0] = parts[0].strip()
                if len(new_args) > 1:
                    new_args[1] = parts[1].strip() or None
                else:
                    kwargs["provider_name"] = parts[1].strip() or None
                args = tuple(new_args)
        else:
            # Handle kwargs-only case
            model_id = kwargs.get("model_id")
            provider_name = kwargs.get("provider_name")

            # Support model@provider shorthand when provider_name not given
            if provider_name is None and model_id and "@" in model_id:
                parts = model_id.split("@", 1)
                kwargs["model_id"] = parts[0].strip()
                kwargs["provider_name"] = parts[1].strip() or None

        return f(*args, **kwargs)

    return wrapper
