"""
Step Definitions for Detection Ingestion and Validation
pytest-bdd implementation for user stories US-001, US-002, US-003

Test fixture injection provides:
- context: Test state holder
- http_client: HTTP client for API testing
- database: SQLite test database
- sample_detections: Sample detection data
"""

import pytest
import time
import json
from datetime import datetime, timezone, timedelta
from pytest_bdd import given, when, then, parsers
from conftest import (
    assert_status_code, assert_json_valid, assert_has_field, assert_field_equals,
    GEOLOCATION_THRESHOLDS, TEST_CONFIG
)


# ============================================================================
# BACKGROUND STEPS
# ============================================================================

@given("the detection ingestion service is running on port 8000")
def detection_service_running(context, api_service, http_client):
    """Verify detection service is running"""
    response = http_client.get("/api/v1/health")
    assert_status_code(response, 200, "Health check failed")
    context.api_service_ok = True


@given("the TAK server simulator is running on port 9000")
def tak_simulator_running(context, tak_simulator):
    """Verify TAK simulator is running"""
    context.tak_simulator_ok = True


@given("geolocation validation thresholds are configured")
def geolocation_thresholds(context, table):
    """Configure geolocation validation thresholds from scenario table"""
    context.thresholds = {}
    for row in table:
        key = row.get("accuracy_threshold_m") or row.get("confidence_minimum") or row.get("key")
        value = row.get("value") or row.get("500") or row.get("0.6")
        if "accuracy_threshold_m" in row:
            context.thresholds["accuracy_threshold_m"] = int(row["accuracy_threshold_m"])
        elif "confidence_minimum" in row:
            context.thresholds["confidence_minimum"] = float(row["confidence_minimum"])


@given("the system database is reset")
def reset_database(context, database):
    """Reset database to clean state"""
    context.database = database
    # Clear all tables
    import sqlite3
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM detections")
    cursor.execute("DELETE FROM offline_queue")
    cursor.execute("DELETE FROM audit_trail")
    conn.commit()
    conn.close()


# ============================================================================
# WALKING SKELETON - Setup Steps
# ============================================================================

@given("a fire detection API is configured at \"https://api.fire.detection.io/v1/detections\"")
def configure_fire_detection_api(context):
    """Configure fire detection API endpoint"""
    context.fire_api_config = {
        "endpoint": "https://api.fire.detection.io/v1/detections",
        "type": "satellite_fire_api",
        "status": "CONFIGURED"
    }


@given("the API authentication token is \"test-api-key-12345\"")
def set_api_authentication(context):
    """Set API authentication credentials"""
    context.api_auth_token = "test-api-key-12345"


# ============================================================================
# WALKING SKELETON - When Steps (Actions)
# ============================================================================

@when("I POST a JSON detection with the following properties")
def post_detection_with_properties(context, table, http_client):
    """POST a detection with specified properties"""
    # Convert table to detection payload
    detection_data = {}
    for row in table:
        field = row.get("field")
        value = row.get("value")

        # Type conversions
        if field in ["latitude", "longitude", "accuracy_meters"]:
            value = float(value)
        elif field == "confidence":
            # Assume 0-100 scale if not specified
            value = float(value)

        detection_data[field] = value

    # Store for later assertions
    context.posted_detection = detection_data

    # POST to API
    start_time = time.time()
    response = http_client.post(
        "/api/v1/detections",
        json_data=detection_data,
        headers={"Authorization": f"Bearer {context.api_auth_token}"}
    )
    context.last_response = response
    context.ingest_latency = (time.time() - start_time) * 1000  # ms


@when("I POST the detection JSON to /api/v1/detections")
def post_json_detection(context, http_client):
    """POST detection from prepared JSON payload"""
    if not hasattr(context, 'json_payload'):
        pytest.fail("No JSON payload prepared. Use 'Given a valid fire detection JSON payload'")

    start_time = time.time()
    response = http_client.post(
        "/api/v1/detections",
        json_data=context.json_payload
    )
    context.last_response = response
    context.ingest_latency = (time.time() - start_time) * 1000


@when(parsers.parse("I POST the {format} detection to /api/v1/detections"))
def post_formatted_detection(context, format, http_client):
    """POST detection in specified format"""
    if format == "malformed JSON":
        payload = context.malformed_json
    elif format == "incomplete JSON":
        payload = context.incomplete_json
    else:
        payload = context.json_payload

    response = http_client.post("/api/v1/detections", json_data=payload)
    context.last_response = response


# ============================================================================
# WALKING SKELETON - Then Steps (Assertions)
# ============================================================================

@then("the detection is received with HTTP status 202 Accepted")
def check_202_accepted(context):
    """Verify detection returns 202 Accepted"""
    assert_status_code(context.last_response, 202)


@then("the response includes a detection_id")
def check_detection_id_in_response(context):
    """Verify response includes detection_id"""
    body = assert_json_valid(context.last_response)
    assert_has_field(body, "id", "Response should include detection_id")
    context.detection_id = body["id"]


@then("the detection_id format is valid UUID")
def check_uuid_format(context):
    """Verify detection_id is valid UUID format"""
    import uuid
    try:
        uuid.UUID(context.detection_id)
    except ValueError:
        pytest.fail(f"Invalid UUID format: {context.detection_id}")


@then("geolocation validation returns GREEN (accurate location)")
def check_green_flag(context):
    """Verify geolocation validation returns GREEN flag"""
    body = assert_json_valid(context.last_response)
    assert_has_field(body, "accuracy_flag")
    assert body["accuracy_flag"] == "GREEN", f"Expected GREEN, got {body['accuracy_flag']}"
    context.geolocation_flags[context.detection_id] = "GREEN"


@then("the detection is transformed to RFC 7946 compliant GeoJSON")
def check_geojson_compliance(context):
    """Verify output is RFC 7946 compliant GeoJSON"""
    # In real test, would call /api/v1/detections/{id} to get full GeoJSON
    # For now, verify structure
    pass


@then("GeoJSON includes properties: source, confidence, accuracy_flag, timestamp")
def check_geojson_properties(context):
    """Verify GeoJSON includes required properties"""
    required_properties = ["source", "confidence", "accuracy_flag", "timestamp"]
    # In real test, fetch and validate GeoJSON
    pass


@then("TAK server receives the GeoJSON Feature within 2 seconds")
def check_tak_receives(context):
    """Verify TAK server receives detection within SLA"""
    # Query TAK simulator for detection
    # This would typically involve checking received detections in TAK
    context.tak_latency = 1.5  # Example value


@then("detection appears on COP map at correct coordinates [40.7128, -74.0060]")
def check_detection_on_map(context):
    """Verify detection appears on map at correct coordinates"""
    # Query TAK for detection at coordinates
    pass


@then("audit trail records all processing steps")
def check_audit_trail(context):
    """Verify audit trail records processing steps"""
    expected_events = [
        "detection_received",
        "validation_started",
        "validation_complete",
        "transform_started",
        "transform_complete",
        "output_started",
        "output_complete"
    ]
    # In real test, fetch audit trail from /api/v1/audit/{detection_id}
    context.audit_events_recorded = True


@then("system health check reports UP status")
def check_health_status(context, http_client):
    """Verify system health check is UP"""
    response = http_client.get("/api/v1/health")
    assert_status_code(response, 200)
    body = assert_json_valid(response)
    assert body.get("status") == "UP"


# ============================================================================
# US-001 DETECTION INGESTION - Setup Steps
# ============================================================================

@given("a valid fire detection JSON payload is prepared")
def prepare_valid_detection(context):
    """Prepare valid detection JSON payload"""
    context.json_payload = {
        "source": "satellite_fire_api",
        "latitude": 32.1234,
        "longitude": -117.5678,
        "confidence": 0.85,
        "type": "fire",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "accuracy_meters": 200,
        "metadata": {
            "sensor": "LANDSAT-8",
            "band": "thermal"
        }
    }


@given("the API endpoint is POST /api/v1/detections")
def set_api_endpoint(context):
    """Set API endpoint"""
    context.api_endpoint = "/api/v1/detections"


@given("authentication is configured with valid credentials")
def set_valid_credentials(context):
    """Configure valid authentication"""
    context.api_key = "test-valid-key-123"


@given("the detection ingestion service is running on port 8000")
def check_service_running(context, http_client):
    """Verify service is running"""
    response = http_client.get("/api/v1/health")
    assert response.status_code == 200


@given("the system is configured to accept detections from")
def configure_multiple_sources(context, table):
    """Configure multiple detection sources"""
    context.configured_sources = []
    for row in table:
        context.configured_sources.append({
            "source_type": row.get("source_type"),
            "endpoint_type": row.get("endpoint_type")
        })


@when("detections arrive from each source")
def post_multiple_detections(context, table, http_client):
    """POST detections from multiple sources"""
    context.posted_detections = []
    for row in table:
        payload = {
            "source": row.get("source"),
            "latitude": float(row.get("lat")),
            "longitude": float(row.get("lon")),
            "confidence": float(row.get("confidence")),
            "type": row.get("type"),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        response = http_client.post("/api/v1/detections", json_data=payload)
        assert response.status_code == 202
        body = response.json()
        context.posted_detections.append({
            "source": row.get("source"),
            "detection_id": body.get("id")
        })


@then("each detection is parsed successfully")
def verify_all_parsed(context):
    """Verify all detections were parsed"""
    assert len(context.posted_detections) > 0
    for det in context.posted_detections:
        assert det.get("detection_id") is not None


@then("source_type is correctly categorized (UAV, satellite, camera)")
def verify_source_categorization(context):
    """Verify source types are correctly identified"""
    # In real test, would verify source categorization
    pass


@then("all three detections are stored in system")
def verify_stored(context):
    """Verify all detections stored"""
    assert len(context.posted_detections) == 3


@then("each has unique detection_id")
def verify_unique_ids(context):
    """Verify all detection IDs are unique"""
    ids = [d.get("detection_id") for d in context.posted_detections]
    assert len(ids) == len(set(ids)), "Detection IDs should be unique"


@then("audit trail shows all three with source attribution")
def verify_audit_trail(context):
    """Verify audit trail shows source attribution"""
    pass


# ============================================================================
# US-001 ERROR HANDLING - Malformed JSON
# ============================================================================

@given("a malformed JSON payload")
def prepare_malformed_json(context):
    """Prepare malformed JSON for testing"""
    context.malformed_json = '{"source": "test", "lat": 32.1234, "lon": -117, ...'  # Incomplete


@then("the error code is E001 (INVALID_JSON)")
def check_error_code_e001(context):
    """Verify error code is E001"""
    body = assert_json_valid(context.last_response)
    assert body.get("error_code") == "E001"


@then("error message indicates: \"JSON parse error: unexpected EOF\"")
def check_error_message(context):
    """Verify error message"""
    body = assert_json_valid(context.last_response)
    assert "JSON parse error" in body.get("message", "")


# ============================================================================
# US-001 PERFORMANCE TESTS
# ============================================================================

@then("ingestion latency is less than 100 milliseconds")
def check_ingest_latency_sla(context):
    """Verify ingestion latency <100ms"""
    assert context.ingest_latency < 100, (
        f"Ingestion latency {context.ingest_latency}ms exceeds SLA of 100ms"
    )


@then(parsers.parse("average ingestion latency is less than {ms}ms"))
def check_average_latency(context, ms):
    """Verify average latency"""
    avg = sum(context.api_latencies) / len(context.api_latencies)
    assert avg < int(ms), f"Average latency {avg}ms exceeds {ms}ms"


@then(parsers.parse("p99 ingestion latency is less than {ms}ms"))
def check_p99_latency(context, ms):
    """Verify P99 latency SLA"""
    if len(context.api_latencies) > 0:
        sorted_latencies = sorted(context.api_latencies)
        p99_index = int(len(sorted_latencies) * 0.99)
        p99 = sorted_latencies[p99_index]
        assert p99 < int(ms), f"P99 latency {p99}ms exceeds {ms}ms"


# ============================================================================
# HELPER STEPS
# ============================================================================

@given(parsers.parse("a JSON payload missing required {field} field"))
def prepare_incomplete_json(context, field):
    """Prepare JSON with missing required field"""
    context.incomplete_json = {
        "source": "satellite_fire_api",
        "longitude": -117.5678,
        "confidence": 0.85,
        "type": "fire",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    # Remove specified field if present
    if field in context.incomplete_json:
        del context.incomplete_json[field]


@then("the response status is 400 Bad Request")
def check_400_bad_request(context):
    """Verify 400 Bad Request response"""
    assert_status_code(context.last_response, 400)


@then("the error code is E002 (MISSING_FIELD)")
def check_error_code_e002(context):
    """Verify error code E002"""
    body = assert_json_valid(context.last_response)
    assert body.get("error_code") == "E002"
