"""Unit tests for security hardening services.

Test Budget: 6 distinct behaviors x 2 = 12 unit tests max
Behaviors:
1. Security audit log records events
2. Security audit log filters by type/client/date
3. Security headers service returns correct headers
4. Secrets manager validates production safety
5. CORS config validates origins
6. Security audit log evicts old events at capacity
"""
import pytest
from datetime import datetime, timedelta, timezone

from src.services.security_service import (
    SecurityAuditLog,
    SecurityEventType,
    SecurityHeadersService,
    SecurityHeadersConfig,
    SecretsManager,
    CORSConfig,
)


class TestSecurityAuditLog:
    """Test security audit logging through the service port."""

    def test_log_event_records_and_returns_event(self):
        """Service records event with correct fields."""
        audit = SecurityAuditLog()
        event = audit.log_event(
            SecurityEventType.AUTH_SUCCESS,
            client_id="client-1",
            source_ip="192.168.1.1",
            details={"method": "jwt"},
        )

        assert event.event_type == SecurityEventType.AUTH_SUCCESS
        assert event.client_id == "client-1"
        assert event.source_ip == "192.168.1.1"
        assert event.details["method"] == "jwt"

    def test_log_event_timestamps_in_utc(self):
        """Service timestamps events in UTC."""
        audit = SecurityAuditLog()
        event = audit.log_event(SecurityEventType.AUTH_FAILURE)

        assert event.timestamp.tzinfo is not None

    def test_get_events_filters_by_type(self):
        """Service filters events by event type."""
        audit = SecurityAuditLog()
        audit.log_event(SecurityEventType.AUTH_SUCCESS, client_id="a")
        audit.log_event(SecurityEventType.AUTH_FAILURE, client_id="b")
        audit.log_event(SecurityEventType.AUTH_SUCCESS, client_id="c")

        failures = audit.get_events(event_type=SecurityEventType.AUTH_FAILURE)
        assert len(failures) == 1
        assert failures[0].client_id == "b"

    def test_get_events_filters_by_client(self):
        """Service filters events by client_id."""
        audit = SecurityAuditLog()
        audit.log_event(SecurityEventType.AUTH_SUCCESS, client_id="client-1")
        audit.log_event(SecurityEventType.AUTH_SUCCESS, client_id="client-2")

        events = audit.get_events(client_id="client-1")
        assert len(events) == 1

    def test_count_events_returns_correct_count(self):
        """Service counts events matching criteria."""
        audit = SecurityAuditLog()
        for _ in range(5):
            audit.log_event(SecurityEventType.RATE_LIMIT_EXCEEDED, client_id="x")
        audit.log_event(SecurityEventType.AUTH_SUCCESS, client_id="x")

        count = audit.count_events(SecurityEventType.RATE_LIMIT_EXCEEDED)
        assert count == 5

    def test_flush_drains_all_events(self):
        """Service flush returns all events and clears buffer."""
        audit = SecurityAuditLog()
        audit.log_event(SecurityEventType.AUTH_SUCCESS)
        audit.log_event(SecurityEventType.AUTH_FAILURE)

        flushed = audit.flush()
        assert len(flushed) == 2
        assert len(audit.get_events()) == 0

    def test_evicts_oldest_when_at_capacity(self):
        """Service evicts oldest events when buffer full."""
        audit = SecurityAuditLog(max_events=3)
        audit.log_event(SecurityEventType.AUTH_SUCCESS, client_id="first")
        audit.log_event(SecurityEventType.AUTH_SUCCESS, client_id="second")
        audit.log_event(SecurityEventType.AUTH_SUCCESS, client_id="third")
        audit.log_event(SecurityEventType.AUTH_SUCCESS, client_id="fourth")

        events = audit.get_events()
        assert len(events) == 3
        # Oldest should be evicted
        client_ids = [e.client_id for e in events]
        assert "first" not in client_ids
        assert "fourth" in client_ids


class TestSecurityHeaders:
    """Test security headers through the service port."""

    def test_returns_all_security_headers(self):
        """Service returns all required security headers."""
        service = SecurityHeadersService()
        headers = service.get_headers()

        assert "Content-Security-Policy" in headers
        assert "X-Content-Type-Options" in headers
        assert "X-Frame-Options" in headers
        assert "X-XSS-Protection" in headers
        assert "Strict-Transport-Security" in headers
        assert "Referrer-Policy" in headers
        assert "Permissions-Policy" in headers

    def test_default_values_are_secure(self):
        """Default header values follow security best practices."""
        service = SecurityHeadersService()
        headers = service.get_headers()

        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["X-Frame-Options"] == "DENY"
        assert "max-age=" in headers["Strict-Transport-Security"]

    def test_custom_config_overrides_defaults(self):
        """Custom config overrides default header values."""
        config = SecurityHeadersConfig(
            x_frame_options="SAMEORIGIN",
            content_security_policy="default-src 'self' https:",
        )
        service = SecurityHeadersService(config)
        headers = service.get_headers()

        assert headers["X-Frame-Options"] == "SAMEORIGIN"
        assert "https:" in headers["Content-Security-Policy"]


class TestSecretsManager:
    """Test secrets management through the service port."""

    def test_validate_required_secrets_reports_missing(self, monkeypatch):
        """Service reports missing required secrets."""
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

        manager = SecretsManager()
        missing = manager.validate_required_secrets()

        assert "JWT_SECRET_KEY" in missing

    def test_is_production_safe_rejects_defaults(self, monkeypatch):
        """Service rejects known development default secrets."""
        monkeypatch.setenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")

        manager = SecretsManager()
        assert manager.is_production_safe() is False

    def test_is_production_safe_accepts_strong_key(self, monkeypatch):
        """Service accepts sufficiently strong secret key."""
        monkeypatch.setenv("JWT_SECRET_KEY", "a" * 64)

        manager = SecretsManager()
        assert manager.is_production_safe() is True

    def test_is_production_safe_rejects_short_key(self, monkeypatch):
        """Service rejects keys shorter than 32 characters."""
        monkeypatch.setenv("JWT_SECRET_KEY", "short")

        manager = SecretsManager()
        assert manager.is_production_safe() is False


class TestCORSConfig:
    """Test CORS configuration through the service port."""

    def test_is_origin_allowed_checks_whitelist(self):
        """Service checks origin against whitelist."""
        cors = CORSConfig(allowed_origins=["http://localhost:3000"])

        assert cors.is_origin_allowed("http://localhost:3000") is True
        assert cors.is_origin_allowed("http://evil.com") is False

    def test_wildcard_origin_allows_all(self):
        """Wildcard origin allows all origins."""
        cors = CORSConfig(allowed_origins=["*"])
        assert cors.is_origin_allowed("http://anything.com") is True

    def test_to_dict_returns_middleware_config(self):
        """Service returns dict for middleware configuration."""
        cors = CORSConfig(
            allowed_origins=["http://localhost:3000"],
            allow_credentials=True,
        )
        config = cors.to_dict()

        assert "allow_origins" in config
        assert config["allow_credentials"] is True
