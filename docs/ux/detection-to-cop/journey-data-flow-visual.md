# Data Flow Journey: AI Detection to COP Translation System

**Status**: Walking Skeleton Architecture - Minimal End-to-End Flow
**Evidence Base**: Discovery interviews (5 customers, 5 segments)
**Context**: Emergency Services Integration (Fire Detection Case)
**Confidence**: HIGH - Based on Interview 3 actual integration workflow

---

## System Context (How Data Flows)

```
                    ┌──────────────────────────────────────────────┐
                    │   EXTERNAL DETECTION SOURCES                │
                    ├──────────────────────────────────────────────┤
                    │                                              │
    ┌───────────┐   │ Example: Wildfire Detection API             │
    │ Satellite │───→ REST API → JSON payload:                   │
    │ Fire Detect│  │   {location, confidence, timestamp}        │
    └───────────┘   │                                              │
                    │   Request:                                   │
    ┌───────────┐   │   GET /api/detections?since=2026-02-17T...  │
    │ Drone      │   │   Authorization: Bearer token              │
    │ Detection  ├───→ Response: [                                │
    └───────────┘   │   { lat: 32.1234, lon: -117.5678,         │
                    │     confidence: 0.85, type: "fire",        │
                    │     timestamp: 2026-02-17T14:35:42Z }      │
    ┌───────────┐   │   ]                                         │
    │ Camera    │   │                                             │
    │ Registry  ├───→ Database query: camera locations           │
    └───────────┘   │                                             │
                    │                                              │
                    └──────────────────────────────────────────────┘
                                    ↓
                    ┌──────────────────────────────────────────────┐
                    │  AI DETECTION TO COP SYSTEM                 │
                    │  (Walking Skeleton - Happy Path)            │
                    ├──────────────────────────────────────────────┤
                    │                                              │
    STEP 1: INGEST  │ 1. Receive detection payload from source   │
    ─────────────   │    Input: {lat, lon, confidence, ...}      │
                    │                                              │
                    │ 2. Validate format (is it valid JSON?)      │
                    │    Check: parseable, required fields exist  │
                    │    Status: ✓ or ✗ → Error handling         │
                    │                                              │
                    │ 3. Log receipt                              │
                    │    Event: "detection_received"              │
                    │    Metadata: source, timestamp, format      │
                    │                                              │
    STEP 2: VALIDATE│ 4. Normalize geolocation                   │
    ──────────────  │    Input: lat, lon (any format)            │
                    │    - Parse coordinate format (WGS84, etc) │
                    │    - Validate ranges (lat -90 to 90)       │
                    │    - Flag accuracy concerns                 │
                    │    Output: {lat_norm, lon_norm,            │
                    │     accuracy_m, confidence_flag}           │
                    │                                              │
                    │ 5. Check geolocation accuracy              │
                    │    - Compare against known boundaries      │
                    │    - Flag if >500m from expected area      │
                    │    - Flag if confidence <0.6               │
                    │    Result: "location_valid" or             │
                    │            "location_flagged"              │
                    │                                              │
                    │ 6. Attach metadata                          │
                    │    - Detection source ID                    │
                    │    - Timestamp (source and received)       │
                    │    - Confidence score (original + normalized)
                    │    - Operator/analyst who processed        │
                    │                                              │
    STEP 3: ENRICH  │ 7. Add source context (if available)       │
    ───────────────  │    - Camera ID → Camera location (LE)     │
                    │    - UAV ID → UAV home base (Military)    │
                    │    - Satellite ID → satellite coverage area│
                    │                                              │
                    │ 8. Normalize confidence to 0-1 scale       │
                    │    Input: confidence in any scale          │
                    │    Output: 0.0-1.0 normalized + mapping    │
                    │    Store: original value + conversion rule │
                    │                                              │
    STEP 4:         │ 9. Convert to GeoJSON format               │
    TRANSFORM       │    Input: normalized detection             │
    ───────────────  │    Output: {                               │
                    │      type: "Feature",                       │
                    │      geometry: {                            │
                    │        type: "Point",                       │
                    │        coordinates: [lon, lat]             │
                    │      },                                     │
                    │      properties: {                          │
                    │        source: "satellite_fire_api",        │
                    │        confidence: 0.85,                    │
                    │        type: "fire",                        │
                    │        timestamp: "2026-02-17T14:35:42Z",  │
                    │        accuracy_m: 45,                      │
                    │        accuracy_flag: "GREEN",              │
                    │        operator_notes: ""                   │
                    │      }                                      │
                    │    }                                        │
                    │                                              │
    STEP 5: QUEUE   │ 10. Store in local queue                   │
    & PERSIST       │    - If connected: write to remote DB      │
    ───────────────  │    - If offline: write to local SQLite     │
                    │    - Mark as: pending_sync / synced        │
                    │                                              │
                    │ 11. Generate unique ID                     │
                    │    Format: {source}_{timestamp}_{hash}     │
                    │    Example: sat_fire_20260217_143542_a1b2c3
                    │                                              │
    STEP 6: OUTPUT  │ 12. Stream to COP format                   │
    & DELIVER       │    - Output as TAK Server feed             │
    ───────────────  │    - Push to GeoJSON endpoint              │
                    │    - Subscribe services receive in <1s     │
                    │                                              │
                    │ 13. Audit log entry                         │
                    │    - Detection ID, source, timestamp       │
                    │    - Processing steps completed            │
                    │    - Confidence flags raised               │
                    │    - COP system informed                    │
                    │                                              │
                    │ 14. Update status dashboard                │
                    │    - Feed: "active" (last detection 30s) │
                    │    - Queue: 0 items pending                │
                    │    - Sync status: "OK"                     │
                    │                                              │
                    └──────────────────────────────────────────────┘
                                    ↓
                    ┌──────────────────────────────────────────────┐
                    │   DOWNSTREAM COP SYSTEMS                    │
                    ├──────────────────────────────────────────────┤
                    │                                              │
    ┌───────────┐   │ Dispatch dashboard shows:                  │
    │  TAK      │←──→ - Fire detection at [32.1234, -117.5678]  │
    │ Server    │   │ - Green confidence flag                   │
    │           │   │ - "Satellite API" source badge           │
    └───────────┘   │ - Timestamp: 2026-02-17 14:35:42 UTC      │
                    │                                              │
    ┌───────────┐   │ Dispatcher action:                          │
    │  CAD      │←──→ - View full detection properties           │
    │ System    │   │ - Add operator notes                       │
    │ (ArcGIS)  │   │ - Dispatch resources                       │
    └───────────┘   │ - System logs the action                   │
                    │                                              │
    ┌───────────┐   │ Operator sees:                              │
    │ Mobile    │   │ - Detection on tactical map                │
    │ COP       │   │ - Accuracy metric                          │
    │ (ATAK)    ├───→ - Can override if incorrect               │
    └───────────┘   │ - System logs override                     │
                    │                                              │
                    └──────────────────────────────────────────────┘
```

---

## Walking Skeleton: Happy Path (Single Fire Detection)

```
TIME    STEP                          INPUT                  STATE              OUTPUT
────    ──────────────────────────────────────────────────────────────────────────────────

T+0     1. API Pull (every 30s)
        → Request /api/detections     Active polling         ✓ Requesting

T+0.2   2. Detect arrives             {"lat":32.1234,        Parse success       GeoJSON queued
                                      "lon":-117.5678,       for output
                                      "conf":0.85}

T+0.3   3. Ingest validation          JSON schema check      ✓ All fields       Format valid
                                      - Required fields ok   present
                                      - Ranges OK

T+0.4   4. Geolocation normalize      WGS84 coordinates      ✓ In bounds        Normalized:
        & validation                  lat: 32.1234 ✓         Valid range        32.1234, -117.5678
                                      lon: -117.5678 ✓       ✓ Accuracy OK
                                      Range checks            (±45m per
                                      Boundary checks         source metadata)

T+0.5   5. Accuracy flagging          Satellite metadata:    Accuracy: 45m      Flag: GREEN
                                      ±45m typical           <500m threshold    (confidence 0.85
                                      Confidence: 0.85       >0.6 threshold      passes all checks)
                                      Threshold: >0.6

T+0.6   6. Metadata enrichment        Source: "satellite"    Timestamp logged    Enhanced payload:
                                      Detection time:        Received time:      - source_id: sat_1
                                      2026-02-17T14:35:42Z   2026-02-17T14:35:43 - timestamps
                                      Received: T+0.3        Confidence norm: ✓  - confidence
                                      Operator: system

T+0.7   7. Coordinate transform       Input WGS84            Check projection    Output WGS84
                                      (no transform needed    requirement:        (standard for
                                      for GeoJSON)           GeoJSON uses        GeoJSON, TAK)
                                      Target: GeoJSON        WGS84 ✓

T+0.8   8. Normalize confidence       Input: 0.85            Scale check:        Output: 0.85
                                      Source scale: 0-1      already 0-1         (no conversion
                                      (satellite uses 0-1)   No conversion       needed)
                                                             needed

T+0.9   9. Build GeoJSON              Feature template       JSON structure      GeoJSON built:
                                      + enriched data        generated           {
                                      Geometry: Point        ✓ Valid            "type": "Feature",
                                      Coordinates: [lon,lat] JSON               "geometry": {...},
                                      Properties: {...}                         "properties": {...}
                                                                                }

T+1.0   10. Persistence decision      Network status:        Connected ✓         Queue: write to
        (Connected case)              Online to remote       Write to remote     remote DB
                                      Write attempt          DB success          Status: SYNCED
                                                             ✓ Confirmed

T+1.1   11. Generate audit entry      Detection ID:          ID generated        Audit logged:
                                      sat_20260217_         All steps OK         detection_id,
                                      143542_a1b2           Source → output      source,
                                      All steps completed                        timestamps,
                                                                                 flags, status

T+1.2   12. Output to COP format      GeoJSON payload        TAK subscription    Push to TAK
        (TAK Server)                  Ready to push          listening           GeoJSON endpoint
                                      Detection              ✓ Connected         Real-time update
                                      timestamp: T+0

T+1.3   13. Operator sees             TAK display updates    ✓ Received          Map shows:
        detection on map              Detection appears      ✓ Rendered          - Point marker
                                      Green confidence flag  Detection visible   - "Fire Detection"
                                      at coordinates         on tactical map     - Confidence badge

T+2.0   14. Optional: Dispatcher      Operator clicks        ✓ Load details      Full detection
        action                        detection              Card displayed      properties shown
                                      Views full info        Operator can        Ready for action
                                      Adds notes: "Gate      annotate            (resource dispatch,
                                      area, staging area    ✓ Notes saved       investigation,
                                      at coordinates X")     Audit logged        etc.)


TOTAL LATENCY: ~2 seconds end-to-end (from API → dispatcher sees on map)
```

---

## Error Path Example: Offline Resilience

```
SCENARIO: Network disconnects during T+1.0 (at persistence layer)

T+0.9   Detection ready to persist
        Network status check: Offline ✗

T+1.0   OFFLINE BRANCH:
        → Write to LOCAL QUEUE (SQLite)
        Status: PENDING_SYNC
        GeoJSON: {same as above, + sync_id}
        Log: "Network offline, queued locally"

T+1.1   System monitors connection
        Attempt: TCP handshake every 5s (exponential backoff)

T+1.5   CONNECTION RESTORED
        Retry queue:
        - Check for pending items (1 item)
        - Attempt push to remote DB
        - Success: UPDATE queue status → SYNCED
        - Log: "Queue synced (1 items)"

T+1.6   Operator dashboard updates:
        - Status panel shows: "Sync: OK (1 item recovered)"
        - Detection appears on map (may be delayed 5-10s)
        - No operator action needed - automatic recovery
        - Audit trail shows queue → sync timeline


COST OF OFFLINE: ~5-10 second additional latency
COST OF ALTERNATIVE (manual screenshot): 5-10 minutes + manual entry errors
SAVINGS: 99%+ of manual workaround time eliminated
```

---

## Operator/Integrator Journey: Setup to Operations

```
ROLE: Systems Integration Engineer (Emergency Services)
CONTEXT: Integrating fire detection API into dispatch center
BASELINE: 2-3 weeks custom integration work per Interview 3
TARGET: <1 hour setup time

┌─────────────────────────────────────────────────────────────────┐
│ PHASE 1: INSTALLATION (5 minutes)                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ Step 1: Deploy System                                          │
│   Action: Run "docker pull detection-to-cop:latest"           │
│   Action: docker run -e API_TOKEN=xxx -e COP_ENDPOINT=yyy    │
│   Result: Service running on localhost:8080                   │
│   Confidence: HIGH (containerized, known good)               │
│                                                                 │
│ Step 2: Verify Installation                                    │
│   Check: curl http://localhost:8080/health                    │
│   Result: {"status": "OK", "version": "1.0.0"}               │
│   Confidence: HIGH (self-evident success)                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ PHASE 2: CONFIGURATION (10 minutes)                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ Step 1: Add Detection Source                                   │
│   UI: Configuration → Add Detection Source                     │
│   Choose: "Wildfire Detection API" template                   │
│   (Auto-detected from API discovery)                          │
│   Confidence: MEDIUM-HIGH (templates provided)               │
│                                                                 │
│ Step 2: Configure API Connection                               │
│   Input: API endpoint: https://api.fire.detection.io/v1      │
│   Input: Auth token: [paste from vendor docs]                 │
│   Test: "Test Connection" → Success in <2s                    │
│   Confidence: HIGH (live test confirms)                       │
│                                                                 │
│ Step 3: Configure Output                                       │
│   Choose: Output format: TAK GeoJSON                          │
│   Choose: COP endpoint: http://tak-server:8080               │
│   Choose: Polling interval: 30 seconds                        │
│   Confidence: HIGH (sensible defaults provided)              │
│                                                                 │
│ Step 4: Configure Accuracy Flagging                            │
│   Set: Accuracy threshold: 100 meters                          │
│   Set: Confidence threshold: 0.7                               │
│   Set: Flag low accuracy detections: YES                       │
│   Confidence: HIGH (documentation clarifies intent)          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ PHASE 3: VALIDATION (15 minutes)                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ Step 1: Dry-Run Detection                                      │
│   Action: "Fetch Test Data" from API                           │
│   Result: Shows sample detection from last 24 hours           │
│   Confidence: HIGH (real data, no transformation yet)         │
│                                                                 │
│ Step 2: Transform & Validate                                   │
│   Simulate: Transform test detection through pipeline          │
│   Show: "What detection would look like on TAK"              │
│   Display: {                                                   │
│     "source": "fire_api_test",                                │
│     "location": [32.1234, -117.5678],                        │
│     "accuracy": "45m ✓ PASS",                                │
│     "confidence": 0.85 (normalized from 85/100)             │
│   }                                                            │
│   Confidence: HIGH (can see exactly what happens)            │
│                                                                 │
│ Step 3: Confirm with Ops Team                                  │
│   Share: "Does this detection look right?"                    │
│   Check: Map coordinates match known fire location           │
│   Check: Accuracy flag matches expected ground truth         │
│   Decision: "Looks good, deploy"                              │
│   Confidence: HIGH (validated with actual ops context)       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ PHASE 4: DEPLOYMENT (5 minutes)                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ Step 1: Enable Live Feed                                       │
│   Button: "Enable Live Detection Feed"                        │
│   Status: Polling started (every 30s)                         │
│ Confidence: HIGH (explicit enable, clear action)             │
│                                                                 │
│ Step 2: Monitor Dashboard                                      │
│   Watch: Status panel shows live statistics                   │
│   Display: {                                                   │
│     "Feed Status": "ACTIVE (3 detections in last 5 min)",    │
│     "Last Detection": "2026-02-17 14:35:42 UTC",            │
│     "Queue Status": "0 pending (connected)",                  │
│     "Error Rate": "0% (0 errors)",                           │
│     "Latency": "1.2s average"                                │
│   }                                                            │
│ Confidence: MEDIUM (early data, but trending good)           │
│                                                                 │
│ Step 3: Declare Success                                        │
│   Status: Integration complete                                │
│   Total time: ~35 minutes                                      │
│   Baseline: 2-3 weeks (custom code approach)                 │
│   Time saved: 94% faster                                      │
│ Confidence: HIGH (objective measurements)                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

EMOTIONAL ARC (Integration Specialist):
├─ Start: Anxious ("We're looking at another 2-3 week project")
├─ T+5min: Cautiously optimistic ("Installation was easy")
├─ T+15min: Uncertain ("Is the configuration correct?")
├─ T+20min: Confident ("Dry run looks right!")
├─ T+30min: Relieved ("We're done. Actually done.")
└─ End: Validated ("This actually works. We saved weeks.")
```

---

## Emotional Arc Analysis

### How Users Feel Throughout Data Journey

```
MILITARY OPERATIONS MANAGER (Interview 1):
Start of Mission:
  ├─ Anxiety: "We have 3 feeds to get integrated before 0600 hours"
  ├─ Frustration: "Last time this took 45 minutes to get right"
  └─ Pressure: "Junior analyst is already working on manual parsing"

With Current System (Custom Python):
  ├─ T+15min: Fragile ("I'm checking logs, still parsing feed 1")
  ├─ T+30min: Doubt ("Feed 2 has a new format, we're debugging")
  ├─ T+35min: Frustration ("Python script broke again, coordinate mismatch")
  ├─ T+45min: Relief ("OK, all three feeds parsed")
  ├─ T+45-75min: Exhaustion ("Spot-checking coordinates manually, 30 locations")
  └─ End: Uncertain ("Are we ready to go? Did we miss a bad coordinate?")

With New System (Geolocation Validation):
  ├─ T+5min: Confidence ("System is running, feeds auto-detected")
  ├─ T+10min: Trust ("Format translation happened automatically")
  ├─ T+15min: Relief ("Green checkmarks on all coordinates")
  ├─ T+20min: Certainty ("System flagged 2 low-accuracy detections, I verified manually")
  └─ End: Ready ("Mission can start on time, confidence in data")

TIME SAVED: 45 minutes → 15 minutes (67% reduction)
CONFIDENCE GAIN: "Uncertain" → "Mission-ready"

---

EMERGENCY SERVICES INTEGRATION SPECIALIST (Interview 3):
Before (Manual Integration):
  ├─ Week 1: Frustration ("Vendor docs are incomplete, reverse-engineering API")
  ├─ Week 2: Overwhelmed ("Three systems to coordinate: API, CAD, COP")
  ├─ Week 3: Doubtful ("Still debugging coordinate transformation")
  └─ End: Exhausted ("Done but fragile, update will break it")

With New System:
  ├─ T+30min: Surprise ("Really that simple?")
  ├─ T+45min: Confidence ("Dry run matches what I expect")
  ├─ T+60min: Relief ("Live feed is working, no custom code needed")
  └─ End: Empowered ("I can integrate another source this week")

WORKLOAD IMPACT: 3 weeks → 1 hour = 99% time savings
PSYCHOLOGICAL: From "dread of next integration" → "excited to add more sources"
```

---

## Shared Artifacts Registry

### Single Source of Truth for All Constants & Configurations

```yaml
shared_artifacts:

  # ACCURACY & VALIDATION THRESHOLDS
  accuracy:
    threshold_meters: 500
    description: "Flag detections >500m from expected area"
    source: "Interview 1 - Military ISR ops manager stated: '500 meter error is unacceptable'"
    impact: "Geolocation validation step uses this to determine GREEN/YELLOW/RED flags"
    shared_by: ["validation-service", "accuracy-flagging", "dashboard"]

  confidence_minimum:
    threshold: 0.6
    description: "Minimum confidence score to pass without flagging"
    scale: "0.0-1.0 normalized"
    source: "Interview 1 - 'We trust 60% and above, anything lower needs review'"
    impact: "Accuracy flagging uses this to determine flag status"
    shared_by: ["validation-service", "accuracy-flagging", "audit-trail"]

  # DATA FORMATS & SCHEMAS

  geojson_feature:
    type: "GeoJSON Feature (RFC 7946)"
    schema: |
      {
        "type": "Feature",
        "geometry": {
          "type": "Point",
          "coordinates": [longitude, latitude]  # Note: [lon, lat] per GeoJSON spec
        },
        "properties": {
          "source": string,                      # "satellite_fire_api", "drone_detection", etc
          "source_id": string,                   # Unique identifier for source
          "confidence": number,                  # 0.0-1.0 normalized
          "confidence_original": {               # Preserve original for audit
            "value": number,
            "scale": string                      # "0-1", "0-100", etc
          },
          "type": string,                        # "fire", "vehicle", "person", etc
          "timestamp": ISO8601,                  # When detection occurred
          "received_timestamp": ISO8601,         # When we received it
          "accuracy_m": number,                  # GPS accuracy in meters
          "accuracy_flag": enum,                 # "GREEN", "YELLOW", "RED"
          "operator_notes": string,              # Operator can override with notes
          "reviewed_by": string,                 # Operator who verified
          "reviewed_at": ISO8601,                # When operator verified
          "sync_status": enum                    # "SYNCED", "PENDING_SYNC", "FAILED"
        }
      }
    source: "Interview 3 - Emergency services CAD integration; Interview 5 - GIS accuracy requirements"
    impact: "All output transformations produce this schema"
    shared_by: ["output-service", "tap-server", "arcgis-integration", "dashboard"]

  # COORDINATE SYSTEMS

  coordinate_system_wgs84:
    name: "World Geodetic System 1984"
    system_code: "EPSG:4326"
    description: "Standard geographic coordinate system (latitude, longitude)"
    lat_range: [-90, 90]
    lon_range: [-180, 180]
    precision: "decimal degrees"
    example: {lat: 32.1234, lon: -117.5678}
    source: "Interview 3 - 'Our CAD system uses WGS84, but the fire API outputs WGS84 too'"
    impact: "Normalization checks coordinates against this range"
    shared_by: ["validation-service", "coordinate-transformer"]

  coordinate_system_state_plane:
    name: "State Plane Coordinate System (California Zone 6)"
    system_code: "EPSG:2230"
    description: "Projection used by California emergency services"
    conversion_needed: true
    source: "Interview 3 - 'Our CAD system uses state plane projection'"
    impact: "May require transformation for some COP systems"
    shared_by: ["coordinate-transformer", "emergency-services-integration"]

  # POLLING & TIMING

  polling_interval_seconds: 30
  description: "How frequently we poll detection APIs for new data"
  rationale: "Interview 3 - 'Current system polls every 30s, sufficient for fire detection'"
  impact: "Data freshness trade-off: lower = fresher but more load, higher = stale data risk"
  shared_by: ["polling-service", "dashboard"]

  retry_backoff_strategy:
    initial_delay_ms: 100
    max_delay_ms: 30000
    multiplier: 1.5
    description: "Exponential backoff for retrying failed API calls"
    rationale: "Interview 3 - 'API sometimes goes down briefly, need graceful recovery'"
    impact: "Connection resilience without hammering failed endpoints"
    shared_by: ["polling-service", "connection-manager"]

  offline_queue_persistence:
    storage_type: "SQLite"
    description: "Local queue when connection to remote is lost"
    max_queue_size: 10000
    schema: "detection_id, payload, status, created_at, synced_at"
    rationale: "Interview 4 - 'System fails 30% of the time, need to queue and retry'"
    impact: "Enables offline-first architecture for reliability"
    shared_by: ["queue-service", "sync-service", "status-dashboard"]

  # ERROR CODES

  error_codes:
    E001:
      code: "INVALID_JSON"
      message: "Detection payload is not valid JSON"
      recovery: "Log and skip detection, continue polling"
      example: "Malformed API response"
      source: "Interview 3 - 'Sometimes API returns garbage, need graceful handling'"

    E002:
      code: "MISSING_COORDINATES"
      message: "Detection has no location data"
      recovery: "Flag for manual review, don't output to COP"
      example: "Detection missing lat/lon fields"

    E003:
      code: "OUT_OF_BOUNDS"
      message: "Coordinates outside expected geographic area"
      recovery: "Flag YELLOW, require operator verification before using"
      example: "Detection at lat=500 (invalid)"

    E004:
      code: "LOW_CONFIDENCE"
      message: "Confidence score below threshold"
      recovery: "Flag YELLOW/RED depending on severity"
      example: "Confidence=0.3 < threshold 0.6"

    E005:
      code: "API_UNREACHABLE"
      message: "Cannot connect to source API"
      recovery: "Use offline queue, attempt retry with backoff"
      example: "Network timeout, connection refused"

    E006:
      code: "SYNC_FAILED"
      message: "Cannot push queued detections to remote"
      recovery: "Keep in queue, retry on next connection attempt"
      example: "Remote DB temporarily unavailable"

  # AUDIT TRAIL METADATA

  audit_trail_entry:
    fields:
      - detection_id: "Unique identifier for this detection"
      - source: "Which API/system provided this detection"
      - ingestion_timestamp: "When we received it"
      - steps_completed: "All processing steps that succeeded"
      - steps_failed: "Any processing steps that failed"
      - flags_raised: "YELLOW/RED flags set"
      - output_timestamp: "When we sent to COP"
      - sync_status: "Whether it reached remote DB"
      - operator_action: "Operator verification or override"
      - notes: "Free-text operator notes"
    retention: "Immutable 90-day minimum per federal compliance (Interview 1)"
    shared_by: ["audit-service", "compliance-reporting", "investigation-tools"]

  # CONFIDENCE NORMALIZATION MAPPINGS

  confidence_scales:
    "satellite_fire_api":
      input_scale: "0-100"
      interpretation: "Probability of fire (0=no fire, 100=definite fire)"
      normalization_formula: "input_value / 100"
      historical_accuracy: "78% correct when >=70"
      source: "Interview 5 - 'Satellite system uses 0-100 scale'"

    "drone_detection":
      input_scale: "0-1"
      interpretation: "Confidence score (0=uncertain, 1=certain)"
      normalization_formula: "input_value (no conversion needed)"
      historical_accuracy: "91% correct when >=0.8"
      source: "Interview 5 - 'Drone system already uses 0-1'"

    "uav_gcs":
      input_scale: "0-255"
      interpretation: "Certainty as 8-bit value"
      normalization_formula: "input_value / 255"
      historical_accuracy: "65% correct overall"
      source: "Interview 1 - 'Ground station uses 0-255, less reliable than others'"
```

---

## Integration Checkpoints Between Steps

```
CHECKPOINT 1: Format Validation → Normalization
├─ Precondition: JSON parsed successfully
├─ Data: detection object with required fields
├─ Check: All fields have expected types
├─ Success: Proceed to geolocation normalization
├─ Failure: Log E001, continue polling
├─ Responsible: validation-service

CHECKPOINT 2: Geolocation Normalization → Accuracy Check
├─ Precondition: Coordinates parsed and in valid range
├─ Data: lat/lon as decimal degrees
├─ Check: Both within [-90,90] and [-180,180] ranges
├─ Success: Proceed to accuracy flagging
├─ Failure: Log E003 or E004, flag RED, require override
├─ Responsible: coordinate-transformer

CHECKPOINT 3: Accuracy Check → Confidence Normalization
├─ Precondition: Location validated, accuracy determined
├─ Data: location_valid flag, accuracy_m value
├─ Check: Confidence >=0.6 threshold
├─ Success: Proceed to confidence scale normalization
├─ Failure: Flag YELLOW/RED, queue for review
├─ Responsible: accuracy-flagging

CHECKPOINT 4: Confidence Normalization → Metadata Enrichment
├─ Precondition: Confidence normalized to 0-1 scale
├─ Data: original confidence, scale, normalized value
├─ Check: Mapping rule applied correctly
├─ Success: Proceed to GeoJSON building
├─ Failure: Log with original value + conversion error
├─ Responsible: confidence-normalizer

CHECKPOINT 5: Metadata Enrichment → GeoJSON Transform
├─ Precondition: All data enriched and validated
├─ Data: detection object + accuracy + confidence + metadata
├─ Check: Required GeoJSON fields present
├─ Success: Proceed to persistence layer
├─ Failure: Missing fields = cannot output, require manual review
├─ Responsible: geojson-builder

CHECKPOINT 6: GeoJSON Transform → Persistence
├─ Precondition: Valid GeoJSON Feature object
├─ Data: GeoJSON + audit metadata
├─ Check: Network connectivity status
├─ Success Path A (Connected): Write to remote DB, mark SYNCED
├─ Success Path B (Offline): Write to local queue, mark PENDING_SYNC
├─ Failure: Log E006, retry queue on next connection
├─ Responsible: persistence-layer

CHECKPOINT 7: Persistence → Output Delivery
├─ Precondition: GeoJSON persisted successfully
├─ Data: GeoJSON + detection_id
├─ Check: TAK Server connection active
├─ Success: Push to TAK endpoint, return to operator in <2s
├─ Failure: Log E005, keep in persistence, retry
├─ Responsible: output-service

CHECKPOINT 8: Output Delivery → Audit Logging
├─ Precondition: Detection delivered to COP
├─ Data: All processing steps, timestamps, flags
├─ Check: All required audit fields recorded
├─ Success: Entry persisted in audit trail
├─ Failure: Log audit failure, mark detection for investigation
├─ Responsible: audit-service
```

---

## Summary: Data Journey Maturity Model

```
┌─────────────────────────────────────────────────────────┐
│ MATURITY LEVEL 0: Current State (Customer Baseline)    │
├─────────────────────────────────────────────────────────┤
│ - Manual format translation (2-3 weeks per source)     │
│ - Manual geolocation validation (30 min per mission)   │
│ - 20-30% failure rate (manual workarounds)            │
│ - Audit trail: ad-hoc, incomplete                      │
│ - Integration time: WEEKS                              │
│ - Operator confidence: LOW                             │
└─────────────────────────────────────────────────────────┘
                           ↓↓↓
┌─────────────────────────────────────────────────────────┐
│ MATURITY LEVEL 1: Walking Skeleton MVP (Target)        │
├─────────────────────────────────────────────────────────┤
│ - Auto format detection (JSON/REST APIs)               │
│ - Geolocation validation + flagging (80% time savings) │
│ - Offline queuing + sync (99% reliability)             │
│ - Audit trail: Complete, immutable                     │
│ - Integration time: <1 HOUR                            │
│ - Operator confidence: HIGH                            │
│ - Latency: <2 seconds end-to-end                       │
└─────────────────────────────────────────────────────────┘
```

**Evidence Basis**:
- Interview 1 (Military ISR): 45 min integration → target <5 min with validation
- Interview 3 (Emergency Services): 2-3 weeks integration → target <1 hour
- Interview 4 (Field Operations): 30% failure rate → target >99% reliability
- Interview 5 (GIS Specialist): 4-5 hrs/week maintenance → target automated, no maintenance

---

**Document Status**: Ready for PHASE 2 (Requirements Crafting)
**Next Step**: Create journey-data-flow.yaml (structured schema) and journey-operator.feature (Gherkin scenarios)
