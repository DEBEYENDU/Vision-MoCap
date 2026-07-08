"""Pose result data model for the VisionMoCap application."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class Landmark:
    """A single landmark detected by the pose estimation model.

    Attributes:
        x: Normalized x-coordinate in the range ``[0.0, 1.0]``.
        y: Normalized y-coordinate in the range ``[0.0, 1.0]``.
        z: Depth relative to the hip center (negative is closer to camera).
        visibility: Detection visibility in the range ``[0.0, 1.0]``.
    """

    x: float
    y: float
    z: float
    visibility: float


@dataclass
class PoseResult:
    """Encapsulates the output of a single pose inference call.

    Attributes:
        timestamp: Monotonic timestamp of the inference in seconds.
        landmarks: 33 normalized pose landmarks.
        world_landmarks: 33 pose landmarks in 3D world coordinates (meters).
        confidence: Overall pose detection confidence (0.0 – 1.0).
        frame_width: Width of the input frame in pixels.
        frame_height: Height of the input frame in pixels.
        pose_detected: Whether a valid pose was detected in the frame.
    """

    timestamp: float
    landmarks: List[Landmark] = field(default_factory=list)
    world_landmarks: List[Landmark] = field(default_factory=list)
    confidence: float = 0.0
    frame_width: int = 0
    frame_height: int = 0
    pose_detected: bool = False
