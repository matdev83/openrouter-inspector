import importlib
from datetime import datetime
from unittest import mock

import pytest

from openrouter_inspector.client import OpenRouterClient


@pytest.fixture(autouse=True)
def reload_main_module():
    """Ensure we reload the __main__ module fresh for every test.

    A fresh import guarantees that any monkey-patching of ``openrouter_inspector.cli.cli``
    is applied before the module-level import inside ``openrouter_inspector.__main__``
    executes.
    """
    # Nothing to do *before* the test – the body yields.
    yield
    # Remove the module so the next test gets a clean import.
    import sys

    sys.modules.pop("openrouter_inspector.__main__", None)


def _make_mock_cli() -> mock.MagicMock:
    """Return a MagicMock that poses as the Click CLI entry point."""
    m = mock.MagicMock(name="mock_cli")
    # Mimic Click's ``commands`` mapping so that __main__.main can inspect it.
    m.commands = {"list": None, "ping": None}
    return m


def test_main_inserts_list_for_unknown_command(monkeypatch):
    """__main__.main should prepend ``list`` when the first arg is not a command."""
    mock_cli = _make_mock_cli()
    # Patch the real ``openrouter_inspector.cli`` module before importing __main__.
    cli_module = importlib.import_module("openrouter_inspector.cli")
    monkeypatch.setattr(cli_module, "cli", mock_cli, raising=True)
    mock_cli.commands = {"list": None, "ping": None}

    # Import (or reload) the __main__ module so it picks up our patched ``cli``.
    main_mod = importlib.import_module("openrouter_inspector.__main__")

    # Call with an unrecognised first argument.
    main_mod.main(["unknown", "filter"])

    # ``cli`` should have been invoked once with the transformed args.
    assert mock_cli.call_count == 1
    passed_args = mock_cli.call_args.kwargs["args"]
    assert passed_args == ["list", "unknown", "filter"]


def test_main_respects_known_command(monkeypatch):
    """If the first argument *is* a known command, it should not be altered."""
    mock_cli = _make_mock_cli()
    cli_module = importlib.import_module("openrouter_inspector.cli")
    monkeypatch.setattr(cli_module, "cli", mock_cli, raising=True)
    mock_cli.commands = {"list": None, "ping": None}

    main_mod = importlib.import_module("openrouter_inspector.__main__")

    main_mod.main(["ping", "some-model"])

    passed_args = mock_cli.call_args.kwargs["args"]
    assert passed_args[0] == "ping"


# --------------------------------------------------------------------------------------
# ``OpenRouterClient._parse_datetime`` – cover multiple branches
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value, expected_year",
    [
        ("2024-06-01T12:34:56Z", 2024),  # ISO with Z suffix
        ("1719843496", 2024),  # second-precision numeric string (2024-07-02T…)
        (1719843496000, 2024),  # millisecond epoch int
        (1719843496.0, 2024),  # float seconds
    ],
)
def test_parse_datetime_recognised_formats(value, expected_year):
    client = OpenRouterClient(api_key="dummy")
    dt = client._parse_datetime(value)  # type: ignore[arg-type]
    # All inputs decode to a datetime in the expected year.
    assert isinstance(dt, datetime)
    assert dt.year == expected_year


def test_parse_datetime_invalid_returns_now():
    """Unparseable input should fall back to a value very close to *now*."""
    client = OpenRouterClient(api_key="dummy")

    before = datetime.now()
    dt = client._parse_datetime("not-a-date")  # type: ignore[arg-type]
    after = datetime.now()

    # dt should be between *before* and *after* timestamps (± ~1 s window).
    assert before <= dt <= after
