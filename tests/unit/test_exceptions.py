"""Unit tests for exception hierarchy."""

from openrouter_inspector.exceptions import (
    APIError,
    AuthenticationError,
    OpenRouterError,
    RateLimitError,
    ValidationError,
)


class TestOpenRouterError:
    """Test the base OpenRouterError exception."""

    def test_basic_initialization(self):
        """Test basic exception initialization."""
        error = OpenRouterError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    def test_inheritance_chain(self):
        """Test that all custom exceptions inherit from OpenRouterError."""
        error = OpenRouterError("Test")
        assert isinstance(error, Exception)

        # Test API errors
        api_error = APIError("API error")
        assert isinstance(api_error, OpenRouterError)

        auth_error = AuthenticationError("Auth error")
        assert isinstance(auth_error, APIError)
        assert isinstance(auth_error, OpenRouterError)

        rate_error = RateLimitError("Rate limit")
        assert isinstance(rate_error, APIError)
        assert isinstance(rate_error, OpenRouterError)

        # Test validation error
        validation_error = ValidationError("Validation error")
        assert isinstance(validation_error, OpenRouterError)


class TestAPIError:
    """Test API-related exceptions."""

    def test_api_error_with_status_code(self):
        """Test APIError with status code."""
        error = APIError("Server error", status_code=500)
        assert str(error) == "Server error"
        assert error.status_code == 500

    def test_api_error_without_status_code(self):
        """Test APIError without status code."""
        error = APIError("Generic error")
        assert str(error) == "Generic error"
        assert error.status_code is None

    def test_authentication_error(self):
        """Test AuthenticationError inherits from APIError."""
        error = AuthenticationError("Invalid API key", status_code=401)
        assert str(error) == "Invalid API key"
        assert error.status_code == 401
        assert isinstance(error, APIError)

    def test_rate_limit_error(self):
        """Test RateLimitError inherits from APIError."""
        error = RateLimitError("Rate limit exceeded", status_code=429)
        assert str(error) == "Rate limit exceeded"
        assert error.status_code == 429
        assert isinstance(error, APIError)


class TestValidationError:
    """Test ValidationError exception."""

    def test_validation_error(self):
        """Test ValidationError basic functionality."""
        error = ValidationError("Invalid data format")
        assert str(error) == "Invalid data format"
        assert isinstance(error, OpenRouterError)
