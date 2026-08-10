"""Unit tests for the animation system (Module 4).

Covers AnimationClip interpolation (linear + slerp), AnimationEngine
conversion of RetargetedMotion, and the MotionToAnimationConverter
pipeline entry point.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from src.animation.animation_clip import AnimationClip
from src.animation.animation_engine import AnimationEngine
from src.animation.keyframe import InterpolationType, Keyframe
from src.animation.motion_to_animation import MotionToAnimationConverter
from src.animation.retargeted_motion import (
    BoneTransform,
    RetargetedFrame,
    RetargetedMotion,
)
from src.core.exceptions import RetargetingError
from src.core.models import Vector3D
from src.motion.motion_sequence import MotionSequence
from src.pose.pose_result import Landmark, PoseResult

_IDENTITY = (1.0, 0.0, 0.0, 0.0)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _bt(x: float, rotation: Tuple[float, float, float, float] = _IDENTITY) -> BoneTransform:
    return BoneTransform(position=Vector3D(x, 0.0, 0.0), rotation=rotation)


def _keyframes() -> List[Keyframe]:
    return [
        Keyframe(
            timestamp=0.0,
            frame_number=0,
            bone_transforms={"Hips": _bt(0.0), "Spine": _bt(0.1)},
            interpolation=InterpolationType.LINEAR,
        ),
        Keyframe(
            timestamp=1.0,
            frame_number=1,
            bone_transforms={"Hips": _bt(1.0), "Spine": _bt(1.1)},
            interpolation=InterpolationType.LINEAR,
        ),
        Keyframe(
            timestamp=2.0,
            frame_number=2,
            bone_transforms={"Hips": _bt(2.0), "Spine": _bt(2.1)},
            interpolation=InterpolationType.LINEAR,
        ),
    ]


def _clip() -> AnimationClip:
    return AnimationClip(keyframes=_keyframes(), duration=2.0, fps=30.0)


def _retargeted_motion() -> RetargetedMotion:
    frames = [
        RetargetedFrame(
            timestamp=float(i),
            bones={"Hips": _bt(float(i))},
        )
        for i in range(3)
    ]
    return RetargetedMotion(
        frames=frames, avatar_name="test", fps=30.0, duration=2.0
    )


def _pose(lms: List[Landmark], timestamp: float) -> PoseResult:
    return PoseResult(
        timestamp=timestamp,
        landmarks=lms,
        world_landmarks=lms,
        confidence=0.9,
        frame_width=640,
        frame_height=480,
        pose_detected=True,
    )


def _tpose_landmarks() -> List[Landmark]:
    lms = [Landmark(0.5, 0.5, 0.0, 1.0) for _ in range(33)]
    lms[23] = Landmark(0.45, 0.7, 0.0, 1.0)
    lms[24] = Landmark(0.55, 0.7, 0.0, 1.0)
    lms[11] = Landmark(0.35, 0.4, 0.0, 1.0)
    lms[12] = Landmark(0.65, 0.4, 0.0, 1.0)
    lms[0] = Landmark(0.5, 0.15, 0.0, 1.0)
    lms[2] = Landmark(0.52, 0.15, 0.0, 1.0)
    lms[13] = Landmark(0.25, 0.4, 0.0, 1.0)
    lms[15] = Landmark(0.15, 0.4, 0.0, 1.0)
    lms[19] = Landmark(0.10, 0.4, 0.0, 1.0)
    lms[14] = Landmark(0.75, 0.4, 0.0, 1.0)
    lms[16] = Landmark(0.85, 0.4, 0.0, 1.0)
    lms[20] = Landmark(0.90, 0.4, 0.0, 1.0)
    lms[25] = Landmark(0.45, 0.9, 0.0, 1.0)
    lms[26] = Landmark(0.55, 0.9, 0.0, 1.0)
    lms[27] = Landmark(0.45, 1.0, 0.0, 1.0)
    lms[28] = Landmark(0.55, 1.0, 0.0, 1.0)
    lms[29] = Landmark(0.45, 1.0, -0.1, 1.0)
    lms[30] = Landmark(0.55, 1.0, -0.1, 1.0)
    lms[31] = Landmark(0.45, 1.0, 0.1, 1.0)
    lms[32] = Landmark(0.55, 1.0, 0.1, 1.0)
    return lms


def _motion_sequence(n_frames: int = 3) -> MotionSequence:
    return MotionSequence(
        pose_results=[_pose(_tpose_landmarks(), float(i)) for i in range(n_frames)],
        start_time=0.0,
        end_time=float(n_frames - 1),
        total_frames=n_frames,
        average_fps=30.0,
        duration=float(n_frames - 1),
    )


# ---------------------------------------------------------------------------
# AnimationClip
# ---------------------------------------------------------------------------


class TestAnimationClip:
    def test_frame_count_and_metadata(self) -> None:
        clip = _clip()
        assert clip.frame_count == 3
        assert clip.fps == 30.0
        assert clip.duration == 2.0
        assert clip.metadata == {}
        assert clip.bone_names == ["Hips", "Spine"]

    def test_interpolate_at_keyframe(self) -> None:
        clip = _clip()
        bones = clip.interpolate(1.0)
        assert bones is not None
        assert abs(bones["Hips"].position.x - 1.0) < 1e-9

    def test_interpolate_midpoint_linear(self) -> None:
        clip = _clip()
        bones = clip.interpolate(0.5)
        assert abs(bones["Hips"].position.x - 0.5) < 1e-9

    def test_interpolate_clamps_before_first(self) -> None:
        clip = _clip()
        bones = clip.interpolate(-5.0)
        assert abs(bones["Hips"].position.x - 0.0) < 1e-9

    def test_interpolate_clamps_after_last(self) -> None:
        clip = _clip()
        bones = clip.interpolate(99.0)
        assert abs(bones["Hips"].position.x - 2.0) < 1e-9

    def test_step_keyframes_hold_value(self) -> None:
        kfs = [
            Keyframe(
                timestamp=0.0, frame_number=0,
                bone_transforms={"Hips": _bt(0.0)},
                interpolation=InterpolationType.STEP,
            ),
            Keyframe(
                timestamp=1.0, frame_number=1,
                bone_transforms={"Hips": _bt(1.0)},
                interpolation=InterpolationType.STEP,
            ),
        ]
        clip = AnimationClip(keyframes=kfs, duration=1.0, fps=30.0)
        bones = clip.interpolate(0.7)
        assert abs(bones["Hips"].position.x - 0.0) < 1e-9

    def test_empty_clip_interpolate_none(self) -> None:
        clip = AnimationClip(keyframes=[], duration=0.0)
        assert clip.interpolate(0.0) is None

    def test_add_and_remove_keyframe(self) -> None:
        clip = _clip()
        clip.add_keyframe(
            Keyframe(
                timestamp=0.5, frame_number=5,
                bone_transforms={"Hips": _bt(0.25)},
            )
        )
        assert clip.frame_count == 4
        assert clip.get_keyframe(5) is not None
        assert clip.remove_keyframe(5) is True
        assert clip.frame_count == 3

    def test_slerp_quarter_turn(self) -> None:
        # Rotate 90° around Z between keyframes; midpoint should be 45°.
        import math

        a = 1.0 / math.sqrt(2.0)
        kfs = [
            Keyframe(
                timestamp=0.0, frame_number=0,
                bone_transforms={"J": _bt(0.0, (1.0, 0.0, 0.0, 0.0))},
            ),
            Keyframe(
                timestamp=1.0, frame_number=1,
                bone_transforms={"J": _bt(0.0, (a, 0.0, 0.0, a))},
            ),
        ]
        clip = AnimationClip(keyframes=kfs, duration=1.0, fps=30.0)
        bones = clip.interpolate(0.5)
        w, x, y, z = bones["J"].rotation
        # Midpoint of 0°→90° around Z is 45° = (cos22.5, 0, 0, sin22.5).
        assert abs(w - math.cos(math.radians(22.5))) < 1e-6

    def test_keyframes_sorted_on_construction(self) -> None:
        clip = AnimationClip(
            keyframes=list(reversed(_keyframes())),
            duration=2.0,
            fps=30.0,
        )
        assert [kf.timestamp for kf in clip.keyframes] == [0.0, 1.0, 2.0]


# ---------------------------------------------------------------------------
# AnimationEngine
# ---------------------------------------------------------------------------


class TestAnimationEngine:
    def test_convert_creates_per_frame_keyframes(self) -> None:
        engine = AnimationEngine()
        clip = engine.convert(_retargeted_motion())
        assert clip.frame_count == 3
        assert clip.fps == 30.0
        assert clip.duration == 2.0
        assert clip.metadata["source_avatar"] == "test"

    def test_convert_empty_raises(self) -> None:
        engine = AnimationEngine()
        empty = RetargetedMotion(frames=[], avatar_name="test", fps=30.0, duration=0.0)
        try:
            engine.convert(empty)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_find_frame_nearest(self) -> None:
        engine = AnimationEngine()
        clip = engine.convert(_retargeted_motion())
        kf = engine.find_frame(clip, 1.7)
        assert kf is not None
        assert kf.frame_number == 2

    def test_playback_duration_fallback(self) -> None:
        engine = AnimationEngine()
        clip = AnimationClip(keyframes=_keyframes(), duration=0.0, fps=30.0)
        assert abs(engine.get_playback_duration(clip) - 2.0) < 1e-9


# ---------------------------------------------------------------------------
# MotionToAnimationConverter (end-to-end pipeline entry)
# ---------------------------------------------------------------------------


class TestMotionToAnimationConverter:
    def test_convert_end_to_end(self) -> None:
        converter = MotionToAnimationConverter()
        clip = converter.convert(_motion_sequence())
        assert clip.frame_count == 3
        assert clip.duration == 2.0
        assert "Hips" in clip.bone_names
        assert len(clip.bone_names) == 22  # full Mixamo template

    def test_convert_none_raises_friendly_error(self) -> None:
        converter = MotionToAnimationConverter()
        try:
            converter.convert(None)
            assert False, "Should have raised RetargetingError"
        except RetargetingError as exc:
            assert "Cannot create animation" in str(exc)

    def test_convert_empty_raises(self) -> None:
        converter = MotionToAnimationConverter()
        empty = MotionSequence(pose_results=[], total_frames=0)
        try:
            converter.convert(empty)
            assert False, "Should have raised RetargetingError"
        except RetargetingError:
            pass

    def test_convert_all_undetected_raises(self) -> None:
        converter = MotionToAnimationConverter()
        seq = MotionSequence(
            pose_results=[
                _pose(_tpose_landmarks(), 0.0),
            ],
            total_frames=1,
        )
        seq.pose_results[0].pose_detected = False
        try:
            converter.convert(seq)
            assert False, "Should have raised RetargetingError"
        except RetargetingError as exc:
            assert "pose" in str(exc).lower()

    def test_retarget_exposes_motion(self) -> None:
        converter = MotionToAnimationConverter()
        motion = converter.retarget(_motion_sequence(4))
        assert len(motion.frames) == 4

    def test_custom_interpolation(self) -> None:
        converter = MotionToAnimationConverter()
        seq = _motion_sequence(2)
        seq.average_fps = 30.0
        clip = converter.convert(seq, interpolation=InterpolationType.STEP)
        assert all(
            kf.interpolation == InterpolationType.STEP for kf in clip.keyframes
        )

    def test_custom_fps_sampling(self) -> None:
        converter = MotionToAnimationConverter()
        # 61 frames at 30 fps over 2 seconds → 10 fps sampling gives 21.
        seq = _motion_sequence(61)
        seq.average_fps = 30.0
        seq.duration = 2.0
        clip = converter.convert(seq, fps=10.0)
        assert clip.fps == 10.0
        assert clip.frame_count == 21