#!/usr/bin/env python3
"""
Quick integration test - shows YDC → Adapter → Geolocation-Engine2 working

This simulates the full flow without needing actual YDC running.
"""
import asyncio
import json
import httpx
import base64
from datetime import datetime


async def simulate_detection():
    """Simulate what happens when YDC detects an object"""

    print("=" * 60)
    print("YDC ↔ Geolocation-Engine2 Integration Demo")
    print("=" * 60)
    print()

    # Simulate YDC detection
    print("📷 YDC detects an object in the video feed:")
    ydc_detection = {
        "x": 400,
        "y": 300,
        "width": 100,
        "height": 80,
        "class": "vehicle",
        "confidence": 0.95,
    }
    print(f"   {json.dumps(ydc_detection, indent=2)}")
    print()

    # Adapter processes it
    print("🔄 Adapter processes the detection:")
    pixel_x = ydc_detection["x"] + ydc_detection["width"] / 2
    pixel_y = ydc_detection["y"] + ydc_detection["height"] / 2
    print(f"   • Extract bbox center: pixel({pixel_x:.0f}, {pixel_y:.0f})")
    print(f"   • Add camera position: lat 40.7135, lon -74.0050, elevation 50m")
    print(f"   • Build geolocation-engine2 API payload...")
    print()

    # Create a minimal valid image (1×1 pixel transparent PNG)
    minimal_png = base64.b64encode(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    ).decode()

    # Build payload matching the API schema
    payload = {
        "image_base64": minimal_png,  # Required: base64-encoded image
        "pixel_x": pixel_x,
        "pixel_y": pixel_y,
        "object_class": ydc_detection["class"],  # Required
        "ai_confidence": ydc_detection["confidence"],  # Required
        "source": "ydc-adapter-demo",  # Required
        "camera_id": "laptop-webcam",  # Required
        "timestamp": datetime.utcnow().isoformat() + "Z",  # Required
        "sensor_metadata": {  # Required
            "location_lat": 40.7135,
            "location_lon": -74.0050,
            "location_elevation": 50.0,
            "heading": 0.0,
            "pitch": -30.0,
            "roll": 0.0,
            "focal_length": 3000.0,
            "sensor_width_mm": 6.4,
            "sensor_height_mm": 4.8,
            "image_width": 1920,
            "image_height": 1440,
        },
    }

    print("📤 Sending to Geolocation-Engine2 API:")
    print(f"   POST http://localhost:8000/api/v1/detections")
    print()

    # Call geolocation-engine2
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                "http://localhost:8000/api/v1/detections",
                json=payload,
            )

        if response.status_code == 201:
            # Response is XML (CoT format)
            cot_xml = response.text
            print("✅ Success! Geolocation-Engine2 calculated world coordinates:")
            print()
            print("🎯 Response Headers:")
            print(f"   Detection ID: {response.headers.get('X-Detection-ID')}")
            print(f"   Confidence Flag: {response.headers.get('X-Confidence-Flag')}")
            print()
            print("📋 CoT/TAK XML Output (for TAK system):")
            # Pretty print the XML
            lines = cot_xml.split("><")
            for i, line in enumerate(lines[:3]):  # Show first 3 lines
                if i == 0:
                    print(f"   {line}>")
                else:
                    print(f"   <{line}>")
            print("   ...")
            print()
            print("🗺️  Result automatically pushed to TAK/ATAK server for map display")
            print()
            print("=" * 70)
            print("✅ Integration working!")
            print("   YDC Detection → Adapter → Geolocation-Engine2 → CoT XML → TAK")
            print("=" * 70)
        else:
            print(f"❌ API Error: {response.status_code}")
            print(response.text)

    except Exception as e:
        print(f"❌ Connection error: {e}")
        print()
        print("Make sure Geolocation-Engine2 API is running:")
        print("  cd /workspaces/geolocation-engine2")
        print("  python -m uvicorn src.main:app --host localhost --port 8000")


if __name__ == "__main__":
    asyncio.run(simulate_detection())
