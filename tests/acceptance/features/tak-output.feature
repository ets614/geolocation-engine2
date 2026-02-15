@feature_us004
Feature: Output to TAK CoT XML
  As a command team dispatcher
  I want detections to appear on the tactical map in real-time via CoT
  So that I can make operational decisions with current information

  Background:
    Given the CoT service is running
    And TAK server is available at configured endpoint
    And output latency target is <2 seconds
    And reliability target is >99% delivery rate

  @happy_path @smoke @milestone_1
  Scenario: Detection appears on TAK map in real-time
    Given a validated CoT XML detection is ready for output
    And TAK Server is connected and accepting CoT updates
    When the system outputs the detection to TAK Server via HTTP PUT /CoT
    Then TAK Server receives the CoT XML
    And HTTP response is 200 OK or 201 Created
    And detection appears on dispatcher's map within 2 seconds
    And map marker shows coordinates correctly at [32.1234, -117.5678]
    And confidence circle shows accuracy (GREEN/YELLOW/RED)
    And detection type shows correct ATAK symbology (vehicle, person, etc.)
    And operator can click marker for full CoT properties
    And sync_status is marked SYNCED in audit trail

  @happy_path @milestone_1
  Scenario: Fire detection flows through photogrammetry to TAK map
    Given a fire detection with image pixel coordinates:
      | field              | value              |
      | pixel_x            | 640                |
      | pixel_y            | 480                |
      | camera_lat         | 32.1200            |
      | camera_lon         | -117.5700          |
      | camera_elevation   | 1000               |
      | focal_length       | 50                 |
      | ai_confidence      | 0.92               |
      | object_class       | fire               |
      | timestamp          | 2026-02-15T14:35:42Z |
    And the system timestamp is 2026-02-15T14:35:43Z
    When the detection goes through the full pipeline:
      | step          | timestamp | action                                |
      | accept        | 14:35:43  | Detection received with pixels       |
      | geolocate     | 14:35:43  | Photogrammetry calculates coordinates|
      | validate      | 14:35:43  | Confidence flag calculated GREEN     |
      | cot_generate  | 14:35:44  | CoT XML built with type code         |
      | tak_push      | 14:35:44  | PUT /CoT sent to TAK Server         |
      | receive       | 14:35:45  | TAK Client receives update           |
    Then detection appears on dispatcher's map by 14:35:45
    And end-to-end latency is 3 seconds (target <2s)
    And dispatcher sees: Fire symbol at calculated coordinates with GREEN circle
    And accuracy circle matches photogrammetry uncertainty (±Xm)
    And dispatcher can dispatch resources immediately

  @error_handling @resilience
  Scenario: Queue and sync when TAK Server temporarily offline
    Given a CoT XML detection is ready for output
    And TAK Server is temporarily unavailable (connection refused)
    When the system attempts HTTP PUT /CoT to TAK
    Then the push fails (connection refused error)
    And the system writes CoT XML to local SQLite queue
    And detection is marked PENDING_SYNC
    And status dashboard shows "TAK: OFFLINE (1 CoT queued)"
    And operator is NOT notified (transparent operation)
    And system continues accepting new detections (no blocking)
    When TAK Server comes back online (30 seconds later)
    Then system detects connectivity restored
    And automatically begins syncing queued CoT detection
    And CoT detection syncs within 2 seconds of reconnection
    And status dashboard updates: "TAK: SYNCING (1/1 complete)"
    And detection now appears on map (may be 30 seconds late)
    And sync_status changes from PENDING_SYNC to SYNCED
    And audit trail shows queue → sync timeline

  @error_handling @resilience
  Scenario: Multiple detections queue and batch sync efficiently
    Given TAK Server is offline
    And 5 CoT XML detections arrive while offline
    When each detection cannot reach TAK via PUT /CoT
    Then each is queued to local SQLite:
      | detection | status        | queued_at |
      | 1         | PENDING_SYNC  | 14:35:44  |
      | 2         | PENDING_SYNC  | 14:35:45  |
      | 3         | PENDING_SYNC  | 14:35:46  |
      | 4         | PENDING_SYNC  | 14:35:47  |
      | 5         | PENDING_SYNC  | 14:35:48  |
    And status dashboard shows "TAK: OFFLINE (5 pending)"
    When TAK Server comes back online
    Then system detects connectivity restored
    And begins batch sync of all 5 CoT detections
    And syncing completes in <2 seconds (batch processing)
    And all 5 appear on map with correct symbology
    And status dashboard: "TAK: SYNCED (5 items recovered)"

  @error_handling @timeout
  Scenario: HTTP timeout to TAK Server is handled gracefully
    Given TAK Server is responding slowly (>5 seconds)
    And HTTP timeout is set to 5 seconds
    When the system attempts HTTP PUT /CoT with timeout
    Then the request times out after 5 seconds
    And timeout error is caught
    And CoT detection is queued locally (marked PENDING_SYNC)
    And system logs error with timestamp
    And status dashboard: "TAK: TIMEOUT (1 pending)"
    And no detections are lost

  @error_handling @availability
  Scenario: TAK Server unavailable is handled with queue fallback
    Given TAK Server is completely unavailable (not responding)
    When system attempts HTTP PUT /CoT to TAK
    Then connection fails immediately (connection refused)
    And CoT XML is queued locally
    And detection stored with PENDING_SYNC status
    And operator receives no error (transparent fallback)
    And audit trail logs TAK unavailability
    And system continues normal operation

  @performance @sla
  Scenario: High-volume detection stream is handled without degradation
    Given the system is receiving 10+ detections per minute
    And each detection needs transformation and output
    When detections are output to TAK in high volume:
      | time      | detections | latency target |
      | 14:35:42  | 1          | <2s            |
      | 14:35:44  | 2          | <2s            |
      | 14:35:46  | 3          | <2s            |
      | 14:35:48  | 5          | <2s            |
      | 14:35:50  | 4          | <2s            |
    Then each detection is output independently
    And each appears on map within 2 seconds of transform
    And all markers appear on map (no overwriting)
    And no detections are dropped or lost
    And dispatcher can see fire front advancement
    And system remains responsive

  @reliability @sla
  Scenario: Output reliability exceeds 99% delivery rate
    Given 1000 detections are output to TAK Server
    When all 1000 are sent and tracked
    Then at least 990 reach TAK successfully (>99%)
    And failed detections are queued for retry
    And failed count is monitored and alerted if >1%
    And retry succeeds on next connectivity window

  @audit_trail
  Scenario: TAK output is logged in audit trail
    Given a detection is output to TAK Server
    When output completes
    Then audit trail records:
      | event              | details                                |
      | output_started     | timestamp, destination (TAK Server)    |
      | output_sent        | HTTP PUT, GeoJSON payload, timestamp   |
      | output_received    | HTTP 200 response, TAK timestamp       |
      | output_complete    | latency_ms, sync_status (SYNCED)       |
    And all events are immutable
    And audit trail is searchable by detection_id
    And audit trail shows end-to-end latency

  @edge_case
  Scenario: System handles TAK Server IP address change
    Given TAK Server IP changes (failover scenario)
    And system is configured with DNS name (not hardcoded IP)
    When system attempts to output detection
    Then DNS lookup resolves to new IP address
    And detection is sent to new IP successfully
    And no detections are lost during failover
    And operation is transparent to operators

  @stress_test
  Scenario: Burst traffic spike is handled
    Given baseline is 1 detection/second
    When sudden spike of 100 detections arrives (burst)
    Then all 100 are queued for output
    And output processes burst as quickly as possible
    And no detections dropped during burst
    And system recovers to baseline within 10 seconds
    And CPU/memory remain within acceptable bounds

  @compliance
  Scenario: HTTPS/TLS is used for TAK communication
    Given TAK Server endpoint is HTTPS (encrypted)
    When system outputs detection to TAK
    Then connection uses TLS encryption
    And certificate is validated
    And no data is transmitted in plaintext
    And security audit log shows "HTTPS connection verified"

  @monitoring
  Scenario: TAK output metrics are collected for monitoring
    Given the system is running
    When detections are output to TAK
    Then metrics are collected:
      | metric                    | unit       | example |
      | output_latency_p95        | ms         | 1200    |
      | output_latency_p99        | ms         | 1850    |
      | output_success_rate       | percent    | 99.5%   |
      | output_attempts_total     | count      | 1000    |
      | output_failures_total     | count      | 5       |
      | queue_depth               | count      | 0       |
      | sync_duration             | ms         | 150     |
    And metrics are exported to monitoring system (Prometheus)
    And dashboards can be created from metrics
    And alerting can be configured on thresholds
