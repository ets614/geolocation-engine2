"""Pydantic models for API validation and data serialization."""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime
from typing import Optional, Dict, Any, Literal
from enum import Enum
import base64


class ConfidenceFlagEnum(str, Enum):
    """Geolocation confidence/quality flags."""
    GREEN = "GREEN"    # High confidence calculation
    YELLOW = "YELLOW"  # Medium confidence
    RED = "RED"        # Low confidence or failed calculation


class SensorMetadata(BaseModel):
    """Camera/sensor metadata for geolocation calculation."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "location_lat": 40.7128,
                "location_lon": -74.0060,
                "location_elevation": 10.5,
                "heading": 45.0,
                "pitch": -30.0,
                "roll": 0.0,
                "focal_length": 3000.0,
                "sensor_width_mm": 6.4,
                "sensor_height_mm": 4.8,
                "image_width": 1920,
                "image_height": 1440
            }
        }
    )

    location_lat: float = Field(..., ge=-90, le=90, description="Camera latitude")
    location_lon: float = Field(..., ge=-180, le=180, description="Camera longitude")
    location_elevation: float = Field(..., description="Camera elevation in meters above ground")
    heading: float = Field(..., ge=0, le=360, description="Camera compass heading (0-360°)")
    pitch: float = Field(..., ge=-90, le=90, description="Camera elevation angle (-90 to +90°)")
    roll: float = Field(..., ge=-180, le=180, description="Camera roll/rotation around optical axis")
    focal_length: float = Field(..., gt=0, description="Focal length in pixels")
    sensor_width_mm: float = Field(..., gt=0, description="Sensor width in millimeters")
    sensor_height_mm: float = Field(..., gt=0, description="Sensor height in millimeters")
    image_width: int = Field(..., gt=0, description="Image width in pixels")
    image_height: int = Field(..., gt=0, description="Image height in pixels")


class DetectionInput(BaseModel):
    """Input model for AI detection data with image and pixel coordinates."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "image_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
                "pixel_x": 512,
                "pixel_y": 384,
                "object_class": "vehicle",
                "ai_confidence": 0.92,
                "source": "uav_detection_model_v2",
                "camera_id": "dji_phantom_4",
                "timestamp": "2026-02-15T12:00:00Z",
                "sensor_metadata": {
                    "location_lat": 40.7128,
                    "location_lon": -74.0060,
                    "location_elevation": 100.0,
                    "heading": 45.0,
                    "pitch": -30.0,
                    "roll": 0.0,
                    "focal_length": 3000.0,
                    "sensor_width_mm": 6.4,
                    "sensor_height_mm": 4.8,
                    "image_width": 1920,
                    "image_height": 1440
                }
            }
        }
    )

    image_base64: str = Field(..., description="Image data as base64-encoded string")
    pixel_x: int = Field(..., ge=0, description="Object X coordinate in image (pixels)")
    pixel_y: int = Field(..., ge=0, description="Object Y coordinate in image (pixels)")
    object_class: str = Field(..., min_length=1, description="Detected object class (vehicle, person, etc.)")
    ai_confidence: float = Field(..., ge=0, le=1, description="AI detection confidence (0-1)")
    source: str = Field(..., min_length=1, description="Detection source/model identifier")
    camera_id: str = Field(..., min_length=1, description="Camera or sensor identifier")
    timestamp: datetime = Field(..., description="Image capture timestamp in ISO8601 UTC")
    sensor_metadata: SensorMetadata = Field(..., description="Camera/sensor metadata for geolocation")

    @field_validator("ai_confidence")
    @classmethod
    def confidence_normalized(cls, v):
        """Ensure AI confidence is in 0-1 range."""
        if not (0.0 <= v <= 1.0):
            raise ValueError("AI confidence must be between 0.0 and 1.0")
        return v

    @field_validator("image_base64")
    @classmethod
    def validate_image_base64(cls, v):
        """Validate base64 encoding."""
        try:
            base64.b64decode(v, validate=True)
        except Exception:
            raise ValueError("image_base64 must be valid base64-encoded data")
        return v

    @field_validator("pixel_x")
    @classmethod
    def validate_pixel_x(cls, v, info):
        """Validate pixel X is within image bounds."""
        if 'sensor_metadata' in info.data and v >= info.data['sensor_metadata'].image_width:
            raise ValueError(f"pixel_x ({v}) must be < image_width ({info.data['sensor_metadata'].image_width})")
        return v

    @field_validator("pixel_y")
    @classmethod
    def validate_pixel_y(cls, v, info):
        """Validate pixel Y is within image bounds."""
        if 'sensor_metadata' in info.data and v >= info.data['sensor_metadata'].image_height:
            raise ValueError(f"pixel_y ({v}) must be < image_height ({info.data['sensor_metadata'].image_height})")
        return v

    @field_validator("timestamp", mode="before")
    @classmethod
    def timestamp_iso8601(cls, v):
        """Validate timestamp is ISO8601 format."""
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                raise ValueError("Timestamp must be ISO8601 format (e.g., 2026-02-15T12:00:00Z)")
        raise ValueError("Timestamp must be ISO8601 format")


class GeolocationValidationResult(BaseModel):
    """Result of geolocation calculation from image coordinates."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "calculated_lat": 40.7135,
                "calculated_lon": -74.0050,
                "confidence_flag": "GREEN",
                "confidence_value": 0.85,
                "uncertainty_radius_meters": 15.5,
                "calculation_method": "ground_plane_intersection"
            }
        }
    )

    calculated_lat: float = Field(..., ge=-90, le=90, description="Calculated latitude")
    calculated_lon: float = Field(..., ge=-180, le=180, description="Calculated longitude")
    confidence_flag: ConfidenceFlagEnum = Field(..., description="Quality of calculation (GREEN/YELLOW/RED)")
    confidence_value: float = Field(..., ge=0, le=1, description="Confidence in calculation (0-1)")
    uncertainty_radius_meters: float = Field(..., ge=0, description="Estimated error radius in meters")
    calculation_method: str = Field(..., description="Method used for calculation (e.g., ground_plane_intersection)")


class DetectionOutput(BaseModel):
    """Output model for processed detections with geolocation."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "detection_id": "550e8400-e29b-41d4-a716-446655440000",
                "calculated_lat": 40.7135,
                "calculated_lon": -74.0050,
                "confidence_flag": "GREEN",
                "confidence_value": 0.85,
                "uncertainty_radius_meters": 15.5,
                "object_class": "vehicle",
                "ai_confidence": 0.92,
                "source": "uav_detection_model_v2",
                "timestamp": "2026-02-15T12:00:00Z",
                "processed_at": "2026-02-15T12:00:01Z"
            }
        }
    )

    detection_id: str = Field(..., description="Unique detection identifier")
    calculated_lat: float = Field(..., ge=-90, le=90, description="Calculated latitude")
    calculated_lon: float = Field(..., ge=-180, le=180, description="Calculated longitude")
    confidence_flag: ConfidenceFlagEnum = Field(..., description="Geolocation confidence (GREEN/YELLOW/RED)")
    confidence_value: float = Field(..., ge=0, le=1, description="Confidence in geolocation (0-1)")
    uncertainty_radius_meters: float = Field(..., ge=0, description="Estimated error radius")
    object_class: str = Field(..., description="Detected object class")
    ai_confidence: float = Field(..., ge=0, le=1, description="AI detection confidence")
    source: str = Field(..., description="Detection source/model")
    timestamp: datetime = Field(..., description="Image capture timestamp")
    processed_at: datetime = Field(default_factory=datetime.utcnow, description="Processing timestamp")


class ErrorResponse(BaseModel):
    """Error response model."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error_code": "E001",
                "error_message": "Invalid JSON: coordinate out of bounds",
                "details": {"field": "latitude", "constraint": "-90 <= value <= 90"}
            }
        }
    )

    error_code: str = Field(..., description="Machine-readable error code")
    error_message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class APIRequest(BaseModel):
    """Generic API request wrapper."""

    detection: DetectionInput
    request_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class APIResponse(BaseModel):
    """Generic API response wrapper."""

    status: Literal["success", "error"]
    data: Optional[Any] = None
    error: Optional[ErrorResponse] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
