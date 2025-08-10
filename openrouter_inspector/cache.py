"""Simple TTL-based in-memory cache manager."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple


class CacheManager:
    """A minimal TTL cache for API responses.

    Not thread-safe; intended for simple CLI usage.
    """

    def __init__(self, ttl: int = 300):
        self._store: Dict[str, Tuple[Any, datetime]] = {}
        self._ttl = int(ttl)

    def get(self, key: str) -> Optional[Any]:
        """Get cached value if it has not expired."""
        entry = self._store.get(key)
        if not entry:
            return None
        value, ts = entry
        if datetime.now() - ts <= timedelta(seconds=self._ttl):
            return value
        # Expired; delete and return None
        self._store.pop(key, None)
        return None

    def set(self, key: str, value: Any) -> None:
        """Cache a value with current timestamp."""
        self._store[key] = (value, datetime.now())
