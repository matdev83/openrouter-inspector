"""Unit tests for utility functions."""

from unittest.mock import MagicMock, patch

from openrouter_inspector.utils import (
    check_parameter_support,
    configure_logging,
    create_command_dependencies,
    normalize_string,
    parse_context_threshold,
    parse_quantization_bits,
)


class TestConfigureLogging:
    """Test cases for configure_logging function."""

    def test_configure_logging_none(self):
        """Test configure_logging with None level."""
        # Should not raise an exception
        configure_logging(None)

    def test_configure_logging_none_with_default(self):
        """Test configure_logging with None level and default_to_warning=True."""
        with patch("logging.getLogger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            mock_logger.handlers = [MagicMock()]

            configure_logging(None, default_to_warning=True)

            mock_logger.setLevel.assert_called_once()

    def test_configure_logging_valid_levels(self):
        """Test configure_logging with valid levels."""
        # Should not raise an exception
        configure_logging("DEBUG")
        configure_logging("INFO")
        configure_logging("WARNING")
        configure_logging("ERROR")
        configure_logging("CRITICAL")

    def test_configure_logging_invalid_level(self):
        """Test configure_logging with invalid level."""
        # Should default to WARNING
        with patch("logging.getLogger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            mock_logger.handlers = [MagicMock()]

            configure_logging("INVALID")

            mock_logger.setLevel.assert_called_once()

    def test_configure_logging_case_insensitive(self):
        """Test configure_logging is case insensitive."""
        # Should not raise an exception
        configure_logging("debug")
        configure_logging("Debug")
        configure_logging("DEBUG")


class TestCreateCommandDependencies:
    """Test cases for create_command_dependencies function."""

    @patch(
        "openrouter_inspector.utils.dependency_injection.client_mod.OpenRouterClient"
    )
    @patch("openrouter_inspector.utils.dependency_injection.services_mod.ModelService")
    @patch("openrouter_inspector.utils.dependency_injection.TableFormatter")
    @patch("openrouter_inspector.utils.dependency_injection.JsonFormatter")
    def test_create_command_dependencies(
        self, mock_json_formatter, mock_table_formatter, mock_model_service, mock_client
    ):
        """Test create_command_dependencies function."""
        api_key = "test-api-key"

        client, model_service, table_formatter, json_formatter = (
            create_command_dependencies(api_key)
        )

        mock_client.assert_called_once_with(api_key)
        mock_model_service.assert_called_once_with(mock_client.return_value)
        mock_table_formatter.assert_called_once()
        mock_json_formatter.assert_called_once()


class TestNormalizeString:
    """Test cases for normalize_string function."""

    def test_normalize_string_basic(self):
        """Test basic string normalization."""
        assert normalize_string("Hello World") == "hello world"
        assert normalize_string("  UPPERCASE  ") == "uppercase"
        assert normalize_string("MixedCase") == "mixedcase"

    def test_normalize_string_none(self):
        """Test normalize_string with None input."""
        assert normalize_string(None) == ""

    def test_normalize_string_empty(self):
        """Test normalize_string with empty string."""
        assert normalize_string("") == ""
        assert normalize_string("   ") == ""

    def test_normalize_string_special_chars(self):
        """Test normalize_string with special characters."""
        assert normalize_string("Test-String_123") == "test-string_123"
        assert normalize_string("  Test@String!  ") == "test@string!"


class TestParseQuantizationBits:
    """Test cases for parse_quantization_bits function."""

    def test_parse_quantization_bits_none(self):
        """Test parse_quantization_bits with None input."""
        assert parse_quantization_bits(None) == float("inf")

    def test_parse_quantization_bits_empty(self):
        """Test parse_quantization_bits with empty string."""
        assert parse_quantization_bits("") == float("inf")

    def test_parse_quantization_bits_bf16(self):
        """Test parse_quantization_bits with bf16."""
        assert parse_quantization_bits("bf16") == 16
        assert parse_quantization_bits("BF16") == 16

    def test_parse_quantization_bits_numeric(self):
        """Test parse_quantization_bits with numeric values."""
        assert parse_quantization_bits("8bit") == 8
        assert parse_quantization_bits("4bit") == 4
        assert parse_quantization_bits("16") == 16

    def test_parse_quantization_bits_no_digits(self):
        """Test parse_quantization_bits with no digits."""
        assert parse_quantization_bits("fp") == 0.0
        assert parse_quantization_bits("unknown") == 0.0


class TestParseContextThreshold:
    """Test cases for parse_context_threshold function."""

    def test_parse_context_threshold_none(self):
        """Test parse_context_threshold with None input."""
        assert parse_context_threshold(None) == 0

    def test_parse_context_threshold_k_suffix(self):
        """Test parse_context_threshold with K suffix."""
        assert parse_context_threshold("128K") == 128000
        assert parse_context_threshold("32k") == 32000
        assert parse_context_threshold("1.5K") == 1500

    def test_parse_context_threshold_numeric(self):
        """Test parse_context_threshold with numeric values."""
        assert parse_context_threshold("131072") == 131072
        assert parse_context_threshold("8192") == 8192

    def test_parse_context_threshold_invalid(self):
        """Test parse_context_threshold with invalid input."""
        assert parse_context_threshold("invalid") == 0
        assert parse_context_threshold("") == 0


class TestCheckParameterSupport:
    """Test cases for check_parameter_support function."""

    def test_check_parameter_support_list_exact_match(self):
        """Test check_parameter_support with list and exact match."""
        supported_params = ["reasoning", "image", "tools"]
        assert check_parameter_support(supported_params, "reasoning") is True
        assert check_parameter_support(supported_params, "image") is True
        assert check_parameter_support(supported_params, "tools") is True

    def test_check_parameter_support_list_prefix_match(self):
        """Test check_parameter_support with list and prefix match."""
        supported_params = ["reasoning_advanced", "image_generation"]
        assert check_parameter_support(supported_params, "reasoning") is True
        assert check_parameter_support(supported_params, "image") is True

    def test_check_parameter_support_list_no_match(self):
        """Test check_parameter_support with list and no match."""
        supported_params = ["tools", "audio"]
        assert check_parameter_support(supported_params, "reasoning") is False
        assert check_parameter_support(supported_params, "image") is False

    def test_check_parameter_support_dict_true(self):
        """Test check_parameter_support with dict and True value."""
        supported_params = {"reasoning": True, "image": False, "tools": True}
        assert check_parameter_support(supported_params, "reasoning") is True
        assert check_parameter_support(supported_params, "tools") is True

    def test_check_parameter_support_dict_false(self):
        """Test check_parameter_support with dict and False value."""
        supported_params = {"reasoning": True, "image": False, "tools": True}
        assert check_parameter_support(supported_params, "image") is False

    def test_check_parameter_support_dict_missing(self):
        """Test check_parameter_support with dict and missing key."""
        supported_params = {"reasoning": True}
        assert check_parameter_support(supported_params, "image") is False

    def test_check_parameter_support_other_type(self):
        """Test check_parameter_support with other types."""
        assert check_parameter_support("not_a_list_or_dict", "reasoning") is False
        assert check_parameter_support(123, "reasoning") is False
        assert check_parameter_support(None, "reasoning") is False
