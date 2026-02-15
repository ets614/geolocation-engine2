"""Middleware for request validation and error handling."""
import json
import logging
from typing import Callable, Optional
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class ValidationErrorFormatter:
    """Format validation errors in consistent response structure."""

    @staticmethod
    def format_pydantic_error(error: ValidationError) -> dict:
        """Convert Pydantic ValidationError to response format.

        Args:
            error: Pydantic validation error

        Returns:
            Dictionary with formatted error details
        """
        errors = []
        for err in error.errors():
            field_path = ".".join(str(x) for x in err["loc"])
            error_type = err["type"]
            msg = err.get("msg", "Validation failed")

            errors.append({
                "field": field_path,
                "error_code": f"V{hash(error_type) % 1000:03d}",
                "message": msg,
                "constraint": error_type,
            })

        return {
            "error_code": "E400",
            "error_message": "Request validation failed",
            "details": {
                "validation_errors": errors,
                "error_count": len(errors),
            },
        }


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Middleware for validating requests and handling validation errors."""

    def __init__(self, app: ASGIApp):
        """Initialize middleware.

        Args:
            app: ASGI application
        """
        super().__init__(app)
        self.suspicious_requests = []
        self.validation_failures = []

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with validation.

        Args:
            request: HTTP request
            call_next: Next middleware/handler

        Returns:
            HTTP response
        """
        # Store request details for logging
        request_info = {
            "method": request.method,
            "path": request.url.path,
            "client_host": request.client.host if request.client else "unknown",
        }

        try:
            # Proceed to next handler
            response = await call_next(request)
            return response

        except ValidationError as e:
            # Log validation failure
            logger.warning(
                "Request validation failed",
                extra={
                    "error_count": len(e.errors()),
                    "path": request.url.path,
                    "method": request.method,
                    "client_ip": request.client.host if request.client else "unknown",
                }
            )

            # Track validation failure
            self.validation_failures.append(request_info)

            # Return formatted error response
            error_response = ValidationErrorFormatter.format_pydantic_error(e)
            return JSONResponse(
                status_code=400,
                content=error_response,
            )

        except Exception as e:
            logger.error(
                "Unexpected error in validation middleware",
                extra={"error": str(e), "path": request.url.path},
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error_code": "E500",
                    "error_message": "Internal server error",
                },
            )

    def get_validation_stats(self) -> dict:
        """Get validation statistics.

        Returns:
            Dictionary with validation stats
        """
        return {
            "total_validation_failures": len(self.validation_failures),
            "suspicious_requests": len(self.suspicious_requests),
            "recent_failures": self.validation_failures[-10:],  # Last 10
            "recent_suspicious": self.suspicious_requests[-10:],  # Last 10
        }


class SuspiciousPatternDetectorMiddleware(BaseHTTPMiddleware):
    """Middleware for detecting and logging suspicious patterns."""

    def __init__(self, app: ASGIApp):
        """Initialize middleware.

        Args:
            app: ASGI application
        """
        super().__init__(app)
        self.sql_injection_attempts = []
        self.xss_attempts = []
        self.path_traversal_attempts = []

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Detect suspicious patterns in request.

        Args:
            request: HTTP request
            call_next: Next middleware/handler

        Returns:
            HTTP response
        """
        client_ip = request.client.host if request.client else "unknown"

        # Check query parameters
        for key, value in request.query_params.items():
            if self._detect_sql_injection(value):
                self._log_sql_injection_attempt(key, value, client_ip)
            elif self._detect_xss(value):
                self._log_xss_attempt(key, value, client_ip)
            elif self._detect_path_traversal(value):
                self._log_path_traversal_attempt(key, value, client_ip)

        try:
            response = await call_next(request)
            return response
        except Exception as e:
            logger.error(f"Error in suspicious pattern detector: {str(e)}")
            raise

    @staticmethod
    def _detect_sql_injection(value: str) -> bool:
        """Detect SQL injection patterns."""
        patterns = [
            r"(\bunion\b.*\bselect\b)",
            r"(\bor\b\s+1\s*=\s*1)",
            r"(--)",
            r"(/\*)",
        ]
        import re
        for pattern in patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        return False

    @staticmethod
    def _detect_xss(value: str) -> bool:
        """Detect XSS patterns."""
        patterns = [
            r"<script",
            r"on\w+\s*=",
            r"javascript:",
        ]
        import re
        for pattern in patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        return False

    @staticmethod
    def _detect_path_traversal(value: str) -> bool:
        """Detect path traversal patterns."""
        patterns = [
            r"\.\./",
            r"\.\.",
            r"%2e%2e",
        ]
        import re
        for pattern in patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        return False

    def _log_sql_injection_attempt(self, field: str, value: str, client_ip: str) -> None:
        """Log SQL injection attempt."""
        logger.warning(
            "SQL injection attempt detected",
            extra={
                "field": field,
                "value_sample": value[:100],
                "client_ip": client_ip,
                "attack_type": "sql_injection",
            }
        )
        self.sql_injection_attempts.append({
            "field": field,
            "client_ip": client_ip,
            "timestamp": str(__import__("datetime").datetime.utcnow()),
        })

    def _log_xss_attempt(self, field: str, value: str, client_ip: str) -> None:
        """Log XSS attempt."""
        logger.warning(
            "XSS attempt detected",
            extra={
                "field": field,
                "value_sample": value[:100],
                "client_ip": client_ip,
                "attack_type": "xss",
            }
        )
        self.xss_attempts.append({
            "field": field,
            "client_ip": client_ip,
            "timestamp": str(__import__("datetime").datetime.utcnow()),
        })

    def _log_path_traversal_attempt(self, field: str, value: str, client_ip: str) -> None:
        """Log path traversal attempt."""
        logger.warning(
            "Path traversal attempt detected",
            extra={
                "field": field,
                "value_sample": value[:100],
                "client_ip": client_ip,
                "attack_type": "path_traversal",
            }
        )
        self.path_traversal_attempts.append({
            "field": field,
            "client_ip": client_ip,
            "timestamp": str(__import__("datetime").datetime.utcnow()),
        })

    def get_attempt_stats(self) -> dict:
        """Get suspicious attempt statistics.

        Returns:
            Dictionary with attempt stats
        """
        return {
            "sql_injection_attempts": len(self.sql_injection_attempts),
            "xss_attempts": len(self.xss_attempts),
            "path_traversal_attempts": len(self.path_traversal_attempts),
            "total_suspicious": (
                len(self.sql_injection_attempts) +
                len(self.xss_attempts) +
                len(self.path_traversal_attempts)
            ),
            "recent_sql_injections": self.sql_injection_attempts[-5:],
            "recent_xss": self.xss_attempts[-5:],
            "recent_path_traversals": self.path_traversal_attempts[-5:],
        }
