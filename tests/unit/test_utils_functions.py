import logging

from openrouter_inspector import utils


def test_normalize_string():
    assert utils.normalize_string("  ABC ") == "abc"
    assert utils.normalize_string(None) == ""


def test_parse_quantization_bits():
    assert utils.parse_quantization_bits("fp8") == 8
    assert utils.parse_quantization_bits("bf16") == 16
    assert utils.parse_quantization_bits("4bit") == 4
    assert utils.parse_quantization_bits(None) == float("inf")


def test_parse_context_threshold():
    assert utils.parse_context_threshold("128K") == 128000
    assert utils.parse_context_threshold("131072") == 131072
    assert utils.parse_context_threshold(None) == 0
    # invalid returns 0
    assert utils.parse_context_threshold("abc") == 0


def test_check_parameter_support():
    assert utils.check_parameter_support(["image", "reasoning"], "image")
    assert not utils.check_parameter_support(["image"], "audio")

    assert utils.check_parameter_support({"image": True}, "image")
    assert not utils.check_parameter_support({"image": False}, "image")


def test_configure_logging_sets_level(caplog):
    # Ensure no exception and root logger level set.
    utils.configure_logging("info")
    assert logging.getLogger().level == logging.INFO

    # Invalid level defaults to WARNING
    utils.configure_logging("invalid_level")
    assert logging.getLogger().level == logging.WARNING


def test_configure_logging_without_handlers(monkeypatch):
    """Cover branch that calls ``logging.basicConfig`` when no handlers exist."""
    root = logging.getLogger()
    # Temporarily detach existing handlers
    saved = root.handlers.copy()
    root.handlers.clear()

    try:
        utils.configure_logging(None, default_to_warning=True)
        assert root.level == logging.WARNING
    finally:
        # Restore handlers to avoid side-effects on other tests.
        root.handlers.extend(saved)


def test_configure_logging_non_int_attribute(monkeypatch):
    """Provide a level name that exists on logging but is *not* an int to hit fallback branch."""
    # Monkeypatch the logging module with a dummy attribute.
    monkeypatch.setattr(logging, "SILLY", "not_an_int", raising=False)

    utils.configure_logging("SILLY")
    # Should fall back to WARNING
    assert logging.getLogger().level == logging.WARNING


def test_parse_quantization_bits_invalid():
    """Non-numeric strings should return 0.0."""
    assert utils.parse_quantization_bits("abc") == 0.0


def test_parse_quantization_bits_float_conversion_error(monkeypatch):
    """Force float() to raise to exercise exception branch (lines 104-105)."""

    def _raise(_):  # noqa: ANN001
        raise ValueError

    import builtins

    monkeypatch.setattr(builtins, "float", _raise, raising=True)

    # Digits extracted will be '8', but our patched float raises, so fallback 0.0
    assert utils.parse_quantization_bits("fp8") == 0.0
