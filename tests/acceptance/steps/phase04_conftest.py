"""
Phase 04: Security & Performance Hardening - Test Fixtures

Provides fixtures for:
- JWT token generation and verification (driving port: /api/v1/auth/token)
- Sample detection payloads for authenticated submissions
- Rate limiting test helpers
- Load testing client pools
- Cache verification utilities

All tests invoke the system through its driving ports (REST API).
No internal components are accessed directly.
"""

import pytest
import os
import time
import base64
from datetime import datetime, timezone
from typing import Dict, Any, Optional


# ============================================================================
# TEST CONFIGURATION - Phase 04 Security
# ============================================================================

PHASE04_CONFIG = {
    "jwt_secret_key": os.getenv(
        "JWT_SECRET_KEY",
        "your-secret-key-change-in-production"
    ),
    "jwt_algorithm": "HS256",
    "rate_limit_requests_per_minute": 100,
    "rate_limit_burst": 10,
    "cache_ttl_seconds": 300,
    "cache_max_entries": 1000,
    "load_test_concurrent_users": 100,
    "load_test_target_rps": 1000,
    "load_test_p99_latency_ms": 500,
}

# Minimal valid 1x1 PNG image encoded as base64 for test payloads
MINIMAL_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4"
    "2mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


# ============================================================================
# JWT SERVICE FIXTURE
# ============================================================================

@pytest.fixture
def jwt_service():
    """
    Provides a JWTService instance for test token generation.

    Used to create valid, expired, and tampered tokens for
    authentication acceptance tests. This fixture wraps the
    production JWTService to ensure tests exercise the real
    token logic.
    """
    from src.services.jwt_service import JWTService
    return JWTService(
        secret_key=PHASE04_CONFIG["jwt_secret_key"],
        algorithm=PHASE04_CONFIG["jwt_algorithm"],
    )


# ============================================================================
# SAMPLE DETECTION PAYLOAD FIXTURE
# ============================================================================

@pytest.fixture
def sample_detection_payload() -> Dict[str, Any]:
    """
    Provides a complete, valid detection payload for test submissions.

    This payload satisfies all input validation requirements:
    - Valid base64 image data
    - Pixel coordinates within image bounds
    - Valid object class and confidence
    - Valid camera/sensor metadata with coordinates and orientation
    - ISO8601 UTC timestamp

    Returns a new copy each call to prevent cross-test contamination.
    """
    return {
        "image_base64": MINIMAL_PNG_BASE64,
        "pixel_x": 0,
        "pixel_y": 0,
        "object_class": "fire",
        "ai_confidence": 0.92,
        "source": "acceptance-test-sensor",
        "camera_id": "test-cam-001",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sensor_metadata": {
            "location_lat": 32.1200,
            "location_lon": -117.5700,
            "location_elevation": 1000.0,
            "heading": 45.0,
            "pitch": -30.0,
            "roll": 0.0,
            "focal_length": 3000.0,
            "sensor_width_mm": 36.0,
            "sensor_height_mm": 24.0,
            "image_width": 1920,
            "image_height": 1440,
        },
    }


# ============================================================================
# AUTHENTICATED HTTP CLIENT FIXTURE
# ============================================================================

@pytest.fixture
def auth_client(http_client, jwt_service):
    """
    HTTP client pre-configured with a valid JWT token.

    Wraps the base http_client to automatically include
    Authorization headers, simplifying step definitions
    that need authenticated access.
    """
    token = jwt_service.generate_token(
        subject="acceptance-test-user",
        expires_in_minutes=60
    )

    class AuthenticatedClient:
        def __init__(self, client, access_token):
            self._client = client
            self._token = access_token
            self._auth_headers = {"Authorization": f"Bearer {access_token}"}

        def post(self, endpoint, json_data, **kwargs):
            headers = kwargs.pop("headers", {})
            headers.update(self._auth_headers)
            return self._client.post(endpoint, json_data=json_data, headers=headers, **kwargs)

        def get(self, endpoint, **kwargs):
            headers = kwargs.pop("headers", {})
            headers.update(self._auth_headers)
            return self._client.get(endpoint, headers=headers, **kwargs)

        def put(self, endpoint, json_data, **kwargs):
            headers = kwargs.pop("headers", {})
            headers.update(self._auth_headers)
            return self._client.put(endpoint, json_data=json_data, headers=headers, **kwargs)

        @property
        def token(self):
            return self._token

    return AuthenticatedClient(http_client, token)


# ============================================================================
# RATE LIMIT TEST HELPERS
# ============================================================================

@pytest.fixture
def rate_limit_config():
    """Provides rate limit configuration for test assertions."""
    return {
        "requests_per_minute": PHASE04_CONFIG["rate_limit_requests_per_minute"],
        "burst_allowance": PHASE04_CONFIG["rate_limit_burst"],
        "time_window_seconds": 60,
    }


# ============================================================================
# LOAD TEST HELPERS
# ============================================================================

@pytest.fixture
def load_test_config():
    """Provides load test configuration and thresholds."""
    return {
        "concurrent_users": PHASE04_CONFIG["load_test_concurrent_users"],
        "target_rps": PHASE04_CONFIG["load_test_target_rps"],
        "p99_latency_ms": PHASE04_CONFIG["load_test_p99_latency_ms"],
        "p95_latency_ms": 400,
        "p50_latency_ms": 100,
        "max_latency_ms": 2000,
        "min_success_rate": 0.99,
        "max_memory_growth_pct": 10,
    }


# ============================================================================
# PYTEST MARKERS - Phase 04
# ============================================================================

def pytest_configure(config):
    """Register Phase 04 custom markers."""
    config.addinivalue_line("markers", "phase_04: Phase 04 Security & Performance")
    config.addinivalue_line("markers", "security: Security test")
    config.addinivalue_line("markers", "injection: Injection prevention test")
    config.addinivalue_line("markers", "xss: XSS prevention test")
    config.addinivalue_line("markers", "isolation: Multi-user isolation test")
    config.addinivalue_line("markers", "invalidation: Cache invalidation test")
    config.addinivalue_line("markers", "load: Load/performance test")
    config.addinivalue_line("markers", "concurrent: Concurrent user test")
    config.addinivalue_line("markers", "throughput: Throughput test")
    config.addinivalue_line("markers", "latency: Latency test")
    config.addinivalue_line("markers", "resources: Resource utilization test")
    config.addinivalue_line("markers", "resilience: Resilience test")
    config.addinivalue_line("markers", "issue_14: Authentication & Authorization")
    config.addinivalue_line("markers", "issue_15: API Key Management")
    config.addinivalue_line("markers", "issue_16: Rate Limiting")
    config.addinivalue_line("markers", "issue_17: Load Testing")
    config.addinivalue_line("markers", "issue_18: Input Validation")
    config.addinivalue_line("markers", "issue_21: Caching")
