# YDC Adapter - Design Decisions Matrix

**Quick reference for all architectural decisions with rationale and alternatives.**

---

## Decision 1: Hexagonal Architecture

| Aspect | Decision |
|--------|----------|
| **What** | Use hexagonal architecture (ports & adapters pattern) |
| **Why** | Multiple variable I/O sources (camera providers, Geolocation API); need to test domain logic in isolation without mocks; future extensibility |
| **Status** | ✅ Accepted |
| **Document** | ADR-001-hexagonal-architecture.md |

### Alternatives Rejected

| Alternative | Why Rejected | Impact |
|-------------|-------------|--------|
| **Layered** (Controller → Service → Model) | Business logic couples to I/O; testing requires stubbing external services; hard to add new camera providers | +2 weeks to add DJI provider; untestable domain layer |
| **Event-driven** (Kafka/RabbitMQ) | Adds latency (queue → processing); overkill for MVP; TAK push already async in Geolocation-Engine2 | Defeats <200ms latency target; +3-4 weeks operational overhead |
| **Monolithic** (Embedded in Geolocation-Engine2) | Violates single responsibility; couples orchestration to geolocation math; scales inefficiently | Can't test independently; slow dev cycles; brittle |

---

## Decision 2: Separate Microservice (Not Embedded)

| Aspect | Decision |
|--------|----------|
| **What** | Build YDC Adapter as standalone Docker container (port 8001), calls Geolocation-Engine2 via REST (port 8000) |
| **Why** | Independent deployment, testing, scaling; clear separation of concerns; reusable adapter; future-proof |
| **Status** | ✅ Accepted |
| **Document** | ADR-002-separate-service.md |

### Alternatives Rejected

| Alternative | Why Rejected | Impact |
|-------------|-------------|--------|
| **Embedded** in Geolocation-Engine2 | God service; hard to test; scales both when only YDC has load; couples orchestration to photogrammetry logic | Shared database complexity; 5x slower tests; tight coupling |
| **Message Queue** (Kafka) | Adds latency (event → queue → processing); overkill; TAK push already async | +5-10s latency; Kafka operational overhead; doesn't fit MVP |
| **Sidecar** (Kubernetes Pod) | Premature K8s adoption; MVP not on Kubernetes | K8s complexity upfront; not applicable to docker-compose dev env |

---

## Decision 3: Synchronous REST (Not Async Queue)

| Aspect | Decision |
|--------|----------|
| **What** | Call Geolocation-Engine2 via synchronous POST /api/v1/detections, wait for response |
| **Why** | Low latency (<200ms target); simple deployment; clear error semantics; backpressure if backend slow |
| **Status** | ✅ Accepted |
| **Document** | ADR-003 (in architecture-design.md) |

### Alternatives Rejected

| Alternative | Why Rejected | Impact |
|-------------|-------------|--------|
| **Async Queue** (Kafka/RabbitMQ) | Queue delay defeats <200ms latency; operational complexity; fire-and-forget loses error feedback | Latency increased 5-10x; must manage message broker; silent failures |
| **Batch processing** | Loses real-time property; doesn't fit streaming use case | Defeats purpose of YDC integration; high latency |
| **Fire-and-forget** | No error feedback to YDC client; dangerous | Silent detection loss; can't debug failures |

---

## Decision 4: Pluggable Camera Position Providers

| Aspect | Decision |
|--------|----------|
| **What** | Abstract camera position as secondary port; implement adapters for Mock, DJI, MAVLink |
| **Why** | Extensible (new provider = new adapter only); testable (mock adapter); future-proof (DJI/MAVLink Phase 2) |
| **Status** | ✅ Accepted |
| **Document** | ADR-004 (in architecture-design.md) |

### Alternatives Rejected

| Alternative | Why Rejected | Impact |
|-------------|-------------|--------|
| **Hardcoded if/elif** in domain | Not extensible; violates OCP; tight coupling | Can't add DJI without refactoring core logic; 2x test coupling |
| **Factory pattern only** | No abstraction (port); no interface contract; hard to mock | Tests require real hardware; can't validate DJI integration independently |
| **Single monolithic provider** | Inflexible; scales poorly; couples unrelated concerns | Must build DJI + MAVLink simultaneously; serial development |

---

## Decision 5: Stateless Adapter (No Persistence)

| Aspect | Decision |
|--------|----------|
| **What** | YDC Adapter is stateless; no database, no disk persistence. Geolocation-Engine2 owns durability |
| **Why** | MVP simplicity; horizontal scaling (no state sync); Geolocation-Engine2 already persists (detections, offline queue, audit trail) |
| **Status** | ✅ Accepted |
| **Document** | ADR-005 (in architecture-design.md) |

### Alternatives Rejected

| Alternative | Why Rejected | Impact |
|-------------|-------------|--------|
| **Local SQLite queue** | Buffers frames on disk; can't scale horizontally (state sync nightmare); added complexity | Must migrate schema Phase 2; can't add 2nd adapter instance without conflict; +4 weeks dev |
| **Shared database** (PostgreSQL) | Premature for MVP; adds operational burden (DB migration, HA setup) | Phase 2+ decision; not blocking MVP |

---

## Decision 6: Python + FastAPI (Consistency)

| Aspect | Decision |
|--------|----------|
| **What** | Implement YDC Adapter in Python 3.11 + FastAPI (same stack as Geolocation-Engine2) |
| **Why** | Consistency (same deployment patterns, ops knowledge); async native (asyncio); team expertise; time-to-market |
| **Status** | ✅ Accepted |
| **Document** | ADR-006 (in architecture-design.md) |

### Alternatives Rejected

| Alternative | Why Rejected | Impact |
|-------------|-------------|--------|
| **Go** (goroutines) | Faster runtime but +3-4 weeks dev time; immature geospatial libs; unfamiliar to team | MVP delayed to Q2; learning curve steep |
| **Node.js** | Type safety issues; async error handling weaker than Python; geospatial support weak | Bugs harder to catch; MVP risk high |
| **Rust** | Steep learning curve; +4-6 weeks; overkill for MVP throughput needs | MVP delayed; no benefit for MVP scale targets |

---

## Decision 7: Mock Provider for MVP (Phase 1)

| Aspect | Decision |
|--------|----------|
| **What** | Implement MockCameraPositionAdapter (fixed/randomized position) for MVP. DJI/MAVLink deferred to Phase 2 |
| **Why** | MVP focus: validate architecture, test integration with Geolocation-Engine2. Real providers require hardware/SDKs (+2-3 weeks). Port design allows easy addition later |
| **Status** | ✅ Accepted |
| **Document** | ADR-007 (in architecture-design.md) |

### Alternatives Rejected

| Alternative | Why Rejected | Impact |
|-------------|-------------|--------|
| **All providers** in MVP | Out of scope; delays MVP 2-3 weeks | Q2 start instead of Q1 end; business impact high |
| **No mock** at all | Can't test locally without hardware | MVP can't validate end-to-end; must wait for Phase 2 hardware |

---

## Decision 8: No Shared Database (Phase 1)

| Aspect | Decision |
|--------|----------|
| **What** | YDC Adapter and Geolocation-Engine2 use separate databases initially. Adapter is stateless (no DB at all) |
| **Why** | MVP simplicity; independent scaling; Geolocation-Engine2 already has SQLite with detection history, offline queue, audit trail |
| **Status** | ✅ Accepted |
| **Contingency** | Phase 2+: Migrate to shared PostgreSQL if horizontal scaling demands |

### Phase 2+ Upgrade Path

```
MVP (Phase 1)                          Phase 2+
┌──────────────────┐                   ┌──────────────────┐
│ YDC Adapter      │                   │ YDC Adapter      │ ← No change
│ (stateless)      │                   │ (stateless)      │
└────────┬─────────┘                   └────────┬─────────┘
         │                                      │
    [no database]          ──────→         [Connection to]
         │                                      │
         ↓                                      ↓
Geolocation-Engine2                  Shared PostgreSQL
│ SQLite                             (with Geo-Engine2)
└─ detections_table                 └─ detections_table
└─ offline_queue_table              └─ offline_queue_table
└─ audit_trail_table                └─ audit_trail_table
```

---

## Decision 9: Error Recovery Strategy

| Aspect | Decision |
|--------|----------|
| **What** | Retry with exponential backoff (1s, 2s, 4s max); max 3 retries; respects HTTP 429 (rate limit) |
| **Why** | Transient failures common (network hiccup, brief API unavailability); exponential backoff prevents thundering herd; respects rate limits |
| **Status** | ✅ Accepted |
| **Document** | Architecture-design.md Section 6 (Error Handling) |

### Retry Policy Rationale

| Failure Type | Retry? | Backoff | Max Retries | Why |
|--------------|--------|---------|-------------|-----|
| Camera provider timeout | Yes | 1, 2, 4s | 3 | Transient network issues; avoid cascade failures |
| Geolocation 500 error | Yes | 1, 2, 4s | 3 | Server hiccup; recovered quickly |
| Geolocation 429 limit | Yes | Exponential | Infinite* | Respect backoff header; preserve SLA |
| Geolocation 400 error | No | N/A | 0 | Client error; retry won't help (e.g., pixel out of bounds) |
| Geolocation 404 error | No | N/A | 0 | Endpoint gone; programming error |

*Backoff max 8s; will eventually succeed or timeout after 30+ seconds

---

## Decision 10: Observability Strategy

| Aspect | Decision |
|--------|----------|
| **What** | Structured JSON logging (Python stdlib); frame_id in all logs; Prometheus-compatible metrics |
| **Why** | Easy debugging (frame_id propagation); container log aggregation compatible (ELK, CloudWatch); operational observability |
| **Status** | ✅ Accepted |

### Logging Format

```json
{
  "timestamp": "2026-02-17T14:35:42.123Z",
  "level": "INFO",
  "logger": "ydc_adapter.services.processor",
  "message": "Detection processed successfully",
  "frame_id": "ydc-frame-001",
  "detection_id": "550e8400-e29b-41d4",
  "latency_ms": 125,
  "camera_provider": "mock",
  "geolocation_confidence": "GREEN"
}
```

### Metrics (Prometheus Format)

```
# HELP ydc_frames_received_total Total frames received
# TYPE ydc_frames_received_total counter
ydc_frames_received_total 1234

# HELP ydc_latency_ms Processing latency (histogram)
# TYPE ydc_latency_ms histogram
ydc_latency_ms_bucket{le="100"} 456
ydc_latency_ms_bucket{le="200"} 789
ydc_latency_ms_bucket{le="500"} 1000
ydc_latency_ms_count 1234
ydc_latency_ms_sum 123456

# HELP ydc_errors_total Total errors by type
# TYPE ydc_errors_total counter
ydc_errors_total{type="provider_unavailable"} 12
ydc_errors_total{type="geo_api_failed"} 5
ydc_errors_total{type="invalid_bbox"} 2
```

---

## Decision 11: Deployment Strategy

| Aspect | Decision |
|--------|----------|
| **Local Dev** | Docker Compose (YDC Adapter + Geolocation-Engine2 + Mock TAK) |
| **MVP Production** | Docker on single EC2 instance; both containers managed by docker-compose or systemd |
| **Phase 2+** | Kubernetes (multi-instance YDC Adapter, load balancer) |
| **Why** | Docker Compose familiar; scales naturally to K8s; no infrastructure lock-in |
| **Status** | ✅ Accepted |

### Evolution Path

```
Phase 1 (MVP)          Phase 2 (Scale)           Phase 3 (HA)
┌─────────────┐        ┌─────────────────┐       ┌──────────────────┐
│ Docker      │        │ Kubernetes      │       │ Kubernetes +     │
│ Compose     │   →    │ Multi-instance  │   →   │ Multi-region     │
│             │        │ Load balancer   │       │ Service mesh     │
│ Single host │        │ Auto-scaling    │       │ Multi-AZ HA      │
└─────────────┘        └─────────────────┘       └──────────────────┘
  MVP ship         Scale as needed            Future (if needed)
```

---

## Decision 12: Technology Stack Rationale

| Component | Chosen | License | Why NOT Alternatives |
|-----------|--------|---------|---------------------|
| **Language** | Python 3.11 | PSF | Go (+3-4w), Node.js (type safety), Rust (complexity) |
| **Framework** | FastAPI | MIT | Flask (no async), Django (overkill), Starlette (too low-level) |
| **HTTP Client** | httpx | BSD | requests (no async), aiohttp (complex API), urllib3 (low-level) |
| **WebSocket** | FastAPI built-in | MIT | websockets pkg (duplication), custom sockets (fragile) |
| **Serialization** | Pydantic v2 | MIT | dataclasses (no validation), marshmallow (less type-safe) |
| **Async Runtime** | asyncio | PSF | Trio (learning curve), Curio (experimental), gevent (no FastAPI support) |
| **Logging** | stdlib logging | PSF | structlog (complexity), loguru (non-stdlib), custom (waste of time) |
| **Testing** | pytest | MIT | unittest (verbose), nose2 (abandoned), testng (Java) |
| **Container** | Docker | Apache | Podman (operational friction), LXC (complexity) |

**Total Stack Cost**: $0 (all open source)

---

## Decision 13: Interface Contracts

| Port | Interface | Method Signature |
|------|-----------|------------------|
| **Camera Provider** | `CameraPositionProvider` | `async get_position(frame_id: str) → CameraPosition` |
| (abstract) | | `async health_check() → bool` |
| **Geolocation Client** | `GeolocationClient` | `async post_detection(req: GeolocationApiRequest) → str` |
| (abstract) | | (returns CoT XML) |
| **Observability** | `ObservabilityPort` | `log_info(msg, context_dict) → None` |
| (abstract) | | `log_error(msg, exception) → None` |
| | | `track_metric(name, value) → None` |

**Rationale**: Minimal, focused interfaces; each port has 1-2 core methods; no god interfaces

---

## Decision 14: Testing Coverage Strategy

| Layer | Target | Approach | Benefits |
|-------|--------|----------|----------|
| **Domain** | 95%+ | Pure function unit tests; no mocks | Fast (<1s), clear failures, regression detection |
| **Services** | 90%+ | Mock adapters, test state transitions | Fast (<5s), validates logic coupling |
| **Adapters** | 85%+ | Real adapters with mock backends | Catches integration bugs (e.g., REST parsing) |
| **Integration** | 75%+ | Full stack with Docker Compose | End-to-end validation, realistic load |
| **Load** | N/A | 100+ det/sec for 60s | Performance regression detection |

**Overall**: ~85-90% coverage planned; ~95 tests total

**Why not 100%**: Test maintenance ROI decreases; focus on high-risk areas (error paths, orchestration)

---

## Summary Table: All Decisions

| Decision | Status | Priority | Risk | Phase |
|----------|--------|----------|------|-------|
| 1. Hexagonal Architecture | ✅ Accepted | P0 (Core) | Low | MVP |
| 2. Separate Microservice | ✅ Accepted | P0 (Core) | Low | MVP |
| 3. Sync REST (not queue) | ✅ Accepted | P0 (Core) | Low | MVP |
| 4. Pluggable Providers | ✅ Accepted | P1 (Important) | Low | MVP |
| 5. Stateless Adapter | ✅ Accepted | P1 (Important) | Low | MVP |
| 6. Python + FastAPI | ✅ Accepted | P1 (Important) | Low | MVP |
| 7. Mock Provider Phase 1 | ✅ Accepted | P2 (Nice) | Medium | MVP |
| 8. No Shared DB Phase 1 | ✅ Accepted | P1 (Important) | Low | MVP |
| 9. Error Recovery (Retry) | ✅ Accepted | P0 (Core) | Low | MVP |
| 10. Structured Logging | ✅ Accepted | P2 (Nice) | Low | MVP |
| 11. Docker Compose Deploy | ✅ Accepted | P1 (Important) | Low | MVP |
| 12. OSS Tech Stack | ✅ Accepted | P1 (Important) | Low | MVP |
| 13. Interface Contracts | ✅ Accepted | P1 (Important) | Low | MVP |
| 14. Test Coverage 85-90% | ✅ Accepted | P0 (Core) | Low | MVP |

---

## Trade-offs Accepted

| Trade-off | Accept | Trade-off | Reason |
|-----------|--------|-----------|--------|
| Network latency +5-10ms | Accept | Independent deployment | Separate containers necessary for scalability |
| Docker Compose overhead | Accept | Simplicity | Familiar tool; scales to K8s naturally |
| Mock provider (Phase 1) | Accept | Real DJI integration | Deferred doesn't block MVP; saves 2-3 weeks |
| Stateless adapter (Phase 1) | Accept | No local buffer | Simplicity; Geolocation-Engine2 has offline queue |
| No multi-db consistency | Accept | Simplicity | Geolocation-Engine2 owns detections; Adapter stateless |

---

## Future Decisions (Phase 2+)

| Decision | When | Conditions |
|----------|------|-----------|
| Add DJI provider | Q2 2026 | Real drone hardware available + UAV team collaboration confirmed |
| Add MAVLink provider | Q2 2026 | Conditional on DJI success + ArduPilot adoption |
| Migrate to PostgreSQL | Q2-Q3 2026 | Multi-instance scale needed OR operational complexity justifies upgrade |
| Deploy to Kubernetes | Q3+ 2026 | Multi-region OR auto-scaling requirements OR k8s adoption org-wide |
| Add message queue | Q4 2026+ | If decoupling needed for TAK pipeline (currently not required) |

---

**Document Version**: 1.0
**Last Updated**: 2026-02-17
**Audience**: Architecture Decision Stakeholders
**Approval**: Pending peer review (Morgan → Atlas)

