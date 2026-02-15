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
        self.tak_server_url: str = os.getenv(
            "TAK_SERVER_URL",
            "http://localhost:8080/CoT"
        )
        self.jwt_secret_key: str = os.getenv(
            "JWT_SECRET_KEY",
            "your-secret-key-change-in-production"
        )
        self.jwt_algorithm: str = "HS256"
        self.jwt_expiration_minutes: int = 60

        # Rate limiting
        self.rate_limit_capacity: int = int(
            os.getenv("RATE_LIMIT_CAPACITY", "100")
        )
        self.rate_limit_refill_rate: float = float(
            os.getenv("RATE_LIMIT_REFILL_RATE", "10.0")
        )

        # Cache
        self.cache_ttl_seconds: float = float(
            os.getenv("CACHE_TTL_SECONDS", "300.0")
        )
        self.cache_max_entries: int = int(
            os.getenv("CACHE_MAX_ENTRIES", "1000")
        )

        # Security
        self.enforce_https: bool = os.getenv(
            "ENFORCE_HTTPS", "False"
        ).lower() == "true"


def get_config() -> Config:
    """Get application configuration.

    Returns:
        Config: Application configuration object.
    """
    return Config()
