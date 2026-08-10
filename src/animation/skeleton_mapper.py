"""Skeleton mapping for the VisionMoCap animation subsystem.

Maps MediaPipe Pose landmarks (33 indices) to avatar bone positions
using a configurable mapping dictionary.  Preset configurations are
provided for common rig formats (Mixamo, Blender/Rigify, VRM, Ready
Player Me) but the mapper itself is agnostic to bone names — it simply
follows whatever mapping it is given.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

from src.core.models import Vector3D
from src.pose.pose_result import Landmark, PoseResult

# ------------------------------------------------------------------
# Mapping entry type
# ------------------------------------------------------------------

BoneMapping = Dict[str, int]
"""A single bone mapping entry: ``{"head": <landmark_idx>, "tail": <landmark_idx>}``."""

SkeletonMapping = Dict[str, BoneMapping]
"""Complete mapping from avatar bone names to landmark indices.

Example::

    {"LeftUpperArm": {"head": 11, "tail": 13}}
"""

# ------------------------------------------------------------------
# Preset configurations
# ------------------------------------------------------------------
# Each preset maps a common rig's bone names to MediaPipe landmark
# indices.  Because bone naming varies between rig formats these
# presets use generic English names; users aliasing them to their
# rig's exact bone names via the *aliases* parameter of SkeletonMapper.
# ------------------------------------------------------------------

# MediaPipe landmark reference:
#   0:nose  1:l_eye_inner  2:l_eye  3:l_eye_outer
#   4:r_eye_inner  5:r_eye  6:r_eye_outer  7:l_ear  8:r_ear
#   9:mouth_l  10:mouth_r  11:l_shoulder  12:r_shoulder
#   13:l_elbow  14:r_elbow  15:l_wrist  16:r_wrist
#   17:l_pinky  18:r_pinky  19:l_index  20:r_index
#   21:l_thumb  22:r_thumb  23:l_hip  24:r_hip
#   25:l_knee  26:r_knee  27:l_ankle  28:r_ankle
#   29:l_heel  30:r_heel  31:l_foot_index  32:r_foot_index

PRESET_MIXAMO: SkeletonMapping = {
    "Hips":               {"head": 23, "tail": 24},
    "Spine":              {"head": 23, "tail": 11},
    "Spine1":             {"head": 11, "tail": 12},
    "Spine2":             {"head": 12, "tail": 0},
    "Neck":               {"head": 12, "tail": 0},
    "Head":               {"head": 0,  "tail": 2},
    "LeftShoulder":       {"head": 11, "tail": 13},
    "LeftUpperArm":       {"head": 11, "tail": 13},
    "LeftForearm":        {"head": 13, "tail": 15},
    "LeftHand":           {"head": 15, "tail": 19},
    "RightShoulder":      {"head": 12, "tail": 14},
    "RightUpperArm":      {"head": 12, "tail": 14},
    "RightForearm":       {"head": 14, "tail": 16},
    "RightHand":          {"head": 16, "tail": 20},
    "LeftUpLeg":          {"head": 23, "tail": 25},
    "LeftLeg":            {"head": 25, "tail": 27},
    "LeftFoot":           {"head": 27, "tail": 31},
    "LeftToeBase":        {"head": 31, "tail": 29},
    "RightUpLeg":         {"head": 24, "tail": 26},
    "RightLeg":           {"head": 26, "tail": 28},
    "RightFoot":          {"head": 28, "tail": 32},
    "RightToeBase":       {"head": 32, "tail": 30},
}

PRESET_BLENDER: SkeletonMapping = {
    "hips":               {"head": 23, "tail": 24},
    "spine":              {"head": 23, "tail": 11},
    "chest":              {"head": 11, "tail": 12},
    "upper_chest":        {"head": 12, "tail": 0},
    "neck":               {"head": 12, "tail": 0},
    "head":               {"head": 0,  "tail": 2},
    "shoulder.L":         {"head": 11, "tail": 13},
    "upper_arm.L":        {"head": 11, "tail": 13},
    "forearm.L":          {"head": 13, "tail": 15},
    "hand.L":             {"head": 15, "tail": 19},
    "shoulder.R":         {"head": 12, "tail": 14},
    "upper_arm.R":        {"head": 12, "tail": 14},
    "forearm.R":          {"head": 14, "tail": 16},
    "hand.R":             {"head": 16, "tail": 20},
    "thigh.L":            {"head": 23, "tail": 25},
    "shin.L":             {"head": 25, "tail": 27},
    "foot.L":             {"head": 27, "tail": 31},
    "thigh.R":            {"head": 24, "tail": 26},
    "shin.R":             {"head": 26, "tail": 28},
    "foot.R":             {"head": 28, "tail": 32},
}

PRESET_VRM: SkeletonMapping = {
    "hips":               {"head": 23, "tail": 24},
    "spine":              {"head": 23, "tail": 11},
    "chest":              {"head": 11, "tail": 12},
    "upperChest":         {"head": 12, "tail": 0},
    "neck":               {"head": 12, "tail": 0},
    "head":               {"head": 0,  "tail": 2},
    "leftUpperArm":       {"head": 11, "tail": 13},
    "leftLowerArm":       {"head": 13, "tail": 15},
    "leftHand":           {"head": 15, "tail": 19},
    "rightUpperArm":      {"head": 12, "tail": 14},
    "rightLowerArm":      {"head": 14, "tail": 16},
    "rightHand":          {"head": 16, "tail": 20},
    "leftUpperLeg":       {"head": 23, "tail": 25},
    "leftLowerLeg":       {"head": 25, "tail": 27},
    "leftFoot":           {"head": 27, "tail": 31},
    "leftToes":           {"head": 31, "tail": 29},
    "rightUpperLeg":      {"head": 24, "tail": 26},
    "rightLowerLeg":      {"head": 26, "tail": 28},
    "rightFoot":          {"head": 28, "tail": 32},
    "rightToes":          {"head": 32, "tail": 30},
}

PRESET_READY_PLAYER_ME: SkeletonMapping = {
    "Hips":               {"head": 23, "tail": 24},
    "Spine":              {"head": 23, "tail": 11},
    "Spine1":             {"head": 11, "tail": 12},
    "Spine2":             {"head": 12, "tail": 0},
    "Neck":               {"head": 12, "tail": 0},
    "Head":               {"head": 0,  "tail": 2},
    "LeftArm":            {"head": 11, "tail": 13},
    "LeftForearm":        {"head": 13, "tail": 15},
    "LeftHand":           {"head": 15, "tail": 19},
    "RightArm":           {"head": 12, "tail": 14},
    "RightForearm":       {"head": 14, "tail": 16},
    "RightHand":          {"head": 16, "tail": 20},
    "LeftUpLeg":          {"head": 23, "tail": 25},
    "LeftLeg":            {"head": 25, "tail": 27},
    "LeftFoot":           {"head": 27, "tail": 31},
    "RightUpLeg":         {"head": 24, "tail": 26},
    "RightLeg":           {"head": 26, "tail": 28},
    "RightFoot":          {"head": 28, "tail": 32},
}

# Lookup from preset name to preset dict.
AVAILABLE_PRESETS: Dict[str, SkeletonMapping] = {
    "mixamo": PRESET_MIXAMO,
    "blender": PRESET_BLENDER,
    "vrm": PRESET_VRM,
    "ready_player_me": PRESET_READY_PLAYER_ME,
}


class SkeletonMapper:
    """Maps MediaPipe landmarks to avatar bone positions.

    The mapper is driven by a configurable :class:`SkeletonMapping`
    dictionary that associates each avatar bone name with a pair of
    MediaPipe landmark indices (head and tail).  It does **not**
    hardcode bone names — the mapping is provided externally.

    Coordinate conversion:
        MediaPipe uses *x*‑right, *y*‑down, *z*‑depth.  By default the
        mapper converts to *x*‑right, *y*‑up, *z*‑forward by flipping
        *y* and negating *z*.  This can be disabled with *flip_y* and
        *flip_z*.
    """

    def __init__(
        self,
        mapping: Optional[SkeletonMapping] = None,
        preset: Optional[str] = None,
        aliases: Optional[Dict[str, str]] = None,
        flip_y: bool = True,
        flip_z: bool = True,
    ) -> None:
        if mapping is not None and preset is not None:
            raise ValueError(
                "Provide either a custom *mapping* or a *preset* name, not both."
            )
        if mapping is not None:
            self._mapping = mapping
        elif preset is not None:
            if preset not in AVAILABLE_PRESETS:
                raise ValueError(
                    f"Unknown preset '{preset}'. "
                    f"Available: {list(AVAILABLE_PRESETS)}."
                )
            self._mapping = dict(AVAILABLE_PRESETS[preset])
        else:
            self._mapping = {}

        # Apply aliases — rename keys in the mapping to match the
        # avatar's actual bone names without losing the landmark indices.
        if aliases:
            remapped: SkeletonMapping = {}
            for bone_name, entry in self._mapping.items():
                target = aliases.get(bone_name, bone_name)
                remapped[target] = entry
            self._mapping = remapped

        self._flip_y = flip_y
        self._flip_z = flip_z
        self._logger = logging.getLogger(self.__class__.__name__)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def mapping(self) -> SkeletonMapping:
        """Read-only view of the current bone-to-landmark mapping."""
        return dict(self._mapping)

    def has_bone(self, name: str) -> bool:
        """Return whether a bone with *name* is present in the mapping."""
        return name in self._mapping

    @property
    def bone_names(self) -> List[str]:
        """Return the list of bone names this mapper knows about."""
        return list(self._mapping.keys())

    def map_frame(
        self, pose_result: PoseResult
    ) -> Dict[str, Tuple[Vector3D, Vector3D]]:
        """Map a single pose frame to bone head/tail positions.

        Bones whose landmark indices are out of range for this pose
        result (incomplete/missing landmarks) are skipped, matching the
        Retargeter's contract of tolerant partial mappings.

        Args:
            pose_result: A single frame's pose data from the estimator.

        Returns:
            ``{bone_name: (head_position, tail_position)}`` for every
            bone in the mapping whose landmarks are present.  Both
            positions are in the converted coordinate space.
        """
        landmarks = (
            pose_result.world_landmarks
            if pose_result.world_landmarks
            else pose_result.landmarks
        )
        max_idx = len(landmarks) - 1

        result: Dict[str, Tuple[Vector3D, Vector3D]] = {}
        for bone_name, entry in self._mapping.items():
            head_idx = entry["head"]
            tail_idx = entry["tail"]

            if head_idx > max_idx or tail_idx > max_idx:
                continue

            head_pos = self._landmark_to_vector(landmarks[head_idx])
            tail_pos = self._landmark_to_vector(landmarks[tail_idx])
            result[bone_name] = (head_pos, tail_pos)

        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _landmark_to_vector(self, lm: Landmark) -> Vector3D:
        """Convert a MediaPipe Landmark to a Vector3D with coordinate
        space conversion applied."""
        x = lm.x
        y = 1.0 - lm.y if self._flip_y else lm.y
        z = -lm.z if self._flip_z else lm.z
        return Vector3D(x, y, z)
