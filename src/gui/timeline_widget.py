"""Timeline scrubbing widget for VisionMoCap Studio playback.

Provides a draggable slider with time displays and frame counter for
precise navigation through recorded motion sequences.
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

import customtkinter as ctk


class TimelineWidget(ctk.CTkFrame):
    """A timeline scrubber for playback navigation.

    Displays:
      * A horizontal slider spanning the full recording duration
      * Start time (00:00.00) on the left
      * End time (MM:SS.ss) on the right
      * Current frame number (Frame X / Y) below the slider

    The widget emits callbacks when the user drags the slider, allowing
    the application to seek to the requested position.

    Usage::

        def on_scrub(progress: float):
            controller.seek_to_progress(progress)

        timeline = TimelineWidget(parent, on_scrub=on_scrub)
        timeline.update_display(progress=0.5, current_frame=50, total_frames=100)
    """

    def __init__(
        self,
        master: ctk.BaseWidget,
        on_scrub: Optional[Callable[[float], None]] = None,
        on_scrub_release: Optional[Callable[[float], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)

        self._logger = logging.getLogger(self.__class__.__name__)
        self._on_scrub = on_scrub
        self._on_scrub_release = on_scrub_release
        self._is_dragging = False
        self._total_frames = 0

        # Configure grid
        self.grid_columnconfigure(0, weight=1)

        # Top row: time displays
        self._time_start_label = ctk.CTkLabel(
            self,
            text="00:00.00",
            font=ctk.CTkFont(size=11),
            anchor=ctk.W,
            width=60,
        )
        self._time_start_label.grid(row=0, column=0, padx=(0, 5), sticky=ctk.W)

        self._time_end_label = ctk.CTkLabel(
            self,
            text="--:--.--",
            font=ctk.CTkFont(size=11),
            anchor=ctk.E,
            width=60,
        )
        self._time_end_label.grid(row=0, column=2, padx=(5, 0), sticky=ctk.E)

        # Middle row: slider
        self._slider = ctk.CTkSlider(
            self,
            from_=0.0,
            to=1.0,
            number_of_steps=0,  # continuous
            command=self._on_slider_change,
        )
        self._slider.grid(row=1, column=0, columnspan=3, padx=8, pady=(2, 4), sticky="ew")

        # Bind mouse events for drag detection
        self._slider.bind("<ButtonPress-1>", self._on_drag_start)
        self._slider.bind("<ButtonRelease-1>", self._on_drag_end)
        self._slider.bind("<B1-Motion>", self._on_drag_motion)

        # Bottom row: frame counter
        self._frame_label = ctk.CTkLabel(
            self,
            text="Frame 0 / 0",
            font=ctk.CTkFont(size=11, weight="bold"),
            anchor=ctk.CENTER,
        )
        self._frame_label.grid(row=2, column=0, columnspan=3, pady=(0, 2))

        # Bind Configure to handle resize
        self.bind("<Configure>", self._on_resize)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_drag_start(self, event) -> None:
        """Called when user starts dragging the slider."""
        self._is_dragging = True
        self._logger.debug("Timeline scrub started.")

    def _on_drag_motion(self, event) -> None:
        """Called continuously while user drags the slider."""
        if not self._is_dragging:
            return
        # Slider value is already updated by CTkSlider
        progress = self._slider.get()
        if self._on_scrub:
            self._on_scrub(progress)

    def _on_drag_end(self, event) -> None:
        """Called when user releases the slider."""
        if not self._is_dragging:
            return
        self._is_dragging = False
        progress = self._slider.get()
        self._logger.debug("Timeline scrub ended at progress %.3f.", progress)
        if self._on_scrub_release:
            self._on_scrub_release(progress)

    def _on_slider_change(self, value: float) -> None:
        """Called by CTkSlider on value change (including programmatic)."""
        if self._is_dragging and self._on_scrub:
            self._on_scrub(value)

    def _on_resize(self, event) -> None:
        """Handle widget resize to ensure proper layout."""
        pass  # Layout is handled by grid

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update_display(
        self,
        progress: float,
        current_frame: int,
        total_frames: int,
        duration_seconds: float = 0.0,
        current_time: float = 0.0,
    ) -> None:
        """Update the timeline display with current playback position.

        Args:
            progress: Playback progress (0.0 to 1.0).
            current_frame: Current frame index.
            total_frames: Total number of frames in the recording.
            duration_seconds: Total duration in seconds (for end time display).
            current_time: Current elapsed time in seconds (for start time display).
        """
        self._total_frames = total_frames

        # Update slider position (clamped to valid range)
        progress = max(0.0, min(1.0, progress))
        self._slider.set(progress)

        # Update frame counter
        self._frame_label.configure(text=f"Frame {current_frame} / {total_frames}")

        # Update time displays
        self._time_start_label.configure(text=self._format_time(current_time))
        if duration_seconds > 0:
            self._time_end_label.configure(text=self._format_time(duration_seconds))

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the timeline widget.

        Args:
            enabled: If False, the slider is greyed out and non-interactive.
        """
        state = ctk.NORMAL if enabled else ctk.DISABLED
        self._slider.configure(state=state)

    def reset(self) -> None:
        """Reset the timeline to its initial state (no recording loaded)."""
        self._slider.set(0.0)
        self._time_start_label.configure(text="00:00.00")
        self._time_end_label.configure(text="--:--.--")
        self._frame_label.configure(text="Frame 0 / 0")
        self.set_enabled(False)
        self._total_frames = 0

    @staticmethod
    def _format_time(seconds: float) -> str:
        """Format a time value as MM:SS.ss.

        Args:
            seconds: Time in seconds.

        Returns:
            Formatted string like "01:23.45" or "12:34.56".
        """
        minutes = int(seconds) // 60
        secs = int(seconds) % 60
        centis = int((seconds * 100) % 100)
        return f"{minutes:02d}:{secs:02d}.{centis:02d}"

    @property
    def current_progress(self) -> float:
        """Return the current slider position (0.0 to 1.0)."""
        return self._slider.get()

    @property
    def is_dragging(self) -> bool:
        """Return True if the user is currently dragging the slider."""
        return self._is_dragging