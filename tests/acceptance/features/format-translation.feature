@feature_us003
Feature: Translate to GeoJSON Format
  As an integration specialist
  I want detections transformed to standardized GeoJSON format
  So that output works with TAK, ArcGIS, and standard COP systems

  Background:
    Given the format translation service is running
    And output format is RFC 7946 compliant GeoJSON
    And transformation latency must be <100ms

  @happy_path @smoke
  Scenario: Convert validated detection to GeoJSON Feature
    Given a validated fire detection with fields:
      | field                | value                    |
      | detection_id         | det-12345-abc            |
      | source               | satellite_fire_api       |
      | latitude             | 32.1234                  |
      | longitude            | -117.5678                |
      | confidence           | 0.85                     |
      | confidence_original  | {value: 85, scale: 0-100}|
      | accuracy_meters      | 200                      |
      | accuracy_flag        | GREEN                    |
      | type                 | fire                     |
      | timestamp            | 2026-02-17T14:35:42Z     |
      | received_at          | 2026-02-17T14:35:43Z     |
    When format translation to GeoJSON runs
    Then output is valid GeoJSON Feature (RFC 7946 compliant)
    And geometry is structured correctly:
      | field          | value                    |
      | type           | Point                    |
      | coordinates    | [-117.5678, 32.1234]     |
    And properties include all required fields:
      | property              | value                    |
      | source                | satellite_fire_api       |
      | confidence            | 0.85                     |
      | accuracy_m            | 200                      |
      | accuracy_flag         | GREEN                    |
      | type                  | fire                     |
      | timestamp             | 2026-02-17T14:35:42Z     |
    And output is parseable by standard GeoJSON parsers
    And transformation latency is <100ms

  @happy_path @milestone_1
  Scenario: Handle multiple source formats consistently
    Given detections from three different source formats:
      | source    | input_format | detection_data           |
      | uav_1     | {lat, lon, conf, ts} | UAV ground control output |
      | satellite | {latitude, longitude, confidence_0_100, timestamp} | Satellite API response |
      | camera_47 | camera_id registry | CCTV detection + location lookup |
    When each detection is transformed to GeoJSON
    Then all three produce valid GeoJSON Features
    And all use same coordinate system: WGS84 [longitude, latitude]
    And all use same confidence scale: 0-1 normalized
    And geometry structure is identical across all sources
    And properties structure is consistent across all sources
    And operator sees uniform data regardless of source

  @normalization @critical
  Scenario: Confidence scales are normalized correctly
    Given detections with confidence in different scales:
      | source   | input_value | input_scale | expected_output |
      | uav      | 0.89        | 0-1 scale   | 0.89            |
      | satellite| 92          | 0-100 scale | 0.92            |
      | camera   | 78          | 0-100 scale | 0.78            |
      | radar    | 85%         | percentage  | 0.85            |
    When format translation normalizes confidence
    Then UAV confidence 0.89 → normalized 0.89 (unchanged)
    And satellite confidence 92 → normalized 0.92 (divide by 100)
    And camera confidence 78 → normalized 0.78 (divide by 100)
    And radar confidence 85% → normalized 0.85 (divide by 100)
    And all are output in 0-1 scale (standard)
    And original values preserved in confidence_original field:
      | detection | confidence_original       |
      | uav       | {value: 0.89, scale: "0-1"} |
      | satellite | {value: 92, scale: "0-100"} |
      | camera    | {value: 78, scale: "0-100"} |
      | radar     | {value: 85%, scale: "percent"} |

  @accuracy_preservation
  Scenario: Accuracy metadata is preserved and validated
    Given a detection with accuracy metadata:
      | field              | value           |
      | accuracy_meters    | 180             |
      | accuracy_flag      | YELLOW          |
      | gps_pdop           | 4.5             |
      | satellite_count    | 8               |
    When format translation builds GeoJSON
    Then accuracy_m field includes: 180
    And accuracy_flag included in properties
    And additional metadata preserved in properties:
      | property           | value           |
      | gps_pdop           | 4.5             |
      | satellite_count    | 8               |
    And all accuracy data survives round-trip validation

  @rfc7946_compliance @critical
  Scenario: Output is RFC 7946 compliant GeoJSON
    Given a validated fire detection
    When format translation produces GeoJSON output
    Then GeoJSON structure matches RFC 7946 specification:
      | element          | requirement                    |
      | type             | "Feature"                      |
      | geometry         | Point geometry present         |
      | geometry.type    | "Point"                        |
      | geometry.coordinates | [lon, lat] format          |
      | properties       | Object with detection data     |
      | crs              | Not included (WGS84 default)   |
    And GeoJSON can be validated by standard RFC 7946 validators
    And GeoJSON can be parsed by GeoJSON.io and QGIS
    And GeoJSON can be imported to TAK Server
    And GeoJSON can be imported to ArcGIS

  @audit_trail
  Scenario: Transformation includes audit metadata
    Given a detection being transformed
    When format translation completes
    Then GeoJSON includes audit metadata:
      | field                 | example                   |
      | received_timestamp    | 2026-02-17T14:35:43Z      |
      | processed_at          | 2026-02-17T14:35:44Z      |
      | sync_status           | SYNCED                    |
      | operator_verified     | false / true (if manual)  |
      | operator_notes        | null / "operator input"   |
    And metadata enables full audit trail reconstruction

  @multi_source @integration
  Scenario: Multi-source detections maintain consistency
    Given a scenario with 3 detections from different sources:
      | #  | source    | confidence | accuracy | flag   |
      | 1  | uav       | 0.92       | 50m      | GREEN  |
      | 2  | satellite | 0.78       | 180m     | YELLOW |
      | 3  | camera    | 0.85       | 100m     | GREEN  |
    When all three are transformed to GeoJSON
    Then GeoJSON array is produced with 3 Feature objects
    And each Feature has identical structure
    And coordinate systems are all WGS84
    And confidence scales all 0-1
    And accuracy flags displayed consistently
    And operator can view all three on same map without confusion

  @edge_case
  Scenario: Extremely precise coordinates are preserved
    Given a detection with high-precision coordinates:
      | field              | value           |
      | latitude           | 32.123456789    |
      | longitude          | -117.567890123  |
      | accuracy_meters    | 0.5             |
    When format translation runs
    Then GeoJSON coordinates preserve precision
    And coordinates are not rounded or truncated
    And GeoJSON output: [-117.567890123, 32.123456789]
    And no floating-point precision loss occurs

  @performance @sla
  Scenario: Transformation meets latency SLA
    Given a batch of 100 validated detections
    When all are transformed to GeoJSON
    Then each transformation <100ms
    And average latency <50ms
    And p99 latency <100ms
    And system remains responsive
    And no transformations timeout or fail

  @compatibility
  Scenario: Output is compatible with TAK Server
    Given a GeoJSON Feature from our system
    When sent to TAK Server subscription endpoint
    Then TAK Server accepts the GeoJSON
    And detection appears on TAK map
    And properties are displayed in TAK UI
    And accuracy flag is visible to operators
    And confidence is displayed
    And timestamp is displayed correctly

  @compatibility
  Scenario: Output is compatible with ArcGIS
    Given a GeoJSON Feature from our system
    When imported to ArcGIS as feature service input
    Then ArcGIS accepts the GeoJSON without errors
    And feature appears on map at correct coordinates
    And properties are available in feature attributes
    And symbology can be based on accuracy_flag
    And popup displays all metadata

  @compliance
  Scenario: Transformation audit trail is complete
    Given a detection undergoing transformation
    When format translation completes
    Then audit trail records:
      | event                  | details                   |
      | transform_started      | timestamp, detection_id   |
      | confidence_normalized  | original scale, method    |
      | geojson_built          | geometry, properties      |
      | transform_completed    | timestamp, latency_ms     |
    And all transformation logic is logged
    And normalization methods are documented
    And failures are captured with error details
