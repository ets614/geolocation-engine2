"""Middleware setup for FastAPI application."""
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from src.config import Config
from src.services.security_service import SecurityHeadersService, SecurityHeadersConfig


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware that adds security headers to every response."""

    def __init__(self, app, headers_service: SecurityHeadersService):
        super().__init__(app)
        self.headers_service = headers_service

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        for name, value in self.headers_service.get_headers().items():
            response.headers[name] = value
        return response


def setup_middleware(app: FastAPI, config: Config) -> None:
    """Set up middleware for the FastAPI application.

    Args:
        app: FastAPI application instance.
        config: Application configuration.
    """
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add security headers middleware
    headers_service = SecurityHeadersService(SecurityHeadersConfig())
    app.add_middleware(SecurityHeadersMiddleware, headers_service=headers_service)
