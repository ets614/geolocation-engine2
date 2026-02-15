# Opportunity Solution Tree
**Project**: AI Object Detection to COP Translation System
**Date**: 2026-02-17
**Status**: PHASE 2 - IN PROGRESS

---

## Opportunity Mapping Framework

**Root Need**: "Translate AI detection data so my team sees what's being detected in real-time with confidence"

This breaks down into discrete, testable opportunities:

---

## Level 1: Core Opportunities (Jobs-to-be-Done)

### Opportunity 1.1: Format Translation
**Customer Language**: "Every vendor outputs a different format. I need a way to accept multiple input formats and convert them to COP format."

**Who**: All segments
**Why It Matters**: Format incompatibility blocks integration entirely
**Current Workaround**: Custom ETL code per vendor
**Evidence**: 5/5 interviews
**Segment Breakdown**:
- Military/Defense: Multi-vendor UAV feeds (JSON, CSV, binary)
- Law Enforcement: AI detection API + camera registry
- Emergency Services: Multiple API endpoints + coordinate transforms
- GIS: Satellite API + drone API + aerial imagery
- Field Operators: GCS proprietary output → TAK

**Success Metric**: Integration takes <1 hour instead of 2-3 weeks
**Risk**: Flexibility vs. complexity tradeoff

---

### Opportunity 1.2: Geolocation Accuracy
**Customer Language**: "If the location is wrong by 500 meters, the whole thing fails. I spend 30 minutes per mission just validating coordinates."

**Who**: All segments (100% mention this)
**Why It Matters**: Accuracy directly impacts decision quality
**Current Workaround**: Manual spot-checking against known landmarks
**Evidence**: 5/5 interviews (highest priority across all)
**Segment Breakdown**:
- Military/Defense: UAV metadata accuracy, spot-checking workaround, 30 min/mission lost
- Law Enforcement: Camera registry lookup, 30 sec per detection × 100+ detections/day = 50+ min/day
- Emergency Services: Coordinate validation fails silently, breaks 3 days before detected
- GIS: "too imprecise for emergency response... need sub-100m accuracy"
- Field Operators: "Detections plot in the wrong location"

**Success Metric**: Sub-100m accuracy, no manual verification needed
**Risk**: Source system accuracy varies - can't fix bad input

---

### Opportunity 1.3: Confidence Score Normalization
**Customer Language**: "This system uses 0-1 confidence, but that system uses 0-100. I have to normalize them so our command team can compare."

**Who**: Segments managing multiple detection sources (Emergency Services, GIS, Military managing multi-vendor feeds)
**Why It Matters**: Enables cross-source decision-making
**Current Workaround**: Manual mapping or ignoring confidence from some sources
**Evidence**: 3 interviews explicitly mention (3, 5, 1)
**Segment Breakdown**:
- Military/Defense: Different ground stations use different scales
- Emergency Services: Satellite fire detection (unknown scale) vs. drone detection (known scale)
- GIS: Multiple vendors with different normalization approaches
- Law Enforcement: Less critical (single source)
- Field Operators: Less critical (single aircraft source)

**Success Metric**: Confidence scores from any source normalized to 0-1 scale with documented methodology
**Risk**: Requires mapping each vendor's confidence model

---

### Opportunity 1.4: Metadata Preservation and Audit Trail
**Customer Language**: "We need to log what was translated and why, for after-action reviews. We need to know if it was human-reviewed before any action was taken."

**Who**: Military/Defense (compliance), Law Enforcement (chain of custody), Emergency Services (liability)
**Why It Matters**: Operational accountability and legal compliance
**Current Workaround**: Manual logging or no audit trail
**Evidence**: 3 interviews mention (1, 2, 5)
**Segment Breakdown**:
- Military/Defense: After-action reviews, operational logs
- Law Enforcement: Chain of custody for enforcement actions
- Emergency Services: Incident documentation for post-response review
- GIS: Source tracking and update history
- Field Operators: Less critical

**Success Metric**: Every detection has immutable record of source, timestamp, confidence, and review status
**Risk**: Performance impact of comprehensive logging

---

### Opportunity 1.5: Real-Time Performance
**Customer Language**: "I need detections on the COP within seconds of them being detected, not minutes."

**Who**: Military/Defense (tactical), Emergency Services (fire detection), Field Operators
**Why It Matters**: Tactical relevance degrades with latency
**Current Workaround**: None - accept slow integration as status quo
**Evidence**: 3 interviews mention (1, 3, 4)
**Segment Breakdown**:
- Military/Defense: <2 second latency needed for tactical decisions
- Emergency Services: <5 second latency needed for dispatch
- GIS: 5+ minute batches acceptable (pull every 5 min per interview)
- Law Enforcement: 1-2 minute acceptable (daily workflows)
- Field Operators: Real-time critical

**Success Metric**: Detection to COP display latency <2 seconds
**Risk**: Network latency may be limiting factor

---

### Opportunity 1.6: System Reliability and Resilience
**Customer Language**: "If it breaks mid-mission, it breaks the whole operation. It's fragile."

**Who**: All segments (implicit in all interviews)
**Why It Matters**: Unreliable system is abandoned (20-30% failure rate currently)
**Current Workaround**: Manual fallback processes (screenshots, spreadsheets)
**Evidence**: 4 interviews explicitly mention reliability issues (1, 3, 4, 5)
**Segment Breakdown**:
- Military/Defense: 45 min workaround if system fails; mission effectiveness impacted
- Emergency Services: 3-day outage detected post-failure; critical service impacted
- GIS: Ongoing maintenance burden (4-5 hrs/week), fragile to API changes
- Law Enforcement: Falls back to manual spreadsheet
- Field Operators: Falls back to manual entry; adds 15-20 min per mission

**Success Metric**: 99% uptime, graceful degradation on failures, minimal manual fallback needed
**Risk**: Vendor API reliability is outside our control

---

### Opportunity 1.7: Ease of Integration
**Customer Language**: "There's no standard... I'm basically reinventing the wheel every time."

**Who**: Integration specialists, technical teams
**Why It Matters**: Blocks adoption of new detection sources
**Current Workaround**: Custom Python scripts, manual configuration
**Evidence**: 2 interviews from integration perspective (3, 5)
**Segment Breakdown**:
- Emergency Services: 2-3 weeks per integration specialist time
- GIS: 4-5 hours/week maintenance overhead
- Military/Defense: Junior analyst at 20% time doing ETL
- Law Enforcement: Spreadsheet + manual process
- Field Operators: Not their concern

**Success Metric**: New vendor integration in <1 day, not weeks
**Risk**: Requires pre-built adapters for common vendors

---

## Level 2: Opportunity Scoring

| Opportunity | Customer Segments | Pain Severity | Market Size | Feasibility | User Willingness to Pay | Score | Priority |
|---|---|---|---|---|---|---|---|
| 1.1 Format Translation | All 5 | CRITICAL | Large (All) | Medium | High | 9.2 | P0 |
| 1.2 Geolocation Accuracy | All 5 | CRITICAL | Large (All) | Medium | High | 9.5 | **P0** |
| 1.3 Confidence Normalization | 3 (Military, Emergency, GIS) | High | Medium | Medium | Medium | 7.8 | P1 |
| 1.4 Metadata/Audit Trail | 3 (Military, LE, Emergency) | Medium | Medium | Low | Medium | 6.5 | P2 |
| 1.5 Real-Time Performance | 3 (Military, Emergency, Ops) | High | Medium | Medium | High | 8.2 | P1 |
| 1.6 Reliability/Resilience | All 5 | CRITICAL | Large (All) | High | High | 9.8 | **P0** |
| 1.7 Ease of Integration | 2 (Integration roles) | High | Medium | Medium | High | 7.5 | P1 |

---

## Level 3: Must-Have Feature Set (P0 Only)

Based on scoring, these three opportunities are must-haves and are tightly coupled:

### MVP Feature Set
```
┌─────────────────────────────────────────────┐
│  AI Detection to COP Translation System    │
├─────────────────────────────────────────────┤
│ 1. Format Translation (P0)                 │
│    - JSON input/output                     │
│    - CSV input support                     │
│    - Configurable mapping                  │
│    - GeoJSON output for COP systems        │
│                                             │
│ 2. Geolocation Accuracy (P0)               │
│    - Attach geolocation from source        │
│    - Validate coordinate accuracy          │
│    - Support multiple coordinate systems   │
│    - Flag low-confidence locations         │
│                                             │
│ 3. Reliability/Resilience (P0)             │
│    - Error handling and logging            │
│    - Graceful degradation                  │
│    - Offline queuing and sync              │
│    - Health checks and alerting            │
│                                             │
│ Phase 2 Priority:                          │
│ 4. Real-Time Performance (P1)              │
│    - <2 second latency target              │
│    - Batch processing option               │
│    - Streaming support                     │
└─────────────────────────────────────────────┘
```

---

## Segment-Specific Opportunity Stacks

### Stack 1: Military/Defense ISR (HIGH PRIORITY)
**Segment Score**: 9.1/10
- Highest pain severity (mission critical)
- Largest budget availability
- Multi-vendor format translation needed
- Real-time performance required
- Audit trail needed
- Field integration required

**Key Opportunities**:
1. Format Translation (multi-vendor UAV feeds)
2. Geolocation Accuracy (GPS/IMU metadata)
3. Real-Time Performance (<2 sec)
4. Metadata/Audit Trail (after-action review)
5. Reliability (mission-critical operations)

**Decision Factors**:
- Must support JSON, CSV, binary formats
- Must provide sub-100m accuracy
- Must work offline and sync when connection restored
- Integration with TAK/ATAK required

---

### Stack 2: Emergency Services (HIGH PRIORITY)
**Segment Score**: 8.8/10
- High pain severity (critical service)
- Available budget for integration
- Multiple data sources (fire, flood, structural)
- Reliability is life-critical
- Ease of integration matters (integration specialist role)

**Key Opportunities**:
1. Geolocation Accuracy (sub-100m for emergency response)
2. Format Translation (satellite API, drone API, imagery)
3. Confidence Normalization (comparing multiple sources)
4. Ease of Integration (don't require 2-3 weeks per source)
5. Reliability (no 3-day outages)

**Decision Factors**:
- Must support REST APIs and batch imports
- Must handle coordinate transformation (WGS84 → state plane)
- Must normalize confidence across sources
- Integration with CAD systems required

---

### Stack 3: GIS/Geospatial (MEDIUM-HIGH PRIORITY)
**Segment Score**: 8.3/10
- High pain severity (ongoing maintenance burden)
- Multiple data sources (satellite, drone, imagery)
- Deduplication needed (not in MVP, but critical for this segment)
- Geolocation accuracy critical
- Data quality and source tracking important

**Key Opportunities**:
1. Geolocation Accuracy (sub-100m)
2. Format Translation (API → GeoJSON/ArcGIS format)
3. Confidence Normalization (comparing satellite + drone)
4. Metadata Preservation (source, timestamp, review status)
5. Ease of Integration (not spending 5 hrs/week on maintenance)

**Decision Factors**:
- Must output GeoJSON compatible with ArcGIS
- Must support satellite imagery APIs
- Must include deduplication logic (post-MVP)
- Must alert on connection failures

---

### Stack 4: Law Enforcement (MEDIUM PRIORITY)
**Segment Score**: 7.2/10
- Medium-high pain severity (scalability blocker)
- Cost-sensitive (considering hiring intern instead)
- Single source (CCTV + AI detection)
- Manual processes causing delay

**Key Opportunities**:
1. Geolocation Accuracy (camera location attachment)
2. Format Translation (AI detection output → dashboard format)
3. Ease of Integration (connect camera registry to detection system)
4. Real-Time Performance (faster than current spreadsheet process)
5. Metadata Preservation (chain of custody for enforcement)

**Decision Factors**:
- Must connect to camera registry database
- Must provide fast lookups (not 30 sec per detection)
- Cost of product must be <cost of hiring intern
- Integration with custom dashboard required

---

### Stack 5: Field Operators (MEDIUM PRIORITY)
**Segment Score**: 7.5/10
- High pain severity (mission effectiveness)
- Limited control (integration done by ground team)
- Single data source (aircraft detection)
- Reliability critical (workaround adds 15-20 min per mission)

**Key Opportunities**:
1. Reliability (system works 95%+ of the time, not 70%)
2. Real-Time Performance (detections appear instantly on COP)
3. Offline Capability (queue detections if connection drops, sync when restored)
4. Format Translation (GCS output → TAK format)

**Decision Factors**:
- Must work with TAK/ATAK
- Must handle intermittent connectivity
- Must not require pilot to troubleshoot connection issues
- Transparent to operator

---

## Level 4: Feature Prioritization for Testing (Phase 3)

### Test 1: Format Translation
**Hypothesis**: Teams can integrate a new detection source in <1 hour with our system vs. 2-3 weeks with custom code

**Test with**: Integration specialist, one new vendor format
**Success criteria**: <1 hour end-to-end integration time
**Segments to test with**: Emergency Services (Interview 3 context), Military with new vendor

### Test 2: Geolocation Accuracy
**Hypothesis**: Automated geolocation attachment + validation reduces manual coordinate checking time by 80%

**Test with**: Military ops team, emergency services GIS team
**Success criteria**: <5 min manual verification needed vs. 30 min baseline
**Segments to test with**: Military ISR (Interview 1), Emergency Services (Interview 3)

### Test 3: Real-Time Performance
**Hypothesis**: <2 second latency from detection to COP display enables faster tactical decision-making

**Test with**: Field operator, military ops team
**Success criteria**: Detections appear on COP within 2 seconds, not 5+ minutes
**Segments to test with**: Military ISR (Interview 1), Field Operators (Interview 4)

### Test 4: Confidence Normalization
**Hypothesis**: Normalized confidence scores enable analysts to compare detections across multiple sources

**Test with**: GIS specialist managing multiple sensor sources, emergency services with satellite + drone
**Success criteria**: Analysts report increased confidence in cross-source comparisons
**Segments to test with**: GIS (Interview 5), Emergency Services (Interview 3)

### Test 5: Reliability/Error Handling
**Hypothesis**: Graceful degradation + offline queuing reduces outage impact from 30% to <1%

**Test with**: Integration specialist, ops team
**Success criteria**: System continues to operate if API connection drops, queues data and syncs when restored
**Segments to test with**: Emergency Services (Interview 3), Military ISR (Interview 1)

---

## Critical Unknowns (Phase 3)

1. **Which format should we support first?** - JSON most common, but CSV also frequent
2. **How do we handle coordinate system transformation automatically?** - Need mapping library or manual config?
3. **How do we normalize confidence without vendor metadata?** - Reverse engineering approach vs. vendor integration?
4. **What's the acceptable latency for each segment?** - Military <2s, Emergency <5s, GIS 5min+?
5. **Should we build adapters for TAK/ATAK or generic COP format?** - TAK is highest priority, but flexibility matters
6. **What's the minimum viable reliability?** - 95%? 99%? 99.9%?
7. **How do we handle deduplication for GIS segment?** - Post-MVP, but need architecture for this

---

## PHASE 2 STATUS: IN PROGRESS

### Completed
- ✓ 5 customer interviews conducted
- ✓ 5 customer segments identified
- ✓ 7 core opportunities mapped
- ✓ Opportunities scored (P0, P1, P2)
- ✓ MVP feature set defined
- ✓ Segment-specific stacks created

### Next Steps (Phase 2 completion)
- [ ] Validate prioritization with 2-3 more interviews from high-priority segments (Military, Emergency)
- [ ] Test specific features (format translation, geolocation accuracy)
- [ ] Identify competitive landscape
- [ ] Score segments by market size and willingness to pay

### Phase 3 Entry Criteria
- [ ] Top 2-3 opportunities score >8
- [ ] Segment prioritization confirmed
- [ ] Solution approach defined (features to test)
- [ ] Team alignment on MVP scope
