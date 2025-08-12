"""Tests for the cache module."""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from openrouter_inspector.cache import ListCommandCache
from openrouter_inspector.models import ModelInfo


class TestListCommandCache:
    """Test cases for ListCommandCache."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create a temporary directory for cache testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def cache(self, temp_cache_dir):
        """Create a cache instance with temporary directory."""
        return ListCommandCache(cache_dir=temp_cache_dir)

    @pytest.fixture
    def sample_models(self):
        """Sample models for testing."""
        created_time = datetime(2024, 1, 1, 0, 0, 0)
        return [
            ModelInfo(
                id="meta/llama-3",
                name="Meta Llama 3",
                description="Meta's Llama 3 model",
                context_length=8192,
                pricing={"prompt": 0.000001, "completion": 0.000002},
                created=created_time,
            ),
            ModelInfo(
                id="openai/gpt-4",
                name="GPT-4",
                description="OpenAI's GPT-4 model",
                context_length=8192,
                pricing={"prompt": 0.03, "completion": 0.06},
                created=created_time,
            ),
        ]

    def test_cache_key_generation(self, cache):
        """Test cache key generation from parameters."""
        params1 = {"filters": ("test",), "min_context": 1000, "tools": True}
        params2 = {"filters": ("test",), "min_context": 1000, "tools": True}
        params3 = {"filters": ("test",), "min_context": 2000, "tools": True}

        key1 = cache._generate_cache_key(**params1)
        key2 = cache._generate_cache_key(**params2)
        key3 = cache._generate_cache_key(**params3)

        # Same parameters should generate same key
        assert key1 == key2
        # Different parameters should generate different keys
        assert key1 != key3
        # Keys should be valid SHA256 hashes
        assert len(key1) == 64
        assert all(c in "0123456789abcdef" for c in key1)

    def test_store_and_retrieve_response(self, cache, sample_models):
        """Test storing and retrieving cache responses."""
        params = {"filters": ("test",), "min_context": 1000}

        # Initially no cached response
        assert cache.get_previous_response(**params) is None

        # Store response
        cache.store_response(sample_models, **params)

        # Retrieve response
        cached_data = cache.get_previous_response(**params)
        assert cached_data is not None
        assert "timestamp" in cached_data
        assert "parameters" in cached_data
        assert "models" in cached_data
        assert len(cached_data["models"]) == 2
        assert cached_data["models"][0]["id"] == "meta/llama-3"
        assert cached_data["models"][1]["id"] == "openai/gpt-4"

    def test_cache_file_creation(self, cache, sample_models, temp_cache_dir):
        """Test that cache files are created correctly."""
        params = {"filters": ("test",), "min_context": 1000}
        cache.store_response(sample_models, **params)

        # Check that cache file was created
        cache_files = list(Path(temp_cache_dir).glob("list_cache_*.json"))
        assert len(cache_files) == 1

        # Check file content
        with open(cache_files[0], encoding="utf-8") as f:
            data = json.load(f)
        assert "timestamp" in data
        assert "parameters" in data
        assert "models" in data

    def test_compare_responses_new_models(self, cache, sample_models):
        """Test comparison detecting new models."""
        created_time = datetime(2024, 1, 1, 0, 0, 0)

        # Original models
        original_models = sample_models[:1]  # Only first model

        # Current models with additional model
        current_models = sample_models + [
            ModelInfo(
                id="anthropic/claude-3",
                name="Claude 3",
                description="Anthropic's Claude 3 model",
                context_length=200000,
                pricing={"prompt": 0.015, "completion": 0.075},
                created=created_time,
            )
        ]

        # Create previous data
        previous_data = {
            "timestamp": datetime.now().isoformat(),
            "parameters": {},
            "models": [model.model_dump() for model in original_models],
        }

        new_models, pricing_changes = cache.compare_responses(
            current_models, previous_data
        )

        # Should detect 2 new models (gpt-4 and claude-3)
        assert len(new_models) == 2
        assert new_models[0].id == "openai/gpt-4"
        assert new_models[1].id == "anthropic/claude-3"
        assert len(pricing_changes) == 0

    def test_compare_responses_pricing_changes(self, cache, sample_models):
        """Test comparison detecting pricing changes."""
        # Create modified models with different pricing
        modified_models = []
        for model in sample_models:
            model_dict = model.model_dump()
            if model.id == "meta/llama-3":
                # Change pricing
                model_dict["pricing"]["prompt"] = 0.000002  # Changed from 0.000001
                model_dict["pricing"]["completion"] = 0.000003  # Changed from 0.000002
            modified_models.append(ModelInfo(**model_dict))

        # Create previous data with original pricing
        previous_data = {
            "timestamp": datetime.now().isoformat(),
            "parameters": {},
            "models": [model.model_dump() for model in sample_models],
        }

        new_models, pricing_changes = cache.compare_responses(
            modified_models, previous_data
        )

        # Should detect no new models but pricing changes
        assert len(new_models) == 0
        assert len(pricing_changes) == 2

        # Check pricing changes
        changes_dict = {
            (change[0], change[1]): (change[2], change[3]) for change in pricing_changes
        }
        assert ("meta/llama-3", "prompt") in changes_dict
        assert ("meta/llama-3", "completion") in changes_dict
        assert changes_dict[("meta/llama-3", "prompt")] == (0.000001, 0.000002)
        assert changes_dict[("meta/llama-3", "completion")] == (0.000002, 0.000003)

    def test_compare_responses_no_previous_data(self, cache, sample_models):
        """Test comparison with no previous data."""
        new_models, pricing_changes = cache.compare_responses(sample_models, {})

        # Should return empty lists when no previous data
        assert len(new_models) == 0
        assert len(pricing_changes) == 0

    def test_compare_responses_malformed_previous_data(self, cache, sample_models):
        """Test comparison with malformed previous data."""
        malformed_data = {"timestamp": "2024-01-01", "parameters": {}}
        # Missing "models" key

        new_models, pricing_changes = cache.compare_responses(
            sample_models, malformed_data
        )

        # Should return empty lists when previous data is malformed
        assert len(new_models) == 0
        assert len(pricing_changes) == 0

    def test_cache_different_parameters(self, cache, sample_models):
        """Test that different parameters create separate cache entries."""
        params1 = {"filters": ("test1",), "min_context": 1000}
        params2 = {"filters": ("test2",), "min_context": 1000}

        # Store with different parameters
        cache.store_response(sample_models[:1], **params1)
        cache.store_response(sample_models[1:], **params2)

        # Retrieve should return different data
        cached1 = cache.get_previous_response(**params1)
        cached2 = cache.get_previous_response(**params2)

        assert cached1 is not None
        assert cached2 is not None
        assert len(cached1["models"]) == 1
        assert len(cached2["models"]) == 1
        assert cached1["models"][0]["id"] != cached2["models"][0]["id"]

    def test_cache_file_corruption_handling(self, cache, temp_cache_dir):
        """Test handling of corrupted cache files."""
        # Create a corrupted cache file
        cache_key = cache._generate_cache_key(filters=("test",))
        cache_file = cache._get_cache_file_path(cache_key)

        with open(cache_file, "w", encoding="utf-8") as f:
            f.write("invalid json content")

        # Should return None for corrupted file
        result = cache.get_previous_response(filters=("test",))
        assert result is None
