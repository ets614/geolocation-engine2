#!/usr/bin/env python3
"""
ISS Earth Camera to Geolocation-Engine2 Adapter

Captures frames from the International Space Station live video feed
and processes them through the geolocation engine.

Live stream: NASA ISS HD Earth Viewing Experiment
"""
import asyncio
import cv2
import numpy as np
import httpx
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional
import requests


class ISSCameraAdapter:
    # ISS current position is published via API
    ISS_API_URL = "http://api.open-notify.org/iss-now.json"
    # HLS stream URL (NASA ISS)
    ISS_STREAM_URL = "http://iss-hd-client.ustream.tv/video/3120508/chunklist.m3u8"

    def __init__(
        self,
        geolocation_url: str = "http://localhost:8000",
        capture_interval: int = 5,  # Capture frame every N seconds
    ):
        """
        Args:
            geolocation_url: Geolocation-Engine2 base URL
            capture_interval: Seconds between frame captures
        """
        self.geolocation_url = geolocation_url
        self.capture_interval = capture_interval
        self.frame_count = 0
        self.iss_position = {"latitude": 0, "longitude": 0, "altitude": 400}  # ISS ~400km altitude

    def get_iss_position(self) -> dict:
        """Fetch current ISS position from NASA API"""
        try:
            response = requests.get(self.ISS_API_URL, timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.iss_position["latitude"] = float(data["iss_position"]["latitude"])
                self.iss_position["longitude"] = float(data["iss_position"]["longitude"])
                self.iss_position["altitude"] = 400  # ISS altitude ~400km
                return self.iss_position
        except Exception as e:
            print(f"⚠️ Could not fetch ISS position: {e}")
        return self.iss_position

    async def capture_frames(self):
        """Capture frames from ISS stream"""
        print(f"🛰️  Connecting to ISS live feed...")
        print(f"    Stream: {self.ISS_STREAM_URL}")

        try:
            cap = cv2.VideoCapture(self.ISS_STREAM_URL)

            if not cap.isOpened():
                print("❌ Could not open ISS stream. Make sure ffmpeg is installed:")
                print("   Ubuntu: sudo apt-get install ffmpeg")
                print("   macOS: brew install ffmpeg")
                return

            print("✅ Connected to ISS feed!")

            while True:
                ret, frame = cap.read()
                if not ret:
                    print("Stream ended or disconnected")
                    break

                self.frame_count += 1

                # Process every Nth frame
                if self.frame_count % (30 * self.capture_interval) == 0:  # Assuming 30fps
                    await self.process_frame(frame)

                # Show frame with annotation
                cv2.putText(frame, f"ISS Live - Frame {self.frame_count}",
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.imshow("ISS Earth Camera", cv2.resize(frame, (800, 600)))

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

            cap.release()
            cv2.destroyAllWindows()

        except Exception as e:
            print(f"❌ Error: {e}")

    async def process_frame(self, frame: np.ndarray):
        """Send frame to geolocation engine"""
        try:
            # Update ISS position
            position = self.get_iss_position()

            # Save frame temporarily
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                cv2.imwrite(tmp.name, frame)

                # Random detection point for demo (normally would use object detection)
                h, w = frame.shape[:2]
                pixel_x = np.random.randint(0, w)
                pixel_y = np.random.randint(0, h)

                # Prepare payload
                with open(tmp.name, "rb") as f:
                    files = {"image_file": ("frame.jpg", f, "image/jpeg")}
                    payload = {
                        "pixel_x": pixel_x,
                        "pixel_y": pixel_y,
                        "camera_latitude": position["latitude"],
                        "camera_longitude": position["longitude"],
                        "camera_elevation": position["altitude"],
                        "camera_heading": 0.0,
                        "camera_pitch": -45.0,  # Nadir view (straight down)
                        "camera_roll": 0.0,
                        "detection_class": "terrain_feature",
                        "detection_confidence": 0.85,
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
                            f"🛰️  Frame {self.frame_count} processed:\n"
                            f"    ISS Position: {position['latitude']:.2f}°, {position['longitude']:.2f}° (alt: {position['altitude']}km)\n"
                            f"    Detected location: {result.get('latitude', 0):.4f}°, {result.get('longitude', 0):.4f}°\n"
                            f"    Confidence: {result.get('confidence', 0):.2%}"
                        )
                    else:
                        print(f"❌ API Error: {response.status_code}")

                Path(tmp.name).unlink()

        except Exception as e:
            print(f"Error processing frame: {e}")

    def run(self):
        """Start the adapter"""
        asyncio.run(self.capture_frames())


if __name__ == "__main__":
    adapter = ISSCameraAdapter(
        geolocation_url="http://localhost:8000",
        capture_interval=5,
    )

    adapter.run()
