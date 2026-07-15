"""Unit tests for the Blender integration module.

Tests the export / launch logic (which runs outside Blender).  The
add-on Python files are verified for basic syntax correctness but
cannot be executed because ``bpy`` is only available inside Blender.
"""

from __future__ import annotations

import ast
import tempfile
from pathlib import Path

from src.animation.animation_clip import AnimationClip
from src.animation.avatar import Avatar
from src.animation.bone import Bone
from src.blender.exporter import BlenderExporter
from src.config.manager import BlenderConfig
from src.core.models import Vector3D


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_ADDON_DIR = (
    Path(__file__).resolve().parent.parent.parent / "src" / "blender" / "addon"
)


def _make_avatar() -> Avatar:
    bones = [
        Bone(
            name="Hips", parent=None, children=["Spine"],
            head_position=Vector3D(0.0, 0.0, 0.0),
            tail_position=Vector3D(0.0, 0.1, 0.0),
        ),
        Bone(
            name="Spine", parent="Hips", children=[],
            head_position=Vector3D(0.0, 0.1, 0.0),
            tail_position=Vector3D(0.0, 0.5, 0.0),
        ),
    ]
    return Avatar(name="test", root_bone="Hips", bones=bones)


def _make_clip() -> AnimationClip:
    from src.animation.keyframe import InterpolationType, Keyframe
    from src.animation.retargeted_motion import BoneTransform

    identity = (1.0, 0.0, 0.0, 0.0)
    return AnimationClip(
        keyframes=[
            Keyframe(
                timestamp=0.0, frame_number=0,
                bone_transforms={
                    "Hips": BoneTransform(Vector3D(0.0, 0.0, 0.0), identity),
                    "Spine": BoneTransform(Vector3D(0.0, 0.1, 0.0), identity),
                },
                interpolation=InterpolationType.LINEAR,
            ),
        ],
        duration=1.0, fps=30.0,
    )


# ---------------------------------------------------------------------------
# Add-on syntax checks
# ---------------------------------------------------------------------------


class TestAddonSyntax:
    def test_addon_files_exist(self) -> None:
        assert _ADDON_DIR.exists()
        expected = {"__init__.py", "operators.py", "panels.py"}
        actual = {f.name for f in _ADDON_DIR.iterdir() if f.suffix == ".py"}
        assert expected.issubset(actual)

    def test_addon_files_parse(self) -> None:
        for py_file in sorted(_ADDON_DIR.rglob("*.py")):
            source = py_file.read_text(encoding="utf-8")
            ast.parse(source, filename=str(py_file))


# ---------------------------------------------------------------------------
# BlenderExporter tests
# ---------------------------------------------------------------------------


class TestBlenderExporter:
    def test_send_to_blender_writes_bvh(self) -> None:
        config = BlenderConfig(auto_launch=False)
        exporter = BlenderExporter(config)
        clip = _make_clip()
        avatar = _make_avatar()

        with tempfile.NamedTemporaryFile(suffix=".bvh", delete=False) as f:
            bvh_path = Path(f.name)

        try:
            result = exporter.send_to_blender(clip, avatar, bvh_path)
            assert result
            assert bvh_path.exists()
            assert bvh_path.stat().st_size > 0
        finally:
            bvh_path.unlink()

    def test_send_to_blender_temp_file(self) -> None:
        config = BlenderConfig(auto_launch=False)
        exporter = BlenderExporter(config)
        clip = _make_clip()
        avatar = _make_avatar()

        with tempfile.NamedTemporaryFile(suffix=".bvh", delete=False) as f:
            bvh_path = Path(f.name)
        try:
            result = exporter.send_to_blender(clip, avatar, bvh_path)
            assert result
            assert bvh_path.exists()
        finally:
            bvh_path.unlink()
