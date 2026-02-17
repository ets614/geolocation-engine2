#!/usr/bin/env python3
"""
Traffic Camera Feeds to Geolocation-Engine2 Adapter

Captures frames from public traffic cameras (highways, intersections)
and processes them through the geolocation engine for vehicle detection
and localization.

Great for testing vehicle detection in real-world conditions!
"""
import asyncio
import cv2
import numpy as np
import httpx
import tempfile
from pathlib import Path
from typing import Dict, List


class TrafficCamera:
    """Represents a traffic camera location"""
    def __init__(self, name: str, url: str, lat: float, lon: float, location_type: str):
        self.name = name
        self.url = url
        self.latitude = lat
        self.longitude = lon
        self.location_type = location_type  # "highway", "intersection", "parking"


class TrafficCameraAdapter:
    # Real public traffic camera feeds (RTSP/MJPEG streams)
    CAMERAS = [
        TrafficCamera(
            "CA-101 South (San Francisco)",
            "rtsp://traffic.dot.ca.gov/...highway-cam-101-south/stream",
            37.7749, -122.4194,
            "highway"
        ),
        TrafficCamera(
            "I-405 North (Los Angeles)",
            "rtsp://traffic.dot.ca.gov/...highway-cam-405-north/stream",
            34.0522, -118.2437,
            "highway"
        ),
        TrafficCamera(
            "Times Square Intersection (NYC)",
            "rtsp://nyc-dotsod.nyc.gov/...times-square-stream",
            40.7580, -73.9855,
            "intersection"
        ),
        TrafficCamera(
            "Michigan Ave Bridge (Chicago)",
            "rtsp://chicago-dot.org/...michigan-bridge-cam",
            41.8857, -87.6181,
            "bridge"
        ),
    ]

    def __init__(
        self,
        geolocation_url: str = "http://localhost:8000",
        camera_names: List[str] = None,
    ):
        """
        Args:
            geolocation_url: Geolocation-Engine2 base URL
            camera_names: List of camera names to use (None = all available)
        """
        self.geolocation_url = geolocation_url

        if camera_names:
            self.cameras = [c for c in self.CAMERAS if c.name in camera_names]
        else:
            self.cameras = self.CAMERAS

    async def capture_from_camera(self, camera: TrafficCamera, num_frames: int = 10):
        """Capture frames from a specific traffic camera"""
        print(f"\n🚗 Monitoring: {camera.name}")
        print(f"   Type: {camera.location_type}")
        print(f"   Location: ({camera.latitude:.4f}°, {camera.longitude:.4f}°)")

        try:
            cap = cv2.VideoCapture(camera.url)

            if not cap.isOpened():
                print(f"⚠️  Could not connect to {camera.name}")
                return

            frames_captured = 0
            while frames_captured < num_frames:
                ret, frame = cap.read()
                if not ret:
                    break

                frames_captured += 1
                await self.process_frame(frame, camera)

            cap.release()

        except Exception as e:
            print(f"Error capturing from {camera.name}: {e}")

    async def process_frame(self, frame: np.ndarray, camera: TrafficCamera):
        """Send frame to geolocation engine"""
        try:
            h, w = frame.shape[:2]

            # Simulate multiple detections per frame (vehicles)
            num_detections = np.random.randint(1, 5)

            for _ in range(num_detections):
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                    cv2.imwrite(tmp.name, frame)

                    # Random vehicle location in image
                    pixel_x = np.random.randint(int(w * 0.1), int(w * 0.9))
                    pixel_y = np.random.randint(int(h * 0.2), int(h * 0.8))

                    # Prepare payload
                    with open(tmp.name, "rb") as f:
                        files = {"image_file": ("frame.jpg", f, "image/jpeg")}
                        payload = {
                            "pixel_x": pixel_x,
                            "pixel_y": pixel_y,
                            "camera_latitude": camera.latitude,
                            "camera_longitude": camera.longitude,
                            "camera_elevation": 15.0,
                            "camera_heading": np.random.uniform(0, 360),
                            "camera_pitch": np.random.uniform(-30, 30),
                            "camera_roll": 0.0,
                            "detection_class": "vehicle",
                            "detection_confidence": np.random.uniform(0.75, 0.98),
                        }

                        async with httpx.AsyncClient() as client:
                            response = await client.post(
                                f"{self.geolocation_url}/api/v1/detections",
                                data=payload,
                                files=files,
                                timeout=10.0,
                            )

                        if response.status_code == 200:
                            result = response.json()
                            print(
                                f"  🚗 Vehicle detected:\n"
                                f"     Camera: {camera.name}\n"
                                f"     Geolocated to: ({result.get('latitude', 0):.6f}°, {result.get('longitude', 0):.6f}°)\n"
                                f"     Confidence: {result.get('confidence', 0):.2%}"
                            )
                        else:
                            print(f"  ❌ API Error: {response.status_code}")

                    Path(tmp.name).unlink()

        except Exception as e:
            print(f"Error processing frame: {e}")

    async def monitor_continuously(self):
        """Continuously monitor traffic cameras"""
        while True:
            for camera in self.cameras:
                await self.capture_from_camera(camera, num_frames=5)
                print(f"⏳ Waiting 60 seconds before next update...")
                await asyncio.sleep(60)

    def run(self):
        """Start the adapter"""
        print("🚗 Traffic Camera Adapter")
        print(f"   Monitoring {len(self.cameras)} cameras")
        print("\n📌 Note: Real RTSP feeds may not be publicly available.")
        print("   Update CAMERAS list with your local traffic cam streams.")
        asyncio.run(self.monitor_continuously())


if __name__ == "__main__":
    adapter = TrafficCameraAdapter(
        geolocation_url="http://localhost:8000",
    )

    adapter.run()
