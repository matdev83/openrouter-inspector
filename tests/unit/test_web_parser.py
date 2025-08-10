"""Unit tests for the OpenRouter web parser."""

import pytest
from datetime import datetime

from openrouter_inspector.web_parser import OpenRouterWebParser
from openrouter_inspector.models import WebProviderData


class TestOpenRouterWebParser:
    """Test cases for OpenRouterWebParser class."""

    def test_parse_throughput_valid_formats(self):
        """Test parsing various valid throughput formats."""
        test_cases = [
            ("15.2 TPS", 15.2),
            ("12 tokens/s", 12.0),
            ("8.5 tokens per second", 8.5),
            ("20 t/s", 20.0),
            ("5.75", 5.75),  # Just a number
            ("100 TPS", 100.0),
            ("0.5 tokens/s", 0.5),
        ]
        
        for text, expected in test_cases:
            result = OpenRouterWebParser.parse_throughput(text)
            assert result == expected, f"Failed to parse '{text}', expected {expected}, got {result}"

    def test_parse_throughput_invalid_formats(self):
        """Test parsing invalid throughput formats returns None."""
        invalid_cases = [
            "—", "-", "N/A", "", "   ", "invalid", "abc TPS", "TPS 15"
        ]
        
        for text in invalid_cases:
            result = OpenRouterWebParser.parse_throughput(text)
            assert result is None, f"Expected None for '{text}', got {result}"

    def test_parse_latency_valid_formats(self):
        """Test parsing various valid latency formats."""
        test_cases = [
            ("0.85s", 0.85),
            ("850ms", 0.85),
            ("1.2 seconds", 1.2),
            ("500 ms", 0.5),
            ("2.5", 2.5),  # Just a number, assume seconds
            ("1 minute", 60.0),
            ("0.5 minutes", 30.0),
        ]
        
        for text, expected in test_cases:
            result = OpenRouterWebParser.parse_latency(text)
            assert result == expected, f"Failed to parse '{text}', expected {expected}, got {result}"

    def test_parse_latency_invalid_formats(self):
        """Test parsing invalid latency formats returns None."""
        invalid_cases = [
            "—", "-", "N/A", "", "   ", "invalid", "abc ms", "s 850"
        ]
        
        for text in invalid_cases:
            result = OpenRouterWebParser.parse_latency(text)
            assert result is None, f"Expected None for '{text}', got {result}"

    def test_parse_uptime_valid_formats(self):
        """Test parsing various valid uptime formats."""
        test_cases = [
            ("99.5%", 99.5),
            ("98.2", 98.2),  # Just a number
            ("100%", 100.0),
            ("0.995", 99.5),  # Decimal format converted to percentage
            ("95.0%", 95.0),
        ]
        
        for text, expected in test_cases:
            result = OpenRouterWebParser.parse_uptime(text)
            assert result == expected, f"Failed to parse '{text}', expected {expected}, got {result}"

    def test_parse_uptime_invalid_formats(self):
        """Test parsing invalid uptime formats returns None."""
        invalid_cases = [
            "—", "-", "N/A", "", "   ", "invalid", "abc%", "% 99", "150%"  # > 100%
        ]
        
        for text in invalid_cases:
            result = OpenRouterWebParser.parse_uptime(text)
            assert result is None, f"Expected None for '{text}', got {result}"

    def test_parse_model_page_empty_content(self):
        """Test parsing empty HTML content raises ValueError."""
        with pytest.raises(ValueError, match="HTML content cannot be empty"):
            OpenRouterWebParser.parse_model_page("", "test/model")
        
        with pytest.raises(ValueError, match="HTML content cannot be empty"):
            OpenRouterWebParser.parse_model_page("   ", "test/model")

    def test_parse_model_page_invalid_html(self):
        """Test parsing invalid HTML content raises ValueError."""
        with pytest.raises(ValueError, match="HTML content cannot be empty"):
            # This should cause the empty content check to fail
            OpenRouterWebParser.parse_model_page(None, "test/model")

    def test_parse_model_page_simple_table(self):
        """Test parsing a simple provider table."""
        html_content = """
        <html>
        <body>
            <table>
                <tr>
                    <th>Provider</th>
                    <th>Throughput</th>
                    <th>Latency</th>
                    <th>Uptime</th>
                </tr>
                <tr>
                    <td>DeepInfra</td>
                    <td>15.2 TPS</td>
                    <td>0.85s</td>
                    <td>99.5%</td>
                </tr>
                <tr>
                    <td>Lambda</td>
                    <td>12.8 TPS</td>
                    <td>1.20s</td>
                    <td>98.9%</td>
                </tr>
            </table>
        </body>
        </html>
        """
        
        providers = OpenRouterWebParser.parse_model_page(html_content, "test/model")
        
        assert len(providers) == 2
        
        # Check first provider
        assert providers[0].provider_name == "DeepInfra"
        assert providers[0].throughput_tps == 15.2
        assert providers[0].latency_seconds == 0.85
        assert providers[0].uptime_percentage == 99.5
        assert isinstance(providers[0].last_scraped, datetime)
        
        # Check second provider
        assert providers[1].provider_name == "Lambda"
        assert providers[1].throughput_tps == 12.8
        assert providers[1].latency_seconds == 1.20
        assert providers[1].uptime_percentage == 98.9

    def test_parse_model_page_partial_data(self):
        """Test parsing table with missing data columns."""
        html_content = """
        <html>
        <body>
            <table>
                <tr>
                    <th>Provider</th>
                    <th>Throughput</th>
                </tr>
                <tr>
                    <td>DeepInfra</td>
                    <td>15.2 TPS</td>
                </tr>
                <tr>
                    <td>Lambda</td>
                    <td>—</td>
                </tr>
            </table>
        </body>
        </html>
        """
        
        providers = OpenRouterWebParser.parse_model_page(html_content, "test/model")
        
        assert len(providers) == 2
        
        # Check first provider
        assert providers[0].provider_name == "DeepInfra"
        assert providers[0].throughput_tps == 15.2
        assert providers[0].latency_seconds is None
        assert providers[0].uptime_percentage is None
        
        # Check second provider with missing throughput
        assert providers[1].provider_name == "Lambda"
        assert providers[1].throughput_tps is None
        assert providers[1].latency_seconds is None
        assert providers[1].uptime_percentage is None

    def test_parse_model_page_different_column_order(self):
        """Test parsing table with different column order."""
        html_content = """
        <html>
        <body>
            <table>
                <tr>
                    <th>Uptime</th>
                    <th>Provider Name</th>
                    <th>Latency</th>
                    <th>TPS</th>
                </tr>
                <tr>
                    <td>99.5%</td>
                    <td>DeepInfra</td>
                    <td>0.85s</td>
                    <td>15.2</td>
                </tr>
            </table>
        </body>
        </html>
        """
        
        providers = OpenRouterWebParser.parse_model_page(html_content, "test/model")
        
        assert len(providers) == 1
        assert providers[0].provider_name == "DeepInfra"
        assert providers[0].throughput_tps == 15.2
        assert providers[0].latency_seconds == 0.85
        assert providers[0].uptime_percentage == 99.5

    def test_parse_model_page_multiple_tables(self):
        """Test parsing page with multiple tables, only provider table should be parsed."""
        html_content = """
        <html>
        <body>
            <table>
                <tr><th>Random</th><th>Data</th></tr>
                <tr><td>Not</td><td>Providers</td></tr>
            </table>
            
            <table>
                <tr>
                    <th>Provider</th>
                    <th>Throughput</th>
                </tr>
                <tr>
                    <td>DeepInfra</td>
                    <td>15.2 TPS</td>
                </tr>
            </table>
        </body>
        </html>
        """
        
        providers = OpenRouterWebParser.parse_model_page(html_content, "test/model")
        
        assert len(providers) == 1
        assert providers[0].provider_name == "DeepInfra"
        assert providers[0].throughput_tps == 15.2

    def test_parse_model_page_no_provider_table(self):
        """Test parsing page with no provider tables returns empty list."""
        html_content = """
        <html>
        <body>
            <h1>Model Information</h1>
            <p>This model has no provider data.</p>
            <table>
                <tr><th>Random</th><th>Data</th></tr>
                <tr><td>Not</td><td>Providers</td></tr>
            </table>
        </body>
        </html>
        """
        
        providers = OpenRouterWebParser.parse_model_page(html_content, "test/model")
        assert len(providers) == 0

    def test_parse_model_page_div_based_layout(self):
        """Test parsing non-table layout with div containers."""
        html_content = """
        <html>
        <body>
            <div class="provider-card">
                <h3 class="provider-name">DeepInfra</h3>
                <p>Throughput: 15.2 TPS</p>
                <p>Latency: 0.85s</p>
                <p>Uptime: 99.5%</p>
            </div>
            <div class="provider-card">
                <h4>Lambda</h4>
                <span>12.8 tokens/s throughput</span>
                <span>1.20 seconds latency</span>
                <span>98.9% uptime</span>
            </div>
        </body>
        </html>
        """
        
        providers = OpenRouterWebParser.parse_model_page(html_content, "test/model")
        
        assert len(providers) == 2
        
        # Check first provider
        assert providers[0].provider_name == "DeepInfra"
        assert providers[0].throughput_tps == 15.2
        assert providers[0].latency_seconds == 0.85
        assert providers[0].uptime_percentage == 99.5
        
        # Check second provider
        assert providers[1].provider_name == "Lambda"
        assert providers[1].throughput_tps == 12.8
        assert providers[1].latency_seconds == 1.20
        assert providers[1].uptime_percentage == 98.9

    def test_parse_model_page_case_insensitive_headers(self):
        """Test parsing with different case headers."""
        html_content = """
        <html>
        <body>
            <table>
                <tr>
                    <th>PROVIDER</th>
                    <th>throughput</th>
                    <th>Latency</th>
                    <th>UPTIME</th>
                </tr>
                <tr>
                    <td>DeepInfra</td>
                    <td>15.2 TPS</td>
                    <td>0.85s</td>
                    <td>99.5%</td>
                </tr>
            </table>
        </body>
        </html>
        """
        
        providers = OpenRouterWebParser.parse_model_page(html_content, "test/model")
        
        assert len(providers) == 1
        assert providers[0].provider_name == "DeepInfra"
        assert providers[0].throughput_tps == 15.2
        assert providers[0].latency_seconds == 0.85
        assert providers[0].uptime_percentage == 99.5

    def test_parse_model_page_alternative_header_names(self):
        """Test parsing with alternative header names."""
        html_content = """
        <html>
        <body>
            <table>
                <tr>
                    <th>Service</th>
                    <th>Tokens per Second</th>
                    <th>Response Time</th>
                    <th>Availability</th>
                </tr>
                <tr>
                    <td>DeepInfra</td>
                    <td>15.2</td>
                    <td>850ms</td>
                    <td>99.5</td>
                </tr>
            </table>
        </body>
        </html>
        """
        
        providers = OpenRouterWebParser.parse_model_page(html_content, "test/model")
        
        assert len(providers) == 1
        assert providers[0].provider_name == "DeepInfra"
        assert providers[0].throughput_tps == 15.2
        assert providers[0].latency_seconds == 0.85  # 850ms converted to seconds
        assert providers[0].uptime_percentage == 99.5

    def test_parse_model_page_empty_rows(self):
        """Test parsing table with empty rows."""
        html_content = """
        <html>
        <body>
            <table>
                <tr>
                    <th>Provider</th>
                    <th>Throughput</th>
                </tr>
                <tr>
                    <td></td>
                    <td>15.2 TPS</td>
                </tr>
                <tr>
                    <td>DeepInfra</td>
                    <td>12.8 TPS</td>
                </tr>
                <tr>
                    <td></td>
                </tr>
            </table>
        </body>
        </html>
        """
        
        providers = OpenRouterWebParser.parse_model_page(html_content, "test/model")
        
        # Should only get the valid row
        assert len(providers) == 1
        assert providers[0].provider_name == "DeepInfra"
        assert providers[0].throughput_tps == 12.8

    def test_extract_metric_from_text_throughput(self):
        """Test extracting throughput from text content."""
        text = "Provider performance: 15.2 TPS with good reliability"
        result = OpenRouterWebParser._extract_metric_from_text(text, 'throughput')
        assert result == 15.2

    def test_extract_metric_from_text_latency(self):
        """Test extracting latency from text content."""
        text = "Response latency: 850ms average"
        result = OpenRouterWebParser._extract_metric_from_text(text, 'latency')
        assert result == 0.85

    def test_extract_metric_from_text_uptime(self):
        """Test extracting uptime from text content."""
        text = "System uptime: 99.5% over last month"
        result = OpenRouterWebParser._extract_metric_from_text(text, 'uptime')
        assert result == 99.5

    def test_extract_metric_from_text_not_found(self):
        """Test extracting metric when not found in text."""
        text = "No metrics here"
        result = OpenRouterWebParser._extract_metric_from_text(text, 'throughput')
        assert result is None

    def test_is_provider_table_positive(self):
        """Test identifying valid provider tables."""
        from bs4 import BeautifulSoup
        
        html = """
        <table>
            <tr><th>Provider</th><th>Throughput</th></tr>
            <tr><td>Test</td><td>10 TPS</td></tr>
        </table>
        """
        soup = BeautifulSoup(html, 'lxml')
        table = soup.find('table')
        
        assert OpenRouterWebParser._is_provider_table(table) is True

    def test_is_provider_table_negative(self):
        """Test identifying non-provider tables."""
        from bs4 import BeautifulSoup
        
        html = """
        <table>
            <tr><th>Random</th><th>Data</th></tr>
            <tr><td>Not</td><td>Providers</td></tr>
        </table>
        """
        soup = BeautifulSoup(html, 'lxml')
        table = soup.find('table')
        
        assert OpenRouterWebParser._is_provider_table(table) is False

    def test_map_column_indices(self):
        """Test mapping column headers to indices."""
        headers = ['provider', 'throughput', 'latency', 'uptime']
        indices = OpenRouterWebParser._map_column_indices(headers)
        
        expected = {
            'provider': 0,
            'throughput': 1,
            'latency': 2,
            'uptime': 3
        }
        assert indices == expected

    def test_map_column_indices_alternative_names(self):
        """Test mapping alternative column header names."""
        headers = ['service', 'tokens per second', 'response time', 'availability']
        indices = OpenRouterWebParser._map_column_indices(headers)
        
        expected = {
            'provider': 0,
            'throughput': 1,
            'latency': 2,
            'uptime': 3
        }
        assert indices == expected

    def test_map_column_indices_missing_columns(self):
        """Test mapping when some columns are missing."""
        headers = ['provider', 'other', 'throughput']
        indices = OpenRouterWebParser._map_column_indices(headers)
        
        expected = {
            'provider': 0,
            'throughput': 2
        }
        assert indices == expected
        assert 'latency' not in indices
        assert 'uptime' not in indices


class TestOpenRouterWebParserWithFixtures:
    """Test cases using HTML fixtures."""

    def load_fixture(self, filename: str) -> str:
        """Load HTML fixture file."""
        import os
        fixture_path = os.path.join(os.path.dirname(__file__), '..', 'fixtures', filename)
        with open(fixture_path, 'r', encoding='utf-8') as f:
            return f.read()

    def test_parse_sample_model_page(self):
        """Test parsing the sample model page fixture."""
        html_content = self.load_fixture('sample_model_page.html')
        providers = OpenRouterWebParser.parse_model_page(html_content, "qwen/qwen-2.5-coder-32b-instruct")
        
        assert len(providers) == 4
        
        # Check DeepInfra
        deepinfra = next(p for p in providers if p.provider_name == "DeepInfra")
        assert deepinfra.throughput_tps == 15.2
        assert deepinfra.latency_seconds == 0.85
        assert deepinfra.uptime_percentage == 99.5
        
        # Check Lambda
        lambda_provider = next(p for p in providers if p.provider_name == "Lambda")
        assert lambda_provider.throughput_tps == 12.8
        assert lambda_provider.latency_seconds == 1.20
        assert lambda_provider.uptime_percentage == 98.9
        
        # Check Together
        together = next(p for p in providers if p.provider_name == "Together")
        assert together.throughput_tps == 18.5
        assert together.latency_seconds == 0.65
        assert together.uptime_percentage == 99.8
        
        # Check Fireworks (with missing data)
        fireworks = next(p for p in providers if p.provider_name == "Fireworks")
        assert fireworks.throughput_tps is None  # "—" should parse as None
        assert fireworks.latency_seconds is None  # "—" should parse as None
        assert fireworks.uptime_percentage == 97.2

    def test_parse_malformed_model_page(self):
        """Test parsing malformed HTML with inconsistent structure."""
        html_content = self.load_fixture('malformed_model_page.html')
        providers = OpenRouterWebParser.parse_model_page(html_content, "test/malformed-model")
        
        # Should still extract valid providers despite malformed structure
        assert len(providers) >= 2  # At least Provider1 and CardProvider1
        
        # Check that valid providers are extracted
        provider_names = [p.provider_name for p in providers]
        assert "Provider1" in provider_names
        assert "CardProvider1" in provider_names
        
        # Check Provider1 from table
        provider1 = next(p for p in providers if p.provider_name == "Provider1")
        assert provider1.throughput_tps == 10.5
        assert provider1.latency_seconds == 1.2
        
        # Check CardProvider1 from div layout
        card_provider1 = next(p for p in providers if p.provider_name == "CardProvider1")
        assert card_provider1.throughput_tps == 15.0
        assert card_provider1.latency_seconds == 0.8  # 800ms converted to seconds
        assert card_provider1.uptime_percentage == 99.1

    def test_parse_no_provider_page(self):
        """Test parsing page with no provider data."""
        html_content = self.load_fixture('no_provider_page.html')
        providers = OpenRouterWebParser.parse_model_page(html_content, "test/no-providers-model")
        
        # Should return empty list when no providers found
        assert len(providers) == 0

    def test_parse_alternative_layout_page(self):
        """Test parsing page with card-based layout instead of tables."""
        html_content = self.load_fixture('alternative_layout_page.html')
        providers = OpenRouterWebParser.parse_model_page(html_content, "test/alternative-layout-model")
        
        assert len(providers) >= 3  # Should find at least 3 providers
        
        provider_names = [p.provider_name for p in providers]
        assert "DeepInfra" in provider_names
        assert "Lambda Labs" in provider_names
        assert "Together AI" in provider_names
        
        # Check DeepInfra
        deepinfra = next(p for p in providers if p.provider_name == "DeepInfra")
        assert deepinfra.throughput_tps == 22.3
        assert deepinfra.latency_seconds == 0.75
        assert deepinfra.uptime_percentage == 99.7
        
        # Check Lambda Labs
        lambda_labs = next(p for p in providers if p.provider_name == "Lambda Labs")
        assert lambda_labs.throughput_tps == 18.9
        assert lambda_labs.latency_seconds == 0.95  # 950ms converted
        assert lambda_labs.uptime_percentage == 98.5
        
        # Check Together AI
        together = next(p for p in providers if p.provider_name == "Together AI")
        assert together.throughput_tps == 25.1
        assert together.latency_seconds == 0.62
        assert together.uptime_percentage == 99.9

    def test_parse_edge_cases_with_fixtures(self):
        """Test various edge cases using fixture data."""
        # Test with minimal HTML
        minimal_html = "<html><body><p>No providers here</p></body></html>"
        providers = OpenRouterWebParser.parse_model_page(minimal_html, "test/minimal")
        assert len(providers) == 0
        
        # Test with only whitespace in cells
        whitespace_html = """
        <html><body>
            <table>
                <tr><th>Provider</th><th>TPS</th></tr>
                <tr><td>   </td><td>10.5</td></tr>
                <tr><td>ValidProvider</td><td>   </td></tr>
            </table>
        </body></html>
        """
        providers = OpenRouterWebParser.parse_model_page(whitespace_html, "test/whitespace")
        # Should only get ValidProvider, but with None throughput
        assert len(providers) == 1
        assert providers[0].provider_name == "ValidProvider"
        assert providers[0].throughput_tps is None

    def test_parse_unicode_and_special_characters(self):
        """Test parsing with unicode and special characters."""
        unicode_html = """
        <html><body>
            <table>
                <tr><th>Provider</th><th>Throughput</th><th>Latency</th></tr>
                <tr><td>Ñice Provider™</td><td>15.2 TPS</td><td>0.85s</td></tr>
                <tr><td>Provider-2_test</td><td>12.8 TPS</td><td>1.20s</td></tr>
                <tr><td>Provider (Beta)</td><td>10.0 TPS</td><td>1.50s</td></tr>
            </table>
        </body></html>
        """
        providers = OpenRouterWebParser.parse_model_page(unicode_html, "test/unicode")
        
        assert len(providers) == 3
        provider_names = [p.provider_name for p in providers]
        assert "Ñice Provider™" in provider_names
        assert "Provider-2_test" in provider_names
        assert "Provider (Beta)" in provider_names

    def test_parse_various_metric_formats(self):
        """Test parsing various metric formats found in real pages."""
        formats_html = """
        <html><body>
            <table>
                <tr><th>Provider</th><th>Throughput</th><th>Latency</th><th>Uptime</th></tr>
                <tr><td>Provider1</td><td>15.2 TPS</td><td>0.85s</td><td>99.5%</td></tr>
                <tr><td>Provider2</td><td>12 tokens/s</td><td>850ms</td><td>98.2</td></tr>
                <tr><td>Provider3</td><td>8.5 t/s</td><td>1.2 seconds</td><td>0.997</td></tr>
                <tr><td>Provider4</td><td>20</td><td>2.5</td><td>95.0%</td></tr>
                <tr><td>Provider5</td><td>N/A</td><td>—</td><td>-</td></tr>
            </table>
        </body></html>
        """
        providers = OpenRouterWebParser.parse_model_page(formats_html, "test/formats")
        
        assert len(providers) == 5
        
        # Check various format parsing
        p1 = next(p for p in providers if p.provider_name == "Provider1")
        assert p1.throughput_tps == 15.2
        assert p1.latency_seconds == 0.85
        assert p1.uptime_percentage == 99.5
        
        p2 = next(p for p in providers if p.provider_name == "Provider2")
        assert p2.throughput_tps == 12.0
        assert p2.latency_seconds == 0.85  # 850ms -> 0.85s
        assert p2.uptime_percentage == 98.2
        
        p3 = next(p for p in providers if p.provider_name == "Provider3")
        assert p3.throughput_tps == 8.5
        assert p3.latency_seconds == 1.2
        assert p3.uptime_percentage == 99.7  # 0.997 -> 99.7%
        
        p4 = next(p for p in providers if p.provider_name == "Provider4")
        assert p4.throughput_tps == 20.0  # Just number
        assert p4.latency_seconds == 2.5  # Just number
        assert p4.uptime_percentage == 95.0
        
        p5 = next(p for p in providers if p.provider_name == "Provider5")
        assert p5.throughput_tps is None  # N/A
        assert p5.latency_seconds is None  # —
        assert p5.uptime_percentage is None  # -


class TestOpenRouterWebParserMultipleOffers:
    """Test cases for multiple offers from the same provider."""

    def load_fixture(self, filename: str) -> str:
        """Load HTML fixture file."""
        import os
        fixture_path = os.path.join(os.path.dirname(__file__), '..', 'fixtures', filename)
        with open(fixture_path, 'r', encoding='utf-8') as f:
            return f.read()

    def test_parse_context_window_valid_formats(self):
        """Test parsing various valid context window formats."""
        test_cases = [
            ("33K", 33000),
            ("16K", 16000),
            ("1M", 1000000),
            ("2.5K", 2500),
            ("16384", 16384),
            ("32768", 32768),
        ]
        
        for text, expected in test_cases:
            result = OpenRouterWebParser.parse_context_window(text)
            assert result == expected, f"Failed to parse '{text}', expected {expected}, got {result}"

    def test_parse_context_window_invalid_formats(self):
        """Test parsing invalid context window formats returns None."""
        invalid_cases = [
            "—", "-", "N/A", "", "   ", "invalid", "abc K", "K 33"
        ]
        
        for text in invalid_cases:
            result = OpenRouterWebParser.parse_context_window(text)
            assert result is None, f"Expected None for '{text}', got {result}"

    def test_create_provider_key_unique_offers(self):
        """Test creating unique keys for different provider offers."""
        from openrouter_inspector.models import WebProviderData
        from datetime import datetime
        
        # Same provider, different quantization
        provider1 = WebProviderData(
            provider_name="Chutes",
            quantization="fp16",
            context_window=32000,
            max_completion_tokens=16000,
            throughput_tps=18.5,
            latency_seconds=0.75,
            uptime_percentage=99.2,
            last_scraped=datetime.now()
        )
        
        provider2 = WebProviderData(
            provider_name="Chutes",
            quantization="int8",
            context_window=32000,
            max_completion_tokens=8000,
            throughput_tps=22.1,
            latency_seconds=0.65,
            uptime_percentage=99.2,
            last_scraped=datetime.now()
        )
        
        key1 = OpenRouterWebParser._create_provider_key(provider1)
        key2 = OpenRouterWebParser._create_provider_key(provider2)
        
        # Keys should be different
        assert key1 != key2
        assert "Chutes" in key1
        assert "Chutes" in key2
        assert "fp16" in key1
        assert "int8" in key2

    def test_create_provider_key_minimal_data(self):
        """Test creating keys with minimal provider data."""
        from openrouter_inspector.models import WebProviderData
        from datetime import datetime
        
        provider = WebProviderData(
            provider_name="TestProvider",
            throughput_tps=15.0,
            last_scraped=datetime.now()
        )
        
        key = OpenRouterWebParser._create_provider_key(provider)
        assert key == "TestProvider"

    def test_parse_multiple_offers_from_same_provider(self):
        """Test parsing multiple offers from the same provider."""
        html_content = """
        <html>
        <body>
            <table>
                <tr>
                    <th>Provider</th>
                    <th>Quantization</th>
                    <th>Context</th>
                    <th>Max Output</th>
                    <th>Throughput</th>
                    <th>Latency</th>
                    <th>Uptime</th>
                </tr>
                <tr>
                    <td>Chutes</td>
                    <td>fp16</td>
                    <td>32K</td>
                    <td>16K</td>
                    <td>18.5 TPS</td>
                    <td>0.75s</td>
                    <td>99.2%</td>
                </tr>
                <tr>
                    <td>Chutes</td>
                    <td>int8</td>
                    <td>32K</td>
                    <td>8K</td>
                    <td>22.1 TPS</td>
                    <td>0.65s</td>
                    <td>99.2%</td>
                </tr>
                <tr>
                    <td>DeepInfra</td>
                    <td>fp8</td>
                    <td>32K</td>
                    <td>16K</td>
                    <td>15.2 TPS</td>
                    <td>0.85s</td>
                    <td>99.5%</td>
                </tr>
            </table>
        </body>
        </html>
        """
        
        providers = OpenRouterWebParser.parse_model_page(html_content, "test/model")
        
        # Should find 3 providers (2 Chutes offers + 1 DeepInfra)
        assert len(providers) == 3
        
        # Check that we have 2 Chutes offers
        chutes_providers = [p for p in providers if p.provider_name == "Chutes"]
        assert len(chutes_providers) == 2
        
        # Check that the offers are different
        chutes_fp16 = next(p for p in chutes_providers if p.quantization == "fp16")
        chutes_int8 = next(p for p in chutes_providers if p.quantization == "int8")
        
        assert chutes_fp16.max_completion_tokens == 16000
        assert chutes_fp16.throughput_tps == 18.5
        assert chutes_fp16.latency_seconds == 0.75
        
        assert chutes_int8.max_completion_tokens == 8000
        assert chutes_int8.throughput_tps == 22.1
        assert chutes_int8.latency_seconds == 0.65
        
        # Check DeepInfra
        deepinfra = next(p for p in providers if p.provider_name == "DeepInfra")
        assert deepinfra.quantization == "fp8"
        assert deepinfra.throughput_tps == 15.2

    def test_parse_multiple_offers_fixture(self):
        """Test parsing the multiple offers fixture."""
        html_content = self.load_fixture('multiple_offers_page.html')
        providers = OpenRouterWebParser.parse_model_page(html_content, "qwen/qwen3-coder")
        
        # Should find 4 providers (2 Chutes offers + DeepInfra + Lambda)
        assert len(providers) == 4
        
        # Check that we have 2 Chutes offers
        chutes_providers = [p for p in providers if p.provider_name == "Chutes"]
        assert len(chutes_providers) == 2
        
        # Verify the different Chutes offers
        chutes_fp16 = next(p for p in chutes_providers if p.quantization == "fp16")
        chutes_int8 = next(p for p in chutes_providers if p.quantization == "int8")
        
        # Check fp16 offer
        assert chutes_fp16.context_window == 32000
        assert chutes_fp16.max_completion_tokens == 16000
        assert chutes_fp16.throughput_tps == 18.5
        assert chutes_fp16.latency_seconds == 0.75
        assert chutes_fp16.uptime_percentage == 99.2
        
        # Check int8 offer
        assert chutes_int8.context_window == 32000
        assert chutes_int8.max_completion_tokens == 8000
        assert chutes_int8.throughput_tps == 22.1
        assert chutes_int8.latency_seconds == 0.65
        assert chutes_int8.uptime_percentage == 99.2
        
        # Check other providers exist
        provider_names = [p.provider_name for p in providers]
        assert "DeepInfra" in provider_names
        assert "Lambda" in provider_names