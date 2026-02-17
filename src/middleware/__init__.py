"""Middleware setup for FastAPI application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config import Config


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
