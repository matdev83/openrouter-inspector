# Vulture whitelist for openrouter-inspector
# This file contains patterns that vulture should ignore to reduce false positives

# CLI command functions - these are used by Click decorators
endpoints
check_command
search_command
ping_command
benchmark_command

# Pydantic model fields and methods - used by the framework
description
created
validate_pricing
model_config
performance_tps
last_updated
validate_min_context
total_count
validate_total_count_matches_models

# Classes and methods that may be used externally or by frameworks
CacheManager
_store
health_check
filter_models_by_query
ModelsResponse
ProvidersResponse
_normalize_provider_name
