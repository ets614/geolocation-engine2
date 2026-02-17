# YDC → Geolocation-Engine2 Adapter (Simple Reference)

A minimal example adapter that connects YDC (YOLO object detector) to Geolocation-Engine2.

**Goal**: Show how to bridge YDC detections into real-world coordinates for TAK/ATAK.

---

## **What It Does**

```
YDC Detection (bbox + class + confidence)
  ↓
Extract bbox center → pixel coordinates
  ↓
Add mock camera position
  ↓
Send to Geolocation-Engine2 API
  ↓
Get back: lat, lon, accuracy
  ↓
(Geolocation-Engine2 pushes to TAK)
```

---

## **Quick Start (Local Laptop)**

### 1. Install dependencies
```bash
pip install websockets httpx
```

### 2. Update camera position
Edit `adapter.py` - change these to your location:
```python
adapter = YDCAdapter(
    camera_lat=40.7135,      # Your latitude
    camera_lon=-74.0050,     # Your longitude
    camera_elevation=50.0,   # Your elevation (meters)
)
```

### 3. Run
```bash
python adapter.py
```

**Expected output:**
```
Connecting to YDC at ws://localhost:5173/api/detections
Connected! Listening for detections...
✅ vehicle (92%): Lat 40.7138, Lon -74.0053
✅ person (87%): Lat 40.7135, Lon -74.0050
```

---

## **How to Extend**

### **Add Real Camera Position (Day 100)**

Instead of hardcoded position, get it from a camera/drone:

```python
class DJIProvider:
    async def get_position(self):
        # Connect to DJI SDK
        telemetry = await dji.get_telemetry()
        return {
            "latitude": telemetry.latitude,
            "longitude": telemetry.longitude,
            "elevation": telemetry.altitude,
            "heading": telemetry.yaw,
            "pitch": telemetry.pitch,
            "roll": telemetry.roll,
        }

# In adapter
async def get_camera_position(self):
    if USE_DJI:
        return await self.dji_provider.get_position()
    else:
        return self.mock_position
```

### **Add Camera Calibration**

If your camera has lens distortion or intrinsic matrix:

```python
payload = {
    # ... existing fields ...
    "camera_intrinsic_matrix": [
        [fx, 0, cx],
        [0, fy, cy],
        [0, 0, 1]
    ]
}
```

### **Handle Multiple Cameras**

```python
adapters = [
    YDCAdapter(..., camera_id="front", camera_heading=0),
    YDCAdapter(..., camera_id="left", camera_heading=-90),
]

for adapter in adapters:
    adapter.run()  # Each in separate thread
```

### **Add Filtering**

Only send high-confidence detections:

```python
if confidence < 0.75:
    return  # Skip low confidence

if class_name not in ["vehicle", "person", "aircraft"]:
    return  # Skip irrelevant classes
```

### **Add Batching**

Send multiple detections at once instead of one-by-one:

```python
async def process_batch(self, detections: list):
    payload = {
        "detections": [
            {
                "pixel_x": d["x"] + d["width"]/2,
                "pixel_y": d["y"] + d["height"]/2,
                "class": d["class"],
                "confidence": d["confidence"],
                # ... camera data ...
            }
            for d in detections
        ]
    }
    # Send as batch
```

---

## **Configuration**

### YDC WebSocket Endpoint
Find the correct URL for your YDC instance:
- Local dev: `ws://localhost:5173/api/detections`
- Docker: `ws://ydc:5173/api/detections`
- Remote: `ws://ydc.example.com/api/detections`

### Geolocation-Engine2 API
Default: `http://localhost:8001`

Check the main geolocation-engine2 README for API authentication (JWT/API Key).

---

## **Example: Multiple Adapters**

Run different adapters for different cameras:

```bash
# Terminal 1: Laptop webcam (hardcoded position)
python adapter.py

# Terminal 2: Drone (gets position from UAV telemetry)
python adapter.py --provider dji --ydc-url ws://drone:5173

# Terminal 3: Fixed camera (static position)
python adapter.py --camera-lat 40.7135 --camera-lon -74.0050 --static
```

---

## **Troubleshooting**

| Problem | Solution |
|---------|----------|
| Connection refused | Check YDC is running: `http://localhost:5173` |
| No detections | YDC may not be detecting anything. Check YDC web UI |
| 404 API error | Geolocation-Engine2 endpoint wrong. Check URL |
| Coordinates way off | Update camera position in code |

---

## **What's Next?**

- ✅ **This example**: Reference for simple adapters
- 📊 **Advanced**: See `/docs/feature/ydc-integration/` for production architecture
- 🤖 **Other cameras**: Add providers for DJI, MAVLink, custom telemetry
- 🗺️ **TAK Integration**: Geolocation-Engine2 already pushes to TAK - just works!

---

**Status**: Reference Example - Ready to extend
