"""Retargeted motion data models for the VisionMoCap animation subsystem.

Contains the output container produced by the Retargeter: per-frame
bone transforms ready for consumption by a future Blender connector
or other export target.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from src.core.models import Vector3D


@dataclass
class BoneTransform:
    """The spatial state of a single bone at one point in time.

    Attributes:
        position: World-space position of the bone's head joint.
        rotation: Orientation as a unit quaternion ``(w, x, y, z)``.
    """

    position: Vector3D
    rotation: Tuple[float, float, float, float]


@dataclass
class RetargetedFrame:
    """The state of every bone in the avatar skeleton at one frame.

    Attributes:
        bones: Mapping from bone name to its world-space transform.
        timestamp: Monotonic timestamp of this frame in seconds.
    """

    bones: Dict[str, BoneTransform]
    timestamp: float


@dataclass
class RetargetedMotion:
    """Complete retargeted animation ready for export or playback.

    Produced by the :class:`Retargeter`.  Contains one
    :class:`RetargetedFrame` per input pose frame, with bone transforms
    computed via the :class:`SkeletonMapper`.

    Attributes:
        frames: Timestamp-ordered list of retargeted frames.
        avatar_name: Name of the avatar this motion was retargeted for.
        fps: Frame rate of the retargeted animation.
        duration: Total duration in seconds.
    """

    frames: List[RetargetedFrame] = field(default_factory=list)
    avatar_name: str = ""
    fps: float = 0.0
    duration: float = 0.0

    @property
    def frame_count(self) -> int:
        """Return the total number of retargeted frames."""
        return len(self.frames)

    @property
    def bone_names(self) -> List[str]:
        """Return the list of bone names from the first frame."""
        if not self.frames:
            return []
        return list(self.frames[0].bones.keys())
