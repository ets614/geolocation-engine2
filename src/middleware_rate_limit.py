"""Rate limiting middleware for FastAPI."""
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from src.services.rate_limiter_service import (
    RateLimiterService,
    RateLimitConfig,
)


logger = logging.getLogger(__name__)


def setup_rate_limiting(
    app: FastAPI,
    config: RateLimitConfig,
) -> RateLimiterService:
    """Set up rate limiting middleware for FastAPI app.

    Args:
        app: FastAPI application instance
        config: Rate limit configuration

    Returns:
        RateLimiterService: Rate limiter instance
    """
    rate_limiter = RateLimiterService(config=config)

    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        """Rate limiting middleware.

        Args:
            request: HTTP request
            call_next: Next middleware/route handler

        Returns:
            HTTP response with rate limit headers
        """
        # Extract client ID from JWT token (from request state if available)
        client_id = getattr(request.state, "client_id", "anonymous")

        # Get endpoint path
        endpoint = request.url.path

        # Skip rate limiting for health check and metrics
        if endpoint in ["/api/v1/health", "/api/v1/metrics/rate-limit", "/health"]:
            return await call_next(request)

        # Check rate limit
        allowed, headers = rate_limiter.allow_request(client_id, endpoint)

        if not allowed:
            # Return 429 Too Many Requests
            response = JSONResponse(
                status_code=429,
                content={
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "error_message": "Rate limit exceeded",
                    "quota_limit": config.per_user_quota,
                    "quota_remaining": 0,
                },
            )
            for key, value in headers.items():
                response.headers[key] = value
            return response

        # Proceed with request
        response = await call_next(request)

        # Add rate limit headers to response
        for key, value in headers.items():
            response.headers[key] = value

        return response

    return rate_limiter
