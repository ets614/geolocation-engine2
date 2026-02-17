# ADR-001: Hexagonal Architecture for YDC Adapter

**Date**: 2026-02-17
**Status**: Accepted
**Decider**: Morgan (Solution Architect)

## Context

The YDC Adapter must integrate with multiple, variable data sources:
- **Inbound**: YOLO detections from YDC (WebSocket)
- **Outbound**:
  - Camera position from variable providers (Mock, DJI, MAVLink, future unknown sources)
  - Geolocation calculation via Geolocation-Engine2 API
  - Observability outputs (logging, metrics)

The system requires:
- Easy testing with mocks (no hardware dependencies)
- Clear separation between business logic and I/O details
- Future extensibility (new camera providers without core refactoring)
- Team can develop domain logic independently of adapter implementations

**Constraint**: Rapid MVP delivery (8-12 weeks). Architecture must not slow development.

## Decision

Implement **hexagonal architecture (ports and adapters pattern)** with three layers:

1. **Domain Layer** (innermost)
   - Pure business logic, no I/O
   - Testable in isolation without mocks or stubs
   - Examples: BboxUtils, DetectionTransformer, ResultAggregator

2. **Application/Orchestration Layer** (middle)
   - Coordinates domain logic with adapter calls
   - State machines, error handling, observability
   - Examples: YdcToGeoProcessingService, ErrorRecoveryService

3. **Adapter Layer** (outermost)
   - Implements abstract ports (interfaces)
   - Handles I/O, external system details
   - Primary adapters (WebSocket listener, HTTP health check)
   - Secondary adapters (camera provider, geolocation client, logging)

## Architecture Diagram

```
┌─────────────────────────────────────────┐
│  PRIMARY PORTS (Inbound)                │
│  • WebSocketListener                    │
│  • HealthCheckHandler                   │
└────────────┬────────────────────────────┘
             ↓
┌─────────────────────────────────────────┐
│  APPLICATION LAYER (Orchestration)      │
│  • YdcToGeoProcessingService            │
│  • ErrorRecoveryService                 │
│  • TelemetryCollector                   │
└────────────┬────────────────────────────┘
             ↓
┌─────────────────────────────────────────┐
│  DOMAIN LAYER (Pure Business Logic)     │
│  • BboxUtils                            │
│  • CameraAggregator                     │
│  • DetectionTransformer                 │
│  • ResultAggregator                     │
│  (NO I/O - testable without mocks)      │
└────────────┬────────────────────────────┘
             ↓
┌─────────────────────────────────────────┐
│  SECONDARY PORTS (Outbound Interfaces)  │
│  • CameraPositionProvider (abstract)    │
│  • GeolocationClient (abstract)         │
│  • ObservabilityPort (abstract)         │
└────────────┬────────────────────────────┘
             ↓
┌─────────────────────────────────────────┐
│  ADAPTERS (Concrete Implementations)    │
│  • MockCameraPositionAdapter            │
│  • DjiTelemetryAdapter (stub, Phase 2)  │
│  • MavlinkAdapter (stub, Phase 2)       │
│  • HttpGeolocationAdapter               │
│  • JsonLoggingAdapter                   │
└─────────────────────────────────────────┘
```

## Rationale

1. **Testability**: Domain layer has zero I/O dependencies. Unit tests require only pure function assertions, no fixtures or external services.
   - Example: `test_bbox_center_extraction()` computes pixel center in isolation
   - No mocks needed; no Docker containers required for local dev

2. **Extensibility**: New camera provider requires only one new adapter file
   - Adapter implements `CameraPositionProvider` interface
   - Zero changes to domain layer or orchestration
   - Team can work on Phase 2 (DJI adapter) while Phase 1 MVP ships

3. **Separation of Concerns**:
   - Domain owns: "How do I extract the detection's center pixel and prepare the geolocation request?"
   - Application owns: "If the camera provider fails, should I retry?"
   - Adapter owns: "How do I call this specific DJI API endpoint?"

4. **Maintainability**: Clear boundaries reduce cognitive load. New team member can:
   - Learn domain logic from unit tests (pure functions)
   - Understand error handling from orchestration layer
   - Implement new adapter without touching domain

5. **Testability Hierarchy**:
   - **Unit (Domain)**: Fastest, no fixtures, instant feedback
   - **Service (Orchestration)**: Mocked adapters, clear state transitions
   - **Integration**: Real adapters, Docker Compose
   - **E2E**: Full stack against live Geolocation-Engine2

## Alternatives Considered

### Alternative 1: Layered Architecture (Controller → Service → Model)
```
WebSocket Handler
    ↓
DetectionService
    ↓
DetectionModel
    ↓
[Database]
```

**Why Rejected**:
- Business logic tightly coupled to I/O (camera provider, Geolocation-Engine2)
- Testing domain requires stubbing external services (mocks needed)
- Adding new camera provider requires modifying DetectionService (violates OCP)
- Less testable: unit tests unavoidable depend on mocks

**Evidence**: Layered architecture works for CRUD apps; breaks with multiple variable data sources

### Alternative 2: Event-Driven Architecture (Pub/Sub with Message Queue)
```
YDC WebSocket
    → (detection event)
Kafka/RabbitMQ
    → (detection consumed by multiple subscribers)
    → Geolocation Subscriber
    → TAK Subscriber
```

**Why Rejected**:
- Adds latency: event → queue → processing → result (defeats <200ms latency target)
- Adds operational complexity: Kafka/RabbitMQ to manage
- Overkill for MVP: asynchronous handling of TAK push already handled by Geolocation-Engine2
- Simple synchronous REST call adequate

**Evidence**: Event-driven suits high-volume decoupling; MVP has tight latency requirement

### Alternative 3: Monolithic (All-in-One)
Embed YDC adapter logic directly in Geolocation-Engine2 (single service).

**Why Rejected**:
- Violates single responsibility: Geolocation-Engine2 handles geolocation + TAK push
- YDC Adapter adds orchestration, camera position aggregation (separate concern)
- Harder to test: must start entire Geolocation-Engine2 stack for YDC tests
- Harder to scale: YDC-specific logic couples to geolocation-specific logic
- Limits future reuse: if YDC need to call different geolocation provider, can't swap easily

**Evidence**: Separation of concerns; independent deployment flexibility

## Consequences

### Positive

1. **Fast unit testing**: Domain tests run in <1 second (pure functions), instant developer feedback during TDD
2. **Clear extension mechanism**: New camera provider (DJI, MAVLink) = new adapter file + 1-2 unit tests; zero impact on core logic
3. **Team parallelization**: Phase 1 crew works on MVP domain; Phase 2 crew starts DJI adapter stub independently
4. **Debuggable**: Stack traces, logs clearly indicate which layer failed (adapter, orchestration, or domain)
5. **Reusable domain logic**: BboxUtils, DetectionTransformer could be ported to other systems (e.g., batch processing pipeline) without I/O cruft

### Negative

1. **Slight complexity increase**: More files, more interfaces. 15-20 Python files vs 5-8 in simpler design
2. **Interface indirection**: To understand adapter behavior, must read interface contract (minimal doc overhead)
3. **Learning curve**: Team less familiar with ports/adapters pattern; upfront training cost (~2-4 hours)

**Mitigation for negatives**:
- Provide clear examples in architecture documentation ✓ (this doc)
- Use clear naming conventions (Provider, Adapter suffixes) ✓
- Minimal interface complexity (2-3 methods per port) ✓

## Implementation Notes

### Domain Layer Files
```
src/domain/
  ├── models.py (DetectionPixelCoordinates, CameraPosition, etc.)
  ├── bbox_utils.py (pure functions for pixel math)
  ├── detection_transformer.py (YDC → Geolocation schema)
  └── result_aggregator.py (parse geolocation response)
```

### Orchestration Layer Files
```
src/services/
  ├── ydc_to_geo_processing_service.py (main orchestrator)
  ├── error_recovery_service.py (retry logic)
  └── telemetry_collector.py (observability)
```

### Port/Adapter Layer Files
```
src/ports/
  ├── camera_position_provider.py (abstract port)
  └── geolocation_client.py (abstract port)

src/adapters/
  ├── camera_position/
  │   ├── mock_adapter.py (Phase 1)
  │   ├── dji_adapter.py (Phase 2, stub)
  │   └── mavlink_adapter.py (Phase 2, stub)
  ├── geolocation/
  │   └── http_client_adapter.py (REST client)
  └── observability/
      └── json_logging_adapter.py
```

### Dependency Injection Pattern
```python
# src/main.py
from src.config import get_config
from src.adapters.camera_position import MockCameraPositionAdapter
from src.adapters.geolocation import HttpGeolocationAdapter

config = get_config()

# Instantiate based on config
if config.camera_provider_type == "mock":
    camera_provider = MockCameraPositionAdapter(config.mock_lat, config.mock_lon)
elif config.camera_provider_type == "dji":
    camera_provider = DjiTelemetryAdapter(config.dji_api_url)
else:
    raise ValueError(f"Unknown provider: {config.camera_provider_type}")

# Inject into orchestration layer
geolocation_client = HttpGeolocationAdapter(config.geolocation_api_url)
processing_service = YdcToGeoProcessingService(
    camera_provider=camera_provider,
    geolocation_client=geolocation_client
)

# Use in FastAPI route
@app.websocket("/ws/ydc")
async def websocket_endpoint(websocket: WebSocket):
    await processing_service.handle_websocket(websocket)
```

## Testing Strategy

### Unit Tests (Domain Layer)
- **Target**: 95%+ coverage
- **Approach**: No mocks, no fixtures, only pure functions
- Example: `test_extract_bbox_center()` — asserts pixel math

### Service Tests (Orchestration Layer)
- **Target**: 90%+ coverage
- **Approach**: Mock adapters (in-memory implementations)
- Example: `test_retry_on_provider_failure()` — mock provider throws, assert retry logic

### Integration Tests
- **Target**: 75%+ coverage
- **Approach**: Real adapters, Docker Compose stack (Mock Geolocation-Engine2)
- Example: `test_e2e_detection_processing()` — full flow with mocked backend

## Validation Criteria

- [ ] No domain layer module imports from adapters
- [ ] All primary ports have at least 2 adapters (one real, one mock/test)
- [ ] Orchestration layer decoupled from specific adapters (dependency injection working)
- [ ] New adapter (DJI in Phase 2) requires <200 LOC
- [ ] Domain tests run in <1 second (no external calls)
- [ ] Error paths tested: at least 5 error scenarios per service

## References

- Alistair Cockburn, "Hexagonal Architecture" (2005)
- Robert C. Martin, "Clean Architecture" (2017)
- This project's existing Geolocation-Engine2 (similar hexagonal pattern used)

