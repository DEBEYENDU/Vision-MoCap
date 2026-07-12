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
from typing import Optional

import customtkinter as ctk

from src.gui.app_controller import AppController
from src.gui.base import GUIAppBase
from src.gui.camera_widget import CameraWidget
from src.gui.status_bar import StatusBar
from src.gui.toolbar import Toolbar


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

        self.grid_rowconfigure(8, weight=1)

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

    # ------------------------------------------------------------------
    # GUIAppBase implementation
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Create the UI layout and register callbacks."""
        super().initialize()

        ctk.set_appearance_mode("dark")
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
            on_export=self._on_export,
            on_settings=self._on_settings,
            on_exit=self._on_exit,
        )
        self._toolbar.grid(row=2, column=0, padx=8, pady=(2, 4), sticky="ew")

        # ---- Status bar ----
        self._status_bar = StatusBar(self._window)
        self._status_bar.grid(row=3, column=0, padx=8, pady=(0, 8), sticky="ew")

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
        """Discover cameras and open the first available one."""
        devices = self._controller.discover_cameras()
        if not devices:
            messagebox.showerror(
                "Camera Error",
                "No cameras found.  Please connect a camera and try again.",
            )
            self._logger.error("No cameras found.")
            return

        index = devices[0].index
        ok = self._controller.start_camera(index)
        if not ok:
            self._status_bar.flash("Failed to start camera.", "ERROR")
            return

        device = self._controller.get_current_camera()
        name = device.name if device else f"Camera {index}"
        self._toolbar.set_camera_started()
        self._status_bar.set_camera_status(name)
        self._status_bar.set_camera_index(index)

        if device:
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

    def _on_export(self) -> None:
        """Trigger a file-save dialog for the last recording."""
        from tkinter import filedialog

        src = Path("exports/recordings")
        if not src.exists():
            self._status_bar.flash("No recordings to export.", "WARNING")
            return

        recordings = sorted(src.glob("recording_*.json"))
        if not recordings:
            self._status_bar.flash("No recordings to export.", "WARNING")
            return

        latest = recordings[-1]
        dest = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile=latest.name,
        )
        if dest:
            import shutil

            shutil.copy2(latest, dest)
            self._status_bar.flash(
                f"Exported to {Path(dest).name}", "INFO"
            )

    def _on_settings(self) -> None:
        """Show a placeholder settings dialog."""
        ctk.CTkInputDialog(
            title="Settings",
            text="Settings dialog (coming soon)",
        )

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
        """Consume frames from the worker thread and refresh widgets.

        * Frames are drained from the queue — only the latest frame is
          displayed (older frames are dropped).
        * The status bar is refreshed at 1-second intervals.
        * Fatal errors from the worker thread trigger a dialog and an
          automatic camera stop.
        """
        now = time.monotonic()

        # --- Frame consumption (non-blocking, drain to latest) ---
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

        # --- Error check ---
        error = self._controller.pop_error()
        if error is not None:
            title, msg = error
            self._logger.error("Worker error: %s — %s", title, msg)
            messagebox.showerror(title, msg)
            self._on_stop_camera()
            self._schedule_update()
            return

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

        # --- Info panel recording timer + frames (every frame) ---
        if self._controller.is_recording or self._controller.is_recording_paused:
            self._info_panel.set_recording_timer(
                self._controller.recording_elapsed
            )
            self._info_panel.set_recording_frames(
                self._controller.recorded_frame_count
            )

        self._schedule_update()