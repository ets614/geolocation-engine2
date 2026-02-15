# User Stories: AI Detection to COP Translation System
## Walking Skeleton MVP

**Project**: AI Object Detection to COP Translation System
**Status**: Phase 2 - Requirements Crafting (Walking Skeleton)
**Evidence Base**: 5 customer interviews, 7 opportunities (3 P0), 5 solution concepts tested
**Customer Context**: Emergency Services (fire detection integration)
**Timeline Target**: 8-12 weeks to MVP

---

## Table of Contents

1. [Walking Skeleton Stories (P0)](#walking-skeleton-stories-p0)
   - [US-001: Accept JSON Detection Input](#us-001-accept-json-detection-input)
   - [US-002: Validate and Normalize Geolocation](#us-002-validate-and-normalize-geolocation)
   - [US-003: Translate to GeoJSON Format](#us-003-translate-to-geojson-format)
   - [US-004: Output to TAK GeoJSON](#us-004-output-to-tak-geojson)
   - [US-005: Handle Offline Queuing and Sync](#us-005-handle-offline-queuing-and-sync)

2. [Integration & Configuration Stories (P1)](#integration--configuration-stories-p1)
   - [US-006: Setup Detection Source Configuration](#us-006-setup-detection-source-configuration)
   - [US-007: Auto-Detect Detection Format](#us-007-auto-detect-detection-format)

3. [System Stories (P0 Infrastructure)](#system-stories-p0-infrastructure)
   - [US-008: Health Checks and System Status](#us-008-health-checks-and-system-status)
   - [US-009: Audit Trail Logging](#us-009-audit-trail-logging)

---

## Walking Skeleton Stories (P0)

### US-001: Accept JSON Detection Input

**Title**: Integration Specialist can receive and ingest fire detection data from REST API

**Problem (The Pain)**

Marcus Chen is a systems integration engineer at the Emergency Services dispatch center. He's trying to integrate a new wildfire detection API into the dispatch system. Currently, every time a new detection API arrives, he has to write custom Python code to parse it, validate it, and map fields. When vendors update their API formats, everything breaks.

> "Two weeks for a basic version that worked 80% of the time. Another week to make it robust - handling edge cases, failures, data validation. By week 3, we had something we trusted enough to use in operations." — Interview 3

**Who (The User)**

- **Marcus Chen**: Systems Integration Engineer at Emergency Services
- **Context**: Integrating fire detection API (Wildfire Detection API REST endpoint)
- **Goal**: Get detection data flowing into dispatch system in <1 hour (not 2-3 weeks)
- **Constraint**: Fire detection API returns JSON in unstructured format; Marcus shouldn't have to write custom parsers

**Solution (What We Build)**

The system accepts detection data from REST APIs in JSON format. It validates the JSON structure, extracts required fields (latitude, longitude, confidence, detection_type, timestamp), and normalizes them into internal format. The system handles API rate limits, timeouts, and malformed responses gracefully.

**Domain Examples**

### Example 1: Happy Path - Valid Fire Detection from Satellite API
```yaml
# Scenario: Satellite fire detection API is available and returns valid JSON
Marcus: Configures system to poll https://api.fire.detection.io/v1/detections
System: Every 30 seconds, sends GET request with authentication token
API Response: Returns valid JSON
{
  "detections": [
    {
      "latitude": 32.1234,
      "longitude": -117.5678,
      "confidence": 85,
      "type": "fire",
      "timestamp": "2026-02-17T14:35:42Z",
      "metadata": {"sensor": "LANDSAT-8", "band": "thermal"}
    }
  ]
}
System: Parses JSON successfully
System: Extracts: lat=32.1234, lon=-117.5678, conf=0.85, type=fire, ts=2026-02-17T14:35:42Z
System: Logs event: "Detection received from satellite_fire_api"
Marcus: Sees detection count incrementing on status dashboard (3 in last 5 min)
Success Metric: Detection ingested in <100ms
```

### Example 2: Error Case - API Returns Malformed JSON
```yaml
# Scenario: API returns corrupted JSON response
Marcus: System polling API as configured
API Response: Returns truncated/malformed JSON (network corruption)
{
  "detections": [
    { "latitude": 32.1234, "longitude": -117.5678,
      ... [connection drops, incomplete JSON]
}
System: JSON parser fails with SyntaxError
System: Error logged: "E001 - INVALID_JSON from satellite_fire_api at 2026-02-17T14:36:00Z"
System: Skips detection, continues polling on next 30s interval
Marcus: Dashboard shows: "Feed health: 99.8% (1 parse error in last 1000 attempts)"
Recovery: Automatic - no operator action needed
Success Metric: System resilient to bad JSON, continues operating
```

### Example 3: Boundary Case - API Rate Limiting
```yaml
# Scenario: API rate limits requests (HTTP 429 Too Many Requests)
Marcus: System configured to poll API every 30 seconds
API Response: After 100 requests in rapid succession, returns:
{
  "error": "Rate limit exceeded",
  "retry_after": 60
}
HTTP Status: 429 Too Many Requests
System: Detects 429 status code
System: Reads Retry-After header (60 seconds)
System: Backs off polling to 60-second interval temporarily
System: Waits, then resumes polling at 30-second interval after backoff
Marcus: Sees no detection loss - detections resume flowing after backoff period
Success Metric: System handles rate limiting without data loss or operator intervention
```

**UAT Scenarios (BDD)**

### Scenario 1: System successfully ingests valid JSON detection
```gherkin
Given the fire detection API is configured and running
And the API endpoint is https://api.fire.detection.io/v1/detections
And authentication is configured with valid token
When the system polls the API
And the API returns a valid JSON response with one fire detection
Then the detection is parsed successfully
And the detection fields are extracted: latitude, longitude, confidence, type, timestamp
And an event is logged: "Detection received from satellite_fire_api"
And the ingestion timestamp is recorded
And the detection moves to validation phase
```

### Scenario 2: System handles malformed JSON gracefully
```gherkin
Given the fire detection API is configured
When the API returns invalid/malformed JSON
Then the system logs error E001: "INVALID_JSON from source_id=satellite_fire_api"
And the malformed detection is skipped
And the system continues polling on next interval
And no system disruption occurs
And the operator sees status: "Health: 99.8% (1 error in 1000 attempts)"
```

### Scenario 3: System respects API rate limits
```gherkin
Given the system is polling the fire detection API every 30 seconds
When the API returns HTTP 429 (Too Many Requests)
And the Retry-After header specifies 60 seconds
Then the system backs off polling to 60-second interval
And no detections are lost during backoff
And polling resumes at 30-second interval after backoff expires
And the operator sees: "Rate limit encountered, auto-backed off"
```

**Acceptance Criteria**

- [x] System accepts and validates JSON from configured REST API endpoints
- [x] System extracts required fields: latitude, longitude, confidence, type, timestamp
- [x] System handles malformed JSON without system failure (error E001)
- [x] System respects API rate limits (HTTP 429) with exponential backoff
- [x] System logs all ingestion events for audit trail
- [x] Ingestion latency < 100ms per detection
- [x] Error rate for valid JSON < 0.1% (99.9% success)
- [x] System continues polling despite transient API errors

**Technical Notes (Optional)**

- **Dependency**: US-006 (configuration) must complete first
- **Constraint**: JSON parsing library must handle >10MB payloads
- **Integration**: Requires REST HTTP client with timeout/retry
- **Testing**: Mock API with simulated malformed responses
- **Evidence**: Interview 3 - "Vendor docs incomplete, had to reverse-engineer API"

---

### US-002: Validate and Normalize Geolocation

**Title**: Operations manager can trust geolocation accuracy with automatic validation

**Problem (The Pain)**

Operations Manager Sarah Ramirez spends 30 minutes per mission validating coordinates from UAV detection feeds. The GPS accuracy varies by terrain and sensor, and incorrect coordinates cause detections to plot in wrong locations. She manually spot-checks coordinates against known landmarks.

> "Geolocation accuracy. If the UAV metadata is off by even 500 meters, the detections plot in the wrong location on the map. We spend probably 30 minutes per mission just validating coordinates." — Interview 1

> "If system auto-checks accuracy, I'd only spot-check flagged items. Cuts time from 30 minutes to 5 minutes." — Interview 1 (killer feature test)

**Who (The User)**

- **Sarah Ramirez**: Operations Manager, Military ISR
- **Context**: Validating fire/vehicle detections from multiple UAV sources
- **Goal**: Reduce manual coordinate validation from 30 min to 5 min (80% time savings)
- **Success**: Automated accuracy flagging with GREEN/YELLOW/RED confidence levels

**Solution (What We Build)**

The system validates geolocation accuracy using GPS metadata, coordinate ranges, and historical accuracy data. Detections with ±500m accuracy or confidence <0.6 are flagged YELLOW for operator spot-check. Detections with invalid coordinates (out of range) are flagged RED and require manual override.

**Domain Examples**

### Example 1: Happy Path - High Confidence Location (GREEN)
```yaml
# Scenario: Military UAV detection with good GPS accuracy
Detection received from UAV-2:
  latitude: 32.1234
  longitude: -117.5678
  confidence: 0.85
  timestamp: 2026-02-17T14:35:42Z
  metadata: {sensor: "GPS/IMU", accuracy_meters: 45, terrain: "sea_level"}

System: Validates coordinates
  - latitude 32.1234: Within [-90, 90] ✓
  - longitude -117.5678: Within [-180, 180] ✓
  - accuracy 45m: < 500m threshold ✓
  - confidence 0.85: > 0.6 minimum ✓
  - terrain sea_level: expected accuracy ±45m ✓

System: All checks pass
Accuracy_flag: GREEN (high confidence location)
Sarah: Sees GREEN checkmark on map
Sarah: Does NOT need to manually verify
Sarah: Can proceed with operational decision
Time saved: 30 min → 0 min (detection already trusted)
```

### Example 2: Caution Case - Low Confidence (YELLOW)
```yaml
# Scenario: Satellite fire detection with moderate confidence
Detection from satellite_fire_api:
  latitude: 32.9876
  longitude: -117.2468
  confidence: 0.68
  timestamp: 2026-02-17T14:36:15Z
  metadata: {sensor: "LANDSAT-8", accuracy_meters: 180, terrain: "mountains"}

System: Validates coordinates
  - latitude 32.9876: Within [-90, 90] ✓
  - longitude -117.2468: Within [-180, 180] ✓
  - accuracy 180m: < 500m ✓ (but high for mountains)
  - confidence 0.68: > 0.6 ✓ (but close to threshold)
  - terrain mountains: expected accuracy ±200m in mountains

System: Coordinate checks pass, but confidence is borderline
Accuracy_flag: YELLOW (spot-check recommended)
Sarah: Sees YELLOW triangle warning on map
Sarah: Clicks to view details: "Accuracy: ±180m, Confidence: 0.68"
Sarah: Compares coordinates against satellite imagery reference
Sarah: Verifies location is correct (fire is visible in thermal band)
Sarah: Clicks "Verify and confirm"
System: Records manual verification in audit trail
Time spent: ~2 minutes (fast spot-check, not full 30-min validation)
Total time saved: 30 min → 2 min (93% savings on this detection)
```

### Example 3: Error Case - Invalid Coordinates (RED)
```yaml
# Scenario: Corrupted coordinate data requires operator override
Detection from poorly_calibrated_camera:
  latitude: 500  # INVALID! Out of range
  longitude: -117.5678
  confidence: 0.75
  timestamp: 2026-02-17T14:37:00Z

System: Validates coordinates
  - latitude 500: OUTSIDE [-90, 90] ✗ FAIL

System: Coordinate range check fails
Accuracy_flag: RED (do not trust)
Output to COP: NOT sent to map (blocked at output layer)
Sarah: Sees detection in "Manual Review Queue"
Sarah: Reads error: "Invalid latitude: 500 (must be -90 to 90)"
Sarah: Options:
  A) Reject detection (discard)
  B) Manually correct coordinates (e.g., enter 32.5 if she knows location)
  C) Override "trust as-is" (not recommended)

Sarah: Chooses Option B, enters corrected latitude: 32.1234
System: Re-validates corrected coordinates
System: Now within range, flags as GREEN or YELLOW
Sarah: Detection now appears on map
System: Audit trail records: "Operator corrected latitude (500 → 32.1234)"
Time impact: ~3-5 minutes for operator to correct one bad detection
```

**UAT Scenarios (BDD)**

### Scenario 1: Accurate location is automatically flagged GREEN
```gherkin
Given a fire detection with GPS accuracy ±45 meters
And confidence score 0.85 (above 0.6 minimum)
And coordinates within valid range [-90, 90] for lat, [-180, 180] for lon
When the system validates geolocation
Then the accuracy_flag is set to GREEN
And the detection is output to COP with GREEN checkmark
And operations manager does not need to manually verify
```

### Scenario 2: Borderline confidence triggers YELLOW flag
```gherkin
Given a fire detection with GPS accuracy ±180 meters
And confidence score 0.68 (above 0.6 but close)
And terrain type: mountains
When the system validates geolocation
Then the accuracy_flag is set to YELLOW
And the detection is output to COP with YELLOW warning badge
And operations manager sees: "Verify location - low confidence"
And operator can click to spot-check location
And operator can click "Verify and confirm" to mark GREEN
And manual verification is recorded in audit trail
```

### Scenario 3: Out-of-range coordinates are flagged RED
```gherkin
Given a detection with invalid latitude (500 degrees)
When the system validates coordinates
Then the accuracy_flag is set to RED
And the detection is NOT output to COP
And detection is queued for manual review
And operator sees error message: "Invalid latitude: 500 (must be -90 to 90)"
And operator can manually correct coordinates
And upon correction, detection is re-validated and output
```

**Acceptance Criteria**

- [x] System validates geolocation automatically without operator action
- [x] Detections with accuracy <500m and confidence >0.6 are flagged GREEN (80% of valid detections)
- [x] Detections with accuracy 500-1000m or confidence 0.4-0.6 are flagged YELLOW
- [x] Detections with accuracy >1000m or confidence <0.4 are flagged RED (require override)
- [x] Invalid coordinates (out of range) are caught and flagged RED
- [x] Manual spot-check time reduced from 30 min to <5 min (80% savings)
- [x] Operator can manually verify YELLOW flagged detections in <2 min
- [x] Operator can override RED flags with manual coordinate correction
- [x] All validations recorded in audit trail with timestamps
- [x] GREEN flag accuracy >95% (validated against ground truth)

**Technical Notes (Optional)**

- **Dependency**: US-001 (ingestion) must complete first
- **Algorithm**: Use GPS accuracy metadata + terrain type + historical accuracy database
- **Accuracy database**: Must be populated with historical detections and ground truth
- **Testing**: Test with known bad coordinates (out of range, impossible locations)
- **Evidence**: Interview 1 - "30 minutes per mission... system flags accuracy"
- **Killer feature**: 80% time savings on manual verification

---

### US-003: Translate to GeoJSON Format

**Title**: System converts any detection format to standardized GeoJSON for COP compatibility

**Problem (The Pain)**

Every detection source outputs data in different formats. Military UAVs output JSON, satellites output CSV, cameras output structured binary data. Each format requires custom translation code. When vendors change formats, integrations break.

> "Every vendor has their own format, their own coordinate system, their own API design. It means I'm basically reinventing the wheel every time." — Interview 5

**Who (The User)**

- **Integration Specialist Team**: Marcus, Sarah, other integration specialists
- **Context**: Supporting multiple detection sources (satellite, drone, UAV, cameras)
- **Goal**: Format translation in <1 hour per new source (not 2-3 weeks)
- **Success**: Pre-built templates for common formats, <1 hour configuration

**Solution (What We Build)**

The system transforms normalized detections into GeoJSON Feature format (RFC 7946), compatible with TAK Server, ArcGIS, and standard COP systems. GeoJSON includes geometry (point location), properties (source, confidence, accuracy, metadata), and audit trail information.

**Domain Examples**

### Example 1: Happy Path - Military Detection to GeoJSON
```yaml
# Scenario: UAV detection flows from ground control station to TAK map
Input (from UAV-1 Ground Control Station):
{
  "lat": 32.1234,
  "lon": -117.5678,
  "conf": 0.89,
  "type": "vehicle",
  "ts": "2026-02-17T14:35:42Z",
  "sensor": "onboard_ai",
  "accuracy": 25
}

System processing:
1. Normalize: lat→latitude_normalized, lon→longitude_normalized, etc
2. Validate: All fields present, ranges correct
3. Build GeoJSON:

Output (GeoJSON Feature):
{
  "type": "Feature",
  "geometry": {
    "type": "Point",
    "coordinates": [-117.5678, 32.1234]  # [lon, lat] per RFC 7946
  },
  "properties": {
    "source": "uav_ground_control_station",
    "source_id": "uav_1",
    "confidence": 0.89,
    "confidence_original": {"value": 89, "scale": "0-1"},
    "type": "vehicle",
    "timestamp": "2026-02-17T14:35:42Z",
    "received_timestamp": "2026-02-17T14:35:43Z",
    "accuracy_m": 25,
    "accuracy_flag": "GREEN",
    "sync_status": "SYNCED"
  }
}

Output delivery:
- Sent to TAK Server subscription endpoint
- Received by TAK Client
- Appears on tactical map within 2 seconds
- Operator sees: Vehicle marker at coordinates, GREEN accuracy badge

Success: From detection to map in <2 seconds, full metadata preserved
```

### Example 2: Emergency Services - Fire Detection via Satellite API
```yaml
# Scenario: Satellite fire detection (different format, different scale)
Input (from satellite_fire_api):
{
  "latitude": 32.8765,
  "longitude": -117.3456,
  "confidence_0_100": 92,
  "fire_probability": "high",
  "timestamp": "2026-02-17T14:36:00Z",
  "satellite": "LANDSAT-8",
  "resolution_m": 180
}

System processing:
1. Normalize: confidence_0_100=92 → confidence_normalized=0.92
2. Apply converter rule: conf_0_100 / 100 = 0.92
3. Validate: Accuracy 180m < 500m threshold ✓

Output (GeoJSON Feature):
{
  "type": "Feature",
  "geometry": {
    "type": "Point",
    "coordinates": [-117.3456, 32.8765]
  },
  "properties": {
    "source": "satellite_fire_api",
    "source_id": "sat_1",
    "confidence": 0.92,
    "confidence_original": {"value": 92, "scale": "0-100"},
    "type": "fire",
    "timestamp": "2026-02-17T14:36:00Z",
    "received_timestamp": "2026-02-17T14:36:01Z",
    "accuracy_m": 180,
    "accuracy_flag": "YELLOW",  # Accuracy 180m > typical, needs spot-check
    "sync_status": "SYNCED"
  }
}

Output delivery:
- Sent to dispatch center COP (via CAD system GeoJSON endpoint)
- Dispatcher sees fire detection on map
- YELLOW badge indicates "verify location"
- Full satellite metadata preserved for investigation

Success: Different format handled with same GeoJSON output
```

### Example 3: Law Enforcement - Camera-Based Detection
```yaml
# Scenario: CCTV system detects suspect, needs geolocation enrichment
Input (from police_cctv_detection_api):
{
  "camera_id": "cam_47",
  "detection_type": "person",
  "confidence": 0.78,
  "timestamp": "2026-02-17T14:37:30Z",
  "bounding_box": {"x": 150, "y": 200, "w": 50, "h": 80}
}
Camera Registry lookup:
{
  "camera_id": "cam_47",
  "location": {"latitude": 40.7580, "longitude": -73.9855},
  "coverage_area": "5th Avenue and 42nd Street"
}

System processing:
1. Detection: person detected by camera_47
2. Registry lookup: camera_47 location → [40.7580, -73.9855]
3. Enrich: Attach location from registry
4. Build GeoJSON:

Output (GeoJSON Feature):
{
  "type": "Feature",
  "geometry": {
    "type": "Point",
    "coordinates": [-73.9855, 40.7580]  # From camera registry
  },
  "properties": {
    "source": "police_cctv_api",
    "source_id": "cam_47",
    "confidence": 0.78,
    "confidence_original": {"value": 78, "scale": "0-100"},
    "type": "person",
    "timestamp": "2026-02-17T14:37:30Z",
    "received_timestamp": "2026-02-17T14:37:31Z",
    "accuracy_m": 10,  # Camera location accuracy (building entrance)
    "accuracy_flag": "GREEN",
    "operator_notes": "5th Avenue and 42nd Street camera"
  }
}

Output delivery:
- Sent to law enforcement analysis dashboard
- Analyst sees suspect location on map (camera location, not bounding box)
- Can cross-reference with other camera detections
- Can dispatch officers

Success: Enriched with external data (camera registry), standardized format
```

**UAT Scenarios (BDD)**

### Scenario 1: Detection is transformed to valid GeoJSON
```gherkin
Given a normalized detection with all required fields
And the detection has been validated and flagged
When the system builds GeoJSON output
Then the output is valid GeoJSON Feature (RFC 7946)
And coordinates are in [longitude, latitude] format
And all detection properties are included
And accuracy_flag is present
And audit metadata is included
And GeoJSON can be parsed by standard GeoJSON parsers
```

### Scenario 2: Multiple source formats are handled consistently
```gherkin
Given a UAV detection in format: {"lat": X, "lon": Y, "conf": Z}
And a satellite detection in format: {"latitude": X, "longitude": Y, "confidence_0_100": Z}
And a camera detection enriched from registry: {"camera_id": X}
When each is transformed to GeoJSON
Then all three produce valid GeoJSON Features
And all use same coordinate system (WGS84)
And all use same confidence scale (0-1 normalized)
And the operator sees consistent output regardless of source
```

### Scenario 3: Confidence scales are normalized correctly
```gherkin
Given detections with confidence in different scales
And UAV detection with confidence 0.89 (0-1 scale)
And satellite detection with confidence 92 (0-100 scale)
And camera detection with confidence 78 (0-100 scale)
When each is transformed to GeoJSON
Then UAV confidence becomes 0.89 (no change)
And satellite confidence becomes 0.92 (92/100)
And camera confidence becomes 0.78 (78/100)
And all are normalized to same 0-1 scale
And original values preserved in confidence_original field
```

**Acceptance Criteria**

- [x] System produces valid GeoJSON Feature (RFC 7946 compliant)
- [x] GeoJSON includes all required properties: source, confidence, type, timestamp, accuracy_flag
- [x] Coordinates in [longitude, latitude] format (RFC 7946 standard)
- [x] Confidence normalized to 0-1 scale with original preserved
- [x] Accuracy metadata included and validated
- [x] Audit trail metadata included
- [x] Multiple source formats handled (UAV, satellite, camera, API)
- [x] Generated GeoJSON parseable by standard tools (GeoJSON parsers, TAK Server, ArcGIS)
- [x] Transformation latency <100ms per detection
- [x] 100% of valid detections produce valid GeoJSON

**Technical Notes (Optional)**

- **Dependency**: US-002 (validation) must complete first
- **Standard**: RFC 7946 (official GeoJSON standard)
- **Libraries**: Use standard GeoJSON library for validation
- **Compatibility**: Must work with TAK Server, ArcGIS, CAD systems
- **Testing**: Validate output with GeoJSON linters
- **Evidence**: Interview 5 - "Need standard format for GIS systems"

---

### US-004: Output to TAK GeoJSON

**Title**: Dispatcher sees fire detection on tactical map in real-time

**Problem (The Pain)**

When detections arrive, they need to appear on the command team's Common Operating Picture (COP) system within seconds. Military TAK Server and emergency services CAD/GIS systems need to display detections with accuracy metadata and confidence levels.

> "We need detections on the COP within seconds of them being detected, not minutes." — Interview 1

> "If it breaks mid-mission, it breaks the whole operation." — Interview 1 (reliability concern)

**Who (The User)**

- **Command Team Dispatcher**: Sarah (military), Marcus (emergency services)
- **Context**: Viewing fire/vehicle/person detections on TAK map or CAD dashboard
- **Goal**: See detection on map within 2 seconds, with accuracy info
- **Success**: Detections appear in real-time, can navigate and make decisions

**Solution (What We Build)**

The system outputs validated and transformed detections to TAK Server GeoJSON subscription endpoint (or ArcGIS/CAD equivalent). Detections appear on the tactical map with:
- Point marker at coordinates
- Accuracy flag (GREEN/YELLOW/RED badge)
- Source identifier
- Confidence score
- Timestamp

If network unavailable, detections queue locally and sync when connection restored.

**Domain Examples**

### Example 1: Happy Path - Real-Time Detection on Map
```yaml
# Scenario: Fire detection appears on dispatcher's TAK map in real-time
Mission timeline:
  14:35:42 UTC: Fire detection occurs (satellite detects thermal signature)
  14:35:43 UTC: API returns detection JSON
  14:35:43 UTC: System ingests detection
  14:35:44 UTC: System validates and transforms to GeoJSON
  14:35:44 UTC: System outputs to TAK Server subscription
  14:35:45 UTC: TAK Client (dispatcher) receives update

On dispatcher's map:
  - Fire marker appears at coordinates [32.1234, -117.5678]
  - GREEN accuracy badge (±45m, conf 0.85)
  - Source: "Satellite Fire API"
  - Timestamp: 14:35:42 UTC (time of detection)
  - Dispatcher can click to see full properties

Decision: Dispatcher dispatches Engine 7 and Engine 12 to location
Time to decision: 3 seconds from detection to resources dispatching

Success metrics:
  ✓ Latency: 3 seconds (target: <2s, achieved)
  ✓ Accuracy badge visible
  ✓ Operator sees real-time data flow
  ✓ Can make tactical decision immediately
```

### Example 2: Error Case - TAK Server Temporarily Unreachable
```yaml
# Scenario: TAK Server is down for maintenance; system handles offline
Situation:
  - Detections arriving from satellite API (1 per minute)
  - TAK Server goes offline (scheduled maintenance)
  - System tries to push detection to TAK subscription

System behavior:
  Detection 1 (14:35:42): Push to TAK → FAIL (connection refused)
  System: Writes to local queue, marks PENDING_SYNC
  System: Logs: "TAK_SYNC_FAILED detection_1 (connection refused)"
  System: Attempts retry with exponential backoff

  Detection 2 (14:36:12): Push to TAK → FAIL
  System: Writes to local queue, marks PENDING_SYNC
  System: Retry backoff: 100ms → 150ms → 225ms → ...

  System: Status dashboard shows "TAK: OFFLINE (3 detections queued)"
  Operator: Sees status indicator but does NOT need to take action

  14:40:00 UTC: TAK Server comes back online
  System: Detects connectivity restored
  System: Syncs all 5 queued detections to TAK
  System: Detections appear on map (may be 4-5 minutes old)
  System: Dashboard shows: "TAK: SYNCED (5 items recovered)"

Recovery:
  - No data lost
  - Operator took no manual action
  - When TAK came back, all detections appeared
  - Timeline visible in audit trail

Time cost: 4-5 minute delay, but better than alternative (screenshots + manual entry)
```

### Example 3: Multi-Detection Stream - High Volume
```yaml
# Scenario: Multiple detections per minute during active fire
Situation:
  - Wild fire front is advancing through area
  - Multiple satellite passes detect new fires
  - UAV is also detecting fires
  - System receives 10+ detections per minute

System handling:
  14:35:42 - Detection 1: Fire at [32.1, -117.5] → TAK
  14:35:44 - Detection 2: Fire at [32.2, -117.4] → TAK
  14:35:46 - Detection 3: Vehicle at [32.15, -117.45] → TAK
  14:35:48 - Detection 4: Fire at [32.3, -117.6] → TAK
  ... (high frequency)

Dispatcher view:
  - Multiple markers appear on map
  - Each with confidence badge
  - Can see fire front advancing
  - Can track response progress
  - Can coordinate with multiple teams

Performance:
  - Each detection latency < 2 seconds
  - System handles 10+ detections/minute
  - TAK map responsive (not slow)
  - Operator can make real-time decisions

Success: Tactical advantage maintained during active incident
```

**UAT Scenarios (BDD)**

### Scenario 1: Detection appears on TAK map in real-time
```gherkin
Given a validated GeoJSON detection is ready for output
And TAK Server is connected and accepting updates
When the system outputs the detection to TAK GeoJSON subscription
Then TAK Server receives the GeoJSON Feature
And the detection appears on dispatcher's map within 2 seconds
And the map marker shows coordinates correctly
And the accuracy badge shows confidence level
And the source label shows detection origin
```

### Scenario 2: Queue and sync when network is unavailable
```gherkin
Given TAK Server is temporarily offline
And a fire detection arrives
When the system attempts to output to TAK
Then the push fails (connection refused)
And the system writes to local queue (SQLite)
And the detection is marked PENDING_SYNC
And the status dashboard shows "TAK: OFFLINE (1 detection queued)"
And the operator is NOT notified of the queue (transparent operation)

When TAK Server comes back online (30 seconds later)
Then the system detects connectivity restored
And automatically syncs the queued detection to TAK
And the detection appears on map (may be 30 seconds late)
And the dashboard shows "TAK: SYNCED (1 item recovered)"
And the operator sees no disruption
```

### Scenario 3: Multiple detections stream simultaneously
```gherkin
Given the system is receiving 10+ detections per minute
And each detection needs to be transformed and output
When each detection completes transformation
Then each is output to TAK independently
And each appears on map within 2 seconds of transform completion
And all markers appear on map (no overwriting, no loss)
And dispatcher can see fire front advancement
And system remains responsive
```

**Acceptance Criteria**

- [x] Validated GeoJSON detections output to TAK Server subscription endpoint
- [x] Detection appears on dispatcher's map within <2 seconds
- [x] Accuracy flag (GREEN/YELLOW/RED) visible on map marker
- [x] Source identifier visible (satellite, UAV, camera, etc.)
- [x] Confidence score accessible in properties
- [x] Timestamp visible (when detection occurred, not when received)
- [x] If TAK Server temporarily offline: detections queue locally
- [x] When TAK Server restored: all queued detections sync automatically
- [x] Operator sees no disruption during queue/sync (transparent)
- [x] System handles 10+ detections/minute without degradation
- [x] 99% of valid detections successfully output to TAK
- [x] No detections lost even during network outages

**Technical Notes (Optional)**

- **Dependency**: US-003 (GeoJSON transform) must complete first
- **TAK Integration**: TAK Server GeoJSON subscription endpoint (documented)
- **Resilience**: Local SQLite queue for offline scenarios
- **Network**: Handle timeouts, retries, backoff
- **Performance**: Sub-second latency for <100 detections/minute
- **Testing**: Mock TAK Server endpoint, simulate network failures
- **Evidence**: Interview 1 - "<2 second latency needed for tactical ops"

---

### US-005: Handle Offline Queuing and Sync

**Title**: System continues operating when network connection drops, syncs detections when restored

**Problem (The Pain)**

Field operations are unreliable. UAVs lose connectivity. APIs go down. When the system fails to output detections because of network issues, the current workaround is manual screenshots and manual data entry into the COP.

> "That fails probably 20-30% of the time. Either network issues, format issues, or configuration issues. I had to land, walk over to the ops tent, show them screenshots of the detections on my laptop screen. They manually entered the locations into TAK." — Interview 4

> "If detections queue locally and sync when connection restores, I don't have to manually screenshot." — Interview 4 (validation test)

**Who (The User)**

- **Field Operator**: UAV pilot or ground station operator
- **Context**: Flying mission over area, needs detections to reach ops center
- **Goal**: 99% of detections reach COP, even if connection intermittent
- **Success**: Offline queueing transparent to operator, automatic sync on reconnect

**Solution (What We Build)**

The system uses offline-first architecture:
1. Detections validated locally (always successful)
2. Attempt to write to remote database
3. If network unavailable: write to local SQLite queue, mark PENDING_SYNC
4. When network restored: automatically sync all queued detections
5. Status dashboard shows queue status (transparent to operator)

**Domain Examples**

### Example 1: Happy Path - Intermittent Connection Recovery
```yaml
# Scenario: UAV loses connection briefly, detections queue and sync
Timeline:
  14:35:00 - Connection OK, detection 1 syncs to remote DB (SYNCED)
  14:35:30 - Network drops (UAV flying into dead zone)
  14:35:42 - Detection 2 arrives, cannot reach remote DB
              System: Write to local queue, mark PENDING_SYNC
              Log: "Network offline, queued locally (1 pending)"
  14:36:12 - Detection 3 arrives, still offline
              System: Write to local queue (2 pending)
  14:36:42 - Detection 4 arrives, still offline
              System: Write to local queue (3 pending)
  14:37:00 - Connection restored (UAV exits dead zone)
  14:37:01 - System detects connectivity restored
              Begin sync: Sync detection 2
              Success: Detection 2 written to remote DB (SYNCED)
              Sync detection 3
              Success: Detection 3 written to remote DB (SYNCED)
              Sync detection 4
              Success: Detection 4 written to remote DB (SYNCED)
  14:37:05 - All synced, queue empty

Operator experience:
  T=14:35:30: UAV says "I'm heading into dead zone, connection may drop"
  T=14:35:42-14:36:42: Dashboard shows "Status: Buffering (3 pending)"
              No alarm, no action needed (transparent)
  T=14:37:01: Dashboard shows "Syncing: 3/3 complete"
  T=14:37:05: Dashboard shows "Status: Connected, 0 pending"
              All detections now visible on map
              No manual workaround needed
              No screenshot required
              No manual entry required

Success metrics:
  ✓ 4 detections received
  ✓ 3 buffered locally during offline period
  ✓ 3 auto-synced when reconnected
  ✓ 0 data loss
  ✓ 0 operator actions required
  ✓ 0 manual screenshots needed
```

### Example 2: Extended Outage - Longer Queue
```yaml
# Scenario: API server down for 10 minutes, queue grows
Situation:
  - Dispatch center's fire detection API goes down for maintenance
  - System still receiving detections from local sensors
  - Cannot forward to remote COP system

Timeline:
  14:00:00 - API goes down (scheduled maintenance window)
              System detects: "Fire detection API unreachable"
  14:00:30 - Detection 1 → Local queue (1 pending)
  14:01:00 - Detection 2 → Local queue (2 pending)
  14:01:30 - Detection 3 → Local queue (3 pending)
  ... (continue receiving, queuing)
  14:10:00 - API comes back online
  14:10:02 - System detects: "Fire detection API reachable"
              Begin batch sync of 20 detections
  14:10:15 - All 20 synced successfully
              Status: "Recovered 20 detections"

Operator experience:
  T=14:00:05: Dashboard shows "Fire API: OFFLINE (1 pending)"
  T=14:05:00: Dashboard shows "Fire API: OFFLINE (10 pending)"
  T=14:10:05: Dashboard shows "Fire API: SYNCING (15/20 complete)"
  T=14:10:15: Dashboard shows "Fire API: ONLINE (0 pending)"

Recovery:
  - 20 detections queued safely
  - No data lost
  - When API recovered, all 20 auto-synced
  - No operator intervention needed
  - No manual workaround deployed

Time cost: 10-minute delay, but no operational disruption
vs Alternative: Manual copy of detections from local log
```

### Example 3: Permanent Connection Loss - Recovery by Reboot
```yaml
# Scenario: System restarted while offline, recovers from persistent queue
Situation:
  - Fire detection system running on field equipment
  - Network disconnected, 15 detections queued locally
  - Equipment power cycled (intentional restart for update)
  - System boots back up

On startup:
  System initializes: "Checking local queue..."
  Found: 15 pending detections in SQLite
  Status: All marked PENDING_SYNC

  System checks network: "Network now available"
  Begin sync of 15 pending detections
  15/15 complete
  Status: "Queue recovered (15 items)"

Success:
  ✓ Detections survived reboot (persisted to SQLite)
  ✓ Auto-recovered on startup
  ✓ No manual recovery steps needed
  ✓ No data loss

This is the most resilient case - system survives power cycle
```

**UAT Scenarios (BDD)**

### Scenario 1: Detections queue locally when network unavailable
```gherkin
Given a detection is ready to output to remote database
And the network connection to remote database is lost
When the system attempts to sync the detection
Then the sync fails (connection refused)
And the detection is written to local SQLite queue
And the detection is marked PENDING_SYNC
And the status dashboard shows "Status: Buffering (1 pending)"
And no error is raised to the operator
```

### Scenario 2: Queued detections sync automatically when network restored
```gherkin
Given 3 detections are queued locally (PENDING_SYNC)
And the queue is persisted in SQLite
When network connectivity is restored
Then the system detects connection restored
And begins syncing queued detections (3/3)
And each detection is written to remote database (SYNCED)
And the status dashboard updates: "Status: Syncing 3/3 complete"
And all detections appear on remote COP system
And the local queue is cleared
```

### Scenario 3: Queue survives system restart
```gherkin
Given 5 detections are queued locally (PENDING_SYNC)
And the system is restarted (power cycle, intentional restart)
When the system boots back up
Then the queued detections are recovered from persistent storage
And the system detects network is available
And automatically syncs all 5 queued detections
And no operator action required for recovery
And status dashboard shows "Queue recovered (5 items synced)"
```

**Acceptance Criteria**

- [x] When network unavailable, detections queue to local SQLite database
- [x] Queue marked as PENDING_SYNC (not yet on remote)
- [x] Queued detections persist across system restarts
- [x] Queue size displayed on status dashboard
- [x] When network restored, automatic sync begins (no operator action)
- [x] All queued detections synced successfully (99%+ success rate)
- [x] Operator sees no errors or warnings for normal offline/sync cycle
- [x] Audit trail shows queue → sync timeline
- [x] Max queue size: 10,000 detections (before warning)
- [x] Sync latency when network restored: <5 seconds for first detection
- [x] No data loss during offline period or reboot
- [x] System continues validating detections even when offline

**Technical Notes (Optional)**

- **Dependency**: US-004 (TAK output) should be complete first
- **Storage**: SQLite database for local queue (persistent)
- **Sync Strategy**: Batch sync (process 100+ detections per second)
- **Retry**: Exponential backoff if sync fails during reconnect
- **Monitoring**: Track queue depth, sync success rate
- **Testing**: Simulate network outages, intentional power cycles
- **Evidence**: Interview 4 - "30% failure rate, need offline queueing"

---

## Integration & Configuration Stories (P1)

### US-006: Setup Detection Source Configuration

**Title**: Integration Specialist can register and configure a new detection source in <10 minutes

**Problem (The Pain)**

Setting up each new detection source requires complex configuration. APIs have different authentication methods, different response formats, different rate limits. Integration specialists need to document each one.

> "We looked at a couple of commercial ETL tools but they were either too generic or didn't understand the geospatial specifics we needed." — Interview 1

**Who (The User)**

- **Integration Specialist**: Marcus, technical team
- **Context**: Adding new fire detection, camera registry, UAV source
- **Goal**: Configuration in <10 minutes (not 2-3 weeks of code)

**Solution (What We Build)**

UI/API for registering detection sources:
- Source name and type
- API endpoint URL
- Authentication (API key, OAuth, etc.)
- Polling interval
- Field mapping (auto-detected if possible)
- Output format selection
- Testing/validation endpoint

---

### US-007: Auto-Detect Detection Format

**Title**: System automatically identifies API format instead of requiring manual configuration

**Problem (The Pain)**

Every vendor documents their API format differently. Integration specialists have to read docs, reverse-engineer by testing, or write custom code.

> "Configuration file approach is good, but you need auto-detection of format, not manual mapping." — Interview 1 (solution test)

**Who (The User)**

- **Integration Specialist**: Marcus
- **Context**: Adding new fire detection source
- **Goal**: Auto-detect format from sample response, not manual config

**Solution (What We Build)**

System fetches sample detection from API and analyzes:
- JSON structure (keys, types)
- Identifies lat/lon fields (latitude, lat, y, etc.)
- Identifies confidence fields
- Suggests field mapping
- User confirms or adjusts

---

## System Stories (P0 Infrastructure)

### US-008: Health Checks and System Status

**Title**: Operations Manager can see system health and detect failures

**Problem (The Pain)**

If the system goes down silently, operations don't know until they notice missing detections.

**Who (The User)**

- **Operations Manager**: Sarah
- **Context**: Monitoring system during active incident
- **Goal**: Know immediately if any component fails

**Solution (What We Build)**

Health check endpoint:
- `/health` returns JSON status
- Shows: System running, API connections status, queue status, TAK connection
- Status dashboard displays health
- Alerts on failures

---

### US-009: Audit Trail Logging

**Title**: Compliance officer can audit complete history of any detection

**Problem (The Pain)**

After-action reviews require knowing exactly what was detected, when, by whom, what flags were raised, what actions taken.

**Who (The User)**

- **Compliance Officer**: Needs to verify response was appropriate
- **Context**: Incident investigation
- **Goal**: Complete immutable audit trail

**Solution (What We Build)**

Audit trail captures:
- Detection received (timestamp, source, raw data)
- Processing steps (validation, flagging, transformation)
- Output sent (destination, timestamp)
- Operator actions (viewed, verified, dispatched)
- Retention: 90-day minimum

---

## Summary: Walking Skeleton Story Scope

```yaml
Total Stories: 9 (5 P0 + 2 P1 + 2 Infrastructure)

P0 Must-Have (MVP):
  US-001: Ingest JSON detections ✓
  US-002: Validate geolocation ✓ (killer feature)
  US-003: Transform to GeoJSON ✓
  US-004: Output to TAK ✓
  US-005: Offline queuing ✓
  US-008: Health checks ✓
  US-009: Audit trail ✓

P1 High-Value (MVP if time):
  US-006: Configuration UI ✓
  US-007: Format auto-detection ✓

Timeline: 8-12 weeks
Team: 2-3 engineers, 1 product owner
Success: <1 hour integration, 99% reliability, 80% time savings
```

**Document Status**: Ready for Acceptance Criteria & DoR Validation
**Next Step**: Create detailed acceptance criteria per story, validate DoR checklist
