# YDC + Geolocation-Engine2 Integration: Implementation Guide

**Date**: 2026-02-15
**Audience**: Backend engineers implementing integration
**Status**: Ready for development
**Effort Estimate**: 40-60 hours (Phase 1)

---

## Quick Start: 5-Minute Overview

### What You're Building

An adapter service that connects YDC's object detection inference to geolocation-engine2, creating an end-to-end pipeline from live video → model inference → geolocation → tactical map.

```
[YDC Inference]
      ↓ REST POST (detection event)
[Adapter Service] (this)
      ↓ REST POST (formatted detection)
[Geolocation-Engine2]
      ↓ HTTP PUT (CoT XML)
[TAK/ATAK Map]
```

### Key Points

- **YDC outputs**: class, confidence, bounding box (pixel coordinates)
- **Geolocation-Engine2 needs**: pixel_x, pixel_y, camera metadata
- **You build**: Transform + Route + Error Handling

### Minimal Implementation

```python
# File: /ydc/adapters/geolocation_engine_adapter.py
# ~200 lines of Python code

import httpx
import base64
import cv2
from typing import Dict

async def push_detection_to_geo_engine(
    frame: np.ndarray,
    detection: Dict,  # YDC format
    camera_metadata: Dict
):
    # Convert bbox to pixel coords
    pixel_x = (detection['x1'] + detection['x2']) // 2
    pixel_y = (detection['y1'] + detection['y2']) // 2

    # Build geolocation-engine2 payload
    payload = {
        "image_base64": base64.b64encode(cv2.imencode('.jpg', frame)[1]).decode(),
        "pixel_x": pixel_x,
        "pixel_y": pixel_y,
        "object_class": map_class(detection['class_id']),
        "ai_confidence": detection['confidence'],
        "source": "ydc_live_inference",
        "sensor_metadata": camera_metadata
    }

    # POST to geolocation-engine2
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://geolocation-engine2:8000/api/v1/detections",
            json=payload,
            headers={"X-API-Key": "ydc-service-account"}
        )
        return response.status_code == 201
```

That's the core. The rest is error handling, retries, testing.

---

## Part 1: Understanding the Data Transformation

### YDC Detection Format

YDC's inference subsystem outputs detections in this format:

```python
{
    "class_id": 2,           # COCO class ID (0=person, 2=car, etc.)
    "class_name": "car",     # Human-readable class
    "confidence": 0.92,      # 0-1 scale
    "x1": 450,               # Bounding box (pixel coordinates)
    "y1": 350,               # Top-left corner
    "x2": 650,               # Bottom-right corner
    "y2": 500,
    "tracked_id": 123        # Optional: tracking ID across frames
}
```

### Geolocation-Engine2 Detection Format

Geolocation-Engine2 expects:

```python
{
    "image_base64": "iVBORw0KGgo...",  # JPEG frame as base64
    "pixel_x": 550,                      # Pixel X (required)
    "pixel_y": 425,                      # Pixel Y (required)
    "object_class": "vehicle",           # CoT class name
    "ai_confidence": 0.92,               # AI model confidence
    "source": "ydc_live_inference",      # Detection source
    "sensor_metadata": {                 # Camera pose + intrinsics
        "location_lat": 40.7128,
        "location_lon": -74.0060,
        "location_elevation": 100.0,
        "heading": 45.0,
        "pitch": -30.0,
        "roll": 0.0,
        "focal_length": 3000.0,
        "sensor_width_mm": 6.4,
        "sensor_height_mm": 4.8,
        "image_width": 1920,
        "image_height": 1440
    }
}
```

### Transformation Mapping

| YDC Field | Geo-Engine Field | Transformation |
|-----------|------------------|-----------------|
| x1, y1, x2, y2 | pixel_x, pixel_y | (x1+x2)/2, (y1+y2)/2 |
| confidence | ai_confidence | Use as-is (already 0-1) |
| class_id | object_class | Map via COCO→CoT lookup |
| (frame) | image_base64 | base64.encode(cv2.imencode(frame)) |
| (camera) | sensor_metadata | Get from YDC Feeds API |

---

## Part 2: Implementation Steps

### Step 1: Create Adapter Service Structure

```bash
# In YDC repository
mkdir -p ydc/adapters
touch ydc/adapters/__init__.py
touch ydc/adapters/geolocation_engine_adapter.py
touch ydc/adapters/config.py
touch ydc/adapters/class_mappings.py
touch tests/test_geolocation_adapter.py
```

### Step 2: Implement Class Mapping

File: `/ydc/adapters/class_mappings.py`

```python
"""Map YOLO class IDs to CoT-compatible class names"""

# COCO dataset class IDs (standard YOLO)
COCO_CLASSES = {
    0: "person",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    4: "airplane",
    5: "bus",
    6: "train",
    7: "truck",
    8: "boat",
    # ... etc
}

# Map COCO classes to CoT object_class values
# (what geolocation-engine2 understands)
COCO_TO_COT_MAP = {
    0: "person",         # person → person
    2: "vehicle",        # car → vehicle
    3: "vehicle",        # motorcycle → vehicle
    5: "vehicle",        # bus → vehicle
    7: "vehicle",        # truck → vehicle
    # Custom mappings for fine-tuned models
    # "vehicle_detector_v2": {
    #     0: "sedan",
    #     1: "truck",
    #     2: "bus"
    # }
}

def get_cot_class(class_id: int, model_name: str = "yolov8") -> str:
    """
    Convert YOLO class ID to CoT object_class

    Args:
        class_id: COCO class ID
        model_name: Model name for custom mappings

    Returns:
        CoT-compatible class name
    """
    # Check for model-specific mapping first
    if model_name in COCO_TO_COT_MAP:
        mapping = COCO_TO_COT_MAP[model_name]
        return mapping.get(class_id, "object")

    # Fall back to standard COCO mapping
    return COCO_TO_COT_MAP.get(class_id, "object")
```

### Step 3: Implement Core Adapter

File: `/ydc/adapters/geolocation_engine_adapter.py`

```python
"""
Adapter for pushing YDC detections to geolocation-engine2
"""

import asyncio
import base64
import logging
import cv2
import httpx
import numpy as np
from typing import Dict, Optional, List
from datetime import datetime
from .class_mappings import get_cot_class

logger = logging.getLogger(__name__)

class GeolocationEngineAdapter:
    """
    Converts YDC detection events to geolocation-engine2 format
    and handles delivery with comprehensive error handling.
    """

    def __init__(self,
                 geo_engine_url: str,
                 api_key: str,
                 max_retries: int = 3,
                 timeout: float = 10.0,
                 min_confidence: float = 0.5):
        """
        Initialize adapter.

        Args:
            geo_engine_url: Base URL of geolocation-engine2 (e.g., http://geo:8000)
            api_key: API key for authentication
            max_retries: Max retries on transient failures
            timeout: HTTP request timeout in seconds
            min_confidence: Only push detections above this confidence
        """
        self.geo_engine_url = geo_engine_url.rstrip('/')
        self.api_key = api_key
        self.max_retries = max_retries
        self.timeout = timeout
        self.min_confidence = min_confidence
        self.client = httpx.AsyncClient(timeout=timeout)

        # Stats
        self.stats = {
            'detections_processed': 0,
            'detections_sent': 0,
            'send_failures': 0,
            'last_send_time': None
        }

    async def process_detection(self,
                               frame: np.ndarray,
                               detection: Dict,
                               camera_metadata: Dict) -> bool:
        """
        Process a single YDC detection and push to geolocation-engine2.

        Args:
            frame: Image frame (np.ndarray, BGR)
            detection: YDC detection dict:
                      {class_id, confidence, x1, y1, x2, y2}
            camera_metadata: Camera pose and intrinsics:
                           {latitude, longitude, elevation,
                            heading, pitch, roll,
                            focal_length, sensor_width_mm, sensor_height_mm,
                            image_width, image_height}

        Returns:
            True if successfully posted, False otherwise
        """

        self.stats['detections_processed'] += 1

        # Filter by confidence
        confidence = detection.get('confidence', 0)
        if confidence < self.min_confidence:
            logger.debug(f"Skipping detection: confidence {confidence} "
                        f"below threshold {self.min_confidence}")
            return False

        try:
            # Validate inputs
            if frame is None or frame.size == 0:
                logger.error("Invalid frame provided")
                return False

            if not camera_metadata:
                logger.error("Missing camera metadata")
                return False

            # Extract detection components
            class_id = detection.get('class_id')
            x1 = detection.get('x1')
            y1 = detection.get('y1')
            x2 = detection.get('x2')
            y2 = detection.get('y2')

            # Validate required fields
            if any(v is None for v in [class_id, x1, y1, x2, y2]):
                logger.error(f"Missing detection fields: {detection}")
                return False

            # Convert bbox to center pixel coordinates
            pixel_x = int((x1 + x2) / 2)
            pixel_y = int((y1 + y2) / 2)

            # Validate pixel coordinates
            img_h, img_w = frame.shape[:2]
            if not (0 <= pixel_x < img_w and 0 <= pixel_y < img_h):
                logger.error(f"Invalid pixel coords ({pixel_x}, {pixel_y}) "
                            f"for image {img_w}x{img_h}")
                return False

            # Encode frame as base64 JPEG
            success, buffer = cv2.imencode('.jpg', frame)
            if not success:
                logger.error("Failed to encode frame as JPEG")
                return False

            image_base64 = base64.b64encode(buffer).decode('utf-8')

            # Build geolocation-engine2 payload
            payload = {
                "image_base64": image_base64,
                "pixel_x": pixel_x,
                "pixel_y": pixel_y,
                "object_class": get_cot_class(class_id),
                "ai_confidence": float(confidence),
                "source": "ydc_live_inference",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "sensor_metadata": {
                    "location_lat": camera_metadata.get('latitude'),
                    "location_lon": camera_metadata.get('longitude'),
                    "location_elevation": camera_metadata.get('elevation'),
                    "heading": camera_metadata.get('heading'),
                    "pitch": camera_metadata.get('pitch'),
                    "roll": camera_metadata.get('roll'),
                    "focal_length": camera_metadata.get('focal_length'),
                    "sensor_width_mm": camera_metadata.get('sensor_width_mm'),
                    "sensor_height_mm": camera_metadata.get('sensor_height_mm'),
                    "image_width": img_w,
                    "image_height": img_h
                }
            }

            # POST to geolocation-engine2 with retry
            success = await self._post_with_retry(payload)
            if success:
                self.stats['detections_sent'] += 1
                self.stats['last_send_time'] = datetime.utcnow()
            else:
                self.stats['send_failures'] += 1

            return success

        except Exception as e:
            logger.error(f"Error processing detection: {e}", exc_info=True)
            self.stats['send_failures'] += 1
            return False

    async def _post_with_retry(self, payload: Dict) -> bool:
        """
        Post detection to geolocation-engine2 with exponential backoff retry.

        Args:
            payload: Detection payload

        Returns:
            True if successful, False otherwise
        """

        endpoint = f"{self.geo_engine_url}/api/v1/detections"
        headers = {"X-API-Key": self.api_key}

        for attempt in range(self.max_retries):
            try:
                response = await self.client.post(
                    endpoint,
                    json=payload,
                    headers=headers
                )

                if response.status_code == 201:
                    logger.debug("Detection posted successfully")
                    return True

                elif response.status_code == 429:  # Rate limited
                    retry_after = int(
                        response.headers.get('Retry-After', 2 ** attempt)
                    )
                    logger.warning(f"Rate limited, backing off {retry_after}s")
                    await asyncio.sleep(retry_after)
                    continue

                elif response.status_code >= 500:  # Server error
                    logger.warning(f"Server error {response.status_code}, "
                                 f"retry {attempt + 1}/{self.max_retries}")
                    if attempt < self.max_retries - 1:
                        wait_time = 2 ** attempt  # Exponential backoff
                        await asyncio.sleep(wait_time)
                        continue
                    return False

                else:  # Client error (4xx) - don't retry
                    logger.error(f"Client error {response.status_code}: "
                               f"{response.text}")
                    return False

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"Network error: {e}, "
                                 f"retrying in {wait_time}s "
                                 f"({attempt + 1}/{self.max_retries})")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Failed after {self.max_retries} retries: {e}")
                    return False

            except Exception as e:
                logger.error(f"Unexpected error: {e}", exc_info=True)
                return False

        return False

    async def get_stats(self) -> Dict:
        """Get adapter statistics"""
        return self.stats.copy()

    async def close(self):
        """Clean up HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
```

### Step 4: Integration with YDC Inference

File: `/ydc/inference/detection_handler.py` (or similar in YDC)

```python
"""
Hook detection results to geolocation-engine2 adapter
"""

from ..adapters.geolocation_engine_adapter import GeolocationEngineAdapter
import logging

logger = logging.getLogger(__name__)

# Initialize adapter at startup
geo_adapter = None

async def initialize_geo_adapter(config):
    """Initialize adapter with config from environment/file"""
    global geo_adapter

    geo_engine_url = config.get('GEO_ENGINE_URL', 'http://localhost:8001')
    api_key = config.get('GEO_ENGINE_API_KEY', 'default-api-key')

    geo_adapter = GeolocationEngineAdapter(
        geo_engine_url=geo_engine_url,
        api_key=api_key,
        max_retries=3,
        min_confidence=0.5
    )

    logger.info(f"Initialized GeolocationEngineAdapter: {geo_engine_url}")

async def on_inference_complete(frame, detections, camera_metadata):
    """
    Callback when YOLO inference completes.
    Called by YDC inference subsystem.

    Args:
        frame: Image frame (np.ndarray)
        detections: List of detection dicts
        camera_metadata: Camera pose/intrinsics dict
    """

    if geo_adapter is None:
        logger.warning("GeolocationEngineAdapter not initialized")
        return

    # Filter and push high-confidence detections
    for detection in detections:
        confidence = detection.get('confidence', 0)

        # Only push confident detections
        if confidence > 0.5:
            try:
                success = await geo_adapter.process_detection(
                    frame,
                    detection,
                    camera_metadata
                )

                if not success:
                    logger.debug(f"Failed to push detection: {detection}")

            except Exception as e:
                logger.error(f"Error pushing detection: {e}", exc_info=True)

async def shutdown_geo_adapter():
    """Clean up adapter at shutdown"""
    global geo_adapter

    if geo_adapter:
        stats = await geo_adapter.get_stats()
        logger.info(f"Geo adapter stats: {stats}")
        await geo_adapter.close()
        geo_adapter = None
```

### Step 5: Configuration

File: `/ydc/.env.example`

```bash
# Geolocation Engine Integration
GEO_ENGINE_URL=http://localhost:8001
GEO_ENGINE_API_KEY=ydc-service-account

# Detection filtering
MIN_DETECTION_CONFIDENCE=0.5

# Adapter behavior
GEO_ENGINE_MAX_RETRIES=3
GEO_ENGINE_TIMEOUT=10.0
```

---

## Part 3: Testing

### Unit Tests

File: `/tests/test_geolocation_adapter.py`

```python
"""
Unit tests for GeolocationEngineAdapter
"""

import pytest
import numpy as np
import base64
from unittest.mock import Mock, AsyncMock, patch
from ydc.adapters.geolocation_engine_adapter import GeolocationEngineAdapter

@pytest.fixture
def adapter():
    """Create adapter instance"""
    return GeolocationEngineAdapter(
        geo_engine_url="http://localhost:8001",
        api_key="test-key"
    )

@pytest.fixture
def mock_frame():
    """Create mock image frame"""
    return np.zeros((1440, 1920, 3), dtype=np.uint8)

@pytest.fixture
def mock_detection():
    """Create mock YDC detection"""
    return {
        'class_id': 2,  # car
        'confidence': 0.92,
        'x1': 450,
        'y1': 350,
        'x2': 650,
        'y2': 500
    }

@pytest.fixture
def mock_camera_metadata():
    """Create mock camera metadata"""
    return {
        'latitude': 40.7128,
        'longitude': -74.0060,
        'elevation': 100.0,
        'heading': 45.0,
        'pitch': -30.0,
        'roll': 0.0,
        'focal_length': 3000.0,
        'sensor_width_mm': 6.4,
        'sensor_height_mm': 4.8
    }

@pytest.mark.asyncio
async def test_detection_transform_bbox_to_pixels(
    adapter, mock_frame, mock_detection, mock_camera_metadata
):
    """Test bbox center calculation"""

    # Mock HTTP client
    mock_response = AsyncMock()
    mock_response.status_code = 201

    with patch.object(adapter.client, 'post', return_value=mock_response):
        result = await adapter.process_detection(
            mock_frame,
            mock_detection,
            mock_camera_metadata
        )

    assert result is True

    # Verify called with correct pixel coords
    call_args = adapter.client.post.call_args
    payload = call_args.kwargs['json']

    # (450+650)/2 = 550, (350+500)/2 = 425
    assert payload['pixel_x'] == 550
    assert payload['pixel_y'] == 425

@pytest.mark.asyncio
async def test_filter_low_confidence(adapter, mock_frame, mock_camera_metadata):
    """Test filtering by confidence threshold"""

    low_conf_detection = {
        'class_id': 2,
        'confidence': 0.3,  # Below default threshold
        'x1': 100, 'y1': 100, 'x2': 200, 'y2': 200
    }

    result = await adapter.process_detection(
        mock_frame,
        low_conf_detection,
        mock_camera_metadata
    )

    # Should not POST if confidence below threshold
    assert result is False

@pytest.mark.asyncio
async def test_invalid_pixel_coords(adapter, mock_detection, mock_camera_metadata):
    """Test rejection of out-of-bounds pixel coordinates"""

    # Create frame
    frame = np.zeros((100, 100, 3), dtype=np.uint8)

    # Create detection with coords outside frame
    invalid_detection = {
        'class_id': 2,
        'confidence': 0.92,
        'x1': 500,   # Outside frame!
        'y1': 500,
        'x2': 600,
        'y2': 600
    }

    result = await adapter.process_detection(
        frame,
        invalid_detection,
        mock_camera_metadata
    )

    assert result is False

@pytest.mark.asyncio
async def test_retry_on_timeout(adapter, mock_frame, mock_detection, mock_camera_metadata):
    """Test exponential backoff on timeout"""

    # First call times out, second succeeds
    mock_response = AsyncMock()
    mock_response.status_code = 201

    side_effects = [
        Exception("Timeout"),
        Exception("Timeout"),
        mock_response
    ]

    with patch.object(adapter.client, 'post', side_effect=side_effects):
        result = await adapter.process_detection(
            mock_frame,
            mock_detection,
            mock_camera_metadata
        )

    # Should succeed after retries
    assert result is True

@pytest.mark.asyncio
async def test_rate_limit_handling(adapter, mock_frame, mock_detection, mock_camera_metadata):
    """Test 429 rate limit response"""

    mock_response = AsyncMock()
    mock_response.status_code = 429
    mock_response.headers = {'Retry-After': '1'}

    # First 429, then 201
    side_effects = [mock_response, AsyncMock(status_code=201)]

    with patch.object(adapter.client, 'post', side_effect=side_effects):
        with patch('asyncio.sleep'):  # Don't actually sleep in tests
            result = await adapter.process_detection(
                mock_frame,
                mock_detection,
                mock_camera_metadata
            )

    assert result is True

@pytest.mark.asyncio
async def test_stats_tracking(adapter, mock_frame, mock_detection, mock_camera_metadata):
    """Test statistics collection"""

    mock_response = AsyncMock()
    mock_response.status_code = 201

    with patch.object(adapter.client, 'post', return_value=mock_response):
        await adapter.process_detection(
            mock_frame,
            mock_detection,
            mock_camera_metadata
        )

    stats = await adapter.get_stats()

    assert stats['detections_processed'] == 1
    assert stats['detections_sent'] == 1
    assert stats['send_failures'] == 0
```

### Integration Test

```python
"""
Integration test: YDC → Adapter → Geolocation-Engine2 (mock)
"""

@pytest.mark.asyncio
async def test_end_to_end_detection_flow():
    """Test complete flow from YDC to geolocation-engine2"""

    # Start mock geolocation-engine2 server
    async with MockGeolocationServer() as mock_server:

        # Create adapter pointing to mock
        adapter = GeolocationEngineAdapter(
            geo_engine_url=f"http://localhost:{mock_server.port}",
            api_key="test-key"
        )

        # Create test data
        frame = create_test_frame(1920, 1440)
        detection = {
            'class_id': 2,
            'confidence': 0.92,
            'x1': 450, 'y1': 350, 'x2': 650, 'y2': 500
        }
        camera = create_test_camera_metadata()

        # Process detection
        result = await adapter.process_detection(frame, detection, camera)

        assert result is True

        # Verify mock server received request
        received = mock_server.get_last_request()
        assert received['pixel_x'] == 550
        assert received['pixel_y'] == 425
        assert received['object_class'] == 'vehicle'
        assert received['ai_confidence'] == 0.92
```

---

## Part 4: Deployment

### Local Development

```bash
# Terminal 1: Start geolocation-engine2
cd /path/to/geolocation-engine2
python -m uvicorn src.main:app --host 0.0.0.0 --port 8001

# Terminal 2: Start YDC
cd /path/to/ydc
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

# Terminal 3: Test integration
python -c "
import asyncio
from ydc.adapters.geolocation_engine_adapter import GeolocationEngineAdapter

async def test():
    adapter = GeolocationEngineAdapter(
        'http://localhost:8001',
        'test-key'
    )
    # ... test code
    await adapter.close()

asyncio.run(test())
"
```

### Docker Compose

```yaml
version: '3.8'
services:
  ydc:
    build: ./ydc
    ports:
      - "3000:3000"
      - "8000:8000"
    environment:
      - GEO_ENGINE_URL=http://geolocation-engine2:8000
      - GEO_ENGINE_API_KEY=ydc-service-account
    depends_on:
      - geolocation-engine2
    networks:
      - tactical

  geolocation-engine2:
    build: ./geolocation-engine2
    ports:
      - "8001:8000"
    environment:
      - TAK_SERVER_URL=http://tak-server:8080
      - DATABASE_URL=sqlite:////data/app.db
    volumes:
      - ./data:/data
    networks:
      - tactical

networks:
  tactical:
```

### Kubernetes

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ydc-config
data:
  GEO_ENGINE_URL: "http://geolocation-engine2:8000"
  GEO_ENGINE_API_KEY: "ydc-service-account"

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ydc
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ydc
  template:
    metadata:
      labels:
        app: ydc
    spec:
      containers:
      - name: ydc
        image: ydc:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: ydc-config
        - secretRef:
            name: ydc-secrets
```

---

## Part 5: Troubleshooting Guide

### Problem: Detection not reaching geolocation-engine2

**Symptoms**: YDC logs show detections, but geolocation-engine2 never receives them

**Debugging**:
```python
# Add logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check adapter stats
stats = await adapter.get_stats()
print(f"Processed: {stats['detections_processed']}")
print(f"Sent: {stats['detections_sent']}")
print(f"Failed: {stats['send_failures']}")

# Check network
curl -X GET http://geolocation-engine2:8000/api/v1/health
```

**Common Causes**:
1. geolocation-engine2 not running
2. Network connectivity issue
3. API key invalid
4. Detection confidence below threshold

---

### Problem: High latency (>500ms)

**Symptoms**: Detections reach TAK map slowly

**Investigation**:
```python
# Time each step
import time

start = time.time()
success = await adapter.process_detection(frame, detection, metadata)
elapsed = time.time() - start

print(f"Total latency: {elapsed*1000:.1f}ms")

# Check geolocation-engine2 latency
curl -w "@curl-format.txt" -o /dev/null -s \
  http://geolocation-engine2:8000/api/v1/health
```

**Common Causes**:
1. Image encoding too slow (large frame)
2. Network latency to geolocation-engine2
3. geolocation-engine2 photogrammetry expensive
4. TAK server slow response

**Solutions**:
- Reduce frame resolution
- Add local caching of camera metadata
- Batch multiple detections

---

### Problem: Detection dropped due to rate limiting

**Symptoms**: geolocation-engine2 returns 429 Too Many Requests

**Fix**:
```python
# Reduce detection sending rate
adapter = GeolocationEngineAdapter(
    geo_engine_url="...",
    api_key="...",
    max_retries=5,  # More patient retries
)

# Or reduce detection rate in YDC inference callback
if detection['confidence'] > 0.8:  # Higher threshold
    await adapter.process_detection(...)
```

---

## Part 6: Performance Optimization

### Reduce Payload Size

```python
# Instead of full JPEG frame, send only detection region
# (Reduce image_base64 size by 10-50x)

def get_detection_region(frame, detection, padding=50):
    """Extract just the detection region"""
    x1, y1, x2, y2 = detection['x1'], detection['y1'], \
                     detection['x2'], detection['y2']

    # Add padding
    x1 = max(0, x1 - padding)
    y1 = max(0, y1 - padding)
    x2 = min(frame.shape[1], x2 + padding)
    y2 = min(frame.shape[0], y2 + padding)

    return frame[y1:y2, x1:x2]
```

### Batch Detections

```python
# Instead of pushing each detection individually,
# collect a few and POST together

class BatchedAdapter(GeolocationEngineAdapter):
    def __init__(self, *args, batch_size=10, batch_timeout=1.0, **kwargs):
        super().__init__(*args, **kwargs)
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.batch_queue = []
        self.batch_task = None

    async def add_detection(self, frame, detection, camera_metadata):
        self.batch_queue.append((frame, detection, camera_metadata))

        if len(self.batch_queue) >= self.batch_size:
            await self._flush_batch()

    async def _flush_batch(self):
        # POST multiple detections at once
        payloads = [
            self._build_payload(f, d, c)
            for f, d, c in self.batch_queue
        ]

        # Geolocation-engine2 could support batch endpoint
        await self.client.post(
            f"{self.geo_engine_url}/api/v1/detections/batch",
            json={"detections": payloads},
            headers={"X-API-Key": self.api_key}
        )

        self.batch_queue = []
```

---

## Part 7: Monitoring & Observability

### Add Metrics

```python
from prometheus_client import Counter, Histogram

detection_counter = Counter(
    'ydc_detections_sent_total',
    'Total detections sent to geolocation-engine2',
    ['status', 'class']
)

send_latency = Histogram(
    'ydc_send_latency_seconds',
    'Latency sending detection to geolocation-engine2'
)

@send_latency.time()
async def process_detection(self, frame, detection, metadata):
    # ... existing code ...

    if success:
        detection_counter.labels(
            status='success',
            class=get_cot_class(detection['class_id'])
        ).inc()
```

### Structured Logging

```python
import json
from datetime import datetime

logger.info(
    json.dumps({
        'timestamp': datetime.utcnow().isoformat(),
        'event': 'detection_sent',
        'detection_id': detection_id,
        'class': class_name,
        'confidence': confidence,
        'pixel_x': pixel_x,
        'pixel_y': pixel_y,
        'latency_ms': latency
    })
)
```

---

## Checklist: Ready for Production

- [ ] Unit tests pass (100% code coverage of adapter)
- [ ] Integration tests pass (YDC → adapter → mock geo-engine)
- [ ] E2E test with real geolocation-engine2 and TAK mock
- [ ] Load test: 100+ detections/sec sustained
- [ ] Network failure test: adapter recovers correctly
- [ ] Configuration from environment variables
- [ ] Metrics exposed (Prometheus)
- [ ] Structured logging
- [ ] Docker image builds and runs
- [ ] Kubernetes manifests created and tested
- [ ] Documentation complete
- [ ] Rollback procedure tested
- [ ] Performance targets met: <500ms latency
- [ ] Security: API key handled securely
- [ ] Monitoring alerts configured

---

**Next Steps**: Follow this guide in order, test at each step, then deploy.

