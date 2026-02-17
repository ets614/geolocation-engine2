# 🦁 Wildlife & Nature Streams Adapter

Test geolocation across **exotic locations** using live wildlife and nature cameras from around the world!

## What is this?

This adapter connects to live wildlife, nature, and scientific monitoring cameras:
1. **African Safari**: Real wildlife in natural habitat
2. **Volcano Monitoring**: Active geological features
3. **Underwater**: Coral reefs and marine life
4. **Polar**: Antarctic research and ice
5. **Indian Reserves**: Endangered species monitoring

Each location provides:
- 🌍 **Verified GPS Coordinates**: Known locations
- 🎬 **Real-time Video**: Live streams
- 🌙 **Varied Lighting**: Different times/seasons
- 🌧️ **Weather Challenges**: Rain, fog, snow
- 🦁 **Dynamic Content**: Wildlife detection

## Included Locations

| Location | Habitat | Coordinates | Stream Type |
|----------|---------|-------------|------------|
| **Serengeti** | Savanna/Wildlife | -2.3333°, 34.8888° | Wildlife cam |
| **Mount Etna** | Active Volcano | 37.7511°, 15.0034° | Geoscience cam |
| **Great Barrier Reef** | Underwater | -18.2871°, 147.6992° | Dive/research |
| **Antarctica** | Polar/Research | -70.0°, 0.0° | Science station |
| **Kaziranga Park** | Wildlife Reserve | 26.6000°, 93.5000° | Nature preserve |

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Start adapter (cycles through exotic locations)
python adapter.py

# Or test specific location
python adapter.py --location "Serengeti National Park"
```

## Features

- 🌍 **Global Coverage**: 5 locations across 5 continents
- 🦁 **Wildlife Detection**: Animal, terrain, vegetation, water classes
- 🎥 **Dynamic Cameras**: Various angles and perspectives
- 📊 **Real-time Processing**: Live frame analysis
- 🌙 **Extreme Conditions**: Low light, underwater, high altitude

## Data Flow

```
Wildlife/Nature Live Stream
    ↓
Select Random Location
    ↓
Capture Frames
    ↓
Multi-class Detection
    (animal, terrain, vegetation, water)
    ↓
Send to Geolocation Engine
    (with exotic location GPS)
    ↓
Engine Processes Frame
    ↓
Return Geolocated Feature
    ↓
Display Results
```

## Location Details

### 🦁 Serengeti National Park
- **Tanzania**: -2.3333°, 34.8888°
- **Highlights**: Big Five wildlife, migration routes
- **Best time**: June-October (dry season)
- **Challenges**: Variable lighting, fast-moving subjects
- **Detection**: Animals, grassland patterns, water holes

### 🌋 Mount Etna (Sicily, Italy)
- **Coordinates**: 37.7511°, 15.0034°
- **Highlights**: Active volcano, lava flows, geological features
- **Elevation**: 3,300m
- **Challenges**: Steam, ash, thermal variations
- **Detection**: Lava features, volcanic terrain, smoke patterns

### 🐠 Great Barrier Reef (Australia)
- **Coordinates**: -18.2871°, 147.6992°
- **Highlights**: World's largest coral reef, marine biodiversity
- **Challenges**: Water turbidity, light absorption, color shifts
- **Detection**: Coral features, fish schools, reef structures

### 🧊 Antarctic Research Station
- **Coordinates**: -70.0°, 0.0°
- **Highlights**: Polar research, ice sheets, aurora borealis
- **Challenges**: Low lighting, extreme temperatures, ice reflection
- **Detection**: Ice patterns, snow formations, structural features

### 🦏 Kaziranga National Park (India)
- **Coordinates**: 26.6000°, 93.5000°
- **Highlights**: Indian rhino habitat, grasslands, river ecosystems
- **Challenges**: Dense vegetation, seasonal flooding, monsoon rains
- **Detection**: Large animals, grassland patterns, water

## Example Output

```
🦁 Wildlife & Nature Streams Adapter
   Monitoring 5 exotic locations

🦁 Connecting to: Serengeti National Park
   Mammals in African savanna
   Location: (-2.3333°, 34.8888°)

  🦁 Animal detected:
     Location: Serengeti National Park
     Geolocated to: (-2.3335°, 34.8890°)
     Confidence: 85.67%

  🏔️ Terrain feature detected:
     Location: Serengeti National Park
     Geolocated to: (-2.3340°, 34.8885°)
     Confidence: 78.34%

⏳ Waiting 45 seconds before next camera...
```

## Configuration

```python
# Test specific locations
adapter = WildlifeStreamAdapter(
    geolocation_url="http://localhost:8000",
    camera_names=["Serengeti National Park", "Mount Etna Volcano"],
)
```

## Tips & Tricks

- 🎥 **Stream Quality**: Wildlife cams vary in quality; some are seasonal
- 🌙 **Lighting**: Underwater and polar cams have extreme lighting
- 📍 **GPS Accuracy**: All coordinates verified via OpenStreetMap
- 🔍 **Multi-class**: Try detecting different object types per location
- 📊 **Benchmarking**: Great for testing edge cases and challenging scenarios

## Real Stream URLs

Find actual wildlife streams here:

### YouTube Live Channels
- https://www.youtube.com/results?search_query=live+safari+stream
- https://www.youtube.com/results?search_query=volcano+monitoring+live
- https://www.youtube.com/results?search_query=coral+reef+live+cam

### Specialized Services
- **Explore.org**: Live wildlife feeds (explorers.org)
- **Safari.com**: African safari streams
- **EarthCam**: Nature cameras (earthcam.com)
- **Windy**: Volcano monitoring feeds
- **NOAA**: Scientific camera feeds

### Setting Local Test Stream
```bash
# Create test video from wildlife footage
ffmpeg -i wildlife_sample.mp4 -f mjpeg http://localhost:8080/stream
```

## Integration with Geolocation Engine

### Simple Detection Classes
```python
detection_classes = [
    "animal",           # Wildlife
    "terrain_feature",  # Mountains, rocks, geological
    "vegetation",       # Trees, grass, plants
    "water",           # Lakes, rivers, ocean
]
```

### Variable Camera Angles
```python
if "underwater" in camera.description.lower():
    pitch = random.uniform(-60, 60)  # Wide angle
elif "volcano" in camera.description.lower():
    pitch = random.uniform(-45, 0)   # Downward looking
else:
    pitch = random.uniform(-30, 30)  # Medium angle
```

## Use Cases

- 🔬 **Research**: Geolocation accuracy in challenging environments
- 🌍 **Conservation**: Wildlife tracking and monitoring integration
- 🗺️ **Mapping**: Remote location validation and mapping
- 🎓 **Education**: Teaching geolocation concepts with exotic examples
- 🚨 **Security**: Perimeter monitoring in remote areas
- 📊 **Analytics**: Environmental monitoring and analysis

## Challenges by Location

| Location | Challenge | Solution |
|----------|-----------|----------|
| Serengeti | Fast-moving wildlife | Increase capture rate, multi-frame tracking |
| Etna | Steam/ash | Use thermal data if available |
| Reef | Water turbidity | Tune color thresholds, use frequency analysis |
| Antarctica | Low light | Enhance contrast, use night vision modes |
| Kaziranga | Dense vegetation | Focus on silhouettes, movement tracking |

## Privacy & Ethics

- ✅ All streams are public and published
- ✅ No personal data involved
- ✅ Scientific/conservation purposes
- ✅ Educational use authorized
- ⚠️ Respect terms of service for each source
- ⚠️ Credit content sources in publications

## Links & Resources

- Serengeti Live: https://www.explorers.org/live-cams/serengeti-live
- Volcano Monitoring: https://www.usgs.gov/observe-earth
- Coral Reef: https://www.coral.org/live-coral-cam
- Antarctic Research: https://www.nsf.gov/geo/antarctic/
- Wildlife Cams: https://www.explorers.org/live-cams

## Troubleshooting

**Stream not available**
- Streams may be offline for maintenance
- Some are seasonal (safari dry/wet seasons)
- Check internet connection and firewall

**Low frame rate**
- Reduce detection classes to speed up processing
- Increase capture interval
- Check API response times

**Detection accuracy issues**
- Challenging environments! Expected for some locations
- Underwater: color shifts, low contrast
- Polar: extreme lighting, reflection
- Savanna: movement blur, dust
