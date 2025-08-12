"""Formatting utilities for consistent string conversions."""

from decimal import Decimal


def fmt_money(value: Decimal | float) -> str:
    """Format a monetary value to 2 decimal places.

    Args:
        value: The monetary value to format (Decimal or float)

    Returns:
        A formatted string with exactly 2 decimal places

    Examples:
        >>> fmt_money(12.3)
        '12.30'
        >>> fmt_money(Decimal('5.567'))
        '5.57'
        >>> fmt_money(100)
        '100.00'
    """
    return f"{Decimal(value).quantize(Decimal('0.01')):.2f}"
