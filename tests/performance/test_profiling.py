"""Performance benchmarks for core VisionMoCap pipelines.

These tests measure throughput of critical paths and fail if they
exceed defined latency budgets.  Run with::

    pytest tests/performance/ -v
"""

from __future__ import annotations

import time
from typing import List

import numpy as np

from src.motion.motion_sequence import MotionSequence
from src.pose.pose_result import Landmark, PoseResult

# ---------------------------------------------------------------------------
# Budgets (seconds)
# ---------------------------------------------------------------------------
_FRAME_PROCESS_BUDGET = 0.033  # 30 FPS target
_PLAYBACK_SEEK_BUDGET = 0.001
_SEQUENCE_COPY_BUDGET = 0.010  # 10 ms for a 1000-frame sequence


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_landmarks(count: int = 33) -> List[Landmark]:
    return [
        Landmark(x=float(i), y=float(i * 2), z=float(i * 3), visibility=0.9)
        for i in range(count)
    ]


def _make_pose(timestamp: float) -> PoseResult:
    return PoseResult(
        timestamp=timestamp,
        landmarks=_make_landmarks(),
        world_landmarks=_make_landmarks(),
        confidence=0.85,
        frame_width=640,
        frame_height=480,
        pose_detected=True,
    )


def _make_sequence(n_frames: int = 1000) -> MotionSequence:
    return MotionSequence(
        pose_results=[_make_pose(float(i) / 30.0) for i in range(n_frames)],
        start_time=0.0,
        end_time=float(n_frames) / 30.0,
        total_frames=n_frames,
        average_fps=30.0,
        duration=float(n_frames) / 30.0,
    )


# ---------------------------------------------------------------------------
# Benchmarks
# ---------------------------------------------------------------------------


class TestFrameProcessing:
    """Measure raw pose result construction throughput."""

    def test_frame_rate_budget(self) -> None:
        """Building a PoseResult should take less than 33 ms."""
        lm = _make_landmarks()
        start = time.perf_counter()
        for _ in range(100):
            PoseResult(
                timestamp=1.0,
                landmarks=lm,
                world_landmarks=lm,
                confidence=0.85,
                frame_width=640,
                frame_height=480,
                pose_detected=True,
            )
        elapsed = (time.perf_counter() - start) / 100
        assert elapsed < _FRAME_PROCESS_BUDGET, (
            f"PoseResult construction took {elapsed*1000:.1f} ms "
            f"(budget {_FRAME_PROCESS_BUDGET*1000:.1f} ms)"
        )


class TestPlaybackPerformance:
    """Measure seek and advance performance."""

    def test_seek_latency(self) -> None:
        """Seeking in a 1000-frame sequence should be fast."""
        from src.playback.playback_player import PlaybackPlayer

        player = PlaybackPlayer()
        player.load(_make_sequence())

        start = time.perf_counter()
        for i in range(100):
            player.seek(i * 10)
        elapsed = (time.perf_counter() - start) / 100
        assert elapsed < _PLAYBACK_SEEK_BUDGET, (
            f"Seek took {elapsed*1000:.1f} ms "
            f"(budget {_PLAYBACK_SEEK_BUDGET*1000:.1f} ms)"
        )

    def test_advance_throughput(self) -> None:
        """Advancing through every frame should stay within budget."""
        from src.playback.playback_player import PlaybackPlayer

        player = PlaybackPlayer()
        seq = _make_sequence(500)
        player.load(seq)
        player.play()

        start = time.perf_counter()
        for _ in range(len(seq.pose_results)):
            player.advance()
        elapsed = time.perf_counter() - start
        per_frame = elapsed / len(seq.pose_results)
        assert per_frame < _FRAME_PROCESS_BUDGET, (
            f"Advance took {per_frame*1000:.1f} ms per frame "
            f"(budget {_FRAME_PROCESS_BUDGET*1000:.1f} ms)"
        )


class TestSequenceCopy:
    """Measure deep-copy throughput for filter pipelines."""

    def test_deep_copy_throughput(self) -> None:
        """Deep-copying a 1000-frame sequence should be fast."""
        from src.motion.base import deep_copy_sequence

        seq = _make_sequence(1000)
        start = time.perf_counter()
        for _ in range(10):
            deep_copy_sequence(seq)
        elapsed = (time.perf_counter() - start) / 10
        assert elapsed < _SEQUENCE_COPY_BUDGET, (
            f"Deep copy took {elapsed*1000:.1f} ms "
            f"(budget {_SEQUENCE_COPY_BUDGET*1000:.1f} ms)"
        )
