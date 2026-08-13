"""BVH file exporter for the VisionMoCap animation subsystem.

Converts an AnimationClip (backed by an Avatar skeleton) into the
standard Biovision Hierarchy (BVH) ASCII format used by Blender,
Maya, Unity, and other DCC tools.

Data flow::

    AnimationClip + Avatar
        ↓
    BvhExporter.export(path)
        ↓
    .bvh file (HIERARCHY + MOTION sections)
"""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from src.animation.animation_clip import AnimationClip
from src.animation.avatar import Avatar
from src.animation.bone import Bone
from src.animation.keyframe import Keyframe
from src.animation.retargeted_motion import BoneTransform
from src.core.exceptions import AnimationExportError
from src.core.models import Vector3D


class BvhExporter:
    """Exports an AnimationClip to the BVH file format.

    The exporter converts per-bone quaternion rotations to Euler angles
    in ZXY order (the most common BVH convention) and computes
    parent-space rotations from the world-space bone transforms.

    The skeleton hierarchy is derived from the Avatar's bone tree with
    OFFSET values computed from the first keyframe's bone positions.

    Attributes:
        avatar: The Avatar whose skeleton defines the BVH hierarchy.
        clip: The AnimationClip whose keyframes supply the motion data.
        hierarchy_order: Bones in depth-first traversal order.
    """

    def __init__(
        self,
        avatar: Avatar,
        clip: AnimationClip,
    ) -> None:
        if not clip.keyframes:
            raise ValueError("AnimationClip must contain at least one keyframe.")
        if not avatar.bones:
            raise ValueError("Avatar must contain at least one bone.")

        self._avatar = avatar
        self._clip = clip
        self._logger = logging.getLogger(self.__class__.__name__)

        # Build depth-first bone order and compute rest-pose offsets.
        self._hierarchy_order: List[str] = self._build_hierarchy_order()
        self._offsets: Dict[str, Vector3D] = self._compute_offsets()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def avatar(self) -> Avatar:
        return self._avatar

    @property
    def clip(self) -> AnimationClip:
        return self._clip

    @property
    def hierarchy_order(self) -> List[str]:
        return list(self._hierarchy_order)

    def export(self, path: Union[str, Path]) -> None:
        """Write the BVH file to *path*.

        Args:
            path: Destination file path.  Parent directories are created
                  automatically.

        Raises:
            AnimationExportError: If the file cannot be written.
        """
        path = Path(path)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)

            content = self._format_hierarchy() + self._format_motion()

            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(content)
        except (OSError, ValueError) as e:
            raise AnimationExportError(
                f"Failed to write BVH file {path}: {e}",
                cause=e,
            )

        self._logger.info(
            "BVH exported to %s (%d frames, %d bones).",
            path.name,
            len(self._clip.keyframes),
            len(self._hierarchy_order),
        )

    # ------------------------------------------------------------------
    # Hierarchy builder
    # ------------------------------------------------------------------

    def _build_hierarchy_order(self) -> List[str]:
        """Return bone names in depth-first traversal order (parent
        before children)."""
        order: List[str] = []

        def visit(name: str) -> None:
            order.append(name)
            bone = self._avatar.bone(name)
            for child_name in bone.children:
                visit(child_name)

        visit(self._avatar.root_bone)
        return order

    def _compute_offsets(self) -> Dict[str, Vector3D]:
        """Compute rest-pose OFFSET for each bone.

        Root OFFSET is (0, 0, 0).  Child OFFSET values are the
        head-position difference from the parent, taken from the
        first keyframe.
        """
        first_frame = self._clip.keyframes[0].bone_transforms
        offsets: Dict[str, Vector3D] = {}

        # Root OFFSET is always the origin (the root position is encoded
        # in the motion channels, not the hierarchy).
        offsets[self._avatar.root_bone] = Vector3D(0.0, 0.0, 0.0)

        for name in self._hierarchy_order:
            bone = self._avatar.bone(name)
            if bone.parent is None:
                continue
            child_pos = first_frame.get(name)
            parent_pos = first_frame.get(bone.parent)
            if child_pos is not None and parent_pos is not None:
                offsets[name] = child_pos.position - parent_pos.position
            else:
                offsets[name] = Vector3D(0.0, 0.0, 0.0)

        return offsets

    # ------------------------------------------------------------------
    # BVH string formatters
    # ------------------------------------------------------------------

    def _format_hierarchy(self) -> str:
        """Build the HIERARCHY section of the BVH file."""
        lines: List[str] = ["HIERARCHY"]

        def write_bone(name: str, indent: int) -> None:
            prefix = "  " * indent
            bone = self._avatar.bone(name)
            offset = self._offsets.get(name, Vector3D(0.0, 0.0, 0.0))
            is_root = bone.parent is None

            if is_root:
                lines.append(f"{prefix}ROOT {name}")
            else:
                lines.append(f"{prefix}JOINT {name}")
            lines.append(f"{prefix}{{")
            lines.append(
                f"{prefix}  OFFSET {offset.x:.6f} {offset.y:.6f} {offset.z:.6f}"
            )

            if is_root:
                lines.append(
                    f"{prefix}  CHANNELS 6 "
                    "Xposition Yposition Zposition "
                    "Zrotation Xrotation Yrotation"
                )
            else:
                lines.append(
                    f"{prefix}  CHANNELS 3 "
                    "Zrotation Xrotation Yrotation"
                )

            for child_name in bone.children:
                write_bone(child_name, indent + 1)

            lines.append(f"{prefix}}}")

        write_bone(self._avatar.root_bone, 0)
        lines.append("")
        return "\n".join(lines)

    def _format_motion(self) -> str:
        """Build the MOTION section of the BVH file."""
        kfs = self._clip.keyframes
        frame_time = 1.0 / self._clip.fps if self._clip.fps > 0 else 1.0 / 30.0

        lines: List[str] = [
            "MOTION",
            f"Frames: {len(kfs)}",
            f"Frame Time: {frame_time:.6f}",
        ]

        for kf in kfs:
            line_parts: List[str] = []
            transforms = kf.bone_transforms

            for name in self._hierarchy_order:
                bt = transforms.get(name)
                if bt is None:
                    line_parts.extend(["0.0"] * (6 if name == self._avatar.root_bone else 3))
                    continue

                is_root = name == self._avatar.root_bone
                parent_rot = self._compute_parent_space_rotation(
                    name, transforms
                )
                z_deg, x_deg, y_deg = self._quat_to_euler_zxy(*parent_rot)

                if is_root:
                    pos = bt.position
                    line_parts.extend([
                        f"{pos.x:.6f}",
                        f"{pos.y:.6f}",
                        f"{pos.z:.6f}",
                        f"{z_deg:.6f}",
                        f"{x_deg:.6f}",
                        f"{y_deg:.6f}",
                    ])
                else:
                    line_parts.extend([
                        f"{z_deg:.6f}",
                        f"{x_deg:.6f}",
                        f"{y_deg:.6f}",
                    ])

            lines.append(" ".join(line_parts))

        lines.append("")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Rotation math
    # ------------------------------------------------------------------

    def _compute_parent_space_rotation(
        self,
        bone_name: str,
        transforms: Dict[str, BoneTransform],
    ) -> Tuple[float, float, float, float]:
        """Convert a bone's world-space rotation to parent space.

        For the root bone the world-space rotation is returned as-is.
        For child bones the rotation is expressed relative to the
        parent's world orientation using::

            inv(parent_world_rotation) * child_world_rotation

        Returns:
            Quaternion ``(w, x, y, z)`` in parent space.
        """
        bt = transforms.get(bone_name)
        if bt is None:
            return (1.0, 0.0, 0.0, 0.0)

        bone_world = bt.rotation
        parent_name = self._avatar.bone(bone_name).parent

        if parent_name is None or parent_name not in transforms:
            return bone_world

        parent_world = transforms[parent_name].rotation
        inv_parent = self._quat_conjugate(parent_world)
        return self._quat_multiply(inv_parent, bone_world)

    @staticmethod
    def _quat_to_euler_zxy(
        w: float, x: float, y: float, z: float
    ) -> Tuple[float, float, float]:
        """Convert a quaternion ``(w, x, y, z)`` to ZXY Euler angles.

        Returns:
            ``(z_angle, x_angle, y_angle)`` in **degrees**, matching the
            ``Zrotation Xrotation Yrotation`` channel order in BVH.
        """
        # Z-X-Y intrinsic Euler (R = Ry * Rx * Rz).
        # Pitch (X) singularity check
        sin_pitch = 2.0 * (w * y - z * x)

        if abs(sin_pitch) >= 1.0:
            pitch = math.copysign(math.pi / 2.0, sin_pitch)
            yaw = math.atan2(-2.0 * (z * w - x * y), 2.0 * (w * w + y * y) - 1.0)
            roll = 0.0
        else:
            pitch = math.asin(sin_pitch)
            yaw = math.atan2(
                2.0 * (w * z + x * y),
                1.0 - 2.0 * (y * y + z * z)
            )
            roll = math.atan2(
                2.0 * (w * x + y * z),
                1.0 - 2.0 * (x * x + y * y)
            )

        z_deg = math.degrees(yaw)
        x_deg = math.degrees(pitch)
        y_deg = math.degrees(roll)

        return (z_deg, x_deg, y_deg)

    @staticmethod
    def _quat_multiply(
        q1: Tuple[float, float, float, float],
        q2: Tuple[float, float, float, float],
    ) -> Tuple[float, float, float, float]:
        """Multiply two quaternions ``(w, x, y, z)``."""
        w1, x1, y1, z1 = q1
        w2, x2, y2, z2 = q2
        return (
            w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
            w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
        )

    @staticmethod
    def _quat_conjugate(
        q: Tuple[float, float, float, float],
    ) -> Tuple[float, float, float, float]:
        """Return the conjugate of a quaternion."""
        w, x, y, z = q
        return (w, -x, -y, -z)

    @staticmethod
    def _quat_inverse(
        q: Tuple[float, float, float, float],
    ) -> Tuple[float, float, float, float]:
        """Return the inverse of a unit quaternion."""
        return (q[0], -q[1], -q[2], -q[3])
