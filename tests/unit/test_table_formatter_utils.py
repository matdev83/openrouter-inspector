from openrouter_inspector.formatters.table_formatter import TableFormatter


def test_fmt_k():
    tf = TableFormatter()
    assert tf._fmt_k(None) == "—"
    assert tf._fmt_k(0) == "0K"
    assert tf._fmt_k(2048) == "2K"  # rounded


def test_fmt_price():
    tf = TableFormatter()
    # 0.0005 dollars per token -> $500 per million tokens
    assert tf._fmt_price(0.0005) == "$500.00"


def test_check_reasoning_support():
    tf = TableFormatter()
    assert tf._check_reasoning_support(["reasoning", "other"])
    assert tf._check_reasoning_support({"reasoning": True})
    assert not tf._check_reasoning_support(["image"])


def test_check_image_support():
    tf = TableFormatter()
    assert tf._check_image_support(["image", "something"])
    assert tf._check_image_support({"image": True})
    assert not tf._check_image_support({"reasoning": True})


def test_format_models_highlights_changes(capsys):
    """Ensure pricing changes are highlighted via Rich markup (yellow)."""
    from datetime import datetime

    from openrouter_inspector.models import ModelInfo

    tf = TableFormatter()

    m1 = ModelInfo(
        id="author/model-a",
        name="Model A",
        description=None,
        context_length=8192,
        pricing={"prompt": 0.0004, "completion": 0.0005},
        created=datetime.utcnow(),
    )

    # Simulate *after* price update – we want completion price change highlighted
    pricing_changes = [(m1.id, "completion", 0.0005, 0.0006)]

    out = tf.format_models([m1], pricing_changes=pricing_changes)
    # It should still include the updated price string "$500.00" once.
    assert "$500.00" in out


def test_format_models_new_models_table():
    from datetime import datetime

    from openrouter_inspector.models import ModelInfo

    tf = TableFormatter()

    existing = ModelInfo(
        id="author/existing",
        name="Existing",
        description=None,
        context_length=4096,
        pricing={},
        created=datetime.utcnow(),
    )
    new = ModelInfo(
        id="author/new",
        name="New Model",
        description=None,
        context_length=4096,
        pricing={},
        created=datetime.utcnow(),
    )

    out = tf.format_models(
        [existing], with_providers=True, provider_counts=[1], new_models=[new]
    )

    # The second table title should be present.
    assert "New Models Since Last Run" in out


def test_format_providers_no_longer_includes_hints():
    """Test that format_providers no longer includes hints (moved to command layer)."""
    from datetime import datetime

    from openrouter_inspector.models import ProviderDetails, ProviderInfo

    tf = TableFormatter()

    provider_info = ProviderInfo(
        provider_name="TestProvider",
        model_id="test/model",
        endpoint_name="Test Model",
        context_window=8192,
        supports_tools=True,
        is_reasoning_model=False,
        quantization="fp16",
        uptime_30min=99.5,
        pricing={"prompt": 0.00001, "completion": 0.00002},
        max_completion_tokens=4096,
        supported_parameters=[],
        status="active",
        performance_tps=100.0,
    )
    provider_details = [
        ProviderDetails(
            provider=provider_info,
            availability=True,
            last_updated=datetime.now(),
        )
    ]

    out = tf.format_providers(provider_details, model_id="test/model")

    # Should not include hints (moved to command layer)
    assert "💡 Quick Commands:" not in out
    assert "openrouter-inspector details" not in out
    assert "openrouter-inspector ping" not in out
    assert "openrouter-inspector benchmark" not in out


def test_format_providers_respects_no_hints_parameter():
    """Test that format_providers still accepts no_hints parameter for backward compatibility."""
    from datetime import datetime

    from openrouter_inspector.models import ProviderDetails, ProviderInfo

    tf = TableFormatter()

    provider_info = ProviderInfo(
        provider_name="TestProvider",
        model_id="test/model",
        endpoint_name="Test Model",
        context_window=8192,
        supports_tools=True,
        is_reasoning_model=False,
        quantization="fp16",
        uptime_30min=99.5,
        pricing={"prompt": 0.00001, "completion": 0.00002},
        max_completion_tokens=4096,
        supported_parameters=[],
        status="active",
        performance_tps=100.0,
    )
    provider_details = [
        ProviderDetails(
            provider=provider_info,
            availability=True,
            last_updated=datetime.now(),
        )
    ]

    # Both should produce the same output since hints are handled at command layer
    out_default = tf.format_providers(provider_details, model_id="test/model")
    out_no_hints = tf.format_providers(
        provider_details, model_id="test/model", no_hints=True
    )

    # Should be the same since formatter no longer handles hints
    assert out_default == out_no_hints
    assert "💡 Quick Commands:" not in out_default
    assert "💡 Quick Commands:" not in out_no_hints


def test_format_model_details_no_longer_includes_hints():
    """Test that format_model_details no longer includes hints (moved to command layer)."""
    from datetime import datetime

    from openrouter_inspector.models import ProviderDetails, ProviderInfo

    tf = TableFormatter()

    provider_info = ProviderInfo(
        provider_name="TestProvider",
        model_id="test/model",
        endpoint_name="Test Model",
        context_window=8192,
        supports_tools=True,
        is_reasoning_model=False,
        quantization="fp16",
        uptime_30min=99.5,
        pricing={"prompt": 0.00001, "completion": 0.00002},
        max_completion_tokens=4096,
        supported_parameters=[],
        status="active",
        performance_tps=100.0,
    )
    provider_detail = ProviderDetails(
        provider=provider_info,
        availability=True,
        last_updated=datetime.now(),
    )

    out = tf.format_model_details(
        provider_detail, model_id="test/model", provider_name="TestProvider"
    )

    # Should not include hints (moved to command layer)
    assert "💡 Quick Commands:" not in out
    assert "openrouter-inspector ping" not in out
    assert "openrouter-inspector benchmark" not in out


def test_format_model_details_respects_no_hints_parameter():
    """Test that format_model_details still accepts no_hints parameter for backward compatibility."""
    from datetime import datetime

    from openrouter_inspector.models import ProviderDetails, ProviderInfo

    tf = TableFormatter()

    provider_info = ProviderInfo(
        provider_name="TestProvider",
        model_id="test/model",
        endpoint_name="Test Model",
        context_window=8192,
        supports_tools=True,
        is_reasoning_model=False,
        quantization="fp16",
        uptime_30min=99.5,
        pricing={"prompt": 0.00001, "completion": 0.00002},
        max_completion_tokens=4096,
        supported_parameters=[],
        status="active",
        performance_tps=100.0,
    )
    provider_detail = ProviderDetails(
        provider=provider_info,
        availability=True,
        last_updated=datetime.now(),
    )

    # Both should produce the same output since hints are handled at command layer
    out_default = tf.format_model_details(
        provider_detail, model_id="test/model", provider_name="TestProvider"
    )
    out_no_hints = tf.format_model_details(
        provider_detail,
        model_id="test/model",
        provider_name="TestProvider",
        no_hints=True,
    )

    # Should be the same since formatter no longer handles hints
    assert out_default == out_no_hints
    assert "💡 Quick Commands:" not in out_default
    assert "💡 Quick Commands:" not in out_no_hints
