"""Landmark interpolation for the VisionMoCap motion pipeline.

Reconstructs landmarks with low visibility or confidence by linearly
interpolating between the nearest surrounding valid frames.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from src.config.manager import MotionConfig
from src.motion.base import SequenceProcessor, deep_copy_sequence
from src.motion.motion_sequence import MotionSequence
from src.pose.pose_result import Landmark, PoseResult


class LinearInterpolator(SequenceProcessor):
    """Reconstructs missing landmarks using linear interpolation.

    For every landmark index, frames whose ``visibility`` falls below
    *visibility_threshold* (or whose ``pose_detected`` is False) are
    considered invalid. The position of each invalid landmark is
    linearly interpolated from the nearest previous and next valid
    frames. If only one neighbour is available, that neighbour's value
    is used directly (forward / backward fill).

    This dramatically stabilises animation when the subject partially
    leaves the frame or when self-occlusion causes a joint to drop out
    for a few frames.
    """

    def __init__(
        self,
        config: Optional[MotionConfig] = None,
        visibility_threshold: Optional[float] = None,
    ) -> None:
        self._config = config or MotionConfig()
        self._visibility_threshold = (
            visibility_threshold
            if visibility_threshold is not None
            else self._config.visibility_threshold
        )
        self._logger = logging.getLogger(self.__class__.__name__)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(self, sequence: MotionSequence) -> MotionSequence:
        """Interpolate missing landmarks across the sequence.

        Args:
            sequence: Input MotionSequence (not mutated).

        Returns:
            New MotionSequence with low-visibility landmarks reconstructed.
        """
        result = deep_copy_sequence(sequence)
        poses = result.pose_results
        count = len(poses)
        self._log_start(self._logger, count)

        if count == 0:
            return result

        num_landmarks = self._landmark_count(poses)
        if num_landmarks == 0:
            return result

        for landmark_idx in range(num_landmarks):
            self._interpolate_landmark(
                poses, landmark_idx, self._visibility_threshold
            )

        self._log_done(self._logger, count)
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _landmark_count(poses: List[PoseResult]) -> int:
        """Return the landmark count from the first pose that has any."""
        for pose in poses:
            if pose.landmarks:
                return len(pose.landmarks)
        return 0

    def _interpolate_landmark(
        self,
        poses: List[PoseResult],
        landmark_idx: int,
        vis_threshold: float,
    ) -> None:
        """Fill invalid instances of a single landmark via interpolation."""
        valid_indices = [
            i
            for i, pose in enumerate(poses)
            if (
                pose.pose_detected
                and len(pose.landmarks) > landmark_idx
                and pose.landmarks[landmark_idx].visibility >= vis_threshold
            )
        ]

        if not valid_indices:
            return

        for i, pose in enumerate(poses):
            if pose.pose_detected and len(pose.landmarks) > landmark_idx:
                if pose.landmarks[landmark_idx].visibility >= vis_threshold:
                    continue
            prev_idx = self._find_nearest_before(valid_indices, i)
            next_idx = self._find_nearest_after(valid_indices, i)
            interpolated = self._compute_interpolated(
                poses, landmark_idx, i, prev_idx, next_idx
            )
            if interpolated is not None:
                self._set_landmark(pose, landmark_idx, interpolated)

    @staticmethod
    def _find_nearest_before(
        valid_indices: List[int], target: int
    ) -> Optional[int]:
        """Return the largest valid index <= target, or None."""
        result: Optional[int] = None
        for idx in valid_indices:
            if idx <= target:
                result = idx
            else:
                break
        return result

    @staticmethod
    def _find_nearest_after(
        valid_indices: List[int], target: int
    ) -> Optional[int]:
        """Return the smallest valid index >= target, or None."""
        for idx in valid_indices:
            if idx >= target:
                return idx
        return None

    @staticmethod
    def _compute_interpolated(
        poses: List[PoseResult],
        landmark_idx: int,
        target_idx: int,
        prev_idx: Optional[int],
        next_idx: Optional[int],
    ) -> Optional[Landmark]:
        """Linearly interpolate a landmark between two neighbours.

        Args:
            poses: All pose results in the sequence.
            landmark_idx: Index of the landmark being interpolated.
            target_idx: Frame index for which the landmark is needed.
            prev_idx: Nearest valid frame before or at *target_idx*.
            next_idx: Nearest valid frame at or after *target_idx*.

        Returns:
            A reconstructed Landmark, or None if no neighbours exist.
        """
        if prev_idx is None and next_idx is None:
            return None
        if prev_idx is None:
            src = poses[next_idx].landmarks[landmark_idx]
            return Landmark(
                x=src.x,
                y=src.y,
                z=src.z,
                visibility=src.visibility * 0.5,
            )
        if next_idx is None:
            src = poses[prev_idx].landmarks[landmark_idx]
            return Landmark(
                x=src.x,
                y=src.y,
                z=src.z,
                visibility=src.visibility * 0.5,
            )
        if prev_idx == next_idx:
            src = poses[prev_idx].landmarks[landmark_idx]
            return Landmark(
                x=src.x,
                y=src.y,
                z=src.z,
                visibility=src.visibility,
            )

        prev_lm = poses[prev_idx].landmarks[landmark_idx]
        next_lm = poses[next_idx].landmarks[landmark_idx]
        span = next_idx - prev_idx
        offset = target_idx - prev_idx
        t = max(0.0, min(1.0, offset / span)) if span > 0 else 0.0
        return Landmark(
            x=prev_lm.x + (next_lm.x - prev_lm.x) * t,
            y=prev_lm.y + (next_lm.y - prev_lm.y) * t,
            z=prev_lm.z + (next_lm.z - prev_lm.z) * t,
            visibility=(prev_lm.visibility + next_lm.visibility) / 2.0,
        )

    @staticmethod
    def _set_landmark(
        pose: PoseResult, landmark_idx: int, landmark: Landmark
    ) -> None:
        """Write a landmark into a pose, extending the list if needed."""
        if not pose.pose_detected or len(pose.landmarks) == 0:
            pose.landmarks = [
                Landmark(x=0.0, y=0.0, z=0.0, visibility=0.0)
                for _ in range(landmark_idx + 1)
            ]
            pose.pose_detected = True
        elif len(pose.landmarks) <= landmark_idx:
            while len(pose.landmarks) <= landmark_idx:
                pose.landmarks.append(
                    Landmark(x=0.0, y=0.0, z=0.0, visibility=0.0)
                )
        pose.landmarks[landmark_idx] = landmark
