# YDC ↔ Geolocation-Engine2 Adapter - System Architecture

**Status**: Design Complete (Ready for Acceptance Designer)
**Date**: 2026-02-17
**Architect**: Morgan (Solution Architect)

---

## Executive Summary

The YDC Adapter bridges YOLO object detection (real-time bounding boxes via WebSocket) with the mature Geolocation-Engine2 service to provide end-to-end geolocation → CoT/TAK output.

**Architecture Style**: Hexagonal (ports and adapters)
**Deployment**: Standalone microservice (Docker)
**Communication**: Sync REST to Geolocation-Engine2
**Data Flow**: YDC bbox → Camera position provider → Geolocation-Engine2 API → TAK push
**Scalability**: Stateless; horizontal scaling via load balancer
**Integration**: Pluggable camera position providers (Mock, DJI, MAVLink)

---

## Problem Statement

YDC streams continuous YOLO detections (bounding boxes) via WebSocket. Each detection requires:
1. **Extract bbox center** → pixel coordinates
2. **Get camera position** → latitude, longitude, elevation, orientation (heading, pitch, roll)
3. **Call Geolocation-Engine2 API** → pixel coords + camera metadata → real-world coordinates
4. **Result**: CoT/XML pushed to TAK via Geolocation-Engine2

**Challenge**: Camera position is variable. Must support:
- Mock provider (testing, ground targets)
- DJI SDK provider (DJI drones with telemetry API)
- MAVLink provider (ArduPilot aircraft)
- Future providers (extensible)

---

## 1. Hexagonal Architecture

### 1.1 Domain Layer (Business Logic)

```
┌─────────────────────────────────────────────────┐
│          DOMAIN LAYER                           │
│  (Detection Processing, No I/O)                 │
├─────────────────────────────────────────────────┤
│                                                 │
│  • BboxToPixelCoordinate (center extraction)   │
│  • CameraPositionAggregator (fetch position)   │
│  • DetectionTransformer (→ Geolocation API)    │
│  • ResultAggregator (response handling)        │
│  • ErrorHandler (resilience, logging)          │
│                                                 │
└─────────────────────────────────────────────────┘
```

**Responsibility**:
- Extract pixel center from YOLO bbox `{x_min, y_min, x_max, y_max}` → `{pixel_x, pixel_y}`
- Request camera position from injected provider
- Transform detection to Geolocation-Engine2 API schema
- Handle errors without side effects (pure functions)
- Coordinate orchestration (no direct I/O)

**Key Classes**:
- `DetectionProcessor` — Main orchestrator (testable)
- `BboxUtils` — Pixel math (pure functions)
- `DetectionSchema` — Domain models

---

### 1.2 Primary Ports (Inbound)

**Port 1: YDC WebSocket Listener**
- Protocol: WebSocket @ `/ws/ydc`
- Message Format: JSON YOLO detection frame
- Responsibility: Listen, deserialize, invoke domain processor
- Error Handling: Close connection gracefully on serialization errors

**Port 2: Health/Status Endpoint**
- Endpoint: `GET /api/v1/health`
- Response: Service status, telemetry (msg count, errors)
- SLA: <50ms response

---

### 1.3 Secondary Ports (Outbound)

**Port A: Camera Position Provider (Abstract)**
- Interface: `CameraPositionProvider`
- Contract: `async get_position() → CameraPosition`
- Adapters:
  - `MockCameraPositionAdapter` (fixed or randomized position)
  - `DjiTelemetryAdapter` (DJI SDK integration)
  - `MavlinkAdapter` (MAVLink protocol)

**Port B: Geolocation-Engine2 Client**
- Interface: `GeolocationClient`
- Contract: `async call_geolocation_api(detection) → CoT XML`
- Adapter: `HttpGeolocationAdapter` (REST client via httpx)
- Integration Point: Existing Geolocation-Engine2 `/api/v1/detections` endpoint

**Port C: Observability**
- Telemetry: Structured logging (JSON)
- Metrics: Detection count, latency, errors
- Adapter: `StdoutLoggingAdapter` (stdout for container logs)

---

## 2. Component Boundaries

```
┌─────────────────────────────────────────────────────────────────┐
│  YDC ADAPTER SERVICE (Microservice)                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  PRIMARY ADAPTER LAYER                                  │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │  • WebSocketListener (receive YOLO detections)          │   │
│  │  • HealthCheckHandler (readiness probe)                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│           ↓                                         ↓            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  APPLICATION/ORCHESTRATION LAYER                        │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │  • YdcToGeoProcessingService (state machine)            │   │
│  │  • DetectionProcessor (domain invocation)               │   │
│  │  • ErrorRecoveryService (retry, backoff)                │   │
│  │  • TelemetryCollector (observability)                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│           ↓                                         ↓            │
│  ┌──────────────────────┐        ┌─────────────────────────┐   │
│  │  DOMAIN LAYER        │        │  (BUSINESS LOGIC)       │   │
│  ├──────────────────────┤        ├─────────────────────────┤   │
│  │ • BboxToPixel        │        │ • Detection models      │   │
│  │ • CameraAggregator   │        │ • Position models       │   │
│  │ • DetectionXformer   │        │ • Result models         │   │
│  │ • ResultAggregator   │        │ • Error models          │   │
│  └──────────────────────┘        └─────────────────────────┘   │
│           ↓                                         ↓            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  SECONDARY ADAPTER LAYER                                │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ CameraPosition      │ Geolocation    │ Observability    │   │
│  │ • MockAdapter       │ • HttpClient   │ • JsonLogger     │   │
│  │ • DjiAdapter        │ • Retry logic  │ • Metrics        │   │
│  │ • MavlinkAdapter    │ • Circuit break│ • Health status  │   │
│  └─────────────────────────────────────────────────────────┘   │
│           ↓                    ↓                    ↓            │
└─────────────────────────────────────────────────────────────────┘
           │                    │                    │
           ↓                    ↓                    ↓
    ┌────────────┐      ┌─────────────┐      ┌──────────────┐
    │DJI/MAVLink │      │Geolocation- │      │Logging/      │
    │Telemetry   │      │Engine2 API  │      │Metrics Stack │
    │(External)  │      │(Port 8000)  │      │(Container)   │
    └────────────┘      └─────────────┘      └──────────────┘
```

### 2.1 Component Details

| Component | Responsibility | Dependencies | Tests |
|-----------|-----------------|--------------|-------|
| **WebSocketListener** | Accept YOLO frames, deserialize | FastAPI-WebSockets | 8 |
| **HealthCheckHandler** | Readiness probe, status | TelemetryCollector | 4 |
| **YdcToGeoProcessingService** | State machine: receive → process → respond | DetectionProcessor, ErrorRecoveryService | 12 |
| **DetectionProcessor** | Domain invocation: bbox → pixel, provider call, transformation | BboxUtils, CameraAggregator, DetectionXformer | 15 |
| **ErrorRecoveryService** | Retry logic, backoff, circuit breaker | Logger | 10 |
| **TelemetryCollector** | Metrics: frame count, latency, error rate | Logger | 6 |
| **BboxUtils** | Pixel math: center extraction, validation | (none) | 8 |
| **CameraAggregator** | Fetch camera position (abstracted provider) | CameraPositionProvider (port) | 10 |
| **DetectionTransformer** | YDC frame → Geolocation-Engine2 schema | DetectionModel | 6 |
| **ResultAggregator** | Consume Geolocation-Engine2 response, prepare client reply | (none) | 5 |
| **MockCameraPositionAdapter** | Fixed/randomized position (testing) | (none) | 5 |
| **DjiTelemetryAdapter** | DJI SDK integration (future) | dji-sdk (TBD) | 0 (stub) |
| **MavlinkAdapter** | MAVLink protocol (future) | pymavlink (TBD) | 0 (stub) |
| **HttpGeolocationAdapter** | REST client to Geolocation-Engine2 | httpx | 12 |
| **JsonLoggingAdapter** | Structured JSON logging | logging | 4 |

**Total**: ~95 tests planned

---

## 3. Technology Stack

### 3.1 Justified Selections

| Layer | Technology | License | Rationale |
|-------|-----------|---------|-----------|
| **Language** | Python 3.11+ | PSF | Same as Geolocation-Engine2; async/await native; team expertise |
| **Framework** | FastAPI | MIT | WebSocket support, async, auto-docs; reuses existing patterns |
| **Async Runtime** | asyncio | PSF | Standard library; native to FastAPI; concurrent provider calls |
| **HTTP Client** | httpx | BSD | Async-first, connection pooling, retry support |
| **WebSocket** | websockets / fastapi.websockets | PSF/MIT | Built into FastAPI; no extra dependency |
| **Serialization** | Pydantic v2 | MIT | Type safety, auto-validation; same as Geolocation-Engine2 |
| **Logging** | Python stdlib logging | PSF | Built-in; JSON formatter for observability |
| **Testing** | pytest + pytest-asyncio | MIT | Industry standard; async support |
| **Container** | Docker | Apache 2.0 | Same deployment pattern as Geolocation-Engine2 |
| **Deployment** | Docker Compose | Apache 2.0 | Local dev; orchestrates YDC adapter + Geolocation-Engine2 |

**Cost**: $0 (all open source)

### 3.2 Alternative Technologies Rejected

| Alternative | Considered | Rejected Because | Evidence |
|-------------|-----------|-----------------|----------|
| Go (goroutines) | Yes | +3-4 weeks dev time; no geospatial libs; unfamiliar to team | Go camera provider libs immature vs Python |
| Node.js (async/await) | No | Type safety issues; async exception handling weaker; no existing patterns in org | Team expertise in Python |
| Async WebSocket (aiohttp) | No | FastAPI already chosen for Geolocation-Engine2 consistency | Standardization around FastAPI ecosystem |
| Connection pooling (raw sockets) | No | httpx handles pooling; premature optimization | httpx sufficient for throughput targets |

---

## 4. Data Models & API Contracts

### 4.1 YDC Input (WebSocket Frame)

```python
# Received via WebSocket @ /ws/ydc
class YdcDetectionFrame(BaseModel):
    """YOLO detection frame from YDC"""
    frame_id: str                   # Unique frame identifier
    timestamp: datetime             # Frame capture time (ISO8601 UTC)
    detections: List[YoloDetection]

class YoloDetection(BaseModel):
    """Single YOLO detection (bounding box)"""
    object_id: int                  # Track ID (0-N)
    class_name: str                 # Class: "vehicle", "person", etc.
    confidence: float               # 0.0-1.0 confidence score
    x_min: int                      # Left edge (pixels)
    y_min: int                      # Top edge (pixels)
    x_max: int                      # Right edge (pixels)
    y_max: int                      # Bottom edge (pixels)

# Example JSON:
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
    }
  ]
}
```

### 4.2 Pixel Extraction (Domain)

```python
# Internal domain model (no I/O)
@dataclass
class DetectionPixelCoordinates:
    """Extracted pixel center from YOLO bbox"""
    pixel_x: int                    # Center X in image
    pixel_y: int                    # Center Y in image
    confidence_yolo: float          # AI confidence (0-1)
    object_class: str               # Class name

# Calculation (pure function):
# pixel_x = (x_min + x_max) // 2
# pixel_y = (y_min + y_max) // 2
```

### 4.3 Camera Position Model

```python
# Port interface (abstract)
class CameraPosition(BaseModel):
    """Camera position at frame capture time"""
    latitude: float                 # -90 to 90
    longitude: float                # -180 to 180
    elevation_m: float              # Meters above ground
    heading_deg: float              # 0-360 compass degrees
    pitch_deg: float                # -90 to +90 elevation angle
    roll_deg: float                 # -180 to +180 roll

# Adapter implementations fill this via provider-specific APIs
```

### 4.4 Transformation to Geolocation-Engine2 API

```python
# Request to POST /api/v1/detections on Geolocation-Engine2
class GeolocationApiRequest(BaseModel):
    """Request payload to Geolocation-Engine2"""
    image_base64: str               # Full frame as base64 (from YDC or placeholder)
    pixel_x: int                    # Extracted center X
    pixel_y: int                    # Extracted center Y
    object_class: str               # Detection class
    ai_confidence: float            # YOLO confidence
    source: str                     # "ydc_adapter"
    camera_id: str                  # Provider-specific ID
    timestamp: datetime             # Frame capture time
    sensor_metadata: SensorMetadata # Camera orientation + intrinsics

class SensorMetadata(BaseModel):
    """Camera/sensor metadata (reused from Geolocation-Engine2)"""
    location_lat: float
    location_lon: float
    location_elevation: float
    heading: float
    pitch: float
    roll: float
    focal_length: float             # 3000 px default
    sensor_width_mm: float          # 6.4 mm default
    sensor_height_mm: float         # 4.8 mm default
    image_width: int                # 1920 px default
    image_height: int               # 1440 px default
```

### 4.5 Response Flow

```python
# Geolocation-Engine2 returns CoT XML (via Response.content)
# YDC Adapter:
# 1. Parse CoT XML
# 2. Extract geolocation (lat, lon, confidence)
# 3. Reply via WebSocket

class YdcAdapterResponse(BaseModel):
    """WebSocket response to YDC client"""
    frame_id: str                   # Echo request frame_id
    detection_id: str               # Generated by Geolocation-Engine2
    geolocation: Geolocation
    cot_xml: str                    # Full CoT XML (optional)
    status: Literal["success", "error"]
    error_message: Optional[str]
    latency_ms: int                 # Total processing latency

class Geolocation(BaseModel):
    calculated_lat: float
    calculated_lon: float
    confidence_flag: Literal["GREEN", "YELLOW", "RED"]
    confidence_value: float
    uncertainty_radius_meters: float
```

---

## 5. Integration with Geolocation-Engine2

### 5.1 Shared Database

**Decision**: Separate databases initially, shared during scaling phase.

**Rationale**:
- MVP: YDC adapter is stateless, only calls Geolocation-Engine2 API
- No need to share detection history or offline queue
- Simplifies deployment: YDC adapter has no persistent storage
- Phase 2: If scaling requires shared database, migrate to PostgreSQL

**Current State (MVP)**:
```
┌────────────────────┐        ┌──────────────────────────────┐
│  YDC Adapter       │        │ Geolocation-Engine2          │
│  (Stateless)       │        │                              │
│  No database       │   →    │ POST /api/v1/detections      │
│  No persistence    │  REST  │                              │
│  Cache free        │        │ Returns: CoT XML             │
└────────────────────┘        │ Stores: SQLite (local)       │
                              │ • Detections table           │
                              │ • Offline queue              │
                              │ • Audit trail                │
                              └──────────────────────────────┘
```

### 5.2 Authentication & Authorization

**Geolocation-Engine2 Expectations** (from `/src/config.py` & `/src/middleware.py`):
- JWT tokens (optional, via middleware)
- API Key (optional, via header)
- Rate limiting (Token bucket: capacity=100, refill=10/sec)

**YDC Adapter Integration**:
```python
# In HttpGeolocationAdapter.__init__():
self.api_key = os.getenv("GEOLOCATION_API_KEY", None)
self.jwt_token = os.getenv("GEOLOCATION_JWT_TOKEN", None)

# In request:
headers = {}
if self.api_key:
    headers["X-API-Key"] = self.api_key
if self.jwt_token:
    headers["Authorization"] = f"Bearer {self.jwt_token}"
```

**Rate Limiting Handling**:
- Geolocation-Engine2: Token bucket (100 capacity, 10/sec refill)
- YDC Adapter: Respects rate limits; queues excess frames locally (in-memory queue, not persisted)
- If 429 received: exponential backoff (1s, 2s, 4s, 8s max)

---

## 6. Error Handling & Resilience

### 6.1 Error Scenarios

| Scenario | Impact | Handling | Recovery |
|----------|--------|----------|----------|
| **YDC disconnects** | Stop receiving frames | Close connection gracefully | Reconnect attempt (exponential backoff) |
| **Camera provider unavailable** | Can't get position | Fail detection with error code | Reply error via WebSocket, mark detection failed |
| **Geolocation-Engine2 offline** | API call fails | Retry with backoff (1s, 2s, 4s, 8s) | After max retries: reply error to YDC |
| **Invalid bbox** | Domain error | Validation fails early | Log error, reply validation error to YDC |
| **Network timeout** | Partial loss | 5s timeout on httpx calls | Retry logic applies |
| **Rate limit (429)** | Throttling | Exponential backoff | Respect rate limits |

### 6.2 Error Reply (WebSocket)

```python
# If error occurs during processing:
error_response = YdcAdapterResponse(
    frame_id=frame_id,
    detection_id=None,
    geolocation=None,
    cot_xml=None,
    status="error",
    error_message="Geolocation service unavailable (attempted 3 retries)",
    latency_ms=elapsed_ms
)
await websocket.send_json(error_response.model_dump())
```

### 6.3 Observability

**Logging** (JSON to stdout):
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
  "geolocation_status": "GREEN"
}
```

**Metrics** (Prometheus-compatible, scraped by container monitoring):
- `ydc_frames_received_total` — Total frames received
- `ydc_detections_processed_total` — Detections successfully processed
- `ydc_errors_total` — Errors by type (invalid_bbox, provider_unavailable, geo_api_failed)
- `ydc_latency_ms` — Processing latency histogram
- `ydc_camera_provider_calls_total` — Provider calls by type

---

## 7. Extension Points (Pluggable Providers)

### 7.1 Camera Position Provider Interface

```python
# Abstract port (src/ports/camera_position_provider.py)
from abc import ABC, abstractmethod

class CameraPositionProvider(ABC):
    """Port: Abstraction for camera position sources"""

    @abstractmethod
    async def get_position(self, frame_id: str) -> CameraPosition:
        """Get camera position at frame capture time.

        Args:
            frame_id: YDC frame identifier for timestamped lookup

        Returns:
            CameraPosition with lat, lon, elevation, orientation

        Raises:
            CameraPositionUnavailableError: If position can't be determined
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Verify provider is operational.

        Returns:
            True if provider can be contacted
        """
        pass
```

### 7.2 Mock Adapter (For Testing, Phase 1)

```python
# src/adapters/camera_position/mock_adapter.py
class MockCameraPositionAdapter(CameraPositionProvider):
    """Test adapter: Fixed or randomized position"""

    def __init__(self,
                 latitude: float = 40.7128,
                 longitude: float = -74.0060,
                 elevation_m: float = 100.0,
                 randomize: bool = False):
        self.base_position = CameraPosition(
            latitude=latitude,
            longitude=longitude,
            elevation_m=elevation_m,
            heading_deg=45.0,
            pitch_deg=-30.0,
            roll_deg=0.0
        )
        self.randomize = randomize

    async def get_position(self, frame_id: str) -> CameraPosition:
        """Return fixed or slightly randomized position"""
        if self.randomize:
            # Add ±0.001 degrees noise (~100m)
            return CameraPosition(
                latitude=self.base_position.latitude + random.uniform(-0.001, 0.001),
                longitude=self.base_position.longitude + random.uniform(-0.001, 0.001),
                elevation_m=self.base_position.elevation_m,
                heading_deg=random.uniform(0, 360),
                pitch_deg=random.uniform(-45, -15),
                roll_deg=0.0
            )
        return self.base_position
```

### 7.3 DJI Adapter (Phase 2, Stub)

```python
# src/adapters/camera_position/dji_adapter.py
class DjiTelemetryAdapter(CameraPositionProvider):
    """DJI SDK integration (Future)"""

    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url  # e.g., "http://localhost:9000"
        self.api_key = api_key
        self.client = None

    async def get_position(self, frame_id: str) -> CameraPosition:
        """Fetch current position from DJI API

        Expected DJI API response:
        {
            "lat": 40.7128,
            "lon": -74.0060,
            "altitude": 100.0,
            "yaw": 45,
            "pitch": -30,
            "roll": 0
        }
        """
        # TODO: Phase 2 implementation
        # 1. Connect to DJI Telem API
        # 2. Poll current aircraft position
        # 3. Map DJI fields to CameraPosition
        raise NotImplementedError("DJI adapter available in Phase 2")
```

### 7.4 MAVLink Adapter (Phase 2, Stub)

```python
# src/adapters/camera_position/mavlink_adapter.py
class MavlinkAdapter(CameraPositionProvider):
    """MAVLink protocol support (Future, e.g., ArduPilot)"""

    def __init__(self, device: str = "/dev/ttyUSB0", baudrate: int = 115200):
        self.device = device
        self.baudrate = baudrate
        self.connection = None

    async def get_position(self, frame_id: str) -> CameraPosition:
        """Fetch position via MAVLink heartbeat

        Expected MAVLink GLOBAL_POSITION_INT message:
        - lat (degrees * 1e7)
        - lon (degrees * 1e7)
        - alt (mm above ground)
        - vx, vy, vz (velocities)
        """
        # TODO: Phase 2 implementation
        # 1. Open serial connection to MAVLink device
        # 2. Request current position
        # 3. Parse GLOBAL_POSITION_INT message
        # 4. Convert to CameraPosition
        raise NotImplementedError("MAVLink adapter available in Phase 2")
```

### 7.5 Adapter Registry (Dependency Injection)

```python
# src/config.py
from enum import Enum

class CameraProviderType(str, Enum):
    MOCK = "mock"
    DJI = "dji"
    MAVLINK = "mavlink"

# Load via config:
camera_provider_type = os.getenv("CAMERA_PROVIDER_TYPE", "mock")
camera_provider: CameraPositionProvider

if camera_provider_type == "mock":
    camera_provider = MockCameraPositionAdapter(
        latitude=float(os.getenv("MOCK_LAT", "40.7128")),
        longitude=float(os.getenv("MOCK_LON", "-74.0060")),
        elevation_m=float(os.getenv("MOCK_ELEVATION", "100"))
    )
elif camera_provider_type == "dji":
    camera_provider = DjiTelemetryAdapter(
        api_url=os.getenv("DJI_API_URL"),
        api_key=os.getenv("DJI_API_KEY")
    )
# ... etc
```

---

## 8. C4 Diagrams

### 8.1 System Context (Level 1)

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                    SYSTEM CONTEXT                               │
│                   (External perspective)                        │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐                                               │
│  │   YOLO       │                                               │
│  │  Detector    │──WebSocket────────┐                           │
│  │  (YDC)       │  YOLO detections  │                           │
│  └──────────────┘                   │                           │
│                                     ↓                           │
│                          ┌──────────────────┐                   │
│                          │  YDC ↔ Geoloc    │                   │
│                          │  Adapter         │                   │
│                          │  (This Service)  │                   │
│                          └──────────────────┘                   │
│                            ↑ (REST)    ↓ (WebSocket reply)     │
│                            │           ↓                        │
│                    ┌───────────────┐  ┌──────────────┐          │
│                    │  Geolocation- │  │   YDC Client │          │
│                    │  Engine2      │  │  (Receiver)  │          │
│                    │  (Geolocate + │  └──────────────┘          │
│                    │   TAK push)   │                            │
│                    └───────────────┘                            │
│                      ↓ (async)                                  │
│                    ┌───────────────┐                            │
│                    │   TAK Server  │                            │
│                    │   (CoT sink)  │                            │
│                    └───────────────┘                            │
│                                                                 │
│  ┌──────────────┐     ┌──────────────┐                          │
│  │ Camera Pos   │     │ Telemetry    │                          │
│  │ Provider:    │────→│ APIs         │                          │
│  │ Mock/DJI/    │     │ (DJI, MAVLink)                          │
│  │ MAVLink      │     └──────────────┘                          │
│  └──────────────┘                                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 8.2 Container Diagram (Level 2)

```
┌─────────────────────────────────────────────────────────────────┐
│            YDC ↔ GEOLOCATION-ENGINE2 ADAPTER                    │
│              (Single Docker Container)                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ FastAPI Application (Port 8001)                         │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │                                                         │   │
│  │ Route: WebSocket /ws/ydc                               │   │
│  │ Route: GET /api/v1/health                              │   │
│  │ Route: GET /api/v1/metrics (Prometheus-compat)         │   │
│  │                                                         │   │
│  └──────────────────┬──────────────────────────────────────┘   │
│                     ↓                                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Orchestration Services (asyncio)                        │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ • WebSocketListener                                     │   │
│  │ • YdcToGeoProcessingService                             │   │
│  │ • ErrorRecoveryService                                  │   │
│  │ • TelemetryCollector                                    │   │
│  │                                                         │   │
│  └──────────────────┬──────────────────────────────────────┘   │
│                     ↓                                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Domain Layer (Business Logic)                           │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ • BboxUtils (pixel center extraction)                   │   │
│  │ • CameraAggregator (fetch position via provider)        │   │
│  │ • DetectionTransformer (YDC → Geolocation-Engine2)     │   │
│  │ • ResultAggregator (handle response)                    │   │
│  │                                                         │   │
│  └──────────┬───────────────────────────────┬──────────────┘   │
│             ↓                               ↓                  │
│  ┌──────────────────────┐    ┌─────────────────────────────┐   │
│  │ Camera Position      │    │ Geolocation-Engine2 Client  │   │
│  │ Provider Adapter     │    │ (HTTP REST)                 │   │
│  ├──────────────────────┤    ├─────────────────────────────┤   │
│  │ • MockAdapter        │    │ • HttpGeolocationAdapter    │   │
│  │ • DjiAdapter (stub)  │    │ • Retry with backoff        │   │
│  │ • MavlinkAdapter(...)│    │ • Rate limit handling       │   │
│  │                      │    │ • Circuit breaker           │   │
│  └──────────────────────┘    └─────────────────────────────┘   │
│             ↓                               ↓                  │
│             │                               │                  │
└─────────────┼───────────────────────────────┼──────────────────┘
              ↓                               ↓
       ┌─────────────┐              ┌──────────────────┐
       │ Camera Telem│              │ Geolocation-     │
       │ (DJI/       │              │ Engine2 API      │
       │ MAVLink)    │              │ (localhost:8000) │
       └─────────────┘              └──────────────────┘
```

### 8.3 Component Diagram (Level 3)

```
┌────────────────────────────────────────────────────────────┐
│          YDC ADAPTER - DETAILED COMPONENTS                 │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌───────────────────────────────────────────────────┐   │
│  │ REQUEST HANDLER LAYER                             │   │
│  ├───────────────────────────────────────────────────┤   │
│  │                                                   │   │
│  │  ┌─────────────────────────────────────────────┐ │   │
│  │  │ WebSocketListener (Inbound Primary Port)    │ │   │
│  │  │ • Accept /ws/ydc connections                │ │   │
│  │  │ • Validate JSON frame format                │ │   │
│  │  │ • Invoke ProcessingService for each frame   │ │   │
│  │  │ • Handle disconnects gracefully             │ │   │
│  │  └────────────────┬──────────────────────────┘ │   │
│  │                   ↓                            │   │
│  │  ┌─────────────────────────────────────────────┐ │   │
│  │  │ HealthCheckHandler (Inbound Primary Port)  │ │   │
│  │  │ • GET /api/v1/health                        │ │   │
│  │  │ • Return status + metrics                   │ │   │
│  │  └─────────────────────────────────────────────┘ │   │
│  │                                                   │   │
│  └───────────────────────────────────────────────────┘   │
│             ↓                                      ↓      │
│  ┌────────────────────────────┐    ┌──────────────────┐  │
│  │ ORCHESTRATION LAYER        │    │ TELEMETRY        │  │
│  ├────────────────────────────┤    ├──────────────────┤  │
│  │                            │    │ • Metrics cache  │  │
│  │ YdcToGeoProcessingService  │    │ • Error counter  │  │
│  │ • State machine: idle      │    │ • Latency hist   │  │
│  │   → processing → complete  │    │ • Provider stats │  │
│  │ • Invoke DetectionProc...  │    │                  │  │
│  │ • Route errors via err-hdlr│    └──────────────────┘  │
│  │                            │          ↑                │
│  └────┬───────────────────┬───┘          │                │
│       ↓                   ↓              │                │
│  ┌──────────────┐  ┌──────────────┐     │                │
│  │ Detector     │  │ Error        │     │                │
│  │ Processor    │  │ Recovery     │     │                │
│  │              │  │ Service      │     │                │
│  │ • Validates  │  │              │     │                │
│  │   bbox input │  │ • Retry logic│─────┘                │
│  │ • Calls      │  │ • Exponential│                      │
│  │   provider   │  │   backoff    │                      │
│  │ • Transforms │  │ • Logging    │                      │
│  │   to Geoloc  │  │              │                      │
│  │ • Aggregates │  └──────────────┘                      │
│  │   result     │                                        │
│  └──────┬───────┘                                        │
│         ↓                                                │
│  ┌──────────────────────────────────────────────────┐  │
│  │ DOMAIN LAYER (Pure Business Logic)               │  │
│  ├──────────────────────────────────────────────────┤  │
│  │                                                  │  │
│  │ ┌──────────────┐  ┌──────────────────────────┐ │  │
│  │ │ BboxUtils    │  │ CameraAggregator         │ │  │
│  │ │              │  │                          │ │  │
│  │ │ • Validate   │  │ • Call provider abstract │ │  │
│  │ │   bounds     │  │ • Validate camera pos   │ │  │
│  │ │ • Extract    │  │ • Cache (optional)       │ │  │
│  │ │   center X,Y │  │                          │ │  │
│  │ │              │  │                          │ │  │
│  │ └──────────────┘  └──────────────────────────┘ │  │
│  │                                                  │  │
│  │ ┌──────────────────┐  ┌─────────────────────┐  │  │
│  │ │DetectionTransformer
│  │ │                   │  │ResultAggregator     │  │  │
│  │ │ • Map YDC fields  │  │                     │  │  │
│  │ │   to Geolocation  │  │ • Parse CoT XML     │  │  │
│  │ │   API schema      │  │ • Extract geoloc    │  │  │
│  │ │ • Set defaults    │  │ • Prepare response  │  │  │
│  │ │   (focal_length,  │  │ • Calc latency      │  │  │
│  │ │    sensor size)   │  │                     │  │  │
│  │ │                   │  │                     │  │  │
│  │ └──────────────────┘  └─────────────────────┘  │  │
│  │                                                  │  │
│  └──────────────┬────────────────┬────────────────┘  │
│                 ↓                ↓                   │
│  ┌────────────────────────────────────────────────┐  │
│  │ ADAPTER LAYER (External I/O)                   │  │
│  ├────────────────────────────────────────────────┤  │
│  │                                                │  │
│  │ ┌─────────────────────────────────────────┐  │  │
│  │ │CameraPositionProvider (Abstract Port)   │  │  │
│  │ │                                         │  │  │
│  │ │ ┌──────────────────────────────────┐   │  │  │
│  │ │ │ MockCameraPositionAdapter        │   │  │  │
│  │ │ │ • Fixed position (testing)       │   │  │  │
│  │ │ │ • Randomized (simulation)        │   │  │  │
│  │ │ └──────────────────────────────────┘   │  │  │
│  │ │                                         │  │  │
│  │ │ ┌──────────────────────────────────┐   │  │  │
│  │ │ │ DjiTelemetryAdapter (Phase 2)    │   │  │  │
│  │ │ │ • DJI SDK integration (stub)     │   │  │  │
│  │ │ └──────────────────────────────────┘   │  │  │
│  │ │                                         │  │  │
│  │ │ ┌──────────────────────────────────┐   │  │  │
│  │ │ │ MavlinkAdapter (Phase 2)         │   │  │  │
│  │ │ │ • MAVLink protocol (stub)        │   │  │  │
│  │ │ └──────────────────────────────────┘   │  │  │
│  │ │                                         │  │  │
│  │ └─────────────────────────────────────────┘  │  │
│  │                                                │  │
│  │ ┌─────────────────────────────────────────┐  │  │
│  │ │HttpGeolocationAdapter                   │  │  │
│  │ │ • POST to /api/v1/detections            │  │  │
│  │ │ • Retry with exponential backoff        │  │  │
│  │ │ • Handle 429 rate limit                 │  │  │
│  │ │ • Connection pooling (httpx)            │  │  │
│  │ │ • Parse CoT XML response                │  │  │
│  │ └─────────────────────────────────────────┘  │  │
│  │                                                │  │
│  │ ┌─────────────────────────────────────────┐  │  │
│  │ │JsonLoggingAdapter                       │  │  │
│  │ │ • Structured JSON logs to stdout        │  │  │
│  │ │ • Prometheus metrics format             │  │  │
│  │ └─────────────────────────────────────────┘  │  │
│  │                                                │  │
│  └────────────────────────────────────────────────┘  │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## 9. Data Flow Diagrams

### 9.1 Happy Path: Successful Detection Processing

```
Time →

YDC Client                    YDC Adapter                  Geolocation-Engine2
    │                             │                              │
    │  1. WebSocket frame         │                              │
    ├────────────────────────────→│                              │
    │  {detections: [...]}        │                              │
    │                             │                              │
    │                             │ 2. Validate bbox             │
    │                             │ (BboxUtils)                  │
    │                             │←──┐                          │
    │                             │   │ OK                       │
    │                             │   └──────────────────────┐   │
    │                             │                         │   │
    │                             │ 3. Request camera pos   │   │
    │                             │ (CameraAggregator       │   │
    │                             │  → MockAdapter)         │   │
    │                             │←──┐                     │   │
    │                             │   │ CameraPosition      │   │
    │                             │   │ {lat, lon, ...}     │   │
    │                             │   └──────────────────┐  │   │
    │                             │                     │  │   │
    │                             │ 4. Transform frame  │  │   │
    │                             │ (DetectionTransformer)      │   │
    │                             │ YDC → Geolocation schema    │   │
    │                             │←──┐                 │       │   │
    │                             │   │ OK              │       │   │
    │                             │   └────────────┐    │       │   │
    │                             │                │    │       │   │
    │                             │ 5. POST /api/v1/detections  │   │
    │                             ├───────────────────────────→ │
    │                             │ {pixel_x, pixel_y, ...}     │
    │                             │ {sensor_metadata: ...}      │
    │                             │                             │
    │                             │                   Geolocate │
    │                             │                   (photogram) │
    │                             │                   TAK push  │
    │                             │                   (async)   │
    │                             │                             │
    │                             │  6. 201 CoT XML response   │
    │                             │ ←───────────────────────────┤
    │                             │                             │
    │                             │ 7. Parse CoT XML            │
    │                             │ (ResultAggregator)          │
    │                             │←──┐                         │
    │                             │   │ {lat, lon, confidence}   │
    │                             │   └──────────┐              │
    │                             │              │              │
    │  8. WebSocket response      │              │              │
    │ ←────────────────────────────              │              │
    │  {geolocation, status:ok}                  │              │
    │                             ←──────────────┘              │
    │                                                           │
  (success)                    ✓ Frame processed            ✓ Detection stored
                               ~125ms latency              + offline queue
                                                           + audit trail
```

### 9.2 Error Path: Camera Provider Unavailable

```
Time →

YDC Client            YDC Adapter              CameraProvider    Telemetry
    │                     │                         │                │
    │ 1. Frame            │                         │                │
    ├────────────────────→│                         │                │
    │                     │ 2. Validate ✓           │                │
    │                     │                         │                │
    │                     │ 3. Request position     │                │
    │                     ├────────────────────────→│                │
    │                     │                         │ → Dial TCP     │
    │                     │                         │   timeout!     │
    │                     │ 4. ERROR: Unavailable   │                │
    │                     │←────────────────────────┤                │
    │                     │                         │                │
    │                     │ 5. ErrorRecoveryService │                │
    │                     │    Retry #1 (1s backoff)                 │
    │                     ├────────────────────────→│ ← (timeout)    │
    │                     │                         │                │
    │                     │    Retry #2 (2s backoff)│                │
    │                     ├────────────────────────→│ ← (timeout)    │
    │                     │                         │                │
    │                     │    Retry #3 (4s backoff)                 │
    │                     ├────────────────────────→│ ← (timeout)    │
    │                     │                         │                │
    │                     │ 6. Max retries exceeded │                │
    │                     │    ERROR REPLY          │                │
    │                     │                         │                │
    │  7. Error response  │                         │                │
    │ ←────────────────────                         │                │
    │  {status: error,                              │                │
    │   error_msg: "camera position unavailable"}   │                │
    │                                               │                │
  (failure)                ⚠ Frame dropped       ✗ No geolocation
                           ~9s latency (retries)
```

### 9.3 Error Path: Geolocation-Engine2 Rate Limited

```
Time →

YDC Adapter               Geolocation-Engine2
    │                             │
    │ 1. POST /api/v1/detections  │
    ├────────────────────────────→│
    │                             │
    │ 2. 429 Too Many Requests    │
    │ ←────────────────────────────┤
    │ (rate limit exceeded)        │
    │                             │
    │ 3. ErrorRecoveryService:    │
    │    Wait 1s (exponential)     │
    │                             │
    │    Retry #1                 │
    ├────────────────────────────→│
    │                             │
    │ 4. 429 Too Many Requests    │
    │ ←────────────────────────────┤
    │                             │
    │    Wait 2s                  │
    │                             │
    │    Retry #2                 │
    ├────────────────────────────→│
    │                             │
    │ 5. 200 OK, CoT XML response │
    │ ←────────────────────────────┤
    │ (rate limit window cleared)  │
    │                             │
  (eventual success)              ✓ Detection processed
                                  ~6s total latency (with backoff)
```

---

## 10. Scalability Considerations

### 10.1 Single Instance Throughput

**Hardware**: Single Docker container on t2.micro (1 CPU, 1GB RAM)

| Metric | Capacity | Limiting Factor |
|--------|----------|-----------------|
| **Concurrent WebSocket connections** | 1,000+ | asyncio event loop |
| **Detections/second (stateless processing)** | 100+ | Domain logic (pure functions) |
| **Latency (happy path)** | ~125ms | Geolocation-Engine2 latency + network |
| **Memory usage** | <500MB | Python process + asyncio buffers |
| **CPU usage (at 100 det/sec)** | ~60-70% | Domain processing + I/O wait |

**Example**: At 100 detections/second:
- 125ms latency × 100 det/sec = 12.5 "in-flight" detections
- Each detection: ~5KB (metadata) = 62.5 KB buffered
- CPU: Mostly idle (I/O bound), waiting for Geolocation-Engine2

### 10.2 Horizontal Scaling (Phase 2+)

```
┌─────────────────────────────────────────────┐
│        Load Balancer (nginx/HAProxy)        │
│         :8001 (WebSocket routing)           │
└────────────┬────────────────────────────────┘
             │
    ┌────────┼────────┐
    ↓        ↓        ↓
┌────────┐ ┌────────┐ ┌────────┐
│YDC     │ │YDC     │ │YDC     │
│Adapter │ │Adapter │ │Adapter │
│  #1    │ │  #2    │ │  #3    │
└────────┘ └────────┘ └────────┘
    │        │        │
    └────────┼────────┘
             ↓
    ┌──────────────────┐
    │Geolocation-Engine2
    │  (Shared backend)
    │  Port 8000
    └──────────────────┘
```

**Scaling Path**:
1. **MVP (Phase 1)**: Single container, mock camera position
2. **Phase 2**: Multiple YDC adapters behind load balancer; Geolocation-Engine2 instances
3. **Phase 3**: Kubernetes orchestration; auto-scaling on CPU

**Zero Shared State**:
- Each adapter is stateless
- No inter-adapter communication
- Can spin up/down independently
- Load balancer routes WebSocket connections

### 10.3 Camera Provider Scaling

**Mock Adapter**: No external dependencies, scales trivially

**DJI Adapter (Phase 2)**:
- Single DJI aircraft = one camera position
- Multiple DJI aircraft = multiple adapter instances (one per aircraft)
- Deployment: Sidecar pattern (DJI adapter runs on same host as camera)

**MAVLink Adapter (Phase 2)**:
- Single serial port per aircraft
- Multiple aircraft = multiple adapter instances
- Deployment: Sidecar pattern (MAVLink on same host as radio/aircraft)

---

## 11. Testing Strategy

### 11.1 Test Layers

| Layer | Approach | Examples |
|-------|----------|----------|
| **Unit (Domain)** | Pure function tests, no I/O | BboxUtils, DetectionTransformer |
| **Service (Orchestration)** | Mocked adapters, in-memory | YdcToGeoProcessingService (mock geo client) |
| **Integration** | Real adapters, Docker Compose | YDC adapter + mock Geolocation-Engine2 |
| **End-to-End** | Full stack: YDC + adapter + Geolocation-Engine2 | Regression tests against live stack |

### 11.2 Mock Geolocation-Engine2 (Testing)

For unit/integration tests, use mock HTTP server:

```python
# tests/fixtures/mock_geolocation_server.py
from fastapi import FastAPI
from fastapi.responses import Response

mock_geo_app = FastAPI()

@mock_geo_app.post("/api/v1/detections")
async def mock_create_detection(body: dict):
    """Mock endpoint returns fixed CoT XML"""
    cot_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <event version="2.0" uid="test-detection-001"
           time="2026-02-17T14:35:42Z" type="b-m-p-s-u-c">
        <point lat="40.7135" lon="-74.0050" hae="100.0"
               ce="9999999.0" le="9999999.0"/>
    </event>"""

    return Response(
        content=cot_xml,
        status_code=201,
        media_type="application/xml",
        headers={"X-Detection-ID": "test-550e8400-e29b-41d4"}
    )

# Usage in pytest:
@pytest.fixture
def mock_geo_server():
    """Start mock server on port 9999"""
    # Use TestClient or asyncio + httpx.AsyncServer
    ...
```

### 11.3 Test Coverage Goals

```
Layer                 Coverage      Count    Strategy
────────────────────────────────────────────────────────
Domain (pure logic)   95%+          35       Unit tests + property-based
Services             90%+          40       Mocked adapters
Adapters              85%+          15       Mock external APIs
Integration          75%+          5        E2E against mock server
────────────────────────────────────────────────────────
TOTAL                ~85-90%        ~95 tests
```

### 11.4 Load Test Scenario

```python
# tests/load/test_100_det_per_sec.py
import asyncio
import httpx
from faker import Faker

@pytest.mark.asyncio
async def test_100_detections_per_second():
    """Simulate 100 detections/sec for 60 seconds"""
    fake = Faker()
    client = httpx.AsyncClient()

    start_time = time.time()
    success_count = 0
    error_count = 0
    latencies = []

    async def send_detection():
        nonlocal success_count, error_count
        try:
            frame = {
                "frame_id": fake.uuid4(),
                "timestamp": datetime.utcnow().isoformat(),
                "detections": [
                    {
                        "object_id": 0,
                        "class_name": "vehicle",
                        "confidence": random.uniform(0.85, 0.98),
                        "x_min": random.randint(0, 1920),
                        "y_min": random.randint(0, 1440),
                        "x_max": random.randint(100, 1920),
                        "y_max": random.randint(100, 1440),
                    }
                ]
            }

            resp_start = time.time()
            response = await client.post(
                "http://localhost:8001/ws/ydc",  # Note: WebSocket test
                json=frame,
                timeout=5
            )
            resp_end = time.time()

            if response.status_code == 200:
                success_count += 1
                latencies.append((resp_end - resp_start) * 1000)
            else:
                error_count += 1
        except Exception as e:
            error_count += 1

    # Fire 6,000 detections over 60 seconds (100/sec)
    tasks = [send_detection() for _ in range(6000)]
    await asyncio.gather(*tasks, return_exceptions=True)

    elapsed = time.time() - start_time

    # Assertions
    assert success_count > 5500, f"Too many errors: {error_count}"
    assert elapsed < 70, f"Load test too slow: {elapsed}s"
    assert np.median(latencies) < 200, f"Median latency too high: {np.median(latencies)}ms"

    print(f"✓ Load test passed: {success_count} successes, {error_count} errors")
    print(f"  Latency: min={min(latencies)}ms, p50={np.median(latencies)}ms, p99={np.percentile(latencies, 99)}ms")
```

---

## 12. Deployment Architecture

### 12.1 Docker Compose (Local Development)

```yaml
# docker-compose.yml
version: '3.8'

services:
  geolocation-engine2:
    image: geolocation-engine2:latest
    build:
      context: ../geolocation-engine2
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      FASTAPI_ENV: development
      DATABASE_URL: sqlite:///./data/app.db
      TAK_SERVER_URL: http://mock-tak:1080/CoT
      LOG_LEVEL: DEBUG
    volumes:
      - ./geolocation-engine2-data:/app/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 10s
      timeout: 5s
      retries: 3
    restart: unless-stopped

  ydc-adapter:
    image: ydc-adapter:latest
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8001:8001"
    depends_on:
      geolocation-engine2:
        condition: service_healthy
    environment:
      FASTAPI_ENV: development
      GEOLOCATION_API_URL: http://geolocation-engine2:8000
      CAMERA_PROVIDER_TYPE: mock
      MOCK_LAT: 40.7128
      MOCK_LON: -74.0060
      MOCK_ELEVATION: 100.0
      LOG_LEVEL: DEBUG
    volumes:
      - ./src:/app/src  # Hot reload
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/api/v1/health"]
      interval: 10s
      timeout: 5s
      retries: 3
    restart: unless-stopped

  mock-tak:
    image: mockserver/mockserver:latest
    ports:
      - "1080:1080"
    environment:
      MOCKSERVER_PROPERTY_FILE: /config/mockserver.properties
    volumes:
      - ./tests/mocktak:/config
    restart: unless-stopped

volumes:
  geolocation-engine2-data:
```

### 12.2 Dockerfile (YDC Adapter)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ .

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:8001/api/v1/health', timeout=5)" || exit 1

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
```

### 12.3 Production Deployment (Kubernetes, Phase 2)

```yaml
# k8s/ydc-adapter-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ydc-adapter
  namespace: default
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ydc-adapter
  template:
    metadata:
      labels:
        app: ydc-adapter
    spec:
      containers:
      - name: ydc-adapter
        image: registry.example.com/ydc-adapter:v1.0.0
        ports:
        - containerPort: 8001
        env:
        - name: FASTAPI_ENV
          value: production
        - name: GEOLOCATION_API_URL
          value: http://geolocation-engine2-service:8000
        - name: CAMERA_PROVIDER_TYPE
          value: mock  # Or dji/mavlink in Phase 2
        livenessProbe:
          httpGet:
            path: /api/v1/health
            port: 8001
          initialDelaySeconds: 10
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/v1/health
            port: 8001
          initialDelaySeconds: 5
          periodSeconds: 5
      resources:
        requests:
          memory: "256Mi"
          cpu: "250m"
        limits:
          memory: "512Mi"
          cpu: "500m"

---
apiVersion: v1
kind: Service
metadata:
  name: ydc-adapter-service
spec:
  selector:
    app: ydc-adapter
  ports:
  - protocol: TCP
    port: 8001
    targetPort: 8001
  type: LoadBalancer
```

---

## 13. Quality Attributes Strategy

### 13.1 Performance

**Target**: <200ms latency (frame in → WebSocket response out)

**Strategy**:
- **Domain layer**: Pure functions, O(1) complexity
- **Async I/O**: Concurrent camera provider + Geolocation-Engine2 calls (if needed)
- **Caching**: Optional in-memory cache for camera position (if stable)
- **Measurement**: Histogram metrics by operation (bbox extraction, provider call, api call)

**Acceptance Criteria**:
- Median latency <150ms (happy path)
- p99 latency <300ms
- No memory leaks over 24h (monitored)

### 13.2 Reliability

**Target**: 99.5% uptime (during TAK online window)

**Strategy**:
- **Retry with backoff**: Camera provider, Geolocation-Engine2
- **Graceful degradation**: If camera provider unavailable, error reply (not hang)
- **Async TAK push**: Non-blocking (handled by Geolocation-Engine2)
- **Health checks**: Kubernetes liveness/readiness probes

**Acceptance Criteria**:
- No single point of failure (restart doesn't lose data)
- Error recovery <10s (retry exhaustion)
- Health check responsive <100ms

### 13.3 Scalability

**Target**: Horizontal scaling to 1,000+ detections/second

**Strategy**:
- **Stateless design**: No inter-instance communication
- **Load balancer ready**: Multiple adapter instances behind LB
- **Connection pooling**: httpx for Geolocation-Engine2
- **Observability**: Metrics per instance for load distribution

**Acceptance Criteria**:
- Linear scaling up to 5 instances (80%+ efficiency)
- No inter-instance contention

### 13.4 Observability

**Target**: Debug any detection failure within 2 minutes

**Strategy**:
- **Structured JSON logging**: Stdout, parsed by container logs
- **Unique IDs**: frame_id, detection_id propagated through logs
- **Metrics**: Prometheus-compatible format
- **Correlation**: frame_id links all related logs

**Acceptance Criteria**:
- All errors logged with context (frame_id, operation, error message)
- Latency metrics aggregated (p50, p99, max)
- Error rate dashboard shows trending

### 13.5 Maintainability

**Target**: Onboard new camera provider (DJI/MAVLink) in <1 sprint

**Strategy**:
- **Hexagonal architecture**: Clear port/adapter boundaries
- **Minimal domain coupling**: Pure functions in domain layer
- **Comprehensive tests**: 85-90% coverage, clear fixtures
- **ADRs**: Document design decisions

**Acceptance Criteria**:
- New provider requires only 1 new adapter file
- No changes to orchestration or domain logic
- All new code tested (>85% coverage for new adapter)

---

## 14. ADRs (Architecture Decision Records)

### ADR-001: Hexagonal Architecture Over Layered

**Status**: Accepted

**Context**:
- Multiple camera position sources (Mock, DJI, MAVLink)
- Must support testing with mocks
- Domain logic should be testable without I/O

**Decision**:
Use hexagonal architecture (ports and adapters) with clear separation:
- Domain layer: Pure business logic (no I/O)
- Primary ports: Inbound (WebSocket, HTTP)
- Secondary ports: Outbound (Camera provider, Geolocation API, logging)

**Alternatives Considered**:
- **Layered (Controller → Service → Model)**: Less flexible for swapping implementations; domain tightly coupled to I/O
- **Event-driven (Pub/Sub)**: Overkill for MVP; async patterns sufficient

**Consequences**:
- **Positive**: Easy to test domain in isolation; new camera provider requires only new adapter
- **Negative**: Slight complexity in port/adapter interface definitions; extra indirection

---

### ADR-002: Separate YDC Adapter vs Embedded in Geolocation-Engine2

**Status**: Accepted

**Context**:
- Geolocation-Engine2 consumes raw image + pixel coordinates
- YDC provides bounding boxes (not pixel-perfect, frame-dependent)
- Two distinct integration patterns

**Decision**:
Build separate YDC Adapter microservice (standalone Docker container).

**Rationale**:
- Geolocation-Engine2 focuses on geolocation calculation
- YDC Adapter adds orchestration (WebSocket listening, camera position aggregation)
- Clear separation of concerns; independent deployment
- Allows future YDC → other backends (not just Geolocation-Engine2)

**Alternatives Considered**:
- **Embed in Geolocation-Engine2**: Mixes concerns; harder to test; tightly couples two distinct responsibilities
- **Separate service communicating via message queue**: Overkill for MVP; REST sufficient

**Consequences**:
- **Positive**: Independent scaling, deployment, testing
- **Negative**: Must manage two services locally (docker-compose); network latency between adapter and Geolocation-Engine2

---

### ADR-003: Synchronous REST (Not Async Queue)

**Status**: Accepted

**Context**:
- YDC sends continuous frame stream (WebSocket)
- Each detection requires geolocation
- Low latency is priority (<200ms target)

**Decision**:
Use synchronous REST API calls to Geolocation-Engine2 (POST /api/v1/detections).
Adapter blocks until response received, replies immediately to YDC.

**Rationale**:
- Latency: Sync call → response is immediate, no queue delay
- Simplicity: No message broker to manage
- Backpressure: If Geolocation-Engine2 slow, adapter naturally throttles
- Failure clarity: Error response immediate (not delayed)

**Alternatives Considered**:
- **Async queue (Kafka/RabbitMQ)**: Adds latency (queue drain delay); overkill for MVP
- **Batch processing**: Loses real-time property; defeats purpose
- **Fire-and-forget**: No error feedback; dangerous

**Consequences**:
- **Positive**: <200ms latency achievable; simple deployment
- **Negative**: Geolocation-Engine2 availability is critical; if down, adapter blocks

---

### ADR-004: Pluggable Camera Position Providers

**Status**: Accepted

**Context**:
- MVP uses Mock (fixed/randomized position)
- Phase 2: Add DJI telemetry, MAVLink support
- Different APIs per provider

**Decision**:
Abstract camera position as secondary port with pluggable adapters.

**Interface**:
```python
class CameraPositionProvider(ABC):
    async def get_position(frame_id: str) -> CameraPosition
    async def health_check() -> bool
```

**Rationale**:
- Extensible: New provider = new adapter file (no core changes)
- Testable: Mock adapter for unit tests
- Future-proof: Support new sources without refactoring

**Alternatives Considered**:
- **Configuration-driven (hardcoded if/elif)**: Not extensible; core logic couples to implementations
- **Factory pattern only**: Missing abstraction (port); no interface contract

**Consequences**:
- **Positive**: Easy to add DJI/MAVLink later; testable with mocks
- **Negative**: Slight overhead of abstract interface

---

### ADR-005: Stateless YDC Adapter (No Persistence)

**Status**: Accepted

**Context**:
- MVP is PoC/integration layer
- Geolocation-Engine2 already handles persistence (detections, offline queue, audit trail)
- Horizontal scaling desired

**Decision**:
YDC Adapter is stateless. No database, no disk persistence.

**Rationale**:
- Simplicity: No migration scripts, no schema management
- Horizontal scaling: Spin up/down instances independently
- Responsibility: Geolocation-Engine2 owns durability (detections already queued/audited there)

**Alternatives Considered**:
- **Local SQLite queue**: If Adapter buffers frames; adds complexity, doesn't scale horizontally
- **Shared database**: Premature; Phase 2+ only

**Consequences**:
- **Positive**: Simple deployment, scales horizontally
- **Negative**: Frame loss if adapter crashes during processing (mitigated by Geolocation-Engine2's offline queue)

---

### ADR-006: Python + FastAPI (Consistency with Geolocation-Engine2)

**Status**: Accepted

**Context**:
- Geolocation-Engine2 is Python + FastAPI
- Team expertise in Python
- Need async support for concurrent operations

**Decision**:
Build YDC Adapter in Python 3.11 + FastAPI.

**Rationale**:
- **Consistency**: Same stack as Geolocation-Engine2; easier operations/debugging
- **Async**: FastAPI + asyncio native for concurrent I/O (camera provider, API calls)
- **Team fit**: Python expertise available
- **Time-to-market**: Faster dev than Go/Rust

**Alternatives Considered**:
- **Go (goroutines)**: Faster at runtime but +3-4 weeks dev time; no geospatial libs
- **Node.js**: Type safety concerns; async error handling weaker
- **Rust**: Steep learning curve; +4-6 weeks

**Consequences**:
- **Positive**: Familiar stack, fast development, asyncio native
- **Negative**: Slightly lower throughput than Go at extreme scale (not an MVP blocker)

---

### ADR-007: Mock Camera Provider for MVP (Not Real DJI)

**Status**: Accepted

**Context**:
- MVP must deliver end-to-end flow (YDC → Adapter → Geolocation-Engine2 → TAK)
- DJI/MAVLink providers complex, require hardware/SDKs
- Time budget: 8-12 weeks

**Decision**:
Implement MockCameraPositionAdapter for MVP (fixed or randomized position).
DJI/MAVLink adapters deferred to Phase 2.

**Rationale**:
- **MVP focus**: Validate architecture, test integration with Geolocation-Engine2
- **Time**: DJI SDK setup + testing ~2-3 weeks; deferred doesn't block MVP delivery
- **Extensibility**: Port design allows easy addition later

**Alternatives Considered**:
- **All providers in MVP**: Out of scope, delays MVP by 2-3 weeks
- **No mock at all**: Can't test locally without hardware

**Consequences**:
- **Positive**: MVP ships on time, validates architecture
- **Negative**: Real drone integration deferred to Phase 2

---

## 15. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| **Geolocation-Engine2 unavailable** | Medium | High | Retry with backoff; error reply to YDC |
| **Camera provider API changes** | Low | Medium | Abstract port; adapter easily updated |
| **WebSocket connection instability** | Low | Medium | Graceful reconnect with exponential backoff |
| **Rate limit from Geolocation-Engine2** | Medium | Low | Respect 429; exponential backoff; queue overflow error |
| **Performance regression** | Low | Medium | Load testing in CI/CD; latency alerts |
| **Memory leak** | Low | Medium | Unit tests for resource cleanup; monitoring over 24h |

---

## 16. Success Criteria

### Architecture Validation

- [ ] Component boundaries clear: Primary/secondary ports defined
- [ ] Hexagonal architecture enforced: Domain layer has no I/O
- [ ] Adapters pluggable: New camera provider requires <200 LOC new code
- [ ] No cyclic dependencies: Layer diagram acyclic
- [ ] Error paths tested: At least 8 error scenarios covered

### Performance Targets

- [ ] Latency: Median <150ms, p99 <300ms (happy path)
- [ ] Throughput: 100+ detections/sec (single instance)
- [ ] Memory: <500MB resident (single instance)

### Reliability Targets

- [ ] Retry logic: Max 3 retries, exponential backoff
- [ ] Error recovery: <10 seconds (retry exhaustion)
- [ ] Health checks: <100ms response

### Observability Targets

- [ ] All errors logged with frame_id context
- [ ] Latency metrics: p50, p99, max tracked
- [ ] Error rate trending over time

### Testability Targets

- [ ] 85%+ code coverage
- [ ] Domain layer 95%+ coverage
- [ ] All integrations testable with mocks

---

## 17. Handoff to Acceptance Designer

**Architecture design complete. Ready for DISTILL wave.**

**Deliverables for Acceptance Designer**:
1. This architecture document (15 sections, 8,000+ words)
2. ADRs (7 records, design decisions documented)
3. C4 diagrams (System, Container, Component level)
4. Data models (Pydantic schemas)
5. Component boundaries (clear responsibilities)
6. Integration points (Geolocation-Engine2 API contract)
7. Error handling matrix (scenarios + recovery)
8. Test strategy (95 tests planned, layers defined)
9. Deployment templates (Docker Compose, Dockerfile, K8s stub)
10. Extension points (camera provider port, adapter examples)

**What the software-crafter will do (BUILD wave)**:
- Implement domain layer (BboxUtils, DetectionTransformer, etc.)
- Implement orchestration services (YdcToGeoProcessingService, ErrorRecoveryService)
- Implement adapters (MockCameraPositionAdapter, HttpGeolocationAdapter)
- Write 95+ tests (unit, service, integration, load)
- Build Docker image, Docker Compose setup
- Validate against acceptance criteria

**What the acceptance-designer will do (DISTILL wave)**:
- Write acceptance tests (Gherkin scenarios, robot framework)
- Validate quality attributes (performance, reliability)
- Sign off on hexagonal architecture compliance
- Prepare user documentation
- Coordinate with TAK/YDC teams on integration

---

## 18. Appendix: Glossary

| Term | Definition |
|------|-----------|
| **YDC** | YOLO Detection Component; real-time object detection via WebSocket |
| **Bbox** | Bounding box; four coordinates (x_min, y_min, x_max, y_max) around detected object |
| **Pixel center** | Arithmetic mean of bbox: pixel_x = (x_min + x_max) / 2 |
| **Geolocation-Engine2** | Existing FastAPI service; converts pixel → GPS coordinates via photogrammetry |
| **CoT XML** | Cursor on Target format; tactical XML for TAK/ATAK military systems |
| **TAK** | Tactical Assault Kit; military command & control system |
| **Hexagonal Architecture** | Ports & adapters pattern; domain layer isolated from I/O |
| **Primary Port** | Inbound; driven by external actor (YDC client via WebSocket) |
| **Secondary Port** | Outbound; depends on external service (camera telemetry, geolocation API) |
| **Adapter** | Concrete implementation of port interface; bridges domain to external system |
| **Provider** | Concrete implementation of secondary port; supplies data (camera position) |

---

**Document Version**: 1.0
**Last Updated**: 2026-02-17
**Author**: Morgan (Solution Architect)
**Status**: Ready for Acceptance Designer

