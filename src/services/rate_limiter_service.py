"""Rate limiting service using token bucket algorithm."""
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple


@dataclass
class TokenBucket:
    """Token bucket for rate limiting a single client.

    Attributes:
        capacity: Maximum number of tokens.
        refill_rate: Tokens added per second.
        tokens: Current token count.
        last_refill: Timestamp of last refill.
    """
    capacity: int
    refill_rate: float
    tokens: float = field(init=False)
    last_refill: float = field(init=False)

    def __post_init__(self):
        self.tokens = float(self.capacity)
        self.last_refill = time.monotonic()

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(
            self.capacity,
            self.tokens + elapsed * self.refill_rate,
        )
        self.last_refill = now

    def consume(self, count: int = 1) -> bool:
        """Attempt to consume tokens.

        Args:
            count: Number of tokens to consume.

        Returns:
            True if tokens were consumed, False if insufficient.
        """
        self._refill()
        if self.tokens >= count:
            self.tokens -= count
            return True
        return False

    def remaining(self) -> int:
        """Return the number of remaining tokens (integer floor)."""
        self._refill()
        return int(self.tokens)

    def time_until_available(self) -> float:
        """Return seconds until at least 1 token is available."""
        self._refill()
        if self.tokens >= 1.0:
            return 0.0
        deficit = 1.0 - self.tokens
        return deficit / self.refill_rate


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""
    allowed: bool
    remaining: int
    limit: int
    retry_after_seconds: float = 0.0
    reset_seconds: float = 0.0


class RateLimiterService:
    """Per-client rate limiting service using token bucket algorithm.

    Each client gets an independent bucket with configurable capacity and refill rate.
    """

    def __init__(
        self,
        default_capacity: int = 100,
        default_refill_rate: float = 10.0,
    ):
        """Initialize rate limiter.

        Args:
            default_capacity: Default max tokens per client.
            default_refill_rate: Default tokens per second refill rate.
        """
        if default_capacity <= 0:
            raise ValueError("capacity must be positive")
        if default_refill_rate <= 0:
            raise ValueError("refill_rate must be positive")

        self.default_capacity = default_capacity
        self.default_refill_rate = default_refill_rate
        self._buckets: Dict[str, TokenBucket] = {}
        self._client_overrides: Dict[str, Tuple[int, float]] = {}

    def set_client_limit(
        self, client_id: str, capacity: int, refill_rate: float
    ) -> None:
        """Set custom rate limit for a specific client.

        Args:
            client_id: Client identifier.
            capacity: Max tokens for this client.
            refill_rate: Tokens per second for this client.
        """
        self._client_overrides[client_id] = (capacity, refill_rate)
        # Reset existing bucket if override changes
        if client_id in self._buckets:
            del self._buckets[client_id]

    def _get_bucket(self, client_id: str) -> TokenBucket:
        """Get or create a token bucket for a client.

        Args:
            client_id: Client identifier.

        Returns:
            TokenBucket for the client.
        """
        if client_id not in self._buckets:
            if client_id in self._client_overrides:
                capacity, rate = self._client_overrides[client_id]
            else:
                capacity = self.default_capacity
                rate = self.default_refill_rate
            self._buckets[client_id] = TokenBucket(
                capacity=capacity, refill_rate=rate
            )
        return self._buckets[client_id]

    def check_rate_limit(self, client_id: str) -> RateLimitResult:
        """Check and consume a rate limit token for a client.

        Args:
            client_id: Client identifier.

        Returns:
            RateLimitResult with allowed status and metadata.
        """
        bucket = self._get_bucket(client_id)
        allowed = bucket.consume(1)

        if allowed:
            return RateLimitResult(
                allowed=True,
                remaining=bucket.remaining(),
                limit=bucket.capacity,
                retry_after_seconds=0.0,
                reset_seconds=bucket.capacity / bucket.refill_rate,
            )
        else:
            return RateLimitResult(
                allowed=False,
                remaining=0,
                limit=bucket.capacity,
                retry_after_seconds=bucket.time_until_available(),
                reset_seconds=bucket.capacity / bucket.refill_rate,
            )

    def get_remaining(self, client_id: str) -> int:
        """Get remaining tokens for a client without consuming.

        Args:
            client_id: Client identifier.

        Returns:
            Number of remaining tokens.
        """
        bucket = self._get_bucket(client_id)
        return bucket.remaining()

    def reset_client(self, client_id: str) -> None:
        """Reset rate limit for a client (restore full bucket).

        Args:
            client_id: Client identifier.
        """
        if client_id in self._buckets:
            del self._buckets[client_id]
