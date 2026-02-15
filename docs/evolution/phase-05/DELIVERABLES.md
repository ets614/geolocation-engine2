# Phase 05 Deliverables

## Deliverable 1: Kubernetes Architecture

**Design:** `docs/architecture/phase05-kubernetes-production.md`

- Dedicated `detection-system` namespace with Pod Security Standards (restricted)
- Blue-green deployment strategy with instant traffic switch
- Resource limits: 250m/512Mi requests, 1000m/1Gi limits per pod
- emptyDir for offline queue storage (per-pod, ephemeral)
- PersistentVolumeClaim for application database (50Gi SSD)
- Resource quotas scoped to namespace

**Helm Chart Templates:**
| Template | Resource |
|----------|----------|
| `deployment.yaml` | Blue-green deployments |
| `service.yaml` | ClusterIP service |
| `ingress.yaml` | NGINX Ingress with TLS |
| `configmap.yaml` | Application configuration |
| `pvc.yaml` | Persistent storage |
| `hpa.yaml` | Horizontal Pod Autoscaler |
| `networkpolicy.yaml` | Network access control |
| `pdb.yaml` | Pod Disruption Budget |
| `serviceaccount.yaml` | RBAC service account |
| `servicemonitor.yaml` | Prometheus ServiceMonitor |

---

## Deliverable 2: GitOps with ArgoCD

**Decision:** `docs/adrs/ADR-007-gitops-argocd.md`

- ArgoCD Application resource pointing to `kubernetes/manifests/`
- Auto-sync with prune and self-heal enabled
- Drift detection and automatic remediation
- Deployment flow: Git commit -> ArgoCD sync -> blue-green switch
- Rollback via Git revert (ArgoCD syncs automatically)

**Workflow:**
1. Developer merges PR to main
2. CI/CD builds image, pushes to registry with SHA tag
3. CI/CD updates image tag in manifests (Git commit)
4. ArgoCD detects change, syncs green deployment
5. Smoke tests pass -> service selector patched to green
6. 5-minute monitoring window -> success -> scale down blue

---

## Deliverable 3: Sealed Secrets

**Decision:** `docs/adrs/ADR-008-secret-management-sealed-secrets.md`

- Bitnami Sealed Secrets controller for in-cluster decryption
- SealedSecret CRDs encrypted with cluster public key
- Encrypted secrets safe to store in Git
- No external secret store dependency (air-gap compatible)

**Secrets Managed:**
| Secret | Keys |
|--------|------|
| `tak-server-credentials` | username, password, endpoint |
| `jwt-signing-key` | secret_key |
| `registry-credentials` | .dockerconfigjson |

**Rotation:** JWT key quarterly, TAK credentials per policy, registry annually

---

## Deliverable 4: Observability Stack

**Decision:** `docs/adrs/ADR-009-observability-prometheus-loki-grafana.md`

### Prometheus
- Scrapes `/metrics` endpoint on detection-api pods
- 19 alert rules across 7 groups
- RED metrics (Rate, Errors, Duration) + business metrics

### Loki
- Lightweight log aggregation (indexes labels, not content)
- Promtail DaemonSet scrapes pod stdout logs
- JSON fields extracted at query time via LogQL

### Grafana
- 4 pre-built dashboards:
  1. Detection Pipeline (request rate, latency, error rate, confidence)
  2. TAK Integration (push success/failure, queue depth, sync rate)
  3. Infrastructure (CPU/memory, pod count, restarts, node health)
  4. Audit Trail (events by type, severity, detection throughput)

### Alert Rules
| Group | Rules | Examples |
|-------|-------|---------|
| SLO | 3 | Error rate > 0.1%, P95 > 300ms, P99 > 500ms |
| Availability | 3 | Service down, too few instances, no requests |
| Authentication | 2 | High failure rate, brute force |
| Detection | 3 | Processing errors, slow processing, low confidence |
| TAK Server | 2 | Push failures, push latency |
| Offline Queue | 3 | Growing, critical, stale items |
| Cache | 1 | Low hit rate |

---

## Deliverable 5: Infrastructure as Code

### Terraform Modules

| Module | Resources Created |
|--------|-------------------|
| `vpc` | VPC, subnets (public/private), NAT gateway, route tables |
| `eks` | EKS cluster, node groups, OIDC provider |
| `rds` | PostgreSQL instance, subnet group, security group |
| `s3` | Backup bucket with lifecycle policies |
| `iam` | Roles for EKS nodes, ArgoCD, application |

### Environments
| Environment | Configuration |
|-------------|--------------|
| `dev` | Single-AZ, t3.medium nodes, 1 replica |
| `staging` | Multi-AZ, t3.large nodes, 2 replicas |
| `prod` | Multi-AZ, t3.xlarge nodes, 3-10 replicas (HPA) |

---

## Deliverable 6: Disaster Recovery

**Design:** `docs/architecture/phase05-ha-resilience.md`

### Backup Strategy
- Daily SQLite backup CronJob at 02:00 UTC
- 30-day retention with automated cleanup
- Separate backup PVC (100Gi standard storage)
- Backup verification via restore test

### Rollback Procedures
| Scenario | Action | Recovery Time |
|----------|--------|--------------|
| Bad deploy (smoke test fail) | Service stays on blue | 0 seconds |
| Bad deploy (monitoring fail) | Git revert selector | < 60 seconds |
| Bad deploy (post-rollout) | ArgoCD rollback | < 120 seconds |
| Configuration error | Git revert ConfigMap | < 60 seconds |
| Infrastructure failure | PDB + HPA + reschedule | Automatic |

### High Availability
- 99.9% uptime target (8.76 hours/year max downtime)
- PDB: minAvailable 2 (survives voluntary disruptions)
- HPA: 3-10 replicas (auto-scale on CPU/memory)
- Topology spread across zones and nodes
- Graceful shutdown with in-flight request completion

---

## Deliverable 7: Deployment Runbook

**Document:** `docs/architecture/phase05-deployment-strategy.md`

- 10-stage deployment pipeline (commit to production)
- Blue-green slot lifecycle documentation
- Automatic and manual rollback procedures
- Pre-deployment checklist (tests, scans, signing)
- Post-deployment verification matrix
- Incident response with SEV levels (1-4)
- Capacity planning thresholds and scaling actions
