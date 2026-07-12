"""Core playback engine — frame-accurate, timer-based replay."""

from __future__ import annotations

import logging
import time
from typing import Optional

from src.motion.motion_sequence import MotionSequence
from src.playback.playback_state import PlaybackState
from src.pose.pose_result import PoseResult


class PlaybackPlayer:
    """Low-level playback engine with timing and frame management.

    Operates on an already-loaded MotionSequence.  Does NOT handle
    file I/O — the controller or caller provides the sequence.

    Timing model
    ------------
    During PLAYING state the player tracks accumulated wall-clock time
    and multiplies it by the speed factor to obtain the sequence
    position.  Pausing captures the wall time; resuming continues from
    where it left off.  Frame stepping (``step_forward`` / ``step_back``)
    is independent of the timer and works in any state.
    """

    def __init__(self) -> None:
        self._sequence: Optional[MotionSequence] = None
        self._current_frame: int = 0
        self._state: PlaybackState = PlaybackState.STOPPED
        self._speed: float = 1.0
        self._play_start_time: float = 0.0
        self._accumulated_time: float = 0.0
        self._logger = logging.getLogger(self.__class__.__name__)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def load(self, sequence: MotionSequence) -> None:
        """Load a MotionSequence for playback.

        Resets all state: frame index to 0, speed to 1.0, and
        transitions to STOPPED.

        Args:
            sequence: The sequence to replay.
        """
        self._sequence = sequence
        self._current_frame = 0
        self._speed = 1.0
        self._state = PlaybackState.STOPPED
        self._play_start_time = 0.0
        self._accumulated_time = 0.0
        self._logger.info(
            "Loaded sequence: %d frames, %.2f s, %.1f FPS.",
            sequence.total_frames,
            sequence.duration,
            sequence.average_fps,
        )

    def play(self) -> None:
        """Start or restart playback from the current position.

        If the sequence is FINISHED, rewinds to frame 0 first.
        If PAUSED, resumes from the paused position.
        """
        if self._sequence is None:
            self._logger.warning("play() called but no sequence loaded.")
            return

        if self._state == PlaybackState.PAUSED:
            self.resume()
            return

        if self._state == PlaybackState.FINISHED:
            self._current_frame = 0
            self._accumulated_time = 0.0

        self._play_start_time = time.perf_counter()
        self._state = PlaybackState.PLAYING
        self._logger.info("Playback started.")

    def pause(self) -> None:
        """Pause playback at the current frame.

        No-op if not currently PLAYING.
        """
        if self._state != PlaybackState.PLAYING:
            return
        elapsed = time.perf_counter() - self._play_start_time
        self._accumulated_time += elapsed
        self._play_start_time = 0.0
        self._state = PlaybackState.PAUSED
        self._logger.debug("Playback paused at frame %d.", self._current_frame)

    def resume(self) -> None:
        """Resume playback from a paused position.

        No-op if not currently PAUSED.
        """
        if self._state != PlaybackState.PAUSED:
            return
        self._play_start_time = time.perf_counter()
        self._state = PlaybackState.PLAYING
        self._logger.debug("Playback resumed.")

    def stop(self) -> None:
        """Stop playback and reset to frame 0."""
        self._current_frame = 0
        self._state = PlaybackState.STOPPED
        self._play_start_time = 0.0
        self._accumulated_time = 0.0
        self._logger.info("Playback stopped.")

    # ------------------------------------------------------------------
    # Frame advancement
    # ------------------------------------------------------------------

    def advance(self) -> Optional[PoseResult]:
        """Advance to the frame indicated by elapsed playback time.

        Must be called periodically during PLAYING state (e.g. once per
        render cycle).  Uses wall-clock time, accumulated pauses, and
        the speed multiplier to determine the correct frame.

        Returns:
            The PoseResult at the computed frame, or None when the
            sequence ends or playback is not active.
        """
        if self._state != PlaybackState.PLAYING or self._sequence is None:
            return None

        elapsed = time.perf_counter() - self._play_start_time
        total_wall = elapsed + self._accumulated_time
        sequence_time = total_wall * self._speed
        target = int(sequence_time * self._sequence.average_fps)

        if target >= len(self._sequence.pose_results):
            self._current_frame = len(self._sequence.pose_results) - 1
            self._state = PlaybackState.FINISHED
            self._logger.info("Playback finished at end of sequence.")
            return None

        self._current_frame = target
        return self._sequence.pose_results[self._current_frame]

    def seek(self, frame: int) -> bool:
        """Jump to a specific frame index (0-based).

        Timing is rebased so that continuous play (``advance()``)
        continues seamlessly from the new position.

        Args:
            frame: Target frame index (0-based).

        Returns:
            True if the seek was successful, False if the frame is
            out of range or no sequence is loaded.
        """
        if self._sequence is None:
            return False
        if frame < 0 or frame >= len(self._sequence.pose_results):
            return False

        self._current_frame = frame
        frame_time = frame / self._sequence.average_fps
        self._accumulated_time = frame_time / self._speed
        self._play_start_time = time.perf_counter()

        if self._state == PlaybackState.FINISHED:
            self._state = PlaybackState.PAUSED
        return True

    def step_forward(self) -> Optional[PoseResult]:
        """Advance one frame forward.

        Works in any state.  If already at the last frame, returns the
        last frame without advancing.

        Returns:
            The PoseResult at the new position, or None if no sequence
            is loaded.
        """
        if self._sequence is None:
            return None
        if self._current_frame < len(self._sequence.pose_results) - 1:
            self._current_frame += 1
        return self._sequence.pose_results[self._current_frame]

    def step_backward(self) -> Optional[PoseResult]:
        """Go one frame backward.

        Works in any state.  If already at frame 0, returns frame 0
        without moving.

        Returns:
            The PoseResult at the new position, or None if no sequence
            is loaded.
        """
        if self._sequence is None:
            return None
        if self._current_frame > 0:
            self._current_frame -= 1
        return self._sequence.pose_results[self._current_frame]

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_speed(self, speed: float) -> None:
        """Set the playback speed multiplier.

        If currently PLAYING, the accumulated time is rebased to avoid
        a sudden jump in frame position.

        Args:
            speed: Multiplier where 1.0 is real-time, 2.0 is double
                   speed, 0.5 is half speed.  Must be positive.
        """
        if speed <= 0.0:
            self._logger.warning("Speed must be positive, ignoring %.2f.", speed)
            return

        if self._state == PlaybackState.PLAYING:
            elapsed = time.perf_counter() - self._play_start_time
            total_wall = elapsed + self._accumulated_time
            sequence_time = total_wall * self._speed
            self._accumulated_time = sequence_time / speed
            self._play_start_time = time.perf_counter()

        self._speed = speed
        self._logger.debug("Playback speed set to %.2fx.", speed)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def state(self) -> PlaybackState:
        return self._state

    @property
    def is_playing(self) -> bool:
        return self._state == PlaybackState.PLAYING

    @property
    def is_paused(self) -> bool:
        return self._state == PlaybackState.PAUSED

    @property
    def is_stopped(self) -> bool:
        return self._state == PlaybackState.STOPPED

    @property
    def is_finished(self) -> bool:
        return self._state == PlaybackState.FINISHED

    @property
    def current_frame_index(self) -> int:
        return self._current_frame

    @property
    def total_frames(self) -> int:
        if self._sequence is None:
            return 0
        return self._sequence.total_frames

    @property
    def speed(self) -> float:
        return self._speed

    @property
    def sequence(self) -> Optional[MotionSequence]:
        return self._sequence

    @property
    def duration(self) -> float:
        if self._sequence is None:
            return 0.0
        return self._sequence.duration

    @property
    def average_fps(self) -> float:
        if self._sequence is None:
            return 0.0
        return self._sequence.average_fps
