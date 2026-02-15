"""Unit tests for JWT token refresh functionality.

Test Budget: 3 distinct behaviors x 2 = 6 unit tests max
Behaviors:
1. Refresh valid token returns new token with same claims
2. Refresh expired token raises error
3. Refresh endpoint returns new token via API
"""
import pytest
from src.services.jwt_service import JWTService


class TestJWTTokenRefresh:
    """Test token refresh through the JWTService driving port."""

    def test_refresh_valid_token_returns_new_token(self):
        """Service issues new token preserving subject claim."""
        service = JWTService(secret_key="test-secret")
        original = service.generate_token(subject="client-123", expires_in_minutes=60)

        refreshed = service.refresh_token(original, expires_in_minutes=120)

        assert refreshed != original  # New token issued
        payload = service.verify_token(refreshed)
        assert payload["sub"] == "client-123"

    def test_refresh_preserves_additional_claims(self):
        """Service carries forward non-standard claims on refresh."""
        service = JWTService(secret_key="test-secret")
        original = service.generate_token(
            subject="client-123",
            expires_in_minutes=60,
            additional_claims={"scope": "admin", "role": "operator"},
        )

        refreshed = service.refresh_token(original)
        payload = service.verify_token(refreshed)

        assert payload["scope"] == "admin"
        assert payload["role"] == "operator"

    def test_refresh_invalid_token_raises(self):
        """Service rejects refresh of invalid token."""
        service = JWTService(secret_key="test-secret")

        with pytest.raises(ValueError, match="Invalid token"):
            service.refresh_token("invalid.token.here")


class TestTokenRefreshEndpoint:
    """Test token refresh through the API endpoint."""

    def test_refresh_endpoint_returns_new_token(self, test_client):
        """POST /auth/refresh returns new valid token."""
        # First generate a token
        token_resp = test_client.post(
            "/api/v1/auth/token",
            json={"client_id": "test-client"},
        )
        original_token = token_resp.json()["access_token"]

        # Refresh it
        refresh_resp = test_client.post(
            "/api/v1/auth/refresh",
            json={"token": original_token, "expires_in_minutes": 120},
        )

        assert refresh_resp.status_code == 200
        data = refresh_resp.json()
        assert "access_token" in data
        assert data["token_type"] == "Bearer"
        assert data["expires_in"] == 7200  # 120 * 60

    def test_refresh_endpoint_rejects_invalid_token(self, test_client):
        """POST /auth/refresh returns 401 for invalid token."""
        refresh_resp = test_client.post(
            "/api/v1/auth/refresh",
            json={"token": "invalid.token.value"},
        )

        assert refresh_resp.status_code == 401
