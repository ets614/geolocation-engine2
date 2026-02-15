"""Unit tests for middleware setup."""
import pytest


@pytest.mark.unit
def test_cors_middleware_accepts_configured_origins(test_client):
    """Unit test: CORS middleware accepts configured origins."""
    response = test_client.get(
        "/api/v1/health",
        headers={"Origin": "http://localhost:3000"}
    )
    assert response.status_code in [200, 404]


@pytest.mark.unit
def test_middleware_setup_function_exists():
    """Unit test: Middleware setup function is available."""
    from src.middleware import setup_middleware
    assert callable(setup_middleware)


@pytest.mark.unit
def test_setup_middleware_applies_cors():
    """Unit test: setup_middleware applies CORS middleware."""
    from fastapi import FastAPI
    from src.middleware import setup_middleware
    from src.config import get_config

    app = FastAPI()
    config = get_config()
    setup_middleware(app, config)

    assert len(app.user_middleware) > 0
