# OpenRouter Inspector

[![CI](https://github.com/matdev83/openrouter-inspector/actions/workflows/ci.yml/badge.svg)](https://github.com/matdev83/openrouter-inspector/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/matdev83/openrouter-inspector/branch/main/graph/badge.svg)](https://codecov.io/gh/matdev83/openrouter-inspector)
[![PyPI](https://img.shields.io/pypi/v/openrouter-inspector.svg)](https://pypi.org/project/openrouter-inspector/)
![Python](https://img.shields.io/badge/python-%3E%3D3.10-blue)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![security: bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit)
[![Pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
![Last commit](https://img.shields.io/github/last-commit/matdev83/openrouter-inspector)
[![Issues](https://img.shields.io/github/issues/matdev83/openrouter-inspector)](https://github.com/matdev83/openrouter-inspector/issues)

A lightweight CLI for exploring OpenRouter AI models, listing provider endpoints with supported model parameters, and benchmarking endpoint latency and throughput.

## Installation

### Requirements

- Python >=3.10

### From PyPI (recommended)

- With pipx (recommended for CLIs):
  ```bash
  pipx install openrouter-inspector
  ```
- Or with pip into your active environment:
  ```bash
  pip install openrouter-inspector
  ```

## Features

- Explore available models and provider-specific endpoints from OpenRouter.
- Rich table output with pricing per 1M tokens and optional provider counts.
- Change detection for new models and pricing changes between runs.
- JSON output for easy scripting.

## Usage

The CLI supports both subcommands and lightweight global flags.

### Authentication

Set your OpenRouter API key via environment variable (required):

```bash
export OPENROUTER_API_KEY=sk-or-...
```

For security, the CLI does not accept API keys via command-line flags. It reads the key only from the `OPENROUTER_API_KEY` environment variable. If the key is missing or invalid, the CLI shows a friendly error and exits.

### Quick starts

```bash
# Show the version of the CLI
openrouter-inspector --version

# List all models
openrouter-inspector list

# List models filtered by substring (matches id or display name)
openrouter-inspector list openai

# List models with multiple filters (AND logic)
openrouter-inspector list meta free

# Or just type your search terms; default action is `list`
openrouter-inspector gemini-2.0 free

# Detailed provider endpoints (exact model id)
openrouter-inspector endpoints deepseek/deepseek-r1

# Show detailed model parameters and features for a specific provider
openrouter-inspector details tngtech/deepseek-r1t2-chimera:free Chutes

# To check the endpoint health and latency
openrouter-inspector ping google/gemini-2.0-flash-exp:free
```

 

### Commands

#### list

```bash
openrouter-inspector list [filters...] [--with-providers] [--sort-by id|name|context|providers] [--desc] [--format table|json|yaml]
```

- Displays all available models with enhanced table output (Name, ID, Context, Input/Output pricing).
- Optional positional `filters` performs case-insensitive substring matches against model id and name using AND logic.
- Context values are displayed with K suffix (e.g., 128K).
- Input/Output prices are shown per million tokens in USD.
- **Change Detection**: Automatically detects new models and pricing changes compared to previous runs with the same parameters. New models are shown in a separate table, and pricing changes are highlighted in yellow.

Options:
- `--format [table|json|yaml]` (default: table)
- `--with-providers` add a Providers column (makes extra API calls per model)
- `--sort-by [id|name|context|providers]` (default: id)
- `--desc` sort descending
- `--tools / --no-tools` filter to models that do or do not support tool calling
- `--reasoning / --no-reasoning` filter to models that require (or exclude) reasoning-capable providers
- `--img / --no-img` filter to models that accept (or exclude) image input

#### endpoints

```bash
openrouter-inspector endpoints MODEL_ID [--min-quant VALUE] [--min-context VALUE] [--sort-by provider|model|quant|context|maxout|price_in|price_out] [--desc] [--per-1m] [--format table|json|yaml]
```

Shows detailed provider offers for an exact model id (`author/slug`), with:
- Provider, Model (provider endpoint name), Reason (+/-), Quant, Context (K), Max Out (K), Input/Output price (USD/1M)

Behavior:
- Fails if model id does not match an exact existing model or returns no offers.

Filters and sorting:
- `--min-quant VALUE` minimum quantization (e.g., fp8). Unspecified quant (“—”) is included as best.
- `--min-context VALUE` minimum context window (e.g., `128K` or `131072`).
- `--sort-by [provider|model|quant|context|maxout|price_in|price_out]` (default: provider)
- `--desc` sort descending

#### details

```bash
openrouter-inspector details MODEL_ID PROVIDER_NAME
openrouter-inspector details MODEL_ID@PROVIDER_NAME
```

Displays comprehensive model parameters and supported features for a specific provider endpoint, including:
- Model identification and provider information
- Context window and token limits
- Pricing per million tokens (input/output)
- Feature support (reasoning, tool calling, image input)
- Technical details (quantization method)
- Performance metrics and uptime statistics
- Current endpoint status

The command also provides helpful hints showing the exact commands needed to:
- Check latency: `openrouter-inspector ping MODEL_ID@PROVIDER_NAME`
- Benchmark throughput: `openrouter-inspector benchmark MODEL_ID@PROVIDER_NAME`

Examples:
```bash
# Show details for a specific model and provider combination
openrouter-inspector details tngtech/deepseek-r1t2-chimera:free Chutes

# Using @ shorthand syntax
openrouter-inspector details tngtech/deepseek-r1t2-chimera:free@Chutes

# On Windows PowerShell, quote the @ syntax to avoid parsing issues:
openrouter-inspector details "tngtech/deepseek-r1t2-chimera:free@Chutes"
```

Behavior:
- Requires both model ID and provider name to be specified
- Fails if the model ID doesn't exist or the provider doesn't offer that model
- Shows available providers in error message if provider not found

#### check

```bash
openrouter-inspector check MODEL_ID PROVIDER_NAME ENDPOINT_NAME
```

Checks a specific provider endpoint's health using OpenRouter API status. Web-scraped metrics have been removed.

Behavior:
- Returns one of: `Functional`, `Disabled`.
- If API indicates provider is offline/disabled or not available → `Disabled`.
- Otherwise → `Functional`.

Options:
- `--log-level [CRITICAL|ERROR|WARNING|INFO|DEBUG|NOTSET]` set logging level

#### ping

```bash
openrouter-inspector ping MODEL_ID [PROVIDER_NAME]
openrouter-inspector ping MODEL_ID@PROVIDER_NAME

# Examples
openrouter-inspector ping openai/o4-mini
openrouter-inspector ping deepseek/deepseek-chat-v3-0324:free Chutes
openrouter-inspector ping deepseek/deepseek-chat-v3-0324:free@Chutes
```

- Performs an end-to-end chat completion call to verify the functional state of a model or a specific provider endpoint.
- Uses a tiny “Ping/Pong” prompt and minimizes completion size for a fast and inexpensive check.
- When a provider is specified (positional or `@` shorthand), the request pins routing order to that provider and disables fallbacks.
- Prints the provider that served the request, token usage, USD cost (unrounded when provided by the API), measured latency, and effective TTL.
- Returns OS exit code `0` on 100% success (zero packet loss) and `1` otherwise, making it suitable for scripting.

Behavior:
- Default timeout: 60s. Change via `--timeout <seconds>`.
- Default ping count: 3. Change via `-n <count>` or `-c <count>`.
- Reasoning minimized by default for low-cost pings (reasoning.effort=low, exclude=true; legacy include_reasoning=false).
- Caps `max_tokens` to 4 for expected “Pong” reply.
- Dynamically formats latency: `<1000ms` prints in `ms`; `>=1s` prints in seconds with two decimals (e.g., `1.63s`).

Options:
- `--timeout <seconds>`: Per-request timeout override (defaults to 60 if missing or invalid).
- `-n <count>`, `-c <count>`: Number of pings to send (defaults to 3).
- `--filthy-rich`: Required if sending more than 10 pings to acknowledge potential API costs.
- `--log-level [CRITICAL|ERROR|WARNING|INFO|DEBUG|NOTSET]`: Set logging level.

Example output:

```

Pinging https://openrouter.ai/api/v1/chat/completions/tngtech/deepseek-r1t2-chimera:free@Chutes with 26 input tokens:
Reply from: https://openrouter.ai/api/v1/chat/completions/tngtech/deepseek-r1t2-chimera:free@Chutes tokens: 4 cost: $0.00 time=2.50s TTL=60s

Pinging https://openrouter.ai/api/v1/chat/completions/tngtech/deepseek-r1t2-chimera:free@Chutes with 26 input tokens:
Reply from: https://openrouter.ai/api/v1/chat/completions/tngtech/deepseek-r1t2-chimera:free@Chutes tokens: 4 cost: $0.00 time=2.30s TTL=60s

Ping statistics for tngtech/deepseek-r1t2-chimera:free@Chutes:
    Packets: Sent = 2, Received = 2, Lost = 0 (0% loss),
Approximate round trip times in seconds:
    Minimum = 2.30s, Maximum = 2.50s, Average = 2.40s
Total API cost for this run: $0.000000

```

Notes:
- Provider pinning uses the OpenRouter provider routing preferences (order, allow_fallbacks=false when a provider is specified). See provider routing docs for details.

> ⚠️ **Warning**
>
> Running `ping` against paid endpoints will make a real completion call and can consume your API credits. It is not a simulated or “no-op” health check. Use with care on metered providers.
>
> Additionally, even when using "free" models, each ping counts against the daily request limit of OpenRouter's free tier. Use with caution, especially if incorporating the command into monitoring scripts or frequent, automated checks.

#### benchmark

```bash
openrouter-inspector benchmark MODEL_ID [PROVIDER_NAME] \
  [--timeout <seconds>] [--max-tokens <limit>] [--format table|json|text] [--min-tps <threshold>] [--debug-response] [--prompt-file <file>]
```

- Measures model or provider-specific throughput (tokens per second, TPS) by streaming a long response.
- When **`PROVIDER_NAME`** is specified (either as a second positional argument *or* using the shorthand `MODEL_ID@PROVIDER_NAME`), routing is *pinned* to that provider and fallbacks are disabled. If omitted, OpenRouter automatically selects the best provider.
- Supports multiple output modes so you can use it in scripts:
  - `table` (default): Rich table with metrics (Status, Duration, Input/Output/Total tokens, Throughput, Cost). Includes a short “Benchmarking …” preface.
  - `json`: Emits a JSON object with the same metrics as the table.
  - `text`: Emits a single line: `TPS: <value>`.

> ⚠️ **Warning**
>
> `benchmark` sends real chat completion requests and streams long responses. On paid providers this can incur non-trivial costs, especially with larger `--max-tokens` or repeated runs. Even for "free" models, requests may count against rate or daily usage quotas. Use with care, prefer smaller `--max-tokens`, and consider testing on free tiers first.

Options:
- `--timeout <seconds>`: Request timeout (default: 120).
- `--max-tokens <limit>`: Safety cap for generated tokens (default: 3000).
- `--format [table|json|text]`: Output format (default: table).
- `--min-tps <threshold>`: Enforce a minimum TPS threshold (range 1–10000) in `text` mode. Exit code is `1` when measured TPS is lower than threshold, otherwise `0`.
- `--debug-response`: Print streaming chunk JSON for debugging (noisy).
- `--prompt-file <file>`: Override the default throughput prompt with the contents of a custom file. The file must exist and be readable. If invalid, the command fails with exit code `2`.

Examples:

```bash
# Human-friendly table for auto-selected provider
openrouter-inspector benchmark google/gemini-2.0-flash-exp:free

# Pin benchmark to a specific provider (positional argument)
openrouter-inspector benchmark google/gemini-2.0-flash-exp:free Chutes

# Same, using @ shorthand
openrouter-inspector benchmark google/gemini-2.0-flash-exp:free@Chutes

# JSON for automation
openrouter-inspector benchmark google/gemini-2.0-flash-exp:free --format json

# Text-only TPS with threshold suitable for CI/monitoring (non-zero exit code on breach)
openrouter-inspector benchmark google/gemini-2.0-flash-exp:free --format text --min-tps 200

# Use a custom benchmark prompt
openrouter-inspector benchmark google/gemini-2.0-flash-exp:free --prompt-file ./config/prompts/my-throughput.md
```

Scripting/monitoring notes:
- In `text` format with `--min-tps`, the command exits with code `1` if TPS is below the threshold (else `0`). Use this in CI/CD, cron, or health checks.
- In `table`/`json` formats, the exit code reflects execution success, not a threshold check.

### Examples

```bash
# Top-level listing filtered by vendor substring
openrouter-inspector list "google"

# List models with multiple filters (AND logic)
openrouter-inspector list "meta" "free"

# Endpoints with filters and sorting: min quant fp8, min context 128K, sort by price_out desc
openrouter-inspector endpoints deepseek/deepseek-r1 --min-quant fp8 --min-context 128K --sort-by price_out --desc

# Lightweight mode with sorting
openrouter-inspector --list --sort-by name
```

## Notes

- Models are retrieved from `/api/v1/models`. Provider offers per model are retrieved from `/api/v1/models/:author/:slug/endpoints`.
- Supported parameters listed on `/models` are a union across providers. Use `/endpoints` for per-provider truth.
- Some fields may vary by provider (context, pricing, features); the CLI reflects these differences.

### Contributing

Contributors are welcome! Feel free to fork this project, add any new features or fix bugs. Submit PRs to the `dev` branch once completed.

For development setup, installation from source, QA/testing, and pre-release checks, see the contributor guide.

[CONTRIBUTING.md](CONTRIBUTING.md)


## License

MIT License - see LICENSE file for details.
