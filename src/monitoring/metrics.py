"""Prometheus metrics definitions and collectors for detection API."""
from prometheus_client import Counter, Histogram, Gauge, Info
import time

# Application Info
app_info = Info("detection_api", "Detection API Information")

# Request Metrics
request_latency_seconds = Histogram(
    "request_latency_seconds",
    "HTTP request latency in seconds",
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0),
    labelnames=["method", "endpoint", "status"],
)

request_total = Counter(
    "requests_total",
    "Total number of HTTP requests",
    labelnames=["method", "endpoint", "status"],
)

# Error Metrics
errors_total = Counter(
    "errors_total",
    "Total number of errors",
    labelnames=["type", "endpoint"],
)

# Authentication Metrics
auth_failures_total = Counter(
    "auth_failures_total",
    "Total number of authentication failures",
    labelnames=["reason"],
)

auth_attempts_total = Counter(
    "auth_attempts_total",
    "Total number of authentication attempts",
    labelnames=["method"],
)

# Rate Limit Metrics
rate_limit_hits_total = Counter(
    "rate_limit_hits_total",
    "Total number of rate limit hits",
    labelnames=["endpoint", "client_id"],
)

rate_limit_remaining = Gauge(
    "rate_limit_remaining",
    "Remaining rate limit quota",
    labelnames=["endpoint", "client_id"],
)

# Validation Metrics
validation_failures_total = Counter(
    "validation_failures_total",
    "Total number of validation failures",
    labelnames=["field", "reason"],
)

invalid_requests_total = Counter(
    "invalid_requests_total",
    "Total invalid requests by endpoint",
    labelnames=["endpoint", "error_type"],
)

# Database Metrics
db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0),
    labelnames=["operation", "table"],
)

db_queries_total = Counter(
    "db_queries_total",
    "Total number of database queries",
    labelnames=["operation", "table", "status"],
)

db_connections_active = Gauge(
    "db_connections_active",
    "Number of active database connections",
)

# Cache Metrics
cache_hits_total = Counter(
    "cache_hits_total",
    "Total number of cache hits",
    labelnames=["cache_name"],
)

cache_misses_total = Counter(
    "cache_misses_total",
    "Total number of cache misses",
    labelnames=["cache_name"],
)

cache_size_bytes = Gauge(
    "cache_size_bytes",
    "Cache size in bytes",
    labelnames=["cache_name"],
)

cache_evictions_total = Counter(
    "cache_evictions_total",
    "Total cache evictions",
    labelnames=["cache_name"],
)

# Processing Metrics (Detection Pipeline)
detections_received_total = Counter(
    "detections_received_total",
    "Total detections received",
    labelnames=["source"],
)

detections_processed_total = Counter(
    "detections_processed_total",
    "Total detections processed",
    labelnames=["status"],
)

geolocation_latency_seconds = Histogram(
    "geolocation_latency_seconds",
    "Geolocation processing latency in seconds",
    buckets=(0.001, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0),
)

cot_generation_latency_seconds = Histogram(
    "cot_generation_latency_seconds",
    "CoT generation latency in seconds",
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1),
)

tak_push_attempts_total = Counter(
    "tak_push_attempts_total",
    "Total TAK push attempts",
    labelnames=["status"],
)

# Offline Queue Metrics
offline_queue_size = Gauge(
    "offline_queue_size",
    "Current size of offline queue",
)

offline_queue_max_size = Gauge(
    "offline_queue_max_size",
    "Maximum offline queue size",
)

offline_items_queued_total = Counter(
    "offline_items_queued_total",
    "Total items queued offline",
)

offline_items_synced_total = Counter(
    "offline_items_synced_total",
    "Total items synced from offline queue",
)

offline_queue_errors_total = Counter(
    "offline_queue_errors_total",
    "Total offline queue errors",
    labelnames=["error_type"],
)

# Connectivity Metrics
tak_server_connectivity = Gauge(
    "tak_server_connectivity",
    "TAK server connectivity status (1=connected, 0=disconnected)",
)

tak_server_latency_seconds = Histogram(
    "tak_server_latency_seconds",
    "TAK server response latency in seconds",
    buckets=(0.1, 0.25, 0.5, 1.0, 2.0, 5.0),
)

# Audit Trail Metrics
audit_events_total = Counter(
    "audit_events_total",
    "Total audit events logged",
    labelnames=["event_type"],
)

audit_log_latency_seconds = Histogram(
    "audit_log_latency_seconds",
    "Audit logging latency in seconds",
    buckets=(0.001, 0.005, 0.01, 0.05),
)

# System Metrics (collected by Kubernetes)
# These are defined for scrape target configuration

# Business Metrics
detection_confidence_distribution = Histogram(
    "detection_confidence_distribution",
    "Distribution of detection confidence scores",
    buckets=(0.0, 0.25, 0.5, 0.75, 1.0),
)

geolocation_accuracy_distribution = Histogram(
    "geolocation_accuracy_distribution",
    "Distribution of geolocation accuracy (meters)",
    buckets=(1, 10, 25, 100, 500, 1000, 5000),
)

cot_type_distribution = Counter(
    "cot_type_distribution",
    "Distribution of CoT type codes generated",
    labelnames=["cot_type"],
)


class MetricsContext:
    """Context manager for timing and recording metrics."""

    def __init__(self, histogram_metric):
        """Initialize metrics context.

        Args:
            histogram_metric: Prometheus Histogram metric to record to.
        """
        self.histogram = histogram_metric
        self.start_time = None

    def __enter__(self):
        """Start timing."""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Record elapsed time."""
        if self.start_time is not None:
            elapsed = time.time() - self.start_time
            self.histogram.observe(elapsed)
        return False


class MetricsRecorder:
    """Helper class for recording common metrics."""

    @staticmethod
    def record_request(method: str, endpoint: str, status_code: int, latency: float):
        """Record HTTP request metrics.

        Args:
            method: HTTP method (GET, POST, etc).
            endpoint: Endpoint path.
            status_code: HTTP status code.
            latency: Request latency in seconds.
        """
        request_latency_seconds.labels(
            method=method, endpoint=endpoint, status=status_code
        ).observe(latency)
        request_total.labels(method=method, endpoint=endpoint, status=status_code).inc()

    @staticmethod
    def record_auth_failure(reason: str):
        """Record authentication failure.

        Args:
            reason: Failure reason (invalid_token, expired_token, etc).
        """
        auth_failures_total.labels(reason=reason).inc()

    @staticmethod
    def record_validation_failure(field: str, reason: str):
        """Record validation failure.

        Args:
            field: Field that failed validation.
            reason: Validation failure reason.
        """
        validation_failures_total.labels(field=field, reason=reason).inc()

    @staticmethod
    def record_db_query(operation: str, table: str, status: str, duration: float):
        """Record database query metrics.

        Args:
            operation: DB operation (SELECT, INSERT, UPDATE, DELETE).
            table: Table name.
            status: Operation status (success, error).
            duration: Query duration in seconds.
        """
        db_query_duration_seconds.labels(operation=operation, table=table).observe(
            duration
        )
        db_queries_total.labels(operation=operation, table=table, status=status).inc()

    @staticmethod
    def record_cache_hit(cache_name: str):
        """Record cache hit.

        Args:
            cache_name: Name of the cache.
        """
        cache_hits_total.labels(cache_name=cache_name).inc()

    @staticmethod
    def record_cache_miss(cache_name: str):
        """Record cache miss.

        Args:
            cache_name: Name of the cache.
        """
        cache_misses_total.labels(cache_name=cache_name).inc()

    @staticmethod
    def record_detection(status: str):
        """Record detection processing.

        Args:
            status: Processing status (success, failed, queued).
        """
        detections_processed_total.labels(status=status).inc()

    @staticmethod
    def record_offline_queue(action: str):
        """Record offline queue action.

        Args:
            action: Action (queued, synced).
        """
        if action == "queued":
            offline_items_queued_total.inc()
        elif action == "synced":
            offline_items_synced_total.inc()

    @staticmethod
    def record_audit_event(event_type: str):
        """Record audit trail event.

        Args:
            event_type: Type of audit event.
        """
        audit_events_total.labels(event_type=event_type).inc()
