"""Settings dialog for configuring camera, pose detection, and general
application parameters.  Integrates with the existing ConfigManager
and AppController to read/write persistent settings.

Layout is tabbed: Camera | Pose | General.
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

import customtkinter as ctk

from src.camera.device import CameraDevice
from src.config.manager import RESOLUTION_PRESETS, AppConfig


class SettingsDialog(ctk.CTkToplevel):
    """Modal settings dialog with three tabs.

    Camera tab:
        Device selection, resolution preset, backend, target FPS.

    Pose tab:
        Model complexity, minimum detection confidence,
        minimum tracking confidence.

    General tab:
        GUI theme, logging level.
    """

    def __init__(
        self,
        master: ctk.BaseWidget,
        config: AppConfig,
        cameras: list[CameraDevice],
        on_apply: Callable[[AppConfig], None],
    ) -> None:
        super().__init__(master)
        self._config = config
        self._cameras = cameras
        self._on_apply = on_apply
        self._logger = logging.getLogger(self.__class__.__name__)

        self.title("Settings")
        self.geometry("520x480")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        # Copy so changes are isolated until Apply
        import copy
        self._working_config: AppConfig = copy.deepcopy(config)

        self._build_ui()

    def _build_ui(self) -> None:
        self._tabview = ctk.CTkTabview(self)
        self._tabview.pack(fill=ctk.BOTH, expand=True, padx=12, pady=(12, 0))

        self._tab_camera = self._tabview.add("Camera")
        self._tab_pose = self._tabview.add("Pose Detection")
        self._tab_general = self._tabview.add("General")

        self._build_camera_tab()
        self._build_pose_tab()
        self._build_general_tab()

        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(fill=ctk.X, padx=12, pady=(8, 12))
        btn_frame.grid_columnconfigure(0, weight=1)
        btn_frame.grid_columnconfigure(1, weight=1)
        btn_frame.grid_columnconfigure(2, weight=1)

        ctk.CTkButton(
            btn_frame, text="Apply", command=self._apply,
        ).grid(row=0, column=0, padx=4)
        ctk.CTkButton(
            btn_frame, text="Cancel", command=self.destroy,
        ).grid(row=0, column=1, padx=4)

    # ------------------------------------------------------------------
    # Camera tab
    # ------------------------------------------------------------------

    def _build_camera_tab(self) -> None:
        cfg = self._working_config.camera
        row = 0

        ctk.CTkLabel(self._tab_camera, text="Device:").grid(
            row=row, column=0, padx=12, pady=(12, 2), sticky=ctk.W
        )
        self._device_var = ctk.StringVar(
            value=str(cfg.device_id)
        )
        device_options = [str(d.index) for d in self._cameras] if self._cameras else ["0"]
        self._device_combo = ctk.CTkComboBox(
            self._tab_camera, values=device_options, variable=self._device_var,
            state="readonly",
        )
        self._device_combo.grid(row=row, column=1, padx=(0, 12), pady=(12, 2), sticky="ew")
        row += 1

        device_names = [d.name for d in self._cameras] if self._cameras else []
        if device_names:
            name_text = device_names[int(self._device_var.get())] if self._cameras else ""
            self._device_name_label = ctk.CTkLabel(
                self._tab_camera, text=name_text, font=ctk.CTkFont(size=11),
            )
            self._device_name_label.grid(
                row=row, column=1, padx=(0, 12), pady=(0, 4), sticky=ctk.W
            )
            self._device_combo.configure(
                command=self._on_device_change
            )
            row += 1
        else:
            self._device_name_label = None

        ctk.CTkLabel(self._tab_camera, text="Resolution:").grid(
            row=row, column=0, padx=12, pady=2, sticky=ctk.W
        )
        self._resolution_var = ctk.StringVar(value=cfg.resolution_preset)
        self._resolution_combo = ctk.CTkComboBox(
            self._tab_camera,
            values=list(RESOLUTION_PRESETS.keys()),
            variable=self._resolution_var,
            state="readonly",
        )
        self._resolution_combo.grid(row=row, column=1, padx=(0, 12), pady=2, sticky="ew")
        row += 1

        ctk.CTkLabel(self._tab_camera, text="Backend:").grid(
            row=row, column=0, padx=12, pady=2, sticky=ctk.W
        )
        backends = ["directshow", "msmf"]
        self._backend_var = ctk.StringVar(value=cfg.backend)
        self._backend_combo = ctk.CTkComboBox(
            self._tab_camera, values=backends, variable=self._backend_var,
            state="readonly",
        )
        self._backend_combo.grid(row=row, column=1, padx=(0, 12), pady=2, sticky="ew")
        row += 1

        ctk.CTkLabel(self._tab_camera, text="Target FPS:").grid(
            row=row, column=0, padx=12, pady=2, sticky=ctk.W
        )
        self._fps_slider = ctk.CTkSlider(
            self._tab_camera, from_=15, to=60, number_of_steps=45,
            command=self._on_fps_change,
        )
        self._fps_slider.set(cfg.fps)
        self._fps_slider.grid(row=row, column=1, padx=(0, 12), pady=2, sticky="ew")
        self._fps_label = ctk.CTkLabel(
            self._tab_camera, text=f"{int(cfg.fps)} FPS",
            font=ctk.CTkFont(size=11),
        )
        self._fps_label.grid(row=row, column=2, padx=(0, 12), pady=2, sticky=ctk.W)
        row += 1

        self._tab_camera.grid_columnconfigure(1, weight=1)

    def _on_device_change(self, choice: str) -> None:
        if self._device_name_label is not None and self._cameras:
            idx = int(choice)
            if 0 <= idx < len(self._cameras):
                self._device_name_label.configure(
                    text=self._cameras[idx].name
                )

    def _on_fps_change(self, value: float) -> None:
        self._fps_label.configure(text=f"{int(value)} FPS")

    # ------------------------------------------------------------------
    # Pose tab
    # ------------------------------------------------------------------

    def _build_pose_tab(self) -> None:
        cfg = self._working_config.pose
        row = 0

        ctk.CTkLabel(self._tab_pose, text="Model Complexity:").grid(
            row=row, column=0, padx=12, pady=(12, 2), sticky=ctk.W
        )
        complexity_map = {"Lite (0)": 0, "Full (1)": 1, "Heavy (2)": 2}
        rev_map = {v: k for k, v in complexity_map.items()}
        self._complexity_var = ctk.StringVar(value=rev_map.get(cfg.model_complexity, "Full (1)"))
        self._complexity_combo = ctk.CTkComboBox(
            self._tab_pose,
            values=list(complexity_map.keys()),
            variable=self._complexity_var,
            state="readonly",
        )
        self._complexity_combo.grid(row=row, column=1, padx=(0, 12), pady=(12, 2), sticky="ew")
        ctk.CTkLabel(
            self._tab_pose,
            text="Lite=faster · Heavy=more accurate",
            font=ctk.CTkFont(size=10),
            text_color="grey",
        ).grid(row=row + 1, column=0, columnspan=2, padx=24, pady=(0, 4), sticky=ctk.W)
        row += 2

        ctk.CTkLabel(self._tab_pose, text="Detection Confidence:").grid(
            row=row, column=0, padx=12, pady=2, sticky=ctk.W
        )
        self._det_conf_slider = ctk.CTkSlider(
            self._tab_pose, from_=0.1, to=1.0, number_of_steps=90,
            command=self._on_det_conf_change,
        )
        self._det_conf_slider.set(cfg.min_detection_confidence)
        self._det_conf_slider.grid(row=row, column=1, padx=(0, 12), pady=2, sticky="ew")
        self._det_conf_label = ctk.CTkLabel(
            self._tab_pose, text=f"{cfg.min_detection_confidence:.2f}",
            font=ctk.CTkFont(size=11),
        )
        self._det_conf_label.grid(row=row, column=2, padx=(0, 12), pady=2, sticky=ctk.W)
        row += 1

        ctk.CTkLabel(self._tab_pose, text="Tracking Confidence:").grid(
            row=row, column=0, padx=12, pady=2, sticky=ctk.W
        )
        self._trk_conf_slider = ctk.CTkSlider(
            self._tab_pose, from_=0.1, to=1.0, number_of_steps=90,
            command=self._on_trk_conf_change,
        )
        self._trk_conf_slider.set(cfg.min_tracking_confidence)
        self._trk_conf_slider.grid(row=row, column=1, padx=(0, 12), pady=2, sticky="ew")
        self._trk_conf_label = ctk.CTkLabel(
            self._tab_pose, text=f"{cfg.min_tracking_confidence:.2f}",
            font=ctk.CTkFont(size=11),
        )
        self._trk_conf_label.grid(row=row, column=2, padx=(0, 12), pady=2, sticky=ctk.W)
        row += 1

        self._tab_pose.grid_columnconfigure(1, weight=1)

    def _on_det_conf_change(self, value: float) -> None:
        self._det_conf_label.configure(text=f"{value:.2f}")

    def _on_trk_conf_change(self, value: float) -> None:
        self._trk_conf_label.configure(text=f"{value:.2f}")

    # ------------------------------------------------------------------
    # General tab
    # ------------------------------------------------------------------

    def _build_general_tab(self) -> None:
        cfg = self._working_config
        row = 0

        ctk.CTkLabel(self._tab_general, text="GUI Theme:").grid(
            row=row, column=0, padx=12, pady=(12, 2), sticky=ctk.W
        )
        self._theme_var = ctk.StringVar(value=cfg.gui.theme)
        self._theme_combo = ctk.CTkComboBox(
            self._tab_general,
            values=["dark", "light"],
            variable=self._theme_var,
            state="readonly",
        )
        self._theme_combo.grid(row=row, column=1, padx=(0, 12), pady=(12, 2), sticky="ew")
        row += 1

        ctk.CTkLabel(self._tab_general, text="Logging Level:").grid(
            row=row, column=0, padx=12, pady=2, sticky=ctk.W
        )
        self._log_level_var = ctk.StringVar(value=cfg.logging.level)
        self._log_level_combo = ctk.CTkComboBox(
            self._tab_general,
            values=["DEBUG", "INFO", "WARNING", "ERROR"],
            variable=self._log_level_var,
            state="readonly",
        )
        self._log_level_combo.grid(row=row, column=1, padx=(0, 12), pady=2, sticky="ew")
        row += 1

        self._tab_general.grid_columnconfigure(1, weight=1)

    # ------------------------------------------------------------------
    # Apply
    # ------------------------------------------------------------------

    def _apply(self) -> None:
        cfg = self._working_config

        # Camera
        cfg.camera.device_id = int(self._device_var.get())
        cfg.camera.resolution_preset = self._resolution_var.get()
        w, h = RESOLUTION_PRESETS.get(cfg.camera.resolution_preset, (640, 480))
        cfg.camera.width = w
        cfg.camera.height = h
        backend_val = self._backend_var.get()
        cfg.camera.backend = "msmf" if backend_val == "msmf" else "directshow"
        cfg.camera.fps = float(int(self._fps_slider.get()))

        # Pose
        complexity_map = {"Lite (0)": 0, "Full (1)": 1, "Heavy (2)": 2}
        cfg.pose.model_complexity = complexity_map.get(self._complexity_var.get(), 1)
        cfg.pose.min_detection_confidence = round(self._det_conf_slider.get(), 2)
        cfg.pose.min_tracking_confidence = round(self._trk_conf_slider.get(), 2)

        # General
        cfg.gui.theme = self._theme_var.get()
        cfg.logging.level = self._log_level_var.get()

        self._on_apply(cfg)
        self._logger.info("Settings applied.")
        self.destroy()

    def run(self) -> None:
        self.wait_window()
