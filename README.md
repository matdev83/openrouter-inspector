# OpenRouter Inspector

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
│   └── utils.py            # Utilities
├── tests/                  # Test suite
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── fixtures/          # Test fixtures
├── pyproject.toml         # Project configuration
└── README.md              # This file
```

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

# Search models by name/id with optional filters
openrouter-inspector search "gpt-4" --min-context 128000 --supports-tools

# Detailed provider endpoints (exact model id), prices per 1M tokens
openrouter-inspector endpoints deepseek/deepseek-r1 --per-1m
```

Lightweight flags (no subcommand):

```bash
# List all models
openrouter-inspector --list

# List filtered models
openrouter-inspector --list --search "anthropic"

# List models with multiple filters (AND logic)
openrouter-inspector --list --search "meta free"

# Simple search (same as subcommand without extra filters)
openrouter-inspector --search "gpt-4"
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

#### search

```bash
openrouter-inspector search QUERY [options]
```

Searches models by name/id with optional filters.

Options:
- `--min-context INT` minimum context window
- `--supports-tools` or `--no-supports-tools`
- `--reasoning-only`
- `--format [table|json|yaml]`


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

### Examples

```bash
# Top-level listing filtered by vendor substring
openrouter-inspector list "google"

# List models with multiple filters (AND logic)
openrouter-inspector list "meta" "free"

# Lightweight list + filter
openrouter-inspector --list --search "openai"

# Lightweight list with multiple filters (AND logic)
openrouter-inspector --list --search "meta free"

# Endpoints with filters and sorting: min quant fp8, min context 128K, sort by price_out desc
openrouter-inspector endpoints deepseek/deepseek-r1 --min-quant fp8 --min-context 128K --sort-by price_out --desc

# Lightweight mode with sorting
openrouter-inspector --list --search "openai" --sort-by name
```

## Notes

- Models are retrieved from `/api/v1/models`. Provider offers per model are retrieved from `/api/v1/models/:author/:slug/endpoints`.
- Supported parameters listed on `/models` are a union across providers. Use `/endpoints` for per-provider truth.
- Some fields may vary by provider (context, pricing, features); the CLI reflects these differences.

## License

MIT License - see LICENSE file for details.
