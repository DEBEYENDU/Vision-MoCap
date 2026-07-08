"""Camera device model for the VisionMoCap application."""

from dataclasses import dataclass


@dataclass
class CameraDevice:
    """Represents a physical or virtual camera detected on the system.

    Attributes:
        index: Zero-based device index used to open the camera via OpenCV.
        name: Human-readable identifier for the camera.
        backend: OpenCV backend constant used to access this camera.
        is_available: Whether the camera responded successfully during probing.
    """

    index: int
    name: str
    backend: int
    is_available: bool = True
