"""Middleware setup for FastAPI application."""
from fastapi import FastAPI
from src.config import Config


def setup_middleware(app: FastAPI, config: Config):
    """Set up middleware for the application.

    Args:
        app: FastAPI application instance
        config: Application configuration
    """
    # CORS middleware could be added here if needed
    # CORSMiddleware.add_middleware(app, allow_origins=["*"])
    pass
