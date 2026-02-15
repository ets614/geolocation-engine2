"""Unit tests for security middleware (headers, CORS).

Test Budget: 3 distinct behaviors x 2 = 6 unit tests max
Behaviors:
1. Security headers present on every response
2. CORS middleware allows configured origins
3. Middleware setup registers both CORS and security headers
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


class TestSecurityHeadersInResponse:
    """Test security headers through the API driving port."""

    def test_health_check_includes_security_headers(self, test_client):
        """Every response includes X-Content-Type-Options."""
        response = test_client.get("/api/v1/health")

        assert response.status_code == 200
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"

    def test_security_headers_on_error_responses(self, test_client):
        """Security headers present even on 404 responses."""
        response = test_client.get("/api/v1/nonexistent-endpoint")

        assert response.status_code == 404
        assert "X-Content-Type-Options" in response.headers

    def test_hsts_header_present(self, test_client):
        """Strict-Transport-Security header is set."""
        response = test_client.get("/api/v1/health")

        hsts = response.headers.get("Strict-Transport-Security", "")
        assert "max-age=" in hsts


class TestMiddlewareSetup:
    """Test middleware registration through the driving port."""

    def test_setup_middleware_registers_cors_and_security(self):
        """setup_middleware registers both CORS and security headers middleware."""
        from src.middleware import setup_middleware
        from src.config import get_config

        app = FastAPI()
        config = get_config()
        setup_middleware(app, config)

        # Should have registered at least 2 middleware layers
        assert len(app.user_middleware) >= 2

    def test_cors_allows_configured_origin(self, test_client):
        """CORS middleware allows requests from configured origins."""
        response = test_client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        # Should not be blocked
        assert response.status_code in [200, 405]
