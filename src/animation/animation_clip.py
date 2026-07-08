"""Animation clip data model for the VisionMoCap animation subsystem.

An AnimationClip is a time-ordered sequence of Keyframes that describe
the motion of an avatar skeleton.  It supports per-frame bone transform
interpolation (linear position + spherical rotation) and is independent
of any specific export or playback target.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional, Tuple

from src.animation.keyframe import InterpolationType, Keyframe
from src.animation.retargeted_motion import BoneTransform
from src.core.models import Vector3D


class AnimationClip:
    """A time-ordered sequence of keyframes.

    Keyframes are maintained in chronological order.  The :meth:`interpolate`
    method returns the skeleton pose at any arbitrary timestamp by blending
    between the two surrounding keyframes.

    Attributes:
        keyframes: Ordered list of Keyframes (ascending timestamp).
        duration: Total duration of the clip in seconds.
        fps: Nominal frame rate of the clip.
        metadata: Arbitrary key-value store for application-specific data.
    """

    def __init__(
        self,
        keyframes: Optional[List[Keyframe]] = None,
        duration: float = 0.0,
        fps: float = 30.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._keyframes: List[Keyframe] = (
            sorted(keyframes, key=lambda kf: kf.timestamp)
            if keyframes
            else []
        )
        self._duration = duration
        self._fps = fps
        self._metadata = dict(metadata) if metadata else {}
        self._logger = logging.getLogger(self.__class__.__name__)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def keyframes(self) -> List[Keyframe]:
        """Read-only view of the keyframe list."""
        return list(self._keyframes)

    @property
    def duration(self) -> float:
        return self._duration

    @duration.setter
    def duration(self, value: float) -> None:
        self._duration = value

    @property
    def fps(self) -> float:
        return self._fps

    @fps.setter
    def fps(self, value: float) -> None:
        self._fps = value

    @property
    def metadata(self) -> Dict[str, Any]:
        return dict(self._metadata)

    @property
    def frame_count(self) -> int:
        return len(self._keyframes)

    @property
    def bone_names(self) -> List[str]:
        if not self._keyframes:
            return []
        return list(self._keyframes[0].bone_transforms.keys())

    # ------------------------------------------------------------------
    # Keyframe management
    # ------------------------------------------------------------------

    def add_keyframe(self, keyframe: Keyframe) -> None:
        """Add a keyframe and maintain chronological order.

        If a keyframe with the same ``frame_number`` already exists it
        is replaced.

        Args:
            keyframe: The Keyframe to add.
        """
        self._remove_by_frame_number(keyframe.frame_number)
        self._keyframes.append(keyframe)
        self._keyframes.sort(key=lambda kf: kf.timestamp)
        self._logger.debug(
            "Added keyframe %d at t=%.3f. Total: %d.",
            keyframe.frame_number,
            keyframe.timestamp,
            len(self._keyframes),
        )

    def remove_keyframe(self, frame_number: int) -> bool:
        """Remove the keyframe with the given frame number.

        Args:
            frame_number: Frame number of the keyframe to remove.

        Returns:
            True if a keyframe was removed, False otherwise.
        """
        removed = self._remove_by_frame_number(frame_number)
        if removed:
            self._logger.debug(
                "Removed keyframe %d. Remaining: %d.",
                frame_number,
                len(self._keyframes),
            )
        return removed

    def get_keyframe(self, frame_number: int) -> Optional[Keyframe]:
        """Retrieve a keyframe by frame number.

        Args:
            frame_number: Frame number to look up.

        Returns:
            The matching Keyframe, or None if not found.
        """
        for kf in self._keyframes:
            if kf.frame_number == frame_number:
                return kf
        return None

    # ------------------------------------------------------------------
    # Interpolation
    # ------------------------------------------------------------------

    def interpolate(
        self, timestamp: float
    ) -> Optional[Dict[str, BoneTransform]]:
        """Evaluate the skeleton pose at an arbitrary timestamp.

        The pose is obtained by blending the two keyframes that surround
        *timestamp*.  For ``LINEAR`` keyframes the position is linearly
        interpolated and the rotation is spherically interpolated
        (slerp).  For ``STEP`` keyframes the earlier keyframe's pose is
        held unchanged.

        Args:
            timestamp: Time in seconds from the start of the clip.

        Returns:
            ``{bone_name: BoneTransform}`` for all bones, or ``None``
            if the clip has no keyframes.
        """
        count = len(self._keyframes)
        if count == 0:
            return None
        if count == 1:
            return dict(self._keyframes[0].bone_transforms)

        # Clamp to clip bounds.
        if timestamp <= self._keyframes[0].timestamp:
            return dict(self._keyframes[0].bone_transforms)
        if timestamp >= self._keyframes[-1].timestamp:
            return dict(self._keyframes[-1].bone_transforms)

        # Find the surrounding keyframes.
        prev_kf = self._keyframes[0]
        for next_kf in self._keyframes[1:]:
            if next_kf.timestamp >= timestamp:
                break
            prev_kf = next_kf
        else:
            return dict(self._keyframes[-1].bone_transforms)

        if prev_kf.interpolation == InterpolationType.STEP:
            return dict(prev_kf.bone_transforms)

        span = next_kf.timestamp - prev_kf.timestamp
        if span <= 0.0:
            return dict(prev_kf.bone_transforms)

        t = (timestamp - prev_kf.timestamp) / span
        t = max(0.0, min(1.0, t))

        return self._blend(
            prev_kf.bone_transforms,
            next_kf.bone_transforms,
            t,
        )

    # ------------------------------------------------------------------
    # Internal helpers — keyframe management
    # ------------------------------------------------------------------

    def _remove_by_frame_number(self, frame_number: int) -> bool:
        before = len(self._keyframes)
        self._keyframes = [
            kf for kf in self._keyframes if kf.frame_number != frame_number
        ]
        return len(self._keyframes) < before

    # ------------------------------------------------------------------
    # Internal helpers — blending / interpolation math
    # ------------------------------------------------------------------

    def _blend(
        self,
        prev_bones: Dict[str, BoneTransform],
        next_bones: Dict[str, BoneTransform],
        t: float,
    ) -> Dict[str, BoneTransform]:
        """Blend two bone transform dictionaries at parameter *t*."""
        all_names = set(prev_bones) | set(next_bones)
        result: Dict[str, BoneTransform] = {}

        for name in all_names:
            prev_bt = prev_bones.get(name)
            next_bt = next_bones.get(name)

            if prev_bt is None and next_bt is None:
                continue
            if prev_bt is None:
                result[name] = BoneTransform(
                    position=next_bt.position,
                    rotation=next_bt.rotation,
                )
                continue
            if next_bt is None:
                result[name] = BoneTransform(
                    position=prev_bt.position,
                    rotation=prev_bt.rotation,
                )
                continue

            result[name] = BoneTransform(
                position=self._lerp_vector3d(
                    prev_bt.position, next_bt.position, t
                ),
                rotation=self._slerp_quaternion(
                    prev_bt.rotation, next_bt.rotation, t
                ),
            )

        return result

    @staticmethod
    def _lerp_vector3d(a: Vector3D, b: Vector3D, t: float) -> Vector3D:
        """Linearly interpolate between two vectors.

        ``result = a + (b - a) * t``
        """
        return Vector3D(
            a.x + (b.x - a.x) * t,
            a.y + (b.y - a.y) * t,
            a.z + (b.z - a.z) * t,
        )

    @staticmethod
    def _slerp_quaternion(
        q1: Tuple[float, float, float, float],
        q2: Tuple[float, float, float, float],
        t: float,
    ) -> Tuple[float, float, float, float]:
        """Spherically linear interpolate between two unit quaternions.

        Uses the standard geometric slerp formula.  If the quaternions
        are nearly parallel it falls back to normalised linear
        interpolation (nlerp) to avoid division by near-zero.
        """
        w1, x1, y1, z1 = q1
        w2, x2, y2, z2 = q2

        dot = w1 * w2 + x1 * x2 + y1 * y2 + z1 * z2

        # Take the shorter rotation path.
        if dot < 0.0:
            w2, x2, y2, z2 = -w2, -x2, -y2, -z2
            dot = -dot

        # Nearly parallel — use nlerp for numerical stability.
        if dot > 0.9995:
            n = 1.0 / math.sqrt(
                (w1 + (w2 - w1) * t) ** 2
                + (x1 + (x2 - x1) * t) ** 2
                + (y1 + (y2 - y1) * t) ** 2
                + (z1 + (z2 - z1) * t) ** 2
            )
            return (
                (w1 + (w2 - w1) * t) * n,
                (x1 + (x2 - x1) * t) * n,
                (y1 + (y2 - y1) * t) * n,
                (z1 + (z2 - z1) * t) * n,
            )

        theta_0 = math.acos(dot)
        sin_theta_0 = math.sin(theta_0)
        s1 = math.sin((1.0 - t) * theta_0) / sin_theta_0
        s2 = math.sin(t * theta_0) / sin_theta_0

        return (
            s1 * w1 + s2 * w2,
            s1 * x1 + s2 * x2,
            s1 * y1 + s2 * y2,
            s1 * z1 + s2 * z2,
        )
