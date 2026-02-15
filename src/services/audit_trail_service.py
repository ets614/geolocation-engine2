"""Audit trail service for immutable event logging and compliance."""
import json
import logging
from datetime import datetime
from enum import Enum
from typing import Optional, List, Any
from dataclasses import dataclass, asdict
from sqlalchemy.orm import Session
from src.models.database_models import AuditEvent


class AuditEventType(str, Enum):
    """Types of events captured in audit trail."""

    DETECTION_RECEIVED = "detection_received"
    DETECTION_VALIDATED = "detection_validated"
    GEOLOCATION_CALCULATED = "geolocation_calculated"
    COT_GENERATED = "cot_generated"
    TAK_PUSH_ATTEMPTED = "tak_push_attempted"
    TAK_PUSH_SUCCESS = "tak_push_success"
    TAK_PUSH_FAILED = "tak_push_failed"
    DETECTION_QUEUED = "detection_queued"
    DETECTION_SYNCED = "detection_synced"
    ERROR_OCCURRED = "error_occurred"


@dataclass
class AuditTrailEntry:
    """Immutable audit trail entry."""

    detection_id: str
    event_type: AuditEventType
    timestamp: datetime
    details: dict[str, Any]
    severity: str = "INFO"  # INFO, WARNING, ERROR


class AuditTrailService:
    """Immutable event log for compliance, debugging, and operational investigation."""

    def __init__(self, session: Optional[Session] = None):
        """Initialize audit trail service.

        Args:
            session: SQLAlchemy session for persistence (optional)
        """
        self.session = session
        self.logger = logging.getLogger(__name__)

    def log_event(self, entry: AuditTrailEntry) -> None:
        """Log event to audit trail (immutable append-only log).

        Args:
            entry: AuditTrailEntry to log

        Raises:
            RuntimeError: If database write fails
        """
        try:
            # Log to structured logging first (JSON format for aggregation)
            log_data = {
                "detection_id": entry.detection_id,
                "event_type": entry.event_type.value,
                "timestamp": entry.timestamp.isoformat(),
                "severity": entry.severity,
                "details": entry.details,
            }
            self.logger.info(json.dumps(log_data))

            # Persist to database if session available
            if self.session:
                db_event = AuditEvent(
                    detection_id=entry.detection_id,
                    event_type=entry.event_type.value,
                    timestamp=entry.timestamp,
                    details=json.dumps(entry.details),
                    severity=entry.severity,
                )
                self.session.add(db_event)
                self.session.commit()

        except Exception as e:
            self.logger.error(f"Failed to write audit event: {str(e)}")
            if self.session:
                self.session.rollback()
            raise RuntimeError(f"Audit trail persistence failed: {str(e)}")

    def get_detection_trail(self, detection_id: str) -> List[AuditTrailEntry]:
        """Retrieve complete audit trail for a specific detection.

        Args:
            detection_id: Detection identifier

        Returns:
            List of audit trail entries in chronological order

        Raises:
            ValueError: If detection_id not found
        """
        if not self.session:
            return []

        try:
            db_events = (
                self.session.query(AuditEvent)
                .filter(AuditEvent.detection_id == detection_id)
                .order_by(AuditEvent.timestamp.asc())
                .all()
            )

            if not db_events:
                raise ValueError(f"No audit trail found for detection: {detection_id}")

            return [
                AuditTrailEntry(
                    detection_id=event.detection_id,
                    event_type=AuditEventType(event.event_type),
                    timestamp=event.timestamp,
                    details=json.loads(event.details),
                    severity=event.severity,
                )
                for event in db_events
            ]

        except Exception as e:
            self.logger.error(f"Failed to retrieve audit trail: {str(e)}")
            raise

    def get_trail_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[AuditTrailEntry]:
        """Query audit trail by date range (for post-incident investigation).

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of audit trail entries in date range
        """
        if not self.session:
            return []

        try:
            db_events = (
                self.session.query(AuditEvent)
                .filter(AuditEvent.timestamp >= start_date)
                .filter(AuditEvent.timestamp <= end_date)
                .order_by(AuditEvent.timestamp.asc())
                .all()
            )

            return [
                AuditTrailEntry(
                    detection_id=event.detection_id,
                    event_type=AuditEventType(event.event_type),
                    timestamp=event.timestamp,
                    details=json.loads(event.details),
                    severity=event.severity,
                )
                for event in db_events
            ]

        except Exception as e:
            self.logger.error(f"Failed to query audit trail by date: {str(e)}")
            raise

    def log_detection_received(
        self, detection_id: str, source: str, **details
    ) -> None:
        """Log detection received event."""
        entry = AuditTrailEntry(
            detection_id=detection_id,
            event_type=AuditEventType.DETECTION_RECEIVED,
            timestamp=datetime.utcnow(),
            details={"source": source, **details},
            severity="INFO",
        )
        self.log_event(entry)

    def log_detection_validated(
        self, detection_id: str, confidence_flag: str, **details
    ) -> None:
        """Log detection validated event."""
        entry = AuditTrailEntry(
            detection_id=detection_id,
            event_type=AuditEventType.DETECTION_VALIDATED,
            timestamp=datetime.utcnow(),
            details={"confidence_flag": confidence_flag, **details},
            severity="INFO",
        )
        self.log_event(entry)

    def log_geolocation_calculated(
        self,
        detection_id: str,
        latitude: float,
        longitude: float,
        uncertainty_m: float,
        **details,
    ) -> None:
        """Log geolocation calculated event."""
        entry = AuditTrailEntry(
            detection_id=detection_id,
            event_type=AuditEventType.GEOLOCATION_CALCULATED,
            timestamp=datetime.utcnow(),
            details={
                "latitude": latitude,
                "longitude": longitude,
                "uncertainty_m": uncertainty_m,
                **details,
            },
            severity="INFO",
        )
        self.log_event(entry)

    def log_cot_generated(self, detection_id: str, cot_type: str, **details) -> None:
        """Log CoT XML generated event."""
        entry = AuditTrailEntry(
            detection_id=detection_id,
            event_type=AuditEventType.COT_GENERATED,
            timestamp=datetime.utcnow(),
            details={"cot_type": cot_type, **details},
            severity="INFO",
        )
        self.log_event(entry)

    def log_tak_push_attempted(self, detection_id: str, endpoint: str) -> None:
        """Log TAK push attempted event."""
        entry = AuditTrailEntry(
            detection_id=detection_id,
            event_type=AuditEventType.TAK_PUSH_ATTEMPTED,
            timestamp=datetime.utcnow(),
            details={"endpoint": endpoint},
            severity="INFO",
        )
        self.log_event(entry)

    def log_tak_push_success(self, detection_id: str, latency_ms: float) -> None:
        """Log TAK push success event."""
        entry = AuditTrailEntry(
            detection_id=detection_id,
            event_type=AuditEventType.TAK_PUSH_SUCCESS,
            timestamp=datetime.utcnow(),
            details={"latency_ms": latency_ms},
            severity="INFO",
        )
        self.log_event(entry)

    def log_tak_push_failed(
        self, detection_id: str, error_code: str, error_message: str
    ) -> None:
        """Log TAK push failed event."""
        entry = AuditTrailEntry(
            detection_id=detection_id,
            event_type=AuditEventType.TAK_PUSH_FAILED,
            timestamp=datetime.utcnow(),
            details={"error_code": error_code, "error_message": error_message},
            severity="WARNING",
        )
        self.log_event(entry)

    def log_detection_queued(self, detection_id: str, reason: str) -> None:
        """Log detection queued to offline queue event."""
        entry = AuditTrailEntry(
            detection_id=detection_id,
            event_type=AuditEventType.DETECTION_QUEUED,
            timestamp=datetime.utcnow(),
            details={"reason": reason},
            severity="WARNING",
        )
        self.log_event(entry)

    def log_detection_synced(self, detection_id: str, latency_ms: float) -> None:
        """Log detection synced from queue event."""
        entry = AuditTrailEntry(
            detection_id=detection_id,
            event_type=AuditEventType.DETECTION_SYNCED,
            timestamp=datetime.utcnow(),
            details={"latency_ms": latency_ms},
            severity="INFO",
        )
        self.log_event(entry)

    def log_error(
        self, detection_id: str, error_code: str, error_message: str, **details
    ) -> None:
        """Log error event."""
        entry = AuditTrailEntry(
            detection_id=detection_id,
            event_type=AuditEventType.ERROR_OCCURRED,
            timestamp=datetime.utcnow(),
            details={"error_code": error_code, "error_message": error_message, **details},
            severity="ERROR",
        )
        self.log_event(entry)
