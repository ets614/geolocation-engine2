"""Detection service - accepts and stores detections (application service)."""
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from src.models.schemas import DetectionInput
from src.models.database_models import Detection


class DetectionService:
    """Application service for detection acceptance and storage."""

    def __init__(self, session: Session):
        """Initialize detection service with database session.

        Args:
            session: SQLAlchemy database session
        """
        self.session = session

    def accept_detection(self, detection: DetectionInput) -> str:
        """Accept and store a detection in the database.

        Args:
            detection: Valid detection payload

        Returns:
            str: UUID of stored detection

        Raises:
            ValueError: If detection cannot be stored
        """
        try:
            # Generate unique detection ID
            detection_id = str(uuid.uuid4())

            # Create database record
            db_detection = Detection(
                source=detection.source,
                class_name=detection.class_name,
                confidence=detection.confidence,
                latitude=detection.latitude,
                longitude=detection.longitude,
                accuracy=detection.accuracy_meters,
                timestamp=detection.timestamp
            )

            # Store in database
            self.session.add(db_detection)
            self.session.commit()
            self.session.refresh(db_detection)

            return detection_id

        except Exception as e:
            self.session.rollback()
            raise ValueError(f"Failed to store detection: {str(e)}")
