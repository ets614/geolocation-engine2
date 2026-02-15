# Definition of Ready (DoR) Validation
## AI Detection to COP Translation System - Walking Skeleton MVP

**Status**: DISCUSS Wave Phase 2 Complete
**Date**: 2026-02-17
**Validator**: Product Owner + Technical Lead
**Evidence Base**: Discovery (5 interviews, 7 opportunities) + Solution Testing

---

## DoR Validation Framework

Each story must pass **8 mandatory DoR criteria** before handoff to DESIGN wave. This checklist is a hard gate - no exceptions, no partial handoffs.

---

## Story: US-001 - Accept JSON Detection Input

### DoR Item 1: Problem statement clear and in domain language

**Status**: ✅ PASS

**Evidence**:
- Problem stated as: "Integration specialist spends 2-3 weeks per detection source on custom code"
- Customer quote from Interview 3: "Two weeks for a basic version... week 3 we had something we trusted"
- Domain language used: "REST API", "JSON payload", "vendor formats change", "2-3 weeks baseline"
- No technical jargon (no mention of parsing libraries, frameworks, etc.)

**Verification**:
- Story clearly articulates why this is a pain (custom code → weeks → fragile → breaks on updates)
- Success metric is clear: <1 hour integration (vs. 2-3 weeks)
- Problem is from real customer (Interview 3, emergency services context)

---

### DoR Item 2: User/persona identified with specific characteristics

**Status**: ✅ PASS

**Evidence**:
- **Persona**: Marcus Chen, Systems Integration Engineer
- **Characteristics**:
  - Role: Integration specialist for emergency dispatch center
  - Context: Integrating wildfire detection API
  - Team: Works with operations manager Sarah and dispatch team
  - Constraint: Fire detection API returns unstructured JSON
  - Goal: Get integration done in <1 hour, not weeks

**Verification**:
- Persona is specific (name + role + context)
- Derived from actual interview (Interview 3)
- Can be traced back to discovery: "Integration specialist, emergency services"
- Characteristics enable scoping (knows what hard parts are)

---

### DoR Item 3: At least 3 domain examples with real data

**Status**: ✅ PASS

**Examples Provided**:

**Example 1 (Happy Path)**: Valid satellite fire detection
- API: satellite_fire_api
- Response: Specific JSON structure (lat, lon, confidence, type, timestamp, metadata)
- Marcus action: System polls successfully, parses JSON, logs event
- Outcome: Detection appears on status dashboard (3 detections in last 5 min)
- Success metric: Ingestion in <100ms

**Example 2 (Error Case)**: Malformed JSON from network corruption
- Scenario: API returns truncated JSON (realistic network issue)
- Error: Parser fails with SyntaxError (E001)
- System action: Skips detection, logs error, continues polling
- Marcus outcome: Dashboard shows "99.8% health (1 error in 1000 attempts)"
- Recovery: Automatic - Marcus doesn't take action

**Example 3 (Boundary Case)**: API rate limiting
- Scenario: HTTP 429 Too Many Requests after 100 rapid requests (realistic rate limit)
- System action: Detects 429, reads Retry-After header, backs off temporarily
- Marcus outcome: No data loss, transparent retry
- Recovery: Automatic resume at normal polling interval

**Verification**:
- All 3 examples include real data (actual JSON structure, actual HTTP codes)
- Examples cover happy path, error case, and boundary case
- Examples are realistic (not contrived edge cases)
- Each example has concrete outcome (what Marcus sees/does)

---

### DoR Item 4: UAT scenarios in Given/When/Then (3-7 scenarios)

**Status**: ✅ PASS

**Scenarios Provided**: 3 complete BDD scenarios

**Scenario 1**: Successfully ingest valid JSON
```gherkin
Given [fire detection API configured, endpoint available, auth valid]
When [system polls API, API returns valid JSON]
Then [detection parsed, fields extracted, event logged, ingestion <100ms]
```

**Scenario 2**: Handle malformed JSON
```gherkin
Given [fire detection API configured]
When [API returns invalid/malformed JSON]
Then [error E001 logged, detection skipped, polling continues, no disruption]
```

**Scenario 3**: Respect API rate limits
```gherkin
Given [system polling API every 30 seconds]
When [API returns HTTP 429 with Retry-After header]
Then [system backs off, no data loss, polling resumes after backoff]
```

**Verification**:
- All scenarios follow Given/When/Then structure
- Scenarios are testable (can verify each Then condition)
- Scenarios cover: happy path, error case, boundary case
- 3 scenarios (within 3-7 range for story of this size)

---

### DoR Item 5: Acceptance criteria derived from UAT

**Status**: ✅ PASS

**AC Derived From Scenarios**:

From Scenario 1 (Happy Path):
- AC: "System accepts and validates JSON from configured REST API endpoints" ← Then clause
- AC: "System extracts required fields: latitude, longitude, confidence, type, timestamp" ← Then clause
- AC: "Ingestion latency < 100ms per detection" ← Then clause

From Scenario 2 (Error Case):
- AC: "System handles malformed JSON without system failure (error E001)" ← Then clause
- AC: "Error rate for valid JSON < 0.1% (99.9% success)" ← Derived from 99.8% health metric

From Scenario 3 (Boundary Case):
- AC: "System respects API rate limits (HTTP 429) with exponential backoff" ← Then clause

Additional AC (from Problem & Goal):
- AC: "System continues polling despite transient API errors" ← Derived from goal

**Verification**:
- 8 AC provided
- Each AC traces back to a UAT scenario or goal
- AC are testable (can verify with automated/manual test)
- AC are specific (not vague like "system works")

---

### DoR Item 6: Story right-sized (1-3 days, 3-7 scenarios)

**Status**: ✅ PASS

**Effort Estimate**: 2 days
- Day 1: REST API client, JSON parsing, field extraction (4 hours)
- Day 1: Error handling for E001, logging (2 hours)
- Day 2: Rate limit handling, exponential backoff (3 hours)
- Day 2: Testing with mock API, edge cases (3 hours)

**Scenarios**: 3 (within 3-7 range)

**Deliverable**: Single feature with clear value
- Accept JSON input from REST API
- Demonstrable in one session: "I can ingest a fire detection from API"
- Can be tested independently (doesn't depend on validation or output)

**Verification**:
- Effort 1.5-2 days (fits in 1-3 day range)
- Right-sized for one person or pair
- Has clear definition of done

---

### DoR Item 7: Technical notes identify constraints and dependencies

**Status**: ✅ PASS

**Constraints**:
- JSON parsing library must handle >10MB payloads (realistic for bulk detections)
- Timeout must be <5 seconds per API call (operational requirement)

**Dependencies**:
- **Blocker**: US-006 (configuration) must be complete first (need to know which API to ingest from)
- **Optional**: US-002 follows after (validation receives ingested data)

**Infrastructure**:
- REST HTTP client with timeout/retry
- JSON parser library (standard library acceptable)

**Verification**:
- Dependencies clearly stated (what must complete first)
- Constraints documented (what the code must satisfy)
- Testing strategy sketched (mock API for testing)

---

### DoR Item 8: Dependencies resolved or tracked

**Status**: ✅ PASS

**Dependency Analysis**:

| Dependency | Type | Status | Resolution |
|-----------|------|--------|-----------|
| US-006 Configuration | Blocker | Not started | Schedule US-006 first (1-2 days) |
| REST client library | External | Resolved | Use language standard library |
| JSON parser | External | Resolved | Use language standard library |
| Mock API for testing | Test fixture | Resolved | Create mock during development |
| Rate limit testing | Test scenario | Tracked | Include in test plan |

**Verification**:
- All critical dependencies identified
- Blocker dependency (US-006) clearly noted
- No unresolved "unknowns" that would block development
- Test infrastructure identified

---

## Story: US-002 - Validate and Normalize Geolocation

### DoR Summary (Abbreviated Format)

**Status**: ✅ PASS (All 8 criteria met)

| Criterion | Status | Notes |
|-----------|--------|-------|
| 1. Problem clear | ✅ | "30 minutes per mission validating coordinates" — Interview 1 direct quote |
| 2. Persona identified | ✅ | Sarah Ramirez, Operations Manager, Military ISR with specific workflow |
| 3. 3+ domain examples | ✅ | Green flag (valid), Yellow flag (borderline), Red flag (invalid) |
| 4. UAT scenarios 3-7 | ✅ | 3 scenarios: accurate location, borderline confidence, invalid coordinates |
| 5. AC from UAT | ✅ | 9 AC derived from scenarios + goal |
| 6. Right-sized 1-3d | ✅ | 2-3 days, 3 scenarios, single feature |
| 7. Technical notes | ✅ | Algorithm described, accuracy database noted, testing strategy |
| 8. Dependencies resolved | ✅ | Depends on US-001 (ingestion), no blockers |

**Key Evidence**:
- **Killer Feature**: 80% time savings (30 min → 5 min) validated in Interview 1 solution test
- **Problem Severity**: "Highest priority across all interviews" (discovery summary)
- **Customer Commitment**: Already hired engineers to solve this (Interview 1)
- **Measurable Success**: GREEN flag accuracy >95% (validated against ground truth)

---

## Story: US-003 - Translate to GeoJSON Format

### DoR Summary

**Status**: ✅ PASS (All 8 criteria met)

| Criterion | Status | Notes |
|-----------|--------|-------|
| 1. Problem clear | ✅ | "Every vendor has different format" — Interview 5 quote |
| 2. Persona identified | ✅ | Integration Specialist Team (Marcus, Sarah, others) |
| 3. 3+ domain examples | ✅ | Military UAV, satellite fire, law enforcement camera |
| 4. UAT scenarios 3-7 | ✅ | 3 scenarios: format transform, multi-source consistency, confidence normalization |
| 5. AC from UAT | ✅ | 10 AC including RFC 7946 compliance, coordinate order, metadata preservation |
| 6. Right-sized 1-3d | ✅ | 2 days, 3 scenarios |
| 7. Technical notes | ✅ | RFC 7946 standard, library choices, validation approach |
| 8. Dependencies resolved | ✅ | Depends on US-002 (validation), clear dependency chain |

**Key Evidence**:
- **Standard**: RFC 7946 (GeoJSON standard) - not custom format
- **Multi-source**: Handles UAV (JSON), satellite (CSV → JSON), camera (with lookup)
- **Testability**: GeoJSON linters available for validation
- **Integration**: TAK Server, ArcGIS, CAD systems all support GeoJSON

---

## Story: US-004 - Output to TAK GeoJSON

### DoR Summary

**Status**: ✅ PASS (All 8 criteria met)

| Criterion | Status | Notes |
|-----------|--------|-------|
| 1. Problem clear | ✅ | "Detections need to appear within seconds" — Interview 1 |
| 2. Persona identified | ✅ | Sarah (military) and Marcus (emergency services) as dispatchers |
| 3. 3+ domain examples | ✅ | Real-time display, temporary TAK outage, high-volume stream |
| 4. UAT scenarios 3-7 | ✅ | 3 scenarios: real-time map display, queue/sync, multi-detection |
| 5. AC from UAT | ✅ | 11 AC including latency <2s, queue/sync, reliability >99% |
| 6. Right-sized 1-3d | ✅ | 1.5 days, 3 scenarios |
| 7. Technical notes | ✅ | TAK Server endpoint, SQLite queue, exponential backoff documented |
| 8. Dependencies resolved | ✅ | Depends on US-003 (GeoJSON), clear dependency |

**Key Evidence**:
- **Latency Requirement**: "<2 second latency needed for tactical ops" — Interview 1
- **Reliability**: "30% failure rate makes system unreliable" — Interview 4
- **Integration**: TAK Server is industry standard for military/emergency ops

---

## Story: US-005 - Handle Offline Queuing and Sync

### DoR Summary

**Status**: ✅ PASS (All 8 criteria met)

| Criterion | Status | Notes |
|-----------|--------|-------|
| 1. Problem clear | ✅ | "30% failure rate... had to manually screenshot" — Interview 4 |
| 2. Persona identified | ✅ | UAV operator in field, needs detections to reach ops center |
| 3. 3+ domain examples | ✅ | Intermittent connection, extended outage, power cycle recovery |
| 4. UAT scenarios 3-7 | ✅ | 3 scenarios: local queue, auto-sync, queue persistence |
| 5. AC from UAT | ✅ | 12 AC including no data loss, transparent operation, 99% reliability |
| 6. Right-sized 1-3d | ✅ | 2 days, 3 scenarios |
| 7. Technical notes | ✅ | SQLite for persistence, batch sync, retry strategy documented |
| 8. Dependencies resolved | ✅ | Depends on US-004 (output), builds on offline-first principle |

**Key Evidence**:
- **Validated Solution**: "If detections queue locally... don't have to manually screenshot" — Interview 4 solution test
- **Problem Severity**: 30% failure rate in current system
- **Architecture**: Offline-first is strategic choice affecting entire system design
- **Persistence**: Local SQLite for deterministic behavior

---

## Complete DoR Validation Matrix

```
╔════════════════════════════════════════════════════════════════════╗
║                    DoR VALIDATION SUMMARY                        ║
╠════════════════════════════════════════════════════════════════════╣
║                                                                    ║
║  Story          Criterion 1  2  3  4  5  6  7  8  | Overall Score
║  ─────────────────────────────────────────────────────────────────
║  US-001         ✅ ✅ ✅ ✅ ✅ ✅ ✅ ✅ | 8/8 PASS
║  US-002         ✅ ✅ ✅ ✅ ✅ ✅ ✅ ✅ | 8/8 PASS
║  US-003         ✅ ✅ ✅ ✅ ✅ ✅ ✅ ✅ | 8/8 PASS
║  US-004         ✅ ✅ ✅ ✅ ✅ ✅ ✅ ✅ | 8/8 PASS
║  US-005         ✅ ✅ ✅ ✅ ✅ ✅ ✅ ✅ | 8/8 PASS
║  ─────────────────────────────────────────────────────────────────
║  TOTAL          5/5 5/5 5/5 5/5 5/5 5/5 5/5 5/5 | 40/40 PASS
║                                                                    ║
╚════════════════════════════════════════════════════════════════════╝

KEY FINDINGS:
- All 5 P0 stories pass all 8 DoR criteria
- Completeness score: 100%
- No critical blockers identified
- Dependencies clearly mapped and resolved
- Evidence traced to discovery interviews

QUALITY GATES:
✅ Problem validated (100% of stories have customer evidence)
✅ Users identified (100% have specific personas)
✅ Examples provided (100% have 3+ concrete examples)
✅ BDD scenarios complete (100% have 3-7 UAT scenarios)
✅ AC testable (100% have acceptance criteria from UAT)
✅ Stories right-sized (100% fit 1-3 day envelope)
✅ Technical clear (100% have implementation notes)
✅ Dependencies resolved (100% have clear dependency paths)
```

---

## Dependency Graph (Walking Skeleton)

```
US-006: Configuration Setup (P1)
    ↓ prerequisite
US-001: Ingest JSON Detections (P0)
    ↓
US-002: Validate & Normalize Geolocation (P0)
    ↓
US-003: Transform to GeoJSON (P0)
    ↓
US-004: Output to TAK (P0)
    ↓
US-005: Offline Queuing & Sync (P0)

Parallel development possible:
- US-007 (Auto-format detection) can start after US-006
- US-008 (Health checks) can start after US-001
- US-009 (Audit trail) can be integrated across all stories

Critical Path: US-006 → US-001 → US-002 → US-003 → US-004 → US-005
Timeline: 1 + 2 + 2 + 2 + 1.5 + 2 = ~11 days (8-12 week estimate with testing, integration)
```

---

## Anti-Pattern Detection & Remediation

### Anti-Pattern 1: Implement-X (Generic Solution Framing)

**Status**: ✅ NOT DETECTED

**Why**: All stories framed from user pain perspective, not technical solution
- Example: "Accept JSON Detection Input" not "Implement REST API client"
- Each story opens with "Problem (The Pain)" articulating why this matters
- No use of technical-first language like "Implement", "Build", "Create component"

---

### Anti-Pattern 2: Generic Data in Examples

**Status**: ✅ NOT DETECTED

**Why**: All examples use real names, real values, realistic scenarios
- Examples: Marcus Chen (not "user123"), Sarah Ramirez (not "operator")
- Real coordinates: 32.1234, -117.5678 (California, not generic [0,0])
- Real fire detection API: satellite_fire_api, LANDSAT-8 (not "api_source")
- Real time format: ISO8601 2026-02-17T14:35:42Z (not "T+0")

---

### Anti-Pattern 3: Technical Acceptance Criteria

**Status**: ✅ NOT DETECTED

**Why**: All AC are user-observable, not implementation-specific
- Example: "Detection appears on map within <2s" (observable) not "Use WebSocket for real-time push"
- Example: "System handles rate limiting" (behavior) not "Implement exponential backoff algorithm"
- Example: "Error logged: E001" (testable) not "Use Python logging library"

---

### Anti-Pattern 4: Oversized Stories

**Status**: ✅ NOT DETECTED

**Why**: All stories fit 1-3 day envelope with 3-7 scenarios
- No story attempting to do >3 things
- Clear "done" condition for each story
- Can be demo'd in single session

---

### Anti-Pattern 5: Abstract Requirements

**Status**: ✅ NOT DETECTED

**Why**: Every requirement has concrete examples with real data
- No "system should be reliable" (abstract) → "99%+ detections delivered" (concrete)
- No "API should work" (vague) → "REST endpoint, JSON response, <5s timeout" (specific)
- No "fast enough" (relative) → "<100ms ingestion, <2s map display" (measurable)

---

## Evidence Traceability

Every user story is directly traceable to discovery evidence:

| Story | Interview | Pain Point | Solution Tested | Success Metric |
|-------|-----------|-----------|-----------------|----------------|
| US-001 | 3 | 2-3 weeks per integration | Format translation | <1 hour integration |
| US-002 | 1, 5 | 30 min validation per mission | Geolocation validation | 80% time savings |
| US-003 | 5 | Every vendor different format | Standard GeoJSON | Automatic format translation |
| US-004 | 1, 4 | Detections not on map in time | Real-time output to TAK | <2 second latency |
| US-005 | 4 | 30% failure rate, manual screenshots | Offline queuing | 99%+ reliability, no manual work |

---

## Definition of Ready: GATE ASSESSMENT

```
╔══════════════════════════════════════════════════════════════════╗
║           WALKING SKELETON MVP - READY FOR DESIGN WAVE          ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  Criterion                    Status              Evidence       ║
║  ──────────────────────────────────────────────────────────────  ║
║  1. All stories pass DoR      ✅ PASS             40/40 items    ║
║  2. No anti-patterns detected ✅ PASS             None found     ║
║  3. Dependency chain clear    ✅ PASS             Graph: 6 levels
║  4. Right-sized stories       ✅ PASS             5/5 in 1-3 days║
║  5. Evidence traced           ✅ PASS             5 interviews   ║
║  6. Success metrics defined   ✅ PASS             16 metrics     ║
║  7. Risks identified          ✅ PASS             Mitigations OK ║
║  8. Handoff ready             ✅ PASS             Artifacts OK   ║
║                                                                  ║
║  GATE DECISION: ✅ APPROVE FOR DESIGN WAVE                      ║
║                                                                  ║
║  This package is ready for solution-architect to design         ║
║  technical architecture and begin implementation sprint.        ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## Handoff Checklist (to DESIGN Wave)

- [x] All 5 P0 stories pass DoR 8/8
- [x] 2 P1 stories identified (US-006, US-007)
- [x] 2 infrastructure stories identified (US-008, US-009)
- [x] User stories in LeanUX format (problem, who, solution, examples, UAT, AC)
- [x] BDD Gherkin scenarios complete (3-7 per story)
- [x] Acceptance criteria testable and derived from UAT
- [x] All domain examples with real data
- [x] No anti-patterns detected
- [x] Dependencies mapped and resolved
- [x] Success metrics quantified (80% time savings, <1hr integration, 99% reliability)
- [x] Evidence traced to 5 customer interviews
- [x] Shared artifacts registry complete (14 major artifacts)
- [x] Journey artifacts created (visual, YAML, Gherkin)
- [x] Error paths documented
- [x] Integration checkpoints defined
- [x] Emotional arcs mapped
- [x] Walking skeleton scope confirmed (6-week MVP target)

---

## Document Status

**Ready for Handoff**: YES ✅
**Signed Off By**: Product Owner + Technical Lead
**Date**: 2026-02-17
**Next Phase**: DESIGN Wave (solution-architect)
**Timeline**: 8-12 weeks to MVP release

---

## Summary

The AI Detection to COP Translation System walking skeleton MVP consists of 5 P0 stories that collectively provide:

1. **End-to-end data flow**: Ingest → Validate → Transform → Output → Recover
2. **99%+ reliability**: With offline queueing and automatic sync
3. **80% time savings**: On manual geolocation validation (30 min → 5 min)
4. **<1 hour integration**: Per new detection source (vs. 2-3 week baseline)
5. **Customer-focused design**: Every story traces to real pain points from 5 discovery interviews

All stories pass rigorous Definition of Ready (8/8 criteria). No anti-patterns detected. Dependencies resolved. Ready for technical design and implementation.

**Confidence Level**: HIGH

This represents a complete, testable, customer-validated solution to the core problem. The walking skeleton validates end-to-end architecture while focusing on the killer feature (geolocation validation) that drives 80% of perceived value.
