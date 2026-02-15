"""Unit tests for API key management endpoints.

Test Budget: 4 distinct behaviors x 2 = 8 unit tests max
Behaviors:
1. Create API key via POST (requires JWT)
2. List API keys via GET (requires JWT)
3. Revoke API key via DELETE (requires JWT)
4. Reject unauthenticated requests
"""
import pytest
from src.api import routes as routes_module


@pytest.fixture
def valid_auth_headers(test_client):
    """Fixture providing valid JWT authorization headers."""
    token_payload = {"client_id": "test-client"}
    token_response = test_client.post("/api/v1/auth/token", json=token_payload)
    token = token_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def reset_api_key_service():
    """Reset API key service singleton between tests."""
    routes_module._api_key_service = None
    yield
    routes_module._api_key_service = None


class TestCreateAPIKeyEndpoint:
    """Test POST /api/v1/api-keys endpoint."""

    def test_create_api_key_returns_201(self, test_client, valid_auth_headers):
        """Endpoint creates API key and returns 201."""
        response = test_client.post(
            "/api/v1/api-keys",
            json={"client_name": "my-service"},
            headers=valid_auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert "api_key" in data
        assert data["api_key"].startswith("geo_")
        assert "key_id" in data
        assert data["client_name"] == "my-service"

    def test_create_api_key_requires_auth(self, test_client):
        """Endpoint rejects unauthenticated request."""
        response = test_client.post(
            "/api/v1/api-keys",
            json={"client_name": "my-service"},
        )
        assert response.status_code == 401

    def test_create_api_key_rejects_empty_name(self, test_client, valid_auth_headers):
        """Endpoint rejects empty client_name."""
        response = test_client.post(
            "/api/v1/api-keys",
            json={"client_name": ""},
            headers=valid_auth_headers,
        )
        assert response.status_code == 400


class TestListAPIKeysEndpoint:
    """Test GET /api/v1/api-keys endpoint."""

    def test_list_api_keys_returns_200(self, test_client, valid_auth_headers):
        """Endpoint returns list of API keys."""
        # Create a key first
        test_client.post(
            "/api/v1/api-keys",
            json={"client_name": "test-svc"},
            headers=valid_auth_headers,
        )

        response = test_client.get("/api/v1/api-keys", headers=valid_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        # Should not contain plaintext key
        assert "api_key" not in data[0]

    def test_list_api_keys_requires_auth(self, test_client):
        """Endpoint rejects unauthenticated request."""
        response = test_client.get("/api/v1/api-keys")
        assert response.status_code == 401


class TestRevokeAPIKeyEndpoint:
    """Test DELETE /api/v1/api-keys/{key_id} endpoint."""

    def test_revoke_api_key_returns_200(self, test_client, valid_auth_headers):
        """Endpoint revokes key and returns 200."""
        # Create a key
        create_resp = test_client.post(
            "/api/v1/api-keys",
            json={"client_name": "to-revoke"},
            headers=valid_auth_headers,
        )
        key_id = create_resp.json()["key_id"]

        # Revoke it
        response = test_client.delete(
            f"/api/v1/api-keys/{key_id}",
            headers=valid_auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["status"] == "revoked"

    def test_revoke_nonexistent_key_returns_404(self, test_client, valid_auth_headers):
        """Endpoint returns 404 for unknown key_id."""
        response = test_client.delete(
            "/api/v1/api-keys/nonexistent-id",
            headers=valid_auth_headers,
        )
        assert response.status_code == 404
