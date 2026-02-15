# Shared Artifacts Registry
## AI Detection to COP Translation System

**Purpose**: Single source of truth for all constants, configurations, and data schemas used across the system. Every shared variable has documented ownership, usage, and tracking.

**Status**: Walking Skeleton MVP (Phase 1 Complete)
**Last Updated**: 2026-02-17
**Maintainer**: Product Owner + System Integration Engineer

---

## Table of Contents

1. [Accuracy & Validation Thresholds](#accuracy--validation-thresholds)
2. [Data Formats & Schemas](#data-formats--schemas)
3. [Coordinate Systems](#coordinate-systems)
4. [Polling & Timing Parameters](#polling--timing-parameters)
5. [Error Codes & Recovery](#error-codes--recovery)
6. [Confidence Normalization Mappings](#confidence-normalization-mappings)
7. [Audit Trail Metadata](#audit-trail-metadata)
8. [Integration API Contracts](#integration-api-contracts)
9. [Artifact Lifecycle & Change Management](#artifact-lifecycle--change-management)

---

## Accuracy & Validation Thresholds

### ARTIFACT: Accuracy Distance Threshold

```yaml
artifact_id: "THRESH_ACCURACY_METERS"
name: "Accuracy Distance Threshold"
value: 500
unit: "meters"
data_type: "number"
range: [10, 50000]

definition: >
  Detections with GPS accuracy > 500 meters are flagged YELLOW (caution).
  This threshold indicates acceptable geographic uncertainty for emergency response.

rationale: >
  Interview 1 (Military ISR ops manager):
    "If the UAV metadata is off by even 500 meters, the detections plot
     in the wrong location on the map. 500 meters is our threshold for concern."

  Interview 5 (GIS specialist):
    "We need sub-100-meter accuracy for emergency response. If something is
     off by more than that, we need to flag it."

  Recommendation: Start at 500m (high confidence), can be tuned per segment
    - Emergency Services: 100-500m depending on response type (fire vs. personnel)
    - Military/Tactical: 50-200m for targeting
    - Law Enforcement: 10-50m for street-level operations
    - GIS/Analysis: 100-1000m depending on data source reliability

impacts:
  - validation-service: Uses for accuracy flagging logic
  - accuracy-flagging: Determines GREEN/YELLOW/RED flag
  - dashboard: Displays accuracy flag status
  - operator-overrides: Required input for manual location correction

shared_by:
  - validation-service
  - accuracy-flagging-service
  - status-dashboard
  - audit-service

change_history:
  - version: "1.0.0"
    date: "2026-02-17"
    value: 500
    reason: "Walking skeleton baseline from Interview 1"
    changed_by: "Product Owner"
```

### ARTIFACT: Confidence Minimum Threshold

```yaml
artifact_id: "THRESH_CONFIDENCE_MIN"
name: "Minimum Confidence Score"
value: 0.6
unit: "normalized 0-1 scale"
data_type: "number"
range: [0.0, 1.0]

definition: >
  Detections with confidence < 0.6 are flagged YELLOW (requires spot-check).
  Detections with confidence < 0.4 are flagged RED (requires override).

rationale: >
  Interview 1 (Military ISR):
    "We trust 60% and above. Anything lower needs manual review because the
     detection might be a false positive."

  Interview 5 (GIS specialist):
    "Historical accuracy shows we should only trust confidence >= 0.6 for
     fire detection. Anything below that has too many false positives."

  Recommendation: 0.6 for MVP, consider segment-specific thresholds later
    - Military/Tactical: 0.7+ (high confidence for targeting)
    - Emergency Services: 0.6+ (balanced risk/false negative)
    - Law Enforcement: 0.5+ (more lenient for investigation)
    - GIS/Analysis: 0.4+ (lower confidence acceptable for analysis)

impacts:
  - confidence-normalizer: Determines if confidence is acceptable
  - accuracy-flagging: Combined with accuracy for flag determination
  - output-filter: May skip low-confidence detections entirely
  - operator-notification: Alerts dispatcher if low confidence

shared_by:
  - confidence-normalizer
  - accuracy-flagging-service
  - output-filter
  - alert-service

change_history:
  - version: "1.0.0"
    date: "2026-02-17"
    value: 0.6
    reason: "Walking skeleton baseline from Interview 1 and 5"
    changed_by: "Product Owner"
```

---

## Data Formats & Schemas

### ARTIFACT: GeoJSON Feature Schema (COP Output Format)

```yaml
artifact_id: "SCHEMA_GEOJSON_FEATURE"
name: "GeoJSON Feature Format (RFC 7946)"
type: "JSON Schema"
standard: "RFC 7946"
purpose: "Standard output format for all COP integrations (TAK, ArcGIS, CAD)"

schema:
  root:
    type: "object"
    required: ["type", "geometry", "properties"]
    properties:
      type:
        type: "string"
        enum: ["Feature"]
        description: "Fixed value for GeoJSON Feature"

      geometry:
        type: "object"
        required: ["type", "coordinates"]
        properties:
          type:
            type: "string"
            enum: ["Point"]
            description: "Detection represented as point location"
          coordinates:
            type: "array"
            items:
              type: "number"
            minItems: 2
            maxItems: 2
            description: "[longitude, latitude] per RFC 7946"

      properties:
        type: "object"
        required: ["source", "confidence", "type", "timestamp", "accuracy_flag"]
        properties:
          source:
            type: "string"
            description: "API/system source identifier (e.g., 'satellite_fire_api')"
            example: "satellite_fire_api"

          source_id:
            type: "string"
            description: "Unique identifier for this source instance"
            example: "sat_1"

          confidence:
            type: "number"
            minimum: 0.0
            maximum: 1.0
            description: "Normalized confidence 0-1 scale"
            example: 0.85

          confidence_original:
            type: "object"
            description: "Original confidence value before normalization"
            properties:
              value:
                type: "number"
                description: "Original confidence value"
                example: 85
              scale:
                type: "string"
                description: "Original scale (e.g., '0-100')"
                example: "0-100"

          type:
            type: "string"
            description: "Detection type (e.g., 'fire', 'vehicle', 'person')"
            example: "fire"

          timestamp:
            type: "string"
            format: "date-time"
            description: "ISO8601 timestamp when detection occurred"
            example: "2026-02-17T14:35:42Z"

          received_timestamp:
            type: "string"
            format: "date-time"
            description: "ISO8601 timestamp when we received the detection"
            example: "2026-02-17T14:35:43Z"

          accuracy_m:
            type: "number"
            minimum: 0
            maximum: 50000
            description: "GPS accuracy in meters"
            example: 45

          accuracy_flag:
            type: "string"
            enum: ["GREEN", "YELLOW", "RED"]
            description: "Accuracy confidence level"
            example: "GREEN"

          operator_notes:
            type: ["string", "null"]
            description: "Optional notes added by operator"
            example: "Verified against satellite imagery"

          reviewed_by:
            type: ["string", "null"]
            description: "Operator who manually verified"
            example: "Dispatcher John Smith"

          reviewed_at:
            type: ["string", "null"]
            format: "date-time"
            description: "When manual verification occurred"
            example: "2026-02-17T14:40:00Z"

          sync_status:
            type: "string"
            enum: ["SYNCED", "PENDING_SYNC", "FAILED"]
            description: "Sync status with remote database"
            example: "SYNCED"

example:
  type: "Feature"
  geometry:
    type: "Point"
    coordinates: [-117.5678, 32.1234]
  properties:
    source: "satellite_fire_api"
    source_id: "sat_1"
    confidence: 0.85
    confidence_original:
      value: 85
      scale: "0-100"
    type: "fire"
    timestamp: "2026-02-17T14:35:42Z"
    received_timestamp: "2026-02-17T14:35:43Z"
    accuracy_m: 45
    accuracy_flag: "GREEN"
    operator_notes: null
    reviewed_by: null
    reviewed_at: null
    sync_status: "SYNCED"

rationale: >
  Interview 1 (Military ISR): "Need GeoJSON output for TAK compatibility"
  Interview 3 (Emergency Services): "CAD system needs to understand output format"
  Interview 5 (GIS): "GeoJSON is standard for GIS systems"
  RFC 7946: Industry standard for geographic JSON

  Design choices:
  - [lon, lat] order per RFC 7946 (opposite of typical lat,lon)
  - Confidence preserved in BOTH normalized and original form
  - Accuracy metrics explicit and testable
  - Status tracking for sync audit trail

impacts:
  - output-service: Generates this format
  - tak-integration: Consumes this format
  - arcgis-integration: Consumes this format
  - cad-integration: Consumes this format
  - audit-service: Logs complete object

shared_by:
  - output-service
  - tak-server-adapter
  - arcgis-adapter
  - cad-adapter
  - audit-service
  - dashboard

change_history:
  - version: "1.0.0"
    date: "2026-02-17"
    reason: "Walking skeleton baseline, RFC 7946 compliant"
    changed_by: "Product Owner"

  - version: "2.0.0"
    date: "TBD"
    reason: "Add optional fields for advanced scenarios"
    changed_by: "TBD"
    planned_additions: ["confidence_historical_accuracy", "deduplication_metadata"]
```

### ARTIFACT: Detection Input Schema (API-Independent)

```yaml
artifact_id: "SCHEMA_DETECTION_INPUT"
name: "Normalized Detection Input Format"
type: "Internal schema"
purpose: "Common format for all detection inputs before transformation"

required_fields:
  - latitude: number (decimal degrees)
  - longitude: number (decimal degrees)
  - confidence: number (any scale)
  - detection_type: string (fire, vehicle, person, etc.)
  - timestamp: ISO8601 string

optional_fields:
  - accuracy_meters: number (GPS accuracy)
  - source_metadata: object (vendor-specific data)
  - camera_id: string (for camera-based detections)
  - sensor_id: string (for sensor-based detections)
  - classification_details: object (multi-class confidence scores)

example:
  latitude: 32.1234
  longitude: -117.5678
  confidence: 0.85
  detection_type: "fire"
  timestamp: "2026-02-17T14:35:42Z"
  accuracy_meters: 45
  source_metadata:
    satellite_id: "LANDSAT-8"
    band: "thermal"
    processing_time_ms: 324

rationale: >
  Allows different source APIs to be mapped to common format
  Simplifies processing pipeline (single schema instead of per-vendor)

  Sources handled by adapters:
  - Satellite API: [lat, lon, conf, timestamp] → normalized
  - Drone API: [lat, lon, conf, timestamp, accuracy] → normalized
  - Camera registry: camera_id → [lat, lon] → normalized
  - UAV GCS: binary + metadata → [lat, lon, conf, timestamp] → normalized

impacts:
  - input-adapter: Maps source format to this schema
  - validation-service: Expects this schema
  - processing-pipeline: Works with this schema
  - transformation-service: Transforms from this to GeoJSON

shared_by:
  - all input adapters
  - validation-service
  - processing-pipeline
  - transformation-service
```

---

## Coordinate Systems

### ARTIFACT: WGS84 (EPSG:4326)

```yaml
artifact_id: "COORD_WGS84"
name: "World Geodetic System 1984"
system_code: "EPSG:4326"
type: "Geographic coordinate system"
standard: "ISO 6709:2022"

definition:
  latitude_range: [-90, 90]
  longitude_range: [-180, 180]
  precision: "decimal degrees"
  units: "degrees"

example_valid:
  - [32.1234, -117.5678]   # Fire detection in California
  - [40.7128, -74.0060]    # New York City
  - [0.0, 0.0]             # Equator, Prime Meridian

example_invalid:
  - [500, -117.5678]       # Latitude out of range
  - [32.1234, 185.0]       # Longitude out of range
  - ["32.1234", -117.5678] # Latitude as string (type error)

rationale: >
  Interview 3 (Emergency Services):
    "Our CAD system uses WGS84, but the fire API outputs WGS84 too"
    "We also have state plane projections for some systems"

  GeoJSON standard: RFC 7946 requires WGS84
  TAK Server: Expects WGS84 for compatibility
  Most APIs: Default to WGS84 unless specified otherwise

  Why WGS84 instead of alternatives:
  - Global standard (works for international operations)
  - GPS standard (matches hardware output)
  - GeoJSON requirement (no choice for standard format)
  - Can transform to other systems on output

impacts:
  - coordinate-normalizer: Validates coordinates in this system
  - coordinate-transformer: May transform from/to other systems
  - geojson-builder: Outputs in WGS84 [lon, lat] format
  - accuracy-validator: Uses coordinate ranges to detect errors

shared_by:
  - coordinate-normalizer
  - coordinate-transformer
  - geojson-builder
  - validation-service

change_history:
  - version: "1.0.0"
    date: "2026-02-17"
    reason: "Standard for walking skeleton, GeoJSON requirement"
    changed_by: "Product Owner"
```

### ARTIFACT: State Plane Projection (Example: California Zone 6)

```yaml
artifact_id: "COORD_STATE_PLANE_CA6"
name: "State Plane Coordinate System - California Zone 6"
system_code: "EPSG:2230"
type: "Projected coordinate system"
region: "California (counties)"

rationale: >
  Interview 3 (Emergency Services):
    "Our CAD system uses state plane projection"
    "We need coordinate transformation from WGS84 to state plane"

  Use case: Emergency Services CAD systems often use state plane
  for local accuracy and integration with county/municipal systems

impacts:
  - coordinate-transformer: Handles WGS84 → State Plane conversion
  - cad-adapter: Outputs in state plane format
  - audit-service: Logs coordinate system conversion

notes: >
  Transformation is lossy (small accuracy loss in conversion)
  Always preserve original WGS84 in audit trail
  State plane specific to region - cannot use for military/national
  Future feature: support multiple state plane zones per region
```

---

## Polling & Timing Parameters

### ARTIFACT: API Polling Interval

```yaml
artifact_id: "PARAM_POLLING_INTERVAL_SEC"
name: "Detection API Polling Interval"
value: 30
unit: "seconds"
data_type: "number"
range: [5, 300]

definition: >
  The system polls detection APIs every 30 seconds.
  This controls the balance between data freshness and API load.

rationale: >
  Interview 3 (Emergency Services):
    "Current system polls every 30 seconds, sufficient for fire detection"
    "Any longer and we start missing detections"
    "Any shorter and we hammer the API unnecessarily"

  Trade-offs:
  - 5 second:  Freshest data, but high API load (720 requests/hour)
  - 30 second: Balanced (2,880 requests/hour), good for emergency services
  - 60 second: Stale data for tactical (unacceptable for military)
  - 300 second: Very low load, but 5-minute latency (unacceptable)

  Default for MVP: 30 seconds
  Configurable per source (some APIs may allow less frequent polling)

  API rate limit consideration:
  - Most public APIs: 600-1000 requests/hour limit
  - 30-second polling: 2,880 requests/day (acceptable)
  - 5-second polling: 17,280 requests/day (exceeds most limits)

impacts:
  - polling-service: Uses this interval for request loop
  - status-dashboard: Shows polling frequency
  - load-calculator: Used for capacity planning

shared_by:
  - polling-service
  - api-adapter
  - status-dashboard
  - capacity-planner

configuration:
  per-source: >
    Each detection source can override polling interval
    Example:
      - satellite_fire_api: 30 seconds (global coverage)
      - drone_detection: 5 seconds (regional focus)
      - camera_registry: 60 seconds (lower frequency, static lookup)

change_history:
  - version: "1.0.0"
    date: "2026-02-17"
    value: 30
    reason: "Walking skeleton baseline from Interview 3"
    changed_by: "Product Owner"
```

### ARTIFACT: Retry Backoff Strategy

```yaml
artifact_id: "PARAM_RETRY_BACKOFF"
name: "Exponential Backoff for API Retries"
type: "Algorithm configuration"

strategy: "exponential-backoff-with-jitter"

parameters:
  initial_delay_ms: 100
  max_delay_ms: 30000
  multiplier: 1.5
  jitter_factor: 0.1

algorithm:
  step_1: "First failure → wait 100ms, retry"
  step_2: "Second failure → wait 100 * 1.5 = 150ms, retry"
  step_3: "Third failure → wait 150 * 1.5 = 225ms, retry"
  step_4: "Fourth failure → wait 225 * 1.5 = 337ms, retry"
  step_5: "Fifth failure → wait 337 * 1.5 = 505ms, retry"
  step_6: "Sixth failure → wait 505 * 1.5 = 757ms, retry"
  step_7: "Seventh failure → wait 1135ms, retry"
  step_8: "Eighth failure → wait 1703ms, retry"
  step_9: "Ninth failure → wait 2554ms, retry"
  step_10: "Tenth failure → wait cap at 30000ms, continue retrying"

rationale: >
  Interview 3 (Emergency Services):
    "API sometimes goes down briefly, need graceful recovery"
    "Within 5-10 seconds we should have retry strategy"
    "After that, fall back to local queue"

  Why exponential backoff:
  - Reduces thundering herd (all clients hammering API simultaneously)
  - Gives API time to recover (don't immediately retry failed API)
  - Jitter prevents retry storms (randomizes retry timing)
  - Max delay caps memory/time impact

  Time to max delay: ~15 seconds (sufficient for most API recoveries)
  After max delay: continue retrying at 30s intervals until success

impacts:
  - retry-service: Implements this strategy
  - api-adapter: Uses for connection recovery
  - connection-manager: Monitors retry state
  - status-dashboard: Shows retry state

shared_by:
  - retry-service
  - api-adapter
  - connection-manager

change_history:
  - version: "1.0.0"
    date: "2026-02-17"
    values: "initial_100ms, max_30s, multiplier_1.5"
    reason: "Walking skeleton baseline"
    changed_by: "Product Owner"
```

---

## Error Codes & Recovery

### ARTIFACT: Error Code Registry

```yaml
artifact_id: "REGISTRY_ERROR_CODES"
name: "System Error Codes and Recovery Strategies"
type: "Error handling specification"

errors:

  E001:
    code: "INVALID_JSON"
    severity: "LOW"
    message: "Detection payload is not valid JSON"
    recovery_action: "Skip detection, continue polling"
    operator_notification: "None (transparent)"
    audit_log: "INVALID_JSON from source_id=X at timestamp=Y"
    root_causes:
      - "Detection API returned malformed JSON"
      - "UTF-8 encoding issue in response"
      - "Network corruption during transmission"
    prevention:
      - "Validate JSON schema before processing"
      - "Check Content-Type header for application/json"
      - "Implement connection timeout to detect corruption"
    impact: "Single detection lost, no system disruption"

  E002:
    code: "MISSING_COORDINATES"
    severity: "MEDIUM"
    message: "Detection has no location data"
    recovery_action: "Flag for manual review, do not output to COP"
    operator_notification: "Alert: Detection requires manual location entry"
    audit_log: "MISSING_COORDS from source_id=X"
    root_causes:
      - "API schema change (vendor stopped including lat/lon)"
      - "Optional field actually required"
      - "Location data redacted for privacy"
    prevention:
      - "Implement schema validation against source schema"
      - "Vendor communication for schema changes"
      - "Fallback: camera registry lookup if available"
    impact: "Detection queued for manual processing"

  E003:
    code: "OUT_OF_BOUNDS"
    severity: "MEDIUM"
    message: "Coordinates outside valid range or deployment area"
    recovery_action: "Flag RED, require operator override"
    operator_notification: "Alert: Suspicious location, manual review required"
    audit_log: "OUT_OF_BOUNDS lat=X lon=Y from source_id=Z"
    valid_ranges:
      latitude: [-90, 90]
      longitude: [-180, 180]
    root_causes:
      - "Coordinate system mismatch (vendor using different projection)"
      - "Sensor malfunction or calibration error"
      - "Data corruption or transmission error"
    prevention:
      - "Document expected coordinate ranges per source"
      - "Implement geofence checks (e.g., alert if detection outside service area)"
      - "Validate against historical bounds for source"
    impact: "Detection not output until verified"

  E004:
    code: "LOW_CONFIDENCE"
    severity: "LOW"
    message: "Confidence score below minimum threshold"
    recovery_action: "Flag YELLOW, output with warning badge"
    operator_notification: "Badge on map: 'Unverified detection'"
    audit_log: "LOW_CONFIDENCE score=X from source_id=Y"
    thresholds:
      yellow_flag: "confidence < 0.6"
      red_flag: "confidence < 0.4"
    root_causes:
      - "Detection system uncertain (poor image quality, edge case)"
      - "Environmental conditions (weather, lighting) affecting accuracy"
      - "Model calibration needs update"
    prevention:
      - "Monitor confidence distribution over time"
      - "Adjust model if too many low-confidence detections"
      - "Validate model performance against ground truth"
    impact: "Detection visible but flagged; operator discretion"

  E005:
    code: "API_UNREACHABLE"
    severity: "HIGH"
    message: "Cannot connect to detection source API"
    recovery_action: "Queue locally, retry with exponential backoff"
    operator_notification: "Dashboard shows: 'Source offline, buffering'"
    audit_log: "API_UNREACHABLE source_id=X error=Y"
    root_causes:
      - "Network connectivity lost (internet down, firewall block)"
      - "DNS failure (cannot resolve API hostname)"
      - "API server down for maintenance or failure"
      - "Connection timeout (API responding slowly)"
    retry_strategy: "Exponential backoff 100ms→30s, continue indefinitely"
    prevention:
      - "Implement health checks (ping API before polling)"
      - "Configure firewall rules to allow API access"
      - "Set connection timeout to detect slow responses quickly"
      - "Monitor DNS resolution"
    impact: "Detections queue locally until connection restored"

  E006:
    code: "SYNC_FAILED"
    severity: "HIGH"
    message: "Cannot push queued detections to remote database"
    recovery_action: "Keep in local queue, retry on next connection check"
    operator_notification: "Dashboard shows: 'Syncing 5 detections (retry)'"
    audit_log: "SYNC_FAILED queue_id=X error=Y"
    root_causes:
      - "Remote database unreachable"
      - "Write permission denied (auth issue)"
      - "Database capacity exceeded"
      - "Network timeout during write"
    retry_strategy: "Retry every 10 seconds until success"
    prevention:
      - "Verify database credentials before deployment"
      - "Monitor database capacity"
      - "Set connection timeout for database writes"
      - "Implement health check endpoint on database"
    impact: "Detections stay in local queue, system resilient"

shared_by:
  - error-handler
  - retry-service
  - alert-service
  - audit-service
  - status-dashboard

change_history:
  - version: "1.0.0"
    date: "2026-02-17"
    errors: ["E001", "E002", "E003", "E004", "E005", "E006"]
    reason: "Walking skeleton error handling"
    changed_by: "Product Owner"
```

---

## Confidence Normalization Mappings

### ARTIFACT: Confidence Scale Converters

```yaml
artifact_id: "REGISTRY_CONFIDENCE_SCALES"
name: "Confidence Scale Converters by Source"
type: "Data normalization specification"

converters:

  "satellite_fire_api":
    input_scale: "0-100"
    interpretation: "Probability of fire (0=no fire, 100=definite fire)"
    normalization_formula: "input_value / 100"
    example:
      input: 85
      output: 0.85
    historical_accuracy:
      accuracy_at_85plus: 0.78
      accuracy_at_70plus: 0.65
      note: "78% of detections with score >=85 are true fires"
    source_evidence: "Interview 5 - GIS specialist managing satellite feed"
    shared_by:
      - confidence-normalizer
      - accuracy-dashboard

  "drone_detection":
    input_scale: "0-1"
    interpretation: "Confidence score (0=uncertain, 1=certain)"
    normalization_formula: "input_value (no conversion needed)"
    example:
      input: 0.92
      output: 0.92
    historical_accuracy:
      accuracy_at_92plus: 0.91
      accuracy_at_80plus: 0.84
      note: "91% of detections with score >=0.92 are true fires"
    source_evidence: "Interview 5 - GIS specialist managing drone feed"
    shared_by:
      - confidence-normalizer
      - accuracy-dashboard

  "uav_ground_control_station":
    input_scale: "0-255"
    interpretation: "Certainty as 8-bit value"
    normalization_formula: "input_value / 255"
    example:
      input: 215
      output: 0.843
    historical_accuracy:
      accuracy_overall: 0.65
      note: "Less reliable than satellite or drone systems overall"
    source_evidence: "Interview 1 - Military ISR ops manager"
    shared_by:
      - confidence-normalizer
      - accuracy-dashboard

  "law_enforcement_camera_detection":
    input_scale: "0-100"
    interpretation: "Detection likelihood for suspect/vehicle/activity"
    normalization_formula: "input_value / 100"
    example:
      input: 75
      output: 0.75
    historical_accuracy:
      accuracy_at_75plus: 0.82
      note: "Higher accuracy than fire detection (fewer false positives)"
    source_evidence: "Interview 2 - Law enforcement intelligence analyst"
    shared_by:
      - confidence-normalizer
      - accuracy-dashboard

rationale: >
  Interview 5 (GIS Specialist):
    "Satellite uses 0-100 scale, drone uses 0-1. I have to normalize them"
    "Historical accuracy helps me understand which is more reliable"

  Design approach:
  - All scales normalized to 0-1 (standard range)
  - Original value preserved for audit trail
  - Historical accuracy documented for each scale
  - Can evolve as more data collected

impacts:
  - confidence-normalizer: Implements converters
  - accuracy-dashboard: Displays historical accuracy
  - operator-display: Shows normalized confidence with historical context
  - audit-service: Logs original + normalized + conversion formula

change_history:
  - version: "1.0.0"
    date: "2026-02-17"
    converters: ["satellite_fire_api", "drone_detection", "uav_gcs", "camera_detection"]
    reason: "Walking skeleton baseline from discovery interviews"
    changed_by: "Product Owner"
```

---

## Audit Trail Metadata

### ARTIFACT: Audit Trail Schema

```yaml
artifact_id: "SCHEMA_AUDIT_TRAIL"
name: "Complete Audit Trail Entry"
type: "Compliance and investigation specification"

schema:
  detection_id:
    type: "string"
    description: "Unique identifier for this detection"
    example: "sat_20260217_143542_a1b2c3"
    usage: "Primary key for audit lookups"

  source_api:
    type: "string"
    description: "Which API provided this detection"
    example: "satellite_fire_api"
    usage: "Track detection provenance"

  ingestion_timestamp:
    type: "ISO8601"
    description: "When we received the detection"
    example: "2026-02-17T14:35:43Z"
    usage: "Track latency and timeliness"

  processing_steps:
    type: "array"
    description: "All transformation steps completed"
    items:
      step_name: "Format validation"
      status: "PASS"
      timestamp: "2026-02-17T14:35:43.100Z"
      duration_ms: 2
      notes: "JSON schema valid"
    usage: "Trace complete processing path"

  flags_raised:
    type: "array"
    description: "Any warnings or concerns"
    items:
      flag_type: "YELLOW"
      reason: "Low confidence"
      value: 0.58
      threshold: 0.60
    usage: "Track data quality concerns"

  output_timestamp:
    type: "ISO8601"
    description: "When we sent to COP"
    example: "2026-02-17T14:35:44Z"
    usage: "Track output latency"

  sync_status:
    type: "enum"
    values: ["SYNCED", "PENDING_SYNC", "FAILED"]
    description: "Whether it reached remote DB"
    example: "SYNCED"
    usage: "Track data persistence"

  operator_action:
    type: "object"
    optional: true
    description: "Any operator interaction"
    properties:
      action_type: "enum" (VIEW, VERIFY, OVERRIDE, DISPATCH)
      user_id: "string"
      timestamp: "ISO8601"
      notes: "string"
    example:
      action_type: "DISPATCH"
      user_id: "dispatcher_john_smith"
      timestamp: "2026-02-17T14:45:00Z"
      notes: "Dispatched Engine 7 and Engine 12"
    usage: "Track all operator decisions"

retention_policy:
  minimum: "90 days"
    reason: "Federal compliance requirement (Interview 1)"
  recommended: "1 year"
  compliance_context:
    - "Military after-action reviews"
    - "Emergency response liability"
    - "Law enforcement chain of custody"

rationale: >
  Interview 1 (Military ISR):
    "We need to log what was translated and why, for after-action reviews"

  Interview 2 (Law Enforcement):
    "Need to know if it was human-reviewed before any action was taken"

  Interview 5 (GIS):
    "Need metadata that says where it came from, when it was detected,
     which analyst reviewed it"

  Use cases:
  - Incident investigation: "Why was resource dispatched to location X?"
  - Quality audit: "How many detections were flagged? What % were accurate?"
  - Compliance audit: "Show all detections that led to enforcement action"
  - After-action review: "Timeline of all detection processing"

impacts:
  - audit-service: Generates entries
  - compliance-reporting: Uses for audits
  - investigation-tools: Uses for incident review
  - dashboard: Shows timeline view

change_history:
  - version: "1.0.0"
    date: "2026-02-17"
    reason: "Walking skeleton baseline from discovery interviews"
    changed_by: "Product Owner"
```

---

## Integration API Contracts

### ARTIFACT: TAK Server Integration Contract

```yaml
artifact_id: "CONTRACT_TAK_SERVER"
name: "TAK Server Integration Interface"
type: "API contract"
endpoint: "TAK Server GeoJSON subscription endpoint"

input_format: "GeoJSON Feature (RFC 7946)"
input_example:
  type: "Feature"
  geometry:
    type: "Point"
    coordinates: [-117.5678, 32.1234]
  properties:
    source: "satellite_fire_api"
    confidence: 0.85
    type: "fire"
    timestamp: "2026-02-17T14:35:42Z"

expected_behavior:
  - "TAK Server receives GeoJSON via subscription"
  - "Parses feature and extracts geometry (Point, coordinates)"
  - "Displays on tactical map at [lat, lon]"
  - "Shows properties as popup/detail panel"
  - "Updates in real-time when new features arrive"

data_flow:
  step_1: "Our system transforms detection → GeoJSON"
  step_2: "Our system pushes GeoJSON to TAK endpoint"
  step_3: "TAK Server receives and parses"
  step_4: "TAK displays on map"
  step_5: "Operator sees detection in real-time"

performance_requirements:
  latency_target: "<2 seconds from our push to operator sees"
  throughput: "10+ detections per second"
  reliability: ">99% successful deliveries"

failure_modes:
  - "TAK Server unreachable: Queue locally, retry later"
  - "GeoJSON invalid: Log error, skip detection"
  - "TAK updates while queued: Use latest version on sync"

rationale: >
  Interview 1 (Military ISR):
    "Need to get detections into TAK, need real-time on map"

  TAK Server: De facto standard for military/emergency operations
  GeoJSON: Standardized format, TAK native support

impacts:
  - output-service: Generates and pushes GeoJSON
  - tak-adapter: Handles TAK-specific integration
  - retry-service: Retries if TAK unreachable

shared_by:
  - output-service
  - tak-adapter
  - status-dashboard

change_history:
  - version: "1.0.0"
    date: "2026-02-17"
    endpoint: "TAK Server GeoJSON subscription"
    reason: "Walking skeleton baseline"
    changed_by: "Product Owner"
```

---

## Artifact Lifecycle & Change Management

### Change Request Template

When any shared artifact needs to change, follow this process:

```yaml
change_request:
  id: "CHG-001"  # Unique ID for tracking
  artifact_id: "THRESH_ACCURACY_METERS"
  proposed_value: 250  # Changed from 500
  requested_by: "Integration Specialist"
  justification: >
    "Emergency Services segment requires sub-250m accuracy for
     structural damage assessment. Current 500m threshold results
     in too many YELLOW flags."

  impact_analysis:
    affected_services:
      - "accuracy-flagging-service: Will flag fewer detections YELLOW"
      - "dashboard: Will show fewer warnings"
      - "alert-service: Fewer notifications to operator"
    affected_segments:
      - "Emergency Services: POSITIVE (fewer false warnings)"
      - "Military/Tactical: NEUTRAL (still conservative)"
      - "Law Enforcement: POSITIVE (finer precision)"
    backwards_compatibility: "Detections previously flagged YELLOW may now be GREEN"
    risk_level: "LOW (affects flagging only, not data integrity)"

  approval_chain:
    - "Product Owner (authorization)"
    - "Systems Integration Engineer (ops validation)"
    - "Operations Manager (user validation)"

  rollout_plan:
    - "Change in non-production first"
    - "Validate with test data"
    - "Deploy with feature flag (can roll back)"
    - "Monitor first 24 hours"
    - "Document in release notes"

  status: "APPROVED"
  approved_date: "2026-02-20"
  effective_date: "2026-02-21"
```

### Artifact Dependency Graph

```
THRESH_ACCURACY_METERS (500m)
  ↓ used by
accuracy-flagging-service
  ↓ impacts
operator-notifications
  ↓ affects
accuracy-dashboard
  ↓ viewed by
dispatcher

THRESH_CONFIDENCE_MIN (0.6)
  ↓ used by
confidence-normalizer
  ↓ impacts
output-filter
  ↓ affects
detection-visibility

SCHEMA_GEOJSON_FEATURE
  ↓ generated by
output-service
  ↓ consumed by
tak-adapter, arcgis-adapter, cad-adapter
  ↓ displayed by
operator-dashboard

PARAM_POLLING_INTERVAL_SEC (30s)
  ↓ used by
polling-service
  ↓ affects
API-load, detection-freshness
  ↓ monitored by
capacity-planner
```

---

## Artifact Owners & Responsibilities

| Artifact | Owner | Validator | Can Change | Review Required |
|----------|-------|-----------|-----------|-----------------|
| THRESH_ACCURACY_METERS | System Int. Engineer | Operations Manager | Configuration GUI | High |
| THRESH_CONFIDENCE_MIN | Product Owner | GIS Specialist | Code + Config | High |
| SCHEMA_GEOJSON_FEATURE | Lead Engineer | Product Owner | Major version only | Critical |
| COORD_WGS84 | Lead Engineer | Integration Specialist | Never | N/A (standard) |
| PARAM_POLLING_INTERVAL_SEC | Operations Manager | Integration Specialist | Per-source config | Medium |
| REGISTRY_ERROR_CODES | Lead Engineer | Product Owner | Low risk additions | Medium |
| REGISTRY_CONFIDENCE_SCALES | Data Scientist | GIS Specialist | As calibration improves | Medium |
| SCHEMA_AUDIT_TRAIL | Compliance Officer | Security Review | Additions only | High |
| CONTRACT_TAK_SERVER | Integration Specialist | TAK ecosystem partner | Never (external) | N/A |

---

## Summary: Walking Skeleton Artifact Readiness

```
✓ Accuracy & Validation Thresholds: Complete (500m, 0.6 min confidence)
✓ Data Formats & Schemas: Complete (GeoJSON, Detection Input)
✓ Coordinate Systems: Complete (WGS84, State Plane optional)
✓ Polling & Timing: Complete (30s interval, exponential backoff)
✓ Error Codes: Complete (E001-E006 with recovery paths)
✓ Confidence Normalization: Complete (4 source scales documented)
✓ Audit Trail: Complete (compliance-ready schema)
✓ Integration Contracts: Complete (TAK Server integration)
✓ Change Management: Process defined, ready for evolving system

TOTAL SHARED ARTIFACTS TRACKED: 14 major + 8 sub-artifacts
MATURITY: Walking Skeleton ready for Phase 2 requirements crafting
```

**Document Status**: Ready for Requirements (Phase 2)
**Next Step**: Use these artifacts as foundation for user story acceptance criteria
