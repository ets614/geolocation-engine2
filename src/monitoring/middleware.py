"""Prometheus middleware for FastAPI."""
import time
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from src.monitoring.metrics import request_latency_seconds, request_total


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware to record Prometheus metrics for HTTP requests."""

    async def dispatch(self, request: Request, call_next):
        """Process request and record metrics.

        Args:
            request: HTTP request.
            call_next: Next middleware/handler.

        Returns:
            HTTP response.
        """
        start_time = time.time()
        method = request.method
        endpoint = request.url.path

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            status_code = 500
            raise
        finally:
            # Record metrics
            latency = time.time() - start_time
            request_latency_seconds.labels(
                method=method, endpoint=endpoint, status=status_code
            ).observe(latency)
            request_total.labels(
                method=method, endpoint=endpoint, status=status_code
            ).inc()

        return response


def setup_prometheus_middleware(app: FastAPI) -> None:
    """Set up Prometheus metrics middleware for FastAPI.

    Args:
        app: FastAPI application instance.
    """
    app.add_middleware(PrometheusMiddleware)
