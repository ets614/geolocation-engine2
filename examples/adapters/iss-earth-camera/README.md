# 🛰️ ISS Earth Camera Adapter

Capture frames from the **International Space Station** live video feed and geolocate objects detected on Earth!

## What is this?

The ISS orbits Earth at ~400km altitude with a live HD camera broadcasting continuously. This adapter:
1. **Connects** to NASA's ISS live stream
2. **Captures** frames from the video feed
3. **Fetches** current ISS position from NASA API
4. **Processes** each frame through geolocation-engine2
5. **Shows** results in real-time

Perfect for testing your geolocation system with:
- ✅ Rapidly changing geography
- ✅ Extreme elevation (400km)
- ✅ Nadir view (straight down)
- ✅ Real-time dynamic data

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Make sure geolocation-engine2 API is running (default: http://localhost:8000)

# Run the adapter
python adapter.py
```

## Features

- 🛰️ **Live NASA ISS Feed**: HD video stream from space
- 📍 **Real ISS Position**: Updates via NASA API
- 🎥 **Frame Capture**: Extracts frames at intervals
- 📊 **Geolocation**: Processes each frame through your engine
- 📈 **Real-Time Tracking**: Watch detection results update live

## Requirements

- Python 3.9+
- ffmpeg (for video stream handling)
  ```bash
  # Ubuntu/Debian
  sudo apt-get install ffmpeg

  # macOS
  brew install ffmpeg
  ```

## Configuration

Edit `adapter.py` and modify:

```python
adapter = ISSCameraAdapter(
    geolocation_url="http://localhost:8000",  # Your geolocation API
    capture_interval=5,  # Seconds between frame captures
)
```

## Data Flow

```
NASA ISS Stream
    ↓
[OpenCV/ffmpeg]
    ↓
Capture Frames (every N seconds)
    ↓
Fetch ISS Position (NASA API)
    ↓
Send to Geolocation Engine
    ↓
Display Results
    ↓
Audit Trail → Offline Queue → TAK Push
```

## Example Output

```
🛰️  Connecting to ISS live feed...
✅ Connected to ISS feed!
🛰️  Frame 150 processed:
    ISS Position: -15.23°, 142.56° (alt: 400km)
    Detected location: -15.2234°, 142.5712°
    Confidence: 87.34%
```

## Tips

- 🔍 **Best viewing**: When ISS passes over illuminated areas (daytime on Earth)
- 📱 **Track ISS**: Visit https://www.n2yo.com/ to see current ISS position
- 🎯 **Accuracy**: Test against known landmarks visible from ISS (deserts, lakes, mountains)
- ⚡ **Performance**: Start with `capture_interval=10` for slower systems

## Links

- NASA ISS Live: https://www.nasa.gov/live/
- ISS Position API: http://api.open-notify.org/iss-now.json
- ISS Tracker: https://www.n2yo.com/

## Troubleshooting

**ffmpeg not found**
```bash
# Install ffmpeg first
sudo apt-get install ffmpeg  # Linux
brew install ffmpeg           # macOS
```

**Can't connect to stream**
- Check internet connection
- ISS stream sometimes goes down for maintenance
- Verify `capture_interval` isn't too aggressive

**Geolocation API errors**
- Make sure geolocation-engine2 is running on http://localhost:8000
- Check API logs for error details
- Verify image format is JPEG
