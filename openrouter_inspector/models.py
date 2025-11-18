"""Data models for OpenRouter CLI using Pydantic for validation."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ModelInfo(BaseModel):
    """Information about an AI model from OpenRouter."""

    id: str = Field(..., description="Unique model identifier")
    name: str = Field(..., description="Human-readable model name")
    description: str | None = Field(None, description="Model description")
    context_length: int = Field(..., gt=0, description="Maximum context window size")
    pricing: dict[str, float] = Field(
        default_factory=dict, description="Pricing information"
    )
    created: datetime = Field(..., description="Model creation timestamp")

    @field_validator("pricing")
    @classmethod
    def validate_pricing(cls, v: dict[str, float]) -> dict[str, float]:
        """Ensure pricing values are non-negative."""
        # Silence unused variable warning - cls is required for classmethod
        _ = cls
        for key, value in v.items():
            if value < 0:
                raise ValueError(f"Pricing value for {key} must be non-negative")
        return v


class ProviderInfo(BaseModel):
    """Information about a model provider."""

    model_config = ConfigDict(protected_namespaces=())

    provider_name: str = Field(..., description="Name of the provider")
    model_id: str = Field(..., description="Model identifier for this provider")
    status: str | None = Field(None, description="Provider endpoint status")
    endpoint_name: str | None = Field(
        None, description="Provider's endpoint/model display name for this offer"
    )
    context_window: int = Field(
        ..., gt=0, description="Context window size for this provider"
    )
    supports_tools: bool = Field(
        default=False, description="Whether the provider supports tool calling"
    )
    is_reasoning_model: bool = Field(
        default=False, description="Whether this is a reasoning model"
    )
    supports_image_input: bool = Field(
        default=False, description="Whether the provider accepts image input"
    )
    quantization: str | None = Field(None, description="Quantization method used")
    uptime_30min: float = Field(
        ..., ge=0, le=100, description="Uptime percentage for last 30 minutes"
    )
    performance_tps: float | None = Field(
        None, ge=0, description="Tokens per second performance metric"
    )
    pricing: dict[str, float] = Field(
        default_factory=dict, description="Per-provider pricing information"
    )
    max_completion_tokens: int | None = Field(
        None, gt=0, description="Max completion tokens allowed by this provider"
    )
    supported_parameters: dict[str, Any] | list[str] | None = Field(
        None, description="Provider-specific supported parameters/capabilities"
    )


class ProviderDetails(BaseModel):
    """Detailed information about a provider for a specific model."""

    provider: ProviderInfo = Field(..., description="Provider information")
    availability: bool = Field(
        default=True, description="Whether the provider is currently available"
    )
    last_updated: datetime = Field(..., description="Last update timestamp")


class SearchFilters(BaseModel):
    """Filters for searching models."""

    min_context: int | None = Field(
        None, gt=0, description="Minimum context window size"
    )
    supports_tools: bool | None = Field(
        None, description="Filter by tool calling support"
    )
    reasoning_only: bool | None = Field(
        None,
        description=(
            "Filter by reasoning support (True requires reasoning, False excludes)"
        ),
    )
    supports_image_input: bool | None = Field(
        None,
        description="Filter by image input support (True requires it, False excludes it)",
    )
    max_price_per_token: float | None = Field(
        None, gt=0, description="Maximum price per token"
    )

    @field_validator("min_context")
    @classmethod
    def validate_min_context(cls, v: int | None) -> int | None:
        """Ensure minimum context is reasonable."""
        if (
            v is not None and v > 1000000
        ):  # 1M tokens seems like a reasonable upper bound
            raise ValueError("Minimum context window cannot exceed 1,000,000 tokens")
        return v


class ModelsResponse(BaseModel):
    """Response wrapper for model listings."""

    models: list[ModelInfo] = Field(default_factory=list, description="List of models")
    total_count: int = Field(..., ge=0, description="Total number of models")

    @field_validator("total_count")
    @classmethod
    def validate_total_count_matches_models(cls, v: int, info: Any) -> int:
        """Ensure total_count matches the actual number of models."""
        # Silence unused variable warning - cls is required for classmethod
        _ = cls
        if info.data and "models" in info.data and len(info.data["models"]) != v:
            raise ValueError("total_count must match the number of models in the list")
        return v


class ProvidersResponse(BaseModel):
    """Response wrapper for provider information."""

    model_config = ConfigDict(protected_namespaces=())

    model_name: str = Field(..., description="Name of the model")
    providers: list[ProviderDetails] = Field(
        default_factory=list, description="List of provider details"
    )
    last_updated: datetime = Field(
        ..., description="Last update timestamp for this information"
    )
