# Detection to COP: AI Detection to Photogrammetry to TAK Integration

Transform AI-detected objects from aerial imagery into real-time tactical intelligence for Cursor on Target (CoT) systems and TAK (Tactical Assault Kit) platforms.

**Status**: Production Ready (Phase 04-05 Complete) | **Version**: 1.0.0 | **Tests**: 331+ passing

---

## Project Status Snapshot

```
PHASE 01: Foundation              ████████████████████ 100% DONE
PHASE 02: Core Features           ████████████████████ 100% DONE
PHASE 03: Offline-First           ████████████████████ 100% DONE
PHASE 04: Security & Performance  ████████████████████ 100% DONE
PHASE 05: Production Deployment   ████████████████████ 100% DONE
```

### Test Coverage

| Component | Tests | Status |
|-----------|-------|--------|
| **Geolocation Service** | 27 | PASS |
| **CoT Service** | 15 | PASS |
| **Config Service** | 4 | PASS |
| **Audit Trail Service** | 41 | PASS |
| **Offline Queue Service** | 37 | PASS |
| **JWT Service** | 12 | PASS |
| **API Key Service** | 18 | PASS |
| **Rate Limiter Service** | 14 | PASS |
| **Input Sanitizer Service** | 22 | PASS |
| **Cache Service** | 16 | PASS |
| **Security Service** | 20 | PASS |
| **Auth/Middleware/Endpoints** | 37 | PASS |
| **Monitoring Infrastructure** | 51 | PASS |
| **Acceptance Tests** | 14 | PASS |
| **TOTAL** | **331+** | **ALL PASS** |

**[Full progress tracking in PROGRESS.md](docs/feature/ai-detection-cop-integration/PROGRESS.md)**

---

## What This Does

Converts **image pixel coordinates from AI detections** into **real-world geolocation** via photogrammetry and outputs **standard CoT/XML for TAK systems**.

```
AI Model Output:
  Image + Pixel(512, 384) + Camera(lat, lon, elevation, heading, pitch, roll)
           |
Photogrammetry Pipeline:
  - Pinhole camera model (intrinsic matrix)
  - Euler angle to rotation matrix conversion
  - Ray-ground plane intersection
  - WGS84 coordinate transformation
           |
Security Layer:
  - JWT RS256 / API Key authentication
  - Rate limiting (token bucket)
  - Input sanitization (SQL/XSS/path traversal)
  - Caching (TTL + LFU)
           |
Output: Cursor on Target (CoT) XML
  <event uid="Detection.abc-123" type="b-m-p-s-u-c">
    <point lat="40.7135" lon="-74.0050" ce="15.5"/>
    <detail>
      <remarks>AI Detection: Vehicle | Confidence: 92% | Accuracy: GREEN</remarks>
    </detail>
  </event>
           |
TAK Integration: Push to TAK server for real-time map display
  - Online: Direct push with connection pooling
  - Offline: SQLite queue with auto-sync on reconnect
           |
Observability:
  - Prometheus metrics (/metrics)
  - Grafana dashboards (4 dashboards)
  - Alert rules (19 rules, 7 groups)
  - Structured JSON logs (Loki-ready)
```

---

## Architecture

### Processing Pipeline

```
Input Validation
    |
Authentication (JWT / API Key)
    |
Rate Limiting (Token Bucket)
    |
Input Sanitization
    |
Cache Check (read endpoints)
    |
GeolocationCalculationService (Photogrammetry)
  - Camera intrinsic matrix
  - Euler angles to rotation matrix
  - Pixel normalization
  - Ray generation and world transform
  - Ground plane intersection
  - Confidence and uncertainty
    |
DetectionService (Storage)
  - Image deduplication
  - Database storage
    |
CotService (Format)
  - CoT XML generation
  - TAK color mapping
    |
API Response + TAK Push
  - Return CoT XML (201)
  - Async push to TAK (non-blocking)
  - Offline queue if TAK unavailable
    |
Audit Trail + Metrics
  - Immutable event logging
  - Prometheus counters and histograms
```

### Security Architecture

```
Layer 1: Network         NGINX Ingress TLS, Network Policies
Layer 2: Authentication  JWT RS256 tokens, API keys
Layer 3: Rate Limiting   Token bucket (per-client, per-IP)
Layer 4: Input Validation Sanitization (SQL/XSS/traversal/injection)
Layer 5: Caching         TTL + LFU in-memory cache
Layer 6: Security Headers X-Content-Type-Options, HSTS, CSP
Layer 7: Audit Trail     Immutable event logging, security events
```

### Kubernetes Deployment Architecture

```
                    [NGINX Ingress + TLS]
                           |
                    [detection-api-service]
                    selector: slot=green|blue
                           |
              +------------+------------+
              |                         |
    [green deployment]        [blue deployment]
    3-10 replicas (HPA)       standby
              |
    +----+----+----+----+
    |    |    |    |    |
   PVC  emptyDir CM  Secret
   app.db queue.db config  creds
              |
    [Prometheus + Loki + Grafana]
              |
    [ArgoCD GitOps]
```

---

## Features

### Phase 01-03: Core Pipeline
- **Photogrammetry Engine**: Pinhole camera model, Euler angles, ground plane intersection
- **TAK Integration**: Standard CoT format, type mapping, confidence visualization
- **Offline-First**: SQLite queue, auto-sync, crash recovery, max 3 retries
- **Audit Trail**: 10 event types, immutable logging, 90-day retention
- **124 core tests passing**

### Phase 04: Security and Performance Hardening
- **JWT RS256 Authentication**: Token generation, refresh, revocation with asymmetric signing
- **API Key Management**: Scope-based access control, SHA256 hashing, expiration
- **Rate Limiting**: Token bucket algorithm, per-client and per-IP buckets
- **Input Sanitization**: SQL injection, XSS, path traversal, command injection prevention
- **In-Memory Caching**: TTL-based expiry, LFU eviction, 10K entries, ~50MB
- **Security Headers**: HSTS, CSP, X-Frame-Options, X-Content-Type-Options
- **Prometheus Metrics**: RED metrics, auth metrics, business metrics, /metrics endpoint
- **Load Testing**: Locust framework with 3 user profiles, SLO compliance reporting
- **207+ security and performance tests**

### Phase 05: Production Deployment
- **Kubernetes Architecture**: Blue-green deployment, HPA (3-10 replicas), topology spread
- **ArgoCD GitOps**: Auto-sync, self-heal, drift detection, instant rollback
- **Sealed Secrets**: Bitnami Sealed Secrets for encrypted credentials in Git
- **Observability Stack**: Prometheus + Loki + Grafana with 19 alert rules
- **Infrastructure as Code**: Terraform modules (VPC, EKS, RDS, S3, IAM)
- **Helm Charts**: 10 templates for full application deployment
- **Disaster Recovery**: Daily backups, < 120s rollback, SEV-level incident response
- **51 infrastructure tests**

---

## Quick Start

### Installation

```bash
# Clone repository
git clone <repo-url>
cd geolocation-engine2

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# For development/testing
pip install -e ".[dev]"
```

### Run Service

```bash
# Set environment variables
export TAK_SERVER_URL=http://tak-server:8080/CoT
export JWT_SECRET_KEY=your-secret-key-here
export DEBUG=false

# Start FastAPI server
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# Health check
curl http://localhost:8000/api/v1/health
```

### Docker

```bash
# Build image
docker build -t detection-to-cop .

# Run container
docker run -p 8000:8000 \
  -e TAK_SERVER_URL=http://tak-server:8080/CoT \
  -e JWT_SECRET_KEY=your-secret-key-here \
  detection-to-cop

# Or use Docker Compose
docker-compose up -d
```

### Run with Monitoring

```bash
# Start monitoring stack (Prometheus + Grafana)
docker compose -f infrastructure/docker-compose.monitoring.yml up -d

# Start Detection API
uvicorn src.main:app --host 0.0.0.0 --port 8000

# Access:
# API:        http://localhost:8000
# Prometheus: http://localhost:9090
# Grafana:    http://localhost:3000 (admin/admin)
# Metrics:    http://localhost:8000/metrics
```

---

## Configuration

### Environment Variables

```bash
# Application
DEBUG=false
DATABASE_URL=sqlite:///./data/app.db

# TAK Server Integration
TAK_SERVER_URL=http://localhost:8080/CoT

# Authentication
JWT_SECRET_KEY=your-secret-key-here        # For HS256 (dev)
JWT_PRIVATE_KEY_PATH=/path/to/private.pem  # For RS256 (prod)
JWT_PUBLIC_KEY_PATH=/path/to/public.pem    # For RS256 (prod)

# Rate Limiting
RATE_LIMIT_AUTHENTICATED=100  # requests per bucket
RATE_LIMIT_UNAUTHENTICATED=10

# Cache
CACHE_MAX_ENTRIES=10000
CACHE_DEFAULT_TTL=60
```

---

## API Reference

### Authentication

```bash
# Generate JWT token
curl -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"client_id": "my-app", "client_secret": "secret"}'

# Refresh token
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJ..."}'

# Create API key
curl -X POST http://localhost:8000/api/v1/api-keys \
  -H "Authorization: Bearer eyJ..." \
  -d '{"name": "uav-feed", "scopes": ["write:detections"]}'
```

### Detection Ingestion

```bash
# POST /api/v1/detections (requires auth)
curl -X POST http://localhost:8000/api/v1/detections \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJ..." \
  -d '{
    "image_base64": "iVBORw0KGgo...",
    "pixel_x": 512,
    "pixel_y": 384,
    "object_class": "vehicle",
    "ai_confidence": 0.92,
    "source": "uav_detection_model_v2",
    "camera_id": "dji_phantom_4",
    "timestamp": "2026-02-15T12:00:00Z",
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
  }'
```

**Response (201 Created):**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<event version="2.0" uid="Detection.550e8400-e29b-41d4-a716-446655440000"
        type="b-m-p-s-u-c" time="2026-02-15T12:00:00Z">
  <point lat="40.7135" lon="-74.0050" hae="0.0" ce="15.5" le="9999999.0"/>
  <detail>
    <remarks>AI Detection: Vehicle | AI Confidence: 92% | Geo Confidence: GREEN | Accuracy: +/-15.5m</remarks>
    <contact callsign="Detection-550e8400"/>
  </detail>
</event>
```

### Health and Monitoring

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Prometheus metrics
curl http://localhost:8000/metrics
```

---

## Confidence Flags

| Flag | Value | Meaning | TAK Color |
|------|-------|---------|-----------|
| GREEN | >= 0.75 | High confidence | Red (attention) |
| YELLOW | 0.50-0.75 | Medium confidence | Green (normal) |
| RED | < 0.50 | Low confidence | Blue (informational) |

---

## Testing

### Run All Tests

```bash
# Full test suite (331+ tests)
pytest tests/ -v

# Unit tests only (124 core + 207 security/performance)
pytest tests/unit/ -v

# Infrastructure tests
pytest tests/infrastructure/ -v

# Acceptance tests
pytest tests/acceptance/ -v

# With coverage report
pytest tests/ --cov=src --cov-report=html
```

### Load Testing

```bash
# Quick load test (50 users, 2 minutes)
locust -f tests/load/locustfile.py --host http://localhost:8000 \
  --headless -u 50 -r 10 --run-time 2m

# Full load test with report
./tests/load/run_load_test.sh http://localhost:8000 200 20 5m
```

---

## Performance

| Operation | Latency |
|-----------|---------|
| Geolocation calculation | ~2-5ms |
| CoT XML generation | ~1-2ms |
| Database write | ~5-10ms |
| Total E2E (no TAK push) | ~10-20ms |
| TAK server push | ~50-500ms (async, non-blocking) |
| Cache hit | ~0.1ms |

### SLO Targets

| Metric | Target |
|--------|--------|
| Error rate | < 0.1% |
| P95 latency | < 300ms |
| P99 latency | < 500ms |
| Availability | > 99.9% |

---

## Project Structure

```
src/
+-- main.py                          # FastAPI app
+-- config.py                        # Configuration
+-- middleware.py                     # CORS and middleware
+-- database.py                      # SQLAlchemy setup
+-- metrics.py                       # Prometheus instrumentation
+-- api/
|   +-- routes.py                    # API endpoints
|   +-- auth.py                      # Auth endpoints
+-- services/
|   +-- detection_service.py         # Detection pipeline
|   +-- geolocation_service.py       # Photogrammetry
|   +-- cot_service.py               # CoT generation
|   +-- audit_trail_service.py       # Audit logging
|   +-- offline_queue_service.py     # Offline queue
|   +-- jwt_service.py               # JWT authentication
|   +-- api_key_service.py           # API key management
|   +-- rate_limiter_service.py      # Rate limiting
|   +-- input_sanitizer_service.py   # Input sanitization
|   +-- cache_service.py             # In-memory caching
|   +-- security_service.py          # Security hardening
+-- models/
    +-- schemas.py                   # Pydantic models
    +-- database_models.py           # ORM models

tests/
+-- unit/                            # Unit tests (all services)
+-- integration/                     # Integration tests
+-- acceptance/                      # Acceptance tests
+-- infrastructure/                  # Monitoring config tests
+-- load/                            # Locust load tests

infrastructure/
+-- prometheus/                      # Prometheus config + alert rules
+-- grafana/                         # Dashboards + provisioning
+-- terraform/                       # IaC (VPC, EKS, RDS, S3, IAM)
+-- docker-compose.monitoring.yml    # Local monitoring stack

kubernetes/
+-- manifests/                       # Raw K8s manifests
+-- helm-charts/                     # Helm chart (10 templates)
+-- monitoring/                      # K8s monitoring stack

docs/
+-- architecture/                    # Architecture design documents
+-- design/                          # Phase-specific design docs
+-- evolution/                       # Phase completion archives
+-- adrs/                            # Architecture Decision Records
+-- research/                        # Technical research
+-- feature/                         # Feature progress tracking
```

---

## Technology Stack

**Core**
- Python 3.10+, FastAPI, Pydantic, SQLAlchemy

**Security**
- PyJWT (RS256), hashlib, custom sanitization

**Processing**
- NumPy (linear algebra), PyProj (coordinate systems)

**Performance**
- cachetools (TTL/LFU cache), prometheus_client (metrics)

**Infrastructure**
- Kubernetes, Helm, ArgoCD, Terraform

**Observability**
- Prometheus, Grafana, Loki, Alertmanager

**Testing**
- pytest, pytest-asyncio, pytest-cov, Locust

**Database**
- SQLite (development), PostgreSQL (production)

---

## Documentation

- [Architecture](docs/architecture/architecture.md) - Hexagonal architecture design
- [Security Architecture](docs/design/phase-04/SECURITY-ARCHITECTURE.md) - Auth, rate limiting, sanitization
- [Performance Architecture](docs/design/phase-04/PERFORMANCE-ARCHITECTURE.md) - Caching, metrics, optimization
- [Kubernetes Architecture](docs/architecture/phase05-kubernetes-production.md) - Production K8s design
- [Deployment Strategy](docs/architecture/phase05-deployment-strategy.md) - Blue-green, rollback, runbook
- [Monitoring Setup](infrastructure/MONITORING_SETUP.md) - Prometheus + Grafana setup
- [Photogrammetry Research](docs/research/photogrammetry-image-to-world.md) - 40+ sources
- [Acceptance Tests](tests/acceptance/docs/) - Feature specifications
- [ADRs](docs/adrs/) - 9 Architecture Decision Records
- [Progress Tracking](docs/feature/ai-detection-cop-integration/PROGRESS.md) - Full project timeline

---

## Troubleshooting

**Q: "pixel_x must be < image_width"**
- A: Verify pixel coordinates match sensor_metadata image dimensions

**Q: "Ground plane behind camera"**
- A: Check camera_elevation (positive) and camera_pitch (downward angle)

**Q: TAK server not receiving CoT**
- A: Verify TAK_SERVER_URL is correct: `echo $TAK_SERVER_URL`

**Q: Low geolocation confidence (RED flag)**
- A: Reduce camera elevation or improve camera pitch downward angle

**Q: 401 Unauthorized**
- A: Include `Authorization: Bearer <token>` or `X-API-Key: <key>` header

**Q: 429 Too Many Requests**
- A: Reduce request rate or check `Retry-After` header for wait time

---

## Contributing

### Code Style
- Python: PEP 8
- Commits: Conventional Commits (feat:, fix:, docs:)
- Tests: Minimum 80% coverage
- Docstrings: Google-style

### Process
1. Create feature branch
2. Write tests first (TDD)
3. Implement feature
4. Run full test suite
5. Create PR with description

---

## Roadmap

### Completed (Phases 01-05)
- Photogrammetry engine with confidence calculation
- CoT/TAK output format with color mapping
- Offline-first SQLite queue with persistence and recovery
- Immutable audit trail with 10 event types
- JWT RS256 authentication with token refresh
- API key management with scope-based access
- Token bucket rate limiting
- Input sanitization (SQL/XSS/traversal)
- In-memory caching with TTL and LFU
- Security headers and CORS hardening
- Prometheus metrics and Grafana dashboards
- Kubernetes architecture with blue-green deployment
- ArgoCD GitOps with sealed secrets
- Terraform Infrastructure as Code
- Disaster recovery procedures
- 331+ tests passing (93.5% coverage)

### Future (Phase 06+)
- KEDA event-driven autoscaling
- OpenTelemetry distributed tracing
- External Secrets Operator with Vault
- Multi-COP output (ArcGIS, CAD platforms)
- Machine learning confidence calibration
- Multi-source detection fusion
- Service mesh (Istio/Linkerd)

---

**Last Updated**: 2026-02-15
**Version**: 1.0.0
**Status**: Production Ready (Phase 04-05 Complete)
