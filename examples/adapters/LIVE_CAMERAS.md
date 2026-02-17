# 🎥 Live Camera Adapters - Complete Guide

Real-world streaming video feeds to test your geolocation engine against actual data!

## Quick Comparison

| Adapter | Best For | Challenge Level | Data Type | Locations |
|---------|----------|-----------------|-----------|-----------|
| **🛰️ ISS Earth Camera** | Extreme elevation, rapid geography change | 🔴 Hard | Space imagery | 1 (Orbital) |
| **🌍 EarthCam Landmarks** | Accuracy validation, known ground truth | 🟢 Easy | Urban/outdoor | 5 famous sites |
| **🚗 Traffic Cameras** | Real vehicle detection, dynamic content | 🟡 Medium | Highway/urban | 4 cities |
| **🦁 Wildlife Streams** | Edge cases, challenging environments | 🔴 Hard | Exotic locations | 5 continents |

## Which Adapter to Use?

### 🟢 Starting Out?
**→ Use EarthCam Landmarks**
- Known coordinates (ground truth)
- Clear, well-lit feeds
- Good for initial testing
- Validates accuracy baseline

```bash
cd examples/adapters/earthcam-landmarks/
python adapter.py
```

### 🟡 Testing Real-World Data?
**→ Use Traffic Cameras**
- Real dynamic content
- Multiple objects per frame
- Practical city locations
- Good for production scenarios

```bash
cd examples/adapters/traffic-camera-feeds/
python adapter.py
```

### 🔴 Pushing Limits?
**→ Use ISS or Wildlife**

**ISS** - For extreme scenarios:
- Highest altitude (400km)
- Fastest-changing perspective
- Continuously updated position
- Most challenging coordinates

**Wildlife** - For edge cases:
- Low light, underwater, polar
- Complex natural terrain
- Diverse environments
- Real conservation data

```bash
# ISS: Ultimate challenge
cd examples/adapters/iss-earth-camera/
python adapter.py

# Wildlife: Edge case testing
cd examples/adapters/wildlife-streams/
python adapter.py
```

---

## 🛰️ ISS Earth Camera Adapter

**Status**: Most Awesome 🚀

### Overview
Connects to **NASA's International Space Station** live video feed and processes frames as the ISS orbits Earth at 400km altitude.

### Best For
- ✅ Testing extreme elevation scenarios
- ✅ Validating rapid coordinate changes
- ✅ Benchmark data for space-based systems
- ✅ "Geolocating from space" demo

### Quick Start
```bash
cd examples/adapters/iss-earth-camera/
pip install -r requirements.txt
python adapter.py
```

### Key Features
- 🛰️ Real NASA ISS live stream
- 📍 Current ISS position from NASA API
- 🎥 HD Earth camera feed
- ⏱️ Configurable frame capture rate
- 📊 Real-time results

### Data
- **Source**: NASA ISS HD Earth Viewing Experiment
- **Altitude**: ~400 km
- **Field of View**: Nadir (straight down)
- **Update Rate**: Every ~90 minutes (orbit period)

### Challenges
- 🌙 Only good during daylight over Earth
- ☁️ Cloud cover affects image quality
- 🎯 Large geography means small pixel targets
- ⏰ 90-minute orbit = limited windows per location

### Resources
- [NASA ISS Live](https://www.nasa.gov/live/)
- [ISS Current Position](http://api.open-notify.org/iss-now.json)
- [ISS Tracker](https://www.n2yo.com/)

---

## 🌍 EarthCam Landmarks Adapter

**Status**: Recommended for Testing ✅

### Overview
Cycles through **5 famous landmarks worldwide** with verified GPS coordinates. Perfect for validating accuracy.

### Best For
- ✅ Initial accuracy testing
- ✅ Validation against known coordinates
- ✅ Benchmarking geolocation precision
- ✅ Pre-deployment smoke testing

### Quick Start
```bash
cd examples/adapters/earthcam-landmarks/
pip install -r requirements.txt
python adapter.py
```

### Included Landmarks
1. **Times Square, NYC** - 40.7580°N, 73.9855°W
2. **Eiffel Tower, Paris** - 48.8584°N, 2.2945°E
3. **Tokyo Tower, Japan** - 35.6750°N, 139.7396°E
4. **Christ the Redeemer, Rio** - 22.9519°S, 43.2105°W
5. **Big Ben, London** - 51.4975°N, 0.1357°W

### Key Features
- 📍 Known ground truth coordinates
- 🎯 Automatic error calculation (Δlat, Δlon)
- 🌍 Global distribution
- 🔄 Random landmark cycling
- 📊 Accuracy metrics per frame

### Example Output
```
  ✅ Detection processed:
     Expected: (40.7580°, -73.9855°)
     Got: (40.7581°, -73.9853°)
     Error: Δlat=0.0001°, Δlon=0.0002°
     Confidence: 92.45%
```

### Tips
- 🎯 Use for accuracy baseline
- 🔍 Track error statistics over time
- 🌤️ Best during daylight
- 📊 Good for CI/CD validation

---

## 🚗 Traffic Camera Feeds Adapter

**Status**: Real-World Production Data 🚙

### Overview
Connects to **public traffic management cameras** on highways, intersections, and urban areas. Real vehicles, dynamic content.

### Best For
- ✅ Real vehicle detection testing
- ✅ Urban geolocation scenarios
- ✅ Multi-object tracking validation
- ✅ Production readiness testing

### Quick Start
```bash
cd examples/adapters/traffic-camera-feeds/
pip install -r requirements.txt
python adapter.py
```

### Included Locations
1. **CA-101 South** - San Francisco Highway
2. **I-405 North** - Los Angeles Highway
3. **Times Square** - NYC Intersection
4. **Michigan Ave Bridge** - Chicago

### Key Features
- 🚗 Real vehicle data
- 📍 Known camera locations
- 🎯 Multi-detection per frame
- 📊 Confidence scoring
- 🌍 Real GPS coordinates

### Finding More Streams
**California (CALTRANS)**
```
https://cwwp2.dot.ca.gov/vm/feeds.htm
https://www.dot.ca.gov/
```

**New York (NYC DOT)**
```
https://a841-tfpwg.nyc.gov/
```

**YouTube Live**
Many cities broadcast on YouTube. Search for:
- "[City] traffic webcam"
- "[Highway] live traffic"

### Tips
- 🚗 Use during rush hours (7-9am, 4-7pm)
- 🌞 Daytime has better quality
- 🔗 Some streams require RTSP decoder
- 📝 Document RTSP URLs you find

---

## 🦁 Wildlife & Nature Streams Adapter

**Status**: Edge Cases & Exotic Locations 🌍

### Overview
Connects to **wildlife and nature cameras** from around the world in challenging environments: deserts, oceans, mountains, polar regions.

### Best For
- ✅ Testing edge cases
- ✅ Extreme lighting conditions
- ✅ Challenging terrain
- ✅ Unusual perspectives
- ✅ Conservation applications

### Quick Start
```bash
cd examples/adapters/wildlife-streams/
pip install -r requirements.txt
python adapter.py
```

### Included Locations
1. **Serengeti** - African savanna (-2.3333°, 34.8888°)
2. **Mount Etna** - Active volcano (37.7511°, 15.0034°)
3. **Great Barrier Reef** - Underwater (-18.2871°, 147.6992°)
4. **Antarctica** - Polar research (-70.0°, 0.0°)
5. **Kaziranga** - Wildlife reserve (26.6000°, 93.5000°)

### Key Features
- 🌍 Global coverage (5 continents)
- 🦁 Wildlife + terrain + geology detection
- 🌙 Extreme lighting conditions
- 🎨 Color/contrast challenges
- 📍 Verified GPS coordinates

### Detection Classes
- 🦁 `animal` - Wildlife
- 🏔️ `terrain_feature` - Mountains, rocks, geological
- 🌿 `vegetation` - Trees, grass, plants
- 💧 `water` - Lakes, rivers, ocean

### Tips
- 🎬 Some streams seasonal
- 🌙 Low light = harder accuracy
- 💧 Underwater = color shifts
- 🌡️ Polar = extreme reflection

### Real Stream URLs
Find actual wildlife streams:
- https://www.explorers.org/live-cams/
- https://www.earthcam.com/
- https://www.youtube.com/results?search_query=live+safari+stream

---

## Running All Adapters

### Sequential Testing
```bash
# Test each adapter one by one
for adapter in iss-earth-camera earthcam-landmarks traffic-camera-feeds wildlife-streams; do
    echo "Testing $adapter..."
    cd examples/adapters/$adapter
    pip install -r requirements.txt
    python adapter.py &  # Run in background
done
```

### Monitoring Dashboard
Create a monitoring script to run all simultaneously:

```python
import subprocess
import time

adapters = [
    "iss-earth-camera",
    "earthcam-landmarks",
    "traffic-camera-feeds",
    "wildlife-streams"
]

processes = []
for adapter in adapters:
    p = subprocess.Popen([
        "python", f"examples/adapters/{adapter}/adapter.py"
    ])
    processes.append(p)
    print(f"Started {adapter}")
    time.sleep(5)  # Stagger starts

# Monitor
try:
    for p in processes:
        p.wait()
except KeyboardInterrupt:
    for p in processes:
        p.terminate()
```

---

## Data Flow (All Adapters)

```
Live Stream Source
        ↓
  [Camera Adapter]
        ↓
  Capture Frames
        ↓
  Extract Features
        ↓
  Geolocation Engine
  ├─ Photogrammetry
  ├─ Confidence Scoring
  └─ Error Calculation
        ↓
  Results
  ├─ Geolocated Coordinates
  ├─ Confidence Metrics
  ├─ Error Analysis
  └─ Raw Images
        ↓
  Audit Trail
        ↓
  Offline Queue (if TAK offline)
        ↓
  TAK/ATAK Push
```

---

## Configuration & Customization

### All Adapters Accept
```python
# Geolocation Engine URL
geolocation_url="http://localhost:8000"

# Optional: Specific locations/cameras
camera_names=["Location 1", "Location 2"]
```

### Per-Adapter Configuration
See individual README files:
- [ISS Earth Camera](iss-earth-camera/README.md)
- [EarthCam Landmarks](earthcam-landmarks/README.md)
- [Traffic Cameras](traffic-camera-feeds/README.md)
- [Wildlife Streams](wildlife-streams/README.md)

---

## Testing Checklist

Use these adapters to validate your geolocation system:

- [ ] **EarthCam**: Accuracy validation against known landmarks
- [ ] **Traffic**: Real-world vehicle detection in urban areas
- [ ] **ISS**: Extreme elevation and rapid geography changes
- [ ] **Wildlife**: Edge cases (low light, underwater, extreme terrain)
- [ ] **Combined**: Run multiple adapters simultaneously
- [ ] **Performance**: Monitor API response times
- [ ] **Queue**: Verify offline queue with network interruptions
- [ ] **Audit**: Check audit trail captures all events
- [ ] **Confidence**: Validate confidence scoring across adapters

---

## Troubleshooting

### General Issues
- **API Connection**: Ensure geolocation-engine2 is running on http://localhost:8000
- **Frame Capture**: Install ffmpeg (`sudo apt-get install ffmpeg`)
- **Permissions**: Run with `python3` not `python`

### Per-Adapter Issues
See individual README files for troubleshooting specific to each adapter.

---

## Next Steps

1. **Start with EarthCam** to validate accuracy baseline
2. **Add Traffic Cameras** for real-world testing
3. **Try ISS** for extreme scenario testing
4. **Use Wildlife** for edge case validation
5. **Integrate with Dashboard** for real-time visualization
6. **Hook to TAK/ATAK** for operational deployment

---

## Contributing

Found a cool live camera stream? Add it!

1. Fork the repo
2. Add your camera to the appropriate adapter
3. Document the location and coordinates
4. Test with geolocation-engine2
5. Submit PR with results

---

## Resources

- 📖 [Geolocation Engine Documentation](../../docs/)
- 🎯 [Photogrammetry Concepts](../../../docs/concepts/)
- 🗺️ [Google Maps API](https://developers.google.com/maps)
- 🛰️ [NASA APIs](https://api.nasa.gov/)
- 🎥 [OpenCV Documentation](https://docs.opencv.org/)

---

**Last Updated**: 2026-02-17
**Status**: All 4 adapters tested ✅
