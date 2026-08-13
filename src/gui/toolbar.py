"""Toolbar widget for the VisionMoCap Studio GUI.

Provides action buttons for camera control, recording, playback,
export, settings, and application exit.  Buttons are enabled/disabled
based on the current application state.

Layout
------
The toolbar content is horizontally scrollable so that every tool
stays reachable even in narrow windows::

    Toolbar (CTkFrame)
     ├── canvas viewport (tk.Canvas)
     │    └── content frame (CTkFrame) — all toolbar buttons
     └── horizontal scrollbar (CTkScrollbar, hidden when everything fits)

Scrolling is supported via the scrollbar, the mouse wheel, Shift +
mouse wheel, and horizontal trackpad gestures (reported by Tk as
Shift + wheel on Windows).  Only the toolbar scrolls — the rest of
the application window is unaffected.
"""

from __future__ import annotations

import logging
import tkinter as tk
from typing import Callable, Optional, TYPE_CHECKING

import customtkinter as ctk

if TYPE_CHECKING:
    from src.camera.device import CameraDevice
from src.gui.tooltip import Tooltip


class Toolbar(ctk.CTkFrame):
    """Horizontal, scrollable toolbar with application action buttons.

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

    _WHEEL_SCROLL_UNITS: int = 3

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
        on_toggle_loop: Optional[Callable[[], None]] = None,
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
        self._content_width: int = 0
        self._viewport_update_pending: bool = False

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Horizontal scrollable viewport ---
        self._canvas = tk.Canvas(self, highlightthickness=0, bd=0)
        self._canvas.grid(row=0, column=0, sticky="ew")
        self._canvas.configure(bg=self._viewport_bg_color())

        # Scrollable content — hosts every toolbar button.
        self._content = ctk.CTkFrame(self._canvas, fg_color="transparent")
        self._content_window = self._canvas.create_window(
            (0, 0), window=self._content, anchor="nw"
        )

        # Themed horizontal scrollbar (hidden automatically when the
        # content fits in the viewport).
        self._scrollbar = ctk.CTkScrollbar(
            self,
            orientation="horizontal",
            command=self._canvas.xview,
            height=12,
        )
        self._canvas.configure(xscrollcommand=self._scrollbar.set)
        self._scrollbar.grid(row=1, column=0, sticky="ew")

        self._canvas.bind("<Configure>", self._on_viewport_configure)
        self._content.bind("<Configure>", self._on_content_configure)

        # --- Build the toolbar buttons ---
        col = 0

        # --- Camera selector dropdown ---
        self._camera_menu = ctk.CTkOptionMenu(
            self._content,
            values=["No cameras"],
            state=ctk.DISABLED,
        )
        self._camera_menu.grid(row=0, column=col, padx=(4, 2), pady=4)
        col += 1

        self._start_btn = ctk.CTkButton(
            self._content,
            text="Start Camera",
            command=on_start_camera or self._noop,
        )
        self._start_btn.grid(row=0, column=col, padx=(4, 2), pady=4)
        col += 1

        self._stop_btn = ctk.CTkButton(
            self._content,
            text="Stop Camera",
            command=on_stop_camera or self._noop,
            state=ctk.DISABLED,
        )
        self._stop_btn.grid(row=0, column=col, padx=2, pady=4)
        col += 1

        self._record_btn = ctk.CTkButton(
            self._content,
            text="Record",
            command=on_record or self._noop,
            state=ctk.DISABLED,
        )
        self._record_btn.grid(row=0, column=col, padx=2, pady=4)
        col += 1

        self._pause_rec_btn = ctk.CTkButton(
            self._content,
            text="Pause",
            command=on_pause or self._noop,
            state=ctk.DISABLED,
        )
        self._pause_rec_btn.grid(row=0, column=col, padx=2, pady=4)
        col += 1

        sep1 = ctk.CTkLabel(self._content, text="  |  ")
        sep1.grid(row=0, column=col, padx=2, pady=4)
        col += 1

        # --- Playback controls ---
        self._load_btn = ctk.CTkButton(
            self._content,
            text="Load Recording",
            command=on_load_recording or self._noop,
        )
        self._load_btn.grid(row=0, column=col, padx=2, pady=4)
        col += 1

        self._play_btn = ctk.CTkButton(
            self._content,
            text="Play",
            command=on_play or self._noop,
            state=ctk.DISABLED,
        )
        self._play_btn.grid(row=0, column=col, padx=2, pady=4)
        col += 1

        self._pause_pb_btn = ctk.CTkButton(
            self._content,
            text="Pause",
            command=on_pause_playback or self._noop,
            state=ctk.DISABLED,
        )
        self._pause_pb_btn.grid(row=0, column=col, padx=2, pady=4)
        col += 1

        self._stop_pb_btn = ctk.CTkButton(
            self._content,
            text="Stop",
            command=on_stop_playback or self._noop,
            state=ctk.DISABLED,
        )
        self._stop_pb_btn.grid(row=0, column=col, padx=2, pady=4)
        col += 1

        self._step_bwd_btn = ctk.CTkButton(
            self._content,
            text="\u25C0",
            width=32,
            command=on_step_backward or self._noop,
            state=ctk.DISABLED,
        )
        self._step_bwd_btn.grid(row=0, column=col, padx=2, pady=4)
        col += 1

        self._step_fwd_btn = ctk.CTkButton(
            self._content,
            text="\u25B6",
            width=32,
            command=on_step_forward or self._noop,
            state=ctk.DISABLED,
        )
        self._step_fwd_btn.grid(row=0, column=col, padx=2, pady=4)
        col += 1

        self._loop_btn = ctk.CTkButton(
            self._content,
            text="Loop",
            width=52,
            command=on_toggle_loop or self._noop,
            state=ctk.DISABLED,
        )
        self._loop_btn.grid(row=0, column=col, padx=2, pady=4)
        col += 1

        sep2 = ctk.CTkLabel(self._content, text="  |  ")
        sep2.grid(row=0, column=col, padx=2, pady=4)
        col += 1

        self._create_anim_btn = ctk.CTkButton(
            self._content,
            text="Create Animation",
            command=on_create_animation or self._noop,
            state=ctk.DISABLED,
        )
        self._create_anim_btn.grid(row=0, column=col, padx=2, pady=4)
        col += 1

        self._export_btn = ctk.CTkButton(
            self._content,
            text="Export",
            command=on_export or self._noop,
            state=ctk.DISABLED,
        )
        self._export_btn.grid(row=0, column=col, padx=2, pady=4)
        col += 1

        self._blender_btn = ctk.CTkButton(
            self._content,
            text="Blender",
            command=on_blender or self._noop,
            state=ctk.DISABLED,
        )
        self._blender_btn.grid(row=0, column=col, padx=2, pady=4)
        col += 1

        self._settings_btn = ctk.CTkButton(
            self._content,
            text="Settings",
            command=on_settings or self._noop,
        )
        self._settings_btn.grid(row=0, column=col, padx=2, pady=4)
        col += 1

        self._theme_btn = ctk.CTkButton(
            self._content,
            text="\u263D Light",
            command=on_toggle_theme or self._noop,
        )
        self._theme_btn.grid(row=0, column=col, padx=2, pady=4)
        col += 1

        self._filters_btn = ctk.CTkButton(
            self._content,
            text="Filters",
            command=on_filters or self._noop,
            state=ctk.DISABLED,
        )
        self._filters_btn.grid(row=0, column=col, padx=2, pady=4)
        col += 1

        self._exit_btn = ctk.CTkButton(
            self._content,
            text="Exit",
            command=on_exit or self._noop,
        )
        self._exit_btn.grid(row=0, column=col, padx=(2, 4), pady=4)
        col += 1

        # Spacer to push buttons left.
        self._content.grid_columnconfigure(col, weight=1)

        # --- Remember default button colours so state resets can
        # restore the theme colour (never use fg_color=None). ---
        self._record_idle_color = self._record_btn.cget("fg_color")
        self._pause_rec_idle_color = self._pause_rec_btn.cget("fg_color")
        self._pause_pb_idle_color = self._pause_pb_btn.cget("fg_color")
        self._loop_idle_color = self._loop_btn.cget("fg_color")
        self._loop_hover_idle_color = self._loop_btn.cget("hover_color")

        # --- Wheel scrolling over the toolbar (see _on_mousewheel) ---
        toplevel = self.winfo_toplevel()
        for event in ("<MouseWheel>", "<Shift-MouseWheel>",
                      "<Button-4>", "<Button-5>"):
            toplevel.bind(event, self._on_mousewheel, add="+")

        # --- Tooltips (hover hints; see Tooltip) ---
        self._tooltips = self._attach_tooltips()

    # ------------------------------------------------------------------
    # Theme integration
    # ------------------------------------------------------------------

    def _viewport_bg_color(self) -> str:
        """Resolve the viewport background to match the toolbar frame."""
        return self._apply_appearance_mode(self.cget("fg_color"))

    def _set_appearance_mode(self, mode_string: str) -> None:
        """Keep the canvas viewport in sync when the app theme changes."""
        super()._set_appearance_mode(mode_string)
        self._canvas.configure(bg=self._viewport_bg_color())

    def _attach_tooltips(self) -> dict[str, Tooltip]:
        """Attach hover hints to the toolbar's interactive widgets."""
        hints: dict[tk.Misc, str] = {
            self._camera_menu: "Select the active camera",
            self._start_btn: "Start the camera feed",
            self._stop_btn: "Stop the camera feed",
            self._record_btn: "Start / stop recording motion",
            self._pause_rec_btn: "Pause / resume the recording",
            self._load_btn: "Load a recording (JSON)",
            self._play_btn: "Play or resume playback (Space)",
            self._pause_pb_btn: "Pause / resume playback",
            self._stop_pb_btn: "Stop playback and rewind",
            self._step_bwd_btn: "Step one frame backward (\u2190)",
            self._step_fwd_btn: "Step one frame forward (\u2192)",
            self._loop_btn: "Toggle loop playback (L)",
            self._create_anim_btn: "Convert the recording into an animation",
            self._export_btn: "Export recording / animation",
            self._blender_btn: "Send the animation to Blender",
            self._settings_btn: "Open settings",
            self._theme_btn: "Toggle light / dark theme",
            self._filters_btn: "Open motion filter settings",
            self._exit_btn: "Exit the application",
        }
        return {
            id(widget): Tooltip(widget, text)
            for widget, text in hints.items()
        }

    # ------------------------------------------------------------------
    # Scrolling
    # ------------------------------------------------------------------

    def _on_content_configure(self, event: tk.Event) -> None:
        """Track content size; size the viewport height to fit it."""
        self._content_width = event.width
        self._canvas.configure(
            scrollregion=(0, 0, event.width, event.height),
            height=event.height,
        )

    def _on_viewport_configure(self, event: tk.Event) -> None:
        """Show/hide the scrollbar based on whether scrolling is needed.

        Guarded against re-entry: hiding/showing the scrollbar and
        moving the view can make the widget update its idletasks, which
        re-fires this handler mid-call (see CTkScrollbar.set -> _draw).
        Nested invocations observe the same viewport width, so the
        outermost call already made the correct decision.
        """
        if self._viewport_update_pending:
            return
        self._viewport_update_pending = True
        try:
            if self._content_width <= event.width:
                self._canvas.xview_moveto(0)
                self._scrollbar.grid_remove()
            else:
                self._scrollbar.grid()
        finally:
            self._viewport_update_pending = False

    def _on_mousewheel(self, event: tk.Event) -> Optional[str]:
        """Scroll the toolbar horizontally from the mouse wheel.

        Supports the mouse wheel, Shift + wheel, and horizontal
        trackpad gestures.  Only reacts while the pointer is over the
        toolbar content, so other widgets are unaffected.  Return
        ``"break"`` so the event is not handled elsewhere.
        """
        widget = getattr(event, "widget", None)
        if widget is None or not self._pointer_over_toolbar(widget):
            return None

        if event.type == tk.EventType.MouseWheel:
            delta = getattr(event, "delta", 0)
            if delta == 0:
                return None
            steps = self._WHEEL_SCROLL_UNITS * (-1 if delta < 0 else 1)
        elif event.type == tk.EventType.ButtonPress:
            steps = (
                self._WHEEL_SCROLL_UNITS
                if getattr(event, "num", 5) == 5
                else -self._WHEEL_SCROLL_UNITS
            )
        else:
            return None

        self._canvas.xview_scroll(steps, "units")
        return "break"

    def _pointer_over_toolbar(self, widget: tk.Misc) -> bool:
        """True if *widget* (or one of its masters) is inside the toolbar."""
        node: Optional[tk.Misc] = widget
        while node is not None:
            if node is self._canvas or node is self._content:
                return True
            node = getattr(node, "master", None)
        return False

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
        self._pause_rec_btn.configure(
            text="Pause", fg_color=self._pause_rec_idle_color
        )

    def set_not_recording(self) -> None:
        """Revert all recording buttons to their idle state."""
        self._record_btn.configure(
            text="Record", fg_color=self._record_idle_color
        )
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
        self._loop_btn.configure(state=ctk.NORMAL)

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
        self._pause_pb_btn.configure(
            text="Pause", fg_color=self._pause_pb_idle_color
        )

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
        self._loop_btn.configure(state=ctk.DISABLED)
        self.set_loop_enabled(False)

    def set_loop_enabled(self, enabled: bool) -> None:
        """Highlight the Loop button when loop playback is active.

        Args:
            enabled: True when loop playback is enabled.
        """
        if enabled:
            self._loop_btn.configure(
                fg_color="#27ae60",
                hover_color="#2ecc71",
                text="Loop ON",
            )
        else:
            self._loop_btn.configure(
                fg_color=self._loop_idle_color,
                hover_color=self._loop_hover_idle_color,
                text="Loop",
            )

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
