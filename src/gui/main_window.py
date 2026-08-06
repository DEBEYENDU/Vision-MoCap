"""Main window for the VisionMoCap Studio GUI.

Provides the top-level application window with a dark CustomTkinter
theme, a live camera preview (CameraWidget), an information panel, a
toolbar, and a status bar.  All pipeline communication is routed
through AppController.

The frame pipeline (capture → detect → render) runs in a dedicated
worker thread inside AppController.  The GUI thread consumes
rendered frames from a thread-safe queue and updates the status bar
at 1-second intervals.
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from tkinter import messagebox
from typing import Callable, Optional, TYPE_CHECKING

import customtkinter as ctk

if TYPE_CHECKING:
    from src.config.manager import MotionConfig

from src.gui.app_controller import AppController
from src.gui.base import GUIAppBase
from src.gui.camera_widget import CameraWidget
from src.gui.settings_dialog import SettingsDialog
from src.gui.status_bar import StatusBar
from src.gui.toolbar import Toolbar
from src.gui.timeline_widget import TimelineWidget


class InfoPanel(ctk.CTkFrame):
    """Side panel showing diagnostic information about the current session.

    Displays camera metadata, frame count, pose status, recording
    indicator with a red dot and live timer (MM:SS), and recorded
    frame count in a compact vertical layout.
    """

    def __init__(self, master: ctk.BaseWidget, **kwargs) -> None:
        super().__init__(master, width=280, **kwargs)
        self.grid_propagate(False)

        self._title = ctk.CTkLabel(
            self,
            text="Information",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor=ctk.W,
        )
        self._title.grid(row=0, column=0, padx=12, pady=(12, 4), sticky=ctk.W)

        self._device_label = ctk.CTkLabel(
            self, text="Device: --", anchor=ctk.W, justify=ctk.LEFT
        )
        self._device_label.grid(row=1, column=0, padx=12, pady=2, sticky=ctk.W)

        self._resolution_label = ctk.CTkLabel(
            self, text="Resolution: --", anchor=ctk.W, justify=ctk.LEFT
        )
        self._resolution_label.grid(
            row=2, column=0, padx=12, pady=2, sticky=ctk.W
        )

        self._frame_label = ctk.CTkLabel(
            self, text="Frame: 0", anchor=ctk.W, justify=ctk.LEFT
        )
        self._frame_label.grid(row=3, column=0, padx=12, pady=2, sticky=ctk.W)

        self._pose_label = ctk.CTkLabel(
            self, text="Pose: --", anchor=ctk.W, justify=ctk.LEFT
        )
        self._pose_label.grid(row=4, column=0, padx=12, pady=2, sticky=ctk.W)

        # Recording indicator row: red dot + timer + frame counter
        self._rec_indicator = ctk.CTkLabel(
            self,
            text="\u25CF",  # filled circle
            font=ctk.CTkFont(size=14),
            text_color="#555555",
            anchor=ctk.W,
        )
        self._rec_indicator.grid(
            row=5, column=0, padx=12, pady=(2, 0), sticky=ctk.W
        )

        self._rec_timer_label = ctk.CTkLabel(
            self,
            text="Recording Idle",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor=ctk.W,
        )
        self._rec_timer_label.grid(
            row=6, column=0, padx=12, pady=(0, 2), sticky=ctk.W
        )

        self._rec_frames_label = ctk.CTkLabel(
            self, text="Frames: 0", anchor=ctk.W, justify=ctk.LEFT
        )
        self._rec_frames_label.grid(
            row=7, column=0, padx=12, pady=2, sticky=ctk.W
        )

        # --- Playback section ---
        sep = ctk.CTkLabel(self, text="")
        sep.grid(row=8, column=0, padx=12, pady=2, sticky=ctk.W)

        self._pb_title = ctk.CTkLabel(
            self,
            text="Playback",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor=ctk.W,
        )
        self._pb_title.grid(row=9, column=0, padx=12, pady=(8, 4), sticky=ctk.W)

        self._pb_source_label = ctk.CTkLabel(
            self,
            text="Source: --",
            anchor=ctk.W,
            justify=ctk.LEFT,
            wraplength=260,
        )
        self._pb_source_label.grid(
            row=10, column=0, padx=12, pady=2, sticky=ctk.W
        )

        self._pb_state_label = ctk.CTkLabel(
            self,
            text="Stopped",
            anchor=ctk.W,
            justify=ctk.LEFT,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self._pb_state_label.grid(
            row=11, column=0, padx=12, pady=2, sticky=ctk.W
        )

        self._pb_frame_label = ctk.CTkLabel(
            self, text="Frame: 0 / 0", anchor=ctk.W, justify=ctk.LEFT
        )
        self._pb_frame_label.grid(
            row=12, column=0, padx=12, pady=2, sticky=ctk.W
        )

        self._pb_duration_label = ctk.CTkLabel(
            self, text="Duration: --", anchor=ctk.W, justify=ctk.LEFT
        )
        self._pb_duration_label.grid(
            row=13, column=0, padx=12, pady=2, sticky=ctk.W
        )

        self.grid_rowconfigure(14, weight=1)

    # ------------------------------------------------------------------
    # Update methods
    # ------------------------------------------------------------------

    def set_device(self, name: str) -> None:
        self._device_label.configure(text=f"Device: {name}")

    def set_resolution(self, width: int, height: int) -> None:
        self._resolution_label.configure(
            text=f"Resolution: {width}x{height}"
        )

    def set_frame_number(self, number: int) -> None:
        self._frame_label.configure(text=f"Frame: {number}")

    def set_pose_detected(self, detected: bool) -> None:
        if detected:
            self._pose_label.configure(
                text="Pose: Detected",
                text_color="#2ecc71",
            )
        else:
            self._pose_label.configure(
                text="Pose: Not Detected",
                text_color="#e74c3c",
            )
            

    def set_recording_indicator(self, active: bool, paused: bool = False) -> None:
        """Update the red-dot indicator and timer label.

        Args:
            active: Whether recording is in progress (or paused).
            paused: Whether recording is paused (shows orange colour).
        """
        if not active:
            self._rec_indicator.configure(text="\u25CF", text_color="#555555")
            self._rec_timer_label.configure(text="Recording Idle")
        elif paused:
            self._rec_indicator.configure(text="\u25CF", text_color="#e67e22")
            self._rec_timer_label.configure(
                text="PAUSED", text_color="#e67e22"
            )
        else:
            self._rec_indicator.configure(text="\u25CF", text_color="#e74c3c")
            self._rec_timer_label.configure(
                text="REC", text_color="#e74c3c"
            )

    def set_recording_timer(self, elapsed: float) -> None:
        """Update the recording timer display (MM:SS format)."""
        minutes = int(elapsed) // 60
        seconds = int(elapsed) % 60
        self._rec_timer_label.configure(
            text=f"REC {minutes:02d}:{seconds:02d}",
            text_color="#e74c3c",
        )

    def set_recording_frames(self, count: int) -> None:
        """Update the recorded frame count."""
        self._rec_frames_label.configure(text=f"Frames: {count}")

    def set_recorded_count(self, count: int) -> None:
        """Set the final recording frame count after a session ends."""
        self._rec_frames_label.configure(text=f"Frames: {count}")

    def set_playback_source(self, name: str) -> None:
        self._pb_source_label.configure(text=f"Source: {name}")

    def set_playback_state(self, state_name: str) -> None:
        colour_map = {
            "STOPPED": ("black", "white"),
            "PLAYING": "#2ecc71",
            "PAUSED": "#e67e22",
            "FINISHED": "#3498db",
        }
        colour = colour_map.get(state_name, ("black", "white"))
        self._pb_state_label.configure(text=state_name, text_color=colour)

    def set_playback_frame(self, current: int, total: int) -> None:
        self._pb_frame_label.configure(text=f"Frame: {current} / {total}")

    def set_playback_duration(self, seconds: float) -> None:
        minutes = int(seconds) // 60
        secs = int(seconds) % 60
        self._pb_duration_label.configure(
            text=f"Duration: {minutes:02d}:{secs:02d}"
        )

    def clear_playback(self) -> None:
        self._pb_source_label.configure(text="Source: --")
        self._pb_state_label.configure(text="Stopped", text_color=("black", "white"))
        self._pb_frame_label.configure(text="Frame: 0 / 0")
        self._pb_duration_label.configure(text="Duration: --")

    def clear(self) -> None:
        self._device_label.configure(text="Device: --")
        self._resolution_label.configure(text="Resolution: --")
        self._frame_label.configure(text="Frame: 0")
        self._pose_label.configure(
            text="Pose: --",
            text_color=("black", "white"),
        )
        self.set_recording_indicator(False)
        self._rec_timer_label.configure(
            text="Recording Idle",
            text_color=("black", "white"),
        )
        self._rec_frames_label.configure(text="Frames: 0")
        self.clear_playback()


class FilterDialog(ctk.CTkToplevel):
    """Modal dialog for configuring the motion filter pipeline.

    Allows enabling/disabling individual filters and adjusting their
    parameters.  Apply runs the pipeline on the current sequence;
    Reset restores the original unfiltered sequence.
    """

    def __init__(
        self,
        master: ctk.BaseWidget,
        config: "MotionConfig",
        on_apply: Callable[[], None],
        on_reset: Callable[[], None],
    ) -> None:
        super().__init__(master)
        self._config = config
        self._on_apply = on_apply
        self._on_reset = on_reset

        self.title("Motion Filters")
        self.geometry("480x520")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self._build_ui()

    def _build_ui(self) -> None:
        row = 0

        # --- Outlier Removal ---
        self._outlier_var = ctk.BooleanVar(value=self._config.use_outlier_removal)
        self._outlier_cb = ctk.CTkCheckBox(
            self, text="Outlier Removal", variable=self._outlier_var,
        )
        self._outlier_cb.grid(row=row, column=0, padx=12, pady=(12, 2), sticky=ctk.W)
        row += 1

        ctk.CTkLabel(self, text="  Std Threshold:").grid(
            row=row, column=0, padx=24, sticky=ctk.W
        )
        self._outlier_threshold_slider = ctk.CTkSlider(
            self, from_=0.01, to=1.0, number_of_steps=99,
            command=lambda v: setattr(self._config, "outlier_threshold", round(v, 2)),
        )
        self._outlier_threshold_slider.set(self._config.outlier_threshold)
        self._outlier_threshold_slider.grid(
            row=row, column=1, padx=(0, 12), pady=2, sticky="ew"
        )
        row += 1

        # --- Exponential Smoothing ---
        self._exp_var = ctk.BooleanVar(value=self._config.use_exponential_smoothing)
        self._exp_cb = ctk.CTkCheckBox(
            self, text="Exponential Smoothing", variable=self._exp_var,
        )
        self._exp_cb.grid(row=row, column=0, padx=12, pady=(8, 2), sticky=ctk.W)
        row += 1

        ctk.CTkLabel(self, text="  Alpha:").grid(
            row=row, column=0, padx=24, sticky=ctk.W
        )
        self._exp_alpha_slider = ctk.CTkSlider(
            self, from_=0.01, to=1.0, number_of_steps=99,
            command=lambda v: setattr(self._config, "exponential_alpha", round(v, 2)),
        )
        self._exp_alpha_slider.set(self._config.exponential_alpha)
        self._exp_alpha_slider.grid(
            row=row, column=1, padx=(0, 12), pady=2, sticky="ew"
        )
        row += 1

        # --- Moving Average ---
        self._ma_var = ctk.BooleanVar(value=self._config.use_moving_average)
        self._ma_cb = ctk.CTkCheckBox(
            self, text="Moving Average", variable=self._ma_var,
        )
        self._ma_cb.grid(row=row, column=0, padx=12, pady=(8, 2), sticky=ctk.W)
        row += 1

        ctk.CTkLabel(self, text="  Window Size:").grid(
            row=row, column=0, padx=24, sticky=ctk.W
        )
        self._ma_window_slider = ctk.CTkSlider(
            self, from_=3, to=31, number_of_steps=14,
            command=lambda v: setattr(self._config, "smoothing_window", int(v)),
        )
        self._ma_window_slider.set(self._config.smoothing_window)
        self._ma_window_slider.grid(
            row=row, column=1, padx=(0, 12), pady=2, sticky="ew"
        )
        row += 1

        # --- One Euro Filter ---
        self._oneeuro_var = ctk.BooleanVar(value=self._config.use_one_euro)
        self._oneeuro_cb = ctk.CTkCheckBox(
            self, text="One Euro Filter", variable=self._oneeuro_var,
        )
        self._oneeuro_cb.grid(row=row, column=0, padx=12, pady=(8, 2), sticky=ctk.W)
        row += 1

        ctk.CTkLabel(self, text="  Min Cutoff:").grid(
            row=row, column=0, padx=24, sticky=ctk.W
        )
        self._oneeuro_cutoff_slider = ctk.CTkSlider(
            self, from_=0.1, to=10.0, number_of_steps=99,
            command=lambda v: setattr(self._config, "one_euro_min_cutoff", round(v, 2)),
        )
        self._oneeuro_cutoff_slider.set(self._config.one_euro_min_cutoff)
        self._oneeuro_cutoff_slider.grid(
            row=row, column=1, padx=(0, 12), pady=2, sticky="ew"
        )
        row += 1

        ctk.CTkLabel(self, text="  Beta:").grid(
            row=row, column=0, padx=24, sticky=ctk.W
        )
        self._oneeuro_beta_slider = ctk.CTkSlider(
            self, from_=0.001, to=1.0, number_of_steps=999,
            command=lambda v: setattr(self._config, "one_euro_beta", round(v, 3)),
        )
        self._oneeuro_beta_slider.set(self._config.one_euro_beta)
        self._oneeuro_beta_slider.grid(
            row=row, column=1, padx=(0, 12), pady=2, sticky="ew"
        )
        row += 1

        # --- Savitzky-Golay ---
        self._savgol_var = ctk.BooleanVar(value=self._config.use_savgol)
        self._savgol_cb = ctk.CTkCheckBox(
            self, text="Savitzky-Golay", variable=self._savgol_var,
        )
        self._savgol_cb.grid(row=row, column=0, padx=12, pady=(8, 2), sticky=ctk.W)
        row += 1

        ctk.CTkLabel(self, text="  Window Length:").grid(
            row=row, column=0, padx=24, sticky=ctk.W
        )
        self._savgol_window_slider = ctk.CTkSlider(
            self, from_=3, to=31, number_of_steps=14,
            command=lambda v: setattr(self._config, "savgol_window_length", int(v)),
        )
        self._savgol_window_slider.set(self._config.savgol_window_length)
        self._savgol_window_slider.grid(
            row=row, column=1, padx=(0, 12), pady=2, sticky="ew"
        )
        row += 1

        ctk.CTkLabel(self, text="  Polyorder:").grid(
            row=row, column=0, padx=24, sticky=ctk.W
        )
        self._savgol_poly_slider = ctk.CTkSlider(
            self, from_=1, to=5, number_of_steps=4,
            command=lambda v: setattr(self._config, "savgol_polyorder", int(v)),
        )
        self._savgol_poly_slider.set(self._config.savgol_polyorder)
        self._savgol_poly_slider.grid(
            row=row, column=1, padx=(0, 12), pady=2, sticky="ew"
        )
        row += 1

        # --- Action buttons ---
        btn_frame = ctk.CTkFrame(self)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=(16, 12))
        btn_frame.grid_columnconfigure(0, weight=1)
        btn_frame.grid_columnconfigure(1, weight=1)
        btn_frame.grid_columnconfigure(2, weight=1)

        ctk.CTkButton(
            btn_frame, text="Apply", command=self._apply,
        ).grid(row=0, column=0, padx=4)
        ctk.CTkButton(
            btn_frame, text="Reset", command=self._reset,
        ).grid(row=0, column=1, padx=4)
        ctk.CTkButton(
            btn_frame, text="Close", command=self.destroy,
        ).grid(row=0, column=2, padx=4)

    def _apply(self) -> None:
        self._config.use_outlier_removal = self._outlier_var.get()
        self._config.use_exponential_smoothing = self._exp_var.get()
        self._config.use_moving_average = self._ma_var.get()
        self._config.use_one_euro = self._oneeuro_var.get()
        self._config.use_savgol = self._savgol_var.get()
        self._on_apply()

    def _reset(self) -> None:
        self._on_reset()

    def run(self) -> None:
        self.wait_window()


class MainWindow(GUIAppBase):
    """VisionMoCap Studio main application window.

    Layout (top to bottom):

        1. Title bar
        2. Camera preview (left, expands) + Info panel (right, fixed)
        3. Toolbar
        4. Status bar

    The window runs a periodic ``after`` loop that polls the
    AppController for new frames and updates all widgets.
    """

    _POLL_INTERVAL_MS: int = 33  # ~30 fps

    def __init__(
        self,
        controller: Optional[AppController] = None,
    ) -> None:
        super().__init__(title="VisionMoCap Studio")
        self._controller = controller or AppController()
        self._update_job: Optional[str] = None
        self._last_status_update: float = 0.0
        self._last_recording_count: int = 0
        self._was_playing_before_scrub: bool = False

    # ------------------------------------------------------------------
    # GUIAppBase implementation
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Create the UI layout and register callbacks."""
        super().initialize()

        initial_theme = self._controller.theme
        ctk.set_appearance_mode(initial_theme)
        ctk.set_default_color_theme("dark-blue")

        self._window = ctk.CTk()
        self._window.title(self._title)
        self._window.geometry("1280x800")
        self._window.minsize(960, 600)

        # Grid layout
        self._window.grid_rowconfigure(1, weight=1)
        self._window.grid_columnconfigure(0, weight=1)

        # ---- Title ----
        title_label = ctk.CTkLabel(
            self._window,
            text="VisionMoCap Studio",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        title_label.grid(row=0, column=0, pady=(8, 4), sticky=ctk.N)

        # ---- Camera preview + Info panel ----
        center_frame = ctk.CTkFrame(self._window)
        center_frame.grid(row=1, column=0, padx=8, pady=4, sticky="nsew")
        center_frame.grid_rowconfigure(0, weight=1)
        center_frame.grid_columnconfigure(0, weight=1)

        self._camera_widget = CameraWidget(center_frame)
        self._camera_widget.grid(row=0, column=0, padx=(0, 4), sticky="nsew")

        self._info_panel = InfoPanel(center_frame)
        self._info_panel.grid(row=0, column=1, padx=(4, 0), pady=0, sticky="ns")

        # ---- Toolbar ----
        self._toolbar = Toolbar(
            self._window,
            on_start_camera=self._on_start_camera,
            on_stop_camera=self._on_stop_camera,
            on_record=self._on_record,
            on_pause=self._on_pause,
            on_load_recording=self._on_load_recording,
            on_play=self._on_play_playback,
            on_pause_playback=self._on_pause_playback,
            on_stop_playback=self._on_stop_playback,
            on_step_forward=self._on_step_forward,
            on_step_backward=self._on_step_backward,
            on_export=self._on_export,
            on_blender=self._on_send_to_blender,
            on_settings=self._on_settings,
            on_toggle_theme=self._on_toggle_theme,
            on_filters=self._on_filters,
            on_exit=self._on_exit,
        )
        self._toolbar.grid(row=2, column=0, padx=8, pady=(2, 4), sticky="ew")
        self._toolbar.set_theme(initial_theme)

        # ---- Timeline ----
        self._timeline = TimelineWidget(
            self._window,
            on_scrub=self._on_timeline_scrub,
            on_scrub_release=self._on_timeline_release,
        )
        self._timeline.grid(row=3, column=0, padx=8, pady=(0, 4), sticky="ew")

        # ---- Status bar ----
        self._status_bar = StatusBar(self._window)
        self._status_bar.grid(row=4, column=0, padx=8, pady=(0, 8), sticky="ew")

        # Wire the controller's status callback to the status bar flash.
        def _safe_flash(level: str, message: str):
            try:
                if self._window.winfo_exists():
                    self._status_bar.flash(message, level)
            except Exception:
                pass

        self._controller.on_status = _safe_flash

        self._logger.info("MainWindow initialised.")

    def run(self) -> None:
        """Start the update loop and enter the CustomTkinter event loop."""
        self._logger.info("MainWindow run loop started.")
        self._schedule_update()
        try:
            self._window.mainloop()
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        """Clean shutdown of the controller and window."""
        if self._update_job is not None:
            self._window.after_cancel(self._update_job)
            self._update_job = None
        try:
            self._controller.shutdown()
        except Exception:
            self._logger.exception("Error during controller shutdown.")
        try:
            self._window.destroy()
        except Exception:
            pass
        super().shutdown()
        self._logger.info("MainWindow shut down.")

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _on_start_camera(self) -> None:
        """Discover cameras and automatically open the first working one.

        ``discover_cameras()`` keeps the first working camera open.
        If no camera works, an error dialog is shown.
        """
        devices = self._controller.discover_cameras()
        if not devices:
            messagebox.showerror(
                "Camera Error",
                "No working camera detected.\n"
                "Please connect a webcam and restart VisionMoCap.",
            )
            self._logger.error("No cameras found.")
            return

        self._toolbar.set_camera_list(devices)

        device = self._controller.get_current_camera()
        if device is None:
            messagebox.showerror(
                "Camera Error",
                "No working camera detected.\n"
                "Please connect a webcam and restart VisionMoCap.",
            )
            self._logger.error("No working camera found.")
            return

        ok = self._controller.start_current_camera()
        if not ok:
            self._status_bar.flash("Failed to start camera pipeline.", "ERROR")
            return

        self._toolbar.set_camera_started()
        self._status_bar.set_camera_status(device.name)
        self._status_bar.set_camera_index(device.index)
        self._info_panel.set_device(device.name)
        self._info_panel.set_resolution(
            device.resolution_width, device.resolution_height
        )
        self._camera_widget.clear()
        self._last_status_update = time.monotonic()

    def _on_stop_camera(self) -> None:
        """Stop the camera and reset the UI."""
        self._controller.stop_camera()
        self._toolbar.set_camera_stopped()
        self._status_bar.set_camera_status("Off")
        self._status_bar.set_camera_index(-1)
        self._status_bar.set_recording_status(False)
        self._camera_widget.clear()
        self._info_panel.clear()

    def _on_record(self) -> None:
        """Toggle recording start / stop."""
        if self._controller.is_recording or self._controller.is_recording_paused:
            path = self._controller.stop_recording()
            self._toolbar.set_not_recording()
            self._status_bar.set_recording_status(False)
            self._info_panel.set_recording_indicator(False)
            if path is not None:
                self._status_bar.flash(
                    f"Saved to {path.name}", "INFO"
                )
                self._toolbar.enable_export()
        else:
            self._controller.start_recording()
            self._toolbar.set_recording()
            self._info_panel.set_recording_indicator(True)

    def _on_pause(self) -> None:
        """Toggle recording pause / resume."""
        if self._controller.is_recording_paused:
            self._controller.resume_recording()
            self._toolbar.set_resumed()
            self._info_panel.set_recording_indicator(True)
        elif self._controller.is_recording:
            self._controller.pause_recording()
            self._toolbar.set_paused()
            self._info_panel.set_recording_indicator(True, paused=True)

    # ------------------------------------------------------------------
    # Playback callbacks
    # ------------------------------------------------------------------

    def _on_load_recording(self) -> None:
        """Open a file dialog to load a recorded JSON and start playback."""
        from tkinter import filedialog

        path = filedialog.askopenfilename(
            title="Load Recording",
            filetypes=[("Recording files", "*.json")],
            defaultextension=".json",
        )
        if not path:
            return

        ok = self._controller.load_recording(path)
        if not ok:
            self._status_bar.flash("Failed to load recording.", "ERROR")
            return

        src_path = self._controller.playback_source_path
        src_name = src_path.name if src_path else Path(path).name
        self._toolbar.set_playback_loaded()
        self._toolbar.set_filters_enabled(True)
        self._status_bar.set_playback_status("Loaded")
        self._info_panel.set_playback_source(src_name)
        self._info_panel.set_playback_state("STOPPED")
        self._info_panel.set_playback_frame(0, self._controller.playback_total_frames)
        self._info_panel.set_playback_duration(self._controller.playback_duration)
        self._timeline.set_enabled(True)
        self._update_timeline_display()
        self._toolbar.enable_blender()
        self._status_bar.flash(f"Loaded {src_name}", "INFO")

    def _on_play_playback(self) -> None:
        """Start or restart playback."""
        if self._controller.is_playback_finished:
            self._controller.play_playback()
            self._toolbar.set_playback_playing()
            self._status_bar.set_playback_status("Playing")
            self._status_bar.flash("Playback started", "INFO")
        elif self._controller.is_playback_stopped:
            self._controller.play_playback()
            self._toolbar.set_playback_playing()
            self._status_bar.set_playback_status("Playing")
            self._status_bar.flash("Playback started", "INFO")

    def _on_pause_playback(self) -> None:
        """Toggle playback pause / resume."""
        if self._controller.is_playback_paused:
            self._controller.resume_playback()
            self._toolbar.set_playback_resumed()
            self._status_bar.set_playback_status("Playing")
            self._status_bar.flash("Playback resumed", "INFO")
        elif self._controller.is_playback_playing:
            self._controller.pause_playback()
            self._toolbar.set_playback_paused()
            self._status_bar.set_playback_status("Paused")
            self._status_bar.flash("Playback paused", "INFO")

    def _on_stop_playback(self) -> None:
        """Stop playback and reset to frame 0."""
        self._controller.stop_playback()
        self._toolbar.set_playback_stopped()
        self._status_bar.set_playback_status("Stopped")
        if self._controller.has_playback_sequence:
            self._info_panel.set_playback_frame(0, self._controller.playback_total_frames)
            self._info_panel.set_playback_state("STOPPED")
            self._update_timeline_display()
        else:
            self._timeline.reset()

    def _on_step_forward(self) -> None:
        """Step forward one frame during playback."""
        self._controller.step_playback_forward()
        self._controller.set_playback_paused()
        self._toolbar.set_playback_paused()
        self._status_bar.set_playback_status("Paused")

    def _on_step_backward(self) -> None:
        """Step backward one frame during playback."""
        self._controller.step_playback_backward()
        self._controller.set_playback_paused()
        self._toolbar.set_playback_paused()
        self._status_bar.set_playback_status("Paused")

    def _on_timeline_scrub(self, progress: float) -> None:
        """Called continuously while user drags the timeline slider.

        Only changes the displayed frame during drag.  The playback
        state is preserved and restored on release.

        Args:
            progress: Progress fraction (0.0 to 1.0).
        """
        was_playing = self._controller.is_playback_playing
        if was_playing:
            self._was_playing_before_scrub = True
            self._controller.pause_playback()

        self._controller.seek_to_progress(progress)
        self._update_timeline_display()

    def _on_timeline_release(self, progress: float) -> None:
        """Called when user releases the timeline slider.

        Restores the playback state that was active before scrubbing.

        Args:
            progress: Progress fraction (0.0 to 1.0).
        """
        if self._was_playing_before_scrub and self._controller.has_playback_sequence:
            self._controller.play_playback()
            self._toolbar.set_playback_playing()
            self._status_bar.set_playback_status("Playing")
        elif self._controller.has_playback_sequence:
            self._controller.set_playback_paused()
            self._toolbar.set_playback_paused()
            self._status_bar.set_playback_status("Paused")

        self._was_playing_before_scrub = False
        self._update_timeline_display()

    def _update_timeline_display(self) -> None:
        """Update the timeline widget with current playback position."""
        if not self._controller.has_playback_sequence:
            self._timeline.reset()
            return

        progress = self._controller.playback_progress
        current_frame = self._controller.playback_current_frame
        total_frames = self._controller.playback_total_frames
        duration = self._controller.playback_duration
        current_time = self._controller.current_time_seconds

        self._timeline.update_display(
            progress=progress,
            current_frame=current_frame,
            total_frames=total_frames,
            duration_seconds=duration,
            current_time=current_time,
        )

    def _on_export(self) -> None:
        """Trigger a file-save dialog for JSON recording or BVH animation."""
        from tkinter import filedialog

        has_playback = self._controller.has_playback_sequence

        filetypes = [("JSON recording", "*.json")]
        if has_playback:
            filetypes.extend([
                ("BVH animation", "*.bvh"),
                ("CSV landmarks", "*.csv"),
                ("NumPy binary", "*.npy"),
            ])
        filetypes.append(("All files", "*.*"))

        dest = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=filetypes,
            initialfile="recording.json",
        )
        if not dest:
            return

        ext = Path(dest).suffix.lower()
        dest_path = Path(dest)

        export_handlers = {
            ".bvh": (
                "BVH",
                self._controller.export_bvh if has_playback else None,
            ),
            ".csv": (
                "CSV",
                self._controller.export_csv if has_playback else None,
            ),
            ".npy": (
                "NPY",
                self._controller.export_npy if has_playback else None,
            ),
        }

        if ext in export_handlers:
            label, handler = export_handlers[ext]
            if handler is None:
                self._status_bar.flash(
                    "Load a recording first to export.", "WARNING"
                )
                return
            ok = handler(dest_path)
            if ok:
                self._status_bar.flash(
                    f"{label} exported to {dest_path.name}", "INFO"
                )
        elif ext == ".json":
            src = Path("exports/recordings")
            if not src.exists():
                self._status_bar.flash("No recordings to export.", "WARNING")
                return
            recordings = sorted(src.glob("recording_*.json"))
            if not recordings:
                self._status_bar.flash("No recordings to export.", "WARNING")
                return
            import shutil
            shutil.copy2(recordings[-1], dest)
            self._status_bar.flash(
                f"Exported to {dest_path.name}", "INFO"
            )

    def _on_send_to_blender(self) -> None:
        """Export the current playback sequence to Blender."""
        ok = self._controller.send_to_blender()
        if ok:
            self._status_bar.flash("Sent to Blender.", "INFO")
        else:
            self._status_bar.flash("Failed to send to Blender.", "ERROR")

    def _on_settings(self) -> None:
        """Open the settings dialog for camera, pose, and general config."""
        config = self._controller._config
        cameras = self._controller.discover_cameras() or []

        def on_apply(updated_config):
            was_camera_open = self._controller.is_camera_open
            old_device = self._controller.get_camera_index()
            new_device = updated_config.camera.device_id

            self._controller._config = updated_config
            if self._controller._cfg_mgr is not None:
                self._controller._cfg_mgr.save()

            theme = updated_config.gui.theme
            current_theme = ctk.get_appearance_mode().lower()
            if theme != current_theme:
                ctk.set_appearance_mode(theme)
                self._toolbar.set_theme(theme)
                mode_name = "Light" if theme == "light" else "Dark"
                self._status_bar.flash(f"Switched to {mode_name} Mode", "INFO")

            if was_camera_open and new_device != old_device:
                self._controller.stop_camera()
                self._toolbar.set_camera_stopped()
                self._status_bar.set_camera_status("Off")
                self._camera_widget.clear()
                self._info_panel.clear()
                self._status_bar.flash(
                    "Camera will restart on next use", "INFO"
                )

            self._status_bar.flash("Settings applied", "INFO")

        dialog = SettingsDialog(
            self._window,
            config=config,
            cameras=cameras,
            on_apply=on_apply,
        )
        dialog.run()

    def _on_toggle_theme(self) -> None:
        """Toggle between dark and light theme."""
        current = self._controller.theme
        new_theme = "light" if current == "dark" else "dark"
        self._controller.set_theme(new_theme)
        ctk.set_appearance_mode(new_theme)
        self._toolbar.set_theme(new_theme)
        mode_name = "Light" if new_theme == "light" else "Dark"
        self._status_bar.flash(f"Switched to {mode_name} Mode", "INFO")

    def _on_filters(self) -> None:
        """Open the filter configuration dialog."""
        if not self._controller.has_playback_sequence:
            return

        config = self._controller._config.motion
        dialog = FilterDialog(
            self._window,
            config=config,
            on_apply=lambda: self._controller.apply_filters(),
            on_reset=lambda: self._controller.reset_filters(),
        )
        dialog.run()

    def _on_exit(self) -> None:
        """Exit the application."""
        self._logger.info("Exit requested.")
        self.shutdown()
        sys.exit(0)

    # ------------------------------------------------------------------
    # Update loop
    # ------------------------------------------------------------------

    def _schedule_update(self) -> None:
        """Schedule the next frame poll."""
        self._update_job = self._window.after(
            self._POLL_INTERVAL_MS, self._update_loop
        )

    def _update_loop(self) -> None:
        """Consume frames and refresh all widgets.

        When playback is active, the camera preview shows the playback
        skeleton instead of the live feed.  The camera pipeline continues
        to run independently in the background.

        * Camera frames are drained from the queue (displayed only when
          playback is idle).
        * Playback frames are generated from PoseResult data via the
          PlaybackRenderer.
        * The status bar is refreshed at 1-second intervals.
        * Fatal errors from the worker thread trigger a dialog and an
          automatic camera stop.
        """
        now = time.monotonic()

        # --- Error check (always, before anything else) ---
        error = self._controller.pop_error()
        if error is not None:
            title, msg = error
            self._logger.error("Worker error: %s — %s", title, msg)
            messagebox.showerror(title, msg)
            self._on_stop_camera()
            self._schedule_update()
            return

        # --- Playback frame rendering ---
        pb_active = (
            self._controller.is_playback_playing
            or self._controller.is_playback_paused
            or self._controller.is_playback_finished
        )

        if pb_active:
            pb_frame = self._controller.get_playback_frame()
            if pb_frame is not None:
                self._camera_widget.update_frame(pb_frame)
            elif self._controller.is_playback_finished:
                pass  # keep the last rendered frame on display

            if self._controller.is_playback_finished:
                self._toolbar.set_playback_finished()
                self._status_bar.set_playback_status("Finished")
                self._info_panel.set_playback_state("FINISHED")

            # Update InfoPanel every frame during playback
            self._info_panel.set_playback_frame(
                self._controller.playback_current_frame,
                self._controller.playback_total_frames,
            )
            if self._controller.is_playback_playing:
                self._info_panel.set_playback_state("PLAYING")
            elif self._controller.is_playback_paused:
                self._info_panel.set_playback_state("PAUSED")
            elif self._controller.is_playback_finished:
                self._info_panel.set_playback_state("FINISHED")

            # Update timeline display every frame during playback
            if not self._timeline.is_dragging:
                self._update_timeline_display()

        else:
            # --- Camera frame consumption (non-blocking, drain to latest) ---
            latest_frame = None
            while self._controller.is_camera_open:
                f = self._controller.get_next_frame()
                if f is None:
                    break
                latest_frame = f

            if latest_frame is not None:
                self._camera_widget.update_frame(latest_frame)

            pose = self._controller.get_pose_result()

            if pose is not None:
                self._info_panel.set_pose_detected(pose.pose_detected)

            self._info_panel.set_frame_number(
                self._controller.get_frame_number()
            )

        # --- Info panel recording timer + frames (every frame) ---
        if self._controller.is_recording or self._controller.is_recording_paused:
            self._info_panel.set_recording_timer(
                self._controller.recording_elapsed
            )
            self._info_panel.set_recording_frames(
                self._controller.recorded_frame_count
            )

        # --- Status bar (1-second throttle) ---
        if now - self._last_status_update >= 1.0:
            self._last_status_update = now
            self._status_bar.set_fps(
                self._controller.get_average_fps()
            )
            self._status_bar.set_confidence(
                self._controller.get_tracking_confidence()
            )
            self._status_bar.set_camera_index(
                self._controller.get_camera_index()
            )
            rec = self._controller.is_recording
            if rec:
                self._last_recording_count = (
                    self._controller.recorded_frame_count
                )
            self._status_bar.set_recording_status(
                rec, self._last_recording_count
            )

        self._schedule_update()