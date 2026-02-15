"""Unit tests for caching service.

Test Budget: 6 distinct behaviors x 2 = 12 unit tests max
Behaviors:
1. Set and get cached values
2. Expire entries after TTL
3. Generate deterministic cache keys
4. Evict entries when at capacity
5. Invalidate by prefix pattern
6. Cache warming with loader function
"""
import pytest
import time

from src.services.cache_service import CacheService


class TestCacheSetAndGet:
    """Test basic cache operations through the service port."""

    def test_set_and_get_returns_cached_value(self):
        """Service stores and retrieves values."""
        cache = CacheService(default_ttl_seconds=60)
        cache.set("key1", {"detection_id": "det-001", "lat": 40.7})

        result = cache.get("key1")
        assert result["detection_id"] == "det-001"
        assert result["lat"] == 40.7

    def test_get_nonexistent_key_returns_none(self):
        """Service returns None for missing keys."""
        cache = CacheService()
        assert cache.get("nonexistent") is None

    def test_delete_removes_entry(self):
        """Service removes entry on delete."""
        cache = CacheService()
        cache.set("key1", "value1")

        assert cache.delete("key1") is True
        assert cache.get("key1") is None

    def test_delete_nonexistent_returns_false(self):
        """Service returns False when deleting missing key."""
        cache = CacheService()
        assert cache.delete("missing") is False


class TestCacheTTL:
    """Test TTL expiration through the service port."""

    def test_entry_expires_after_ttl(self):
        """Service expires entries after TTL elapses."""
        cache = CacheService(default_ttl_seconds=0.05)
        cache.set("key1", "value1")

        time.sleep(0.1)
        assert cache.get("key1") is None

    def test_custom_ttl_per_entry(self):
        """Service supports per-entry TTL override."""
        cache = CacheService(default_ttl_seconds=60)
        cache.set("short", "value", ttl_seconds=0.05)
        cache.set("long", "value", ttl_seconds=60)

        time.sleep(0.1)
        assert cache.get("short") is None
        assert cache.get("long") == "value"


class TestCacheKeyGeneration:
    """Test cache key generation through the service port."""

    def test_generate_deterministic_key(self):
        """Same inputs produce same cache key."""
        key1 = CacheService.generate_cache_key("detection", 40.7, -74.0)
        key2 = CacheService.generate_cache_key("detection", 40.7, -74.0)
        assert key1 == key2

    def test_different_inputs_produce_different_keys(self):
        """Different inputs produce different cache keys."""
        key1 = CacheService.generate_cache_key("detection", 40.7)
        key2 = CacheService.generate_cache_key("detection", 41.0)
        assert key1 != key2


class TestCacheEviction:
    """Test eviction and capacity through the service port."""

    def test_evicts_when_at_capacity(self):
        """Service evicts entries when max_entries reached."""
        cache = CacheService(default_ttl_seconds=60, max_entries=5)

        for i in range(10):
            cache.set(f"key{i}", f"value{i}")

        stats = cache.stats()
        assert stats["size"] <= 5

    def test_invalidate_pattern_removes_matching(self):
        """Service removes all keys matching prefix."""
        cache = CacheService()
        cache.set("detection:001", "val1")
        cache.set("detection:002", "val2")
        cache.set("audit:001", "val3")

        removed = cache.invalidate_pattern("detection:")
        assert removed == 2
        assert cache.get("audit:001") == "val3"


class TestCacheWarming:
    """Test cache warming through the service port."""

    def test_warm_calls_loader_on_miss(self):
        """Service calls loader when key not cached."""
        cache = CacheService()
        call_count = 0

        def loader():
            nonlocal call_count
            call_count += 1
            return {"data": "loaded"}

        result = cache.warm("key1", loader)
        assert result["data"] == "loaded"
        assert call_count == 1

    def test_warm_uses_cache_on_hit(self):
        """Service returns cached value without calling loader."""
        cache = CacheService()
        cache.set("key1", {"data": "cached"})

        call_count = 0

        def loader():
            nonlocal call_count
            call_count += 1
            return {"data": "loaded"}

        result = cache.warm("key1", loader)
        assert result["data"] == "cached"
        assert call_count == 0


class TestCacheStats:
    """Test cache statistics through the service port."""

    def test_stats_track_hits_and_misses(self):
        """Service tracks hit rate statistics."""
        cache = CacheService()
        cache.set("key1", "value1")

        cache.get("key1")  # hit
        cache.get("key1")  # hit
        cache.get("miss")  # miss

        stats = cache.stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["hit_rate"] == pytest.approx(0.6667, abs=0.01)
        assert stats["size"] == 1

    def test_clear_resets_stats(self):
        """Service resets stats on clear."""
        cache = CacheService()
        cache.set("key1", "value1")
        cache.get("key1")

        cache.clear()
        stats = cache.stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["size"] == 0
