"""BlenderExporter — launch Blender with the VisionMoCap add-on.

On the VisionMoCap side, this class:
1. Exports a temporary BVH file from the current playback sequence.
2. Locates the Blender executable (from config).
3. Launches Blender with the add-on enabled and the BVH pre-loaded.

Failures are reported precisely: missing executables, unreadable
paths, and export errors all surface through typed messages instead
of silent ``False`` returns.
"""

from __future__ import annotations

import logging
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional

from src.animation.animation_clip import AnimationClip
from src.animation.avatar import Avatar
from src.animation.bvh_exporter import BvhExporter
from src.config.manager import BlenderConfig

_TEMP_BVH_STALE_SECONDS = 24 * 60 * 60  # temp BVH files older than 1 day


class BlenderExporter:
    """Bridge from VisionMoCap to Blender.

    Writes a temporary BVH file and launches Blender with the
    VisionMoCap add-on so the user can import and bake the animation.
    """

    def __init__(self, config: BlenderConfig) -> None:
        self._config = config
        self._logger = logging.getLogger(self.__class__.__name__)
        self._last_error: Optional[str] = None
        self._temp_bvh_path: Optional[Path] = None

    @property
    def config(self) -> BlenderConfig:
        return self._config

    @property
    def last_error(self) -> Optional[str]:
        """Human-readable description of the last failure, if any."""
        return self._last_error

    def send_to_blender(
        self,
        clip: AnimationClip,
        avatar: Avatar,
        bvh_path: Optional[Path] = None,
    ) -> bool:
        """Export *clip* as BVH and launch Blender with the add-on.

        Args:
            clip: The animation clip to export.
            avatar: The avatar skeleton to export.
            bvh_path: Optional explicit path; if omitted a temp file is used.

        Returns:
            True if the BVH was written and (when *auto_launch* is
            enabled) Blender was launched successfully, False otherwise.
            On failure, :attr:`last_error` carries the reason.
        """
        self._last_error = None

        if bvh_path is None:
            self._cleanup_stale_temp_files()
            tmp_dir = Path(tempfile.gettempdir())
            bvh_path = tmp_dir / f"visionmocap_{int(time.time())}.bvh"
            self._temp_bvh_path = bvh_path

        try:
            exporter = BvhExporter(avatar, clip)
            exporter.export(bvh_path)
        except Exception as e:
            self._last_error = f"BVH export failed: {e}"
            self._logger.error("%s", self._last_error)
            return False

        self._logger.info(
            "BVH written to %s (%d frames).",
            bvh_path.name, len(clip.keyframes),
        )

        if not self._config.auto_launch:
            return True

        return self._launch_blender(bvh_path)

    def cleanup_temp_bvh(self) -> None:
        """Remove the temporary BVH written by the last export (if any)."""
        if self._temp_bvh_path is not None:
            try:
                self._temp_bvh_path.unlink(missing_ok=True)
            except OSError as e:
                self._logger.warning(
                    "Failed to remove temp BVH %s: %s",
                    self._temp_bvh_path, e,
                )
            self._temp_bvh_path = None

    def _launch_blender(self, bvh_path: Path) -> bool:
        """Launch Blender with the add-on and BVH file.

        Returns:
            True on successful launch, False otherwise (reason in
            :attr:`last_error`).
        """
        executable = self._config.blender_executable or "blender"
        addon_dir = Path(__file__).resolve().parent / "addon"

        if not addon_dir.is_dir():
            self._last_error = (
                f"VisionMoCap Blender add-on not found at {addon_dir}."
            )
            self._logger.error("%s", self._last_error)
            return False

        cmd = [
            executable,
            "--python-expr",
            f"import bpy; bpy.ops.preferences.addon_install(filepath=r'{addon_dir}'); "
            f"bpy.ops.preferences.addon_enable(module='visionmocap_addon')",
            "--addon",
            str(addon_dir),
        ]

        if self._config.script_path:
            script = Path(self._config.script_path)
            if not script.is_file():
                self._last_error = (
                    f"Blender script not found: {script}"
                )
                self._logger.error("%s", self._last_error)
                return False
            cmd.extend(["--python", self._config.script_path])

        try:
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            self._last_error = (
                f"Blender executable not found: '{executable}'. "
                "Install Blender or set the correct path in Settings."
            )
            self._logger.error("%s", self._last_error)
            return False
        except OSError as e:
            self._last_error = (
                f"Failed to launch Blender ('{executable}'): {e}"
            )
            self._logger.error("%s", self._last_error)
            return False

        self._logger.info(
            "Blender launched (add-on: visionmocap_addon, BVH: %s).",
            bvh_path.name,
        )
        return True

    @staticmethod
    def _cleanup_stale_temp_files() -> None:
        """Remove leftover VisionMoCap temp BVH files older than one day."""
        tmp_dir = Path(tempfile.gettempdir())
        try:
            for stale in tmp_dir.glob("visionmocap_*.bvh"):
                try:
                    if time.time() - stale.stat().st_mtime > _TEMP_BVH_STALE_SECONDS:
                        stale.unlink(missing_ok=True)
                except OSError:
                    continue
        except OSError:
            pass