@phase_04 @security @issue_15
Feature: API Key Management
  As a system administrator
  I want to manage API keys for external integrations
  So that each integration partner has controlled, revocable access to the detection system

  Background:
    Given the detection service is running and healthy
    And the administrator holds a valid management token

  # ---------------------------------------------------------------------------
  # Walking Skeleton: Full key lifecycle from creation to revocation
  # ---------------------------------------------------------------------------

  @walking_skeleton
  Scenario: Administrator creates API key and integration partner uses it successfully
    When administrator generates a new API key for partner "satellite-feed-provider"
    Then a unique API key is returned
    And the key is associated with partner "satellite-feed-provider"
    When partner "satellite-feed-provider" submits a detection using the new key
    Then the detection is accepted and processed
    And audit trail attributes the detection to "satellite-feed-provider"

  # ---------------------------------------------------------------------------
  # Happy Path Scenarios
  # ---------------------------------------------------------------------------

  @happy_path @skip
  Scenario: API key is generated with specific capability permissions
    When administrator creates an API key for "drone-fleet" with access to:
      | capability            |
      | submit detections     |
      | view own detections   |
    Then the key is created with the specified permissions
    And the key identifier and secret are returned
    And the key is active immediately

  @happy_path @skip
  Scenario: API key is rotated without service interruption
    Given partner "camera-network" has an active API key
    When administrator rotates the key for "camera-network"
    Then a new key is generated for "camera-network"
    And the previous key remains valid for a 24-hour grace period
    And both old and new keys work during the grace period
    And after the grace period only the new key works

  @happy_path @skip
  Scenario: Revoked API key is immediately denied
    Given partner "decommissioned-sensor" has an active API key
    When administrator revokes the key for "decommissioned-sensor"
    Then the key status becomes "revoked"
    And subsequent requests using the revoked key are denied
    And the denial reason is "API key has been revoked"
    And audit trail records the revocation event

  @happy_path @skip
  Scenario: Administrator views all active API keys
    Given the following API keys exist:
      | partner               | status  | created          |
      | satellite-feed        | active  | 2026-01-15       |
      | drone-fleet           | active  | 2026-02-01       |
      | decommissioned-sensor | revoked | 2025-11-20       |
    When administrator requests the list of API keys
    Then all three keys are listed with their status
    And active keys show their creation date and last used date
    And revoked keys show the revocation date

  # ---------------------------------------------------------------------------
  # Error Path Scenarios
  # ---------------------------------------------------------------------------

  @error_path @skip
  Scenario: Attempt to use revoked key returns clear rejection
    Given partner "old-integration" had their API key revoked yesterday
    When partner submits a detection using the revoked key
    Then access is denied with reason "API key has been revoked"
    And the response does not reveal why the key was revoked
    And audit trail logs the rejected access attempt

  @error_path @skip
  Scenario: Unknown API key is rejected
    Given a request arrives with API key "nonexistent-key-abc123"
    When the unknown key is used to submit a detection
    Then access is denied with reason "unrecognized API key"
    And no detection data is processed
    And security audit records the unknown key attempt

  @error_path @skip
  Scenario: API key used beyond its permitted scope is rejected
    Given partner "read-only-dashboard" has a key with view-only permissions
    When partner attempts to submit a detection with the view-only key
    Then the request is denied with reason "insufficient permissions"
    And the response indicates which permissions are required
    And audit trail records the scope violation

  @error_path @skip
  Scenario: Duplicate key generation for same partner is prevented
    Given partner "satellite-feed" already has an active API key
    When administrator attempts to generate another key for "satellite-feed"
    Then the system warns that an active key already exists
    And suggests key rotation instead of duplicate creation

  # ---------------------------------------------------------------------------
  # Boundary and Edge Case Scenarios
  # ---------------------------------------------------------------------------

  @boundary @skip
  Scenario: API key with expired grace period stops working
    Given partner "legacy-sensor" had their key rotated 25 hours ago
    And the 24-hour grace period has elapsed
    When partner uses the old key to submit a detection
    Then access is denied with reason "API key expired"
    And only the new rotated key is accepted

  @boundary @skip
  Scenario: High volume of key validations does not degrade performance
    Given 50 different partners each have active API keys
    When all 50 partners submit detections simultaneously
    Then all 50 requests are validated within 200 milliseconds each
    And no key validation failures occur due to load
