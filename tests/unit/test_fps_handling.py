"""Tests for FPS integrity across the motion → playback → animation
pipeline (Group A fix).

No test in this module may raise ``ZeroDivisionError``.  Coverage:

1. Valid FPS recording (preserved, never overwritten)
2. Timestamp-derived FPS
3. FPS = 0
4. Missing FPS
5. One-frame recording
6. Empty recording
7. Duplicate timestamps
8. Invalid timestamps (NaN / infinity)
9. Playback seek
10. Playback step forward
11. Playback step backward
12. Animation creation
13. Invalid FPS raises a clear VisionMoCap exception
14. Existing old JSON recordings keep loading
"""

from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import pytest

from src.animation.motion_to_animation import MotionToAnimationConverter
from src.core.exceptions import RetargetingError
from src.motion.motion_sequence import (
    DEFAULT_FPS,
    MotionSequence,
    fps_from_timestamps,
    is_valid_fps,
)
from src.playback.playback_controller import PlaybackController
from src.playback.playback_player import PlaybackPlayer
from src.pose.pose_result import Landmark, PoseResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _lm(x: float = 0.5) -> Landmark:
    return Landmark(x=x, y=0.5, z=0.0, visibility=0.9)


def _pose(timestamp: float) -> PoseResult:
    return PoseResult(
        timestamp=timestamp,
        landmarks=[_lm() for _ in range(33)],
        world_landmarks=[_lm() for _ in range(33)],
        confidence=0.9,
        frame_width=640,
        frame_height=480,
        pose_detected=True,
    )


def _timed_sequence(n: int = 10, fps: float = 30.0) -> MotionSequence:
    """Sequence whose timestamps match *fps* exactly."""
    start = 1000.0
    interval = 1.0 / fps
    poses = [_pose(start + i * interval) for i in range(n)]
    return MotionSequence(
        pose_results=poses,
        start_time=start,
        end_time=start + (n - 1) * interval,
        total_frames=n,
        average_fps=fps,
        duration=(n - 1) * interval,
    )


def _json_with(out: Dict[str, Any]) -> Path:
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump(out, f)
        path = Path(f.name)
    return path


# ---------------------------------------------------------------------------
# is_valid_fps / fps_from_timestamps
# ---------------------------------------------------------------------------


class TestFpsHelpers:
    def test_valid_fps_accepts_positive_finite(self) -> None:
        for value in (1.0, 0.1, 30.0, 300.0, 1e6):
            assert is_valid_fps(value), value

    def test_invalid_fps_rejected(self) -> None:
        for value in (0.0, -1.0, -0.0, float("nan"), float("inf"),
                      float("-inf"), "30", None, True):
            assert not is_valid_fps(value), value

    def test_from_timestamps_basic(self) -> None:
        assert fps_from_timestamps([0.0, 0.1, 0.2]) == pytest.approx(10.0)

    def test_from_timestamps_one_frame(self) -> None:
        assert fps_from_timestamps([5.0]) is None

    def test_from_timestamps_empty(self) -> None:
        assert fps_from_timestamps([]) is None

    def test_from_timestamps_duplicate(self) -> None:
        assert fps_from_timestamps([1.0, 1.0, 1.0]) is None

    def test_from_timestamps_descending(self) -> None:
        assert fps_from_timestamps([0.2, 0.1, 0.0]) is None

    def test_from_timestamps_nonfinite(self) -> None:
        # Non-finite timestamps are ignored; the valid subset still
        # yields real timing information when a span exists.
        assert fps_from_timestamps([float("nan"), 1.0, 2.0]) == pytest.approx(1.0)
        assert fps_from_timestamps([float("inf"), 1.0, 2.0]) == pytest.approx(1.0)
        # All timestamps invalid → no timing information at all.
        assert fps_from_timestamps([float("nan"), float("inf")]) is None


# ---------------------------------------------------------------------------
# MotionSequence FPS resolution
# ---------------------------------------------------------------------------


class TestMotionSequenceFps:
    def test_valid_fps_preserved(self) -> None:
        seq = _timed_sequence(10, 30.0)
        assert seq.average_fps == 30.0

    def test_timestamp_derived_fps(self) -> None:
        seq = MotionSequence(
            pose_results=[_pose(1000.0 + i * 0.1) for i in range(11)],
            average_fps=0.0,  # invalid — must be derived from timestamps
        )
        assert seq.average_fps == pytest.approx(10.0)
        assert seq.duration > 0.0

    def test_fps_zero_repaired(self) -> None:
        seq = _timed_sequence(10, 30.0)
        seq.average_fps = 0.0
        assert seq.resolve_average_fps() == pytest.approx(30.0)

    def test_missing_fps_defaults(self) -> None:
        seq = MotionSequence(
            pose_results=[_pose(0.0) for _ in range(3)],
        )
        assert seq.average_fps == DEFAULT_FPS

    def test_one_frame_recording_uses_fallback(self) -> None:
        seq = MotionSequence(pose_results=[_pose(42.0)])
        assert seq.average_fps == DEFAULT_FPS

    def test_empty_recording_uses_fallback(self) -> None:
        seq = MotionSequence()
        assert seq.average_fps == DEFAULT_FPS

    def test_duplicate_timestamps_use_fallback(self) -> None:
        seq = MotionSequence(
            pose_results=[_pose(5.0) for _ in range(5)],
        )
        assert seq.average_fps == DEFAULT_FPS

    def test_nan_fps_repaired(self) -> None:
        seq = _timed_sequence(10, 30.0)
        seq.average_fps = float("nan")
        assert is_valid_fps(seq.resolve_average_fps())

    def test_inf_fps_repaired(self) -> None:
        seq = _timed_sequence(10, 30.0)
        seq.average_fps = float("inf")
        assert is_valid_fps(seq.resolve_average_fps())

    def test_negative_fps_repaired(self) -> None:
        seq = _timed_sequence(10, 30.0)
        seq.average_fps = -5.0
        assert is_valid_fps(seq.resolve_average_fps())

    def test_total_frames_reconciled(self) -> None:
        seq = MotionSequence(
            pose_results=[_pose(float(i)) for i in range(4)],
            total_frames=0,
        )
        assert seq.total_frames == 4

    def test_missing_fps_from_dict(self) -> None:
        data = _timed_sequence(10, 30.0).to_dict()
        del data["average_fps"]
        seq = MotionSequence.from_dict(data)
        assert is_valid_fps(seq.average_fps)

    def test_fps_zero_from_dict(self) -> None:
        data = _timed_sequence(10, 30.0).to_dict()
        data["average_fps"] = 0
        seq = MotionSequence.from_dict(data)
        assert seq.average_fps == pytest.approx(30.0)


# ---------------------------------------------------------------------------
# Playback must never divide by zero
# ---------------------------------------------------------------------------


class TestPlaybackFpsSafety:
    def _load_controller(self, seq: MotionSequence) -> PlaybackController:
        path = _json_with(seq.to_dict())
        ctrl = PlaybackController()
        assert ctrl.load(path)
        path.unlink()
        return ctrl

    def test_seek_zero_fps_recording(self) -> None:
        data = _timed_sequence(10, 30.0).to_dict()
        data["average_fps"] = 0.0  # old/broken recording
        ctrl = PlaybackController()
        path = _json_with(data)
        assert ctrl.load(path)
        assert ctrl.seek(5)
        assert ctrl.current_frame_index == 5
        path.unlink()

    def test_seek_single_frame(self) -> None:
        ctrl = self._load_controller(MotionSequence(pose_results=[_pose(1.0)]))
        assert ctrl.seek(0)
        assert not ctrl.seek(1)
        assert ctrl.current_frame_index == 0

    def test_seek_to_progress_single_frame(self) -> None:
        ctrl = self._load_controller(MotionSequence(pose_results=[_pose(1.0)]))
        assert ctrl.seek_to_progress(0.5)
        assert ctrl.current_frame_index == 0

    def test_seek_to_progress_empty(self) -> None:
        ctrl = PlaybackController()
        assert not ctrl.seek_to_progress(0.5)  # no sequence — no crash

    def test_step_forward_one_frame(self) -> None:
        ctrl = self._load_controller(MotionSequence(pose_results=[_pose(1.0)]))
        ctrl.next_frame()
        assert ctrl.current_frame_index == 0  # no movement past the end

    def test_step_backward_one_frame(self) -> None:
        ctrl = self._load_controller(MotionSequence(pose_results=[_pose(1.0)]))
        ctrl.previous_frame()
        assert ctrl.current_frame_index == 0

    def test_play_single_frame_finishes_cleanly(self) -> None:
        player = PlaybackPlayer()
        player.load(MotionSequence(pose_results=[_pose(1.0)]))
        player.play()
        player._accumulated_time = 100.0  # force past the end
        assert player.advance() is None
        assert player.is_finished

    def test_play_empty_sequence_does_not_crash(self) -> None:
        player = PlaybackPlayer()
        player.load(MotionSequence())
        player.play()
        assert player.advance() is None  # empty — no ZeroDivisionError

    def test_playback_zero_fps_no_division_error(self) -> None:
        """End-to-end: loading an old zero-FPS file and scrubbing it."""
        data = _timed_sequence(10, 30.0).to_dict()
        data["average_fps"] = 0.0
        path = _json_with(data)
        ctrl = PlaybackController()
        assert ctrl.load(path)
        ctrl.play()
        for progress in (0.0, 0.25, 0.5, 1.0):
            ctrl.seek_to_progress(progress)
        ctrl.stop()
        assert ctrl.current_frame_index == 0
        path.unlink()


# ---------------------------------------------------------------------------
# Animation creation must never divide by zero
# ---------------------------------------------------------------------------


class TestAnimationFpsSafety:
    def test_animation_zero_fps_sequence(self) -> None:
        """Old zero-FPS recording → converter derives FPS from timestamps."""
        seq = _timed_sequence(6, 30.0)
        seq.average_fps = 0.0
        converter = MotionToAnimationConverter()
        clip = converter.convert(seq)
        assert clip.frame_count == 6
        assert clip.fps > 0.0

    def test_animation_one_frame(self) -> None:
        seq = MotionSequence(pose_results=[_pose(1.0)])
        converter = MotionToAnimationConverter()
        clip = converter.convert(seq)
        assert clip.frame_count == 1
        assert clip.fps == DEFAULT_FPS

    def test_animation_no_timestamps(self) -> None:
        seq = MotionSequence(
            pose_results=[
                PoseResult(
                    timestamp=0.0,  # all identical — no span
                    landmarks=[_lm() for _ in range(33)],
                    world_landmarks=[_lm() for _ in range(33)],
                    confidence=0.9, pose_detected=True,
                )
                for _ in range(5)
            ],
        )
        converter = MotionToAnimationConverter()
        clip = converter.convert(seq)
        assert clip.frame_count == 5
        assert clip.fps == DEFAULT_FPS

    def test_animation_invalid_target_fps_raises(self) -> None:
        seq = _timed_sequence(5, 30.0)
        converter = MotionToAnimationConverter()
        with pytest.raises(RetargetingError) as exc_info:
            converter.convert(seq, fps=0.0)
        assert "invalid frame rate" in str(exc_info.value).lower()

    def test_animation_nan_target_fps_raises(self) -> None:
        seq = _timed_sequence(5, 30.0)
        converter = MotionToAnimationConverter()
        with pytest.raises(RetargetingError):
            converter.convert(seq, fps=float("nan"))

    def test_animation_custom_fps_valid(self) -> None:
        seq = _timed_sequence(61, 30.0)
        seq.duration = 2.0
        converter = MotionToAnimationConverter()
        clip = converter.convert(seq, fps=10.0)
        assert clip.fps == 10.0

    def test_animation_engine_invalid_fps_raises_value_error(self) -> None:
        from src.animation.animation_engine import AnimationEngine
        from src.animation.retargeted_motion import (
            BoneTransform,
            RetargetedFrame,
            RetargetedMotion,
        )
        from src.core.models import Vector3D

        motion = RetargetedMotion(
            frames=[
                RetargetedFrame(
                    timestamp=0.0,
                    bones={"Hips": BoneTransform(
                        position=Vector3D(0, 0, 0), rotation=(1, 0, 0, 0),
                    )},
                )
            ],
            fps=30.0,
            duration=0.0,
        )
        with pytest.raises(ValueError) as exc_info:
            AnimationEngine().convert(motion, fps=0.0)
        assert "invalid frame rate" in str(exc_info.value).lower()

    def test_animation_engine_zero_motion_fps_falls_back(self) -> None:
        """A RetargetedMotion with fps=0 must still convert (documented
        fallback), never divide by zero."""
        from src.animation.animation_engine import AnimationEngine
        from src.animation.retargeted_motion import (
            BoneTransform,
            RetargetedFrame,
            RetargetedMotion,
        )
        from src.core.models import Vector3D

        motion = RetargetedMotion(
            frames=[
                RetargetedFrame(
                    timestamp=float(i),
                    bones={"Hips": BoneTransform(
                        position=Vector3D(float(i), 0, 0),
                        rotation=(1, 0, 0, 0),
                    )},
                )
                for i in range(4)
            ],
            fps=0.0,
            duration=3.0,
        )
        clip = AnimationEngine().convert(motion)
        assert clip.frame_count == 4
        assert clip.fps == DEFAULT_FPS


# ---------------------------------------------------------------------------
# Old recording compatibility
# ---------------------------------------------------------------------------


class TestOldRecordingCompatibility:
    def _minimal_old_json(self) -> Dict[str, Any]:
        """A recording shape that predates the FPS/metadata fields."""
        return {
            "start_time": 0.0,
            "end_time": 0.0,
            "total_frames": 0,  # missing/zero — must be repaired
            "average_fps": 0.0,
            "duration": 0.0,
            "pose_results": [
                {
                    "timestamp": 100.0 + i,
                    "landmarks": [
                        {"x": 0.5, "y": 0.5, "z": 0.0, "visibility": 0.9}
                        for _ in range(33)
                    ],
                    "world_landmarks": [],
                    "confidence": 0.8,
                    "frame_width": 640,
                    "frame_height": 480,
                    "pose_detected": True,
                }
                for i in range(3)
            ],
        }

    def test_old_recording_without_fps_loads(self) -> None:
        path = _json_with(self._minimal_old_json())
        try:
            ctrl = PlaybackController()
            assert ctrl.load(path)
            assert is_valid_fps(ctrl.average_fps)
            assert ctrl.total_frames == 3
            ctrl.play()
            ctrl.seek(2)
            assert ctrl.current_frame_index == 2
        finally:
            path.unlink()

    def test_old_recording_without_timestamps_loads(self) -> None:
        data = self._minimal_old_json()
        for pr in data["pose_results"]:
            del pr["timestamp"]
        path = _json_with(data)
        try:
            ctrl = PlaybackController()
            assert ctrl.load(path)
            assert ctrl.average_fps == DEFAULT_FPS  # fallback, not a crash
            assert ctrl.seek(1)
        finally:
            path.unlink()

    def test_old_recording_single_frame_loads(self) -> None:
        data = self._minimal_old_json()
        data["pose_results"] = [data["pose_results"][0]]
        data["total_frames"] = 1
        path = _json_with(data)
        try:
            ctrl = PlaybackController()
            assert ctrl.load(path)
            assert is_valid_fps(ctrl.average_fps)
            ctrl.play()
            ctrl.next_frame()
            ctrl.previous_frame()
        finally:
            path.unlink()

    def test_modern_recording_fps_preserved(self) -> None:
        """The shipped demo recording must keep its stored FPS."""
        path = Path("demo/sample_recordings/recording_1783577177.json")
        if not path.exists():
            pytest.skip("demo recording not present")
        seq = MotionSequence.load_json(path)
        assert seq.average_fps == pytest.approx(12.2424, abs=0.01)
