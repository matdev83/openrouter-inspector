#!/usr/bin/env python
import sys

from openrouter_inspector import cli

if __name__ == "__main__":
    # Simulate command line arguments for the ping command
    # Example: ping a model to test connectivity
    sys.argv = ["openrouter-inspector", "ping", "openai/gpt-4o-mini", "--count", "1"]
    cli()
