# ADR-004: GeoJSON RFC 7946 Standard Format

**Status**: Accepted

**Date**: 2026-02-17

**Decision Makers**: Solution Architect, Product Owner

---

## Context

The system must output detection data to multiple COP platforms (TAK, ATAK, ArcGIS, CAD systems). Each platform supports different formats:
- TAK Server: Supports GeoJSON, custom TAK format, Shapefile
- ArcGIS: Supports GeoJSON, Shapefile, WFS
- CAD Systems: Varies by vendor

We must choose between:
1. **GeoJSON RFC 7946** (vendor-agnostic standard)
2. **Multiple Format Adapters** (TAK-specific, ArcGIS-specific, CAD-specific)
3. **Custom Internal Format** (proprietary, requires translation layer)

---

## Decision

**Selected**: GeoJSON RFC 7946 standard as primary output format

**Rationale**:
- **Vendor-Agnostic**: Supported by TAK, ArcGIS, CAD systems, GIS platforms
- **Standards-Based**: Official RFC, not proprietary
- **Extensible**: Can add custom properties without breaking compatibility
- **Web-Native**: Works with web mapping libraries (Leaflet, Mapbox)
- **Future-Proof**: Any new COP system will support GeoJSON

**Implementation**:
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
    "confidence": 0.92,
    "accuracy_m": 180,
    "accuracy_flag": "YELLOW",
    "timestamp": "2026-02-17T14:35:42Z",
    "sync_status": "SYNCED"
  }
}
```

---

## Rationale

### Why GeoJSON RFC 7946?

1. **Universal Compatibility**
   - TAK Server: Native GeoJSON subscription endpoint
   - ArcGIS: Can consume GeoJSON directly
   - CAD systems: Standards-compliant systems parse GeoJSON
   - Web mapping: Leaflet, Mapbox, OpenLayers all support GeoJSON
   - No vendor lock-in

2. **Standardization**
   - Official IETF RFC (RFC 7946)
   - Implemented by 100+ mapping libraries
   - Stable specification (not changing)
   - Schema validation tools widely available

3. **Extensibility**
   - Can add custom properties (detection_type, accuracy_flag, etc.)
   - No need to modify standard
   - Downstream systems can safely ignore unknown properties
   - Clear upgrade path

4. **Interoperability**
   - Multiple detection sources output normalized GeoJSON
   - Can feed into single analysis pipeline
   - Can fuse detections from different sources
   - Can replay/replay for audit/debugging

5. **Simple Implementation**
   - JSON is easy to generate (no binary encoding)
   - Standard schema enables validation
   - Pydantic can validate GeoJSON automatically

### Why NOT Custom Format?

**Approach**: Define proprietary JSON format for all detections
```json
{
  "detection_id": "abc-123",
  "location": {"lat": 32.1234, "lon": -117.5678},
  "accuracy_level": "HIGH",
  ...
}
```

**Disadvantages**:
- No tools understand the format (no validators, no visualizers)
- Each integration needs custom parser for this format
- Future format changes require coordinated updates
- Cannot easily feed into existing GIS tools
- No schema validation (must write custom validator)

**Why Rejected**: Reinvents wheel, creates new standard instead of using existing.

### Why NOT Multiple Adapters?

**Approach**: Support TAK format, ArcGIS format, CAD format independently
```python
class TakAdapter:
    def transform(detection): → TAK-specific format

class ArcGisAdapter:
    def transform(detection): → ArcGIS-specific format

class CadAdapter:
    def transform(detection): → CAD-specific format
```

**Disadvantages**:
- 3x development cost (3 adapters)
- 3x testing cost (test each format against each platform)
- Maintenance burden (if platform changes format, must update adapter)
- No single source of truth (confusion about which format is correct)
- Duplicates logic (each adapter has similar transformation rules)

**Why Rejected**: GeoJSON already works with all these platforms. Using it avoids 3x work.

---

## GeoJSON Specification Compliance

### RFC 7946 Requirements

**Required Fields**:
- `type`: "Feature" (required)
- `geometry`: Object with type and coordinates (required)
- `properties`: Object with detection metadata (optional but we use)

**Coordinate Format**: [longitude, latitude] (NOT latitude, longitude)
- This is the standard order in RFC 7946
- Matches WGS84 convention (longitude/X first, latitude/Y second)
- **Critical**: Many systems break if order is reversed

**Valid Example**:
```json
{
  "type": "Feature",
  "geometry": {
    "type": "Point",
    "coordinates": [-117.5678, 32.1234]  # [lon, lat]
  },
  "properties": {
    "source": "satellite",
    "confidence": 0.92
  }
}
```

**Invalid Example** (WRONG coordinate order):
```json
{
  "type": "Feature",
  "geometry": {
    "type": "Point",
    "coordinates": [32.1234, -117.5678]  # WRONG! [lat, lon]
  }
}
```

### Validation

Use standard GeoJSON validation tools:
```python
from geojson import validate
from jsonschema import validate as json_validate

geojson_schema = {...}  # RFC 7946 schema
validate(json_validate(feature, geojson_schema))
```

Pydantic model with strict validation:
```python
from pydantic import BaseModel

class GeoJSONPoint(BaseModel):
    type: Literal["Point"]
    coordinates: tuple[float, float]  # [lon, lat]

    @field_validator('coordinates')
    def validate_coordinates(cls, v):
        lon, lat = v
        if not (-180 <= lon <= 180):
            raise ValueError(f"longitude out of range: {lon}")
        if not (-90 <= lat <= 90):
            raise ValueError(f"latitude out of range: {lat}")
        return v
```

---

## Extended Properties

**Beyond RFC 7946 Core**:

```json
{
  "type": "Feature",
  "id": "detection-abc-123",
  "geometry": {...},
  "properties": {
    "source": "satellite_fire_api",  # Our addition
    "source_id": "sat_1",            # Our addition
    "detection_type": "fire",        # Our addition
    "confidence": 0.92,              # Our addition
    "confidence_original": {         # Our addition
      "value": 92,
      "scale": "0-100"
    },
    "accuracy_m": 180,               # Our addition
    "accuracy_flag": "YELLOW",       # Our addition (GREEN/YELLOW/RED)
    "timestamp": "2026-02-17T14:35:42Z",  # Our addition (ISO 8601)
    "received_timestamp": "2026-02-17T14:35:43Z",  # Our addition
    "sync_status": "SYNCED",         # Our addition
    "operator_verified": true,       # Our addition
    "operator_notes": "..."          # Our addition
  }
}
```

**Design Principle**: Extend with custom properties, don't modify core structure.

**Downstream Systems**:
- TAK Server: Parses geometry, can use any properties in rule engine
- ArcGIS: Parses geometry, displays all properties in feature inspector
- Web Map: Geometry used for marker position, properties shown in popup
- Future Platform X: Can consume our GeoJSON without changes

---

## Integration Point Examples

### TAK Server Integration

**Endpoint**:
```
PUT /api/takmaps/version/capabilities/search/geo/takserver/geojson/json
```

**Request**:
```json
{
  "type": "Feature",
  "geometry": {
    "type": "Point",
    "coordinates": [-117.5678, 32.1234]
  },
  "properties": {
    "source": "satellite",
    "confidence": 0.92,
    "accuracy_flag": "YELLOW"
  }
}
```

**TAK Response**: Marker appears on map with properties visible in properties panel.

### ArcGIS Integration

**Endpoint**: GeoJSON Layer (add to ArcGIS Feature Service)

**Request**: Same GeoJSON Feature

**ArcGIS Response**: Feature added to layer, visible on map, all properties queryable.

### Web Mapping Integration

**Leaflet Example**:
```javascript
const feature = {
  type: "Feature",
  geometry: { type: "Point", coordinates: [-117.5678, 32.1234] },
  properties: { source: "satellite", confidence: 0.92 }
};

const marker = L.geoJSON(feature).addTo(map);
// Automatically creates marker at coordinates, can bind popup with properties
```

---

## Alternative Output Formats (Future, Phase 2)

**If new requirements demand**:
- **GeoServer WFS** (OGC standard): Can export from GeoJSON
- **OGC GeoPackage**: SQLite-based geo format: Can export from GeoJSON
- **Shapefile**: Legacy format: Can export from GeoJSON (via shapely)
- **KML**: Google Earth format: Can export from GeoJSON
- **TopoJSON**: Topology format: Can export from GeoJSON

**Advantage**: All can be generated from GeoJSON. No need to store multiple formats.

---

## Schema Validation & Documentation

**OpenAPI/Swagger Schema**:
```yaml
DetectionGeoJSON:
  type: object
  required:
    - type
    - geometry
  properties:
    type:
      type: string
      enum: ["Feature"]
    id:
      type: string
    geometry:
      type: object
      required:
        - type
        - coordinates
      properties:
        type:
          type: string
          enum: ["Point"]
        coordinates:
          type: array
          items:
            - type: number  # longitude
            - type: number  # latitude
    properties:
      type: object
      additionalProperties: true  # Allow any custom properties
```

**API Documentation** (auto-generated by FastAPI):
- Visit `http://localhost:8000/docs` (Swagger UI)
- Automatically shows GeoJSON schema
- Can test endpoints directly

---

## Related Decisions

- **ADR-003**: Python/FastAPI (Pydantic validates GeoJSON)
- **ADR-005**: SQLite for MVP (stores GeoJSON in JSONB-like field)

---

## References

- **RFC 7946**: https://tools.ietf.org/html/rfc7946
- **Interview 1** (Military ISR): TAK Server integration requirement
- **Interview 3** (Emergency Services): ArcGIS integration requirement
- **Interview 5** (GIS Specialist): "Need standard format for GIS systems"

---

## Validation

**MVP Success Criteria**:
- [x] Output valid GeoJSON (RFC 7946 compliant)
- [x] TAK Server accepts and displays GeoJSON
- [x] ArcGIS can consume GeoJSON output
- [x] All detection metadata preserved in properties
- [x] Schema validates with standard validators
- [x] OpenAPI documentation auto-generated

**Proof**: Integration testing with real TAK Server, validation with GeoJSON linters
