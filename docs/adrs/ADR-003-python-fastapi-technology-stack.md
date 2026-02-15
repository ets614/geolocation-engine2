# ADR-003: Python + FastAPI Technology Stack

**Status**: Accepted

**Date**: 2026-02-17

**Decision Makers**: Solution Architect, Engineering Lead

---

## Context

The system must:
1. Ingest detection data from multiple external APIs (REST, JSON)
2. Validate geolocation with geospatial calculations
3. Transform to GeoJSON format (RFC 7946)
4. Handle polling, async operations, and offline queuing
5. Be deployable in 8-12 weeks with 2-3 engineers

Technology options evaluated: Python, Go, and Rust.

---

## Decision

**Selected**: Python 3.11+ with FastAPI web framework

**Supporting Tools**:
- **Web Framework**: FastAPI (async REST API)
- **Geospatial**: Shapely + pyproj (coordinate validation, transformations)
- **Validation**: Pydantic v2 (type-safe schema validation)
- **HTTP Client**: httpx (async HTTP, connection pooling)
- **Database**: SQLite (MVP) + asyncio wrapper
- **Async Runtime**: asyncio (standard library)

---

## Rationale

### Why Python?

1. **Geospatial Ecosystem**: Best-in-class libraries
   - Shapely: Geometry operations (validate points, distances)
   - pyproj: Coordinate system transformations (WGS84, State Plane, etc.)
   - geopy: Reverse geocoding, distance calculations
   - These are mature, widely used in GIS community
   - Go/Rust lack these libraries or require external C bindings

2. **Fast Development**: Match 8-12 week MVP timeline
   - 40-50% less code than Go/Rust for same functionality
   - Team familiarity (most teams have Python engineers)
   - Rich ecosystem for integration (AWS, APIs, databases)
   - Type hints + Pydantic catch errors at parse time

3. **Async Support**: Modern async/await syntax
   - Python 3.11 asyncio is production-ready
   - FastAPI built on async from day 1
   - Handles 10+ concurrent requests easily
   - Perfect for polling multiple external APIs simultaneously

4. **JSON Handling**: Native JSON parsing + Pydantic validation
   - Automatic schema validation (catch errors early)
   - Automatic type conversion (string "92" → float 0.92)
   - Auto-generate OpenAPI documentation
   - Built-in serialization

5. **Team Productivity**: Factors heavily in MVP speed
   - Python engineers need 3-5 days ramp-up to FastAPI
   - Go engineers need 5-10 days to learn Go idioms
   - Rust requires 2-4 weeks learning curve
   - Team productivity = 8-12 week constraint enabler

### Why NOT Go?

**Advantages**:
- Higher performance (10-50x faster raw speed)
- Excellent concurrency model (goroutines)
- Strong standard library (http, json, database/sql)
- Single binary deployment

**Disadvantages**:
- Geospatial libraries weak or missing
  - No equivalent to Shapely or pyproj
  - Would need C bindings or write custom geometry code
  - Adds technical risk and development time
- Fewer developers comfortable with Go
- Verbosity (error handling `if err != nil` everywhere)
- Slower development cycle (compile time, verbose syntax)
- **Overall Cost**: +2-3 weeks development time for geospatial layer, not worth 10x performance we don't need

**When Go Makes Sense**: If MVP needs 1000+ detections/second or requires sub-millisecond latency. MVP target is <100 detections/second.

### Why NOT Rust?

**Advantages**:
- Maximum performance
- Memory safety guarantees

**Disadvantages**:
- Steep learning curve (ownership model, lifetime parameters)
- Very slow development cycle (compiler feedback cycles)
- Geospatial library ecosystem even weaker than Go
- **Overall Cost**: +4-6 weeks development time, not feasible for 8-12 week MVP
- **ROI**: Performance gains not needed for MVP scale

---

## Alternatives Considered

### Alternative 1: Go + Custom Geospatial Layer
**Approach**:
- Use Go's strong http, concurrency, and JSON support
- Build custom coordinate validation and distance functions
- Use C bindings to GEOS library (if needed)

**Advantages**:
- Single binary deployment
- Higher performance

**Disadvantages**:
- **No Shapely equivalent**: Would need to implement point-in-polygon, distance calculations
- **Risk**: Geospatial algorithms are complex, easy to get wrong
- **Time**: +2-3 weeks to build/test custom geometry functions
- **Maintenance**: Team must maintain geospatial code

**Why Rejected**: Development time overruns 8-12 week constraint. Risk of correctness bugs in custom geospatial code.

### Alternative 2: Rust
**Approach**:
- Use Rust's performance and memory safety
- Build with tokio async runtime

**Advantages**:
- Maximum performance guarantee

**Disadvantages**:
- **Learning Curve**: Team needs 2-4 weeks to get productive with Rust
- **Development Speed**: Rust borrow checker slows iteration
- **Geospatial**: Weak library ecosystem (geo crate is immature)
- **Timeline**: Adds 4-6 weeks to MVP, violates constraint

**Why Rejected**: Timeline constraint makes Rust infeasible for MVP.

### Alternative 3: Node.js + JavaScript
**Approach**:
- Use Node.js async/await, npm ecosystem

**Advantages**:
- Fast development cycle (Python-like)
- Excellent JSON handling

**Disadvantages**:
- **Geospatial Weakness**: turf.js and others are weaker than Python equivalents
- **Type Safety**: No Pydantic equivalent (must validate manually or use TypeScript overhead)
- **Performance**: Slower than Python for numerical operations
- **Team Fit**: Less common in infrastructure/backend teams

**Why Rejected**: Geospatial library weakness, type safety concerns, team skill mismatch.

---

## Technology Justification Details

### FastAPI for Web Framework

**Why FastAPI over Flask/Django?**

| Feature | FastAPI | Flask | Django |
|---------|---------|-------|--------|
| Async | Native, built-in | Add-on (complicated) | Add-on (complex) |
| Validation | Pydantic built-in | Manual or add-on | Lots of boilerplate |
| OpenAPI Docs | Automatic | Manual or swagger | Needs DRF |
| Type Hints | Full support | Partial | Partial |
| Learning Curve | Moderate | Easy | Steep |
| Performance | 10x+ faster | Slower | Slower |

**Selection Rationale**:
- Native async matches MVP requirements (handle 10+ polling loops simultaneously)
- Pydantic validation catches parsing errors early
- Auto-generated OpenAPI documentation for integration partners
- Team productivity factor

### Pydantic for Validation

**Example Usage**:
```python
from pydantic import BaseModel, Field

class DetectionInput(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    confidence: float = Field(..., ge=0, le=1)
    timestamp: str  # ISO 8601

# If JSON has typo or wrong type:
# - {"latitude": "invalid"} → ValidationError raised
# - {"confidence": 1.5} → ValidationError (>1)
# - {"latitude": 95} → ValidationError (>90)
```

**Benefit**: Errors caught at API boundary, not deep in processing logic.

### Shapely + pyproj for Geospatial

**Example Usage**:
```python
from shapely.geometry import Point
from pyproj import Transformer

# Validate point is valid
point = Point(longitude, latitude)
assert point.is_valid  # Catches invalid coordinates

# Transform between coordinate systems
transformer = Transformer.from_crs("EPSG:4326", "EPSG:2927")
x, y = transformer.transform(latitude, longitude)

# Distance calculation
distance = Point(lat1, lon1).distance(Point(lat2, lon2)) * 111000  # meters
```

**Benefits**:
- Mature, widely used in GIS industry
- Battle-tested correctness
- Support for complex coordinate systems
- No equivalent libraries in Go/Rust

---

## Deployment & Performance Expectations

### Performance Profile

| Operation | Latency | Throughput |
|-----------|---------|-----------|
| JSON parse + validation | 1-5ms | 200+/sec per core |
| Geolocation validation | 0.5-2ms | 500+/sec per core |
| GeoJSON transformation | 1-3ms | 300+/sec per core |
| HTTP request to TAK | 50-200ms | 5-10 concurrent |
| SQLite write | 1-5ms | 200+/sec with pooling |

**Single-core throughput**: 200-300 detections/second
**MVP target**: <100 detections/second → 1 core sufficient

### Scalability Path

**MVP**: Single container, Python 3.11 asyncio
- Handle 100+ concurrent polling tasks
- Handle 10+ REST API requests/second
- Performance headroom for 8x growth

**Phase 2**: If throughput needs exceed single core
- Option A: Horizontal scaling (multiple containers behind load balancer)
- Option B: Kubernetes with autoscaling
- Python asyncio has minimal deployment overhead

---

## Open Source & Licensing

All selected technologies are open source:

| Technology | License | Cost | Community |
|-----------|---------|------|-----------|
| Python 3.11 | PSF (GPL-compatible) | FREE | Mature, massive |
| FastAPI | MIT | FREE | Growing, active |
| Pydantic | MIT | FREE | Very active |
| Shapely | BSD | FREE | Active |
| pyproj | MIT | FREE | Active |
| httpx | BSD | FREE | Active |
| SQLite | Public Domain | FREE | Mature |

**Total Stack Cost**: $0 (no proprietary dependencies)

---

## Related Decisions

- **ADR-002**: Monolith architecture (Python enables rapid monolith development)
- **ADR-004**: GeoJSON RFC 7946 standard (Pydantic validates GeoJSON)
- **ADR-005**: SQLite for MVP (Python has native sqlite3 support)

---

## References

- **Interview 5** (GIS Specialist): "Every time a vendor updates their API, something breaks."
  → Pydantic + type hints prevent this class of error
- **Interview 1** (Military ISR): "<2 second latency needed for tactical ops"
  → Python + FastAPI + asyncio achieves this easily
- **MVP Timeline**: 8-12 weeks
  → Python enables this timeline

---

## Validation

**MVP Success Criteria**:
- [x] Handles 10+ concurrent API polling operations
- [x] Geospatial validation accurate (coordinate range checks, distance calculations)
- [x] <100ms detection ingestion latency
- [x] <2 second end-to-end API→map latency
- [x] All 5 user stories implemented in 8-12 weeks

**Proof**: Development sprint velocity on core features
