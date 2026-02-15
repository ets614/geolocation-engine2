# Phase 05: Security Architecture

**Date**: 2026-02-15
**Author**: Alex Chen, Solution Architect

---

## 1. Security Layers

```
Layer 1: Network (Ingress TLS, Network Policies)
Layer 2: Authentication (JWT tokens, API key)
Layer 3: Authorization (RBAC, Namespace isolation)
Layer 4: Pod Security (PSS restricted, non-root, drop capabilities)
Layer 5: Secret Management (Sealed Secrets, etcd encryption)
Layer 6: Supply Chain (Image signing, scanning, base image pinning)
Layer 7: Audit (K8s audit logs, application audit trail)
```

---

## 2. Network Security

### 2.1 TLS Termination

- **Ingress**: NGINX Ingress with cert-manager and Let's Encrypt (existing)
- **Enforcement**: `force-ssl-redirect: true` on Ingress (existing)
- **Internal**: Pod-to-pod communication is plaintext within cluster (acceptable for single-namespace deployment; service mesh in Phase 06 if cross-namespace encryption needed)

### 2.2 Network Policies

**Default deny all** (existing) with explicit allow rules:

| Rule | Direction | From/To | Port | Purpose |
|------|-----------|---------|------|---------|
| `allow-api-ingress` | Ingress | ingress-nginx namespace | TCP/8000 | External API access |
| `allow-prometheus-scrape` | Ingress | monitoring namespace | TCP/8000 | Metrics collection |
| `allow-dns-egress` | Egress | kube-system namespace | UDP+TCP/53 | DNS resolution (NEW) |
| `allow-tak-egress` | Egress | tak-server pods | TCP/8089 | TAK CoT push |
| `allow-loki-egress` | Egress | monitoring namespace | TCP/3100 | Log shipping (NEW) |

**Critical fix**: DNS egress was missing from existing network policies. Without it, pods cannot resolve any hostname, including the TAK server endpoint and Kubernetes API.

### 2.3 Rate Limiting

- **NGINX Ingress**: `limit-rps: 100` (100 requests/second per client IP)
- **Application**: JWT-authenticated endpoints have per-client rate limits
- **Protection**: Prevents DoS and brute-force attacks on detection endpoint

---

## 3. Authentication and Authorization

### 3.1 API Authentication

**JWT-based** (existing, Phase 04):
- Clients obtain JWT token via `POST /api/v1/auth/token` with client_id
- Token included in `Authorization: Bearer <token>` header
- Token validated by `verify_jwt_token` dependency on protected endpoints
- Token expiration: 60 minutes (configurable)

**Production hardening**:
- JWT signing key injected via Kubernetes Secret (not hardcoded default)
- Token rotation: Clients request new token before expiration
- Rate limit on token endpoint: 10 requests/minute per IP

### 3.2 RBAC Roles

| Role | Scope | Subjects | Permissions |
|------|-------|----------|-------------|
| `detection-api-sa` | Namespace | Application pods | Read ConfigMaps, Secrets, PVCs |
| `detection-api-deployer-sa` | Namespace | CI/CD pipeline | Update Deployments, patch Services |
| `detection-api-operations` | Namespace | DevOps, SRE teams | Restart, port-forward, exec |
| `detection-api-readonly` | Namespace | Engineering, support | Read-only pods, logs, config |
| `prometheus-sa` | Cluster | Prometheus | Read nodes, pods, services, endpoints |
| `operator-audit-viewer` | Cluster | Operators | Read audit events |

**Principle of least privilege**: Each role has minimal permissions for its function. No role has cluster-admin access.

---

## 4. Pod Security

### 4.1 Pod Security Standards (PSS)

**Enforcement level**: `restricted` (strictest) via namespace labels:

```yaml
labels:
  pod-security.kubernetes.io/enforce: restricted
  pod-security.kubernetes.io/audit: restricted
  pod-security.kubernetes.io/warn: restricted
```

**Compliance**:
- `runAsNonRoot: true` -- pods run as user 1000
- `seccompProfile: RuntimeDefault` -- syscall filtering enabled
- `capabilities.drop: [ALL]` -- no Linux capabilities
- `allowPrivilegeEscalation: false` -- cannot gain privileges
- `readOnlyRootFilesystem: false` -- EXCEPTION: required for SQLite writes to `/app/data`

### 4.2 Container Security Context

```yaml
securityContext:
  allowPrivilegeEscalation: false
  capabilities:
    drop: [ALL]
  readOnlyRootFilesystem: false  # Required for SQLite
  runAsNonRoot: true
  runAsUser: 1000
  seccompProfile:
    type: RuntimeDefault
```

---

## 5. Supply Chain Security

### 5.1 Image Scanning

**Trivy** (existing in CI/CD):
- Scans for CRITICAL and HIGH vulnerabilities
- Blocks deployment if CRITICAL found
- Results uploaded as SARIF to GitHub Code Scanning

### 5.2 Image Signing

**Cosign** (NEW):
- Signs image after successful build + scan in CI/CD
- Signature stored alongside image in registry
- Kyverno admission policy verifies signature before pod admission

```yaml
# Kyverno ClusterPolicy (enforces signed images)
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: verify-image-signatures
spec:
  validationFailureAction: Enforce
  rules:
    - name: verify-detection-api
      match:
        resources:
          kinds: [Pod]
          namespaces: [detection-system]
      verifyImages:
        - imageReferences: ["registry.internal/detection-api:*"]
          attestors:
            - entries:
                - keys:
                    publicKeys: |-
                      -----BEGIN PUBLIC KEY-----
                      <cosign-public-key>
                      -----END PUBLIC KEY-----
```

### 5.3 Base Image Pinning

- Use digest-pinned base images: `python:3.11-slim@sha256:<digest>`
- Prevents tag mutation attacks where `python:3.11-slim` resolves to a different image
- Digest updated quarterly or when security patches released

### 5.4 Dependency Scanning

- **Bandit** (SAST): Scans Python source for security issues (existing)
- **Safety**: Scans Python dependencies for known vulnerabilities (existing)
- **Trivy**: Scans OS packages in Docker image (existing)

---

## 6. Secret Management

See ADR-008 for detailed decision record.

**Summary**:
- Bitnami Sealed Secrets encrypts secrets in Git
- etcd EncryptionConfiguration encrypts secrets at rest in cluster
- No hardcoded secrets in application code or container images
- JWT signing key, TAK credentials, registry credentials stored as Sealed Secrets

---

## 7. Audit Logging

### 7.1 Application Audit Trail

**Existing** (AuditTrailService, 41 tests):
- 10 event types covering full detection lifecycle
- Immutable append-only events in SQLite
- Queryable by detection_id and date range
- JSON structured logging to stdout

### 7.2 Kubernetes Audit Logging

**API Server Audit Policy** captures:
- Secret reads/writes
- RBAC changes
- Pod exec commands
- Deployment updates
- Service patches (blue-green switches)

**Audit logs shipped to Loki** via Promtail for unified log query interface.

### 7.3 Audit Retention

| Log Type | Retention | Storage |
|----------|-----------|---------|
| Application audit trail | 90 days minimum | SQLite (app.db) |
| Application logs (Loki) | 14 days | Loki PVC |
| K8s audit logs (Loki) | 14 days | Loki PVC |
| Database backups | 30 days | Backup PVC |

---

## 8. Security Checklist

- [ ] TLS enforced on all external endpoints
- [ ] JWT authentication on all API endpoints (except health/ready)
- [ ] Network policies enforce default-deny with explicit allow rules
- [ ] DNS egress allowed for name resolution
- [ ] Pod Security Standards enforced at `restricted` level
- [ ] All containers run as non-root (UID 1000)
- [ ] All capabilities dropped
- [ ] Secrets encrypted in Git via Sealed Secrets
- [ ] Images scanned for vulnerabilities before deployment
- [ ] Images signed and signature verified on admission
- [ ] Base images pinned to digest
- [ ] RBAC roles follow least-privilege principle
- [ ] Audit logging captures security-relevant events
- [ ] No hardcoded secrets in source code or images
