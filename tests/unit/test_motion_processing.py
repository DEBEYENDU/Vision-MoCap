"""Unit tests for the motion processing layer (src/motion).

Covers MotionProcessor orchestration plus the individual filters:
moving average, exponential smoothing, outlier removal, and linear
interpolation of missing landmarks.
"""

from __future__ import annotations

import math
from typing import List

from src.config.manager import MotionConfig
from src.motion.filters import (
    ExponentialSmoothingFilter,
    MovingAverageFilter,
    OutlierRemovalFilter,
)
from src.motion.interpolator import LinearInterpolator
from src.motion.motion_processor import MotionProcessor
from src.motion.motion_sequence import MotionSequence
from src.pose.pose_result import Landmark, PoseResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_landmarks(count: int = 33) -> List[Landmark]:
    return [
        Landmark(x=0.5, y=0.5, z=0.0, visibility=0.95)
        for _ in range(count)
    ]


def _make_pose(
    timestamp: float,
    x: float = 0.5,
    landmark_index: int = 0,
    detected: bool = True,
) -> PoseResult:
    landmarks = _make_landmarks()
    landmarks[landmark_index] = Landmark(x=x, y=0.5, z=0.0, visibility=0.95)
    return PoseResult(
        timestamp=timestamp,
        landmarks=landmarks,
        world_landmarks=landmarks,
        confidence=0.9,
        frame_width=640,
        frame_height=480,
        pose_detected=detected,
    )


def _make_sequence(
    values: List[float], landmark_index: int = 0
) -> MotionSequence:
    poses = [
        _make_pose(float(i), x=v, landmark_index=landmark_index)
        for i, v in enumerate(values)
    ]
    return MotionSequence(
        pose_results=poses,
        start_time=0.0,
        end_time=float(len(poses) - 1),
        total_frames=len(poses),
        average_fps=30.0,
        duration=float(len(poses) - 1),
    )


# ---------------------------------------------------------------------------
# MotionProcessor
# ---------------------------------------------------------------------------


class TestMotionProcessor:
    def test_process_returns_new_sequence(self) -> None:
        seq = _make_sequence([0.1, 0.2, 0.3])
        proc = MotionProcessor()
        out = proc.process(seq)
        assert out is not seq
        assert len(out.pose_results) == 3

    def test_process_preserves_timestamps_and_metadata(self) -> None:
        seq = _make_sequence([0.1, 0.2, 0.3])
        proc = MotionProcessor()
        out = proc.process(seq)
        assert [p.timestamp for p in out.pose_results] == [0.0, 1.0, 2.0]
        assert out.pose_results[0].frame_width == 640
        assert out.pose_results[0].frame_height == 480

    def test_original_sequence_not_mutated(self) -> None:
        seq = _make_sequence([0.1, 0.2, 0.3])
        original_x = seq.pose_results[1].landmarks[0].x
        MotionProcessor().process(seq)
        assert seq.pose_results[1].landmarks[0].x == original_x

    def test_empty_sequence_returns_copy(self) -> None:
        seq = MotionSequence(pose_results=[], total_frames=0)
        out = MotionProcessor().process(seq)
        assert out.pose_results == []

    def test_default_pipeline_order(self) -> None:
        proc = MotionProcessor()
        names = [p.name for p in proc.pipeline]
        assert len(names) == 4
        assert names == [
            "OutlierRemovalFilter",
            "LinearInterpolator",
            "MovingAverageFilter",
            "ExponentialSmoothingFilter",
        ]

    def test_custom_pipeline_injection(self) -> None:
        only = MovingAverageFilter(window=3)
        proc = MotionProcessor(processors=[only])
        assert len(proc.pipeline) == 1
        out = proc.process(_make_sequence([0.1, 0.5, 0.2]))
        assert len(out.pose_results) == 3


# ---------------------------------------------------------------------------
# MovingAverageFilter
# ---------------------------------------------------------------------------


class TestMovingAverageFilter:
    def test_smoothes_noisy_value(self) -> None:
        seq = _make_sequence([0.0, 1.0, 0.0, 0.5, 0.1])
        filt = MovingAverageFilter(window=3)
        out = filt.process(seq)
        # Frame 0 averages the window [0, 1] (both unmodified at this point).
        assert abs(out.pose_results[0].landmarks[0].x - (0.0 + 1.0) / 2.0) < 1e-9
        # Jitter (max adjacent step) is reduced.
        raw = [p.landmarks[0].x for p in seq.pose_results]
        sm = [p.landmarks[0].x for p in out.pose_results]
        raw_step = max(abs(b - a) for a, b in zip(raw, raw[1:]))
        sm_step = max(abs(b - a) for a, b in zip(sm, sm[1:]))
        assert sm_step < raw_step
        # Original untouched.
        assert seq.pose_results[0].landmarks[0].x == 0.0

    def test_window_one_is_identity(self) -> None:
        seq = _make_sequence([0.1, 0.2, 0.3])
        filt = MovingAverageFilter(window=1)
        out = filt.process(seq)
        assert [p.landmarks[0].x for p in out.pose_results] == [0.1, 0.2, 0.3]

    def test_missing_frames_skipped(self) -> None:
        poses = [
            _make_pose(0.0, x=0.1),
            _make_pose(1.0, x=0.5, detected=False),
            _make_pose(2.0, x=0.3),
        ]
        seq = MotionSequence(
            pose_results=poses, total_frames=3, average_fps=30.0, duration=2.0
        )
        filt = MovingAverageFilter(window=5)
        out = filt.process(seq)
        # Frame 0 window = [0, 1, 2]; frame 1 missing, so mean of valid only.
        assert abs(out.pose_results[0].landmarks[0].x - (0.1 + 0.3) / 2.0) < 1e-9


# ---------------------------------------------------------------------------
# ExponentialSmoothingFilter
# ---------------------------------------------------------------------------


class TestExponentialSmoothingFilter:
    def test_first_value_unchanged(self) -> None:
        seq = _make_sequence([0.7, 0.7, 0.7])
        filt = ExponentialSmoothingFilter(alpha=0.5)
        out = filt.process(seq)
        assert out.pose_results[0].landmarks[0].x == 0.7

    def test_alpha_one_is_identity(self) -> None:
        seq = _make_sequence([0.1, 0.9, 0.2])
        filt = ExponentialSmoothingFilter(alpha=1.0)
        out = filt.process(seq)
        assert [p.landmarks[0].x for p in out.pose_results] == [0.1, 0.9, 0.2]

    def test_recursive_smoothing(self) -> None:
        seq = _make_sequence([0.0, 1.0, 1.0])
        filt = ExponentialSmoothingFilter(alpha=0.5)
        out = filt.process(seq)
        assert out.pose_results[1].landmarks[0].x == 0.5
        assert out.pose_results[2].landmarks[0].x == 0.75

    def test_alpha_clamped(self) -> None:
        filt = ExponentialSmoothingFilter(alpha=5.0)
        assert filt._alpha == 1.0
        filt2 = ExponentialSmoothingFilter(alpha=-1.0)
        assert filt2._alpha == 0.0


# ---------------------------------------------------------------------------
# OutlierRemovalFilter
# ---------------------------------------------------------------------------


class TestOutlierRemovalFilter:
    def test_removes_single_frame_spike(self) -> None:
        seq = _make_sequence([0.1, 0.9, 0.1])
        filt = OutlierRemovalFilter(outlier_threshold=0.5)
        out = filt.process(seq)
        # Middle value is interpolated between its neighbours.
        assert abs(out.pose_results[1].landmarks[0].x - 0.1) < 1e-9

    def test_small_motion_preserved(self) -> None:
        seq = _make_sequence([0.1, 0.12, 0.11])
        filt = OutlierRemovalFilter(outlier_threshold=0.5)
        out = filt.process(seq)
        assert abs(out.pose_results[1].landmarks[0].x - 0.12) < 1e-9

    def test_edge_frames_filled_from_single_neighbour(self) -> None:
        seq = _make_sequence([0.9, 0.1, 0.5])
        filt = OutlierRemovalFilter(outlier_threshold=0.5)
        out = filt.process(seq)
        # Frame 0→1 jumped 0.8 → frame 1 flagged; frame 2 within 0.5 of
        # frame 0 so it stays valid.
        assert abs(out.pose_results[1].landmarks[0].x - (0.9 + 0.5) / 2.0) < 1e-9
        # Valid frames are unchanged.
        assert abs(out.pose_results[0].landmarks[0].x - 0.9) < 1e-9
        assert abs(out.pose_results[2].landmarks[0].x - 0.5) < 1e-9


# ---------------------------------------------------------------------------
# LinearInterpolator
# ---------------------------------------------------------------------------


class TestLinearInterpolator:
    def test_fills_low_visibility_landmark(self) -> None:
        poses = [
            PoseResult(
                timestamp=0.0,
                landmarks=[Landmark(x=0.1, y=0.1, z=0.0, visibility=0.9)],
                confidence=0.9,
                pose_detected=True,
            ),
            PoseResult(
                timestamp=1.0,
                landmarks=[Landmark(x=0.0, y=0.0, z=0.0, visibility=0.1)],
                confidence=0.9,
                pose_detected=True,
            ),
            PoseResult(
                timestamp=2.0,
                landmarks=[Landmark(x=0.3, y=0.3, z=0.0, visibility=0.9)],
                confidence=0.9,
                pose_detected=True,
            ),
        ]
        seq = MotionSequence(
            pose_results=poses, total_frames=3, average_fps=30.0, duration=2.0
        )
        filt = LinearInterpolator(visibility_threshold=0.5)
        out = filt.process(seq)
        assert abs(out.pose_results[1].landmarks[0].x - 0.2) < 1e-9

    def test_undetected_pose_reconstructed(self) -> None:
        poses = [
            _make_pose(0.0, x=0.1),
            _make_pose(1.0, x=0.5, detected=False),
            _make_pose(2.0, x=0.9),
        ]
        seq = MotionSequence(
            pose_results=poses, total_frames=3, average_fps=30.0, duration=2.0
        )
        filt = LinearInterpolator(visibility_threshold=0.5)
        out = filt.process(seq)
        assert out.pose_results[1].pose_detected
        assert abs(out.pose_results[1].landmarks[0].x - 0.5) < 1e-9


# ---------------------------------------------------------------------------
# Landing: MotionConfig defaults are usable
# ---------------------------------------------------------------------------


class TestMotionConfigIntegration:
    def test_default_config_constructs_all_filters(self) -> None:
        cfg = MotionConfig()
        filters = [
            MovingAverageFilter(cfg),
            ExponentialSmoothingFilter(cfg),
            OutlierRemovalFilter(cfg),
            LinearInterpolator(cfg),
        ]
        for f in filters:
            assert f is not None