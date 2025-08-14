"""Domain-specific parsing utilities."""

from typing import Any


def parse_quantization_bits(q: str | None) -> float:
    """Parse quantization string to numeric bits value.

    Args:
        q: Quantization string (e.g., 'fp8', 'bf16', '4bit').

    Returns:
        Numeric bits value, with unspecified treated as best (inf).
    """
    if not q:
        return float("inf")  # treat unspecified as best
    s = q.lower()
    if "bf16" in s:
        return 16
    # extract first integer in string
    num = ""
    for ch in s:
        if ch.isdigit():
            num += ch
    try:
        return float(num) if num else 0.0
    except Exception:
        return 0.0


def parse_context_threshold(v: str | None) -> int:
    """Parse context threshold string to integer value.

    Args:
        v: Context threshold string (e.g., '128K', '131072').

    Returns:
        Integer context threshold value.
    """
    if v is None:
        return 0
    s = str(v).strip()
    try:
        if s.lower().endswith("k"):
            return int(float(s[:-1]) * 1000)
        return int(float(s))
    except Exception:
        return 0


def check_parameter_support(supported_parameters: Any, parameter: str) -> bool:
    """Check if a parameter is supported based on supported_parameters.

    Args:
        supported_parameters: The supported parameters (list or dict).
        parameter: The parameter name to check for.

    Returns:
        True if the parameter is supported, False otherwise.
    """
    if isinstance(supported_parameters, list):
        return any(
            (isinstance(x, str) and (x == parameter or x.startswith(parameter)))
            for x in supported_parameters
        )
    elif isinstance(supported_parameters, dict):
        return bool(supported_parameters.get(parameter, False))
    return False
