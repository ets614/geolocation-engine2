# Phase 04 Architecture: Security and Performance Layers

## Security Architecture

```
                    Request Flow
                         |
                  [1. Size Check]
                  Reject > 10 MB
                         |
                  [2. Rate Limit]
                  Token Bucket per-client
                  429 if exceeded
                         |
                  [3. Authentication]
                  JWT Bearer OR X-API-Key
                  401 if missing/invalid
                         |
                  [4. Input Sanitization]
                  SQL injection check
                  XSS check
                  Path traversal check
                  400 if malicious
                         |
                  [5. Pydantic Validation]
                  Type, range, format
                  422 if invalid
                         |
                  [6. Business Logic]
                  Core domain services
                         |
                  [7. Response]
                  + Security headers
                  + Cache headers
                  + Rate limit headers
                  + X-Request-ID
```

## Authentication Priority

1. `Authorization: Bearer {jwt_token}` header -- checked first
2. `X-API-Key: {api_key}` header -- checked second
3. Reject with 401 Unauthorized

## Caching Architecture

```
Request -> Auth -> Rate Limit -> Cache Lookup
                                      |
                              [Cache HIT] -> Return cached
                              [Cache MISS] -> Process request
                                                   |
                                              Store in cache -> Return
```

**Eviction Strategy:** LFU (Least Frequently Used) when max capacity reached
**Invalidation:** TTL-based automatic expiry

## Monitoring Architecture

```
Detection API (:8000)
     |
     +-- /metrics endpoint (Prometheus exposition format)
     |        |
     |   Prometheus (:9090)
     |        |
     |   Alert Rules (19 rules, 7 groups)
     |        |
     |   Grafana (:3000)
     |        |
     |   4 Dashboards:
     |     - Detection Pipeline
     |     - TAK Integration
     |     - Infrastructure
     |     - Audit Trail
     |
     +-- Structured JSON logs (stdout)
              |
         Promtail (scrape)
              |
         Loki (store)
              |
         Grafana (query)
```

## Hexagonal Architecture Compliance

| Concern | Layer | Integration |
|---------|-------|-------------|
| JWT Verification | Primary Port | FastAPI dependency injection |
| API Key Verification | Primary Port | FastAPI dependency injection |
| Rate Limiting | Adapter | FastAPI middleware |
| Input Validation | Adapter | Pydantic models + middleware |
| Security Headers | Adapter | FastAPI middleware |
| Caching | Adapter | FastAPI middleware |
| Prometheus Metrics | Adapter | FastAPI middleware + /metrics |
| Audit Logging | Domain Core | AuditTrailService (existing) |

**Principle:** Security and performance are enforced at the adapter layer. Domain core services receive only validated, authenticated requests.

## Technology Selections

| Component | Library | License | Cost |
|-----------|---------|---------|------|
| JWT (RS256) | PyJWT 2.x | MIT | Free |
| Rate limiting | In-memory (stdlib) | PSF | Free |
| Key hashing | hashlib (stdlib) | PSF | Free |
| Input sanitization | Pydantic v2 + custom | MIT | Free |
| In-memory cache | cachetools 5.x | MIT | Free |
| Prometheus | prometheus_client | Apache 2.0 | Free |
| Load testing | Locust | MIT | Free |
| Structured logging | structlog | MIT | Free |

**Total additional cost:** $0
