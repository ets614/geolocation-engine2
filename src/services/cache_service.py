"""Redis-based caching service with cache-aside pattern.

Provides multi-tier caching for geolocation results, CoT templates, health checks,
and authentication tokens with configurable TTL and LRU eviction.

Cache Types:
- Geolocation: 24h TTL, 1000 max items (LRU)
- CoT Templates: 7d TTL, 500 items
- Health Status: 30s TTL, 10 items
- Auth Tokens: JWT exp TTL
"""

import json
import logging
import hashlib
from typing import Optional, Any, Dict, List
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: str
    value: Any
    ttl_seconds: int
    created_at: datetime
    accessed_at: datetime
    access_count: int = 0

    def is_expired(self) -> bool:
        """Check if entry has expired."""
        elapsed = (datetime.utcnow() - self.created_at).total_seconds()
        return elapsed > self.ttl_seconds

    def is_stale(self, max_age_seconds: int) -> bool:
        """Check if entry is stale (unused for too long)."""
        elapsed = (datetime.utcnow() - self.accessed_at).total_seconds()
        return elapsed > max_age_seconds


class CacheBackend(ABC):
    """Abstract base for cache backends (in-memory, Redis, etc)."""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Retrieve value from cache."""
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl_seconds: int) -> bool:
        """Store value in cache."""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all cache entries."""
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        pass


class InMemoryCacheBackend(CacheBackend):
    """In-memory cache with LRU eviction policy."""

    def __init__(self, max_items: int = 1000):
        """Initialize in-memory cache.

        Args:
            max_items: Maximum number of items before LRU eviction
        """
        self.cache: Dict[str, CacheEntry] = {}
        self.max_items = max_items
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        """Retrieve value from cache."""
        entry = self.cache.get(key)

        if entry is None:
            self.misses += 1
            return None

        if entry.is_expired():
            del self.cache[key]
            self.misses += 1
            return None

        entry.accessed_at = datetime.utcnow()
        entry.access_count += 1
        self.hits += 1
        return entry.value

    def set(self, key: str, value: Any, ttl_seconds: int) -> bool:
        """Store value in cache with LRU eviction."""
        now = datetime.utcnow()

        # Evict LRU item if at capacity
        if len(self.cache) >= self.max_items and key not in self.cache:
            lru_key = min(
                self.cache.keys(),
                key=lambda k: (self.cache[k].access_count, self.cache[k].accessed_at)
            )
            del self.cache[lru_key]
            logger.debug(f"LRU evicted: {lru_key}")

        self.cache[key] = CacheEntry(
            key=key,
            value=value,
            ttl_seconds=ttl_seconds,
            created_at=now,
            accessed_at=now,
        )
        return True

    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if key in self.cache:
            del self.cache[key]
            return True
        return False

    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()

    def exists(self, key: str) -> bool:
        """Check if key exists and is not expired."""
        entry = self.cache.get(key)
        if entry is None:
            return False
        if entry.is_expired():
            del self.cache[key]
            return False
        return True

    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "hits": self.hits,
            "misses": self.misses,
            "total_requests": total_requests,
            "hit_rate_percent": round(hit_rate, 2),
            "items": len(self.cache),
            "capacity": self.max_items,
        }


class RedisCacheBackend(CacheBackend):
    """Redis-based cache backend."""

    def __init__(self, redis_client: Optional[Any] = None):
        """Initialize Redis cache.

        Args:
            redis_client: Redis client instance (optional for now)
        """
        self.redis = redis_client
        self.is_available = redis_client is not None
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        """Retrieve value from Redis."""
        if not self.is_available:
            self.misses += 1
            return None

        try:
            value = self.redis.get(key)
            if value is None:
                self.misses += 1
                return None

            self.hits += 1
            return json.loads(value)
        except Exception as e:
            logger.error(f"Redis GET failed: {e}")
            self.misses += 1
            return None

    def set(self, key: str, value: Any, ttl_seconds: int) -> bool:
        """Store value in Redis."""
        if not self.is_available:
            return False

        try:
            self.redis.setex(
                key,
                ttl_seconds,
                json.dumps(value)
            )
            return True
        except Exception as e:
            logger.error(f"Redis SET failed: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete value from Redis."""
        if not self.is_available:
            return False

        try:
            return bool(self.redis.delete(key))
        except Exception as e:
            logger.error(f"Redis DELETE failed: {e}")
            return False

    def clear(self) -> None:
        """Clear all Redis cache entries."""
        if not self.is_available:
            return

        try:
            self.redis.flushdb()
        except Exception as e:
            logger.error(f"Redis FLUSHDB failed: {e}")

    def exists(self, key: str) -> bool:
        """Check if key exists in Redis."""
        if not self.is_available:
            return False

        try:
            return bool(self.redis.exists(key))
        except Exception as e:
            logger.error(f"Redis EXISTS failed: {e}")
            return False

    def get_stats(self) -> Dict[str, int]:
        """Get Redis statistics."""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "hits": self.hits,
            "misses": self.misses,
            "total_requests": total_requests,
            "hit_rate_percent": round(hit_rate, 2),
            "redis_available": self.is_available,
        }


class CacheService:
    """Multi-tier caching service with cache-aside pattern."""

    # Cache type configurations
    CACHE_CONFIGS = {
        "geolocation": {"ttl_seconds": 24 * 3600, "max_items": 1000},  # 24h
        "cot_template": {"ttl_seconds": 7 * 24 * 3600, "max_items": 500},  # 7d
        "health": {"ttl_seconds": 30, "max_items": 10},  # 30s
        "token": {"ttl_seconds": 3600, "max_items": 5000},  # 1h
    }

    def __init__(self, backend: Optional[CacheBackend] = None, use_redis: bool = False):
        """Initialize cache service.

        Args:
            backend: Cache backend instance (in-memory or Redis)
            use_redis: Whether to use Redis (requires redis_client)
        """
        if backend is None:
            # Default to in-memory cache
            backend = InMemoryCacheBackend(max_items=1000)

        self.backend = backend
        self.use_redis = use_redis

    def _make_key(self, cache_type: str, identifier: str) -> str:
        """Generate cache key with type prefix and hash."""
        hash_id = hashlib.md5(identifier.encode()).hexdigest()[:8]
        return f"{cache_type}:{hash_id}:{identifier}"

    def get(self, cache_type: str, identifier: str) -> Optional[Any]:
        """Retrieve value from cache (cache-aside pattern).

        Args:
            cache_type: Type of cache (geolocation, cot_template, health, token)
            identifier: Unique identifier for the cached item

        Returns:
            Cached value or None if not found/expired
        """
        key = self._make_key(cache_type, identifier)
        return self.backend.get(key)

    def set(self, cache_type: str, identifier: str, value: Any) -> bool:
        """Store value in cache.

        Args:
            cache_type: Type of cache
            identifier: Unique identifier
            value: Value to cache

        Returns:
            True if successfully cached
        """
        config = self.CACHE_CONFIGS.get(cache_type, {"ttl_seconds": 3600, "max_items": 1000})
        ttl = config["ttl_seconds"]
        key = self._make_key(cache_type, identifier)

        return self.backend.set(key, value, ttl)

    def invalidate(self, cache_type: str, identifier: str) -> bool:
        """Invalidate a cached item.

        Args:
            cache_type: Type of cache
            identifier: Unique identifier

        Returns:
            True if item was invalidated
        """
        key = self._make_key(cache_type, identifier)
        return self.backend.delete(key)

    def invalidate_by_pattern(self, pattern: str) -> int:
        """Invalidate all items matching pattern.

        Note: Pattern support depends on backend implementation.

        Args:
            pattern: Pattern to match (e.g., "geolocation:*")

        Returns:
            Number of items invalidated
        """
        # For in-memory backend, we can iterate
        if isinstance(self.backend, InMemoryCacheBackend):
            count = 0
            keys_to_delete = [k for k in self.backend.cache.keys() if pattern in k]
            for key in keys_to_delete:
                self.backend.delete(key)
                count += 1
            return count
        return 0

    def clear(self) -> None:
        """Clear all cached items."""
        self.backend.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self.backend.get_stats()

    def warm_cache(self, cache_type: str, items: List[tuple]) -> int:
        """Pre-populate cache with items.

        Args:
            cache_type: Type of cache
            items: List of (identifier, value) tuples

        Returns:
            Number of items successfully cached
        """
        count = 0
        for identifier, value in items:
            if self.set(cache_type, identifier, value):
                count += 1
        logger.info(f"Cache warmed: {count} items for {cache_type}")
        return count
