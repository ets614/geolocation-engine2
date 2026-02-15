"""Integration tests for REST API input port (/api/v1/detections)."""
import pytest
from datetime import datetime, timezone
import uuid


class TestDetectionAPIIntegration:
    """Integration tests for detection API - port-to-port testing.

    Test Budget: 6 distinct behaviors x 2 = 12 unit tests max
    Behaviors:
    1. POST returns 201 Created for valid input
    2. Detection is stored in database
    3. Invalid payload fields return 400
    4. Invalid coordinates rejected
    5. Response includes detection_id
    6. API accepts multiple source types
    """

    def test_post_detection_returns_201_created(self, test_client):
        """Acceptance: POST /api/v1/detections returns 201 Created."""
        payload = {
            "source": "satellite_fire_api",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "accuracy_meters": 200,
            "confidence": 0.85,
            "class": "fire",
            "timestamp": "2026-02-15T12:00:00Z"
        }
        response = test_client.post("/api/v1/detections", json=payload)
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

    def test_post_detection_stores_in_database(self, test_client, in_memory_db_session):
        """Acceptance: Detection is stored in database."""
        payload = {
            "source": "satellite_fire_api",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "accuracy_meters": 200,
            "confidence": 0.85,
            "class": "fire",
            "timestamp": "2026-02-15T12:00:00Z"
        }
        response = test_client.post("/api/v1/detections", json=payload)
        assert response.status_code == 201

        # Verify detection exists in database
        from src.models.database_models import Detection
        detection = in_memory_db_session.query(Detection).first()
        assert detection is not None
        assert detection.source == "satellite_fire_api"
        assert detection.latitude == 40.7128
        assert detection.longitude == -74.0060

    def test_detection_api_validates_required_fields(self, test_client):
        """Acceptance: Missing required fields return 400."""
        # Missing latitude
        payload = {
            "source": "satellite_fire_api",
            "longitude": -74.0060,
            "accuracy_meters": 200,
            "confidence": 0.85,
            "class": "fire",
            "timestamp": "2026-02-15T12:00:00Z"
        }
        response = test_client.post("/api/v1/detections", json=payload)
        assert response.status_code == 400

    def test_detection_api_rejects_invalid_coordinates(self, test_client):
        """Acceptance: Invalid lat/lon return 400."""
        # Latitude out of bounds
        payload = {
            "source": "satellite_fire_api",
            "latitude": 95.0,  # Invalid: >90
            "longitude": -74.0060,
            "accuracy_meters": 200,
            "confidence": 0.85,
            "class": "fire",
            "timestamp": "2026-02-15T12:00:00Z"
        }
        response = test_client.post("/api/v1/detections", json=payload)
        assert response.status_code == 400

    def test_detection_api_returns_detection_id(self, test_client):
        """Acceptance: Response includes valid detection_id."""
        payload = {
            "source": "satellite_fire_api",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "accuracy_meters": 200,
            "confidence": 0.85,
            "class": "fire",
            "timestamp": "2026-02-15T12:00:00Z"
        }
        response = test_client.post("/api/v1/detections", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert "detection_id" in data
        # Verify it's a valid UUID
        try:
            uuid.UUID(data["detection_id"])
        except ValueError:
            pytest.fail(f"detection_id is not valid UUID: {data['detection_id']}")

    @pytest.mark.parametrize("source", [
        "satellite_fire_api",
        "uav_detection",
        "camera_feed",
    ])
    def test_detection_api_accepts_multiple_sources(self, test_client, source):
        """Acceptance: API accepts detections from multiple sources."""
        payload = {
            "source": source,
            "latitude": 40.7128,
            "longitude": -74.0060,
            "accuracy_meters": 200,
            "confidence": 0.85,
            "class": "fire",
            "timestamp": "2026-02-15T12:00:00Z"
        }
        response = test_client.post("/api/v1/detections", json=payload)
        assert response.status_code == 201
        assert response.json()["detection_id"] is not None
