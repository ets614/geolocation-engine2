# Detection to CoP - System Architecture

**Status**: Production Ready (Lean Core)
**Version**: 1.0.0

---

## System Purpose

Convert AI-detected objects from aerial imagery (pixel coordinates + camera metadata) into real-time tactical intelligence (GPS coordinates + CoT XML) for military and emergency response systems.

---

## Core Architecture

### High-Level Flow

```
AI Detection Input
    ↓
[Detection Service]
    ├─ Input validation
    ├─ Photogrammetry calculation
    ├─ CoT XML generation
    ├─ TAK server push (async)
    ├─ Offline queue fallback
    └─ Audit logging
    ↓
CoT/TAK Output
```

### Component Diagram

```
┌─────────────────────────────────────────────────────┐
│              FastAPI Application                    │
│              Port 8000                              │
└─────────────────────────────────────────────────────┘
                        ↑
                    Routes
                        ↓
    ┌───────────────────────────────────────────┐
    │    POST /api/v1/detections                │
    │    GET /api/v1/health                     │
    └───────────────────────────────────────────┘
                        ↓
    ┌───────────────────────────────────────────┐
    │    Detection Service (Coordinator)        │
    └───────────────────────────────────────────┘
      │      │           │          │         │
      ↓      ↓           ↓          ↓         ↓
    ┌──┐  ┌──┐       ┌────┐    ┌──────┐  ┌──────┐
    │V ├──┤IN├───────┤GEO │────│ CoT  ├─→│ TAK  │
    │AL│  │P ├───────┤LOC │    │ GEN  │  │PUSH  │
    │ID│  │UT├───────┤ATE │    └──────┘  └──┬───┘
    └──┘  └──┘  →   └────┘                  │
              OFFLINE QUEUE ←────────────────┘
                 (SQLite)     (if offline)
              ┌──────────────┐
              │ AUDIT TRAIL  │
              │ (Immutable)  │
              └──────────────┘
```

---

## Core Services (5)

1. **DetectionService** - Orchestrator (20 tests)
2. **GeolocationService** - Photogrammetry (27 tests)
3. **CotService** - TAK XML output (15 tests)
4. **OfflineQueueService** - SQLite persistence (37 tests)
5. **AuditTrailService** - Event logging (41 tests)

---

## Key Performance Metrics

| Metric | Value | Status |
|--------|-------|--------|
| Geolocation calc | ~3ms | ✅ |
| CoT XML gen | ~1ms | ✅ |
| E2E (no TAK push) | ~15ms | ✅ |
| Throughput | 100+ req/s | ✅ |

---

## Database Schema

### SQLite Tables

```sql
-- Detections
CREATE TABLE detections (
    id TEXT PRIMARY KEY,
    geolocation_lat REAL,
    geolocation_lon REAL,
    confidence_flag TEXT,
    accuracy_meters REAL,
    cot_xml TEXT,
    created_at TIMESTAMP
);

-- Offline Queue (Resilience)
CREATE TABLE detection_queue (
    id TEXT PRIMARY KEY,
    detection_id TEXT,
    cot_xml TEXT,
    status TEXT,  -- PENDING_SYNC, SYNCED
    retry_count INT DEFAULT 0,
    created_at TIMESTAMP
);

-- Audit Trail (Immutable Logging)
CREATE TABLE audit_trail (
    id TEXT PRIMARY KEY,
    event_type TEXT,
    client_id TEXT,
    details TEXT,
    created_at TIMESTAMP
);
```

---

## Deployment

- **Single instance**: FastAPI on port 8000
- **Database**: SQLite (local)
- **TAK Integration**: Async HTTP push
- **Resilience**: Offline queue + auto-sync

---

**Last Updated**: 2026-02-15
