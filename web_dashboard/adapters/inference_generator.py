#!/usr/bin/env python3
"""
Simple Local Inference Generator
Generates realistic object detections without any external APIs
"""
import numpy as np
from typing import List, Dict
from datetime import datetime


class InferenceGenerator:
    """Generate realistic AI detections locally"""

    # Object classes that would be detected
    OBJECT_CLASSES = [
        "person", "car", "dog", "cat", "bird", "bicycle",
        "bus", "truck", "building", "tree", "traffic_light",
        "stop_sign", "motorcycle", "bench", "backpack",
    ]

    # Confidence distribution (more realistic)
    CONFIDENCE_RANGES = {
        "high": (0.85, 0.99),      # Very confident detections
        "medium": (0.70, 0.84),    # Good detections
        "low": (0.50, 0.69),       # Weaker detections
    }

    def __init__(self, seed=None):
        """Initialize with optional seed for reproducibility"""
        if seed is not None:
            np.random.seed(seed)

    def generate_detections(
        self,
        num_objects: int = None,
        image_width: int = 1920,
        image_height: int = 1440,
        confidence_bias: str = "medium",
    ) -> List[Dict]:
        """
        Generate realistic detections

        Args:
            num_objects: Number of objects to detect (random 1-4 if None)
            image_width: Image width in pixels
            image_height: Image height in pixels
            confidence_bias: "high", "medium", or "low" confidence bias

        Returns:
            List of detection dicts with pixel_x, pixel_y, object_class, ai_confidence
        """
        if num_objects is None:
            num_objects = np.random.randint(1, 5)

        detections = []
        conf_range = self.CONFIDENCE_RANGES.get(confidence_bias, self.CONFIDENCE_RANGES["medium"])

        for _ in range(num_objects):
            # Random pixel location (avoid edges)
            pixel_x = float(np.random.randint(int(image_width * 0.1), int(image_width * 0.9)))
            pixel_y = float(np.random.randint(int(image_height * 0.1), int(image_height * 0.9)))

            # Random object class
            obj_class = str(np.random.choice(self.OBJECT_CLASSES))

            # Random confidence in specified range
            confidence = float(np.random.uniform(conf_range[0], conf_range[1]))

            detection = {
                "pixel_x": pixel_x,
                "pixel_y": pixel_y,
                "object_class": obj_class,
                "ai_confidence": confidence,
                "timestamp": datetime.utcnow().isoformat(),
            }

            detections.append(detection)

        return detections


if __name__ == "__main__":
    gen = InferenceGenerator()
    print("Generated Detections:")
    print("=" * 50)
    detections = gen.generate_detections(num_objects=3)
    for d in detections:
        print(f"  {d['object_class']:12} @ ({d['pixel_x']:.0f}, {d['pixel_y']:.0f}) - {d['ai_confidence']:.1%}")
