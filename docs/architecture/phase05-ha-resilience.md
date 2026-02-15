# Phase 05: High Availability and Resilience Design

**Date**: 2026-02-15
**Author**: Alex Chen, Solution Architect

---

## 1. Availability Target

**Target**: 99.9% uptime (8.76 hours/year maximum downtime)

**Measured as**: Detection API accepting and processing requests. TAK push failures are acceptable (offline queue absorbs) -- availability means "system accepts detections," not "TAK receives detections."

---

## 2. Failure Modes and Recovery

### 2.1 Pod Failure

| Failure | Detection | Recovery | Downtime |
|---------|-----------|----------|----------|
| OOM Kill | Kubernetes detects exit code 137 | Automatic restart, HPA may scale up | <30s (restart) |
| Application crash | Liveness probe failure (3 consecutive) | Kubernetes restarts pod | <90s (initial delay + 3 failures) |
| Unresponsive (hung) | Liveness probe timeout | Kubernetes restarts pod | <90s |
| Slow startup | Startup probe (150s window) | Waits for startup, restarts if exceeded | 0 (graceful) |

**PDB guarantee**: `minAvailable: 2` ensures at least 2 pods serve traffic during voluntary disruptions (node drain, deployment rollout).

### 2.2 Node Failure

| Failure | Detection | Recovery | Downtime |
|---------|-----------|----------|----------|
| Node unreachable | Kubernetes node controller (5 min default) | Pods rescheduled to healthy nodes | <6 min |
| Node drain (maintenance) | Voluntary, PDB-controlled | Pods evicted one at a time | 0 (PDB enforced) |

**Topology spread**: `topologySpreadConstraints` distributes pods across zones and nodes. Single zone failure affects at most ceil(replicas/zones) pods. With 3 replicas across 3 zones, single zone loss leaves 2 pods serving.

### 2.3 TAK Server Failure

| Failure | Detection | Recovery | Downtime |
|---------|-----------|----------|----------|
| TAK unreachable | HTTP timeout (5s) | CoT queued to offline queue (emptyDir) | 0 (detection accepted) |
| TAK returns 500 | HTTP response code | CoT queued, retry with backoff | 0 (detection accepted) |
| TAK prolonged outage | Queue depth increasing | Monitor alert, queue absorbs up to 100,000 items | 0 (detection accepted) |
| TAK restored | Connectivity monitor (30s interval) | Automatic batch sync from queue | 0 (transparent) |

**Key design property**: Detection acceptance is decoupled from TAK availability. The offline-first architecture (ADR-001) ensures the detection pipeline never blocks on TAK.

### 2.4 Database Failure

| Failure | Detection | Recovery | Downtime |
|---------|-----------|----------|----------|
| SQLite corruption | Health check fails (SELECT 1) | Restore from daily backup, restart pod | <5 min (manual) |
| PVC full | Write error | Alert, expand PVC or archive old data | Degraded (reads work) |
| PVC detached | Mount error | Pod restart, PVC re-attached | <60s |

### 2.5 Full Cluster Failure

| Failure | Detection | Recovery | Downtime |
|---------|-----------|----------|----------|
| Control plane down | Existing pods continue running | Wait for control plane recovery | 0 (existing pods serve) |
| Full cluster loss | Everything down | Restore from backup, redeploy via ArgoCD to new cluster | Hours (disaster recovery) |

---

## 3. Resilience Patterns

### 3.1 Circuit Breaker (TAK Push)

The CotService already implements timeout-based circuit breaking:
- 5-second timeout on TAK HTTP PUT
- Failure triggers queue fallback (no retry storm)
- Connectivity monitor checks every 30 seconds
- Sync on restore uses batch processing with backoff

### 3.2 Graceful Degradation

```
Normal mode:
  Detection -> Geolocate -> CoT -> TAK Push -> SYNCED

Degraded mode (TAK unavailable):
  Detection -> Geolocate -> CoT -> Queue (PENDING_SYNC)
                                      |
                              [TAK restored]
                                      |
                              Batch Sync -> SYNCED
```

### 3.3 Graceful Shutdown

Existing `preStop` hook: `sleep 15` allows in-flight requests to drain before SIGTERM.

`terminationGracePeriodSeconds: 30` gives total 30 seconds for:
- 15s sleep (request draining)
- 15s for application shutdown (flush audit trail, close DB connections)

### 3.4 Pod Disruption Budget

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: detection-api-pdb
  namespace: detection-system
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: detection-api
```

With 3 replicas, this allows 1 pod disruption at a time. Node drains, cluster upgrades, and voluntary evictions respect this budget.

---

## 4. Data Durability

### 4.1 Detection Data (app.db)

- **Storage**: PersistentVolumeClaim (`detection-data-pvc`, 50Gi, fast-ssd)
- **Backup**: Daily CronJob at 02:00 UTC using `sqlite3 .backup`
- **Retention**: 30 days of backups on `detection-backup-pvc`
- **RPO**: 24 hours (daily backup)
- **RTO**: <10 minutes (restore backup, restart pod)

### 4.2 Offline Queue (queue.db)

- **Storage**: `emptyDir` per pod (ephemeral)
- **Durability**: Queue items survive pod restarts (SQLite WAL mode). Lost on pod deletion or node failure.
- **Acceptable**: Queue is a resilience buffer. Items either sync to TAK within minutes or are regenerated from source. No critical data is exclusively in the queue.
- **Recovery**: `recover_from_crash()` runs on startup, processes any remaining queue items.

### 4.3 Audit Trail (in app.db)

- **Co-located with detection data**: Same PVC, same backup schedule
- **Immutable**: Append-only audit events cannot be modified after creation
- **Compliance**: 90-day retention minimum enforced by application, backup extends to 30 days of full snapshots

---

## 5. Monitoring for Resilience

| Metric | Alert Threshold | Meaning |
|--------|----------------|---------|
| Pod restarts | >2 in 5 minutes | Crash loop, investigate root cause |
| Available replicas | <2 for 2 minutes | Below HA minimum, page on-call |
| PVC usage | >80% | Storage approaching limit, expand or archive |
| Queue depth | >1000 for 10 minutes | TAK connectivity issue, investigate |
| Error rate | >5% for 5 minutes | Application error, may need rollback |
| Request latency p99 | >2 seconds for 5 minutes | Performance degradation |
