# ADR-002: Separate YDC Adapter Service vs Embedded in Geolocation-Engine2

**Date**: 2026-02-17
**Status**: Accepted
**Decider**: Morgan (Solution Architect)

## Context

Two ways to add YDC support:

**Option A: Embedded in Geolocation-Engine2**
- Add new endpoint: `POST /api/v1/detections/ydc` (WebSocket)
- Add service: `YdcOrchestrationService` in existing codebase
- Shared database with Geolocation-Engine2

**Option B: Separate Microservice**
- New service: `ydc-adapter` (standalone Docker container)
- Listens on port 8001 (separate from Geolocation-Engine2 port 8000)
- Calls Geolocation-Engine2 API via REST
- No shared database (stateless)

**Question**: Which maximizes team velocity, clarity, and scalability?

## Decision

**Build separate YDC Adapter microservice** (Option B).

YDC Adapter is a standalone Docker container that:
- Listens for YOLO detections via WebSocket (`/ws/ydc`)
- Fetches camera position from variable providers (Mock, DJI, MAVLink)
- Calls Geolocation-Engine2 REST API (`POST /api/v1/detections`)
- Replies to YDC client via WebSocket
- Runs independently with no shared database

## Rationale

### 1. Separation of Concerns
**Geolocation-Engine2 Responsibility**: Convert pixel → GPS (photogrammetry + geospatial math)
- Domain: Pure geolocation calculation
- Input: Image pixels + camera metadata
- Output: GPS coordinates + CoT XML

**YDC Adapter Responsibility**: Orchestrate YOLO detections → geolocation pipeline
- Domain: Frame handling, camera position aggregation, error recovery
- Input: YOLO bounding boxes (WebSocket)
- Output: Geolocation responses (WebSocket)

**Why separate**: These are two distinct problems. Mixing them creates a "god service" that's harder to test and maintain.

### 2. Independent Deployment & Scaling
- **Geolocation-Engine2**: Shared across multiple detection sources (YDC, satellite, drones, fire API)
- **YDC Adapter**: Only for YDC clients

If YDC has high load (1000+ det/sec):
- Scale YDC Adapter to 5 instances behind load balancer
- Geolocation-Engine2 unaffected (still 1 instance or 2-3 if needed)

If embedded: Scaling one component requires scaling both, wasting resources.

### 3. Testing Independence
**Geolocation-Engine2 tests**:
- Focus on photogrammetry correctness (pixel → GPS accuracy)
- Don't care about YOLO frames, camera telemetry providers
- Mock input: Image + pixel coordinates

**YDC Adapter tests**:
- Focus on orchestration, camera position aggregation
- Don't care about geolocation math (that's Geolocation-Engine2's job)
- Mock Geolocation-Engine2 with simple HTTP mock server

**Why separate**: Unit tests for each service run independently in <5 seconds. Embedded would require:
- Either full Geolocation-Engine2 stack for every YDC test
- Or move geolocation logic to shared library (violates single responsibility, increases complexity)

### 4. Future Reuse & Flexibility
**Scenario 1 (Phase 2)**: "We want YDC to call ML object database instead of Geolocation-Engine2 for some frames"
- **Separate service**: Swap adapter; Geolocation-Engine2 unchanged
- **Embedded**: Modify Geolocation-Engine2; couples ML database to photogrammetry logic

**Scenario 2 (Phase 3)**: "Other projects want to use YDC Adapter with their own geolocation backend"
- **Separate service**: Reuse YDC Adapter; configure endpoint
- **Embedded**: Code duplication; must build new service from scratch

### 5. Technology Stack Consistency
- **Geolocation-Engine2**: Python + FastAPI + SQLite (focused on geolocation)
- **YDC Adapter**: Python + FastAPI + stateless (focused on orchestration)

Both use same stack, so deployments, monitoring, debugging are consistent.

### 6. Operational Clarity
Separate service means:
- Clear log sources: "Error in YDC Adapter" vs "Error in Geolocation-Engine2"
- Clear monitoring: Separate metrics dashboards
- Clear on-call: YDC Adapter issues handled by YDC team; geolocation issues by geolocation team
- Clear rollback: Deploy/rollback each independently

### 7. Resource Efficiency
If Geolocation-Engine2 crashes, only YDC is affected (not satellite detection ingestion).
If YDC Adapter crashes, only YDC clients are affected (Geolocation-Engine2 still works).

## Constraints & Tradeoffs

### Network Latency
- **Embedded**: YDC → Service → Geolocation (same process, 0 latency)
- **Separate**: YDC → Adapter → Geolocation (network calls, +5-10ms)

**Impact**: Latency budget ~200ms; +5-10ms acceptable
**Mitigation**: Connection pooling, local caching (camera position stable for frames)

### Deployment Complexity
- **Embedded**: Deploy single service
- **Separate**: Deploy two containers

**Impact**: Minimal; both use Docker, Docker Compose handles orchestration
**Mitigation**: docker-compose.yml manages both; single `docker-compose up` starts both

### Database Complexity
- **Embedded**: Shared SQLite (one database)
- **Separate**: YDC Adapter has no database; Geolocation-Engine2 has SQLite

**Impact**: Reduces complexity (Adapter is stateless)
**Mitigation**: None needed; simpler is better

## Alternatives Considered

### Alternative 1: Embedded in Geolocation-Engine2

```
Geolocation-Engine2 (single service)
├── Endpoint 1: POST /api/v1/detections (image + pixel)
├── Endpoint 2: WS /ws/ydc (YOLO frames) ← NEW
├── Service 1: GeolocationService (existing)
├── Service 2: YdcOrchestrationService (new) ← NEW
└── Database: SQLite (shared)
```

**Why Rejected**:
1. **Violates single responsibility**: Geolocation-Engine2 becomes responsible for both photogrammetry AND YDC orchestration
2. **Testing couples concerns**: Testing YDC orchestration requires running geolocation logic; slow tests, false failures
3. **Scaling inefficient**: Scaling one service scales both; if YDC has 10x traffic, wastes compute on geolocation
4. **Future brittleness**: When Phase 2 wants to swap geolocation backend, YDC logic entangled
5. **Team coordination**: YDC team can't develop independently; must coordinate database schema changes with Geolocation team

**Evidence**: Real-world microservice failures often stem from mixing responsibilities. See AWS Lambda function bloat, Monolith strangler pattern.

### Alternative 2: Shared Message Queue (Kafka/RabbitMQ)

```
YDC WebSocket
    ↓
YDC Adapter (lightweight)
    ├─→ Kafka
Geolocation Service (consumes from Kafka)
    ├─→ TAK (async)
```

**Why Rejected**:
1. **Adds latency**: Event queued, processed asynchronously (defeats <200ms target)
2. **Adds operational burden**: Must manage Kafka cluster, monitoring, scaling
3. **Overkill for MVP**: Decoupling nice-to-have, not must-have
4. **TAK push already async**: Geolocation-Engine2 already handles offline queue + async TAK push
5. **Timing budget**: 8-12 weeks doesn't include Kafka operations expertise

**Evidence**: Event-driven suits high-volume fire-and-forget patterns. YDC needs request/response (fire-and-wait).

### Alternative 3: Sidecar Pattern (YDC Adapter + Geolocation-Engine2 in same Pod)

```
Kubernetes Pod
├─ Container 1: Geolocation-Engine2 (port 8000)
└─ Container 2: YDC Adapter (port 8001)
   └─→ localhost:8000 (fast local call)
```

**Why Rejected** (for MVP):
1. **Kubernetes not required**: MVP deploys on single Docker container; K8s Phase 2+
2. **Complexity premature**: Adds K8s expertise requirement upfront
3. **Simpler solution available**: Two separate containers, docker-compose orchestration
4. **Scale path unclear**: If each adapter instance needs Geolocation instance, still 2x resources

**Note**: Sidecar pattern valid for Phase 2+ if Kubernetes adoption decided. Not MVP requirement.

## Consequences

### Positive

1. **Clear ownership**: YDC Adapter team owns YDC integration; Geolocation team owns geolocation
2. **Parallel development**: Phase 1 MVP ships Adapter + Mock provider; Phase 1.5 ships DJI provider (independent effort)
3. **Fast testing**: YDC tests run without geolocation stack; <5 seconds
4. **Independent scaling**: Load on YDC doesn't force Geolocation scaling (cost savings)
5. **Reusability**: YDC Adapter could call different backend (ML API, custom service)
6. **Clear debugging**: Logs/metrics clearly identify which service has issue
7. **Operational simplicity**: Standard Docker Compose patterns; familiar to DevOps

### Negative

1. **Network latency**: +5-10ms added (acceptable within 200ms budget)
2. **Deployment overhead**: Must manage two containers (Docker Compose handles this)
3. **Dependency on Geolocation-Engine2**: If Geolocation-Engine2 down, YDC can't geolocation (handled by retry + error response)
4. **No direct database access**: YDC Adapter can't query detection history (not needed for MVP)

**Mitigations**:
- Network latency: Connection pooling via httpx
- Deployment: Docker Compose + Kubernetes Helm charts
- Dependency: Documented explicit dependency; monitoring catches outages
- Database: Phase 2+ if shared DB needed (migrate to PostgreSQL)

## Implementation Plan

### Phase 1 (MVP)
1. Build YDC Adapter as standalone service
2. Mock camera provider (fixed/randomized position)
3. REST client to Geolocation-Engine2
4. Docker Compose orchestrates both services
5. Deploy to staging/prod as two separate containers

### Phase 2 (Q2 2026)
1. Add DJI camera provider (if needed)
2. Scale YDC Adapter to 3+ instances if load warrants
3. Consider PostgreSQL for shared database (if Phase 2 scale demands)

### Phase 3 (Q3+ 2026)
1. Kubernetes orchestration (if multi-region deployment needed)
2. Sidecar pattern optimization (if Kubernetes adopted)

## Validation Criteria

- [ ] YDC Adapter can start/stop without affecting Geolocation-Engine2
- [ ] YDC Adapter tests run in <5 seconds without starting Geolocation-Engine2
- [ ] Geolocation-Engine2 can scale independently of YDC traffic
- [ ] Network latency between Adapter + Geolocation measurable and <10ms
- [ ] Docker Compose starts both services with single command
- [ ] Error handling clear: Adapter errors don't propagate to Geolocation layer

## References

- Sam Newman, "Building Microservices" (2nd ed., 2021) — Microservice boundaries
- Martin Fowler, "Monolith First" (2015) — When NOT to microservice
- This project's Geolocation-Engine2 (proves FastAPI + Python + SQLite pattern works)

---

## Appendix: Deployment Diagrams

### Local Development (docker-compose.yml)
```
Host Machine
├─ Port 8000 → Geolocation-Engine2
├─ Port 8001 → YDC Adapter
├─ Port 1080 → Mock TAK Server (testing)
└─ Volume: ./geolocation-engine2-data (SQLite)
```

### Production (Docker Compose on Single Host)
```
AWS EC2 Instance (t2.medium)
├─ Container: Geolocation-Engine2:v1.0.0
│  └─ Port 8000
│  └─ Volume: /data (EBS persistent)
├─ Container: YDC Adapter:v1.0.0
│  └─ Port 8001
│  └─ No volume (stateless)
└─ nginx (reverse proxy)
   ├─ :80 → Container ports
   ├─ SSL/TLS termination
   └─ Health check routing
```

### Production (Kubernetes, Phase 2+)
```
Kubernetes Cluster
├─ Namespace: production
│  ├─ Deployment: geolocation-engine2 (3 replicas)
│  │  └─ Service: ClusterIP :8000
│  │  └─ StatefulSet: PostgreSQL (1 instance)
│  │
│  ├─ Deployment: ydc-adapter (5 replicas)
│  │  └─ Service: LoadBalancer :8001
│  │  └─ Autoscaling: CPU >70%
│  │
│  └─ ConfigMap: camera-providers (mock, dji, mavlink configs)
```

