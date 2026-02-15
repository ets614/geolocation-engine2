@feature_us005
Feature: Handle Offline Queuing and Sync
  As a field operator
  I want detections to queue locally when connection is lost
  So that I don't lose detections and don't have to manually screenshot

  Background:
    Given the offline queue service is running
    Given the local SQLite database is initialized
    Given queue max size is 10,000 detections
    Given sync batch size is 100 detections/batch

  @happy_path @smoke @milestone_1
  Scenario: Detections queue locally when network unavailable
    Given a detection is ready to output to remote database
    And the network connection to remote database is lost
    When the system attempts to sync the detection
    Then the sync fails (connection refused)
    And the detection is written to local SQLite queue
    And the detection is marked PENDING_SYNC
    And status dashboard shows "Status: OFFLINE (1 pending)"
    And no error is raised to the operator
    And system continues accepting new detections (non-blocking)

  @happy_path @milestone_1
  Scenario: Queued detections sync automatically when network restored
    Given 3 detections are queued locally (PENDING_SYNC):
      | detection | queued_at    | status        |
      | det1      | 14:35:42     | PENDING_SYNC  |
      | det2      | 14:35:43     | PENDING_SYNC  |
      | det3      | 14:35:44     | PENDING_SYNC  |
    And the queue is persisted in SQLite
    When network connectivity is restored
    Then the system detects connection restored automatically
    And system begins syncing queued detections (3 pending)
    And each detection is written to remote database:
      | detection | synced_at    | status   |
      | det1      | 14:37:01     | SYNCED   |
      | det2      | 14:37:02     | SYNCED   |
      | det3      | 14:37:03     | SYNCED   |
    And status dashboard updates: "Status: SYNCING (3/3 complete)"
    And all detections appear on remote COP system
    And local queue is cleared (all marked SYNCED)

  @resilience @critical
  Scenario: Queue survives system restart (power cycle)
    Given 5 detections are queued locally (PENDING_SYNC)
    And the queue is persisted in SQLite file
    When the system is restarted (intentional power cycle, hardware failure simulation)
    Then the queued detections are recovered from persistent storage
    And all 5 detections are still marked PENDING_SYNC
    And system detects network is available
    And automatically syncs all 5 queued detections
    And no operator action required for recovery
    And status dashboard shows "Queue recovered (5 items synced)"

  @edge_case
  Scenario: Intermittent connection (repeated on/off cycles)
    Given the system is receiving detections
    When network connectivity cycles on/off/on/off:
      | time      | event            | action                           |
      | 14:35:00  | Connection UP    | Sync successful                  |
      | 14:35:30  | Connection DOWN  | Detection 1 queued locally       |
      | 14:36:00  | Connection UP    | Sync detection 1 (SYNCED)        |
      | 14:36:15  | Connection DOWN  | Detection 2 queued locally       |
      | 14:37:00  | Connection UP    | Sync detection 2 (SYNCED)        |
    Then system handles repeated on/off cycles gracefully
    And no detections are lost
    And each sync completes successfully
    And no operator intervention needed
    And audit trail shows all sync events

  @resilience @extended_outage
  Scenario: Extended outage - longer queue period
    Given a fire detection API is returning 1 detection/minute
    And network connection to remote is lost
    When network is unavailable for 10 minutes:
      | minute | event                          |
      | 1      | Detection 1 → queue (1 pending) |
      | 2      | Detection 2 → queue (2 pending) |
      | 3      | Detection 3 → queue (3 pending) |
      | ...    | ...                            |
      | 10     | Detection 10 → queue (10 pending) |
    Then system queues all 10 detections successfully
    And queue status shows "10 pending" throughout outage
    And all 10 persisted in SQLite
    When network is restored
    Then system detects connectivity restored
    And begins batch sync of all 10 detections
    And sync completes in <5 seconds for all 10
    And status dashboard: "Recovered 10 detections"
    And operator sees no disruption (transparent recovery)

  @resilience @queue_persistence
  Scenario: Queue persists across multiple failure scenarios
    Given queue contains 5 PENDING_SYNC detections
    When queue is tested for persistence:
      | scenario               | action                           |
      | Power cycle            | System restart → recover queue   |
      | Database lock conflict | SQLite lock, system waits, retry |
      | Disk full warning      | Log warning, queue still accessible |
      | Filesystem unmount     | Remount, queue still intact      |
    Then all 5 detections survive and are recoverable
    And no data corruption occurs
    And queue integrity is maintained
    And sync succeeds after each scenario

  @performance @sla
  Scenario: Sync latency meets <5 second SLA for first detection
    Given 10 detections queued locally
    When network connectivity is restored
    Then first detection begins syncing within 1 second
    And first detection synced within 2 seconds
    And p99 latency for first detection <5 seconds
    And batch processing handles remaining 9 in <3 seconds

  @performance @throughput
  Scenario: Batch sync processes high volume efficiently
    Given 1000 detections queued locally
    When network is restored and sync begins
    Then batch sync processes detections in batches:
      | batch | detections | sync_time |
      | 1     | 100        | 500ms     |
      | 2     | 100        | 480ms     |
      | 3     | 100        | 490ms     |
      | ...   | ...        | ...       |
      | 10    | 100        | 510ms     |
    And total sync time for 1000 items <6 seconds
    And throughput is >1000 detections/sec
    And no detections lost or duplicated

  @error_handling
  Scenario: Sync failures are retried with exponential backoff
    Given 5 detections are queued (PENDING_SYNC)
    When sync is attempted but fails (transient error):
      | attempt | wait_time | status   |
      | 1       | 0s        | FAILED (sync error) |
      | 2       | 100ms     | FAILED (retry)      |
      | 3       | 150ms     | FAILED (retry)      |
      | 4       | 225ms     | SUCCESS (synced)    |
    Then detections are retried with exponential backoff
    And maximum 5 retries before giving up
    And failed detections logged for manual intervention
    And audit trail shows all retry attempts

  @error_handling
  Scenario: Permanent sync failure is logged and alerted
    Given 3 detections are queued (PENDING_SYNC)
    When sync is attempted 5 times and fails every time:
      | retry | error                  |
      | 1     | Connection refused     |
      | 2     | Connection refused     |
      | 3     | Connection refused     |
      | 4     | Connection refused     |
      | 5     | Connection refused     |
    Then system gives up after 5 retries
    And detection is marked SYNC_FAILED (not PENDING_SYNC)
    And operator is alerted: "Permanent sync failure for detections: [det1, det2, det3]"
    And audit trail shows all retry attempts and failure
    And detection remains in queue for manual intervention

  @monitoring @dashboard
  Scenario: Queue status is visible on operations dashboard
    Given the offline queue service is running
    When operator views status dashboard
    Then dashboard displays:
      | metric                | value          |
      | Connection status     | UP/DOWN        |
      | Queue depth           | X pending      |
      | Last sync attempt     | HH:MM:SS ago   |
      | Last successful sync  | HH:MM:SS ago   |
      | Sync success rate     | X.X%           |
      | Oldest queued item    | HH:MM:SS old   |
    And dashboard updates in real-time
    And queue status is color-coded (green=synced, yellow=buffering, red=failed)

  @audit_trail
  Scenario: Queue and sync events are logged in audit trail
    Given a detection goes from queued → synced
    When the sync completes
    Then audit trail records:
      | event              | details                          |
      | sync_failed        | timestamp, detection_id, error   |
      | queued_locally     | timestamp, queue_depth, status   |
      | sync_retry_attempt | retry count, backoff_delay       |
      | sync_success       | timestamp, sync_latency_ms       |
      | status_updated     | PENDING_SYNC → SYNCED            |
    And all events are timestamped and searchable
    And queue timeline visible in audit trail

  @compliance @zero_loss
  Scenario: Zero data loss guarantee during offline period
    Given N detections arrive during offline period:
      | N     | period          |
      | 100   | 1 minute        |
      | 500   | 5 minutes       |
      | 1000  | 10 minutes      |
    When all N are queued locally
    And system is restarted (power cycle)
    And network is restored
    Then all N detections are recovered
    And all N are synced successfully
    And ZERO detections lost
    And ZERO duplicates created
    And Data integrity verified

  @stress_test
  Scenario: Queue approaches maximum size (10,000 limit)
    Given queue limit is 10,000 detections
    When queue grows to 9,900 items (99% capacity)
    Then system logs warning: "Queue approaching limit (9900/10000)"
    And operator is alerted: "Queue utilization 99%"
    And system continues queuing (non-blocking)
    When queue reaches 10,000 items
    Then system logs alert: "Queue at maximum capacity"
    And operator is alerted with urgency: "Queue full, reduce load"
    And system stops accepting new detections (graceful rejection)
    And HTTP 507 error returned: "Queue full"
    When sync completes and queue drains
    Then system resumes accepting detections
    And queue status returns to normal

  @integration @end_to_end
  Scenario: Complete offline journey from field to ops center
    Given UAV is flying mission in area with intermittent connectivity
    When detections are detected and transmitted:
      | time      | event                                    |
      | 14:00:00  | UAV boots, network UP, connects to ops  |
      | 14:05:00  | Detection 1 synced successfully         |
      | 14:15:00  | Network drops (entering dead zone)      |
      | 14:15:30  | Detection 2 detected (offline queued)   |
      | 14:25:00  | Detection 3 detected (offline queued)   |
      | 14:35:00  | Network restored (exiting dead zone)    |
      | 14:35:05  | System auto-syncs Det2 + Det3 to ops    |
    Then ops center receives timeline:
      | detection | received_at | status    |
      | Det1      | 14:05:01    | SYNCED    |
      | Det2      | 14:35:06    | SYNCED    |
      | Det3      | 14:35:07    | SYNCED    |
    And all 3 appear on map in correct locations
    And audit trail shows offline queue lifecycle
    And no manual workaround (screenshots) needed
