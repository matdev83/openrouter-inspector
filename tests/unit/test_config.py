"""Unit tests for configuration management."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from openrouter_inspector.config import Config

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

try:
    import tomli_w
except ImportError:
    tomli_w = None


class TestConfig:
    """Test cases for Config class."""
    
    def test_config_defaults(self):
        """Test Config with default values."""
        config = Config(api_key="test-key")
        
        assert config.api_key == "test-key"
        assert config.base_url == "https://openrouter.ai/api/v1"
        assert config.cache_enabled is True
        assert config.cache_ttl == 300
        assert config.timeout == 30
    
    def test_config_custom_values(self):
        """Test Config with custom values."""
        config = Config(
            api_key="custom-key",
            base_url="https://custom.api.com",
            cache_enabled=False,
            cache_ttl=600,
            timeout=60
        )
        
        assert config.api_key == "custom-key"
        assert config.base_url == "https://custom.api.com"
        assert config.cache_enabled is False
        assert config.cache_ttl == 600
        assert config.timeout == 60


class TestConfigFromEnv:
    """Test cases for Config.from_env() method."""
    
    def test_from_env_success(self):
        """Test loading configuration from environment variables."""
        env_vars = {
            'OPENROUTER_API_KEY': 'env-api-key',
            'OPENROUTER_BASE_URL': 'https://env.api.com',
            'OPENROUTER_CACHE_ENABLED': 'false',
            'OPENROUTER_CACHE_TTL': '600',
            'OPENROUTER_TIMEOUT': '60'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = Config.from_env()
        
        assert config.api_key == 'env-api-key'
        assert config.base_url == 'https://env.api.com'
        assert config.cache_enabled is False
        assert config.cache_ttl == 600
        assert config.timeout == 60
    
    def test_from_env_minimal(self):
        """Test loading configuration with only required environment variable."""
        env_vars = {'OPENROUTER_API_KEY': 'minimal-key'}
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = Config.from_env()
        
        assert config.api_key == 'minimal-key'
        assert config.base_url == "https://openrouter.ai/api/v1"  # default
        assert config.cache_enabled is True  # default
        assert config.cache_ttl == 300  # default
        assert config.timeout == 30  # default
    
    def test_from_env_missing_api_key(self):
        """Test that missing API key raises ValueError."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="OPENROUTER_API_KEY environment variable is required"):
                Config.from_env()
    
    def test_from_env_cache_enabled_variations(self):
        """Test different values for cache_enabled environment variable."""
        test_cases = [
            ('true', True),
            ('True', True),
            ('TRUE', True),
            ('false', False),
            ('False', False),
            ('FALSE', False),
            ('yes', False),  # Only 'true' should be True
            ('1', False),    # Only 'true' should be True
        ]
        
        for env_value, expected in test_cases:
            env_vars = {
                'OPENROUTER_API_KEY': 'test-key',
                'OPENROUTER_CACHE_ENABLED': env_value
            }
            
            with patch.dict(os.environ, env_vars, clear=True):
                config = Config.from_env()
            
            assert config.cache_enabled == expected, f"Failed for env_value: {env_value}"


class TestConfigFromFile:
    """Test cases for Config.from_file() method."""
    
    def test_from_json_file_success(self):
        """Test loading configuration from JSON file."""
        config_data = {
            'api_key': 'json-api-key',
            'base_url': 'https://json.api.com',
            'cache_enabled': False,
            'cache_ttl': 600,
            'timeout': 60
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = Path(f.name)
        
        try:
            config = Config.from_file(temp_path)
            
            assert config.api_key == 'json-api-key'
            assert config.base_url == 'https://json.api.com'
            assert config.cache_enabled is False
            assert config.cache_ttl == 600
            assert config.timeout == 60
        finally:
            temp_path.unlink()
    
    def test_from_toml_file_success(self):
        """Test loading configuration from TOML file."""
        if tomllib is None:
            pytest.skip("TOML support not available")
            
        config_data = {
            'api_key': 'toml-api-key',
            'base_url': 'https://toml.api.com',
            'cache_enabled': True,
            'cache_ttl': 900,
            'timeout': 45
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            if tomli_w is None:
                pytest.skip("TOML writing support not available")
            # Write TOML manually for testing
            f.write('api_key = "toml-api-key"\n')
            f.write('base_url = "https://toml.api.com"\n')
            f.write('cache_enabled = true\n')
            f.write('cache_ttl = 900\n')
            f.write('timeout = 45\n')
            temp_path = Path(f.name)
        
        try:
            config = Config.from_file(temp_path)
            
            assert config.api_key == 'toml-api-key'
            assert config.base_url == 'https://toml.api.com'
            assert config.cache_enabled is True
            assert config.cache_ttl == 900
            assert config.timeout == 45
        finally:
            temp_path.unlink()
    
    def test_from_file_minimal_json(self):
        """Test loading configuration from JSON file with only required fields."""
        config_data = {'api_key': 'minimal-json-key'}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = Path(f.name)
        
        try:
            config = Config.from_file(temp_path)
            
            assert config.api_key == 'minimal-json-key'
            assert config.base_url == "https://openrouter.ai/api/v1"  # default
            assert config.cache_enabled is True  # default
            assert config.cache_ttl == 300  # default
            assert config.timeout == 30  # default
        finally:
            temp_path.unlink()
    
    def test_from_file_not_found(self):
        """Test that missing file raises FileNotFoundError."""
        non_existent_path = Path('/non/existent/config.json')
        
        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            Config.from_file(non_existent_path)
    
    def test_from_file_missing_api_key(self):
        """Test that missing API key in file raises ValueError."""
        config_data = {'base_url': 'https://test.com'}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(ValueError, match="api_key is required in configuration file"):
                Config.from_file(temp_path)
        finally:
            temp_path.unlink()
    
    def test_from_file_unsupported_format(self):
        """Test that unsupported file format raises ValueError."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("api_key: test-key\n")
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(ValueError, match="Unsupported configuration file format"):
                Config.from_file(temp_path)
        finally:
            temp_path.unlink()
    
    def test_from_file_malformed_json(self):
        """Test that malformed JSON raises JSONDecodeError."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"api_key": "test-key",}')  # Invalid JSON (trailing comma)
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(json.JSONDecodeError):
                Config.from_file(temp_path)
        finally:
            temp_path.unlink()
    
    def test_from_file_malformed_toml(self):
        """Test that malformed TOML raises appropriate error."""
        if tomllib is None:
            pytest.skip("TOML support not available")
            
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write('[invalid toml\napi_key = "test"')  # Invalid TOML
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(Exception):  # Could be various TOML parsing errors
                Config.from_file(temp_path)
        finally:
            temp_path.unlink()


class TestConfigFromSources:
    """Test cases for Config.from_sources() method."""
    
    def test_from_sources_env_only(self):
        """Test loading configuration from environment variables only."""
        env_vars = {
            'OPENROUTER_API_KEY': 'env-only-key',
            'OPENROUTER_BASE_URL': 'https://env-only.com'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = Config.from_sources()
        
        assert config.api_key == 'env-only-key'
        assert config.base_url == 'https://env-only.com'
    
    def test_from_sources_file_only(self):
        """Test loading configuration from file only."""
        config_data = {
            'api_key': 'file-only-key',
            'base_url': 'https://file-only.com'
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = Path(f.name)
        
        try:
            with patch.dict(os.environ, {}, clear=True):
                config = Config.from_sources(config_file=temp_path)
            
            assert config.api_key == 'file-only-key'
            assert config.base_url == 'https://file-only.com'
        finally:
            temp_path.unlink()
    
    def test_from_sources_file_overrides_env(self):
        """Test that file configuration overrides environment variables."""
        env_vars = {
            'OPENROUTER_API_KEY': 'env-key',
            'OPENROUTER_BASE_URL': 'https://env.com',
            'OPENROUTER_TIMEOUT': '30'
        }
        
        config_data = {
            'api_key': 'file-key',
            'base_url': 'https://file.com',
            'cache_enabled': False
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = Path(f.name)
        
        try:
            with patch.dict(os.environ, env_vars, clear=True):
                config = Config.from_sources(config_file=temp_path)
            
            # File should override env
            assert config.api_key == 'file-key'
            assert config.base_url == 'https://file.com'
            assert config.cache_enabled is False
            # Env value should be preserved if not in file
            assert config.timeout == 30
        finally:
            temp_path.unlink()
    
    def test_from_sources_nonexistent_file_fallback_to_env(self):
        """Test that nonexistent file falls back to environment variables."""
        env_vars = {'OPENROUTER_API_KEY': 'fallback-key'}
        non_existent_path = Path('/non/existent/config.json')
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = Config.from_sources(config_file=non_existent_path)
        
        assert config.api_key == 'fallback-key'
    
    def test_from_sources_no_api_key_anywhere(self):
        """Test that missing API key in all sources raises ValueError."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="API key is required"):
                Config.from_sources()


class TestConfigUtilityMethods:
    """Test cases for Config utility methods."""
    
    def test_to_dict(self):
        """Test converting configuration to dictionary."""
        config = Config(
            api_key="test-key",
            base_url="https://test.com",
            cache_enabled=False,
            cache_ttl=600,
            timeout=60
        )
        
        expected = {
            'api_key': 'test-key',
            'base_url': 'https://test.com',
            'cache_enabled': False,
            'cache_ttl': 600,
            'timeout': 60
        }
        
        assert config.to_dict() == expected
    
    def test_to_file_json_with_api_key(self):
        """Test saving configuration to JSON file with API key."""
        config = Config(
            api_key="save-test-key",
            base_url="https://save-test.com",
            cache_enabled=False
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            config.to_file(temp_path, exclude_api_key=False)
            
            with open(temp_path, 'r') as f:
                saved_data = json.load(f)
            
            assert saved_data['api_key'] == 'save-test-key'
            assert saved_data['base_url'] == 'https://save-test.com'
            assert saved_data['cache_enabled'] is False
        finally:
            temp_path.unlink()
    
    def test_to_file_json_exclude_api_key(self):
        """Test saving configuration to JSON file excluding API key."""
        config = Config(
            api_key="secret-key",
            base_url="https://save-test.com"
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            config.to_file(temp_path, exclude_api_key=True)
            
            with open(temp_path, 'r') as f:
                saved_data = json.load(f)
            
            assert 'api_key' not in saved_data
            assert saved_data['base_url'] == 'https://save-test.com'
        finally:
            temp_path.unlink()
    
    def test_to_file_toml(self):
        """Test saving configuration to TOML file."""
        if tomli_w is None:
            pytest.skip("TOML writing support not available")
            
        config = Config(
            api_key="toml-save-key",
            base_url="https://toml-save.com",
            cache_ttl=900
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            config.to_file(temp_path, exclude_api_key=False)
            
            if tomllib is None:
                pytest.skip("TOML support not available")
            with open(temp_path, 'rb') as f:
                saved_data = tomllib.load(f)
            
            assert saved_data['api_key'] == 'toml-save-key'
            assert saved_data['base_url'] == 'https://toml-save.com'
            assert saved_data['cache_ttl'] == 900
        finally:
            temp_path.unlink()
    
    def test_to_file_creates_parent_directory(self):
        """Test that to_file creates parent directories if they don't exist."""
        config = Config(api_key="test-key")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            nested_path = Path(temp_dir) / 'nested' / 'config.json'
            
            config.to_file(nested_path)
            
            assert nested_path.exists()
            assert nested_path.parent.exists()
    
    def test_to_file_unsupported_format(self):
        """Test that unsupported file format raises ValueError."""
        config = Config(api_key="test-key")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(ValueError, match="Unsupported configuration file format"):
                config.to_file(temp_path)
        finally:
            temp_path.unlink()