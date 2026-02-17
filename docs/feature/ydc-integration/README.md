# YDC ↔ Geolocation-Engine2 Adapter - Design Deliverables

**Architecture Design Complete - Ready for DISTILL Wave**

**Date**: 2026-02-17
**Architect**: Morgan (Solution Architect)
**Status**: Design phase complete; awaiting peer review and software crafter implementation

---

## 📋 What Was Designed

A **hexagonal microservice architecture** for integrating YOLO object detection (YDC) with the Geolocation-Engine2 photogrammetry system.

```
YDC (YOLO detections)
  ↓ WebSocket
YDC Adapter (this design)
  ├─ Extract pixel center from bbox
  ├─ Fetch camera position (pluggable: Mock, DJI, MAVLink)
  └─ Call Geolocation-Engine2 API
     ↓ HTTP REST
     Geolocation-Engine2
     ├─ Photogrammetry → GPS coords
     ├─ CoT XML generation
     ├─ TAK server push (async)
     └─ Offline queue (resilience)
```

**Result**: Real-world geolocation for tactical systems in <200ms latency

---

## 📚 Deliverable Documents

### 1. **architecture-design.md** (Primary Design Document)
**Length**: ~8,000 words | **Sections**: 18

Complete system design with:
- System context and business capabilities (Section 1)
- Hexagonal architecture layers (Section 2)
- Component boundaries and responsibilities (Section 2-3)
- Technology stack with rationale (Section 3)
- Data models and API contracts (Section 4)
- Integration with Geolocation-Engine2 (Section 5)
- Error handling strategies (Section 6)
- Extension points for camera providers (Section 7)
- C4 diagrams (System, Container, Component) (Section 8)
- Data flow diagrams (happy path, error paths) (Section 9)
- Scalability considerations (Section 10)
- Testing strategy (Section 11)
- Deployment architecture (Section 12)
- Quality attributes strategy (Section 13)
- ADRs for major decisions (Section 14)
- Risk assessment (Section 15)
- Success criteria (Section 16)
- Handoff to acceptance designer (Section 17)
- Glossary (Section 18)

**For**: Software crafter (sections 2-7), acceptance designer (sections 10-13), DevOps (section 12)

---

### 2. **HANDOFF.md** (Executive Summary for Acceptance Designer)
**Length**: ~2,000 words | **Key Sections**: Quick start, integration points, acceptance criteria

Condensed handoff package with:
- Quick architecture summary
- Critical integration points (WebSocket protocol, REST API, camera provider interface)
- Component boundaries for software crafter
- Acceptance criteria (functional & non-functional)
- Test strategy
- Deployment setup instructions
- Known risks & mitigations
- Phase roadmap
- Questions for acceptance designer

**For**: Acceptance designer, software crafter, project manager

---

### 3. **ARCHITECTURE_SUMMARY.md** (Visual Quick Reference)
**Length**: ~1,500 words | **Format**: ASCII diagrams + tables

Visual reference showing:
- System context diagram
- Hexagonal architecture layers with component responsibilities
- Data flow (happy path and error paths)
- Component responsibility matrix
- Integration points summary
- Error handling flowchart
- Deployment architecture options
- Quality attributes targets
- File structure template
- Success criteria checklist

**For**: Quick visual reference, architecture reviews, stakeholder alignment

---

### 4. **DESIGN_DECISIONS_MATRIX.md** (Decision Rationale)
**Length**: ~2,000 words | **Format**: Structured tables

All 14 major design decisions with:
- What was decided
- Why (rationale)
- Alternatives rejected (with impact analysis)
- Trade-offs accepted
- Future decisions (Phase 2+)
- Technology stack rationale table
- Retry policy table

**For**: Understanding "why" behind design; architectural reviews; future changes

---

### 5. **ADR-001-hexagonal-architecture.md** (Architecture Decision Record)
**Length**: ~1,000 words

**Decision**: Use hexagonal architecture (ports & adapters)

**Covers**:
- Context (multiple variable I/O sources)
- Decision rationale
- Architecture diagram
- Why layered/event-driven/monolithic rejected
- Consequences (positive & negative)
- Implementation notes (file structure, dependency injection)
- Testing strategy
- Validation criteria

**References**: Alistair Cockburn, Robert C. Martin

---

### 6. **ADR-002-separate-service.md** (Separation Decision Record)
**Length**: ~1,200 words

**Decision**: Build separate microservice (not embedded in Geolocation-Engine2)

**Covers**:
- Context (two integration approaches)
- Decision rationale (7 reasons)
- Why embedded/message-queue/sidecar rejected
- Consequences (positive & negative with mitigations)
- Implementation plan (Phase 1, 2, 3)
- Deployment diagrams (local dev, production, Kubernetes)
- Validation criteria

**References**: Sam Newman, Martin Fowler

---

## 🎯 For Each Role

### Software Crafter (BUILD Wave)
**Start with**:
1. `HANDOFF.md` Section "Component Boundaries"
2. `architecture-design.md` Sections 2-7 (architecture, components, data models)
3. `ARCHITECTURE_SUMMARY.md` (visual reference while coding)

**Then implement**:
- Domain layer (pure functions, no I/O)
- Orchestration services (state machine, error recovery)
- Adapters (WebSocket, HTTP, camera providers, logging)
- Tests (unit, service, integration, load)

**Success**: All 95+ tests passing, <150ms p50 latency

---

### Acceptance Designer (DISTILL Wave)
**Start with**:
1. `HANDOFF.md` Section "Acceptance Criteria"
2. `architecture-design.md` Section 13 (Quality Attributes)
3. `ARCHITECTURE_SUMMARY.md` (visual reference)

**Then write**:
- BDD test scenarios (Gherkin format)
- Performance/reliability acceptance tests
- Integration tests (YDC Adapter + Geolocation-Engine2)
- Sign-off on quality attributes

**Success**: All acceptance tests passing, architecture validated

---

### DevOps/Infrastructure
**Start with**:
1. `architecture-design.md` Section 12 (Deployment)
2. `HANDOFF.md` Section "Deployment & Environment Setup"
3. `ARCHITECTURE_SUMMARY.md` "Deployment Architecture"

**Then build**:
- Docker image (Dockerfile provided in architecture doc)
- docker-compose.yml (local dev setup)
- Kubernetes manifests (Phase 2+)
- Monitoring/alerting setup

**Success**: Single `docker-compose up` starts full stack locally

---

### Peer Reviewer (Atlas)
**Review checklist**:
1. Bias detection (read `DESIGN_DECISIONS_MATRIX.md`)
2. ADR quality (read `ADR-001` and `ADR-002`)
3. Completeness (ensure all 14 decisions documented)
4. Feasibility (can team implement in 8-12 weeks?)
5. Alignment (consistent with Geolocation-Engine2 patterns?)

**Approval criteria**:
- [ ] No critical issues
- [ ] At least 2 alternatives considered per decision
- [ ] Team capable of execution
- [ ] Quality attributes addressed
- [ ] Risk mitigations credible

**Expected review time**: 3-5 working days

---

## 📊 Architecture at a Glance

### Style: Hexagonal (Ports & Adapters)
- **Domain Layer**: Pure business logic (no I/O) — testable in isolation
- **Orchestration**: State machine, error recovery, observability
- **Adapters**: WebSocket listener, HTTP client, camera providers, logging

### Technology Stack
- **Language**: Python 3.11
- **Framework**: FastAPI (async native)
- **Database**: None (adapter is stateless)
- **Container**: Docker (docker-compose for local dev)
- **Cost**: $0 (all open source)

### Key Decisions
1. ✅ Hexagonal (pluggable providers, testable)
2. ✅ Separate service (independent deployment, scaling)
3. ✅ Sync REST (low latency, clear errors)
4. ✅ Mock provider Phase 1 (DJI/MAVLink Phase 2)
5. ✅ Stateless adapter (horizontal scalability)

### Performance Targets
- **Latency**: p50 <150ms, p99 <300ms (frame → response)
- **Throughput**: 100+ detections/sec (single instance)
- **Memory**: <500MB resident
- **Uptime**: 99.5% (during TAK online window)

### Test Coverage
- **Domain**: 95%+ (pure functions)
- **Services**: 90%+ (mocked adapters)
- **Adapters**: 85%+ (mocked backends)
- **Overall**: ~85-90% (~95 tests)

---

## 🚀 Implementation Timeline (Informational)

### Phase 1: MVP (Weeks 1-8, This Design)
- [x] Architecture designed ← **YOU ARE HERE**
- [ ] Domain layer implementation (crafter)
- [ ] Orchestration services (crafter)
- [ ] Mock camera provider (crafter)
- [ ] HTTP Geolocation adapter (crafter)
- [ ] 95 tests (crafter + acceptance designer)
- [ ] Docker image + docker-compose (DevOps)
- [ ] UAT with mock Geolocation-Engine2 (acceptance designer)

### Phase 2: Scale Ready (Weeks 9-16)
- [ ] DJI provider (if hardware available)
- [ ] MAVLink provider (if ArduPilot adopted)
- [ ] PostgreSQL migration (if needed)
- [ ] Kubernetes deployment (if scaling beyond 1 instance)

### Phase 3+: Enhancement (Q3+ 2026)
- [ ] Multi-region deployment
- [ ] Service mesh integration
- [ ] Alternative geolocation backends

---

## ❓ Questions to Resolve Before BUILD Phase

For **Software Crafter**:
- [ ] Python dev environment ready? (3.11+, poetry/pip)
- [ ] FastAPI experience level? (We'll provide examples)
- [ ] Async/await comfort? (asyncio patterns documented)

For **Acceptance Designer**:
- [ ] BDD framework preference? (behave, robot framework, pytest-bdd?)
- [ ] Test data available? (mock vs real YDC frames)
- [ ] Performance SLA adjustable? (assume <150ms p50)

For **DevOps**:
- [ ] Docker registry configured? (ECR, Docker Hub, on-prem?)
- [ ] Kubernetes timeline? (MVP: docker-compose; Phase 2+: K8s)
- [ ] Monitoring preference? (CloudWatch, Prometheus, ELK?)

---

## 📞 Architecture Review & Approval

**Current Status**: Design complete, awaiting peer review

**Peer Review Process**:
1. Morgan submits design to Atlas (solution-architect-reviewer)
2. Atlas reviews against bias detection + ADR quality checklist
3. Morgan addresses critical/high issues (max 2 iterations)
4. Review approval → Handoff to BUILD phase

**Expected Timeline**: Review complete by 2026-02-20

---

## 🔍 Design Validation Checklist

Before software crafter starts coding:

**Architecture**:
- [x] Component boundaries clear (hexagonal enforced)
- [x] Adapters pluggable (new provider < 200 LOC)
- [x] No cyclic dependencies (DAG)
- [x] Error paths documented (8+ scenarios)

**Integration**:
- [x] Geolocation-Engine2 API contract defined
- [x] WebSocket message format specified
- [x] Camera provider interface defined

**Quality**:
- [x] Performance targets set (<150ms p50)
- [x] Reliability targets set (99.5% uptime)
- [x] Test coverage targets set (85-90%)
- [x] Observability strategy defined

**Feasibility**:
- [x] Technology choices justified
- [x] Risk mitigations credible
- [x] Timeline realistic (8-12 weeks MVP)
- [x] Team capability adequate

---

## 📖 How to Navigate

**TL;DR (5 min)**: Read `ARCHITECTURE_SUMMARY.md`

**Quick Start (20 min)**: Read `HANDOFF.md`

**Full Design (90 min)**: Read `architecture-design.md`

**Decision Deep Dives**: Read specific ADRs (`ADR-001`, `ADR-002`) or `DESIGN_DECISIONS_MATRIX.md`

**Visual Reference**: Bookmark `ARCHITECTURE_SUMMARY.md` for ASCII diagrams

---

## 📁 File Structure

```
docs/feature/ydc-integration/
├── README.md ← YOU ARE HERE
├── design/
│   └── architecture-design.md (primary design document)
├── adrs/
│   ├── ADR-001-hexagonal-architecture.md
│   └── ADR-002-separate-service.md
├── HANDOFF.md (acceptance designer summary)
├── ARCHITECTURE_SUMMARY.md (visual quick reference)
└── DESIGN_DECISIONS_MATRIX.md (decision rationale)
```

All documents cross-reference each other. Start where it makes sense for your role.

---

## ✅ Sign-Off Checklist

**Design Lead (Morgan)**:
- [x] Architecture designed and documented
- [x] ADRs written (2 major decisions)
- [x] Peer review scheduled

**Peer Reviewer (Atlas)** — *Pending*:
- [ ] Design reviewed against bias detection
- [ ] ADR quality validated
- [ ] Feasibility confirmed
- [ ] Sign-off approved

**Software Crafter** — *Ready*:
- [ ] Architecture understood
- [ ] Component boundaries clear
- [ ] First sprint planning

**Acceptance Designer** — *Ready*:
- [ ] Acceptance criteria defined
- [ ] Test strategy understood
- [ ] Quality gates set

**DevOps** — *Ready*:
- [ ] Deployment strategy understood
- [ ] Docker/docker-compose templates provided
- [ ] Kubernetes path clear (Phase 2)

---

## 📞 Contact & Questions

**Architecture Questions**: Refer to `architecture-design.md` or specific ADRs

**Design Rationale**: See `DESIGN_DECISIONS_MATRIX.md`

**Implementation Questions**: Software crafter review with Morgan during BUILD phase

**Integration Questions**: Acceptance designer + Morgan during DISTILL phase

---

**Document Version**: 1.0
**Last Updated**: 2026-02-17
**Status**: Ready for Peer Review → BUILD Phase

**Next Steps**:
1. ✅ Peer review approval
2. ✅ Software crafter implementation (BUILD)
3. ✅ Acceptance designer validation (DISTILL)

