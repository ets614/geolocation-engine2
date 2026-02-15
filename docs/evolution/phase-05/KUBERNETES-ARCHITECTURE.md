# Phase 05 Kubernetes Architecture

## Component Architecture

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

## Namespace: detection-system

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

## Pod Resource Profile

```yaml
resources:
  requests:
    cpu: 250m
    memory: 512Mi
  limits:
    cpu: 1000m
    memory: 1Gi
```

**Rationale:** Application handles 100+ detections/second on a single core. Photogrammetry (numpy) completes in < 5ms. 250m/512Mi is sufficient for steady state.

## Horizontal Pod Autoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
spec:
  scaleTargetRef:
    kind: Deployment
    name: detection-api-green
  minReplicas: 3
  maxReplicas: 10
  metrics:
    - resource:
        name: cpu
        target:
          averageUtilization: 70
    - resource:
        name: memory
        target:
          averageUtilization: 75
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
    scaleUp:
      stabilizationWindowSeconds: 30
```

## Network Policies

1. **Default deny all** - Block all ingress/egress by default
2. **Allow DNS** - UDP/TCP port 53 to kube-system (critical for resolution)
3. **Allow TAK egress** - HTTP/HTTPS to TAK server
4. **Allow ingress** - From NGINX ingress controller
5. **Allow Prometheus scrape** - From monitoring namespace
6. **Allow Loki egress** - Log shipping

## Security Layers

```
Layer 1: Network         (Ingress TLS, Network Policies)
Layer 2: Authentication  (JWT tokens, API key)
Layer 3: Authorization   (RBAC, Namespace isolation)
Layer 4: Pod Security    (PSS restricted, non-root, drop capabilities)
Layer 5: Secret Mgmt     (Sealed Secrets, etcd encryption)
Layer 6: Supply Chain    (Image signing, scanning, base image pinning)
Layer 7: Audit           (K8s audit logs, application audit trail)
```

## Deployment Pipeline

```
[1] Commit Push
     |
[2] Lint + Type Check + Unit Tests + SAST + Dependency Scan
     |
[3] Docker Build + Trivy Scan + Cosign Sign
     |
[4] Update image tag in manifests (Git commit)
     |
[5] ArgoCD syncs green deployment
     |
[6] Smoke tests against green pods
     |
[7] Traffic switch: patch selector to green (Git commit)
     |
[8] ArgoCD syncs service selector
     |
[9] 5-minute monitoring (error rate, latency, queue depth)
     |
[10a] PASS: Scale down blue
[10b] FAIL: Revert selector to blue (Git revert)
```

## Technology Decisions

| Component | Technology | License | Cost | ADR |
|-----------|-----------|---------|------|-----|
| Orchestration | Kubernetes 1.28+ | Apache 2.0 | Free | - |
| GitOps | ArgoCD 2.x | Apache 2.0 | Free | ADR-007 |
| Secrets | Sealed Secrets | Apache 2.0 | Free | ADR-008 |
| Metrics | Prometheus | Apache 2.0 | Free | ADR-009 |
| Logging | Loki + Promtail | AGPL 3.0 | Free | ADR-009 |
| Dashboards | Grafana | AGPL 3.0 | Free | ADR-009 |
| Ingress | NGINX Ingress | Apache 2.0 | Free | Existing |
| TLS | cert-manager | Apache 2.0 | Free | Existing |
| Image Sign | Cosign (Sigstore) | Apache 2.0 | Free | ADR-008 |
| Image Scan | Trivy | Apache 2.0 | Free | Existing |
| IaC | Terraform | MPL 2.0 | Free | - |
| App Deploy | Helm 3.x | Apache 2.0 | Free | - |

**Total additional cost:** $0 (all open source)
