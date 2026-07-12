"""Playback state enumeration for the VisionMoCap playback system."""

from __future__ import annotations

from enum import Enum, auto


class PlaybackState(Enum):
    """Current state of the playback state machine.

    States:
        STOPPED: No sequence loaded or playback stopped/reset.
        PLAYING: Playback is actively advancing frames in real-time.
        PAUSED:  Playback suspended at the current frame.
        FINISHED: The end of the sequence has been reached.
    """

    STOPPED = auto()
    PLAYING = auto()
    PAUSED = auto()
    FINISHED = auto()
