# Phase 04 Deliverables

## Feature 1: JWT RS256 Authentication

**Service:** `src/services/jwt_service.py`
**Tests:** `tests/unit/test_jwt_service.py` (12 tests)

- Token generation with configurable expiry (15 min access / 7 day refresh)
- RS256 asymmetric signing support
- Token verification with expiry and issuer checks
- Refresh token flow (generate, validate, revoke)
- Claims: sub, iss, aud, iat, exp, jti, scope
- Token revocation via jti blocklist

**Endpoints:**
- `POST /api/v1/auth/token` - Generate access and refresh tokens
- `POST /api/v1/auth/refresh` - Refresh an expired access token
- `POST /api/v1/auth/revoke` - Revoke a refresh token

---

## Feature 2: API Key Management

**Service:** `src/services/api_key_service.py`
**Tests:** `tests/unit/test_api_key_service.py` (18 tests)

- Key generation with format: `geoeng_{env}_{random_32_hex}`
- SHA256 hashing (plaintext never stored)
- Scope-based access control (read:detections, write:detections, read:audit, admin)
- Key expiration with configurable TTL
- Key revocation and lifecycle management
- Rate limit quotas per key

**Endpoints:**
- `POST /api/v1/api-keys` - Create a new API key
- `GET /api/v1/api-keys` - List API keys (metadata only)
- `DELETE /api/v1/api-keys/{key_id}` - Revoke an API key

---

## Feature 3: Token Bucket Rate Limiting

**Service:** `src/services/rate_limiter_service.py`
**Tests:** `tests/unit/test_rate_limiter_service.py` (14 tests)

- Token bucket algorithm with configurable capacity and refill rate
- Per-client buckets (by JWT subject or API key ID)
- Per-IP fallback for unauthenticated requests
- Response headers: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
- HTTP 429 with Retry-After on exceeded limits
- Endpoint-specific overrides (5 req/min on auth endpoints)

**Configuration:**
| Client Type | Bucket Size | Refill Rate |
|-------------|-------------|-------------|
| Authenticated (JWT) | 100 | 20 req/s |
| API Key | 50 | 10 req/s |
| Unauthenticated | 10 | 2 req/s |
| Health check | Unlimited | N/A |

---

## Feature 4: Input Sanitization

**Service:** `src/services/input_sanitizer_service.py`
**Tests:** `tests/unit/test_input_sanitizer_service.py` (22 tests)

- SQL injection pattern detection and blocking
- XSS payload detection (`<script>`, event handlers, javascript: URIs)
- Path traversal prevention (`../`, `..\\`, encoded variants)
- Command injection blocking (`;`, `|`, backticks, `$()`)
- Null byte rejection in all string fields
- Payload size enforcement (10 MB request body, 8 MB base64 field)
- String field length limits (64-1024 chars by field)
- Whitespace stripping and normalization

---

## Feature 5: In-Memory Caching

**Service:** `src/services/cache_service.py`
**Tests:** `tests/unit/test_cache_service.py` (16 tests)

- TTL-based expiration per cache entry
- LFU (Least Frequently Used) eviction when capacity reached
- Configurable max entries (default 10,000) and max memory (~50 MB)
- Cache key pattern: `{resource}:{identifier}:{version}`
- Cache warming support for static lookups
- Thread-safe operations
- Cache statistics (hit rate, miss rate, eviction count)

**Cache Targets:**
| Data | TTL | Cached? |
|------|-----|---------|
| Detection by ID (GET) | 60s | Yes |
| Audit trail (GET) | 30s | Yes |
| CoT type mapping | 3600s | Yes |
| Detection POST | N/A | No (write) |
| Health check | N/A | No (real-time) |

---

## Feature 6: Security Hardening

**Service:** `src/services/security_service.py`
**Tests:** `tests/unit/test_security_service.py` (20 tests)

- Security event logging (auth success/failure, rate limit, input rejection)
- Security headers middleware (X-Content-Type-Options, X-Frame-Options, HSTS, CSP)
- CORS policy tightening (explicit methods, headers, origins)
- Request ID generation and propagation (X-Request-ID)
- Suspicious activity detection (repeated auth failures)
- Integration with existing AuditTrailService

**Security Headers Applied:**
| Header | Value |
|--------|-------|
| X-Content-Type-Options | nosniff |
| X-Frame-Options | DENY |
| Strict-Transport-Security | max-age=31536000; includeSubDomains |
| Content-Security-Policy | default-src 'none' |
| Cache-Control | no-store |
| X-Request-ID | {uuid} |
