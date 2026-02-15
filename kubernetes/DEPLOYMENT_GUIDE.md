# Kubernetes Deployment Guide - Phase 05
## Detection API - Production Ready Deployment

**Status:** Phase 05 - Production Ready Infrastructure
**Last Updated:** 2026-02-15
**Scope:** Kubernetes Deployment, Helm Charts, HPA, RBAC, Ingress, Storage

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Resource Configuration](#resource-configuration)
5. [Secrets Management](#secrets-management)
6. [Scaling Configuration](#scaling-configuration)
7. [Monitoring & Observability](#monitoring--observability)
8. [Deployment Strategies](#deployment-strategies)
9. [Rollback Procedures](#rollback-procedures)
10. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

### Component Stack

```
┌────────────────────────────────────────────────────────┐
│                 HTTPS Ingress (nginx)                  │
│     Rate Limiting | CORS | Security Headers            │
└────────────────┬─────────────────────────────────────┘
                 │
        ┌────────▼────────┐
        │   Service       │
        │   (ClusterIP)   │
        │   Port 8000     │
        └────────┬────────┘
                 │
    ┌────────────┴────────────┐
    ▼                         ▼
┌──────────────┐       ┌──────────────┐
│ Detection    │       │ Detection    │
│ API Blue     │       │ API Green    │
│ (3→10 pods)  │       │ (3→10 pods)  │
└──────┬───────┘       └──────┬───────┘
       │                      │
       └──────────┬───────────┘
                  │
        ┌─────────▼─────────┐
        │ HPA (2-10 pods)   │
        │ 70% CPU / 80% MEM │
        └───────────────────┘

Storage Layer:
├── SSD Queue (fast-ssd: 50Gi)
├── SSD Cache (fast-ssd: 10Gi)
└── Standard DB (standard-db: configurable)

Security Layer:
├── RBAC (minimal permissions)
├── Network Policies (deny-all default)
├── Pod Security Context (non-root: 1000)
├── Secrets (TAK creds, JWT keys, Discord webhooks)
└── TLS (cert-manager, letsencrypt-prod)
```

### Phase 05 Enhancements

| Component | Status | Details |
|-----------|--------|---------|
| **Deployment Manifest** | ✅ | Blue-green strategy, 3 replicas → HPA 2-10 |
| **Services** | ✅ | ClusterIP (internal), Headless (DNS) |
| **ConfigMap** | ✅ | Application config, detection thresholds |
| **Secrets** | ✅ | TAK creds, JWT keys, Discord webhooks, DB creds |
| **StorageClass** | ✅ | SSD (queue), Standard (DB), with encryption |
| **PersistentVolumes** | ✅ | 50Gi queue + 10Gi cache + configurable DB |
| **HPA** | ✅ | 2-10 pods, CPU/memory metrics + custom metrics |
| **Ingress** | ✅ | HTTPS, path-routing, rate limiting, CORS |
| **RBAC** | ✅ | Service accounts, roles, minimal permissions |
| **Resource Limits** | ✅ | Requests: 250m CPU / 256Mi MEM, Limits: 500m / 512Mi |
| **Health Checks** | ✅ | Liveness, readiness, startup probes |
| **Helm Chart** | ✅ | Templated, values-driven, production-ready |

---

## Prerequisites

### Kubernetes Cluster Requirements

```bash
# Minimum version: 1.24+
kubectl version --client

# Required API versions
kubectl api-versions | grep autoscaling
# Expected: autoscaling/v2

# Cluster info
kubectl cluster-info
kubectl get nodes -o wide
```

### Tools & Dependencies

```bash
# Helm 3.x
helm version

# kubectl configured with prod context
kubectl config current-context

# cert-manager (for HTTPS)
kubectl get crd | grep cert-manager

# nginx-ingress-controller
kubectl get deployment -n ingress-nginx
```

### Required Namespaces

```bash
# Create default namespace (if needed)
kubectl create namespace default --dry-run=client -o yaml | kubectl apply -f -

# Create monitoring namespace (for Prometheus)
kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -

# Create ingress-nginx namespace (if not exists)
kubectl create namespace ingress-nginx --dry-run=client -o yaml | kubectl apply -f -

# Label namespaces
kubectl label namespace ingress-nginx name=ingress-nginx
kubectl label namespace monitoring name=monitoring
```

### Storage Requirements

```bash
# Check available storage classes
kubectl get storageclass

# If AWS EBS provisioner needed:
kubectl get deployment -n kube-system | grep ebs

# Expected output: ebs-csi-controller
```

---

## Quick Start

### 1. Deploy with Helm (Recommended)

```bash
# Add Helm chart repository (if applicable)
helm repo add detection-api https://charts.example.com
helm repo update

# Install chart
helm install detection-api ./kubernetes/helm-charts \
  --namespace default \
  --create-namespace \
  --values ./kubernetes/helm-charts/values.yaml

# Verify deployment
helm status detection-api
helm get values detection-api
```

### 2. Deploy with kubectl (Direct Manifests)

```bash
# Create namespace
kubectl create namespace default

# Apply manifests in order
kubectl apply -f kubernetes/manifests/storage.yaml
kubectl apply -f kubernetes/manifests/secrets.yaml
kubectl apply -f kubernetes/manifests/rbac.yaml
kubectl apply -f kubernetes/manifests/deployment.yaml
kubectl apply -f kubernetes/manifests/services.yaml
kubectl apply -f kubernetes/manifests/hpa.yaml
kubectl apply -f kubernetes/manifests/ingress.yaml

# Verify
kubectl get all -n default
kubectl get pvc -n default
kubectl get secret -n default
```

### 3. Verify Deployment

```bash
# Check pod status
kubectl get pods -n default -w

# Check deployment rollout
kubectl rollout status deployment/detection-api-blue
kubectl rollout status deployment/detection-api-green

# Check service endpoints
kubectl get endpoints -n default

# Check HPA status
kubectl get hpa -n default

# Check ingress
kubectl get ingress -n default
```

---

## Resource Configuration

### CPU & Memory Limits

**Phase 05 Optimizations:**

| Resource | Request | Limit | Reason |
|----------|---------|-------|--------|
| **CPU** | 250m | 500m | Efficient for geolocation processing |
| **Memory** | 256Mi | 512Mi | Optimized for SQLite queue + CoT generation |

```yaml
resources:
  requests:
    cpu: 250m          # Reserve 250 millicores per pod
    memory: 256Mi      # Reserve 256 MiB per pod
  limits:
    cpu: 500m          # Max burst to 500 millicores
    memory: 512Mi      # Max burst to 512 MiB
```

### Scaling Calculations

**With 10 nodes × 4 cores each:**
- Total CPU: 40 cores = 40,000 millicores
- Reserved per pod: 250m
- Max pods: 40,000 / 250 = 160 pods (theoretical)

**With HPA 2-10 pods:**
- Min memory: 2 × 256Mi = 512Mi
- Max memory: 10 × 512Mi = 5.12Gi
- Min CPU: 2 × 250m = 500m
- Max CPU: 10 × 500m = 5 cores

---

## Secrets Management

### Secret Types

#### 1. TAK Server Credentials
```bash
kubectl create secret generic tak-server-credentials \
  --from-literal=endpoint=https://tak-server.internal:8089 \
  --from-literal=username=detection-api-service \
  --from-literal=password=<change-me> \
  --from-file=ca_cert=./certs/tak-ca.crt \
  --from-file=client_cert=./certs/client.crt \
  --from-file=client_key=./certs/client.key \
  --namespace=default
```

#### 2. Database Credentials
```bash
kubectl create secret generic db-credentials \
  --from-literal=database_url=postgresql://user:pass@db.internal:5432/api \
  --from-literal=db_username=detection_user \
  --from-literal=db_password=<change-me> \
  --namespace=default
```

#### 3. JWT Keys
```bash
# Generate new JWT secret
SECRET=$(openssl rand -base64 32)

kubectl create secret generic jwt-keys \
  --from-literal=jwt_secret_key=$SECRET \
  --from-literal=jwt_algorithm=HS256 \
  --from-literal=jwt_expiration=3600 \
  --namespace=default
```

#### 4. Discord Webhook
```bash
kubectl create secret generic discord-webhook \
  --from-literal=webhook_url=https://discord.com/api/webhooks/XXX/YYY \
  --namespace=default
```

### Secret Rotation Strategy

```bash
# 1. Create new secret with "_v2" suffix
kubectl create secret generic jwt-keys-v2 \
  --from-literal=jwt_secret_key=$NEW_SECRET \
  --namespace=default

# 2. Update deployment to reference new secret
kubectl patch deployment detection-api-blue \
  -p '{"spec":{"template":{"spec":{"containers":[{"name":"detection-api","env":[{"name":"JWT_SECRET_KEY","valueFrom":{"secretKeyRef":{"name":"jwt-keys-v2","key":"jwt_secret_key"}}}]}]}}}}'

# 3. Wait for rollout
kubectl rollout status deployment/detection-api-blue

# 4. Delete old secret
kubectl delete secret jwt-keys
```

### Production Secret Management

**Recommended:** Use one of:
- **Sealed Secrets** (open source)
- **External Secrets** (Vault integration)
- **AWS Secrets Manager** (via EKS)
- **HashiCorp Vault** (enterprise)

```bash
# Example: External Secrets Operator
kubectl apply -f https://github.com/external-secrets/external-secrets/releases/download/v0.9.0/external-secrets.yaml

# Create ExternalSecret
kubectl apply -f - <<EOF
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: detection-api-secrets
  namespace: default
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-backend
    kind: SecretStore
  target:
    name: detection-api-secrets
    creationPolicy: Owner
  data:
  - secretKey: jwt_secret_key
    remoteRef:
      key: secret/data/detection-api/jwt
      property: secret_key
EOF
```

---

## Scaling Configuration

### Horizontal Pod Autoscaler (HPA)

**Configuration:**

```yaml
minReplicas: 2        # Always 2 pods for HA
maxReplicas: 10       # Never exceed 10 pods
targetCPUUtilization: 70%   # Scale up at 70%
targetMemoryUtilization: 80%# Scale up at 80%
```

**Scaling Behavior:**

```bash
# View HPA status
kubectl get hpa detection-api-hpa -w

# View HPA events
kubectl describe hpa detection-api-hpa

# Check metrics (requires metrics-server)
kubectl top pods -n default
kubectl top nodes
```

**Manual Scaling:**

```bash
# Override HPA temporarily
kubectl scale deployment detection-api-blue --replicas=5

# Resume HPA
kubectl patch hpa detection-api-hpa -p '{"spec":{"minReplicas":2}}'
```

### Vertical Pod Autoscaler (VPA) - Optional

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: detection-api-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: detection-api-blue
  updatePolicy:
    updateMode: "Auto"  # Auto-apply recommendations
```

---

## Monitoring & Observability

### Metrics Collection

**Prometheus Scrape Configuration:**

```yaml
- job_name: 'detection-api'
  kubernetes_sd_configs:
    - role: pod
      namespaces:
        names:
          - default
  relabel_configs:
    - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
      action: keep
      regex: true
    - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
      action: replace
      target_label: __metrics_path__
      regex: ([^:]+)(?::\d+)?;(\d+)
      replacement: $1:$2
```

### Health Check Endpoints

```bash
# Liveness probe (is pod healthy?)
curl http://localhost:8000/health

# Readiness probe (can it serve requests?)
curl http://localhost:8000/ready

# Metrics endpoint (Prometheus)
curl http://localhost:8000/metrics
```

### Key Metrics to Monitor

```
detection_queue_depth        # Queue size (scale up if > 1000)
detection_api_request_duration_seconds
detection_api_requests_total
container_cpu_usage_seconds
container_memory_usage_bytes
pod_network_transmit_bytes
pod_network_receive_bytes
```

### Alerting Rules

```yaml
groups:
  - name: detection-api
    interval: 30s
    rules:
      - alert: HighCPUUsage
        expr: rate(container_cpu_usage_seconds_total[5m]) > 0.4
        for: 5m
        annotations:
          summary: "Pod {{ $labels.pod }} high CPU"

      - alert: HighMemoryUsage
        expr: container_memory_usage_bytes > 400000000
        for: 5m
        annotations:
          summary: "Pod {{ $labels.pod }} high memory"

      - alert: PodRestarts
        expr: rate(kube_pod_container_status_restarts_total[15m]) > 0
        annotations:
          summary: "Pod {{ $labels.pod }} restarting"
```

---

## Deployment Strategies

### 1. Blue-Green Deployment

**Current Setup:** Blue and Green deployments in same manifest

```bash
# Deploy to green slot
kubectl patch service detection-api-service \
  -p '{"spec":{"selector":{"slot":"green"}}}'

# Run smoke tests
kubectl run smoke-test --rm -it --image=curlimages/curl -- /bin/sh

# If tests pass, traffic already on green
# If tests fail, revert:
kubectl patch service detection-api-service \
  -p '{"spec":{"selector":{"slot":"blue"}}}'
```

**Steps:**
1. Deploy new version to inactive slot (blue OR green)
2. Run smoke tests against inactive slot
3. Update service selector to point to new slot
4. Monitor for errors
5. Keep old slot running for 10min (quick rollback)

### 2. Rolling Update (via Helm)

```bash
# Update values
vim kubernetes/helm-charts/values.yaml
# Change image.tag to new version

# Upgrade
helm upgrade detection-api ./kubernetes/helm-charts \
  --namespace default \
  --values ./kubernetes/helm-charts/values.yaml

# Monitor
helm status detection-api
kubectl rollout status deployment/detection-api-blue
```

### 3. Canary Deployment

```bash
# Install Flagger (for automated canary)
kubectl apply -k github.com/fluxcd/flagger//kustomize/istio

# Create canary resource
kubectl apply -f - <<EOF
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: detection-api-canary
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: detection-api-blue
  progressDeadlineSeconds: 300
  service:
    port: 8000
  analysis:
    interval: 30s
    threshold: 10
    maxWeight: 50
    stepWeight: 10
    metrics:
      - name: request-success-rate
        thresholdRange:
          min: 99
        interval: 1m
EOF
```

---

## Rollback Procedures

### Automatic Rollback (Deployment)

```bash
# If readiness probe fails repeatedly:
# - Kubernetes auto-stops rolling update
# - Keeps previous version running
# - Requires manual investigation

# Check rollout history
kubectl rollout history deployment/detection-api-blue

# Rollback to previous version
kubectl rollout undo deployment/detection-api-blue

# Rollback to specific revision
kubectl rollout undo deployment/detection-api-blue --to-revision=3
```

### Blue-Green Rollback

```bash
# If green slot has issues, switch back to blue
kubectl patch service detection-api-service \
  -p '{"spec":{"selector":{"slot":"blue"}}}'

# Keep green running for investigation
kubectl logs -f deployment/detection-api-green
```

### Helm Rollback

```bash
# View release history
helm history detection-api

# Rollback to previous release
helm rollback detection-api

# Rollback to specific revision
helm rollback detection-api 3
```

### Data Rollback

```bash
# If database migrations caused issues:
# 1. Check migration status
kubectl exec -it detection-api-blue-xxx -- /bin/bash
cd /app && alembic current

# 2. Downgrade database
alembic downgrade -1

# 3. Verify schema
alembic current
```

---

## Troubleshooting

### Pod Not Starting

```bash
# Check pod status
kubectl describe pod detection-api-blue-xxx

# Common issues:
# 1. ImagePullBackOff
kubectl get events -n default --sort-by='.lastTimestamp'

# 2. Insufficient resources
kubectl describe nodes

# 3. ConfigMap/Secret missing
kubectl get configmap -n default
kubectl get secret -n default
```

### High Memory Usage

```bash
# Check memory metrics
kubectl top pods -n default

# If consistently high:
# 1. Review SQLite queue size
kubectl exec -it detection-api-blue-xxx -- sqlite3 /app/data/queue.db "SELECT COUNT(*) FROM offline_queue;"

# 2. Increase memory limit in values.yaml
vim kubernetes/helm-charts/values.yaml
# Change memory.limits to 1Gi

# 3. Redeploy
helm upgrade detection-api ./kubernetes/helm-charts
```

### Connection Timeouts to TAK Server

```bash
# Test TAK server connectivity
kubectl exec -it detection-api-blue-xxx -- bash
curl -v https://tak-server.internal:8089

# Check network policies
kubectl get networkpolicy -n default
kubectl describe networkpolicy allow-tak-egress

# Verify credentials
kubectl get secret tak-server-credentials -o yaml
```

### Ingress Not Routing Traffic

```bash
# Check ingress status
kubectl get ingress -n default
kubectl describe ingress detection-api-ingress

# Verify service endpoints
kubectl get endpoints detection-api-service

# Check ingress controller
kubectl get deployment -n ingress-nginx
kubectl logs -f deployment/nginx-ingress-controller -n ingress-nginx
```

### HPA Not Scaling

```bash
# Check HPA status
kubectl describe hpa detection-api-hpa

# Metrics server required
kubectl get deployment -n kube-system | grep metrics-server

# If missing:
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Check metrics
kubectl get --raw /apis/metrics.k8s.io/v1/namespaces/default/pods
```

---

## Production Checklist

- [ ] Secrets rotated and stored securely (not in git)
- [ ] RBAC configured with minimal permissions
- [ ] Network policies enforced (deny-all default)
- [ ] Resource quotas and limits configured
- [ ] Monitoring and alerting active
- [ ] Backup strategy for persistent volumes
- [ ] Disaster recovery plan documented
- [ ] Load testing completed (> 1000 RPS)
- [ ] Chaos engineering tests passed
- [ ] Security scanning passed (SAST, DAST, SCA)
- [ ] Documentation updated
- [ ] Team trained on deployments/rollbacks

---

## References

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Helm Documentation](https://helm.sh/docs/)
- [Detection API Source Code](../../src/)
- [Architecture Documentation](../../docs/)

---

**Document Version:** 1.0.0
**Phase:** Phase 05 - Production Ready
**Last Updated:** 2026-02-15
