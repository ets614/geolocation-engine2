#!/usr/bin/env python3
"""
Roboflow Real AI Detection Adapter
Connects to Roboflow cloud API for real object detection
Free tier: 100 inferences/month
"""
import httpx
import base64
import os
from typing import Dict, List, Optional
from datetime import datetime


class RoboflowDetector:
    """Real AI object detection via Roboflow cloud API"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "coco",
        confidence_threshold: float = 0.5,
    ):
        """
        Initialize Roboflow detector

        Args:
            api_key: Roboflow API key (or set ROBOFLOW_API_KEY env var)
            model: Model name (coco, openlogo, etc)
            confidence_threshold: Only return detections >= this confidence
        """
        self.api_key = api_key or os.getenv("ROBOFLOW_API_KEY")
        self.model = model
        self.confidence_threshold = confidence_threshold
        self.base_url = "https://detect.roboflow.com"

        if not self.api_key:
            raise ValueError(
                "ROBOFLOW_API_KEY required. Set env var or pass api_key parameter"
            )

    async def detect(self, image_base64: str) -> Dict:
        """
        Send image to Roboflow and get real AI detections

        Args:
            image_base64: Base64-encoded image string

        Returns:
            {
                "predictions": [
                    {
                        "x": 500,           # Center X pixel
                        "y": 300,           # Center Y pixel
                        "width": 150,
                        "height": 200,
                        "confidence": 0.92,
                        "class": "person"
                    },
                    ...
                ],
                "image": {"width": 1920, "height": 1440}
            }
        """
        try:
            # Decode base64 to binary
            image_bytes = base64.b64decode(image_base64)

            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{self.base_url}/{self.model}",
                    params={"api_key": self.api_key},
                    content=image_bytes,
                    headers={"Content-Type": "image/jpeg"},
                )

            if response.status_code == 200:
                data = response.json()

                # Filter by confidence threshold
                if "predictions" in data:
                    data["predictions"] = [
                        p
                        for p in data["predictions"]
                        if p.get("confidence", 0) >= self.confidence_threshold
                    ]

                return data

            return {
                "error": f"API returned {response.status_code}",
                "predictions": [],
            }

        except Exception as e:
            return {
                "error": str(e),
                "predictions": [],
            }

    async def detect_and_convert_pixels(
        self, image_base64: str, image_width: int = 1920, image_height: int = 1440
    ) -> List[Dict]:
        """
        Detect objects and convert to pixel coordinates for geolocation engine

        Returns list of detections in format:
        [
            {
                "pixel_x": 500,
                "pixel_y": 300,
                "object_class": "person",
                "ai_confidence": 0.92,
                "roboflow_data": {...}
            },
            ...
        ]
        """
        result = await self.detect(image_base64)

        if "error" in result:
            return []

        detections = []
        for pred in result.get("predictions", []):
            # Convert Roboflow format to geolocation format
            detection = {
                "pixel_x": float(pred.get("x", 0)),
                "pixel_y": float(pred.get("y", 0)),
                "object_class": pred.get("class", "unknown"),
                "ai_confidence": float(pred.get("confidence", 0)),
                "roboflow_data": pred,
            }
            detections.append(detection)

        return detections


class RoboflowAdapter:
    """Adapter to integrate Roboflow into worker service"""

    ADAPTERS = {
        "roboflow-coco": {
            "name": "🤖 Roboflow COCO (Real AI)",
            "lat": 40.7128,  # NYC default
            "lon": -74.0060,
            "elevation": 10.0,
            "icon": "🤖",
            "category": "ai",
            "detector_config": {"model": "coco", "confidence_threshold": 0.5},
        },
        "roboflow-openlogo": {
            "name": "🏷️ Roboflow Logos (Real AI)",
            "lat": 40.7128,
            "lon": -74.0060,
            "elevation": 10.0,
            "icon": "🏷️",
            "category": "ai",
            "detector_config": {"model": "openlogo", "confidence_threshold": 0.6},
        },
    }

    @staticmethod
    def get_detector(adapter_id: str) -> Optional[RoboflowDetector]:
        """Get RoboflowDetector for adapter"""
        if adapter_id not in RoboflowAdapter.ADAPTERS:
            return None

        config = RoboflowAdapter.ADAPTERS[adapter_id]
        detector_config = config.get("detector_config", {})

        return RoboflowDetector(**detector_config)


# Quick test
async def test():
    """Test Roboflow connection"""
    import base64

    # Minimal PNG for testing
    minimal_png = base64.b64encode(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    ).decode()

    detector = RoboflowDetector()
    result = await detector.detect(minimal_png)
    print("Roboflow Response:", result)


if __name__ == "__main__":
    import asyncio

    asyncio.run(test())
