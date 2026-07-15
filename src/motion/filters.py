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


class OneEuroFilter(SequenceProcessor):
    """Adaptive low-pass filter for jitter reduction (1€ filter).

    The cutoff frequency decreases with the velocity of the signal:
    slow movements are smoothed more, fast movements are smoothed less.
    This preserves responsiveness while eliminating jitter.

    Parameters are taken from ``MotionConfig``:
        one_euro_min_cutoff: Minimum cutoff frequency (Hz).
        one_euro_beta: Velocity coefficient for cutoff adaptation.
        one_euro_derivative_cutoff: Cutoff for velocity low-pass.

    Reference:
        Casiez, G., Roussel, N., & Vogel, D. (2012). 1€ filter.
        https://doi.org/10.1145/2380116.2380149
    """

    def __init__(
        self,
        config: Optional[MotionConfig] = None,
        min_cutoff: Optional[float] = None,
        beta: Optional[float] = None,
        derivative_cutoff: Optional[float] = None,
    ) -> None:
        self._config = config or MotionConfig()
        self._min_cutoff = (
            min_cutoff if min_cutoff is not None
            else self._config.one_euro_min_cutoff
        )
        self._beta = (
            beta if beta is not None
            else self._config.one_euro_beta
        )
        self._derivative_cutoff = (
            derivative_cutoff if derivative_cutoff is not None
            else self._config.one_euro_derivative_cutoff
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

        if count < 2:
            return result

        num_landmarks = self._landmark_count(poses)
        if num_landmarks == 0:
            return result

        for landmark_idx in range(num_landmarks):
            self._filter_landmark(poses, landmark_idx)

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

    @staticmethod
    def _is_missing(
        poses: List[PoseResult], idx: int, landmark_idx: int
    ) -> bool:
        pose = poses[idx]
        return (
            not pose.pose_detected
            or len(pose.landmarks) <= landmark_idx
        )

    @staticmethod
    def _alpha( cutoff: float, elapsed: float) -> float:
        tau = 1.0 / (2.0 * math.pi * max(cutoff, 1e-9))
        return 1.0 / (1.0 + tau / max(elapsed, 1e-9))

    def _filter_landmark(
        self, poses: List[PoseResult], landmark_idx: int
    ) -> None:
        total = len(poses)
        prev_x: Optional[float] = None
        prev_y: Optional[float] = None
        prev_z: Optional[float] = None
        prev_v: Optional[float] = None
        vx: float = 0.0
        vy: float = 0.0
        vz: float = 0.0
        vv: float = 0.0
        prev_t: Optional[float] = None
        prev_valid: Optional[int] = None

        for i in range(total):
            if self._is_missing(poses, i, landmark_idx):
                prev_valid = None
                continue

            lm = poses[i].landmarks[landmark_idx]
            t = poses[i].timestamp

            if prev_valid is None:
                prev_x, prev_y, prev_z, prev_v = lm.x, lm.y, lm.z, lm.visibility
                vx = vy = vz = vv = 0.0
                prev_t = t
                prev_valid = i
                continue

            elapsed = max(t - prev_t, 1e-9)

            # Adaptive cutoff
            cutoff = self._min_cutoff + self._beta * math.sqrt(
                vx * vx + vy * vy + vz * vz
            )

            alpha = self._alpha(cutoff, elapsed)
            v_alpha = self._alpha(self._derivative_cutoff, elapsed)

            # Filter value
            fx = alpha * lm.x + (1.0 - alpha) * prev_x
            fy = alpha * lm.y + (1.0 - alpha) * prev_y
            fz = alpha * lm.z + (1.0 - alpha) * prev_z
            fv = alpha * lm.visibility + (1.0 - alpha) * prev_v

            poses[i].landmarks[landmark_idx] = Landmark(
                x=fx, y=fy, z=fz, visibility=fv,
            )

            # Update velocity (filtered)
            raw_vx = (fx - prev_x) / elapsed if prev_valid is not None else 0.0
            raw_vy = (fy - prev_y) / elapsed if prev_valid is not None else 0.0
            raw_vz = (fz - prev_z) / elapsed if prev_valid is not None else 0.0
            raw_vv = (fv - prev_v) / elapsed if prev_valid is not None else 0.0

            vx = v_alpha * raw_vx + (1.0 - v_alpha) * vx
            vy = v_alpha * raw_vy + (1.0 - v_alpha) * vy
            vz = v_alpha * raw_vz + (1.0 - v_alpha) * vz
            vv = v_alpha * raw_vv + (1.0 - v_alpha) * vv

            prev_x, prev_y, prev_z, prev_v = fx, fy, fz, fv
            prev_t = t
            prev_valid = i

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    @property
    def min_cutoff(self) -> float:
        return self._min_cutoff

    @property
    def beta(self) -> float:
        return self._beta

    @property
    def derivative_cutoff(self) -> float:
        return self._derivative_cutoff


class SavitzkyGolayFilter(SequenceProcessor):
    """Smooth landmark trajectories using Savitzky–Golay filtering.

    Fits a polynomial of order *polyorder* to each landmark's trajectory
    within a sliding window of *window_length* frames and replaces each
    point with the fitted value.  Preserves higher-order moments (peaks,
    valleys) better than a simple moving average.

    Parameters are taken from ``MotionConfig``:
        savgol_window_length: Odd window length (default 5).
        savgol_polyorder: Polynomial order (default 2).

    Requires ``scipy.signal``.
    """

    def __init__(
        self,
        config: Optional[MotionConfig] = None,
        window_length: Optional[int] = None,
        polyorder: Optional[int] = None,
    ) -> None:
        self._config = config or MotionConfig()
        self._window_length = (
            window_length if window_length is not None
            else self._config.savgol_window_length
        )
        self._polyorder = (
            polyorder if polyorder is not None
            else self._config.savgol_polyorder
        )
        if self._window_length < 3:
            self._window_length = 3
        if self._window_length % 2 == 0:
            self._window_length -= 1
        if self._polyorder >= self._window_length:
            self._polyorder = self._window_length - 1
        self._logger = logging.getLogger(self.__class__.__name__)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(self, sequence: MotionSequence) -> MotionSequence:
        result = deep_copy_sequence(sequence)
        poses = result.pose_results
        count = len(poses)
        self._log_start(self._logger, count)

        if count < self._window_length:
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

    @staticmethod
    def _is_missing(
        poses: List[PoseResult], idx: int, landmark_idx: int
    ) -> bool:
        pose = poses[idx]
        return (
            not pose.pose_detected
            or len(pose.landmarks) <= landmark_idx
        )

    def _smooth_landmark(
        self, poses: List[PoseResult], landmark_idx: int
    ) -> None:
        from scipy.signal import savgol_filter

        total = len(poses)
        xs: List[float] = []
        ys: List[float] = []
        zs: List[float] = []
        vs: List[float] = []
        valid_indices: List[int] = []

        for i in range(total):
            if not self._is_missing(poses, i, landmark_idx):
                lm = poses[i].landmarks[landmark_idx]
                xs.append(lm.x)
                ys.append(lm.y)
                zs.append(lm.z)
                vs.append(lm.visibility)
                valid_indices.append(i)

        n_valid = len(xs)
        if n_valid < self._window_length:
            return

        wl = min(self._window_length, n_valid if n_valid % 2 == 1 else n_valid - 1)
        po = min(self._polyorder, wl - 1)
        if wl < 3:
            return

        try:
            sx = savgol_filter(xs, wl, po)
            sy = savgol_filter(ys, wl, po)
            sz = savgol_filter(zs, wl, po)
            sv = savgol_filter(vs, wl, po)
        except Exception:
            self._logger.warning(
                "SavGol filter failed for landmark %d, skipping.",
                landmark_idx,
            )
            return

        for j, idx in enumerate(valid_indices):
            poses[idx].landmarks[landmark_idx] = Landmark(
                x=float(sx[j]),
                y=float(sy[j]),
                z=float(sz[j]),
                visibility=float(sv[j]),
            )
