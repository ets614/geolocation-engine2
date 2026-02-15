# ADR-002: Monolith vs. Microservices

**Status**: Accepted

**Date**: 2026-02-17

**Decision Makers**: Solution Architect, Engineering Lead

---

## Context

The system has multiple responsibilities: ingesting detections, validating geolocation, transforming formats, outputting to TAK, queuing offline, and maintaining audit trails. We must choose between:

1. **Monolith**: Single process with all components (DetectionIngestionService, GeolocationValidationService, etc.) running in-process
2. **Microservices**: Separate services for ingestion, validation, transformation, output, queuing

This decision impacts deployment complexity, scalability, and development timeline.

---

## Decision

We will build a **Monolith for MVP** (8-12 week timeline) with clear internal service boundaries to enable future decomposition.

**Architecture**:
- Single Docker container running all components in-process
- Services communicate via function calls (no network overhead)
- Shared SQLite database
- Clear hexagonal interfaces enable independent evolution

**Future Evolution Path**:
- Phase 2: Decompose to microservices if horizontal scaling needed
- Phase 2: Message queue (Kafka) for decoupling if high-volume streaming needed

---

## Rationale

### Why Monolith for MVP?

1. **Fast Development**: No inter-service communication overhead, debugging simpler
2. **Fast Deployment**: Single Docker image, one container to manage
3. **Operational Simplicity**: Single process, single health check, single database
4. **Performance**: In-process function calls have zero network latency
5. **MVP Constraints**: 8-12 week timeline requires minimizing infrastructure work
6. **Detection Volume**: MVP target <100 detections/second, single container sufficient

**Supporting Evidence**:
- MVP scope is walking skeleton (5 core stories), not full platform
- Emergency Services customer (primary target) doesn't require massive scale initially
- Team can focus on validation (detecting bugs) vs. infrastructure (managing services)

### Why NOT Microservices?

1. **Deployment Complexity**: Each service needs own database, health checks, deployment pipeline
2. **Debugging**: Network calls between services make debugging detection failures harder
3. **Timeline Pressure**: Infrastructure overhead would push MVP beyond 8-12 weeks
4. **Premature**: Don't optimize for scale we don't have yet

---

## Alternatives Considered

### Alternative 1: Microservices from Day 1
**Architecture**:
```
API Service → Ingestion Service → Validation Service → Transform Service → Output Service → Queue Service
↓
PostgreSQL (shared database)
```

**Advantages**:
- Each service can scale independently
- Teams can work on services in parallel
- Easier to replace/upgrade individual services

**Disadvantages**:
- **4-6 additional weeks for infrastructure** (service mesh, API gateways, deployment automation)
- Network latency between services (multi-millisecond overhead vs. in-process)
- Each service needs its own health checks, logging, monitoring
- Debugging distributed system failures is 10x harder
- Overkill for MVP scale (<100 detections/sec)

**Why Rejected**: Timeline constraint. 8-12 week MVP timeline cannot absorb 4-6 week infrastructure tax.

### Alternative 2: Monolith with Separate Processes
**Architecture**:
```
API Service (FastAPI process)
Ingestion Polling Service (separate Python process)
Output Service (separate Python service)
All share PostgreSQL database
```

**Advantages**:
- Can scale individual components

**Disadvantages**:
- Cross-process communication complexity (queues, message passing)
- Shared database contention under load
- Debugging inter-process failures (race conditions, deadlocks)
- Not a clear path to microservices
- Still requires multiple health checks, monitoring

**Why Rejected**: Complexity without clear benefit. If scaling needed (Phase 2), microservices are cleaner.

---

## Consequences

### Positive

1. **Development Speed**: 2-3 team members can deliver MVP in 8-12 weeks
2. **Deployment Speed**: `docker build && docker push && kubectl apply` = live
3. **Debugging**: Stack traces show full call chain end-to-end
4. **Performance**: In-process calls have zero network latency
5. **Operational Simplicity**: One health check, one container, one database

### Negative

1. **Horizontal Scaling Limited**: If detection volume exceeds single container capacity, must redesign
2. **Component Independence**: All components share same process lifecycle (one crash affects all)
3. **Technology Lock-in**: All components must use same language/runtime

### Mitigations

1. **Clear Service Boundaries**: Hexagonal architecture with abstract ports enables future decomposition
2. **Performance Monitoring**: Track resource usage (CPU, memory, latency) to identify scaling need early
3. **Scalability Tests**: Load test to 1000+ detections/second to understand single-container limits
4. **Documented Decomposition Path**: ADRs document how to extract services to microservices (Phase 2)

---

## Evolution Path (Phase 2)

### When to Migrate to Microservices

**Trigger Conditions**:
- Single container hits CPU/memory limits at >500 detections/second
- Geolocation validation algorithm becomes compute-intensive
- Customer requirements demand geographic redundancy (separate instances in different regions)
- Team grows to >5 engineers (communication overhead of monolith increases)

### Migration Strategy

**Phase 2 Decomposition** (if triggered):
1. Extract GeolocationValidationService to separate container (most CPU-intensive)
2. Extract TACOutputService to separate container (handles network I/O)
3. Introduce message queue (RabbitMQ or Kafka) between services
4. Migrate database to PostgreSQL for multi-service consistency
5. Deploy with Kubernetes orchestration

**Code Reuse**: Hexagonal architecture ensures >80% of code remains unchanged. Only communication layer (HTTP/message queue) changes.

---

## Technology Choices Enabled by Monolith

### Single Container Benefits

1. **Shared State**: All components access same SQLite database without network overhead
2. **Atomic Operations**: Can wrap multiple service calls in single database transaction
3. **Shared Configuration**: All components read same environment variables, config files
4. **Shared Logging**: Single logging pipeline, easier to correlate events
5. **Single Health Check**: One endpoint reports system health (API, database, queues all in-process)

### Database Simplicity (MVP)

```
SQLite Database (local file)
├─ Detections table (current detections, validation results)
├─ Offline Queue table (PENDING_SYNC items)
├─ Audit Trail table (all events)
└─ Configuration table (sources, settings)
```

All components read/write same tables. No distributed transaction problems.

---

## Deployment Implications

### MVP Deployment (Single Container)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY src/ .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Single responsibility**: Run the entire application.

### Phase 2 Deployment (Microservices)

```yaml
# Each service gets separate deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: detection-api
spec:
  replicas: 3  # Horizontal scaling
  template:
    spec:
      containers:
      - name: detection-api
        image: detection-api:latest

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: geolocation-validation
spec:
  replicas: 5  # Can scale independent of API
  template:
    spec:
      containers:
      - name: validation
        image: geolocation-validation:latest
```

Clear separation from day 1, enabled by hexagonal architecture.

---

## Related Decisions

- **ADR-003**: Technology stack (Python + FastAPI enables rapid monolith development)
- **ADR-001**: Offline-first architecture (simplifies data consistency in monolith)

---

## References

- **MVP Timeline**: 8-12 weeks (DISCUSS wave summary)
- **Target Detection Volume**: <100 detections/second (MVP scope)
- **Team Size**: 2-3 engineers for MVP (fits monolith development model)

---

## Validation

**MVP Success Criteria**:
- [x] Single container deploys successfully
- [x] All 5 user stories functional in-process
- [x] Performance acceptable (<100ms ingestion, <2s API→map latency)
- [x] Hexagonal boundaries clear (enables future service extraction)

**Phase 2 Trigger**: If >500 detections/second sustained throughput needed or team >5 engineers
