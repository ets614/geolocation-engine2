# AI Detection to COP Translation System - Architecture Design

**Project**: AI Object Detection to COP Translation System (Walking Skeleton MVP)
**Phase**: DESIGN Wave Architecture
**Date**: 2026-02-17
**Status**: FINAL - Ready for Implementation (BUILD Wave)
**Architecture Pattern**: Hexagonal (Ports & Adapters)
**System Style**: Monolithic with Offline-First Resilience

---

## 1. System Context & Business Capabilities

### Problem Statement
Integration teams waste 2-3 weeks per detection source, lose 30% of detections to system failures, and spend 30+ minutes per mission validating geolocation accuracy. Manual workarounds (screenshots, manual data entry) are standard operational practice.

### Solution Overview
A translation system that:
1. **Accepts** detection data from multiple sources (REST APIs, UAVs, satellites, cameras)
2. **Validates** geolocation with automatic GREEN/YELLOW/RED accuracy flagging
3. **Transforms** to standardized GeoJSON format (RFC 7946)
4. **Delivers** to TAK/ATAK/CAD systems in real-time
5. **Queues** locally when network unavailable, auto-syncs on reconnect

### Business Outcomes (Validated in Discovery)
- **Integration Time**: 2-3 weeks → <1 hour (96% faster)
- **Manual Validation**: 30 min/mission → 5 min (80% savings)
- **System Reliability**: 70% → >99% (offline-first architecture)
- **Time to Detection on Map**: Variable → <2 seconds (tactical operations)

### Customer Segments Served
1. **Emergency Services** (PRIMARY) — Fire detection, dispatch integration
2. **Military/Defense** (SECONDARY) — ISR, TAK Server, ATAK
3. **Law Enforcement** (TERTIARY) — Camera/CCTV integration, suspect tracking
4. **GIS/Geospatial** (TERTIARY) — Multi-source management, ArcGIS integration
5. **Field Operators** (SUPPORT) — UAV pilots, ground station operators

---

## 2. Hexagonal Architecture - Component Boundaries

### Core Domain (Business Logic)

#### 2.1 DetectionIngestionService
**Responsibility**: Accept and parse detection data from external sources
**Input**: Raw JSON from REST APIs, UAVs, satellites, cameras
**Output**: Normalized Detection objects with metadata preserved
**Key Operations**:
- Parse JSON payloads (validate structure, extract fields)
- Handle API rate limits (429 backoff, exponential retry)
- Preserve original format (for audit trail, replay)
- Log ingestion events with timestamps

**Design Decision**: Single ingestion service with pluggable parsers (polymorphism by source type) vs. separate parsers. Chosen: Single service with type-based dispatch for centralized error handling, consistent logging, unified rate limit management.

#### 2.2 GeolocationValidationService
**Responsibility**: Validate and normalize geolocation with confidence flagging (KILLER FEATURE)
**Input**: Detection with raw coordinates, confidence, metadata
**Output**: Validated Detection with accuracy_flag (GREEN/YELLOW/RED)
**Key Operations**:
- Validate coordinate ranges (latitude [-90, 90], longitude [-180, 180])
- Check GPS accuracy metadata (<500m threshold for GREEN)
- Evaluate confidence scores (>0.6 for GREEN)
- Apply terrain-specific accuracy expectations (mountains ±200m vs. sea level ±45m)
- Flag for manual review (RED = invalid, YELLOW = borderline)

**Quality Attribute**: 95% accuracy on GREEN flags (validated against ground truth)

**Design Decision**: Geolocation validation as separate service vs. integrated into ingestion. Chosen: Separate service allows reuse across multiple input types, independent testing, independent evolution of accuracy algorithms.

#### 2.3 FormatTranslationService
**Responsibility**: Convert normalized detections to standardized GeoJSON format
**Input**: Validated Detection with accuracy flags
**Output**: RFC 7946 compliant GeoJSON Feature
**Key Operations**:
- Normalize confidence to 0-1 scale (preserve original in metadata)
- Build GeoJSON geometry (Point with [longitude, latitude])
- Include properties (source, confidence, accuracy, timestamp, audit trail)
- Validate RFC 7946 compliance

**Design Decision**: Separate translation service vs. inline transformation. Chosen: Separate allows reuse if multiple output formats added (CAD formats, custom formats), independent schema versioning.

#### 2.4 TACOutputService
**Responsibility**: Deliver validated GeoJSON to TAK/ATAK systems
**Input**: GeoJSON Feature with accuracy flag
**Output**: TAK Server subscription endpoint (HTTP PUT)
**Key Operations**:
- HTTP client with timeout/retry handling
- Batch delivery for high-volume streams (10+ detections/minute)
- Mark as SYNCED on success
- Fall back to OfflineQueueService on failure

**Design Decision**: Separate output service vs. integrated. Chosen: Separation enables multi-output strategy (TAK + CAD + GIS in future), independent evolution of each protocol.

#### 2.5 OfflineQueueService
**Responsibility**: Persist detections locally when network unavailable, sync on reconnect
**Input**: GeoJSON Feature with sync status
**Output**: Persisted to SQLite queue, synced to remote on connectivity restore
**Key Operations**:
- Write to local SQLite queue (status: PENDING_SYNC)
- Monitor network connectivity
- Auto-sync when connection restored (exponential backoff on failures)
- Batch sync for efficiency (1000+ items/sec)
- Audit trail for all sync events

**Design Decision**: Offline-first architecture (always local first, then remote) vs. remote-first with fallback. Chosen: Offline-first ensures zero data loss during network outages, transparent to operators, critical for field operations (Interview 4 requirement).

#### 2.6 AuditTrailService
**Responsibility**: Immutable event log for compliance and operations investigation
**Input**: Events from all other services
**Output**: Persisted audit records with timestamps
**Events Captured**:
- Detection received (source, timestamp, raw data)
- Validation results (accuracy flag, confidence, checks performed)
- Transformation applied (GeoJSON, field mappings)
- Output sent (destination, timestamp, status)
- Operator actions (viewed, verified, corrected, dispatched)
- Error conditions (code, severity, recovery action)

**Quality Attribute**: 90-day retention minimum, searchable by detection_id

### Primary Ports (Input - How External Systems Call Us)

#### 2.7 REST API Port
**Contract**: HTTP endpoints accepting JSON
**Endpoints**:
- `POST /api/v1/detections` — Ingest detection JSON
- `GET /api/v1/detections/{id}` — Retrieve detection status
- `PUT /api/v1/detections/{id}/verify` — Manual verification (YELLOW flagging)
- `GET /api/v1/health` — System health check
- `GET /api/v1/audit/{detection_id}` — Audit trail for detection

**Response Format**:
```json
{
  "id": "uuid",
  "status": "RECEIVED|VALIDATED|TRANSFORMED|SYNCED|FAILED",
  "accuracy_flag": "GREEN|YELLOW|RED",
  "timestamp": "2026-02-17T14:35:42Z"
}
```

**Quality Attribute**: <100ms response time for POST, handle 10+ requests/second

#### 2.8 Configuration Port
**Contract**: API to register and configure detection sources
**Operations**:
- `POST /api/v1/sources` — Register new detection source
- `GET /api/v1/sources` — List configured sources
- `PUT /api/v1/sources/{id}` — Update source configuration
- `POST /api/v1/sources/{id}/test` — Test source connectivity

**Configuration Schema**:
```yaml
name: "satellite_fire_api"
type: "satellite_fire"
api_endpoint: "https://api.fire.detection.io/v1/detections"
authentication: "api_key"
api_key: "${SECRET_API_KEY}"
polling_interval_seconds: 30
field_mapping:
  latitude: "latitude"
  longitude: "longitude"
  confidence: "confidence_0_100"  # Will normalize 0-100 → 0-1
  type: "fire_type"
  timestamp: "timestamp"
```

#### 2.9 HealthCheckPort
**Contract**: Diagnostic endpoints for monitoring
**Endpoints**:
- `GET /api/v1/health` — Overall system status
- `GET /api/v1/health/components` — Per-component status

**Response**:
```json
{
  "status": "UP|DOWN|DEGRADED",
  "components": {
    "api_connections": "UP",
    "database": "UP",
    "tak_server": "DEGRADED",
    "queue": "UP"
  },
  "queue_depth": 3,
  "detections_processed": 1250
}
```

### Secondary Ports (Output - How We Call External Systems)

#### 2.10 TAK Server Port
**Contract**: HTTP subscription endpoint for GeoJSON streaming
**Protocol**: HTTP PUT to TAK Server GeoJSON subscription
**Responsibility**:
- Push validated GeoJSON Features to TAK Server
- Handle connection failures gracefully
- Implement exponential backoff for retries

**Example Request**:
```
PUT /api/takmaps/version/capabilities/search/geo/takserver/geojson/json
Content-Type: application/json

{
  "type": "Feature",
  "geometry": { "type": "Point", "coordinates": [-117.5678, 32.1234] },
  "properties": { ... }
}
```

#### 2.11 Database Port
**Contract**: Persistent storage for detections, queue, audit trail
**Operations**:
- Write Detection record with validation results
- Write Queue entry (PENDING_SYNC)
- Mark Queue entry SYNCED
- Write Audit Trail events
- Query by detection_id, source, date range

**Quality Attribute**: Sub-second latency for reads/writes

#### 2.12 Queue Port (SQLite)
**Contract**: Local SQLite database for offline-first queuing
**Operations**:
- Enqueue detection (status: PENDING_SYNC)
- Dequeue on sync success (mark SYNCED)
- Query queue depth
- Batch load for sync operations

**Schema**:
```sql
CREATE TABLE offline_queue (
  id TEXT PRIMARY KEY,
  detection_json TEXT NOT NULL,
  status TEXT DEFAULT 'PENDING_SYNC',
  created_at TEXT NOT NULL,
  synced_at TEXT,
  retry_count INTEGER DEFAULT 0,
  error_message TEXT
);
```

#### 2.13 Logging Port
**Contract**: Audit trail and system logging
**Operations**:
- Log detection received (info level)
- Log validation results (info/warning based on flag)
- Log output to TAK (info)
- Log errors with severity and recovery action
- Structured logging: JSON format with detection_id, source, timestamp

**Example Log Entry**:
```json
{
  "timestamp": "2026-02-17T14:35:42Z",
  "level": "INFO",
  "event": "detection_received",
  "detection_id": "abc-123",
  "source": "satellite_fire_api",
  "confidence": 0.92
}
```

### Adapters (Implementation of Ports)

#### 2.14 REST API Adapter
**Technology**: FastAPI (Python) or Gin (Go)
**Responsibility**: HTTP server implementing Primary Ports
**Quality Attributes**:
- Async request handling (handle concurrent requests)
- Request validation (Pydantic/JSON schema)
- Error handling (return appropriate HTTP status codes)
- Rate limiting (protect against abuse)

#### 2.15 TAK Integration Adapter
**Technology**: Python `requests` or Go `net/http`
**Responsibility**: HTTP client implementing TAK Server Port
**Quality Attributes**:
- Connection pooling for efficiency
- Timeout handling (5-second default)
- Exponential backoff on failures
- Preserve request/response for audit trail

#### 2.16 SQLite Adapter
**Technology**: Python `sqlite3` or Go `database/sql` + `mattn/go-sqlite3`
**Responsibility**: Local persistent storage
**Quality Attributes**:
- Transaction support for consistency
- Connection pooling
- Schema migrations on startup
- Backup/recovery capabilities

#### 2.17 File System Adapter
**Technology**: Native filesystem + SQLite
**Responsibility**: Offline queue persistence
**Quality Attributes**:
- ACID compliance (via SQLite)
- Recovery from crashes
- Automatic cleanup of old synced items

---

## 3. Data Model Design

### 3.1 Core Entities

#### Detection Entity
```yaml
detection_id: UUID  # Unique identifier
source_type: String  # "satellite", "uav", "camera", "api", etc.
detection_class: String  # "vehicle", "person", "fire", etc.
confidence_original:
  value: Float  # Original confidence value
  scale: String  # "0-1", "0-100", etc.
confidence: Float  # Normalized to 0-1
raw_coordinates:
  latitude: Float
  longitude: Float
  accuracy_meters: Float  # GPS accuracy metadata
validated_coordinates:
  latitude: Float
  longitude: Float
  accuracy_meters: Float
  accuracy_flag: Enum  # GREEN | YELLOW | RED
  validated_at: ISO8601
timestamp: ISO8601  # Time of detection (at source)
received_timestamp: ISO8601  # Time system received it
processed_at: ISO8601  # Time system processed it
original_format_data: JSON  # Raw payload (for audit)
metadata: JSON  # Preserved from source (sensor, band, etc.)
sync_status: Enum  # PENDING_SYNC | SYNCED | FAILED
error_message: Optional[String]
operator_verified: Optional[Boolean]
operator_notes: Optional[String]
audit_trail_ids: List[UUID]  # Links to audit events
```

#### GeoJSON Output Format (RFC 7946)
```json
{
  "type": "Feature",
  "id": "detection-abc-123",
  "geometry": {
    "type": "Point",
    "coordinates": [-117.5678, 32.1234]
  },
  "properties": {
    "source": "satellite_fire_api",
    "source_id": "sat_1",
    "detection_type": "fire",
    "confidence": 0.92,
    "confidence_original": {"value": 92, "scale": "0-100"},
    "accuracy_m": 180,
    "accuracy_flag": "YELLOW",
    "timestamp": "2026-02-17T14:35:42Z",
    "received_timestamp": "2026-02-17T14:35:43Z",
    "sync_status": "SYNCED",
    "operator_verified": true,
    "operator_notes": "Location verified against satellite imagery"
  }
}
```

#### Offline Queue Entity
```yaml
queue_id: UUID
detection_json: String  # Full GeoJSON Feature as string
status: Enum  # PENDING_SYNC | SYNCED | FAILED
created_at: ISO8601
synced_at: Optional[ISO8601]
retry_count: Integer
error_message: Optional[String]
batch_id: Optional[UUID]  # For batch sync tracking
```

#### Audit Trail Entity
```yaml
event_id: UUID
detection_id: UUID  # Foreign key to Detection
event_type: Enum  # "received" | "validated" | "transformed" | "output" | "error" | "operator_action"
source: String  # "api" | "system" | "operator"
timestamp: ISO8601  # When event occurred
details: JSON  # Event-specific data
  - For "received": {api_endpoint, response_time_ms}
  - For "validated": {accuracy_flag, confidence, checks_performed}
  - For "transformed": {transformation_type, errors}
  - For "output": {destination, status, response_time_ms}
  - For "error": {error_code, error_message, recovery_action}
  - For "operator_action": {action, user_id, notes}
status: Enum  # "success" | "warning" | "error"
retention_until: ISO8601  # 90 days minimum
```

### 3.2 Coordinate System & Accuracy Thresholds

**Coordinate System**: WGS84 (World Geodetic System 1984)
- Latitude range: -90 to +90 degrees
- Longitude range: -180 to +180 degrees
- Precision: Decimal degrees (6 decimal places = ~0.1m accuracy)

**Accuracy Thresholds**:
- GREEN: accuracy < 500m AND confidence > 0.6 (80% of detections in field ops)
- YELLOW: accuracy 500-1000m OR confidence 0.4-0.6 (15% of detections)
- RED: accuracy > 1000m OR confidence < 0.4 OR out-of-range (5% of detections)

**Terrain-Specific Expectations**:
- Sea level/flat: ±45m typical GPS accuracy
- Mountains: ±200m typical GPS accuracy
- Dense urban: ±100m typical GPS accuracy
- Satellite imagery: ±180m typical accuracy (LANDSAT-8)

### 3.3 Confidence Normalization Rules

**Input Scales Supported**:
- 0-1 scale (drone, onboard AI) — use as-is
- 0-100 scale (satellite, camera APIs) — divide by 100
- Percentage (50%, 75%) — divide by 100
- Text labels (high/medium/low) — map to (0.8/0.5/0.2)

**Normalization Examples**:
- Drone confidence 0.89 → normalized 0.89 (0-1 scale)
- Satellite confidence 92 → normalized 0.92 (92/100)
- Camera confidence 78% → normalized 0.78 (78/100)
- Text "high" → normalized 0.8

**Audit Trail**: Always preserve original in `confidence_original` field for replay/debugging

---

## 4. Technology Stack Selection

### 4.1 Language & Runtime

**Selected**: Python 3.11+

**Rationale**:
- Rich geospatial library ecosystem (Shapely, pyproj, geopy)
- Fast development cycle (match 8-12 week timeline)
- Strong async support (asyncio) for concurrent API polling
- Excellent JSON handling (Pydantic for validation)
- Native SQLite support
- Strong community for integrations (TAK Server, ArcGIS)

**Alternatives Considered**:
- Go: Higher performance, strong networking → Would add complexity for detection validation algorithms, slower dev cycle
- Rust: Maximum performance → Overkill for this workload, slower dev cycle
- Node.js: Good async → Weak geospatial libraries, less suitable for validation logic

### 4.2 Web Framework

**Selected**: FastAPI 0.104+

**Rationale**:
- Built-in async (handles 10+ requests/second easily)
- Automatic request validation (Pydantic)
- Auto-generated OpenAPI documentation
- Excellent performance (modern ASGI)
- Type hints for IDE support and documentation
- Small learning curve for team

**Key Dependencies**:
- `fastapi` — Web framework
- `uvicorn` — ASGI server
- `pydantic` — Data validation
- `httpx` — Async HTTP client

### 4.3 Geospatial Libraries

**Selected**: Shapely + pyproj + geopy

**Rationale**:
- Shapely: Point validation, coordinate system operations
- pyproj: Coordinate system transformations (WGS84, State Plane, etc.)
- geopy: Distance calculations, reverse geocoding (for operator map context)
- All are actively maintained, widely used in GIS community

**Alternative**: PostGIS inside PostgreSQL → Overkill for MVP, adds deployment complexity

### 4.4 Data Validation

**Selected**: Pydantic v2

**Rationale**:
- Type-safe validation (catch errors at parse time)
- Automatic JSON schema generation
- Serialization to/from JSON
- Custom validators for domain rules (coordinate ranges, confidence bounds)

**Key Usage**:
- Input validation (REST API requests)
- Detection model validation
- Configuration schema validation
- GeoJSON output validation

### 4.5 Async Framework

**Selected**: asyncio (standard library)

**Rationale**:
- Built into Python standard library
- Sufficient for MVP concurrency needs
- Well-understood by team
- Integrates seamlessly with FastAPI

**Key Operations** (async):
- Polling external APIs (30s intervals)
- HTTP requests to TAK Server
- SQLite operations (async wrapper)
- Network connectivity monitoring

### 4.6 Database - Persistence

**Selected**: SQLite (local) + PostgreSQL (optional production)

**Rationale**:
- **SQLite (MVP)**: Embedded, zero configuration, ACID compliance, perfect for offline queue
- **PostgreSQL (future)**: When multi-server deployment needed, better concurrent writes
- Zero license cost, open source

**Schema Migrations**: Alembic (SQLAlchemy migration tool)

**Alternative**: NoSQL databases (MongoDB) → Not suitable for relational detection data, adds operational overhead

### 4.7 Offline Queuing

**Selected**: SQLite with polling + event-driven sync

**Architecture**:
```
Detection → Try remote write
         ↓
      Success? → Mark SYNCED
         ↓
        NO → Write to SQLite queue (PENDING_SYNC)
             ↓
             Monitor connectivity
             ↓
             Connection restored? → Batch sync to remote
                                  ↓
                                  Mark all SYNCED
```

**Quality Attributes**:
- Zero data loss (persistence before network)
- Transparent to operators
- Auto-recovery on reconnect
- Batch sync efficiency (1000+ items/sec)

### 4.8 Logging & Audit Trail

**Selected**: Python `logging` module + structured JSON logging

**Format**: JSON with structured fields
```json
{
  "timestamp": "2026-02-17T14:35:42Z",
  "level": "INFO",
  "logger": "detection_ingestion_service",
  "event": "detection_received",
  "detection_id": "abc-123",
  "source": "satellite_fire_api",
  "confidence": 0.92,
  "sync_status": "PENDING_SYNC"
}
```

**Retention**: SQLite audit table (90-day default)

**Tool**: Python `structlog` for structured logging, or standard `logging` with JSON formatter

### 4.9 HTTP Client

**Selected**: `httpx` (async HTTP client)

**Rationale**:
- Async-first design (matches FastAPI)
- Connection pooling built-in
- Timeout handling
- Request/response logging for audit
- Active maintenance

**Key Usage**:
- Polling external APIs (satellite, UAV, camera systems)
- Pushing to TAK Server
- Configuration source validation

### 4.10 Container & Deployment

**Selected**: Docker + Docker Compose

**Rationale**:
- Single image for MVP deployment
- Local dev = production environment
- Easy to iterate
- Portable across environments

**Dockerfile Structure**:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY src/ .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0"]
```

**Docker Compose** (local dev + MVP):
```yaml
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:///./app.db
    volumes:
      - ./data:/app/data
```

**Future**: Kubernetes for production scaling

### 4.11 Configuration Management

**Selected**: Environment variables + YAML configuration file

**Approach**:
- Secrets (API keys) → Environment variables
- Operational config (polling intervals) → YAML file
- Deployment config (database, logging) → Environment variables

**Example `.env`**:
```bash
FASTAPI_ENV=production
DATABASE_URL=sqlite:///./app.db
TAK_SERVER_URL=https://tak.example.com
SATELLITE_API_KEY=abc-def-ghi
LOG_LEVEL=INFO
QUEUE_MAX_SIZE=10000
```

**Example `config.yaml`**:
```yaml
sources:
  - name: satellite_fire_api
    endpoint: https://api.fire.detection.io/v1/detections
    polling_interval_seconds: 30
    authentication_method: api_key
    field_mapping:
      latitude: latitude
      longitude: longitude
      confidence: confidence_0_100
      type: fire_type
      timestamp: timestamp
```

### 4.12 Testing Framework

**Selected**: pytest + hypothesis (property-based testing)

**Coverage Requirements**:
- Unit tests: 80%+ (validation logic, geospatial calculations)
- Integration tests: 100% (API endpoints, TAK integration, queue sync)
- E2E tests: Happy path + error recovery

**Key Test Fixtures**:
- Mock TAK Server (for testing output failures)
- Simulated network outages (timeout injection)
- Sample detections in all formats (satellite, drone, camera)

### 4.13 Open Source Licenses

**All selected technologies**: GPL-compatible or MIT/Apache

| Technology | License | Cost |
|-----------|---------|------|
| Python 3.11 | PSF | FREE |
| FastAPI | MIT | FREE |
| Pydantic | MIT | FREE |
| Shapely | BSD | FREE |
| pyproj | MIT | FREE |
| geopy | MIT | FREE |
| httpx | BSD | FREE |
| SQLite | Public Domain | FREE |
| Docker | Community (free) | FREE |
| Alembic | MIT | FREE |
| pytest | MIT | FREE |

**Total Stack Cost**: $0 (fully open source)

---

## 5. Integration Patterns & API Contracts

### 5.1 Inbound Integration - REST API

#### Endpoint 1: Ingest Detection
```
POST /api/v1/detections
Content-Type: application/json

{
  "latitude": 32.1234,
  "longitude": -117.5678,
  "confidence": 0.85,
  "type": "fire",
  "timestamp": "2026-02-17T14:35:42Z",
  "metadata": {"sensor": "LANDSAT-8", "band": "thermal"}
}
```

**Response (Success)**:
```
HTTP 202 Accepted

{
  "id": "det-abc-123",
  "status": "RECEIVED",
  "accuracy_flag": null,
  "timestamp": "2026-02-17T14:35:43Z"
}
```

**Response (Malformed JSON)**:
```
HTTP 400 Bad Request

{
  "error": "E001_INVALID_JSON",
  "message": "JSON parse error: missing required field 'latitude'",
  "timestamp": "2026-02-17T14:35:43Z"
}
```

**Response (Rate Limited)**:
```
HTTP 429 Too Many Requests
Retry-After: 60

{
  "error": "RATE_LIMITED",
  "message": "Too many requests. Retry after 60 seconds.",
  "timestamp": "2026-02-17T14:35:43Z"
}
```

#### Endpoint 2: Get Detection Status
```
GET /api/v1/detections/{detection_id}
```

**Response**:
```json
{
  "id": "det-abc-123",
  "source": "satellite_fire_api",
  "status": "SYNCED",
  "accuracy_flag": "GREEN",
  "confidence": 0.92,
  "latitude": 32.1234,
  "longitude": -117.5678,
  "timestamp": "2026-02-17T14:35:42Z",
  "received_at": "2026-02-17T14:35:43Z",
  "processed_at": "2026-02-17T14:35:44Z"
}
```

#### Endpoint 3: Verify Detection (Manual Override for YELLOW)
```
PUT /api/v1/detections/{detection_id}/verify
Content-Type: application/json

{
  "verified": true,
  "notes": "Location verified against satellite imagery"
}
```

**Response**:
```json
{
  "id": "det-abc-123",
  "accuracy_flag": "GREEN",
  "operator_verified": true,
  "operator_notes": "Location verified against satellite imagery",
  "verified_at": "2026-02-17T14:36:00Z"
}
```

### 5.2 Outbound Integration - TAK Server

#### TAK GeoJSON Subscription Endpoint

**Protocol**: HTTP PUT (streaming)
**Endpoint**: `PUT /api/takmaps/version/capabilities/search/geo/takserver/geojson/json`

**Request**:
```json
{
  "type": "Feature",
  "id": "det-abc-123",
  "geometry": {
    "type": "Point",
    "coordinates": [-117.5678, 32.1234]
  },
  "properties": {
    "source": "satellite_fire_api",
    "source_id": "sat_1",
    "detection_type": "fire",
    "confidence": 0.92,
    "accuracy_m": 180,
    "accuracy_flag": "YELLOW",
    "timestamp": "2026-02-17T14:35:42Z"
  }
}
```

**Response (Success)**:
```
HTTP 200 OK
```

**Response (Failure)**:
```
HTTP 500 Internal Server Error

→ Queue locally, mark PENDING_SYNC, retry on next connectivity check
```

**Error Handling**:
- Connection refused: Queue locally, retry with exponential backoff
- HTTP 500: Queue locally, retry after 5-minute backoff
- HTTP 401 (auth): Check credentials, log error, require operator intervention
- Timeout (>5s): Treat as connection failure, queue locally

### 5.3 Configuration Management API

#### Register Detection Source
```
POST /api/v1/sources
Content-Type: application/json

{
  "name": "fire_detection_api",
  "type": "satellite_fire",
  "api_endpoint": "https://api.fire.detection.io/v1/detections",
  "authentication_method": "api_key",
  "polling_interval_seconds": 30,
  "field_mapping": {
    "latitude": "latitude",
    "longitude": "longitude",
    "confidence": "confidence_0_100",
    "type": "fire_type",
    "timestamp": "timestamp"
  }
}
```

**Response (Created)**:
```
HTTP 201 Created

{
  "id": "src-fire-123",
  "name": "fire_detection_api",
  "status": "ACTIVE",
  "first_detection": null,
  "last_detection_at": null
}
```

#### Test Source Connectivity
```
POST /api/v1/sources/{source_id}/test
```

**Response (Success)**:
```json
{
  "status": "REACHABLE",
  "sample_detection": {
    "latitude": 32.1234,
    "longitude": -117.5678,
    "confidence_0_100": 92,
    "fire_type": "wildfire",
    "timestamp": "2026-02-17T14:35:42Z"
  },
  "detected_fields": {
    "latitude": "latitude",
    "longitude": "longitude",
    "confidence": "confidence_0_100 (0-100 scale, will normalize)",
    "type": "fire_type",
    "timestamp": "timestamp"
  },
  "message": "Source is reachable. Configured field mappings detected correctly."
}
```

### 5.4 Health Check Port

#### System Health
```
GET /api/v1/health
```

**Response**:
```json
{
  "status": "UP",
  "timestamp": "2026-02-17T14:35:42Z",
  "components": {
    "api_server": {
      "status": "UP",
      "uptime_seconds": 3600
    },
    "database": {
      "status": "UP",
      "connection_pool": "5/10"
    },
    "tak_server": {
      "status": "UP",
      "last_sync_at": "2026-02-17T14:35:30Z"
    },
    "offline_queue": {
      "status": "UP",
      "pending_items": 0
    },
    "detection_sources": {
      "satellite_fire_api": {
        "status": "UP",
        "last_poll_at": "2026-02-17T14:35:40Z",
        "detections_received": 125
      }
    }
  },
  "metrics": {
    "total_detections_processed": 1250,
    "queue_depth": 0,
    "uptime_days": 7
  }
}
```

### 5.5 Error Handling & Recovery

**Error Codes** (mapped to user-observable failures):

| Code | HTTP Status | Meaning | Recovery |
|------|-----------|---------|----------|
| E001_INVALID_JSON | 400 | JSON parse error | Log, skip detection, continue |
| E002_MISSING_FIELD | 400 | Required field missing | Log, skip detection, continue |
| E003_INVALID_COORDINATES | 422 | Out-of-range lat/lon | Flag RED, queue for manual review |
| E004_API_TIMEOUT | 503 | Detection source unreachable | Retry with backoff, queue locally |
| E005_TAK_SERVER_DOWN | 503 | TAK output failed | Queue locally, retry on reconnect |
| E006_QUEUE_FULL | 507 | Local queue exceeded 10K | Alert operator, stop polling sources |

**Exponential Backoff Strategy**:
- Initial retry: 100ms
- Subsequent: 100ms × 1.5^attempt (capped at 30 seconds)
- Max attempts: 5 before manual intervention

**Operator Alerting**:
- System stays operational during transient failures (no alert)
- Alert only when: queue approaches limit, source permanently unreachable (5+ retries failed)

---

## 6. Quality Attribute Strategies

### 6.1 Performance
- **Ingestion Latency**: <100ms per detection (target)
  - Optimized JSON parsing, minimal validation
  - Async I/O for I/O-bound operations
  - Connection pooling for database/HTTP

- **API → Map Latency**: <2 seconds end-to-end (target)
  - Fast validation (coordinate range checks, simple math)
  - Batch output to TAK (combine multiple detections per request)
  - Monitor: Instrument with timestamps at each step

- **Query Performance**: <1 second for audit trail queries
  - Index detection_id, source, timestamp
  - Pagination for large result sets

### 6.2 Reliability
- **Availability**: >99% (target)
  - Offline-first: system operational even if TAK Server down
  - Graceful degradation: continue accepting detections, queue locally
  - Health checks every 30 seconds to detect failures
  - Auto-restart failed components

- **Data Persistence**: 99.99% of detections reach destination
  - Disk-backed SQLite queue (survives crashes/reboots)
  - Audit trail captures all events
  - Retry logic with exponential backoff

- **Mean Time to Recovery**: <5 minutes automatic
  - Auto-sync when connectivity restored
  - Batch processing for efficiency

### 6.3 Security
- **API Authentication**: API key (configured in environment)
  - No hardcoded secrets
  - Rotate keys regularly
  - Audit trail logs access

- **Data Encryption**: TLS in transit, AES at rest (optional for MVP)
  - TAK Server communication: HTTPS only
  - SQLite database: stored in secure location
  - Audit trail: read-only after creation

- **Access Control**: Role-based (minimal for MVP)
  - Operator (can view, verify detections)
  - Administrator (can configure sources, view logs)
  - Field operators (read-only status)

### 6.4 Maintainability
- **Code Structure**: Hexagonal architecture allows independent service evolution
- **Testability**: Dependency injection, mock external services
- **Documentation**: Architecture ADRs, API documentation (OpenAPI/Swagger), inline code comments for algorithms
- **Monitoring**: Structured JSON logging, easy to parse and alert on

### 6.5 Scalability (Phase 2+)
- **Horizontal Scaling**: Stateless API layer can scale horizontally
- **Database Scaling**: SQLite → PostgreSQL for production (multi-server)
- **Message Queue**: Kafka for high-volume streaming (if needed)
- **Current MVP**: Single Docker container (vertical scaling only)

---

## 7. Deployment Architecture

### 7.1 MVP Deployment (Single Container)

```
┌─────────────────────────────────────────┐
│        Docker Container                  │
├─────────────────────────────────────────┤
│  FastAPI Application (uvicorn)           │
│  ├─ REST API endpoints                   │
│  ├─ Configuration management             │
│  └─ Health checks                        │
├─────────────────────────────────────────┤
│  Core Services (in-process)              │
│  ├─ DetectionIngestionService            │
│  ├─ GeolocationValidationService         │
│  ├─ FormatTranslationService             │
│  ├─ TACOutputService                     │
│  ├─ OfflineQueueService                  │
│  └─ AuditTrailService                    │
├─────────────────────────────────────────┤
│  SQLite Database (embedded)              │
│  ├─ Detections table                     │
│  ├─ Queue table                          │
│  └─ Audit trail table                    │
└─────────────────────────────────────────┘
     ↓                                  ↑
External APIs (satellite, UAV, etc.)   TAK Server
```

**Deployment Model**:
- Single Docker image
- Runs on Linux, macOS, Windows (Docker Desktop)
- Exposed on port 8000 (HTTP)
- Persistent volume for SQLite database
- Environment variables for configuration

**Example Docker Compose**:
```yaml
version: '3.8'
services:
  detection-cop-translator:
    build: .
    ports:
      - "8000:8000"
    environment:
      - FASTAPI_ENV=production
      - DATABASE_URL=sqlite:///./data/app.db
      - TAK_SERVER_URL=https://tak.example.com
      - SATELLITE_API_KEY=${SATELLITE_API_KEY}
      - LOG_LEVEL=INFO
    volumes:
      - ./data:/app/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### 7.2 Production Deployment (Future - Phase 2)

```
┌──────────────────────────────────────────────┐
│          Kubernetes Cluster                   │
├──────────────────────────────────────────────┤
│  API Layer (Stateless - scale horizontally)  │
│  ├─ Deployment: 3 replicas                   │
│  ├─ Service: LoadBalancer                    │
│  └─ Port: 8000                               │
├──────────────────────────────────────────────┤
│  Data Layer (PostgreSQL)                     │
│  ├─ Persistent volume                        │
│  ├─ Replicated for HA                        │
│  └─ Connection pooling                       │
├──────────────────────────────────────────────┤
│  Message Queue (Kafka - optional)            │
│  ├─ For high-volume streaming                │
│  └─ Async processing                         │
├──────────────────────────────────────────────┤
│  Monitoring (Prometheus + Grafana)           │
│  ├─ Metrics collection                       │
│  └─ Alerting                                 │
└──────────────────────────────────────────────┘
```

**Phase 2 Changes**:
- PostgreSQL replaces SQLite for multi-server consistency
- Kafka for decoupling API layer from output services (if needed)
- Horizontal pod autoscaling
- Helm charts for deployment automation

### 7.3 Environment Configuration

**Development Environment**:
```bash
FASTAPI_ENV=development
DATABASE_URL=sqlite:///./dev.db
LOG_LEVEL=DEBUG
TAK_SERVER_URL=http://localhost:8001  # Mock server
SATELLITE_API_KEY=test-key-dev
```

**Staging Environment**:
```bash
FASTAPI_ENV=staging
DATABASE_URL=postgresql://user:pass@postgres-staging:5432/app
LOG_LEVEL=INFO
TAK_SERVER_URL=https://tak-staging.example.com
SATELLITE_API_KEY=${SECRET_STAGING_API_KEY}
```

**Production Environment**:
```bash
FASTAPI_ENV=production
DATABASE_URL=postgresql://user:pass@postgres-prod:5432/app
LOG_LEVEL=WARN
TAK_SERVER_URL=https://tak.example.com
SATELLITE_API_KEY=${SECRET_PROD_API_KEY}
QUEUE_MAX_SIZE=10000
```

---

## 8. Mapping User Stories to Architecture

### Traceability Matrix: User Stories → Components

| User Story | Primary Component | Supporting Components | Quality Target |
|-----------|------------------|----------------------|-----------------|
| US-001: Ingest JSON | DetectionIngestionService | REST API Adapter, AuditTrailService | <100ms, 99.9% success |
| US-002: Validate Geolocation | GeolocationValidationService | AuditTrailService | 95% GREEN accuracy |
| US-003: Transform to GeoJSON | FormatTranslationService | AuditTrailService | RFC 7946 compliant |
| US-004: Output to TAK | TACOutputService | TAK Adapter, OfflineQueueService, AuditTrailService | <2s latency, 99%+ delivery |
| US-005: Offline Queuing | OfflineQueueService | SQLite Adapter, AuditTrailService | 99%+ reliability, auto-sync |
| US-006: Configuration | Configuration Port | REST API Adapter | <10 min setup |
| US-007: Format Detection | DetectionIngestionService | FormatTranslationService | Auto-detect from sample |
| US-008: Health Checks | HealthCheckPort | All components | <1 sec response |
| US-009: Audit Trail | AuditTrailService | All components | 90-day retention |

### Component-to-Story Coverage

**DetectionIngestionService**: US-001, US-007
**GeolocationValidationService**: US-002
**FormatTranslationService**: US-003
**TACOutputService**: US-004
**OfflineQueueService**: US-005
**AuditTrailService**: US-009 (all stories add events)
**REST API Adapter**: US-001, US-006, US-008
**Configuration Port**: US-006
**HealthCheckPort**: US-008

---

## 9. Key Architectural Decisions (ADRs)

See `/workspaces/geolocation-engine2/docs/adrs/` for detailed decision records:

- **ADR-001**: Offline-first architecture (sync later, not remote-first)
- **ADR-002**: Single monolith vs. microservices (monolith for MVP)
- **ADR-003**: Python + FastAPI vs. Go (Python chosen for ecosystem)
- **ADR-004**: GeoJSON RFC 7946 standard (vendor-agnostic compatibility)
- **ADR-005**: SQLite for MVP, PostgreSQL for production
- **ADR-006**: Geolocation flagging (GREEN/YELLOW/RED) vs. fixing coordinates
- **ADR-007**: Hexagonal architecture with independent services

---

## 10. Quality Gates Before Handoff

### Architecture Design Quality Checklist

- [x] All user stories mapped to components
- [x] Component boundaries clear (single responsibility)
- [x] Technology stack justified (open source, documented, team-suitable)
- [x] Integration patterns specified with examples
- [x] Error handling strategies defined
- [x] Quality attributes addressed (performance, reliability, security)
- [x] Deployment architecture clear (MVP single container)
- [x] ADRs written for significant decisions
- [x] Hexagonal architecture compliant (ports/adapters defined)
- [x] Roadmap step count reasonable (steps/components ratio <3)

### Acceptance Criteria for Each User Story

**US-001**:
- REST API accepts valid JSON → parsed successfully
- Malformed JSON → error logged, detection skipped
- Rate limits → respected with backoff
- Ingestion latency → <100ms

**US-002**:
- Valid coordinates + high confidence → GREEN flag
- Valid coordinates + borderline confidence → YELLOW flag
- Invalid coordinates → RED flag, queued for review
- Manual verification → recorded in audit trail

**US-003**:
- Output valid GeoJSON (RFC 7946)
- Coordinates in [lon, lat] format
- All properties included
- Confidence normalized to 0-1

**US-004**:
- GeoJSON output to TAK Server → appears on map <2 sec
- TAK offline → detection queued locally
- TAK recovery → queued detections auto-synced
- High volume (10+/min) → no degradation

**US-005**:
- Network unavailable → detection queued (PENDING_SYNC)
- Network restored → auto-sync without operator action
- Queue persists across reboots
- Sync success rate >99%

---

## 11. Known Risks & Mitigations

### Risk 1: TAK Server Integration Complexity
**Likelihood**: MEDIUM | **Impact**: HIGH
**Mitigation**:
- Proof-of-concept integration in week 1 of BUILD
- Mock TAK Server endpoint for testing
- Clear error handling for connection failures

### Risk 2: Geolocation Accuracy Below Expectations
**Likelihood**: MEDIUM | **Impact**: MEDIUM
**Mitigation**:
- System is flagging service, not fixing service
- Operator spot-check for YELLOW flagged items
- Preserve original accuracy metadata
- Transparent about limitations

### Risk 3: Offline Queue Unbounded Growth
**Likelihood**: LOW | **Impact**: MEDIUM
**Mitigation**:
- Max queue size: 10,000 detections
- Alert when approaching limit
- Batch sync for efficiency (1000+ items/sec)
- Monitor sync success rate

### Risk 4: Performance Under High Detection Volume
**Likelihood**: LOW | **Impact**: MEDIUM
**Mitigation**:
- Load testing in BUILD phase (target: 10+ detections/sec)
- Async I/O throughout
- Connection pooling for database/HTTP
- Scale to Kubernetes if needed (Phase 2)

---

## 12. Success Metrics & Validation

### Implementation Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Integration time | <1 hour per new source | Measure time from configuration to first detection on map |
| Manual validation time | 5 min per mission (80% savings) | Measure operator time for YELLOW flag spot-check |
| System reliability | >99% (detections reaching map) | Track sync success rate, queue depth, error rates |
| Detection latency | <2 seconds API → map | Instrument with timestamps at each stage |
| Configuration time | <10 minutes | Measure from API call to operational polling |
| Audit trail coverage | 100% of detections logged | Verify every detection has linked audit events |

### Customer Validation Milestones

- Week 4: Internal UAT with mock TAK Server
- Week 6: Field testing with Interview 3 contact (Emergency Services)
- Week 8: Performance validation under realistic load
- Week 10-12: Customer feedback integration, MVP polish

---

## 13. Phase 04: Security and Performance Layer (COMPLETE)

Phase 04 added production-grade security and performance capabilities to the core architecture. These components integrate at the adapter layer, preserving the hexagonal architecture principle that domain services receive only validated, authenticated requests.

### Security Components Added

| Component | Architecture Layer | Service |
|-----------|-------------------|---------|
| JWT RS256 Authentication | Primary Port (REST API) | `JWTService` |
| API Key Management | Primary Port (REST API) | `APIKeyService` |
| Token Bucket Rate Limiting | Adapter (Middleware) | `RateLimiterService` |
| Input Sanitization | Adapter (Middleware) | `InputSanitizerService` |
| Security Headers | Adapter (Middleware) | `SecurityService` |
| Security Audit Events | Domain Core | `SecurityService` -> `AuditTrailService` |

### Performance Components Added

| Component | Architecture Layer | Service |
|-----------|-------------------|---------|
| In-Memory Cache (TTL/LFU) | Adapter (Middleware) | `CacheService` |
| Prometheus Metrics | Adapter (/metrics endpoint) | `metrics.py` |
| Load Testing Framework | Testing | Locust (3 user profiles) |

### Request Processing Pipeline (Updated)

```
Request -> Size Check -> Rate Limit -> Authentication (JWT/API Key)
    -> Input Sanitization -> Cache Lookup -> Domain Services -> Response
    + Security Headers + Rate Limit Headers + X-Request-ID
```

**Design Documents:**
- [Security Architecture](../design/phase-04/SECURITY-ARCHITECTURE.md)
- [Performance Architecture](../design/phase-04/PERFORMANCE-ARCHITECTURE.md)
- [ADR-P04-001: JWT vs Session Auth](../design/phase-04/ADRs/ADR-P04-001-jwt-vs-session-authentication.md)
- [ADR-P04-002: Redis vs In-Memory Cache](../design/phase-04/ADRs/ADR-P04-002-redis-vs-in-memory-caching.md)
- [ADR-P04-003: Rate Limiting Algorithm](../design/phase-04/ADRs/ADR-P04-003-rate-limiting-algorithm.md)
- [ADR-P04-004: Secrets Management](../design/phase-04/ADRs/ADR-P04-004-secrets-management-approach.md)

---

## 14. Phase 05: Kubernetes Production Deployment (COMPLETE)

Phase 05 transformed the single-container deployment into a production-grade Kubernetes architecture with high availability, GitOps delivery, and full observability.

### Deployment Architecture

```
Internet -> NGINX Ingress (TLS) -> detection-api-service (ClusterIP)
                                        |
                           selector: slot=green|blue
                                        |
                     +------------------+------------------+
                     |                                     |
           green deployment (3-10)              blue deployment (standby)
           HPA enabled                          idle during green active
```

### Infrastructure Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Orchestration | Kubernetes 1.28+ | Container orchestration |
| GitOps | ArgoCD | Auto-sync, self-heal, drift detection |
| Secrets | Sealed Secrets | Encrypted credentials in Git |
| Metrics | Prometheus | Scrape /metrics endpoint |
| Logging | Loki + Promtail | Structured log aggregation |
| Dashboards | Grafana | 4 operational dashboards |
| Alerts | Grafana Alerting | 19 rules across 7 groups |
| IaC | Terraform | VPC, EKS, RDS, S3, IAM modules |
| App Deploy | Helm 3.x | 10 chart templates |

### Availability and Resilience

- **Target**: 99.9% uptime (8.76 hours/year max downtime)
- **HPA**: 3-10 replicas, scale on CPU (70%) and memory (75%)
- **PDB**: minAvailable 2 (survives voluntary disruptions)
- **Topology Spread**: Across zones and nodes
- **Rollback**: < 120 seconds recovery time
- **Backup**: Daily CronJob at 02:00 UTC, 30-day retention

**Design Documents:**
- [Kubernetes Architecture](phase05-kubernetes-production.md)
- [Deployment Strategy](phase05-deployment-strategy.md)
- [HA and Resilience](phase05-ha-resilience.md)
- [Security Layers](phase05-security.md)
- [ADR-007: GitOps ArgoCD](../adrs/ADR-007-gitops-argocd.md)
- [ADR-008: Sealed Secrets](../adrs/ADR-008-secret-management-sealed-secrets.md)
- [ADR-009: Observability Stack](../adrs/ADR-009-observability-prometheus-loki-grafana.md)

---

## 15. Future Evolution (Phase 06+)

### Planned Enhancements
1. **KEDA Event-Driven Autoscaling**: Scale on queue depth, not just CPU
2. **OpenTelemetry Distributed Tracing**: When service decomposition begins
3. **External Secrets Operator**: Vault integration for secret rotation
4. **Multiple COP Systems**: Extend to ArcGIS, CAD platforms beyond TAK
5. **Multi-Source Detection Fusion**: Correlate detections from multiple sources
6. **Machine Learning**: Confidence calibration from ground truth
7. **Service Mesh**: Istio/Linkerd for mTLS and traffic management

### Scalability Path
- Phase 01-03 (DONE): Single container, SQLite, 100+ detections/sec
- Phase 04-05 (DONE): Kubernetes, production security, 100+ req/s sustained
- Phase 06+: PostgreSQL migration, Kafka message queue, 10K+ detections/sec

---

## Summary

This architecture delivers a production-ready detection-to-COP translation system:

1. **Satisfying all user stories** through clear component-to-story mapping
2. **Enabling fast integration** (<1 hour per source) via REST API + configuration
3. **Providing operational trust** through geolocation validation flagging (killer feature)
4. **Ensuring reliability** with offline-first architecture (99%+ delivery)
5. **Supporting tactical decisions** with <2 second latency to map
6. **Maintaining compliance** through immutable audit trail
7. **Staying cost-effective** with 100% open source stack ($0)
8. **Enabling evolution** with hexagonal architecture and clear service boundaries
9. **Production security** with JWT, rate limiting, input sanitization, and caching
10. **Production deployment** with Kubernetes, GitOps, observability, and disaster recovery

**Total Tests**: 331+ passing (93.5% coverage)
**Status**: Production Ready (Phase 04-05 Complete)

---

**Architecture Document Status**: COMPLETE - All Phases Delivered
**Last Updated**: 2026-02-15
