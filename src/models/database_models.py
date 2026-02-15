"""SQLAlchemy database models for Detection to COP integration."""
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    JSON,
    Index,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Detection(Base):
    """Detection event model."""

    __tablename__ = "detections"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(255), nullable=False)
    class_name = Column(String(255), nullable=False)
    confidence = Column(Float, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    accuracy = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (Index("idx_timestamp", "timestamp"),)


class OfflineQueue(Base):
    """Offline queue for storing detections to sync later."""

    __tablename__ = "offline_queue"

    id = Column(Integer, primary_key=True, index=True)
    detection_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    synced_at = Column(DateTime, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)

    __table_args__ = (Index("idx_synced_at", "synced_at"),)


class AuditTrail(Base):
    """Audit trail for tracking actions and system events."""

    __tablename__ = "audit_trail"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String(255), nullable=False)
    source = Column(String(255), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    details = Column(JSON, nullable=True)
    status = Column(String(50), nullable=False)

    __table_args__ = (Index("idx_audit_timestamp", "timestamp"),)
