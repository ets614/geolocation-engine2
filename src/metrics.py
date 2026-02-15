"""Prometheus metrics instrumentation for Detection API.

Exposes RED (Rate, Errors, Duration) and custom business metrics
via /metrics endpoint for Prometheus scraping.
"""
import time
from typing import Callable

from fastapi import FastAPI, Request, Response
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Info,
    generate_latest,
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    REGISTRY,
)

# ---------------------------------------------------------------------------
# RED Metrics -- Request Rate, Error Rate, Duration
# ---------------------------------------------------------------------------

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=(0.01, 0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3, 0.5, 0.75, 1.0, 2.5, 5.0),
)

HTTP_REQUESTS_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "HTTP requests currently being processed",
    ["method", "endpoint"],
)

# ---------------------------------------------------------------------------
# Authentication Metrics
# ---------------------------------------------------------------------------

AUTH_ATTEMPTS_TOTAL = Counter(
    "auth_attempts_total",
    "Total authentication attempts",
    ["result"],  # success, failure, expired
)

AUTH_TOKEN_GENERATION_TOTAL = Counter(
    "auth_token_generation_total",
    "Total JWT tokens generated",
    ["client_id"],
)

# ---------------------------------------------------------------------------
# Detection Processing Metrics
# ---------------------------------------------------------------------------

DETECTIONS_PROCESSED_TOTAL = Counter(
    "detections_processed_total",
    "Total detections processed",
    ["status", "confidence_flag"],  # status: success/error; confidence: GREEN/YELLOW/RED
)

DETECTION_PROCESSING_DURATION_SECONDS = Histogram(
    "detection_processing_duration_seconds",
    "Time to process a single detection (geolocation + CoT generation)",
    buckets=(0.01, 0.025, 0.05, 0.1, 0.2, 0.5, 1.0, 2.5, 5.0),
)

DETECTION_GEOLOCATION_CONFIDENCE = Histogram(
    "detection_geolocation_confidence",
    "Distribution of geolocation confidence values",
    buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
)

# ---------------------------------------------------------------------------
# Rate Limiting Metrics
# ---------------------------------------------------------------------------

RATE_LIMIT_HITS_TOTAL = Counter(
    "rate_limit_hits_total",
    "Total requests that hit rate limits",
    ["client_id", "endpoint"],
)

# ---------------------------------------------------------------------------
# Cache Metrics (if caching is introduced)
# ---------------------------------------------------------------------------

CACHE_HITS_TOTAL = Counter(
    "cache_hits_total",
    "Total cache hits",
    ["cache_name"],
)

CACHE_MISSES_TOTAL = Counter(
    "cache_misses_total",
    "Total cache misses",
    ["cache_name"],
)

# ---------------------------------------------------------------------------
# TAK Server Push Metrics
# ---------------------------------------------------------------------------

TAK_PUSH_TOTAL = Counter(
    "tak_push_total",
    "Total CoT push attempts to TAK server",
    ["status"],  # success, failure, queued
)

TAK_PUSH_DURATION_SECONDS = Histogram(
    "tak_push_duration_seconds",
    "Duration of TAK server push operations",
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# ---------------------------------------------------------------------------
# Offline Queue Metrics
# ---------------------------------------------------------------------------

OFFLINE_QUEUE_SIZE = Gauge(
    "offline_queue_size",
    "Current number of items in the offline queue",
)

OFFLINE_QUEUE_OLDEST_ITEM_AGE_SECONDS = Gauge(
    "offline_queue_oldest_item_age_seconds",
    "Age of the oldest item in the offline queue in seconds",
)

# ---------------------------------------------------------------------------
# Application Info
# ---------------------------------------------------------------------------

APP_INFO = Info(
    "detection_api",
    "Detection API application information",
)

# ---------------------------------------------------------------------------
# Database Metrics
# ---------------------------------------------------------------------------

DB_CONNECTION_POOL_SIZE = Gauge(
    "db_connection_pool_size",
    "Current database connection pool size",
    ["state"],  # checked_in, checked_out
)


def _normalize_path(path: str) -> str:
    """Normalize URL path to reduce cardinality.

    Replaces UUIDs and numeric IDs with placeholders.

    Args:
        path: Raw URL path.

    Returns:
        Normalized path string safe for label values.
    """
    import re
    # Replace UUIDs
    path = re.sub(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        "{id}",
        path,
    )
    # Replace numeric IDs
    path = re.sub(r"/\d+", "/{id}", path)
    return path


async def metrics_middleware(request: Request, call_next: Callable) -> Response:
    """Middleware to capture HTTP request metrics.

    Records request count, duration, and in-progress gauge
    for every HTTP request.

    Args:
        request: Incoming HTTP request.
        call_next: Next middleware/handler in chain.

    Returns:
        Response from downstream handler.
    """
    # Skip metrics endpoint to avoid recursion
    if request.url.path == "/metrics":
        return await call_next(request)

    method = request.method
    path = _normalize_path(request.url.path)

    HTTP_REQUESTS_IN_PROGRESS.labels(method=method, endpoint=path).inc()
    start_time = time.perf_counter()

    try:
        response = await call_next(request)
        status_code = str(response.status_code)
    except Exception:
        status_code = "500"
        raise
    finally:
        duration = time.perf_counter() - start_time
        HTTP_REQUESTS_TOTAL.labels(
            method=method, endpoint=path, status_code=status_code
        ).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(method=method, endpoint=path).observe(
            duration
        )
        HTTP_REQUESTS_IN_PROGRESS.labels(method=method, endpoint=path).dec()

    return response


def setup_metrics(app: FastAPI, version: str = "0.1.0") -> None:
    """Register Prometheus metrics middleware and /metrics endpoint.

    Args:
        app: FastAPI application instance.
        version: Application version for info metric.
    """
    APP_INFO.info({"version": version, "service": "detection-api"})

    # Register middleware
    app.middleware("http")(metrics_middleware)

    @app.get("/metrics", include_in_schema=False)
    async def prometheus_metrics():
        """Expose Prometheus metrics endpoint."""
        return Response(
            content=generate_latest(REGISTRY),
            media_type=CONTENT_TYPE_LATEST,
        )
