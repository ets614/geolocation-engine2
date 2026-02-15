"""Middleware modules for request handling and validation."""
from fastapi import FastAPI
from src.middleware.validation_middleware import (
    RequestValidationMiddleware,
    SuspiciousPatternDetectorMiddleware,
    ValidationErrorFormatter,
)

__all__ = [
    "RequestValidationMiddleware",
    "SuspiciousPatternDetectorMiddleware",
    "ValidationErrorFormatter",
    "setup_middleware",
]


def setup_middleware(app: FastAPI) -> None:
    """Set up all middleware for the FastAPI application.

    Args:
        app: FastAPI application instance
    """
    # Add validation middleware
    app.add_middleware(RequestValidationMiddleware)
    app.add_middleware(SuspiciousPatternDetectorMiddleware)
