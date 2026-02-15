# Component Boundaries & Hexagonal Architecture

**System**: AI Detection to COP Translation System
**Pattern**: Hexagonal (Ports & Adapters)
**Date**: 2026-02-17

---

## Hexagonal Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      PRIMARY PORTS (Input)                   │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │ REST API   │  │Configuration │  │HealthCheck  │        │
│  │   Port     │  │    Port      │  │   Port      │        │
│  └────────────┘  └──────────────┘  └──────────────┘        │
│         ▲               ▲                  ▲                 │
└─────────┼───────────────┼──────────────────┼─────────────────┘
          │               │                  │
          │ HTTP/JSON     │ Config           │ Status
          │               │                  │
┌─────────▼───────────────▼──────────────────▼─────────────────┐
│                      ADAPTERS (External Interface)            │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │REST API    │  │Configuration │  │HealthCheck  │        │
│  │ Adapter    │  │   Adapter    │  │  Adapter    │        │
│  │(FastAPI)   │  │              │  │             │        │
│  └────────────┘  └──────────────┘  └──────────────┘        │
│         ▲               ▲                  ▲                 │
└─────────┼───────────────┼──────────────────┼─────────────────┘
          │               │                  │
          │               │                  │
┌─────────▼───────────────▼──────────────────▼─────────────────┐
│                     DOMAIN CORE (Business Logic)              │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ DetectionIngestionService                           │    │
│  │  • Parse JSON from APIs                             │    │
│  │  • Handle rate limits, timeouts                      │    │
│  │  • Extract required fields (lat, lon, conf, ts)     │    │
│  └──────────────────────┬──────────────────────────────┘    │
│                         │                                     │
│  ┌──────────────────────▼──────────────────────────────┐    │
│  │ GeolocationValidationService (KILLER FEATURE)       │    │
│  │  • Validate coordinate ranges                        │    │
│  │  • Check GPS accuracy metadata                       │    │
│  │  • Flag GREEN/YELLOW/RED                            │    │
│  │  • Apply terrain-specific expectations              │    │
│  └──────────────────────┬──────────────────────────────┘    │
│                         │                                     │
│  ┌──────────────────────▼──────────────────────────────┐    │
│  │ CotService                                          │    │
│  │  • Map object class to CoT type codes               │    │
│  │  • Map confidence flags to color codes              │    │
│  │  • Build CoT XML with point/detail elements         │    │
│  │  • Generate remarks with detection metadata         │    │
│  └──────────────────────┬──────────────────────────────┘    │
│                         │                                     │
│  ┌──────────────────────▼──────────────────────────────┐    │
│  │ TAK Push Service                                    │    │
│  │  • HTTP PUT CoT XML to TAK Server /CoT endpoint     │    │
│  │  • Handle connection failures & async non-blocking  │    │
│  │  • Mark SYNCED on success                           │    │
│  └──────────────────┬───────────────────┬──────────────┘    │
│                     │                   │                    │
│  ┌──────────────────▼────┐  ┌──────────▼────────────────┐   │
│  │OfflineQueueService    │  │ AuditTrailService        │   │
│  │ • Write to local queue │  │ • Log all events         │   │
│  │ • Sync when connected  │  │ • Maintain audit trail   │   │
│  │ • Batch optimization   │  │ • Enable debugging       │   │
│  └───────────────────────┘  └──────────────────────────┘   │
│                                                               │
└───────────┬──────────────────────────────────────────────────┘
            │
            │
┌───────────▼──────────────────────────────────────────────────┐
│                   SECONDARY PORTS (Output)                    │
│  ┌───────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐ │
│  │TAK Server │  │ Database │  │  Queue   │  │  Logging   │ │
│  │   Port    │  │  Port    │  │  Port    │  │   Port     │ │
│  └───────────┘  └──────────┘  └──────────┘  └────────────┘ │
│         ▲           ▲             ▲              ▲          │
└─────────┼───────────┼─────────────┼──────────────┼──────────┘
          │           │             │              │
          │           │             │              │
┌─────────▼───────────▼─────────────▼──────────────▼──────────┐
│                   ADAPTERS (External Interface)              │
│  ┌───────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐ │
│  │TAK HTTP   │  │SQLite    │  │SQLite    │  │Python      │ │
│  │Client     │  │ Adapter  │  │Queue     │  │logging     │ │
│  │Adapter    │  │          │  │Adapter   │  │Adapter     │ │
│  └───────────┘  └──────────┘  └──────────┘  └────────────┘ │
│         ▲           ▲             ▲              ▲          │
└─────────┼───────────┼─────────────┼──────────────┼──────────┘
          │           │             │              │
          │ HTTP PUT  │ Disk-based  │ Disk-based   │ stdout
          │           │ SQLite      │ SQLite       │ + files
          │           │             │              │
    ┌─────▼─────┐    └─────┬───────┘              └──────┐
    │ TAK Server│          │                            │
    │           │    ┌──────▼──────┐                   │Logging
    │ (External)│    │ /app/data/  │                   │System
    │           │    │  app.db     │                   │
    └───────────┘    └─────────────┘                   │
```

---

## Component Definitions & Responsibilities

### DOMAIN CORE COMPONENTS (Business Logic)

#### 1. DetectionIngestionService

**Responsibility**: Accept and parse detection data from external sources

**Interface**:
```python
class DetectionIngestionService:
    def ingest(self, raw_json: Dict) -> Detection:
        """
        Parse JSON, validate structure, extract required fields

        Args:
            raw_json: Raw JSON payload from external API

        Returns:
            Detection object with parsed fields

        Raises:
            ValidationError: If JSON invalid or required fields missing
        """
        pass

    def handle_rate_limit(self, retry_after: int) -> None:
        """Implement exponential backoff for rate-limited sources"""
        pass
```

**Responsibilities**:
- Parse JSON payload
- Validate JSON structure (well-formed)
- Extract required fields: latitude, longitude, confidence, type, timestamp
- Handle API rate limits (HTTP 429)
- Preserve original format (audit trail)
- Log ingestion events

**Inputs**:
- Raw JSON from REST API, polling loop

**Outputs**:
- Detection object (validated fields, original preserved)
- Ingestion event (to audit trail)

**Error Handling**:
- E001: INVALID_JSON → Log, skip detection, continue polling
- E004: API_TIMEOUT → Retry with exponential backoff

**Performance**:
- Latency: <10ms per detection
- Throughput: 100+ detections/second

---

#### 2. GeolocationValidationService (KILLER FEATURE)

**Responsibility**: Validate geolocation accuracy and flag with confidence level

**Interface**:
```python
class GeolocationValidationService:
    def validate(self, detection: Detection) -> Detection:
        """
        Validate geolocation and set accuracy_flag

        Args:
            detection: Detection with raw_coordinates

        Returns:
            Detection with validated_coordinates and accuracy_flag
        """
        pass

    def assess_accuracy(self,
                       accuracy_meters: float,
                       confidence: float,
                       terrain: str) -> AccuracyFlag:
        """
        Assess accuracy and return GREEN/YELLOW/RED flag

        Returns:
            AccuracyFlag: GREEN | YELLOW | RED
        """
        pass
```

**Responsibilities**:
- Validate coordinate ranges (latitude -90..90, longitude -180..180)
- Check GPS accuracy metadata (<500m for GREEN)
- Evaluate confidence score (>0.6 for GREEN)
- Apply terrain-specific accuracy expectations
- Flag for manual review (RED = invalid, YELLOW = borderline)
- Preserve original accuracy metadata

**Accuracy Thresholds**:
- GREEN: accuracy < 500m AND confidence > 0.6
- YELLOW: accuracy 500-1000m OR confidence 0.4-0.6
- RED: accuracy > 1000m OR confidence < 0.4

**Inputs**:
- Detection with raw_coordinates, confidence, metadata

**Outputs**:
- Detection with validated_coordinates and accuracy_flag
- Validation event (to audit trail)

**Performance**:
- Latency: <5ms per detection
- Accuracy: >95% of GREEN flags validated against ground truth

---

#### 3. CotService

**Responsibility**: Generate Cursor on Target (CoT) XML for TAK/ATAK systems

**Interface**:
```python
class CotService:
    def generate_cot_xml(self, detection: Detection, geolocation: GeolocationResult) -> str:
        """
        Generate CoT XML from detection and geolocation result

        Args:
            detection: Detection with object_class, ai_confidence, timestamp
            geolocation: Geolocation result with coordinates, uncertainty, confidence_flag

        Returns:
            CoT XML string (TAK-compatible)
        """
        pass
```

**Responsibilities**:
- Map object_class to CoT type code (b-m-p-s-u-c for vehicle, etc.)
- Map confidence_flag to color code (GREEN/-65536, YELLOW/-256, RED/-16711936)
- Build CoT XML with event, point (lat/lon/ce), detail (link/color/remarks/contact) elements
- Include remarks with AI class, AI confidence %, geo confidence flag, accuracy ±Xm
- Generate unique UIDs and callsigns for TAK display

**Inputs**:
- Detection with object_class, ai_confidence, camera_id, timestamp
- GeolocationResult with calculated_lat, calculated_lon, uncertainty_radius_meters, confidence_flag

**Outputs**:
- CoT XML string (TAK-parseable)
- Generation event (to audit trail)

**Performance**:
- Latency: <5ms per detection
- Compliance: 100% TAK-compatible CoT XML

---

#### 4. TAK Push (via CotService.push_to_tak_server)

**Responsibility**: Deliver CoT XML to TAK Server asynchronously

**Interface**:
```python
class CotService:
    async def push_to_tak_server(self, cot_xml: str) -> bool:
        """
        Send CoT XML to TAK Server via HTTP PUT

        Args:
            cot_xml: CoT XML string

        Returns:
            bool: True if successful, False otherwise

        Side effects:
            - Sends to TAK Server via HTTP PUT /CoT
            - Returns immediately (non-blocking)
            - Marks SYNCED on success
            - Falls back to queue on failure
        """
        pass
```

**Responsibilities**:
- HTTP PUT client with timeout handling (5 second timeout)
- Async, non-blocking push (doesn't block detection processing)
- Mark as SYNCED on success (HTTP 200/201/204)
- Fall back to OfflineQueueService on failure
- Log errors for monitoring
- Graceful degradation when TAK unavailable

**Inputs**:
- CoT XML ready for output

**Outputs**:
- Detection marked SYNCED (remote)
- Output event (to audit trail)
- Falls back to queue if TAK unavailable

**Performance**:
- Latency: <2 seconds end-to-end from ingestion
- Delivery: 99%+ of valid detections reach TAK
- Non-blocking: Detection accepted within 100ms regardless of TAK status

---

#### 5. OfflineQueueService

**Responsibility**: Persist detections locally when network unavailable, sync on reconnect

**Interface**:
```python
class OfflineQueueService:
    def enqueue(self, detection: Detection) -> None:
        """Write detection to local queue (PENDING_SYNC)"""
        pass

    async def sync(self) -> int:
        """
        Sync queued detections to remote systems

        Returns:
            Number of detections synced
        """
        pass

    async def monitor_connectivity(self) -> None:
        """Monitor network, auto-sync on restore"""
        pass
```

**Responsibilities**:
- Write to local SQLite queue (status: PENDING_SYNC)
- Monitor network connectivity
- Auto-sync when connection restored
- Batch sync for efficiency (1000+ items/second)
- Exponential backoff on failures
- Audit trail for all sync events

**Inputs**:
- Detection failed to output (network error)

**Outputs**:
- Detection persisted to SQLite
- Synced to remote when network available
- Queue status (for health check)

**Quality Attributes**:
- Reliability: 99.99% of queued detections synced
- Persistence: Queue survives reboot
- Transparency: No operator alerts for normal offline/sync

---

#### 6. AuditTrailService

**Responsibility**: Immutable event log for compliance and operations investigation

**Interface**:
```python
class AuditTrailService:
    def log_event(self, event: AuditEvent) -> None:
        """Log event to audit trail"""
        pass

    def get_detection_trail(self, detection_id: str) -> List[AuditEvent]:
        """Get all events for a specific detection"""
        pass
```

**Responsibilities**:
- Capture events from all services
- Timestamp every event (UTC)
- Log with structured data (JSON)
- Enable after-action review
- Support compliance audits
- Enforce retention policy (90-day minimum)

**Events Captured**:
- Detection received (source, timestamp, raw data)
- Validation results (accuracy flag, confidence)
- Transformation applied (GeoJSON format)
- Output sent (destination, timestamp, status)
- Operator actions (verified, corrected, etc.)
- Errors (code, recovery action)

**Inputs**:
- Events from DetectionIngestionService, GeolocationValidationService, etc.

**Outputs**:
- Audit trail records (queryable by detection_id)
- Compliance reports

---

### PRIMARY PORTS (Input)

#### REST API Port

**Purpose**: Accept incoming detection data and configuration requests from external systems

**Endpoints**:
- `POST /api/v1/detections` — Ingest detection JSON
- `GET /api/v1/detections/{id}` — Retrieve detection status
- `PUT /api/v1/detections/{id}/verify` — Manual verification
- `GET /api/v1/health` — System health check
- `GET /api/v1/audit/{detection_id}` — Audit trail query

**Contract**: HTTP REST with JSON payloads
**Responsibility**: Define API contracts, validation rules, error responses

---

#### Configuration Port

**Purpose**: Allow operators to register and configure detection sources

**Endpoints**:
- `POST /api/v1/sources` — Register new source
- `GET /api/v1/sources` — List configured sources
- `PUT /api/v1/sources/{id}` — Update source
- `POST /api/v1/sources/{id}/test` — Test connectivity

**Contract**: API for source management, field mapping, authentication
**Responsibility**: Define configuration schema, validation

---

#### HealthCheckPort

**Purpose**: Provide system diagnostics for monitoring

**Endpoints**:
- `GET /api/v1/health` — Overall system status
- `GET /api/v1/health/components` — Per-component status

**Contract**: JSON response with component statuses, queue depth, metrics
**Responsibility**: Define health check contract

---

### SECONDARY PORTS (Output)

#### TAK Server Port

**Purpose**: Output validated detections to TAK/ATAK systems

**Protocol**: HTTP PUT (subscription endpoint)
**Contract**: Send GeoJSON Features to TAK Server
**Responsibility**: Define TAK protocol contract, error handling

---

#### Database Port

**Purpose**: Persist detections, queue, and audit trail

**Operations**:
- Write Detection with validation results
- Write Queue entry
- Write Audit Trail events
- Query by detection_id, source, date range

**Contract**: ACID compliance, sub-second latency
**Responsibility**: Define schema, query patterns, consistency requirements

---

#### Queue Port (SQLite)

**Purpose**: Local persistent storage for offline-first queuing

**Operations**:
- Enqueue detection (PENDING_SYNC)
- Dequeue on sync (mark SYNCED)
- Query queue depth
- Batch load for sync

**Contract**: ACID-compliant local storage
**Responsibility**: Define queue schema, sync algorithm

---

#### Logging Port

**Purpose**: Audit trail and system logging

**Operations**:
- Log detection received
- Log validation results
- Log output status
- Log errors

**Contract**: Structured JSON logging, searchable by detection_id
**Responsibility**: Define logging schema, retention policy

---

### ADAPTERS (Implementation of Ports)

#### REST API Adapter

**Technology**: FastAPI + uvicorn
**Responsibility**:
- HTTP server implementing REST API Port
- Request validation (Pydantic)
- Error handling (HTTP status codes)
- Rate limiting (protect against abuse)

**Interfaces with**:
- DetectionIngestionService (ingest endpoint)
- Configuration Port (sources endpoint)
- HealthCheckPort (health endpoint)
- AuditTrailService (audit queries)

---

#### TAK Integration Adapter

**Technology**: Python httpx (async HTTP client)
**Responsibility**:
- HTTP client implementing TAK Server Port
- Connection pooling, timeouts, retry logic
- Exponential backoff on failures
- Audit trail for requests/responses

---

#### SQLite Adapter

**Technology**: Python asyncio + aiosqlite
**Responsibility**:
- Local persistent storage
- Schema management (migrations)
- Connection pooling
- Transaction handling

---

#### File System Adapter

**Technology**: Native filesystem + SQLite
**Responsibility**:
- Offline queue persistence
- ACID compliance
- Automatic cleanup

---

## Service Interaction Flows

### Happy Path: Detection Ingestion to TAK Map Display

```
1. Camera detects object in image (pixel coordinates + camera metadata)
   ↓
2. REST API Adapter receives HTTP POST with image_base64, pixel_x, pixel_y, sensor metadata
   ↓
3. DetectionService.accept_detection()
   - Parse image + pixel coordinates
   - Extract sensor metadata (camera pose, intrinsics)
   ↓
4. GeolocationCalculationService.calculate()
   - Pinhole camera model
   - Ray-ground plane intersection (photogrammetry)
   - Output: calculated_lat, calculated_lon, uncertainty_radius_m
   ↓
5. Confidence calculation
   - Ray-to-ground angle
   - Camera elevation
   - Output: confidence_flag (GREEN/YELLOW/RED)
   ↓
6. AuditTrailService.log_event("geolocated")
   ↓
7. CotService.generate_cot_xml()
   - Map object_class to CoT type code
   - Map confidence_flag to color code
   - Build CoT XML with point (lat/lon/ce) and detail (remarks/contact)
   ↓
8. AuditTrailService.log_event("cot_generated")
   ↓
9. CotService.push_to_tak_server() [async, non-blocking]
   - HTTP PUT CoT XML to TAK Server /CoT endpoint
   - Mark SYNCED on success
   ↓
10. AuditTrailService.log_event("output_success")
    ↓
11. Detection appears on TAK map with correct symbology within 2 seconds
```

### Error Path: Network Failure

```
1-8. [Same as happy path: detection processed through photogrammetry to CoT generation]
   ↓
9. CotService.push_to_tak_server() [async, non-blocking]
   - Attempt HTTP PUT CoT XML to TAK Server
   - Connection timeout or connection refused
   ↓
10. CotService catches NetworkError
    - Calls OfflineQueueService.enqueue(cot_xml, detection_id)
    ↓
11. OfflineQueueService.enqueue()
    - Write CoT XML to SQLite queue (PENDING_SYNC)
    - Update detection status: "QUEUED"
    ↓
12. AuditTrailService.log_event("queued_offline")
    ↓
13. OfflineQueueService.monitor_connectivity()
    - Detects TAK Server online (periodically checks)
    - Calls sync()
    ↓
14. OfflineQueueService.sync()
    - Batch load all PENDING_SYNC CoT items
    - HTTP PUT each to TAK Server
    - Mark SYNCED
    ↓
15. AuditTrailService.log_event("sync_success")
    ↓
16. Detection now appears on TAK map (with timestamp showing it's from earlier)
```

---

## Dependency Injection & Testability

### Service Dependencies

```python
# Wiring (main.py)
app = FastAPI()

# Adapters
rest_api_adapter = RestAPIAdapter()
sqlite_adapter = SQLiteAdapter(db_path="/app/data/app.db")
logging_adapter = LoggingAdapter()
tak_adapter = TAKAdapter(tak_url="https://tak.example.com")

# Services
audit_service = AuditTrailService(logging_adapter)
ingestion_service = DetectionIngestionService(audit_service)
validation_service = GeolocationValidationService(audit_service)
translation_service = FormatTranslationService(audit_service)
queue_service = OfflineQueueService(sqlite_adapter, audit_service)
output_service = TACOutputService(tak_adapter, queue_service, audit_service)

# Wire to REST adapter
rest_api_adapter.set_services(
    ingestion_service,
    validation_service,
    translation_service,
    output_service
)

app.include_router(rest_api_adapter.router)
```

### Testing: Mock External Systems

```python
# Test with mock TAK Server
mock_tak_adapter = MockTAKAdapter()
output_service = TACOutputService(mock_tak_adapter, queue_service, audit_service)

# Test detection → map flow
detection = Detection(...)
output_service.output(detection)  # Calls mock adapter
assert mock_tak_adapter.received_features == [...]

# Test network failure
mock_tak_adapter.simulate_network_error()
output_service.output(detection)  # Should queue locally
assert queue_service.get_queue_depth() == 1
```

---

## Component Lifecycle

### Startup

1. **Adapter Initialization**
   - SQLite: Create tables if not exist, run migrations
   - HTTP client: Initialize connection pools
   - Logging: Setup structured logging

2. **Service Initialization**
   - AuditTrailService: Load retention policy
   - OfflineQueueService: Recover persisted queue items
   - DetectionIngestionService: Load polling configuration

3. **Health Check**
   - Verify SQLite database connectivity
   - Verify TAK Server reachability
   - Set system status: READY

### Shutdown

1. **Graceful Shutdown**
   - Stop accepting new detections
   - Wait for in-flight detections to complete (5-second timeout)
   - Flush audit trail (ensure all events persisted)
   - Close database connections
   - Close HTTP connections

### Error Recovery

- **Component Failure**: System continues operating with degraded mode
  - TAK Server down? Queue locally, continue accepting detections
  - Database error? Retry with exponential backoff
- **Health Check**: Every 30 seconds, verify component health
- **Auto-Restart**: Failed components auto-restart (with backoff)

---

## Evolution & Decomposition Path (Phase 2)

**Current State (MVP)**: All components in single process

**Future State (Phase 2)**: Microservices if scaling needed

**Decomposition Strategy**:

1. **Extract GeolocationValidationService** to separate container
   - Most CPU-intensive component
   - Enable independent scaling
   - Introduce message queue between Ingestion and Validation

2. **Extract TACOutputService** to separate container
   - Handles network I/O
   - Can scale independently
   - Add message queue between Translation and Output

3. **Migrate to PostgreSQL**
   - SQLite fine for single container
   - PostgreSQL needed for multi-service consistency

4. **Deploy with Kubernetes**
   - Each service in separate pod
   - Automatic scaling based on CPU
   - Service mesh for inter-service communication

**Code Impact**: >80% of code remains unchanged (business logic, tests)
Only communication layer (HTTP/message queue) replaces function calls

---

## Summary

This hexagonal architecture enables:

1. **Clear Boundaries**: Each service has single responsibility
2. **Testability**: Mock external systems, test components independently
3. **Evolvability**: Service interfaces abstract implementation
4. **Scalability**: Decompose to microservices when needed
5. **Maintainability**: Dependencies explicit, easy to understand flow

**MVP**: Single process, all components in-process
**Phase 2**: Microservices, message queues, Kubernetes
**Evolution Path**: Clear from day 1
