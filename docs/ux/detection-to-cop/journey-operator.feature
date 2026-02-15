# AI Detection to COP Translation System - Operator & Integrator Workflows
# Evidence: 5 customer discovery interviews, 7 opportunities scored, 5 concepts tested
# File: docs/ux/detection-to-cop/journey-operator.feature

Feature: AI Detection to COP Translation System - Operator Journeys

  Background:
    Given the system is installed and running
    And the health endpoint returns OK
    And network connectivity is stable

  # ========================================================================
  # HAPPY PATH: Integration Specialist Sets Up New Detection Source
  # ========================================================================

  Scenario: Integration Specialist deploys fire detection in under 1 hour
    Given an Emergency Services dispatch center needs to integrate a fire detection API
    And the fire detection API is available at https://api.fire.detection.io/v1
    And the integration specialist has API credentials
    And the dispatch center uses TAK Server for COP
    When the integration specialist installs the system
    Then the system is running on localhost:8080
    And the health endpoint responds with status OK
    And the integration took less than 5 minutes

    When the integration specialist adds a new detection source
    And selects the "Wildfire Detection API" template
    And enters the API endpoint and credentials
    And tests the connection
    Then the system connects successfully within 2 seconds
    And at least 3 recent detections are returned

    When the integration specialist configures output parameters
    And sets accuracy threshold to 100 meters
    And sets confidence threshold to 0.7
    And sets output format to TAK GeoJSON
    Then the configuration is saved without errors
    And configuration took less than 10 minutes

    When the integration specialist runs a dry-run with test data
    And retrieves a sample detection from the API
    And transforms it through the pipeline
    Then a valid GeoJSON Feature is generated
    And the feature includes source, confidence, accuracy_flag fields
    And accuracy_flag shows GREEN (for valid detection)

    When the integration specialist shows the preview to the operations manager
    And the operations manager confirms location accuracy
    And the operations manager approves the configuration
    Then deployment can proceed
    And validation took less than 15 minutes

    When the integration specialist enables the live feed
    Then the system starts polling the API every 30 seconds
    And detections begin flowing into TAK Server
    And the status dashboard shows ACTIVE
    And total setup time is less than 1 hour
    And the integration specialist can declare success

    # Evidence: Interview 3 - "Two weeks for a basic version... another week to make it robust"
    # Evidence: Interview 3 - "1 hour vs. two weeks is huge"
    # Evidence: Interview 3 - "Pre-built adapters would save us weeks"

  # ========================================================================
  # ERROR PATH: Geolocation Data Quality Problem
  # ========================================================================

  Scenario: Operator handles low-confidence geolocation gracefully
    Given a fire detection arrives with questionable accuracy
    And the detection is at coordinates [32.1234, -117.5678]
    And GPS metadata indicates accuracy of ±200 meters
    And confidence score is 0.65 (above minimum 0.6 but close)
    When the system processes the detection
    Then the detection is transformed to GeoJSON
    And the accuracy_flag is set to YELLOW (caution - verify)
    And the detection is output to TAK with warning badge

    When the dispatcher sees the detection on the tactical map
    Then it appears with a yellow triangle warning icon
    And hovering shows "Unverified location - Dispatcher review recommended"
    And timestamp shows when detection occurred (2026-02-17 14:35:42 UTC)
    And source shows "Satellite Fire API"

    When the dispatcher spot-checks the location
    And compares coordinates against known landmarks
    And verifies the location is actually correct
    Then the dispatcher can click "Verify and confirm"
    And the system records the manual verification in audit trail
    And the map updates the detection to green flag (verified)
    And dispatcher can proceed with response (resource dispatch, investigation)

    # Evidence: Interview 1 - "30 minutes per mission just validating coordinates"
    # Evidence: Interview 1 - "If system auto-checks accuracy, I'd only spot-check flagged items"
    # Evidence: Interview 1 - "80% time savings (30 min → 5 min)"

  # ========================================================================
  # ERROR PATH: Offline Resilience During Network Outage
  # ========================================================================

  Scenario: System queues detections during network outage and syncs on reconnect
    Given the system is actively polling a detection API
    And a fire detection is received successfully at T+0
    And the detection is validated and ready to send to COP
    When network connectivity drops at T+1 (while trying to sync to remote DB)
    Then the detection is queued to local SQLite database
    And the detection status is marked PENDING_SYNC
    And the audit log shows "Network offline, queued locally"

    When the status dashboard updates
    Then it shows "Status: Buffering (1 detection queued)"
    And the operator sees clear indication that system is still working
    And the operator does NOT need to take manual action

    When the polling continues (if local API is accessible)
    Then additional detections continue to flow into local queue
    And each detection is validated and queued
    And local queue grows (example: 5 detections queued after 2 minutes offline)

    When network connectivity is restored at T+120 (after 2 minutes)
    Then the system detects connection success
    And automatically initiates sync of all queued detections
    And first detection is pushed to remote DB (1/5)
    And second detection is pushed to remote DB (2/5)
    And final detection is pushed to remote DB (5/5)

    When all detections are synced
    Then status dashboard updates to "Sync: OK (5 items recovered)"
    And all queued detections appear on TAK map (may be delayed 5-10s from original time)
    And audit trail shows complete timeline: queue → sync
    And operator can see when each detection was originally detected vs. when it synced
    And no data was lost
    And operator did not have to manually screenshot or re-enter data

    # Evidence: Interview 4 - "System fails 20-30% of the time"
    # Evidence: Interview 4 - "I had to land, walk over to the ops tent, show them screenshots"
    # Evidence: Interview 4 - "If detections queue locally and sync when connection restores, I don't have to manually screenshot"

  # ========================================================================
  # ERROR PATH: Invalid Geolocation (Out of Bounds)
  # ========================================================================

  Scenario: System flags suspicious coordinates requiring operator override
    Given a detection arrives with coordinates [500, -117.5678]
    When the system validates the detection
    Then latitude range check fails (latitude must be -90 to 90)
    And the system flags this as ERROR: OUT_OF_BOUNDS
    And accuracy_flag is set to RED (do not trust)

    When the system processes this detection
    Then the detection is NOT automatically output to COP
    Instead the detection is queued for operator review

    When the operator reviews flagged detections
    And sees the detection with RED flag
    And reads the explanation "Invalid latitude: 500 (out of valid range -90 to 90)"
    Then the operator can:
      - Option A: "Reject this detection" (discarded)
      - Option B: "Manually correct location" (enter correct coordinates)
      - Option C: "Override - trust as-is" (output with manual override note)

    If the operator chooses Option B (manually correct):
      When entering corrected coordinates [32.1234, -117.5678]
      Then the detection is re-validated
      And accuracy_flag updates to GREEN (if valid after correction)
      And detection outputs to COP with note "Operator corrected coordinates"
      And audit trail records: "Operator override: corrected latitude"

    # Evidence: Interview 1 - "Sometimes the metadata is incomplete or wrong"
    # Evidence: Interview 1 - "We manually spot-checked the coordinates against known landmarks"
    # Evidence: Interview 1 - "On the last mission, we missed a coordinate error"

  # ========================================================================
  # HAPPY PATH: Confidence Normalization Across Multi-Source Detections
  # ========================================================================

  Scenario: Dispatcher compares fire detections from different sources with normalized confidence
    Given a dispatch center has two fire detection sources
    And Source A (Satellite API) outputs confidence as 0-100 scale
    And Source B (Drone Detection) outputs confidence as 0-1 scale

    When a detection from Source A arrives with confidence=85
    And a detection from Source B arrives with confidence=0.92
    Then the system normalizes both to 0-1 scale:
      - Source A: 85 / 100 = 0.85 (normalized)
      - Source B: 0.92 (already normalized, no conversion)

    When both detections appear on the dispatch map
    And the dispatcher hovers over each detection
    Then Source A shows "Confidence: 0.85 (normalized from 85/100 by satellite system)"
    And Source B shows "Confidence: 0.92 (drone confidence score)"
    And the dispatcher can compare them on same scale
    And Source B's higher confidence (0.92 > 0.85) is visually evident

    When the system has historical data
    And Satellite fire detections with 0.85+ have been 78% accurate historically
    And Drone detections with 0.92+ have been 91% accurate historically
    Then Source B shows additional note "Historical accuracy: 91% at this confidence level"
    And Source A shows additional note "Historical accuracy: 78% at this confidence level"
    And the dispatcher understands which source is more reliable

    # Evidence: Interview 5 - "Satellite uses 0-100 scale, drone uses 0-1, need to normalize"
    # Evidence: Interview 5 - "I need to know what the confidence means"
    # Evidence: Solution testing - "Historical accuracy helps calibrate trust"

  # ========================================================================
  # ERROR PATH: Metadata Loss and Audit Trail Recovery
  # ========================================================================

  Scenario: Operator can audit complete history of any detection's journey
    Given a fire detection has been processed and acted upon
    And the dispatcher sent resources to the location at 14:45 UTC
    When the operations manager needs to investigate why resources were sent
    And clicks "View audit trail" on the detection
    Then the complete journey is visible:
      Timeline entry 1 (14:35:42 UTC):
        Event: "Detection received from satellite_fire_api"
        Confidence: 85 (normalized to 0.85)
        Location: [32.1234, -117.5678]
        Accuracy: ±45 meters
        Status: "Processed successfully"

      Timeline entry 2 (14:35:43 UTC):
        Event: "Geolocation validated"
        Check: "Accuracy ±45m < 500m threshold ✓"
        Flag: "GREEN (high confidence location)"
        Status: "Passed validation"

      Timeline entry 3 (14:35:44 UTC):
        Event: "Transformed to GeoJSON"
        Fields: "All required properties present"
        Status: "Synced to TAK Server"

      Timeline entry 4 (14:35:45 UTC):
        Event: "Dispatcher viewed detection"
        User: "Dispatcher John Smith"
        Status: "Detection acknowledged"

      Timeline entry 5 (14:45:00 UTC):
        Event: "Dispatcher took action"
        User: "Dispatcher John Smith"
        Action: "Dispatched Engine 7 and Engine 12"
        Location confirmed: "[32.1234, -117.5678]"
        Status: "Resources deployed"

    When the operations manager reviews this trail
    Then they understand:
      - Where the detection came from
      - What validation was performed
      - When and by whom decisions were made
      - Full chain of custody from source to action

    And if needed, the operations manager can:
      - Verify the detection was actually valid (it was - GREEN flag)
      - Confirm the dispatch was appropriate (yes, based on location)
      - Identify any training needs (none apparent)
      - Support regulatory compliance (complete audit trail present)

    # Evidence: Interview 1 - "We need to log what was translated and why, for after-action reviews"
    # Evidence: Interview 2 - "Need to know if it was human-reviewed before any action was taken"
    # Evidence: Interview 5 - "Need metadata that says where it came from, when it was last updated"

  # ========================================================================
  # HAPPY PATH: Real-Time Tactical Operations (Military Context)
  # ========================================================================

  Scenario: Military operations sees UAV detection on COP within 2 seconds
    Given a military ISR mission is active
    And UAV-1 is flying reconnaissance over a tactical area
    And detection system (onboard AI) detects a vehicle at coordinates [32.1234, -117.5678]
    And UAV ground control station outputs detection as JSON at 14:35:42.000 UTC
    When the JSON detection arrives at the system
      T+0.0s: Detection received (timestamp logged)
      T+0.2s: Format validated (JSON structure OK)
      T+0.3s: Coordinates normalized and validated (GREEN)
      T+0.4s: Confidence normalized to 0.89
      T+0.5s: GeoJSON feature built
      T+0.7s: Transformed to TAK format
      T+0.8s: Pushed to TAK Server subscription

    Then at T+1.2s total (from detection to operator view):
      The operations team sees the vehicle marker appear on TAK map
      Location: [32.1234, -117.5678]
      Confidence badge: "0.89 (HIGH)"
      Source: "UAV-1 AI Detection"
      Timestamp: "14:35:42 UTC (30 seconds ago)"

    And the tactical advantage is preserved:
      - Latency < 2 seconds (decision cycle can react immediately)
      - Confidence high enough for tactical targeting
      - Multiple UAV feeds can flow simultaneously
      - Operators can task aircraft based on fresh detections

    When additional detections from other UAVs arrive simultaneously:
      UAV-2 detection at 14:35:44 UTC
      UAV-3 detection at 14:35:45 UTC
    Then all three appear on map within 2 seconds of each arrival
    And team can build complete tactical picture
    And can coordinate airborne assets in real-time

    # Evidence: Interview 1 - "45 minutes to get all three feeds integrated for a 2-hour mission"
    # Evidence: Interview 1 - "We need detections on the COP within seconds of being detected"
    # Evidence: Interview 1 - "Reliability - if it breaks mid-mission, it breaks the whole operation"

  # ========================================================================
  # INTEGRATION CHECKPOINT: From Source API to COP Display
  # ========================================================================

  Scenario: System validates integration checkpoints at each transformation step
    Given a detection is flowing through the system
    When the detection reaches each checkpoint
    Then checkpoint validation occurs:

      Checkpoint 1 - Format Validation:
        Input: Raw JSON from API
        Check: Valid JSON structure, required fields present
        Status: ✓ PASS or ✗ FAIL (log E001 if fail)

      Checkpoint 2 - Geolocation Normalization:
        Input: lat/lon in source format
        Check: Within valid range, can be parsed
        Status: ✓ PASS or ✗ FAIL (log E003 if fail)

      Checkpoint 3 - Accuracy Flagging:
        Input: Normalized coordinates, accuracy metadata
        Check: Accuracy < 500m AND confidence > 0.6
        Status: ✓ PASS (GREEN) or ✗ FAIL (YELLOW/RED)

      Checkpoint 4 - Confidence Normalization:
        Input: Confidence in any scale
        Check: Converted to 0-1 range correctly
        Status: ✓ PASS or ✗ FAIL (log for investigation)

      Checkpoint 5 - GeoJSON Build:
        Input: All enriched data
        Check: Valid GeoJSON Feature (RFC 7946)
        Status: ✓ PASS or ✗ FAIL (cannot output)

      Checkpoint 6 - Persistence:
        Input: Valid GeoJSON
        Check: Written to remote DB OR local queue
        Status: ✓ PASS (SYNCED) or ✓ PASS (PENDING_SYNC) or ✗ FAIL (error E006)

      Checkpoint 7 - Output Delivery:
        Input: Persisted GeoJSON
        Check: TAK Server endpoint reachable
        Status: ✓ DELIVERED or queued for retry

      Checkpoint 8 - Audit Logging:
        Input: All checkpoint results
        Check: Complete audit entry persisted
        Status: ✓ LOGGED for compliance

    And if any checkpoint fails:
      The detection does not proceed to next step
      Error is logged with source and cause
      Operator is notified if action needed
      System continues processing other detections

  # ========================================================================
  # WALKING SKELETON SUCCESS CRITERIA
  # ========================================================================

  Scenario: Walking skeleton validates end-to-end architecture
    Given the system is deployed in emergency services context
    When one fire detection flows from API through complete pipeline to TAK map
    Then every step succeeds:
      ✓ Detection received from source API
      ✓ Format validated (JSON structure OK)
      ✓ Geolocation normalized (WGS84 coordinates)
      ✓ Accuracy flagged (GREEN if valid, YELLOW/RED if not)
      ✓ Confidence normalized (0-1 scale)
      ✓ GeoJSON feature generated (RFC 7946 compliant)
      ✓ Persisted (local or remote, marked SYNCED or PENDING_SYNC)
      ✓ Output to TAK Server (delivered or queued)
      ✓ Operator sees detection on map (<2s latency)
      ✓ Audit trail complete (source → output)

    And performance metrics meet targets:
      ✓ Installation time < 5 minutes
      ✓ Configuration time < 10 minutes
      ✓ Dry-run validation < 15 minutes
      ✓ Total integration < 1 hour (vs. 2-3 week baseline)
      ✓ End-to-end latency < 2 seconds
      ✓ Manual verification < 5 minutes
      ✓ System reliability > 99%

    And emotional arc is positive:
      ✓ Integration specialist moves from "anxious" to "relieved"
      ✓ Operations manager moves from "uncertain" to "convinced"
      ✓ Field dispatcher moves from "experienced" to "confident"

    And customer metrics show impact:
      ✓ 94% time savings on integration (3 weeks → 1 hour)
      ✓ 80% time savings on manual verification (30 min → 5 min)
      ✓ 29% improvement in reliability (70% → 99%)
      ✓ Near-zero data loss (offline-first architecture)

    # Evidence: All 5 discovery interviews
    # Evidence: Lean Canvas success metrics
    # Evidence: MVP scope definition from solution testing

# ============================================================================
# GHERKIN FEATURE STRUCTURE NOTES
# ============================================================================
# These scenarios are written to be:
# 1. TESTABLE - Each "Then" can be verified with automated or manual testing
# 2. EVIDENCE-BASED - Each scenario traces back to discovery interviews
# 3. INTEGRATION-FOCUSED - Emphasizes data flow and system boundaries
# 4. OPERATOR-CENTRIC - Written from user perspective, not technical perspective
# 5. ERROR-AWARE - Includes both happy path and error recovery paths
#
# Next steps: Convert to executable specs with step definitions (Behave/Cucumber)
# Map each scenario to acceptance criteria in user stories
# Use as basis for UAT scripts and integration test automation
