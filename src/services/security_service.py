"""Security hardening service: CORS, headers, secrets, and audit logging."""
import hashlib
import logging
import os
import re
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class SecurityEventType(str, Enum):
    """Types of security-relevant events."""
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILURE = "auth_failure"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    INVALID_INPUT = "invalid_input"
    KEY_GENERATED = "key_generated"
    KEY_REVOKED = "key_revoked"
    SUSPICIOUS_REQUEST = "suspicious_request"
    CONFIG_CHANGE = "config_change"


@dataclass
class SecurityEvent:
    """Immutable record of a security-relevant event."""
    event_type: SecurityEventType
    timestamp: datetime
    client_id: Optional[str]
    source_ip: Optional[str]
    details: Dict[str, Any]
    severity: str = "INFO"


class SecurityAuditLog:
    """Append-only security audit log for sensitive operations.

    Events are stored in-memory for the process lifetime and can be
    drained to a persistent store via flush().
    """

    def __init__(self, max_events: int = 10000):
        self._events: List[SecurityEvent] = []
        self.max_events = max_events

    def log_event(
        self,
        event_type: SecurityEventType,
        client_id: Optional[str] = None,
        source_ip: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        severity: str = "INFO",
    ) -> SecurityEvent:
        """Record a security event.

        Args:
            event_type: Type of event.
            client_id: Authenticated client identity.
            source_ip: Request source IP.
            details: Additional context.
            severity: INFO, WARNING, or ERROR.

        Returns:
            The recorded event.
        """
        event = SecurityEvent(
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            client_id=client_id,
            source_ip=source_ip,
            details=details or {},
            severity=severity,
        )

        self._events.append(event)

        # Evict oldest if over limit
        if len(self._events) > self.max_events:
            self._events = self._events[-self.max_events:]

        # Also write to structured logger
        logger.log(
            logging.WARNING if severity == "WARNING" else
            logging.ERROR if severity == "ERROR" else
            logging.INFO,
            "Security event: %s client=%s ip=%s details=%s",
            event_type.value,
            client_id,
            source_ip,
            details,
        )

        return event

    def get_events(
        self,
        event_type: Optional[SecurityEventType] = None,
        client_id: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> List[SecurityEvent]:
        """Query security events with optional filters.

        Args:
            event_type: Filter by event type.
            client_id: Filter by client.
            since: Only events after this timestamp.

        Returns:
            Matching events in chronological order.
        """
        results = self._events
        if event_type:
            results = [e for e in results if e.event_type == event_type]
        if client_id:
            results = [e for e in results if e.client_id == client_id]
        if since:
            results = [e for e in results if e.timestamp >= since]
        return results

    def count_events(
        self,
        event_type: SecurityEventType,
        client_id: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> int:
        """Count security events matching filters."""
        return len(self.get_events(event_type, client_id, since))

    def flush(self) -> List[SecurityEvent]:
        """Drain all events (for persistence to external store).

        Returns:
            All events, clearing internal buffer.
        """
        events = self._events.copy()
        self._events.clear()
        return events


@dataclass
class SecurityHeadersConfig:
    """Configuration for HTTP security headers."""
    content_security_policy: str = "default-src 'self'"
    x_content_type_options: str = "nosniff"
    x_frame_options: str = "DENY"
    x_xss_protection: str = "1; mode=block"
    strict_transport_security: str = "max-age=31536000; includeSubDomains"
    referrer_policy: str = "strict-origin-when-cross-origin"
    permissions_policy: str = "camera=(), microphone=(), geolocation=()"


class SecurityHeadersService:
    """Service for applying HTTP security headers to responses."""

    def __init__(self, config: Optional[SecurityHeadersConfig] = None):
        self.config = config or SecurityHeadersConfig()

    def get_headers(self) -> Dict[str, str]:
        """Return security headers as a dictionary.

        Returns:
            Dict of header name -> value.
        """
        return {
            "Content-Security-Policy": self.config.content_security_policy,
            "X-Content-Type-Options": self.config.x_content_type_options,
            "X-Frame-Options": self.config.x_frame_options,
            "X-XSS-Protection": self.config.x_xss_protection,
            "Strict-Transport-Security": self.config.strict_transport_security,
            "Referrer-Policy": self.config.referrer_policy,
            "Permissions-Policy": self.config.permissions_policy,
        }


class SecretsManager:
    """Manage application secrets from environment variables.

    Never stores secrets in code. All secrets are read from environment
    at initialization and validated.
    """

    REQUIRED_SECRETS = ["JWT_SECRET_KEY"]
    OPTIONAL_SECRETS = ["REDIS_URL", "DATABASE_URL", "TAK_SERVER_URL"]

    def __init__(self):
        self._secrets: Dict[str, str] = {}
        self._load_from_environment()

    def _load_from_environment(self) -> None:
        """Load secrets from environment variables."""
        for name in self.REQUIRED_SECRETS + self.OPTIONAL_SECRETS:
            value = os.getenv(name)
            if value:
                self._secrets[name] = value

    def get_secret(self, name: str) -> Optional[str]:
        """Get a secret value.

        Args:
            name: Secret name (environment variable name).

        Returns:
            Secret value or None.
        """
        return self._secrets.get(name)

    def validate_required_secrets(self) -> List[str]:
        """Check that all required secrets are configured.

        Returns:
            List of missing required secrets (empty = all present).
        """
        missing = []
        for name in self.REQUIRED_SECRETS:
            if name not in self._secrets:
                missing.append(name)
        return missing

    def is_production_safe(self) -> bool:
        """Check if secrets configuration is production-ready.

        Returns:
            True if no default/weak secrets are in use.
        """
        jwt_key = self._secrets.get("JWT_SECRET_KEY", "")
        # Check for known development defaults
        unsafe_values = [
            "your-secret-key-change-in-production",
            "secret",
            "password",
            "test",
            "development",
        ]
        if jwt_key.lower() in unsafe_values:
            return False
        if len(jwt_key) < 32:
            return False
        return True


class CORSConfig:
    """CORS configuration with strict origin validation."""

    def __init__(
        self,
        allowed_origins: Optional[List[str]] = None,
        allow_credentials: bool = True,
        allowed_methods: Optional[List[str]] = None,
        allowed_headers: Optional[List[str]] = None,
        max_age: int = 3600,
    ):
        self.allowed_origins = allowed_origins or ["http://localhost:3000"]
        self.allow_credentials = allow_credentials
        self.allowed_methods = allowed_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.allowed_headers = allowed_headers or [
            "Authorization", "Content-Type", "X-API-Key", "X-Request-ID"
        ]
        self.max_age = max_age

    def is_origin_allowed(self, origin: str) -> bool:
        """Check if an origin is in the allowed list.

        Args:
            origin: The Origin header value.

        Returns:
            True if origin is allowed.
        """
        if "*" in self.allowed_origins:
            return True
        return origin in self.allowed_origins

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for middleware configuration."""
        return {
            "allow_origins": self.allowed_origins,
            "allow_credentials": self.allow_credentials,
            "allow_methods": self.allowed_methods,
            "allow_headers": self.allowed_headers,
            "max_age": self.max_age,
        }
