# 🌍 Web Dashboard - Feature Guide

## What This Dashboard Does For Business Users

### The Big Picture: One Screen, Complete Pipeline

```
Real Camera Feed
      ↓
AI Detects Objects
      ↓
Engine Calculates GPS Coordinates
      ↓
Generates TAK/ATAK XML
      ↓
Maps in TAK/ATAK
```

**All visible on one screen. No technical expertise needed.**

---

## Section 1: Feed Selection (Left Panel)

### Purpose
Choose which camera/location to process

### Features
- **Dropdown Menu** - 5 world-famous landmarks
  - Times Square, NYC
  - Eiffel Tower, Paris
  - Tokyo Tower, Japan
  - Christ the Redeemer, Rio
  - Big Ben, London

- **Location Details** - Automatically shows:
  - 📍 GPS Coordinates (latitude, longitude)
  - 📏 Elevation (in meters)
  - ℹ️ Description of the location

- **Real-Time Stats**
  - Number of detections so far
  - Number of CoT XML files generated

- **Start Button** - One click to begin processing

### Example Usage
1. Open dropdown
2. Select "Times Square, NYC" 🗽
3. See location details populate
4. Click "Start Processing" ▶️
5. Watch detections appear in real-time

---

## Section 2: Live Video Feed (Center Panel)

### Purpose
Display the incoming video stream in real-time

### Features
- **Video Display** - Shows current frame
- **Status Indicator** 🟢 - Green dot shows live activity
- **Live Metrics**
  - Stream Status (Idle / Processing / Active)
  - Frame Size (1920×1440 for example)
  - Last Update Time (updated continuously)

### What End Users See
- Real video from the selected camera
- Live updates as frame arrives
- Quality indicator (shows if stream is healthy)

### Why It Matters
"I can see the actual video that's being analyzed"

---

## Section 3: AI Detections (Right Panel)

### Purpose
Show what the AI found in the video

### Features
- **Detection List** - Shows up to 10 most recent
- **For Each Detection:**
  - 🎯 Detection Class (what it is - e.g., "landmark")
  - Detection ID (unique identifier for tracking)
  - Pixel Location (where in the image: x, y coordinates)
  - **Confidence Level** - Color coded:
    - 🟩 **GREEN** (>90%) - Very confident
    - 🟨 **YELLOW** (75-90%) - Confident
    - 🟥 **RED** (<75%) - Low confidence

### Example
```
🎯 Landmark
ID: DET-0001
Pixel: (1505, 775)
[GREEN 93%] ← Very confident
```

### Why It Matters
"The AI found this object with 93% confidence"

---

## Section 4: Generated CoT/TAK XML (Full Width)

### Purpose
Show the exact XML that gets sent to TAK/ATAK servers

### Features
- **Live XML Display** - Copy-paste ready
- **Syntax Highlighting** - Color-coded for readability
- **Scrollable** - For large payloads
- **Complete Packet** - Everything TAK needs

### What's In The XML
```xml
<?xml version="1.0" encoding="UTF-8"?>
<event version="2.0"
       uid="Detection.12345"        ← Unique ID
       type="b-m-p-s-u-c"           ← TAK type
       time="2026-02-17T04:11:07">  ← Timestamp
    <point lat="40.758000"          ← Calculated GPS (lat)
           lon="-73.985500"         ← Calculated GPS (lon)
           ce="32.92" />            ← Accuracy/Confidence Estimate
    <detail>
        <contact callsign="Detection-7" />
        ...
    </detail>
</event>
```

### Why It Matters
"This is the exact format TAK servers expect. It's ready to push to the map."

---

## How Business Users Understand It

### For Decision Makers
**"This dashboard shows the entire workflow in one place"**
- Input: Camera feed (left)
- Processing: AI detection (right)
- Output: TAK format (bottom)
- Success: All three panels working together = working system

### For Operators
**"I can see detections in real-time with confidence scoring"**
- GREEN detections = trust this location on the map
- YELLOW = use with caution
- RED = might be a false positive

### For IT/Integration Teams
**"The XML is ready to integrate with TAK/ATAK"**
- Copy the XML → Paste into TAK
- Automatic field mapping
- All coordinates already calculated

---

## The User Flow

```
1. Open Dashboard
   ↓
2. Select a Location (dropdown)
   ↓
3. Location Details Appear (auto-populated)
   ↓
4. Click "Start Processing"
   ↓
5. Watch Live Video Feed Update
   ↓
6. See AI Detections Appear (with confidence)
   ↓
7. View Generated XML
   ↓
8. Copy XML → Push to TAK
   ↓
9. See Detection on TAK Map
```

---

## Real-World Example: Times Square

**What happens when you select Times Square:**

1. **Feed Selection Shows:**
   - 📍 Latitude: 40.7580°
   - ↔️ Longitude: -73.9855°
   - 📏 Elevation: 30.0m
   - Description: "Urban landmark with high complexity"

2. **After Clicking Start:**
   - Video shows Times Square live feed
   - Status: "Active"

3. **Detections Appear:**
   ```
   🎯 Landmark (pixel: 1505, 775) GREEN 93%
   🎯 Landmark (pixel: 415, 501)  YELLOW 85%
   🎯 Landmark (pixel: 1238, 542) GREEN 83%
   ```

4. **CoT XML Generated:**
   ```xml
   <point lat="40.7580" lon="-73.9855" ce="32.92" />
   ```

5. **Result:** All three detections appear on TAK map at Times Square location

---

## Visual Design Principles

### Color Scheme
- 🟣 **Purple Gradient** - Modern, professional
- 🟩 **GREEN** - High confidence (trust it)
- 🟨 **YELLOW** - Medium confidence (check it)
- 🟥 **RED** - Low confidence (verify it)
- ⚫ **Black** - Video background

### Layout
- **3-Column Grid** - Clearly separates concerns
- **Full-Width XML** - Emphasizes importance
- **Responsive** - Works on any screen size
- **Emoji Icons** - Clear, instant visual recognition

### Typography
- **System Font** - Fast, professional
- **Fixed-Width for XML** - Proper formatting
- **High Contrast** - Easy to read

---

## For Non-Technical Audiences

### What To Tell Them

**"This shows you the complete AI pipeline"**

| Panel | What It Does |
|-------|---|
| Left | Pick a camera/location |
| Middle | See the live video |
| Right | See what AI found |
| Bottom | See what TAK receives |

### Key Metrics

- ✅ **Detection Count** - How many objects found
- 🟩 **GREEN Detections** - High confidence (good)
- 📊 **CoT Generation** - XML packets ready

### Success Indicators

- Video is updating ✅
- Detections are appearing ✅
- XML is being generated ✅
- Confidence levels are HIGH (GREEN) ✅

---

## Use Cases

### 1. Live Monitoring
- Open dashboard
- Select location
- Watch detections in real-time
- Verify accuracy on actual map

### 2. Accuracy Validation
- Compare detections with known landmarks
- Check if GPS coordinates match expected locations
- Assess confidence scoring

### 3. System Testing
- Test all 5 landmarks
- Verify pipeline end-to-end
- Demo to stakeholders

### 4. Training
- Show new users the workflow
- Demonstrate AI capabilities
- Explain XML integration

---

## Key Takeaways For Stakeholders

✅ **Complete Visibility** - See the entire workflow in one dashboard
✅ **Real-Time Results** - Live updates as detections happen
✅ **Confidence Scoring** - Know how reliable each detection is
✅ **TAK Ready** - XML automatically formatted for integration
✅ **Simple Interface** - No technical knowledge required
✅ **Beautiful Design** - Professional, trustworthy appearance
✅ **Responsive** - Works on desktop, tablet, mobile
✅ **Extensible** - Easy to add more cameras/locations

---

## Technical Notes (For Developers)

- FastAPI backend
- Vanilla JavaScript frontend
- Real-time updates via polling
- CoT XML with syntax highlighting
- CORS enabled for remote APIs
- Responsive CSS Grid layout

See README.md for deployment options.
