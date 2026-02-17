#!/usr/bin/env python3
"""
EarthCam Landmarks to Geolocation-Engine2 Adapter

Captures frames from public EarthCam webcams around the world
and processes them through the geolocation engine for validation.

Famous landmarks with known GPS coordinates - perfect for accuracy testing!
"""
import asyncio
import cv2
import numpy as np
import httpx
import tempfile
from pathlib import Path
from typing import Dict, List
import random


class EarthCamLandmark:
    """Represents a landmark with stream URL and coordinates"""
    def __init__(self, name: str, url: str, lat: float, lon: float, elevation: float = 0):
        self.name = name
        self.url = url
        self.latitude = lat
        self.longitude = lon
        self.elevation = elevation


class EarthCamAdapter:
    LANDMARKS = [
        EarthCamLandmark(
            "Times Square, NYC",
            "https://www.earthcam.com/usa/newyork/timessquare/",
            40.7580, -73.9855, 30.0
        ),
        EarthCamLandmark(
            "Eiffel Tower, Paris",
            "https://www.earthcam.com/world/france/paris/eiffeltower/",
            48.8584, 2.2945, 100.0
        ),
        EarthCamLandmark(
            "Tokyo Tower, Japan",
            "https://www.earthcam.com/world/japan/tokyo/tokyotower/",
            35.6750, 139.7396, 150.0
        ),
        EarthCamLandmark(
            "Christ the Redeemer, Rio",
            "https://www.earthcam.com/world/brazil/rio/christtheredeemer/",
            -22.9519, -43.2105, 380.0
        ),
        EarthCamLandmark(
            "Big Ben, London",
            "https://www.earthcam.com/world/unitedkingdom/london/bigben/",
            51.4975, -0.1357, 50.0
        ),
    ]

    def __init__(
        self,
        geolocation_url: str = "http://localhost:8000",
        landmark_names: List[str] = None,
    ):
        """
        Args:
            geolocation_url: Geolocation-Engine2 base URL
            landmark_names: List of landmark names to use (None = all)
        """
        self.geolocation_url = geolocation_url

        if landmark_names:
            self.landmarks = [l for l in self.LANDMARKS if l.name in landmark_names]
        else:
            self.landmarks = self.LANDMARKS

    async def capture_from_landmark(self, landmark: EarthCamLandmark, num_frames: int = 5):
        """Capture frames from a specific landmark"""
        print(f"\n📹 Capturing from: {landmark.name}")
        print(f"   Location: ({landmark.latitude:.4f}°, {landmark.longitude:.4f}°)")
        print(f"   Elevation: {landmark.elevation}m")

        try:
            cap = cv2.VideoCapture(landmark.url)

            if not cap.isOpened():
                print(f"⚠️  Could not connect to {landmark.name} stream")
                return

            frames_captured = 0
            while frames_captured < num_frames:
                ret, frame = cap.read()
                if not ret:
                    break

                frames_captured += 1
                await self.process_frame(frame, landmark)

            cap.release()

        except Exception as e:
            print(f"Error capturing from {landmark.name}: {e}")

    async def process_frame(self, frame: np.ndarray, landmark: EarthCamLandmark):
        """Send frame to geolocation engine"""
        try:
            # Save frame temporarily
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                cv2.imwrite(tmp.name, frame)

                # Random detection point in image (normally would use object detection)
                h, w = frame.shape[:2]
                pixel_x = np.random.randint(int(w * 0.2), int(w * 0.8))
                pixel_y = np.random.randint(int(h * 0.2), int(h * 0.8))

                # Prepare payload
                with open(tmp.name, "rb") as f:
                    files = {"image_file": ("frame.jpg", f, "image/jpeg")}
                    payload = {
                        "pixel_x": pixel_x,
                        "pixel_y": pixel_y,
                        "camera_latitude": landmark.latitude,
                        "camera_longitude": landmark.longitude,
                        "camera_elevation": landmark.elevation,
                        "camera_heading": np.random.uniform(0, 360),
                        "camera_pitch": np.random.uniform(-45, 45),
                        "camera_roll": 0.0,
                        "detection_class": "landmark",
                        "detection_confidence": np.random.uniform(0.7, 0.95),
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
                        lat_error = abs(result.get('latitude', 0) - landmark.latitude)
                        lon_error = abs(result.get('longitude', 0) - landmark.longitude)

                        print(
                            f"  ✅ Detection processed:\n"
                            f"     Expected: ({landmark.latitude:.4f}°, {landmark.longitude:.4f}°)\n"
                            f"     Got: ({result.get('latitude', 0):.4f}°, {result.get('longitude', 0):.4f}°)\n"
                            f"     Error: Δlat={lat_error:.4f}°, Δlon={lon_error:.4f}°\n"
                            f"     Confidence: {result.get('confidence', 0):.2%}"
                        )
                    else:
                        print(f"  ❌ API Error: {response.status_code}")

                Path(tmp.name).unlink()

        except Exception as e:
            print(f"Error processing frame: {e}")

    async def run_all_landmarks(self):
        """Cycle through all landmarks"""
        while True:
            landmark = random.choice(self.landmarks)
            await self.capture_from_landmark(landmark, num_frames=3)
            print(f"\n⏳ Waiting 30 seconds before next landmark...")
            await asyncio.sleep(30)

    def run(self):
        """Start the adapter"""
        print("🌍 EarthCam Landmarks Adapter")
        print(f"   Monitoring {len(self.landmarks)} landmarks")
        asyncio.run(self.run_all_landmarks())


if __name__ == "__main__":
    adapter = EarthCamAdapter(
        geolocation_url="http://localhost:8000",
        # Uncomment to test specific landmarks:
        # landmark_names=["Times Square, NYC", "Eiffel Tower, Paris"],
    )

    adapter.run()
