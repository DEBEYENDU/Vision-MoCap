"""Noise reduction and outlier detection filters for motion sequences.

Each filter operates on landmark data frame-by-frame to reduce jitter,
smooth movement, or detect and replace implausible landmark jumps.
"""

from __future__ import annotations

import logging
import math
from typing import List, Optional

from src.config.manager import MotionConfig
from src.motion.base import SequenceProcessor, deep_copy_sequence
from src.motion.motion_sequence import MotionSequence
from src.pose.pose_result import Landmark, PoseResult


class MovingAverageFilter(SequenceProcessor):
    """Reduce frame-to-frame jitter by averaging over a sliding window.

    Each landmark's position is replaced by the mean of its positions
    within a symmetric window of *window* frames centred on the current
    frame. The window size is taken from ``MotionConfig.smoothing_window``
    and is clamped to at least 1. If an even value is provided it is
    reduced by one so that the window is symmetric.

    .. rubric:: Algorithm

        For each frame *i* and landmark *j* with valid neighbours in
        a window of size *W* = ``window`` centred on *i*:

        .. code::

            x[i] = (1 / N) * sum(x[start] .. x[end])

        where *start* = max(0, i - h), *end* = min(T, i + h + 1),
        *h* = (W - 1) / 2, and *N* is the number of valid frames
        in the window.

    Why this improves animation quality:
        High-frequency jitter from per-frame pose-estimation noise is
        attenuated. Slow, deliberate motion is preserved while rapid
        spurious landmark jumps are averaged away, producing a visually
        smoother animation.
    """

    def __init__(
        self,
        config: Optional[MotionConfig] = None,
        window: Optional[int] = None,
    ) -> None:
        self._config = config or MotionConfig()
        self._window = (
            window if window is not None else self._config.smoothing_window
        )
        if self._window < 1:
            self._window = 1
        if self._window % 2 == 0:
            self._window -= 1
        self._half_window = self._window // 2
        self._logger = logging.getLogger(self.__class__.__name__)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(self, sequence: MotionSequence) -> MotionSequence:
        result = deep_copy_sequence(sequence)
        poses = result.pose_results
        count = len(poses)
        self._log_start(self._logger, count)

        if count == 0 or self._window <= 1:
            return result

        num_landmarks = self._landmark_count(poses)
        if num_landmarks == 0:
            return result

        for landmark_idx in range(num_landmarks):
            self._smooth_landmark(poses, landmark_idx)

        self._log_done(self._logger, count)
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _landmark_count(poses: List[PoseResult]) -> int:
        for pose in poses:
            if pose.landmarks:
                return len(pose.landmarks)
        return 0

    def _smooth_landmark(
        self, poses: List[PoseResult], landmark_idx: int
    ) -> None:
        total = len(poses)
        for i in range(total):
            if self._is_missing(poses, i, landmark_idx):
                continue

            xs: List[float] = []
            ys: List[float] = []
            zs: List[float] = []
            vs: List[float] = []

            start = max(0, i - self._half_window)
            end = min(total, i + self._half_window + 1)

            for j in range(start, end):
                if not self._is_missing(poses, j, landmark_idx):
                    lm = poses[j].landmarks[landmark_idx]
                    xs.append(lm.x)
                    ys.append(lm.y)
                    zs.append(lm.z)
                    vs.append(lm.visibility)

            if xs:
                n = len(xs)
                poses[i].landmarks[landmark_idx] = Landmark(
                    x=sum(xs) / n,
                    y=sum(ys) / n,
                    z=sum(zs) / n,
                    visibility=sum(vs) / n,
                )

    @staticmethod
    def _is_missing(
        poses: List[PoseResult], idx: int, landmark_idx: int
    ) -> bool:
        pose = poses[idx]
        return (
            not pose.pose_detected
            or len(pose.landmarks) <= landmark_idx
        )


class ExponentialSmoothingFilter(SequenceProcessor):
    """Smooth noisy landmark movement with exponential moving average.

    Applies a first-order IIR (infinite impulse response) filter
    independently to each landmark's trajectory:

    .. code::

        s[0] = x[0]
        s[i] = alpha * x[i] + (1 - alpha) * s[i - 1]

    where *alpha* is the smoothing factor
    (``MotionConfig.exponential_alpha``).

    Why this improves animation quality:
        The recursive (IIR) structure provides a smooth trajectory with
        no fixed latency. High-frequency noise is progressively damped
        while the overall motion curve is preserved. A lower *alpha*
        value produces heavier smoothing; a higher value tracks raw
        motion more closely.
    """

    def __init__(
        self,
        config: Optional[MotionConfig] = None,
        alpha: Optional[float] = None,
    ) -> None:
        self._config = config or MotionConfig()
        self._alpha = (
            alpha if alpha is not None else self._config.exponential_alpha
        )
        self._alpha = max(0.0, min(1.0, self._alpha))
        self._logger = logging.getLogger(self.__class__.__name__)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(self, sequence: MotionSequence) -> MotionSequence:
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
            self._smooth_trajectory(poses, landmark_idx)

        self._log_done(self._logger, count)
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _landmark_count(poses: List[PoseResult]) -> int:
        for pose in poses:
            if pose.landmarks:
                return len(pose.landmarks)
        return 0

    def _smooth_trajectory(
        self, poses: List[PoseResult], landmark_idx: int
    ) -> None:
        total = len(poses)
        prev_x: Optional[float] = None
        prev_y: Optional[float] = None
        prev_z: Optional[float] = None
        prev_v: Optional[float] = None

        for i in range(total):
            if self._is_missing(poses, i, landmark_idx):
                prev_x = prev_y = prev_z = prev_v = None
                continue

            lm = poses[i].landmarks[landmark_idx]

            if prev_x is None:
                prev_x, prev_y, prev_z, prev_v = lm.x, lm.y, lm.z, lm.visibility
                continue

            smoothed_x = self._alpha * lm.x + (1.0 - self._alpha) * prev_x
            smoothed_y = self._alpha * lm.y + (1.0 - self._alpha) * prev_y
            smoothed_z = self._alpha * lm.z + (1.0 - self._alpha) * prev_z
            smoothed_v = self._alpha * lm.visibility + (1.0 - self._alpha) * prev_v

            poses[i].landmarks[landmark_idx] = Landmark(
                x=smoothed_x,
                y=smoothed_y,
                z=smoothed_z,
                visibility=smoothed_v,
            )

            prev_x, prev_y, prev_z, prev_v = (
                smoothed_x,
                smoothed_y,
                smoothed_z,
                smoothed_v,
            )

    @staticmethod
    def _is_missing(
        poses: List[PoseResult], idx: int, landmark_idx: int
    ) -> bool:
        pose = poses[idx]
        return (
            not pose.pose_detected
            or len(pose.landmarks) <= landmark_idx
        )


class OutlierRemovalFilter(SequenceProcessor):
    """Detect and replace impossible landmark jumps.

    Computes the Euclidean displacement of each landmark between
    consecutive valid frames.  If the displacement exceeds
    *outlier_threshold* (from ``MotionConfig``) the landmark at the
    later frame is flagged as an outlier and its position is linearly
    interpolated from the nearest non-outlier neighbours.

    .. rubric:: Algorithm

        1. Compute initial validity based on ``pose_detected``.
        2. For each landmark index, scan forward through the sequence:

           .. code::

               d = ||landmark[i] - landmark[i-1]||
               if d > threshold: mark frame *i* as invalid

        3. Replace every invalid landmark with a linear interpolation
           of the nearest preceding and following valid landmarks.

    Why this improves animation quality:
        Pose estimators occasionally produce single-frame spikes where
        a joint teleports to an implausible location.  Removing these
        outliers prevents jarring visual artefacts and ensures that
        downstream filters (moving average, exponential smoothing)
        operate on physically plausible data.
    """

    def __init__(
        self,
        config: Optional[MotionConfig] = None,
        outlier_threshold: Optional[float] = None,
        visibility_threshold: Optional[float] = None,
    ) -> None:
        self._config = config or MotionConfig()
        self._outlier_threshold = (
            outlier_threshold
            if outlier_threshold is not None
            else self._config.outlier_threshold
        )
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
            valid = self._initial_validity(poses, landmark_idx)
            valid = self._detect_outliers(poses, landmark_idx, valid)
            self._fill_invalid(poses, landmark_idx, valid)

        self._log_done(self._logger, count)
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _landmark_count(poses: List[PoseResult]) -> int:
        for pose in poses:
            if pose.landmarks:
                return len(pose.landmarks)
        return 0

    def _initial_validity(
        self, poses: List[PoseResult], landmark_idx: int
    ) -> List[bool]:
        valid: List[bool] = []
        for pose in poses:
            if (
                pose.pose_detected
                and len(pose.landmarks) > landmark_idx
                and pose.landmarks[landmark_idx].visibility
                >= self._visibility_threshold
            ):
                valid.append(True)
            else:
                valid.append(False)
        return valid

    def _detect_outliers(
        self,
        poses: List[PoseResult],
        landmark_idx: int,
        valid: List[bool],
    ) -> List[bool]:
        result: List[bool] = list(valid)
        prev_valid_idx: Optional[int] = None

        for i in range(len(poses)):
            if not result[i]:
                prev_valid_idx = None
                continue

            if prev_valid_idx is not None:
                dx = (
                    poses[i].landmarks[landmark_idx].x
                    - poses[prev_valid_idx].landmarks[landmark_idx].x
                )
                dy = (
                    poses[i].landmarks[landmark_idx].y
                    - poses[prev_valid_idx].landmarks[landmark_idx].y
                )
                dz = (
                    poses[i].landmarks[landmark_idx].z
                    - poses[prev_valid_idx].landmarks[landmark_idx].z
                )
                dist = math.sqrt(dx * dx + dy * dy + dz * dz)

                if dist > self._outlier_threshold:
                    result[i] = False
                    continue

            prev_valid_idx = i

        return result

    def _fill_invalid(
        self,
        poses: List[PoseResult],
        landmark_idx: int,
        valid: List[bool],
    ) -> None:
        total = len(poses)

        for i in range(total):
            if valid[i]:
                continue

            prev_idx: Optional[int] = None
            for j in range(i - 1, -1, -1):
                if valid[j]:
                    prev_idx = j
                    break

            next_idx: Optional[int] = None
            for j in range(i + 1, total):
                if valid[j]:
                    next_idx = j
                    break

            if prev_idx is None and next_idx is None:
                continue
            if prev_idx is None:
                src = poses[next_idx].landmarks[landmark_idx]
                poses[i].landmarks[landmark_idx] = Landmark(
                    x=src.x,
                    y=src.y,
                    z=src.z,
                    visibility=src.visibility * 0.5,
                )
                valid[i] = True
                continue
            if next_idx is None:
                src = poses[prev_idx].landmarks[landmark_idx]
                poses[i].landmarks[landmark_idx] = Landmark(
                    x=src.x,
                    y=src.y,
                    z=src.z,
                    visibility=src.visibility * 0.5,
                )
                valid[i] = True
                continue

            prev_lm = poses[prev_idx].landmarks[landmark_idx]
            next_lm = poses[next_idx].landmarks[landmark_idx]
            span = next_idx - prev_idx
            offset = i - prev_idx
            t = max(0.0, min(1.0, offset / span)) if span > 0 else 0.0

            poses[i].landmarks[landmark_idx] = Landmark(
                x=prev_lm.x + (next_lm.x - prev_lm.x) * t,
                y=prev_lm.y + (next_lm.y - prev_lm.y) * t,
                z=prev_lm.z + (next_lm.z - prev_lm.z) * t,
                visibility=(prev_lm.visibility + next_lm.visibility) / 2.0,
            )
            valid[i] = True
