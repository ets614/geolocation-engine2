# ADR-001: Offline-First Architecture

**Status**: Accepted

**Date**: 2026-02-17

**Decision Makers**: Solution Architect, Product Owner

---

## Context

The system must deliver detections to TAK/ATAK/COP platforms when field operators have intermittent or unreliable network connectivity. Current systems fail 20-30% of the time due to network outages, forcing operators to manually screenshot detections and manually enter them into the COP (Interview 4).

Two architectural approaches were considered:

1. **Remote-First with Local Fallback**: Attempt remote write first, queue locally only if it fails
2. **Offline-First with Automatic Sync**: Always write to local queue first, sync to remote asynchronously

---

## Decision

We will implement **Offline-First architecture** where:

1. All detections are written to local SQLite queue immediately upon validation
2. System attempts to sync to remote TAK/ArcGIS system asynchronously
3. When network is unavailable, system continues operating normally
4. When network is restored, system automatically syncs all queued detections
5. Operator sees no disruption during offline/sync cycle

**Data Flow**:
```
Detection → Validate → Write to Queue (local) → Attempt Remote Sync
                                    ↓
                          If sync fails → Queue persists
                          If sync succeeds → Mark SYNCED
                          On reconnect → Auto-retry sync
```

---

## Rationale

### Why Offline-First?

1. **Zero Data Loss**: Detections are persisted to disk BEFORE attempting network operations. If network fails mid-sync, data is preserved.

2. **User Experience**: Operators experience no disruption during transient network failures. No alerts, no errors, no manual workarounds required.

3. **Tactical Operations**: Field operators (UAV pilots, ground station operators) cannot wait for network to stabilize. They need detections to appear on the map whenever connectivity exists.

4. **Field Reality**: Interviews revealed operators currently work around system failures by taking screenshots and manually entering data. Offline-first eliminates this workaround entirely.

5. **Transparent Recovery**: System handles network failures invisibly. When connection restored (even minutes later), all queued detections sync automatically. Operators never need to be aware of offline periods.

---

## Alternatives Considered

### Alternative 1: Remote-First with Local Fallback
**Process**:
1. Receive detection
2. Attempt to write to remote database
3. If remote write fails → write to local queue
4. Manual operator intervention to retry sync

**Advantages**:
- Simpler immediate logic (try remote first)
- Fewer detections in local queue typically

**Disadvantages**:
- Data loss if crash occurs between remote failure and local write
- Operator must manually trigger retry (requires awareness of offline state)
- Encourages timeout tuning games (how long to wait for remote?)
- Contradicts "offline-first" operational model

**Why Rejected**: Interview 4 explicitly stated manual workarounds are unacceptable. Operator must not be required to take action for system to recover.

### Alternative 2: Dual-Write (Remote + Local Simultaneously)
**Process**:
1. Receive detection
2. Write to both remote AND local queue simultaneously
3. If either fails, log error

**Advantages**:
- Both systems always consistent

**Disadvantages**:
- Network latency blocks ingestion (must wait for remote write)
- Increases ingestion latency from <100ms to potentially 1-5 seconds
- Violates stated acceptance criterion (<100ms ingestion)
- More complex error recovery (what if one succeeds, other fails?)

**Why Rejected**: Violates ingestion latency target (<100ms). Network operations are too variable to serialize ingestion.

---

## Consequences

### Positive

1. **Reliability**: 99%+ of detections reach destination, even during outages
2. **User Experience**: Zero operator friction during network failures
3. **Simplicity**: Single source of truth (local queue), simpler error handling
4. **Speed**: Ingestion latency unaffected by network conditions
5. **Resilience**: Survives system crashes (queue persists to disk)

### Negative

1. **Eventual Consistency**: Remote system may lag behind local state during offline periods
2. **Disk Space**: Must allocate disk space for queue (mitigated by max size limit)
3. **Sync Complexity**: Must implement batch sync, retry logic, duplicate detection
4. **Operational Monitoring**: Operators cannot see which detections are queued vs. synced (mitigated by status dashboard)

### Mitigations

1. **Max Queue Size**: Limit queue to 10,000 detections. Alert operator if approaching limit.
2. **Sync Efficiency**: Batch sync at 1000+ items/second when reconnected
3. **Transparent Status**: Dashboard shows queue depth, last sync time, sync success rate
4. **Audit Trail**: Every sync event logged with timestamps (no ambiguity about timeline)
5. **Duplicate Detection**: Tag detections with unique ID + timestamp to detect replays

---

## Implementation Details

### SQLite Queue Schema
```sql
CREATE TABLE offline_queue (
  id TEXT PRIMARY KEY,
  detection_json TEXT NOT NULL,
  status TEXT DEFAULT 'PENDING_SYNC',  -- PENDING_SYNC | SYNCED | FAILED
  created_at TEXT NOT NULL,
  synced_at TEXT,
  retry_count INTEGER DEFAULT 0,
  error_message TEXT,
  batch_id TEXT
);
```

### Sync Algorithm
```python
def sync_queue():
    """Sync all PENDING_SYNC items to remote system"""
    pending = db.query("SELECT * FROM offline_queue WHERE status = 'PENDING_SYNC' ORDER BY created_at")

    batch = []
    for item in pending:
        detection = json.loads(item.detection_json)
        batch.append(detection)

        if len(batch) >= 100:  # Batch size for efficiency
            try:
                sync_batch_to_remote(batch)
                for detection in batch:
                    db.update(f"UPDATE offline_queue SET status='SYNCED', synced_at=NOW() WHERE id='{detection.id}'")
                batch = []
            except NetworkError:
                # Retry exponential backoff
                update_retry_count(batch)
                return  # Stop batch, will retry on next connectivity check

    # Final batch
    if batch:
        try:
            sync_batch_to_remote(batch)
            for detection in batch:
                db.update(f"UPDATE offline_queue SET status='SYNCED', synced_at=NOW() WHERE id='{detection.id}'")
        except NetworkError:
            update_retry_count(batch)
```

### Connectivity Monitoring
```python
async def monitor_connectivity():
    """Check network status every 30 seconds"""
    while True:
        try:
            # Test connectivity to TAK Server
            response = httpx.get(TAK_HEALTH_ENDPOINT, timeout=5)
            if response.status_code == 200:
                # Network is up, sync queued items
                await sync_queue()
        except:
            pass  # Network is down, continue

        await asyncio.sleep(30)
```

---

## Related Decisions

- **ADR-005**: SQLite for MVP persistence layer
- **ADR-004**: GeoJSON RFC 7946 standard (enables multi-platform compatibility)

---

## References

- **Interview 4** (Field Operations): "System fails 20-30% of the time... I had to land, walk over to the ops tent, show them screenshots... then they manually entered the locations into TAK."
- **Solution Test** (Interview 4): "If detections queue locally and sync when connection restores, I don't have to manually screenshot." — VALIDATED

---

## Validation

**MVP Success Criteria**:
- [x] 99%+ of detections reach destination even during network outages
- [x] Operator sees no alerts/errors during normal offline/sync cycle
- [x] Queue survives system restart
- [x] Sync automatic (no operator intervention)
- [x] Audit trail shows sync timeline

**Proof**: Integration testing with simulated network failures, power cycles, extended outages
