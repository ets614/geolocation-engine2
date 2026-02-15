"""Unit tests for rate limiter service (token bucket algorithm)."""
import pytest
import time
from src.services.rate_limiter_service import (
    RateLimiterService,
    RateLimitConfig,
    TokenBucketState,
    InMemoryRateLimitStore,
)


@pytest.fixture
def rate_limit_config():
    """Create rate limit configuration."""
    return RateLimitConfig(
        per_user_quota=100,
        per_endpoint_quota=1000,
        refill_rate=100.0 / 60.0,  # 100 per minute
        window_seconds=60,
    )


@pytest.fixture
def in_memory_store():
    """Create in-memory rate limit store."""
    return InMemoryRateLimitStore()


@pytest.fixture
def rate_limiter(rate_limit_config, in_memory_store):
    """Create rate limiter service."""
    return RateLimiterService(config=rate_limit_config, store=in_memory_store)


class TestRateLimitConfig:
    """Test rate limit configuration."""

    def test_config_default_quota(self):
        """Should have default per-user quota of 100."""
        config = RateLimitConfig()
        assert config.per_user_quota == 100

    def test_config_default_endpoint_quota(self):
        """Should have default per-endpoint quota of 1000."""
        config = RateLimitConfig()
        assert config.per_endpoint_quota == 1000

    def test_config_default_refill_rate(self):
        """Should have default refill rate of 100/60 tokens per second."""
        config = RateLimitConfig()
        assert config.refill_rate == 100.0 / 60.0

    def test_config_whitelist_initialization(self):
        """Should initialize whitelist as empty set."""
        config = RateLimitConfig()
        assert isinstance(config.whitelist, set)
        assert len(config.whitelist) == 0

    def test_config_custom_whitelist(self):
        """Should support custom whitelist."""
        whitelist = {"trusted-client", "admin"}
        config = RateLimitConfig(whitelist=whitelist)
        assert "trusted-client" in config.whitelist
        assert "admin" in config.whitelist


class TestTokenBucketState:
    """Test token bucket state."""

    def test_bucket_creation(self):
        """Should create token bucket state."""
        bucket = TokenBucketState(
            tokens=100.0,
            last_refill_time=time.time(),
            quota_limit=100,
            refill_rate=1.67,
        )
        assert bucket.tokens == 100.0
        assert bucket.quota_limit == 100
        assert bucket.refill_rate == 1.67

    def test_bucket_empty(self):
        """Should support empty bucket."""
        bucket = TokenBucketState(
            tokens=0.0,
            last_refill_time=time.time(),
            quota_limit=100,
            refill_rate=1.67,
        )
        assert bucket.tokens == 0.0


class TestInMemoryRateLimitStore:
    """Test in-memory rate limit store."""

    def test_store_get_bucket_nonexistent(self, in_memory_store):
        """Should return None for nonexistent bucket."""
        bucket = in_memory_store.get_bucket("user:test")
        assert bucket is None

    def test_store_update_bucket(self, in_memory_store):
        """Should update bucket state."""
        bucket = TokenBucketState(
            tokens=50.0,
            last_refill_time=time.time(),
            quota_limit=100,
            refill_rate=1.67,
        )
        in_memory_store.update_bucket("user:test", bucket)

        retrieved = in_memory_store.get_bucket("user:test")
        assert retrieved is not None
        assert retrieved.tokens == 50.0

    def test_store_increment_requests_new_endpoint(self, in_memory_store):
        """Should increment requests for new endpoint."""
        count = in_memory_store.increment_requests("/api/v1/detections")
        assert count == 1

    def test_store_increment_requests_same_endpoint(self, in_memory_store):
        """Should increment requests sequentially."""
        count1 = in_memory_store.increment_requests("/api/v1/detections")
        count2 = in_memory_store.increment_requests("/api/v1/detections")
        assert count1 == 1
        assert count2 == 2

    def test_store_get_endpoint_requests(self, in_memory_store):
        """Should get total endpoint requests."""
        in_memory_store.increment_requests("/api/v1/detections")
        in_memory_store.increment_requests("/api/v1/detections")

        count = in_memory_store.get_endpoint_requests("/api/v1/detections")
        assert count == 2

    def test_store_reset_window(self, in_memory_store):
        """Should reset window tracking."""
        in_memory_store.increment_requests("/api/v1/detections")
        in_memory_store.reset_window("user:test", "/api/v1/detections")

        count = in_memory_store.get_endpoint_requests("/api/v1/detections")
        assert count == 0


class TestAllowRequest:
    """Test request allowance logic."""

    def test_allow_first_request(self, rate_limiter):
        """Should allow first request."""
        allowed, headers = rate_limiter.allow_request("client1", "/api/v1/detections")
        assert allowed is True

    def test_allow_request_within_quota(self, rate_limiter):
        """Should allow requests within quota."""
        for i in range(10):
            allowed, headers = rate_limiter.allow_request(
                "client1",
                "/api/v1/detections"
            )
            assert allowed is True

    def test_headers_include_limit(self, rate_limiter):
        """Should include RateLimit-Limit header."""
        allowed, headers = rate_limiter.allow_request("client1", "/api/v1/detections")
        assert "RateLimit-Limit" in headers
        assert headers["RateLimit-Limit"] == "100"

    def test_headers_include_remaining(self, rate_limiter):
        """Should include RateLimit-Remaining header."""
        allowed, headers = rate_limiter.allow_request("client1", "/api/v1/detections")
        assert "RateLimit-Remaining" in headers

    def test_remaining_decreases(self, rate_limiter):
        """Should show decreasing remaining quota."""
        _, headers1 = rate_limiter.allow_request("client1", "/api/v1/detections")
        remaining1 = int(headers1["RateLimit-Remaining"])

        _, headers2 = rate_limiter.allow_request("client1", "/api/v1/detections")
        remaining2 = int(headers2["RateLimit-Remaining"])

        assert remaining2 < remaining1

    def test_headers_include_reset_time(self, rate_limiter):
        """Should include RateLimit-Reset header with Unix timestamp."""
        allowed, headers = rate_limiter.allow_request("client1", "/api/v1/detections")
        assert "RateLimit-Reset" in headers
        reset_time = int(headers["RateLimit-Reset"])
        # Reset time should be within the next 60 seconds
        assert reset_time >= int(time.time())

    def test_reject_after_quota_exceeded(self, rate_limiter):
        """Should reject when quota exceeded."""
        # Use up all 100 tokens
        for i in range(100):
            allowed, _ = rate_limiter.allow_request("client2", "/api/v1/detections")
            assert allowed is True

        # Next request should fail
        allowed, headers = rate_limiter.allow_request("client2", "/api/v1/detections")
        assert allowed is False
        assert headers["RateLimit-Remaining"] == "0"

    def test_reject_response_has_limit_headers(self, rate_limiter):
        """Should include rate limit headers in rejection."""
        for i in range(100):
            rate_limiter.allow_request("client3", "/api/v1/detections")

        allowed, headers = rate_limiter.allow_request("client3", "/api/v1/detections")
        assert allowed is False
        assert headers["RateLimit-Limit"] == "100"
        assert headers["RateLimit-Remaining"] == "0"

    def test_different_clients_independent_quotas(self, rate_limiter):
        """Should track quotas independently per client."""
        # Client A uses 50
        for i in range(50):
            rate_limiter.allow_request("clientA", "/api/v1/detections")

        # Client B should still have full quota
        allowed, headers = rate_limiter.allow_request("clientB", "/api/v1/detections")
        assert allowed is True
        assert int(headers["RateLimit-Remaining"]) > 90


class TestTokenRefill:
    """Test token refilling over time."""

    def test_tokens_refill_after_wait(self, rate_limiter):
        """Should refill tokens after waiting."""
        # Use up quota
        for i in range(100):
            rate_limiter.allow_request("client4", "/api/v1/detections")

        allowed, _ = rate_limiter.allow_request("client4", "/api/v1/detections")
        assert allowed is False

        # Wait for partial refill (1 second = ~1.67 tokens refilled)
        time.sleep(1)

        allowed, _ = rate_limiter.allow_request("client4", "/api/v1/detections")
        assert allowed is True

    def test_tokens_refill_capped_at_quota(self, rate_limiter):
        """Should not exceed quota limit after refill."""
        # Use some tokens
        rate_limiter.allow_request("client5", "/api/v1/detections")
        rate_limiter.allow_request("client5", "/api/v1/detections")

        # Wait and check that tokens don't exceed quota
        time.sleep(1)
        _, headers = rate_limiter.allow_request("client5", "/api/v1/detections")

        # Should have close to quota
        remaining = int(headers["RateLimit-Remaining"])
        assert remaining > 0
        assert remaining <= 100


class TestWhitelist:
    """Test whitelist bypass."""

    def test_whitelist_allows_bypass(self, rate_limit_config):
        """Should allow whitelisted clients to bypass quota."""
        config = RateLimitConfig(whitelist={"trusted-client"})
        rate_limiter = RateLimiterService(config=config)

        # Use far more than quota
        for i in range(500):
            allowed, headers = rate_limiter.allow_request(
                "trusted-client",
                "/api/v1/detections"
            )
            assert allowed is True
            # Whitelisted clients don't get rate limit headers
            assert "RateLimit-Limit" not in headers

    def test_whitelist_is_case_sensitive(self):
        """Should treat whitelist as case sensitive."""
        config = RateLimitConfig(whitelist={"TrustedClient"})
        rate_limiter = RateLimiterService(config=config)

        # Different case should not be whitelisted
        allowed, headers = rate_limiter.allow_request(
            "trustedclient",
            "/api/v1/detections"
        )
        assert allowed is True  # First request always succeeds
        assert "RateLimit-Limit" in headers

    def test_non_whitelisted_enforces_quota(self, rate_limit_config):
        """Should enforce quota for non-whitelisted clients."""
        config = RateLimitConfig(whitelist={"trusted-client"})
        rate_limiter = RateLimiterService(config=config)

        for i in range(100):
            rate_limiter.allow_request("regular-client", "/api/v1/detections")

        allowed, _ = rate_limiter.allow_request("regular-client", "/api/v1/detections")
        assert allowed is False


class TestQuotaUsageMetrics:
    """Test quota usage reporting."""

    def test_get_quota_usage_no_requests(self, rate_limiter):
        """Should report full quota with no requests."""
        usage = rate_limiter.get_quota_usage("client6")
        assert usage["quota_limit"] == 100
        assert usage["quota_used"] == 0
        assert usage["quota_remaining"] == 100

    def test_get_quota_usage_partial_requests(self, rate_limiter):
        """Should report correct usage after some requests."""
        for i in range(25):
            rate_limiter.allow_request("client7", "/api/v1/detections")

        usage = rate_limiter.get_quota_usage("client7")
        assert usage["quota_used"] == 25
        assert usage["quota_remaining"] == 75

    def test_get_quota_usage_full_quota(self, rate_limiter):
        """Should report empty quota when used up."""
        for i in range(100):
            rate_limiter.allow_request("client8", "/api/v1/detections")

        usage = rate_limiter.get_quota_usage("client8")
        assert usage["quota_used"] == 100
        assert usage["quota_remaining"] == 0

    def test_quota_usage_includes_reset_time(self, rate_limiter):
        """Should include reset time in quota usage."""
        rate_limiter.allow_request("client9", "/api/v1/detections")
        usage = rate_limiter.get_quota_usage("client9")

        assert "quota_reset_time_seconds" in usage
        assert usage["quota_reset_time_seconds"] >= 0
        assert usage["quota_reset_time_seconds"] <= 60


class TestBurstHandling:
    """Test burst traffic handling."""

    def test_burst_within_quota(self, rate_limiter):
        """Should handle burst of requests within quota."""
        burst_size = 50
        for i in range(burst_size):
            allowed, _ = rate_limiter.allow_request("client10", "/api/v1/detections")
            assert allowed is True

        usage = rate_limiter.get_quota_usage("client10")
        assert usage["quota_used"] == burst_size

    def test_burst_exceeding_quota(self, rate_limiter):
        """Should reject requests when burst exceeds quota."""
        allowed_count = 0
        rejected_count = 0

        # Send 150 burst requests
        for i in range(150):
            allowed, _ = rate_limiter.allow_request("client11", "/api/v1/detections")
            if allowed:
                allowed_count += 1
            else:
                rejected_count += 1

        # First 100 should succeed, rest fail
        assert allowed_count == 100
        assert rejected_count == 50


class TestEndpointTracking:
    """Test per-endpoint request tracking."""

    def test_increment_endpoint_requests(self, in_memory_store):
        """Should track requests per endpoint."""
        store = in_memory_store

        store.increment_requests("/api/v1/detections")
        store.increment_requests("/api/v1/detections")
        store.increment_requests("/api/v1/auth/token")

        assert store.get_endpoint_requests("/api/v1/detections") == 2
        assert store.get_endpoint_requests("/api/v1/auth/token") == 1

    def test_different_endpoints_independent(self, in_memory_store):
        """Should track different endpoints independently."""
        store = in_memory_store

        for i in range(10):
            store.increment_requests("/api/v1/detections")

        for i in range(5):
            store.increment_requests("/api/v1/auth/token")

        assert store.get_endpoint_requests("/api/v1/detections") == 10
        assert store.get_endpoint_requests("/api/v1/auth/token") == 5


class TestWindowReset:
    """Test rate limit window reset."""

    def test_window_reset_clears_endpoint_requests(self, in_memory_store):
        """Should reset endpoint request counter."""
        store = in_memory_store

        store.increment_requests("/api/v1/detections")
        store.increment_requests("/api/v1/detections")

        store.reset_window("user:test", "/api/v1/detections")

        assert store.get_endpoint_requests("/api/v1/detections") == 0
