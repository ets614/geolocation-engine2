#!/usr/bin/env python3
"""
Adapter Worker Service
Runs live camera adapters and streams results to the dashboard
"""
import asyncio
import httpx
import numpy as np
import base64
from datetime import datetime
from typing import Dict, List, Callable
import json


# Minimal valid PNG for testing
MINIMAL_PNG = base64.b64encode(
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
).decode()


class AdapterWorker:
    """Runs a single adapter feed and streams results"""

    ADAPTERS = {
        # Landmarks
        "times-square": {
            "name": "Times Square, NYC",
            "lat": 40.7580,
            "lon": -73.9855,
            "elevation": 30.0,
            "icon": "🗽",
            "category": "landmarks"
        },
        "eiffel-tower": {
            "name": "Eiffel Tower, Paris",
            "lat": 48.8584,
            "lon": 2.2945,
            "elevation": 100.0,
            "icon": "🗼",
            "category": "landmarks"
        },
        "tokyo-tower": {
            "name": "Tokyo Tower, Japan",
            "lat": 35.6750,
            "lon": 139.7396,
            "elevation": 150.0,
            "icon": "🗾",
            "category": "landmarks"
        },
        "christ-redeemer": {
            "name": "Christ the Redeemer, Rio",
            "lat": -22.9519,
            "lon": -43.2105,
            "elevation": 380.0,
            "icon": "🗿",
            "category": "landmarks"
        },
        "big-ben": {
            "name": "Big Ben, London",
            "lat": 51.4975,
            "lon": -0.1357,
            "elevation": 50.0,
            "icon": "🏛️",
            "category": "landmarks"
        },
        # ISS - Space
        "iss-earth": {
            "name": "ISS Earth Camera (Orbital)",
            "lat": 0.0,  # Varies, updated from API
            "lon": 0.0,  # Varies, updated from API
            "elevation": 400000.0,  # 400km altitude
            "icon": "🛰️",
            "category": "space"
        },
        # Traffic Cameras
        "ca-highway-101": {
            "name": "CA Highway 101 South",
            "lat": 37.7749,
            "lon": -122.4194,
            "elevation": 15.0,
            "icon": "🚗",
            "category": "traffic"
        },
        "la-highway-405": {
            "name": "LA Highway I-405",
            "lat": 34.0522,
            "lon": -118.2437,
            "elevation": 15.0,
            "icon": "🚗",
            "category": "traffic"
        },
        # Wildlife
        "serengeti-safari": {
            "name": "Serengeti National Park",
            "lat": -2.3333,
            "lon": 34.8888,
            "elevation": 1500.0,
            "icon": "🦁",
            "category": "wildlife"
        },
        "mount-etna": {
            "name": "Mount Etna Volcano",
            "lat": 37.7511,
            "lon": 15.0034,
            "elevation": 3300.0,
            "icon": "🌋",
            "category": "wildlife"
        },
        "great-barrier-reef": {
            "name": "Great Barrier Reef",
            "lat": -18.2871,
            "lon": 147.6992,
            "elevation": 0.0,
            "icon": "🐠",
            "category": "wildlife"
        },
    }

    def __init__(
        self,
        adapter_id: str,
        geolocation_url: str = "http://localhost:8000",
        on_detection: Callable = None,
    ):
        self.adapter_id = adapter_id
        self.geolocation_url = geolocation_url
        self.on_detection = on_detection or self._default_callback
        self.adapter_config = self.ADAPTERS.get(adapter_id)
        self.running = False
        self.detection_count = 0
        self.cot_count = 0

    def _default_callback(self, detection: Dict):
        """Default callback - print to console"""
        print(json.dumps(detection, indent=2))

    async def process_frame(self) -> Dict:
        """Process a single frame and return detection"""
        if not self.adapter_config:
            raise ValueError(f"Adapter {self.adapter_id} not found")

        config = self.adapter_config

        # Simulate detection at random pixel location
        pixel_x = float(np.random.randint(200, 1720))
        pixel_y = float(np.random.randint(150, 1290))
        confidence = float(np.random.uniform(0.70, 0.98))

        # Build geolocation API payload
        payload = {
            "image_base64": MINIMAL_PNG,
            "pixel_x": pixel_x,
            "pixel_y": pixel_y,
            "object_class": "landmark",
            "ai_confidence": confidence,
            "source": f"adapter-{self.adapter_id}",
            "camera_id": self.adapter_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "sensor_metadata": {
                "location_lat": config["lat"],
                "location_lon": config["lon"],
                "location_elevation": config["elevation"],
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

        result = {
            "adapter_id": self.adapter_id,
            "adapter_name": config["name"],
            "timestamp": datetime.utcnow().isoformat(),
            "pixel_x": pixel_x,
            "pixel_y": pixel_y,
            "ai_confidence": confidence,
            "status": "processing",
            "error": None,
        }

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{self.geolocation_url}/api/v1/detections",
                    json=payload,
                )

            if response.status_code == 201:
                self.detection_count += 1
                self.cot_count += 1

                result["status"] = "success"
                result["detection_id"] = response.headers.get("X-Detection-ID")
                result["confidence_flag"] = response.headers.get("X-Confidence-Flag")
                result["cot_xml"] = response.text

                # Callback to dashboard
                await self.on_detection(result)

                return result
            else:
                result["status"] = "error"
                result["error"] = f"API returned {response.status_code}"

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

        await self.on_detection(result)
        return result

    async def run_continuous(self, interval: float = 2.0):
        """Run adapter continuously, processing frames at interval"""
        self.running = True
        print(f"🚀 Started adapter: {self.adapter_config['name']}")

        try:
            while self.running:
                await self.process_frame()
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            print(f"⏹️  Stopped adapter: {self.adapter_config['name']}")
        except Exception as e:
            print(f"❌ Error in adapter {self.adapter_id}: {e}")
        finally:
            self.running = False

    def stop(self):
        """Stop the adapter"""
        self.running = False


class WorkerManager:
    """Manages multiple adapter workers"""

    def __init__(self, geolocation_url: str = "http://localhost:8000"):
        self.geolocation_url = geolocation_url
        self.workers: Dict[str, AdapterWorker] = {}
        self.tasks: Dict[str, asyncio.Task] = {}
        self.detection_queue: asyncio.Queue = asyncio.Queue()

    async def start_adapter(self, adapter_id: str) -> AdapterWorker:
        """Start an adapter"""
        if adapter_id in self.workers and self.workers[adapter_id].running:
            return self.workers[adapter_id]

        worker = AdapterWorker(
            adapter_id,
            geolocation_url=self.geolocation_url,
            on_detection=self._on_detection,
        )

        self.workers[adapter_id] = worker

        # Create task to run adapter
        task = asyncio.create_task(worker.run_continuous(interval=1.5))
        self.tasks[adapter_id] = task

        return worker

    async def stop_adapter(self, adapter_id: str):
        """Stop an adapter"""
        if adapter_id in self.workers:
            self.workers[adapter_id].stop()

        if adapter_id in self.tasks:
            self.tasks[adapter_id].cancel()
            try:
                await self.tasks[adapter_id]
            except asyncio.CancelledError:
                pass

    def get_worker_status(self, adapter_id: str) -> Dict:
        """Get status of a worker"""
        if adapter_id not in self.workers:
            return {"status": "not_started"}

        worker = self.workers[adapter_id]
        return {
            "status": "running" if worker.running else "stopped",
            "adapter_id": adapter_id,
            "adapter_name": worker.adapter_config["name"],
            "detections": worker.detection_count,
            "cot_generated": worker.cot_count,
        }

    async def _on_detection(self, detection: Dict):
        """Handle detection from any worker"""
        await self.detection_queue.put(detection)

    async def get_detections_stream(self):
        """Get stream of detections"""
        while True:
            detection = await self.detection_queue.get()
            yield detection


# Global manager instance
manager = WorkerManager()


async def main():
    """Demo: run all adapters"""
    print("🌍 Starting Adapter Worker Service")
    print("=" * 70)

    # Start all adapters
    for adapter_id in AdapterWorker.ADAPTERS.keys():
        await manager.start_adapter(adapter_id)
        await asyncio.sleep(0.5)

    print("\n✅ All adapters started. Processing frames...\n")

    # Run for demo duration
    try:
        await asyncio.sleep(60)
    except KeyboardInterrupt:
        print("\n⏹️  Stopping...")

    # Stop all adapters
    for adapter_id in manager.workers.keys():
        await manager.stop_adapter(adapter_id)

    # Print stats
    print("\n📊 Final Statistics:")
    for adapter_id, worker in manager.workers.items():
        print(
            f"  {worker.adapter_config['icon']} {worker.adapter_config['name']}: "
            f"{worker.detection_count} detections"
        )


if __name__ == "__main__":
    asyncio.run(main())
