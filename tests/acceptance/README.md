# Acceptance Tests - AI Detection to COP Translation System

**Status**: READY FOR EXECUTION
**Test Framework**: pytest-bdd (Python BDD)
**Test Count**: 74 scenarios across 7 feature files
**Coverage**: Happy path (26%) + Error handling (22%) + Boundary (22%) + Performance (27%)

---

## Quick Start

### Prerequisites
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install pytest pytest-bdd requests
docker-compose up -d
```

### Run Walking Skeleton Test
```bash
# First test - validates entire architecture
pytest features/walking-skeleton.feature::Scenario -v -m milestone_1

# Expected: PASSED (confirms architecture works end-to-end)
```

### Run All Tests
```bash
# Walking skeleton (milestone 1, enabled)
pytest features/walking-skeleton.feature -v

# All acceptance tests (walking skeleton + @skip for future)
pytest features/ -v

# Only error handling tests
pytest features/ -v -m error_handling

# Only performance SLA tests
pytest features/ -v -m performance
```

---

## Structure

```
tests/acceptance/
├── README.md (this file)
├── features/
│   ├── walking-skeleton.feature          (Validates entire architecture)
│   ├── detection-ingestion.feature       (US-001: Ingest JSON)
│   ├── geolocation-validation.feature    (US-002: Validate geolocation - KILLER FEATURE)
│   ├── format-translation.feature        (US-003: Transform to GeoJSON)
│   ├── tak-output.feature                (US-004: Output to TAK)
│   ├── offline-queue-sync.feature        (US-005: Offline queuing)
│   └── deployment-smoke-tests.feature    (Infrastructure tests)
├── steps/
│   ├── conftest.py                       (Test fixtures & configuration)
│   ├── detection_steps.py                (Step definitions for US-001, US-002)
│   ├── geolocation_steps.py              (Step definitions for validation)
│   ├── format_steps.py                   (Step definitions for GeoJSON)
│   ├── tak_steps.py                      (Step definitions for TAK output)
│   ├── queue_steps.py                    (Step definitions for offline queue)
│   └── infrastructure_steps.py            (Step definitions for deployment)
└── docs/
    ├── test-scenarios.md                 (Test coverage matrix & strategy)
    ├── walking-skeleton-guide.md         (Step-by-step setup & execution)
    └── acceptance-review.md              (Quality review & peer approval)
```

---

## Feature Files

### 1. walking-skeleton.feature
**Purpose**: Demonstrate complete end-to-end system
**Scenarios**: 4
- ✅ **Ingest JSON detection and output to TAK** (milestone_1, enabled)
- ⏭️ Multiple detections from different sources (@skip)
- ⏭️ System handles network outage transparently (@skip)
- ⏭️ Deployment smoke test (@skip)

**Start here**: `pytest features/walking-skeleton.feature -v -m milestone_1`

---

### 2. detection-ingestion.feature (US-001)
**Problem**: Integrating new detection source takes 2-3 weeks
**Solution**: REST API accepts JSON detections in <100ms

**Scenarios**: 9 (2 happy path, 4 error, 2 boundary, 1 performance)
- Happy: Valid JSON ingested, multiple sources
- Error: Malformed JSON (E001), missing fields (E002), rate limit (429), timeout
- Boundary: Precise coordinates, concurrent requests
- Performance: <100ms latency, >100 req/sec throughput

---

### 3. geolocation-validation.feature (US-002 - KILLER FEATURE)
**Problem**: Manual coordinate validation takes 30 minutes per mission
**Solution**: Automatic GREEN/YELLOW/RED accuracy flagging (80% time savings)

**Scenarios**: 12 (2 happy path, 3 error, 4 boundary, 3 performance)
- Happy: GREEN flag (auto-trust), YELLOW flag (spot-check 2 min), RED flag (manual correction)
- Error: Out-of-range coordinates, low confidence, validation failure
- Boundary: Terrain-specific thresholds, coordinate system normalization
- Performance: <100ms validation, >95% GREEN flag accuracy

**Key Success Metric**: 30 minutes → 5 minutes (80% time savings)

---

### 4. format-translation.feature (US-003)
**Problem**: Every vendor has different format (JSON, CSV, binary)
**Solution**: Transform any format to standardized GeoJSON (RFC 7946)

**Scenarios**: 10 (2 happy path, 1 error, 3 boundary, 2 compatibility, 2 performance)
- Happy: UAV detection → GeoJSON, satellite detection → GeoJSON, camera → GeoJSON
- Error: Invalid coordinate precision
- Boundary: Extremely precise coordinates, multiple source consistency
- Compatibility: TAK Server compatible, ArcGIS compatible
- Performance: <100ms transformation

---

### 5. tak-output.feature (US-004)
**Problem**: Detections need to appear on COP map in real-time (<2 seconds)
**Solution**: Real-time TAK Server output + offline queuing

**Scenarios**: 10 (2 happy path, 3 error, 2 boundary, 3 performance)
- Happy: Detection appears on map <2s, fire detection E2E flow
- Error: TAK offline (queue locally), timeout (retry), auth failure (alert)
- Boundary: High-volume stream (10+ det/min), burst traffic
- Performance: <2s latency, >99% delivery rate

---

### 6. offline-queue-sync.feature (US-005)
**Problem**: System fails 30% of the time; field ops manually screenshot
**Solution**: Offline-first (queue locally) + auto-sync (transparent recovery)

**Scenarios**: 13 (2 happy path, 3 error, 4 boundary, 3 performance, 1 E2E)
- Happy: Queue locally when offline, auto-sync on reconnect
- Error: Sync retries (exponential backoff), permanent failure (alert)
- Boundary: Power cycle (queue survives reboot), intermittent connection, extended outage
- Performance: Batch sync >1000 items/sec, <5s first detection synced
- E2E: UAV mission with intermittent connectivity (complete user journey)

**Key Success Metric**: Zero data loss (99.99% reliability)

---

### 7. deployment-smoke-tests.feature
**Purpose**: Validate deployment readiness and CI/CD integration

**Scenarios**: 16 (8 happy path, 0 error, 8 infrastructure)
- Health check (database, API, TAK, queue)
- Docker deployment (container starts, port listening)
- Configuration (environment variables, secrets)
- Database (schema, migration, backup/restore)
- Kubernetes (manifests, pod health)
- Security (API authentication, HTTPS)
- Monitoring (Prometheus metrics, alerting)
- CI/CD (pipeline validation, smoke tests)

---

## Test Scenarios Summary

| Feature | Happy Path | Error | Boundary | Performance | Total |
|---------|-----------|-------|----------|-------------|-------|
| Walking Skeleton | 1 | 2 | 1 | 0 | 4 |
| US-001 Ingestion | 2 | 4 | 2 | 1 | 9 |
| US-002 Validation | 2 | 3 | 4 | 3 | 12 |
| US-003 Translation | 2 | 1 | 3 | 2 | 8 |
| US-004 TAK Output | 2 | 3 | 2 | 3 | 10 |
| US-005 Queue/Sync | 2 | 3 | 4 | 3 | 13 |
| Infrastructure | 8 | 0 | 0 | 8 | 16 |
| **TOTAL** | **19** | **16** | **16** | **20** | **74** |

---

## Key Success Criteria

### Integration Specialist (US-001)
- ✅ Integration time: <1 hour per source (vs. 2-3 weeks)
- ✅ Configuration: <10 minutes via API
- ✅ Error handling: Automatic (no operator intervention)

### Operations Manager (US-002 - Killer Feature)
- ✅ Manual validation: 5 minutes per mission (vs. 30 minutes)
- ✅ Time savings: **80% (30 min → 5 min)**
- ✅ GREEN flag accuracy: >95% validated

### Command Dispatcher (US-004)
- ✅ Time to map: <2 seconds (API → display)
- ✅ Reliability: >99% (detections displayed)
- ✅ No manual workarounds

### Field Operator (US-005)
- ✅ Data loss: **ZERO** during offline periods
- ✅ Recovery: Automatic (no operator action)
- ✅ Uptime: >99% (transparent queueing)

---

## Implementation Roadmap

### Phase 1: Walking Skeleton (Milestone 1)
```bash
pytest features/walking-skeleton.feature::Scenario -v -m milestone_1
```
- ✅ Proves architecture works end-to-end
- <2s latency, all components integrated
- Enables 1st commit

### Phase 2: Core Stories (One at a time)
```bash
# Remove @skip from US-001 scenarios
pytest features/detection-ingestion.feature -v -m milestone_1
# [implement] → commit → move to next story
```

**Order**: US-001 → US-002 → US-003 → US-004 → US-005

Each story:
1. Enable happy path (@milestone_1)
2. Implement feature
3. Enable error scenarios (@error_handling)
4. Implement error recovery
5. Enable boundary scenarios (@boundary)
6. Optimize edge cases
7. Enable performance tests (@performance)
8. Tune for SLA

### Phase 3: Infrastructure (Week 8-12)
```bash
pytest features/deployment-smoke-tests.feature -v -m infrastructure
```
- Docker image validated
- Kubernetes manifests working
- CI/CD pipeline green

---

## Performance SLA Targets

| Component | Target | How to Validate |
|-----------|--------|-----------------|
| JSON Ingestion | <100ms | `@then("ingestion latency is less than 100 milliseconds")` |
| Geolocation Validation | <100ms | `@then("validation latency < 100ms")` |
| GeoJSON Transformation | <100ms | Performance test scenario |
| TAK Output | <1000ms | Performance test scenario |
| **End-to-End** | **<2 seconds** | Walking skeleton, US-004 E2E |
| Queue Batch Sync | >1000 items/sec | US-005 batch performance |
| Health Check | <1 second | Infrastructure smoke test |

---

## Test Execution

### Local Development
```bash
# Terminal 1: Start services
docker-compose up -d app tak-sim

# Terminal 2: Run tests
pytest tests/acceptance/features/walking-skeleton.feature -v -s

# Terminal 3: Monitor services (optional)
docker-compose logs -f app
```

### CI/CD Pipeline
```yaml
test:
  stage: test
  script:
    - pytest tests/acceptance/features/ -v --junit-xml=report.xml
    - pytest tests/acceptance/ --cov=src --cov-report=html
  artifacts:
    reports:
      junit: report.xml
    paths:
      - htmlcov/
```

### Coverage Goals
- Acceptance tests: **100% of user stories** (40+ scenarios)
- Integration: **Real service fixtures** (HTTP client, TAK, database)
- Unit tests: **>80%** (planned separately)

---

## Documentation

### For Product Owners
📖 **test-scenarios.md**: Test coverage matrix, success metrics, one-at-a-time roadmap

### For Engineers
📖 **walking-skeleton-guide.md**: Step-by-step setup, data flow tracing, debugging tips

### For Tech Leads
📖 **acceptance-review.md**: Quality review (6 dimensions), peer approval checklist

---

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| API service not ready | `docker-compose up app` + wait 5s |
| TAK simulator not responding | `docker-compose up tak-sim` |
| Database locked | Delete `data/test.db`, restart |
| Latency exceeds SLA | Profile with cProfile, check docker stats |
| Audit trail missing | Verify AuditTrailService is logging |
| GeoJSON invalid | Validate with RFC 7946 validator |

---

## Resources

- **Architecture**: `/docs/architecture/architecture.md`
- **User Stories**: `/docs/requirements/user-stories.md`
- **Thresholds**: `/docs/requirements/shared-artifacts-registry.md`
- **pytest-bdd Docs**: https://pytest-bdd.readthedocs.io/
- **Gherkin Syntax**: https://cucumber.io/docs/gherkin/

---

## Next Steps

1. **Read walking-skeleton-guide.md** (15 min setup)
2. **Run walking skeleton test** (expect PASSED in 2-3s)
3. **Review test-scenarios.md** (understand coverage)
4. **Start implementation**: Enable 1 scenario, implement, commit, repeat
5. **Peer review**: acceptance-review.md (quality gates)

---

**Ready to Start?**
```bash
pytest tests/acceptance/features/walking-skeleton.feature::Scenario -v -m milestone_1
```

Expected: `PASSED (1 scenario) in 2.34s`

---

**Questions?**
- Architecture: Check `/docs/architecture/`
- Test setup: See `walking-skeleton-guide.md`
- Coverage details: See `test-scenarios.md`
- Quality review: See `acceptance-review.md`

**Status**: ✅ READY FOR EXECUTION
**Next Owner**: Software Crafter (BUILD Wave)
**Timeline**: 8-12 weeks to MVP
