"""Acceptance tests for JWT authentication with RS256 and refresh tokens (Phase 04)."""
import pytest
from fastapi.testclient import TestClient
from src.main import app
import jwt as pyjwt


@pytest.fixture
def test_client():
    """Create test client."""
    return TestClient(app)


class TestJWTAuthenticationAcceptance:
    """Acceptance tests for JWT authentication system.

    Test Budget: 8 distinct behaviors (acceptance level)
    Behaviors:
    1. Obtain JWT access and refresh tokens with RS256
    2. Use access token to access protected endpoint
    3. Refresh expired access token with rotation
    4. Verify token validity
    5. Reject expired access token
    6. Reject invalid token signature
    7. Reject reused refresh token
    8. Reject missing Authorization header
    """

    def test_client_obtains_jwt_access_and_refresh_tokens_with_rs256(self, test_client):
        """
        ACCEPTANCE TEST: Client obtains JWT access and refresh tokens.

        Given the JWT service is configured with RS256 algorithm
        When I request a token with client_id "test-client-001"
        Then I should receive an HTTP 201 response
        And the response should contain an access_token with 15-minute expiration
        And the response should contain a refresh_token with 7-day expiration
        And the access_token should be signed with RS256 algorithm
        And the refresh_token should be signed with RS256 algorithm
        """
        # When: Request token
        payload = {"client_id": "test-client-001"}
        response = test_client.post("/api/v1/auth/token", json=payload)

        # Then: Verify HTTP 201
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

        data = response.json()

        # Then: Verify access_token exists with 15-min expiration
        assert "access_token" in data, "Response missing access_token"
        assert data["access_token"], "access_token is empty"
        assert "expires_in" in data, "Response missing expires_in"
        assert data["expires_in"] == 900, f"Expected 900 seconds (15 min), got {data['expires_in']}"

        # Then: Verify refresh_token exists with 7-day expiration
        assert "refresh_token" in data, "Response missing refresh_token"
        assert data["refresh_token"], "refresh_token is empty"
        assert "refresh_expires_in" in data, "Response missing refresh_expires_in"
        assert data["refresh_expires_in"] == 604800, (
            f"Expected 604800 seconds (7 days), got {data['refresh_expires_in']}"
        )

        # Then: Verify access_token uses RS256
        access_header = pyjwt.get_unverified_header(data["access_token"])
        assert access_header["alg"] == "RS256", (
            f"Expected RS256 algorithm for access_token, got {access_header['alg']}"
        )

        # Then: Verify refresh_token uses RS256
        refresh_header = pyjwt.get_unverified_header(data["refresh_token"])
        assert refresh_header["alg"] == "RS256", (
            f"Expected RS256 algorithm for refresh_token, got {refresh_header['alg']}"
        )

    @pytest.mark.skip("Phase 2: Will be implemented after token generation works")
    def test_client_uses_access_token_to_access_protected_endpoint(self, test_client):
        """
        ACCEPTANCE TEST: Client uses access token to access protected endpoint.

        Given I have a valid access token for client "test-client-002"
        When I call POST /api/v1/detections with the access token
        And the detection payload is valid
        Then I should receive an HTTP 201 response
        And the detection should be processed successfully
        """
        # Given: Obtain valid access token
        token_response = test_client.post(
            "/api/v1/auth/token",
            json={"client_id": "test-client-002"}
        )
        assert token_response.status_code == 201
        access_token = token_response.json()["access_token"]

        # When: Call detection endpoint with token
        headers = {"Authorization": f"Bearer {access_token}"}
        detection_payload = {
            "source": "test_source",
            "latitude": 40.0,
            "longitude": -74.0,
            "accuracy_meters": 100,
            "confidence": 0.9,
            "class": "fire",
            "timestamp": "2026-02-15T12:00:00Z"
        }
        response = test_client.post(
            "/api/v1/detections",
            json=detection_payload,
            headers=headers
        )

        # Then: Should not receive 401 (authentication failure)
        assert response.status_code != 401, "Authentication failed with valid token"

    @pytest.mark.skip("Phase 2: Will be implemented after token generation works")
    def test_client_refreshes_expired_access_token_with_rotation(self, test_client):
        """
        ACCEPTANCE TEST: Client refreshes expired access token.

        Given I have a valid refresh token for client "test-client-003"
        When I call POST /api/v1/auth/refresh with the refresh token
        Then I should receive an HTTP 200 response
        And I should receive a new access_token with 15-minute expiration
        And I should receive a new refresh_token with 7-day expiration
        And the old refresh_token should be invalidated
        """
        # Given: Obtain tokens
        token_response = test_client.post(
            "/api/v1/auth/token",
            json={"client_id": "test-client-003"}
        )
        assert token_response.status_code == 201
        old_refresh_token = token_response.json()["refresh_token"]

        # When: Refresh token
        refresh_response = test_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": old_refresh_token}
        )

        # Then: Verify success
        assert refresh_response.status_code == 200
        refresh_data = refresh_response.json()

        # Then: Verify new access token
        assert "access_token" in refresh_data
        assert refresh_data["expires_in"] == 900

        # Then: Verify new refresh token (different from old one)
        assert "refresh_token" in refresh_data
        assert refresh_data["refresh_token"] != old_refresh_token
        assert refresh_data["refresh_expires_in"] == 604800

        # Then: Verify old refresh token is invalidated
        retry_response = test_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": old_refresh_token}
        )
        assert retry_response.status_code == 401, "Old refresh token should be invalid"

    @pytest.mark.skip("Phase 2: Will be implemented after token generation works")
    def test_system_verifies_token_validity(self, test_client):
        """
        ACCEPTANCE TEST: System verifies token validity.

        Given I have a valid access token for client "test-client-004"
        When I call POST /api/v1/auth/verify with the access token
        Then I should receive an HTTP 200 response
        And the response should confirm the token is valid
        And the response should include the client_id claim
        """
        # Given: Obtain valid token
        token_response = test_client.post(
            "/api/v1/auth/token",
            json={"client_id": "test-client-004"}
        )
        access_token = token_response.json()["access_token"]

        # When: Verify token
        verify_response = test_client.post(
            "/api/v1/auth/verify",
            json={"token": access_token}
        )

        # Then: Verify response
        assert verify_response.status_code == 200
        verify_data = verify_response.json()
        assert verify_data["valid"] is True
        assert verify_data["client_id"] == "test-client-004"

    @pytest.mark.skip("Phase 2: Will be implemented after token generation works")
    def test_system_rejects_expired_access_token(self, test_client):
        """
        ACCEPTANCE TEST: System rejects expired access token.

        Given I have an expired access token
        When I call POST /api/v1/detections with the expired token
        Then I should receive an HTTP 401 response
        And the error message should indicate "Token has expired"
        """
        # This test will need special setup to create an expired token
        pass

    @pytest.mark.skip("Phase 2: Will be implemented after token generation works")
    def test_system_rejects_invalid_token_signature(self, test_client):
        """
        ACCEPTANCE TEST: System rejects invalid token signature.

        Given I have a token signed with wrong private key
        When I call POST /api/v1/detections with the invalid token
        Then I should receive an HTTP 401 response
        And the error message should indicate "Invalid token signature"
        """
        pass

    @pytest.mark.skip("Phase 2: Will be implemented after token generation works")
    def test_system_rejects_reused_refresh_token(self, test_client):
        """
        ACCEPTANCE TEST: System rejects reused refresh token.

        Given I have a refresh token that was already used once
        When I call POST /api/v1/auth/refresh with the used token
        Then I should receive an HTTP 401 response
        And the error message should indicate "Refresh token already used"
        """
        pass

    @pytest.mark.skip("Phase 2: Will be implemented after token generation works")
    def test_system_rejects_missing_authorization_header(self, test_client):
        """
        ACCEPTANCE TEST: System rejects missing Authorization header.

        When I call POST /api/v1/detections without Authorization header
        Then I should receive an HTTP 401 response
        And the error message should indicate "Missing authorization header"
        """
        detection_payload = {
            "source": "test_source",
            "latitude": 40.0,
            "longitude": -74.0,
            "accuracy_meters": 100,
            "confidence": 0.9,
            "class": "fire",
            "timestamp": "2026-02-15T12:00:00Z"
        }
        response = test_client.post("/api/v1/detections", json=detection_payload)
        assert response.status_code == 401
        assert "missing authorization header" in response.json()["detail"].lower()
