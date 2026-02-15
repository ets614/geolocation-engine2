@feature_us004
Feature: Output to TAK GeoJSON
  As a command team dispatcher
  I want detections to appear on the tactical map in real-time
  So that I can make operational decisions with current information

  Background:
    Given the TAK output service is running
    And TAK server is available at configured endpoint
    And output latency target is <2 seconds
    And reliability target is >99% delivery rate

  @happy_path @smoke @milestone_1
  Scenario: Detection appears on TAK map in real-time
    Given a validated GeoJSON detection is ready for output
    And TAK Server is connected and accepting updates
    When the system outputs the detection to TAK subscription endpoint
    Then TAK Server receives the GeoJSON Feature
    And HTTP response is 200 OK
    And detection appears on dispatcher's map within 2 seconds
    And map marker shows coordinates correctly [40.7128, -74.0060]
    And accuracy badge shows confidence level (GREEN/YELLOW/RED)
    And source label shows "Satellite Fire API"
    And operator can click marker for full properties
    And sync_status is marked SYNCED in audit trail

  @happy_path @milestone_1
  Scenario: Fire detection flows from satellite API to dispatcher map
    Given a satellite fire detection with:
      | field              | value              |
      | latitude           | 32.1234            |
      | longitude          | -117.5678          |
      | confidence         | 0.92               |
      | type               | fire               |
      | timestamp          | 2026-02-17T14:35:42Z |
    And the system timestamp is 2026-02-17T14:35:43Z
    When the detection goes through the full pipeline:
      | step     | timestamp | action                           |
      | ingest   | 14:35:43  | API returns detection            |
      | validate | 14:35:43  | Geolocation validated GREEN      |
      | transform| 14:35:44  | GeoJSON built                    |
      | output   | 14:35:44  | Sent to TAK subscription         |
      | receive  | 14:35:45  | TAK Client receives update       |
    Then detection appears on dispatcher's map by 14:35:45
    And end-to-end latency is 3 seconds (target <2s)
    And dispatcher sees: Fire marker at coordinates with GREEN flag
    And dispatcher can dispatch resources immediately

  @error_handling @resilience
  Scenario: Queue and sync when TAK Server temporarily offline
    Given a GeoJSON detection is ready for output
    And TAK Server is temporarily unavailable (connection refused)
    When the system attempts to output to TAK subscription
    Then the push fails (connection refused error)
    And the system writes to local SQLite queue
    And detection is marked PENDING_SYNC
    And status dashboard shows "TAK: OFFLINE (1 detection queued)"
    And operator is NOT notified (transparent operation)
    And system continues accepting new detections (no blocking)
    When TAK Server comes back online (30 seconds later)
    Then system detects connectivity restored
    And automatically begins syncing queued detection
    And detection syncs within 2 seconds of reconnection
    And status dashboard updates: "TAK: SYNCING (1/1 complete)"
    And detection now appears on map (may be 30 seconds late)
    And sync_status changes from PENDING_SYNC to SYNCED
    And audit trail shows queue → sync timeline

  @error_handling @resilience
  Scenario: Multiple detections queue and batch sync efficiently
    Given TAK Server is offline
    And 5 GeoJSON detections arrive while offline
    When each detection cannot reach TAK
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
    And begins batch sync of all 5 detections
    And syncing completes in <2 seconds (batch processing)
    And all 5 appear on map in correct order
    And status dashboard: "TAK: SYNCED (5 items recovered)"

  @error_handling @timeout
  Scenario: Timeout to TAK Server is handled gracefully
    Given TAK Server is responding slowly (5+ seconds)
    And HTTP timeout is set to 5 seconds
    When the system outputs a detection with timeout
    Then the request times out after 5 seconds
    And timeout error is caught
    And detection is queued locally (marked PENDING_SYNC)
    And system logs error E005 (TAK_SERVER_DOWN)
    And status dashboard: "TAK: TIMEOUT (1 pending)"
    And no detections are lost

  @error_handling @auth
  Scenario: Authentication failure is detected and logged
    Given TAK Server authentication is misconfigured (wrong API key)
    When system attempts to output detection
    Then TAK Server returns HTTP 401 (Unauthorized)
    And system logs error E005 (TAK_AUTH_FAILED)
    And detection is queued locally
    And status dashboard: "TAK: AUTH FAILURE - check credentials"
    And operator intervention required (manual credential update)
    And audit trail shows auth failure with timestamp

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
