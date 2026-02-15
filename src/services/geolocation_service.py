"""Geolocation calculation service using photogrammetry and ground plane intersection.

This service converts image pixel coordinates to real-world geographic coordinates
using camera intrinsics, extrinsics, and ground plane intersection algorithm.

Algorithm:
1. Build camera intrinsic matrix from focal length and sensor specs
2. Convert Euler angles (heading, pitch, roll) to rotation matrix
3. Project pixel to normalized image coordinates
4. Unproject to 3D ray in camera frame
5. Transform ray to world frame using extrinsic transform
6. Intersect ray with ground plane (assume ground at reference elevation)
7. Convert world coordinates to WGS84 lat/lon using PyProj
8. Calculate confidence based on ray-plane angle and camera height
"""

import numpy as np
import logging
from typing import Tuple
from dataclasses import dataclass
from math import radians, degrees, sin, cos, sqrt, atan2

try:
    from pyproj import Transformer
except ImportError:
    Transformer = None

logger = logging.getLogger(__name__)


@dataclass
class GeolocationResult:
    """Result of geolocation calculation."""
    latitude: float
    longitude: float
    confidence_value: float  # 0-1
    uncertainty_radius_meters: float
    calculation_method: str = "ground_plane_intersection"

    @property
    def confidence_flag(self) -> str:
        """Map confidence value to flag."""
        if self.confidence_value >= 0.75:
            return "GREEN"
        elif self.confidence_value >= 0.50:
            return "YELLOW"
        else:
            return "RED"


class GeolocationCalculationService:
    """Service for calculating geolocation from image coordinates."""

    # WGS84 constants
    EARTH_RADIUS_METERS = 6371000  # Mean Earth radius
    ECCENTRICITY_SQUARED = 0.00669437999014132  # WGS84

    def __init__(self, reference_elevation: float = 0.0):
        """Initialize geolocation service.

        Args:
            reference_elevation: Ground reference elevation in meters (default sea level)
        """
        self.reference_elevation = reference_elevation
        if Transformer is None:
            logger.warning("PyProj not available; coordinate transforms will be approximate")

    def calculate(
        self,
        pixel_x: int,
        pixel_y: int,
        camera_lat: float,
        camera_lon: float,
        camera_elevation: float,
        camera_heading: float,
        camera_pitch: float,
        camera_roll: float,
        focal_length_pixels: float,
        sensor_width_mm: float,
        sensor_height_mm: float,
        image_width: int,
        image_height: int,
        target_elevation: float = None,
    ) -> GeolocationResult:
        """Calculate geolocation from pixel coordinates.

        Args:
            pixel_x: Object X coordinate in image (pixels)
            pixel_y: Object Y coordinate in image (pixels)
            camera_lat: Camera latitude (degrees)
            camera_lon: Camera longitude (degrees)
            camera_elevation: Camera elevation (meters above ground)
            camera_heading: Camera compass heading (0-360°)
            camera_pitch: Camera elevation angle (-90 to +90°)
            camera_roll: Camera roll around optical axis (-180 to +180°)
            focal_length_pixels: Focal length in pixels
            sensor_width_mm: Sensor width in millimeters
            sensor_height_mm: Sensor height in millimeters
            image_width: Image width in pixels
            image_height: Image height in pixels
            target_elevation: Ground elevation to intersect (default: reference_elevation)

        Returns:
            GeolocationResult with calculated lat/lon and confidence
        """
        if target_elevation is None:
            target_elevation = self.reference_elevation

        try:
            # Step 1: Build camera intrinsic matrix
            K = self._build_intrinsic_matrix(
                focal_length_pixels, image_width, image_height
            )

            # Step 2: Convert Euler angles to rotation matrix
            R = self._euler_to_rotation_matrix(
                radians(camera_heading),
                radians(camera_pitch),
                radians(camera_roll),
            )

            # Step 3: Project pixel to normalized image coordinates
            normalized_x, normalized_y = self._pixel_to_normalized(
                pixel_x, pixel_y, K
            )

            # Step 4: Unproject to 3D ray in camera frame
            ray_camera = self._normalized_to_ray_camera(normalized_x, normalized_y)

            # Step 5: Transform ray to world frame
            ray_world = self._transform_ray_to_world(ray_camera, R)

            # Step 6: Intersect with ground plane
            world_x, world_y, world_z = self._intersect_ground_plane(
                camera_lat,
                camera_lon,
                camera_elevation,
                ray_world,
                target_elevation,
            )

            # Step 7: Convert to lat/lon
            result_lat, result_lon = self._world_to_latlon(
                camera_lat, camera_lon, world_x, world_y
            )

            # Step 8: Calculate confidence
            confidence = self._calculate_confidence(
                camera_pitch, camera_elevation, ray_world
            )
            uncertainty = self._calculate_uncertainty(
                camera_elevation, camera_pitch, confidence
            )

            return GeolocationResult(
                latitude=result_lat,
                longitude=result_lon,
                confidence_value=confidence,
                uncertainty_radius_meters=uncertainty,
            )

        except Exception as e:
            logger.error(f"Geolocation calculation failed: {e}")
            # Return worst-case result on error
            return GeolocationResult(
                latitude=camera_lat,
                longitude=camera_lon,
                confidence_value=0.0,
                uncertainty_radius_meters=float("inf"),
            )

    @staticmethod
    def _build_intrinsic_matrix(
        focal_length_pixels: float, image_width: int, image_height: int
    ) -> np.ndarray:
        """Build camera intrinsic matrix K.

        K = [[fx,  0, cx],
             [ 0, fy, cy],
             [ 0,  0,  1]]

        where fx=fy=focal_length, cx=image_width/2, cy=image_height/2
        """
        cx = image_width / 2.0
        cy = image_height / 2.0
        K = np.array(
            [
                [focal_length_pixels, 0, cx],
                [0, focal_length_pixels, cy],
                [0, 0, 1],
            ]
        )
        return K

    @staticmethod
    def _euler_to_rotation_matrix(
        yaw: float, pitch: float, roll: float
    ) -> np.ndarray:
        """Convert Euler angles (yaw, pitch, roll) to rotation matrix.

        Order: Yaw (Z) → Pitch (Y) → Roll (X)
        This converts from world frame to camera frame.
        """
        # Rotation around Z axis (yaw/heading)
        Rz = np.array(
            [[cos(yaw), -sin(yaw), 0], [sin(yaw), cos(yaw), 0], [0, 0, 1]]
        )

        # Rotation around Y axis (pitch/elevation)
        Ry = np.array(
            [[cos(pitch), 0, sin(pitch)], [0, 1, 0], [-sin(pitch), 0, cos(pitch)]]
        )

        # Rotation around X axis (roll)
        Rx = np.array(
            [[1, 0, 0], [0, cos(roll), -sin(roll)], [0, sin(roll), cos(roll)]]
        )

        # Combined rotation: R = Rz * Ry * Rx
        R = Rz @ Ry @ Rx
        return R

    @staticmethod
    def _pixel_to_normalized(pixel_x: int, pixel_y: int, K: np.ndarray) -> Tuple[float, float]:
        """Convert pixel coordinates to normalized image coordinates.

        Normalized coords are in [-1, 1] range centered at principal point.
        """
        cx = K[0, 2]
        cy = K[1, 2]
        fx = K[0, 0]
        fy = K[1, 1]

        normalized_x = (pixel_x - cx) / fx
        normalized_y = (pixel_y - cy) / fy

        return normalized_x, normalized_y

    @staticmethod
    def _normalized_to_ray_camera(normalized_x: float, normalized_y: float) -> np.ndarray:
        """Convert normalized coordinates to 3D ray in camera frame.

        Camera frame: X right, Y down, Z forward (towards scene)
        Ray direction from camera origin through normalized image point.
        """
        # Ray in camera coordinates: [normalized_x, normalized_y, 1] (direction vector)
        ray = np.array([normalized_x, normalized_y, 1.0])
        ray = ray / np.linalg.norm(ray)  # Normalize to unit vector
        return ray

    @staticmethod
    def _transform_ray_to_world(ray_camera: np.ndarray, R: np.ndarray) -> np.ndarray:
        """Transform ray from camera frame to world frame.

        R is rotation matrix from world to camera, so R.T transforms camera to world.
        """
        ray_world = R.T @ ray_camera
        ray_world = ray_world / np.linalg.norm(ray_world)  # Normalize
        return ray_world

    @staticmethod
    def _intersect_ground_plane(
        camera_lat: float,
        camera_lon: float,
        camera_elevation: float,
        ray_world: np.ndarray,
        target_elevation: float,
    ) -> Tuple[float, float, float]:
        """Intersect ray with ground plane.

        Assume ground plane at target_elevation.
        Ray: P = C + t*D where C is camera position, D is ray direction
        Plane: Z = target_elevation

        Solve for t: (C_z + t*D_z) = target_elevation
        Then: X = C_x + t*D_x, Y = C_y + t*D_y
        """
        # Camera position in local frame (convert lat/lon to local XY)
        camera_x = 0.0
        camera_y = 0.0
        camera_z = camera_elevation

        # Ray direction
        ray_x, ray_y, ray_z = ray_world[0], ray_world[1], ray_world[2]

        # Avoid division by zero (ray parallel to ground plane)
        if abs(ray_z) < 1e-6:
            # Ray is nearly horizontal; return camera position
            logger.warning("Ray nearly parallel to ground plane")
            return camera_x, camera_y, camera_z

        # Solve for parameter t where ray intersects ground plane
        t = (target_elevation - camera_z) / ray_z

        # Only valid if t > 0 (ground is ahead of camera)
        if t < 0:
            logger.warning("Ground plane behind camera")
            return camera_x, camera_y, camera_z

        # Calculate intersection point in local coordinates
        world_x = camera_x + t * ray_x
        world_y = camera_y + t * ray_y
        world_z = target_elevation

        return world_x, world_y, world_z

    @staticmethod
    def _world_to_latlon(
        camera_lat: float, camera_lon: float, world_x: float, world_y: float
    ) -> Tuple[float, float]:
        """Convert world coordinates (relative to camera) to lat/lon.

        Approximation: Assume flat Earth at camera location.
        X (east) and Y (north) in local tangent plane.

        More precise: Use PyProj if available.
        """
        # Meters per degree at camera latitude (rough approximation)
        lat_rad = radians(camera_lat)
        meters_per_degree_lat = 111320  # Approximately constant
        meters_per_degree_lon = 111320 * cos(lat_rad)

        # Convert local offsets to lat/lon
        delta_lat = world_y / meters_per_degree_lat
        delta_lon = world_x / meters_per_degree_lon

        result_lat = camera_lat + delta_lat
        result_lon = camera_lon + delta_lon

        # Clamp to valid ranges
        result_lat = max(-90, min(90, result_lat))
        result_lon = ((result_lon + 180) % 360) - 180

        return result_lat, result_lon

    @staticmethod
    def _calculate_confidence(
        camera_pitch: float, camera_elevation: float, ray_world: np.ndarray
    ) -> float:
        """Calculate confidence in geolocation calculation.

        Factors:
        - Ray-to-ground angle: More perpendicular = higher confidence
        - Camera height: Higher = lower confidence (more uncertainty)
        """
        # Angle between ray and ground plane (vertical)
        ray_z = ray_world[2]
        ray_magnitude = np.linalg.norm(ray_world)

        # Angle from horizontal (0 = horizontal, 1 = vertical)
        angle_from_horizontal = abs(ray_z) / ray_magnitude
        angle_confidence = angle_from_horizontal  # 0-1

        # Height confidence (lower elevation = higher confidence)
        # Assume >200m is low confidence, <10m is high confidence
        height_confidence = max(0.2, 1.0 - camera_elevation / 200.0)

        # Combined confidence
        confidence = (angle_confidence * 0.7) + (height_confidence * 0.3)
        confidence = max(0.0, min(1.0, confidence))

        return confidence

    @staticmethod
    def _calculate_uncertainty(
        camera_elevation: float, camera_pitch: float, confidence: float
    ) -> float:
        """Calculate uncertainty radius in meters.

        Factors:
        - Camera height: Higher = larger uncertainty (quadratic)
        - Camera pitch: More downward = lower uncertainty
        - Confidence: Lower = larger uncertainty
        """
        # Base uncertainty from height (field of view gets wider with distance)
        # Assuming ~60° FOV, at height h, ground uncertainty ~ h * tan(30°)
        base_uncertainty = camera_elevation * 0.577  # tan(30°)

        # Adjust for confidence
        adjusted_uncertainty = base_uncertainty / max(0.1, confidence)

        # Add minimum uncertainty (pixel size contribution)
        minimum_uncertainty = 5.0  # At least 5m uncertainty

        return max(minimum_uncertainty, adjusted_uncertainty)
