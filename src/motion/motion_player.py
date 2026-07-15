"""Motion player — deprecated, use :mod:`src.playback` instead.

This module is retained only to re-export ``PlaybackState`` from the
canonical location for backwards compatibility.
"""

from src.playback.playback_state import PlaybackState

__all__ = ["PlaybackState"]
