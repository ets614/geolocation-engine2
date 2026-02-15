"""Unit tests for CoT (Cursor on Target) XML service."""
import pytest
from datetime import datetime
from src.services.cot_service import CotService
from src.models.schemas import GeolocationValidationResult, ConfidenceFlagEnum


@pytest.fixture
def cot_service():
    """Create CoT service instance."""
    return CotService(tak_server_url="http://localhost:8080/CoT")


@pytest.fixture
def sample_geolocation():
    """Create sample geolocation result."""
    return GeolocationValidationResult(
        calculated_lat=40.7128,
        calculated_lon=-74.0060,
        confidence_flag=ConfidenceFlagEnum.GREEN,
        confidence_value=0.85,
        uncertainty_radius_meters=15.5,
        calculation_method="ground_plane_intersection",
    )


class TestCotGeneration:
    """Test CoT XML generation."""

    def test_cot_xml_structure(self, cot_service, sample_geolocation):
        """Generated CoT XML should have valid structure."""
        cot_xml = cot_service.generate_cot_xml(
            detection_id="test-001",
            geolocation=sample_geolocation,
            object_class="vehicle",
            ai_confidence=0.92,
            camera_id="camera-1",
            timestamp=datetime(2026, 2, 15, 12, 0, 0),
        )

        # Should contain XML declaration
        assert cot_xml.startswith('<?xml version="1.0"')

        # Should contain event element
        assert "<event" in cot_xml
        assert "version" in cot_xml

        # Should contain point with coordinates
        assert "<point" in cot_xml
        assert f'lat="{sample_geolocation.calculated_lat}"' in cot_xml
        assert f'lon="{sample_geolocation.calculated_lon}"' in cot_xml

    def test_cot_uid_generation(self, cot_service, sample_geolocation):
        """CoT UID should use detection ID."""
        cot_xml = cot_service.generate_cot_xml(
            detection_id="abc-123",
            geolocation=sample_geolocation,
            object_class="person",
            ai_confidence=0.75,
            camera_id="cam-x",
            timestamp=datetime.now(),
        )

        assert 'uid="Detection.abc-123"' in cot_xml

    def test_cot_type_mapping_vehicle(self, cot_service, sample_geolocation):
        """Vehicle detection should map to correct CoT type."""
        cot_xml = cot_service.generate_cot_xml(
            detection_id="det-001",
            geolocation=sample_geolocation,
            object_class="vehicle",
            ai_confidence=0.9,
            camera_id="cam-1",
            timestamp=datetime.now(),
        )

        # Vehicle type code
        assert 'type="b-m-p-s-u-c"' in cot_xml

    def test_cot_type_mapping_person(self, cot_service, sample_geolocation):
        """Person detection should map to correct CoT type."""
        cot_xml = cot_service.generate_cot_xml(
            detection_id="det-002",
            geolocation=sample_geolocation,
            object_class="person",
            ai_confidence=0.88,
            camera_id="cam-2",
            timestamp=datetime.now(),
        )

        # Person (walking) type code
        assert 'type="b-m-p-s-p-w-g"' in cot_xml

    def test_cot_confidence_in_remarks(self, cot_service, sample_geolocation):
        """Remarks should include confidence information."""
        cot_xml = cot_service.generate_cot_xml(
            detection_id="det-003",
            geolocation=sample_geolocation,
            object_class="vehicle",
            ai_confidence=0.92,
            camera_id="cam-3",
            timestamp=datetime.now(),
        )

        assert "AI Confidence: 92%" in cot_xml
        assert "Geo Confidence: GREEN" in cot_xml
        assert "Accuracy: ±15.5m" in cot_xml

    def test_cot_accuracy_in_point(self, cot_service, sample_geolocation):
        """Point element should include uncertainty as CEP."""
        cot_xml = cot_service.generate_cot_xml(
            detection_id="det-004",
            geolocation=sample_geolocation,
            object_class="vehicle",
            ai_confidence=0.85,
            camera_id="cam-4",
            timestamp=datetime.now(),
        )

        # CEP (circular error probable) should match uncertainty
        assert f'ce="{sample_geolocation.uncertainty_radius_meters}"' in cot_xml

    def test_cot_color_mapping_green(self, cot_service):
        """GREEN confidence should map to correct color."""
        geo_green = GeolocationValidationResult(
            calculated_lat=40.0,
            calculated_lon=-74.0,
            confidence_flag=ConfidenceFlagEnum.GREEN,
            confidence_value=0.85,
            uncertainty_radius_meters=10.0,
            calculation_method="ground_plane_intersection",
        )

        cot_xml = cot_service.generate_cot_xml(
            detection_id="det-005",
            geolocation=geo_green,
            object_class="vehicle",
            ai_confidence=0.9,
            camera_id="cam-5",
            timestamp=datetime.now(),
        )

        # RED color value (-65536)
        assert 'value="-65536"' in cot_xml

    def test_cot_color_mapping_yellow(self, cot_service):
        """YELLOW confidence should map to correct color."""
        geo_yellow = GeolocationValidationResult(
            calculated_lat=40.0,
            calculated_lon=-74.0,
            confidence_flag=ConfidenceFlagEnum.YELLOW,
            confidence_value=0.6,
            uncertainty_radius_meters=25.0,
            calculation_method="ground_plane_intersection",
        )

        cot_xml = cot_service.generate_cot_xml(
            detection_id="det-006",
            geolocation=geo_yellow,
            object_class="vehicle",
            ai_confidence=0.75,
            camera_id="cam-6",
            timestamp=datetime.now(),
        )

        # GREEN color value (-256)
        assert 'value="-256"' in cot_xml

    def test_cot_color_mapping_red(self, cot_service):
        """RED confidence should map to correct color."""
        geo_red = GeolocationValidationResult(
            calculated_lat=40.0,
            calculated_lon=-74.0,
            confidence_flag=ConfidenceFlagEnum.RED,
            confidence_value=0.3,
            uncertainty_radius_meters=50.0,
            calculation_method="ground_plane_intersection",
        )

        cot_xml = cot_service.generate_cot_xml(
            detection_id="det-007",
            geolocation=geo_red,
            object_class="vehicle",
            ai_confidence=0.6,
            camera_id="cam-7",
            timestamp=datetime.now(),
        )

        # BLUE color value (-16711936)
        assert 'value="-16711936"' in cot_xml

    def test_cot_contact_callsign(self, cot_service, sample_geolocation):
        """Contact element should include callsign from detection ID."""
        cot_xml = cot_service.generate_cot_xml(
            detection_id="abc-def-ghi-jkl",
            geolocation=sample_geolocation,
            object_class="vehicle",
            ai_confidence=0.9,
            camera_id="cam-8",
            timestamp=datetime.now(),
        )

        # Callsign should include first 8 chars of detection ID
        assert 'callsign="Detection-abc-def-' in cot_xml


class TestCotParsing:
    """Test CoT XML parsing to dictionary."""

    def test_cot_to_dict_structure(self, cot_service, sample_geolocation):
        """CoT XML should parse to dictionary with expected structure."""
        cot_xml = cot_service.generate_cot_xml(
            detection_id="det-001",
            geolocation=sample_geolocation,
            object_class="vehicle",
            ai_confidence=0.92,
            camera_id="cam-1",
            timestamp=datetime.now(),
        )

        cot_dict = cot_service.cot_to_dict(cot_xml)

        # Should have required fields
        assert "uid" in cot_dict
        assert "type" in cot_dict
        assert "time" in cot_dict
        assert "location" in cot_dict
        assert "metadata" in cot_dict

    def test_cot_to_dict_coordinates(self, cot_service, sample_geolocation):
        """Parsed dictionary should contain correct coordinates."""
        cot_xml = cot_service.generate_cot_xml(
            detection_id="det-002",
            geolocation=sample_geolocation,
            object_class="vehicle",
            ai_confidence=0.9,
            camera_id="cam-2",
            timestamp=datetime.now(),
        )

        cot_dict = cot_service.cot_to_dict(cot_xml)

        assert cot_dict["location"]["latitude"] == sample_geolocation.calculated_lat
        assert cot_dict["location"]["longitude"] == sample_geolocation.calculated_lon
        assert cot_dict["location"]["accuracy_meters"] == sample_geolocation.uncertainty_radius_meters

    def test_cot_to_dict_remarks(self, cot_service, sample_geolocation):
        """Parsed dictionary should include remarks."""
        cot_xml = cot_service.generate_cot_xml(
            detection_id="det-003",
            geolocation=sample_geolocation,
            object_class="vehicle",
            ai_confidence=0.85,
            camera_id="cam-3",
            timestamp=datetime.now(),
        )

        cot_dict = cot_service.cot_to_dict(cot_xml)

        assert "remarks" in cot_dict["metadata"]
        assert len(cot_dict["metadata"]["remarks"]) > 0


class TestCotConfiguration:
    """Test CoT service configuration."""

    def test_cot_service_with_tak_url(self):
        """CoT service should accept TAK server URL."""
        service = CotService(tak_server_url="http://tak-server:9000/CoT")
        assert service.tak_server_url == "http://tak-server:9000/CoT"

    def test_cot_service_without_tak_url(self):
        """CoT service should work without TAK URL."""
        service = CotService()
        assert service.tak_server_url is None
