"""Configuration management for OpenRouter CLI."""

import os
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any

try:
    import tomllib  # type: ignore[import-not-found]  # Python 3.11+
except ImportError:  # pragma: no cover - fallback for <3.11
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

try:
    import tomli_w  # type: ignore[import-not-found]  # for writing TOML files
except ImportError:  # pragma: no cover
    tomli_w = None


@dataclass
class Config:
    """Configuration class for OpenRouter CLI."""
    
    api_key: str
    base_url: str = "https://openrouter.ai/api/v1"
    cache_enabled: bool = True
    cache_ttl: int = 300  # 5 minutes
    timeout: int = 30
    
    @classmethod
    def from_env(cls) -> 'Config':
        """Load configuration from environment variables.
        
        Returns:
            Config: Configuration instance loaded from environment variables.
            
        Raises:
            ValueError: If required API key is not found in environment.
        """
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required")
        
        return cls(
            api_key=api_key,
            base_url=os.getenv('OPENROUTER_BASE_URL', cls.base_url),
            cache_enabled=os.getenv('OPENROUTER_CACHE_ENABLED', 'true').lower() == 'true',
            cache_ttl=int(os.getenv('OPENROUTER_CACHE_TTL', str(cls.cache_ttl))),
            timeout=int(os.getenv('OPENROUTER_TIMEOUT', str(cls.timeout)))
        )
    
    @classmethod
    def from_file(cls, path: Path) -> 'Config':
        """Load configuration from file.
        
        Supports JSON and TOML formats based on file extension.
        
        Args:
            path: Path to configuration file.
            
        Returns:
            Config: Configuration instance loaded from file.
            
        Raises:
            FileNotFoundError: If configuration file doesn't exist.
            ValueError: If required API key is not found in file or file format is unsupported.
            json.JSONDecodeError: If JSON file is malformed.
            toml.TomlDecodeError: If TOML file is malformed.
        """
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")
        
        # Determine file format from extension
        if path.suffix.lower() == '.json':
            with open(path, 'r') as f:
                data = json.load(f)
        elif path.suffix.lower() in ['.toml', '.tml']:
            if tomllib is None:
                raise ValueError("TOML support not available. Install 'tomli' package for Python < 3.11")
            with open(path, 'rb') as f:
                data = tomllib.load(f)
        else:
            raise ValueError(f"Unsupported configuration file format: {path.suffix}")
        
        # Validate required fields
        if 'api_key' not in data:
            raise ValueError("api_key is required in configuration file")
        
        return cls(
            api_key=data['api_key'],
            base_url=data.get('base_url', cls.base_url),
            cache_enabled=data.get('cache_enabled', cls.cache_enabled),
            cache_ttl=data.get('cache_ttl', cls.cache_ttl),
            timeout=data.get('timeout', cls.timeout)
        )
    
    @classmethod
    def from_sources(cls, config_file: Optional[Path] = None) -> 'Config':
        """Load configuration from multiple sources with precedence.
        
        Precedence order (highest to lowest):
        1. Configuration file (if provided)
        2. Environment variables
        3. Default values
        
        Args:
            config_file: Optional path to configuration file.
            
        Returns:
            Config: Configuration instance loaded from available sources.
            
        Raises:
            ValueError: If no valid configuration source provides required API key.
        """
        # Start with defaults
        config_data = {
            'base_url': cls.base_url,
            'cache_enabled': cls.cache_enabled,
            'cache_ttl': cls.cache_ttl,
            'timeout': cls.timeout
        }
        
        # Override with environment variables
        env_api_key = os.getenv('OPENROUTER_API_KEY')
        if env_api_key:
            config_data['api_key'] = env_api_key
        
        if os.getenv('OPENROUTER_BASE_URL'):
            config_data['base_url'] = os.getenv('OPENROUTER_BASE_URL')
        
        if os.getenv('OPENROUTER_CACHE_ENABLED') is not None:
            val = os.getenv('OPENROUTER_CACHE_ENABLED') or ""
            config_data['cache_enabled'] = val.lower() == 'true'
        
        if os.getenv('OPENROUTER_CACHE_TTL') is not None:
            ttl_val = os.getenv('OPENROUTER_CACHE_TTL') or "0"
            config_data['cache_ttl'] = int(ttl_val)
        
        if os.getenv('OPENROUTER_TIMEOUT') is not None:
            to_val = os.getenv('OPENROUTER_TIMEOUT') or "0"
            config_data['timeout'] = int(to_val)
        
        # Override with config file if provided
        if config_file and config_file.exists():
            try:
                file_config = cls.from_file(config_file)
                config_data.update({
                    'api_key': file_config.api_key,
                    'base_url': file_config.base_url,
                    'cache_enabled': file_config.cache_enabled,
                    'cache_ttl': file_config.cache_ttl,
                    'timeout': file_config.timeout
                })
            except Exception:
                # If file config fails, continue with env/defaults
                pass
        
        # Validate that we have an API key
        if 'api_key' not in config_data:
            raise ValueError(
                "API key is required. Set OPENROUTER_API_KEY environment variable "
                "or provide it in a configuration file."
            )
        
        return cls(**config_data)  # type: ignore[arg-type]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary.
        
        Returns:
            Dict[str, Any]: Configuration as dictionary.
        """
        return {
            'api_key': self.api_key,
            'base_url': self.base_url,
            'cache_enabled': self.cache_enabled,
            'cache_ttl': self.cache_ttl,
            'timeout': self.timeout
        }
    
    def to_file(self, path: Path, exclude_api_key: bool = True) -> None:
        """Save configuration to file.
        
        Args:
            path: Path where to save configuration file.
            exclude_api_key: Whether to exclude API key from saved file for security.
            
        Raises:
            ValueError: If file format is unsupported.
        """
        data = self.to_dict()
        
        if exclude_api_key:
            data.pop('api_key', None)
        
        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save based on file extension
        if path.suffix.lower() == '.json':
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
        elif path.suffix.lower() in ['.toml', '.tml']:
            if tomli_w is None:
                raise ValueError("TOML writing support not available. Install 'tomli-w' package")
            with open(path, 'wb') as f:
                tomli_w.dump(data, f)
        else:
            raise ValueError(f"Unsupported configuration file format: {path.suffix}")