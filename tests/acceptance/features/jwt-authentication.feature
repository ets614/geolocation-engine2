Feature: JWT Authentication with Refresh Token Rotation (Phase 04)
  As an API consumer
  I want to authenticate using JWT tokens with refresh capability
  So that I can securely access protected endpoints with automatic token renewal

  Background:
    Given the API service is running
    And the JWT service is configured with RS256 algorithm

  @jwt-auth @phase-04
  Scenario: Client obtains JWT access and refresh tokens
    When I request a token with client_id "test-client-001"
    Then I should receive an HTTP 201 response
    And the response should contain an access_token with 15-minute expiration
    And the response should contain a refresh_token with 7-day expiration
    And the access_token should be signed with RS256 algorithm
    And the refresh_token should be signed with RS256 algorithm

  @jwt-auth @phase-04 @skip
  Scenario: Client uses access token to access protected endpoint
    Given I have a valid access token for client "test-client-002"
    When I call POST /api/v1/detections with the access token
    And the detection payload is valid
    Then I should receive an HTTP 201 response
    And the detection should be processed successfully

  @jwt-auth @phase-04 @skip
  Scenario: Client refreshes expired access token
    Given I have a valid refresh token for client "test-client-003"
    When I call POST /api/v1/auth/refresh with the refresh token
    Then I should receive an HTTP 200 response
    And I should receive a new access_token with 15-minute expiration
    And I should receive a new refresh_token with 7-day expiration
    And the old refresh_token should be invalidated

  @jwt-auth @phase-04 @skip
  Scenario: Client verifies token validity
    Given I have a valid access token for client "test-client-004"
    When I call POST /api/v1/auth/verify with the access token
    Then I should receive an HTTP 200 response
    And the response should confirm the token is valid
    And the response should include the client_id claim

  @jwt-auth @phase-04 @skip
  Scenario: System rejects expired access token
    Given I have an expired access token for client "test-client-005"
    When I call POST /api/v1/detections with the expired token
    Then I should receive an HTTP 401 response
    And the error message should indicate "Token has expired"

  @jwt-auth @phase-04 @skip
  Scenario: System rejects invalid token signature
    Given I have a token signed with wrong private key
    When I call POST /api/v1/detections with the invalid token
    Then I should receive an HTTP 401 response
    And the error message should indicate "Invalid token signature"

  @jwt-auth @phase-04 @skip
  Scenario: System rejects reused refresh token
    Given I have a refresh token that was already used once
    When I call POST /api/v1/auth/refresh with the used token
    Then I should receive an HTTP 401 response
    And the error message should indicate "Refresh token already used"

  @jwt-auth @phase-04 @skip
  Scenario: System rejects missing Authorization header
    When I call POST /api/v1/detections without Authorization header
    Then I should receive an HTTP 401 response
    And the error message should indicate "Missing authorization header"
