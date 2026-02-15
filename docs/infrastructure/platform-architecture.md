# Platform Architecture: On-Premise Kubernetes Cluster Design

**Date**: 2026-02-15
**Status**: DEVOP Wave (Production Readiness)
**Deployment Target**: On-Premise Kubernetes
**High Availability**: 3-Control Plane + 2+ Worker Nodes
**Feature**: AI Object Detection to COP Translation System

---

## Executive Summary

This document defines the complete on-premise Kubernetes cluster architecture for the AI Detection to COP Translation System. The design focuses on **zero-downtime deployments** (blue-green strategy), **enterprise-grade reliability** (99%+ SLO), and **security-hardened operations** (network policies, RBAC, secrets management).

**Key Design Principles**:
- High availability across 3+ control plane nodes
- Network isolation with microsegmentation (Network Policies)
- Immutable infrastructure (no manual patches)
- Observable operations (Prometheus + Grafana stack)
- Shift-left security (scanning every artifact)

---

## 1. Cluster Architecture Overview

### 1.1 Multi-Zone High Availability

```
┌──────────────────────────────────────────────────────────────────┐
│                  Kubernetes Cluster (On-Premise)                 │
├──────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              Control Plane (HA - 3 nodes)                    │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │ │
│  │  │ Master 1     │  │ Master 2     │  │ Master 3     │      │ │
│  │  │ (etcd, API)  │  │ (etcd, API)  │  │ (etcd, API)  │      │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘      │ │
│  │      CPU: 4        CPU: 4             CPU: 4                │ │
│  │      RAM: 8GB      RAM: 8GB           RAM: 8GB              │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              Worker Nodes (Minimum HA - 2 nodes)            │ │
│  │  ┌──────────────────────┐  ┌──────────────────────┐        │ │
│  │  │  Worker Node 1       │  │  Worker Node 2       │        │ │
│  │  │  (Detection Engine)  │  │  (Detection Engine)  │ ...   │ │
│  │  │                      │  │                      │ Scale  │ │
│  │  │  CPU: 8 cores        │  │  CPU: 8 cores        │ to 10  │ │
│  │  │  RAM: 32GB           │  │  RAM: 32GB           │        │ │
│  │  │  SSD: 500GB (queue)  │  │  SSD: 500GB (queue)  │        │ │
│  │  └──────────────────────┘  └──────────────────────┘        │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │         Cluster Add-ons (Monitoring & Networking)           │ │
│  │  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐ │ │
│  │  │ Prometheus     │  │ Grafana        │  │ Ingress      │ │ │
│  │  │ (Monitoring)   │  │ (Dashboards)   │  │ (nginx)      │ │ │
│  │  └────────────────┘  └────────────────┘  └──────────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                    │
└──────────────────────────────────────────────────────────────────┘
```

### 1.2 Namespace Isolation

| Namespace | Purpose | RBAC | Network Policy | Resource Quota |
|-----------|---------|------|-----------------|-----------------|
| `default` | Application (prod) | Restricted | Deny-all + allow | 50 CPU, 128GB RAM |
| `staging` | Pre-prod testing | Restricted | Deny-all + allow | 20 CPU, 64GB RAM |
| `monitoring` | Prometheus + Grafana | System | Allow all inbound | 10 CPU, 32GB RAM |
| `kube-system` | Kubernetes system | System | Allow all | Unlimited |

---

## 2. Node Pool Design

### 2.1 Control Plane Nodes (3x HA etcd cluster)

**Specifications**:
- **Count**: 3 nodes (provides quorum for HA)
- **CPU**: 4 cores per node
- **Memory**: 8GB per node
- **Storage**: 50GB SSD (etcd data)
- **Network**: 1Gbps NIC (cluster internal communication)

**etcd Configuration**:
```
--initial-cluster=master-1=https://10.0.0.1:2380,master-2=https://10.0.0.2:2380,master-3=https://10.0.0.3:2380
--initial-cluster-state=new
--initial-cluster-token=control-plane-token
```

**Rationale**:
- 3 nodes enable split-brain prevention (quorum = 2)
- Single node failure: cluster remains operational
- Two node failures: cluster loses quorum (manual recovery needed)
- Backup: Daily snapshots of etcd to persistent storage

### 2.2 Worker Nodes (2-10 nodes)

**Base Specifications** (per worker):
- **CPU**: 8 cores (geospatial processing CPU-intensive)
- **Memory**: 32GB (detection storage + buffer)
- **Storage**: 500GB SSD (local queue persistence)
- **Network**: 1Gbps+ (cluster communication)

**Scaling Strategy**:
- **Minimum**: 2 nodes (HA for stateless pods)
- **Target**: 4-6 nodes (production load)
- **Maximum**: 10 nodes (cluster capacity)
- **Autoscaler**: HPA + cluster autoscaler (Phase 2)

**Node Labeling** (pod affinity):
```yaml
node-type: worker
detection-engine: true
region: datacenter-1
capacity: high-compute
```

---

## 3. Storage Architecture

### 3.1 PersistentVolume Classes

#### Class 1: Fast (SSD, local, for queue)
```yaml
name: fast-ssd
provisioner: local-ssd
reclaimPolicy: Delete
allowVolumeExpansion: true
```

**Usage**:
- Offline detection queue (SQLite database)
- Cache for geolocation validation results
- Audit trail journals

**Capacity Planning**:
- Queue max size: 100,000 detections
- SQLite DB size: ~500MB per 10K detections
- Required SSD: 50GB per node

#### Class 2: Standard (NFS, for shared config)
```yaml
name: standard-nfs
provisioner: nfs
reclaimPolicy: Retain
allowVolumeExpansion: true
```

**Usage**:
- ConfigMaps backed by NFS (shared across pods)
- Secrets for TAK server credentials
- Application configuration files

#### Class 3: Archive (Slow, for backups)
```yaml
name: archive
provisioner: backup-provisioner
reclaimPolicy: Retain
```

**Usage**:
- Daily etcd backups
- Historical audit logs (90-day retention)
- Database snapshots

### 3.2 PersistentVolume Claim (PVC) Design

**Offline Queue PVC**:
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: detection-queue-pvc
  namespace: default
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: fast-ssd
  resources:
    requests:
      storage: 50Gi
```

**Lifecycle**:
- Created: During pod startup
- Mounted: `/app/data/queue.db`
- Persists: Across pod restarts
- Backed up: Daily to archive storage

---

## 4. Networking Architecture

### 4.1 Network Policies (Microsegmentation)

#### Default Deny Policy
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: default
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
```

**Rationale**: Zero-trust by default. Only allow explicit, documented traffic.

#### Allow Ingress to Detection API
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-api-ingress
  namespace: default
spec:
  podSelector:
    matchLabels:
      app: detection-api
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: ingress-nginx
      ports:
        - protocol: TCP
          port: 8000
```

#### Allow Detection API to TAK Server (Egress)
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-tak-egress
  namespace: default
spec:
  podSelector:
    matchLabels:
      app: detection-api
  policyTypes:
    - Egress
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: tak-server
      ports:
        - protocol: TCP
          port: 8089
```

### 4.2 Service Mesh (Phase 2)

**Decision**: Not required for MVP. Revisit when:
- Multi-namespace communication required
- Advanced traffic management (canary, traffic split)
- mTLS enforcement beyond simple TLS

**When to Implement** (Phase 2):
- Install Istio or Linkerd
- Enable automatic sidecar injection
- Define VirtualServices for traffic routing

### 4.3 Ingress Controller

**Controller**: nginx-ingress-controller
- Runs in `ingress-nginx` namespace
- Listens on port 80/443 (cluster entrypoint)
- Forwards traffic to internal services

**Ingress Resource**:
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: detection-api-ingress
  namespace: default
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - detection-api.internal.example.com
      secretName: api-tls-cert
  rules:
    - host: detection-api.internal.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: detection-api-service
                port:
                  number: 8000
```

---

## 5. RBAC Configuration

### 5.1 Service Accounts

#### Detection API Service Account
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: detection-api-sa
  namespace: default
```

**Permissions**:
- Read ConfigMaps (geolocation thresholds)
- Read Secrets (TAK server credentials)
- Access PersistentVolumes (queue storage)

#### Monitoring Service Account
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: prometheus-sa
  namespace: monitoring
```

**Permissions**:
- Read pod metrics
- Access all namespaces
- Scrape /metrics endpoints

### 5.2 Roles and RoleBindings

#### Detection API Role
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: detection-api-role
  namespace: default
rules:
  - apiGroups: [""]
    resources: ["configmaps", "secrets"]
    verbs: ["get", "list", "watch"]
  - apiGroups: [""]
    resources: ["persistentvolumes", "persistentvolumeclaims"]
    verbs: ["get", "list"]
```

#### Prometheus ClusterRole
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: prometheus-role
rules:
  - apiGroups: [""]
    resources:
      - nodes
      - nodes/proxy
      - services
      - endpoints
      - pods
    verbs: ["get", "list", "watch"]
  - apiGroups: ["extensions"]
    resources: ["ingresses"]
    verbs: ["get", "list", "watch"]
```

---

## 6. Resource Quotas and Limits

### 6.1 Namespace Resource Quota

#### Production Namespace
```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: production-quota
  namespace: default
spec:
  hard:
    requests.cpu: "50"
    requests.memory: "128Gi"
    limits.cpu: "100"
    limits.memory: "256Gi"
    pods: "100"
    services: "20"
    persistentvolumeclaims: "10"
```

### 6.2 Pod Resource Limits

#### Detection API Pod
```yaml
resources:
  requests:
    cpu: "2"
    memory: "4Gi"
  limits:
    cpu: "4"
    memory: "8Gi"
```

**Rationale**:
- **Request (reserved)**: Kubernetes allocates this at scheduling time
- **Limit (ceiling)**: Pod cannot exceed this; OOMKilled if exceeded
- Detection processing CPU-intensive but bounded
- Memory: Buffer for queue growth

---

## 7. Security Configuration

### 7.1 Pod Security Standards

**Policy**: Restricted (tight constraints)

```yaml
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: restricted-psp
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
  runAsUser:
    rule: "MustRunAsNonRoot"
  seLinux:
    rule: "MustRunAs"
  fsGroup:
    rule: "MustRunAs"
  readOnlyRootFilesystem: true
```

### 7.2 Secrets Management

**Kubernetes Secrets** (MVP):
- TAK server credentials stored in Kubernetes Secrets
- Encrypted at rest (etcd encryption enabled)
- Mounted as volumes (not environment variables)

**Example Secret**:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: tak-server-credentials
  namespace: default
type: Opaque
stringData:
  username: tak-operator
  password: encrypted-password
  endpoint: https://tak-server.internal:8089
```

**Phase 2**: Migrate to external secrets operator (HSM integration)

### 7.3 TLS/mTLS Communication

#### Pod-to-Pod TLS
- Detection API → TAK Server: mTLS
- Certificate distribution: Kubernetes Secret

#### Cluster-Wide mTLS (Phase 2)
- Istio sidecar proxies handle encryption
- Automatic certificate rotation
- Policy-based traffic encryption

---

## 8. High Availability Design

### 8.1 Control Plane Redundancy

| Component | Replicas | HA Strategy |
|-----------|----------|-------------|
| etcd | 3 | Raft consensus (majority quorum) |
| API Server | 3 | Independent, stateless |
| Controller Manager | 1 active + 2 standby | Leader election |
| Scheduler | 1 active + 2 standby | Leader election |

**Failure Scenarios**:
- **1 master down**: Cluster operational, reduced capacity
- **2 masters down**: Cluster loses control plane (manual recovery)
- **All masters down**: Cluster uncontrollable (disaster recovery procedure)

### 8.2 Application Pod Redundancy

**Detection API Deployment**:
```yaml
replicas: 3
podAntiAffinity: required
  topologyKey: kubernetes.io/hostname
```

**Ensures**:
- 3 pod instances always running
- Each pod on different worker node
- Single node failure: 2 pods remain operational
- Rolling updates: Zero downtime

### 8.3 Persistent Storage Redundancy

**Detection Queue (SQLite)**:
- Primary: Local SSD on worker node
- Backup: Daily snapshot to archive storage
- Recovery: Restore from snapshot on pod restart

**Configuration Data**:
- Primary: NFS (RAID-6 on storage array)
- Replica: Synchronous replication to second array

---

## 9. Disaster Recovery

### 9.1 RTO/RPO Targets

| Scenario | RTO | RPO |
|----------|-----|-----|
| Single node failure | <5 min (auto pod restart) | <1 min (PVC snapshot) |
| Control plane node failure | <15 min (auto recovery) | None (etcd HA) |
| Entire control plane loss | <1 hour (manual restore) | <15 min (etcd backup) |
| Datacenter failure | <4 hours (failover to DR site) | <15 min (continuous replication) |

### 9.2 etcd Backup Strategy

**Automation**:
```bash
*/6 * * * * /usr/local/bin/etcd-backup.sh
```

**Script**:
```bash
#!/bin/bash
BACKUP_DIR=/backups/etcd
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

ETCDCTL_API=3 etcdctl \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  snapshot save $BACKUP_DIR/etcd_$TIMESTAMP.db

# Keep last 30 backups
ls -t $BACKUP_DIR/etcd_*.db | tail -n +31 | xargs rm -f
```

**Retention**: 30 snapshots (approx 5 days of 6-hourly backups)

### 9.3 Recovery Procedure

**Restore from etcd Backup** (if control plane lost):

```bash
# On a new master node:
ETCDCTL_API=3 etcdctl \
  --data-dir=/var/lib/etcd \
  snapshot restore /backups/etcd/etcd_YYYYMMDD_HHMMSS.db
```

**Then**:
1. Start kubelet
2. Wait for control plane pods to restart
3. Verify all nodes healthy (`kubectl get nodes`)
4. Verify all pods running (`kubectl get pods -A`)

---

## 10. Cluster Initialization

### 10.1 Prerequisites

**Hardware**:
- 3x control plane nodes (4 CPU, 8GB RAM each)
- 2x worker nodes (8 CPU, 32GB RAM each)
- Network connectivity 1Gbps+
- NFS storage (100GB for shared config)

**Software**:
- CRI: containerd 1.7.x
- CNI: Calico 3.27.x (network policies)
- Kubernetes: 1.29.x

### 10.2 Initialization Steps

1. **Install CRI** (containerd):
```bash
curl https://get.docker.com | sh
```

2. **Join control plane**:
```bash
kubeadm init --control-plane-endpoint=10.0.0.1:6443 \
  --pod-network-cidr=10.244.0.0/16 \
  --service-cidr=10.96.0.0/12
```

3. **Install CNI** (Calico):
```bash
kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.27.0/manifests/tigera-operator.yaml
```

4. **Configure RBAC**:
```bash
kubectl apply -f rbac-config.yaml
```

5. **Deploy monitoring stack**:
```bash
helm install prometheus prometheus-community/kube-prometheus-stack -f values.yaml
```

---

## 11. Upgrade Strategy

### 11.1 Kubernetes Version Upgrade

**Process**:
1. Backup etcd (`etcd-backup.sh`)
2. Drain worker node
3. Upgrade kubeadm, kubelet on node
4. Uncordon node
5. Verify node healthy
6. Repeat for next node

**Example** (upgrade to 1.30.x):
```bash
# On each control plane:
apt-mark unhold kubeadm kubelet
apt-get update && apt-get install -y kubeadm=1.30.0-00 kubelet=1.30.0-00
kubeadm upgrade plan
kubeadm upgrade apply v1.30.0
systemctl daemon-reload && systemctl restart kubelet

# On each worker:
kubectl drain <node> --ignore-daemonsets --delete-emptydir-data
# ... kubeadm upgrade ...
kubectl uncordon <node>
```

### 11.2 Addon Upgrade (Prometheus, Ingress)

**Helm upgrade**:
```bash
helm repo update
helm upgrade prometheus prometheus-community/kube-prometheus-stack -f values.yaml
```

**Verification**:
```bash
kubectl rollout status deployment/prometheus-operator -n monitoring
```

---

## 12. Capacity Planning

### 12.1 Resource Utilization Targets

| Component | Target Usage |
|-----------|--------------|
| Control plane CPU | <40% under normal load |
| Control plane Memory | <50% under normal load |
| Worker node CPU | <70% under normal load |
| Worker node Memory | <75% under normal load |
| etcd disk | <80% capacity |

**Monitoring**: Prometheus alerts if usage exceeds 80% of target

### 12.2 Scaling Triggers

| Metric | Threshold | Action |
|--------|-----------|--------|
| Pod CPU requests > 80% cluster capacity | Scale up | Add worker node |
| Pod memory requests > 80% cluster capacity | Scale up | Add worker node |
| etcd disk > 8GB | Compact | Run `etcdctl compact` |
| Offline queue size > 50K detections | Alert | Manual intervention |

---

## 13. Compliance and Audit

### 13.1 Audit Logging

**Kubernetes Audit Policy**:
```yaml
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
  - level: RequestResponse
    resources: ["secrets", "configmaps"]
  - level: Metadata
    verbs: ["create", "update", "patch", "delete"]
  - level: Metadata
    omitStages: ["RequestReceived"]
```

**Audit Log Rotation**:
- File size: 100MB per file
- Retention: 90 days
- Destination: Persistent storage

### 13.2 RBAC Audit

**Audit Trail**:
- Every ServiceAccount action logged
- Role binding changes tracked
- Permission escalation detected

**Review Cadence**: Monthly RBAC review

---

## 14. Cost Analysis

### 14.1 Infrastructure Costs (On-Premise)

| Component | Qty | Unit Cost | Annual Cost |
|-----------|-----|-----------|-------------|
| Control plane server | 3 | $5,000 | $15,000 |
| Worker server | 6 | $8,000 | $48,000 |
| Storage array (NFS) | 1 | $20,000 | $20,000 |
| Network switch | 1 | $10,000 | $10,000 |
| Power/cooling (3 years) | - | - | $30,000 |
| **Total CapEx (3 years)** | - | - | **$123,000** |
| **Annual OpEx (staffing)** | - | - | **$250,000-300,000** |

### 14.2 Software Costs

**All open source**:
- Kubernetes: FREE (open source)
- Prometheus: FREE
- Grafana: FREE (open source edition)
- Docker/containerd: FREE

**Total software cost**: $0

---

## 15. Evolution Path

### Phase 2 Enhancements

1. **Service Mesh** (Istio): Advanced traffic management, security
2. **GitOps** (ArgoCD): Declarative deployment automation
3. **Secret rotation** (External Secrets Operator): HSM integration
4. **Horizontal autoscaling**: HPA + cluster autoscaler
5. **Multi-region**: Failover to secondary datacenter

### Phase 3 Optimization

1. **Performance tuning**: Node kernel parameters, etcd optimization
2. **Cost optimization**: Reserved compute, right-sizing
3. **Multi-tenancy**: Stronger isolation, chargeback models

---

## Summary

This platform architecture provides:

✅ **High Availability**: 3-control plane + 2-10 worker HA design
✅ **Zero-Downtime Deployments**: Blue-green strategy with automatic rollback
✅ **Enterprise Security**: RBAC, network policies, pod security
✅ **Observable Operations**: Prometheus + Grafana, structured logging
✅ **Disaster Recovery**: RTO <1 hour, RPO <15 minutes
✅ **Scalable Design**: Path to 10+ nodes without architecture change

**Status**: ✅ READY FOR IMPLEMENTATION

---

**Document Version**: 1.0
**Last Updated**: 2026-02-15
**Maintainer**: Platform Architecture Team
**Next Review**: 2026-05-15 (post-MVP deployment)
