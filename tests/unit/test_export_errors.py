"""Unit tests for the wrapped I/O error paths added during hardening.

Every filesystem-facing operation in the tool should surface a typed,
project-specific exception (never a raw OSError leaking to the GUI).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.animation.animation_clip import AnimationClip
from src.animation.avatar import Avatar
from src.animation.bone import Bone
from src.animation.bvh_exporter import BvhExporter
from src.animation.csv_exporter import CsvExporter
from src.animation.keyframe import InterpolationType, Keyframe
from src.animation.npy_exporter import NpyExporter
from src.animation.retargeted_motion import BoneTransform
from src.core.exceptions import AnimationExportError, RecordingError
from src.core.models import Vector3D
from src.motion.motion_sequence import MotionSequence
from src.pose.pose_result import Landmark, PoseResult
from src.recording.session_manager import SessionManager


def _make_pose(timestamp: float) -> PoseResult:
    return PoseResult(
        timestamp=timestamp,
        landmarks=[
            Landmark(x=0.1 * i, y=0.2 * i, z=0.3 * i, visibility=0.9)
            for i in range(33)
        ],
        confidence=0.9,
        frame_width=640,
        frame_height=480,
        pose_detected=True,
    )


def _make_sequence(n_frames: int = 5, fps: float = 30.0) -> MotionSequence:
    poses = [_make_pose(i / fps) for i in range(n_frames)]
    return MotionSequence(
        pose_results=poses,
        start_time=0.0,
        end_time=n_frames / fps,
        total_frames=n_frames,
        average_fps=fps,
        duration=n_frames / fps,
    )


def _make_avatar() -> Avatar:
    bones = [
        Bone(name="Hips", parent=None, children=["Spine"]),
        Bone(name="Spine", parent="Hips", children=[]),
    ]
    return Avatar(name="test", root_bone="Hips", bones=bones)


def _make_keyframes() -> list[Keyframe]:
    identity = (1.0, 0.0, 0.0, 0.0)
    kfs = []
    for i in range(5):
        kfs.append(
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
    return kfs


def _make_clip() -> AnimationClip:
    return AnimationClip(keyframes=_make_keyframes())


def _unwritable_child(tmp_path: Path, name: str) -> Path:
    """A path whose parent is a regular file --- mkdir() must fail."""
    blocker = tmp_path / "blocker.txt"
    blocker.write_text("x")
    return blocker / "nested" / name


def _make_manager(tmp_path: Path, n_frames: int = 3) -> SessionManager:
    manager = SessionManager(output_dir=tmp_path)
    manager.start_session()
    for i in range(n_frames):
        manager.record_pose(_make_pose(i), frame_number=i + 1, current_fps=30.0)
    manager.stop_session()
    return manager


class TestBvhExportErrors:
    def test_unwritable_parent_raises(self, tmp_path: Path) -> None:
        exporter = BvhExporter(avatar=_make_avatar(), clip=_make_clip())
        with pytest.raises(AnimationExportError) as exc_info:
            exporter.export(_unwritable_child(tmp_path, "clip.bvh"))
        assert exc_info.value.cause is not None

    def test_happy_path(self, tmp_path: Path) -> None:
        exporter = BvhExporter(avatar=_make_avatar(), clip=_make_clip())
        out = tmp_path / "clip.bvh"
        exporter.export(out)
        text = out.read_text(encoding="utf-8")
        assert "HIERARCHY" in text
        assert "MOTION" in text
        assert "Frames: 5" in text


class TestCsvExportErrors:
    def test_unwritable_parent_raises(self, tmp_path: Path) -> None:
        exporter = CsvExporter()
        with pytest.raises(AnimationExportError) as exc_info:
            exporter.export(_make_sequence(), _unwritable_child(tmp_path, "out.csv"))
        assert exc_info.value.cause is not None

    def test_empty_sequence_raises_value_error(self, tmp_path: Path) -> None:
        exporter = CsvExporter()
        with pytest.raises(ValueError):
            exporter.export(_make_sequence(0), tmp_path / "out.csv")


class TestNpyExportErrors:
    def test_unwritable_parent_raises(self, tmp_path: Path) -> None:
        exporter = NpyExporter()
        with pytest.raises(AnimationExportError) as exc_info:
            exporter.export(_make_sequence(), _unwritable_child(tmp_path, "out.npy"))
        assert exc_info.value.cause is not None

    def test_happy_path(self, tmp_path: Path) -> None:
        exporter = NpyExporter()
        out = tmp_path / "out.npy"
        exporter.export(_make_sequence(), out)
        assert out.exists()
        assert out.stat().st_size > 0


class TestRecordingSessionErrors:
    def test_unwritable_output_dir_raises(self, tmp_path: Path) -> None:
        blocker = tmp_path / "blocker.txt"
        blocker.write_text("x")
        manager = _make_manager(blocker / "sub")
        with pytest.raises(RecordingError) as exc_info:
            manager.save_recording()
        assert exc_info.value.cause is not None

    def test_happy_path(self, tmp_path: Path) -> None:
        manager = _make_manager(tmp_path)
        result = manager.save_recording()
        assert result is not None
        assert result.exists()
        data = json.loads(result.read_text(encoding="utf-8"))
        assert data["metadata"]["frame_count"] == 3

    def test_save_without_frames_returns_none(self, tmp_path: Path) -> None:
        manager = SessionManager(output_dir=tmp_path)
        manager.start_session()
        manager.stop_session()
        assert manager.save_recording() is None

    def test_save_active_session_returns_none(self, tmp_path: Path) -> None:
        manager = SessionManager(output_dir=tmp_path)
        manager.start_session()
        manager.record_pose(_make_pose(0.0), frame_number=1, current_fps=30.0)
        assert manager.save_recording() is None
        manager.stop_session()