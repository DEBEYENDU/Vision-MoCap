"""Unit tests for the Blender bridge (src/blender/exporter.py).

Popen is mocked so tests never launch a real process.
"""

from __future__ import annotations

import subprocess
import tempfile
import time
from pathlib import Path

import pytest

from src.animation.animation_clip import AnimationClip
from src.animation.avatar import Avatar
from src.animation.bone import Bone
from src.animation.bvh_exporter import BvhExporter
from src.animation.keyframe import InterpolationType, Keyframe
from src.animation.retargeted_motion import BoneTransform
from src.blender.exporter import BlenderExporter
from src.config.manager import BlenderConfig
from src.core.models import Vector3D


def _make_avatar() -> Avatar:
    bones = [
        Bone(name="Hips", parent=None, children=["Spine"]),
        Bone(name="Spine", parent="Hips", children=[]),
    ]
    return Avatar(name="test", root_bone="Hips", bones=bones)


def _make_clip() -> AnimationClip:
    identity = (1.0, 0.0, 0.0, 0.0)
    keyframes = []
    for i in range(3):
        keyframes.append(
            Keyframe(
                timestamp=i / 30.0,
                frame_number=i,
                bone_transforms={
                    "Hips": BoneTransform(
                        position=Vector3D(0.0, 0.0, 0.0), rotation=identity
                    ),
                    "Spine": BoneTransform(
                        position=Vector3D(0.0, 0.1, 0.0), rotation=identity
                    ),
                },
                interpolation=InterpolationType.LINEAR,
            )
        )
    return AnimationClip(keyframes=keyframes)


class TestSendToBlender:
    def test_no_auto_launch_returns_true(self, tmp_path: Path) -> None:
        cfg = BlenderConfig(auto_launch=False)
        exporter = BlenderExporter(config=cfg)
        out = tmp_path / "out.bvh"
        assert exporter.send_to_blender(_make_clip(), _make_avatar(), out) is True
        assert out.exists()
        assert exporter.last_error is None

    def test_explicit_path_skips_temp_tracking(self, tmp_path: Path) -> None:
        cfg = BlenderConfig(auto_launch=False)
        exporter = BlenderExporter(config=cfg)
        out = tmp_path / "out.bvh"
        exporter.send_to_blender(_make_clip(), _make_avatar(), out)
        assert exporter._temp_bvh_path is None

    def test_temp_path_is_created_when_omitted(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "src.blender.exporter.BlenderExporter._cleanup_stale_temp_files", lambda self: None
        )
        cfg = BlenderConfig(auto_launch=False)
        exporter = BlenderExporter(config=cfg)
        assert exporter.send_to_blender(_make_clip(), _make_avatar()) is True
        assert exporter._temp_bvh_path is not None
        assert exporter._temp_bvh_path.exists()
        assert exporter._temp_bvh_path.name.startswith("visionmocap_")
        assert exporter._temp_bvh_path.name.endswith(".bvh")

    def test_cleanup_temp_bvh_removes_file(self, monkeypatch, tmp_path: Path) -> None:
        monkeypatch.setattr(
            "src.blender.exporter.BlenderExporter._cleanup_stale_temp_files", lambda self: None
        )
        cfg = BlenderConfig(auto_launch=False)
        exporter = BlenderExporter(config=cfg)
        exporter.send_to_blender(_make_clip(), _make_avatar())
        path = exporter._temp_bvh_path
        assert path is not None and path.exists()
        exporter.cleanup_temp_bvh()
        assert not path.exists()
        assert exporter._temp_bvh_path is None

    def test_export_failure_sets_last_error(self, monkeypatch) -> None:
        monkeypatch.setattr("src.blender.exporter.BvhExporter", _RaisingBvhExporter)
        cfg = BlenderConfig(auto_launch=False)
        exporter = BlenderExporter(config=cfg)
        assert exporter.send_to_blender(_make_clip(), _make_avatar()) is False
        assert exporter.last_error is not None
        assert "BVH export failed" in exporter.last_error


class _RaisingBvhExporter:
    def __init__(self, *args, **kwargs) -> None:
        pass

    def export(self, path) -> None:
        raise OSError("disk full")


class TestLaunchBlender:
    def test_missing_addon_dir(self, monkeypatch, tmp_path: Path) -> None:
        cfg = BlenderConfig(auto_launch=True)
        exporter = BlenderExporter(config=cfg)
        monkeypatch.setattr(
            "src.blender.exporter.Path.is_dir", lambda self: False
        )
        out = tmp_path / "out.bvh"
        out.write_text("")
        assert exporter._launch_blender(out) is False
        assert "add-on" in (exporter.last_error or "")

    def test_missing_script_reports_precisely(self, monkeypatch, tmp_path: Path) -> None:
        cfg = BlenderConfig(
            auto_launch=True,
            blender_executable="blender",
            script_path=str(tmp_path / "missing_script.py"),
        )
        exporter = BlenderExporter(config=cfg)
        out = tmp_path / "out.bvh"
        out.write_text("")
        assert exporter._launch_blender(out) is False
        assert "script not found" in (exporter.last_error or "")

    def test_executable_not_found(self, monkeypatch, tmp_path: Path) -> None:
        def raise_fnf(*args, **kwargs):
            raise FileNotFoundError("no such file")

        monkeypatch.setattr(subprocess, "Popen", raise_fnf)
        cfg = BlenderConfig(auto_launch=True, blender_executable="blender")
        exporter = BlenderExporter(config=cfg)
        out = tmp_path / "out.bvh"
        out.write_text("")
        assert exporter._launch_blender(out) is False
        assert "Blender executable not found" in (exporter.last_error or "")

    def test_oserror_on_launch(self, monkeypatch, tmp_path: Path) -> None:
        def raise_oserr(*args, **kwargs):
            raise OSError("access denied")

        monkeypatch.setattr(subprocess, "Popen", raise_oserr)
        cfg = BlenderConfig(auto_launch=True, blender_executable="blender")
        exporter = BlenderExporter(config=cfg)
        out = tmp_path / "out.bvh"
        out.write_text("")
        assert exporter._launch_blender(out) is False
        assert "Failed to launch Blender" in (exporter.last_error or "")

    def test_successful_launch(self, monkeypatch, tmp_path: Path) -> None:
        captured = {}

        def fake_popen(cmd, **kwargs):
            captured["cmd"] = cmd
            captured["kwargs"] = kwargs
            return object()

        monkeypatch.setattr(subprocess, "Popen", fake_popen)
        cfg = BlenderConfig(auto_launch=True, blender_executable="blender")
        exporter = BlenderExporter(config=cfg)
        out = tmp_path / "out.bvh"
        out.write_text("")
        assert exporter._launch_blender(out) is True
        assert exporter.last_error is None
        assert captured["cmd"][0] == "blender"
        assert captured["kwargs"] == {
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        }


class TestStaleTempCleanup:
    def test_removes_only_old_files(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
        old = tmp_path / "visionmocap_old.bvh"
        new = tmp_path / "visionmocap_new.bvh"
        old.write_text("x")
        new.write_text("x")
        old_time = time.time() - 2 * 24 * 60 * 60  # 2 days old
        os_utime = getattr(__import__("os"), "utime")
        os_utime(old, (old_time, old_time))
        os_utime(new, (time.time() - 60, time.time() - 60))

        BlenderExporter._cleanup_stale_temp_files()

        assert not old.exists()
        assert new.exists()

    def test_ignores_unrelated_files(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
        unrelated = tmp_path / "keep_me.txt"
        unrelated.write_text("x")
        BlenderExporter._cleanup_stale_temp_files()
        assert unrelated.exists()
