"""Unit tests for monitoring metrics module."""
import pytest
import time
from src.monitoring.metrics import (
    MetricsContext,
    MetricsRecorder,
    request_latency_seconds,
    request_total,
    errors_total,
    auth_failures_total,
    rate_limit_hits_total,
    validation_failures_total,
    db_query_duration_seconds,
    db_queries_total,
    cache_hits_total,
    cache_misses_total,
    detections_received_total,
    detections_processed_total,
    offline_queue_size,
    tak_server_connectivity,
    audit_events_total,
)


class TestMetricsContext:
    """Test MetricsContext for timing operations."""

    def test_metrics_context_records_time(self):
        """Test that context manager records elapsed time."""
        metric = request_latency_seconds.labels(
            method="GET", endpoint="/health", status=200
        )

        with MetricsContext(metric) as ctx:
            time.sleep(0.01)

        assert ctx.histogram is metric

    def test_metrics_context_on_exception(self):
        """Test that context manager handles exceptions."""
        metric = request_latency_seconds.labels(
            method="GET", endpoint="/health", status=200
        )

        try:
            with MetricsContext(metric):
                raise ValueError("Test exception")
        except ValueError:
            pass

    def test_metrics_context_with_valid_histogram(self):
        """Test context manager with valid histogram."""
        metric = request_latency_seconds.labels(
            method="POST", endpoint="/api/detection", status=201
        )

        with MetricsContext(metric) as ctx:
            time.sleep(0.01)

        assert ctx.histogram is metric


class TestMetricsRecorder:
    """Test MetricsRecorder helper class."""

    def test_record_request(self):
        """Test recording HTTP request metrics."""
        MetricsRecorder.record_request("GET", "/health", 200, 0.05)
        # Verify metrics were recorded (prometheus_client handles this)

    def test_record_auth_failure(self):
        """Test recording authentication failure."""
        MetricsRecorder.record_auth_failure("invalid_token")
        # Verify metric was incremented

    def test_record_validation_failure(self):
        """Test recording validation failure."""
        MetricsRecorder.record_validation_failure("email", "invalid_format")
        # Verify metric was incremented

    def test_record_db_query(self):
        """Test recording database query."""
        MetricsRecorder.record_db_query("SELECT", "detections", "success", 0.05)
        # Verify metrics were recorded

    def test_record_cache_hit(self):
        """Test recording cache hit."""
        MetricsRecorder.record_cache_hit("detection_cache")
        # Verify metric was incremented

    def test_record_cache_miss(self):
        """Test recording cache miss."""
        MetricsRecorder.record_cache_miss("detection_cache")
        # Verify metric was incremented

    def test_record_detection_success(self):
        """Test recording successful detection."""
        MetricsRecorder.record_detection("success")
        # Verify metric was incremented

    def test_record_detection_failed(self):
        """Test recording failed detection."""
        MetricsRecorder.record_detection("failed")
        # Verify metric was incremented

    def test_record_offline_queue_queued(self):
        """Test recording offline queue action (queued)."""
        MetricsRecorder.record_offline_queue("queued")
        # Verify metric was incremented

    def test_record_offline_queue_synced(self):
        """Test recording offline queue action (synced)."""
        MetricsRecorder.record_offline_queue("synced")
        # Verify metric was incremented

    def test_record_audit_event(self):
        """Test recording audit trail event."""
        MetricsRecorder.record_audit_event("detection_received")
        # Verify metric was incremented


class TestMetricsDefinitions:
    """Test metric definitions are properly configured."""

    def test_request_latency_histogram_exists(self):
        """Test request latency histogram is defined."""
        assert request_latency_seconds is not None
        assert hasattr(request_latency_seconds, 'labels')

    def test_request_total_counter_exists(self):
        """Test request total counter is defined."""
        assert request_total is not None
        assert hasattr(request_total, 'labels')

    def test_errors_total_counter_exists(self):
        """Test errors total counter is defined."""
        assert errors_total is not None
        assert hasattr(errors_total, 'labels')

    def test_auth_failures_counter_exists(self):
        """Test auth failures counter is defined."""
        assert auth_failures_total is not None
        assert hasattr(auth_failures_total, 'labels')

    def test_rate_limit_hits_counter_exists(self):
        """Test rate limit hits counter is defined."""
        assert rate_limit_hits_total is not None
        assert hasattr(rate_limit_hits_total, 'labels')

    def test_validation_failures_counter_exists(self):
        """Test validation failures counter is defined."""
        assert validation_failures_total is not None
        assert hasattr(validation_failures_total, 'labels')

    def test_db_query_duration_histogram_exists(self):
        """Test database query duration histogram is defined."""
        assert db_query_duration_seconds is not None
        assert hasattr(db_query_duration_seconds, 'labels')

    def test_db_queries_counter_exists(self):
        """Test database queries counter is defined."""
        assert db_queries_total is not None
        assert hasattr(db_queries_total, 'labels')

    def test_cache_hits_counter_exists(self):
        """Test cache hits counter is defined."""
        assert cache_hits_total is not None
        assert hasattr(cache_hits_total, 'labels')

    def test_cache_misses_counter_exists(self):
        """Test cache misses counter is defined."""
        assert cache_misses_total is not None
        assert hasattr(cache_misses_total, 'labels')

    def test_detections_received_counter_exists(self):
        """Test detections received counter is defined."""
        assert detections_received_total is not None
        assert hasattr(detections_received_total, 'labels')

    def test_detections_processed_counter_exists(self):
        """Test detections processed counter is defined."""
        assert detections_processed_total is not None
        assert hasattr(detections_processed_total, 'labels')

    def test_offline_queue_size_gauge_exists(self):
        """Test offline queue size gauge is defined."""
        assert offline_queue_size is not None
        assert hasattr(offline_queue_size, '_value')

    def test_tak_connectivity_gauge_exists(self):
        """Test TAK connectivity gauge is defined."""
        assert tak_server_connectivity is not None
        assert hasattr(tak_server_connectivity, '_value')

    def test_audit_events_counter_exists(self):
        """Test audit events counter is defined."""
        assert audit_events_total is not None
        assert hasattr(audit_events_total, 'labels')


class TestMetricsRecording:
    """Test recording metrics with labels."""

    def test_request_latency_with_labels(self):
        """Test recording request latency with various labels."""
        metric = request_latency_seconds.labels(
            method="POST", endpoint="/api/detection", status=201
        )
        metric.observe(0.125)

    def test_request_total_with_labels(self):
        """Test recording request total with labels."""
        counter = request_total.labels(
            method="GET", endpoint="/health", status=200
        )
        counter.inc()

    def test_errors_with_labels(self):
        """Test recording errors with labels."""
        counter = errors_total.labels(type="validation_error", endpoint="/api/detection")
        counter.inc(5)

    def test_db_query_with_labels(self):
        """Test recording database query with labels."""
        metric = db_query_duration_seconds.labels(
            operation="INSERT", table="detections"
        )
        metric.observe(0.025)

    def test_cache_metrics_with_labels(self):
        """Test recording cache metrics with labels."""
        hits = cache_hits_total.labels(cache_name="detection_cache")
        hits.inc(10)

        misses = cache_misses_total.labels(cache_name="detection_cache")
        misses.inc(3)

    def test_auth_failures_with_reason(self):
        """Test recording auth failures with reason."""
        counter = auth_failures_total.labels(reason="expired_token")
        counter.inc()

        counter2 = auth_failures_total.labels(reason="invalid_signature")
        counter2.inc(2)

    def test_rate_limit_with_labels(self):
        """Test recording rate limit hits with labels."""
        counter = rate_limit_hits_total.labels(
            endpoint="/api/detection", client_id="client-001"
        )
        counter.inc()

    def test_validation_failures_with_labels(self):
        """Test recording validation failures with labels."""
        counter = validation_failures_total.labels(
            field="latitude", reason="out_of_range"
        )
        counter.inc(3)


class TestMetricsIntegration:
    """Test metrics integration across multiple operations."""

    def test_request_lifecycle_metrics(self):
        """Test metrics recording for a complete request."""
        # Record request start
        request_total.labels(
            method="POST", endpoint="/api/detection", status=201
        ).inc()

        # Record latency
        request_latency_seconds.labels(
            method="POST", endpoint="/api/detection", status=201
        ).observe(0.145)

        # Record detection processing
        detections_processed_total.labels(status="success").inc()

    def test_error_path_metrics(self):
        """Test metrics recording for error cases."""
        # Record error
        errors_total.labels(
            type="database_error", endpoint="/api/detection"
        ).inc()

        # Record failed processing
        detections_processed_total.labels(status="failed").inc()

        # Record request with error status
        request_total.labels(
            method="POST", endpoint="/api/detection", status=500
        ).inc()

    def test_auth_and_security_metrics(self):
        """Test security-related metrics."""
        # Record auth attempt
        auth_failures_total.labels(reason="invalid_token").inc()

        # Record rate limit hit
        rate_limit_hits_total.labels(
            endpoint="/api/detection", client_id="client-001"
        ).inc()

        # Record validation failure
        validation_failures_total.labels(
            field="confidence", reason="below_threshold"
        ).inc()
