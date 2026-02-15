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
  Scenario: Ingest detection from image pixels and output to TAK CoT
    Given a camera is located at latitude 32.1200, longitude -117.5700, elevation 1000m
    And the camera has heading 45°, pitch -30°, roll 0°
    And focal length is 50mm, sensor 36x24mm, image 1920x1440 pixels
    When I POST a detection with the following properties:
      | field                    | value                    |
      | image_base64             | [valid base64 image]     |
      | pixel_x                  | 960                      |
      | pixel_y                  | 720                      |
      | object_class             | fire                     |
      | ai_confidence            | 0.92                     |
      | camera_id                | cam-001                  |
      | timestamp                | 2026-02-15T14:35:42Z     |
    Then the detection is received with HTTP status 201 Created
    And the response includes a detection_id
    And the detection_id format is valid UUID
    And photogrammetry calculates coordinates from pixels + camera metadata
    And geolocation validation returns GREEN (accurate geolocation)
    And confidence flag is computed from ray-to-ground angle
    And the detection is transformed to CoT XML with type b-i-x-f-f (fire)
    And CoT includes point element: lat, lon, ce (uncertainty)
    And CoT includes detail element: color (-256 for GREEN), remarks with AI confidence
    And TAK server receives the CoT XML within 2 seconds
    And detection appears on TAK map at calculated coordinates
    And accuracy circle matches photogrammetry uncertainty
    And audit trail records all processing steps (geolocate, validate, cot_generate, tak_push)
    And system health check reports UP status

  @milestone_1 @skip
  Scenario: Multiple detections with different types flow end-to-end
    Given detections from three different object classes:
      | class        | ai_confidence | pixels_in_image | expected_cot_type |
      | vehicle      | 0.92          | (640, 480)      | b-m-p-s-u-c       |
      | person       | 0.85          | (800, 600)      | b-m-p-s-p-w-g     |
      | aircraft     | 0.78          | (1000, 300)     | b-m-p-a           |
    When detections are submitted with image pixels and camera metadata
    Then each detection is geolocated via photogrammetry
    And each detection is validated independently
    And each detection produces valid CoT XML with correct type code
    And all three appear on TAK map within 2 seconds with correct symbology
    And confidence flags are calculated consistently (all based on ray angle)
    And accuracy circles match photogrammetry uncertainty
    And audit trail shows all three detections with type attribution

  @milestone_1 @skip
  Scenario: System handles network outage transparently
    Given a fire detection is ready for output to TAK as CoT XML
    And the network connection to TAK Server is lost
    When the system attempts HTTP PUT /CoT
    Then the push fails initially (connection refused)
    And the CoT XML is written to local SQLite queue (PENDING_SYNC)
    And status dashboard shows "TAK: OFFLINE (1 pending)"
    And system continues accepting new detections (no blocking)
    When network connectivity is restored after 30 seconds
    Then system automatically detects connection restored
    And CoT detection is synced to TAK within 2 seconds
    And status dashboard shows "TAK: ONLINE (0 pending)"
    And all detections appear on map with correct coordinates and symbology

  @milestone_1 @skip
  Scenario: Deployment smoke test - All components ready
    Given the system is freshly deployed
    When the health check endpoint is called
    Then response status is 200 OK
    And response includes component status:
      | component               | status | details           |
      | api_server              | UP     | listening on 8000 |
      | database                | UP     | 0 detections      |
      | tak_server              | UP     | ping successful   |
      | offline_queue           | UP     | 0 queued          |
      | photogrammetry_service  | UP     | ready             |
      | cot_service             | UP     | ready             |
    And database schema is initialized with detection table
    And API documentation is available at /docs
    And CoT example output available for testing
