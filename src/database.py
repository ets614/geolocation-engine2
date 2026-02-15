"""Database connection and session management."""
import os
from contextlib import asynccontextmanager, contextmanager
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and sessions."""

    def __init__(self, database_url: str = None):
        """Initialize database manager.

        Args:
            database_url: SQLite database URL. If None, uses environment variable or default.
        """
        self.database_url = (
            database_url
            or os.getenv("DATABASE_URL", "sqlite:///./app/data/app.db")
        )
        self.engine = None
        self.SessionLocal = None
        self._initialize_engine()

    def _initialize_engine(self):
        """Initialize SQLAlchemy engine with connection pooling."""
        # SQLite-specific configuration
        if self.database_url.startswith("sqlite"):
            self.engine = create_engine(
                self.database_url,
                connect_args={"check_same_thread": False},
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=5,
                pool_pre_ping=True,
                echo=False,
            )
        else:
            # PostgreSQL or other databases
            self.engine = create_engine(
                self.database_url,
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=5,
                pool_pre_ping=True,
                echo=False,
            )

        # Register SQLite-specific event listeners
        if self.database_url.startswith("sqlite"):
            @event.listens_for(self.engine, "connect")
            def set_sqlite_pragma(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.close()

        self.SessionLocal = sessionmaker(
            bind=self.engine, expire_on_commit=False, class_=Session
        )
        logger.info(f"Database engine initialized: {self.database_url}")

    def create_all(self):
        """Create all tables in the database."""
        from src.models.database_models import Base

        Base.metadata.create_all(self.engine)
        logger.info("Database tables created")

    def get_session(self) -> Session:
        """Get a new database session.

        Returns:
            Session: SQLAlchemy session.
        """
        return self.SessionLocal()

    @contextmanager
    def session_scope(self):
        """Provide a transactional scope for database operations.

        Yields:
            Session: SQLAlchemy session within a transaction.
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()

    def get_pool_size(self) -> dict:
        """Get current connection pool statistics.

        Returns:
            dict: Pool size information.
        """
        pool = self.engine.pool
        return {
            "pool_size": getattr(pool, "pool_size", 5),
            "max_overflow": getattr(pool, "max_overflow", 5),
            "checked_in": getattr(pool, "checkedin", 0),
            "checked_out": getattr(pool, "checkedout", 0),
        }

    def health_check(self) -> bool:
        """Perform a health check on the database connection.

        Returns:
            bool: True if healthy, False otherwise.
        """
        try:
            with self.session_scope() as session:
                from sqlalchemy import text
                session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    def close(self):
        """Close the database engine and connection pool."""
        if self.engine:
            self.engine.dispose()
            logger.info("Database engine closed")

    def get_table_info(self, table_name: str) -> dict:
        """Get information about a specific table.

        Args:
            table_name: Name of the table.

        Returns:
            dict: Table information including columns.
        """
        inspector = inspect(self.engine)
        columns = inspector.get_columns(table_name)
        indices = inspector.get_indexes(table_name)
        return {"columns": columns, "indices": indices}


# Global database manager instance
_db_manager = None


def get_db_manager() -> DatabaseManager:
    """Get the global database manager instance.

    Returns:
        DatabaseManager: The database manager instance.
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def init_db():
    """Initialize the database on application startup."""
    db_manager = get_db_manager()
    db_manager.create_all()
    health = db_manager.health_check()
    if health:
        logger.info("Database initialized successfully")
    else:
        logger.error("Database health check failed")


def get_db_session() -> Session:
    """Dependency for FastAPI to get a database session.

    Yields:
        Session: SQLAlchemy session.
    """
    db_manager = get_db_manager()
    session = db_manager.get_session()
    try:
        yield session
    finally:
        session.close()
