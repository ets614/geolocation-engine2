"""Unit tests for API key management service.

Test Budget: 6 distinct behaviors x 2 = 12 unit tests max
Behaviors:
1. Generate API key with client name and scopes
2. Validate a valid API key and return record
3. Reject invalid/expired/revoked keys
4. Revoke a key by key_id
5. Rotate a key (revoke old, generate new)
6. List keys with optional revoked filter
"""
import pytest
from datetime import datetime, timedelta, timezone

from src.services.api_key_service import APIKeyService, APIKeyScope


class TestAPIKeyGeneration:
    """Test API key generation through the service port."""

    def test_generate_key_returns_plaintext_and_key_id(self):
        """Service generates key returning (plaintext, key_id) tuple."""
        service = APIKeyService()
        plaintext, key_id = service.generate_key(client_name="test-client")

        assert plaintext.startswith("geo_")
        assert len(plaintext) > 20
        assert len(key_id) == 16  # 8 bytes hex

    def test_generate_key_stores_hashed_not_plaintext(self):
        """Service stores key hash, never plaintext."""
        service = APIKeyService()
        plaintext, key_id = service.generate_key(client_name="test-client")

        record = service._store[key_id]
        assert record.key_hash != plaintext
        assert len(record.key_hash) == 64  # SHA-256 hex

    def test_generate_key_rejects_empty_client_name(self):
        """Service rejects empty client_name."""
        service = APIKeyService()
        with pytest.raises(ValueError, match="client_name is required"):
            service.generate_key(client_name="")

    def test_generate_key_assigns_default_read_scope(self):
        """Service defaults to read:detections scope."""
        service = APIKeyService()
        _, key_id = service.generate_key(client_name="reader")

        record = service._store[key_id]
        assert APIKeyScope.READ_DETECTIONS.value in record.scopes

    def test_generate_key_with_custom_scopes(self):
        """Service assigns requested scopes."""
        service = APIKeyService()
        scopes = {APIKeyScope.WRITE_DETECTIONS.value, APIKeyScope.READ_AUDIT.value}
        _, key_id = service.generate_key(client_name="writer", scopes=scopes)

        record = service._store[key_id]
        assert record.scopes == scopes


class TestAPIKeyValidation:
    """Test API key validation through the service port."""

    def test_validate_valid_key_returns_record(self):
        """Service validates correct key and returns record."""
        service = APIKeyService()
        plaintext, key_id = service.generate_key(client_name="test-client")

        record = service.validate_key(plaintext)
        assert record.key_id == key_id
        assert record.client_name == "test-client"

    def test_validate_key_updates_last_used(self):
        """Service updates last_used_at on successful validation."""
        service = APIKeyService()
        plaintext, _ = service.generate_key(client_name="test-client")

        record = service.validate_key(plaintext)
        assert record.last_used_at is not None

    @pytest.mark.parametrize("bad_key", [
        "",
        "geo_invalid_key_that_does_not_exist",
        "not_even_a_geo_key",
    ])
    def test_validate_rejects_invalid_keys(self, bad_key):
        """Service rejects invalid keys with ValueError."""
        service = APIKeyService()
        service.generate_key(client_name="real-client")

        with pytest.raises(ValueError):
            service.validate_key(bad_key)

    def test_validate_rejects_revoked_key(self):
        """Service rejects key after revocation."""
        service = APIKeyService()
        plaintext, key_id = service.generate_key(client_name="test-client")

        service.revoke_key(key_id)

        with pytest.raises(ValueError, match="revoked"):
            service.validate_key(plaintext)

    def test_validate_rejects_expired_key(self):
        """Service rejects key past expiration."""
        service = APIKeyService()
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        plaintext, _ = service.generate_key(
            client_name="test-client", expires_at=past
        )

        with pytest.raises(ValueError, match="expired"):
            service.validate_key(plaintext)


class TestAPIKeyRevocationAndRotation:
    """Test key lifecycle management through the service port."""

    def test_revoke_key_marks_as_revoked(self):
        """Service marks key as revoked."""
        service = APIKeyService()
        _, key_id = service.generate_key(client_name="test-client")

        result = service.revoke_key(key_id)
        assert result is True
        assert service._store[key_id].revoked is True
        assert service._store[key_id].revoked_at is not None

    def test_revoke_nonexistent_key_raises(self):
        """Service raises ValueError for unknown key_id."""
        service = APIKeyService()
        with pytest.raises(ValueError, match="not found"):
            service.revoke_key("nonexistent-id")

    def test_rotate_key_revokes_old_and_creates_new(self):
        """Service rotation revokes old key and returns new one."""
        service = APIKeyService()
        old_plaintext, old_key_id = service.generate_key(
            client_name="test-client",
            scopes={APIKeyScope.ADMIN.value},
        )

        new_plaintext, new_key_id = service.rotate_key(old_key_id)

        # Old key is revoked
        assert service._store[old_key_id].revoked is True

        # New key is valid with same config
        record = service.validate_key(new_plaintext)
        assert record.client_name == "test-client"
        assert APIKeyScope.ADMIN.value in record.scopes

    def test_has_scope_checks_admin_access(self):
        """Admin scope grants access to all scopes."""
        service = APIKeyService()
        plaintext, _ = service.generate_key(
            client_name="admin", scopes={APIKeyScope.ADMIN.value}
        )

        assert service.has_scope(plaintext, APIKeyScope.READ_DETECTIONS.value) is True
        assert service.has_scope(plaintext, APIKeyScope.WRITE_DETECTIONS.value) is True


class TestAPIKeyListing:
    """Test key listing through the service port."""

    def test_list_keys_excludes_revoked_by_default(self):
        """Service lists only active keys by default."""
        service = APIKeyService()
        _, key_id_1 = service.generate_key(client_name="active")
        _, key_id_2 = service.generate_key(client_name="revoked")
        service.revoke_key(key_id_2)

        keys = service.list_keys()
        assert len(keys) == 1
        assert keys[0].client_name == "active"

    def test_list_keys_includes_revoked_when_requested(self):
        """Service includes revoked keys when include_revoked=True."""
        service = APIKeyService()
        service.generate_key(client_name="active")
        _, key_id = service.generate_key(client_name="revoked")
        service.revoke_key(key_id)

        keys = service.list_keys(include_revoked=True)
        assert len(keys) == 2
