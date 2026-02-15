"""Pydantic v2 validation schemas with comprehensive input validation."""
from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
    ConfigDict,
    StringConstraints,
    field_serializer,
)
from typing import Optional, Dict, Any, Literal, Annotated
from enum import Enum
import base64
import re
from datetime import datetime, timedelta


class ValidationErrorResponse(BaseModel):
    """Detailed validation error response."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "field": "pixel_x",
            "error_code": "V001",
            "message": "Value 2000 exceeds maximum image width 1920",
            "constraint": "max_value",
        }
    })

    field: str = Field(..., description="Field name with error")
    error_code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    constraint: str = Field(..., description="Constraint that was violated")


class SafeString(str):
    """String type with automatic sanitization."""

    @classmethod
    def __get_validators__(cls):
        """Provide validators for Pydantic v2."""
        yield cls.validate

    @classmethod
    def validate(cls, v):
        """Validate and sanitize string."""
        if not isinstance(v, str):
            raise ValueError("Must be a string")

        # Prevent null bytes
        if "\x00" in v:
            raise ValueError("Input contains null bytes (invalid)")

        return v


# Field constraints
ClientIdField = Annotated[
    str,
    StringConstraints(min_length=1, max_length=255, pattern=r"^[a-zA-Z0-9_-]+$")
]

ObjectClassField = Annotated[
    str,
    StringConstraints(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
]

SourceField = Annotated[
    str,
    StringConstraints(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_.-]+$")
]

CameraIdField = Annotated[
    str,
    StringConstraints(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_.-]+$")
]


class TokenRequestSchema(BaseModel):
    """Validated token request schema."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "client_id": "detector-001",
            "expires_in_minutes": 60,
        }
    })

    client_id: ClientIdField = Field(
        ...,
        description="Client identifier (alphanumeric, dash, underscore only)"
    )
    expires_in_minutes: int = Field(
        default=60,
        ge=1,
        le=10080,  # 7 days max
        description="Token expiration in minutes (1-10080, default 60)"
    )

    @field_validator("client_id")
    @classmethod
    def validate_client_id(cls, v):
        """Validate client_id for injection attacks."""
        if not v or not v.strip():
            raise ValueError("client_id cannot be empty or whitespace")

        # Check for SQL injection patterns
        sql_patterns = [
            r"['\";]",  # Quotes and semicolons
            r"(--)",    # SQL comments
            r"(/\*)",   # SQL comments
            r"(\b(union|select|drop|insert|update|delete)\b)",
        ]

        for pattern in sql_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError("client_id contains invalid characters (security)")

        return v


class SensorMetadataSchema(BaseModel):
    """Validated sensor metadata with all constraints."""

    model_config = ConfigDict(json_schema_extra={
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
    })

    location_lat: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="Camera latitude (-90 to 90)"
    )
    location_lon: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="Camera longitude (-180 to 180)"
    )
    location_elevation: float = Field(
        ...,
        ge=-500.0,
        le=10000.0,
        description="Elevation in meters above sea level"
    )
    heading: float = Field(
        ...,
        ge=0.0,
        le=360.0,
        description="Compass heading (0-360 degrees)"
    )
    pitch: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="Vertical tilt (-90 to 90 degrees)"
    )
    roll: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="Roll rotation (-180 to 180 degrees)"
    )
    focal_length: float = Field(
        ...,
        gt=0,
        le=100000.0,
        description="Focal length in pixels (positive)"
    )
    sensor_width_mm: float = Field(
        ...,
        gt=0,
        le=100.0,
        description="Sensor width in millimeters (positive)"
    )
    sensor_height_mm: float = Field(
        ...,
        gt=0,
        le=100.0,
        description="Sensor height in millimeters (positive)"
    )
    image_width: int = Field(
        ...,
        gt=0,
        le=100000,
        description="Image width in pixels (1-100000)"
    )
    image_height: int = Field(
        ...,
        gt=0,
        le=100000,
        description="Image height in pixels (1-100000)"
    )


class DetectionInputSchema(BaseModel):
    """Comprehensive validated detection input."""

    model_config = ConfigDict(json_schema_extra={
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
    })

    image_base64: str = Field(
        ...,
        min_length=50,  # Minimum reasonable base64 image size
        max_length=10_000_000,  # 10MB base64
        description="Base64-encoded image (50B - 10MB)"
    )
    pixel_x: int = Field(
        ...,
        ge=0,
        le=100000,
        description="Object X coordinate in image (0-100000)"
    )
    pixel_y: int = Field(
        ...,
        ge=0,
        le=100000,
        description="Object Y coordinate in image (0-100000)"
    )
    object_class: ObjectClassField = Field(
        ...,
        description="Detected object class (alphanumeric, dash, underscore)"
    )
    ai_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="AI confidence (0.0-1.0)"
    )
    source: SourceField = Field(
        ...,
        description="Detection source/model identifier"
    )
    camera_id: CameraIdField = Field(
        ...,
        description="Camera/sensor identifier"
    )
    timestamp: datetime = Field(
        ...,
        description="Image capture timestamp (ISO8601)"
    )
    sensor_metadata: SensorMetadataSchema = Field(
        ...,
        description="Camera sensor metadata"
    )

    @field_validator("image_base64")
    @classmethod
    def validate_image_base64(cls, v):
        """Validate base64 encoding."""
        try:
            base64.b64decode(v, validate=True)
        except Exception:
            raise ValueError("image_base64 must be valid base64-encoded data")

        # Ensure minimum size (at least 100 bytes decoded)
        try:
            decoded = base64.b64decode(v)
            if len(decoded) < 50:
                raise ValueError("Decoded image data is too small")
        except Exception:
            raise ValueError("Cannot decode image_base64")

        return v

    @field_validator("pixel_x")
    @classmethod
    def validate_pixel_x(cls, v, info):
        """Validate pixel X within image bounds."""
        if "sensor_metadata" in info.data:
            if v >= info.data["sensor_metadata"].image_width:
                raise ValueError(
                    f"pixel_x ({v}) must be < image_width "
                    f"({info.data['sensor_metadata'].image_width})"
                )
        return v

    @field_validator("pixel_y")
    @classmethod
    def validate_pixel_y(cls, v, info):
        """Validate pixel Y within image bounds."""
        if "sensor_metadata" in info.data:
            if v >= info.data["sensor_metadata"].image_height:
                raise ValueError(
                    f"pixel_y ({v}) must be < image_height "
                    f"({info.data['sensor_metadata'].image_height})"
                )
        return v

    @field_validator("timestamp", mode="before")
    @classmethod
    def validate_timestamp(cls, v):
        """Validate timestamp is ISO8601 and not too old/future."""
        if isinstance(v, datetime):
            ts = v
        elif isinstance(v, str):
            try:
                ts = datetime.fromisoformat(v.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                raise ValueError("Timestamp must be ISO8601 format (e.g., 2026-02-15T12:00:00Z)")
        else:
            raise ValueError("Timestamp must be ISO8601 format")

        # Check not too old (> 24 hours)
        now = datetime.utcnow().replace(tzinfo=ts.tzinfo) if ts.tzinfo else datetime.utcnow()
        if (now - ts).total_seconds() > 86400:
            raise ValueError("Timestamp is too old (> 24 hours)")

        # Check not too far in future (> 1 hour)
        if (ts - now).total_seconds() > 3600:
            raise ValueError("Timestamp is too far in future (> 1 hour)")

        return ts

    @field_validator("ai_confidence")
    @classmethod
    def validate_confidence(cls, v):
        """Validate AI confidence is properly normalized."""
        if not (0.0 <= v <= 1.0):
            raise ValueError("AI confidence must be between 0.0 and 1.0")
        return v

    @model_validator(mode="after")
    def validate_pixel_in_bounds(self):
        """Cross-field validation: pixels must be in image bounds."""
        if self.pixel_x >= self.sensor_metadata.image_width:
            raise ValueError(
                f"pixel_x ({self.pixel_x}) must be < "
                f"image_width ({self.sensor_metadata.image_width})"
            )
        if self.pixel_y >= self.sensor_metadata.image_height:
            raise ValueError(
                f"pixel_y ({self.pixel_y}) must be < "
                f"image_height ({self.sensor_metadata.image_height})"
            )
        return self


class FileUploadMetadataSchema(BaseModel):
    """File upload validation schema."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "filename": "detection_001.tiff",
            "content_type": "image/tiff",
            "size_bytes": 102400,
        }
    })

    filename: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Sanitized filename"
    )
    content_type: str = Field(
        ...,
        pattern=r"^[a-z0-9]+/[a-z0-9.+\-]+$",
        description="MIME type (e.g., image/jpeg)"
    )
    size_bytes: int = Field(
        ...,
        gt=0,
        le=100_000_000,  # 100MB
        description="File size in bytes (1B - 100MB)"
    )

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v):
        """Validate content type is in allowed list."""
        allowed = {
            "image/jpeg", "image/png", "image/tiff", "image/webp",
            "application/octet-stream",
        }
        if v not in allowed:
            raise ValueError(f"Content type {v} not allowed. Allowed: {allowed}")
        return v

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v):
        """Validate filename doesn't contain path traversal."""
        # Check for path separators
        if "/" in v or "\\" in v:
            raise ValueError("Filename cannot contain path separators")

        # Check for traversal patterns
        if ".." in v:
            raise ValueError("Filename cannot contain .. pattern")

        # Check for allowed extensions
        allowed_exts = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".webp"}
        if not any(v.lower().endswith(ext) for ext in allowed_exts):
            raise ValueError(f"File extension not allowed. Allowed: {allowed_exts}")

        # Ensure it's not just an extension
        if v.startswith("."):
            raise ValueError("Filename cannot start with .")

        return v


class CSRFTokenSchema(BaseModel):
    """CSRF token validation schema."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "token": "abc123def456ghi789jkl012mno345",
        }
    })

    token: str = Field(
        ...,
        min_length=32,
        max_length=256,
        pattern=r"^[a-zA-Z0-9_\-]+$",
        description="CSRF token (alphanumeric, dash, underscore)"
    )

    @field_validator("token")
    @classmethod
    def validate_token_format(cls, v):
        """Validate token format and length."""
        if len(v) < 32:
            raise ValueError("Token must be at least 32 characters")
        if len(v) > 256:
            raise ValueError("Token must be at most 256 characters")
        return v


class BulkDetectionInputSchema(BaseModel):
    """Bulk detection input with size limits."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "detections": [
                {
                    "image_base64": "iVBORw0KGgoAAAA...",
                    "pixel_x": 512,
                    "pixel_y": 384,
                    "object_class": "vehicle",
                    "ai_confidence": 0.92,
                    "source": "uav_model_v2",
                    "camera_id": "cam_001",
                    "timestamp": "2026-02-15T12:00:00Z",
                    "sensor_metadata": {...}
                }
            ]
        }
    })

    detections: list[DetectionInputSchema] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Detections array (1-100 items)"
    )

    @field_validator("detections")
    @classmethod
    def validate_detections_count(cls, v):
        """Validate detection count."""
        if len(v) == 0:
            raise ValueError("detections array cannot be empty")
        if len(v) > 100:
            raise ValueError("detections array cannot exceed 100 items")
        return v
