@phase_04 @security @issue_14
Feature: Authentication and Authorization
  As an operations manager
  I want only authorized personnel to access the detection system
  So that sensitive geolocation data is protected from unauthorized access

  Background:
    Given the detection service is running and healthy
    And the authentication system is configured with a signing key

  # ---------------------------------------------------------------------------
  # Walking Skeleton: Authenticated user submits detection end-to-end
  # ---------------------------------------------------------------------------

  @walking_skeleton
  Scenario: Authorized analyst submits detection and receives confirmation
    Given analyst "sarah.ramirez" has valid credentials
    When analyst requests an access token with client identifier "sarah.ramirez"
    Then analyst receives a signed access token
    And the token type is "Bearer"
    When analyst submits a fire detection using the access token
    Then the detection is accepted and processed
    And the response includes a detection identifier
    And audit trail records the submitting analyst as "sarah.ramirez"

  # ---------------------------------------------------------------------------
  # Happy Path Scenarios
  # ---------------------------------------------------------------------------

  @happy_path @skip
  Scenario: Access token is generated for a registered client
    When client "field-sensor-alpha" requests an access token
    Then the response confirms token creation
    And the token is a properly signed credential
    And the token contains subject "field-sensor-alpha"
    And the token has an expiration time set

  @happy_path @skip
  Scenario: Valid token grants access to submit detections
    Given analyst "maya.patel" holds a valid access token
    When analyst submits a vehicle detection with the token
    Then the detection is accepted with status "created"
    And processing proceeds to geolocation calculation

  @happy_path @skip
  Scenario: Token with custom expiration is honored
    When client "ops-dashboard" requests a token valid for 120 minutes
    Then the token is issued with 120-minute expiration
    And the token remains valid for requests within that window

  # ---------------------------------------------------------------------------
  # Error Path Scenarios (Token Validation Failures)
  # ---------------------------------------------------------------------------

  @error_path @skip
  Scenario: Request without credentials is rejected
    Given no access token is provided
    When a detection submission is attempted without credentials
    Then access is denied with reason "missing credentials"
    And the response indicates authentication is required
    And no detection data is stored
    And audit trail records the unauthorized access attempt

  @error_path @skip
  Scenario: Tampered token is rejected immediately
    Given analyst "james.chen" holds a valid access token
    When the token contents are altered after issuance
    And analyst submits a detection with the tampered token
    Then access is denied with reason "invalid token signature"
    And no detection data is processed
    And security audit logs the tampered token attempt

  @error_path @skip
  Scenario: Expired token is rejected with clear guidance
    Given analyst "sarah.ramirez" holds a token that expired 5 minutes ago
    When analyst submits a detection with the expired token
    Then access is denied with reason "token has expired"
    And the response advises requesting a new token
    And no detection data is stored

  @error_path @skip
  Scenario: Token signed with wrong key is rejected
    Given a token is signed with an unrecognized signing key
    When the forged token is used to submit a detection
    Then access is denied with reason "invalid token"
    And security audit logs the foreign key attempt

  @error_path @skip
  Scenario: Malformed credentials are rejected
    Given credentials are presented in an unrecognized format
    When a detection submission is attempted with the malformed credentials
    Then access is denied with reason "invalid authorization format"
    And the expected credential format is indicated in the response

  @error_path @skip
  Scenario: Token missing subject claim is rejected
    Given a token was issued without a subject identifier
    When the incomplete token is used to submit a detection
    Then access is denied with reason "missing subject"
    And audit trail records the malformed token

  # ---------------------------------------------------------------------------
  # Boundary and Edge Case Scenarios
  # ---------------------------------------------------------------------------

  @boundary @skip
  Scenario: Token at exact expiration boundary is handled gracefully
    Given analyst "maya.patel" holds a token expiring in exactly 1 second
    When analyst submits a detection at the moment of expiration
    Then the system either accepts or rejects consistently
    And no partial processing occurs
    And the outcome is recorded in audit trail

  @boundary @skip
  Scenario: Concurrent requests with same valid token are all accepted
    Given analyst "ops-team" holds a valid access token
    When 10 detection submissions arrive simultaneously using that token
    Then all 10 submissions are authenticated successfully
    And each receives an independent detection identifier
    And no token validation errors occur

  @boundary @skip
  Scenario: Empty credential value is rejected
    Given credentials are presented with an empty token value
    When a detection submission is attempted with the empty token
    Then access is denied with reason "invalid token"
    And the system remains stable for subsequent requests
