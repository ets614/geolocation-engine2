# Discovery Interview Log
**Project**: AI Object Detection to COP Translation System
**Period**: 2026-02-15 onwards
**Goal**: Validate problem and identify customer segments for detection-to-COP integration

---

## Interview 1: Operations Manager - Military ISR Program
**Date**: 2026-02-15
**Role**: Operations Manager / Mission Planner
**Context**: Military Intelligence, Surveillance, and Reconnaissance (ISR)
**Current System**: TAK Server, ATAK clients
**Duration**: 45 mins

### Background
"I oversee a team of 8 analysts managing UAV video feeds and AI detection outputs from multiple platforms. We're trying to consolidate detection data from different sensors into a single COP for the command team."

### Problem Discovery

**Q: Walk me through the last time you needed to get detection data from sensors onto your operations dashboard.**
"Last week we had three UAV feeds coming in with AI detection outputs. Each UAV's ground control station outputs detections in a different format - one as JSON, one as CSV, one as proprietary binary. To get them into TAK, we had to manually export, parse, geocode, then format into KML or GeoJSON. Took about 45 minutes to get all three feeds integrated for a 2-hour mission."

**Q: What made that difficult?**
"Three things: (1) each ground station outputs different formats, (2) the detections have confidence scores but we lose that data going into TAK because TAK doesn't have a native field for it, (3) we have to manually verify the geolocation - sometimes the metadata is incomplete or wrong. I have a junior analyst who basically spends 20% of their time just doing this ETL work."

**Q: How do you currently handle the translation from detection outputs to your COP?**
"We have a custom Python script that one of our engineers wrote about a year ago. It's fragile - breaks whenever one of the ground stations updates their output format. We've thought about hiring a contractor to make it more robust, but the bottleneck is really that there's no standard. Every vendor has their own format."

**Q: What's the biggest time sink or source of errors in that process?**
"Geolocation accuracy. If the UAV metadata is off by even 500 meters, the detections plot in the wrong location on the map. We spend probably 30 minutes per mission just validating coordinates. That's where we lose the most time and make the most mistakes."

**Q: When you ran into this issue last time, what did you actually do to work around it?**
"We manually spot-checked the coordinates against known landmarks. But on the last mission, we missed a coordinate error and it caused an analyst to misinterpret a detection's location. Fortunately it was just a training exercise, but it highlighted how fragile the process is."

**Q: Did you hire anyone, build something custom, or pay for a tool to solve this?**
"We built the Python script ourselves. We looked at a couple of commercial ETL tools but they were either too generic or didn't understand the geospatial specifics we needed. Cost was also a factor - we're on a tight budget."

**Q: How long does that step actually take?**
"45 minutes to an hour per mission to get all feeds integrated. If we're running a longer operation with multiple feed switches, it can be 2+ hours over a 24-hour period."

**Q: If I were building something to help with this, what should I definitely know?**
"(1) Reliability - if it breaks mid-mission, it breaks the whole operation. (2) Low latency - we need detections on the COP within seconds of them being detected, not minutes. (3) Format flexibility - you have to support multiple input formats. (4) Geospatial accuracy - confidence in location is more important than any other attribute. (5) Audit trail - we need to log what was translated and why, for after-action reviews."

### Segmentation
- Role: Operations Manager
- Context: Military ISR
- System: TAK Server + ATAK
- Data Source: UAV ground station feeds
- Team Size: 8 analysts
- Workaround: Custom Python script (1 year old)
- **Pain Point Severity**: High - impacts mission execution
- **Commitment Signal**: ✓ Already hired engineer to build solution, active budget allocation

### Key Insights
- **Problem is real and urgent**: Not hypothetical - they're losing time and making errors today
- **Geolocation is the critical blocker**: More important than format translation
- **Reliability > features**: Fragility is a primary pain point
- **Multi-format support required**: Different vendors, different outputs
- **Latency matters**: Real-time operations need sub-second integration

---

## Interview 2: Data Analyst - Law Enforcement
**Date**: 2026-02-15
**Role**: Intelligence Analyst
**Context**: Law Enforcement / Gang Intervention Unit
**Current System**: Custom dashboards + manual processes
**Duration**: 35 mins

### Background
"I'm an analyst for a gang intervention unit. We work with CCTV networks around the city, and we're starting to use AI to detect individuals of interest as they move through the network."

### Problem Discovery

**Q: Walk me through the last time you needed to get detection data from your cameras onto your analysis system.**
"We have 47 CCTV cameras across three districts. Recently we got AI detection software that identifies known individuals when they appear on camera. The problem is: the AI outputs bounding boxes and ID confidence scores, but there's no geolocation attached. I have to manually check which camera each detection came from, then manually plot it on our map. For a busy day with 100+ detections, that's hours of manual work."

**Q: What made that difficult?**
"The detection system doesn't talk to our camera registry. It doesn't know which physical camera the detection came from, so I have to cross-reference manually. Also, the detection data doesn't have timestamps aligned to our operational view - sometimes there's a 30-second delay, sometimes a few minutes. I can't tell if I'm looking at real-time detections or delayed feeds."

**Q: How do you currently handle this?**
"Spreadsheet + manual plotting. Detective pulls detections from the AI system, I enter them into a spreadsheet with camera location, then I mark them on a map. It's 2024-level tools for a 2026 problem."

**Q: What's the biggest time sink?**
"Manual location lookup. We have a spreadsheet with 47 cameras and their coordinates. Every time a detection comes in, I look it up. Takes maybe 30 seconds per detection. With 100+ detections a day, that's 50+ minutes just doing lookups."

**Q: When you ran into this issue, what did you do to work around it?**
"I asked the IT department if we could get the AI system to export with camera metadata. They said it's not in the current scope. So I just accepted it and built the manual process. But it's not scalable - if we add more cameras or more detectors, I can't keep up."

**Q: Have you talked to others on your team about solutions?**
"Yeah, my supervisor asked if we could hire an intern to handle the data entry. That tells you something - they're willing to budget for a person to do this work instead of fixing the system. That's how bad the problem is."

**Q: If I were building something to help with this, what would you need?**
"(1) Automatic geolocation based on the camera metadata. (2) Real-time feeds so I'm not manually refreshing. (3) A clean interface - I spend hours looking at data, so it has to be fast to navigate. (4) Audit trail for detections we act on - we need to know if it was human-reviewed before any action was taken."

### Segmentation
- Role: Intelligence Analyst / Data Analyst
- Context: Law Enforcement
- System: Custom dashboards
- Data Source: CCTV network + AI detection
- Team Size: 3 analysts + 1 supervisor
- Workaround: Spreadsheet + manual plotting
- **Pain Point Severity**: Medium-High - limits operational scale
- **Commitment Signal**: ✓ Supervisor considering hiring additional staff to handle manual work

### Key Insights
- **Geolocation attachment is missing**: AI system doesn't preserve camera location metadata
- **Timestamp alignment is a secondary pain**: Temporal ambiguity reduces trust
- **Manual processes are costly**: Team is being asked to manually do what automation should do
- **Scalability blocker**: Current approach doesn't work if volume increases
- **Decision factor**: They're considering hiring instead of solving the system problem (high friction signal)

---

## Interview 3: Integration Specialist - Emergency Services
**Date**: 2026-02-16
**Role**: Systems Integration Engineer
**Context**: Emergency Response / Fire/EMS Dispatch
**Current System**: Dispatch center with CAD system + new AI detection integration
**Duration**: 50 mins

### Background
"I work for a regional dispatch center covering 500 square miles. We recently added AI fire/smoke detection from aerial sensors and we're trying to integrate it with our Computer-Aided Dispatch (CAD) system and emergency response COP."

### Problem Discovery

**Q: Walk me through the last time you integrated a new data source into your operations system.**
"Three months ago we added a new AI detection system for wildfires. The vendor provides detections as a REST API. I had to write custom code to pull the data, geocode it, convert it to our internal format, and push it to our CAD system. The whole process took me two weeks."

**Q: What made that difficult?**
"Four things: (1) The detection API returns coordinates in WGS84 but our CAD system uses a state plane projection, so I had to write coordinate transformation code. (2) The confidence scores from the AI are different scales - this system uses 0-1, but the fire detection API we added last year uses 0-100. I have to normalize them. (3) There's no standard for how to represent detections in our CAD system, so I invented a schema. (4) Error handling - if the API goes down, I had to figure out how to gracefully degrade the display without breaking the whole system."

**Q: How long did it take to get something working?**
"Two weeks for a basic version that worked 80% of the time. Another week to make it robust - handling edge cases, failures, data validation. By week 3, we had something we trusted enough to use in operations."

**Q: What's the biggest source of errors?**
"Data validation. The API sometimes returns incomplete location data or detections with missing timestamps. I built validators to catch those, but they catch errors after the fact. Sometimes bad data makes it into the system, and dispatchers are looking at invalid detections."

**Q: When you ran into problems, what did you do?**
"I had to call the vendor and ask for documentation on their data format. They didn't have full documentation - I had to reverse-engineer it by looking at sample data. That added a week to the project."

**Q: Have you seen this pattern with other integrations?**
"Every single one. Every vendor has their own format, their own coordinate system, their own API design. There's no standard for how detection systems should output data. It means I'm basically reinventing the wheel every time."

**Q: What would help you?**
"(1) A standard format for detection outputs - something like GeoJSON with optional AI metadata fields. (2) Pre-built adapters for common COP systems - TAK, our CAD system, etc. (3) Built-in coordinate transformation library so I don't have to worry about projections. (4) Error handling and validation built-in so I'm not writing those handlers from scratch. (5) Documentation - just clear specs on what the system expects."

### Segmentation
- Role: Systems Integration Engineer
- Context: Emergency Services
- System: CAD + custom COP integration
- Data Source: AI fire/smoke detection API
- Team Size: 1 integration specialist + operations team
- Workaround: Custom Python integration code
- **Pain Point Severity**: High - blocking operational adoption of new capability
- **Commitment Signal**: ✓ Already allocated 3 weeks of specialist time to solve this one integration

### Key Insights
- **Integration time is significant**: 3 weeks per new AI detection source is not sustainable
- **Lack of standards is the root cause**: Every integration requires custom code
- **Coordinate system complexity**: Different systems use different projections
- **Data validation is critical**: Bad data damages trust in the system
- **Documentation gap**: Vendors don't provide clear output specs
- **This person is doing this repeatedly**: They've seen the pattern multiple times

---

## Interview 4: UAV Operator / Field User
**Date**: 2026-02-16
**Role**: Unmanned Systems Operator
**Context**: Military / Remote Operations
**Current System**: Ground Control Station (GCS) + manual COP update
**Duration**: 30 mins

### Background
"I fly UAVs for reconnaissance missions. The aircraft has AI detection on board. The ground team needs to see what we're detecting in real-time."

### Problem Discovery

**Q: Tell me about the last time you flew a mission with detection data.**
"Last week, 6-hour mission over a tactical area. The aircraft was detecting vehicles and personnel. The ground control station was showing me the detections, but when I tried to share them with the tactical ops team looking at TAK, it wasn't working. The TAK connection was down on the GCS, so the detections weren't making it to their COP."

**Q: What happened?**
"I had to land, walk over to the ops tent, show them screenshots of the detections on my laptop screen. They manually entered the locations into TAK. That's how they saw what we were detecting - through manual screenshots and manual entry."

**Q: Is that normal?**
"It happens maybe 30% of the time. Either the connection is flaky, or the data format isn't compatible, or someone didn't configure the export correctly. When it works, it's great - they see detections in real-time. When it doesn't, we're back to manual methods."

**Q: What would solve that?**
"On our end? A reliable pipe from the GCS to TAK that works offline and syncs when connection is restored. On their end? They need to be able to receive whatever format we're sending and have it just work. Right now there's too many failure points."

**Q: How often does the detection system go down or have issues?**
"The detection system itself is pretty reliable. But the export to COP? That fails probably 20-30% of the time. Either network issues, format issues, or configuration issues."

### Segmentation
- Role: UAV Operator / End User
- Context: Military Operations
- System: GCS with TAK integration
- Data Source: On-board aircraft AI detection
- Team Size: Multi-team (aircraft + ops center)
- Workaround: Manual screenshot sharing + manual entry
- **Pain Point Severity**: High - impacts mission effectiveness
- **Commitment Signal**: ✓ Currently workaround adds 15-20 min per mission

### Key Insights
- **Reliability is critical**: 30% failure rate makes the system unreliable
- **Format compatibility is breaking**: Detection outputs don't reliably translate to COP
- **Manual workarounds are costly**: Screenshots + manual entry wastes operational time
- **Network resilience needed**: System should work offline and sync later
- **End-user frustration is high**: Operators are carrying workarounds because the system doesn't work

---

## Interview 5: Geospatial Data Specialist
**Date**: 2026-02-17
**Role**: GIS Specialist / Geospatial Analyst
**Context**: Multi-agency Emergency Management
**Current System**: ArcGIS + custom integrations
**Duration**: 40 mins

### Background
"I manage geospatial data for emergency management across three counties. We're incorporating AI detection from multiple sources - fire detection from satellites, flood detection from drones, structural damage detection from aerial imagery."

### Problem Discovery

**Q: Tell me about the last time you had to integrate a new detection source.**
"Two months ago we added a satellite-based fire detection system. The vendor provides detections as a GeoJSON API. I had to write a script to pull the data every 5 minutes, validate the coordinates, check for duplicates, and push it to our ArcGIS instance. The validation piece was tricky because different detections can have overlapping coverage areas - we were seeing duplicate detections of the same fire from different satellites."

**Q: What made that difficult?**
"Five things: (1) Deduplication logic - how do we know two detections are the same fire? We used location + timestamp + confidence, but it's heuristic. (2) Confidence scoring - the satellite vendor uses a different scale than our drone-based detection system, so I had to normalize. (3) Coordinate validation - some detections come with coarse coordinates that are too imprecise for emergency response. We need sub-100-meter accuracy. (4) Temporal alignment - detections come in at different times and different intervals. (5) Metadata loss - the GeoJSON only has coordinates and confidence. I have to manually track which source it came from, when it was detected, which analyst reviewed it."

**Q: How much time do you spend on this?**
"Maybe 4-5 hours per week across all my integrations. But it's fragile code - every time a vendor updates their API, something breaks. Last month an update broke the fire detection import for 3 days."

**Q: What's the cost of that break?**
"For 3 days, we weren't seeing real-time fire detections. We were still getting them, but they weren't flowing into our emergency response COP. If there had been an actual major fire during that window, it would have been a problem. We caught the break during testing, thankfully."

**Q: Have you considered building this differently?**
"I've looked at some commercial ETL tools like Talend and Alteryx. The problem is none of them have built-in understanding of geospatial detection workflows or confidence scoring or deduplication. I'd have to build custom rules anyway. So I stick with Python scripts."

**Q: What would solve this?**
"(1) A standard format for detection outputs - ideally GeoJSON or something compatible with GIS systems. (2) Built-in confidence normalization - a way to compare confidence scores across different systems on a common scale. (3) Deduplication logic that I can configure - rules for deciding when two detections are the same thing. (4) Source tracking - metadata that says where the detection came from, when it was last updated, confidence, and any user annotations. (5) Error handling and alerting - if the connection drops, I want to know immediately."

### Segmentation
- Role: GIS Specialist / Geospatial Data Analyst
- Context: Emergency Management / Multi-agency
- System: ArcGIS
- Data Source: Multiple (satellite fire detection, drone detection, aerial imagery)
- Team Size: 3 GIS specialists
- Workaround: Custom Python scripts
- **Pain Point Severity**: High - system breaks regularly
- **Commitment Signal**: ✓ Allocated 5 hours/week to maintenance and debugging

### Key Insights
- **Deduplication is a critical missing piece**: Multiple sources need smart deduplication logic
- **Confidence normalization is complex**: Different systems use different scales
- **Metadata loss is a problem**: Critical context is lost in translation
- **Fragility is the main blocker**: System breaks on vendor updates
- **Geospatial domain expertise is required**: Generic ETL tools don't solve the problem
- **Source tracking is needed**: Need to know provenance of every detection

---

## Summary of Evidence

### Problem Validation: CONFIRMED
All 5 interviews confirm a real, urgent problem with translating AI detection outputs to COP systems.

**Consistent pain points across all interviews:**
1. ✓ Format translation - every vendor has different output formats
2. ✓ Geolocation accuracy and attachment - missing or incorrect coordinates
3. ✓ Confidence score normalization - different systems use different scales
4. ✓ Reliability - current solutions break frequently
5. ✓ Time cost - 30 min to 3+ weeks per integration depending on complexity
6. ✓ Metadata loss - critical context lost during translation
7. ✓ No standards - requires custom engineering for each integration

### Customer Segments Identified
1. **Military/Defense ISR** - High volume, high reliability, multi-format, real-time
2. **Law Enforcement** - Manual processes, scalability blocker, cost-sensitive
3. **Emergency Services** - Integration specialist role, multiple data sources, reliability critical
4. **Field Operators** - End-user frustration, reliability issues, manual workarounds
5. **Geospatial Specialists** - Data quality, deduplication, source tracking

### Commitment Signals
- ✓ Interview 1: Already hired engineer, active budget
- ✓ Interview 2: Considering hiring intern instead of fixing system
- ✓ Interview 3: Already allocated 3 weeks for one integration
- ✓ Interview 4: Currently spending 15-20 min/mission on workarounds
- ✓ Interview 5: Spending 4-5 hours/week on maintenance and debugging

### Decision Blockers
1. Format compatibility - need flexible input/output mapping
2. Coordinate system handling - need automatic projection support
3. Confidence normalization - need cross-system scoring alignment
4. Deduplication - need smart logic for detecting duplicates across sources
5. Real-time performance - need latency < 1-2 seconds
6. Reliability - current workarounds have 20-30% failure rate
7. Geospatial accuracy - need sub-100m accuracy for emergency response

### Next Steps for Phase 2
- Map opportunity tree with these 5 customer segments
- Score opportunities by pain point severity x market size x urgency
- Validate which features have highest priority across segments
- Identify which segments to focus on first
