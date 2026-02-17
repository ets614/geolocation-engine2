#!/usr/bin/env python3
"""
HuggingFace Inference API Real AI Detection Adapter
Access 1000+ pre-trained models on HuggingFace
Free tier: 30,000 inferences/month
"""
import httpx
import base64
import os
from typing import Dict, List, Optional
from datetime import datetime


class HuggingFaceDetector:
    """Real AI object detection via HuggingFace Inference API"""

    # Popular pre-trained models for object detection
    MODELS = {
        "facebook/detr-resnet-50": "COCO object detection (80 classes)",
        "facebook/detr-resnet-101": "COCO detection (higher accuracy)",
        "hustvl/yolos-tiny": "YOLO tiny (fast, lower memory)",
        "hustvl/yolos-base": "YOLO base (balanced)",
        "hustvl/yolos-large": "YOLO large (slower, more accurate)",
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "facebook/detr-resnet-50",
        confidence_threshold: float = 0.5,
    ):
        """
        Initialize HuggingFace detector

        Args:
            api_key: HuggingFace API token (or set HF_API_KEY env var)
            model: Model ID from huggingface.co
            confidence_threshold: Only return detections >= this confidence
        """
        self.api_key = api_key or os.getenv("HF_API_KEY")
        self.model = model
        self.confidence_threshold = confidence_threshold
        self.base_url = "https://api-inference.huggingface.co/models"

        if not self.api_key:
            raise ValueError(
                "HF_API_KEY required. Get at https://huggingface.co/settings/tokens"
            )

    async def detect(self, image_base64: str) -> Dict:
        """
        Send image to HuggingFace and get real AI detections

        Args:
            image_base64: Base64-encoded image string

        Returns:
            {
                "predictions": [
                    {
                        "score": 0.92,
                        "label": "person",
                        "box": {
                            "xmin": 400,
                            "ymin": 200,
                            "xmax": 600,
                            "ymax": 500
                        }
                    },
                    ...
                ]
            }
        """
        try:
            # Decode base64 to binary
            image_bytes = base64.b64decode(image_base64)

            headers = {"Authorization": f"Bearer {self.api_key}"}

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/{self.model}",
                    content=image_bytes,
                    headers=headers,
                )

            if response.status_code == 200:
                data = response.json()

                # Handle different response formats
                if isinstance(data, list):
                    # DETR format
                    predictions = [
                        p
                        for p in data
                        if float(p.get("score", 0)) >= self.confidence_threshold
                    ]
                    return {"predictions": predictions}
                else:
                    # Already formatted
                    return data

            # Check for rate limit
            if response.status_code == 429:
                return {
                    "error": "Rate limit exceeded. Free tier: 30k/month",
                    "predictions": [],
                }

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
                "hf_data": {...}
            },
            ...
        ]
        """
        result = await self.detect(image_base64)

        if "error" in result:
            return []

        detections = []
        for pred in result.get("predictions", []):
            # Convert HuggingFace format to geolocation format
            box = pred.get("box", {})

            # Calculate center pixel
            xmin = box.get("xmin", 0)
            ymin = box.get("ymin", 0)
            xmax = box.get("xmax", image_width)
            ymax = box.get("ymax", image_height)

            pixel_x = (xmin + xmax) / 2
            pixel_y = (ymin + ymax) / 2

            detection = {
                "pixel_x": float(pixel_x),
                "pixel_y": float(pixel_y),
                "object_class": pred.get("label", "unknown"),
                "ai_confidence": float(pred.get("score", 0)),
                "hf_data": pred,
            }
            detections.append(detection)

        return detections


class HuggingFaceAdapter:
    """Adapter to integrate HuggingFace into worker service"""

    ADAPTERS = {
        "huggingface-detr": {
            "name": "🤗 HuggingFace DETR (30k free)",
            "lat": 40.7128,  # NYC default
            "lon": -74.0060,
            "elevation": 10.0,
            "icon": "🤗",
            "category": "ai",
            "detector_config": {
                "model": "facebook/detr-resnet-50",
                "confidence_threshold": 0.5,
            },
        },
        "huggingface-yolos": {
            "name": "⚡ HuggingFace YOLOS (Fast)",
            "lat": 40.7128,
            "lon": -74.0060,
            "elevation": 10.0,
            "icon": "⚡",
            "category": "ai",
            "detector_config": {
                "model": "hustvl/yolos-tiny",
                "confidence_threshold": 0.5,
            },
        },
    }

    @staticmethod
    def get_detector(adapter_id: str) -> Optional[HuggingFaceDetector]:
        """Get HuggingFaceDetector for adapter"""
        if adapter_id not in HuggingFaceAdapter.ADAPTERS:
            return None

        config = HuggingFaceAdapter.ADAPTERS[adapter_id]
        detector_config = config.get("detector_config", {})

        return HuggingFaceDetector(**detector_config)


# Quick test
async def test():
    """Test HuggingFace connection"""
    import base64

    # Minimal PNG for testing
    minimal_png = base64.b64encode(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    ).decode()

    detector = HuggingFaceDetector()
    result = await detector.detect(minimal_png)
    print("HuggingFace Response:", result)


if __name__ == "__main__":
    import asyncio

    asyncio.run(test())
