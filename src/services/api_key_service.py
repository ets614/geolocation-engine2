"""API key management service for machine-to-machine authentication."""
import hashlib
import os
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Set


class APIKeyScope(str, Enum):
    """Scopes that restrict API key access to specific endpoints."""
    READ_DETECTIONS = "read:detections"
    WRITE_DETECTIONS = "write:detections"
    READ_AUDIT = "read:audit"
    ADMIN = "admin"


@dataclass
class APIKeyRecord:
    """Stored API key record (key stored as hash, never plaintext)."""
    key_id: str
    key_hash: str
    client_name: str
    scopes: Set[str]
    created_at: datetime
    expires_at: Optional[datetime] = None
    revoked: bool = False
    revoked_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None


class APIKeyService:
    """Service for API key generation, validation, and lifecycle management.

    Keys are stored hashed using SHA-256. The plaintext key is returned
    only once at creation time and never stored.
    """

    KEY_PREFIX = "geo_"
    KEY_BYTE_LENGTH = 32

    def __init__(self, store: Optional[Dict[str, APIKeyRecord]] = None):
        """Initialize API key service.

        Args:
            store: Optional external store. Defaults to in-memory dict.
        """
        self._store: Dict[str, APIKeyRecord] = store if store is not None else {}

    @staticmethod
    def _hash_key(plaintext_key: str) -> str:
        """Hash an API key using SHA-256.

        Args:
            plaintext_key: The raw API key string.

        Returns:
            Hex-encoded SHA-256 hash.
        """
        return hashlib.sha256(plaintext_key.encode("utf-8")).hexdigest()

    def generate_key(
        self,
        client_name: str,
        scopes: Optional[Set[str]] = None,
        expires_at: Optional[datetime] = None,
    ) -> tuple:
        """Generate a new API key for a client.

        Args:
            client_name: Human-readable name for the key owner.
            scopes: Set of permission scopes. Defaults to read-only.
            expires_at: Optional expiration datetime (UTC).

        Returns:
            Tuple of (plaintext_key, key_id) -- plaintext returned only once.

        Raises:
            ValueError: If client_name is empty.
        """
        if not client_name or not client_name.strip():
            raise ValueError("client_name is required")

        if scopes is None:
            scopes = {APIKeyScope.READ_DETECTIONS.value}

        # Generate cryptographically secure random key
        random_bytes = secrets.token_hex(self.KEY_BYTE_LENGTH)
        plaintext_key = f"{self.KEY_PREFIX}{random_bytes}"

        key_id = secrets.token_hex(8)
        key_hash = self._hash_key(plaintext_key)

        record = APIKeyRecord(
            key_id=key_id,
            key_hash=key_hash,
            client_name=client_name,
            scopes=scopes,
            created_at=datetime.now(timezone.utc),
            expires_at=expires_at,
        )

        self._store[key_id] = record
        return plaintext_key, key_id

    def validate_key(self, plaintext_key: str) -> APIKeyRecord:
        """Validate an API key and return its record.

        Args:
            plaintext_key: The raw API key to validate.

        Returns:
            APIKeyRecord for the valid key.

        Raises:
            ValueError: If key is invalid, expired, or revoked.
        """
        if not plaintext_key:
            raise ValueError("API key is required")

        key_hash = self._hash_key(plaintext_key)

        # Find matching record by hash
        for record in self._store.values():
            if record.key_hash == key_hash:
                if record.revoked:
                    raise ValueError("API key has been revoked")
                if record.expires_at and record.expires_at < datetime.now(timezone.utc):
                    raise ValueError("API key has expired")

                # Update last used timestamp
                record.last_used_at = datetime.now(timezone.utc)
                return record

        raise ValueError("Invalid API key")

    def has_scope(self, plaintext_key: str, required_scope: str) -> bool:
        """Check if an API key has a specific scope.

        Args:
            plaintext_key: The raw API key.
            required_scope: The scope to check.

        Returns:
            True if key has the scope or ADMIN scope.
        """
        record = self.validate_key(plaintext_key)
        return (
            required_scope in record.scopes
            or APIKeyScope.ADMIN.value in record.scopes
        )

    def revoke_key(self, key_id: str) -> bool:
        """Revoke an API key by its ID.

        Args:
            key_id: The key identifier.

        Returns:
            True if key was revoked.

        Raises:
            ValueError: If key_id not found.
        """
        if key_id not in self._store:
            raise ValueError(f"Key ID '{key_id}' not found")

        record = self._store[key_id]
        record.revoked = True
        record.revoked_at = datetime.now(timezone.utc)
        return True

    def rotate_key(self, key_id: str) -> tuple:
        """Rotate an API key: revoke old, generate new with same config.

        Args:
            key_id: The key identifier to rotate.

        Returns:
            Tuple of (new_plaintext_key, new_key_id).

        Raises:
            ValueError: If key_id not found.
        """
        if key_id not in self._store:
            raise ValueError(f"Key ID '{key_id}' not found")

        old_record = self._store[key_id]

        # Revoke old key
        old_record.revoked = True
        old_record.revoked_at = datetime.now(timezone.utc)

        # Generate new key with same config
        return self.generate_key(
            client_name=old_record.client_name,
            scopes=old_record.scopes,
            expires_at=old_record.expires_at,
        )

    def list_keys(self, include_revoked: bool = False) -> List[APIKeyRecord]:
        """List all API keys.

        Args:
            include_revoked: Include revoked keys in listing.

        Returns:
            List of APIKeyRecord (without plaintext keys).
        """
        records = list(self._store.values())
        if not include_revoked:
            records = [r for r in records if not r.revoked]
        return records
