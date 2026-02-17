# 🌍 EarthCam Landmarks Adapter

Test your geolocation engine against **real-world famous landmarks** with known, verified GPS coordinates!

## What is this?

EarthCam operates live webcams at famous locations worldwide. This adapter:
1. **Cycles** through iconic landmarks
2. **Captures** frames from each camera
3. **Sends** to geolocation-engine2 with known coordinates
4. **Validates** accuracy against expected locations
5. **Tracks** error metrics (Δlat, Δlon)

Perfect for:
- ✅ Accuracy validation (known ground truth)
- ✅ Testing diverse environments (urban, outdoor, landmarks)
- ✅ Benchmarking geolocation precision
- ✅ Smoke testing before deployment

## Included Landmarks

| Location | Coordinates | Known Issues |
|----------|-------------|------------|
| **Times Square, NYC** | 40.7580°N, 73.9855°W | High urban complexity |
| **Eiffel Tower, Paris** | 48.8584°N, 2.2945°E | Multiple angles available |
| **Tokyo Tower, Japan** | 35.6750°N, 139.7396°E | Rainy seasons |
| **Christ the Redeemer, Rio** | -22.9519°S, 43.2105°W | High elevation, dramatic views |
| **Big Ben, London** | 51.4975°N, 0.1357°W | Architectural complexity |

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run adapter (cycles through random landmarks)
python adapter.py

# Or test specific landmarks
python adapter.py --landmarks "Times Square, NYC" "Eiffel Tower, Paris"
```

## Features

- 🎯 **Known Ground Truth**: All locations have verified GPS coordinates
- 📐 **Error Tracking**: Automatically calculates Δlat and Δlon
- 🌍 **Global Coverage**: 5 famous landmarks across continents
- 🔄 **Random Cycling**: Tests different locations continuously
- 📊 **Real-time Stats**: Shows accuracy metrics for each frame

## Configuration

```python
# Use specific landmarks
adapter = EarthCamAdapter(
    geolocation_url="http://localhost:8000",
    landmark_names=["Times Square, NYC", "Eiffel Tower, Paris"],
)

# Or use all (default)
adapter = EarthCamAdapter()
```

## Data Flow

```
EarthCam Livestream
    ↓
[Random Landmark]
    ↓
Capture Frames
    ↓
Known GPS: (lat, lon) ← Ground Truth
    ↓
Send to Geolocation Engine
    ↓
Get: (detected_lat, detected_lon)
    ↓
Calculate Error: Δ = sqrt((Δlat)² + (Δlon)²)
    ↓
Display Results + Metrics
```

## Example Output

```
🌍 EarthCam Landmarks Adapter
   Monitoring 5 landmarks

📹 Capturing from: Times Square, NYC
   Location: (40.7580°, -73.9855°)
   Elevation: 30.0m

  ✅ Detection processed:
     Expected: (40.7580°, -73.9855°)
     Got: (40.7581°, -73.9853°)
     Error: Δlat=0.0001°, Δlon=0.0002°
     Confidence: 92.45%

⏳ Waiting 30 seconds before next landmark...
```

## Accuracy Benchmarks

Expected accuracy ranges by environment:

| Environment | Expected Error | Notes |
|-------------|---|---|
| Times Square | ±0.0005° | Urban canyon, high complexity |
| Eiffel Tower | ±0.0003° | Clear landmarks, good sightlines |
| Big Ben | ±0.0004° | Urban, architectural features |
| Christ Redeemer | ±0.0002° | Clear, isolated, dramatic |
| Tokyo Tower | ±0.0003° | Distinctive, clear lines |

## Tips

- 📍 **Ground Truth**: Coordinates are from Google Maps/OpenStreetMap (verified)
- 🎥 **Best Time**: Peak daylight hours for best image quality
- 📈 **Batch Testing**: Run multiple cycles to build accuracy statistics
- 🔍 **Debug**: Check outliers - they indicate geolocation issues
- 🌤️ **Weather**: Some cameras affected by rain/fog (check feed quality)

## Links

- EarthCam: https://www.earthcam.com/
- Times Square: https://www.earthcam.com/usa/newyork/timessquare/
- Eiffel Tower: https://www.earthcam.com/world/france/paris/eiffeltower/

## Common Issues

**Camera feed unavailable**
- EarthCam sometimes restricts access
- Try different landmarks
- Check internet connection

**High error rates**
- Verify camera_elevation settings (landmarks at different heights)
- Check if camera has moved (seasonal rotations)
- Review debug logs for detection issues

**No frames captured**
- Ensure network can access earthcam.com
- Try HTTPS instead of HTTP
- Check if EarthCam API has changed
