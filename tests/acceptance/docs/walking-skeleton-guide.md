# Walking Skeleton Implementation Guide
## AI Detection to COP Translation System

**Status**: READY FOR EXECUTION
**Audience**: Software Crafter / BUILD Wave Engineers
**Timeline**: Day 1-3 of implementation

---

## What is the Walking Skeleton?

The walking skeleton is a **minimal end-to-end demo** that proves the entire architecture works. It answers: *"Can a user accomplish their goal?"* not *"Do the layers connect?"*

**User Goal**: System integrator ingests detection data and sees it on the COP map

**Observable Value**: <2 second latency from API → map display

**Success Criteria**:
- Detection posted to `/api/v1/detections`
- Geolocation validated automatically
- Transformed to RFC 7946 GeoJSON
- Appears on TAK map within 2 seconds
- Audit trail records all steps

---

## Prerequisites

### Development Environment

```bash
# Clone repository
git clone https://github.com/your-org/geolocation-engine2.git
cd geolocation-engine2

# Install dependencies
python -m venv venv
source venv/bin/activate  # or: venv\Scripts\activate (Windows)
pip install -r requirements.txt

# Install test dependencies
pip install pytest pytest-bdd requests testcontainers[docker]

# Verify Docker is running (for test containers)
docker --version
docker run hello-world
```

### Required Services

The walking skeleton requires three services:
1. **Detection Ingestion API** (FastAPI) - port 8000
2. **TAK Server Simulator** (mock HTTP server) - port 9000
3. **SQLite Database** (embedded)

### Directory Structure

```
tests/acceptance/
├── features/
│   ├── walking-skeleton.feature (start here)
│   ├── detection-ingestion.feature
│   ├── geolocation-validation.feature
│   ├── format-translation.feature
│   ├── tak-output.feature
│   ├── offline-queue-sync.feature
│   └── deployment-smoke-tests.feature
├── steps/
│   ├── conftest.py (fixtures, test infrastructure)
│   ├── detection_steps.py (step definitions)
│   └── (other step files)
└── docs/
    ├── test-scenarios.md (this document)
    └── walking-skeleton-guide.md
```

---

## Step 1: Start the Services

### Option A: Docker Compose (Recommended)

```bash
# Build and start all services
docker-compose up -d

# Verify services are running
docker-compose ps

# View logs
docker-compose logs -f app
docker-compose logs -f tak-sim
```

### Option B: Manual Startup

**Terminal 1 - Detection API**:
```bash
cd src
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
# Output: "Application startup complete"
```

**Terminal 2 - TAK Simulator**:
```bash
cd tests/mocks
python tak_simulator.py
# Output: "TAK Simulator listening on port 9000"
```

**Terminal 3 - Test Runner**:
```bash
# Keep this for running tests
cd /repo/root
```

### Verify Services Are Running

```bash
# API health check
curl http://localhost:8000/api/v1/health
# Response: {"status": "UP", "components": {...}}

# TAK simulator health check
curl http://localhost:9000/health
# Response: {"status": "OK"}
```

---

## Step 2: Run the Walking Skeleton Test

### Execute the Test

```bash
# Run only the walking skeleton scenario
pytest tests/acceptance/features/walking-skeleton.feature -v

# Or run the milestone_1 scenario specifically
pytest tests/acceptance/features/walking-skeleton.feature::Scenario -v -m milestone_1
```

### Expected Output

```
tests/acceptance/features/walking-skeleton.feature::Scenario: Ingest JSON detection and output to TAK GeoJSON PASSED

===== 1 passed in 2.34s =====
```

### If the Test Fails

**Problem**: Health check fails
```
AssertionError: API service did not become ready at localhost:8000
```
**Solution**: Verify API is running and healthy
```bash
curl http://localhost:8000/api/v1/health
# If fails, check API logs for errors
docker-compose logs app
```

**Problem**: TAK output assertion fails
```
AssertionError: TAK server did not receive detection within 2 seconds
```
**Solution**: Verify TAK simulator is running
```bash
curl http://localhost:9000/health
# Check TAK simulator logs
docker-compose logs tak-sim
```

**Problem**: Latency exceeds 2 second SLA
```
AssertionError: Latency 2.5s exceeds target <2s
```
**Solution**: Check system load and optimize
```bash
# Monitor system resources
docker stats

# Profile API endpoints
ab -n 100 -c 10 http://localhost:8000/api/v1/health
```

---

## Step 3: Trace the Data Flow

The walking skeleton validates this flow:

```
┌─────────────────────────────────────────────────────────┐
│ STEP 1: INGEST                                          │
│ Timestamp: 14:35:42                                     │
│ Action: POST /api/v1/detections with JSON              │
│ Example payload:                                        │
│ {                                                       │
│   "latitude": 40.7128,                                 │
│   "longitude": -74.0060,                               │
│   "confidence": 92,                                    │
│   "type": "fire"                                       │
│ }                                                       │
└──────────────────────┬──────────────────────────────────┘
                       ↓ Latency: <100ms
┌─────────────────────────────────────────────────────────┐
│ STEP 2: VALIDATE                                        │
│ Timestamp: 14:35:42                                     │
│ Action: GeolocationValidationService checks:           │
│ - Latitude in [-90, 90]? ✓                             │
│ - Longitude in [-180, 180]? ✓                          │
│ - Accuracy <500m? ✓                                    │
│ - Confidence >0.6? ✓                                   │
│ Result: accuracy_flag = GREEN                          │
│ Response: 202 Accepted                                 │
│ Returns: detection_id (UUID)                           │
└──────────────────────┬──────────────────────────────────┘
                       ↓ Latency: <100ms
┌─────────────────────────────────────────────────────────┐
│ STEP 3: TRANSFORM                                       │
│ Timestamp: 14:35:43                                     │
│ Action: FormatTranslationService builds GeoJSON        │
│ Input: Validated Detection                             │
│ Output: RFC 7946 GeoJSON Feature                        │
│ {                                                       │
│   "type": "Feature",                                   │
│   "geometry": {                                         │
│     "type": "Point",                                   │
│     "coordinates": [-74.0060, 40.7128]                │
│   },                                                    │
│   "properties": {                                       │
│     "source": "satellite_fire_api",                    │
│     "confidence": 0.92,                                │
│     "accuracy_flag": "GREEN",                          │
│     "timestamp": "2026-02-17T14:35:42Z"               │
│   }                                                     │
│ }                                                       │
└──────────────────────┬──────────────────────────────────┘
                       ↓ Latency: <100ms
┌─────────────────────────────────────────────────────────┐
│ STEP 4: OUTPUT                                          │
│ Timestamp: 14:35:44                                     │
│ Action: TACOutputService sends to TAK                  │
│ Method: HTTP PUT to TAK subscription endpoint           │
│ Response: 200 OK from TAK                               │
│ Detection written to local database (SYNCED)            │
└──────────────────────┬──────────────────────────────────┘
                       ↓ Latency: <1000ms
┌─────────────────────────────────────────────────────────┐
│ STEP 5: DISPLAY                                         │
│ Timestamp: 14:35:45                                     │
│ Action: TAK Client receives update                      │
│ Result: Fire marker appears on map at [40.7128,-74.0060]
│ Accuracy badge: GREEN checkmark                         │
│ Operator can see: coordinates, source, confidence       │
│ Total latency: 3 seconds (target: <2s achieved)        │
└─────────────────────────────────────────────────────────┘

AUDIT TRAIL RECORDED:
─────────────────────
Event 1: detection_received (14:35:42)
Event 2: validation_started (14:35:42)
Event 3: validation_complete → GREEN (14:35:42)
Event 4: transform_started (14:35:43)
Event 5: transform_complete → GeoJSON (14:35:43)
Event 6: output_started (14:35:44)
Event 7: output_complete → SYNCED (14:35:44)
```

### Verify Each Step

```bash
# 1. Check detection was ingested
curl http://localhost:8000/api/v1/detections/det-12345 \
  -H "Accept: application/json"

# 2. Check validation result
# Look for "accuracy_flag": "GREEN" in response

# 3. Check GeoJSON transformation
# Response should have:
# - "type": "Feature"
# - "geometry": {"type": "Point", "coordinates": [-74.0060, 40.7128]}
# - "properties": {"accuracy_flag": "GREEN", ...}

# 4. Check TAK received detection
curl http://localhost:9000/received_detections \
  -H "Accept: application/json"
# Should show detection with source, coordinates, timestamp

# 5. Check audit trail
curl "http://localhost:8000/api/v1/audit/det-12345" \
  -H "Accept: application/json"
# Should show all 7 events in chronological order
```

---

## Step 4: Understand What's Being Tested

The walking skeleton validates these architectural layers:

### 1. Primary Port (Input)
- **REST API Adapter** accepts JSON on POST /api/v1/detections
- **Contract**: HTTP 202 Accepted with detection_id returned

### 2. Domain Services (Business Logic)
- **DetectionIngestionService**: Parse JSON, validate format, log event
- **GeolocationValidationService**: Validate coordinates, apply thresholds, flag accuracy
- **FormatTranslationService**: Build GeoJSON, normalize confidence

### 3. Secondary Port (Output)
- **TAK Output Service**: HTTP PUT to TAK subscription endpoint
- **Contract**: Detections appear on map within 2 seconds

### 4. Resilience
- **Offline Queue Service**: Queue to SQLite if TAK unavailable
- **Audit Trail Service**: Record all events for compliance

### 5. Infrastructure
- **REST API**: FastAPI server handling concurrent requests
- **Database**: SQLite for persistence
- **Logging**: Structured JSON audit trail

---

## Step 5: Next Steps After Walking Skeleton Passes

### Phase 1: Additional Happy Path Scenarios
```bash
# Scenario 2: Multiple detections from different sources
pytest tests/acceptance/features/walking-skeleton.feature::Scenario -v -k "multiple"

# This validates:
# - Handle 3 concurrent detections
# - Different source types (satellite, UAV, camera)
# - Confidence scales normalized
# - All appear on map simultaneously
```

### Phase 2: Error Handling
```bash
# Test network outage resilience
pytest tests/acceptance/features/walking-skeleton.feature::Scenario -v -k "outage"

# This validates:
# - TAK unavailable → queue locally
# - Auto-sync when connection restored
# - All detections appear on map (no data loss)
# - Operator doesn't need to manually intervene
```

### Phase 3: Implementation by User Story
```bash
# After walking skeleton passes, enable:
@skip → remove from US-001 scenarios
@skip → remove from US-002 scenarios (one at a time)
@skip → remove from US-003 scenarios
# etc.

# One scenario at a time: enable, implement, test, commit
```

---

## Step 6: Performance Validation

The walking skeleton includes performance assertions:

```gherkin
Scenario: Ingest JSON detection and output to TAK GeoJSON
  When I POST a JSON detection ...
  Then ingestion latency is less than 100 milliseconds
  And geolocation validation latency < 100ms
  And GeoJSON transformation latency < 100ms
  And TAK output latency < 1000ms
  And total end-to-end latency < 2 seconds
```

### Measure Performance

```bash
# Run with timing output
pytest tests/acceptance/features/walking-skeleton.feature -v -s

# Use pytest-benchmark for detailed analysis
pip install pytest-benchmark
pytest --benchmark-only tests/acceptance/

# Profile with cProfile
python -m cProfile -s cumulative src/main.py
```

### If Performance SLA Fails

**Problem**: Ingestion >100ms
```
AssertionError: Ingestion latency 150ms exceeds SLA of 100ms
```
**Solutions**:
- Check FastAPI startup time (should be <1s)
- Verify no blocking I/O in ingestion path
- Check database connection pooling
- Profile with Python profiler

**Problem**: TAK output >2s
```
AssertionError: TAK output latency 2500ms exceeds SLA of 2000ms
```
**Solutions**:
- Check network latency to TAK simulator
- Verify async I/O in TAK client
- Check GeoJSON serialization time
- Monitor CPU/memory on test machine

---

## Step 7: Debugging Tips

### Enable Debug Logging

```python
# In conftest.py
import logging
logging.basicConfig(level=logging.DEBUG)

# Or set environment variable
export LOG_LEVEL=DEBUG
pytest tests/acceptance/features/walking-skeleton.feature -v -s
```

### Inspect HTTP Requests/Responses

```python
# In test step
@then("the detection is received with HTTP status 202 Accepted")
def check_202(context):
    print(f"Status: {context.last_response.status_code}")
    print(f"Headers: {context.last_response.headers}")
    print(f"Body: {context.last_response.text}")
    assert_status_code(context.last_response, 202)
```

### Check Database State

```bash
# Query SQLite directly
sqlite3 data/app.db

# List detections
SELECT id, source, accuracy_flag FROM detections;

# Check offline queue
SELECT id, status FROM offline_queue;

# View audit trail
SELECT event_type, details FROM audit_trail ORDER BY timestamp DESC;
```

### Monitor Service Health

```bash
# During test, in separate terminal
watch -n 1 'curl -s http://localhost:8000/api/v1/health | jq .'

# Check TAK simulator received detections
watch -n 1 'curl -s http://localhost:9000/stats | jq .'
```

---

## Step 8: Success Criteria Checklist

Walking skeleton is complete when:

- [ ] Test runs: `pytest walking-skeleton.feature -v`
- [ ] All 4 scenarios in walking-skeleton.feature pass
- [ ] Latency <2 seconds (API → COP map)
- [ ] Accuracy flag validated (GREEN correctly assigned)
- [ ] TAK server receives detections
- [ ] Audit trail records all events
- [ ] Health checks pass
- [ ] Database schema initialized
- [ ] No errors or warnings in logs
- [ ] Code review approved
- [ ] Commit message includes story reference

---

## Step 9: Commit and Handoff

When walking skeleton passes all scenarios:

```bash
# Verify all tests pass
pytest tests/acceptance/features/walking-skeleton.feature -v

# Stage changes
git add tests/acceptance/features/walking-skeleton.feature
git add tests/acceptance/steps/conftest.py
git add tests/acceptance/steps/detection_steps.py
git add tests/acceptance/docs/

# Commit with message
git commit -m "feat: implement walking skeleton acceptance tests

- E2E validation: JSON → validation → transform → TAK output
- All scenarios passing with <2s latency
- Audit trail complete
- Infrastructure smoke tests passing

Stories: US-001, US-002, US-003, US-004
Acceptance criteria: 100% passing"

# Push to main
git push origin main
```

---

## Troubleshooting Quick Reference

| Issue | Symptom | Solution |
|-------|---------|----------|
| API not ready | "Connection refused port 8000" | `docker-compose up app` |
| TAK not ready | "TAK simulator not responding" | `docker-compose up tak-sim` |
| Database error | "sqlite3.OperationalError" | Delete `data/*.db`, restart |
| Latency SLA fail | "Latency 2.5s exceeds target <2s" | Profile with cProfile, optimize paths |
| Audit trail missing | "No audit events found" | Check AuditTrailService is logging |
| Geolocation flag wrong | "Expected GREEN, got YELLOW" | Verify accuracy_meters < 500m |
| GeoJSON invalid | "Invalid JSON output" | Validate with RFC 7946 validator |
| Concurrent test fail | "Duplicate detection_ids" | Use UUID generator in fixture |

---

## Resources

- **Architecture**: `/docs/architecture/architecture.md`
- **User Stories**: `/docs/requirements/user-stories.md`
- **Thresholds**: `/docs/requirements/shared-artifacts-registry.md`
- **BDD Methodology**: Load `bdd-methodology` skill
- **pytest-bdd Docs**: https://pytest-bdd.readthedocs.io/
- **Gherkin Syntax**: https://cucumber.io/docs/gherkin/

---

**Status**: READY FOR EXECUTION
**Next Step**: Execute `pytest tests/acceptance/features/walking-skeleton.feature -v`
**Expected Time**: 30-60 minutes to first passing test
**Success**: "1 passed in 2.34s"
