@feature_cot_generation
Feature: Generate CoT XML Format for TAK
  As an integration specialist
  I want detections transformed to Cursor on Target (CoT) XML format
  So that output works seamlessly with TAK and ATAK command maps

  Background:
    Given the CoT service is running
    And output format is valid ATAK CoT XML
    And CoT generation latency must be <5ms

  @happy_path @smoke
  Scenario: Convert validated detection to CoT XML
    Given a validated vehicle detection with fields:
      | field                    | value                    |
      | detection_id             | det-12345-abc            |
      | object_class             | vehicle                  |
      | calculated_latitude      | 32.1234                  |
      | calculated_longitude     | -117.5678                |
      | confidence_flag          | GREEN                    |
      | uncertainty_radius_m     | 200                      |
      | ai_confidence            | 0.92                     |
      | camera_id                | cam-001                  |
      | timestamp                | 2026-02-15T14:35:42Z     |
    When CoT generation runs
    Then output is valid CoT XML (TAK-compatible schema)
    And event element has correct attributes:
      | attribute    | value                    |
      | version      | 2.0                      |
      | uid          | Detection.det-12345-abc  |
      | type         | b-m-p-s-u-c              |
    And point element contains coordinates:
      | field        | value                    |
      | lat          | 32.1234                  |
      | lon          | -117.5678                |
      | ce           | 200                      |
    And detail element includes metadata:
      | element      | expected_value           |
      | color value  | -65536                   |
      | remarks text | Vehicle at 92% confidence|
    And TAK Server can parse and display CoT XML

  @happy_path @milestone_1
  Scenario: Handle multiple detection types correctly
    Given detections from three different classes:
      | object_class | cot_type_code         | expected_symbol      |
      | vehicle      | b-m-p-s-u-c           | Blue vehicle marker  |
      | person       | b-m-p-s-p-w-g         | Blue walking person  |
      | aircraft     | b-m-p-a               | Blue air platform    |
    When each detection is transformed to CoT
    Then all three produce valid CoT XML
    And type codes match ATAK hierarchy:
      | class    | type_code       |
      | vehicle  | b-m-p-s-u-c     |
      | person   | b-m-p-s-p-w-g   |
      | aircraft | b-m-p-a         |
    And ATAK client renders each with correct symbology

  @confidence_mapping @critical
  Scenario: Confidence flags map to color codes correctly
    Given detections with different confidence levels:
      | geolocation_confidence | expected_flag | expected_color | expected_hex |
      | 0.85                   | GREEN         | green circle   | -65536       |
      | 0.60                   | YELLOW        | yellow circle  | -256         |
      | 0.35                   | RED           | red circle     | -16711936    |
    When CoT generation maps confidence to colors
    Then GREEN confidence (>0.75) → color value -65536 (red in BGR)
    And YELLOW confidence (0.4-0.75) → color value -256 (green in BGR)
    And RED confidence (<0.4) → color value -16711936 (blue in BGR)
    And TAK operators see correct confidence circles on map

  @accuracy_preservation
  Scenario: Accuracy metadata is preserved as CEP
    Given a detection with photogrammetry uncertainty:
      | field                    | value           |
      | uncertainty_radius_m     | 180             |
      | confidence_flag          | YELLOW          |
      | ai_confidence            | 0.78            |
      | camera_elevation_m       | 500             |
    When CoT generation builds XML
    Then CEP (ce attribute) includes: 180 meters
    And accuracy circle displayed on TAK map
    And color reflects YELLOW confidence
    And remarks include accuracy details: "Accuracy: ±180.0m"
    And all accuracy data survives TAK parsing

  @tak_compatibility @critical
  Scenario: Output is TAK-compatible CoT XML
    Given a validated detection
    When CoT generation produces XML output
    Then CoT structure follows ATAK schema:
      | element          | requirement                    |
      | event            | version 2.0, uid, type, time   |
      | point            | lat, lon, ce (accuracy)        |
      | detail           | link, color, remarks, contact  |
      | link             | uid (camera), type (a-f-G-E-S)|
      | color            | value (hex color code)         |
      | remarks          | human-readable detection info  |
      | contact          | callsign for operator          |
    And CoT can be parsed by standard TAK parsers
    And CoT can be imported to TAK Server
    And CoT displays on ATAK client map

  @audit_trail
  Scenario: CoT generation includes audit metadata
    Given a detection being transformed
    When CoT generation completes
    Then CoT remarks include audit metadata:
      | field                    | example                   |
      | object_class             | Vehicle                   |
      | ai_confidence            | AI Confidence: 92%        |
      | geo_confidence           | Geo Confidence: GREEN     |
      | accuracy                 | Accuracy: ±200.0m         |
    And timestamp shows when detection was created
    And camera source is linked in detail.link
    And metadata enables full detection chain reconstruction

  @multi_source @integration
  Scenario: Multi-source detections map to CoT consistently
    Given a scenario with 3 detections from different sources:
      | #  | source    | object_class | confidence | accuracy | flag   |
      | 1  | uav       | vehicle      | 0.92       | 50m      | GREEN  |
      | 2  | satellite | fire         | 0.78       | 180m     | YELLOW |
      | 3  | camera    | person       | 0.85       | 100m     | GREEN  |
    When all three are transformed to CoT
    Then each produces valid CoT XML with correct type code
    And coordinate systems all use WGS84 (lat/lon)
    And confidence flags all map correctly to colors
    And accuracy (ce) all reflected in CEP circles
    And operator can view all three on TAK map with correct symbology

  @edge_case
  Scenario: Extremely precise coordinates are preserved
    Given a detection with high-precision geolocation:
      | field                    | value           |
      | calculated_latitude      | 32.123456789    |
      | calculated_longitude     | -117.567890123  |
      | uncertainty_radius_m     | 0.5             |
    When CoT generation runs
    Then CoT coordinates preserve precision
    And coordinates are not rounded or truncated
    And CoT output: <point lat="32.123456789" lon="-117.567890123" ce="0.5"/>
    And no floating-point precision loss occurs

  @performance @sla
  Scenario: CoT generation meets latency SLA
    Given a batch of 100 validated detections
    When all are transformed to CoT XML
    Then each generation <5ms
    And average latency <3ms
    And p99 latency <5ms
    And system remains responsive
    And no CoT generations timeout or fail

  @remarks_quality
  Scenario: Remarks field provides complete detection summary
    Given a complex detection with:
      | field                    | value                    |
      | object_class             | vehicle                  |
      | ai_confidence            | 0.92                     |
      | confidence_flag          | GREEN                    |
      | uncertainty_radius_m     | 150                      |
    When CoT is generated
    Then remarks text includes all required fields:
      | field           | example pattern              |
      | class           | "AI Detection: Vehicle"      |
      | ai_confidence   | "AI Confidence: 92%"         |
      | geo_confidence  | "Geo Confidence: GREEN"      |
      | accuracy        | "Accuracy: ±150.0m"          |
    And remarks are human-readable for TAK operators
    And remarks fit within CoT XML text length limits

  @type_code_mapping
  Scenario: Object class to type code mapping is comprehensive
    Given all supported object classes:
      | object_class    | cot_type_code      | description              |
      | vehicle         | b-m-p-s-u-c        | Civilian vehicle         |
      | armed_vehicle   | b-m-p-s-u-c-v-a    | Armed vehicle variant    |
      | person          | b-m-p-s-p-w-g      | Ground walking person    |
      | aircraft        | b-m-p-a            | Air platform             |
      | fire            | b-i-x-f-f          | Fire/building            |
      | unknown         | b-m-p-s-p-loc      | Generic point of interest|
    When each is transformed to CoT
    Then all produce correct type codes
    And ATAK symbology displays correctly for each
    And operators see expected icons and colors

