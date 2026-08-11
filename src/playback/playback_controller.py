"""Playback controller — user-facing API for loading and replaying
recorded MotionSequence JSON files.

The controller owns a :class:`PlaybackPlayer` and adds file I/O,
error handling, and convenience methods on top of the raw engine.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional, Union

from src.motion.motion_sequence import MotionSequence
from src.playback.playback_player import PlaybackPlayer
from src.playback.playback_state import PlaybackState
from src.pose.pose_result import PoseResult


class PlaybackController:
    """Playback controller — user-facing API.

    Typical usage::

        ctrl = PlaybackController()
        if ctrl.load("exports/recording_12345.json"):
            ctrl.play()

        # In render loop:
        pose = ctrl.advance()
        if pose is not None:
            render(pose)
    """

    def __init__(self) -> None:
        self._player = PlaybackPlayer()
        self._source_path: Optional[Path] = None
        self._logger = logging.getLogger(self.__class__.__name__)

    # ------------------------------------------------------------------
    # Load / unload
    # ------------------------------------------------------------------

    def load(self, path: Union[str, Path]) -> bool:
        """Load a recorded MotionSequence from a JSON file.

        The file may be in either the plain ``MotionSequence`` format
        or the enhanced recording format (with ``metadata``,
        ``frame_numbers``, etc.).  Both are handled transparently.

        On success the player is reset to STOPPED at frame 0.

        Args:
            path: Path to a ``.json`` recording file.

        Returns:
            True if the file was loaded successfully, False otherwise.
        """
        path = Path(path)
        if not path.exists():
            self._logger.error("File not found: %s", path)
            return False
        if path.suffix.lower() != ".json":
            self._logger.error("Not a JSON file: %s", path)
            return False

        try:
            sequence = MotionSequence.load_json(path)
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            self._logger.error(
                "Failed to parse %s: %s", path.name, exc,
            )
            return False

        if not sequence.pose_results:
            self._logger.warning("Sequence loaded from %s has no pose data.", path.name)
            return False

        self._player.load(sequence)
        self._source_path = path
        self._logger.info("Loaded %d frames from %s.", sequence.total_frames, path.name)
        return True

    def unload(self) -> None:
        """Unload the current sequence and reset the player."""
        self._player = PlaybackPlayer()
        self._source_path = None
        self._logger.info("Playback unloaded.")

    def replace_sequence(self, sequence: MotionSequence) -> None:
        """Replace the loaded sequence in-place (for filtered processing).

        The source path and playback position are preserved so the user
        can continue working with the filtered data.

        Args:
            sequence: The new MotionSequence to use.
        """
        pos = self._player.current_frame_index
        self._player.load(sequence)
        self._player._current_frame = min(pos, self.total_frames - 1)
        self._logger.info(
            "Sequence replaced: %d frames, %.2f s, %.1f FPS.",
            sequence.total_frames,
            sequence.duration,
            sequence.average_fps,
        )

    # ------------------------------------------------------------------
    # Transport controls
    # ------------------------------------------------------------------

    def play(self) -> None:
        """Start or restart playback."""
        self._player.play()

    def pause(self) -> bool:
        """Pause playback at the current frame.

        Returns:
            True if playback was paused, False if it was not PLAYING.
        """
        if not self._player.is_playing:
            return False
        self._player.pause()
        return True

    def stop(self) -> None:
        """Stop playback and reset to frame 0."""
        self._player.stop()

    def set_paused(self) -> None:
        """Transition the player to PAUSED state from any non-playing state.

        If the player is already PAUSED this is a no-op.  If the player
        is PLAYING it is paused first.  The current frame index is
        preserved.
        """
        if self._player.is_playing:
            self._player.pause()
        elif self._player.is_stopped and self._player.sequence is not None:
            self._player.play()
            self._player.pause()

    def seek(self, frame: int) -> bool:
        """Jump to the specified frame index (0-based).

        If the sequence is FINISHED, seeking to a valid frame sets the
        state to PAUSED.

        Args:
            frame: Target frame index.

        Returns:
            True if the seek succeeded, False if the frame is out of
            range or no sequence is loaded.
        """
        return self._player.seek(frame)

    def seek_to_progress(self, progress: float) -> bool:
        """Seek to a position specified as a progress fraction.

        This is a convenience method for timeline scrubbing.  The
        playback state (PLAYING/PAUSED/STOPPED) is preserved; only
        the frame position changes.

        Args:
            progress: Fraction from 0.0 (start) to 1.0 (end).

        Returns:
            True if the seek succeeded, False on error.
        """
        if self._player.sequence is None:
            return False
        total = self._player.total_frames
        if total <= 0:
            return False
        # Clamp progress to valid range
        progress = max(0.0, min(1.0, progress))
        if total == 1:
            return self.seek(0)
        target_frame = int(progress * (total - 1))
        return self.seek(target_frame)

    def next_frame(self) -> Optional[PoseResult]:
        """Step forward one frame.

        If currently PLAYING, playback is paused so the user can
        examine the frame.

        Returns:
            The PoseResult at the new frame, or None if no sequence
            is loaded.
        """
        if self._player.is_playing:
            self._player.pause()
        return self._player.step_forward()

    def previous_frame(self) -> Optional[PoseResult]:
        """Step backward one frame.

        If currently PLAYING, playback is paused so the user can
        examine the frame.

        Returns:
            The PoseResult at the new frame, or None if no sequence
            is loaded or already at frame 0.
        """
        if self._player.is_playing:
            self._player.pause()
        return self._player.step_backward()

    def set_speed(self, speed: float) -> None:
        """Set the playback speed multiplier.

        Args:
            speed: Positive float.  1.0 = real-time.
        """
        self._player.set_speed(speed)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_current_pose(self) -> Optional[PoseResult]:
        """Return the PoseResult at the current frame, or None."""
        if self._player.sequence is None:
            return None
        idx = self._player.current_frame_index
        if idx >= len(self._player.sequence.pose_results):
            return None
        return self._player.sequence.pose_results[idx]

    def advance(self) -> Optional[PoseResult]:
        """Advance playback by elapsed time (for use in a render loop).

        Equivalent to calling ``advance()`` on the underlying player.
        Only meaningful during PLAYING state.

        Returns:
            The current PoseResult, or None if playback has finished
            or is not active.
        """
        return self._player.advance()

    @property
    def state(self) -> PlaybackState:
        return self._player.state

    @property
    def is_playing(self) -> bool:
        return self._player.is_playing

    @property
    def is_paused(self) -> bool:
        return self._player.is_paused

    @property
    def is_stopped(self) -> bool:
        return self._player.is_stopped

    @property
    def is_finished(self) -> bool:
        return self._player.is_finished

    @property
    def current_frame_index(self) -> int:
        return self._player.current_frame_index

    @property
    def total_frames(self) -> int:
        return self._player.total_frames

    @property
    def current_frame(self) -> int:
        return self._player.current_frame_index

    @property
    def speed(self) -> float:
        return self._player.speed

    @property
    def duration(self) -> float:
        return self._player.duration

    @property
    def average_fps(self) -> float:
        return self._player.average_fps

    @property
    def source_path(self) -> Optional[Path]:
        return self._source_path

    @property
    def sequence(self) -> Optional[MotionSequence]:
        return self._player.sequence

    @property
    def player(self) -> PlaybackPlayer:
        return self._player

    # ------------------------------------------------------------------
    # Timeline properties
    # ------------------------------------------------------------------

    @property
    def playback_progress(self) -> float:
        """Return playback progress as a fraction (0.0 to 1.0).

        Returns:
            Progress ratio, or 0.0 if no sequence is loaded.
        """
        if self._player.sequence is None or self._player.total_frames <= 1:
            return 0.0
        return self._player.current_frame_index / (self._player.total_frames - 1)

    @property
    def current_time_seconds(self) -> float:
        """Return the current playback time based on frame position.

        Computed as ``current_frame_index / average_fps`` regardless
        of playback state.  This is deterministic and always matches
        the displayed frame.

        Returns:
            Current time in seconds, or 0.0 if no sequence is loaded.
        """
        if self._player.sequence is None or self._player.average_fps <= 0:
            return 0.0
        return self._player.current_frame_index / self._player.average_fps

    @property
    def duration_seconds(self) -> float:
        """Return the total duration of the loaded sequence in seconds.

        Returns:
            Duration in seconds, or 0.0 if no sequence is loaded.
        """
        return self._player.duration
