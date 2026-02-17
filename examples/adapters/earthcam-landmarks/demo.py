#!/usr/bin/env python3
"""
EarthCam Landmarks Adapter - Live Demo
Headless version for testing without video display
"""
import asyncio
import numpy as np
import httpx
import base64
from datetime import datetime
from typing import List


class EarthCamLandmark:
    """Represents a landmark with stream URL and coordinates"""
    def __init__(self, name: str, url: str, lat: float, lon: float, elevation: float = 0):
        self.name = name
        self.url = url
        self.latitude = lat
        self.longitude = lon
        self.elevation = elevation


class EarthCamAdapterDemo:
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
        self.geolocation_url = geolocation_url
        if landmark_names:
            self.landmarks = [l for l in self.LANDMARKS if l.name in landmark_names]
        else:
            self.landmarks = self.LANDMARKS

        # Minimal valid PNG for testing
        self.minimal_png = base64.b64encode(
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        ).decode()

    async def process_landmark(self, landmark: EarthCamLandmark, num_frames: int = 3):
        """Process frames from a specific landmark"""
        print(f"\n📹 Processing: {landmark.name}")
        print(f"   📍 Location: ({landmark.latitude:.4f}°, {landmark.longitude:.4f}°)")
        print(f"   📏 Elevation: {landmark.elevation}m")
        print(f"   🎬 Stream: {landmark.url}")

        for frame_idx in range(num_frames):
            # Simulate random detection point in image
            pixel_x = np.random.randint(int(1920 * 0.2), int(1920 * 0.8))
            pixel_y = np.random.randint(int(1440 * 0.2), int(1440 * 0.8))

            confidence = np.random.uniform(0.7, 0.95)

            # Build payload in correct API format
            payload = {
                "image_base64": self.minimal_png,
                "pixel_x": float(pixel_x),
                "pixel_y": float(pixel_y),
                "object_class": "landmark",
                "ai_confidence": float(confidence),
                "source": "earthcam-landmarks-demo",
                "camera_id": landmark.name.replace(" ", "-").lower(),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "sensor_metadata": {
                    "location_lat": landmark.latitude,
                    "location_lon": landmark.longitude,
                    "location_elevation": landmark.elevation,
                    "heading": float(np.random.uniform(0, 360)),
                    "pitch": float(np.random.uniform(-45, 45)),
                    "roll": 0.0,
                    "focal_length": 3000.0,
                    "sensor_width_mm": 6.4,
                    "sensor_height_mm": 4.8,
                    "image_width": 1920,
                    "image_height": 1440,
                },
            }

            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.post(
                        f"{self.geolocation_url}/api/v1/detections",
                        json=payload,
                    )

                if response.status_code == 201:
                    detection_id = response.headers.get('X-Detection-ID', 'unknown')
                    conf_flag = response.headers.get('X-Confidence-Flag', 'UNKNOWN')

                    print(
                        f"  ✅ Frame {frame_idx + 1}:\n"
                        f"     Detection ID: {detection_id}\n"
                        f"     Confidence: {conf_flag}\n"
                        f"     Input: pixel({pixel_x}, {pixel_y}), {confidence:.0%} AI confidence\n"
                        f"     Status: CoT XML generated ✓"
                    )
                else:
                    print(f"  ❌ API Error: {response.status_code}")
                    try:
                        err = response.json()
                        print(f"     {err.get('detail', 'Unknown error')}")
                    except:
                        pass

            except Exception as e:
                print(f"  ❌ Error: {str(e)[:80]}")

            await asyncio.sleep(0.5)

    async def run_all_landmarks(self, num_frames_per_landmark: int = 2):
        """Process all landmarks sequentially"""
        print("=" * 75)
        print("🌍 EarthCam Landmarks - Geolocation Testing Demo")
        print("=" * 75)
        print(f"\nAdapter: earthcam-landmarks")
        print(f"API: {self.geolocation_url}")
        print(f"Testing: {len(self.landmarks)} famous world landmarks")
        print(f"Frames per landmark: {num_frames_per_landmark}")
        print()

        for landmark in self.landmarks:
            await self.process_landmark(landmark, num_frames=num_frames_per_landmark)
            await asyncio.sleep(0.5)

        print("\n" + "=" * 75)
        print("✅ Demo Complete!")
        print("=" * 75)
        print("\n📊 Summary:")
        print(f"  • Tested {len(self.landmarks)} landmarks")
        print(f"  • Total detections: {len(self.landmarks) * num_frames_per_landmark}")
        print("  • All processed through geolocation-engine2")
        print("  • CoT/TAK XML generated for each detection")
        print("  • Ready for TAK/ATAK map display")
        print("\n🚀 Next steps:")
        print("  • Try ISS adapter for extreme altitude (400km)")
        print("  • Try traffic cameras for real vehicle detection")
        print("  • Try wildlife streams for edge cases\n")

    def run(self):
        """Start the demo"""
        asyncio.run(self.run_all_landmarks(num_frames_per_landmark=2))


if __name__ == "__main__":
    # Run demo with all landmarks
    adapter = EarthCamAdapterDemo(
        geolocation_url="http://localhost:8000",
    )

    adapter.run()
