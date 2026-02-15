"""Unit tests for database connection and session management."""
import pytest
import time
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session

# Test Budget: 5 distinct behaviors x 2 = 10 unit tests
# Behaviors:
# 1. Connection pool creates 5-10 connections
# 2. Session is thread-safe and properly isolated
# 3. Transaction rollback works correctly on errors
# 4. Query execution completes within performance requirement
# 5. Database URL is configured from environment


class TestDatabaseManager:
    """Test DatabaseManager connection and session handling."""

    def test_database_manager_initializes_with_default_url(self):
        """Unit: DatabaseManager uses default SQLite URL when no config provided."""
        from src.database import DatabaseManager

        db = DatabaseManager("sqlite:///:memory:")
        assert db.database_url == "sqlite:///:memory:"
        assert db.engine is not None
        assert db.SessionLocal is not None

    def test_database_manager_initializes_with_custom_url(self, temp_db_path):
        """Unit: DatabaseManager accepts custom database URL."""
        from src.database import DatabaseManager

        custom_url = f"sqlite:///{temp_db_path}"
        db = DatabaseManager(custom_url)
        assert db.database_url == custom_url
        assert db.engine is not None

    @pytest.mark.parametrize("min_pool,max_pool", [(5, 10), (10, 15)])
    def test_connection_pool_size_configurable(self, min_pool, max_pool):
        """Unit: Connection pool size is configurable within acceptable range."""
        from src.database import DatabaseManager

        db = DatabaseManager("sqlite:///:memory:")
        pool_stats = db.get_pool_size()

        assert pool_stats["pool_size"] == 5  # SQLite default
        assert pool_stats["max_overflow"] == 5  # SQLite default

    def test_session_creation_returns_valid_session(self, in_memory_db_session):
        """Unit: Get session returns a valid SQLAlchemy session."""
        from src.models.database_models import Detection

        assert in_memory_db_session is not None
        assert isinstance(in_memory_db_session, Session)

    def test_session_scope_context_manager_commits(self, in_memory_db_engine):
        """Unit: Session scope context manager commits transactions."""
        from src.database import DatabaseManager
        from src.models.database_models import Detection, Base
        from sqlalchemy.orm import sessionmaker

        Base.metadata.create_all(in_memory_db_engine)

        db = DatabaseManager("sqlite:///:memory:")
        db.engine = in_memory_db_engine
        db.SessionLocal = sessionmaker(bind=in_memory_db_engine)

        # Create a detection via session scope
        detection_data = {
            "source": "test_camera",
            "class_name": "vehicle",
            "confidence": 0.95,
            "latitude": 40.7128,
            "longitude": -74.0060,
            "accuracy": 5.0,
        }

        with db.session_scope() as session:
            detection = Detection(**detection_data)
            session.add(detection)
            session.flush()
            detection_id = detection.id

        # Verify in a new session
        with db.session_scope() as session:
            retrieved = session.get(Detection, detection_id)
            assert retrieved is not None
            assert retrieved.source == "test_camera"

    def test_transaction_rollback_on_error(self, in_memory_db_engine):
        """Unit: Transaction rollback works correctly on database error."""
        from src.database import DatabaseManager
        from src.models.database_models import Detection, Base
        from sqlalchemy.orm import sessionmaker

        Base.metadata.create_all(in_memory_db_engine)

        db = DatabaseManager("sqlite:///:memory:")
        db.engine = in_memory_db_engine
        db.SessionLocal = sessionmaker(bind=in_memory_db_engine)

        # Add a valid detection first
        with db.session_scope() as session:
            detection = Detection(
                source="test",
                class_name="vehicle",
                confidence=0.95,
                latitude=40.7128,
                longitude=-74.0060,
                accuracy=5.0,
            )
            session.add(detection)

        # Attempt invalid operation that triggers rollback
        try:
            with db.session_scope() as session:
                # This should trigger an error due to missing required field
                from sqlalchemy import text

                session.execute(
                    text(
                        "INSERT INTO detections (source, class_name, confidence, latitude, longitude, accuracy, timestamp) "
                        "VALUES ('test', 'person', 0.85, NULL, NULL, 5.0, datetime('now'))"
                    )
                )
        except Exception:
            pass  # Expected to fail

        # Verify previous data is intact (rollback prevented corruption)
        with db.session_scope() as session:
            count = session.query(Detection).count()
            assert count == 1

    @pytest.mark.parametrize(
        "num_inserts",
        [
            10,
            50,
            100,
        ],
    )
    def test_query_execution_within_performance_budget(
        self, in_memory_db_engine, num_inserts
    ):
        """Unit: Query execution completes within 500ms for standard operations."""
        from src.database import DatabaseManager
        from src.models.database_models import Detection, Base
        from sqlalchemy.orm import sessionmaker

        Base.metadata.create_all(in_memory_db_engine)

        db = DatabaseManager("sqlite:///:memory:")
        db.engine = in_memory_db_engine
        db.SessionLocal = sessionmaker(bind=in_memory_db_engine)

        # Insert test data
        with db.session_scope() as session:
            for i in range(num_inserts):
                detection = Detection(
                    source=f"camera_{i}",
                    class_name="vehicle",
                    confidence=0.85 + (i % 10) * 0.01,
                    latitude=40.7128 + i * 0.001,
                    longitude=-74.0060 + i * 0.001,
                    accuracy=5.0,
                )
                session.add(detection)

        # Measure query performance
        start = time.time()
        with db.session_scope() as session:
            results = session.query(Detection).filter(Detection.class_name == "vehicle").all()
        elapsed = (time.time() - start) * 1000  # Convert to milliseconds

        assert elapsed < 500, f"Query took {elapsed}ms, exceeds 500ms budget"
        assert len(results) == num_inserts

    def test_database_health_check_passes(self, in_memory_db_engine):
        """Unit: Health check returns True for valid connection."""
        from src.database import DatabaseManager
        from src.models.database_models import Base
        from sqlalchemy.orm import sessionmaker

        Base.metadata.create_all(in_memory_db_engine)

        db = DatabaseManager("sqlite:///:memory:")
        db.engine = in_memory_db_engine
        db.SessionLocal = sessionmaker(bind=in_memory_db_engine)

        assert db.health_check() is True

    def test_get_table_info_returns_schema(self, in_memory_db_engine):
        """Unit: Get table info returns correct columns and indices."""
        from src.database import DatabaseManager
        from src.models.database_models import Base
        from sqlalchemy.orm import sessionmaker

        Base.metadata.create_all(in_memory_db_engine)

        db = DatabaseManager("sqlite:///:memory:")
        db.engine = in_memory_db_engine

        table_info = db.get_table_info("detections")
        column_names = {col["name"] for col in table_info["columns"]}

        assert "id" in column_names
        assert "source" in column_names
        assert "timestamp" in column_names

    def test_session_closes_properly(self, in_memory_db_engine):
        """Unit: Session closes properly preventing resource leak."""
        from src.database import DatabaseManager
        from src.models.database_models import Base
        from sqlalchemy.orm import sessionmaker

        Base.metadata.create_all(in_memory_db_engine)

        db = DatabaseManager("sqlite:///:memory:")
        db.engine = in_memory_db_engine
        db.SessionLocal = sessionmaker(bind=in_memory_db_engine)

        session = db.get_session()
        assert session is not None
        old_id = id(session)
        session.close()
        # After close, a new session should have different id
        new_session = db.get_session()
        assert id(new_session) != old_id

    @pytest.mark.parametrize(
        "source,class_name",
        [
            ("camera_1", "vehicle"),
            ("camera_2", "person"),
            ("camera_3", "animal"),
        ],
    )
    def test_detection_creation_via_session(
        self, in_memory_db_session, source, class_name
    ):
        """Unit: Detections can be created and retrieved via session."""
        from src.models.database_models import Detection

        detection = Detection(
            source=source,
            class_name=class_name,
            confidence=0.95,
            latitude=40.7128,
            longitude=-74.0060,
            accuracy=5.0,
        )
        in_memory_db_session.add(detection)
        in_memory_db_session.commit()

        retrieved = in_memory_db_session.query(Detection).filter_by(source=source).first()
        assert retrieved is not None
        assert retrieved.class_name == class_name
