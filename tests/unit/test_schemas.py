"""Unit tests for Pydantic data models and schemas validation."""
import pytest
from datetime import datetime
from pydantic import ValidationError
import base64

from src.models.schemas import (
    DetectionInput,
    SensorMetadata,
    GeolocationValidationResult,
    DetectionOutput,
    ErrorResponse,
    APIRequest,
    APIResponse,
    ConfidenceFlagEnum,
)


@pytest.fixture
def sample_sensor_metadata():
    """Create sample sensor metadata fixture."""
    return SensorMetadata(
        location_lat=40.7128,
        location_lon=-74.0060,
        location_elevation=100.0,
        heading=45.0,
        pitch=-30.0,
        roll=0.0,
        focal_length=3000.0,
        sensor_width_mm=6.4,
        sensor_height_mm=4.8,
        image_width=1920,
        image_height=1440,
    )


@pytest.fixture
def sample_detection_input(sample_sensor_metadata):
    """Create sample detection input fixture with valid base64 image."""
    # Create a minimal valid PNG (1x1 pixel)
    png_bytes = base64.b64encode(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
        b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    ).decode()

    return DetectionInput(
        image_base64=png_bytes,
        pixel_x=512,
        pixel_y=384,
        object_class="vehicle",
        ai_confidence=0.92,
        source="uav_detection_model_v2",
        camera_id="dji_phantom_4",
        timestamp="2026-02-15T12:00:00Z",
        sensor_metadata=sample_sensor_metadata,
    )


# ============================================================================
# ACCEPTANCE TESTS - RED PHASE
# ============================================================================


@pytest.mark.acceptance
def test_detection_input_accepts_valid_image_and_pixels():
    """Acceptance test: DetectionInput accepts image data and pixel coordinates."""
    png_bytes = base64.b64encode(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
        b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    ).decode()

    detection = DetectionInput(
        image_base64=png_bytes,
        pixel_x=512,
        pixel_y=384,
        object_class="vehicle",
        ai_confidence=0.92,
        source="uav_detection_model_v2",
        camera_id="dji_phantom_4",
        timestamp="2026-02-15T12:00:00Z",
        sensor_metadata=SensorMetadata(
            location_lat=40.7128,
            location_lon=-74.0060,
            location_elevation=100.0,
            heading=45.0,
            pitch=-30.0,
            roll=0.0,
            focal_length=3000.0,
            sensor_width_mm=6.4,
            sensor_height_mm=4.8,
            image_width=1920,
            image_height=1440,
        ),
    )
    assert detection.pixel_x == 512
    assert detection.pixel_y == 384
    assert detection.object_class == "vehicle"


@pytest.mark.acceptance
def test_detection_input_requires_image_base64():
    """Acceptance test: DetectionInput requires valid base64-encoded image."""
    incomplete_data = {
        "image_base64": "invalid-base64!!!",
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
        },
    }
    with pytest.raises(ValidationError) as exc_info:
        DetectionInput(**incomplete_data)
    assert "image_base64" in str(exc_info.value)


@pytest.mark.acceptance
def test_ai_confidence_normalized_to_0_1():
    """Acceptance test: AI confidence must be between 0.0 and 1.0."""
    png_bytes = base64.b64encode(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
        b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    ).decode()

    # Valid confidence
    valid_data = {
        "image_base64": png_bytes,
        "pixel_x": 512,
        "pixel_y": 384,
        "object_class": "vehicle",
        "ai_confidence": 0.85,
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
        },
    }
    detection = DetectionInput(**valid_data)
    assert detection.ai_confidence == 0.85

    # Invalid confidence > 1.0
    invalid_data = valid_data.copy()
    invalid_data["ai_confidence"] = 1.5
    with pytest.raises(ValidationError):
        DetectionInput(**invalid_data)


@pytest.mark.acceptance
def test_sensor_metadata_validates_coordinate_ranges():
    """Acceptance test: Sensor metadata validates coordinate ranges."""
    # Invalid latitude > 90
    with pytest.raises(ValidationError):
        SensorMetadata(
            location_lat=95.0,  # Invalid: > 90
            location_lon=-74.0060,
            location_elevation=100.0,
            heading=45.0,
            pitch=-30.0,
            roll=0.0,
            focal_length=3000.0,
            sensor_width_mm=6.4,
            sensor_height_mm=4.8,
            image_width=1920,
            image_height=1440,
        )

    # Invalid longitude > 180
    with pytest.raises(ValidationError):
        SensorMetadata(
            location_lat=40.7128,
            location_lon=185.0,  # Invalid: > 180
            location_elevation=100.0,
            heading=45.0,
            pitch=-30.0,
            roll=0.0,
            focal_length=3000.0,
            sensor_width_mm=6.4,
            sensor_height_mm=4.8,
            image_width=1920,
            image_height=1440,
        )


@pytest.mark.acceptance
def test_geolocation_validation_result_includes_confidence():
    """Acceptance test: GeolocationValidationResult includes confidence flag."""
    result = GeolocationValidationResult(
        calculated_lat=40.7135,
        calculated_lon=-74.0050,
        confidence_flag=ConfidenceFlagEnum.GREEN,
        confidence_value=0.85,
        uncertainty_radius_meters=15.5,
        calculation_method="ground_plane_intersection",
    )
    assert result.confidence_flag == ConfidenceFlagEnum.GREEN
    assert result.confidence_value == 0.85


# ============================================================================
# UNIT TESTS - RED PHASE
# ============================================================================


@pytest.mark.parametrize("ai_confidence,should_pass", [
    (0.0, True),
    (0.5, True),
    (1.0, True),
    (0.85, True),
    (-0.1, False),
    (1.1, False),
    (2.0, False),
])
def test_ai_confidence_scale(ai_confidence, should_pass):
    """Unit test: AI confidence values validated to 0-1 scale."""
    png_bytes = base64.b64encode(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
        b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    ).decode()

    data = {
        "image_base64": png_bytes,
        "pixel_x": 512,
        "pixel_y": 384,
        "object_class": "vehicle",
        "ai_confidence": ai_confidence,
        "source": "test_model",
        "camera_id": "camera_1",
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
        },
    }
    if should_pass:
        detection = DetectionInput(**data)
        assert detection.ai_confidence == ai_confidence
    else:
        with pytest.raises(ValidationError):
            DetectionInput(**data)


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
def test_sensor_location_boundaries(latitude, longitude, should_pass):
    """Unit test: Sensor location validates coordinate boundaries."""
    if should_pass:
        sensor = SensorMetadata(
            location_lat=latitude,
            location_lon=longitude,
            location_elevation=100.0,
            heading=45.0,
            pitch=-30.0,
            roll=0.0,
            focal_length=3000.0,
            sensor_width_mm=6.4,
            sensor_height_mm=4.8,
            image_width=1920,
            image_height=1440,
        )
        assert sensor.location_lat == latitude
        assert sensor.location_lon == longitude
    else:
        with pytest.raises(ValidationError):
            SensorMetadata(
                location_lat=latitude,
                location_lon=longitude,
                location_elevation=100.0,
                heading=45.0,
                pitch=-30.0,
                roll=0.0,
                focal_length=3000.0,
                sensor_width_mm=6.4,
                sensor_height_mm=4.8,
                image_width=1920,
                image_height=1440,
            )


def test_geolocation_result_confidence_mapping():
    """Unit test: GeolocationValidationResult maps confidence to flags correctly."""
    # GREEN: confidence >= 0.75
    green_result = GeolocationValidationResult(
        calculated_lat=40.0,
        calculated_lon=-74.0,
        confidence_flag=ConfidenceFlagEnum.GREEN,
        confidence_value=0.85,
        uncertainty_radius_meters=10.0,
        calculation_method="ground_plane_intersection",
    )
    assert green_result.confidence_flag == ConfidenceFlagEnum.GREEN

    # YELLOW: 0.50 <= confidence < 0.75
    yellow_result = GeolocationValidationResult(
        calculated_lat=40.0,
        calculated_lon=-74.0,
        confidence_flag=ConfidenceFlagEnum.YELLOW,
        confidence_value=0.60,
        uncertainty_radius_meters=20.0,
        calculation_method="ground_plane_intersection",
    )
    assert yellow_result.confidence_flag == ConfidenceFlagEnum.YELLOW

    # RED: confidence < 0.50
    red_result = GeolocationValidationResult(
        calculated_lat=40.0,
        calculated_lon=-74.0,
        confidence_flag=ConfidenceFlagEnum.RED,
        confidence_value=0.30,
        uncertainty_radius_meters=50.0,
        calculation_method="ground_plane_intersection",
    )
    assert red_result.confidence_flag == ConfidenceFlagEnum.RED


def test_error_response_has_error_code():
    """Unit test: ErrorResponse includes error code and message."""
    error = ErrorResponse(
        error_code="E001",
        error_message="Invalid image data",
        details={"field": "image_base64"},
    )
    assert error.error_code == "E001"
    assert error.error_message == "Invalid image data"
    assert error.details is not None


def test_api_request_serialization(sample_detection_input):
    """Unit test: APIRequest serializes correctly."""
    request = APIRequest(detection=sample_detection_input)
    json_data = request.model_dump_json()
    assert "detection" in json_data
    assert "image_base64" in json_data


def test_api_response_deserialization():
    """Unit test: APIResponse deserializes correctly."""
    response_json = {
        "status": "success",
        "data": {
            "detection_id": "550e8400-e29b-41d4-a716-446655440000",
            "calculated_lat": 40.0,
            "calculated_lon": -74.0,
        },
        "error": None,
    }
    response = APIResponse(**response_json)
    assert response.status == "success"
    assert response.data is not None


def test_timestamp_iso8601_validation():
    """Unit test: Timestamp validates ISO8601 format."""
    png_bytes = base64.b64encode(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
        b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    ).decode()

    # Valid ISO8601
    detection = DetectionInput(
        image_base64=png_bytes,
        pixel_x=512,
        pixel_y=384,
        object_class="vehicle",
        ai_confidence=0.92,
        source="test_model",
        camera_id="camera_1",
        timestamp="2026-02-15T12:00:00Z",
        sensor_metadata=SensorMetadata(
            location_lat=40.7128,
            location_lon=-74.0060,
            location_elevation=100.0,
            heading=45.0,
            pitch=-30.0,
            roll=0.0,
            focal_length=3000.0,
            sensor_width_mm=6.4,
            sensor_height_mm=4.8,
            image_width=1920,
            image_height=1440,
        ),
    )
    assert isinstance(detection.timestamp, datetime)


def test_detection_output_structure():
    """Unit test: DetectionOutput has required fields."""
    output = DetectionOutput(
        detection_id="550e8400-e29b-41d4-a716-446655440000",
        calculated_lat=40.7135,
        calculated_lon=-74.0050,
        confidence_flag=ConfidenceFlagEnum.GREEN,
        confidence_value=0.85,
        uncertainty_radius_meters=15.5,
        object_class="vehicle",
        ai_confidence=0.92,
        source="uav_detection_model_v2",
        timestamp=datetime.fromisoformat("2026-02-15T12:00:00+00:00"),
    )
    assert output.detection_id == "550e8400-e29b-41d4-a716-446655440000"
    assert output.calculated_lat == 40.7135
    assert output.confidence_flag == ConfidenceFlagEnum.GREEN
    assert output.processed_at is not None
