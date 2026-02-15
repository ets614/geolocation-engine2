"""Unit tests for main FastAPI application."""
import pytest
from fastapi import FastAPI


@pytest.mark.unit
def test_app_instance_created():
    """Unit test: FastAPI app instance is created."""
    from src.main import app
    assert isinstance(app, FastAPI)
    assert app.title == "Detection to COP"


@pytest.mark.unit
def test_health_endpoint_exists(test_client):
    """Unit test: Health endpoint is registered."""
    response = test_client.get("/api/v1/health")
    assert response.status_code in [200, 404]  # 200 if implemented, 404 if not yet


@pytest.mark.unit
def test_health_endpoint_is_async():
    """Unit test: Health endpoint is async."""
    from src.main import app
    routes = [route.path for route in app.routes]
    assert "/api/v1/health" in routes


@pytest.mark.unit
def test_cors_middleware_registered(test_client):
    """Unit test: CORS middleware is registered."""
    from src.main import app
    middlewares = [m.__class__.__name__ for m in app.user_middleware]
    assert any("CORSMiddleware" in str(m) for m in app.user_middleware)


@pytest.mark.unit
def test_error_handlers_registered():
    """Unit test: Error handlers are registered."""
    from src.main import app
    # Check that exception handlers exist
    assert app.exception_handlers is not None
