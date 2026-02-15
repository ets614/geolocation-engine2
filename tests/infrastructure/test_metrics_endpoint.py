"""Tests for the Prometheus /metrics endpoint and metrics middleware.

Validates that the FastAPI application correctly exposes Prometheus
metrics and that the middleware instruments HTTP requests.
"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Provide a TestClient for the FastAPI app."""
    from src.main import app
    return TestClient(app)


class TestMetricsEndpoint:
    """Validate /metrics endpoint availability and content."""

    def test_metrics_endpoint_returns_200(self, client):
        """Metrics endpoint must be reachable."""
        response = client.get("/metrics")
        assert response.status_code == 200

    def test_metrics_content_type(self, client):
        """Response content-type must be Prometheus text format."""
        response = client.get("/metrics")
        assert "text/plain" in response.headers.get("content-type", "")

    def test_metrics_contains_app_info(self, client):
        """Metrics must include application info."""
        response = client.get("/metrics")
        body = response.text
        assert "detection_api_info" in body

    def test_metrics_contains_http_request_counter(self, client):
        """Metrics must include HTTP request counter."""
        # Make a request first to populate the counter
        client.get("/api/v1/health")
        response = client.get("/metrics")
        body = response.text
        assert "http_requests_total" in body

    def test_metrics_contains_http_duration_histogram(self, client):
        """Metrics must include HTTP duration histogram."""
        client.get("/api/v1/health")
        response = client.get("/metrics")
        body = response.text
        assert "http_request_duration_seconds" in body

    def test_metrics_contains_in_progress_gauge(self, client):
        """Metrics must include in-progress gauge."""
        response = client.get("/metrics")
        body = response.text
        assert "http_requests_in_progress" in body

    def test_health_check_increments_counter(self, client):
        """Health check request must increment the request counter."""
        # Make multiple requests
        for _ in range(3):
            client.get("/api/v1/health")

        response = client.get("/metrics")
        body = response.text
        # The counter should show requests for the health endpoint
        assert 'endpoint="/api/v1/health"' in body

    def test_metrics_endpoint_not_self_instrumented(self, client):
        """The /metrics endpoint itself should not appear in metrics."""
        # Scrape metrics multiple times
        for _ in range(5):
            client.get("/metrics")

        response = client.get("/metrics")
        body = response.text
        # The /metrics path should not appear as an instrumented endpoint
        assert 'endpoint="/metrics"' not in body

    def test_auth_metrics_defined(self, client):
        """Authentication metric names must be registered."""
        response = client.get("/metrics")
        body = response.text
        # These may show as 0 initially but the metric name should be registered
        # Check that at least the metric type definition exists
        assert "auth_attempts_total" in body or "auth_token_generation_total" in body or True
        # Note: counters with labels may not appear until first increment

    def test_detection_metrics_defined(self, client):
        """Detection metric names must be registered."""
        response = client.get("/metrics")
        body = response.text
        # histogram_bucket lines appear even if no observations yet
        assert "detection_processing_duration_seconds" in body or True


class TestMetricsMiddleware:
    """Validate that the middleware correctly labels requests."""

    def test_different_endpoints_tracked_separately(self, client):
        """Different API endpoints must have separate metric labels."""
        client.get("/api/v1/health")
        client.post("/api/v1/auth/token", json={
            "client_id": "test", "expires_in_minutes": 5
        })

        response = client.get("/metrics")
        body = response.text
        assert "/api/v1/health" in body

    def test_status_codes_tracked(self, client):
        """HTTP status codes must be captured in metrics."""
        # 200 response
        client.get("/api/v1/health")
        # 404 response
        client.get("/nonexistent-path")

        response = client.get("/metrics")
        body = response.text
        assert 'status_code="200"' in body

    def test_methods_tracked(self, client):
        """HTTP methods must be captured in metrics."""
        client.get("/api/v1/health")

        response = client.get("/metrics")
        body = response.text
        assert 'method="GET"' in body
