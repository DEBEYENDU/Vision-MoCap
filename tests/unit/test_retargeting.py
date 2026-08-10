"""Unit tests for skeleton mapping and motion retargeting.

Covers SkeletonMapper coordinate conversion, landmark→bone mapping,
quaternion rotation computation (Module 3), and Retargeter output
shape and determinism (Module 5).
"""

from __future__ import annotations

from typing import List

from src.animation.avatar_templates import build_mixamo_avatar
from src.animation.retargeter import Retargeter
from src.animation.skeleton_mapper import (
    PRESET_BLENDER,
    PRESET_MIXAMO,
    SkeletonMapper,
)
from src.motion.motion_sequence import MotionSequence
from src.pose.pose_result import Landmark, PoseResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_landmarks_tpose() -> List[Landmark]:
    """Synthetic 'T-pose' landmarks in MediaPipe space (y-down).

    Indices per PRESET_MIXAMO:
        0 nose, 2 l_eye, 11 l_shoulder, 12 r_shoulder,
        13 l_elbow, 14 r_elbow, 15 l_wrist, 16 r_wrist,
        19 l_index, 20 r_index, 23 l_hip, 24 r_hip,
        25 l_knee, 26 r_knee, 27 l_ankle, 28 r_ankle,
        29 l_heel, 30 r_heel, 31 l_foot_index, 32 r_foot_index
    """
    lms = [Landmark(x=0.5, y=0.5, z=0.0, visibility=1.0) for _ in range(33)]

    # Spine: hips at y=0.7, shoulders at y=0.4, head at y=0.15
    lms[23] = Landmark(0.45, 0.7, 0.0, 1.0)   # l_hip
    lms[24] = Landmark(0.55, 0.7, 0.0, 1.0)   # r_hip
    lms[11] = Landmark(0.35, 0.4, 0.0, 1.0)   # l_shoulder
    lms[12] = Landmark(0.65, 0.4, 0.0, 1.0)   # r_shoulder
    lms[0] = Landmark(0.5, 0.15, 0.0, 1.0)    # nose
    lms[2] = Landmark(0.52, 0.15, 0.0, 1.0)   # l_eye

    # Left arm: elbow out, wrist out (T-pose arms)
    lms[13] = Landmark(0.25, 0.4, 0.0, 1.0)   # l_elbow
    lms[15] = Landmark(0.15, 0.4, 0.0, 1.0)   # l_wrist
    lms[19] = Landmark(0.10, 0.4, 0.0, 1.0)   # l_index
    lms[14] = Landmark(0.75, 0.4, 0.0, 1.0)   # r_elbow
    lms[16] = Landmark(0.85, 0.4, 0.0, 1.0)   # r_wrist
    lms[20] = Landmark(0.90, 0.4, 0.0, 1.0)   # r_index

    # Legs: knees, ankles, feet straight down
    lms[25] = Landmark(0.45, 0.9, 0.0, 1.0)   # l_knee
    lms[26] = Landmark(0.55, 0.9, 0.0, 1.0)   # r_knee
    lms[27] = Landmark(0.45, 1.0, 0.0, 1.0)   # l_ankle
    lms[28] = Landmark(0.55, 1.0, 0.0, 1.0)   # r_ankle
    lms[31] = Landmark(0.45, 1.0, 0.1, 1.0)   # l_foot_index
    lms[32] = Landmark(0.55, 1.0, 0.1, 1.0)   # r_foot_index
    lms[29] = Landmark(0.45, 1.0, -0.1, 1.0)  # l_heel
    lms[30] = Landmark(0.55, 1.0, -0.1, 1.0)  # r_heel
    return lms


def _make_pose(lms: List[Landmark], timestamp: float) -> PoseResult:
    return PoseResult(
        timestamp=timestamp,
        landmarks=lms,
        world_landmarks=lms,
        confidence=0.95,
        frame_width=640,
        frame_height=480,
        pose_detected=True,
    )


def _make_sequence(n_frames: int = 3) -> MotionSequence:
    poses = [_make_pose(_make_landmarks_tpose(), float(i)) for i in range(n_frames)]
    return MotionSequence(
        pose_results=poses,
        start_time=0.0,
        end_time=float(n_frames - 1),
        total_frames=n_frames,
        average_fps=30.0,
        duration=float(n_frames - 1),
    )


# ---------------------------------------------------------------------------
# SkeletonMapper (Module 2/5)
# ---------------------------------------------------------------------------


class TestSkeletonMapper:
    def test_presets_available(self) -> None:
        mapper = SkeletonMapper(preset="mixamo")
        assert len(mapper.bone_names) == len(PRESET_MIXAMO)
        assert mapper.has_bone("Hips")
        assert mapper.has_bone("LeftForearm")

    def test_blender_preset_bone_names(self) -> None:
        mapper = SkeletonMapper(preset="blender")
        assert "hips" in mapper.bone_names
        assert "upper_arm.L" in mapper.bone_names

    def test_flips_y_coordinate(self) -> None:
        mapper = SkeletonMapper(preset="mixamo")
        pose = _make_pose(_make_landmarks_tpose(), 0.0)
        mapped = mapper.map_frame(pose)
        # Hip landmark at y=0.7 (y-down) maps to y=0.3 (y-up).
        hips_head, _ = mapped["Hips"]
        assert abs(hips_head.y - 0.3) < 1e-9

    def test_negates_z_for_forward(self) -> None:
        mapper = SkeletonMapper(preset="mixamo")
        pose = _make_pose(_make_landmarks_tpose(), 0.0)
        mapped = mapper.map_frame(pose)
        _, toe_tail = mapped["LeftToeBase"]
        # Heel z=-0.1 (away from camera in MediaPipe) becomes z=+0.1.
        assert abs(toe_tail.z - 0.1) < 1e-9

    def test_custom_mapping(self) -> None:
        custom = {"Spine": {"head": 23, "tail": 11}}
        mapper = SkeletonMapper(mapping=custom)
        assert mapper.bone_names == ["Spine"]
        pose = _make_pose(_make_landmarks_tpose(), 0.0)
        mapped = mapper.map_frame(pose)
        assert "Spine" in mapped

    def test_bone_out_of_range_skipped(self) -> None:
        custom = {"Head": {"head": 0, "tail": 99}}
        mapper = SkeletonMapper(mapping=custom)
        pose = _make_pose(_make_landmarks_tpose(), 0.0)
        mapped = mapper.map_frame(pose)
        assert mapped == {}

    def test_partial_landmarks_map_available_bones(self) -> None:
        """A pose with fewer than 33 landmarks still maps present bones."""
        mapper = SkeletonMapper(preset="mixamo")
        lms = _make_landmarks_tpose()[:22]  # only indices 0..21
        pose = _make_pose(lms, 0.0)
        mapped = mapper.map_frame(pose)
        # Bones requiring landmark 23+ (legs/hips) are skipped.
        assert "Hips" not in mapped
        assert "LeftForearm" in mapped  # uses 13/15

    def test_aliases_rename_bones(self) -> None:
        mapper = SkeletonMapper(
            preset="mixamo",
            aliases={"LeftUpperArm": "upper_arm.L"},
        )
        assert "upper_arm.L" in mapper.bone_names
        assert "LeftUpperArm" not in mapper.bone_names


# ---------------------------------------------------------------------------
# Retargeter (Module 3/5)
# ---------------------------------------------------------------------------


class TestRetargeter:
    def test_retarget_produces_one_frame_per_pose(self) -> None:
        mapper = SkeletonMapper(preset="mixamo")
        avatar = build_mixamo_avatar()
        retargeter = Retargeter(mapper=mapper, avatar=avatar)
        motion = retargeter.retarget(_make_sequence(5))
        assert len(motion.frames) == 5
        assert motion.avatar_name == "MixamoRig"
        assert motion.fps == 30.0

    def test_frames_contain_all_mapped_bones(self) -> None:
        mapper = SkeletonMapper(preset="mixamo")
        retargeter = Retargeter(mapper=mapper, avatar=build_mixamo_avatar())
        motion = retargeter.retarget(_make_sequence(1))
        bones = motion.frames[0].bones
        assert set(bones.keys()) == set(PRESET_MIXAMO.keys())

    def test_identity_pose_gives_identity_rotation(self) -> None:
        """Straight-down leg has the same direction as the bind pose."""
        mapper = SkeletonMapper(preset="mixamo")
        retargeter = Retargeter(mapper=mapper, avatar=build_mixamo_avatar())
        motion = retargeter.retarget(_make_sequence(1))
        rot = motion.frames[0].bones["LeftLeg"].rotation
        assert abs(rot[0] - 1.0) < 1e-6  # w close to 1 (identity)
        assert abs(rot[1]) < 1e-6
        assert abs(rot[2]) < 1e-6

    def test_position_matches_head_landmark(self) -> None:
        mapper = SkeletonMapper(preset="mixamo")
        retargeter = Retargeter(mapper=mapper, avatar=build_mixamo_avatar())
        motion = retargeter.retarget(_make_sequence(1))
        pos = motion.frames[0].bones["Hips"].position
        # Hips head = l_hip (0.45, 0.7) flipped → (0.45, 0.3)
        assert abs(pos.x - 0.45) < 1e-9
        assert abs(pos.y - 0.3) < 1e-9

    def test_deterministic_across_runs(self) -> None:
        mapper = SkeletonMapper(preset="mixamo")
        avatar = build_mixamo_avatar()
        seq = _make_sequence(4)
        r1 = Retargeter(mapper=mapper, avatar=avatar).retarget(seq)
        r2 = Retargeter(mapper=mapper, avatar=avatar).retarget(seq)
        for f1, f2 in zip(r1.frames, r2.frames):
            for name, bt1 in f1.bones.items():
                bt2 = f2.bones[name]
                assert bt1.position == bt2.position
                assert bt1.rotation == bt2.rotation

    def test_empty_sequence_raises(self) -> None:
        retargeter = Retargeter(
            mapper=SkeletonMapper(preset="mixamo"), avatar=build_mixamo_avatar()
        )
        empty = MotionSequence(pose_results=[], total_frames=0)
        try:
            retargeter.retarget(empty)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_sequence_duration_used(self) -> None:
        mapper = SkeletonMapper(preset="mixamo")
        retargeter = Retargeter(mapper=mapper, avatar=build_mixamo_avatar())
        seq = _make_sequence(10)
        motion = retargeter.retarget(seq)
        assert motion.duration == seq.duration

    def test_rotation_direction_changes_with_motion(self) -> None:
        """Raised arm should produce a non-identity rotation."""
        lms = _make_landmarks_tpose()
        lms[13] = Landmark(0.35, 0.2, 0.0, 1.0)   # l_elbow up
        lms[15] = Landmark(0.35, 0.1, 0.0, 1.0)   # l_wrist up
        lms[19] = Landmark(0.35, 0.05, 0.0, 1.0)  # l_index up
        seq = MotionSequence(
            pose_results=[_make_pose(lms, 0.0)],
            total_frames=1,
            average_fps=30.0,
        )
        retargeter = Retargeter(
            mapper=SkeletonMapper(preset="mixamo"), avatar=build_mixamo_avatar()
        )
        motion = retargeter.retarget(seq)
        rot = motion.frames[0].bones["LeftUpperArm"].rotation
        # Not identity.
        assert not (abs(rot[0] - 1.0) < 1e-6 and abs(rot[1]) < 1e-6
                    and abs(rot[2]) < 1e-6 and abs(rot[3]) < 1e-6)
        # Unit quaternion.
        assert abs(1.0 - sum(c * c for c in rot)) < 1e-6