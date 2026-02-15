# ADR-P04-001: JWT vs Session-Based Authentication

## Status

Accepted

## Date

2026-02-15

## Context

The Detection-to-CoP system requires authentication for all API endpoints. The system currently has a basic JWT implementation (HS256 symmetric) in `src/services/jwt_service.py` and `src/api/auth.py`. Phase 04 hardens this. Two authentication approaches were evaluated.

**System characteristics influencing this decision**:
- Single-instance MVP deployment (Docker container)
- Stateless FastAPI async endpoints
- Machine-to-machine clients (UAVs, cameras, automated pipelines)
- Field operations with intermittent connectivity
- Future horizontal scaling path (multiple API instances behind load balancer)

## Decision

We will use **JWT (JSON Web Tokens) with RS256 asymmetric signing**, upgrading from the current HS256 implementation.

**Token Architecture**:
- Access tokens: RS256 signed, 15-minute lifetime, stateless verification
- Refresh tokens: opaque, 7-day lifetime, stored server-side
- API keys: SHA256 hashed at rest, for machine-to-machine auth

## Alternatives Considered

### Alternative 1: Server-Side Sessions (Cookie-Based)

**How it works**: Server stores session state in database/memory. Client receives session ID in cookie. Every request sends cookie; server looks up session.

**Advantages**:
- Simple revocation (delete session record)
- No token replay risk (session tied to server state)
- Smaller request overhead (cookie vs JWT header)

**Disadvantages**:
- **Stateful**: Every request requires session lookup (database or cache query)
- **Horizontal scaling**: Requires shared session store (Redis/database) across instances
- **M2M unsuitable**: Automated clients (UAVs, cameras) do not support cookie-based auth naturally
- **Connectivity**: Session persistence problematic during intermittent connectivity (field ops)
- **Performance**: Session lookup adds 1-5ms per request to every endpoint

**Why Rejected**: Session-based auth is fundamentally stateful. The system is designed for horizontal scaling (Phase 2 Kubernetes deployment) and serves machine-to-machine clients. Adding a shared session store increases operational complexity and adds a single point of failure. JWT's stateless verification is a better fit.

### Alternative 2: JWT with HS256 (Current Implementation)

**How it works**: Symmetric secret shared between issuer and verifier. Same key signs and verifies.

**Advantages**:
- Already implemented (zero development cost)
- Simpler key management (one secret)
- Faster signing/verification than RS256

**Disadvantages**:
- **Shared secret risk**: Any service that verifies tokens can also forge them
- **Key rotation complexity**: Changing the secret invalidates ALL outstanding tokens instantly
- **Microservice readiness**: If services are extracted (Phase 2), each service needing verification also has the signing key
- **Current security gap**: Hardcoded default secret (`"your-secret-key-change-in-production"`)

**Why Rejected**: HS256 is acceptable for single-service MVPs but becomes a liability when the system evolves. The shared secret problem means every verifier is also a potential issuer. RS256 separates signing (private key, API server only) from verification (public key, any service), which is correct security posture for production and for future multi-service architecture.

## Consequences

### Positive

- **Stateless verification**: No database lookup per request; token is self-contained
- **Horizontal scaling**: Any API instance can verify tokens with the public key
- **M2M compatible**: Token exchange works naturally for automated clients
- **Key separation**: Only the API server holds the private signing key
- **Future-proof**: Works unchanged when extracting microservices (Phase 2)

### Negative

- **Token revocation**: Cannot instantly revoke an access token (mitigated by 15-min lifetime)
- **Key management**: RSA key pair generation and rotation is more complex than symmetric secret
- **Token size**: RS256 tokens are larger (~800 bytes vs ~300 bytes for HS256)
- **CPU cost**: RS256 verification is ~10x slower than HS256 (~0.5ms vs ~0.05ms per verification); still negligible vs network I/O

### Mitigations

- Short access token lifetime (15 min) limits revocation window
- Refresh token stored server-side enables true revocation
- Token ID (`jti`) blocklist for emergency revocation of specific tokens
- Key rotation with `kid` header allows graceful key transitions

## References

- RFC 7519 (JWT)
- RFC 7518 (JWA - RS256 specification)
- Existing implementation: `src/services/jwt_service.py`, `src/api/auth.py`
