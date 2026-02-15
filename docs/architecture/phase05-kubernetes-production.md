# Phase 05: Production Kubernetes Architecture Design

**Project**: AI Detection to COP Translation System
**Phase**: 05 - Production Deployment
**Date**: 2026-02-15
**Author**: Alex Chen, Solution Architect
**Status**: DESIGN COMPLETE - Ready for Peer Review

---

## 1. Executive Summary

Phase 05 transforms the detection-api from a walking skeleton deployed with raw manifests into a production-grade Kubernetes deployment with high availability, observability, security hardening, and GitOps-driven delivery.

### Existing System Inventory

| Component | Location | Status |
|-----------|----------|--------|
| Blue/Green Deployment | `kubernetes/manifests/deployment.yaml` | EXISTS - needs revision |
| Services, Ingress, NetworkPolicies | `kubernetes/manifests/services.yaml` | EXISTS - needs revision |
| RBAC | `kubernetes/manifests/rbac.yaml` | EXISTS - adequate |
| Helm values | `kubernetes/helm-charts/values.yaml` | EXISTS - needs revision |
| CI/CD Pipeline | `.github/workflows/ci-cd-pipeline.yml` | EXISTS - adequate |

### Critical Gaps Identified

| Gap | Severity | Section |
|-----|----------|---------|
| SQLite PVC shared across blue/green pods (ReadWriteOnce conflict) | CRITICAL | 2.1 |
| All resources in `default` namespace | HIGH | 2.2 |
| No HPA manifests | HIGH | 3.1 |
| No observability stack | HIGH | 5.0 |
| Missing DNS egress in NetworkPolicy | HIGH | 6.1 |
| No secret rotation strategy | MEDIUM | 4.2 |
| No multi-zone topology spread | MEDIUM | 3.2 |
| No backup CronJob | MEDIUM | 3.4 |
| HPA disabled in values.yaml | MEDIUM | 3.1 |
| No Pod Security Standards admission | MEDIUM | 6.2 |

---

## 2. Kubernetes Architecture Design

### 2.1 Pod Specifications and Resource Limits

**Current State**: Existing `deployment.yaml` defines blue/green deployments with 3 replicas each, 500m/1Gi requests, 1000m/2Gi limits.

**Issue**: Both blue and green deployments reference the same PVC `detection-queue-pvc` with `ReadWriteOnce` access mode. Only one pod on one node can mount this PVC at a time. With `podAntiAffinity` requiring spread across nodes, only one deployment slot can function.

**Resolution**: Each pod must maintain its own SQLite queue file. Use `emptyDir` for ephemeral queue storage or switch to per-pod PVCs via StatefulSet. Since the OfflineQueueService already supports crash recovery (`recover_from_crash()`), ephemeral storage with periodic backup to a shared volume is acceptable.

**Revised Pod Spec**:

```yaml
# Pod resource profile (per container)
resources:
  requests:
    cpu: 250m        # Reduced from 500m; photogrammetry is not CPU-bound at 10 req/s
    memory: 512Mi    # Reduced from 1Gi; SQLite + FastAPI fits in 512Mi
  limits:
    cpu: 1000m       # Burst for numpy calculations
    memory: 1Gi      # Reduced from 2Gi; cap prevents OOM cascade
```

**Rationale for resource reduction**: Profiling data from Phase 04 performance tests shows the application handles 100+ detections/second on a single core. The photogrammetry calculation (numpy matrix operations) completes in <5ms. The 500m/1Gi baseline was conservative padding; 250m/512Mi is sufficient for steady state with 1000m/1Gi burst headroom.

### 2.2 Namespace Strategy

**Decision**: Dedicated `detection-system` namespace replaces `default`.

**Justification**:
- Resource quotas scoped to workload, not shared with system pods
- NetworkPolicy defaults apply only to detection workloads
- RBAC boundaries prevent cross-workload access
- Simplifies `kubectl` operations and monitoring queries

**Namespace Manifest**:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: detection-system
  labels:
    app.kubernetes.io/part-of: detection-cop
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

### 2.3 Deployment Strategy: Blue-Green

**Decision**: RETAIN existing blue-green strategy with corrections.

**Alternatives Considered**:
- Canary (progressive traffic shift): More complex; requires service mesh or Flagger. Rejected -- overkill for single-service deployment with <10 req/s baseline.
- Rolling update only: Simpler but no instant rollback capability. Rejected -- tactical system requires instant rollback for zero-downtime guarantee.

**Blue-green is correct** for this workload because:
- Service selector patch (`slot: blue` / `slot: green`) provides instant traffic switch
- Old slot remains running for instant rollback
- CI/CD pipeline already implements this pattern
- Low replica count (3) makes doubling resources during deploy acceptable

**Correction Required**: Remove shared PVC. Each slot uses `emptyDir` for queue storage. The offline queue is a resilience buffer, not a persistence layer; detections are the primary data in the app database.

### 2.4 Services and Ingress

**Existing**: ClusterIP service, headless service, NGINX Ingress with TLS.

**Revisions**:
- Move all resources to `detection-system` namespace
- Add `topology.kubernetes.io/zone` to Ingress annotations for zone-aware routing
- Rate limit annotation correction: `nginx.ingress.kubernetes.io/limit-rps` replaces non-standard `rate-limit`

### 2.5 Resource Quotas

**Existing quotas are oversized** for a single-service namespace. Revised:

```yaml
spec:
  hard:
    requests.cpu: "8"          # 3 replicas * 2 slots * 250m + headroom
    requests.memory: "8Gi"     # 3 replicas * 2 slots * 512Mi + headroom
    limits.cpu: "16"
    limits.memory: "16Gi"
    pods: "20"                 # 6 app + monitoring + jobs
    services: "5"
    persistentvolumeclaims: "5"
```

---

## 3. High Availability and Resilience

### 3.1 Horizontal Pod Autoscaler

**Decision**: Enable HPA with conservative thresholds.

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: detection-api-hpa
  namespace: detection-system
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: detection-api-green  # Target active slot
  minReplicas: 3
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 75
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300  # 5 min cooldown prevents flapping
      policies:
        - type: Pods
          value: 1
          periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 30
      policies:
        - type: Pods
          value: 2
          periodSeconds: 60
```

**Alternatives Considered**:
- KEDA (event-driven autoscaling): Would allow scaling on queue depth metric. Rejected for MVP -- adds operator dependency and complexity. CPU-based HPA covers the primary bottleneck (numpy photogrammetry). KEDA is a Phase 06 enhancement when custom metrics pipeline is established.
- Fixed replica count: Simpler. Rejected -- cannot handle burst detection loads from multiple concurrent UAV streams without over-provisioning.

### 3.2 Topology Spread Constraints

**Replace** existing `podAntiAffinity` (hard requirement) with topology spread constraints. Hard anti-affinity fails scheduling when nodes < replicas.

```yaml
topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: ScheduleAnyway
    labelSelector:
      matchLabels:
        app: detection-api
  - maxSkew: 1
    topologyKey: kubernetes.io/hostname
    whenUnsatisfiable: ScheduleAnyway
    labelSelector:
      matchLabels:
        app: detection-api
```

**Rationale**: `ScheduleAnyway` with `maxSkew: 1` provides best-effort zone/node spread without blocking scheduling. The existing `requiredDuringSchedulingIgnoredDuringExecution` anti-affinity would prevent scaling beyond the number of nodes.

### 3.3 Health Checks

**Existing probes are well-configured**. Retain with minor adjustments:

| Probe | Path | Initial Delay | Period | Timeout | Failure Threshold |
|-------|------|--------------|--------|---------|-------------------|
| Startup | `/health` | 5s | 5s | 3s | 30 (150s max) |
| Liveness | `/health` | 10s | 30s | 5s | 3 |
| Readiness | `/ready` | 5s | 5s | 3s | 1 |

**Recommendation**: The `/ready` endpoint should check database connectivity and queue service health. The `/health` endpoint should be lightweight (return 200 if process is alive). This separation already exists in the application -- FastAPI serves `/api/v1/health`. The K8s probes use `/health` and `/ready` which need to be implemented as thin K8s-specific endpoints. The crafter owns this implementation.

### 3.4 Pod Disruption Budget

**Existing PDB** (`minAvailable: 2`) is correct for 3-replica baseline. Retain as-is.

### 3.5 Backup Strategy

**CronJob** for SQLite database backup (app.db contains detections and audit trail):

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: detection-db-backup
  namespace: detection-system
spec:
  schedule: "0 2 * * *"   # Daily at 02:00 UTC
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: backup
              image: registry.internal/detection-api:v1.0.0
              command: ["sqlite3", "/app/data/app.db", ".backup /backup/app-$(date +%Y%m%d).db"]
              volumeMounts:
                - name: data
                  mountPath: /app/data
                  readOnly: true
                - name: backup
                  mountPath: /backup
          volumes:
            - name: data
              persistentVolumeClaim:
                claimName: detection-data-pvc
            - name: backup
              persistentVolumeClaim:
                claimName: detection-backup-pvc
          restartPolicy: OnFailure
  successfulJobsHistoryLimit: 7
  failedJobsHistoryLimit: 3
```

**Retention**: 30 days, enforced by a cleanup CronJob or PVC lifecycle policy.

---

## 4. Secrets and Configuration

### 4.1 ConfigMap Strategy

**Existing ConfigMap** (`detection-config`) is adequate. Retain with namespace migration.

**Immutable ConfigMaps**: Set `immutable: true` on production ConfigMaps. Changes require creating a new ConfigMap and updating the deployment reference, which aligns with GitOps (every config change is a versioned commit).

### 4.2 Secret Storage

**Current State**: Plaintext `stringData` in `services.yaml` with comment "Use sealed-secrets or external-secrets in production."

**Decision**: Bitnami Sealed Secrets for secret encryption at rest in Git.

**Alternatives Considered**:
- External Secrets Operator (ESO) with AWS Secrets Manager / HashiCorp Vault: More feature-rich, supports rotation. Rejected for MVP -- requires external secret store infrastructure that may not exist in the deployment environment. Tactical/military deployments often run air-gapped.
- SOPS (Mozilla): Encrypts YAML files in-place. Rejected -- more complex GitOps workflow, no Kubernetes-native CRD.
- Kubernetes native secrets only: Simplest. Rejected -- secrets stored as base64 in etcd are not encrypted unless etcd encryption is configured cluster-wide.

**Sealed Secrets Workflow**:
1. Developer creates `SealedSecret` resource encrypted with cluster public key
2. SealedSecret stored in Git (encrypted, safe)
3. Sealed Secrets controller decrypts to native `Secret` in-cluster
4. Application reads secrets via `secretKeyRef` (unchanged)

**Secrets Inventory**:

| Secret Name | Keys | Source |
|-------------|------|--------|
| `tak-server-credentials` | username, password, endpoint | TAK Server admin |
| `jwt-signing-key` | secret_key | Generated, 256-bit random |
| `registry-credentials` | .dockerconfigjson | Container registry |

### 4.3 Secret Rotation

**Strategy**: Manual rotation with deployment rollout.

1. Generate new secret value
2. Create new SealedSecret with updated value
3. Commit to Git, ArgoCD syncs
4. Deployment picks up new secret via rollout restart

**Frequency**: JWT signing key quarterly. TAK credentials per organizational policy. Registry credentials annually.

**Automated rotation** (External Secrets Operator with Vault) is a Phase 06 enhancement when secret store infrastructure is available.

### 4.4 Environment Variables

**Retain existing pattern**: ConfigMap for non-sensitive config, Secret for credentials, fieldRef for pod identity. No changes needed.

---

## 5. Observability Architecture

### 5.1 Metrics Collection: Prometheus

**Decision**: Prometheus (self-hosted) scraping FastAPI `/metrics` endpoint.

The existing deployment already has Prometheus annotations:
```yaml
annotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "8000"
  prometheus.io/path: "/metrics"
```

**Application Integration**: The crafter must expose a `/metrics` endpoint serving Prometheus exposition format. The FastAPI application should use `prometheus-fastapi-instrumentator` (MIT license, free) or `starlette-prometheus` (MIT, free) to auto-instrument request latency, count, and error rate.

**Key Metrics to Expose**:

| Metric | Type | Description |
|--------|------|-------------|
| `detection_requests_total` | Counter | Total detections processed |
| `detection_request_duration_seconds` | Histogram | Processing latency |
| `geolocation_confidence_flag` | Counter (labels: flag) | GREEN/YELLOW/RED distribution |
| `tak_push_success_total` | Counter | Successful TAK pushes |
| `tak_push_failure_total` | Counter | Failed TAK pushes |
| `offline_queue_depth` | Gauge | Pending items in queue |
| `offline_queue_sync_total` | Counter | Items synced from queue |

### 5.2 Log Aggregation: Loki + Promtail

**Decision**: Grafana Loki for log aggregation.

**Alternatives Considered**:
- ELK Stack (Elasticsearch, Logstash, Kibana): Feature-rich full-text search. Rejected -- Elasticsearch requires significant memory (2-4GB minimum per node), expensive for a single-service deployment. Overkill.
- Cloud provider logging (CloudWatch, Stackdriver): Vendor-locked. Rejected -- tactical/military deployments may be air-gapped.

**Loki Advantages**:
- Lightweight (indexes labels, not content)
- Native Grafana integration
- 10x less resource usage than Elasticsearch
- Log correlation by pod labels (detection_id, source)
- Open source, Apache 2.0 license, free

**Architecture**:
```
detection-api pods (stdout JSON logs)
         |
    Promtail DaemonSet (scrapes pod logs)
         |
    Loki (stores, indexes by labels)
         |
    Grafana (query, visualize, alert)
```

**Existing JSON logging**: The application already outputs structured JSON logs (`LOG_FORMAT=json`). Loki indexes on `app`, `namespace`, `pod` labels. JSON fields extracted at query time via LogQL.

### 5.3 Distributed Tracing: OpenTelemetry

**Decision**: Defer to Phase 06.

**Rationale**: Single-service monolith has no inter-service calls to trace. The detection pipeline is: API -> DetectionService -> GeolocationService -> CotService -> TAK push. All in-process. Structured logging with `detection_id` correlation provides equivalent debugging capability for a monolith.

**When to add**: When the system decomposes into microservices (Phase 2+ in architecture doc) or when cross-service TAK integration debugging becomes a bottleneck.

### 5.4 Alerting Strategy

**Tool**: Grafana Alerting (built into Grafana, no separate Alertmanager needed for MVP).

**Alert Rules**:

| Alert | Condition | Severity | Action |
|-------|-----------|----------|--------|
| HighErrorRate | detection error rate > 5% for 5 min | Critical | Page on-call |
| TAKPushFailure | tak_push_failure_total increasing > 10/min for 5 min | Critical | Page on-call |
| QueueDepthHigh | offline_queue_depth > 1000 for 10 min | Warning | Notify Slack |
| QueueDepthCritical | offline_queue_depth > 5000 for 5 min | Critical | Page on-call |
| PodRestart | kube_pod_container_status_restarts_total increasing | Warning | Notify Slack |
| HighLatency | p99 request duration > 2s for 5 min | Warning | Notify Slack |
| LowReplicas | available replicas < 2 for 2 min | Critical | Page on-call |

**Notification Channels**: Slack webhook (existing in CI/CD), PagerDuty/OpsGenie for critical alerts.

### 5.5 Grafana Dashboards

**Pre-built dashboards** (the crafter configures via Grafana JSON provisioning):

1. **Detection Pipeline**: Request rate, latency percentiles, error rate, confidence flag distribution
2. **TAK Integration**: Push success/failure rate, queue depth, sync rate
3. **Infrastructure**: CPU/memory usage, pod count, restart count, node health
4. **Audit Trail**: Events by type, error severity distribution, detection throughput over time

---

## 6. Security Architecture

### 6.1 Network Policies

**Issue with existing**: Default-deny policy blocks all egress including DNS. The `allow-tak-egress` policy only allows TAK server. Pods cannot resolve DNS, download health check dependencies, or reach the Kubernetes API.

**Revised Network Policies**:

```yaml
# 1. Default deny all (RETAIN)
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: detection-system
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress

# 2. Allow DNS resolution (NEW - CRITICAL)
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns-egress
  namespace: detection-system
spec:
  podSelector:
    matchLabels:
      app: detection-api
  policyTypes:
    - Egress
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53

# 3. Allow TAK server egress (RETAIN with namespace migration)
# 4. Allow ingress from NGINX (RETAIN with namespace migration)
# 5. Allow Prometheus scrape (RETAIN with namespace migration)
# 6. Allow Loki/Promtail egress (NEW)
```

### 6.2 Pod Security Standards

**Decision**: Enforce `restricted` Pod Security Standard via namespace labels.

The existing pod security context already complies:
- `runAsNonRoot: true`
- `runAsUser: 1000`
- `seccompProfile: RuntimeDefault`
- `capabilities.drop: [ALL]`
- `allowPrivilegeEscalation: false`

**One exception**: `readOnlyRootFilesystem: false` is required for SQLite writes. This is documented and accepted. The `restricted` PSS allows this when justified.

### 6.3 RBAC

**Existing RBAC is adequate**. Roles defined:
- `detection-api-sa`: Application service account (read ConfigMaps, Secrets, PVCs, Pods)
- `detection-api-deployer-sa`: CI/CD deployment (update Deployments, patch Services)
- `detection-api-operations`: DevOps troubleshooting (restart, port-forward, exec)
- `detection-api-readonly`: Engineering/support read-only access
- `prometheus-sa`: Cluster-wide metrics scraping

**Revision**: Migrate all to `detection-system` namespace.

### 6.4 Image Security

**Existing**: Trivy scan in CI/CD pipeline (`aquasecurity/trivy-action`).

**Additions**:
- **Image signing**: Cosign (Sigstore, Apache 2.0, free) signs images after build. Admission controller (Kyverno or Connaisseur) verifies signatures before deployment.
- **Base image pinning**: Use digest-pinned base images (`python:3.11-slim@sha256:...`) to prevent supply chain attacks.
- **Registry**: Private registry (`registry.internal`) already configured.

### 6.5 Audit Logging

**Kubernetes audit logging** complements application-level AuditTrailService:
- API server audit policy captures: Secret access, RBAC changes, pod exec, deployment updates
- Audit logs shipped to Loki via Promtail
- Operator audit viewer ClusterRole already exists in RBAC

---

## 7. Deployment Strategy

### 7.1 GitOps: ArgoCD

**Decision**: ArgoCD for GitOps-driven deployment.

**Alternatives Considered**:
- Flux v2: Equivalent capability, lighter footprint. Rejected -- ArgoCD has better UI for deployment visualization and rollback, which benefits operations teams unfamiliar with GitOps.
- Raw `kubectl apply` from CI/CD: Current approach. Rejected for production -- no drift detection, no automatic remediation, no audit trail of who deployed what.

**ArgoCD Application**:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: detection-api
  namespace: argocd
spec:
  project: detection-system
  source:
    repoURL: https://github.com/org/geolocation-engine2.git
    targetRevision: main
    path: kubernetes/manifests
  destination:
    server: https://kubernetes.default.svc
    namespace: detection-system
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

**Workflow**:
1. Developer merges PR to `main`
2. CI/CD builds image, pushes to registry with SHA tag
3. CI/CD updates image tag in `kubernetes/manifests/deployment.yaml`
4. ArgoCD detects Git change, syncs to cluster
5. Blue-green switch via service selector patch
6. ArgoCD self-heals any manual drift

### 7.2 CI/CD Integration

**Existing pipeline** (`.github/workflows/ci-cd-pipeline.yml`) covers:
1. Lint + Type Check + Unit Tests
2. Docker Build + Trivy Scan
3. Staging Deploy (green slot)
4. Integration + E2E Tests
5. Production Deploy (green slot)
6. Smoke Tests + Traffic Switch + 5-min Monitor + Rollback on Failure

**Enhancement for GitOps**: Replace direct `kubectl set image` with Git commit to manifests repo. ArgoCD handles the actual deployment.

### 7.3 Progressive Delivery

**Blue-green with manual gate** for production:

```
CI/CD: Build -> Test -> Push Image
              |
         Update manifest in Git (green slot image tag)
              |
ArgoCD: Sync green deployment
              |
CI/CD: Run smoke tests against green (direct pod access)
              |
         [PASS] -> Patch service selector to green (via Git commit)
              |
ArgoCD: Sync service -> traffic switches
              |
CI/CD: Monitor 5 min -> [PASS] -> Scale down blue
                      -> [FAIL] -> Revert service selector to blue (via Git revert)
```

### 7.4 Rollback Procedures

| Scenario | Action | Time to Recovery |
|----------|--------|-----------------|
| Bad deploy (caught in smoke tests) | Service selector stays on blue | 0 seconds (never switched) |
| Bad deploy (caught in 5-min monitor) | Git revert service selector, ArgoCD syncs | <60 seconds |
| Bad deploy (caught after full rollout) | `argocd app rollback detection-api` or Git revert | <120 seconds |
| Configuration error | Revert ConfigMap/Secret in Git, ArgoCD syncs | <60 seconds |
| Infrastructure failure | PDB maintains 2+ pods, HPA scales, pods reschedule | Automatic |

---

## 8. Storage Architecture

### 8.1 PersistentVolume Strategy

**Application Database (app.db)**: Contains detections and audit trail records. This is the primary persistence layer.

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: detection-data-pvc
  namespace: detection-system
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: fast-ssd
  resources:
    requests:
      storage: 50Gi
```

**Offline Queue (queue.db)**: Ephemeral resilience buffer. Use `emptyDir` per pod. Queue data is transient -- items are either synced to TAK or recovered on restart.

```yaml
volumes:
  - name: queue-storage
    emptyDir:
      sizeLimit: 5Gi
```

**Backup Volume**:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: detection-backup-pvc
  namespace: detection-system
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: standard  # Cheaper storage class for backups
  resources:
    requests:
      storage: 100Gi
```

### 8.2 Data Encryption at Rest

- **etcd encryption**: Enable `EncryptionConfiguration` for Secrets in etcd (cluster-level, not application-level)
- **Storage class encryption**: Use encrypted storage class (`encrypted-ssd`) if cloud provider supports it (AWS EBS encryption, GCP PD encryption)
- **SQLite**: No native encryption. If required, use SQLCipher (BSD license, free) -- this is a crafter implementation decision

---

## 9. Component Architecture Summary

```
                    Internet / Internal Network
                              |
                    [NGINX Ingress Controller]
                         TLS termination
                         Rate limiting
                              |
                    [detection-api-service]
                    ClusterIP, port 8000
                    selector: slot=green|blue
                              |
              +---------------+---------------+
              |                               |
    [detection-api-green]           [detection-api-blue]
    Deployment, 3-10 replicas       Deployment, 3 replicas (standby)
    HPA enabled                     Idle during green active
              |
    [init-queue-db container]
    Creates queue.db in emptyDir
              |
    [detection-api container]
    FastAPI on port 8000
    /health, /ready, /metrics
              |
    +----+----+----+----+
    |    |    |    |    |
   PVC  emptyDir CM  Secret
   app.db queue.db config tak-creds
              |
    [Prometheus] <-- scrapes /metrics
    [Promtail]  <-- scrapes stdout logs
    [Loki]      <-- stores logs
    [Grafana]   <-- dashboards + alerts
              |
    [ArgoCD]   <-- GitOps sync from Git
```

---

## 10. Technology Decisions Summary

| Component | Technology | License | Cost | ADR |
|-----------|-----------|---------|------|-----|
| Container Orchestration | Kubernetes 1.28+ | Apache 2.0 | Free | - |
| GitOps | ArgoCD 2.x | Apache 2.0 | Free | ADR-007 |
| Secret Encryption | Bitnami Sealed Secrets | Apache 2.0 | Free | ADR-008 |
| Metrics | Prometheus | Apache 2.0 | Free | ADR-009 |
| Logging | Grafana Loki + Promtail | AGPL 3.0 | Free | ADR-009 |
| Dashboards/Alerts | Grafana | AGPL 3.0 | Free | ADR-009 |
| Ingress Controller | NGINX Ingress | Apache 2.0 | Free | Existing |
| TLS Certificates | cert-manager + Let's Encrypt | Apache 2.0 | Free | Existing |
| Image Signing | Cosign (Sigstore) | Apache 2.0 | Free | ADR-008 |
| Image Scanning | Trivy | Apache 2.0 | Free | Existing |
| HPA Metrics | metrics-server | Apache 2.0 | Free | - |

**Total additional cost**: $0 (all open source)

---

## 11. Quality Gates

- [ ] All resources deployed to `detection-system` namespace (not `default`)
- [ ] Blue-green deployments use separate storage (no shared PVC conflict)
- [ ] HPA enabled and tested with load
- [ ] Network policies allow DNS, ingress, TAK egress, Prometheus scrape
- [ ] Sealed Secrets encrypts TAK credentials and JWT key
- [ ] Prometheus scrapes `/metrics` endpoint
- [ ] Loki aggregates structured JSON logs
- [ ] Grafana dashboards display pipeline metrics
- [ ] Alert rules configured for error rate, queue depth, latency, pod health
- [ ] ArgoCD syncs manifests from Git
- [ ] Topology spread constraints distribute pods across zones/nodes
- [ ] Pod Security Standards enforced at namespace level
- [ ] Backup CronJob runs daily
- [ ] Rollback tested and documented (<120s recovery time)
- [ ] Image signing and verification configured

---

## 12. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| SQLite write contention with multiple pods | MEDIUM | HIGH | Only one pod writes to app.db PVC (leader election or StatefulSet with 1 write replica). Queue uses emptyDir per pod. |
| ArgoCD single point of failure | LOW | MEDIUM | ArgoCD HA mode (3 replicas). Manual `kubectl` fallback documented. |
| Loki storage growth | LOW | MEDIUM | Log retention policy (14 days). Structured labels reduce index size. |
| Air-gapped deployment blocks external dependencies | MEDIUM | HIGH | All images pre-pulled to internal registry. Sealed Secrets controller bundled. No external API calls from infrastructure. |
| HPA flapping under variable load | LOW | LOW | 5-min scale-down stabilization window. Conservative thresholds (70% CPU). |

---

## 13. Handoff to Acceptance Designer

### Deliverables for DISTILL Wave

1. **This document** (`docs/architecture/phase05-kubernetes-production.md`)
2. **ADRs**: ADR-007, ADR-008, ADR-009 (in `docs/adrs/`)
3. **Revised manifests scope**: Namespace, Deployment (corrected PVC), HPA, Network Policies (DNS), Sealed Secrets, Observability stack
4. **Existing manifests to retain**: RBAC, Services/Ingress (namespace migration), PDB, LimitRange

### Acceptance Criteria for Phase 05 (Behavioral)

- Detection API remains available during deployment rollout
- Failed deployment automatically reverts to previous version
- Pod failure triggers automatic rescheduling without data loss
- Detection processing latency stays below 2 seconds under load
- TAK push failures queue locally and sync on recovery
- Unauthorized access to detection API returns 401
- Operator can view real-time pipeline metrics in dashboard
- Alert fires within 5 minutes of sustained error condition
- Daily backup completes and is verifiable
- All secrets are encrypted in Git repository
