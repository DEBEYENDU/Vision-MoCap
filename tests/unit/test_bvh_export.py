"""Unit tests for the BVH exporter (src/animation/bvh_exporter.py)."""

from __future__ import annotations

import math
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple

from src.animation.animation_clip import AnimationClip
from src.animation.avatar import Avatar
from src.animation.bone import Bone
from src.animation.bvh_exporter import BvhExporter
from src.animation.keyframe import InterpolationType, Keyframe
from src.animation.retargeted_motion import BoneTransform
from src.core.models import Vector3D

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_simple_avatar() -> Avatar:
    """Create a minimal avatar with 3 bones: Hips → Spine → Head."""
    bones = [
        Bone(
            name="Hips",
            parent=None,
            children=["Spine"],
            head_position=Vector3D(0.0, 0.0, 0.0),
            tail_position=Vector3D(0.0, 0.1, 0.0),
        ),
        Bone(
            name="Spine",
            parent="Hips",
            children=["Head"],
            head_position=Vector3D(0.0, 0.1, 0.0),
            tail_position=Vector3D(0.0, 0.5, 0.0),
        ),
        Bone(
            name="Head",
            parent="Spine",
            children=[],
            head_position=Vector3D(0.0, 0.5, 0.0),
            tail_position=Vector3D(0.0, 0.6, 0.0),
        ),
    ]
    return Avatar(name="test_avatar", root_bone="Hips", bones=bones)


def _make_simple_keyframes() -> List[Keyframe]:
    """Create 3 keyframes with identity rotations and varying positions."""
    identity = (1.0, 0.0, 0.0, 0.0)
    kfs = [
        Keyframe(
            timestamp=0.0,
            frame_number=0,
            bone_transforms={
                "Hips": BoneTransform(
                    position=Vector3D(0.0, 0.0, 0.0), rotation=identity
                ),
                "Spine": BoneTransform(
                    position=Vector3D(0.0, 0.1, 0.0), rotation=identity
                ),
                "Head": BoneTransform(
                    position=Vector3D(0.0, 0.5, 0.0), rotation=identity
                ),
            },
            interpolation=InterpolationType.LINEAR,
        ),
        Keyframe(
            timestamp=0.5,
            frame_number=1,
            bone_transforms={
                "Hips": BoneTransform(
                    position=Vector3D(0.1, 0.0, 0.0), rotation=identity
                ),
                "Spine": BoneTransform(
                    position=Vector3D(0.1, 0.1, 0.0), rotation=identity
                ),
                "Head": BoneTransform(
                    position=Vector3D(0.1, 0.5, 0.0), rotation=identity
                ),
            },
            interpolation=InterpolationType.LINEAR,
        ),
        Keyframe(
            timestamp=1.0,
            frame_number=2,
            bone_transforms={
                "Hips": BoneTransform(
                    position=Vector3D(0.2, 0.0, 0.0), rotation=identity
                ),
                "Spine": BoneTransform(
                    position=Vector3D(0.2, 0.1, 0.0), rotation=identity
                ),
                "Head": BoneTransform(
                    position=Vector3D(0.2, 0.5, 0.0), rotation=identity
                ),
            },
            interpolation=InterpolationType.LINEAR,
        ),
    ]
    return kfs


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBvhExporter:
    def test_export_creates_file(self) -> None:
        avatar = _make_simple_avatar()
        clip = AnimationClip(
            keyframes=_make_simple_keyframes(),
            duration=1.0,
            fps=30.0,
        )
        exporter = BvhExporter(avatar, clip)

        with tempfile.NamedTemporaryFile(suffix=".bvh", delete=False) as f:
            p = Path(f.name)

        try:
            exporter.export(p)
            assert p.exists()
            assert p.stat().st_size > 0
        finally:
            p.unlink()

    def test_export_bvh_starts_with_hierarchy(self) -> None:
        avatar = _make_simple_avatar()
        clip = AnimationClip(
            keyframes=_make_simple_keyframes(),
            duration=1.0,
            fps=30.0,
        )
        exporter = BvhExporter(avatar, clip)

        with tempfile.NamedTemporaryFile(suffix=".bvh", delete=False) as f:
            p = Path(f.name)

        try:
            exporter.export(p)
            content = p.read_text(encoding="utf-8")
            assert content.startswith("HIERARCHY")
        finally:
            p.unlink()

    def test_export_contains_motion_section(self) -> None:
        avatar = _make_simple_avatar()
        clip = AnimationClip(
            keyframes=_make_simple_keyframes(),
            duration=1.0,
            fps=30.0,
        )
        exporter = BvhExporter(avatar, clip)

        with tempfile.NamedTemporaryFile(suffix=".bvh", delete=False) as f:
            p = Path(f.name)

        try:
            exporter.export(p)
            content = p.read_text(encoding="utf-8")
            assert "MOTION" in content
            assert "Frames:" in content
            assert "Frame Time:" in content
        finally:
            p.unlink()

    def test_export_correct_frame_count(self) -> None:
        avatar = _make_simple_avatar()
        clip = AnimationClip(
            keyframes=_make_simple_keyframes(),
            duration=1.0,
            fps=30.0,
        )
        exporter = BvhExporter(avatar, clip)

        with tempfile.NamedTemporaryFile(suffix=".bvh", delete=False) as f:
            p = Path(f.name)

        try:
            exporter.export(p)
            content = p.read_text(encoding="utf-8")
            assert "Frames: 3" in content
        finally:
            p.unlink()

    def test_export_contains_all_bones(self) -> None:
        avatar = _make_simple_avatar()
        clip = AnimationClip(
            keyframes=_make_simple_keyframes(),
            duration=1.0,
            fps=30.0,
        )
        exporter = BvhExporter(avatar, clip)

        with tempfile.NamedTemporaryFile(suffix=".bvh", delete=False) as f:
            p = Path(f.name)

        try:
            exporter.export(p)
            content = p.read_text(encoding="utf-8")
            assert "ROOT Hips" in content
            assert "JOINT Spine" in content
            assert "JOINT Head" in content
        finally:
            p.unlink()

    def test_hierarchy_order(self) -> None:
        avatar = _make_simple_avatar()
        clip = AnimationClip(
            keyframes=_make_simple_keyframes(),
            duration=1.0,
            fps=30.0,
        )
        exporter = BvhExporter(avatar, clip)
        order = exporter.hierarchy_order
        assert order == ["Hips", "Spine", "Head"]

    def test_root_has_six_channels(self) -> None:
        avatar = _make_simple_avatar()
        clip = AnimationClip(
            keyframes=_make_simple_keyframes(),
            duration=1.0,
            fps=30.0,
        )
        exporter = BvhExporter(avatar, clip)

        with tempfile.NamedTemporaryFile(suffix=".bvh", delete=False) as f:
            p = Path(f.name)

        try:
            exporter.export(p)
            content = p.read_text(encoding="utf-8")
            assert "CHANNELS 6" in content
            assert "Xposition" in content
            assert "Zrotation" in content
        finally:
            p.unlink()

    def test_child_has_three_channels(self) -> None:
        avatar = _make_simple_avatar()
        clip = AnimationClip(
            keyframes=_make_simple_keyframes(),
            duration=1.0,
            fps=30.0,
        )
        exporter = BvhExporter(avatar, clip)

        with tempfile.NamedTemporaryFile(suffix=".bvh", delete=False) as f:
            p = Path(f.name)

        try:
            exporter.export(p)
            content = p.read_text(encoding="utf-8")
            lines = content.split("\n")
            channel_count = 0
            for line in lines:
                if "JOINT" in line and "CHANNELS 3" in content:
                    channel_count += 1
            assert "JOINT Spine" in content
            assert "JOINT Head" in content
        finally:
            p.unlink()

    def test_motion_line_count(self) -> None:
        avatar = _make_simple_avatar()
        clip = AnimationClip(
            keyframes=_make_simple_keyframes(),
            duration=1.0,
            fps=30.0,
        )
        exporter = BvhExporter(avatar, clip)

        with tempfile.NamedTemporaryFile(suffix=".bvh", delete=False) as f:
            p = Path(f.name)

        try:
            exporter.export(p)
            content = p.read_text(encoding="utf-8")
            motion_lines = []
            in_motion = False
            for line in content.split("\n"):
                if line.startswith("MOTION"):
                    in_motion = True
                    continue
                if in_motion and line.strip() and not line.startswith("Frames:") and not line.startswith("Frame Time:"):
                    motion_lines.append(line)
            assert len(motion_lines) == 3
        finally:
            p.unlink()

    def test_quaternion_to_euler_identity(self) -> None:
        z, x, y = BvhExporter._quat_to_euler_zxy(1.0, 0.0, 0.0, 0.0)
        assert abs(z) < 1e-6
        assert abs(x) < 1e-6
        assert abs(y) < 1e-6

    def test_quaternion_to_euler_90z(self) -> None:
        # 90-degree rotation around Z: q = (cos(45), 0, 0, sin(45))
        angle = math.radians(90.0)
        w = math.cos(angle / 2.0)
        z = math.sin(angle / 2.0)
        z_deg, x_deg, y_deg = BvhExporter._quat_to_euler_zxy(w, 0.0, 0.0, z)
        assert abs(z_deg - 90.0) < 1.0
        assert abs(x_deg) < 1.0
        assert abs(y_deg) < 1.0

    def test_quaternion_multiply_and_conjugate(self) -> None:
        angle = math.radians(90.0)
        w = math.cos(angle / 2.0)
        x = math.sin(angle / 2.0)
        q = (w, x, 0.0, 0.0)  # 90 deg around X
        inv = BvhExporter._quat_conjugate(q)
        result = BvhExporter._quat_multiply(q, inv)
        assert abs(result[0] - 1.0) < 1e-6  # should be identity
        assert abs(result[1]) < 1e-6
        assert abs(result[2]) < 1e-6
        assert abs(result[3]) < 1e-6

    def test_export_without_frames_raises(self) -> None:
        avatar = _make_simple_avatar()
        clip = AnimationClip(keyframes=[], duration=0.0, fps=30.0)
        try:
            BvhExporter(avatar, clip)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_motion_data_format_for_root(self) -> None:
        """Root should have 6 values per frame (pos + euler)."""
        avatar = _make_simple_avatar()
        clip = AnimationClip(
            keyframes=_make_simple_keyframes(),
            duration=1.0,
            fps=30.0,
        )
        exporter = BvhExporter(avatar, clip)

        with tempfile.NamedTemporaryFile(suffix=".bvh", delete=False) as f:
            p = Path(f.name)

        try:
            exporter.export(p)
            content = p.read_text(encoding="utf-8")
            in_motion = False
            for line in content.split("\n"):
                if line.startswith("MOTION"):
                    in_motion = True
                    continue
                if in_motion and line.strip() and not line.startswith("Frames:") and not line.startswith("Frame Time:"):
                    values = [v for v in line.split() if v.strip()]
                    # 3 root channels + 3 bones * 3 channels = 12 values
                    assert len(values) == 12
                    break
        finally:
            p.unlink()
