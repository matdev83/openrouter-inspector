# OpenRouter Inspector

[![CI](https://github.com/matdev83/openrouter-inspector/workflows/CI/badge.svg)](https://github.com/matdev83/openrouter-inspector/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/matdev83/openrouter-inspector/branch/main/graph/badge.svg)](https://codecov.io/gh/matdev83/openrouter-inspector)
[![PyPI version](https://badge.fury.io/py/openrouter-inspector.svg)](https://badge.fury.io/py/openrouter-inspector)
[![Python versions](https://img.shields.io/pypi/pyversions/openrouter-inspector.svg)](https://pypi.org/project/openrouter-inspector/)  
Requires Python 3.10+
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![security: bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit)
[![Pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)

A lightweight CLI for exploring OpenRouter AI models and provider-specific offers.

## Installation

### Development Setup

1. Clone the repository
2. Run the development setup script:
   ```bash
   python setup_dev.py
   ```
3. Activate the virtual environment:
   - On Windows: `.venv\Scripts\activate.bat`
   - On Unix/macOS: `source .venv/bin/activate`

### Using Make (optional)

If you have `make` installed, you can use the provided Makefile:

```bash
# Set up development environment
make setup-dev

# Install in development mode
make install-dev

# Run tests
make test

# Run quality assurance checks
make qa
```

## Development

### Project Structure

```
openrouter-inspector/
├── openrouter_inspector/    # Main package
│   ├── __init__.py
│   ├── cli.py              # CLI interface
│   ├── client.py           # API client
│   ├── services.py         # Business logic
│   ├── models.py           # Data models
│   ├── cache.py            # Response caching for change detection
│   └── utils.py            # Utilities
├── data/                   # Cache files for change detection
├── tests/                  # Test suite
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── fixtures/          # Test fixtures
├── pyproject.toml         # Project configuration
└── README.md              # This file
```

### Change Detection

The `list` command automatically tracks changes between runs:

- **New Models**: When new models become available, they're displayed in a separate "🆕 New Models Since Last Run" table
- **Pricing Changes**: Modified input/output token prices are highlighted in yellow in the main table
- **Separate Tracking**: Each unique combination of command parameters maintains its own change history
- **No Caching**: API calls are always made; cached data is used only for comparison

### Quality Assurance

The project uses several tools for code quality:

- **Black**: Code formatting
- **Ruff**: Linting and error detection
- **MyPy**: Static type checking
- **Pytest**: Testing framework

Run all QA checks with:
```bash
make qa
```

### Testing

Run tests with coverage:
```bash
pytest --cov=openrouter_inspector --cov-report=html
```

## Usage

The CLI supports both subcommands and lightweight global flags.

### Authentication

Set your OpenRouter API key via environment variable (required):

```bash
export OPENROUTER_API_KEY=sk-or-...
```

For security, the CLI does not accept API keys via command-line flags. It reads the key only from the `OPENROUTER_API_KEY` environment variable. If the key is missing or invalid, the CLI shows a friendly error and exits.

### Quick starts

Subcommands:

```bash
# List all models
openrouter-inspector list

# List models filtered by substring (matches id or display name)
openrouter-inspector list "openai"

# List models with multiple filters (AND logic)
openrouter-inspector list "meta" "free"

# Detailed provider endpoints (exact model id), prices per 1M tokens
openrouter-inspector endpoints deepseek/deepseek-r1 --per-1m
```

Lightweight flags (no subcommand):

```bash
# List all models
openrouter-inspector --list
```

Direct search (without explicit command):

```bash
# Search for models containing "openai"
openrouter-inspector openai

# Search for models containing "gpt-4"
openrouter-inspector gpt-4

# Search with multiple terms (AND logic)
openrouter-inspector openai gpt
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

Examples:
```bash
# List all models
openrouter-inspector list

# List models containing "openai" 
openrouter-inspector list "openai"

# List models containing BOTH "meta" AND "free"
openrouter-inspector list "meta" "free"

# List models with providers count
openrouter-inspector list --with-providers

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

## License

MIT License - see LICENSE file for details.
