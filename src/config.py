"""Configuration management for Detection to COP service."""
import os
from typing import List


class Config:
    """Application configuration."""

    def __init__(self):
        self.app_title: str = "Detection to COP"
        self.app_version: str = "0.1.0"
        self.cors_origins: List[str] = [
            "http://localhost:3000",
            "http://localhost:8080",
            "http://127.0.0.1:3000",
        ]
        self.debug: bool = os.getenv("DEBUG", "False").lower() == "true"


def get_config() -> Config:
    """Get application configuration.

    Returns:
        Config: Application configuration object.
    """
    return Config()
