#!/usr/bin/env python3
"""
Simple YDC to Geolocation-Engine2 Adapter

Connects to YDC WebSocket, gets detections, sends to geolocation-engine2 API.
"""
import asyncio
import json
import httpx
import websockets
from typing import Optional


class YDCAdapter:
    def __init__(
        self,
        ydc_url: str = "ws://localhost:8000",
        geolocation_url: str = "http://localhost:8001",
        camera_lat: float = 40.7135,
        camera_lon: float = -74.0050,
        camera_elevation: float = 50.0,
        camera_heading: float = 0.0,
        camera_pitch: float = -30.0,
        camera_roll: float = 0.0,
    ):
        """
        Args:
            ydc_url: YDC WebSocket URL (e.g., ws://localhost:5173/api/detections)
            geolocation_url: Geolocation-Engine2 base URL
            camera_*: Mock camera position (update for real camera later)
        """
        self.ydc_url = ydc_url
        self.geolocation_url = geolocation_url
        self.camera = {
            "latitude": camera_lat,
            "longitude": camera_lon,
            "elevation": camera_elevation,
            "heading": camera_heading,
            "pitch": camera_pitch,
            "roll": camera_roll,
        }

    async def connect_and_listen(self):
        """Connect to YDC and process detections"""
        print(f"Connecting to YDC at {self.ydc_url}")

        try:
            async with websockets.connect(self.ydc_url) as websocket:
                print("Connected! Listening for detections...")

                async for message in websocket:
                    detection = json.loads(message)
                    await self.process_detection(detection)

        except Exception as e:
            print(f"Error: {e}")

    async def process_detection(self, detection: dict):
        """
        Convert YDC detection to geolocation-engine2 format and send

        YDC output example:
        {
          "x": 512,
          "y": 384,
          "width": 100,
          "height": 80,
          "class": "vehicle",
          "confidence": 0.92
        }
        """
        try:
            # Extract detection data
            x = detection.get("x", 0)
            y = detection.get("y", 0)
            width = detection.get("width", 0)
            height = detection.get("height", 0)
            class_name = detection.get("class", "unknown")
            confidence = detection.get("confidence", 0.0)

            # Convert bbox to pixel coordinates (center of bbox)
            pixel_x = x + width / 2
            pixel_y = y + height / 2

            # Build geolocation-engine2 API request
            payload = {
                "image_file": "ydc-stream",  # Placeholder - YDC doesn't upload images
                "pixel_x": pixel_x,
                "pixel_y": pixel_y,
                "camera_latitude": self.camera["latitude"],
                "camera_longitude": self.camera["longitude"],
                "camera_elevation": self.camera["elevation"],
                "camera_heading": self.camera["heading"],
                "camera_pitch": self.camera["pitch"],
                "camera_roll": self.camera["roll"],
                "detection_class": class_name,
                "detection_confidence": confidence,
            }

            # Send to geolocation-engine2
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.geolocation_url}/api/v1/detections",
                    json=payload,
                    timeout=5.0,
                )

            if response.status_code == 200:
                result = response.json()
                print(
                    f"✅ {class_name} ({confidence:.0%}): "
                    f"Lat {result.get('latitude', 0):.4f}, "
                    f"Lon {result.get('longitude', 0):.4f}"
                )
            else:
                print(f"❌ API Error: {response.status_code}")

        except Exception as e:
            print(f"Error processing detection: {e}")

    def run(self):
        """Start the adapter"""
        asyncio.run(self.connect_and_listen())


if __name__ == "__main__":
    # Configure here
    adapter = YDCAdapter(
        ydc_url="ws://localhost:5173",                 # YDC WebSocket endpoint
        geolocation_url="http://localhost:8000",       # Geolocation-Engine2 API
        camera_lat=40.7135,    # Your location (NYC example)
        camera_lon=-74.0050,
        camera_elevation=50.0,
        camera_heading=0.0,
        camera_pitch=-30.0,
        camera_roll=0.0,
    )

    adapter.run()
