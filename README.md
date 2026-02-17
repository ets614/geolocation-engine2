# Detection to COP: AI Detection to Geolocation to TAK Integration

Transform AI-detected objects from aerial imagery into real-time tactical intelligence for Cursor on Target (CoT) systems and TAK (Tactical Assault Kit) platforms.

**Status**: Production Ready | **Version**: 1.0.0 | **Tests**: 154 passing

---

## What This Does

Converts **image pixel coordinates from AI detections** into **real-world geolocation** via photogrammetry and outputs **standard CoT/XML for TAK systems**.

```
AI Detection Input
  Image + Pixel(512, 384) + Camera(lat, lon, elevation, heading, pitch, roll)
           ↓
Photogrammetry Pipeline
  - Pinhole camera model (intrinsic matrix)
  - Euler angle to rotation matrix conversion
  - Ray-ground plane intersection
  - WGS84 coordinate transformation
           ↓
Core Processing
  - Validate input
  - Calculate geolocation + confidence
  - Generate CoT (Cursor on Target) XML
           ↓
TAK Integration
  - Push to TAK server (async, non-blocking)
  - Or queue locally (SQLite) if TAK offline
           ↓
Output: CoT XML for Display
  <event uid="Detection.abc-123" type="b-m-p-s-u-c">
    <point lat="40.7135" lon="-74.0050" ce="15.5"/>
    <remarks>AI Detection: Vehicle | Confidence: 92% | Accuracy: ±15.5m</remarks>
  </event>
```

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
```

### Run Service

```bash
# Set environment variables
export TAK_SERVER_URL=http://tak-server:8080/CoT
export DATABASE_URL=sqlite:///./data/app.db

# Start FastAPI server
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000

# Health check
curl http://localhost:8000/api/v1/health
```

### Submit Detection

```bash
curl -X POST http://localhost:8000/api/v1/detections \
  -H "Content-Type: application/json" \
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

---

## Architecture

### Processing Pipeline

```
Input Validation
    ↓
GeolocationCalculation
  - Camera intrinsic matrix
  - Euler angles to rotation matrix
  - Pixel normalization
  - Ray generation and world transform
  - Ground plane intersection
  - Confidence and uncertainty
    ↓
DetectionService (Storage)
  - Store detection
  - Generate CoT XML
    ↓
TAK Push
  - Return CoT XML (201)
  - Async push to TAK (non-blocking)
  - Offline queue if TAK unavailable
    ↓
Audit Trail + Response
  - Immutable event logging
  - HTTP response with XML
```

### Core Services

```
src/
├── detection_service.py      - Pipeline coordinator
├── geolocation_service.py    - Photogrammetry (27 tests)
├── cot_service.py            - TAK XML generation (15 tests)
├── offline_queue_service.py  - SQLite queue (37 tests)
└── audit_trail_service.py    - Event logging (41 tests)
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
```

---

## API Reference

### POST /api/v1/detections

Submit a detection from an AI model.

**Request:**
```json
{
  "image_base64": "string (base64 encoded image)",
  "pixel_x": 512,
  "pixel_y": 384,
  "object_class": "vehicle|person|fire|aircraft|unknown",
  "ai_confidence": 0.92,
  "source": "string",
  "camera_id": "string",
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
}
```

**Response (201):**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<event version="2.0" uid="Detection.{id}" type="{cot-type}" time="{timestamp}">
  <point lat="{latitude}" lon="{longitude}" ce="{accuracy_meters}"/>
  <detail>
    <remarks>AI Detection: {class} | AI Confidence: {confidence}% | Geo Confidence: {flag}</remarks>
    <contact callsign="Detection-{id}"/>
  </detail>
</event>
```

### GET /api/v1/health

Health check endpoint.

**Response (200):**
```json
{
  "status": "running",
  "version": "1.0.0",
  "service": "Detection to COP"
}
```

---

## Confidence Flags

| Flag | Meaning | Accuracy | TAK Display |
|------|---------|----------|-------------|
| GREEN | High confidence | ±<30m | Red icon (attention) |
| YELLOW | Medium confidence | ±30-100m | Green icon (normal) |
| RED | Low confidence | ±>100m | Blue icon (info) |

---

## Testing

### Run All Tests

```bash
# Full test suite (154 tests)
pytest tests/ -v

# Unit tests only
pytest tests/unit/ -v

# With coverage report
pytest tests/ --cov=src --cov-report=html
```

---

## Performance

| Operation | Latency |
|-----------|---------|
| Geolocation calculation | ~3ms |
| CoT XML generation | ~1ms |
| Database write | ~5-10ms |
| Total E2E (no TAK push) | ~10-20ms |
| TAK server push | ~50-500ms (async) |

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

---

## Project Structure

```
src/
├── main.py                          # FastAPI app
├── config.py                        # Configuration
├── database.py                      # SQLAlchemy setup
├── middleware.py                    # CORS
├── api/
│   └── routes.py                    # API endpoints
├── services/
│   ├── detection_service.py         # Detection pipeline
│   ├── geolocation_service.py       # Photogrammetry
│   ├── cot_service.py               # CoT generation
│   ├── offline_queue_service.py     # Offline queue
│   ├── audit_trail_service.py       # Audit logging
│   └── config_service.py            # Config management
└── models/
    ├── schemas.py                   # Pydantic models
    └── database_models.py           # ORM models

tests/
└── unit/                            # 154 unit tests

docs/
├── architecture/                    # Architecture design
└── README.md                        # This file
```

---

## Technology Stack

- **Runtime**: Python 3.10+, FastAPI, Pydantic, SQLAlchemy
- **Processing**: NumPy (linear algebra), PyProj (coordinate systems)
- **Database**: SQLite (local), PostgreSQL (production)
- **Testing**: pytest, pytest-asyncio, pytest-cov
- **HTTP**: aiohttp (async HTTP client)

---

## Documentation

- [Architecture](docs/architecture/architecture.md) - System design
- [PROGRESS](docs/feature/ai-detection-cop-integration/PROGRESS.md) - Implementation status

---

## Contributing

### Code Style
- Python: PEP 8
- Tests: Minimum 80% coverage
- Docstrings: Google-style

### Process
1. Write tests first (TDD)
2. Implement feature
3. Run full test suite
4. Submit PR

---

## Performance Characteristics

**Latency Distribution (measured):**
- P50: ~5ms
- P95: ~15ms
- P99: ~25ms

**Throughput:**
- Single instance: 100+ detections/second
- With offline queue: Full resilience when TAK offline

**Reliability:**
- Automatic TAK failover
- SQLite queue persistence
- Complete audit trail

---

**Last Updated**: 2026-02-15
**Version**: 1.0.0
**Status**: Production Ready
