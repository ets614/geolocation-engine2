# Phase 04: Security Architecture

**Project**: AI Detection to COP Translation System
**Phase**: 04 - Security & Performance Hardening
**Date**: 2026-02-15
**Status**: DESIGN WAVE - Ready for Review
**Author**: Alex Chen, Solution Architect

---

## 1. Overview

This document defines the security architecture for hardening the Detection-to-CoP system. It addresses authentication, authorization, input validation, secrets management, and transport security. It builds on existing components discovered during codebase analysis.

### Existing System Baseline

| Component | Current State | Gap |
|-----------|--------------|-----|
| JWT Auth | HS256 symmetric, hardcoded default secret | Upgrade to RS256, remove defaults |
| CORS | `allow_methods=["*"]`, `allow_headers=["*"]` | Restrict to required methods/headers |
| Rate Limiting | None | Add token bucket per-client |
| Input Validation | Pydantic field-level validation only | Add payload size limits, sanitization |
| Secrets | Env vars with fallback defaults | Remove defaults, add validation on startup |
| Security Headers | None | Add standard security headers |
| API Key Mgmt | None | Add rotating API keys with scoping |

### Threat Model Summary

**Attack Surface**: REST API (FastAPI on port 8000) accepting detection payloads with base64 image data, sensor metadata, and pixel coordinates.

**Primary Threats**:
1. Unauthorized access to detection ingestion endpoint
2. Denial of service via large payloads or request flooding
3. Credential compromise (JWT secret, API keys)
4. Data injection via malformed payloads
5. Man-in-the-middle on TAK Server communication

**Trust Boundaries**:
- External clients --> REST API (untrusted)
- REST API --> Core Domain Services (trusted, in-process)
- Core Domain --> TAK Server (semi-trusted, authenticated)
- Core Domain --> SQLite (trusted, local)

---

## 2. Authentication Architecture

### 2.1 JWT Authentication (Stateless)

**Current**: `src/services/jwt_service.py` uses HS256 with symmetric secret.

**Target**: RS256 asymmetric signing with proper key rotation.

| Attribute | Current | Target |
|-----------|---------|--------|
| Algorithm | HS256 (symmetric) | RS256 (asymmetric) |
| Secret management | Env var with hardcoded default | RSA key pair, no defaults |
| Token lifetime | 60 minutes | 15 min access / 7 day refresh |
| Claims | `sub`, `iat`, `exp` | Add `iss`, `aud`, `scope`, `jti` |
| Revocation | None | Token ID (`jti`) blocklist |

**Token Structure (Target)**:

```
Header: { "alg": "RS256", "typ": "JWT", "kid": "<key-id>" }
Payload: {
  "sub": "<client_id>",
  "iss": "detection-cop-api",
  "aud": "detection-cop",
  "iat": <unix_timestamp>,
  "exp": <unix_timestamp>,
  "jti": "<unique-token-id>",
  "scope": "detection:write detection:read"
}
```

**Key Management**:
- RSA 2048-bit key pair minimum
- Private key: signs tokens (server-side only)
- Public key: verifies tokens (can be distributed)
- Key rotation: generate new key pair, old key remains valid for verification until all tokens expire
- Key ID (`kid`): header identifies which public key to use for verification

**Refresh Token Flow**:
```
Client --> POST /api/v1/auth/token (credentials) --> Access Token (15 min) + Refresh Token (7 day)
Client --> POST /api/v1/auth/refresh (refresh_token) --> New Access Token (15 min)
Client --> POST /api/v1/auth/revoke (refresh_token) --> Token invalidated
```

**ADR Reference**: See ADR-P04-001 for JWT vs Session decision rationale.

### 2.2 API Key Authentication (Machine-to-Machine)

For automated systems (UAV feeds, camera integrations) that cannot perform interactive token exchange.

**API Key Properties**:
- Format: `geoeng_<environment>_<random_32_hex>` (e.g., `geoeng_prod_a3f8b2...`)
- Prefix enables quick identification and log filtering
- Scoped to specific operations (read, write, admin)
- Expiration: configurable, default 90 days
- Rate limit: per-key quota

**API Key Lifecycle**:
```
Admin --> POST /api/v1/admin/api-keys (name, scopes, expiry)
       --> { key: "geoeng_prod_...", key_id: "...", expires_at: "..." }

System stores: SHA256(key) + metadata (never stores plaintext key)
Client sends: X-API-Key: geoeng_prod_...
Server verifies: SHA256(received_key) matches stored hash
```

**Scope Definitions**:

| Scope | Allowed Operations |
|-------|-------------------|
| `detection:write` | POST /api/v1/detections |
| `detection:read` | GET /api/v1/detections/{id} |
| `audit:read` | GET /api/v1/audit/{detection_id} |
| `source:manage` | POST/PUT/GET /api/v1/sources |
| `admin` | All operations including key management |

**Authentication Priority** (checked in order):
1. `Authorization: Bearer <jwt_token>` header
2. `X-API-Key: <api_key>` header
3. Reject with 401

---

## 3. Rate Limiting Strategy

### 3.1 Algorithm: Token Bucket

**ADR Reference**: See ADR-P04-003 for algorithm selection rationale.

**Why Token Bucket**:
- Allows burst capacity (tactical operations may spike)
- Simple to implement and reason about
- Per-client fairness without global lock contention

**Configuration**:

| Client Type | Bucket Size (burst) | Refill Rate | Window |
|-------------|-------------------|-------------|--------|
| Authenticated (JWT) | 100 requests | 20 req/sec | Per client_id |
| API Key | 50 requests | 10 req/sec | Per key_id |
| Unauthenticated | 10 requests | 2 req/sec | Per IP |
| Health check | Unlimited | N/A | N/A |

**Implementation Pattern**:
- Rate limit state stored in-memory (single-instance MVP)
- Future: Redis-backed for multi-instance deployment
- Response headers on every request:
  - `X-RateLimit-Limit`: bucket size
  - `X-RateLimit-Remaining`: tokens remaining
  - `X-RateLimit-Reset`: seconds until bucket refill
- Exceeded: HTTP 429 with `Retry-After` header

**Endpoint-Specific Limits**:

| Endpoint | Additional Limit | Rationale |
|----------|-----------------|-----------|
| POST /api/v1/auth/token | 5 req/min per IP | Brute force prevention |
| POST /api/v1/detections | Standard per-client | Primary workload |
| GET /api/v1/health | No limit | Monitoring must not be rate-limited |

---

## 4. Input Validation Framework

### 4.1 Existing Validation (Pydantic)

The system already validates via `src/models/schemas.py`:
- Coordinate ranges (lat -90..90, lon -180..180)
- Confidence range (0..1)
- Base64 encoding validity
- Pixel bounds vs image dimensions
- ISO8601 timestamp format

### 4.2 Additional Validation Required

**Payload Size Limits**:

| Limit | Value | Rationale |
|-------|-------|-----------|
| Max request body | 10 MB | Base64 image data (~7.5 MB decoded) |
| Max image_base64 field | 8 MB | Largest reasonable detection image |
| Max JSON depth | 5 levels | Prevent nested object attacks |
| Max string field length | 1024 chars | Prevent memory exhaustion |

**String Sanitization Rules**:
- `object_class`: alphanumeric + underscore only, max 64 chars
- `source`: alphanumeric + underscore + hyphen, max 128 chars
- `camera_id`: alphanumeric + underscore + hyphen, max 128 chars
- Strip leading/trailing whitespace from all string fields
- Reject null bytes in any string field

**CoT XML Output Safety**:
- All user-supplied strings in CoT XML output must be XML-escaped
- Detection of XML injection patterns in input fields (`<`, `>`, `&`, CDATA sections)

### 4.3 Request Validation Pipeline

```
Request --> Size Check (reject >10MB)
        --> JSON Parse (reject malformed)
        --> Pydantic Validation (type, range, format)
        --> String Sanitization (strip, escape, length)
        --> Business Logic Validation (coordinate crosscheck, confidence normalization)
        --> Accept
```

---

## 5. Secrets Management

### 5.1 Current State (Gaps)

File `src/config.py` line 24-25:
```python
self.jwt_secret_key: str = os.getenv(
    "JWT_SECRET_KEY",
    "your-secret-key-change-in-production"  # CRITICAL: hardcoded default
)
```

File `src/services/jwt_service.py` line 18-21:
```python
self.secret_key = secret_key or os.getenv(
    "JWT_SECRET_KEY",
    "your-secret-key-change-in-production"  # CRITICAL: duplicate default
)
```

### 5.2 Target Architecture

**Principle**: No secret has a default value. Application fails to start if required secrets are missing.

**Environment Variable Requirements**:

| Variable | Required | Description |
|----------|----------|-------------|
| `JWT_PRIVATE_KEY_PATH` | Yes (if JWT enabled) | Path to RSA private key PEM file |
| `JWT_PUBLIC_KEY_PATH` | Yes (if JWT enabled) | Path to RSA public key PEM file |
| `DATABASE_URL` | Yes | Database connection string |
| `TAK_SERVER_URL` | No | TAK server endpoint (offline-first tolerates absence) |
| `API_KEY_ENCRYPTION_KEY` | Yes (if API keys enabled) | Key for encrypting API key hashes at rest |

**Startup Validation**:
- On boot, validate all required environment variables are set
- Validate key files exist and are readable
- Validate key format (PEM, correct algorithm)
- Fail fast with clear error message if any secret is missing

**Secret Rotation**:
- JWT keys: rotate quarterly, old public key retained for token lifetime
- API keys: individual expiry, admin-initiated rotation
- Database credentials: rotate on schedule via deployment pipeline

### 5.3 Vault Strategy (Production)

**MVP**: Environment variables injected via Docker/K8s secrets.

**Production Path**: HashiCorp Vault (open source, MPL 2.0 license) or Kubernetes Secrets with encryption at rest.

| Environment | Secrets Source | Encryption |
|-------------|---------------|------------|
| Development | `.env` file (gitignored) | None (local only) |
| Staging | K8s Secrets | etcd encryption at rest |
| Production | K8s Secrets or Vault | AES-256 encryption at rest |

---

## 6. CORS Policy and Security Headers

### 6.1 CORS Hardening

**Current** (`src/middleware.py`):
```python
allow_origins=config.cors_origins,   # ["http://localhost:3000", ...]
allow_methods=["*"],                 # TOO PERMISSIVE
allow_headers=["*"],                 # TOO PERMISSIVE
```

**Target**:

| Setting | Value | Rationale |
|---------|-------|-----------|
| `allow_origins` | Configurable via env var, default empty | Only explicitly trusted origins |
| `allow_methods` | `["GET", "POST", "PUT", "OPTIONS"]` | Only methods the API uses |
| `allow_headers` | `["Authorization", "Content-Type", "X-API-Key", "X-Request-ID"]` | Only headers the API expects |
| `allow_credentials` | `True` (only if origins are explicit) | Required for auth cookies if used |
| `max_age` | `600` (10 minutes) | Preflight cache duration |

### 6.2 Security Headers

All responses should include:

| Header | Value | Purpose |
|--------|-------|---------|
| `X-Content-Type-Options` | `nosniff` | Prevent MIME type sniffing |
| `X-Frame-Options` | `DENY` | Prevent clickjacking |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | Force HTTPS (production) |
| `X-XSS-Protection` | `0` | Disable (CSP is better) |
| `Content-Security-Policy` | `default-src 'none'` | API returns JSON/XML only |
| `Cache-Control` | `no-store` | Prevent caching of detection data |
| `X-Request-ID` | `<uuid>` | Request tracing correlation |

---

## 7. Transport Security

### 7.1 TLS Configuration

| Connection | TLS Required | Minimum Version | Certificate |
|------------|-------------|-----------------|-------------|
| Client --> API | Yes (production) | TLS 1.2 | Server cert via reverse proxy |
| API --> TAK Server | Yes | TLS 1.2 | Mutual TLS if TAK requires |
| API --> SQLite | N/A | N/A | Local filesystem |

**MVP**: TLS termination at reverse proxy (nginx/traefik) or cloud load balancer. Application serves HTTP internally.

**TAK Server Communication**:
- Existing `cot_service.py` uses aiohttp for TAK push
- Must verify TLS certificate of TAK Server (no `verify=False`)
- Support mutual TLS (client certificate) for TAK Server authentication if required by deployment

---

## 8. Audit Trail Security Integration

The existing `AuditTrailService` (41 tests passing) captures 10 event types. Security events to add:

| Event Type | Trigger | Severity |
|------------|---------|----------|
| `auth_success` | Successful JWT verification | INFO |
| `auth_failure` | Failed JWT verification (invalid, expired) | WARNING |
| `rate_limited` | Client exceeded rate limit | WARNING |
| `api_key_created` | New API key generated | INFO |
| `api_key_revoked` | API key revoked | INFO |
| `input_rejected` | Payload failed validation (size, sanitization) | WARNING |
| `suspicious_activity` | Repeated auth failures from same IP (>5 in 1 min) | ERROR |

These events flow through the existing audit trail pipeline (structured JSON logging + SQLite persistence).

---

## 9. Technology Selections

All security components use open source libraries:

| Component | Library | License | Cost |
|-----------|---------|---------|------|
| JWT (RS256) | PyJWT 2.x | MIT | FREE |
| Rate limiting | In-memory (stdlib) | N/A | FREE |
| Password/key hashing | hashlib (stdlib) | PSF | FREE |
| Input sanitization | Pydantic v2 + custom | MIT | FREE |
| TLS | Built into httpx/aiohttp | BSD/Apache | FREE |
| Secrets (future) | HashiCorp Vault OSS | MPL 2.0 | FREE |

**Total additional cost**: $0

---

## 10. Security Quality Attributes (ISO 25010)

| Attribute | Target | Measurement |
|-----------|--------|-------------|
| Confidentiality | All API endpoints require authentication | 0 unauthenticated access in audit log |
| Integrity | All inputs validated before processing | 100% of requests pass validation pipeline |
| Non-repudiation | All actions logged with client identity | Audit trail links every detection to authenticated client |
| Accountability | JWT `sub` or API key ID on every request | 100% of requests have identity attached |
| Authenticity | Token signature verified on every request | 0 accepted requests with invalid tokens |

---

## 11. Hexagonal Architecture Compliance

Security components map to the existing port/adapter pattern:

| Security Concern | Architecture Layer | Integration Point |
|-----------------|-------------------|-------------------|
| JWT Verification | Primary Port (REST API) | FastAPI dependency injection |
| API Key Verification | Primary Port (REST API) | FastAPI dependency injection |
| Rate Limiting | Adapter (REST API Adapter) | FastAPI middleware |
| Input Validation | Adapter (REST API Adapter) | Pydantic models + middleware |
| Security Headers | Adapter (REST API Adapter) | FastAPI middleware |
| Audit Logging | Domain Core | AuditTrailService (existing) |
| Secret Loading | Adapter (Configuration) | Config class startup |
| TLS | Adapter (TAK Integration) | httpx/aiohttp client config |

**Key principle**: Security is enforced at the adapter layer. Domain core services receive only validated, authenticated requests.

---

## 12. Implementation Roadmap (Steps for Crafter)

| Step | Title | Production Files | AC Count |
|------|-------|-----------------|----------|
| S1 | JWT upgrade to RS256 with key file loading | 3 | 4 |
| S2 | Startup secret validation (fail-fast) | 2 | 3 |
| S3 | Rate limiting middleware (token bucket) | 2 | 4 |
| S4 | Input validation hardening (size limits, sanitization) | 2 | 4 |
| S5 | Security headers middleware | 1 | 3 |
| S6 | CORS policy tightening | 1 | 3 |
| S7 | Security audit events integration | 2 | 3 |
| S8 | API key management (create, verify, revoke) | 3 | 5 |

**Steps/production-files ratio**: 8 steps / 16 files = 0.5 (well under 2.5 limit)

---

**Document Status**: COMPLETE - Ready for Peer Review
**Next**: Performance Architecture Document, then ADRs
