#!/usr/bin/env python
"""Main entry point for the openrouter-inspector CLI."""

import sys

from .cli import cli


def main(args: list[str] | None = None) -> None:
    """Run the CLI with the given arguments."""
    if args is None:
        args = sys.argv[1:]

        # If the first argument is not a flag, check if it's a recognized command
    # If not, insert the 'list' command and treat arguments as search terms
    if args and not args[0].startswith("-"):
        # Get all available commands from the Click command group
        from .cli import cli as cli_group

        available_commands = list(cli_group.commands.keys())

        # If the first argument is not a recognized command, treat it as a search term for list
        if args[0] not in available_commands:
            args.insert(0, "list")

    cli(args=args)


if __name__ == "__main__":
    main()
