# ADR-007: GitOps Deployment with ArgoCD

## Status: Accepted

## Date: 2026-02-15

## Context

The CI/CD pipeline (`.github/workflows/ci-cd-pipeline.yml`) currently deploys via direct `kubectl set image` and `kubectl patch` commands from GitHub Actions runners. This approach has several production concerns:

- No drift detection: Manual `kubectl` changes are not reconciled with Git state
- No audit trail of cluster state changes beyond CI/CD logs
- Rollback requires re-running pipelines or manual `kubectl` commands
- No self-healing: If a pod spec is manually modified, it stays modified
- Credentials for cluster access stored in GitHub Secrets (broad attack surface)

The system handles tactical detection data (military/defense, emergency services) where deployment reliability and auditability are non-negotiable.

## Decision

Adopt ArgoCD as the GitOps controller for production Kubernetes deployments. The Git repository (`kubernetes/manifests/`) becomes the single source of truth for cluster state. ArgoCD continuously reconciles cluster state with Git.

**Deployment Flow**:
1. CI/CD builds and pushes image, updates image tag in Git manifests
2. ArgoCD detects Git change, syncs to cluster
3. Blue-green traffic switch via service selector update in Git
4. ArgoCD self-heals any manual drift

## Alternatives Considered

### Flux v2
- **Pros**: Lighter footprint, native Kubernetes controller pattern, Helm controller built-in
- **Cons**: No built-in UI for deployment visualization, weaker rollback UX
- **Rejection reason**: Operations teams benefit from ArgoCD's visual deployment dashboard for understanding blue-green slot status and rollback history. The tactical deployment context requires clear visual confirmation of which slot is active.

### Direct kubectl from CI/CD (current approach)
- **Pros**: Simplest, no additional infrastructure
- **Cons**: No drift detection, no self-healing, no deployment state UI, rollback is manual
- **Rejection reason**: Insufficient for production workload handling tactical detection data. Manual drift in production could cause silent service degradation.

### Helm-only (no GitOps controller)
- **Pros**: Familiar, well-documented
- **Cons**: Helm releases are imperative (apply-and-forget), no continuous reconciliation
- **Rejection reason**: Same drift detection gap as direct kubectl

## Consequences

### Positive
- Single source of truth for cluster state in Git
- Automatic drift detection and self-healing (reconciliation every 3 minutes)
- Visual deployment dashboard for operations team
- One-click rollback to any previous Git commit
- Reduced blast radius: CI/CD only needs Git push access, not cluster admin
- Full audit trail via Git history

### Negative
- Additional infrastructure component to maintain (ArgoCD controller pods)
- Learning curve for operations team unfamiliar with GitOps patterns
- CI/CD pipeline must be refactored from direct kubectl to Git commit workflow
- ArgoCD itself becomes a dependency (mitigated by HA deployment and kubectl fallback)

### Operational
- ArgoCD deployed in HA mode (3 replicas) in dedicated `argocd` namespace
- Manual `kubectl` documented as emergency fallback procedure
- ArgoCD admin credentials stored as Sealed Secret
