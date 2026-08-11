"""Motion retargeting for the VisionMoCap animation subsystem.

The Retargeter converts a processed MotionSequence into a
RetargetedMotion by mapping MediaPipe landmarks to avatar bones
(via SkeletonMapper) and computing per-frame bone transforms
including rotation relative to the avatar's bind pose.
"""

from __future__ import annotations

import logging
import math
from typing import Dict, List, Optional, Tuple

from src.animation.avatar import Avatar
from src.animation.retargeted_motion import BoneTransform, RetargetedFrame, RetargetedMotion
from src.animation.skeleton_mapper import SkeletonMapping, SkeletonMapper
from src.core.models import Vector3D
from src.motion.motion_sequence import MotionSequence


class Retargeter:
    """Retarget a MotionSequence onto an Avatar skeleton.

    The retargeting pipeline for each frame::

        MotionSequence frame
            ↓
        SkeletonMapper.map_frame()
            ↓  (bone_name → (head_pos, tail_pos))
        Compute per-bone transform:
          - position = head_pos
          - rotation = shortest arc from bind-pose direction
                        to current frame's head→tail direction
            ↓
        RetargetedFrame

    The Retargeter is independent of any export target (Blender, FBX,
    glTF, etc.) — it produces a pure-data RetargetedMotion that a
    downstream connector can consume.
    """

    def __init__(
        self,
        mapper: SkeletonMapper,
        avatar: Avatar,
    ) -> None:
        self._mapper = mapper
        self._avatar = avatar
        self._logger = logging.getLogger(self.__class__.__name__)

        # Pre-compute bind-pose bone directions for rotation computation.
        self._bind_dirs: Dict[str, Vector3D] = {
            b.name: b.direction
            for b in avatar.bones
            if mapper.has_bone(b.name)
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def retarget(self, sequence: MotionSequence) -> RetargetedMotion:
        """Retarget an entire motion sequence onto the avatar.

        Args:
            sequence: A processed MotionSequence (e.g. after filtering
                      and interpolation).  Must contain at least one
                      PoseResult with detectable landmarks.

        Returns:
            A RetargetedMotion with one frame per input pose.

        Raises:
            ValueError: If the sequence is empty or has no mapped bones.
        """
        if not sequence.pose_results:
            raise ValueError("Cannot retarget an empty MotionSequence.")

        mapped_bones = self._mapper.bone_names
        if not mapped_bones:
            raise ValueError(
                "SkeletonMapper has no bones configured. "
                "Provide a mapping or select a preset."
            )

        self._logger.info(
            "Retargeting %d frames onto avatar '%s' (%d bones).",
            len(sequence.pose_results),
            self._avatar.name,
            len(mapped_bones),
        )

        frames: List[RetargetedFrame] = []
        for pose_result in sequence.pose_results:
            frame = self._retarget_frame(pose_result, mapped_bones)
            frames.append(frame)

        duration = sequence.duration if sequence.duration > 0.0 else (
            sequence.end_time - sequence.start_time
        )

        return RetargetedMotion(
            frames=frames,
            avatar_name=self._avatar.name,
            fps=sequence.resolve_average_fps(),
            duration=duration,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _retarget_frame(
        self,
        pose_result: object,
        mapped_bones: List[str],
    ) -> RetargetedFrame:
        """Retarget a single pose frame.

        Args:
            pose_result: A PoseResult from the motion sequence.
            mapped_bones: List of bone names to compute transforms for.

        Returns:
            A RetargetedFrame with transforms for every mapped bone.
        """
        from src.pose.pose_result import PoseResult

        assert isinstance(pose_result, PoseResult), (
            f"Expected PoseResult, got {type(pose_result)}"
        )

        raw = self._mapper.map_frame(pose_result)
        bones: Dict[str, BoneTransform] = {}

        for bone_name in mapped_bones:
            if bone_name not in raw:
                continue
            head_pos, tail_pos = raw[bone_name]

            # Compute rotation: shortest arc from bind-pose direction
            # to the current frame's head→tail direction.
            bind_dir = self._bind_dirs.get(bone_name)
            if bind_dir is not None:
                current_dir = (tail_pos - head_pos).normalize()
                rotation = self._direction_to_quaternion(bind_dir, current_dir)
            else:
                rotation = (1.0, 0.0, 0.0, 0.0)

            bones[bone_name] = BoneTransform(
                position=head_pos,
                rotation=rotation,
            )

        return RetargetedFrame(
            bones=bones,
            timestamp=getattr(pose_result, "timestamp", 0.0),
        )

    # ------------------------------------------------------------------
    # Quaternion math
    # ------------------------------------------------------------------

    @staticmethod
    def _direction_to_quaternion(
        from_dir: Vector3D,
        to_dir: Vector3D,
    ) -> Tuple[float, float, float, float]:
        """Compute the shortest‑arc quaternion rotating *from_dir* to
        *to_dir*.

        Both vectors should be unit length.  Returns a unit quaternion
        ``(w, x, y, z)``.
        """
        dot = (
            from_dir.x * to_dir.x
            + from_dir.y * to_dir.y
            + from_dir.z * to_dir.z
        )
        dot = max(-1.0, min(1.0, dot))  # clamp

        # Parallel — identity quaternion.
        if dot > 0.99999:
            return (1.0, 0.0, 0.0, 0.0)

        # Opposite — rotate 180° around an arbitrary perpendicular axis.
        if dot < -0.99999:
            axis = Vector3D(1.0, 0.0, 0.0).cross(from_dir)
            if axis.magnitude < 1e-6:
                axis = Vector3D(0.0, 1.0, 0.0).cross(from_dir)
            axis = axis.normalize()
            return (0.0, axis.x, axis.y, axis.z)

        # General case.
        axis = from_dir.cross(to_dir)
        w = math.sqrt((1.0 + dot) * 2.0) / 2.0
        s = 1.0 / (2.0 * w)
        return (w, axis.x * s, axis.y * s, axis.z * s)
