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


@pytest.fixture
def db_session():
    """Provides a test database session with schema created."""
    from src.database import DatabaseManager
    from src.models.database_models import Base

    # Create an in-memory SQLite database for testing
    db_manager = DatabaseManager(database_url="sqlite:///:memory:")

    # Create all tables
    Base.metadata.create_all(db_manager.engine)

    # Create and yield a session
    session = db_manager.get_session()
    try:
        yield session
    finally:
        session.close()
        db_manager.close()
