"""Unit tests for rate limit middleware."""
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from src.middleware_rate_limit import setup_rate_limiting
from src.services.rate_limiter_service import RateLimitConfig


@pytest.fixture
def rate_limit_config():
    """Create rate limit configuration."""
    return RateLimitConfig(
        per_user_quota=10,  # Low quota for testing
        per_endpoint_quota=1000,
    )


@pytest.fixture
def app_with_rate_limiting(rate_limit_config):
    """Create FastAPI app with rate limiting middleware."""
    app = FastAPI()

    # Setup rate limiting
    rate_limiter = setup_rate_limiting(app, rate_limit_config)

    @app.get("/test")
    async def test_endpoint():
        """Test endpoint."""
        return {"status": "ok"}

    @app.get("/health")
    async def health_check():
        """Health check (should bypass rate limiting)."""
        return {"status": "running"}

    return app


@pytest.fixture
def client(app_with_rate_limiting):
    """Create test client."""
    return TestClient(app_with_rate_limiting)


class TestRateLimitMiddlewareSetup:
    """Test rate limit middleware setup."""

    def test_middleware_added_to_app(self, app_with_rate_limiting):
        """Should add middleware to FastAPI app."""
        assert len(app_with_rate_limiting.user_middleware) > 0


class TestRateLimitResponse:
    """Test rate limit response headers."""

    def test_response_includes_rate_limit_headers(self, client):
        """Should include RateLimit headers in response."""
        response = client.get("/test")
        assert response.status_code == 200
        assert "RateLimit-Limit" in response.headers
        assert "RateLimit-Remaining" in response.headers
        assert "RateLimit-Reset" in response.headers

    def test_rate_limit_header_values(self, client):
        """Should have correct RateLimit header values."""
        response = client.get("/test")
        assert response.headers["RateLimit-Limit"] == "10"
        assert int(response.headers["RateLimit-Remaining"]) < 10

    def test_remaining_decreases_per_request(self, client):
        """Should decrease RateLimit-Remaining with each request."""
        response1 = client.get("/test")
        remaining1 = int(response1.headers["RateLimit-Remaining"])

        response2 = client.get("/test")
        remaining2 = int(response2.headers["RateLimit-Remaining"])

        assert remaining2 < remaining1


class TestRateLimitExceeded:
    """Test 429 Too Many Requests response."""

    def test_reject_when_quota_exceeded(self, client):
        """Should return 429 when quota exceeded."""
        # Use up quota (10 requests)
        for i in range(10):
            response = client.get("/test")
            assert response.status_code == 200

        # Next request should fail
        response = client.get("/test")
        assert response.status_code == 429

    def test_429_includes_error_code(self, client):
        """Should include error code in 429 response."""
        for i in range(10):
            client.get("/test")

        response = client.get("/test")
        assert response.status_code == 429
        body = response.json()
        assert body["error_code"] == "RATE_LIMIT_EXCEEDED"

    def test_429_includes_rate_limit_headers(self, client):
        """Should include rate limit headers in 429 response."""
        for i in range(10):
            client.get("/test")

        response = client.get("/test")
        assert response.status_code == 429
        assert "RateLimit-Limit" in response.headers
        assert response.headers["RateLimit-Remaining"] == "0"

    def test_429_error_message(self, client):
        """Should include error message in 429 response."""
        for i in range(10):
            client.get("/test")

        response = client.get("/test")
        assert response.status_code == 429
        body = response.json()
        assert "Rate limit exceeded" in body["error_message"]


class TestHealthCheckBypass:
    """Test health check bypass."""

    def test_health_check_bypasses_rate_limit(self, app_with_rate_limiting):
        """Should bypass rate limiting for health checks."""
        app = app_with_rate_limiting
        client = TestClient(app)

        # Make many health check requests (exceeding quota)
        for i in range(20):
            response = client.get("/health")
            assert response.status_code == 200

        # Health checks should not have rate limit headers
        response = client.get("/health")
        assert response.status_code == 200
        # Health check doesn't enforce rate limiting
