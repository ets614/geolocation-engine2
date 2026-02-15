# ADR-P04-004: Secrets Management Approach

## Status

Accepted

## Date

2026-02-15

## Context

The Detection-to-CoP system manages sensitive credentials: JWT signing keys, API keys, database connection strings, and TAK Server URLs with potential credentials. The current implementation has critical gaps discovered during codebase analysis:

**Current gaps**:
1. `src/config.py` line 24: `jwt_secret_key` has hardcoded default `"your-secret-key-change-in-production"`
2. `src/services/jwt_service.py` line 20: same hardcoded default duplicated
3. No startup validation -- application starts successfully with insecure defaults
4. No separation between signing keys and verification keys
5. API keys for external sources referenced in config examples but no secure storage

**Secrets inventory**:

| Secret | Current Source | Risk Level |
|--------|---------------|------------|
| JWT signing key | Env var with hardcoded default | CRITICAL |
| Database URL | Env var with hardcoded default | MEDIUM |
| TAK Server URL | Env var with hardcoded default | LOW |
| External API keys (satellite, UAV) | Env vars referenced in docs | HIGH |

Three secrets management approaches were evaluated for the production path.

## Decision

We will implement a **tiered approach**:

1. **Immediate (Phase 04)**: Environment variables with mandatory startup validation. No defaults for security-critical values. Application fails to start if required secrets are missing.

2. **Production**: Kubernetes Secrets with encryption at rest, injected as environment variables or mounted files.

3. **Future (if needed)**: HashiCorp Vault for dynamic secrets (database credential rotation, short-lived certificates).

## Alternatives Considered

### Alternative 1: HashiCorp Vault from Day One

**How it works**: Deploy Vault server, configure secrets engines, application fetches secrets dynamically at startup and rotates them during runtime.

**Advantages**:
- Dynamic secret generation (database credentials auto-rotated)
- Audit trail for all secret access
- Fine-grained access control (policies per service)
- Encryption as a service (application can delegate encryption to Vault)
- Secret leasing with automatic revocation

**Disadvantages**:
- **Operational complexity**: Vault server requires HA deployment, unsealing, backup
- **Infrastructure dependency**: Application cannot start if Vault is down
- **Connectivity requirement**: Conflicts with offline-first architecture (field ops with intermittent connectivity)
- **Overkill for MVP**: Single-instance deployment with 5 secrets does not justify Vault infrastructure
- **Learning curve**: Team must learn Vault operations, policies, and troubleshooting
- **Cost**: While Vault OSS is free, operational overhead is significant (1-2 days setup, ongoing maintenance)

**Why Rejected for MVP**: The system has 5 secrets and runs as a single Docker container. Vault adds a critical infrastructure dependency that conflicts with the offline-first architecture (ADR-001). Field deployments with intermittent connectivity cannot reliably reach a Vault server. Environment variables with startup validation provides equivalent security for the current scale with zero operational overhead.

### Alternative 2: Encrypted Configuration File

**How it works**: Store secrets in an encrypted file (e.g., SOPS, age-encrypted YAML). Application decrypts at startup using a master key from environment.

**Advantages**:
- Secrets checked into version control (encrypted) -- disaster recovery
- Audit trail via git history (who changed what)
- Works offline (no external service dependency)
- Multiple secrets in one file (organized)

**Disadvantages**:
- **Master key problem**: Still need to deliver the decryption key securely (environment variable or K8s Secret)
- **Rotation complexity**: Changing a secret requires re-encrypting the file and redeploying
- **Git exposure risk**: Encrypted secrets in repo increase blast radius if master key leaks
- **Tooling dependency**: Requires SOPS, age, or similar tool in build/deploy pipeline
- **Complexity overhead**: Adds encryption/decryption step to deployment without proportional security benefit over K8s Secrets

**Why Rejected**: Encrypted config files solve the "secrets in version control" problem but introduce the "master key distribution" problem -- which is exactly what environment variables already solve. For a system with 5 secrets, the added encryption layer does not provide meaningful security improvement over Kubernetes Secrets with etcd encryption at rest, while adding tooling complexity.

### Alternative 3: Environment Variables with Startup Validation (Selected)

**How it works**: All secrets provided via environment variables (Docker env, K8s Secrets mounted as env vars). Application validates all required secrets exist at startup and fails fast if any are missing. No default values for security-critical secrets.

**Advantages**:
- **Zero infrastructure**: No additional services to deploy or manage
- **Offline compatible**: Secrets baked into container/deployment -- works without network
- **12-factor compliant**: Standard cloud-native pattern
- **K8s native**: Kubernetes Secrets inject as environment variables automatically
- **Simple rotation**: Update Secret + restart pod (rolling update = zero downtime)
- **Fail fast**: Missing secrets caught at startup, not at first request

**Disadvantages**:
- No dynamic rotation (requires pod restart)
- No fine-grained audit trail for secret access (mitigated by K8s audit logging)
- Environment variables visible in process listing (mitigated by K8s security context)
- No encryption at application layer (mitigated by K8s etcd encryption)

## Consequences

### Positive

- **Zero operational overhead**: No additional infrastructure for secrets management
- **Offline-first compatible**: Secrets available locally, no network dependency
- **Fail-fast behavior**: Application refuses to start with missing/default secrets
- **Clear upgrade path**: K8s Secrets --> Vault when scale justifies it
- **Standard pattern**: Every cloud platform supports environment variable injection

### Negative

- **Manual rotation**: Changing a secret requires deployment (acceptable for quarterly rotation)
- **No dynamic secrets**: Cannot auto-rotate database credentials (acceptable for MVP)
- **Process visibility**: Secrets visible in `/proc/<pid>/environ` (mitigated by container isolation)

### Mitigations

- Required secrets validated at startup (no silent insecure defaults)
- JWT uses RSA key files (path in env var, not key material in env var)
- Kubernetes Secrets with encryption at rest for staging/production
- Container security context: `readOnlyRootFilesystem`, non-root user
- Secret rotation documented in runbook with zero-downtime procedure

## Implementation Requirements

**Startup validation behavior**:
```
On application boot:
  1. Check JWT_PRIVATE_KEY_PATH exists and file is readable
  2. Check JWT_PUBLIC_KEY_PATH exists and file is readable
  3. Check DATABASE_URL is set (no default)
  4. Validate key format (PEM, RSA)
  5. If any check fails: log error with specific missing secret name, exit with code 1

NEVER:
  - Use hardcoded default for any secret
  - Log secret values
  - Start with insecure defaults in any environment
```

**Environment tiers**:

| Environment | Secrets Source | Encryption |
|-------------|---------------|------------|
| Development | `.env` file (gitignored) | None |
| CI/CD | GitHub Secrets injected as env vars | GitHub encryption |
| Staging | K8s Secrets | etcd encryption at rest |
| Production | K8s Secrets | etcd encryption at rest |

## Technology

| Component | Tool | License | Cost |
|-----------|------|---------|------|
| Env loading | python-dotenv 1.x | BSD | FREE |
| K8s Secrets | Kubernetes (built-in) | Apache 2.0 | FREE |
| Future Vault | HashiCorp Vault OSS | MPL 2.0 | FREE |

## References

- 12-Factor App: https://12factor.net/config
- Kubernetes Secrets: https://kubernetes.io/docs/concepts/configuration/secret/
- Current config: `src/config.py`, `src/services/jwt_service.py`
- Offline-first architecture: ADR-001 (secrets must be locally available)
