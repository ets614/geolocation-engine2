@phase_04 @security @issue_16
Feature: Rate Limiting
  As an operations manager
  I want detection submission rates to be controlled per client
  So that no single integration overwhelms the system and all partners get fair access

  Background:
    Given the detection service is running and healthy
    And rate limiting is configured with:
      | setting                | value              |
      | requests per minute    | 100                |
      | burst allowance        | 10                 |
      | time window            | 60 seconds         |

  # ---------------------------------------------------------------------------
  # Walking Skeleton: Rate limit enforced and resets after time window
  # ---------------------------------------------------------------------------

  @walking_skeleton
  Scenario: Client submits detections within rate limit and all are accepted
    Given analyst "field-ops" has a valid access token
    When analyst submits 50 detections within 60 seconds
    Then all 50 detections are accepted and processed
    And no rate limiting is applied
    And each detection receives a unique identifier

  # ---------------------------------------------------------------------------
  # Happy Path Scenarios
  # ---------------------------------------------------------------------------

  @happy_path @skip
  Scenario: Rate limit quota resets after time window expires
    Given analyst "sensor-hub" has used 95 of 100 allowed requests this minute
    When the 60-second time window expires
    And analyst submits 10 more detections in the new window
    Then all 10 detections are accepted
    And the quota counter shows 10 of 100 used

  @happy_path @skip
  Scenario: Rate limit status informs client of remaining quota
    Given analyst "field-ops" has a valid access token
    When analyst submits a single detection
    Then the response includes rate limit information:
      | indicator           | meaning                    |
      | quota limit         | 100 requests per window    |
      | quota remaining     | 99 requests left           |
      | quota reset time    | seconds until window resets|

  # ---------------------------------------------------------------------------
  # Error Path Scenarios
  # ---------------------------------------------------------------------------

  @error_path @skip
  Scenario: Client exceeding rate limit receives throttle response
    Given analyst "overactive-sensor" has used all 100 allowed requests this minute
    When analyst submits one more detection
    Then the request is throttled with "too many requests" response
    And the response includes a retry-after duration in seconds
    And the throttled request does not consume system resources
    And audit trail records the rate limit breach

  @error_path @skip
  Scenario: Burst of requests beyond limit is rejected gracefully
    Given analyst "burst-sensor" has a valid access token
    When analyst submits 150 detections in rapid succession within 60 seconds
    Then the first 100 detections are accepted
    And detections 101 through 150 are throttled
    And each throttled response includes retry guidance
    And no accepted detections are lost or corrupted
    And the system remains responsive to other clients

  @error_path @skip
  Scenario: Throttled client retries after wait period and succeeds
    Given analyst "impatient-sensor" was throttled 60 seconds ago
    When analyst waits for the retry-after duration to pass
    And analyst submits a new detection
    Then the detection is accepted and processed normally
    And the quota counter reflects the new time window

  # ---------------------------------------------------------------------------
  # Multi-User Isolation Scenarios
  # ---------------------------------------------------------------------------

  @isolation @skip
  Scenario: Rate limits are tracked independently per client
    Given two analysts are active:
      | analyst        | requests sent | quota limit |
      | sensor-alpha   | 98            | 100         |
      | sensor-beta    | 5             | 100         |
    When sensor-alpha submits 5 more detections
    And sensor-beta submits 50 more detections
    Then sensor-alpha has 2 accepted and 3 throttled
    And sensor-beta has all 50 accepted
    And sensor-beta is unaffected by sensor-alpha reaching the limit

  @isolation @skip
  Scenario: One client hitting rate limit does not block other clients
    Given analyst "noisy-sensor" has exhausted their 100-request quota
    And analyst "quiet-sensor" has only used 10 requests
    When both attempt to submit detections simultaneously
    Then noisy-sensor is throttled
    And quiet-sensor submission is accepted immediately
    And quiet-sensor response time is not degraded

  # ---------------------------------------------------------------------------
  # Boundary and Edge Case Scenarios
  # ---------------------------------------------------------------------------

  @boundary @skip
  Scenario: Request arriving at exact quota boundary is handled deterministically
    Given analyst "edge-sensor" has submitted exactly 99 detections this minute
    When analyst submits detection number 100
    Then detection 100 is accepted (quota allows exactly 100)
    When analyst immediately submits detection number 101
    Then detection 101 is throttled

  @boundary @skip
  Scenario: Rate limit counter survives service restart
    Given analyst "persistent-sensor" has used 80 of 100 requests
    When the detection service restarts
    And analyst submits 25 more detections
    Then the rate limit state is either preserved or safely reset
    And no more than 100 requests are processed in any 60-second window

  @boundary @skip
  Scenario: Multiple rapid requests at window boundary are counted correctly
    Given the rate limit window is about to expire in 1 second
    And analyst "timing-sensor" has used 95 of 100 requests
    When analyst submits 10 requests spanning the window boundary
    Then requests before the boundary use the old window quota
    And requests after the boundary use the new window quota
    And no requests are incorrectly throttled or incorrectly allowed
