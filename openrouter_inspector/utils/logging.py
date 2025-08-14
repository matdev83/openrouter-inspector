"""Logging configuration utilities."""

import logging


def configure_logging(
    level_name: str | None, *, default_to_warning: bool = False
) -> None:
    """Configure root logging level.

    Defaults to WARNING if not provided or invalid.

    Args:
        level_name: The logging level name (e.g., 'DEBUG', 'INFO', 'WARNING').
        default_to_warning: Whether to default to WARNING level if level_name is None.
    """
    if level_name is None:
        if not default_to_warning:
            return
        level_value = logging.WARNING
    else:
        try:
            level_value = getattr(logging, level_name.upper())
            if not isinstance(level_value, int):
                level_value = logging.WARNING
        except Exception:
            level_value = logging.WARNING
    root_logger = logging.getLogger()
    if root_logger.handlers:
        root_logger.setLevel(level_value)
    else:
        logging.basicConfig(level=level_value)
