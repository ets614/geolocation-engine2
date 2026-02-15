"""Unit tests for Pydantic data models and schemas validation."""
import pytest
from datetime import datetime, timezone
from pydantic import ValidationError
from src.models.schemas import (
    DetectionInput,
    GeolocationData,
    DetectionOutput,
    ErrorResponse,
    APIRequest,
    APIResponse,
    ConfidenceFlagEnum,
    AccuracyFlagEnum,
)


# ============================================================================
# ACCEPTANCE TESTS - RED PHASE
# ============================================================================

@pytest.mark.acceptance
def test_detection_input_accepts_valid_json():
    """Acceptance test: DetectionInput accepts valid JSON with all required fields."""
    valid_data = {
        "latitude": 40.7128,
        "longitude": -74.0060,
        "accuracy_meters": 200,
        "confidence": 0.85,
        "source": "satellite_fire_api",
        "class": "fire",
        "timestamp": "2026-02-15T12:00:00Z"
    }
    detection = DetectionInput(**valid_data)
    assert detection.latitude == 40.7128
    assert detection.longitude == -74.0060
    assert detection.accuracy_meters == 200
    assert detection.confidence == 0.85
    assert detection.source == "satellite_fire_api"


@pytest.mark.acceptance
def test_detection_input_requires_lat_lon():
    """Acceptance test: DetectionInput requires latitude and longitude fields."""
    incomplete_data = {
        "accuracy_meters": 200,
        "confidence": 0.85,
        "source": "satellite_fire_api",
        "class": "fire",
        "timestamp": "2026-02-15T12:00:00Z"
    }
    with pytest.raises(ValidationError) as exc_info:
        DetectionInput(**incomplete_data)
    assert "latitude" in str(exc_info.value) or "longitude" in str(exc_info.value)


@pytest.mark.acceptance
def test_detection_input_validates_coordinate_ranges():
    """Acceptance test: DetectionInput validates coordinate ranges (±90° lat, ±180° lon)."""
    # Test invalid latitude > 90
    invalid_lat_data = {
        "latitude": 95.0,  # Invalid: > 90
        "longitude": -74.0060,
        "accuracy_meters": 200,
        "confidence": 0.85,
        "source": "satellite_fire_api",
        "class": "fire",
        "timestamp": "2026-02-15T12:00:00Z"
    }
    with pytest.raises(ValidationError):
        DetectionInput(**invalid_lat_data)

    # Test invalid longitude > 180
    invalid_lon_data = {
        "latitude": 40.7128,
        "longitude": 185.0,  # Invalid: > 180
        "accuracy_meters": 200,
        "confidence": 0.85,
        "source": "satellite_fire_api",
        "class": "fire",
        "timestamp": "2026-02-15T12:00:00Z"
    }
    with pytest.raises(ValidationError):
        DetectionInput(**invalid_lon_data)


@pytest.mark.acceptance
def test_confidence_normalized_to_0_1_scale():
    """Acceptance test: Confidence values normalized to 0-1 scale (rejects > 1.0)."""
    # Valid confidence
    valid_data = {
        "latitude": 40.7128,
        "longitude": -74.0060,
        "accuracy_meters": 200,
        "confidence": 0.85,
        "source": "satellite_fire_api",
        "class": "fire",
        "timestamp": "2026-02-15T12:00:00Z"
    }
    detection = DetectionInput(**valid_data)
    assert detection.confidence == 0.85

    # Invalid confidence > 1.0
    invalid_data = {
        "latitude": 40.7128,
        "longitude": -74.0060,
        "accuracy_meters": 200,
        "confidence": 1.5,  # Invalid: > 1.0
        "source": "satellite_fire_api",
        "class": "fire",
        "timestamp": "2026-02-15T12:00:00Z"
    }
    with pytest.raises(ValidationError):
        DetectionInput(**invalid_data)


@pytest.mark.acceptance
def test_accuracy_in_meters_validated():
    """Acceptance test: Accuracy in meters validated as positive value."""
    # Valid accuracy
    valid_data = {
        "latitude": 40.7128,
        "longitude": -74.0060,
        "accuracy_meters": 200,
        "confidence": 0.85,
        "source": "satellite_fire_api",
        "class": "fire",
        "timestamp": "2026-02-15T12:00:00Z"
    }
    detection = DetectionInput(**valid_data)
    assert detection.accuracy_meters == 200

    # Invalid accuracy (zero)
    invalid_data = {
        "latitude": 40.7128,
        "longitude": -74.0060,
        "accuracy_meters": 0,  # Invalid: not > 0
        "confidence": 0.85,
        "source": "satellite_fire_api",
        "class": "fire",
        "timestamp": "2026-02-15T12:00:00Z"
    }
    with pytest.raises(ValidationError):
        DetectionInput(**invalid_data)


@pytest.mark.acceptance
def test_timestamp_iso8601_required():
    """Acceptance test: Timestamp in ISO8601 format (UTC) required."""
    # Valid ISO8601 timestamp
    valid_data = {
        "latitude": 40.7128,
        "longitude": -74.0060,
        "accuracy_meters": 200,
        "confidence": 0.85,
        "source": "satellite_fire_api",
        "class": "fire",
        "timestamp": "2026-02-15T12:00:00Z"
    }
    detection = DetectionInput(**valid_data)
    assert isinstance(detection.timestamp, datetime)

    # Invalid timestamp format
    invalid_data = {
        "latitude": 40.7128,
        "longitude": -74.0060,
        "accuracy_meters": 200,
        "confidence": 0.85,
        "source": "satellite_fire_api",
        "class": "fire",
        "timestamp": "not-a-timestamp"
    }
    with pytest.raises(ValidationError):
        DetectionInput(**invalid_data)


@pytest.mark.acceptance
def test_source_field_required():
    """Acceptance test: Source field required and non-empty."""
    # Missing source
    missing_source = {
        "latitude": 40.7128,
        "longitude": -74.0060,
        "accuracy_meters": 200,
        "confidence": 0.85,
        "class": "fire",
        "timestamp": "2026-02-15T12:00:00Z"
    }
    with pytest.raises(ValidationError):
        DetectionInput(**missing_source)

    # Empty source
    empty_source = {
        "latitude": 40.7128,
        "longitude": -74.0060,
        "accuracy_meters": 200,
        "confidence": 0.85,
        "source": "",
        "class": "fire",
        "timestamp": "2026-02-15T12:00:00Z"
    }
    with pytest.raises(ValidationError):
        DetectionInput(**empty_source)


@pytest.mark.acceptance
def test_class_field_required():
    """Acceptance test: Class field required (aliased as 'class' in JSON)."""
    # Missing class
    missing_class = {
        "latitude": 40.7128,
        "longitude": -74.0060,
        "accuracy_meters": 200,
        "confidence": 0.85,
        "source": "satellite_fire_api",
        "timestamp": "2026-02-15T12:00:00Z"
    }
    with pytest.raises(ValidationError):
        DetectionInput(**missing_class)


# ============================================================================
# UNIT TESTS - RED PHASE
# ============================================================================

@pytest.mark.parametrize("latitude,longitude,should_pass", [
    (-90.0, -180.0, True),    # Minimum valid
    (90.0, 180.0, True),      # Maximum valid
    (0.0, 0.0, True),         # Zero (valid)
    (40.7128, -74.0060, True),  # New York
    (-33.8688, 151.2093, True), # Sydney
    (91.0, 0.0, False),        # Latitude too high
    (-91.0, 0.0, False),       # Latitude too low
    (0.0, 181.0, False),       # Longitude too high
    (0.0, -181.0, False),      # Longitude too low
])
def test_detection_input_model_validates_boundaries(latitude, longitude, should_pass):
    """Unit test: Model validates coordinate boundaries correctly."""
    data = {
        "latitude": latitude,
        "longitude": longitude,
        "accuracy_meters": 200,
        "confidence": 0.85,
        "source": "test_source",
        "class": "fire",
        "timestamp": "2026-02-15T12:00:00Z"
    }
    if should_pass:
        detection = DetectionInput(**data)
        assert detection.latitude == latitude
        assert detection.longitude == longitude
    else:
        with pytest.raises(ValidationError):
            DetectionInput(**data)


@pytest.mark.parametrize("confidence_input,should_pass", [
    (0.0, True),
    (0.5, True),
    (1.0, True),
    (0.85, True),
    (-0.1, False),
    (1.1, False),
    (2.0, False),
])
def test_detection_input_converts_confidence_scale(confidence_input, should_pass):
    """Unit test: Confidence values validated to 0-1 scale."""
    data = {
        "latitude": 40.7128,
        "longitude": -74.0060,
        "accuracy_meters": 200,
        "confidence": confidence_input,
        "source": "test_source",
        "class": "fire",
        "timestamp": "2026-02-15T12:00:00Z"
    }
    if should_pass:
        detection = DetectionInput(**data)
        assert detection.confidence == confidence_input
    else:
        with pytest.raises(ValidationError):
            DetectionInput(**data)


def test_detection_output_includes_validation_flags():
    """Unit test: DetectionOutput includes confidence and accuracy validation flags."""
    output = DetectionOutput(
        detection_id="550e8400-e29b-41d4-a716-446655440000",
        latitude=40.7128,
        longitude=-74.0060,
        accuracy_meters=200,
        confidence=0.85,
        source="satellite_fire_api",
        class_name="fire",
        timestamp=datetime.now(timezone.utc),
        confidence_flag=ConfidenceFlagEnum.GREEN,
        accuracy_flag=AccuracyFlagEnum.GREEN,
        validation_passed=True
    )
    assert output.confidence_flag == ConfidenceFlagEnum.GREEN
    assert output.accuracy_flag == AccuracyFlagEnum.GREEN
    assert output.validation_passed is True


@pytest.mark.parametrize("error_code,error_message", [
    ("E001", "Invalid JSON format"),
    ("E002", "Missing required field"),
    ("E003", "Coordinate out of bounds"),
])
def test_error_response_has_error_code(error_code, error_message):
    """Unit test: ErrorResponse includes error code and message."""
    error = ErrorResponse(
        error_code=error_code,
        error_message=error_message,
        details={"field": "latitude"}
    )
    assert error.error_code == error_code
    assert error.error_message == error_message
    assert error.details is not None


def test_api_request_serialization():
    """Unit test: APIRequest serializes correctly."""
    detection_data = {
        "latitude": 40.7128,
        "longitude": -74.0060,
        "accuracy_meters": 200,
        "confidence": 0.85,
        "source": "satellite_fire_api",
        "class": "fire",
        "timestamp": "2026-02-15T12:00:00Z"
    }
    request = APIRequest(detection=DetectionInput(**detection_data))
    json_data = request.model_dump_json()
    assert "detection" in json_data
    assert "latitude" in json_data


def test_api_response_deserialization():
    """Unit test: APIResponse deserializes correctly."""
    response_json = {
        "status": "success",
        "data": {"detection_id": "550e8400-e29b-41d4-a716-446655440000"},
        "error": None
    }
    response = APIResponse(**response_json)
    assert response.status == "success"
    assert response.data is not None


@pytest.mark.parametrize("accuracy,should_pass", [
    (1.0, True),
    (10.5, True),
    (500.0, True),
    (1000.0, True),
    (0.0, False),
    (-10.0, False),
])
def test_accuracy_positive_meters(accuracy, should_pass):
    """Unit test: Accuracy must be positive meters."""
    data = {
        "latitude": 40.7128,
        "longitude": -74.0060,
        "accuracy_meters": accuracy,
        "confidence": 0.85,
        "source": "test_source",
        "class": "fire",
        "timestamp": "2026-02-15T12:00:00Z"
    }
    if should_pass:
        detection = DetectionInput(**data)
        assert detection.accuracy_meters == accuracy
    else:
        with pytest.raises(ValidationError):
            DetectionInput(**data)


def test_geolocation_data_with_validation_flags():
    """Unit test: GeolocationData includes both confidence and accuracy flags."""
    geo = GeolocationData(
        latitude=40.7128,
        longitude=-74.0060,
        accuracy_meters=200,
        confidence_flag=ConfidenceFlagEnum.GREEN,
        accuracy_flag=AccuracyFlagEnum.YELLOW
    )
    assert geo.confidence_flag == ConfidenceFlagEnum.GREEN
    assert geo.accuracy_flag == AccuracyFlagEnum.YELLOW


@pytest.mark.parametrize("timestamp_str,should_pass", [
    ("2026-02-15T12:00:00Z", True),
    ("2026-02-15T12:00:00+00:00", True),
    ("2026-02-15", True),  # Pydantic accepts date-only ISO8601 strings
    ("not-a-timestamp", False),
    ("2026-13-45T25:99:99Z", False),  # Invalid month and time
])
def test_timestamp_iso8601_validation(timestamp_str, should_pass):
    """Unit test: Timestamp validates ISO8601 format."""
    data = {
        "latitude": 40.7128,
        "longitude": -74.0060,
        "accuracy_meters": 200,
        "confidence": 0.85,
        "source": "test_source",
        "class": "fire",
        "timestamp": timestamp_str
    }
    if should_pass:
        detection = DetectionInput(**data)
        assert isinstance(detection.timestamp, datetime)
    else:
        with pytest.raises(ValidationError):
            DetectionInput(**data)
