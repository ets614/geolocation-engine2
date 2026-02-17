# 🚗 Traffic Camera Feeds Adapter

Test vehicle detection and localization using **real traffic camera streams** from highways, intersections, and urban areas!

## What is this?

Public traffic management agencies operate live cameras for traffic monitoring. This adapter:
1. **Connects** to public traffic camera streams (RTSP/MJPEG)
2. **Captures** real vehicle traffic data
3. **Sends** frames to geolocation-engine2
4. **Localizes** detected vehicles
5. **Tracks** vehicle movement over time

Perfect for:
- ✅ Real-world vehicle detection
- ✅ Dynamic content testing
- ✅ Urban geolocation scenarios
- ✅ Multi-object tracking validation

## Included Camera Locations

| Camera | Type | Location | Stream |
|--------|------|----------|--------|
| **CA-101 South** | Highway | San Francisco | RTSP (CALTRANS) |
| **I-405 North** | Highway | Los Angeles | RTSP (CALTRANS) |
| **Times Square** | Intersection | New York | RTSP (NYC DOT) |
| **Michigan Ave Bridge** | Bridge | Chicago | RTSP (Chicago DOT) |

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Make sure geolocation-engine2 API is running

# Run adapter
python adapter.py
```

## Configuration

Add your local traffic camera streams:

```python
CAMERAS = [
    TrafficCamera(
        "Your Highway Name",
        "rtsp://your-stream-url/path",
        latitude=37.7749,
        longitude=-122.4194,
        location_type="highway"
    ),
    # Add more...
]
```

## Finding Public Camera Streams

### California (CALTRANS)
```
https://cwwp2.dot.ca.gov/vm/feeds.htm
https://www.dot.ca.gov/programs/traffic-operations/find-real-time-traffic-information
```

### New York (NYC DOT)
```
https://a841-tfpwg.nyc.gov/
```

### RTSP Stream Formats
- `rtsp://camera-ip/stream1`
- `rtsp://camera-server:554/path/to/stream`
- `http://camera-ip:8080/mjpeg`

### YouTube Live Channels
Some cities broadcast on YouTube:
```
https://www.youtube.com/watch?v=traffic-stream-id
```

## Features

- 🚗 **Real Vehicles**: Actual traffic data
- 📍 **Multi-Detection**: Multiple vehicles per frame
- ⏱️ **Temporal Tracking**: Vehicle movement over time
- 🌍 **Real Coordinates**: Actual GPS locations
- 📊 **Live Stats**: Confidence and accuracy metrics

## Data Flow

```
Traffic Camera Stream (RTSP/MJPEG)
    ↓
Capture Frames
    ↓
Detect Vehicles (object detection)
    ↓
Calculate Pixel Coordinates
    ↓
Send to Geolocation Engine
    (with camera position + vehicle pixel location)
    ↓
Engine Localizes Vehicle
    ↓
Display Results
    ↓
Database/Queue/TAK Push
```

## Example Output

```
🚗 Traffic Camera Adapter
   Monitoring 4 cameras

🚗 Monitoring: CA-101 South (San Francisco)
   Type: highway
   Location: (37.7749°, -122.4194°)

  🚗 Vehicle detected:
     Camera: CA-101 South
     Geolocated to: (37.7751°, -122.4192°)
     Confidence: 89.23%

  🚗 Vehicle detected:
     Camera: CA-101 South
     Geolocated to: (37.7753°, -122.4189°)
     Confidence: 92.15%
```

## Tips

- 🎥 **Test Locally First**: Set up local RTSP server for testing
- 🔍 **Verify Coordinates**: Use Google Maps to verify camera locations
- ⏰ **Peak Hours**: Rush hour (7-9am, 4-7pm) has most vehicles
- 📹 **Resolution**: Higher resolution cameras = better localization
- 🌤️ **Lighting**: Best during daytime; night cameras may have poor quality

## Setting Up Local Test Stream

For development, create a mock RTSP server:

```bash
# Using GStreamer (Ubuntu)
gst-launch-1.0 videotestsrc ! \
  rtpvpayload ! \
  udpsink host=localhost port=5004

# Or use ffmpeg
ffmpeg -re -i test_video.mp4 -f rtsp rtsp://localhost:8554/stream
```

## Common Issues

**Can't connect to RTSP stream**
- RTSP ports often blocked by firewalls
- Some ISPs block RTSP traffic
- Try HTTP/MJPEG endpoints instead
- Verify camera IP is accessible

**No vehicles detected**
- May need dedicated object detection model
- Current code uses random simulation for demo
- Integrate with YOLO or similar for real detection

**High latency/buffering**
- RTSP streams can have 5-30s delay
- Reduce frame capture rate
- Check network bandwidth

## Integration Ideas

- 📊 **Dashboard**: Real-time traffic visualization
- 🚨 **Alerts**: Incident detection (accident, congestion)
- 📈 **Analytics**: Traffic flow analysis
- 🗺️ **Heatmaps**: Congestion mapping
- 🚓 **Law Enforcement**: Stolen vehicle detection

## Privacy & Legal

- ✅ Public traffic cameras are publicly available
- ✅ Data is already broadcast/published
- ⚠️ Check local regulations on video recording
- ⚠️ Vehicle plate reading may be restricted

## Links

- California DOT: https://www.dot.ca.gov/
- NYC Traffic: https://a841-tfpwg.nyc.gov/
- RTSP Reference: https://tools.ietf.org/html/rfc7826
