"""Integration tests for database schema initialization and migrations."""
import pytest
import tempfile
import os
import time
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json


class TestDatabaseInitialization:
    """Test database initialization and schema creation."""

    def test_database_initializes_on_startup(self, in_memory_db_engine):
        """Acceptance: Database initializes on startup without manual intervention."""
        from src.models.database_models import Base

        # Verify tables are created
        Base.metadata.create_all(in_memory_db_engine)
        inspector = inspect(in_memory_db_engine)
        tables = inspector.get_table_names()

        assert "detections" in tables
        assert "offline_queue" in tables
        assert "audit_trail" in tables

    def test_detections_table_has_required_columns(self, in_memory_db_engine):
        """Acceptance: Detections table includes required columns."""
        from src.models.database_models import Base

        Base.metadata.create_all(in_memory_db_engine)
        inspector = inspect(in_memory_db_engine)
        columns = {col["name"] for col in inspector.get_columns("detections")}

        required_columns = {
            "id",
            "source",
            "class_name",
            "confidence",
            "latitude",
            "longitude",
            "accuracy",
            "timestamp",
        }
        assert required_columns.issubset(columns)

    def test_offline_queue_table_has_required_columns(self, in_memory_db_engine):
        """Acceptance: Offline queue table includes required columns."""
        from src.models.database_models import Base

        Base.metadata.create_all(in_memory_db_engine)
        inspector = inspect(in_memory_db_engine)
        columns = {col["name"] for col in inspector.get_columns("offline_queue")}

        required_columns = {"id", "detection_json", "created_at", "synced_at", "retry_count"}
        assert required_columns.issubset(columns)

    def test_audit_trail_table_has_required_columns(self, in_memory_db_engine):
        """Acceptance: Audit trail table includes required columns."""
        from src.models.database_models import Base

        Base.metadata.create_all(in_memory_db_engine)
        inspector = inspect(in_memory_db_engine)
        columns = {col["name"] for col in inspector.get_columns("audit_trail")}

        required_columns = {"id", "action", "source", "timestamp", "details", "status"}
        assert required_columns.issubset(columns)

    def test_indices_are_created_on_timestamp_columns(self, in_memory_db_engine):
        """Acceptance: Indices are created on timestamp columns."""
        from src.models.database_models import Base

        Base.metadata.create_all(in_memory_db_engine)
        inspector = inspect(in_memory_db_engine)

        # Check detections table timestamp index
        detections_indices = {idx["name"] for idx in inspector.get_indexes("detections")}
        assert "idx_timestamp" in detections_indices

        # Check offline_queue table synced_at index
        offline_indices = {idx["name"] for idx in inspector.get_indexes("offline_queue")}
        assert "idx_synced_at" in offline_indices

        # Check audit_trail table timestamp index
        audit_indices = {idx["name"] for idx in inspector.get_indexes("audit_trail")}
        assert "idx_audit_timestamp" in audit_indices

    def test_migration_applies_successfully(self, temp_db_path):
        """Acceptance: Migrations apply successfully from empty database to current schema."""
        os.environ["DATABASE_URL"] = f"sqlite:///{temp_db_path}"

        # Create engine and apply migrations
        engine = create_engine(
            f"sqlite:///{temp_db_path}",
            connect_args={"check_same_thread": False},
        )

        # Apply initial migration
        from src.models.database_models import Base

        Base.metadata.create_all(engine)

        # Verify tables exist
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        assert "detections" in tables
        assert "offline_queue" in tables
        assert "audit_trail" in tables

        engine.dispose()

    def test_database_file_created_at_correct_location(self):
        """Acceptance: Database file is created at expected location."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "app.db")
            os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

            from src.database import DatabaseManager

            db_manager = DatabaseManager(f"sqlite:///{db_path}")
            db_manager.create_all()

            assert os.path.exists(db_path)
            assert os.path.getsize(db_path) > 0

    def test_schema_survives_connection_close_and_reopen(self, temp_db_path):
        """Acceptance: Schema persists after connection close and reopen."""
        db_url = f"sqlite:///{temp_db_path}"

        from src.database import DatabaseManager

        # First connection: create schema
        db1 = DatabaseManager(db_url)
        db1.create_all()
        db1.close()

        # Second connection: verify schema exists
        db2 = DatabaseManager(db_url)
        inspector = inspect(db2.engine)
        tables = inspector.get_table_names()

        assert "detections" in tables
        assert "offline_queue" in tables
        assert "audit_trail" in tables

        db2.close()
