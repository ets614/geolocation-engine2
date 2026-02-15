# Implementation Roadmap - BUILD Wave

**Project**: AI Detection to COP Translation System (Walking Skeleton MVP)
**Timeline**: 8-12 weeks
**Team**: 2-3 engineers
**Status**: Ready for BUILD Wave kickoff

---

## Overview

This roadmap maps user stories to implementation steps, maintaining the hexagonal architecture and ensuring parallel work is possible. The roadmap prioritizes:

1. **Core validation flow first** (ingestion → validation → transformation)
2. **TAK output early** (enable end-to-end testing)
3. **Offline resilience** (critical for reliability)
4. **Configuration & monitoring** (operational requirements)

---

## Phase 1: Foundation (Weeks 1-2) — 6 days

### Step 1.1: Project Setup & Infrastructure
**Duration**: 2 days

**What**: Bootstrap the project with development environment, CI/CD pipeline, and core dependencies

**Acceptance Criteria**:
- GitHub repository initialized with standard Python structure
- Docker development environment working locally (`docker-compose up`)
- Requirements.txt with core dependencies pinned
- CI/CD pipeline runs basic tests on each commit
- Team can run tests and start development

**Deliverables**:
- `pyproject.toml` with project metadata
- `requirements.txt` with pinned versions
- `Dockerfile` and `docker-compose.yml` for local dev
- GitHub Actions workflow for CI/CD
- `.env.example` for configuration template

**Technical Details**:
```
Project structure:
src/
  ├── main.py                 (FastAPI app entry point)
  ├── services/
  │   ├── ingestion.py        (DetectionIngestionService)
  │   ├── validation.py       (GeolocationValidationService)
  │   ├── translation.py      (FormatTranslationService)
  │   ├── output.py           (TACOutputService)
  │   ├── queue.py            (OfflineQueueService)
  │   └── audit.py            (AuditTrailService)
  ├── adapters/
  │   ├── rest_api.py         (FastAPI REST adapter)
  │   ├── database.py         (SQLite adapter)
  │   ├── tak_client.py       (TAK HTTP adapter)
  │   └── logging.py          (Logging adapter)
  └── models/
      ├── detection.py        (Detection Pydantic model)
      └── geojson.py          (GeoJSON models)
tests/
  ├── unit/
  ├── integration/
  └── e2e/
```

---

### Step 1.2: Core Data Models & Validation
**Duration**: 2 days

**What**: Define Detection, GeoJSON, and related Pydantic models. Establish data validation rules.

**Acceptance Criteria**:
- Detection model validates latitude/longitude ranges
- Detection model normalizes confidence to 0-1 scale
- GeoJSON model RFC 7946 compliant (validated with standard validators)
- All models have unit tests (100% coverage)
- OpenAPI schema auto-generates correctly

**Deliverables**:
- `src/models/detection.py` with Detection class
- `src/models/geojson.py` with GeoJSON classes
- Unit tests for all validation rules
- OpenAPI schema documentation (auto-generated)

**Models Defined**:
```python
class Detection:
    detection_id: UUID
    source_type: str
    latitude: float  # Validated -90..90
    longitude: float  # Validated -180..180
    confidence: float  # Normalized 0-1
    confidence_original: Dict  # Preserved original
    accuracy_meters: float
    timestamp: ISO8601
    sync_status: Enum
    accuracy_flag: Enum  # GREEN, YELLOW, RED
    original_format_data: JSON  # For audit

class GeoJSONFeature:
    type: Literal["Feature"]
    geometry: Point
    properties: Dict  # Custom properties allowed
    id: str
```

---

### Step 1.3: REST API Skeleton
**Duration**: 2 days

**What**: Build FastAPI REST adapter with core endpoints (ingest, health, status).

**Acceptance Criteria**:
- `POST /api/v1/detections` endpoint accepts JSON
- `GET /api/v1/health` endpoint returns system status
- `GET /api/v1/detections/{id}` retrieves detection status
- Request validation works (rejects malformed JSON with 400)
- OpenAPI docs available at `/docs`

**Deliverables**:
- `src/adapters/rest_api.py` with FastAPI routes
- Request/response models
- Error handling (400, 422, 500 responses)
- Swagger documentation

**Example Endpoints**:
```python
@app.post("/api/v1/detections")
async def ingest_detection(detection: DetectionInput):
    """Ingest detection JSON"""
    return {"id": "...", "status": "RECEIVED"}

@app.get("/api/v1/health")
async def health_check():
    """System health check"""
    return {
        "status": "UP",
        "components": {...}
    }

@app.get("/api/v1/detections/{detection_id}")
async def get_detection(detection_id: str):
    """Get detection status"""
    return {"id": "...", "status": "SYNCED", ...}
```

---

## Phase 2: Core Validation Loop (Weeks 2-4) — 10 days

### Step 2.1: Detection Ingestion Service
**Duration**: 2 days (Builds on US-001)

**What**: Implement DetectionIngestionService to parse JSON, validate structure, handle errors.

**Acceptance Criteria**:
- Parse valid JSON detections successfully
- Extract required fields (lat, lon, confidence, type, timestamp)
- Handle malformed JSON gracefully (log E001, skip, continue)
- Handle API rate limits (HTTP 429, exponential backoff)
- Ingest latency <100ms per detection
- 99.9% success rate for valid JSON

**Deliverables**:
- `src/services/ingestion.py` with DetectionIngestionService
- Unit tests for JSON parsing, error handling
- Integration tests with mock APIs

**Key Methods**:
```python
class DetectionIngestionService:
    async def ingest(self, raw_json: Dict) -> Detection:
        """Parse and normalize detection"""

    async def handle_rate_limit(self, retry_after: int) -> None:
        """Implement exponential backoff"""
```

---

### Step 2.2: Geolocation Validation Service
**Duration**: 3 days (Builds on US-002 — killer feature)

**What**: Implement GeolocationValidationService with accuracy flagging (GREEN/YELLOW/RED).

**Acceptance Criteria**:
- Validate coordinate ranges (-90..90, -180..180)
- Check GPS accuracy metadata (<500m for GREEN)
- Evaluate confidence (>0.6 for GREEN)
- Apply terrain-specific accuracy expectations
- GREEN flag accuracy >95% (validated against ground truth)
- Manual spot-check workflow for YELLOW flagged items
- Audit trail captures all validation events

**Deliverables**:
- `src/services/validation.py` with GeolocationValidationService
- Accuracy thresholds configuration
- Terrain-specific accuracy expectations (sea level, mountains, urban)
- Unit tests for accuracy flagging logic
- Integration tests with sample detections (all 3 flags)

**Key Methods**:
```python
class GeolocationValidationService:
    def validate(self, detection: Detection) -> Detection:
        """Validate coordinates, set accuracy_flag"""

    def assess_accuracy(self, accuracy_m, confidence, terrain) -> AccuracyFlag:
        """Determine GREEN/YELLOW/RED flag"""
```

**Accuracy Thresholds**:
- GREEN: accuracy < 500m AND confidence > 0.6
- YELLOW: accuracy 500-1000m OR confidence 0.4-0.6
- RED: accuracy > 1000m OR confidence < 0.4

---

### Step 2.3: Format Translation Service (GeoJSON)
**Duration**: 2 days (Builds on US-003)

**What**: Implement FormatTranslationService to transform detections to RFC 7946 GeoJSON.

**Acceptance Criteria**:
- Generate valid GeoJSON Features (RFC 7946)
- Coordinates in [longitude, latitude] format (correct order)
- All properties included (source, confidence, accuracy_flag, etc.)
- Confidence normalized to 0-1 scale
- Original confidence preserved in metadata
- 100% RFC 7946 compliant (validate with standard tools)
- Transform latency <5ms per detection

**Deliverables**:
- `src/services/translation.py` with FormatTranslationService
- GeoJSON validation
- Unit tests for multiple source formats (UAV, satellite, camera)
- RFC 7946 compliance validation

**Key Methods**:
```python
class FormatTranslationService:
    def transform(self, detection: Detection) -> GeoJSONFeature:
        """Transform to GeoJSON Feature"""
```

---

### Step 2.4: Audit Trail Service
**Duration**: 2 days (Supports US-009)

**What**: Implement AuditTrailService for compliance and debugging.

**Acceptance Criteria**:
- Log all detection events (received, validated, transformed, output)
- Timestamp every event (UTC)
- Structured JSON logging
- Searchable by detection_id
- 90-day retention minimum
- Enable after-action review

**Deliverables**:
- `src/services/audit.py` with AuditTrailService
- Audit trail schema
- Unit tests for event logging
- Query API (get audit trail for detection_id)

**Events Captured**:
- detection_received: source, timestamp, raw_data
- detected_validated: accuracy_flag, confidence
- detection_transformed: transformation_type
- detection_output: destination, status
- error_occurred: error_code, recovery_action

---

## Phase 3: Output & Offline Resilience (Weeks 4-6) — 10 days

### Step 3.1: TAK Output Service
**Duration**: 2 days (Builds on US-004)

**What**: Implement TACOutputService to push GeoJSON to TAK Server.

**Acceptance Criteria**:
- Push validated GeoJSON to TAK subscription endpoint
- Detection appears on map within 2 seconds
- Handle connection failures gracefully
- Fallback to offline queue on network error
- 99%+ of valid detections reach TAK
- Support multiple detections/second (high volume)

**Deliverables**:
- `src/services/output.py` with TACOutputService
- TAK HTTP client adapter
- Unit tests with mock TAK Server
- Integration tests with simulated network failures

**Key Methods**:
```python
class TACOutputService:
    async def output(self, geojson: GeoJSONFeature) -> None:
        """Send GeoJSON to TAK Server, queue if failed"""
```

**Error Handling**:
- Connection refused → Queue locally
- HTTP 500 → Retry with exponential backoff
- HTTP 401 → Log auth error, require manual intervention
- Timeout → Treat as connection failure, queue locally

---

### Step 3.2: Offline Queue Service
**Duration**: 3 days (Builds on US-005 — core reliability)

**What**: Implement OfflineQueueService for offline-first resilience.

**Acceptance Criteria**:
- Write detections to local SQLite queue (PENDING_SYNC) when network unavailable
- Queue persists across system restarts
- Auto-sync when network restored (no operator action)
- Batch sync for efficiency (1000+ items/sec)
- Operator sees no errors during normal offline/sync cycle
- Status dashboard shows queue depth
- 99.99% of queued detections sync successfully

**Deliverables**:
- `src/services/queue.py` with OfflineQueueService
- SQLite adapter with queue schema
- Connectivity monitoring (detect network restore)
- Batch sync algorithm
- Unit tests (queue write, sync, persistence)
- Integration tests (network failure simulation, recovery)

**Key Methods**:
```python
class OfflineQueueService:
    def enqueue(self, detection: Detection) -> None:
        """Write to SQLite queue"""

    async def sync(self) -> int:
        """Sync all PENDING_SYNC items to remote"""

    async def monitor_connectivity(self) -> None:
        """Check network, auto-sync on restore"""
```

---

### Step 3.3: Database Adapter & Schema
**Duration**: 2 days

**What**: Implement SQLite adapter and initialize database schema.

**Acceptance Criteria**:
- SQLite database initializes on startup
- Schema includes: detections, queue, audit_trail tables
- Database schema versioned (Alembic migrations)
- Connection pooling for performance
- ACID compliance (transactions work correctly)
- Sub-second latency for read/write operations

**Deliverables**:
- `src/adapters/database.py` with SQLiteAdapter
- Database schema (SQL)
- Alembic migrations
- Unit tests for database operations
- Backup/recovery strategy documented

**Schema Tables**:
```sql
CREATE TABLE detections (
  id TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  status TEXT DEFAULT 'RECEIVED',
  accuracy_flag TEXT,
  geojson TEXT,
  created_at TEXT NOT NULL,
  synced_at TEXT
);

CREATE TABLE offline_queue (
  id TEXT PRIMARY KEY,
  detection_json TEXT NOT NULL,
  status TEXT DEFAULT 'PENDING_SYNC',
  created_at TEXT NOT NULL,
  synced_at TEXT,
  retry_count INTEGER DEFAULT 0
);

CREATE TABLE audit_trail (
  id TEXT PRIMARY KEY,
  detection_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  timestamp TEXT NOT NULL,
  details TEXT
);
```

---

## Phase 4: Configuration & Operations (Weeks 6-8) — 8 days

### Step 4.1: Configuration Management
**Duration**: 2 days (Builds on US-006)

**What**: Implement configuration API and source registration.

**Acceptance Criteria**:
- API to register detection sources (<10 minutes)
- Store source configuration (endpoint, auth, field mapping)
- Test source connectivity
- List configured sources
- Support field mapping (auto-detect if possible)
- Configuration persists across restarts

**Deliverables**:
- Configuration endpoints (REST API)
- Source configuration schema
- Field mapping validation
- Unit tests for configuration CRUD
- Integration tests with real detection APIs

**Endpoints**:
```
POST /api/v1/sources — Register new source
GET /api/v1/sources — List sources
PUT /api/v1/sources/{id} — Update source
DELETE /api/v1/sources/{id} — Remove source
POST /api/v1/sources/{id}/test — Test connectivity
```

---

### Step 4.2: Health Checks & Monitoring
**Duration**: 2 days (Builds on US-008)

**What**: Implement health check endpoints and component status monitoring.

**Acceptance Criteria**:
- `/api/v1/health` returns overall system status (UP/DOWN/DEGRADED)
- Per-component status visible (API, database, TAK, queue)
- Queue depth displayed
- Last sync timestamp shown
- Health check completes in <1 second
- External monitoring can use health endpoint

**Deliverables**:
- Health check endpoint implementation
- Component health queries
- Status dashboard data structure
- Unit tests for health checks
- Integration tests (simulate component failures)

**Health Response**:
```json
{
  "status": "UP",
  "components": {
    "api": "UP",
    "database": "UP",
    "tak_server": "UP",
    "queue": "UP"
  },
  "metrics": {
    "total_detections": 1250,
    "queue_depth": 0,
    "last_sync": "2026-02-17T14:35:40Z"
  }
}
```

---

### Step 4.3: Error Handling & Recovery
**Duration**: 2 days

**What**: Implement comprehensive error handling and recovery strategies.

**Acceptance Criteria**:
- All error codes (E001-E006) handled properly
- Graceful degradation (system continues operating)
- Exponential backoff for retries (100ms → 30s max)
- Error logging with recovery action
- Operator can see errors without manual intervention
- System recovers automatically

**Deliverables**:
- Error handling middleware
- Retry logic with exponential backoff
- Error code mapping
- Recovery strategies documented
- Unit tests for error paths

**Error Codes**:
- E001: INVALID_JSON → Log, skip, continue
- E002: MISSING_FIELD → Log, skip, continue
- E003: INVALID_COORDINATES → Flag RED, queue for review
- E004: API_TIMEOUT → Retry with backoff
- E005: TAK_SERVER_DOWN → Queue locally, sync later
- E006: QUEUE_FULL → Alert operator, pause polling

---

### Step 4.4: Integration Testing Framework
**Duration**: 2 days

**What**: Build integration test suite with mock external systems.

**Acceptance Criteria**:
- Mock TAK Server for testing output failures
- Simulated network outages (timeout injection)
- Sample detections in all formats (satellite, drone, camera)
- Tests cover happy path + error scenarios
- Test suite runs in CI/CD pipeline
- 100% test pass rate required for merge

**Deliverables**:
- Mock TAK Server implementation (mockserver)
- Integration test cases
- Network simulation utilities
- Sample test data
- Test documentation

---

## Phase 5: End-to-End Testing & Validation (Weeks 8-10) — 8 days

### Step 5.1: Unit Test Coverage
**Duration**: 2 days

**What**: Achieve 80%+ unit test coverage for all services.

**Acceptance Criteria**:
- All services >80% code coverage
- All validation logic tested
- Error conditions tested
- Edge cases covered (boundary values, empty inputs)
- Tests run in CI/CD

**Deliverables**:
- Unit tests for all services
- Coverage report (pytest-cov)
- Coverage badge in README
- Test documentation

---

### Step 5.2: End-to-End Testing
**Duration**: 3 days

**What**: Test complete detection workflow from ingestion to TAK output.

**Acceptance Criteria**:
- Detection ingested successfully
- Validation applied correctly
- GeoJSON transformation valid
- TAK output successful (or queued if offline)
- Queue syncs on network restore
- Audit trail complete
- Performance meets targets (<2s end-to-end)

**Deliverables**:
- End-to-end test scenarios (pytest)
- Performance measurement tests
- Network failure scenarios tested
- Results documented

---

### Step 5.3: Performance Testing
**Duration**: 2 days

**What**: Load test system to validate performance targets.

**Acceptance Criteria**:
- Ingestion latency <100ms per detection (99th percentile)
- End-to-end latency <2 seconds (detection → TAK map)
- Throughput >100 detections/second (single container)
- Memory usage <500MB
- CPU usage <70% single core

**Deliverables**:
- Load test script (locust or similar)
- Performance baseline results
- Bottleneck analysis
- Performance optimization recommendations

---

### Step 5.4: Security & Compliance Review
**Duration**: 1 day

**What**: Review security, compliance, and operational readiness.

**Acceptance Criteria**:
- API authentication working
- Database backup strategy documented
- Audit trail retention verified (90 days)
- Error handling doesn't leak sensitive data
- All external dependencies reviewed (known vulnerabilities check)

**Deliverables**:
- Security audit checklist
- Vulnerability scan results
- Backup/recovery procedure documented
- Security recommendations

---

## Phase 6: Documentation & Handoff (Weeks 10-12) — 6 days

### Step 6.1: API Documentation
**Duration**: 1 day

**What**: Auto-generate and verify API documentation.

**Acceptance Criteria**:
- OpenAPI/Swagger docs complete (`/docs` endpoint)
- All endpoints documented
- Request/response examples provided
- Error responses documented
- Accessible without authentication

**Deliverables**:
- OpenAPI schema (auto-generated)
- API documentation PDF
- Quick start guide
- Example curl requests

---

### Step 6.2: Operational Runbook
**Duration**: 2 days

**What**: Document operations procedures.

**Acceptance Criteria**:
- Deployment procedure documented
- Health check procedure
- Troubleshooting guide for common errors
- Backup/recovery procedures
- Monitoring setup documented
- On-call playbook

**Deliverables**:
- Deployment guide (how to bring up system)
- Operational manual
- Troubleshooting guide
- Monitoring setup guide

---

### Step 6.3: First Customer Reference Integration
**Duration**: 2 days

**What**: Prepare integration with first customer (Emergency Services).

**Acceptance Criteria**:
- System deployed to staging environment
- Emergency Services team can configure fire detection API
- Detections flow end-to-end
- System operating stably (99%+ uptime)
- Customer feedback incorporated

**Deliverables**:
- Staging environment deployment
- Integration checklist
- Customer setup guide
- Support procedures documented

---

### Step 6.4: MVP Release Preparation
**Duration**: 1 day

**What**: Final checklist before MVP release.

**Acceptance Criteria**:
- All user stories closed (US-001 through US-005)
- All acceptance criteria met
- No critical bugs open
- Performance targets verified
- Deployment runbook complete
- Team trained on operations

**Deliverables**:
- Release notes
- Deployment checklist
- Training materials
- Known limitations documented

---

## Parallel Work Streams

### Week-by-Week Allocation

**Weeks 1-2** (Foundation):
- Engineer 1: Project setup, REST API skeleton
- Engineer 2: Data models, validation rules
- Engineer 3 (if available): Database schema, tests

**Weeks 2-4** (Core Loop):
- Engineer 1: Detection ingestion + geolocation validation
- Engineer 2: Format translation + GeoJSON
- Engineer 3: Audit trail + tests

**Weeks 4-6** (Output & Resilience):
- Engineer 1: TAK output service + error handling
- Engineer 2: Offline queue service + database
- Engineer 3: Integration tests + performance tests

**Weeks 6-8** (Configuration):
- Engineer 1: Configuration management
- Engineer 2: Health checks + monitoring
- Engineer 3: End-to-end tests

**Weeks 8-10** (Testing & Validation):
- All engineers: Unit tests, performance tests, security review

**Weeks 10-12** (Documentation & Release):
- Engineer 1: Operational documentation
- Engineer 2: Customer integration
- Engineer 3: Release preparation

---

## Success Criteria

### MVP Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Integration time | <1 hour per new source | Time from config to first detection on map |
| Ingestion latency | <100ms | Measure at each processing step |
| End-to-end latency | <2 seconds | Detection received → appears on map |
| Manual validation time | 5 min/mission | 80% savings (30 min → 5 min) |
| System reliability | >99% | Detections reaching TAK/queued offline |
| Configuration time | <10 minutes | Time to register detection source |
| GREEN flag accuracy | >95% | Validated against ground truth |
| Test coverage | >80% | Unit test coverage |

---

## Risk Mitigation

### Technical Risks

**Risk 1: TAK Server Integration Complex**
- Mitigation: Week 1-2 proof-of-concept integration
- Fallback: Mock TAK Server for testing

**Risk 2: Geolocation Accuracy Below Expectations**
- Mitigation: Extensive unit tests on accuracy logic
- Fallback: Position as "flagging service", not "correction service"

**Risk 3: Performance Under Load**
- Mitigation: Load testing in week 5-6
- Fallback: Kubernetes scaling if needed (Phase 2)

---

## Timeline Summary

| Phase | Weeks | Focus |
|-------|-------|-------|
| Phase 1 | 1-2 | Foundation (project setup, models, REST API) |
| Phase 2 | 2-4 | Core loop (ingestion, validation, translation, audit) |
| Phase 3 | 4-6 | Output & resilience (TAK output, offline queue) |
| Phase 4 | 6-8 | Configuration & operations (sources, health, errors) |
| Phase 5 | 8-10 | Testing & validation (unit, E2E, performance, security) |
| Phase 6 | 10-12 | Documentation & release (runbook, customer integration) |

**Total Timeline**: 8-12 weeks
**Team**: 2-3 engineers
**Ready for Implementation**: YES ✓

---

## Next Steps

1. **Week 1 Kickoff**:
   - Assign engineers to parallel work streams
   - Setup development environment
   - Hold architecture review session

2. **Daily Standups**: 15 minutes, same time daily
   - What did you complete?
   - What's blocking you?
   - Do we need to adjust plan?

3. **Sprint Reviews**: Weekly, end of Friday
   - Demo working software
   - Verify acceptance criteria met
   - Discuss next sprint priorities

4. **Sprint Retrospectives**: Weekly, after demo
   - What went well?
   - What could improve?
   - Adjust process for next sprint

---

**Roadmap Status**: APPROVED FOR BUILD WAVE EXECUTION ✓
