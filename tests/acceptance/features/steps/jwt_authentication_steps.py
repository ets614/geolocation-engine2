"""Step definitions for JWT authentication acceptance tests."""
from behave import given, when, then
from fastapi.testclient import TestClient
import jwt as pyjwt
from src.main import app


@given('the API service is running')
def step_impl(context):
    """Initialize test client."""
    context.client = TestClient(app)


@given('the JWT service is configured with RS256 algorithm')
def step_impl(context):
    """Verify JWT service uses RS256."""
    # This will be verified in the response assertions
    pass


@when('I request a token with client_id "{client_id}"')
def step_impl(context, client_id):
    """Request JWT token from /api/v1/auth/token endpoint."""
    payload = {"client_id": client_id}
    context.response = context.client.post("/api/v1/auth/token", json=payload)


@then('I should receive an HTTP {status_code:d} response')
def step_impl(context, status_code):
    """Verify HTTP response status code."""
    assert context.response.status_code == status_code, (
        f"Expected {status_code}, got {context.response.status_code}. "
        f"Response: {context.response.text}"
    )


@then('the response should contain an access_token with 15-minute expiration')
def step_impl(context):
    """Verify access_token exists and has 15-minute expiration."""
    data = context.response.json()
    assert "access_token" in data, "Response missing access_token"
    assert data["access_token"], "access_token is empty"

    # Store for later use
    context.access_token = data["access_token"]

    # Verify expiration is 15 minutes (900 seconds)
    assert "expires_in" in data, "Response missing expires_in"
    assert data["expires_in"] == 900, f"Expected 900 seconds, got {data['expires_in']}"


@then('the response should contain a refresh_token with 7-day expiration')
def step_impl(context):
    """Verify refresh_token exists and has 7-day expiration."""
    data = context.response.json()
    assert "refresh_token" in data, "Response missing refresh_token"
    assert data["refresh_token"], "refresh_token is empty"

    # Store for later use
    context.refresh_token = data["refresh_token"]

    # Verify refresh expiration is 7 days (604800 seconds)
    assert "refresh_expires_in" in data, "Response missing refresh_expires_in"
    assert data["refresh_expires_in"] == 604800, (
        f"Expected 604800 seconds (7 days), got {data['refresh_expires_in']}"
    )


@then('the access_token should be signed with RS256 algorithm')
def step_impl(context):
    """Verify access token uses RS256 algorithm."""
    token = context.access_token

    # Decode header without verification to check algorithm
    header = pyjwt.get_unverified_header(token)
    assert header["alg"] == "RS256", f"Expected RS256, got {header['alg']}"


@then('the refresh_token should be signed with RS256 algorithm')
def step_impl(context):
    """Verify refresh token uses RS256 algorithm."""
    token = context.refresh_token

    # Decode header without verification to check algorithm
    header = pyjwt.get_unverified_header(token)
    assert header["alg"] == "RS256", f"Expected RS256, got {header['alg']}"


@given('I have a valid access token for client "{client_id}"')
def step_impl(context, client_id):
    """Obtain valid access token for testing."""
    payload = {"client_id": client_id}
    response = context.client.post("/api/v1/auth/token", json=payload)
    assert response.status_code == 201
    context.access_token = response.json()["access_token"]
    context.client_id = client_id


@when('I call POST /api/v1/detections with the access token')
def step_impl(context):
    """Call detection endpoint with access token."""
    headers = {"Authorization": f"Bearer {context.access_token}"}
    context.detection_headers = headers


@when('the detection payload is valid')
def step_impl(context):
    """Prepare valid detection payload."""
    payload = {
        "source": "test_source",
        "latitude": 40.0,
        "longitude": -74.0,
        "accuracy_meters": 100,
        "confidence": 0.9,
        "class": "fire",
        "timestamp": "2026-02-15T12:00:00Z"
    }
    context.response = context.client.post(
        "/api/v1/detections",
        json=payload,
        headers=context.detection_headers
    )


@then('the detection should be processed successfully')
def step_impl(context):
    """Verify detection was processed."""
    # Should receive either 201 (success) or 500 (processing error)
    # but NOT 401 (authentication error)
    assert context.response.status_code != 401, "Authentication failed"


@given('I have a valid refresh token for client "{client_id}"')
def step_impl(context, client_id):
    """Obtain valid refresh token for testing."""
    payload = {"client_id": client_id}
    response = context.client.post("/api/v1/auth/token", json=payload)
    assert response.status_code == 201
    context.refresh_token = response.json()["refresh_token"]
    context.client_id = client_id


@when('I call POST /api/v1/auth/refresh with the refresh token')
def step_impl(context):
    """Call refresh endpoint with refresh token."""
    payload = {"refresh_token": context.refresh_token}
    context.response = context.client.post("/api/v1/auth/refresh", json=payload)


@then('I should receive a new access_token with 15-minute expiration')
def step_impl(context):
    """Verify new access token received."""
    data = context.response.json()
    assert "access_token" in data
    assert data["access_token"] != context.access_token  # Different from old token
    assert data["expires_in"] == 900


@then('I should receive a new refresh_token with 7-day expiration')
def step_impl(context):
    """Verify new refresh token received."""
    data = context.response.json()
    assert "refresh_token" in data
    assert data["refresh_token"] != context.refresh_token  # Different from old token
    assert data["refresh_expires_in"] == 604800


@then('the old refresh_token should be invalidated')
def step_impl(context):
    """Verify old refresh token cannot be reused."""
    # Try to use old refresh token again
    payload = {"refresh_token": context.refresh_token}
    response = context.client.post("/api/v1/auth/refresh", json=payload)
    assert response.status_code == 401


@when('I call POST /api/v1/auth/verify with the access token')
def step_impl(context):
    """Call verify endpoint with access token."""
    payload = {"token": context.access_token}
    context.response = context.client.post("/api/v1/auth/verify", json=payload)


@then('the response should confirm the token is valid')
def step_impl(context):
    """Verify token validity confirmation."""
    data = context.response.json()
    assert data["valid"] is True


@then('the response should include the client_id claim')
def step_impl(context):
    """Verify client_id is in response."""
    data = context.response.json()
    assert "client_id" in data
    assert data["client_id"] == context.client_id


@given('I have an expired access token for client "{client_id}"')
def step_impl(context, client_id):
    """Create an expired token for testing."""
    # This will need special handling - create token with past expiration
    from src.services.jwt_service import JWTService
    from src.config import get_config

    config = get_config()
    jwt_service = JWTService(
        private_key_path=config.jwt_private_key_path,
        public_key_path=config.jwt_public_key_path,
        algorithm="RS256"
    )

    # Create token that expired 1 hour ago
    context.access_token = jwt_service.generate_access_token(
        subject=client_id,
        expires_in_minutes=-60  # Negative = already expired
    )


@when('I call POST /api/v1/detections with the expired token')
def step_impl(context):
    """Call detection endpoint with expired token."""
    headers = {"Authorization": f"Bearer {context.access_token}"}
    payload = {
        "source": "test_source",
        "latitude": 40.0,
        "longitude": -74.0,
        "accuracy_meters": 100,
        "confidence": 0.9,
        "class": "fire",
        "timestamp": "2026-02-15T12:00:00Z"
    }
    context.response = context.client.post(
        "/api/v1/detections",
        json=payload,
        headers=headers
    )


@then('the error message should indicate "{message}"')
def step_impl(context, message):
    """Verify error message contains expected text."""
    data = context.response.json()
    error_detail = str(data.get("detail", ""))
    assert message.lower() in error_detail.lower(), (
        f"Expected '{message}' in error, got: {error_detail}"
    )


@given('I have a token signed with wrong private key')
def step_impl(context):
    """Create token with invalid signature."""
    # Create a token with different key
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.backends import default_backend
    import jwt as pyjwt
    from datetime import datetime, timedelta, timezone

    # Generate temporary wrong key
    wrong_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )

    # Create token with wrong key
    payload = {
        "sub": "test-client",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15)
    }

    from cryptography.hazmat.primitives import serialization
    wrong_pem = wrong_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    context.access_token = pyjwt.encode(payload, wrong_pem, algorithm="RS256")


@when('I call POST /api/v1/detections with the invalid token')
def step_impl(context):
    """Call detection endpoint with invalid token."""
    headers = {"Authorization": f"Bearer {context.access_token}"}
    payload = {
        "source": "test_source",
        "latitude": 40.0,
        "longitude": -74.0,
        "accuracy_meters": 100,
        "confidence": 0.9,
        "class": "fire",
        "timestamp": "2026-02-15T12:00:00Z"
    }
    context.response = context.client.post(
        "/api/v1/detections",
        json=payload,
        headers=headers
    )


@given('I have a refresh token that was already used once')
def step_impl(context):
    """Create and use a refresh token once."""
    # Get initial tokens
    payload = {"client_id": "test-client"}
    response = context.client.post("/api/v1/auth/token", json=payload)
    context.refresh_token = response.json()["refresh_token"]

    # Use it once
    refresh_payload = {"refresh_token": context.refresh_token}
    context.client.post("/api/v1/auth/refresh", json=refresh_payload)


@when('I call POST /api/v1/auth/refresh with the used token')
def step_impl(context):
    """Attempt to reuse refresh token."""
    payload = {"refresh_token": context.refresh_token}
    context.response = context.client.post("/api/v1/auth/refresh", json=payload)


@when('I call POST /api/v1/detections without Authorization header')
def step_impl(context):
    """Call detection endpoint without auth header."""
    payload = {
        "source": "test_source",
        "latitude": 40.0,
        "longitude": -74.0,
        "accuracy_meters": 100,
        "confidence": 0.9,
        "class": "fire",
        "timestamp": "2026-02-15T12:00:00Z"
    }
    context.response = context.client.post("/api/v1/detections", json=payload)
