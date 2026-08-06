"""Camera device model for the VisionMoCap application."""

from __future__ import annotations

from dataclasses import dataclass

from src.camera.backend import Backend


@dataclass
class CameraDevice:
    """Represents a camera detected on the system.

    Attributes:
        index: Zero-based device index used to open the camera via OpenCV.
        name: Human-readable identifier for the camera.
        backend: The OpenCV backend used to access this camera.
        is_available: Whether the camera responded successfully during probing.
        resolution_width: Native frame width in pixels (0 if unknown).
        resolution_height: Native frame height in pixels (0 if unknown).
        fps: Native frame rate in frames per second (0.0 if unknown).
    """

    index: int
    name: str
    backend: Backend
    is_available: bool = True
    resolution_width: int = 0
    resolution_height: int = 0
    fps: float = 0.0