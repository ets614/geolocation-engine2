"""Detection service - accepts, geolocates, and stores detections (application service)."""
import uuid
import hashlib
from datetime import datetime
from sqlalchemy.orm import Session
import base64
from src.models.schemas import DetectionInput
from src.models.database_models import Detection
from src.services.geolocation_service import GeolocationCalculationService


class DetectionService:
    """Application service for detection acceptance, geolocation, and storage."""

    def __init__(self, session: Session, reference_elevation: float = 0.0):
        """Initialize detection service with database session.

        Args:
            session: SQLAlchemy database session
            reference_elevation: Ground reference elevation in meters (default sea level)
        """
        self.session = session
        self.geolocation_service = GeolocationCalculationService(
            reference_elevation=reference_elevation
        )

    def accept_detection(self, detection: DetectionInput) -> dict:
        """Accept, geolocate, and store a detection in the database.

        Args:
            detection: Valid detection payload with image and pixel coordinates

        Returns:
            dict: Contains detection_id and geolocation result

        Raises:
            ValueError: If detection cannot be processed or stored
        """
        try:
            # Generate unique detection ID
            detection_id = str(uuid.uuid4())

            # Hash image data for deduplication
            image_hash = hashlib.sha256(
                base64.b64decode(detection.image_base64)
            ).hexdigest()

            # Calculate geolocation from pixel coordinates using photogrammetry
            sensor = detection.sensor_metadata
            geo_result = self.geolocation_service.calculate(
                pixel_x=detection.pixel_x,
                pixel_y=detection.pixel_y,
                camera_lat=sensor.location_lat,
                camera_lon=sensor.location_lon,
                camera_elevation=sensor.location_elevation,
                camera_heading=sensor.heading,
                camera_pitch=sensor.pitch,
                camera_roll=sensor.roll,
                focal_length_pixels=sensor.focal_length,
                sensor_width_mm=sensor.sensor_width_mm,
                sensor_height_mm=sensor.sensor_height_mm,
                image_width=sensor.image_width,
                image_height=sensor.image_height,
                target_elevation=0.0,  # Ground level
            )

            # Create database record with both input and output data
            db_detection = Detection(
                detection_id=detection_id,
                source=detection.source,
                camera_id=detection.camera_id,
                object_class=detection.object_class,
                ai_confidence=detection.ai_confidence,
                timestamp=detection.timestamp,
                image_data_hash=image_hash,
                pixel_x=detection.pixel_x,
                pixel_y=detection.pixel_y,
                camera_lat=sensor.location_lat,
                camera_lon=sensor.location_lon,
                camera_elevation=sensor.location_elevation,
                camera_heading=sensor.heading,
                camera_pitch=sensor.pitch,
                camera_roll=sensor.roll,
                focal_length=sensor.focal_length,
                sensor_width_mm=sensor.sensor_width_mm,
                sensor_height_mm=sensor.sensor_height_mm,
                image_width=sensor.image_width,
                image_height=sensor.image_height,
                calculated_lat=geo_result.latitude,  # GeolocationResult has latitude, not calculated_lat
                calculated_lon=geo_result.longitude,  # GeolocationResult has longitude, not calculated_lon
                confidence_value=geo_result.confidence_value,
                confidence_flag=geo_result.confidence_flag,
                uncertainty_radius_meters=geo_result.uncertainty_radius_meters,
                calculation_method=geo_result.calculation_method,
            )

            # Store in database
            self.session.add(db_detection)
            self.session.commit()
            self.session.refresh(db_detection)

            return {
                "detection_id": detection_id,
                "geolocation": geo_result,
            }

        except Exception as e:
            self.session.rollback()
            raise ValueError(f"Failed to process detection: {str(e)}")
