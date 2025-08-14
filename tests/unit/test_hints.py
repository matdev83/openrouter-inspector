"""Tests for the hint system."""

from openrouter_inspector.hints import HintService
from openrouter_inspector.hints.context import HintContext
from openrouter_inspector.hints.providers import (
    DetailsHintProvider,
    EndpointsHintProvider,
    ListHintProvider,
    SearchHintProvider,
)


class TestHintContext:
    """Test cases for HintContext."""

    def test_hint_context_creation(self):
        """Test creating a hint context."""
        context = HintContext(
            command_name="endpoints",
            model_id="test/model",
            provider_name="TestProvider",
        )

        assert context.command_name == "endpoints"
        assert context.model_id == "test/model"
        assert context.provider_name == "TestProvider"

    def test_hint_context_with_methods(self):
        """Test context builder methods."""
        context = HintContext(command_name="test")

        new_context = context.with_model("test/model").with_provider("TestProvider")

        assert new_context.model_id == "test/model"
        assert new_context.provider_name == "TestProvider"
        assert new_context.command_name == "test"


class TestHintProviders:
    """Test cases for hint providers."""

    def test_list_hint_provider(self):
        """Test ListHintProvider."""
        provider = ListHintProvider()
        context = HintContext(command_name="list", example_model_id="test/model")

        hints = provider.get_hints(context)

        assert len(hints) == 2
        assert "Show provider endpoints for a model:" in hints
        assert "  openrouter-inspector endpoints test/model" in hints

    def test_endpoints_hint_provider(self):
        """Test EndpointsHintProvider."""
        from datetime import datetime

        from openrouter_inspector.models import ProviderDetails, ProviderInfo

        provider = EndpointsHintProvider()

        # Create mock provider data
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

        context = HintContext(
            command_name="endpoints", model_id="test/model", data=provider_details
        )

        hints = provider.get_hints(context)

        assert len(hints) == 8  # 3 commands + 5 separators/descriptions
        assert "Show detailed parameters for a provider:" in hints
        assert "  openrouter-inspector details test/model@TestProvider" in hints
        assert "Check latency:" in hints
        assert "  openrouter-inspector ping test/model@TestProvider" in hints
        assert "Benchmark throughput:" in hints
        assert "  openrouter-inspector benchmark test/model@TestProvider" in hints

    def test_details_hint_provider(self):
        """Test DetailsHintProvider."""
        provider = DetailsHintProvider()
        context = HintContext(
            command_name="details", model_id="test/model", provider_name="TestProvider"
        )

        hints = provider.get_hints(context)

        assert len(hints) == 5  # 2 commands + 3 separators/descriptions
        assert "Check latency:" in hints
        assert "  openrouter-inspector ping test/model@TestProvider" in hints
        assert "Benchmark throughput:" in hints
        assert "  openrouter-inspector benchmark test/model@TestProvider" in hints

    def test_search_hint_provider(self):
        """Test SearchHintProvider."""
        provider = SearchHintProvider()
        context = HintContext(command_name="search", example_model_id="test/model")

        hints = provider.get_hints(context)

        assert len(hints) == 2
        assert "Show provider endpoints for a model:" in hints
        assert "  openrouter-inspector endpoints test/model" in hints


class TestHintService:
    """Test cases for HintService."""

    def test_hint_service_initialization(self):
        """Test HintService initialization."""
        service = HintService()

        assert service.supports_hints("list")
        assert service.supports_hints("endpoints")
        assert service.supports_hints("details")
        assert service.supports_hints("search")
        assert not service.supports_hints("unknown")

    def test_hint_service_get_hints(self):
        """Test getting hints from service."""
        service = HintService()
        context = HintContext(command_name="list", example_model_id="test/model")

        hints = service.get_hints(context)

        assert len(hints) > 0
        assert "  openrouter-inspector endpoints test/model" in hints

    def test_hint_service_register_provider(self):
        """Test registering custom hint provider."""
        service = HintService()

        class CustomHintProvider:
            def get_hints(self, context):
                return ["Custom hint"]

        custom_provider = CustomHintProvider()
        service.register_provider("custom", custom_provider)

        assert service.supports_hints("custom")

        context = HintContext(command_name="custom")
        hints = service.get_hints(context)

        assert hints == ["Custom hint"]

    def test_hint_service_unknown_command(self):
        """Test getting hints for unknown command."""
        service = HintService()
        context = HintContext(command_name="unknown")

        hints = service.get_hints(context)

        assert hints == []
