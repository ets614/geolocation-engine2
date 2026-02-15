"""Cursor on Target (CoT) XML generation and TAK output service.

Generates standard ATAK CoT format for Tactical Assault Kit (TAK) systems.
Supports both XML generation and TAK server integration.
"""
import uuid
from datetime import datetime, timedelta
from xml.etree.ElementTree import Element, SubElement, tostring
from typing import Optional
from src.models.schemas import GeolocationValidationResult


class CotService:
    """Generate and manage Cursor on Target (CoT) XML for TAK integration."""

    # CoT event type mapping: detection class → CoT type code
    COT_TYPE_MAP = {
        "vehicle": "b-m-p-s-u-c",  # Civilian vehicle
        "armed_vehicle": "b-m-p-s-u-c-v-a",  # Armed vehicle variant
        "person": "b-m-p-s-p-w-g",  # Ground walking
        "aircraft": "b-m-p-a",  # Air platform
        "fire": "b-i-x-f-f",  # Fire/Building
        "unknown": "b-m-p-s-p-loc",  # Point location (generic)
    }

    # Confidence flag to TAK color mapping (RGB hex)
    CONFIDENCE_COLOR_MAP = {
        "GREEN": "-65536",   # Pure red (high confidence = attention)
        "YELLOW": "-256",    # Pure green (medium confidence)
        "RED": "-16711936",  # Pure blue (low confidence)
    }

    def __init__(self, tak_server_url: Optional[str] = None):
        """Initialize CoT service.

        Args:
            tak_server_url: Optional TAK server URL for pushing events
                           (e.g., http://tak-server:8080/CoT)
        """
        self.tak_server_url = tak_server_url

    def generate_cot_xml(
        self,
        detection_id: str,
        geolocation: GeolocationValidationResult,
        object_class: str,
        ai_confidence: float,
        camera_id: str,
        timestamp: datetime,
    ) -> str:
        """Generate CoT XML from geolocation result.

        Args:
            detection_id: Unique detection identifier
            geolocation: Calculated geolocation with confidence
            object_class: Detected object class (vehicle, person, etc.)
            ai_confidence: AI detection confidence (0-1)
            camera_id: Source camera identifier
            timestamp: Detection timestamp

        Returns:
            str: CoT XML as string
        """
        # Generate CoT UIDs
        cot_uid = f"Detection.{detection_id}"
        source_uid = f"Camera.{camera_id}"

        # Map object class to CoT type
        cot_type = self.COT_TYPE_MAP.get(object_class.lower(), self.COT_TYPE_MAP["unknown"])

        # Calculate time windows
        now_iso = timestamp.isoformat() + "Z" if not timestamp.isoformat().endswith("Z") else timestamp.isoformat()
        stale_time = (timestamp + timedelta(minutes=5)).isoformat() + "Z"

        # Create root event element
        event = Element("event")
        event.set("version", "2.0")
        event.set("uid", cot_uid)
        event.set("type", cot_type)
        event.set("time", now_iso)
        event.set("start", now_iso)
        event.set("stale", stale_time)

        # Point element with geolocation
        point = SubElement(event, "point")
        point.set("lat", str(geolocation.calculated_lat))
        point.set("lon", str(geolocation.calculated_lon))
        point.set("hae", "0.0")  # Height above ellipsoid
        point.set("ce", str(geolocation.uncertainty_radius_meters))  # Circular error (CEP)
        point.set("le", "9999999.0")  # Linear error

        # Detail element with metadata
        detail = SubElement(event, "detail")

        # Link to source
        link = SubElement(detail, "link")
        link.set("uid", source_uid)
        link.set("production_time", now_iso)
        link.set("type", "a-f-G-E-S")  # External source link

        # Archive flag
        SubElement(detail, "archive")

        # Color based on confidence
        color = SubElement(detail, "color")
        confidence_color = self.CONFIDENCE_COLOR_MAP.get(
            geolocation.confidence_flag, self.CONFIDENCE_COLOR_MAP["RED"]
        )
        color.set("value", confidence_color)

        # Remarks with detection info
        remarks = SubElement(detail, "remarks")
        confidence_flag_value = (
            geolocation.confidence_flag.value
            if hasattr(geolocation.confidence_flag, "value")
            else geolocation.confidence_flag
        )
        remarks_text = (
            f"AI Detection: {object_class.capitalize()} | "
            f"AI Confidence: {int(ai_confidence * 100)}% | "
            f"Geo Confidence: {confidence_flag_value} | "
            f"Accuracy: ±{geolocation.uncertainty_radius_meters:.1f}m"
        )
        remarks.text = remarks_text

        # Contact info
        contact = SubElement(detail, "contact")
        contact.set("callsign", f"Detection-{detection_id[:8]}")

        # Labels for TAK display
        labels_on = SubElement(detail, "labels_on")
        labels_on.set("value", "false")

        # UID tracking
        uid_element = SubElement(detail, "uid")
        uid_element.set("Droid", cot_uid)

        # Convert to string
        cot_xml = tostring(event, encoding="unicode")
        return f'<?xml version="1.0" encoding="UTF-8"?>\n{cot_xml}'

    def cot_to_dict(self, cot_xml: str) -> dict:
        """Convert CoT XML to dictionary for JSON responses.

        Args:
            cot_xml: CoT XML string

        Returns:
            dict: Simplified dictionary representation
        """
        import xml.etree.ElementTree as ET

        try:
            root = ET.fromstring(cot_xml)
            point = root.find("point")
            detail = root.find("detail")

            result = {
                "uid": root.get("uid"),
                "type": root.get("type"),
                "time": root.get("time"),
                "location": {
                    "latitude": float(point.get("lat")),
                    "longitude": float(point.get("lon")),
                    "accuracy_meters": float(point.get("ce", 0)),
                },
                "metadata": {
                    "remarks": detail.find("remarks").text if detail.find("remarks") is not None else "",
                    "callsign": detail.find("contact").get("callsign") if detail.find("contact") is not None else "",
                },
            }
            return result
        except Exception as e:
            raise ValueError(f"Failed to parse CoT XML: {str(e)}")

    async def push_to_tak_server(self, cot_xml: str) -> bool:
        """Push CoT XML to TAK server.

        Args:
            cot_xml: CoT XML string

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.tak_server_url:
            return False

        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.put(
                    self.tak_server_url,
                    data=cot_xml.encode("utf-8"),
                    headers={"Content-Type": "application/xml"},
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as response:
                    return response.status in [200, 201, 204]
        except Exception as e:
            import logging

            logging.error(f"Failed to push CoT to TAK server: {str(e)}")
            return False
