"""Unit tests for JWT authentication service."""
import pytest
from datetime import datetime, timedelta, timezone
from src.services.jwt_service import JWTService


class TestJWTService:
    """Tests for JWT service functionality.

    Test Budget: 4 distinct behaviors x 2 = 8 unit tests max
    Behaviors:
    1. Generate valid JWT token with correct claims
    2. Verify token and extract claims
    3. Reject expired tokens
    4. Reject invalid tokens
    """

    def test_jwt_service_generates_token_with_subject(self):
        """Verify JWT service generates token with subject claim."""
        service = JWTService(secret_key="test-secret")
        token = service.generate_token(subject="client-123", expires_in_minutes=60)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
        assert token.count(".") == 2  # JWT has 3 parts separated by dots

    def test_jwt_service_generates_token_with_expiration(self):
        """Verify JWT token includes expiration claim."""
        service = JWTService(secret_key="test-secret")
        token = service.generate_token(subject="client-123", expires_in_minutes=30)
        payload = service.verify_token(token)

        assert "exp" in payload
        assert payload["exp"] > datetime.now(timezone.utc).timestamp()

    def test_jwt_service_verifies_valid_token(self):
        """Verify JWT service can decode and verify valid token."""
        service = JWTService(secret_key="test-secret")
        subject = "client-123"
        token = service.generate_token(subject=subject, expires_in_minutes=60)
        payload = service.verify_token(token)

        assert payload["sub"] == subject
        assert "iat" in payload
        assert "exp" in payload

    def test_jwt_service_rejects_empty_subject(self):
        """Verify JWT service rejects empty subject."""
        service = JWTService(secret_key="test-secret")

        with pytest.raises(ValueError, match="Subject cannot be empty"):
            service.generate_token(subject="", expires_in_minutes=60)

    def test_jwt_service_rejects_none_subject(self):
        """Verify JWT service rejects None subject."""
        service = JWTService(secret_key="test-secret")

        with pytest.raises(ValueError, match="Subject cannot be empty"):
            service.generate_token(subject=None, expires_in_minutes=60)

    def test_jwt_service_rejects_empty_token(self):
        """Verify JWT service rejects empty token."""
        service = JWTService(secret_key="test-secret")

        with pytest.raises(ValueError, match="Token cannot be empty"):
            service.verify_token("")

    def test_jwt_service_rejects_invalid_token_format(self):
        """Verify JWT service rejects malformed token."""
        service = JWTService(secret_key="test-secret")

        with pytest.raises(ValueError, match="Invalid token"):
            service.verify_token("not.a.valid.token.format")

    def test_jwt_service_rejects_token_signed_with_different_key(self):
        """Verify JWT service rejects token signed with different key."""
        service1 = JWTService(secret_key="secret-1")
        service2 = JWTService(secret_key="secret-2")

        token = service1.generate_token(subject="client-123", expires_in_minutes=60)

        with pytest.raises(ValueError, match="Invalid token"):
            service2.verify_token(token)

    def test_jwt_service_includes_additional_claims(self):
        """Verify JWT service includes additional custom claims."""
        service = JWTService(secret_key="test-secret")
        additional = {"scope": "api", "role": "admin"}
        token = service.generate_token(
            subject="client-123",
            expires_in_minutes=60,
            additional_claims=additional
        )
        payload = service.verify_token(token)

        assert payload["scope"] == "api"
        assert payload["role"] == "admin"

    def test_jwt_service_extracts_subject_from_token(self):
        """Verify JWT service can extract subject from token."""
        service = JWTService(secret_key="test-secret")
        subject = "client-456"
        token = service.generate_token(subject=subject, expires_in_minutes=60)
        extracted = service.extract_subject(token)

        assert extracted == subject

    def test_jwt_service_uses_default_secret_from_env(self, monkeypatch):
        """Verify JWT service uses JWT_SECRET_KEY env var as default."""
        monkeypatch.setenv("JWT_SECRET_KEY", "env-secret-key")
        service = JWTService()

        token = service.generate_token(subject="client-789", expires_in_minutes=60)
        payload = service.verify_token(token)

        assert payload["sub"] == "client-789"

    def test_jwt_service_supports_custom_algorithm(self):
        """Verify JWT service can be configured with custom algorithm."""
        service = JWTService(secret_key="test-secret", algorithm="HS512")
        token = service.generate_token(subject="client-123", expires_in_minutes=60)

        # Should verify successfully with HS512
        payload = service.verify_token(token)
        assert payload["sub"] == "client-123"

    @pytest.mark.parametrize("expires_minutes", [1, 5, 30, 60, 120, 1440])
    def test_jwt_service_respects_expiration_minutes(self, expires_minutes):
        """Verify JWT token expiration time matches requested minutes."""
        service = JWTService(secret_key="test-secret")
        before = datetime.now(timezone.utc).timestamp()
        token = service.generate_token(subject="client-123", expires_in_minutes=expires_minutes)
        after = datetime.now(timezone.utc).timestamp()
        payload = service.verify_token(token)

        exp_timestamp = payload["exp"]
        expected_min = before + (expires_minutes * 60)
        expected_max = after + (expires_minutes * 60)

        assert expected_min <= exp_timestamp <= expected_max
