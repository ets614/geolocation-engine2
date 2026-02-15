"""Unit tests for JWT authentication endpoints."""
import pytest
from fastapi.testclient import TestClient


class TestAuthTokenEndpoint:
    """Tests for POST /api/v1/auth/token endpoint.

    Test Budget: 4 distinct behaviors x 2 = 8 unit tests max
    Behaviors:
    1. Generate token with valid client_id
    2. Validate required client_id field
    3. Include correct expiration in response
    4. Return proper response format
    """

    def test_auth_token_endpoint_exists(self, test_client):
        """Verify POST /api/v1/auth/token endpoint exists."""
        payload = {"client_id": "test-client"}
        response = test_client.post("/api/v1/auth/token", json=payload)

        assert response.status_code != 404

    def test_auth_token_generates_access_token(self, test_client):
        """Verify endpoint generates JWT access token."""
        payload = {"client_id": "test-client"}
        response = test_client.post("/api/v1/auth/token", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert data["access_token"] is not None
        assert len(data["access_token"]) > 0

    def test_auth_token_returns_bearer_type(self, test_client):
        """Verify token response includes Bearer token type."""
        payload = {"client_id": "test-client"}
        response = test_client.post("/api/v1/auth/token", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["token_type"] == "Bearer"

    def test_auth_token_includes_expiration_seconds(self, test_client):
        """Verify token response includes expiration in seconds."""
        payload = {"client_id": "test-client", "expires_in_minutes": 60}
        response = test_client.post("/api/v1/auth/token", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert "expires_in" in data
        assert data["expires_in"] == 3600  # 60 minutes * 60 seconds

    def test_auth_token_rejects_missing_client_id(self, test_client):
        """Verify endpoint rejects request without client_id."""
        payload = {}
        response = test_client.post("/api/v1/auth/token", json=payload)

        assert response.status_code == 422  # Unprocessable Entity

    def test_auth_token_rejects_empty_client_id(self, test_client):
        """Verify endpoint rejects empty client_id string."""
        payload = {"client_id": ""}
        response = test_client.post("/api/v1/auth/token", json=payload)

        assert response.status_code == 400
        assert "client_id is required" in response.json()["detail"]

    def test_auth_token_rejects_whitespace_only_client_id(self, test_client):
        """Verify endpoint rejects whitespace-only client_id."""
        payload = {"client_id": "   "}
        response = test_client.post("/api/v1/auth/token", json=payload)

        assert response.status_code == 400

    def test_auth_token_uses_default_expiration(self, test_client):
        """Verify token uses default 60 minute expiration when not specified."""
        payload = {"client_id": "test-client"}
        response = test_client.post("/api/v1/auth/token", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["expires_in"] == 3600  # Default 60 minutes

    @pytest.mark.parametrize("expires_minutes,expected_seconds", [
        (1, 60),
        (5, 300),
        (30, 1800),
        (120, 7200),
    ])
    def test_auth_token_respects_expiration_parameter(self, test_client, expires_minutes, expected_seconds):
        """Verify token expiration matches requested expires_in_minutes."""
        payload = {"client_id": "test-client", "expires_in_minutes": expires_minutes}
        response = test_client.post("/api/v1/auth/token", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["expires_in"] == expected_seconds

    def test_auth_token_generated_token_is_valid_jwt(self, test_client):
        """Verify generated token is valid JWT format."""
        payload = {"client_id": "test-client"}
        response = test_client.post("/api/v1/auth/token", json=payload)

        assert response.status_code == 201
        data = response.json()
        token = data["access_token"]

        # JWT should have 3 parts separated by dots
        assert token.count(".") == 2


class TestDetectionEndpointWithAuth:
    """Tests for POST /api/v1/detections endpoint authentication.

    Test Budget: 3 distinct behaviors x 2 = 6 unit tests max
    Behaviors:
    1. Reject request without Authorization header
    2. Reject request with invalid token
    3. Accept request with valid token
    """

    def test_detection_endpoint_rejects_missing_auth_header(self, test_client):
        """Verify detection endpoint rejects request without Authorization header."""
        payload = {
            "source": "test_source",
            "latitude": 40.0,
            "longitude": -74.0,
            "accuracy_meters": 100,
            "confidence": 0.9,
            "class": "fire",
            "timestamp": "2026-02-15T12:00:00Z"
        }
        response = test_client.post("/api/v1/detections", json=payload)

        assert response.status_code == 401

    def test_detection_endpoint_rejects_invalid_token(self, test_client):
        """Verify detection endpoint rejects invalid JWT token."""
        payload = {
            "source": "test_source",
            "latitude": 40.0,
            "longitude": -74.0,
            "accuracy_meters": 100,
            "confidence": 0.9,
            "class": "fire",
            "timestamp": "2026-02-15T12:00:00Z"
        }
        headers = {"Authorization": "Bearer invalid.token.here"}
        response = test_client.post("/api/v1/detections", json=payload, headers=headers)

        assert response.status_code == 401

    def test_detection_endpoint_rejects_malformed_auth_header(self, test_client):
        """Verify detection endpoint rejects malformed Authorization header."""
        payload = {
            "source": "test_source",
            "latitude": 40.0,
            "longitude": -74.0,
            "accuracy_meters": 100,
            "confidence": 0.9,
            "class": "fire",
            "timestamp": "2026-02-15T12:00:00Z"
        }
        headers = {"Authorization": "not-bearer-format"}
        response = test_client.post("/api/v1/detections", json=payload, headers=headers)

        assert response.status_code == 401

    def test_detection_endpoint_accepts_valid_jwt(self, test_client):
        """Verify detection endpoint accepts request with valid JWT token."""
        # First, get a token
        token_payload = {"client_id": "test-client"}
        token_response = test_client.post("/api/v1/auth/token", json=token_payload)
        assert token_response.status_code == 201
        token = token_response.json()["access_token"]

        # Now use the token to call detection endpoint
        detection_payload = {
            "source": "test_source",
            "latitude": 40.0,
            "longitude": -74.0,
            "accuracy_meters": 100,
            "confidence": 0.9,
            "class": "fire",
            "timestamp": "2026-02-15T12:00:00Z"
        }
        headers = {"Authorization": f"Bearer {token}"}
        response = test_client.post("/api/v1/detections", json=detection_payload, headers=headers)

        # Should not return 401 (either 201 on success or 500 if service error)
        assert response.status_code != 401

    def test_detection_endpoint_rejects_bearer_without_token(self, test_client):
        """Verify detection endpoint rejects 'Bearer' without actual token."""
        payload = {
            "source": "test_source",
            "latitude": 40.0,
            "longitude": -74.0,
            "accuracy_meters": 100,
            "confidence": 0.9,
            "class": "fire",
            "timestamp": "2026-02-15T12:00:00Z"
        }
        headers = {"Authorization": "Bearer"}
        response = test_client.post("/api/v1/detections", json=payload, headers=headers)

        assert response.status_code == 401

    def test_detection_endpoint_case_insensitive_bearer_scheme(self, test_client):
        """Verify detection endpoint accepts case-insensitive Bearer scheme."""
        # First, get a token
        token_payload = {"client_id": "test-client"}
        token_response = test_client.post("/api/v1/auth/token", json=token_payload)
        token = token_response.json()["access_token"]

        # Try with uppercase BEARER
        detection_payload = {
            "source": "test_source",
            "latitude": 40.0,
            "longitude": -74.0,
            "accuracy_meters": 100,
            "confidence": 0.9,
            "class": "fire",
            "timestamp": "2026-02-15T12:00:00Z"
        }
        headers = {"Authorization": f"BEARER {token}"}
        response = test_client.post("/api/v1/detections", json=detection_payload, headers=headers)

        assert response.status_code != 401
