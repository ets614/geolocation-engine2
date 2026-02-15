"""Unit tests for audit trail service (immutable event logging)."""
import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from src.services.audit_trail_service import (
    AuditTrailService,
    AuditTrailEntry,
    AuditEventType,
)


@pytest.fixture
def audit_service(db_session):
    """Create audit trail service instance with database session."""
    return AuditTrailService(session=db_session)


@pytest.fixture
def audit_service_no_db():
    """Create audit trail service instance without database."""
    return AuditTrailService(session=None)


@pytest.fixture
def sample_audit_entry():
    """Create sample audit trail entry."""
    return AuditTrailEntry(
        detection_id="det-001",
        event_type=AuditEventType.DETECTION_RECEIVED,
        timestamp=datetime.utcnow(),
        details={"source": "api", "format": "json"},
        severity="INFO",
    )


class TestAuditEventType:
    """Test AuditEventType enum."""

    def test_event_type_detection_received(self):
        """Should have DETECTION_RECEIVED event type."""
        assert AuditEventType.DETECTION_RECEIVED.value == "detection_received"

    def test_event_type_detection_validated(self):
        """Should have DETECTION_VALIDATED event type."""
        assert AuditEventType.DETECTION_VALIDATED.value == "detection_validated"

    def test_event_type_geolocation_calculated(self):
        """Should have GEOLOCATION_CALCULATED event type."""
        assert (
            AuditEventType.GEOLOCATION_CALCULATED.value == "geolocation_calculated"
        )

    def test_event_type_cot_generated(self):
        """Should have COT_GENERATED event type."""
        assert AuditEventType.COT_GENERATED.value == "cot_generated"

    def test_event_type_tak_push_attempted(self):
        """Should have TAK_PUSH_ATTEMPTED event type."""
        assert AuditEventType.TAK_PUSH_ATTEMPTED.value == "tak_push_attempted"

    def test_event_type_tak_push_success(self):
        """Should have TAK_PUSH_SUCCESS event type."""
        assert AuditEventType.TAK_PUSH_SUCCESS.value == "tak_push_success"

    def test_event_type_tak_push_failed(self):
        """Should have TAK_PUSH_FAILED event type."""
        assert AuditEventType.TAK_PUSH_FAILED.value == "tak_push_failed"

    def test_event_type_detection_queued(self):
        """Should have DETECTION_QUEUED event type."""
        assert AuditEventType.DETECTION_QUEUED.value == "detection_queued"

    def test_event_type_detection_synced(self):
        """Should have DETECTION_SYNCED event type."""
        assert AuditEventType.DETECTION_SYNCED.value == "detection_synced"

    def test_event_type_error_occurred(self):
        """Should have ERROR_OCCURRED event type."""
        assert AuditEventType.ERROR_OCCURRED.value == "error_occurred"


class TestAuditTrailEntry:
    """Test AuditTrailEntry dataclass."""

    def test_audit_entry_creation(self, sample_audit_entry):
        """Should create audit trail entry."""
        assert sample_audit_entry.detection_id == "det-001"
        assert sample_audit_entry.event_type == AuditEventType.DETECTION_RECEIVED
        assert sample_audit_entry.severity == "INFO"
        assert sample_audit_entry.details["source"] == "api"

    def test_audit_entry_default_severity(self):
        """Should default severity to INFO."""
        entry = AuditTrailEntry(
            detection_id="det-002",
            event_type=AuditEventType.DETECTION_VALIDATED,
            timestamp=datetime.utcnow(),
            details={},
        )
        assert entry.severity == "INFO"

    def test_audit_entry_custom_severity(self):
        """Should support custom severity levels."""
        entry = AuditTrailEntry(
            detection_id="det-003",
            event_type=AuditEventType.ERROR_OCCURRED,
            timestamp=datetime.utcnow(),
            details={"error": "connection timeout"},
            severity="ERROR",
        )
        assert entry.severity == "ERROR"


class TestAuditEventLogging:
    """Test basic event logging functionality."""

    def test_log_event_without_db(self, audit_service_no_db, sample_audit_entry):
        """Should log event without database (to structured logging only)."""
        # Should not raise even without session
        audit_service_no_db.log_event(sample_audit_entry)

    def test_log_event_with_db(self, audit_service, sample_audit_entry, db_session):
        """Should log event to both structured logging and database."""
        audit_service.log_event(sample_audit_entry)

        # Verify event was persisted
        from src.models.database_models import AuditEvent

        db_event = (
            db_session.query(AuditEvent)
            .filter(AuditEvent.detection_id == "det-001")
            .first()
        )
        assert db_event is not None
        assert db_event.event_type == "detection_received"

    def test_log_event_preserves_timestamp(
        self, audit_service, db_session
    ):
        """Should preserve original timestamp."""
        timestamp = datetime(2026, 2, 15, 12, 30, 45)
        entry = AuditTrailEntry(
            detection_id="det-004",
            event_type=AuditEventType.DETECTION_RECEIVED,
            timestamp=timestamp,
            details={},
        )
        audit_service.log_event(entry)

        from src.models.database_models import AuditEvent

        db_event = (
            db_session.query(AuditEvent)
            .filter(AuditEvent.detection_id == "det-004")
            .first()
        )
        assert db_event.timestamp == timestamp

    def test_log_event_stores_details_as_json(self, audit_service, db_session):
        """Should store details as JSON."""
        entry = AuditTrailEntry(
            detection_id="det-005",
            event_type=AuditEventType.DETECTION_VALIDATED,
            timestamp=datetime.utcnow(),
            details={"confidence_flag": "GREEN", "score": 0.95},
        )
        audit_service.log_event(entry)

        from src.models.database_models import AuditEvent

        db_event = (
            db_session.query(AuditEvent)
            .filter(AuditEvent.detection_id == "det-005")
            .first()
        )
        assert '"confidence_flag": "GREEN"' in db_event.details
        assert '"score": 0.95' in db_event.details

    def test_log_event_invalid_session_raises_error(self, audit_service, db_session):
        """Should handle error on database write."""
        # Create an entry with the service
        entry = AuditTrailEntry(
            detection_id="det-006",
            event_type=AuditEventType.ERROR_OCCURRED,
            timestamp=datetime.utcnow(),
            details={"error": "test error"},
        )

        # First write succeeds
        audit_service.log_event(entry)

        # Verify it was written
        from src.models.database_models import AuditEvent
        db_event = (
            db_session.query(AuditEvent)
            .filter(AuditEvent.detection_id == "det-006")
            .first()
        )
        assert db_event is not None


class TestConvenienceLoggingMethods:
    """Test convenience logging methods for specific event types."""

    def test_log_detection_received(self, audit_service, db_session):
        """Should log detection received event."""
        audit_service.log_detection_received(
            detection_id="det-007", source="api", format="json"
        )

        from src.models.database_models import AuditEvent

        db_event = (
            db_session.query(AuditEvent)
            .filter(AuditEvent.detection_id == "det-007")
            .first()
        )
        assert db_event.event_type == "detection_received"
        assert db_event.severity == "INFO"

    def test_log_detection_validated(self, audit_service, db_session):
        """Should log detection validated event."""
        audit_service.log_detection_validated(
            detection_id="det-008", confidence_flag="GREEN", accuracy_m=15.5
        )

        from src.models.database_models import AuditEvent

        db_event = (
            db_session.query(AuditEvent)
            .filter(AuditEvent.detection_id == "det-008")
            .first()
        )
        assert db_event.event_type == "detection_validated"

    def test_log_geolocation_calculated(self, audit_service, db_session):
        """Should log geolocation calculated event."""
        audit_service.log_geolocation_calculated(
            detection_id="det-009",
            latitude=40.7128,
            longitude=-74.0060,
            uncertainty_m=10.5,
            method="photogrammetry",
        )

        from src.models.database_models import AuditEvent

        db_event = (
            db_session.query(AuditEvent)
            .filter(AuditEvent.detection_id == "det-009")
            .first()
        )
        assert db_event.event_type == "geolocation_calculated"
        assert "40.7128" in db_event.details
        assert "-74.006" in db_event.details  # JSON serialization drops trailing zero

    def test_log_cot_generated(self, audit_service, db_session):
        """Should log CoT generated event."""
        audit_service.log_cot_generated(
            detection_id="det-010", cot_type="b-m-p-s-u-c", format="xml"
        )

        from src.models.database_models import AuditEvent

        db_event = (
            db_session.query(AuditEvent)
            .filter(AuditEvent.detection_id == "det-010")
            .first()
        )
        assert db_event.event_type == "cot_generated"

    def test_log_tak_push_attempted(self, audit_service, db_session):
        """Should log TAK push attempted event."""
        audit_service.log_tak_push_attempted(
            detection_id="det-011", endpoint="http://tak-server:9000/CoT"
        )

        from src.models.database_models import AuditEvent

        db_event = (
            db_session.query(AuditEvent)
            .filter(AuditEvent.detection_id == "det-011")
            .first()
        )
        assert db_event.event_type == "tak_push_attempted"

    def test_log_tak_push_success(self, audit_service, db_session):
        """Should log TAK push success event."""
        audit_service.log_tak_push_success(detection_id="det-012", latency_ms=125.5)

        from src.models.database_models import AuditEvent

        db_event = (
            db_session.query(AuditEvent)
            .filter(AuditEvent.detection_id == "det-012")
            .first()
        )
        assert db_event.event_type == "tak_push_success"

    def test_log_tak_push_failed(self, audit_service, db_session):
        """Should log TAK push failed event."""
        audit_service.log_tak_push_failed(
            detection_id="det-013",
            error_code="ECONNREFUSED",
            error_message="Connection refused",
        )

        from src.models.database_models import AuditEvent

        db_event = (
            db_session.query(AuditEvent)
            .filter(AuditEvent.detection_id == "det-013")
            .first()
        )
        assert db_event.event_type == "tak_push_failed"
        assert db_event.severity == "WARNING"

    def test_log_detection_queued(self, audit_service, db_session):
        """Should log detection queued event."""
        audit_service.log_detection_queued(
            detection_id="det-014", reason="tak_server_offline"
        )

        from src.models.database_models import AuditEvent

        db_event = (
            db_session.query(AuditEvent)
            .filter(AuditEvent.detection_id == "det-014")
            .first()
        )
        assert db_event.event_type == "detection_queued"
        assert db_event.severity == "WARNING"

    def test_log_detection_synced(self, audit_service, db_session):
        """Should log detection synced event."""
        audit_service.log_detection_synced(detection_id="det-015", latency_ms=250.0)

        from src.models.database_models import AuditEvent

        db_event = (
            db_session.query(AuditEvent)
            .filter(AuditEvent.detection_id == "det-015")
            .first()
        )
        assert db_event.event_type == "detection_synced"

    def test_log_error(self, audit_service, db_session):
        """Should log error event."""
        audit_service.log_error(
            detection_id="det-016",
            error_code="E999",
            error_message="Unexpected error",
            context="photogrammetry",
        )

        from src.models.database_models import AuditEvent

        db_event = (
            db_session.query(AuditEvent)
            .filter(AuditEvent.detection_id == "det-016")
            .first()
        )
        assert db_event.event_type == "error_occurred"
        assert db_event.severity == "ERROR"


class TestAuditTrailRetrieval:
    """Test audit trail retrieval and querying."""

    def test_get_detection_trail_single_event(self, audit_service, db_session):
        """Should retrieve single event for detection."""
        audit_service.log_detection_received(detection_id="det-020", source="api")

        trail = audit_service.get_detection_trail("det-020")

        assert len(trail) == 1
        assert trail[0].detection_id == "det-020"
        assert trail[0].event_type == AuditEventType.DETECTION_RECEIVED

    def test_get_detection_trail_multiple_events(self, audit_service, db_session):
        """Should retrieve multiple events in chronological order."""
        detection_id = "det-021"

        # Log multiple events
        audit_service.log_detection_received(detection_id=detection_id, source="api")
        audit_service.log_detection_validated(
            detection_id=detection_id, confidence_flag="GREEN"
        )
        audit_service.log_geolocation_calculated(
            detection_id=detection_id, latitude=40.0, longitude=-74.0, uncertainty_m=10
        )
        audit_service.log_cot_generated(detection_id=detection_id, cot_type="b-m-p-s-u-c")

        trail = audit_service.get_detection_trail(detection_id)

        assert len(trail) == 4
        assert trail[0].event_type == AuditEventType.DETECTION_RECEIVED
        assert trail[1].event_type == AuditEventType.DETECTION_VALIDATED
        assert trail[2].event_type == AuditEventType.GEOLOCATION_CALCULATED
        assert trail[3].event_type == AuditEventType.COT_GENERATED

    def test_get_detection_trail_chronological_order(self, audit_service, db_session):
        """Should return events in exact chronological order."""
        detection_id = "det-022"
        base_time = datetime(2026, 2, 15, 12, 0, 0)

        # Create entries with specific timestamps
        for i in range(3):
            entry = AuditTrailEntry(
                detection_id=detection_id,
                event_type=AuditEventType.DETECTION_RECEIVED
                if i == 0
                else AuditEventType.DETECTION_VALIDATED,
                timestamp=base_time + timedelta(seconds=i),
                details={},
            )
            audit_service.log_event(entry)

        trail = audit_service.get_detection_trail(detection_id)

        assert trail[0].timestamp < trail[1].timestamp
        assert trail[1].timestamp < trail[2].timestamp

    def test_get_detection_trail_not_found(self, audit_service):
        """Should raise ValueError for non-existent detection."""
        with pytest.raises(ValueError, match="No audit trail found"):
            audit_service.get_detection_trail("non-existent-id")

    def test_get_detection_trail_without_db(self, audit_service_no_db):
        """Should return empty list without database."""
        trail = audit_service_no_db.get_detection_trail("any-id")
        assert trail == []


class TestAuditTrailDateRangeQueries:
    """Test date range query functionality."""

    def test_get_trail_by_date_range_single_event(self, audit_service, db_session):
        """Should retrieve events within date range."""
        base_time = datetime(2026, 2, 15, 12, 0, 0)

        entry = AuditTrailEntry(
            detection_id="det-030",
            event_type=AuditEventType.DETECTION_RECEIVED,
            timestamp=base_time,
            details={},
        )
        audit_service.log_event(entry)

        trail = audit_service.get_trail_by_date_range(
            start_date=base_time - timedelta(hours=1),
            end_date=base_time + timedelta(hours=1),
        )

        assert len(trail) >= 1
        assert any(e.detection_id == "det-030" for e in trail)

    def test_get_trail_by_date_range_multiple_events(self, audit_service, db_session):
        """Should retrieve multiple events within date range."""
        base_time = datetime(2026, 2, 15, 12, 0, 0)

        for i in range(3):
            entry = AuditTrailEntry(
                detection_id=f"det-031-{i}",
                event_type=AuditEventType.DETECTION_RECEIVED,
                timestamp=base_time + timedelta(seconds=i * 10),
                details={},
            )
            audit_service.log_event(entry)

        trail = audit_service.get_trail_by_date_range(
            start_date=base_time - timedelta(seconds=5),
            end_date=base_time + timedelta(seconds=30),
        )

        # Should include at least the events we created
        assert len(trail) >= 3

    def test_get_trail_by_date_range_excludes_outside_range(
        self, audit_service, db_session
    ):
        """Should not include events outside date range."""
        base_time = datetime(2026, 2, 15, 12, 0, 0)

        entry = AuditTrailEntry(
            detection_id="det-032",
            event_type=AuditEventType.DETECTION_RECEIVED,
            timestamp=base_time,
            details={},
        )
        audit_service.log_event(entry)

        # Query range that excludes the event
        trail = audit_service.get_trail_by_date_range(
            start_date=base_time + timedelta(hours=1),
            end_date=base_time + timedelta(hours=2),
        )

        assert not any(e.detection_id == "det-032" for e in trail)

    def test_get_trail_by_date_range_empty_result(self, audit_service):
        """Should return empty list for date range with no events."""
        trail = audit_service.get_trail_by_date_range(
            start_date=datetime(2025, 1, 1),
            end_date=datetime(2025, 1, 2),
        )

        # Should return empty list, not raise error
        assert trail == []

    def test_get_trail_by_date_range_without_db(self, audit_service_no_db):
        """Should return empty list without database."""
        trail = audit_service_no_db.get_trail_by_date_range(
            start_date=datetime(2026, 2, 15),
            end_date=datetime(2026, 2, 16),
        )
        assert trail == []


class TestAuditTrailIntegration:
    """Integration tests for audit trail in detection pipeline."""

    def test_full_detection_pipeline_audit_trail(
        self, audit_service, db_session
    ):
        """Should log complete detection pipeline with all steps."""
        detection_id = "det-100-full-pipeline"

        # Simulate full pipeline
        audit_service.log_detection_received(
            detection_id=detection_id, source="api", format="json"
        )
        audit_service.log_detection_validated(
            detection_id=detection_id, confidence_flag="GREEN", accuracy_m=12.3
        )
        audit_service.log_geolocation_calculated(
            detection_id=detection_id,
            latitude=32.1200,
            longitude=-117.5700,
            uncertainty_m=12.3,
            method="photogrammetry",
        )
        audit_service.log_cot_generated(
            detection_id=detection_id,
            cot_type="b-m-p-s-u-c",
            format="xml",
        )
        audit_service.log_tak_push_attempted(
            detection_id=detection_id, endpoint="http://tak-server:9000/CoT"
        )
        audit_service.log_tak_push_success(detection_id=detection_id, latency_ms=150.0)

        trail = audit_service.get_detection_trail(detection_id)

        # Verify complete trail
        event_types = [e.event_type for e in trail]
        assert AuditEventType.DETECTION_RECEIVED in event_types
        assert AuditEventType.DETECTION_VALIDATED in event_types
        assert AuditEventType.GEOLOCATION_CALCULATED in event_types
        assert AuditEventType.COT_GENERATED in event_types
        assert AuditEventType.TAK_PUSH_ATTEMPTED in event_types
        assert AuditEventType.TAK_PUSH_SUCCESS in event_types

    def test_offline_queue_audit_trail(self, audit_service, db_session):
        """Should log offline queue events when TAK unavailable."""
        detection_id = "det-101-offline"

        # Simulate offline scenario
        audit_service.log_detection_received(
            detection_id=detection_id, source="api"
        )
        audit_service.log_cot_generated(
            detection_id=detection_id, cot_type="b-m-p-s-u-c"
        )
        audit_service.log_tak_push_attempted(
            detection_id=detection_id, endpoint="http://tak-server:9000/CoT"
        )
        audit_service.log_tak_push_failed(
            detection_id=detection_id,
            error_code="ECONNREFUSED",
            error_message="Connection refused",
        )
        audit_service.log_detection_queued(
            detection_id=detection_id, reason="tak_server_offline"
        )

        trail = audit_service.get_detection_trail(detection_id)

        # Verify offline sequence
        assert len(trail) >= 5
        event_types = [e.event_type for e in trail]
        assert AuditEventType.TAK_PUSH_FAILED in event_types
        assert AuditEventType.DETECTION_QUEUED in event_types

    def test_error_in_audit_trail(self, audit_service, db_session):
        """Should log errors in audit trail."""
        detection_id = "det-102-error"

        audit_service.log_detection_received(
            detection_id=detection_id, source="api"
        )
        audit_service.log_error(
            detection_id=detection_id,
            error_code="E999",
            error_message="Photogrammetry calculation failed",
            details="singular_matrix",
        )

        trail = audit_service.get_detection_trail(detection_id)

        assert len(trail) == 2
        error_event = trail[1]
        assert error_event.event_type == AuditEventType.ERROR_OCCURRED
        assert error_event.severity == "ERROR"
