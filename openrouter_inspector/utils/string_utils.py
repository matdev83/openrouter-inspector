"""String manipulation utilities."""


def normalize_string(s: str | None) -> str:
    """Normalize a string for comparison purposes.

    Args:
        s: The string to normalize.

    Returns:
        Normalized string (lowercase and stripped).
    """
    return (s or "").strip().lower()
