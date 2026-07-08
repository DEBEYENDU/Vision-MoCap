"""Keyframe data model for the VisionMoCap animation subsystem.

A Keyframe captures the complete pose of every bone in the skeleton at a
single point in time, together with metadata that controls how the
animation system transitions between consecutive keyframes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict

from src.animation.retargeted_motion import BoneTransform


class InterpolationType(Enum):
    """Controls how the animation blends between two keyframes.

    ``LINEAR``
        Linearly interpolate position and spherically interpolate
        rotation between the previous and next keyframe.
    ``STEP``
        Hold the previous keyframe's pose until the next keyframe
        is reached (no blending).
    """

    LINEAR = auto()
    STEP = auto()


@dataclass
class Keyframe:
    """A single keyframe in an :class:`AnimationClip`.

    Attributes:
        timestamp: Time offset from the start of the clip in seconds.
        frame_number: Zero-based frame index within the clip's frame
            sequence.
        bone_transforms: Mapping from bone name to its world-space
            transform at this keyframe.
        interpolation: How to interpolate **from** this keyframe
            **to** the next one.  The last keyframe's interpolation
            type is unused.
    """

    timestamp: float
    frame_number: int
    bone_transforms: Dict[str, BoneTransform] = field(default_factory=dict)
    interpolation: InterpolationType = InterpolationType.LINEAR
