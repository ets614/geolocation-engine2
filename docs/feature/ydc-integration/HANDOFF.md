# YDC ↔ Geolocation-Engine2 Adapter - Handoff to Acceptance Designer

**From**: Morgan (Solution Architect)
**To**: Acceptance Designer, Software Crafter
**Date**: 2026-02-17
**Status**: DESIGN WAVE COMPLETE → Ready for DISTILL Wave

---

## Quick Start for Acceptance Designer

This document summarizes architecture decisions and integration points. Full details in `architecture-design.md` and ADRs.

### What Was Designed

A **stateless microservice** (YDC Adapter) that bridges YOLO object detection (WebSocket) with Geolocation-Engine2 API.

```
YDC (YOLO detections)
  ↓ WebSocket /ws/ydc
YDC Adapter (this service)
  ├─ Extract pixel center from bbox
  ├─ Fetch camera position (pluggable provider)
  └─ Call Geolocation-Engine2 API
     ↓ POST /api/v1/detections
     Geolocation-Engine2
     ├─ Photogrammetry calculation
     ├─ CoT XML generation
     ├─ TAK server push (async)
     └─ Offline queue (if TAK offline)
```

**Result**: YDC client receives geolocation + confidence via WebSocket

---

## Architecture at a Glance

### Style: Hexagonal (Ports & Adapters)

**Domain Layer** (Pure Business Logic)
- Extract pixel center from YOLO bbox
- Transform detection to Geolocation-Engine2 schema
- Parse CoT XML response

**Orchestration Layer** (Coordination)
- WebSocket listener
- Error recovery (retry with backoff)
- Observability (logging, metrics)

**Adapter Layer** (I/O)
- **Primary**: WebSocket listener, HTTP health endpoint
- **Secondary**:
  - Camera position provider (abstract port; implementations: Mock, DJI, MAVLink)
  - Geolocation-Engine2 REST client
  - Structured logging

### Key Decision: Separate Microservice
- YDC Adapter runs standalone (port 8001)
- Calls Geolocation-Engine2 via REST (port 8000)
- No shared database (stateless)
- Reasons: Independent testing, scaling, deployment

**See**: `ADR-002-separate-service.md` for detailed rationale

---

## Critical Integration Points

### 1. Geolocation-Engine2 API Contract

**Endpoint**: `POST /api/v1/detections`

**Request** (from YDC Adapter):
```json
{
  "image_base64": "iVBORw0KGgo...",
  "pixel_x": 512,
  "pixel_y": 384,
  "object_class": "vehicle",
  "ai_confidence": 0.92,
  "source": "ydc_adapter",
  "camera_id": "mock_camera_001",
  "timestamp": "2026-02-17T14:35:42Z",
  "sensor_metadata": {
    "location_lat": 40.7128,
    "location_lon": -74.0060,
    "location_elevation": 100.0,
    "heading": 45.0,
    "pitch": -30.0,
    "roll": 0.0,
    "focal_length": 3000.0,
    "sensor_width_mm": 6.4,
    "sensor_height_mm": 4.8,
    "image_width": 1920,
    "image_height": 1440
  }
}
```

**Response** (from Geolocation-Engine2): HTTP 201 CoT XML
```xml
<?xml version="1.0" encoding="UTF-8"?>
<event version="2.0" uid="550e8400-e29b-41d4"
       time="2026-02-17T14:35:42Z" type="b-m-p-s-u-c">
    <point lat="40.7135" lon="-74.0050" hae="100.0"
           ce="9999999.0" le="9999999.0"/>
    <detail>
        <usericon iconsetpath="COT_MAPPING_SAR/Ground Equipment.png"/>
        <color value="-65536"/>
        <archive value="false"/>
        <contact callsign="YOLO-0001"/>
    </detail>
</event>
```

**Headers**:
- `X-Detection-ID: 550e8400-e29b-41d4`
- `X-Confidence-Flag: GREEN | YELLOW | RED`

**Status Codes**:
- 201: Success (CoT XML in body)
- 400: Invalid request (pixel out of bounds, missing fields)
- 500: Server error (geolocation calc failed)

**Auth** (Optional):
- YDC Adapter must pass API key or JWT token if Geolocation-Engine2 configured
- Config: `GEOLOCATION_API_KEY` env var
- Header: `X-API-Key: {key}` or `Authorization: Bearer {jwt}`

### 2. YDC Input (WebSocket Message Format)

**Endpoint**: `WS /ws/ydc`

**Message IN** (from YDC):
```json
{
  "frame_id": "ydc-frame-20260217-143542-001",
  "timestamp": "2026-02-17T14:35:42Z",
  "detections": [
    {
      "object_id": 0,
      "class_name": "vehicle",
      "confidence": 0.94,
      "x_min": 100,
      "y_min": 50,
      "x_max": 450,
      "y_max": 280
    },
    {
      "object_id": 1,
      "class_name": "person",
      "confidence": 0.87,
      "x_min": 500,
      "y_min": 200,
      "x_max": 600,
      "y_max": 400
    }
  ]
}
```

**Message OUT** (from YDC Adapter):
```json
{
  "frame_id": "ydc-frame-20260217-143542-001",
  "detection_id": "550e8400-e29b-41d4",
  "geolocation": {
    "calculated_lat": 40.7135,
    "calculated_lon": -74.0050,
    "confidence_flag": "GREEN",
    "confidence_value": 0.85,
    "uncertainty_radius_meters": 15.5
  },
  "cot_xml": "<?xml version=\"1.0\"...?>",
  "status": "success",
  "error_message": null,
  "latency_ms": 125
}
```

**Error Message OUT** (if geolocation fails):
```json
{
  "frame_id": "ydc-frame-20260217-143542-001",
  "detection_id": null,
  "geolocation": null,
  "cot_xml": null,
  "status": "error",
  "error_message": "Camera position provider unavailable (max retries exceeded)",
  "latency_ms": 9000
}
```

### 3. Camera Position Provider Interface

**Abstract Port** (to be implemented by adapters):
```python
class CameraPositionProvider(ABC):
    async def get_position(frame_id: str) -> CameraPosition
    async def health_check() -> bool
```

**Mock Implementation** (Phase 1):
- Fixed position: Always returns same lat/lon/elevation
- Randomized: Adds ±0.001° noise (~100m)

**Future Implementations**:
- **DJI** (Phase 2): Call DJI Telem API
- **MAVLink** (Phase 2): Listen to serial MAVLink stream

---

## Component Boundaries (What Software Crafter Will Build)

### Layer 1: Domain (Pure Business Logic)
```
src/domain/
├── models.py
│   ├── DetectionPixelCoordinates
│   ├── CameraPosition
│   └── DetectionResult
├── bbox_utils.py
│   └── extract_pixel_center(x_min, y_min, x_max, y_max) → (pixel_x, pixel_y)
├── detection_transformer.py
│   └── transform_ydc_to_geolocation_request(...) → GeolocationApiRequest
└── result_aggregator.py
    └── parse_cot_response(xml_string) → Geolocation
```

**Testing**: Pure unit tests, no mocks needed (fast, clear failures)

### Layer 2: Orchestration (State Machines & Error Handling)
```
src/services/
├── ydc_to_geo_processing_service.py
│   └── YdcToGeoProcessingService
│       ├── handle_ydc_frame(frame) → response
│       ├── State machine: validate → fetch_position → call_geo → aggregate_result
│       └── Routes errors to ErrorRecoveryService
├── error_recovery_service.py
│   └── ErrorRecoveryService
│       ├── retry_with_backoff(fn, max_retries=3)
│       ├── Backoff: 1s, 2s, 4s (exponential)
│       └── Respects HTTP 429 (rate limit)
└── telemetry_collector.py
    └── TelemetryCollector
        ├── track_frame_received()
        ├── track_latency(ms)
        ├── track_error(error_type)
        └── health_status() → {"frames": 1234, "errors": 5, ...}
```

**Testing**: Service tests with mocked adapters; test state transitions and error paths

### Layer 3: Adapters (I/O Implementation)
```
src/adapters/
├── camera_position/
│   ├── __init__.py (factory)
│   ├── mock_adapter.py (Phase 1)
│   │   └── MockCameraPositionAdapter(fixed_lat, fixed_lon, fixed_elevation, randomize=False)
│   ├── dji_adapter.py (Phase 2, stub)
│   │   └── DjiTelemetryAdapter(api_url, api_key)
│   └── mavlink_adapter.py (Phase 2, stub)
│       └── MavlinkAdapter(device, baudrate)
├── geolocation/
│   └── http_client_adapter.py
│       └── HttpGeolocationAdapter(base_url, api_key=None, jwt_token=None)
│           ├── async post_detection(request) → CoT XML
│           ├── retry_with_backoff (built-in)
│           └── rate_limit_handling (429 backoff)
└── observability/
    └── json_logging_adapter.py
        └── JsonLoggingAdapter(logger_name)
            ├── log_info(msg, context_dict)
            ├── log_error(msg, exception)
            └── Outputs JSON to stdout (container logs)
```

**Testing**: Integration tests with mocked external services; load tests for adapters

### Layer 4: Primary Adapters (FastAPI Endpoints)
```
src/
├── main.py
│   └── FastAPI app setup, middleware, dependency injection
├── routes.py
│   ├── @app.websocket("/ws/ydc")
│   │   └── websocket_endpoint(websocket) — delegates to YdcToGeoProcessingService
│   └── @app.get("/api/v1/health")
│       └── health_check() → {"status": "running", "version": "1.0.0", ...}
└── middleware.py
    ├── CORS setup
    ├── Exception handlers (400, 404, 500)
    └── Request/response logging
```

---

## Acceptance Criteria (What Acceptance Designer Will Validate)

### Functional Acceptance Criteria

**AC-001: YDC Frame Processing**
- Given a YOLO detection frame (N bounding boxes)
- When YDC Adapter receives via WebSocket
- Then each detection is processed and replied with geolocation result
- *Criteria*: Response received within 500ms, status="success"

**AC-002: Pixel Center Extraction**
- Given bbox {x_min=100, y_min=50, x_max=450, y_max=280}
- When extracted
- Then pixel_x=275, pixel_y=165 (correct center)
- *Criteria*: Pixel math validated via unit tests

**AC-003: Camera Position Aggregation**
- Given camera provider (mock)
- When position requested
- Then CameraPosition object returned with lat, lon, elevation, heading, pitch, roll
- *Criteria*: All fields populated, in valid ranges

**AC-004: Geolocation-Engine2 Integration**
- Given detection ready for geolocation
- When POSTed to Geolocation-Engine2 API
- Then CoT XML response received with geolocation + confidence
- *Criteria*: HTTP 201, valid XML, lat/lon populated

**AC-005: Error Handling - Provider Unavailable**
- Given camera provider unreachable
- When YDC frame arrives
- Then adapter retries 3x with exponential backoff
- Then error response sent to YDC within 10 seconds
- *Criteria*: Status="error", error_message populated, no hanging

**AC-006: Error Handling - Geolocation Service Offline**
- Given Geolocation-Engine2 offline
- When adapter tries to POST detection
- Then retries 3x with backoff
- Then error response sent after retries exhausted
- *Criteria*: Fails gracefully, no server crash

**AC-007: Rate Limiting Respect**
- Given Geolocation-Engine2 returns HTTP 429
- When adapter detects rate limit
- Then backs off exponentially (1s, 2s, 4s)
- Then retries until succeeds
- *Criteria*: Respects 429, doesn't flood service

**AC-008: Health Check Endpoint**
- Given GET /api/v1/health
- When called
- Then HTTP 200 returned
- With body: {"status": "running", "version": "1.0.0", "frames_processed": N, "errors": M}
- *Criteria*: Response <100ms

### Non-Functional Acceptance Criteria

**Performance**
- Median latency: <150ms (frame in → response out)
- p99 latency: <300ms
- Throughput: 100+ detections/second (single instance)
- Memory: <500MB resident

**Reliability**
- No memory leaks over 24h continuous operation
- No infinite loops or deadlocks
- Error recovery: <10 seconds (retry exhaustion)

**Scalability**
- Stateless: Can spin up 5 instances without coordination
- Load balancer ready: WebSocket routing to multiple instances
- Connection pooling: Reuses HTTP connections to Geolocation-Engine2

**Observability**
- All errors logged with frame_id context
- Latency metrics: min, p50, p99, max per minute
- Error rate trending: errors/total requests

**Security**
- API key/JWT passed through to Geolocation-Engine2
- No secrets logged
- CORS configured appropriately

---

## Test Strategy for Acceptance Designer

### Test Layers

1. **Unit Tests** (Domain layer)
   - ~35 tests, all pure functions
   - Target: 95%+ coverage
   - Examples: BboxUtils (pixel center), DetectionTransformer (schema mapping)
   - Run time: <1 second

2. **Service Tests** (Orchestration layer)
   - ~40 tests, mocked adapters
   - Target: 90%+ coverage
   - Examples: Retry logic, error paths, state transitions
   - Run time: <5 seconds

3. **Integration Tests**
   - ~15 tests, real adapters + mock Geolocation-Engine2
   - Target: 75%+ coverage
   - Examples: E2E detection processing, WebSocket roundtrip
   - Run time: <30 seconds

4. **Load Tests**
   - 1-2 tests, 100+ det/sec sustained
   - Target: <150ms p50, <300ms p99 latency
   - Duration: 60+ seconds
   - Run time: ~2 minutes

5. **End-to-End Tests** (Acceptance Designer's domain)
   - Full stack: YDC Adapter + Geolocation-Engine2 + Mock TAK
   - Real YDC WebSocket client simulator
   - Gherkin scenarios (BDD format)
   - Manual or automated (robot framework)

### Example Test Scenarios (BDD)

```gherkin
Feature: YDC Detection Processing

  Scenario: Successful geolocation of vehicle detection
    Given a YOLO detection frame with 1 vehicle bbox (confidence 0.94)
    And camera position provider is mock (lat 40.7128, lon -74.0060)
    And Geolocation-Engine2 is healthy
    When YDC Adapter receives the frame via WebSocket
    Then adapter extracts pixel center (275, 165)
    And calls Geolocation-Engine2 API
    And receives CoT XML with geolocation
    And replies to YDC with status "success" and lat/lon
    And latency is <200ms

  Scenario: Error recovery when camera provider unavailable
    Given a YOLO detection frame
    And camera provider is offline (TCP timeout)
    When YDC Adapter receives the frame
    Then adapter retries camera position 3 times with backoff
    And error response sent to YDC within 10 seconds
    And error_message describes provider unavailability

  Scenario: Handle Geolocation-Engine2 rate limit
    Given Geolocation-Engine2 has rate limit (100 req/sec)
    And YDC sends 150 frames/sec continuously
    When adapter detects HTTP 429
    Then adapter backs off (1s, 2s, 4s)
    And retries until service recovers
    And frames buffered in adapter (not dropped)
    And no request loop flood

  Scenario: Multiple detections per frame
    Given a YOLO detection frame with 3 objects (vehicle, person, person)
    When YDC Adapter receives the frame
    Then each detection geolocated independently
    And all 3 responses sent back to YDC
    And processing completes within 500ms
```

---

## Deployment & Environment Setup

### Local Development (docker-compose.yml)
```bash
docker-compose up
# Starts:
# - Geolocation-Engine2 on port 8000
# - YDC Adapter on port 8001
# - Mock TAK server on port 1080
# - Data volumes for persistence

# Test YDC Adapter:
wscat -c ws://localhost:8001/ws/ydc
# Send test frame JSON

# Test health:
curl http://localhost:8001/api/v1/health
```

### Docker Image Build
```bash
docker build -t ydc-adapter:latest .
docker run -p 8001:8001 \
  -e GEOLOCATION_API_URL=http://localhost:8000 \
  -e CAMERA_PROVIDER_TYPE=mock \
  ydc-adapter:latest
```

### Environment Variables
```bash
# Required
FASTAPI_ENV=development|production
GEOLOCATION_API_URL=http://geolocation-engine2:8000

# Camera Provider
CAMERA_PROVIDER_TYPE=mock|dji|mavlink
MOCK_LAT=40.7128
MOCK_LON=-74.0060
MOCK_ELEVATION=100.0

# Geolocation Authentication (optional)
GEOLOCATION_API_KEY=your-api-key
GEOLOCATION_JWT_TOKEN=your-jwt-token

# Observability
LOG_LEVEL=DEBUG|INFO|WARNING|ERROR
```

---

## Key Files Delivered

### Architecture Documentation
- **architecture-design.md** (18 sections, 8,000+ words)
  - System context, component boundaries, C4 diagrams
  - Data models, integration patterns
  - Error handling, scalability, testing strategy

### Architecture Decision Records (ADRs)
- **ADR-001-hexagonal-architecture.md**
  - Why hexagonal pattern, not layered
  - Port/adapter separation benefits

- **ADR-002-separate-service.md**
  - Why separate microservice, not embedded
  - Independent deployment, testing, scaling rationale

- **ADR-003-004-005-006-007.md** (in architecture-design.md)
  - Sync REST (not async queue)
  - Pluggable providers interface
  - Stateless design
  - Python + FastAPI consistency
  - Mock provider for MVP

### Configuration & Deployment
- **docker-compose.yml** (template provided in architecture doc)
- **Dockerfile** (template provided in architecture doc)
- **requirements.txt** (template, dependencies to be finalized by crafter)

### Testing Artifacts
- **test-strategy.md** (in architecture doc)
  - Layers, coverage targets, example scenarios

---

## Known Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Geolocation-Engine2 unavailable | Medium | High | Retry logic, error response to YDC, monitoring |
| Network latency spike | Low | Low | Connection pooling, timeout protection (5s) |
| WebSocket disconnects | Low | Medium | Graceful close, client reconnect expected |
| Camera provider API changes | Low | Medium | Abstract port, adapter isolation, versioning |
| Rate limit exhaustion | Medium | Low | Backoff respects 429, queue local detection buffer |
| Memory leak | Low | Medium | 24h monitoring, resource cleanup tests |

---

## Phase Roadmap (Informational)

### Phase 1: MVP (Weeks 1-8, This Delivery)
- [x] Hexagonal architecture designed
- [ ] Domain layer implemented (crafter)
- [ ] Orchestration layer implemented (crafter)
- [ ] Mock camera provider implemented (crafter)
- [ ] HTTP Geolocation adapter implemented (crafter)
- [ ] 95 tests written (crafter + acceptance designer)
- [ ] Docker image built (DevOps)
- [ ] docker-compose local dev setup (DevOps)
- [ ] UAT with mock Geolocation-Engine2 (acceptance designer)

### Phase 2: Production Ready (Weeks 9-16)
- [ ] DJI camera provider (hardware integration test)
- [ ] MAVLink camera provider (serial integration test)
- [ ] PostgreSQL migration (shared database, if needed)
- [ ] Kubernetes deployment (multi-instance scaling)
- [ ] Prometheus metrics (monitoring, alerting)
- [ ] Load testing to 500+ det/sec

### Phase 3+: Enhancement
- [ ] Multi-region deployment
- [ ] Service mesh (Istio/Linkerd)
- [ ] Alternative geolocation backends

---

## Questions for Acceptance Designer

1. **Test Automation**: BDD framework preference (Gherkin + behave, robot framework, pytest-bdd)?
2. **Load Testing**: Target throughput for MVP? (100 det/sec assumed; adjust if different)
3. **Hardware**: Dev/staging machine specs for performance validation?
4. **Monitoring**: CloudWatch, Prometheus, ELK stack for observability?
5. **Deployment**: Target environment (AWS, GCP, on-prem)? Kubernetes timeline?
6. **Integration Timeline**: When will real YDC be available for testing? (Mock assumed for MVP)

---

## How to Use This Handoff

**For Software Crafter**:
1. Read `architecture-design.md` (sections 1-6, 14-16 most important)
2. Read `ADR-001` + `ADR-002` (understand why architecture chosen)
3. Implement domain layer from section 4 (data models)
4. Implement orchestration layer from section 2 (component details)
5. Implement adapters from section 7 (pluggable providers)
6. Write tests from section 11 (test strategy)

**For Acceptance Designer**:
1. Skim `architecture-design.md` (sections 3, 5, 10, 12-13 most important)
2. Review acceptance criteria (in `architecture-design.md` section 13)
3. Write BDD test scenarios (above in "Test Strategy")
4. Set up test infrastructure (docker-compose, test framework)
5. Validate against quality attributes (performance, reliability, observability)
6. Sign off on peer review (see below)

**For Peer Reviewer** (Morgan → Atlas):
- See `PEER_REVIEW_REQUEST.md` (separate document)

---

## Peer Review Status

**Status**: Pending (to be scheduled)

**Review Criteria**:
- [ ] Bias detection (no unjustified assumptions)
- [ ] ADR quality (at least 2 alternatives per decision)
- [ ] Completeness (all sections covered)
- [ ] Feasibility (team can implement in 8-12 weeks)
- [ ] Alignment with org patterns (consistent with Geolocation-Engine2)

**Timeline**: Review scheduled within 3 working days

---

**Next Step**: Reviewer approval → Software Crafter begins BUILD wave

