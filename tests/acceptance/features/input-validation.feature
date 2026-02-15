@phase_04 @security @issue_18
Feature: Input Validation and Sanitization
  As a security officer
  I want all incoming detection data to be validated and sanitized
  So that the system is protected from malicious or malformed input

  Background:
    Given the detection service is running and healthy
    And the submitting analyst holds a valid access token

  # ---------------------------------------------------------------------------
  # Walking Skeleton: Valid detection passes all validation checks
  # ---------------------------------------------------------------------------

  @walking_skeleton
  Scenario: Well-formed detection with valid data passes all checks
    Given a fire detection with all required fields:
      | field            | value                              |
      | image data       | valid base64-encoded image         |
      | pixel x          | 960                                |
      | pixel y          | 720                                |
      | object class     | fire                               |
      | confidence       | 0.92                               |
      | source           | satellite-thermal-scanner          |
      | camera           | cam-001                            |
      | capture time     | 2026-02-15T14:35:42Z               |
    And camera metadata with valid coordinates and orientation
    When the detection is submitted for processing
    Then all validation checks pass
    And the detection is accepted for geolocation calculation
    And no sanitization warnings are raised

  # ---------------------------------------------------------------------------
  # Happy Path Scenarios
  # ---------------------------------------------------------------------------

  @happy_path @skip
  Scenario: Coordinates at valid extremes are accepted
    Given a detection with coordinates at valid boundaries:
      | field             | value     |
      | camera latitude   | 89.9999   |
      | camera longitude  | 179.9999  |
    When the detection is submitted for processing
    Then the coordinates are accepted as valid
    And geolocation calculation proceeds normally

  @happy_path @skip
  Scenario: Confidence value at boundary limits is accepted
    Given a detection with confidence exactly 0.0
    When the detection is submitted for processing
    Then the confidence value is accepted
    Given another detection with confidence exactly 1.0
    When the detection is submitted for processing
    Then the confidence value is accepted

  # ---------------------------------------------------------------------------
  # Error Path: Missing and Malformed Fields
  # ---------------------------------------------------------------------------

  @error_path @skip
  Scenario: Missing required image data is rejected with clear message
    Given a detection without image data
    When the incomplete detection is submitted
    Then the submission is rejected with reason "image data is required"
    And the response identifies the missing field
    And no partial detection is stored

  @error_path @skip
  Scenario: Invalid base64 image data is rejected
    Given a detection with corrupted image data "not-valid-base64!!!"
    When the detection is submitted for processing
    Then the submission is rejected with reason "image data must be valid base64"
    And processing does not attempt geolocation on invalid data

  @error_path @skip
  Scenario: Pixel coordinates outside image bounds are rejected
    Given image dimensions are 1920 by 1440 pixels
    And pixel coordinates are set to x=2000, y=720
    When the detection is submitted for processing
    Then the submission is rejected with reason "pixel x exceeds image width"
    And the valid range is indicated in the error details

  @error_path @skip
  Scenario: Negative pixel coordinates are rejected
    Given pixel coordinates are set to x=-50, y=720
    When the detection is submitted for processing
    Then the submission is rejected with reason "pixel coordinates must be non-negative"

  @error_path @skip
  Scenario: Confidence outside valid range is rejected
    Given a detection with confidence value 1.5
    When the detection is submitted for processing
    Then the submission is rejected with reason "confidence must be between 0.0 and 1.0"

  @error_path @skip
  Scenario: Camera latitude out of range is rejected
    Given camera metadata with latitude 95.0
    When the detection is submitted for processing
    Then the submission is rejected with reason "camera latitude must be between -90 and 90"

  @error_path @skip
  Scenario: Future timestamp is rejected
    Given a detection with capture time set to tomorrow
    When the detection is submitted for processing
    Then the submission is rejected with reason "capture time cannot be in the future"

  @error_path @skip
  Scenario: Empty object class is rejected
    Given a detection with empty object class ""
    When the detection is submitted for processing
    Then the submission is rejected with reason "object class is required"

  # ---------------------------------------------------------------------------
  # Security: Injection Prevention
  # ---------------------------------------------------------------------------

  @security @injection @skip
  Scenario: Database injection attempt in source field is neutralized
    Given a detection with source field containing "'; DROP TABLE detections; --"
    When the detection is submitted for processing
    Then the malicious content is sanitized
    And the detection is either rejected or stored safely
    And all stored data remains intact
    And security audit records the injection attempt

  @security @injection @skip
  Scenario: Database injection in object class field is neutralized
    Given a detection with object class "vehicle' OR '1'='1"
    When the detection is submitted for processing
    Then the input is sanitized before storage
    And no unintended data is returned or modified
    And data queries execute safely with parameterized values

  @security @xss @skip
  Scenario: Script injection in camera identifier is neutralized
    Given a detection with camera identifier "<script>alert('xss')</script>"
    When the detection is submitted for processing
    Then markup tags are stripped or escaped in the stored value
    And the detection response does not contain executable markup
    And any downstream display renders the value safely

  @security @xss @skip
  Scenario: Markup injection in source metadata is neutralized
    Given a detection with source containing "<img src=x onerror=alert(1)>"
    When the detection is submitted for processing
    Then the markup content is escaped before storage
    And responses return the escaped version
    And audit trail shows the original input was sanitized

  @security @injection @skip
  Scenario: Oversized submission is rejected before processing
    Given a detection submission exceeding 10 megabytes in size
    When the oversized submission is sent
    Then the submission is rejected with reason "submission exceeds maximum allowed size"
    And the system does not attempt to process the oversized content
    And memory usage remains stable

  @security @injection @skip
  Scenario: Deeply nested data structure is rejected
    Given a detection with 100 levels of nested data
    When the deeply nested submission is sent
    Then the submission is rejected with reason "data structure exceeds complexity limit"
    And no resource exhaustion occurs

  # ---------------------------------------------------------------------------
  # Boundary and Edge Case Scenarios
  # ---------------------------------------------------------------------------

  @boundary @skip
  Scenario: Unicode characters in text fields are handled correctly
    Given a detection with source field containing unicode "sensor-alpha"
    And object class contains "vehiculo" with accented characters
    When the detection is submitted for processing
    Then unicode characters are preserved correctly
    And the detection is stored with original character encoding
    And search by these fields returns accurate results

  @boundary @skip
  Scenario: Maximum length field values are accepted
    Given a detection with source field at the maximum allowed 255 characters
    When the detection is submitted for processing
    Then the field value is accepted at maximum length
    And no truncation occurs during storage

  @boundary @skip
  Scenario: Concurrent malicious and legitimate requests are isolated
    Given 5 legitimate detection submissions
    And 5 submissions containing injection attempts
    When all 10 are submitted simultaneously
    Then the 5 legitimate detections are accepted
    And the 5 malicious submissions are rejected
    And no cross-contamination occurs between requests
