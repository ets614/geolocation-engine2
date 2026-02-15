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
    """Detection event model with photogrammetry-based geolocation."""

    __tablename__ = "detections"

    id = Column(Integer, primary_key=True, index=True)

    # Detection input metadata
    detection_id = Column(String(36), unique=True, nullable=False)
    source = Column(String(255), nullable=False)
    camera_id = Column(String(255), nullable=False)
    object_class = Column(String(255), nullable=False)
    ai_confidence = Column(Float, nullable=False)  # AI model confidence (0-1)
    timestamp = Column(DateTime, nullable=False)  # Image capture time

    # Image and pixel data
    image_data_hash = Column(String(64), nullable=True)  # SHA256 of image for deduplication
    pixel_x = Column(Integer, nullable=False)
    pixel_y = Column(Integer, nullable=False)

    # Camera sensor metadata
    camera_lat = Column(Float, nullable=False)
    camera_lon = Column(Float, nullable=False)
    camera_elevation = Column(Float, nullable=False)
    camera_heading = Column(Float, nullable=False)
    camera_pitch = Column(Float, nullable=False)
    camera_roll = Column(Float, nullable=False)
    focal_length = Column(Float, nullable=False)
    sensor_width_mm = Column(Float, nullable=False)
    sensor_height_mm = Column(Float, nullable=False)
    image_width = Column(Integer, nullable=False)
    image_height = Column(Integer, nullable=False)

    # Geolocation results
    calculated_lat = Column(Float, nullable=False)
    calculated_lon = Column(Float, nullable=False)
    confidence_value = Column(Float, nullable=False)  # Geolocation confidence (0-1)
    confidence_flag = Column(String(10), nullable=False)  # GREEN/YELLOW/RED
    uncertainty_radius_meters = Column(Float, nullable=False)
    calculation_method = Column(String(50), nullable=False, default="ground_plane_intersection")

    # Processing metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_timestamp", "timestamp"),
        Index("idx_created_at", "created_at"),
        Index("idx_detection_id", "detection_id"),
        Index("idx_confidence_flag", "confidence_flag"),
    )


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
