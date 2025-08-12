from types import SimpleNamespace

import pytest

from openrouter_inspector.commands.base_command import BaseCommand


class DummyFormatter:
    """Minimal formatter that lets us verify which helper is chosen."""

    def __init__(self, label: str):
        self.label = label
        self.called_with = None

    # The real formatters take *args and **kwargs; we only need one positional.
    def format_models(self, data, **kwargs):  # noqa: ANN001
        self.called_with = ("models", data, kwargs)
        return f"{self.label}:models"

    def format_providers(self, data, **kwargs):  # noqa: ANN001
        self.called_with = ("providers", data, kwargs)
        return f"{self.label}:providers"


class DummyCommand(BaseCommand):
    async def execute(self, *args, **kwargs):  # noqa: D401, ANN001
        return ""


@pytest.mark.asyncio
async def test_format_output_dispatch_models():
    table = DummyFormatter("table")
    jsonf = DummyFormatter("json")
    cmd = DummyCommand(client=None, model_service=None, table_formatter=table, json_formatter=jsonf)  # type: ignore[arg-type]

    data = [SimpleNamespace(id="id", name="name")]

    out = cmd._format_output(data, output_format="table")
    assert out == "table:models"
    assert table.called_with[0] == "models"

    out_json = cmd._format_output(data, output_format="json")
    assert out_json == "json:models"
    assert jsonf.called_with[0] == "models"


@pytest.mark.asyncio
async def test_format_output_dispatch_providers():
    table = DummyFormatter("table")
    jsonf = DummyFormatter("json")
    cmd = DummyCommand(client=None, model_service=None, table_formatter=table, json_formatter=jsonf)  # type: ignore[arg-type]

    data = [SimpleNamespace(provider="dummy")]

    out = cmd._format_output(data, output_format="table")
    assert out == "table:providers"
    assert table.called_with[0] == "providers"

    out_json = cmd._format_output(data, output_format="json")
    assert out_json == "json:providers"
    assert jsonf.called_with[0] == "providers"
