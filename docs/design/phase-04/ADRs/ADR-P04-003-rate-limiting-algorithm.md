# ADR-P04-003: Rate Limiting Algorithm Choice

## Status

Accepted

## Date

2026-02-15

## Context

The Detection-to-CoP system needs rate limiting to protect against abuse and ensure fair resource allocation across clients. The system currently has no rate limiting. The REST API accepts detection payloads with base64 image data (up to 10 MB), making it susceptible to resource exhaustion attacks.

**Requirements**:
- Per-client rate limiting (authenticated clients get higher limits)
- Burst tolerance (tactical operations may spike during events)
- Low overhead (must not add significant latency to <100ms ingestion target)
- Simple to implement and reason about for the crafter team
- Single-instance MVP; multi-instance awareness for Phase 2

Three rate limiting algorithms were evaluated.

## Decision

We will implement the **Token Bucket algorithm** for rate limiting.

**Configuration**:
- Authenticated (JWT): 100 request burst, 20 req/sec refill
- API Key: 50 request burst, 10 req/sec refill
- Unauthenticated: 10 request burst, 2 req/sec refill
- State stored in-memory (single instance); Redis-backed for Phase 2

## Alternatives Considered

### Alternative 1: Fixed Window Counter

**How it works**: Count requests per client in fixed time windows (e.g., 60-second windows). Reset counter at window boundary.

**Advantages**:
- Simplest to implement (dictionary of counters + timestamps)
- Lowest memory usage (one counter per client per window)
- Easy to understand and debug

**Disadvantages**:
- **Boundary burst problem**: A client can send 2x the limit by timing requests at a window boundary (e.g., 100 requests at second 59, then 100 at second 61 -- 200 in 2 seconds)
- **No burst tolerance**: Cannot handle legitimate burst patterns (tactical event generating rapid detections)
- **Unfair**: Client who happens to start mid-window gets fewer allowed requests

**Why Rejected**: The boundary burst problem is a security issue. An attacker can effectively double their rate limit by timing requests at window boundaries. While simple to implement, this is not robust enough for a system handling tactical operations data.

### Alternative 2: Sliding Window Log

**How it works**: Store timestamp of every request. Count requests in the trailing window (e.g., last 60 seconds).

**Advantages**:
- Precise rate limiting (no boundary issues)
- Smooth limiting behavior
- Accurate per-second calculations

**Disadvantages**:
- **High memory**: Stores timestamp per request per client (at 100 req/sec, that is 6000 timestamps per client per minute)
- **High CPU**: Counting requires scanning all timestamps in window
- **Scaling**: Memory grows linearly with request rate
- **Overkill**: Precision beyond what is needed for this use case

**Why Rejected**: Memory and CPU overhead scale linearly with request volume. At target throughput (100+ req/sec), storing individual timestamps becomes wasteful. The precision benefit over Token Bucket does not justify the resource cost.

### Alternative 3: Token Bucket (Selected)

**How it works**: Each client has a "bucket" that holds tokens. Tokens are consumed per request (1 token per request). Tokens refill at a constant rate. Requests rejected when bucket is empty.

**Advantages**:
- **Burst tolerance**: Bucket size defines burst capacity (tactical event handling)
- **Smooth rate**: Refill rate defines sustained throughput limit
- **Low memory**: Two values per client (token count + last refill timestamp)
- **No boundary issues**: Continuous refill, no window edges
- **Simple**: Easy to implement, easy to explain, easy to tune

**Disadvantages**:
- Slightly more complex than fixed window (requires refill calculation)
- Burst could be exploited (mitigated by reasonable bucket sizes)
- Need to handle stale buckets (clients who haven't made requests in a long time)

## Consequences

### Positive

- **Burst tolerance**: Bucket size of 100 allows tactical event spikes without rejection
- **Fair sustained rate**: Refill at 20 req/sec provides predictable throughput per client
- **Low overhead**: ~0.01ms per rate limit check (two float comparisons + update)
- **Simple tuning**: Two parameters (bucket size, refill rate) per client tier
- **Standard pattern**: Well-understood algorithm with extensive documentation

### Negative

- **In-memory state**: Lost on restart (clients get fresh buckets -- acceptable for rate limiting)
- **Per-instance**: In multi-instance deployment, each instance has independent limits (total effective limit = N x limit)
- **Stale entries**: Need cleanup of inactive client buckets (mitigated by periodic sweep)

### Mitigations

- Redis-backed token bucket for multi-instance deployment (Phase 2)
- Periodic cleanup of inactive client entries (every 5 minutes, remove entries not accessed in 10 minutes)
- Separate limits for auth endpoints (5 req/min for brute force prevention)
- Rate limit headers on every response (`X-RateLimit-Remaining`, `X-RateLimit-Reset`)

## Implementation Notes

**Response on rate limit exceeded**:
```
HTTP 429 Too Many Requests
Retry-After: <seconds_until_tokens_available>
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: <unix_timestamp>

{
  "error": "RATE_LIMITED",
  "message": "Too many requests. Retry after N seconds."
}
```

**Exempt endpoints**:
- `GET /api/v1/health` (monitoring must not be rate-limited)
- `GET /metrics` (Prometheus scraping must not be rate-limited)

## Technology

| Component | Library | License | Cost |
|-----------|---------|---------|------|
| Token bucket (MVP) | Python stdlib (in-memory dict + time) | PSF | FREE |
| Token bucket (production) | Redis + lua script | BSD | FREE |

## References

- Token Bucket algorithm: https://en.wikipedia.org/wiki/Token_bucket
- Existing rate limit mention: `docs/architecture/architecture.md` (Section 2.14, adapter mentions rate limiting)
- API contract: Rate limit response defined in `docs/architecture/architecture.md` (Section 5.1)
