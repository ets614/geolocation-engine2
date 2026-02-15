"""Caching service with Redis-compatible interface and in-memory fallback."""
import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional


@dataclass
class CacheEntry:
    """A single cache entry with TTL tracking."""
    value: Any
    created_at: float
    ttl_seconds: float
    access_count: int = 0

    @property
    def is_expired(self) -> bool:
        """Check if entry has expired based on TTL."""
        if self.ttl_seconds <= 0:
            return False  # No expiry
        return (time.monotonic() - self.created_at) >= self.ttl_seconds


class CacheService:
    """In-memory cache with TTL, eviction, and cache-warming support.

    Designed as a port interface that can be backed by Redis or in-memory store.
    The in-memory implementation is provided for development and testing;
    production deployments should use the Redis adapter.
    """

    def __init__(
        self,
        default_ttl_seconds: float = 300.0,
        max_entries: int = 1000,
    ):
        """Initialize cache service.

        Args:
            default_ttl_seconds: Default TTL for entries (5 minutes).
            max_entries: Maximum number of entries before eviction.
        """
        if default_ttl_seconds < 0:
            raise ValueError("TTL must be non-negative")
        if max_entries <= 0:
            raise ValueError("max_entries must be positive")

        self.default_ttl_seconds = default_ttl_seconds
        self.max_entries = max_entries
        self._store: Dict[str, CacheEntry] = {}
        self._hits = 0
        self._misses = 0

    @staticmethod
    def generate_cache_key(*args: Any) -> str:
        """Generate a deterministic cache key from arguments.

        Args:
            *args: Values to include in the key.

        Returns:
            SHA-256 hex digest as cache key.
        """
        key_data = json.dumps(args, sort_keys=True, default=str)
        return hashlib.sha256(key_data.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """Retrieve a value from cache.

        Args:
            key: Cache key.

        Returns:
            Cached value or None if not found / expired.
        """
        entry = self._store.get(key)
        if entry is None:
            self._misses += 1
            return None

        if entry.is_expired:
            del self._store[key]
            self._misses += 1
            return None

        entry.access_count += 1
        self._hits += 1
        return entry.value

    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[float] = None,
    ) -> None:
        """Store a value in cache.

        Args:
            key: Cache key.
            value: Value to cache.
            ttl_seconds: Optional TTL override.
        """
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds

        # Evict expired entries if at capacity
        if len(self._store) >= self.max_entries:
            self._evict()

        self._store[key] = CacheEntry(
            value=value,
            created_at=time.monotonic(),
            ttl_seconds=ttl,
        )

    def delete(self, key: str) -> bool:
        """Remove a key from cache.

        Args:
            key: Cache key to remove.

        Returns:
            True if key existed and was removed.
        """
        if key in self._store:
            del self._store[key]
            return True
        return False

    def invalidate_pattern(self, prefix: str) -> int:
        """Invalidate all keys matching a prefix.

        Args:
            prefix: Key prefix to match.

        Returns:
            Number of entries invalidated.
        """
        keys_to_remove = [k for k in self._store if k.startswith(prefix)]
        for key in keys_to_remove:
            del self._store[key]
        return len(keys_to_remove)

    def clear(self) -> None:
        """Clear all cache entries."""
        self._store.clear()
        self._hits = 0
        self._misses = 0

    def warm(self, key: str, loader: Callable[[], Any], ttl_seconds: Optional[float] = None) -> Any:
        """Warm a cache entry using a loader function.

        If the key exists and is valid, returns cached value.
        Otherwise calls the loader, caches the result, and returns it.

        Args:
            key: Cache key.
            loader: Function that produces the value.
            ttl_seconds: Optional TTL override.

        Returns:
            The cached or freshly loaded value.
        """
        existing = self.get(key)
        if existing is not None:
            return existing

        value = loader()
        self.set(key, value, ttl_seconds)
        return value

    def stats(self) -> Dict[str, Any]:
        """Return cache statistics.

        Returns:
            Dict with hits, misses, hit_rate, size, max_entries.
        """
        total = self._hits + self._misses
        hit_rate = (self._hits / total) if total > 0 else 0.0
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 4),
            "size": len(self._store),
            "max_entries": self.max_entries,
        }

    def _evict(self) -> None:
        """Evict expired entries, then LRU if still at capacity."""
        # First pass: remove expired
        expired_keys = [k for k, v in self._store.items() if v.is_expired]
        for key in expired_keys:
            del self._store[key]

        # If still at capacity, evict least recently accessed
        if len(self._store) >= self.max_entries:
            # Sort by access_count (LFU-ish), then by created_at (oldest first)
            sorted_keys = sorted(
                self._store.keys(),
                key=lambda k: (
                    self._store[k].access_count,
                    self._store[k].created_at,
                ),
            )
            # Evict bottom 10%
            evict_count = max(1, len(sorted_keys) // 10)
            for key in sorted_keys[:evict_count]:
                del self._store[key]
