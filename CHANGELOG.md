2025-08-14  benchmark: added `--prompt-file <file>` option to override the default throughput prompt.
  - Validates that the file exists and is readable; on invalid path/read errors, the CLI exits with code `2`.
  - Add `--no-hints` option to disable suggested commands from the output of the `list` command
  - Modified the `ping` command to not show response times for failed requests

