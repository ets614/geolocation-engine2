@walking_skeleton
Feature: End-to-end detection ingestion and COP output
  As a system integrator
  I want to ingest AI detection data and see it on the COP map
  So that I can validate the entire system works end-to-end

  Background:
    Given the detection ingestion service is running on port 8000
    And the TAK server simulator is running on port 9000
    And geolocation validation thresholds are configured:
      | accuracy_threshold_m | 500  |
      | confidence_minimum   | 0.6  |
    And the system database is reset

  @milestone_1 @slow
  Scenario: Ingest JSON detection and output to TAK GeoJSON
    Given a fire detection API is configured at "https://api.fire.detection.io/v1/detections"
    And the API authentication token is "test-api-key-12345"
    When I POST a JSON detection with the following properties:
      | field              | value                    |
      | latitude           | 40.7128                  |
      | longitude          | -74.0060                 |
      | confidence         | 92                       |
      | confidence_scale   | 0-100                    |
      | type               | fire                     |
      | timestamp          | 2026-02-17T14:35:42Z     |
      | accuracy_meters    | 200                      |
      | source             | satellite_fire_api       |
    Then the detection is received with HTTP status 202 Accepted
    And the response includes a detection_id
    And the detection_id format is valid UUID
    And geolocation validation returns GREEN (accurate location)
    And the detection is transformed to RFC 7946 compliant GeoJSON
    And GeoJSON includes properties: source, confidence, accuracy_flag, timestamp
    And TAK server receives the GeoJSON Feature within 2 seconds
    And detection appears on COP map at correct coordinates [40.7128, -74.0060]
    And audit trail records all processing steps
    And system health check reports UP status

  @milestone_1 @skip
  Scenario: Multiple detections from different sources flow end-to-end
    Given fire detections are configured from multiple sources:
      | source_type   | endpoint                              | format        | sample_data |
      | satellite     | https://api.fire.detection.io/api     | json          | see-below   |
      | uav           | https://uav-control.local:8443/feed  | json          | see-below   |
      | camera        | https://cctv-api.local/detections    | json          | see-below   |
    When detections arrive from all sources simultaneously (3 detections total)
    Then each detection is ingested successfully
    And each detection is validated independently
    And each detection produces valid GeoJSON
    And all three appear on TAK map within 2 seconds
    And confidence scales are normalized consistently (satellite 92, uav 0.92, camera 85)
    And audit trail shows all three detections with source attribution

  @milestone_1 @skip
  Scenario: System handles network outage transparently
    Given a fire detection is ready for output to TAK
    And the network connection to TAK is lost
    When the system attempts to output the detection
    Then the output fails initially (connection refused)
    And the detection is written to local SQLite queue (PENDING_SYNC)
    And status dashboard shows "TAK: OFFLINE (1 pending)"
    And system continues accepting new detections (no blocking)
    When network connectivity is restored after 30 seconds
    Then system automatically detects connection restored
    And detection is synced to TAK within 2 seconds
    And status dashboard shows "TAK: ONLINE (0 pending)"
    And all detections appear on map in correct order

  @milestone_1 @skip
  Scenario: Deployment smoke test - All components ready
    Given the system is freshly deployed
    When the health check endpoint is called
    Then response status is 200 OK
    And response includes component status:
      | component           | status | details           |
      | api_server          | UP     | listening on 8000 |
      | database            | UP     | 0 detections      |
      | tak_server          | UP     | ping successful   |
      | offline_queue       | UP     | 0 queued          |
      | geolocation_service | UP     | ready             |
    And all configuration sources are reachable (at least one API)
    And database schema is initialized
    And API documentation is available at /api/docs
