"""Cache module for storing and comparing API responses."""

from __future__ import annotations

import hashlib
import json
import os
import platform
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import ModelInfo


def _default_cache_root() -> Path:
    """Return a per-user cache root directory for this application.

    Windows: %LOCALAPPDATA%/openrouter-inspector
    macOS:   ~/Library/Caches/openrouter-inspector
    Linux:   ${XDG_CACHE_HOME:-~/.cache}/openrouter-inspector
    """
    system = platform.system()
    if system == "Windows":
        base = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA")
        if base:
            return Path(base) / "openrouter-inspector"
        # Fallback to typical home-based location
        return Path.home() / "AppData" / "Local" / "openrouter-inspector"
    if system == "Darwin":
        return Path.home() / "Library" / "Caches" / "openrouter-inspector"
    # Default: POSIX (Linux, etc.)
    xdg = os.getenv("XDG_CACHE_HOME")
    if xdg:
        return Path(xdg) / "openrouter-inspector"
    return Path.home() / ".cache" / "openrouter-inspector"


class ListCommandCache:
    """Cache for list command API responses to enable comparison across runs."""

    def __init__(self, cache_dir: str | Path | None = None) -> None:
        """Initialize the cache with a specified directory.

        Args:
            cache_dir: Directory to store cache files. If None, a per-user
                cache directory appropriate for the current platform is used.
        """
        self.cache_dir = (
            Path(cache_dir) if cache_dir is not None else _default_cache_root()
        )
        # Ensure directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _generate_cache_key(self, **kwargs: Any) -> str:
        """Generate a cache key based on command parameters.

        Args:
            **kwargs: Command parameters to include in the cache key.

        Returns:
            SHA256 hash of the parameters as cache key.
        """
        # Sort parameters for consistent hashing
        sorted_params = dict(sorted(kwargs.items()))
        params_str = json.dumps(sorted_params, sort_keys=True, default=str)
        return hashlib.sha256(params_str.encode()).hexdigest()

    def _get_cache_file_path(self, cache_key: str) -> Path:
        """Get the file path for a cache key.

        Args:
            cache_key: The cache key.

        Returns:
            Path to the cache file.
        """
        return self.cache_dir / f"list_cache_{cache_key}.json"

    def store_response(self, models: list[ModelInfo], **kwargs: Any) -> None:
        """Store API response in cache.

        Args:
            models: List of models from API response.
            **kwargs: Command parameters used to generate cache key.
        """
        cache_key = self._generate_cache_key(**kwargs)
        cache_file = self._get_cache_file_path(cache_key)

        cache_data = {
            "timestamp": datetime.now().isoformat(),
            "parameters": kwargs,
            "models": [model.model_dump() for model in models],
        }

        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2, default=str)

    def get_previous_response(self, **kwargs: Any) -> dict[str, Any] | None:
        """Get previous API response from cache.

        Args:
            **kwargs: Command parameters used to generate cache key.

        Returns:
            Previous cache data or None if not found.
        """
        cache_key = self._generate_cache_key(**kwargs)
        cache_file = self._get_cache_file_path(cache_key)

        if not cache_file.exists():
            return None

        try:
            with open(cache_file, encoding="utf-8") as f:
                data: dict[str, Any] = json.load(f)
                return data
        except (json.JSONDecodeError, OSError):
            return None

    def compare_responses(
        self, current_models: list[ModelInfo], previous_data: dict[str, Any]
    ) -> tuple[list[ModelInfo], list[tuple[str, str, Any, Any]]]:
        """Compare current response with previous cached response.

        Args:
            current_models: Current list of models from API.
            previous_data: Previous cached response data.

        Returns:
            Tuple of (new_models, pricing_changes) where:
            - new_models: List of models that are new since last run
            - pricing_changes: List of (model_id, field, old_value, new_value)
        """
        if not previous_data or "models" not in previous_data:
            return [], []

        # Convert previous models to dict for easy lookup
        previous_models = {model["id"]: model for model in previous_data["models"]}
        current_models_dict = {model.id: model for model in current_models}

        # Find new models
        new_models = [
            model for model in current_models if model.id not in previous_models
        ]

        # Find pricing changes
        pricing_changes = []
        for model_id, current_model in current_models_dict.items():
            if model_id in previous_models:
                previous_model = previous_models[model_id]
                current_pricing = current_model.pricing
                previous_pricing = previous_model.get("pricing", {})

                # Compare pricing fields
                for field in ["prompt", "completion"]:
                    current_price = current_pricing.get(field)
                    previous_price = previous_pricing.get(field)

                    if (
                        current_price is not None
                        and previous_price is not None
                        and current_price != previous_price
                    ):
                        pricing_changes.append(
                            (model_id, field, previous_price, current_price)
                        )

        return new_models, pricing_changes
