"""BlenderExporter — launch Blender with the VisionMoCap add-on.

On the VisionMoCap side, this class:
1. Exports a temporary BVH file from the current playback sequence.
2. Locates the Blender executable (from config).
3. Launches Blender with the add-on enabled and the BVH pre-loaded.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from src.animation.animation_clip import AnimationClip
from src.animation.avatar import Avatar
from src.animation.bvh_exporter import BvhExporter
from src.config.manager import BlenderConfig


class BlenderExporter:
    """Bridge from VisionMoCap to Blender.

    Writes a temporary BVH file and launches Blender with the
    VisionMoCap add-on so the user can import and bake the animation.
    """

    def __init__(self, config: BlenderConfig) -> None:
        self._config = config

    @property
    def config(self) -> BlenderConfig:
        return self._config

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
            True if Blender was launched successfully (or if *auto_launch*
            is disabled but the BVH was written).
        """
        if bvh_path is None:
            tmp = tempfile.NamedTemporaryFile(suffix=".bvh", delete=False)
            bvh_path = Path(tmp.name)
            tmp.close()

        exporter = BvhExporter(avatar, clip)
        exporter.export(bvh_path)

        if not self._config.auto_launch:
            return True

        return self._launch_blender(bvh_path)

    def _launch_blender(self, bvh_path: Path) -> bool:
        """Launch Blender with the add-on and BVH file."""
        executable = self._config.blender_executable or "blender"
        addon_dir = Path(__file__).resolve().parent / "addon"

        cmd = [
            executable,
            "--python-expr",
            f"import bpy; bpy.ops.preferences.addon_install(filepath=r'{addon_dir}'); "
            f"bpy.ops.preferences.addon_enable(module='visionmocap_addon')",
            "--addon",
            str(addon_dir),
        ]

        if self._config.script_path:
            cmd.extend(["--python", self._config.script_path])

        try:
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except FileNotFoundError:
            return False
        except OSError:
            return False
