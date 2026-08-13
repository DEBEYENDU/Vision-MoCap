"""Unit tests for loop playback in the playback subsystem."""

from __future__ import annotations

import time

from src.motion.motion_sequence import MotionSequence
from src.playback.playback_controller import PlaybackController
from src.playback.playback_player import PlaybackPlayer
from src.playback.playback_state import PlaybackState
from src.pose.pose_result import Landmark, PoseResult


def _make_pose(timestamp: float) -> PoseResult:
    return PoseResult(
        timestamp=timestamp,
        landmarks=[
            Landmark(x=0.1 * i, y=0.2 * i, z=0.3 * i, visibility=0.9)
            for i in range(33)
        ],
        confidence=0.9,
        frame_width=640,
        frame_height=480,
        pose_detected=True,
    )


def make_sequence(n_frames: int = 10, fps: float = 30.0) -> MotionSequence:
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


class TestLoopPlayer:
    """Loop behaviour of PlaybackPlayer."""

    def test_loop_disabled_by_default(self) -> None:
        player = PlaybackPlayer()
        player.load(make_sequence())
        assert player.loop_enabled is False

    def test_set_loop_enables(self) -> None:
        player = PlaybackPlayer()
        player.load(make_sequence())
        player.set_loop(True)
        assert player.loop_enabled is True
        player.set_loop(False)
        assert player.loop_enabled is False

    def test_loop_wraps_at_end(self) -> None:
        player = PlaybackPlayer()
        seq = make_sequence(n_frames=10, fps=10.0)  # 1.0 s duration
        player.load(seq)
        player.set_loop(True)
        player.play()
        # Advance well past the end of the sequence.
        time.sleep(0.02)
        pose = player.advance()
        assert pose is not None
        assert player.state is PlaybackState.PLAYING
        assert 0 <= player.current_frame_index < 10

    def test_no_loop_finishes(self) -> None:
        player = PlaybackPlayer()
        player.load(make_sequence(n_frames=10, fps=10.0))
        player.play()
        player._accumulated_time = 5.0  # past the end
        assert player.advance() is None
        assert player.state is PlaybackState.FINISHED

    def test_loop_never_finishes(self) -> None:
        player = PlaybackPlayer()
        player.load(make_sequence(n_frames=10, fps=10.0))
        player.set_loop(True)
        player.play()
        player._accumulated_time = 50.0  # many loops past the end
        pose = player.advance()
        assert pose is not None
        assert player.state is PlaybackState.PLAYING

    def test_loop_accumulated_time_is_rebased(self) -> None:
        player = PlaybackPlayer()
        seq = make_sequence(n_frames=10, fps=10.0)
        player.load(seq)
        player.set_loop(True)
        player.play()
        player._accumulated_time = 1.35  # 1.35 s → wrapped 0.35 s
        pose = player.advance()
        assert pose is not None
        assert player.current_frame_index == 3  # int(0.35 * 10)

    def test_stop_resets_loop_state(self) -> None:
        player = PlaybackPlayer()
        player.load(make_sequence())
        player.set_loop(True)
        player.stop()
        assert player.loop_enabled is True  # loop flag survives stop
        assert player.state is PlaybackState.STOPPED


class TestLoopController:
    """Loop passthrough on PlaybackController."""

    def test_controller_passthrough(self) -> None:
        ctrl = PlaybackController()
        ctrl._player.load(make_sequence())
        ctrl.set_loop(True)
        assert ctrl.loop_enabled is True
        ctrl.set_loop(False)
        assert ctrl.loop_enabled is False

    def test_controller_loop_plays_past_end(self) -> None:
        ctrl = PlaybackController()
        ctrl._player.load(make_sequence(n_frames=10, fps=10.0))
        ctrl.set_loop(True)
        ctrl.play()
        ctrl._player._accumulated_time = 2.0
        pose = ctrl.advance()
        assert pose is not None
        assert not ctrl.is_finished
