#!/usr/bin/env python
import sys
from openrouter_inspector import cli

if __name__ == "__main__":
    # Simulate command line arguments
    sys.argv = ["openrouter-inspector", "openai"]
    cli()
