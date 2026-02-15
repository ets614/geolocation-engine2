@rate_limiting
Feature: Rate limiting and quota enforcement
  As a service operator
  I want to enforce per-user and per-endpoint rate limits
  So that I can protect the API from excessive requests and abuse

  Background:
    Given the detection ingestion service is running on port 8000
    And the rate limiting service is initialized
    And the Redis cache is available (or in-memory fallback is active)
    And the default per-user quota is set to 100 requests per minute
    And the default per-endpoint limit is set to 1000 requests per minute

  @milestone_1 @slow
  Scenario: Accept requests within quota
    Given a valid JWT token with client_id "test-client"
    And the client is within the 100 req/min quota
    When I POST to /api/v1/detections with valid detection data 5 times
    Then all 5 requests return HTTP status 201 Created
    And the response includes RateLimit-Limit header
    And the response includes RateLimit-Remaining header
    And RateLimit-Remaining decreases from 95 to 90

  @milestone_1 @skip
  Scenario: Reject requests exceeding per-user quota
    Given a valid JWT token with client_id "spammy-client"
    And the client has already used 100 requests this minute
    When I POST to /api/v1/detections with valid detection data
    Then the response status is 429 Too Many Requests
    And the response includes RateLimit-Limit header (100)
    And the response includes RateLimit-Remaining header (0)
    And the response includes RateLimit-Reset header with Unix timestamp
    And the response body contains error code "RATE_LIMIT_EXCEEDED"

  @milestone_1 @skip
  Scenario: Support token bucket burst handling
    Given a valid JWT token with client_id "burst-client"
    And the token bucket is initialized with 100 tokens and 10 token/sec refill rate
    And the client is at quota with 0 tokens remaining
    When I wait 5 seconds for tokens to accumulate
    And the bucket now has 50 tokens available
    And I POST to /api/v1/detections 30 times rapidly
    Then the first 50 requests succeed (201 Created)
    And requests 51-80 are rejected (429 Too Many Requests)
    And RateLimit-Remaining shows 0 for all rejected requests

  @milestone_1 @skip
  Scenario: Whitelist bypass for trusted clients
    Given the rate limit whitelist includes client_id "trusted-partner"
    And a valid JWT token with client_id "trusted-partner"
    When I POST to /api/v1/detections 500 times (exceeding normal quota)
    Then all 500 requests succeed (201 Created)
    And no RateLimit-* headers are included in responses
    And the request counter does not increment for this client

  @milestone_1 @skip
  Scenario: Per-endpoint rate limits
    Given default per-endpoint limit is 1000 requests per minute
    And multiple clients with separate quotas
    When client-1 sends 600 requests to /api/v1/detections
    And client-2 sends 600 requests to /api/v1/detections (different client)
    Then all requests from client-1 succeed (within user quota)
    And all requests from client-2 succeed (within user quota)
    And the endpoint has received 1200 total requests
    And only the last 200 requests are rejected (endpoint limit exceeded)
    And both clients see 429 status on their last 100+ requests

  @milestone_1 @skip
  Scenario: In-memory fallback when Redis unavailable
    Given the rate limiting service is configured with Redis fallback
    And Redis is temporarily unavailable
    And the in-memory fallback bucket is active
    When I POST to /api/v1/detections with valid detection data 5 times
    Then all 5 requests succeed (201 Created)
    And the RateLimit-* headers are included (from in-memory bucket)
    And requests are tracked in memory with 100 req/min limit

  @milestone_1 @skip
  Scenario: Monitor quota usage metrics
    Given a valid JWT token with client_id "metrics-client"
    And the metrics endpoint is available at /api/v1/metrics/rate-limit
    When I POST 25 requests to /api/v1/detections
    And I call GET /api/v1/metrics/rate-limit?client_id=metrics-client
    Then the response includes:
      | metric                    | value |
      | quota_limit               | 100   |
      | quota_used                | 25    |
      | quota_remaining           | 75    |
      | quota_reset_time_seconds  | ~55   |
    And the metric shows current client window (1-minute window)

  @milestone_1 @skip
  Scenario: Reset quota on configured time window
    Given a valid JWT token with client_id "window-client"
    And the client has used 100 requests (at quota)
    And 60 seconds have elapsed (window expired)
    When I POST to /api/v1/detections with valid detection data
    Then the request succeeds (201 Created)
    And RateLimit-Remaining shows 99 (quota reset)
    And the client's window is now within the latest minute
