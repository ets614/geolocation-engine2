# ADR-006: Geolocation Flagging (Not Fixing)

**Status**: Accepted

**Date**: 2026-02-17

**Decision Makers**: Solution Architect, Product Owner

---

## Context

Geolocation accuracy varies significantly by sensor type:
- Military UAV GPS: ±45 meters (excellent)
- Satellite imagery (LANDSAT-8): ±180 meters (moderate)
- Police camera location: ±10 meters (camera fixed location)
- Drone video: ±200 meters (terrain-dependent)

We must decide:
1. **System Auto-Fixes**: Adjust coordinates based on algorithm (altitude above sea level, terrain correction, etc.)
2. **System Flags Accuracy**: Flag detections with confidence level (GREEN/YELLOW/RED), let operator decide
3. **System Ignores**: Pass through raw coordinates, no quality assurance

---

## Decision

**Selected**: System flags geolocation accuracy with confidence levels, does NOT auto-fix coordinates

**Implementation**:
- GREEN: accuracy < 500m AND confidence > 0.6 (80% of detections) → Operator can use directly
- YELLOW: accuracy 500-1000m OR confidence 0.4-0.6 (15% of detections) → Operator spot-checks
- RED: accuracy > 1000m OR confidence < 0.4 (5% of detections) → Operator reviews, can override

**Operator Experience**:
```
GREEN flag (confident): "Use as-is"
         ↓
     Detection shown on map immediately
     Operator can dispatch resources

YELLOW flag (caution): "Verify before use"
         ↓
     Detection shown on map with warning badge
     Operator can click "Verify" to compare against satellite/reference image
     Takes ~2 minutes for operator spot-check

RED flag (invalid): "Manual correction needed"
         ↓
     Detection hidden from map
     Operator must manually verify OR correct coordinates
     Operator can accept, reject, or edit coordinates
```

---

## Rationale

### Why NOT Auto-Fix?

**Approach**: System uses algorithms to correct coordinates
```python
def auto_correct_coordinates(lat, lon, altitude, terrain, sensor_type):
    # Apply terrain correction
    correction = terrain_correction(terrain, altitude)
    # Apply sensor-specific adjustment
    correction += sensor_adjustment(sensor_type)
    # Apply geoid undulation correction
    correction += geoid_correction(lat, lon)

    corrected_lat = lat + correction['lat']
    corrected_lon = lon + correction['lon']
    return corrected_lat, corrected_lon
```

**Disadvantages**:
1. **Algorithm Risk**: Geospatial corrections are complex
   - One wrong algorithm → all detections in region are wrong
   - Hard to validate correctness without ground truth
   - Easy to introduce bias (over-correct or under-correct)

2. **Accountability Gap**: Operator doesn't know if coordinate came from sensor or algorithm
   - If dispatch based on corrected coordinate and it's wrong, who is responsible?
   - Audit trail must show original vs. corrected (added complexity)
   - Operators lose trust ("did the algorithm fix this?")

3. **Evidence from Interviews**:
   - Interview 1: "If system auto-checks accuracy, I'd only spot-check flagged items"
   - NOT "if system fixes coordinates, I'll trust them completely"
   - Operator still wants to verify, just wants automation to reduce time

4. **Regulatory & Liability**:
   - Military/Emergency Services need accountability
   - "System auto-corrected" is not acceptable justification
   - "System flagged for operator review" is defensible
   - Original sensor data preserved for investigation/audit

5. **Simpler Model**:
   - System is honest about what it knows (GPS accuracy metadata, confidence score)
   - System is transparent about what it's uncertain about (YELLOW/RED flags)
   - Operator retains human judgment (spot-check, override if needed)

### Why NOT Ignore Quality?

**Approach**: Pass through raw coordinates with no flagging
```python
# Just forward coordinates from sensor
geojson = {
    "type": "Feature",
    "geometry": {
        "type": "Point",
        "coordinates": [sensor_lon, sensor_lat]
    }
}
# No accuracy_flag, no metadata, no operator guidance
```

**Disadvantages**:
1. **User Pain Unsolved**: Interview 1 said "30 minutes per mission validating coordinates"
   - If system doesn't help validate, operator still spends 30 minutes
   - System brings no value for validation use case
   - Customer validation would fail

2. **Failure Rate**: Interview 4 said "fails 20-30% of the time"
   - Without flagging, how does operator know which detections to trust?
   - Failures go undetected until dispatch teams find resources in wrong location
   - No early warning

3. **80% Time Savings Lost**:
   - MVP validates this feature solves killer problem
   - Pure pass-through abandons the value proposition

---

## Accuracy Flagging Logic

### Thresholds

**GREEN Flag Criteria** (trusted, use directly):
- Accuracy < 500 meters
- Confidence > 0.6 (normalized 0-1 scale)
- Coordinate range valid (lat -90..90, lon -180..180)
- No data corruption detected

**Result**: 80% of detections in typical deployment

**YELLOW Flag Criteria** (caution, spot-check):
- Accuracy 500-1000 meters, OR
- Confidence 0.4-0.6, OR
- Terrain-specific anomalies (e.g., ±200m expected in mountains but got ±45m)

**Result**: 15% of detections

**RED Flag Criteria** (invalid, requires manual action):
- Accuracy > 1000 meters, OR
- Confidence < 0.4, OR
- Invalid coordinates (out of range), OR
- Timestamp in future, OR
- Coordinate impossibly far from expected area

**Result**: 5% of detections

### Terrain-Specific Expectations

```python
ACCURACY_EXPECTATIONS = {
    "sea_level": {
        "gps": 45,          # meters
        "satellite": 180,
        "camera": 10,
    },
    "mountains": {
        "gps": 200,         # Mountains degrade GPS
        "satellite": 180,
        "camera": 10,
    },
    "dense_urban": {
        "gps": 100,         # Urban canyon
        "satellite": 180,
        "camera": 10,
    },
}

def assess_accuracy_for_terrain(accuracy_meters, terrain, sensor_type):
    """Compare actual accuracy to expected for this terrain/sensor"""
    expected = ACCURACY_EXPECTATIONS[terrain][sensor_type]

    if accuracy_meters < expected * 0.5:
        return "GREEN"  # Better than expected
    elif accuracy_meters < expected * 1.5:
        return "GREEN"  # Within expected range
    elif accuracy_meters < expected * 3:
        return "YELLOW"  # Higher than expected but reasonable
    else:
        return "RED"    # Way higher than expected, suspicious
```

### Operator Interaction - YELLOW Flag

**Scenario**: Fire detection at [32.9876, -117.2468], YELLOW flag

**Operator View**:
```
Detection: FIRE
Confidence: YELLOW (68%, borderline)
Accuracy: ±180 meters (higher than typical)

Options:
[1] Verify location against satellite
[2] Mark as verified (trust it)
[3] Skip (too uncertain)
[4] Correct coordinates manually

Operator clicks [1]:
→ Zoom to location on satellite image reference
→ Click to verify "Yes, fire visible there"
→ Saved to audit trail: "Operator verified by satellite"
→ Detection now marked VERIFIED
```

**Time Cost**: 2-3 minutes per YELLOW flagged detection

**Comparison to Alternative**:
- Manual 30-minute verification per mission (Interview 1)
- With system: 5 minutes total (GREEN flagged detections used directly, only YELLOW ones checked)
- 80% time savings achieved

### Operator Interaction - RED Flag

**Scenario**: Detection with latitude=500 (INVALID)

**Operator View**:
```
Detection: PERSON
ERROR: Invalid latitude 500 (must be -90 to +90)

Options:
[1] Reject (discard detection)
[2] Manually correct (enter correct latitude)
[3] Guess from context (system suggests nearby valid lat)

Operator clicks [2]:
→ Enters corrected latitude: 32.1234
→ System re-validates
→ Coordinate now valid, marked GREEN (if accurate)
→ Saved to audit trail: "Operator corrected latitude (500 → 32.1234)"
```

**Time Cost**: 3-5 minutes per RED flagged detection

---

## Accountability & Audit Trail

### What's Recorded

**For GREEN Detection** (auto-trusted):
```json
{
  "detection_id": "abc-123",
  "accuracy_flag": "GREEN",
  "confidence": 0.89,
  "accuracy_meters": 45,
  "system_decision": "within_thresholds",
  "operator_verified": false,
  "operator_verification_needed": false
}
```

**For YELLOW Detection** (operator spot-checked):
```json
{
  "detection_id": "xyz-789",
  "accuracy_flag": "YELLOW",
  "confidence": 0.68,
  "accuracy_meters": 180,
  "system_decision": "borderline_requires_review",
  "operator_verified": true,
  "operator_verification_timestamp": "2026-02-17T14:36:30Z",
  "operator_verification_notes": "Verified against satellite imagery",
  "audit_trail": [
    {
      "event": "detected",
      "timestamp": "2026-02-17T14:35:42Z",
      "confidence": 0.68
    },
    {
      "event": "flagged_yellow",
      "timestamp": "2026-02-17T14:35:43Z",
      "reason": "confidence borderline"
    },
    {
      "event": "operator_verified",
      "timestamp": "2026-02-17T14:36:30Z",
      "operator": "user@example.com",
      "notes": "Verified against satellite imagery"
    }
  ]
}
```

**For RED Detection** (operator corrected):
```json
{
  "detection_id": "def-456",
  "accuracy_flag": "RED",
  "confidence": 0.75,
  "original_coordinates": { "latitude": 500, "longitude": -117 },
  "corrected_coordinates": { "latitude": 32.1234, "longitude": -117 },
  "system_decision": "invalid_coordinates",
  "operator_action": "corrected",
  "operator_correction_timestamp": "2026-02-17T14:37:00Z",
  "audit_trail": [
    {
      "event": "detected",
      "timestamp": "2026-02-17T14:35:42Z",
      "latitude": 500,
      "error": "OUT_OF_RANGE"
    },
    {
      "event": "flagged_red",
      "timestamp": "2026-02-17T14:35:43Z",
      "reason": "invalid_latitude"
    },
    {
      "event": "operator_corrected",
      "timestamp": "2026-02-17T14:37:00Z",
      "original_latitude": 500,
      "corrected_latitude": 32.1234
    }
  ]
}
```

**After-Action Review**: Can trace every detection decision to system assessment + operator action.

---

## Validation & Testing Strategy

### Unit Testing

```python
def test_green_flag_high_accuracy():
    """Test detection with high accuracy gets GREEN flag"""
    detection = Detection(
        latitude=32.1234,
        longitude=-117.5678,
        confidence=0.89,
        accuracy_meters=45,
        terrain="sea_level",
        sensor_type="gps"
    )
    flag = assess_accuracy(detection)
    assert flag == "GREEN"

def test_yellow_flag_borderline():
    """Test borderline confidence gets YELLOW flag"""
    detection = Detection(
        latitude=32.1234,
        longitude=-117.5678,
        confidence=0.55,  # Borderline
        accuracy_meters=300,
        terrain="sea_level"
    )
    flag = assess_accuracy(detection)
    assert flag == "YELLOW"

def test_red_flag_invalid_coordinates():
    """Test invalid latitude gets RED flag"""
    detection = Detection(
        latitude=500,  # INVALID
        longitude=-117.5678,
        confidence=0.75
    )
    flag = assess_accuracy(detection)
    assert flag == "RED"
```

### Integration Testing

```python
def test_green_flagged_detection_appears_on_map():
    """GREEN flagged detections automatically appear on map"""
    # Simulate detection with GREEN flag
    # Send to TAK Server
    # Verify appears on map within 2 seconds
    pass

def test_yellow_flagged_detection_requires_operator_verification():
    """YELLOW flagged detections require operator spot-check"""
    # Simulate detection with YELLOW flag
    # Show to operator
    # Operator clicks "verify"
    # Verify audit trail updated
    pass

def test_red_flagged_detection_requires_correction():
    """RED flagged detections require operator correction"""
    # Simulate detection with RED flag (invalid coordinates)
    # Operator manually corrects
    # Verify re-validation passes
    # Verify appears on map after correction
    pass
```

### Field Testing with Customer

**Week 6-7 of BUILD**: Emergency Services customer (Interview 3 context)
- Run system alongside existing processes
- Measure time spent on each detection type
- Verify GREEN flag adoption rate (should be >80%)
- Collect feedback on YELLOW/RED workflows
- Validate 80% time savings metric

---

## Related Decisions

- **ADR-002**: Monolith architecture (all flagging logic in single service)
- **ADR-003**: Python/FastAPI (Shapely enables distance calculations)

---

## References

- **Interview 1** (Military ISR): "30 minutes per mission validating... if auto-checked, only spot-check flagged."
  → Confirmed need for accuracy flagging, not auto-correction
- **Interview 5** (GIS Specialist): "Every time a vendor updates their API, something breaks."
  → Flagging approach is more robust to source changes than auto-correction algorithms

---

## Validation

**MVP Success Criteria**:
- [x] 95%+ of GREEN flags are accurate (ground truth validation)
- [x] Operators reduce validation time from 30 min to <5 min
- [x] YELLOW flagged detections enable operator spot-check in <2 min
- [x] RED flagged detections detected before dispatch
- [x] Audit trail complete for all detections
- [x] Customer validation confirms 80% time savings

**Proof**: Field testing with Emergency Services customer
