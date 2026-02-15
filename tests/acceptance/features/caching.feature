@phase_04 @performance @issue_21
Feature: Response Caching
  As an operations manager
  I want frequently accessed detection data to be served from cache
  So that repeated queries are fast and system load is reduced

  Background:
    Given the detection service is running and healthy
    And caching is configured with:
      | setting             | value        |
      | time to live        | 300 seconds  |
      | maximum entries     | 1000         |
    And the submitting analyst holds a valid access token

  # ---------------------------------------------------------------------------
  # Walking Skeleton: Cache hit delivers faster response
  # ---------------------------------------------------------------------------

  @walking_skeleton
  Scenario: Repeated query for same detection is served from cache
    Given a fire detection was submitted and processed with identifier "det-001"
    When analyst retrieves detection "det-001" for the first time
    Then the detection data is returned from the source system
    And the response time is recorded as the baseline
    When analyst retrieves detection "det-001" again within 5 minutes
    Then the same detection data is returned
    And the response time is measurably faster than the baseline
    And the response indicates it was served from cache

  # ---------------------------------------------------------------------------
  # Happy Path Scenarios
  # ---------------------------------------------------------------------------

  @happy_path @skip
  Scenario: Cache miss retrieves data from source and populates cache
    Given detection "det-new-001" has not been queried before
    When analyst retrieves detection "det-new-001"
    Then the detection is fetched from the database
    And the result is stored in cache for subsequent requests
    And the response does not indicate a cache hit

  @happy_path @skip
  Scenario: Multiple different detections are cached independently
    Given three detections were processed: "det-A", "det-B", "det-C"
    When analyst retrieves each detection twice
    Then the first retrieval of each is a cache miss
    And the second retrieval of each is a cache hit
    And cached data for each detection is independent and correct

  @happy_path @skip
  Scenario: Health check responses are not cached
    When analyst checks system health twice in rapid succession
    Then both health responses reflect live system state
    And health responses are never served from stale cache

  # ---------------------------------------------------------------------------
  # Error Path Scenarios
  # ---------------------------------------------------------------------------

  @error_path @skip
  Scenario: Cache entry expires after time-to-live and data is refreshed
    Given detection "det-ttl-test" was cached 6 minutes ago
    And the cache time-to-live is 5 minutes
    When analyst retrieves detection "det-ttl-test"
    Then the cached entry has expired
    And fresh data is retrieved from the database
    And the cache is repopulated with the current data

  @error_path @skip
  Scenario: Cache returns fresh data after detection is updated
    Given detection "det-updated" is cached with confidence flag "YELLOW"
    When an operator verifies detection "det-updated" and upgrades it to "GREEN"
    Then the cache entry for "det-updated" is invalidated
    When analyst retrieves detection "det-updated"
    Then the response shows confidence flag "GREEN"
    And the stale "YELLOW" value is not returned

  @error_path @skip
  Scenario: Cache failure does not prevent data retrieval
    Given the caching layer is temporarily unavailable
    When analyst retrieves detection "det-fallback"
    Then the detection data is served directly from the database
    And no error is visible to the analyst
    And a warning is logged about cache unavailability

  # ---------------------------------------------------------------------------
  # Invalidation Scenarios
  # ---------------------------------------------------------------------------

  @invalidation @skip
  Scenario: New detection submission invalidates related list caches
    Given the detection list query result is cached
    When analyst submits a new fire detection
    Then the detection list cache is invalidated
    And the next list query returns results including the new detection

  @invalidation @skip
  Scenario: Detection deletion invalidates its cache entry
    Given detection "det-remove" is cached
    When detection "det-remove" is removed from the system
    Then the cache entry for "det-remove" is invalidated
    And subsequent retrieval returns "not found" instead of stale cached data

  @invalidation @skip
  Scenario: Operator verification update invalidates detection cache
    Given detection "det-verify" is cached with status "pending review"
    When operator marks detection "det-verify" as verified
    Then the cache entry is invalidated immediately
    And the next retrieval shows status "verified"

  # ---------------------------------------------------------------------------
  # Boundary and Edge Case Scenarios
  # ---------------------------------------------------------------------------

  @boundary @skip
  Scenario: Cache at maximum capacity evicts oldest entries
    Given the cache contains 1000 entries at maximum capacity
    When a new detection query creates entry 1001
    Then the least recently accessed entry is evicted
    And the new entry is stored successfully
    And cache performance does not degrade at capacity

  @boundary @skip
  Scenario: Concurrent cache reads and writes do not cause corruption
    Given detection "det-concurrent" is in the cache
    When 20 read requests and 5 invalidation events occur simultaneously
    Then all read requests receive either the old or new data consistently
    And no partial or corrupted data is returned
    And no deadlocks or timeouts occur

  @boundary @skip
  Scenario: Cache key collision is prevented across different query types
    Given a detection query and a list query could produce similar cache keys
    When both queries are executed
    Then each query type has its own cache namespace
    And detection detail cache does not interfere with list cache
