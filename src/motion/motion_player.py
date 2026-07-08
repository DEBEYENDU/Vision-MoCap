"""Motion playback subsystem for the VisionMoCap application.

Replays a previously recorded MotionSequence with controls for frame
stepping, pause / resume, and configurable playback speed.
"""

from __future__ import annotations

import logging
import time
from enum import Enum, auto
from typing import Optional

from src.motion.motion_sequence import MotionSequence
from src.pose.pose_result import PoseResult


class PlaybackState(Enum):
    """Current state of the MotionPlayer state machine."""

    STOPPED = auto()
    PLAYING = auto()
    PAUSED = auto()


class MotionPlayer:
    """Replays a MotionSequence with stepping and speed control.

    Typical usage::

        player = MotionPlayer()
        player.load(sequence)
        player.play()

        while player.is_playing:
            pose = player.advance()
            if pose is None:
                break
            # render / process pose
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

        Resets the player state to STOPPED at frame 0.

        Args:
            sequence: The sequence to replay.
        """
        self._sequence = sequence
        self._current_frame = 0
        self._state = PlaybackState.STOPPED
        self._speed = 1.0
        self._play_start_time = 0.0
        self._accumulated_time = 0.0
        self._logger.info(
            "Loaded sequence: %d frames, %.2f s, %.1f FPS.",
            sequence.total_frames,
            sequence.duration,
            sequence.average_fps,
        )

    def play(self) -> None:
        """Start or restart playback from the current position."""
        if self._sequence is None:
            self._logger.warning("No sequence loaded. Call load() first.")
            return
        if self._state == PlaybackState.PAUSED:
            self.resume()
            return
        self._current_frame = 0
        self._accumulated_time = 0.0
        self._play_start_time = time.perf_counter()
        self._state = PlaybackState.PLAYING
        self._logger.info("Playback started.")

    def pause(self) -> None:
        """Pause playback at the current frame."""
        if self._state != PlaybackState.PLAYING:
            return
        elapsed = time.perf_counter() - self._play_start_time
        self._accumulated_time += elapsed
        self._state = PlaybackState.PAUSED
        self._logger.debug("Playback paused at frame %d.", self._current_frame)

    def resume(self) -> None:
        """Resume playback from the paused position."""
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
    # Frame access
    # ------------------------------------------------------------------

    def advance(self) -> Optional[PoseResult]:
        """Advance to the frame indicated by elapsed playback time.

        Should be called once per render cycle during ``PLAYING`` state.
        Uses the sequence's average FPS together with the playback speed
        multiplier to determine the correct frame.

        Returns:
            The current PoseResult, or None when the sequence ends or
            playback is not active.
        """
        if self._state != PlaybackState.PLAYING or self._sequence is None:
            return None
        elapsed = time.perf_counter() - self._play_start_time
        total_elapsed = elapsed + self._accumulated_time
        adjusted = total_elapsed * self._speed
        target = int(adjusted * self._sequence.average_fps)

        if target >= len(self._sequence.pose_results):
            self.stop()
            return None

        if target < self._current_frame:
            target = self._current_frame

        self._current_frame = target
        return self._sequence.pose_results[self._current_frame]

    def step_forward(self) -> Optional[PoseResult]:
        """Advance one frame forward (frame stepping).

        Returns:
            The PoseResult at the new position, or None if already at
            the end.
        """
        if self._sequence is None:
            return None
        if self._current_frame < len(self._sequence.pose_results) - 1:
            self._current_frame += 1
        return self._sequence.pose_results[self._current_frame]

    def step_backward(self) -> Optional[PoseResult]:
        """Go one frame backward (frame stepping).

        Returns:
            The PoseResult at the new position, or None if already at
            the beginning.
        """
        if self._sequence is None:
            return None
        if self._current_frame > 0:
            self._current_frame -= 1
        return self._sequence.pose_results[self._current_frame]

    def get_current_frame(self) -> Optional[PoseResult]:
        """Return the PoseResult at the current frame index.

        Returns:
            The current pose, or None if nothing is loaded.
        """
        if self._sequence is None:
            return None
        if self._current_frame >= len(self._sequence.pose_results):
            return None
        return self._sequence.pose_results[self._current_frame]

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_speed(self, speed: float) -> None:
        """Set the playback speed multiplier.

        Args:
            speed: Multiplier where 1.0 is real-time, 2.0 is double
                   speed, 0.5 is half speed. Must be positive.
        """
        if speed <= 0.0:
            self._logger.warning("Speed must be positive, ignoring %.2f.", speed)
            return
        self._speed = speed
        self._logger.debug("Playback speed set to %.2fx.", speed)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def state(self) -> PlaybackState:
        """Current playback state."""
        return self._state

    @property
    def is_playing(self) -> bool:
        """Whether the player is currently in PLAYING state."""
        return self._state == PlaybackState.PLAYING

    @property
    def is_paused(self) -> bool:
        """Whether the player is currently in PAUSED state."""
        return self._state == PlaybackState.PAUSED

    @property
    def total_frames(self) -> int:
        """Total frames in the loaded sequence (0 if none loaded)."""
        if self._sequence is None:
            return 0
        return self._sequence.total_frames

    @property
    def current_frame_index(self) -> int:
        """Index of the current frame (0-based)."""
        return self._current_frame

    @property
    def speed(self) -> float:
        """Current playback speed multiplier."""
        return self._speed

    @property
    def sequence(self) -> Optional[MotionSequence]:
        """The loaded MotionSequence, or None."""
        return self._sequence
