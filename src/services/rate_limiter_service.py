"""Rate limiting service with token bucket algorithm and Redis/in-memory support."""
import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple, Set
from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    per_user_quota: int = 100  # requests per minute per user
    per_endpoint_quota: int = 1000  # requests per minute per endpoint
    refill_rate: float = 100.0 / 60.0  # tokens per second (100/min = 1.67/sec)
    window_seconds: int = 60  # sliding window duration
    whitelist: Set[str] = None  # client IDs to bypass rate limiting

    def __post_init__(self):
        """Initialize whitelist if not provided."""
        if self.whitelist is None:
            self.whitelist = set()


@dataclass
class TokenBucketState:
    """Token bucket state for tracking quota."""

    tokens: float  # current tokens in bucket
    last_refill_time: float  # Unix timestamp of last refill
    quota_limit: int  # maximum tokens
    refill_rate: float  # tokens per second


class RateLimitStore(ABC):
    """Abstract base class for rate limit storage backends."""

    @abstractmethod
    def get_bucket(self, key: str) -> Optional[TokenBucketState]:
        """Get bucket state for a key."""
        pass

    @abstractmethod
    def update_bucket(self, key: str, bucket: TokenBucketState) -> None:
        """Update bucket state for a key."""
        pass

    @abstractmethod
    def increment_requests(self, endpoint: str) -> int:
        """Increment request counter for endpoint. Returns total requests."""
        pass

    @abstractmethod
    def get_endpoint_requests(self, endpoint: str) -> int:
        """Get total requests for endpoint in current window."""
        pass

    @abstractmethod
    def reset_window(self, key: str, endpoint: str) -> None:
        """Reset window timers."""
        pass


class InMemoryRateLimitStore(RateLimitStore):
    """In-memory rate limit store using dictionaries."""

    def __init__(self):
        """Initialize in-memory store."""
        self.buckets: Dict[str, TokenBucketState] = {}
        self.endpoint_requests: Dict[str, int] = {}
        self.window_start_times: Dict[str, float] = {}
        self.logger = logging.getLogger(__name__)

    def get_bucket(self, key: str) -> Optional[TokenBucketState]:
        """Get bucket state for a key."""
        return self.buckets.get(key)

    def update_bucket(self, key: str, bucket: TokenBucketState) -> None:
        """Update bucket state for a key."""
        self.buckets[key] = bucket

    def increment_requests(self, endpoint: str) -> int:
        """Increment request counter for endpoint."""
        current_time = time.time()
        window_key = f"window:{endpoint}"

        # Reset if window expired
        if window_key not in self.window_start_times:
            self.window_start_times[window_key] = current_time
            self.endpoint_requests[endpoint] = 0

        window_age = current_time - self.window_start_times[window_key]
        if window_age >= 60:  # 60-second window
            self.window_start_times[window_key] = current_time
            self.endpoint_requests[endpoint] = 0

        self.endpoint_requests[endpoint] = self.endpoint_requests.get(endpoint, 0) + 1
        return self.endpoint_requests[endpoint]

    def get_endpoint_requests(self, endpoint: str) -> int:
        """Get total requests for endpoint in current window."""
        current_time = time.time()
        window_key = f"window:{endpoint}"

        # Check if window expired
        if window_key in self.window_start_times:
            window_age = current_time - self.window_start_times[window_key]
            if window_age >= 60:
                return 0

        return self.endpoint_requests.get(endpoint, 0)

    def reset_window(self, key: str, endpoint: str) -> None:
        """Reset window timers."""
        window_key = f"window:{endpoint}"
        if window_key in self.window_start_times:
            del self.window_start_times[window_key]
        if endpoint in self.endpoint_requests:
            del self.endpoint_requests[endpoint]


class RedisRateLimitStore(RateLimitStore):
    """Redis-backed rate limit store (stub for future implementation)."""

    def __init__(self, redis_client=None):
        """Initialize Redis store."""
        self.redis = redis_client
        self.logger = logging.getLogger(__name__)
        if not self.redis:
            self.logger.warning("Redis not available, falling back to in-memory")

    def get_bucket(self, key: str) -> Optional[TokenBucketState]:
        """Get bucket state for a key."""
        if not self.redis:
            return None
        # Stub for Redis implementation
        return None

    def update_bucket(self, key: str, bucket: TokenBucketState) -> None:
        """Update bucket state for a key."""
        if not self.redis:
            return
        # Stub for Redis implementation
        pass

    def increment_requests(self, endpoint: str) -> int:
        """Increment request counter for endpoint."""
        if not self.redis:
            return 0
        # Stub for Redis implementation
        return 0

    def get_endpoint_requests(self, endpoint: str) -> int:
        """Get total requests for endpoint in current window."""
        if not self.redis:
            return 0
        # Stub for Redis implementation
        return 0

    def reset_window(self, key: str, endpoint: str) -> None:
        """Reset window timers."""
        if not self.redis:
            return
        # Stub for Redis implementation
        pass


class RateLimiterService:
    """Rate limiter using token bucket algorithm."""

    def __init__(
        self,
        config: Optional[RateLimitConfig] = None,
        store: Optional[RateLimitStore] = None,
    ):
        """Initialize rate limiter service.

        Args:
            config: Rate limit configuration
            store: Storage backend (defaults to in-memory)
        """
        self.config = config or RateLimitConfig()
        self.store = store or InMemoryRateLimitStore()
        self.logger = logging.getLogger(__name__)

    def is_whitelisted(self, client_id: str) -> bool:
        """Check if client is whitelisted.

        Args:
            client_id: Client identifier

        Returns:
            bool: True if client is whitelisted
        """
        return client_id in self.config.whitelist

    def allow_request(
        self,
        client_id: str,
        endpoint: str,
    ) -> Tuple[bool, Dict[str, str]]:
        """Check if request is allowed and return rate limit headers.

        Args:
            client_id: Client identifier
            endpoint: API endpoint path

        Returns:
            Tuple of (allowed: bool, headers: dict)
                headers contains RateLimit-Limit, RateLimit-Remaining, RateLimit-Reset
        """
        # Whitelist bypass
        if self.is_whitelisted(client_id):
            return True, {}

        # Check per-user quota
        user_key = f"user:{client_id}"
        bucket = self._get_or_create_bucket(user_key, self.config.per_user_quota)

        # Refill tokens based on elapsed time
        bucket = self._refill_tokens(bucket)

        # Check if tokens available
        if bucket.tokens >= 1:
            bucket.tokens -= 1
            self.store.update_bucket(user_key, bucket)

            # Calculate reset time
            reset_time = self._calculate_reset_time(bucket)

            headers = {
                "RateLimit-Limit": str(self.config.per_user_quota),
                "RateLimit-Remaining": str(int(bucket.tokens)),
                "RateLimit-Reset": str(int(reset_time)),
            }
            return True, headers

        # Quota exceeded
        reset_time = self._calculate_reset_time(bucket)
        headers = {
            "RateLimit-Limit": str(self.config.per_user_quota),
            "RateLimit-Remaining": "0",
            "RateLimit-Reset": str(int(reset_time)),
        }
        return False, headers

    def get_quota_usage(self, client_id: str) -> Dict[str, int]:
        """Get current quota usage for a client.

        Args:
            client_id: Client identifier

        Returns:
            dict with quota_limit, quota_used, quota_remaining, quota_reset_time_seconds
        """
        user_key = f"user:{client_id}"
        bucket = self._get_or_create_bucket(user_key, self.config.per_user_quota)
        bucket = self._refill_tokens(bucket)

        used = self.config.per_user_quota - int(bucket.tokens)
        remaining = int(bucket.tokens)
        reset_time = self._calculate_reset_time(bucket)
        reset_in_seconds = int(reset_time - time.time())

        return {
            "quota_limit": self.config.per_user_quota,
            "quota_used": used,
            "quota_remaining": remaining,
            "quota_reset_time_seconds": max(0, reset_in_seconds),
        }

    def _get_or_create_bucket(
        self,
        key: str,
        quota_limit: int,
    ) -> TokenBucketState:
        """Get existing bucket or create new one.

        Args:
            key: Bucket key (e.g., "user:client_id")
            quota_limit: Maximum tokens in bucket

        Returns:
            TokenBucketState: Bucket state
        """
        bucket = self.store.get_bucket(key)
        if bucket is None:
            bucket = TokenBucketState(
                tokens=float(quota_limit),
                last_refill_time=time.time(),
                quota_limit=quota_limit,
                refill_rate=self.config.refill_rate,
            )
            self.store.update_bucket(key, bucket)
        return bucket

    def _refill_tokens(self, bucket: TokenBucketState) -> TokenBucketState:
        """Refill tokens based on elapsed time.

        Args:
            bucket: Token bucket state

        Returns:
            TokenBucketState: Updated bucket with refilled tokens
        """
        current_time = time.time()
        elapsed_seconds = current_time - bucket.last_refill_time

        # Add tokens: refill_rate tokens per second
        new_tokens = bucket.tokens + (elapsed_seconds * bucket.refill_rate)

        # Cap at quota limit
        new_tokens = min(new_tokens, float(bucket.quota_limit))

        bucket.tokens = new_tokens
        bucket.last_refill_time = current_time

        return bucket

    def _calculate_reset_time(self, bucket: TokenBucketState) -> float:
        """Calculate Unix timestamp when bucket will be full again.

        Args:
            bucket: Token bucket state

        Returns:
            float: Unix timestamp
        """
        tokens_needed = bucket.quota_limit - bucket.tokens
        seconds_needed = tokens_needed / bucket.refill_rate if bucket.refill_rate > 0 else 0
        return bucket.last_refill_time + seconds_needed
