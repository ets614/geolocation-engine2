@feature_us002
Feature: Validate and Normalize Geolocation (Killer Feature)
  As an operations manager
  I want automatic geolocation validation with confidence flagging
  So that I can reduce manual coordinate verification from 30 minutes to 5 minutes (80% savings)

  Background:
    Given geolocation validator is configured with thresholds:
      | accuracy_threshold_m | 500   |
      | confidence_minimum   | 0.6   |
      | max_accuracy_yellow  | 1000  |
      | terrain_type         | mixed |
    And geolocation validation service is running
    And validation response time must be <100ms

  @happy_path @smoke
  Scenario: Accurate location is automatically flagged GREEN
    Given a fire detection with high-accuracy GPS metadata:
      | field             | value                |
      | latitude          | 32.1234              |
      | longitude         | -117.5678            |
      | confidence        | 0.85                 |
      | accuracy_meters   | 45                   |
      | sensor_type       | GPS/IMU              |
      | terrain           | sea_level            |
      | timestamp         | 2026-02-17T14:35:42Z |
    When geolocation validation runs
    Then accuracy_flag is set to GREEN
    And validation checks pass:
      | check                  | result |
      | latitude in [-90, 90]  | ✓      |
      | longitude in [-180,180]| ✓      |
      | accuracy < 500m        | ✓      |
      | confidence > 0.6       | ✓      |
      | terrain match          | ✓      |
    And detection is output to COP without operator verification needed
    And validation latency is less than 100ms
    And audit trail records: "GREEN flag - HIGH confidence location"

  @happy_path @milestone_1
  Scenario: Borderline confidence triggers YELLOW flag for operator review
    Given a fire detection with moderate accuracy:
      | field             | value                |
      | latitude          | 32.9876              |
      | longitude         | -117.2468            |
      | confidence        | 0.68                 |
      | accuracy_meters   | 180                  |
      | sensor_type       | LANDSAT-8            |
      | terrain           | mountains            |
      | timestamp         | 2026-02-17T14:36:15Z |
    When geolocation validation runs
    Then accuracy_flag is set to YELLOW
    And validation details include:
      | field         | value        |
      | confidence    | 0.68 (>0.6 but borderline) |
      | accuracy      | ±180m (acceptable for mountains) |
      | recommendation| Spot-check against satellite imagery |
    And detection is output to COP WITH yellow warning badge
    And operator sees: "Verify location - moderate confidence"
    And operator can click to spot-check location details
    And operator can click "Verify and confirm" to mark GREEN
    And manual verification is recorded in audit trail
    And verification time is logged (~2 minutes)

  @error_handling @boundary
  Scenario: Out-of-range coordinates are flagged RED and blocked from output
    Given a detection with invalid latitude:
      | field             | value                |
      | latitude          | 500                  |
      | longitude         | -117.5678            |
      | confidence        | 0.75                 |
      | accuracy_meters   | 50                   |
      | timestamp         | 2026-02-17T14:37:00Z |
    When geolocation validation runs
    Then accuracy_flag is set to RED
    And validation fails with error: "Invalid latitude: 500 (must be -90 to 90)"
    And detection is NOT output to COP (blocked)
    And detection is queued for manual review
    And operator sees detection in "Manual Review Queue"
    And operator options are:
      | option                    | action                           |
      | Reject detection          | Mark invalid, discard            |
      | Manually correct latitude | Enter corrected value            |
      | Override and trust-as-is  | Not recommended, requires approval|
    When operator enters corrected latitude: 32.1234
    Then system re-validates corrected coordinates
    And corrected coordinates are now within range
    And detection is re-flagged (GREEN or YELLOW)
    And detection now appears on COP
    And audit trail records: "Operator corrected latitude (500 → 32.1234)"

  @error_handling @boundary
  Scenario: Low confidence score triggers validation for review
    Given a camera detection with low confidence:
      | field             | value                |
      | latitude          | 40.7128              |
      | longitude         | -74.0060             |
      | confidence        | 0.52                 |
      | accuracy_meters   | 150                  |
      | sensor_type       | CCTV AI detector     |
      | timestamp         | 2026-02-17T14:38:00Z |
    When geolocation validation runs
    Then accuracy_flag is set to YELLOW (confidence below recommended 0.6, but above 0.4 minimum)
    And validation detail shows: "Confidence 0.52 is below recommended 0.6"
    And operator spot-check is recommended
    And confidence_score is highlighted in UI for review

  @performance @sla
  Scenario: Validation meets <100ms latency SLA
    Given a batch of 100 fire detections ready for validation
    When all 100 are validated sequentially
    Then each validation completes in <100ms
    And average validation latency is <50ms
    And p99 latency is <100ms
    And no validations timeout or fail

  @accuracy
  Scenario: GREEN flag accuracy is validated >95%
    Given historical ground truth data for 100 past detections
    And each has recorded accuracy_flag (GREEN/YELLOW/RED)
    When accuracy is measured against ground truth
    Then GREEN flagged detections have:
      | metric                | target |
      | Actual accuracy <500m | >95%   |
      | False positives       | <5%    |
      | Confidence match      | >90%   |
    And YELLOW flagged detections:
      | metric                | target |
      | Accuracy 500-1000m    | >80%   |
      | False positives       | <20%   |
    And RED flagged detections:
      | metric              | target |
      | Invalid coordinates | 100%   |
      | Low confidence      | >95%   |

  @normalization @edge_case
  Scenario: Coordinate systems are normalized to WGS84
    Given detections in multiple coordinate systems:
      | detection | format | coordinates                      |
      | det1      | WGS84  | (32.1234, -117.5678)             |
      | det2      | UTM    | (11S 498789 3563214)             |
      | det3      | MGRS   | | 11SPE9878963214              |
      | det4      | State Plane | (2244850.5, 389200.3)      |
    When geolocation validation normalizes coordinates
    Then all output uses WGS84 decimal degrees
    And normalization preserves accuracy (±50m or better)
    And original coordinate system preserved in metadata
    And all conversions verified against reference data

  @terrain_specific
  Scenario: Terrain-specific accuracy expectations are applied
    Given detections from different terrain types:
      | detection | terrain       | expected_accuracy | actual_accuracy |
      | det1      | sea_level     | ±45m              | ±40m            |
      | det2      | mountains     | ±200m             | ±180m           |
      | det3      | dense_urban   | ±100m             | ±90m            |
      | det4      | satellite     | ±180m (LANDSAT-8) | ±175m           |
    When geolocation validation applies terrain-specific thresholds
    Then accuracy flags reflect terrain expectations:
      | detection | flag  | reason                      |
      | det1      | GREEN | ±40m < ±45m expected        |
      | det2      | GREEN | ±180m < ±200m expected      |
      | det3      | GREEN | ±90m < ±100m expected       |
      | det4      | YELLOW| ±175m near threshold, check |

  @operator_override
  Scenario: Operator manual verification overrides YELLOW flag to GREEN
    Given a YELLOW-flagged detection (confidence 0.68)
    And operator has viewed satellite imagery at detection location
    When operator clicks "Verify and confirm"
    Then system prompts for optional notes
    And operator enters: "Location verified against satellite imagery"
    And system records manual verification:
      | field              | value                               |
      | operator_verified  | true                                |
      | verified_at        | 2026-02-17T14:40:30Z               |
      | verifier_id        | operator_sarah_ramirez              |
      | verification_notes | "Location verified..."              |
    And accuracy_flag is upgraded to GREEN (operator confidence)
    And audit trail shows operator action
    And verification time is recorded

  @compliance
  Scenario: Audit trail captures all validation decisions
    Given a detection undergoes validation and flagging
    When the validation process completes
    Then audit trail includes:
      | event                    | details                              |
      | validation_started       | timestamp, detection_id              |
      | accuracy_check           | latitude, longitude, ranges verified |
      | confidence_check         | confidence score, threshold applied  |
      | terrain_check            | terrain type, expected accuracy      |
      | flag_assigned            | accuracy_flag (GREEN/YELLOW/RED)     |
      | validation_completed     | timestamp, latency_ms               |
    And all events are immutable (read-only after creation)
    And audit trail searchable by detection_id
    And events retained for 90 days minimum
