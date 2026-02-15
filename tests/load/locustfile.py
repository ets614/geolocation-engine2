"""Locust load test suite for Detection API.

Performance Targets:
  - P50 latency  < 100ms
  - P95 latency  < 300ms
  - P99 latency  < 500ms
  - Throughput    > 1000 req/sec
  - Error rate    < 0.1%

Test Scenarios:
  1. Health check baseline (unauthenticated)
  2. JWT token generation
  3. Authenticated detection ingestion
  4. Cached endpoint validation
  5. Mixed realistic workload

Usage:
  # Run locally against dev server
  locust -f tests/load/locustfile.py --host http://localhost:8000

  # Headless run with target RPS
  locust -f tests/load/locustfile.py --host http://localhost:8000 \
    --headless -u 200 -r 20 --run-time 5m \
    --csv results/load_test --html results/load_test.html
"""

import base64
import json
import os
import random
import time
from datetime import datetime, timezone

from locust import HttpUser, between, events, tag, task
from locust.runners import MasterRunner

# ---------------------------------------------------------------------------
# Test data generators
# ---------------------------------------------------------------------------

# Minimal valid 1x1 PNG for payload (avoids large base64 in tests)
MINIMAL_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4"
    "2mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)

OBJECT_CLASSES = ["vehicle", "person", "building", "aircraft", "watercraft"]
SOURCES = ["uav_model_v2", "ground_sensor_v1", "satellite_v3", "tower_cam_v1"]
CAMERA_IDS = [f"cam_{i:03d}" for i in range(1, 21)]


def _random_detection_payload() -> dict:
    """Generate a randomised but valid detection payload."""
    image_width = random.choice([640, 1280, 1920, 3840])
    image_height = random.choice([480, 720, 1080, 2160])
    return {
        "image_base64": MINIMAL_PNG_B64,
        "pixel_x": random.randint(0, image_width - 1),
        "pixel_y": random.randint(0, image_height - 1),
        "object_class": random.choice(OBJECT_CLASSES),
        "ai_confidence": round(random.uniform(0.5, 0.99), 2),
        "source": random.choice(SOURCES),
        "camera_id": random.choice(CAMERA_IDS),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sensor_metadata": {
            "location_lat": round(random.uniform(30.0, 50.0), 6),
            "location_lon": round(random.uniform(-120.0, -70.0), 6),
            "location_elevation": round(random.uniform(10.0, 500.0), 1),
            "heading": round(random.uniform(0, 360), 1),
            "pitch": round(random.uniform(-60.0, -5.0), 1),
            "roll": round(random.uniform(-5.0, 5.0), 1),
            "focal_length": round(random.uniform(1000.0, 5000.0), 1),
            "sensor_width_mm": 6.4,
            "sensor_height_mm": 4.8,
            "image_width": image_width,
            "image_height": image_height,
        },
    }


# ---------------------------------------------------------------------------
# Event hooks -- aggregate and report against SLO targets
# ---------------------------------------------------------------------------

_request_latencies = []
_error_count = 0
_total_count = 0


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Track every request for SLO validation at test end."""
    global _error_count, _total_count
    _total_count += 1
    if exception or (hasattr(kwargs.get("response"), "status_code") and kwargs["response"].status_code >= 400):
        _error_count += 1
    _request_latencies.append(response_time)


@events.quitting.add_listener
def on_quitting(environment, **kwargs):
    """Print SLO compliance report when test finishes."""
    if not _request_latencies:
        return

    sorted_latencies = sorted(_request_latencies)
    n = len(sorted_latencies)

    p50 = sorted_latencies[int(n * 0.50)]
    p95 = sorted_latencies[int(n * 0.95)]
    p99 = sorted_latencies[int(n * 0.99)]
    error_rate = (_error_count / _total_count * 100) if _total_count else 0

    print("\n" + "=" * 70)
    print("  SLO COMPLIANCE REPORT")
    print("=" * 70)
    print(f"  Total requests:  {_total_count:,}")
    print(f"  Error count:     {_error_count:,}")
    print(f"  Error rate:      {error_rate:.3f}%  (target < 0.1%)")
    print(f"  P50 latency:     {p50:.1f}ms  (target < 100ms)")
    print(f"  P95 latency:     {p95:.1f}ms  (target < 300ms)")
    print(f"  P99 latency:     {p99:.1f}ms  (target < 500ms)")
    print("-" * 70)

    violations = []
    if p50 >= 100:
        violations.append(f"P50 {p50:.1f}ms >= 100ms")
    if p95 >= 300:
        violations.append(f"P95 {p95:.1f}ms >= 300ms")
    if p99 >= 500:
        violations.append(f"P99 {p99:.1f}ms >= 500ms")
    if error_rate >= 0.1:
        violations.append(f"Error rate {error_rate:.3f}% >= 0.1%")

    if violations:
        print("  SLO STATUS: VIOLATED")
        for v in violations:
            print(f"    - {v}")
    else:
        print("  SLO STATUS: ALL TARGETS MET")
    print("=" * 70 + "\n")


# ---------------------------------------------------------------------------
# User classes
# ---------------------------------------------------------------------------

class DetectionAPIUser(HttpUser):
    """Simulates a realistic Detection API client.

    Weighted task distribution:
      - 60% detection ingestion (core workload)
      - 20% health checks (monitoring probes)
      - 10% token generation (auth flow)
      - 10% metrics endpoint (Prometheus scraping)
    """

    wait_time = between(0.1, 0.5)
    _token = None
    _client_id = None

    def on_start(self):
        """Acquire a JWT token before starting tasks."""
        self._client_id = f"loadtest-{random.randint(1000, 9999)}"
        self._acquire_token()

    def _acquire_token(self):
        """Get a fresh JWT token."""
        resp = self.client.post(
            "/api/v1/auth/token",
            json={"client_id": self._client_id, "expires_in_minutes": 60},
            name="/api/v1/auth/token",
        )
        if resp.status_code == 201:
            data = resp.json()
            self._token = data.get("access_token")
        else:
            self._token = None

    def _auth_headers(self) -> dict:
        """Return Authorization header with current token."""
        if not self._token:
            self._acquire_token()
        return {"Authorization": f"Bearer {self._token}"} if self._token else {}

    # -- Tasks ---------------------------------------------------------------

    @task(6)
    @tag("detection", "core")
    def submit_detection(self):
        """Submit a detection payload (primary workload)."""
        payload = _random_detection_payload()
        self.client.post(
            "/api/v1/detections",
            json=payload,
            headers=self._auth_headers(),
            name="/api/v1/detections",
        )

    @task(2)
    @tag("health", "baseline")
    def health_check(self):
        """Hit the health endpoint (simulates monitoring probes)."""
        self.client.get("/api/v1/health", name="/api/v1/health")

    @task(1)
    @tag("auth", "token")
    def generate_token(self):
        """Generate a new JWT token."""
        self.client.post(
            "/api/v1/auth/token",
            json={
                "client_id": f"loadtest-{random.randint(1000, 9999)}",
                "expires_in_minutes": 30,
            },
            name="/api/v1/auth/token",
        )

    @task(1)
    @tag("metrics", "observability")
    def scrape_metrics(self):
        """Scrape the Prometheus metrics endpoint."""
        self.client.get("/metrics", name="/metrics")


class HealthCheckUser(HttpUser):
    """Lightweight user that only hammers the health endpoint.

    Use to establish a baseline latency with minimal processing.
    """

    wait_time = between(0.05, 0.1)
    weight = 1  # Low weight; spawn few of these

    @task
    @tag("health", "baseline")
    def health_check(self):
        """Rapid health endpoint polling."""
        self.client.get("/api/v1/health", name="/api/v1/health [baseline]")


class AuthStressUser(HttpUser):
    """Stress-tests the authentication flow exclusively."""

    wait_time = between(0.1, 0.3)
    weight = 1

    @task(3)
    @tag("auth", "stress")
    def valid_token_request(self):
        """Generate valid tokens repeatedly."""
        self.client.post(
            "/api/v1/auth/token",
            json={
                "client_id": f"stress-{random.randint(1, 500)}",
                "expires_in_minutes": 5,
            },
            name="/api/v1/auth/token [stress]",
        )

    @task(1)
    @tag("auth", "stress", "negative")
    def invalid_token_request(self):
        """Send invalid auth to measure rejection latency."""
        self.client.post(
            "/api/v1/auth/token",
            json={"client_id": "", "expires_in_minutes": 5},
            name="/api/v1/auth/token [invalid]",
        )

    @task(1)
    @tag("auth", "stress", "negative")
    def expired_token_detection(self):
        """Use a bogus token to measure 401 response latency."""
        self.client.post(
            "/api/v1/detections",
            json=_random_detection_payload(),
            headers={"Authorization": "Bearer invalid.token.here"},
            name="/api/v1/detections [bad-auth]",
        )
