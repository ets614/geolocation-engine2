#!/usr/bin/env python3
"""
Wildlife & Nature Streams to Geolocation-Engine2 Adapter

Captures frames from live wildlife and nature cameras (African safari,
volcano monitoring, weather cameras) and processes them through the
geolocation engine for terrain and wildlife detection.

Perfect for testing in exotic locations and challenging lighting conditions!
"""
import asyncio
import cv2
import numpy as np
import httpx
import tempfile
from pathlib import Path
from typing import List


class WildlifeCamera:
    """Represents a wildlife/nature camera location"""
    def __init__(self, name: str, url: str, lat: float, lon: float, description: str):
        self.name = name
        self.url = url
        self.latitude = lat
        self.longitude = lon
        self.description = description


class WildlifeStreamAdapter:
    CAMERAS = [
        WildlifeCamera(
            "Serengeti National Park",
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Placeholder - African safari live
            -2.3333, 34.8888,
            "African savanna with wildlife"
        ),
        WildlifeCamera(
            "Mount Etna Volcano",
            "https://www.youtube.com/watch?v=SickmKVHpog",  # Placeholder - Sicily volcano cam
            37.7511, 15.0034,
            "Active volcano in Sicily"
        ),
        WildlifeCamera(
            "Great Barrier Reef",
            "https://www.youtube.com/watch?v=Wzo8b_8K9lc",  # Placeholder - reef cam
            -18.2871, 147.6992,
            "Underwater coral reef"
        ),
        WildlifeCamera(
            "Antarctic Research Station",
            "https://www.youtube.com/watch?v=LXb3EKWsInQ",  # Placeholder - Antarctica cam
            -70.0, 0.0,
            "Polar research and ice shelves"
        ),
        WildlifeCamera(
            "Kaziranga National Park",
            "https://www.youtube.com/watch?v=HDfGAGVRjfA",  # Placeholder - India wildlife cam
            26.6000, 93.5000,
            "Indian rhino habitat"
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

    async def capture_from_camera(self, camera: WildlifeCamera, num_frames: int = 8):
        """Capture frames from a wildlife camera"""
        print(f"\n🦁 Connecting to: {camera.name}")
        print(f"   {camera.description}")
        print(f"   Location: ({camera.latitude:.4f}°, {camera.longitude:.4f}°)")

        try:
            cap = cv2.VideoCapture(camera.url)

            if not cap.isOpened():
                print(f"⚠️  Could not connect to {camera.name}")
                print(f"   💡 Tip: Use actual YouTube/live stream URLs in production")
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

    async def process_frame(self, frame: np.ndarray, camera: WildlifeCamera):
        """Send frame to geolocation engine"""
        try:
            h, w = frame.shape[:2]

            # Random object detection (wildlife/terrain features)
            detection_classes = ["animal", "terrain_feature", "vegetation", "water"]
            detection_class = np.random.choice(detection_classes)

            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                cv2.imwrite(tmp.name, frame)

                # Random location in frame
                pixel_x = np.random.randint(int(w * 0.15), int(w * 0.85))
                pixel_y = np.random.randint(int(h * 0.15), int(h * 0.85))

                # Prepare payload
                with open(tmp.name, "rb") as f:
                    files = {"image_file": ("frame.jpg", f, "image/jpeg")}

                    # Variable pitch depending on camera type
                    if "underwater" in camera.description.lower():
                        pitch = np.random.uniform(-60, 60)  # Wide angle for underwater
                    elif "volcano" in camera.description.lower():
                        pitch = np.random.uniform(-45, 0)  # Downward looking
                    else:
                        pitch = np.random.uniform(-30, 30)  # Medium angle

                    payload = {
                        "pixel_x": pixel_x,
                        "pixel_y": pixel_y,
                        "camera_latitude": camera.latitude,
                        "camera_longitude": camera.longitude,
                        "camera_elevation": 100.0,  # Assume elevated
                        "camera_heading": np.random.uniform(0, 360),
                        "camera_pitch": pitch,
                        "camera_roll": 0.0,
                        "detection_class": detection_class,
                        "detection_confidence": np.random.uniform(0.70, 0.96),
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
                        emoji_map = {
                            "animal": "🦁",
                            "terrain_feature": "🏔️",
                            "vegetation": "🌿",
                            "water": "💧",
                        }
                        emoji = emoji_map.get(detection_class, "📍")

                        print(
                            f"  {emoji} {detection_class.title()} detected:\n"
                            f"     Location: {camera.name}\n"
                            f"     Geolocated to: ({result.get('latitude', 0):.4f}°, {result.get('longitude', 0):.4f}°)\n"
                            f"     Confidence: {result.get('confidence', 0):.2%}"
                        )
                    else:
                        print(f"  ❌ API Error: {response.status_code}")

                Path(tmp.name).unlink()

        except Exception as e:
            print(f"Error processing frame: {e}")

    async def monitor_continuously(self):
        """Continuously monitor wildlife cameras"""
        import random
        while True:
            camera = random.choice(self.cameras)
            await self.capture_from_camera(camera, num_frames=5)
            print(f"⏳ Waiting 45 seconds before next camera...")
            await asyncio.sleep(45)

    def run(self):
        """Start the adapter"""
        print("🦁 Wildlife & Nature Streams Adapter")
        print(f"   Monitoring {len(self.cameras)} exotic locations")
        print("\n📌 Note: Use actual YouTube live URLs or streaming services in production.")
        print("   Examples: youtube.com/live, twitch.tv, safari.com/live")
        asyncio.run(self.monitor_continuously())


if __name__ == "__main__":
    adapter = WildlifeStreamAdapter(
        geolocation_url="http://localhost:8000",
    )

    adapter.run()
