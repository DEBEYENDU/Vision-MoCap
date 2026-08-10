"""Toolbar widget for the VisionMoCap Studio GUI.

Provides action buttons for camera control, recording, playback,
export, settings, and application exit.  Buttons are enabled/disabled
based on the current application state.
"""

from __future__ import annotations

import logging
from typing import Callable, Optional, TYPE_CHECKING

import customtkinter as ctk

if TYPE_CHECKING:
    from src.camera.device import CameraDevice


class Toolbar(ctk.CTkFrame):
    """Horizontal toolbar with application action buttons.

    Exposes methods to enable/disable button groups as the
    application state changes.  All button callbacks are injected
    via the constructor.

    Buttons:
        start_camera   — Open the camera.
        stop_camera    — Close the camera.
        record         — Begin / stop motion recording.
        pause_rec      — Pause / resume recording.
        load_recording — Load a recorded JSON file for playback.
        play           — Start / restart playback.
        pause_pb       — Pause / resume playback.
        stop_pb        — Stop and reset playback.
        step_fwd       — Step forward one frame.
        step_back      — Step backward one frame.
        create_anim    — Convert the loaded recording into an animation.
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
        on_load_recording: Optional[Callable[[], None]] = None,
        on_play: Optional[Callable[[], None]] = None,
        on_pause_playback: Optional[Callable[[], None]] = None,
        on_stop_playback: Optional[Callable[[], None]] = None,
        on_step_forward: Optional[Callable[[], None]] = None,
        on_step_backward: Optional[Callable[[], None]] = None,
        on_create_animation: Optional[Callable[[], None]] = None,
        on_export: Optional[Callable[[], None]] = None,
        on_blender: Optional[Callable[[], None]] = None,
        on_settings: Optional[Callable[[], None]] = None,
        on_toggle_theme: Optional[Callable[[], None]] = None,
        on_filters: Optional[Callable[[], None]] = None,
        on_exit: Optional[Callable[[], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self._logger = logging.getLogger(self.__class__.__name__)
        self._camera_index_map: dict[str, int] = {}

        self.grid_columnconfigure(0, weight=0)

        col = 0

        # --- Camera selector dropdown ---
        self._camera_menu = ctk.CTkOptionMenu(
            self,
            values=["No cameras"],
            state=ctk.DISABLED,
        )
        self._camera_menu.grid(row=0, column=col, padx=(4, 2), pady=4)
        col += 1

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

        self._pause_rec_btn = ctk.CTkButton(
            self,
            text="Pause",
            command=on_pause or self._noop,
            state=ctk.DISABLED,
        )
        self._pause_rec_btn.grid(row=0, column=col, padx=2, pady=4)
        col += 1

        sep1 = ctk.CTkLabel(self, text="  |  ")
        sep1.grid(row=0, column=col, padx=2, pady=4)
        col += 1

        # --- Playback controls ---
        self._load_btn = ctk.CTkButton(
            self,
            text="Load Recording",
            command=on_load_recording or self._noop,
        )
        self._load_btn.grid(row=0, column=col, padx=2, pady=4)
        col += 1

        self._play_btn = ctk.CTkButton(
            self,
            text="Play",
            command=on_play or self._noop,
            state=ctk.DISABLED,
        )
        self._play_btn.grid(row=0, column=col, padx=2, pady=4)
        col += 1

        self._pause_pb_btn = ctk.CTkButton(
            self,
            text="Pause",
            command=on_pause_playback or self._noop,
            state=ctk.DISABLED,
        )
        self._pause_pb_btn.grid(row=0, column=col, padx=2, pady=4)
        col += 1

        self._stop_pb_btn = ctk.CTkButton(
            self,
            text="Stop",
            command=on_stop_playback or self._noop,
            state=ctk.DISABLED,
        )
        self._stop_pb_btn.grid(row=0, column=col, padx=2, pady=4)
        col += 1

        self._step_bwd_btn = ctk.CTkButton(
            self,
            text="\u25C0",
            width=32,
            command=on_step_backward or self._noop,
            state=ctk.DISABLED,
        )
        self._step_bwd_btn.grid(row=0, column=col, padx=2, pady=4)
        col += 1

        self._step_fwd_btn = ctk.CTkButton(
            self,
            text="\u25B6",
            width=32,
            command=on_step_forward or self._noop,
            state=ctk.DISABLED,
        )
        self._step_fwd_btn.grid(row=0, column=col, padx=2, pady=4)
        col += 1

        sep2 = ctk.CTkLabel(self, text="  |  ")
        sep2.grid(row=0, column=col, padx=2, pady=4)
        col += 1

        self._create_anim_btn = ctk.CTkButton(
            self,
            text="Create Animation",
            command=on_create_animation or self._noop,
            state=ctk.DISABLED,
        )
        self._create_anim_btn.grid(row=0, column=col, padx=2, pady=4)
        col += 1

        self._export_btn = ctk.CTkButton(
            self,
            text="Export",
            command=on_export or self._noop,
            state=ctk.DISABLED,
        )
        self._export_btn.grid(row=0, column=col, padx=2, pady=4)
        col += 1

        self._blender_btn = ctk.CTkButton(
            self,
            text="Blender",
            command=on_blender or self._noop,
            state=ctk.DISABLED,
        )
        self._blender_btn.grid(row=0, column=col, padx=2, pady=4)
        col += 1

        self._settings_btn = ctk.CTkButton(
            self,
            text="Settings",
            command=on_settings or self._noop,
        )
        self._settings_btn.grid(row=0, column=col, padx=2, pady=4)
        col += 1

        self._theme_btn = ctk.CTkButton(
            self,
            text="\u263D Light",
            command=on_toggle_theme or self._noop,
        )
        self._theme_btn.grid(row=0, column=col, padx=2, pady=4)
        col += 1

        self._filters_btn = ctk.CTkButton(
            self,
            text="Filters",
            command=on_filters or self._noop,
            state=ctk.DISABLED,
        )
        self._filters_btn.grid(row=0, column=col, padx=2, pady=4)
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
    # Camera selector
    # ------------------------------------------------------------------

    def set_camera_list(self, devices: list[CameraDevice]) -> None:
        """Populate the camera selector dropdown with discovered devices.

        Format: ``"Camera N (Working)"`` or ``"Camera N (Unavailable)"``.
        """
        self._camera_index_map.clear()
        if not devices:
            self._camera_menu.configure(
                values=["No cameras"],
                state=ctk.DISABLED,
            )
            return

        labels: list[str] = []
        for d in devices:
            status = "Working" if d.is_available else "Unavailable"
            label = f"Camera {d.index} ({status})"
            labels.append(label)
            self._camera_index_map[label] = d.index

        self._camera_menu.configure(
            values=labels,
            state=ctk.NORMAL,
        )
        self._camera_menu.set(labels[0])

    def get_selected_camera(self) -> int:
        """Return the index of the currently selected camera, or 0."""
        label = self._camera_menu.get()
        return self._camera_index_map.get(label, 0)

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
        self._pause_rec_btn.configure(state=ctk.DISABLED, text="Pause")

    def set_recording(self) -> None:
        """Update buttons to indicate active recording."""
        self._record_btn.configure(text="Stop Recording", fg_color="#c0392b")
        self._pause_rec_btn.configure(state=ctk.NORMAL, text="Pause")

    def set_paused(self) -> None:
        """Update buttons to indicate paused recording."""
        self._pause_rec_btn.configure(text="Resume", fg_color="#e67e22")

    def set_resumed(self) -> None:
        """Update buttons to indicate resumed recording."""
        self._pause_rec_btn.configure(text="Pause", fg_color=None)

    def set_not_recording(self) -> None:
        """Revert all recording buttons to their idle state."""
        self._record_btn.configure(text="Record", fg_color=None)
        self._pause_rec_btn.configure(state=ctk.DISABLED, text="Pause")

    # ------------------------------------------------------------------
    # Playback state helpers
    # ------------------------------------------------------------------

    def set_playback_loaded(self) -> None:
        """Enable playback transport controls after a file is loaded."""
        self._play_btn.configure(state=ctk.NORMAL)
        self._stop_pb_btn.configure(state=ctk.DISABLED)
        self._pause_pb_btn.configure(state=ctk.DISABLED, text="Pause")
        self._step_fwd_btn.configure(state=ctk.NORMAL)
        self._step_bwd_btn.configure(state=ctk.NORMAL)

    def set_playback_playing(self) -> None:
        """Update buttons to indicate active playback."""
        self._play_btn.configure(state=ctk.DISABLED)
        self._pause_pb_btn.configure(state=ctk.NORMAL, text="Pause")
        self._stop_pb_btn.configure(state=ctk.NORMAL)

    def set_playback_paused(self) -> None:
        """Update buttons to indicate paused playback."""
        self._play_btn.configure(state=ctk.DISABLED)
        self._pause_pb_btn.configure(text="Resume", fg_color="#e67e22")

    def set_playback_resumed(self) -> None:
        """Update buttons after resuming from pause."""
        self._pause_pb_btn.configure(text="Pause", fg_color=None)

    def set_playback_stopped(self) -> None:
        """Revert playback buttons to the loaded-but-idle state."""
        self._play_btn.configure(state=ctk.NORMAL)
        self._pause_pb_btn.configure(state=ctk.DISABLED, text="Pause")
        self._stop_pb_btn.configure(state=ctk.DISABLED)

    def set_playback_finished(self) -> None:
        """Handle end-of-playback — enable Play (to restart)."""
        self._play_btn.configure(state=ctk.NORMAL, text="Replay")
        self._pause_pb_btn.configure(state=ctk.DISABLED, text="Pause")
        self._stop_pb_btn.configure(state=ctk.DISABLED)

    def set_no_playback(self) -> None:
        """Reset all playback buttons to idle (no recording loaded)."""
        self._play_btn.configure(state=ctk.DISABLED, text="Play")
        self._pause_pb_btn.configure(state=ctk.DISABLED, text="Pause")
        self._stop_pb_btn.configure(state=ctk.DISABLED)
        self._step_fwd_btn.configure(state=ctk.DISABLED)
        self._step_bwd_btn.configure(state=ctk.DISABLED)

    def enable_animation(self) -> None:
        """Enable the Create Animation button (recording loaded)."""
        self._create_anim_btn.configure(state=ctk.NORMAL)

    def disable_animation(self) -> None:
        """Disable the Create Animation button."""
        self._create_anim_btn.configure(state=ctk.DISABLED)

    def set_animation_created(self) -> None:
        """Mark the animation as created (button reflects regeneration)."""
        self._create_anim_btn.configure(text="Recreate Animation")

    def set_animation_cleared(self) -> None:
        """Reset the animation button after unload."""
        self._create_anim_btn.configure(text="Create Animation")

    def enable_export(self) -> None:
        """Enable the export button (recording data available)."""
        self._export_btn.configure(state=ctk.NORMAL)

    def disable_export(self) -> None:
        """Disable the export button."""
        self._export_btn.configure(state=ctk.DISABLED)

    def enable_blender(self) -> None:
        """Enable the Blender button (playback sequence loaded)."""
        self._blender_btn.configure(state=ctk.NORMAL)

    def disable_blender(self) -> None:
        """Disable the Blender button."""
        self._blender_btn.configure(state=ctk.DISABLED)

    def set_filters_enabled(self, enabled: bool = True) -> None:
        """Enable or disable the Filters button.

        Args:
            enabled: True enables the button, False disables it.
        """
        state = ctk.NORMAL if enabled else ctk.DISABLED
        self._filters_btn.configure(state=state)

    def set_theme(self, theme: str) -> None:
        """Update the theme toggle button text to reflect the current mode.

        Args:
            theme: "dark" or "light".
        """
        if theme == "light":
            self._theme_btn.configure(text="\u263D Light")
        else:
            self._theme_btn.configure(text="\u2600 Dark")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _noop() -> None:
        pass