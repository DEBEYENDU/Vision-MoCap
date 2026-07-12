"""Status bar widget for the VisionMoCap Studio GUI.

Displays real-time telemetry: FPS, tracking confidence, camera
status, recording status, and camera index.  Each metric is shown
in a labelled section with an auto-hide capability for flashing
messages.
"""

from __future__ import annotations

import logging
from typing import Optional

import customtkinter as ctk


class StatusBar(ctk.CTkFrame):
    """Application status bar showing live telemetry values.

    Five labelled indicators are displayed horizontally:
      * FPS — current/average frames per second.
      * Confidence — pose tracking confidence (0–100 %).
      * Camera — camera device status.
      * Camera Index — active camera device index.
      * Recording — recording session state.

    Additionally a *flash* method can be called to temporarily
    show a coloured message (e.g. error / warning).
    """

    def __init__(self, master: ctk.BaseWidget, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self._logger = logging.getLogger(self.__class__.__name__)

        # FPS
        self._fps_label = ctk.CTkLabel(
            self,
            text="FPS: 0.0",
            font=ctk.CTkFont(size=12),
            anchor=ctk.W,
        )
        self._fps_label.grid(row=0, column=0, padx=(8, 12), pady=4, sticky=ctk.W)

        # Confidence
        self._conf_label = ctk.CTkLabel(
            self,
            text="Confidence: 0%",
            font=ctk.CTkFont(size=12),
            anchor=ctk.W,
        )
        self._conf_label.grid(row=0, column=1, padx=8, pady=4, sticky=ctk.W)

        # Camera status
        self._cam_label = ctk.CTkLabel(
            self,
            text="Camera: Off",
            font=ctk.CTkFont(size=12),
            anchor=ctk.W,
        )
        self._cam_label.grid(row=0, column=2, padx=8, pady=4, sticky=ctk.W)

        # Camera index
        self._cam_idx_label = ctk.CTkLabel(
            self,
            text="Index: --",
            font=ctk.CTkFont(size=12),
            anchor=ctk.W,
        )
        self._cam_idx_label.grid(row=0, column=3, padx=8, pady=4, sticky=ctk.W)

        # Recording status
        self._rec_label = ctk.CTkLabel(
            self,
            text="Recording: Idle",
            font=ctk.CTkFont(size=12),
            anchor=ctk.W,
        )
        self._rec_label.grid(row=0, column=4, padx=8, pady=4, sticky=ctk.W)

        # Flash message (hidden by default)
        self._flash_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=12),
            anchor=ctk.E,
        )
        self._flash_label.grid(
            row=0, column=5, padx=8, pady=4, sticky=ctk.E
        )
        self.grid_columnconfigure(5, weight=1)

        self._flash_job: Optional[str] = None

    # ------------------------------------------------------------------
    # Update methods
    # ------------------------------------------------------------------

    def set_fps(self, fps: float) -> None:
        """Update the FPS display.

        Args:
            fps: Current frames-per-second value.
        """
        self._fps_label.configure(text=f"FPS: {fps:.1f}")

    def set_confidence(self, confidence: float) -> None:
        """Update the tracking confidence display.

        Args:
            confidence: Value in [0.0, 1.0].
        """
        percent = min(max(int(confidence * 100), 0), 100)
        self._conf_label.configure(text=f"Confidence: {percent}%")

    def set_camera_status(self, status: str) -> None:
        """Update the camera status text.

        Args:
            status: e.g. "Camera 0", "Off", "Error".
        """
        self._cam_label.configure(text=f"Camera: {status}")

    def set_camera_index(self, index: int) -> None:
        """Update the camera index display.

        Args:
            index: Device index, or -1 to show ``--``.
        """
        text = f"Index: {index}" if index >= 0 else "Index: --"
        self._cam_idx_label.configure(text=text)

    def set_recording_status(self, recording: bool, count: int = 0) -> None:
        """Update the recording status display.

        Args:
            recording: Whether a recording session is active.
            count: Number of frames recorded so far.
        """
        if recording:
            text = f"[REC] {count} frames"
            self._rec_label.configure(
                text=text, text_color="#e74c3c"
            )
        else:
            self._rec_label.configure(
                text="Recording: Idle",
                text_color=("black", "white"),
            )

    def flash(self, message: str, level: str = "INFO") -> None:
        """Show a temporary status message.

        The message auto-clears after 5 seconds unless another
        flash call is made before then.

        Args:
            message: The text to display.
            level: ``"ERROR"`` (red), ``"WARNING"`` (yellow),
                or any other value (neutral).
        """
        if self._flash_job is not None:
            self.after_cancel(self._flash_job)
            self._flash_job = None

        colour = self._resolve_flash_colour(level)
        self._flash_label.configure(text=message, text_color=colour)
        self._flash_job = self.after(
            5000,
            lambda: self._flash_label.configure(text=""),
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_flash_colour(level: str) -> str:
        if level.upper() == "ERROR":
            return "#e74c3c"
        if level.upper() == "WARNING":
            return "#f39c12"
        return "#95a5a6"