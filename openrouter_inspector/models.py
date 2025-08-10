"""Data models for OpenRouter CLI using Pydantic for validation."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator


class ModelInfo(BaseModel):
    """Information about an AI model from OpenRouter."""

    id: str = Field(..., description="Unique model identifier")
    name: str = Field(..., description="Human-readable model name")
    description: Optional[str] = Field(None, description="Model description")
    context_length: int = Field(..., gt=0, description="Maximum context window size")
    pricing: Dict[str, float] = Field(
        default_factory=dict, description="Pricing information"
    )
    created: datetime = Field(..., description="Model creation timestamp")

    @field_validator("pricing")
    @classmethod
    def validate_pricing(cls, v: Dict[str, float]) -> Dict[str, float]:
        """Ensure pricing values are non-negative."""
        for key, value in v.items():
            if value < 0:
                raise ValueError(f"Pricing value for {key} must be non-negative")
        return v


class ProviderInfo(BaseModel):
    """Information about a model provider."""

    provider_name: str = Field(..., description="Name of the provider")
    model_id: str = Field(..., description="Model identifier for this provider")
    status: Optional[str] = Field(None, description="Provider endpoint status")
    endpoint_name: Optional[str] = Field(
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
    quantization: Optional[str] = Field(None, description="Quantization method used")
    uptime_30min: float = Field(
        ..., ge=0, le=100, description="Uptime percentage for last 30 minutes"
    )
    performance_tps: Optional[float] = Field(
        None, ge=0, description="Tokens per second performance metric"
    )
    pricing: Dict[str, float] = Field(
        default_factory=dict, description="Per-provider pricing information"
    )
    max_completion_tokens: Optional[int] = Field(
        None, gt=0, description="Max completion tokens allowed by this provider"
    )
    supported_parameters: Optional[Union[Dict[str, Any], List[str]]] = Field(
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

    min_context: Optional[int] = Field(
        None, gt=0, description="Minimum context window size"
    )
    supports_tools: Optional[bool] = Field(
        None, description="Filter by tool calling support"
    )
    reasoning_only: Optional[bool] = Field(
        None, description="Filter for reasoning models only"
    )
    max_price_per_token: Optional[float] = Field(
        None, gt=0, description="Maximum price per token"
    )

    @field_validator("min_context")
    @classmethod
    def validate_min_context(cls, v: Optional[int]) -> Optional[int]:
        """Ensure minimum context is reasonable."""
        if (
            v is not None and v > 1000000
        ):  # 1M tokens seems like a reasonable upper bound
            raise ValueError("Minimum context window cannot exceed 1,000,000 tokens")
        return v


class ModelsResponse(BaseModel):
    """Response wrapper for model listings."""

    models: List[ModelInfo] = Field(default_factory=list, description="List of models")
    total_count: int = Field(..., ge=0, description="Total number of models")

    @field_validator("total_count")
    @classmethod
    def validate_total_count_matches_models(cls, v: int, info: Any) -> int:
        """Ensure total_count matches the actual number of models."""
        if info.data and "models" in info.data and len(info.data["models"]) != v:
            raise ValueError("total_count must match the number of models in the list")
        return v


class WebProviderData(BaseModel):
    """Additional provider data scraped from web interface."""

    provider_name: str = Field(..., description="Name of the provider")
    quantization: Optional[str] = Field(None, description="Quantization method used")
    context_window: Optional[int] = Field(None, description="Context window size")
    max_completion_tokens: Optional[int] = Field(
        None, description="Max completion tokens"
    )
    throughput_tps: Optional[float] = Field(
        None, ge=0, description="Throughput in tokens per second"
    )
    latency_seconds: Optional[float] = Field(
        None, ge=0, description="Latency in seconds"
    )
    uptime_percentage: Optional[float] = Field(
        None, ge=0, le=100, description="Uptime percentage from web"
    )
    last_scraped: datetime = Field(
        default_factory=datetime.now, description="When this data was scraped"
    )

    @field_validator("throughput_tps")
    @classmethod
    def validate_throughput(cls, v: Optional[float]) -> Optional[float]:
        """Ensure throughput is reasonable if provided."""
        if v is not None and v > 10000:  # 10k TPS seems like a reasonable upper bound
            raise ValueError("Throughput cannot exceed 10,000 TPS")
        return v

    @field_validator("latency_seconds")
    @classmethod
    def validate_latency(cls, v: Optional[float]) -> Optional[float]:
        """Ensure latency is reasonable if provided."""
        if v is not None and v > 300:  # 5 minutes seems like a reasonable upper bound
            raise ValueError("Latency cannot exceed 300 seconds")
        return v


class WebScrapedData(BaseModel):
    """Container for all web-scraped data for a model."""

    model_id: str = Field(..., description="Model identifier")
    providers: List[WebProviderData] = Field(
        default_factory=list, description="List of provider web data"
    )
    scraped_at: datetime = Field(
        default_factory=datetime.now, description="When this data was scraped"
    )
    source_url: str = Field(..., description="URL where data was scraped from")

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, v: str) -> str:
        """Ensure source URL is valid."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("Source URL must be a valid HTTP/HTTPS URL")
        return v


class EnhancedProviderDetails(BaseModel):
    """Provider details enhanced with web-scraped data."""

    provider: ProviderInfo = Field(..., description="Provider information from API")
    availability: bool = Field(
        default=True, description="Whether the provider is currently available"
    )
    last_updated: datetime = Field(..., description="Last update timestamp")
    web_data: Optional[WebProviderData] = Field(
        None, description="Additional web-scraped metrics"
    )

    # Note: We allow fuzzy matching between API and web provider names
    # so we don't validate exact name matches here


class ProvidersResponse(BaseModel):
    """Response wrapper for provider information."""

    model_name: str = Field(..., description="Name of the model")
    providers: List[ProviderDetails] = Field(
        default_factory=list, description="List of provider details"
    )
    last_updated: datetime = Field(
        ..., description="Last update timestamp for this information"
    )
