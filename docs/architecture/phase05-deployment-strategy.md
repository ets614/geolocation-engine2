# Phase 05: Deployment Strategy and Runbook

**Date**: 2026-02-15
**Author**: Alex Chen, Solution Architect

---

## 1. Deployment Pipeline

### Stage Flow

```
[1] Commit Push
     |
[2] Lint + Type Check + Unit Tests + SAST + Dependency Scan
     |
[3] Docker Build + Trivy Image Scan + Cosign Image Sign
     |
[4] Update image tag in kubernetes/manifests/ (Git commit)
     |
[5] ArgoCD detects change, syncs green deployment
     |
[6] Smoke tests against green pods (direct service, not via ingress)
     |
[7] Traffic switch: patch service selector to green (Git commit)
     |
[8] ArgoCD syncs service selector change
     |
[9] 5-minute production monitoring (error rate, latency, queue depth)
     |
[10a] PASS: Scale down blue to 0 replicas (Git commit)
[10b] FAIL: Revert service selector to blue (Git revert + commit)
```

### Blue-Green Slot Lifecycle

| Phase | Blue Slot | Green Slot | Traffic |
|-------|-----------|------------|---------|
| Steady state | Active (current version) | Idle (0 replicas) | Blue |
| Deploy start | Active (current version) | Scaling up (new version) | Blue |
| Smoke test | Active (current version) | Ready (new version) | Blue |
| Traffic switch | Standby (old version) | Active (new version) | Green |
| Monitor (5 min) | Standby (old version) | Active (new version) | Green |
| Finalize | Scale to 0 | Active (new version) | Green |
| Next deploy | Scaling up (newer version) | Active (current version) | Green |

**Slot alternation**: Each deployment targets the idle slot. The active slot becomes standby, then scales to 0 after validation.

---

## 2. Rollback Procedures

### Automatic Rollback (CI/CD)

**Trigger**: Smoke test failure or monitoring threshold breach during deployment.

**Action**: CI/CD commits Git revert of service selector change. ArgoCD syncs revert within 3 minutes (or manual sync for immediate effect).

**Recovery time**: <60 seconds from failure detection to traffic restoration.

### Manual Rollback (Operations)

**Trigger**: Post-deployment issue discovered after pipeline completion.

**Option A: ArgoCD UI**
1. Open ArgoCD dashboard
2. Select `detection-api` application
3. Click "History" to find last known-good revision
4. Click "Rollback" to that revision
5. Verify traffic restored

**Option B: Git Revert**
1. `git revert <bad-commit-sha>`
2. `git push origin main`
3. ArgoCD auto-syncs within 3 minutes

**Option C: Emergency kubectl (when ArgoCD unavailable)**
1. `kubectl patch svc detection-api-service -n detection-system -p '{"spec":{"selector":{"slot":"blue"}}}'`
2. Verify: `kubectl get endpoints detection-api-service -n detection-system`
3. Document manual change for later Git reconciliation

---

## 3. Pre-Deployment Checklist

- [ ] All unit tests passing (CI gate)
- [ ] All integration tests passing (CI gate)
- [ ] Trivy scan: no CRITICAL vulnerabilities
- [ ] Image signed with Cosign
- [ ] Image tag matches Git SHA
- [ ] ConfigMap changes reviewed (if any)
- [ ] Secret changes sealed and committed (if any)
- [ ] Monitoring dashboard accessible
- [ ] On-call engineer identified and notified

---

## 4. Post-Deployment Verification

| Check | Method | Expected |
|-------|--------|----------|
| Pods running | `kubectl get pods -n detection-system -l slot=green` | 3/3 Ready |
| Health endpoint | `curl https://detection-api.internal.example.com/health` | 200 OK |
| Ready endpoint | `curl https://detection-api.internal.example.com/ready` | 200 OK |
| Metrics endpoint | `curl https://detection-api.internal.example.com/metrics` | Prometheus text format |
| Detection pipeline | POST test detection to `/api/v1/detections` | 201 with CoT XML |
| Grafana dashboard | Check detection pipeline dashboard | Metrics updating |
| Error rate | Prometheus query: `rate(http_requests_total{status=~"5.."}[5m])` | < 1% |
| Queue depth | Prometheus query: `offline_queue_depth` | 0 (or stable) |

---

## 5. Incident Response

### Severity Levels

| Level | Definition | Response Time | Example |
|-------|-----------|--------------|---------|
| SEV-1 | Detection pipeline down, no detections reaching TAK | 5 min | All pods CrashLoopBackOff |
| SEV-2 | Degraded performance, >5% error rate | 15 min | TAK push failures queuing |
| SEV-3 | Non-critical issue, workaround available | 1 hour | Grafana dashboard unreachable |
| SEV-4 | Cosmetic or low-impact issue | Next business day | Log format inconsistency |

### SEV-1 Runbook

1. **Assess**: Check Grafana alerts, `kubectl get pods -n detection-system`
2. **Contain**: If deploy-related, rollback immediately (see Section 2)
3. **Diagnose**: `kubectl logs -n detection-system -l app=detection-api --tail=100`
4. **Recover**: Fix forward (if config issue) or rollback (if code issue)
5. **Post-mortem**: Document in incident log within 24 hours

---

## 6. Capacity Planning

### Current Baseline

| Metric | Value | Source |
|--------|-------|--------|
| Request rate | <10 req/s | Phase 04 performance tests |
| P99 latency | <200ms | Phase 04 performance tests |
| Memory per pod | ~256Mi steady | Application profiling |
| CPU per pod | ~100m steady | Application profiling |
| Queue write rate | <1000 items/s | OfflineQueueService batch test |
| Database size growth | ~10MB/day at 10 req/s | Calculated from detection record size |

### Scaling Thresholds

| Trigger | Current | Scale Action |
|---------|---------|-------------|
| CPU > 70% sustained | 3 replicas | HPA adds pods (max 10) |
| Memory > 75% sustained | 3 replicas | HPA adds pods (max 10) |
| >100 req/s sustained | HPA sufficient | Consider SQLite -> PostgreSQL migration |
| >50GB database | 50Gi PVC | Expand PVC or archive old detections |
| >10,000 queue items | emptyDir 5Gi | Investigate TAK connectivity, increase queue size |
