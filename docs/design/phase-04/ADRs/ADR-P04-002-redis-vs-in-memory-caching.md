# ADR-P04-002: Redis vs In-Memory Caching

## Status

Accepted

## Date

2026-02-15

## Context

The Detection-to-CoP system needs a caching layer to reduce redundant computation for read endpoints (detection lookup, audit trail queries). The system currently has no caching. Two approaches were evaluated.

**Workload characteristics**:
- Read-after-write pattern: detection created, then queried for status/audit
- Audit trail queries during incident investigation (repeated reads of same detection trail)
- Health check should NOT be cached (must reflect real-time state)
- Single-instance MVP deployment; multi-instance target in Phase 2
- Expected cache hit rate: 60-80% for read endpoints based on read-after-write pattern

**Cache requirements**:
- TTL-based expiration (detection data is immutable after processing)
- LRU eviction when capacity reached
- Max ~50 MB memory footprint
- Must not add operational complexity for MVP

## Decision

We will implement **in-memory caching using `cachetools`** for the MVP, with a clear migration path to **Redis** for multi-instance production deployment.

**MVP (Phase 04)**:
- `cachetools.TTLCache` for TTL-based caching (detection reads: 60s, audit: 30s)
- `cachetools.LRUCache` for static configuration lookups (CoT type mappings, thresholds)
- Cache accessed through a port interface (adapter pattern) enabling swap to Redis

**Production (Phase 2+)**:
- Redis 7.x as shared cache across API instances
- Same port interface, different adapter implementation

## Alternatives Considered

### Alternative 1: Redis from Day One

**How it works**: Deploy Redis alongside the application. All cache operations go through Redis client over network.

**Advantages**:
- Shared cache across multiple instances (production-ready immediately)
- Persistence options (RDB/AOF) survive application restarts
- Rich data structures (sorted sets for leaderboards, pub/sub for invalidation)
- Industry standard, battle-tested

**Disadvantages**:
- **Operational overhead**: Additional service to deploy, monitor, and maintain for MVP
- **Network latency**: ~0.5-1ms per cache operation (vs ~0.001ms for in-memory)
- **Docker Compose complexity**: Adds Redis container to development environment
- **Single-instance waste**: No cache sharing benefit when running one instance
- **Failure mode**: If Redis goes down, cache misses everywhere (must handle gracefully)

**Why Rejected for MVP**: The system is deployed as a single Docker container for MVP. Redis provides zero benefit over in-memory caching in a single-instance deployment while adding operational complexity (another container, monitoring, failure handling). The abstraction layer (port interface) means Redis can be added later with zero domain code changes.

### Alternative 2: No Caching (Query Optimization Only)

**How it works**: Rely entirely on database index optimization and query tuning. No cache layer.

**Advantages**:
- Zero additional components
- No cache invalidation complexity
- No stale data risk
- Simplest possible architecture

**Disadvantages**:
- **Repeated computation**: Audit trail queries during incident investigation hit database every time
- **No read optimization**: Detection status checks always require database roundtrip
- **Monitoring overhead**: Prometheus metrics queries would benefit from caching frequently-accessed data

**Why Rejected**: While database optimization is necessary (and is part of this phase), it does not eliminate redundant work for repeated reads. During incident investigation, operators query the same audit trail repeatedly. Without caching, each query hits the database. The read-after-write pattern (create detection, immediately query status) also benefits from caching. Expected 60-80% cache hit rate justifies the modest complexity of in-memory caching.

## Consequences

### Positive

- **Zero operational overhead**: No additional services for MVP
- **Sub-microsecond access**: In-memory cache is ~1000x faster than Redis network call
- **Simple implementation**: `cachetools` is a single dependency, well-tested library
- **Clean migration path**: Port/adapter abstraction means swapping to Redis requires only a new adapter
- **No failure mode**: In-memory cache cannot go down independently of the application

### Negative

- **No cache sharing**: Multiple instances would each have their own cache (cold starts)
- **No persistence**: Cache lost on application restart
- **Memory bound**: Cache competes with application for memory (mitigated by 50 MB limit)
- **No distributed invalidation**: Cannot invalidate cache across instances (not needed for MVP)

### Mitigations

- Cache interface defined as a port with adapter pattern; Redis adapter is a drop-in replacement
- Short TTLs (30-60s) mean cache loss on restart has minimal impact
- Memory limit (50 MB) prevents cache from consuming application memory
- LRU eviction ensures most-accessed data stays cached

## Technology

| Component | Library | License | Cost |
|-----------|---------|---------|------|
| MVP cache | cachetools 5.x | MIT | FREE |
| Production cache | Redis 7.x | BSD | FREE |
| Redis client | redis-py 5.x | MIT | FREE |

## References

- cachetools documentation: https://cachetools.readthedocs.io/
- Redis documentation: https://redis.io/docs/
- Existing architecture: `docs/architecture/architecture.md` (no caching currently)
