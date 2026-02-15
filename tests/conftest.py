import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient


@pytest.fixture
def test_client():
    """Provides a synchronous TestClient for the FastAPI app."""
    from src.main import app
    return TestClient(app)


@pytest.fixture
async def async_client():
    """Provides an AsyncClient for testing async endpoints."""
    from src.main import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
