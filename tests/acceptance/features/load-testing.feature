@phase_04 @performance @issue_17
Feature: Load Testing and Performance Acceptance Criteria
  As an operations manager
  I want the detection system to handle high traffic volumes
  So that real-world operational loads do not degrade service quality

  Background:
    Given the detection service is deployed in production-like configuration
    And the database is seeded with 10000 existing detections
    And all authenticated clients have valid access tokens

  # ---------------------------------------------------------------------------
  # Walking Skeleton: System handles baseline operational load
  # ---------------------------------------------------------------------------

  @walking_skeleton @slow
  Scenario: System processes 100 concurrent detection submissions
    Given 100 authenticated clients are ready to submit detections
    When all 100 clients submit a detection simultaneously
    Then at least 95 of 100 submissions are accepted within 2 seconds
    And all 100 submissions complete within 5 seconds
    And no submissions are lost or produce errors
    And each submission receives a unique detection identifier
    And system health check remains healthy after the burst

  # ---------------------------------------------------------------------------
  # Concurrent User Scenarios
  # ---------------------------------------------------------------------------

  @load @concurrent @skip @slow
  Scenario: System sustains 100 concurrent users over 5 minutes
    Given 100 authenticated clients submitting detections continuously
    When the load runs for 5 minutes at 1 request per second per client
    Then the overall success rate is above 99%
    And average response time remains below 200 milliseconds
    And P95 response time remains below 400 milliseconds
    And P99 response time remains below 500 milliseconds
    And no memory leaks are detected (memory growth less than 10%)
    And no data storage connection exhaustion occurs

  @load @concurrent @skip @slow
  Scenario: System handles 1000 concurrent users at peak load
    Given 1000 authenticated clients are ready to submit detections
    When all 1000 clients submit detections over a 60-second window
    Then at least 950 of 1000 submissions succeed
    And failed submissions receive appropriate throttle responses
    And the system recovers to normal response times within 30 seconds after peak
    And no data corruption occurs under load

  # ---------------------------------------------------------------------------
  # Throughput Scenarios
  # ---------------------------------------------------------------------------

  @load @throughput @skip @slow
  Scenario: System sustains 1000 requests per second throughput
    Given a load generator configured for 1000 requests per second
    When the sustained load runs for 2 minutes
    Then achieved throughput is at least 900 requests per second
    And error rate remains below 1%
    And response times do not progressively degrade (no sawtooth pattern)
    And data storage latency remains below 50 milliseconds

  @load @throughput @skip @slow
  Scenario: Detection processing pipeline maintains throughput under load
    Given 500 detections per second are submitted with geolocation data
    When the processing pipeline runs for 3 minutes
    Then geolocation calculations complete within 100 milliseconds each
    And CoT message generation keeps pace with incoming detections
    And the processing queue depth remains below 100 items
    And audit trail writes do not become a bottleneck

  # ---------------------------------------------------------------------------
  # Latency Scenarios
  # ---------------------------------------------------------------------------

  @load @latency @skip @slow
  Scenario: P99 latency stays below 500ms under normal load
    Given 50 concurrent users submitting at steady rate
    When 10000 total requests are processed
    Then P50 response time is below 100 milliseconds
    And P95 response time is below 300 milliseconds
    And P99 response time is below 500 milliseconds
    And maximum response time is below 2000 milliseconds
    And no requests timeout

  @load @latency @skip @slow
  Scenario: Response time distribution remains consistent over extended period
    Given 100 concurrent users submitting detections
    When the load runs for 10 minutes
    Then P99 latency in the first minute is within 20% of P99 in the last minute
    And no progressive latency degradation is observed
    And garbage collection pauses do not exceed 100 milliseconds

  # ---------------------------------------------------------------------------
  # Resource Utilization Scenarios
  # ---------------------------------------------------------------------------

  @load @resources @skip @slow
  Scenario: CPU utilization remains sustainable under peak load
    Given the system is under 500 requests per second load
    When resource metrics are captured over 5 minutes
    Then average CPU utilization stays below 70%
    And CPU spikes above 90% last no longer than 5 seconds
    And the system leaves headroom for traffic bursts

  @load @resources @skip @slow
  Scenario: Memory usage remains bounded during sustained load
    Given the system baseline memory usage is recorded
    When 100000 detections are processed over 10 minutes
    Then memory usage does not exceed 2x the baseline
    And no out-of-memory events occur
    And memory returns to near-baseline within 60 seconds after load stops

  @load @resources @skip @slow
  Scenario: Data storage connection pool handles concurrent demand
    Given the connection pool is configured with 20 connections
    When 200 concurrent data operations are requested
    Then all operations complete without connection errors
    And connection wait time remains below 100 milliseconds
    And no connections are leaked after operations complete

  # ---------------------------------------------------------------------------
  # Recovery and Resilience Scenarios
  # ---------------------------------------------------------------------------

  @load @resilience @skip @slow
  Scenario: System recovers gracefully after traffic spike
    Given normal traffic of 100 requests per second
    When traffic spikes to 2000 requests per second for 30 seconds
    And traffic returns to 100 requests per second
    Then the system returns to normal response times within 60 seconds
    And no requests submitted during recovery are lost
    And the processing backlog is cleared within 2 minutes

  @load @resilience @skip @slow
  Scenario: Partial infrastructure failure under load does not cascade
    Given 200 concurrent users are active
    When the caching layer becomes temporarily unavailable
    Then detection submissions continue to work (bypassing cache)
    And response times increase but remain below 2 seconds
    And when the cache recovers, normal performance resumes
    And no data inconsistency results from the cache outage
