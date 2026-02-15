@feature_us001
Feature: Accept JSON Detection Input
  As an integration specialist
  I want to ingest AI detection data from REST APIs
  So that I can get detection data flowing into the dispatch system

  Background:
    Given the detection ingestion service is running on port 8000
    And the API endpoint is POST /api/v1/detections
    And authentication is configured with valid credentials

  @happy_path @smoke
  Scenario: System successfully ingests valid JSON detection
    Given a valid fire detection JSON payload is prepared:
      """
      {
        "source": "satellite_fire_api",
        "latitude": 32.1234,
        "longitude": -117.5678,
        "confidence": 0.85,
        "type": "fire",
        "timestamp": "2026-02-17T14:35:42Z",
        "accuracy_meters": 200,
        "metadata": {
          "sensor": "LANDSAT-8",
          "band": "thermal"
        }
      }
      """
    When I POST the detection JSON to /api/v1/detections
    Then the response status is 202 Accepted
    And the response includes detection_id in UUID format
    And the response status field is "RECEIVED"
    And an audit event is logged: "Detection received from satellite_fire_api"
    And the ingestion timestamp is recorded
    And the detection moves to validation phase
    And ingestion latency is less than 100 milliseconds

  @happy_path @milestone_1
  Scenario: System ingests detection from multiple sources
    Given the system is configured to accept detections from:
      | source_type   | endpoint_type |
      | UAV           | JSON API      |
      | satellite     | JSON API      |
      | camera        | JSON API      |
    When detections arrive from each source:
      | source    | lat     | lon      | confidence | type    |
      | uav_1     | 32.1234 | -117.5678| 0.92       | vehicle |
      | satellite | 32.4567 | -117.8901| 0.68       | fire    |
      | camera_47 | 32.7890 | -117.2345| 0.78       | person  |
    Then each detection is parsed successfully
    And source_type is correctly categorized (UAV, satellite, camera)
    And all three detections are stored in system
    And each has unique detection_id
    And audit trail shows all three with source attribution

  @error_handling @boundary
  Scenario: System handles malformed JSON gracefully
    Given a malformed JSON payload:
      """
      {
        "source": "satellite_fire_api",
        "latitude": 32.1234,
        "longitude": -117.5678,
        ... [incomplete JSON, connection drops]
      }
      """
    When I POST the malformed JSON to /api/v1/detections
    Then the response status is 400 Bad Request
    And the error code is E001 (INVALID_JSON)
    And error message indicates: "JSON parse error: unexpected EOF"
    And no detection is stored
    And system continues accepting subsequent requests
    And error is logged in audit trail
    And status dashboard health remains: "API: UP"

  @error_handling @boundary
  Scenario: System rejects detection with missing required fields
    Given a JSON payload missing required latitude field:
      """
      {
        "source": "satellite_fire_api",
        "longitude": -117.5678,
        "confidence": 0.85,
        "type": "fire",
        "timestamp": "2026-02-17T14:35:42Z"
      }
      """
    When I POST the incomplete JSON to /api/v1/detections
    Then the response status is 400 Bad Request
    And the error code is E002 (MISSING_FIELD)
    And error message indicates: "Missing required field: latitude"
    And no detection is stored
    And audit trail records the validation error

  @error_handling @boundary
  Scenario: System respects API rate limits with exponential backoff
    Given the system is configured with:
      | polling_interval | 30 seconds           |
      | max_burst_rate   | 100 requests/minute  |
    When I send 150 POST requests to /api/v1/detections within 60 seconds
    Then the first 100 requests succeed (status 202)
    And request 101 receives HTTP 429 (Too Many Requests)
    And the response includes Retry-After: 60
    And the system backs off polling to 60-second interval
    And no detections are lost (all 100 stored)
    And after 60 seconds, system resumes normal polling
    And status dashboard shows: "Rate limiting active, auto-backed off"

  @error_handling @timeout
  Scenario: System handles API timeout gracefully
    Given the detection API endpoint is configured but slow to respond
    When the system sends a detection request with 5-second timeout
    And the API does not respond within 5 seconds
    Then the request times out with error E004 (API_TIMEOUT)
    And the system continues without blocking
    And retry is scheduled with exponential backoff
    And audit trail records: "API timeout from satellite_fire_api"
    And status dashboard shows: "satellite_fire_api: DEGRADED (timeout)"

  @performance @sla
  Scenario: Ingestion meets performance SLA
    Given a batch of 100 valid fire detection JSON payloads
    When all 100 detections are POSTed to /api/v1/detections
    Then all 100 receive HTTP 202 Accepted
    And all 100 have detection_id assigned
    And average ingestion latency is less than 50ms
    And p99 ingestion latency is less than 100ms
    And no detections are dropped or duplicated
    And system remains responsive to health checks

  @reliability
  Scenario: System handles concurrent requests without data loss
    Given 10 concurrent detection API clients
    When each client sends 10 detections simultaneously (100 total)
    Then all 100 requests are accepted (HTTP 202)
    And all 100 detections are stored uniquely
    And no duplicate detection_ids are created
    And no data corruption occurs
    And database consistency is maintained

  @edge_case
  Scenario: System handles extremely precise coordinates
    Given a detection with maximum precision coordinates:
      """
      {
        "latitude": 32.123456789,
        "longitude": -117.567890123,
        "confidence": 0.95,
        "type": "fire"
      }
      """
    When I POST the detection to /api/v1/detections
    Then the response status is 202 Accepted
    And coordinates are preserved with full precision
    And no rounding errors occur in storage or output
    And GeoJSON output maintains precision

  @logging
  Scenario: Ingestion events are logged for audit trail
    Given a valid fire detection JSON
    When I POST the detection to /api/v1/detections
    Then audit trail records these events in order:
      | event_type         | details                         |
      | detection_received | source, timestamp, confidence   |
      | validation_started | check type                      |
      | ingest_complete    | detection_id, status            |
    And each event has: timestamp, detection_id, source
    And events are searchable by detection_id in audit API
    And 90-day retention is enforced on audit logs
