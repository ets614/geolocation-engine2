"""Pydantic models for API validation and data serialization."""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime
from typing import Optional, Dict, Any, Literal
from enum import Enum


class ConfidenceFlagEnum(str, Enum):
    """Confidence validation flags."""
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


class AccuracyFlagEnum(str, Enum):
    """Accuracy validation flags."""
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


class DetectionInput(BaseModel):
    """Input model for detection data from external sources."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "latitude": 40.7128,
                "longitude": -74.0060,
                "accuracy_meters": 200,
                "confidence": 0.85,
                "source": "satellite_fire_api",
                "class": "fire",
                "timestamp": "2026-02-15T12:00:00Z"
            }
        },
        populate_by_name=True
    )

    latitude: float = Field(..., ge=-90, le=90, description="Latitude coordinate (-90 to +90)")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude coordinate (-180 to +180)")
    accuracy_meters: float = Field(..., gt=0, description="Accuracy radius in meters")
    confidence: float = Field(..., ge=0, le=1, description="Confidence value normalized to 0-1 scale")
    source: str = Field(..., min_length=1, description="Detection source identifier")
    class_name: str = Field(alias="class", description="Object class or category")
    timestamp: datetime = Field(..., description="Detection timestamp in ISO8601 UTC format")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    @field_validator("confidence")
    @classmethod
    def confidence_normalized(cls, v):
        """Ensure confidence is normalized to 0-1 scale."""
        if not (0.0 <= v <= 1.0):
            raise ValueError("Confidence must be between 0.0 and 1.0")
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


class GeolocationData(BaseModel):
    """Normalized geolocation data with validation flags."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "latitude": 40.7128,
                "longitude": -74.0060,
                "accuracy_meters": 200,
                "confidence_flag": "GREEN",
                "accuracy_flag": "GREEN"
            }
        }
    )

    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    accuracy_meters: float = Field(..., gt=0)
    confidence_flag: ConfidenceFlagEnum = Field(..., description="Confidence validation flag")
    accuracy_flag: AccuracyFlagEnum = Field(..., description="Accuracy validation flag")


class DetectionOutput(BaseModel):
    """Output model for processed detections."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "detection_id": "550e8400-e29b-41d4-a716-446655440000",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "accuracy_meters": 200,
                "confidence": 0.85,
                "source": "satellite_fire_api",
                "class_name": "fire",
                "timestamp": "2026-02-15T12:00:00Z",
                "processed_at": "2026-02-15T12:00:01Z",
                "confidence_flag": "GREEN",
                "accuracy_flag": "GREEN",
                "validation_passed": True
            }
        }
    )

    detection_id: str = Field(..., description="Unique detection identifier")
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    accuracy_meters: float = Field(..., gt=0)
    confidence: float = Field(..., ge=0, le=1)
    source: str
    class_name: str
    timestamp: datetime
    processed_at: datetime = Field(default_factory=datetime.utcnow)
    confidence_flag: ConfidenceFlagEnum
    accuracy_flag: AccuracyFlagEnum
    validation_passed: bool = Field(True, description="Overall validation result")


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
