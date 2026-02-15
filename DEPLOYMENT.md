# Deployment Guide

## Local Development

### Prerequisites
- Python 3.10+
- pip
- Docker (optional, for monitoring stack)

### Setup

```bash
# Clone and enter project
git clone <repo-url>
cd geolocation-engine2

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install with development dependencies
pip install -e ".[dev]"

# Run tests to verify
pytest tests/ -v
```

### Start the Application

```bash
# Minimal (no TAK, no monitoring)
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# With environment configuration
export TAK_SERVER_URL=http://localhost:8080/CoT
export JWT_SECRET_KEY=dev-secret-key-change-in-production
export DATABASE_URL=sqlite:///./data/app.db
export DEBUG=true

uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

### Verify

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Metrics endpoint
curl http://localhost:8000/metrics
```

---

## Docker Compose (Application + Monitoring)

### Start Everything

```bash
# Start monitoring stack
docker compose -f infrastructure/docker-compose.monitoring.yml up -d

# Start the application
docker build -t detection-to-cop .
docker run -p 8000:8000 \
  -e TAK_SERVER_URL=http://tak-server:8080/CoT \
  -e JWT_SECRET_KEY=your-secret-key \
  detection-to-cop
```

### Access Points

| Service | URL | Credentials |
|---------|-----|-------------|
| Detection API | http://localhost:8000 | JWT token or API key |
| API Docs (Swagger) | http://localhost:8000/docs | None |
| Prometheus | http://localhost:9090 | None |
| Grafana | http://localhost:3000 | admin / admin |
| Metrics | http://localhost:8000/metrics | None |

### Stop

```bash
docker compose -f infrastructure/docker-compose.monitoring.yml down
```

---

## Kubernetes Deployment

### Prerequisites
- Kubernetes cluster (1.28+)
- kubectl configured
- Helm 3.x installed
- ArgoCD installed (optional, for GitOps)

### Option A: Helm Chart

```bash
# Install the application
helm install detection-api kubernetes/helm-charts/ \
  --namespace detection-system \
  --create-namespace \
  --set image.tag=latest \
  --set config.takServerUrl=http://tak-server:8080/CoT \
  --set secrets.jwtSecretKey=your-production-secret

# Verify
kubectl get pods -n detection-system
kubectl get svc -n detection-system

# Check health
kubectl port-forward svc/detection-api-service -n detection-system 8000:8000
curl http://localhost:8000/api/v1/health
```

### Option B: Raw Manifests

```bash
# Create namespace
kubectl create namespace detection-system

# Apply manifests
kubectl apply -f kubernetes/manifests/ -n detection-system

# Verify
kubectl get all -n detection-system
```

### Option C: ArgoCD GitOps

```bash
# Create ArgoCD application
kubectl apply -f - <<EOF
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: detection-api
  namespace: argocd
spec:
  project: default
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
EOF

# Verify sync
argocd app get detection-api
```

### Deploy Monitoring Stack

```bash
# Add Helm repos
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# Install Prometheus
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  -f kubernetes/monitoring/prometheus/prometheus-values.yaml

# Install Loki
helm install loki grafana/loki-stack \
  --namespace monitoring \
  -f kubernetes/monitoring/loki/loki-values.yaml

# Apply alert rules
kubectl apply -f kubernetes/monitoring/prometheus/alerting-rules.yaml -n monitoring

# Apply Grafana dashboard
kubectl create configmap detection-dashboard \
  --from-file=kubernetes/monitoring/grafana/detection-api-dashboard.json \
  -n monitoring
```

---

## Terraform Infrastructure (AWS)

### Prerequisites
- Terraform 1.5+
- AWS CLI configured with appropriate permissions
- S3 bucket for Terraform state

### Deploy

```bash
cd infrastructure/terraform/environments/prod

# Initialize
terraform init

# Plan
terraform plan -out=tfplan

# Apply
terraform apply tfplan
```

### Environments

| Environment | Directory | Resources |
|-------------|-----------|-----------|
| Development | `environments/dev/` | Single-AZ, t3.medium, 1 replica |
| Staging | `environments/staging/` | Multi-AZ, t3.large, 2 replicas |
| Production | `environments/prod/` | Multi-AZ, t3.xlarge, 3-10 replicas |

### Modules

| Module | Creates |
|--------|---------|
| `modules/vpc/` | VPC, public/private subnets, NAT gateway |
| `modules/eks/` | EKS cluster, managed node groups, OIDC |
| `modules/rds/` | PostgreSQL RDS, subnet group, security group |
| `modules/s3/` | Backup bucket with lifecycle policies |
| `modules/iam/` | Roles for EKS, ArgoCD, application |

---

## Production Readiness Checklist

### Security
- [ ] JWT_SECRET_KEY is a strong random value (not the default)
- [ ] RS256 key pair generated for production JWT signing
- [ ] API keys created for all machine-to-machine integrations
- [ ] CORS origins restricted to known domains
- [ ] TLS enabled on ingress (cert-manager + Let's Encrypt)
- [ ] Sealed Secrets encrypting all credentials in Git
- [ ] Network policies applied (default deny, explicit allow)
- [ ] Pod Security Standards enforced (restricted)
- [ ] Image signing with Cosign configured
- [ ] Trivy scan passing with no CRITICAL vulnerabilities

### Monitoring
- [ ] Prometheus scraping /metrics endpoint
- [ ] Grafana dashboards loading (4 dashboards)
- [ ] Alert rules active (19 rules across 7 groups)
- [ ] Notification channels configured (Slack, PagerDuty)
- [ ] On-call rotation documented

### Reliability
- [ ] HPA configured (min 3, max 10 replicas)
- [ ] PDB set (minAvailable: 2)
- [ ] Topology spread across zones and nodes
- [ ] Backup CronJob running daily at 02:00 UTC
- [ ] Rollback procedure tested (< 120s recovery)
- [ ] Blue-green deployment validated

### Performance
- [ ] Load test passing (100+ req/s sustained)
- [ ] P95 latency < 300ms under load
- [ ] Error rate < 0.1% under load
- [ ] Cache hit rate > 60% for read endpoints
- [ ] Database indices optimized

### Documentation
- [ ] Deployment runbook reviewed by operations team
- [ ] Incident response procedures documented (SEV 1-4)
- [ ] Capacity planning thresholds documented
- [ ] Architecture Decision Records (ADRs) up to date
- [ ] API documentation accessible at /docs

---

## Rollback Procedures

### Automatic (during deployment)

Smoke test or monitoring failure triggers automatic revert:
1. CI/CD commits Git revert of service selector change
2. ArgoCD syncs revert within 3 minutes
3. Traffic returns to previous (blue) slot

### Manual (post-deployment)

**Option A: ArgoCD UI**
1. Open ArgoCD dashboard
2. Select `detection-api` application
3. Click History, find last known-good revision
4. Click Rollback

**Option B: Git Revert**
```bash
git revert <bad-commit-sha>
git push origin main
# ArgoCD auto-syncs within 3 minutes
```

**Option C: Emergency kubectl**
```bash
kubectl patch svc detection-api-service -n detection-system \
  -p '{"spec":{"selector":{"slot":"blue"}}}'
```

---

## Disaster Recovery

### Backup

Daily SQLite backup at 02:00 UTC via CronJob:
```bash
# Manual backup
kubectl exec -n detection-system deployment/detection-api-green -- \
  sqlite3 /app/data/app.db ".backup /backup/manual-backup.db"
```

### Restore

```bash
# Restore from backup
kubectl exec -n detection-system deployment/detection-api-green -- \
  cp /backup/app-20260215.db /app/data/app.db

# Restart pods to pick up restored database
kubectl rollout restart deployment/detection-api-green -n detection-system
```

### Recovery Time Objectives

| Scenario | RTO |
|----------|-----|
| Bad deployment | < 120 seconds |
| Pod failure | < 30 seconds (auto-restart) |
| Node failure | < 5 minutes (reschedule) |
| Database corruption | < 30 minutes (restore from backup) |
| Full cluster failure | < 2 hours (Terraform re-provision) |
