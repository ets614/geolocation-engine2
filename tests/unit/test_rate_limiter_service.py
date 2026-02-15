"""Unit tests for rate limiting service (token bucket algorithm).

Test Budget: 5 distinct behaviors x 2 = 10 unit tests max
Behaviors:
1. Allow requests within capacity
2. Block requests when bucket exhausted
3. Tokens refill over time
4. Per-client independent buckets
5. Custom client limits override defaults
"""
import pytest
import time
from unittest.mock import patch

from src.services.rate_limiter_service import RateLimiterService, TokenBucket


class TestTokenBucketAllowance:
    """Test request allowance through the rate limiter port."""

    def test_allows_requests_within_capacity(self):
        """Service allows requests when tokens available."""
        limiter = RateLimiterService(default_capacity=10, default_refill_rate=1.0)

        result = limiter.check_rate_limit("client-1")
        assert result.allowed is True
        assert result.remaining >= 0
        assert result.limit == 10

    def test_blocks_requests_when_exhausted(self):
        """Service blocks requests after bucket is empty."""
        limiter = RateLimiterService(default_capacity=3, default_refill_rate=0.01)

        for _ in range(3):
            limiter.check_rate_limit("client-1")

        result = limiter.check_rate_limit("client-1")
        assert result.allowed is False
        assert result.remaining == 0
        assert result.retry_after_seconds > 0

    @pytest.mark.parametrize("capacity", [1, 5, 50, 100])
    def test_capacity_determines_burst_size(self, capacity):
        """Bucket capacity controls burst size."""
        limiter = RateLimiterService(
            default_capacity=capacity, default_refill_rate=0.001
        )
        allowed_count = 0
        for _ in range(capacity + 5):
            result = limiter.check_rate_limit("burst-client")
            if result.allowed:
                allowed_count += 1

        assert allowed_count == capacity


class TestTokenRefill:
    """Test token refill through the rate limiter port."""

    def test_tokens_refill_over_time(self):
        """Tokens become available again after refill interval."""
        limiter = RateLimiterService(default_capacity=1, default_refill_rate=1000.0)

        # Exhaust
        limiter.check_rate_limit("client-1")

        # Small delay for refill (1000 tokens/sec = 1ms per token)
        time.sleep(0.01)

        result = limiter.check_rate_limit("client-1")
        assert result.allowed is True

    def test_remaining_shows_current_tokens(self):
        """get_remaining returns current available tokens."""
        limiter = RateLimiterService(default_capacity=10, default_refill_rate=1.0)

        initial = limiter.get_remaining("client-1")
        assert initial == 10

        limiter.check_rate_limit("client-1")
        after = limiter.get_remaining("client-1")
        assert after == 9


class TestPerClientBuckets:
    """Test client isolation through the rate limiter port."""

    def test_clients_have_independent_buckets(self):
        """Different clients have independent rate limits."""
        limiter = RateLimiterService(default_capacity=2, default_refill_rate=0.001)

        # Exhaust client-1
        limiter.check_rate_limit("client-1")
        limiter.check_rate_limit("client-1")

        blocked = limiter.check_rate_limit("client-1")
        assert blocked.allowed is False

        # client-2 still has tokens
        allowed = limiter.check_rate_limit("client-2")
        assert allowed.allowed is True

    def test_custom_client_limit_overrides_default(self):
        """Custom per-client limits take precedence."""
        limiter = RateLimiterService(default_capacity=5, default_refill_rate=1.0)
        limiter.set_client_limit("vip-client", capacity=100, refill_rate=50.0)

        remaining = limiter.get_remaining("vip-client")
        assert remaining == 100

    def test_reset_client_restores_full_bucket(self):
        """Resetting a client restores full bucket capacity."""
        limiter = RateLimiterService(default_capacity=3, default_refill_rate=0.001)

        # Exhaust
        for _ in range(3):
            limiter.check_rate_limit("client-1")

        assert limiter.check_rate_limit("client-1").allowed is False

        # Reset
        limiter.reset_client("client-1")
        assert limiter.check_rate_limit("client-1").allowed is True


class TestRateLimiterConfiguration:
    """Test service configuration validation."""

    def test_rejects_zero_capacity(self):
        """Service rejects non-positive capacity."""
        with pytest.raises(ValueError, match="capacity must be positive"):
            RateLimiterService(default_capacity=0, default_refill_rate=1.0)

    def test_rejects_negative_refill_rate(self):
        """Service rejects non-positive refill rate."""
        with pytest.raises(ValueError, match="refill_rate must be positive"):
            RateLimiterService(default_capacity=10, default_refill_rate=-1.0)
