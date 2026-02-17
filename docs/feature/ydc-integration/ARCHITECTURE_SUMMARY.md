# YDC ↔ Geolocation-Engine2 Adapter - Architecture Quick Reference

**Visual summary of architecture design. For detailed documentation, see architecture-design.md**

---

## System Context Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│              YDC ↔ GEOLOCATION-ENGINE2 ADAPTER SYSTEM           │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐                                               │
│  │   YOLO       │                                               │
│  │  Detector    │──WebSocket──────────────┐                     │
│  │  (YDC)       │  Detections (bboxes)    │                     │
│  └──────────────┘                         │                     │
│                                           ↓                     │
│                                ┌──────────────────────────┐     │
│                                │ YDC ADAPTER SERVICE      │     │
│                                │ (Standalone Container)   │     │
│                                │                          │     │
│                                │ ┌────────────────────┐   │     │
│                                │ │ • Extract bbox     │   │     │
│                                │ │   center pixel     │   │     │
│                                │ │ • Request camera   │   │     │
│                                │ │   position         │   │     │
│                                │ │ • Call Geolocation │   │     │
│                                │ │   API              │   │     │
│                                │ │ • Reply result     │   │     │
│                                │ └────────────────────┘   │     │
│                                └──────┬───────────────────┘     │
│                                       │ (REST POST)  │          │
│                                       ↓             ↓           │
│                            ┌─────────────────┐  ┌──────────┐   │
│                            │ Geolocation-    │  │  YDC     │   │
│                            │ Engine2         │  │  Client  │   │
│                            │                 │  │ (Reply)  │   │
│                            │ • Photogrammetry│  └──────────┘   │
│                            │ • CoT XML gen   │                 │
│                            │ • TAK async push│                 │
│                            └────────┬────────┘                 │
│                                     ↓ (async)                  │
│                            ┌──────────────────┐                │
│                            │  TAK Server      │                │
│                            │  (CoT sink)      │                │
│                            └──────────────────┘                │
│                                                                 │
│  ┌──────────────────┐       ┌──────────────────┐               │
│  │ Camera Position  │       │ Telemetry        │               │
│  │ Provider:        │───→   │ (Optional)       │               │
│  │ • Mock (Phase 1) │       │ • DJI SDK        │               │
│  │ • DJI (Phase 2)  │       │ • MAVLink        │               │
│  │ • MAVLink (Ph 2) │       │ • Custom         │               │
│  └──────────────────┘       └──────────────────┘               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Hexagonal Architecture Layers

```
┌────────────────────────────────────────────────────────────┐
│  INBOUND (Primary Ports)                                   │
│                                                            │
│  ┌──────────────────┐        ┌──────────────────┐         │
│  │ WebSocket        │        │ Health Check     │         │
│  │ Listener         │        │ HTTP Endpoint    │         │
│  │ /ws/ydc          │        │ GET /health      │         │
│  └────────┬─────────┘        └────────┬─────────┘         │
│           │                          │                     │
└───────────┼──────────────────────────┼─────────────────────┘
            ↓                          ↓
┌────────────────────────────────────────────────────────────┐
│  APPLICATION LAYER (Orchestration & Coordination)          │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ YdcToGeoProcessingService (State Machine)           │ │
│  │ • Idle → Validate → Fetch Position → Call Geo      │ │
│  │ • Aggregate Result → Reply                          │ │
│  │ • Route errors to ErrorRecoveryService              │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  ┌────────────────────┐  ┌──────────────────────────────┐ │
│  │ ErrorRecoveryService
│  │ • Retry with expo  │  │ TelemetryCollector           │ │
│  │   backoff (1,2,4s) │  │ • Frame counter              │ │
│  │ • Handle 429       │  │ • Latency histogram          │ │
│  │ • Circuit breaker  │  │ • Error rate                 │ │
│  │ • Max 3 retries    │  │ • Provider stats             │ │
│  └────────────────────┘  └──────────────────────────────┘ │
│                                                            │
└───────────────┬────────────────────────────────┬──────────┘
                ↓                                ↓
┌────────────────────────────────────────────────────────────┐
│  DOMAIN LAYER (Pure Business Logic — NO I/O)              │
│                                                            │
│  ┌────────────────────┐  ┌──────────────────────────────┐ │
│  │ BboxUtils          │  │ DetectionTransformer         │ │
│  │                    │  │                              │ │
│  │ • Validate bounds  │  │ • YDC frame → Geo schema    │ │
│  │ • Extract center   │  │ • Map fields                 │ │
│  │   pixel_x = (x_min │  │ • Set defaults              │ │
│  │              + x_max)│ │   (focal_length, sensor)    │ │
│  │              / 2   │  │ • Validate ranges           │ │
│  │                    │  │                              │ │
│  └────────────────────┘  └──────────────────────────────┘ │
│                                                            │
│  ┌────────────────────┐  ┌──────────────────────────────┐ │
│  │ CameraAggregator   │  │ ResultAggregator             │ │
│  │                    │  │                              │ │
│  │ • Calls provider   │  │ • Parse CoT XML              │ │
│  │   abstract port    │  │ • Extract lat, lon, conf     │ │
│  │ • Validates pos    │  │ • Build response             │ │
│  │ • Handles None     │  │ • Calc latency               │ │
│  │                    │  │                              │ │
│  └────────────────────┘  └──────────────────────────────┘ │
│                                                            │
│  [All functions testable in isolation, no mocks needed]   │
│                                                            │
└─────────┬────────────────────────────────────────────┬────┘
          ↓                                            ↓
┌────────────────────────────────────────────────────────────┐
│  SECONDARY PORTS (Outbound Interfaces)                     │
│                                                            │
│  ┌──────────────────────┐  ┌────────────────────────────┐ │
│  │ CameraPositionProvider
│  │ (Abstract Interface) │  │ GeolocationClient          │ │
│  │                      │  │ (Abstract Interface)       │ │
│  │ async get_position() │  │                            │ │
│  │ async health_check() │  │ async post_detection()     │ │
│  │                      │  │                            │ │
│  └──────────────────────┘  └────────────────────────────┘ │
│                                                            │
└─────────┬──────────────────────────────────────────────┬──┘
          ↓                                              ↓
┌─────────────────────────────────────────────────────────────┐
│  ADAPTERS (Concrete I/O Implementations)                    │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Camera Position Adapters                             │  │
│  │                                                      │  │
│  │ • MockCameraPositionAdapter (Phase 1)               │  │
│  │   - Fixed position: returns {lat, lon, elevation}   │  │
│  │   - Randomized: adds ±0.001° noise (~100m)          │  │
│  │                                                      │  │
│  │ • DjiTelemetryAdapter (Phase 2, stub)               │  │
│  │   - Calls DJI Telem API                             │  │
│  │   - Maps DJI response to CameraPosition             │  │
│  │                                                      │  │
│  │ • MavlinkAdapter (Phase 2, stub)                    │  │
│  │   - Listens to MAVLink serial stream                │  │
│  │   - Parses GLOBAL_POSITION_INT messages             │  │
│  │                                                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Geolocation Adapters                                 │  │
│  │                                                      │  │
│  │ • HttpGeolocationAdapter                            │  │
│  │   - httpx async HTTP client                         │  │
│  │   - POST /api/v1/detections                         │  │
│  │   - Connection pooling (reuse TCP conns)            │  │
│  │   - Retry + backoff built-in                        │  │
│  │   - Handles 429 rate limit                          │  │
│  │   - Parse CoT XML response                          │  │
│  │                                                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Observability Adapters                               │  │
│  │                                                      │  │
│  │ • JsonLoggingAdapter                                │  │
│  │   - Python stdlib logging                           │  │
│  │   - JSON formatter (for container logs)             │  │
│  │   - Stdout (container log aggregation)              │  │
│  │   - Prometheus-compatible metrics (optional)        │  │
│  │                                                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
└──────────┬────────────────────────────────────────────────┬─┘
           ↓                                                ↓
           │                                                │
    ┌──────────────┐                               ┌────────────────┐
    │ DJI Telemetry│                               │ Geolocation-   │
    │ / MAVLink    │                               │ Engine2 API    │
    │ (External)   │                               │ (Port 8000)    │
    └──────────────┘                               └────────────────┘
```

---

## Data Flow: Happy Path

```
┌─────────────────────────────────────────────────────────────┐
│  TIME SEQUENCE (Successful Detection Processing)            │
└─────────────────────────────────────────────────────────────┘

YDC Client          YDC Adapter             Geo-Engine2    Camera
   │                   │                        │          Provider
   │                   │                        │              │
   │ 1. WebSocket      │                        │              │
   │    frame          │                        │              │
   ├──────────────────→│                        │              │
   │  {bbox: ...}      │                        │              │
   │                   │                        │              │
   │                   │ 2. Validate bbox       │              │
   │                   │                        │              │
   │                   │ 3. Get camera pos      │              │
   │                   ├──────────────────────────────────────→│
   │                   │                        │     {lat, lon,│
   │                   │←──────────────────────────────────────┤
   │                   │                        │    elevation} │
   │                   │                        │              │
   │                   │ 4. Transform frame     │              │
   │                   │                        │              │
   │                   │ 5. POST detection      │              │
   │                   ├──────────────────────→│              │
   │                   │ {pixel_x, pixel_y,    │              │
   │                   │  camera_metadata}     │              │
   │                   │                        │              │
   │                   │            Photogrammetry calc        │
   │                   │            CoT XML generation         │
   │                   │            TAK push (async)           │
   │                   │                        │              │
   │                   │ 6. 201 CoT XML        │              │
   │                   │←──────────────────────┤              │
   │                   │                        │              │
   │                   │ 7. Parse & aggregate  │              │
   │                   │                        │              │
   │ 8. WebSocket      │                        │              │
   │    response       │                        │              │
   │←──────────────────┤                        │              │
   │ {geolocation,     │                        │              │
   │  status: ok,      │                        │              │
   │  latency_ms: 125} │                        │              │
   │                   │                        │              │
   ✓ Success          ✓ Frame processed        ✓ Stored +    ✓ Called
   (received result)  (~125ms latency)        queued       (response)
```

---

## Component Responsibilities

| Component | Input | Processing | Output | Tests |
|-----------|-------|-----------|--------|-------|
| **BboxUtils** | x_min, y_min, x_max, y_max | Calculate pixel center | pixel_x, pixel_y | 8 unit |
| **CameraAggregator** | frame_id, provider | Call provider interface | CameraPosition | 10 unit |
| **DetectionTransformer** | YdcDetectionFrame, CameraPosition | Map fields, defaults | GeolocationApiRequest | 6 unit |
| **ResultAggregator** | CoT XML | Parse XML, extract geo | GeolocationResponse | 5 unit |
| **YdcToGeoProcessingService** | YdcDetectionFrame | Orchestrate pipeline | YdcAdapterResponse | 12 service |
| **ErrorRecoveryService** | Exception, function | Retry with backoff | Result or exception | 10 service |
| **TelemetryCollector** | Events (frame, latency, error) | Track metrics | Counters, histograms | 6 service |
| **MockCameraPositionAdapter** | frame_id | Return fixed/random pos | CameraPosition | 5 adapter |
| **HttpGeolocationAdapter** | GeolocationApiRequest | POST to API, parse XML | CoT XML | 12 adapter |
| **JsonLoggingAdapter** | Event, context | Format JSON, write stdout | Log line | 4 adapter |

---

## Integration Points

### 1. WebSocket Protocol (YDC ↔ Adapter)

**Input** (`/ws/ydc`):
```json
{
  "frame_id": "ydc-frame-001",
  "timestamp": "2026-02-17T14:35:42Z",
  "detections": [
    {"object_id": 0, "class_name": "vehicle", "confidence": 0.94,
     "x_min": 100, "y_min": 50, "x_max": 450, "y_max": 280}
  ]
}
```

**Output**:
```json
{
  "frame_id": "ydc-frame-001",
  "detection_id": "550e8400-e29b-41d4",
  "geolocation": {"calculated_lat": 40.7135, "calculated_lon": -74.0050,
                  "confidence_flag": "GREEN", "confidence_value": 0.85,
                  "uncertainty_radius_meters": 15.5},
  "status": "success",
  "latency_ms": 125
}
```

### 2. REST API (Adapter ↔ Geolocation-Engine2)

**Endpoint**: `POST /api/v1/detections`

**Request**:
```json
{
  "image_base64": "iVBORw0KGgo...",
  "pixel_x": 275, "pixel_y": 165,
  "object_class": "vehicle",
  "ai_confidence": 0.94,
  "source": "ydc_adapter",
  "camera_id": "mock_001",
  "timestamp": "2026-02-17T14:35:42Z",
  "sensor_metadata": {
    "location_lat": 40.7128, "location_lon": -74.0060,
    "location_elevation": 100.0,
    "heading": 45.0, "pitch": -30.0, "roll": 0.0,
    "focal_length": 3000.0, "sensor_width_mm": 6.4,
    "sensor_height_mm": 4.8, "image_width": 1920,
    "image_height": 1440
  }
}
```

**Response** (HTTP 201):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<event version="2.0" uid="550e8400-e29b-41d4"
       time="2026-02-17T14:35:42Z" type="b-m-p-s-u-c">
    <point lat="40.7135" lon="-74.0050" hae="100.0"
           ce="9999999.0" le="9999999.0"/>
</event>
```

---

## Error Handling Paths

```
┌─────────────────────────────────────────────────────────┐
│  ERROR RECOVERY FLOWCHART                               │
└─────────────────────────────────────────────────────────┘

YDC Frame Received
       │
       ↓
   Validate? ──NO──→ [Log Error] → [Reply to YDC: error] → END
       │ YES
       ↓
   Get Camera Pos
       │
       ├─ FAILURE ──→ [Retry #1] ──→ [Wait 1s] ──→ Retry?
       │                                             │
       │                                        ┌────┴────┐
       │                                   YES  │         NO
       │                                    ↓   ↓
       │                            [Retry #2] [Reply to YDC: error]
       │                                │         (camera unavailable)
       │                        ┌─────────┘         → END
       │                   [Wait 2s]
       │                        │
       │                 [Retry #3]
       │                        │
       │                ┌───────┴────┐
       │            SUCCESS          FAILURE
       │                │                │
       │                ↓                ↓
       │            (continue)    [Reply: camera error]
       │                              → END
       │
       ↓ (pos received)
   Call Geo-Engine2 API
       │
       ├─ HTTP 429 (Rate Limit) → [Backoff 1s] → [Retry] ──┐
       │                                                     │
       ├─ HTTP 500 (Server Error) → [Backoff 2s] → [Retry]─┤
       │                                                     │
       ├─ HTTP 400 (Bad Request) ──→ [Reply to YDC: error]  │
       │                            (validation error)       │
       │                                 → END               │
       │                                                     │
       └─ HTTP 201 (Success) ────→ [Parse XML] ──────┐     │
                                                      │     │
                                        ┌─────────────┘     │
                                        │                   │
                                        ↓ (after retries)   │
                                  [Reply to YDC]           │
                                  {status: success}         │
                                      → END             ┌───┘
                                                        │
                               Max Retries Exceeded?
                                        │
                                   YES  │  NO
                                    ↓   ↓
                               (end) [Retry again]
```

---

## Deployment Architecture

### Local Development (docker-compose)
```
Host Machine
├─ Port 8000
│  └─ geolocation-engine2:latest (FastAPI)
│     └─ SQLite /data/app.db
├─ Port 8001
│  └─ ydc-adapter:latest (FastAPI, this service)
│     └─ Stateless
└─ Port 1080
   └─ MockServer (mock TAK)
```

### Production (Docker on Single Host)
```
AWS EC2 / t2.medium
├─ Container: geolocation-engine2
│  └─ Port 8000
│  └─ Volume: /data (EBS persistent)
│  └─ CPU: 50% allocated
│  └─ Memory: 256MB allocated
├─ Container: ydc-adapter
│  └─ Port 8001
│  └─ Stateless (no volume)
│  └─ CPU: 50% allocated
│  └─ Memory: 256MB allocated
└─ nginx (reverse proxy)
   ├─ Port 80/443 (SSL)
   ├─ Route to 8000/8001
   └─ Health check polling
```

### Production (Kubernetes, Phase 2+)
```
K8s Cluster
├─ Namespace: production
│  ├─ Deployment: geolocation-engine2 (3 replicas)
│  │  └─ Service: ClusterIP :8000
│  │  └─ StatefulSet: PostgreSQL (1 primary, 1 replica)
│  │
│  ├─ Deployment: ydc-adapter (5 replicas)
│  │  └─ Service: LoadBalancer :8001
│  │  └─ HPA: Scale 5-15 replicas on CPU >70%
│  │  └─ ConfigMap: camera-provider configs
│  │
│  └─ Ingress: Route :443 → Services
```

---

## Quality Attributes

### Performance Targets
- Latency (p50): <150ms frame in → response out
- Latency (p99): <300ms
- Throughput: 100+ detections/sec (single instance)
- Memory: <500MB resident
- CPU: <60% at 100 det/sec

### Reliability Targets
- Error recovery: <10 seconds (retry exhaustion)
- Uptime: 99.5% (during TAK online window)
- No memory leaks (24h continuous)
- Graceful degradation (error → reply, not hang)

### Scalability Targets
- Stateless (no inter-instance communication)
- Linear scaling to 5 instances (80%+ efficiency)
- Connection pooling to Geolocation-Engine2

### Observability Targets
- All errors logged with frame_id context
- Latency metrics: p50, p99, max per minute
- Error rate trending

---

## File Structure

```
ydc-adapter/
├── src/
│   ├── __init__.py
│   ├── main.py (FastAPI app, routes)
│   ├── config.py (environment config)
│   ├── middleware.py (CORS, error handlers)
│   │
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── models.py (DetectionPixelCoordinates, CameraPosition, etc.)
│   │   ├── bbox_utils.py (pixel center extraction)
│   │   ├── detection_transformer.py (YDC → Geo schema)
│   │   └── result_aggregator.py (parse CoT XML)
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ydc_to_geo_processing_service.py (orchestrator)
│   │   ├── error_recovery_service.py (retry logic)
│   │   └── telemetry_collector.py (observability)
│   │
│   ├── ports/
│   │   ├── __init__.py
│   │   ├── camera_position_provider.py (abstract)
│   │   └── geolocation_client.py (abstract)
│   │
│   └── adapters/
│       ├── __init__.py
│       ├── camera_position/
│       │   ├── __init__.py
│       │   ├── mock_adapter.py (Phase 1)
│       │   ├── dji_adapter.py (Phase 2 stub)
│       │   └── mavlink_adapter.py (Phase 2 stub)
│       ├── geolocation/
│       │   ├── __init__.py
│       │   └── http_client_adapter.py (REST client)
│       └── observability/
│           ├── __init__.py
│           └── json_logging_adapter.py (structured logging)
│
├── tests/
│   ├── conftest.py (pytest fixtures)
│   ├── unit/
│   │   ├── test_bbox_utils.py (pixel math)
│   │   ├── test_detection_transformer.py (schema mapping)
│   │   ├── test_result_aggregator.py (XML parsing)
│   │   └── test_domain_models.py (validation)
│   │
│   ├── services/
│   │   ├── test_ydc_processing_service.py (orchestration)
│   │   ├── test_error_recovery_service.py (retry logic)
│   │   └── test_telemetry_collector.py (observability)
│   │
│   ├── adapters/
│   │   ├── test_mock_camera_provider.py (mock camera)
│   │   ├── test_http_geolocation_adapter.py (REST client)
│   │   └── test_json_logging_adapter.py (logging)
│   │
│   ├── integration/
│   │   ├── test_e2e_detection_processing.py (full flow)
│   │   └── test_with_mock_geolocation_server.py
│   │
│   └── load/
│       └── test_100_detections_per_sec.py (throughput)
│
├── docker/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .dockerignore
│
├── docker-compose.yml (local dev + mock geolocation-engine2)
├── .env.example (config template)
├── README.md (quick start)
├── pytest.ini (test config)
└── pyproject.toml (project metadata)
```

---

## Success Criteria Checklist

### Architecture Validation
- [ ] Component boundaries clear (hexagonal enforced)
- [ ] No domain layer I/O (pure functions testable)
- [ ] Adapters pluggable (new provider < 200 LOC)
- [ ] No cyclic dependencies (DAG enforced)
- [ ] Error paths documented (8+ scenarios)

### Performance
- [ ] Latency p50 < 150ms, p99 < 300ms
- [ ] Throughput > 100 det/sec
- [ ] Memory < 500MB

### Reliability
- [ ] Retries work (3x with backoff)
- [ ] Errors recoverable (<10s)
- [ ] No infinite loops/deadlocks

### Testability
- [ ] 85%+ code coverage
- [ ] Domain 95%+ coverage (pure functions)
- [ ] All adapters testable with mocks

### Observability
- [ ] Frame_id in all logs
- [ ] Latency metrics tracked
- [ ] Error rate trending

---

**Last Updated**: 2026-02-17
**For**: Acceptance Designer, Software Crafter
**See Also**: architecture-design.md (18 sections, detailed)

