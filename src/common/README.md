# Common Utilities

This package contains common utilities for consistent formatting and data manipulation across the project.

## Formatting Module

### fmt_money

The `fmt_money` function provides consistent 2-decimal place formatting for monetary values.

```python
from src.common.formatting import fmt_money
from decimal import Decimal

# Format float values
print(fmt_money(12.3))      # "12.30"
print(fmt_money(5.567))     # "5.57"

# Format Decimal values (recommended for financial calculations)
print(fmt_money(Decimal("12.30")))   # "12.30"
print(fmt_money(Decimal("5.567")))   # "5.57"

# Format integer values
print(fmt_money(100))       # "100.00"

# Handle negative values
print(fmt_money(-42.50))    # "-42.50"
```

### Usage in Model Pricing

This utility is particularly useful when displaying pricing information from API responses:

```python
from src.common.formatting import fmt_money
from decimal import Decimal

# Example: formatting API response prices
def format_model_prices(input_price, output_price):
    """Format model pricing for display."""
    return {
        "input_cost": fmt_money(Decimal(str(input_price))),
        "output_cost": fmt_money(Decimal(str(output_price)))
    }

# Usage
prices = format_model_prices(0.00015, 0.0006)
print(f"Input: ${prices['input_cost']}, Output: ${prices['output_cost']}")
# Output: "Input: $0.00, Output: $0.00"
```

### Best Practices

1. **Use Decimal for financial calculations**: Always convert to `Decimal` for precise monetary calculations
2. **Consistent formatting**: Use `fmt_money` for all monetary display values
3. **Centralized location**: All money formatting logic is kept in one place for easy maintenance
