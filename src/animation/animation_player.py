"""Animation player for the VisionMoCap application.

The AnimationPlayer provides playback control (play, pause, resume,
stop, seek) over an :class:`AnimationClip` with configurable speed
and loop mode.  It is driven by an external clock via the
:meth:`update` method.
"""

from __future__ import annotations

import logging
from enum import Enum, auto
from typing import Dict, Optional

from src.animation.animation_clip import AnimationClip
from src.animation.retargeted_motion import BoneTransform


class PlaybackState(Enum):
    """Current state of the animation player."""

    STOPPED = auto()
    PLAYING = auto()
    PAUSED = auto()


class AnimationPlayer:
    """Plays, pauses, and seeks through an :class:`AnimationClip`.

    The player is **not** bound to a real-time loop — it advances
    whenever the host calls :meth:`update` with the elapsed delta time.
    This makes it suitable for integration with game engines, GUI
    timers, or offline rendering loops.

    Usage::

        player = AnimationPlayer(clip)
        player.play()

        # In your update loop:
        player.update(delta_time)
        bones = player.current_frame  # Dict[str, BoneTransform] or None
    """

    def __init__(
        self,
        clip: Optional[AnimationClip] = None,
    ) -> None:
        self._clip = clip
        self._state = PlaybackState.STOPPED
        self._current_time: float = 0.0
        self._speed: float = 1.0
        self._loop: bool = False
        self._logger = logging.getLogger(self.__class__.__name__)

    # ------------------------------------------------------------------
    # Playback control
    # ------------------------------------------------------------------

    def play(self) -> None:
        """Start or restart playback from the current position.

        If the player was stopped, playback resumes from time 0.
        If it was paused, it continues from the paused position.
        """
        if self._state == PlaybackState.STOPPED:
            self._current_time = 0.0
        self._state = PlaybackState.PLAYING
        self._logger.debug("Playback started at t=%.3f.", self._current_time)

    def pause(self) -> None:
        """Pause playback, keeping the current position."""
        if self._state == PlaybackState.PLAYING:
            self._state = PlaybackState.PAUSED
            self._logger.debug("Playback paused at t=%.3f.", self._current_time)

    def resume(self) -> None:
        """Resume playback from the paused position."""
        if self._state == PlaybackState.PAUSED:
            self._state = PlaybackState.PLAYING
            self._logger.debug("Playback resumed at t=%.3f.", self._current_time)

    def stop(self) -> None:
        """Stop playback and reset to time 0."""
        self._state = PlaybackState.STOPPED
        self._current_time = 0.0
        self._logger.debug("Playback stopped.")

    def seek(self, timestamp: float) -> None:
        """Jump to a specific timestamp.

        The timestamp is clamped to the clip's duration.

        Args:
            timestamp: Target time in seconds.
        """
        if self._clip is not None:
            duration = self._clip.duration
            self._current_time = max(0.0, min(timestamp, duration))
        else:
            self._current_time = max(0.0, timestamp)
        self._logger.debug("Seeked to t=%.3f.", self._current_time)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def clip(self) -> Optional[AnimationClip]:
        """The currently assigned animation clip."""
        return self._clip

    @clip.setter
    def clip(self, value: Optional[AnimationClip]) -> None:
        self._clip = value
        self._state = PlaybackState.STOPPED
        self._current_time = 0.0

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
    def current_time(self) -> float:
        return self._current_time

    @property
    def current_frame(self) -> Optional[Dict[str, BoneTransform]]:
        """Evaluate the clip at the current playback position.

        Returns:
            ``{bone_name: BoneTransform}`` for all bones at the current
            time, or ``None`` if no clip is loaded.
        """
        if self._clip is None:
            return None
        return self._clip.interpolate(self._current_time)

    @property
    def speed(self) -> float:
        """Playback speed multiplier (1.0 = normal)."""
        return self._speed

    @speed.setter
    def speed(self, value: float) -> None:
        self._speed = value

    @property
    def loop(self) -> bool:
        """Whether playback wraps around when reaching the end."""
        return self._loop

    @loop.setter
    def loop(self, value: bool) -> None:
        self._loop = value

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self, delta_time: float) -> None:
        """Advance the playback by *delta_time* seconds.

        Call this from your update loop with the time elapsed since
        the last frame.  Has no effect when the player is paused or
        stopped.

        Args:
            delta_time: Elapsed time in seconds (should be positive).
        """
        if self._state != PlaybackState.PLAYING:
            return
        if self._clip is None or self._clip.frame_count == 0:
            return

        self._current_time += delta_time * self._speed

        duration = self._clip.duration
        if duration <= 0.0:
            self._current_time = 0.0
            return

        if self._current_time >= duration:
            if self._loop:
                self._current_time = self._current_time % duration
            else:
                self._current_time = duration
                self._state = PlaybackState.STOPPED
                self._logger.debug("Playback reached end.")
        elif self._current_time < 0.0:
            if self._loop:
                self._current_time = duration - abs(self._current_time) % duration
            else:
                self._current_time = 0.0
                self._state = PlaybackState.STOPPED
