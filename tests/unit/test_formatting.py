"""Tests for the formatting utilities."""

from decimal import Decimal

from src.common.formatting import fmt_money


class TestFmtMoney:
    """Test cases for the fmt_money function."""

    def test_format_float(self):
        """Test formatting a float value."""
        assert fmt_money(12.3) == "12.30"
        assert fmt_money(5.567) == "5.57"
        assert fmt_money(100.0) == "100.00"

    def test_format_decimal(self):
        """Test formatting a Decimal value."""
        assert fmt_money(Decimal("12.30")) == "12.30"
        assert fmt_money(Decimal("5.567")) == "5.57"
        assert fmt_money(Decimal("100.00")) == "100.00"

    def test_format_integer(self):
        """Test formatting integer values."""
        assert fmt_money(100) == "100.00"
        assert fmt_money(0) == "0.00"
        assert fmt_money(1) == "1.00"

    def test_format_negative(self):
        """Test formatting negative values."""
        assert fmt_money(-12.30) == "-12.30"
        assert fmt_money(Decimal("-5.567")) == "-5.57"

    def test_format_rounding(self):
        """Test proper rounding behavior."""
        assert fmt_money(12.345) == "12.35"  # Round up
        assert fmt_money(12.344) == "12.34"  # Round down
        # Decimal uses banker's rounding (round half to even)
        assert fmt_money(Decimal("12.345")) == "12.34"  # Round half to even
        assert fmt_money(Decimal("12.355")) == "12.36"  # Round half to even

    def test_format_zero(self):
        """Test formatting zero values."""
        assert fmt_money(0) == "0.00"
        assert fmt_money(0.0) == "0.00"
        assert fmt_money(Decimal("0")) == "0.00"
