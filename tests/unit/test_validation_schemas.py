"""Unit tests for comprehensive input validation schemas.

Test Budget: 10 distinct behaviors x 2 = 20+ unit tests
Behaviors:
1. Type validation errors return proper error codes
2. Range validation enforces min/max bounds
3. Pattern validation rejects invalid formats
4. ClientId validation rejects injection patterns
5. Image base64 validation
6. Pixel coordinate validation within image bounds
7. Timestamp validation (ISO8601, not too old/future)
8. AI confidence normalization
9. Sensor metadata cross-field validation
10. Bulk detection size limits
"""
import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError
from src.models.validation_schemas import (
    TokenRequestSchema,
    DetectionInputSchema,
    SensorMetadataSchema,
    FileUploadMetadataSchema,
    BulkDetectionInputSchema,
    CSRFTokenSchema,
)


class TestTokenRequestSchema:
    """Tests for token request validation.

    Behavior: Token requests validate client_id and expiration
    """

    def test_accepts_valid_token_request(self):
        """Verify valid token request is accepted."""
        data = {
            "client_id": "detector-001",
            "expires_in_minutes": 60,
        }
        schema = TokenRequestSchema(**data)
        assert schema.client_id == "detector-001"
        assert schema.expires_in_minutes == 60

    def test_rejects_empty_client_id(self):
        """Verify empty client_id is rejected."""
        data = {"client_id": ""}
        with pytest.raises(ValidationError) as exc_info:
            TokenRequestSchema(**data)
        assert "client_id cannot be empty" in str(exc_info.value)

    def test_rejects_whitespace_only_client_id(self):
        """Verify whitespace-only client_id is rejected."""
        data = {"client_id": "   "}
        with pytest.raises(ValidationError) as exc_info:
            TokenRequestSchema(**data)
        errors = exc_info.value.errors()
        assert len(errors) > 0

    def test_rejects_client_id_with_quotes(self):
        """Verify client_id with quotes is rejected (SQL injection)."""
        data = {"client_id": "detector'--"}
        with pytest.raises(ValidationError) as exc_info:
            TokenRequestSchema(**data)
        assert "invalid characters" in str(exc_info.value)

    def test_rejects_client_id_with_semicolon(self):
        """Verify client_id with semicolon is rejected."""
        data = {"client_id": "detector;DROP"}
        with pytest.raises(ValidationError) as exc_info:
            TokenRequestSchema(**data)
        errors = exc_info.value.errors()
        assert len(errors) > 0

    def test_rejects_negative_expiration(self):
        """Verify negative expiration is rejected."""
        data = {
            "client_id": "detector-001",
            "expires_in_minutes": -1,
        }
        with pytest.raises(ValidationError) as exc_info:
            TokenRequestSchema(**data)
        assert "greater than 0" in str(exc_info.value).lower()

    def test_rejects_excessive_expiration(self):
        """Verify expiration > 10080 minutes (7 days) is rejected."""
        data = {
            "client_id": "detector-001",
            "expires_in_minutes": 10081,
        }
        with pytest.raises(ValidationError) as exc_info:
            TokenRequestSchema(**data)
        assert "less than or equal to 10080" in str(exc_info.value).lower()

    def test_accepts_minimum_expiration(self):
        """Verify 1 minute expiration is accepted."""
        data = {
            "client_id": "detector-001",
            "expires_in_minutes": 1,
        }
        schema = TokenRequestSchema(**data)
        assert schema.expires_in_minutes == 1

    def test_accepts_maximum_expiration(self):
        """Verify 10080 minute expiration is accepted."""
        data = {
            "client_id": "detector-001",
            "expires_in_minutes": 10080,
        }
        schema = TokenRequestSchema(**data)
        assert schema.expires_in_minutes == 10080

    def test_accepts_client_id_with_dash(self):
        """Verify client_id with dash is accepted."""
        data = {"client_id": "detector-unit-001"}
        schema = TokenRequestSchema(**data)
        assert schema.client_id == "detector-unit-001"

    def test_accepts_client_id_with_underscore(self):
        """Verify client_id with underscore is accepted."""
        data = {"client_id": "detector_unit_001"}
        schema = TokenRequestSchema(**data)
        assert schema.client_id == "detector_unit_001"


class TestSensorMetadataSchema:
    """Tests for sensor metadata validation.

    Behavior: Sensor metadata validates all coordinate and camera parameters
    """

    @pytest.fixture
    def valid_metadata(self):
        return {
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
            "image_height": 1440,
        }

    def test_accepts_valid_metadata(self, valid_metadata):
        """Verify valid metadata is accepted."""
        schema = SensorMetadataSchema(**valid_metadata)
        assert schema.location_lat == 40.7128
        assert schema.location_lon == -74.0060

    def test_rejects_latitude_out_of_range_high(self, valid_metadata):
        """Verify latitude > 90 is rejected."""
        valid_metadata["location_lat"] = 91.0
        with pytest.raises(ValidationError) as exc_info:
            SensorMetadataSchema(**valid_metadata)
        assert "less than or equal to 90" in str(exc_info.value).lower()

    def test_rejects_latitude_out_of_range_low(self, valid_metadata):
        """Verify latitude < -90 is rejected."""
        valid_metadata["location_lat"] = -91.0
        with pytest.raises(ValidationError) as exc_info:
            SensorMetadataSchema(**valid_metadata)
        assert "greater than or equal to -90" in str(exc_info.value).lower()

    def test_rejects_longitude_out_of_range_high(self, valid_metadata):
        """Verify longitude > 180 is rejected."""
        valid_metadata["location_lon"] = 181.0
        with pytest.raises(ValidationError) as exc_info:
            SensorMetadataSchema(**valid_metadata)
        errors = exc_info.value.errors()
        assert len(errors) > 0

    def test_rejects_longitude_out_of_range_low(self, valid_metadata):
        """Verify longitude < -180 is rejected."""
        valid_metadata["location_lon"] = -181.0
        with pytest.raises(ValidationError) as exc_info:
            SensorMetadataSchema(**valid_metadata)
        errors = exc_info.value.errors()
        assert len(errors) > 0

    def test_rejects_heading_out_of_range(self, valid_metadata):
        """Verify heading > 360 is rejected."""
        valid_metadata["heading"] = 361.0
        with pytest.raises(ValidationError) as exc_info:
            SensorMetadataSchema(**valid_metadata)
        errors = exc_info.value.errors()
        assert len(errors) > 0

    def test_rejects_pitch_out_of_range(self, valid_metadata):
        """Verify pitch > 90 is rejected."""
        valid_metadata["pitch"] = 91.0
        with pytest.raises(ValidationError) as exc_info:
            SensorMetadataSchema(**valid_metadata)
        errors = exc_info.value.errors()
        assert len(errors) > 0

    def test_rejects_negative_focal_length(self, valid_metadata):
        """Verify negative focal length is rejected."""
        valid_metadata["focal_length"] = -1.0
        with pytest.raises(ValidationError) as exc_info:
            SensorMetadataSchema(**valid_metadata)
        errors = exc_info.value.errors()
        assert len(errors) > 0

    def test_rejects_negative_image_dimension(self, valid_metadata):
        """Verify negative image width is rejected."""
        valid_metadata["image_width"] = -1
        with pytest.raises(ValidationError) as exc_info:
            SensorMetadataSchema(**valid_metadata)
        errors = exc_info.value.errors()
        assert len(errors) > 0

    def test_rejects_zero_image_dimension(self, valid_metadata):
        """Verify zero image width is rejected."""
        valid_metadata["image_width"] = 0
        with pytest.raises(ValidationError) as exc_info:
            SensorMetadataSchema(**valid_metadata)
        errors = exc_info.value.errors()
        assert len(errors) > 0


class TestDetectionInputSchema:
    """Tests for detection input validation.

    Behavior: Detection input validates image data, coordinates, and timestamps
    """

    @pytest.fixture
    def valid_detection(self):
        return {
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
                "image_height": 1440,
            }
        }

    def test_accepts_valid_detection(self, valid_detection):
        """Verify valid detection is accepted."""
        schema = DetectionInputSchema(**valid_detection)
        assert schema.object_class == "vehicle"
        assert schema.ai_confidence == 0.92

    def test_rejects_invalid_base64(self, valid_detection):
        """Verify invalid base64 is rejected."""
        valid_detection["image_base64"] = "not base64!!!"
        with pytest.raises(ValidationError) as exc_info:
            DetectionInputSchema(**valid_detection)
        assert "base64" in str(exc_info.value).lower()

    def test_rejects_confidence_out_of_range_high(self, valid_detection):
        """Verify confidence > 1.0 is rejected."""
        valid_detection["ai_confidence"] = 1.5
        with pytest.raises(ValidationError) as exc_info:
            DetectionInputSchema(**valid_detection)
        errors = exc_info.value.errors()
        assert len(errors) > 0

    def test_rejects_confidence_negative(self, valid_detection):
        """Verify negative confidence is rejected."""
        valid_detection["ai_confidence"] = -0.1
        with pytest.raises(ValidationError) as exc_info:
            DetectionInputSchema(**valid_detection)
        errors = exc_info.value.errors()
        assert len(errors) > 0

    def test_rejects_pixel_x_out_of_bounds(self, valid_detection):
        """Verify pixel_x >= image_width is rejected."""
        valid_detection["pixel_x"] = 2000  # >= 1920
        with pytest.raises(ValidationError) as exc_info:
            DetectionInputSchema(**valid_detection)
        errors = exc_info.value.errors()
        assert len(errors) > 0

    def test_rejects_pixel_y_out_of_bounds(self, valid_detection):
        """Verify pixel_y >= image_height is rejected."""
        valid_detection["pixel_y"] = 2000  # >= 1440
        with pytest.raises(ValidationError) as exc_info:
            DetectionInputSchema(**valid_detection)
        errors = exc_info.value.errors()
        assert len(errors) > 0

    def test_rejects_timestamp_too_old(self, valid_detection):
        """Verify timestamp > 24 hours old is rejected."""
        old_time = (datetime.utcnow() - timedelta(days=2)).isoformat() + "Z"
        valid_detection["timestamp"] = old_time
        with pytest.raises(ValidationError) as exc_info:
            DetectionInputSchema(**valid_detection)
        assert "too old" in str(exc_info.value).lower()

    def test_rejects_timestamp_too_future(self, valid_detection):
        """Verify timestamp > 1 hour in future is rejected."""
        future_time = (datetime.utcnow() + timedelta(hours=2)).isoformat() + "Z"
        valid_detection["timestamp"] = future_time
        with pytest.raises(ValidationError) as exc_info:
            DetectionInputSchema(**valid_detection)
        assert "future" in str(exc_info.value).lower()

    def test_accepts_datetime_object(self, valid_detection):
        """Verify datetime object is accepted."""
        valid_detection["timestamp"] = datetime.utcnow()
        schema = DetectionInputSchema(**valid_detection)
        assert isinstance(schema.timestamp, datetime)

    def test_accepts_iso8601_string(self, valid_detection):
        """Verify ISO8601 string is accepted."""
        valid_detection["timestamp"] = datetime.utcnow().isoformat() + "Z"
        schema = DetectionInputSchema(**valid_detection)
        assert isinstance(schema.timestamp, datetime)

    def test_rejects_object_class_with_spaces(self, valid_detection):
        """Verify object_class with spaces is rejected."""
        valid_detection["object_class"] = "my vehicle"
        with pytest.raises(ValidationError) as exc_info:
            DetectionInputSchema(**valid_detection)
        errors = exc_info.value.errors()
        assert len(errors) > 0

    def test_rejects_source_with_spaces(self, valid_detection):
        """Verify source with spaces is rejected."""
        valid_detection["source"] = "my model v2"
        with pytest.raises(ValidationError) as exc_info:
            DetectionInputSchema(**valid_detection)
        errors = exc_info.value.errors()
        assert len(errors) > 0


class TestFileUploadMetadataSchema:
    """Tests for file upload validation."""

    def test_accepts_valid_upload_metadata(self):
        """Verify valid file upload metadata is accepted."""
        data = {
            "filename": "detection_001.jpg",
            "content_type": "image/jpeg",
            "size_bytes": 102400,
        }
        schema = FileUploadMetadataSchema(**data)
        assert schema.filename == "detection_001.jpg"

    def test_rejects_filename_with_path_separator(self):
        """Verify filename with / is rejected."""
        data = {
            "filename": "path/to/file.jpg",
            "content_type": "image/jpeg",
            "size_bytes": 102400,
        }
        with pytest.raises(ValidationError) as exc_info:
            FileUploadMetadataSchema(**data)
        assert "path separator" in str(exc_info.value).lower()

    def test_rejects_filename_with_parent_directory(self):
        """Verify filename with .. is rejected."""
        data = {
            "filename": "../../../etc/passwd.jpg",
            "content_type": "image/jpeg",
            "size_bytes": 102400,
        }
        with pytest.raises(ValidationError) as exc_info:
            FileUploadMetadataSchema(**data)
        assert ".." in str(exc_info.value).lower()

    def test_rejects_disallowed_content_type(self):
        """Verify disallowed content type is rejected."""
        data = {
            "filename": "evil.exe",
            "content_type": "application/x-executable",
            "size_bytes": 102400,
        }
        with pytest.raises(ValidationError) as exc_info:
            FileUploadMetadataSchema(**data)
        assert "not allowed" in str(exc_info.value).lower()

    def test_rejects_file_too_large(self):
        """Verify file > 100MB is rejected."""
        data = {
            "filename": "large_file.jpg",
            "content_type": "image/jpeg",
            "size_bytes": 101_000_000,  # > 100MB
        }
        with pytest.raises(ValidationError) as exc_info:
            FileUploadMetadataSchema(**data)
        errors = exc_info.value.errors()
        assert len(errors) > 0

    def test_rejects_file_too_small(self):
        """Verify file with 0 size is rejected."""
        data = {
            "filename": "empty.jpg",
            "content_type": "image/jpeg",
            "size_bytes": 0,
        }
        with pytest.raises(ValidationError) as exc_info:
            FileUploadMetadataSchema(**data)
        errors = exc_info.value.errors()
        assert len(errors) > 0


class TestBulkDetectionInputSchema:
    """Tests for bulk detection input with limits."""

    @pytest.fixture
    def valid_detection(self):
        return {
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
                "image_height": 1440,
            }
        }

    def test_accepts_single_detection(self, valid_detection):
        """Verify single detection in array is accepted."""
        data = {"detections": [valid_detection]}
        schema = BulkDetectionInputSchema(**data)
        assert len(schema.detections) == 1

    def test_accepts_multiple_detections(self, valid_detection):
        """Verify multiple detections are accepted."""
        data = {"detections": [valid_detection] * 5}
        schema = BulkDetectionInputSchema(**data)
        assert len(schema.detections) == 5

    def test_rejects_empty_detections_array(self):
        """Verify empty detections array is rejected."""
        data = {"detections": []}
        with pytest.raises(ValidationError) as exc_info:
            BulkDetectionInputSchema(**data)
        errors = exc_info.value.errors()
        assert len(errors) > 0

    def test_rejects_excessive_detections(self, valid_detection):
        """Verify > 100 detections is rejected."""
        data = {"detections": [valid_detection] * 101}
        with pytest.raises(ValidationError) as exc_info:
            BulkDetectionInputSchema(**data)
        errors = exc_info.value.errors()
        assert len(errors) > 0


class TestCSRFTokenSchema:
    """Tests for CSRF token validation."""

    def test_accepts_valid_token(self):
        """Verify valid token is accepted."""
        data = {"token": "abc123def456ghi789jkl012mno345pqr456"}
        schema = CSRFTokenSchema(**data)
        assert schema.token == data["token"]

    def test_rejects_token_too_short(self):
        """Verify token < 32 chars is rejected."""
        data = {"token": "short123"}
        with pytest.raises(ValidationError) as exc_info:
            CSRFTokenSchema(**data)
        assert "32 characters" in str(exc_info.value).lower()

    def test_rejects_token_too_long(self):
        """Verify token > 256 chars is rejected."""
        data = {"token": "a" * 257}
        with pytest.raises(ValidationError) as exc_info:
            CSRFTokenSchema(**data)
        assert "256 characters" in str(exc_info.value).lower()

    def test_rejects_token_with_invalid_characters(self):
        """Verify token with special chars is rejected."""
        data = {"token": "abc123!@#$%^&*()" * 3}
        with pytest.raises(ValidationError) as exc_info:
            CSRFTokenSchema(**data)
        errors = exc_info.value.errors()
        assert len(errors) > 0
