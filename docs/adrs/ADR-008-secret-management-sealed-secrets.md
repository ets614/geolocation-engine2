# ADR-008: Secret Management with Bitnami Sealed Secrets

## Status: Accepted

## Date: 2026-02-15

## Context

The current `kubernetes/manifests/services.yaml` contains plaintext secrets in `stringData`:

```yaml
stringData:
  username: "tak-operator"
  password: "encrypted-password-here"  # Use sealed-secrets or external-secrets in production
```

This is unacceptable for production. Secrets must be encrypted before storage in Git. Additionally, the JWT signing key (`your-secret-key-change-in-production` default in `src/config.py`) must be injected via Kubernetes Secret, not hardcoded.

The deployment environment may include air-gapped tactical networks (military/defense use case) where external secret stores (AWS Secrets Manager, HashiCorp Vault) are unavailable.

## Decision

Adopt Bitnami Sealed Secrets for encrypting Kubernetes Secrets at rest in the Git repository.

**Secrets to encrypt**:
- `tak-server-credentials` (username, password, endpoint)
- `jwt-signing-key` (secret_key for HS256 JWT signing)
- `registry-credentials` (.dockerconfigjson for private registry)

**Workflow**:
1. Generate secret locally: `kubectl create secret generic tak-server-credentials --dry-run=client -o yaml`
2. Encrypt with cluster public key: `kubeseal --format yaml < secret.yaml > sealed-secret.yaml`
3. Commit `sealed-secret.yaml` to Git (encrypted, safe)
4. Sealed Secrets controller decrypts to native Secret in-cluster
5. Pods reference secrets via `secretKeyRef` (no application changes)

**Image signing**: Cosign (Sigstore project) signs container images after build in CI/CD. A Kyverno admission policy verifies signatures before pod admission, preventing unsigned images from running.

## Alternatives Considered

### External Secrets Operator (ESO) with HashiCorp Vault
- **Pros**: Dynamic secret generation, automatic rotation, centralized secret management, rich audit trail
- **Cons**: Requires Vault infrastructure (server, unsealer, storage backend), network connectivity to Vault endpoint
- **Rejection reason**: Tactical deployments may be air-gapped with no external infrastructure. Vault adds significant operational complexity (unsealing, HA, backup) for a single-service deployment with 3 secrets.

### Mozilla SOPS
- **Pros**: Encrypts YAML files in-place, supports multiple KMS backends (AWS KMS, GCP KMS, PGP)
- **Cons**: No Kubernetes-native CRD, requires CI/CD integration to decrypt before apply, complex GitOps workflow with ArgoCD
- **Rejection reason**: ArgoCD integration requires SOPS plugin configuration. Sealed Secrets is natively Kubernetes-aware with CRD-based workflow that ArgoCD handles transparently.

### Kubernetes Native Secrets (base64 only)
- **Pros**: Simplest, no additional tools
- **Cons**: Secrets stored as base64 in etcd (not encrypted unless etcd EncryptionConfiguration is enabled cluster-wide), unsafe to store in Git
- **Rejection reason**: Cannot store secrets in Git repository. Breaks GitOps principle of Git as single source of truth.

## Consequences

### Positive
- Secrets encrypted in Git with asymmetric cryptography (cluster-specific public key)
- No external infrastructure dependencies (controller runs in-cluster)
- Works in air-gapped environments
- ArgoCD syncs SealedSecrets transparently (no special configuration)
- Existing `secretKeyRef` patterns in deployments unchanged

### Negative
- Sealed Secrets are cluster-scoped: encrypted secret from cluster A cannot be decrypted in cluster B (requires re-sealing per cluster)
- Manual rotation workflow (no automatic rotation)
- Controller is a single point of failure for secret decryption (mitigated by storing decrypted secrets in etcd; controller only needed for initial decryption)
- Public key must be distributed to developers for sealing (manageable for small team)

### Migration Path
- Phase 06: If Vault infrastructure becomes available, migrate to External Secrets Operator for automatic rotation
- The application layer is unaffected (reads secrets via environment variables regardless of secret management tool)
