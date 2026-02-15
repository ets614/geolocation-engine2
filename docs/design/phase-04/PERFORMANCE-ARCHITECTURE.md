# Phase 04: Performance Architecture

**Project**: AI Detection to COP Translation System
**Phase**: 04 - Security & Performance Hardening
**Date**: 2026-02-15
**Status**: DESIGN WAVE - Ready for Review
**Author**: Alex Chen, Solution Architect

---

## 1. Overview

This document defines the performance architecture for the Detection-to-CoP system. It addresses caching, database optimization, connection management, async processing, and observability instrumentation.

### Performance Baseline (from Existing Architecture Docs)

| Metric | Current Target | Observed Capability | Headroom |
|--------|---------------|-------------------|----------|
| Ingestion latency | <100ms | ~42ms (P95) | 58ms |
| End-to-end to TAK | <2 seconds | ~150ms (happy path) | 1.85s |
| Throughput | 10+ req/sec | 100-200 req/sec (estimated) | 10-20x |
| SQLite write | N/A | 1-5ms | N/A |
| Queue depth recovery | N/A | 1000+ items/sec (target) | N/A |

### Existing System Analysis

| Component | Current State | Optimization Opportunity |
|-----------|--------------|------------------------|
| Database | SQLite + SQLAlchemy, QueuePool(5,5), WAL mode, NORMAL sync | Index audit, query optimization |
| HTTP Client | aiohttp in CotService (TAK push) | Switch to httpx (consistency), connection pooling |
| Caching | None | Add response caching for read endpoints |
| Async | FastAPI async endpoints, asyncio for TAK push | Formalize background task processing |
| Connection Pool | pool_size=5, max_overflow=5 | Tune based on workload profile |
| Monitoring | Observability doc exists, not yet instrumented | Instrument with prometheus_client |

---

## 2. Caching Strategy

### 2.1 Decision: In-Memory Cache (MVP), Redis (Production)

**ADR Reference**: See ADR-P04-002 for Redis vs In-Memory decision.

**MVP Approach**: Python `cachetools` (MIT license, FREE) provides TTL cache and LRU cache in-process. Sufficient for single-instance deployment.

**Production Path**: Redis (BSD license, FREE) when horizontal scaling requires shared cache.

### 2.2 What to Cache

| Data | Cache? | TTL | Invalidation | Rationale |
|------|--------|-----|-------------|-----------|
| Detection by ID (GET) | Yes | 60s | On update | Read-after-write pattern; detection data is immutable after processing |
| Audit trail (GET) | Yes | 30s | On new event | Append-only; new events invalidate |
| Health check | No | N/A | N/A | Must reflect real-time state |
| Detection POST | No | N/A | N/A | Write operation, never cache |
| CoT type mapping | Yes | 3600s | On config change | Static lookup table, rarely changes |
| Confidence thresholds | Yes | 3600s | On config change | Static configuration |

### 2.3 Cache Architecture

```
Request --> Auth Check --> Rate Limit --> Cache Lookup
                                            |
                                    [Cache HIT] --> Return cached response
                                    [Cache MISS] --> Process request
                                                      |
                                                  Store in cache --> Return response
```

**Cache Key Pattern**: `{resource}:{identifier}:{version}`
- Example: `detection:det-abc-123:v1`
- Example: `audit:det-abc-123:v1`

**Cache Sizing (MVP)**:
- Max entries: 10,000
- Max memory: ~50 MB (detection responses average ~5 KB)
- Eviction: LRU when capacity reached

### 2.4 Cache Headers

Read endpoints return standard cache headers:
- `Cache-Control: private, max-age=60` (detection reads)
- `ETag: "<hash_of_response>"` (conditional GET support)
- `Last-Modified: <timestamp>`

Write endpoints return:
- `Cache-Control: no-store`

---

## 3. Database Query Optimization

### 3.1 Current Index Analysis

From `src/models/database_models.py`, existing indices:

**Detections table**:
- `idx_timestamp` on `timestamp`
- `idx_created_at` on `created_at`
- `idx_detection_id` on `detection_id` (also unique constraint)
- `idx_confidence_flag` on `confidence_flag`

**Offline Queue table**:
- `idx_synced_at` on `synced_at`

**Audit Events table**:
- `idx_audit_detection_id` on `detection_id`
- `idx_audit_event_timestamp` on `timestamp`
- `idx_audit_event_type` on `event_type`

### 3.2 Missing Indices (Recommended)

| Table | Index | Columns | Query Pattern |
|-------|-------|---------|---------------|
| `offline_queue` | `idx_queue_pending` | `synced_at, created_at` | Pending items ordered by creation (sync queue) |
| `offline_queue` | `idx_queue_retry` | `retry_count, synced_at` | Failed items needing retry |
| `detections` | `idx_source_timestamp` | `source, timestamp` | Filter detections by source + time range |
| `audit_events` | `idx_audit_severity` | `severity, timestamp` | Error event queries |
| `audit_events` | `idx_audit_compound` | `detection_id, event_type` | Specific event type for a detection |

### 3.3 N+1 Query Prevention

**Identified Risk**: `OfflineQueueService._mark_synced()` and `_increment_retry()` both load ALL pending queue items into Python then filter:

```python
# Current pattern (N+1 risk):
queue_items = session.query(OfflineQueue).filter(OfflineQueue.synced_at.is_(None)).all()
for item in queue_items:
    if item.detection_json.get("detection_id") == detection_id:
        item.synced_at = datetime.utcnow()
```

**Target**: Single-query updates using database-level filtering. The crafter should address this during implementation -- the behavioral target is:
- Mark synced: single database operation per detection ID
- Increment retry: single database operation per detection ID
- Batch sync: single query to load batch, single update for batch result

### 3.4 Query Optimization Targets

| Query Pattern | Current | Target | Method |
|--------------|---------|--------|--------|
| Get pending queue items | Full table scan (no pending index) | Index scan | Add composite index |
| Mark synced | Load all pending, filter in Python | Direct update by detection_id | Query redesign |
| Get audit trail | Index scan on detection_id | Index scan (already indexed) | No change needed |
| Count queue size | Full scan of unsynced | Index scan | Use `idx_queue_pending` |

---

## 4. Connection Pooling Configuration

### 4.1 Current Configuration

From `src/database.py`:
```python
pool_size=5,        # Minimum connections
max_overflow=5,     # Additional connections under load
pool_pre_ping=True  # Verify connection before use
```

### 4.2 Recommended Configuration

| Parameter | Current | Recommended | Rationale |
|-----------|---------|-------------|-----------|
| `pool_size` | 5 | 5 | Adequate for SQLite (single-writer) |
| `max_overflow` | 5 | 10 | Allow burst during queue sync |
| `pool_pre_ping` | True | True | Keep -- prevents stale connections |
| `pool_recycle` | None | 3600 (1 hour) | Prevent long-lived connection issues |
| `pool_timeout` | 30 (default) | 10 | Fail fast rather than block |

**SQLite Pragmas** (already configured):
- `journal_mode=WAL` -- enables concurrent reads during write
- `synchronous=NORMAL` -- good balance of speed vs durability

**Additional Pragmas to Consider**:
- `cache_size=-64000` (64 MB page cache, default is 2 MB)
- `busy_timeout=5000` (5 second wait on lock instead of immediate fail)
- `mmap_size=268435456` (256 MB memory-mapped I/O for read performance)

### 4.3 HTTP Client Connection Pooling

**Current**: `aiohttp.ClientSession()` created per TAK push (no persistent pool).

**Target**: Single persistent HTTP client with connection pooling for TAK Server communication.

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Max connections | 10 | TAK server concurrency limit |
| Keepalive timeout | 30s | Reuse connections during burst |
| Connect timeout | 5s | Fail fast for connectivity check |
| Read timeout | 10s | Allow TAK server processing time |
| Retry strategy | 3 attempts, exponential backoff | Resilience |

---

## 5. Async Processing Architecture

### 5.1 Current Async Pattern

```python
# In routes.py -- fire-and-forget TAK push
asyncio.create_task(cot_service.push_to_tak_server(cot_xml))
```

This pattern risks:
- Lost exceptions (unobserved task failures)
- No backpressure (unlimited concurrent pushes)
- No retry on failure (silent data loss)

### 5.2 Target: Background Task Queue

**Architecture**:
```
Detection POST --> Synchronous Processing (validate, geolocate, generate CoT)
              --> Return 201 to client immediately
              --> Enqueue TAK push as background task
                    |
                    v
              Background Task Runner
              - Bounded concurrency (max 10 concurrent pushes)
              - Retry with backoff on failure
              - Falls back to OfflineQueueService after max retries
              - Emits metrics (success/failure/latency)
```

**Key Behavioral Properties**:
- Client response time is independent of TAK push latency
- Background tasks have bounded concurrency (prevent resource exhaustion)
- Failed pushes always fall through to offline queue (zero data loss)
- All task outcomes are audited

### 5.3 Long-Running Operations

| Operation | Async? | Max Duration | Timeout Action |
|-----------|--------|-------------|----------------|
| Detection ingestion (validate + geolocate) | Sync | <100ms | 400 error |
| CoT XML generation | Sync | <10ms | 500 error |
| TAK push | Async (background) | 10s | Queue offline |
| Queue sync (batch) | Async (background) | 60s | Log, retry next cycle |
| Connectivity monitoring | Async (long-running) | Indefinite | Cancel on shutdown |

### 5.4 Graceful Shutdown

On SIGTERM/SIGINT:
1. Stop accepting new requests (health check returns SHUTTING_DOWN)
2. Wait for in-flight synchronous requests to complete (max 5s)
3. Cancel background tasks gracefully (allow current TAK push to finish)
4. Flush audit trail to database
5. Close database connections
6. Close HTTP client connections
7. Exit

---

## 6. Monitoring & Observability Instrumentation

### 6.1 Integration with Existing Observability Design

The `docs/infrastructure/observability-design.md` defines Prometheus metrics and Grafana dashboards but instrumentation is not yet in the codebase. Phase 04 implements the instrumentation layer.

### 6.2 Metrics to Instrument

**Application Metrics (RED pattern)**:

| Metric | Type | Labels | Source |
|--------|------|--------|--------|
| `http_requests_total` | Counter | method, endpoint, status | FastAPI middleware |
| `http_request_duration_seconds` | Histogram | method, endpoint, status | FastAPI middleware |
| `detection_ingestion_total` | Counter | source, status | Detection route |
| `ingestion_latency_seconds` | Histogram | N/A | Detection route |
| `geolocation_calculation_seconds` | Histogram | confidence_flag | GeolocationService |
| `cot_generation_seconds` | Histogram | N/A | CotService |
| `tak_push_duration_seconds` | Histogram | status | CotService |
| `tak_push_total` | Counter | status (success/failure/queued) | CotService |

**Resource Metrics (USE pattern)**:

| Metric | Type | Source |
|--------|------|--------|
| `offline_queue_size` | Gauge | OfflineQueueService |
| `offline_queue_oldest_seconds` | Gauge | OfflineQueueService |
| `db_pool_connections_active` | Gauge | DatabaseManager |
| `db_pool_connections_idle` | Gauge | DatabaseManager |
| `background_tasks_active` | Gauge | Task runner |
| `cache_hits_total` | Counter | Cache middleware |
| `cache_misses_total` | Counter | Cache middleware |

**Security Metrics**:

| Metric | Type | Labels |
|--------|------|--------|
| `auth_attempts_total` | Counter | method (jwt/apikey), result (success/failure) |
| `rate_limit_exceeded_total` | Counter | client_type |

### 6.3 Prometheus Endpoint

Expose `GET /metrics` endpoint (unauthenticated, restricted by network policy in production).

**Library**: `prometheus_client` (Apache 2.0 license, FREE)

### 6.4 Health Check Enhancement

Current health check returns basic status. Enhance to include:

```json
{
  "status": "UP",
  "version": "0.1.0",
  "components": {
    "database": { "status": "UP", "pool": "3/5 active" },
    "tak_server": { "status": "UP", "last_push": "2026-02-15T12:00:00Z" },
    "offline_queue": { "status": "UP", "pending": 0 },
    "cache": { "status": "UP", "hit_rate": "87%" }
  },
  "uptime_seconds": 3600
}
```

### 6.5 Structured Logging Enhancement

Current logging uses Python stdlib with basic messages. Target:
- JSON-formatted log output (for log aggregation)
- Correlation ID (`X-Request-ID`) threaded through all log entries for a request
- Timing breakdowns in log entries (validation_ms, geolocation_ms, cot_generation_ms)

---

## 7. Performance Quality Attributes (ISO 25010)

| Attribute | Target | Measurement |
|-----------|--------|-------------|
| Time Behavior | POST /detections P95 <100ms | Histogram metric |
| Time Behavior | End-to-end <2s (including TAK push) | Histogram metric |
| Resource Utilization | CPU <70% at 100 req/sec | Prometheus gauge |
| Resource Utilization | Memory <75% under load | Prometheus gauge |
| Capacity | Handle 100+ detections/sec sustained | Load test |
| Capacity | Queue sync 1000+ items/sec on reconnect | Load test |

---

## 8. Hexagonal Architecture Compliance

Performance components map to the existing port/adapter pattern:

| Performance Concern | Architecture Layer | Integration Point |
|--------------------|-------------------|-------------------|
| Response caching | Adapter (REST API Adapter) | FastAPI middleware or dependency |
| Database optimization | Adapter (SQLite Adapter) | DatabaseManager, model indices |
| Connection pooling | Adapter (SQLite, HTTP) | DatabaseManager, HTTP client |
| Background tasks | Adapter (TAK Integration) | CotService, OfflineQueueService |
| Prometheus metrics | Adapter (REST API Adapter) | FastAPI middleware + /metrics endpoint |
| Health check | Primary Port (HealthCheckPort) | Existing health endpoint |

**Key principle**: Performance instrumentation lives in the adapter layer. Domain core services (GeolocationService, CotService, AuditTrailService) are measured by the adapters wrapping them, not by internal instrumentation.

---

## 9. Technology Selections

All performance components use open source libraries:

| Component | Library | License | Cost |
|-----------|---------|---------|------|
| In-memory cache | cachetools 5.x | MIT | FREE |
| Cache (production) | Redis 7.x | BSD | FREE |
| Redis client | redis-py 5.x | MIT | FREE |
| Prometheus client | prometheus_client 0.x | Apache 2.0 | FREE |
| HTTP client (unified) | httpx 0.25+ | BSD | FREE |
| Structured logging | structlog 24.x | MIT | FREE |

**Total additional cost**: $0

---

## 10. Rejected Simpler Alternatives

Before proposing this multi-component performance architecture:

**Alternative 1: No caching, optimize queries only**
- Single-file change to add indices + fix N+1 queries
- Rejected: Addresses database layer only. Cache prevents redundant computation for repeated reads (audit trail queries during incident investigation). Cache hit rate expected 60-80% for read endpoints based on read-after-write pattern.

**Alternative 2: Configuration-only changes (pool tuning + pragmas)**
- Adjust pool sizes and SQLite pragmas without new components
- Rejected: Does address connection management but does not solve: missing metrics instrumentation (required by observability design), no background task management (current fire-and-forget loses errors), no read optimization for repeated queries. These are all net-new capabilities, not tuning.

---

## 11. Implementation Roadmap (Steps for Crafter)

| Step | Title | Production Files | AC Count |
|------|-------|-----------------|----------|
| P1 | Database index additions and query optimization | 2 | 4 |
| P2 | SQLite pragma tuning and connection pool adjustment | 1 | 3 |
| P3 | Unified HTTP client with connection pooling for TAK push | 2 | 4 |
| P4 | Background task runner with bounded concurrency | 2 | 5 |
| P5 | Response caching for read endpoints | 2 | 4 |
| P6 | Prometheus metrics instrumentation | 3 | 4 |
| P7 | Health check enhancement with component status | 1 | 3 |
| P8 | Structured JSON logging with correlation IDs | 2 | 3 |

**Steps/production-files ratio**: 8 steps / 15 files = 0.53 (well under 2.5 limit)

---

**Document Status**: COMPLETE - Ready for Peer Review
**Next**: ADRs, then Peer Review
