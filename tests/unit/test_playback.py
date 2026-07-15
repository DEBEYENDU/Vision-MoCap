"""Unit tests for the playback subsystem (src/playback/).

Tests cover PlaybackState, PlaybackPlayer, and PlaybackController.
"""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List

from src.motion.motion_sequence import MotionSequence
from src.playback.playback_controller import PlaybackController
from src.playback.playback_player import PlaybackPlayer
from src.playback.playback_state import PlaybackState
from src.pose.pose_result import Landmark, PoseResult

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_landmarks(count: int = 33) -> List[Landmark]:
    return [Landmark(x=0.1 * i, y=0.2 * i, z=0.3 * i, visibility=0.9) for i in range(count)]


def _make_pose(timestamp: float, confidence: float = 0.85) -> PoseResult:
    return PoseResult(
        timestamp=timestamp,
        landmarks=_make_landmarks(),
        world_landmarks=_make_landmarks(),
        confidence=confidence,
        frame_width=640,
        frame_height=480,
        pose_detected=True,
    )


def make_sequence(n_frames: int = 10, fps: float = 30.0) -> MotionSequence:
    """Create a small MotionSequence for testing."""
    start = 1000.0
    interval = 1.0 / fps
    poses = [_make_pose(start + i * interval) for i in range(n_frames)]
    return MotionSequence(
        pose_results=poses,
        start_time=start,
        end_time=start + n_frames * interval,
        total_frames=n_frames,
        average_fps=fps,
        duration=n_frames * interval,
    )


def make_sequence_json(n_frames: int = 10, fps: float = 30.0) -> Dict[str, Any]:
    """Return a dict in the format that MotionSequence.to_dict() produces."""
    seq = make_sequence(n_frames, fps)
    return seq.to_dict()


def make_enhanced_json(n_frames: int = 10, fps: float = 30.0) -> Dict[str, Any]:
    """Return a dict matching the enhanced format from SessionManager."""
    data = make_sequence_json(n_frames, fps)
    data["metadata"] = {
        "date_iso": "2026-07-11T12:00:00",
        "duration_seconds": n_frames / fps,
        "average_fps": fps,
        "average_confidence": 0.85,
        "frame_count": n_frames,
        "camera_index": 0,
    }
    data["frame_numbers"] = list(range(1, n_frames + 1))
    data["fps_values"] = [fps] * n_frames
    return data


# ---------------------------------------------------------------------------
# Test PlaybackState
# ---------------------------------------------------------------------------


class TestPlaybackState:
    def test_enum_values_present(self) -> None:
        assert PlaybackState.STOPPED is not None
        assert PlaybackState.PLAYING is not None
        assert PlaybackState.PAUSED is not None
        assert PlaybackState.FINISHED is not None

    def test_enum_unique(self) -> None:
        values = [s.value for s in PlaybackState]
        assert len(values) == len(set(values)), "Enum values must be unique"

    def test_playback_state_unified(self) -> None:
        """All PlaybackState exports reference the same enum."""
        from src.motion.motion_player import PlaybackState as MotionPBState
        from src.animation.animation_player import PlaybackState as AnimPBState
        assert PlaybackState is MotionPBState
        assert PlaybackState is AnimPBState


# ---------------------------------------------------------------------------
# Test PlaybackPlayer
# ---------------------------------------------------------------------------


class TestPlaybackPlayer:
    def test_initial_state(self) -> None:
        player = PlaybackPlayer()
        assert player.state == PlaybackState.STOPPED
        assert player.current_frame_index == 0
        assert player.total_frames == 0
        assert player.speed == 1.0
        assert not player.is_playing
        assert not player.is_paused
        assert player.is_stopped
        assert not player.is_finished
        assert player.sequence is None
        assert player.duration == 0.0
        assert player.average_fps == 0.0

    def test_load_resets_state(self) -> None:
        player = PlaybackPlayer()
        seq = make_sequence(10, 30.0)
        player.load(seq)
        assert player.state == PlaybackState.STOPPED
        assert player.current_frame_index == 0
        assert player.total_frames == 10
        assert player.speed == 1.0
        assert player.sequence is seq

    def test_play_transition(self) -> None:
        player = PlaybackPlayer()
        player.load(make_sequence(10, 30.0))
        player.play()
        assert player.is_playing
        assert player.state == PlaybackState.PLAYING

    def test_play_without_load_noop(self) -> None:
        player = PlaybackPlayer()
        player.play()  # should warn but not crash
        assert player.is_stopped

    def test_pause_transition(self) -> None:
        player = PlaybackPlayer()
        player.load(make_sequence(10, 30.0))
        player.play()
        time.sleep(0.01)
        player.pause()
        assert player.is_paused
        assert player.state == PlaybackState.PAUSED

    def test_pause_when_not_playing_noop(self) -> None:
        player = PlaybackPlayer()
        player.load(make_sequence(10, 30.0))
        player.pause()  # STOPPED — noop
        assert player.is_stopped
        player.play()
        player.pause()
        assert player.is_paused
        player.pause()  # already PAUSED — noop
        assert player.is_paused

    def test_resume(self) -> None:
        player = PlaybackPlayer()
        player.load(make_sequence(10, 30.0))
        player.play()
        time.sleep(0.01)
        player.pause()
        prev = player.current_frame_index
        player.resume()
        assert player.is_playing
        assert player.current_frame_index == prev

    def test_stop_resets(self) -> None:
        player = PlaybackPlayer()
        player.load(make_sequence(10, 30.0))
        player.play()
        time.sleep(0.01)
        player.stop()
        assert player.is_stopped
        assert player.current_frame_index == 0

    def test_step_forward(self) -> None:
        player = PlaybackPlayer()
        player.load(make_sequence(10, 30.0))
        pose = player.step_forward()
        assert player.current_frame_index == 1
        assert pose is not None

    def test_step_forward_at_end(self) -> None:
        player = PlaybackPlayer()
        player.load(make_sequence(10, 30.0))
        player._current_frame = 9
        pose = player.step_forward()
        assert player.current_frame_index == 9  # no movement
        assert pose is not None

    def test_step_backward(self) -> None:
        player = PlaybackPlayer()
        player.load(make_sequence(10, 30.0))
        player._current_frame = 5
        pose = player.step_backward()
        assert player.current_frame_index == 4
        assert pose is not None

    def test_step_backward_at_start(self) -> None:
        player = PlaybackPlayer()
        player.load(make_sequence(10, 30.0))
        pose = player.step_backward()
        assert player.current_frame_index == 0  # no movement
        assert pose is not None

    def test_step_forward_without_load(self) -> None:
        player = PlaybackPlayer()
        assert player.step_forward() is None

    def test_step_backward_without_load(self) -> None:
        player = PlaybackPlayer()
        assert player.step_backward() is None

    def test_seek_valid(self) -> None:
        player = PlaybackPlayer()
        player.load(make_sequence(10, 30.0))
        assert player.seek(5)
        assert player.current_frame_index == 5

    def test_seek_invalid_negative(self) -> None:
        player = PlaybackPlayer()
        player.load(make_sequence(10, 30.0))
        assert not player.seek(-1)

    def test_seek_invalid_beyond_end(self) -> None:
        player = PlaybackPlayer()
        player.load(make_sequence(10, 30.0))
        assert not player.seek(100)

    def test_seek_without_load(self) -> None:
        player = PlaybackPlayer()
        assert not player.seek(0)

    def test_set_speed_valid(self) -> None:
        player = PlaybackPlayer()
        player.load(make_sequence(10, 30.0))
        player.set_speed(2.0)
        assert player.speed == 2.0

    def test_set_speed_invalid(self) -> None:
        player = PlaybackPlayer()
        player.load(make_sequence(10, 30.0))
        player.set_speed(-1.0)
        assert player.speed == 1.0  # unchanged
        player.set_speed(0.0)
        assert player.speed == 1.0  # unchanged

    def test_advance_while_paused(self) -> None:
        player = PlaybackPlayer()
        player.load(make_sequence(10, 30.0))
        assert player.advance() is None  # not playing

    def test_advance_while_playing(self) -> None:
        player = PlaybackPlayer()
        player.load(make_sequence(10, 30.0))
        player.play()
        time.sleep(0.05)
        pose = player.advance()
        assert pose is not None
        assert player.current_frame_index >= 1

    def test_advance_past_end(self) -> None:
        player = PlaybackPlayer()
        player.load(make_sequence(10, 1.0))  # 1 fps, 10 frames = 10s duration
        player.play()
        time.sleep(0.5)
        # Should report as finished or still playing depending on time
        result = player.advance()
        # If playback hasn't ended yet due to timing, seek to end and verify
        if result is not None:
            player._current_frame = 9
            player._accumulated_time = 100.0  # force past end
            player._play_start_time = time.perf_counter()
            result = player.advance()
        assert result is None
        assert player.is_finished

    def test_finished_to_play_rewinds(self) -> None:
        player = PlaybackPlayer()
        player.load(make_sequence(10, 30.0))
        player._current_frame = 9
        player._state = PlaybackState.FINISHED
        player.play()
        assert player.current_frame_index == 0
        assert player.is_playing

    def test_speed_change_during_play_preserves_position(self) -> None:
        player = PlaybackPlayer()
        player.load(make_sequence(10, 30.0))
        player.play()
        time.sleep(0.02)
        frame_before = player.current_frame_index
        player.set_speed(2.0)
        frame_after = player.current_frame_index
        assert frame_after == frame_before, "Speed change should not jump frames"


# ---------------------------------------------------------------------------
# Test PlaybackController
# ---------------------------------------------------------------------------


class TestPlaybackController:
    def test_initial_state(self) -> None:
        ctrl = PlaybackController()
        assert ctrl.state == PlaybackState.STOPPED
        assert ctrl.current_frame_index == 0
        assert ctrl.total_frames == 0
        assert ctrl.source_path is None
        assert not ctrl.is_playing
        assert not ctrl.is_paused
        assert ctrl.is_stopped
        assert not ctrl.is_finished

    def test_load_plain_json(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(make_sequence_json(15, 30.0), f)
            p = Path(f.name)
        try:
            ctrl = PlaybackController()
            assert ctrl.load(p)
            assert ctrl.total_frames == 15
            assert ctrl.is_stopped
        finally:
            p.unlink()

    def test_load_enhanced_json(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(make_enhanced_json(20, 60.0), f)
            p = Path(f.name)
        try:
            ctrl = PlaybackController()
            assert ctrl.load(p)
            assert ctrl.total_frames == 20
            assert ctrl.average_fps == 60.0
        finally:
            p.unlink()

    def test_load_file_not_found(self) -> None:
        ctrl = PlaybackController()
        assert not ctrl.load(Path("/nonexistent/test.json"))

    def test_load_invalid_json(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not json at all")
            p = Path(f.name)
        try:
            ctrl = PlaybackController()
            assert not ctrl.load(p)
        finally:
            p.unlink()

    def test_load_wrong_format(self) -> None:
        """A valid JSON that lacks pose_results should fail."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"hello": "world"}, f)
            p = Path(f.name)
        try:
            ctrl = PlaybackController()
            assert not ctrl.load(p)
        finally:
            p.unlink()

    def test_get_current_pose(self) -> None:
        ctrl = PlaybackController()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(make_sequence_json(5, 30.0), f)
            p = Path(f.name)
        try:
            ctrl.load(p)
            pose = ctrl.get_current_pose()
            assert pose is not None
            assert len(pose.landmarks) == 33
            assert pose.frame_width == 640
            assert pose.frame_height == 480
        finally:
            p.unlink()

    def test_next_frame_pauses(self) -> None:
        ctrl = PlaybackController()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(make_sequence_json(10, 30.0), f)
            p = Path(f.name)
        try:
            ctrl.load(p)
            ctrl.play()
            assert ctrl.is_playing
            ctrl.next_frame()
            assert ctrl.is_paused, "next_frame should pause playback"
            assert ctrl.current_frame_index == 1
        finally:
            p.unlink()

    def test_previous_frame_pauses(self) -> None:
        ctrl = PlaybackController()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(make_sequence_json(10, 30.0), f)
            p = Path(f.name)
        try:
            ctrl.load(p)
            ctrl.seek(5)
            ctrl.play()
            ctrl.previous_frame()
            assert ctrl.is_paused
            assert ctrl.current_frame_index == 4
        finally:
            p.unlink()

    def test_seek_via_controller(self) -> None:
        ctrl = PlaybackController()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(make_sequence_json(10, 30.0), f)
            p = Path(f.name)
        try:
            ctrl.load(p)
            assert ctrl.seek(7)
            assert ctrl.current_frame_index == 7
            assert not ctrl.seek(100)
            assert ctrl.current_frame_index == 7  # unchanged
        finally:
            p.unlink()

    def test_unload(self) -> None:
        ctrl = PlaybackController()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(make_sequence_json(10, 30.0), f)
            p = Path(f.name)
        try:
            ctrl.load(p)
            ctrl.unload()
            assert ctrl.total_frames == 0
            assert ctrl.state == PlaybackState.STOPPED
            assert ctrl.source_path is None
        finally:
            p.unlink()

    def test_advance_via_controller(self) -> None:
        ctrl = PlaybackController()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(make_sequence_json(10, 30.0), f)
            p = Path(f.name)
        try:
            ctrl.load(p)
            result = ctrl.advance()
            assert result is None  # not playing
            ctrl.play()
            time.sleep(0.05)
            result = ctrl.advance()
            assert result is not None
        finally:
            p.unlink()

    def test_speed_control(self) -> None:
        ctrl = PlaybackController()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(make_sequence_json(10, 30.0), f)
            p = Path(f.name)
        try:
            ctrl.load(p)
            ctrl.set_speed(0.5)
            assert ctrl.speed == 0.5
            ctrl.set_speed(3.0)
            assert ctrl.speed == 3.0
        finally:
            p.unlink()

    def test_pause_returns_bool(self) -> None:
        ctrl = PlaybackController()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(make_sequence_json(10, 30.0), f)
            p = Path(f.name)
        try:
            ctrl.load(p)
            assert not ctrl.pause()  # not playing
            ctrl.play()
            assert ctrl.pause()  # was playing
        finally:
            p.unlink()

    def test_properties_available(self) -> None:
        ctrl = PlaybackController()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(make_sequence_json(10, 30.0), f)
            p = Path(f.name)
        try:
            ctrl.load(p)
            assert ctrl.source_path is not None
            assert ctrl.sequence is not None
            assert ctrl.player is not None
            assert ctrl.duration > 0
            assert ctrl.average_fps == 30.0
            assert ctrl.current_frame == ctrl.current_frame_index
        finally:
            p.unlink()

    def test_load_empty_sequence_rejected(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            seq = make_sequence_json(0, 30.0)
            json.dump(seq, f)
            p = Path(f.name)
        try:
            ctrl = PlaybackController()
            assert not ctrl.load(p), "Should reject empty sequence"
        finally:
            p.unlink()


# ---------------------------------------------------------------------------
# Integration: load real recording files
# ---------------------------------------------------------------------------


class TestRealRecordings:
    """Load actual recording JSON files to verify real-world compatibility."""

    def _find_recordings(self) -> List[Path]:
        exports = Path("exports")
        files: List[Path] = []
        files.extend(exports.glob("*.json"))
        recordings_dir = exports / "recordings"
        if recordings_dir.is_dir():
            files.extend(recordings_dir.glob("*.json"))
        return files

    def _load_best(self, files: List[Path]) -> Path:
        ctrl = PlaybackController()
        best = max(files, key=lambda f: f.stat().st_size)
        ctrl.load(best)
        return best

    def test_load_all_recordings(self) -> None:
        files = self._find_recordings()
        assert len(files) > 0, "No recording files found"
        for f in files:
            ctrl = PlaybackController()
            ok = ctrl.load(f)
            assert ok, f"Failed to load {f.name}"
            assert ctrl.total_frames > 0, f"Zero frames in {f.name}"
            assert ctrl.duration > 0, f"Zero duration in {f.name}"
            assert ctrl.average_fps > 0, f"Zero FPS in {f.name}"
            pose = ctrl.get_current_pose()
            assert pose is not None, f"pose_results parsing failed in {f.name}"
            # Some recordings may have frames where pose was not detected
            # (empty landmarks, pose_detected=False) — that is expected data
            if pose.pose_detected:
                assert len(pose.landmarks) > 0, f"pose_detected but no landmarks in {f.name}"

    def test_step_through_all_frames(self) -> None:
        """Advance frame-by-frame through the longest recording."""
        files = self._find_recordings()
        ctrl = PlaybackController()
        best = max(files, key=lambda f: f.stat().st_size)
        ctrl.load(best)
        assert ctrl.total_frames > 0
        for i in range(ctrl.total_frames):
            pose = ctrl.get_current_pose()
            assert pose is not None, f"Pose is None at frame {i}"
            if pose.pose_detected:
                assert len(pose.landmarks) > 0, f"pose_detected but no landmarks at frame {i}"
            if i < ctrl.total_frames - 1:
                ctrl.next_frame()
        assert ctrl.current_frame_index == ctrl.total_frames - 1
        ctrl.next_frame()
        assert ctrl.current_frame_index == ctrl.total_frames - 1
