"""Unit tests for caching service.

Tests cache miss/hit, TTL expiration, LRU eviction, invalidation,
pattern matching, and cache warming.
"""

import pytest
from datetime import datetime, timedelta
from time import sleep
from src.services.cache_service import (
    CacheService,
    InMemoryCacheBackend,
    CacheEntry,
)


@pytest.fixture
def cache_backend():
    """Create in-memory cache backend."""
    return InMemoryCacheBackend(max_items=10)


@pytest.fixture
def cache_service(cache_backend):
    """Create cache service with backend."""
    return CacheService(backend=cache_backend)


class TestCacheMissHit:
    """Test cache miss and hit scenarios."""

    def test_cache_miss_on_empty_cache(self, cache_service):
        """Test that get returns None for empty cache."""
        result = cache_service.get("geolocation", "test_id")
        assert result is None

    def test_cache_hit_after_set(self, cache_service):
        """Test that value is retrieved after set."""
        cache_service.set("geolocation", "test_id", {"lat": 40.7128})
        result = cache_service.get("geolocation", "test_id")
        assert result == {"lat": 40.7128}

    def test_multiple_cache_hits(self, cache_service):
        """Test multiple hits don't corrupt data."""
        value = {"lat": 40.7128, "lon": -74.0060}
        cache_service.set("geolocation", "id1", value)

        for _ in range(5):
            result = cache_service.get("geolocation", "id1")
            assert result == value

    def test_cache_hit_rate_tracking(self, cache_backend, cache_service):
        """Test hit rate statistics."""
        cache_service.set("geolocation", "id1", {"lat": 40.7128})

        # 2 hits
        cache_service.get("geolocation", "id1")
        cache_service.get("geolocation", "id1")

        # 1 miss
        cache_service.get("geolocation", "id2")

        stats = cache_backend.get_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["total_requests"] == 3
        assert stats["hit_rate_percent"] == pytest.approx(66.67, abs=0.1)

    def test_separate_cache_namespaces(self, cache_service):
        """Test different cache types don't interfere."""
        cache_service.set("geolocation", "id1", {"lat": 40.7128})
        cache_service.set("cot_template", "id1", {"type": "vehicle"})

        geo = cache_service.get("geolocation", "id1")
        cot = cache_service.get("cot_template", "id1")

        assert geo == {"lat": 40.7128}
        assert cot == {"type": "vehicle"}


class TestCacheTTL:
    """Test TTL (time-to-live) expiration."""

    def test_ttl_expiration(self, cache_backend):
        """Test that expired entries are not returned."""
        # Set with 1 second TTL
        cache_backend.set("key1", {"data": "value"}, ttl_seconds=1)

        # Should hit immediately
        assert cache_backend.get("key1") is not None

        # Simulate expiration
        entry = cache_backend.cache["key1"]
        entry.created_at = datetime.utcnow() - timedelta(seconds=2)

        # Should be expired
        assert cache_backend.get("key1") is None

    def test_different_ttls_for_cache_types(self, cache_service):
        """Test different TTL for different cache types."""
        # Geolocation: 24h, CoT: 7d, Health: 30s
        assert cache_service.CACHE_CONFIGS["geolocation"]["ttl_seconds"] == 24 * 3600
        assert cache_service.CACHE_CONFIGS["cot_template"]["ttl_seconds"] == 7 * 24 * 3600
        assert cache_service.CACHE_CONFIGS["health"]["ttl_seconds"] == 30

    def test_token_ttl_expiration(self, cache_backend):
        """Test token cache uses 1 hour TTL."""
        cache_backend.set("token1", "jwt_token_data", ttl_seconds=3600)
        assert cache_backend.get("token1") is not None

        # Simulate token expiration
        entry = cache_backend.cache["token1"]
        entry.created_at = datetime.utcnow() - timedelta(seconds=3601)

        assert cache_backend.get("token1") is None

    def test_expired_entry_removed_from_cache(self, cache_backend):
        """Test that expired entries are removed when accessed."""
        cache_backend.set("key1", {"data": "value"}, ttl_seconds=1)

        # Simulate expiration
        entry = cache_backend.cache["key1"]
        entry.created_at = datetime.utcnow() - timedelta(seconds=2)

        # Should be removed from cache
        cache_backend.get("key1")
        assert "key1" not in cache_backend.cache


class TestLRUEviction:
    """Test Least Recently Used eviction policy."""

    def test_lru_eviction_on_capacity(self, cache_backend):
        """Test LRU eviction when cache reaches max capacity."""
        max_items = cache_backend.max_items

        # Fill cache
        for i in range(max_items):
            cache_backend.set(f"key{i}", f"value{i}", ttl_seconds=3600)

        assert len(cache_backend.cache) == max_items

        # Add one more - should evict LRU
        cache_backend.set("key_new", "value_new", ttl_seconds=3600)

        assert len(cache_backend.cache) == max_items
        assert "key_new" in cache_backend.cache

    def test_lru_evicts_least_accessed(self, cache_backend):
        """Test that LRU evicts least recently accessed item."""
        cache_backend.max_items = 3

        # Add 3 items
        cache_backend.set("key1", "value1", ttl_seconds=3600)
        cache_backend.set("key2", "value2", ttl_seconds=3600)
        cache_backend.set("key3", "value3", ttl_seconds=3600)

        # Access key1 and key2 multiple times
        cache_backend.get("key1")
        cache_backend.get("key1")
        cache_backend.get("key2")

        # key3 is LRU, should be evicted
        cache_backend.set("key4", "value4", ttl_seconds=3600)

        assert "key1" in cache_backend.cache
        assert "key2" in cache_backend.cache
        assert "key3" not in cache_backend.cache
        assert "key4" in cache_backend.cache

    def test_access_count_tracking(self, cache_backend):
        """Test access count is incremented on each get."""
        cache_backend.set("key1", "value1", ttl_seconds=3600)

        entry = cache_backend.cache["key1"]
        assert entry.access_count == 0

        cache_backend.get("key1")
        assert entry.access_count == 1

        cache_backend.get("key1")
        assert entry.access_count == 2

    def test_lru_with_different_access_patterns(self, cache_backend):
        """Test LRU with realistic access patterns."""
        cache_backend.max_items = 3

        # Add items
        cache_backend.set("hot", "value", ttl_seconds=3600)
        cache_backend.set("warm", "value", ttl_seconds=3600)
        cache_backend.set("cold", "value", ttl_seconds=3600)

        # Access hot frequently, warm occasionally
        for _ in range(10):
            cache_backend.get("hot")
        for _ in range(3):
            cache_backend.get("warm")

        # cold has 0 accesses, should be evicted first
        cache_backend.set("new_hot", "value", ttl_seconds=3600)
        assert "cold" not in cache_backend.cache


class TestCacheInvalidation:
    """Test cache invalidation mechanisms."""

    def test_invalidate_single_key(self, cache_service):
        """Test invalidating a single cached item."""
        cache_service.set("geolocation", "id1", {"lat": 40.7128})
        assert cache_service.get("geolocation", "id1") is not None

        cache_service.invalidate("geolocation", "id1")
        assert cache_service.get("geolocation", "id1") is None

    def test_invalidate_nonexistent_key(self, cache_service):
        """Test invalidating non-existent key returns False."""
        result = cache_service.invalidate("geolocation", "nonexistent")
        assert result is False

    def test_invalidate_by_pattern(self, cache_service):
        """Test invalidating by pattern."""
        cache_service.set("geolocation", "camera_1", {"lat": 40.0})
        cache_service.set("geolocation", "camera_2", {"lat": 41.0})
        cache_service.set("cot_template", "template_1", {"type": "vehicle"})

        # Invalidate all geolocation entries
        count = cache_service.invalidate_by_pattern("geolocation:")
        assert count == 2

        assert cache_service.get("geolocation", "camera_1") is None
        assert cache_service.get("geolocation", "camera_2") is None
        assert cache_service.get("cot_template", "template_1") is not None

    def test_clear_all_cache(self, cache_service):
        """Test clearing all cached items."""
        cache_service.set("geolocation", "id1", {"lat": 40.0})
        cache_service.set("cot_template", "t1", {"type": "vehicle"})
        cache_service.set("health", "h1", {"status": "ok"})

        cache_service.clear()

        assert cache_service.get("geolocation", "id1") is None
        assert cache_service.get("cot_template", "t1") is None
        assert cache_service.get("health", "h1") is None


class TestCacheWarmup:
    """Test cache pre-population."""

    def test_warm_cache_with_items(self, cache_service):
        """Test warming cache with initial items."""
        items = [
            ("id1", {"lat": 40.0}),
            ("id2", {"lat": 41.0}),
            ("id3", {"lat": 42.0}),
        ]

        count = cache_service.warm_cache("geolocation", items)
        assert count == 3

        assert cache_service.get("geolocation", "id1") == {"lat": 40.0}
        assert cache_service.get("geolocation", "id2") == {"lat": 41.0}
        assert cache_service.get("geolocation", "id3") == {"lat": 42.0}

    def test_warm_cache_partial_failure(self, cache_backend, cache_service):
        """Test cache warming with failures."""
        cache_backend.max_items = 2

        items = [
            ("id1", {"lat": 40.0}),
            ("id2", {"lat": 41.0}),
            ("id3", {"lat": 42.0}),  # Will evict earlier item
        ]

        count = cache_service.warm_cache("geolocation", items)
        assert count == 3  # All sets returned True

    def test_warm_empty_cache(self, cache_service):
        """Test warming with empty item list."""
        count = cache_service.warm_cache("geolocation", [])
        assert count == 0


class TestCacheStatistics:
    """Test cache statistics and monitoring."""

    def test_cache_stats_empty(self, cache_service):
        """Test stats for empty cache."""
        stats = cache_service.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["total_requests"] == 0
        assert stats["hit_rate_percent"] == 0

    def test_cache_stats_with_activity(self, cache_service):
        """Test stats accumulate correctly."""
        cache_service.set("geolocation", "id1", {"lat": 40.0})

        # 3 hits
        cache_service.get("geolocation", "id1")
        cache_service.get("geolocation", "id1")
        cache_service.get("geolocation", "id1")

        # 2 misses
        cache_service.get("geolocation", "id2")
        cache_service.get("geolocation", "id3")

        stats = cache_service.get_stats()
        assert stats["hits"] == 3
        assert stats["misses"] == 2
        assert stats["total_requests"] == 5
        assert stats["hit_rate_percent"] == 60.0

    def test_cache_capacity_stats(self, cache_service, cache_backend):
        """Test cache capacity tracking."""
        for i in range(5):
            cache_service.set("geolocation", f"id{i}", {"lat": 40.0 + i})

        stats = cache_service.get_stats()
        assert stats["items"] == 5
        assert stats["capacity"] == cache_backend.max_items  # From fixture


class TestConcurrentAccess:
    """Test cache behavior under concurrent access."""

    def test_cache_with_multiple_types(self, cache_service):
        """Test cache with multiple concurrent type access."""
        # Simulate concurrent access to different cache types
        cache_service.set("geolocation", "id1", {"lat": 40.0})
        cache_service.set("cot_template", "id1", {"type": "vehicle"})
        cache_service.set("health", "h1", {"status": "ok"})
        cache_service.set("token", "t1", "jwt_token")

        # All should be retrievable
        assert cache_service.get("geolocation", "id1") == {"lat": 40.0}
        assert cache_service.get("cot_template", "id1") == {"type": "vehicle"}
        assert cache_service.get("health", "h1") == {"status": "ok"}
        assert cache_service.get("token", "t1") == "jwt_token"

    def test_cache_updates_dont_affect_others(self, cache_service):
        """Test that updating one cache type doesn't affect others."""
        cache_service.set("geolocation", "id1", {"lat": 40.0})
        cache_service.set("geolocation", "id1", {"lat": 41.0})  # Update

        # Should get new value
        assert cache_service.get("geolocation", "id1") == {"lat": 41.0}

        # Other types unaffected
        cache_service.set("cot_template", "id1", {"type": "vehicle"})
        assert cache_service.get("cot_template", "id1") == {"type": "vehicle"}

    def test_cache_key_generation(self, cache_service):
        """Test that cache keys are unique per identifier."""
        cache_service.set("geolocation", "id1", {"data": "value1"})
        cache_service.set("geolocation", "id2", {"data": "value2"})

        # Different identifiers should have different keys
        assert cache_service.get("geolocation", "id1") != cache_service.get("geolocation", "id2")


@pytest.mark.parametrize("cache_type,ttl", [
    ("geolocation", 24 * 3600),
    ("cot_template", 7 * 24 * 3600),
    ("health", 30),
    ("token", 3600),
])
def test_cache_ttl_by_type(cache_service, cache_type, ttl):
    """Test TTL configuration for different cache types."""
    config = cache_service.CACHE_CONFIGS[cache_type]
    assert config["ttl_seconds"] == ttl


@pytest.mark.parametrize("identifier", [
    "simple",
    "with:colon:separators",
    "with/slashes",
    "with spaces",
])
def test_cache_key_generation_special_chars(cache_service, identifier):
    """Test cache key generation with special characters."""
    value = {"test": "data"}
    cache_service.set("geolocation", identifier, value)

    result = cache_service.get("geolocation", identifier)
    assert result == value
