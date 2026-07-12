"""Toolbar widget for the VisionMoCap Studio GUI.

Provides action buttons for camera control, recording, export,
settings, and application exit.  Buttons are enabled/disabled
based on the current application state (e.g. Start Camera is
disabled when the camera is already open).
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

import customtkinter as ctk


class Toolbar(ctk.CTkFrame):
    """Horizontal toolbar with application action buttons.

    Exposes methods to enable/disable button groups as the
    application state changes.  All button callbacks are injected
    via the constructor.

    Buttons:
        start_camera   — Open the camera.
        stop_camera    — Close the camera.
        record         — Begin / stop motion recording.
        pause          — Pause / resume recording.
        export         — Export the last recording.
        settings       — Open the settings dialog.
        exit           — Quit the application.
    """

    def __init__(
        self,
        master: ctk.BaseWidget,
        on_start_camera: Optional[Callable[[], None]] = None,
        on_stop_camera: Optional[Callable[[], None]] = None,
        on_record: Optional[Callable[[], None]] = None,
        on_pause: Optional[Callable[[], None]] = None,
        on_export: Optional[Callable[[], None]] = None,
        on_settings: Optional[Callable[[], None]] = None,
        on_exit: Optional[Callable[[], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self._logger = logging.getLogger(self.__class__.__name__)

        self.grid_columnconfigure(0, weight=0)

        col = 0
        self._start_btn = ctk.CTkButton(
            self,
            text="Start Camera",
            command=on_start_camera or self._noop,
        )
        self._start_btn.grid(row=0, column=col, padx=(4, 2), pady=4)
        col += 1

        self._stop_btn = ctk.CTkButton(
            self,
            text="Stop Camera",
            command=on_stop_camera or self._noop,
            state=ctk.DISABLED,
        )
        self._stop_btn.grid(row=0, column=col, padx=2, pady=4)
        col += 1

        self._record_btn = ctk.CTkButton(
            self,
            text="Record",
            command=on_record or self._noop,
            state=ctk.DISABLED,
        )
        self._record_btn.grid(row=0, column=col, padx=2, pady=4)
        col += 1

        self._pause_btn = ctk.CTkButton(
            self,
            text="Pause",
            command=on_pause or self._noop,
            state=ctk.DISABLED,
        )
        self._pause_btn.grid(row=0, column=col, padx=2, pady=4)
        col += 1

        sep1 = ctk.CTkLabel(self, text="  |  ")
        sep1.grid(row=0, column=col, padx=2, pady=4)
        col += 1

        self._export_btn = ctk.CTkButton(
            self,
            text="Export",
            command=on_export or self._noop,
            state=ctk.DISABLED,
        )
        self._export_btn.grid(row=0, column=col, padx=2, pady=4)
        col += 1

        self._settings_btn = ctk.CTkButton(
            self,
            text="Settings",
            command=on_settings or self._noop,
        )
        self._settings_btn.grid(row=0, column=col, padx=2, pady=4)
        col += 1

        self._exit_btn = ctk.CTkButton(
            self,
            text="Exit",
            command=on_exit or self._noop,
        )
        self._exit_btn.grid(row=0, column=col, padx=(2, 4), pady=4)
        col += 1

        # Spacer to push buttons left.
        self.grid_columnconfigure(col, weight=1)

    # ------------------------------------------------------------------
    # State helpers
    # ------------------------------------------------------------------

    def set_camera_started(self) -> None:
        """Update button state after the camera has started."""
        self._start_btn.configure(state=ctk.DISABLED)
        self._stop_btn.configure(state=ctk.NORMAL)
        self._record_btn.configure(state=ctk.NORMAL)

    def set_camera_stopped(self) -> None:
        """Update button state after the camera has stopped."""
        self._start_btn.configure(state=ctk.NORMAL)
        self._stop_btn.configure(state=ctk.DISABLED)
        self._record_btn.configure(state=ctk.DISABLED, text="Record")
        self._pause_btn.configure(state=ctk.DISABLED, text="Pause")

    def set_recording(self) -> None:
        """Update buttons to indicate active recording."""
        self._record_btn.configure(text="Stop Recording", fg_color="#c0392b")
        self._pause_btn.configure(state=ctk.NORMAL, text="Pause")

    def set_paused(self) -> None:
        """Update buttons to indicate paused recording."""
        self._pause_btn.configure(text="Resume", fg_color="#e67e22")

    def set_resumed(self) -> None:
        """Update buttons to indicate resumed recording."""
        self._pause_btn.configure(text="Pause", fg_color=None)

    def set_not_recording(self) -> None:
        """Revert all recording buttons to their idle state."""
        self._record_btn.configure(text="Record", fg_color=None)
        self._pause_btn.configure(state=ctk.DISABLED, text="Pause")

    def enable_export(self) -> None:
        """Enable the export button (recording data available)."""
        self._export_btn.configure(state=ctk.NORMAL)

    def disable_export(self) -> None:
        """Disable the export button."""
        self._export_btn.configure(state=ctk.DISABLED)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _noop() -> None:
        pass