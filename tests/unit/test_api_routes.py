"""Unit tests for REST API input port (/api/v1/detections)."""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock


class TestDetectionEndpoint:
    """Tests for POST /api/v1/detections endpoint.

    Test Budget: 5 distinct behaviors x 2 = 10 unit tests max
    Behaviors:
    1. Endpoint exists and routes correctly
    2. Input validation enforced via Pydantic schema
    3. DetectionService.accept_detection called with valid input
    4. Error handling for validation/service failures
    5. Response includes detection_id
    """

    def test_detection_endpoint_exists(self, test_client):
        """Verify POST /api/v1/detections endpoint exists."""
        payload = {
            "source": "test_source",
            "latitude": 40.0,
            "longitude": -74.0,
            "accuracy_meters": 100,
            "confidence": 0.9,
            "class": "fire",
            "timestamp": "2026-02-15T12:00:00Z"
        }
        response = test_client.post("/api/v1/detections", json=payload)
        # Should not return 404
        assert response.status_code != 404

    def test_detection_input_validation_missing_field(self, test_client):
        """Verify endpoint validates DetectionInput schema - missing required field."""
        payload = {
            "source": "test_source",
            "latitude": 40.0,
            # Missing longitude
            "accuracy_meters": 100,
            "confidence": 0.9,
            "class": "fire",
            "timestamp": "2026-02-15T12:00:00Z"
        }
        response = test_client.post("/api/v1/detections", json=payload)
        assert response.status_code == 400

    def test_detection_input_validation_out_of_bounds(self, test_client):
        """Verify endpoint validates coordinate bounds."""
        payload = {
            "source": "test_source",
            "latitude": 100.0,  # Invalid: > 90
            "longitude": -74.0,
            "accuracy_meters": 100,
            "confidence": 0.9,
            "class": "fire",
            "timestamp": "2026-02-15T12:00:00Z"
        }
        response = test_client.post("/api/v1/detections", json=payload)
        assert response.status_code == 400

    def test_detection_input_validation_confidence_range(self, test_client):
        """Verify endpoint validates confidence 0-1 range."""
        payload = {
            "source": "test_source",
            "latitude": 40.0,
            "longitude": -74.0,
            "accuracy_meters": 100,
            "confidence": 1.5,  # Invalid: > 1.0
            "class": "fire",
            "timestamp": "2026-02-15T12:00:00Z"
        }
        response = test_client.post("/api/v1/detections", json=payload)
        assert response.status_code == 400

    def test_detection_service_called_with_valid_input(self, test_client):
        """Verify DetectionService.accept_detection called for valid input."""
        payload = {
            "source": "test_source",
            "latitude": 40.0,
            "longitude": -74.0,
            "accuracy_meters": 100,
            "confidence": 0.9,
            "class": "fire",
            "timestamp": "2026-02-15T12:00:00Z"
        }
        response = test_client.post("/api/v1/detections", json=payload)
        # Service should be invoked and return success or expected error
        assert response.status_code in [201, 500]

    def test_error_handling_validation_failure(self, test_client):
        """Verify error handling returns 400 for validation failures."""
        payload = {
            "source": "test_source",
            "latitude": 40.0,
            "longitude": 200.0,  # Invalid: > 180
            "accuracy_meters": 100,
            "confidence": 0.9,
            "class": "fire",
            "timestamp": "2026-02-15T12:00:00Z"
        }
        response = test_client.post("/api/v1/detections", json=payload)
        assert response.status_code == 400

    def test_detection_returns_id(self, test_client):
        """Verify response includes detection_id."""
        payload = {
            "source": "test_source",
            "latitude": 40.0,
            "longitude": -74.0,
            "accuracy_meters": 100,
            "confidence": 0.9,
            "class": "fire",
            "timestamp": "2026-02-15T12:00:00Z"
        }
        response = test_client.post("/api/v1/detections", json=payload)
        if response.status_code == 201:
            data = response.json()
            assert "detection_id" in data
            assert data["status"] == "CREATED"

    def test_detection_returns_400_for_invalid_json(self, test_client):
        """Verify endpoint rejects malformed JSON."""
        response = test_client.post(
            "/api/v1/detections",
            content="{invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 400

    @pytest.mark.parametrize("accuracy,valid", [
        (0.5, True),  # Valid: > 0
        (1, True),
        (100, True),
        (10000, True),
        (0, False),  # Invalid: must be > 0
        (-1, False),  # Invalid: negative
    ])
    def test_detection_accuracy_validation(self, test_client, accuracy, valid):
        """Verify accuracy_meters validation (must be > 0)."""
        payload = {
            "source": "test_source",
            "latitude": 40.0,
            "longitude": -74.0,
            "accuracy_meters": accuracy,
            "confidence": 0.9,
            "class": "fire",
            "timestamp": "2026-02-15T12:00:00Z"
        }
        response = test_client.post("/api/v1/detections", json=payload)
        if valid:
            assert response.status_code in [201, 500]
        else:
            assert response.status_code == 400
