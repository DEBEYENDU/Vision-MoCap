"""Unit tests for the skeleton system (src/animation/avatar.py, bone.py).

Covers bone lengths, hierarchy, parent/child relationships, and the
Avatar template used for retargeting.
"""

from __future__ import annotations

from src.animation.avatar import Avatar
from src.animation.avatar_templates import build_mixamo_avatar
from src.animation.bone import Bone
from src.core.models import Vector3D


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_bone(
    name: str,
    parent: str | None,
    children: list[str],
    head: Vector3D,
    tail: Vector3D,
) -> Bone:
    return Bone(
        name=name,
        parent=parent,
        children=children,
        head_position=head,
        tail_position=tail,
    )


def _make_human_avatar() -> Avatar:
    """A minimal two-arm humanoid for hierarchy tests."""
    bones = [
        _make_bone(
            "Hips", None, ["Spine", "LeftUpLeg", "RightUpLeg"],
            Vector3D(0.0, 0.0, 0.0), Vector3D(0.0, 0.1, 0.0),
        ),
        _make_bone(
            "Spine", "Hips", ["LeftShoulder", "RightShoulder"],
            Vector3D(0.0, 0.1, 0.0), Vector3D(0.0, 0.4, 0.0),
        ),
        _make_bone(
            "LeftShoulder", "Spine", ["LeftUpperArm"],
            Vector3D(0.05, 0.4, 0.0), Vector3D(0.09, 0.4, 0.0),
        ),
        _make_bone(
            "LeftUpperArm", "LeftShoulder", [],
            Vector3D(0.09, 0.4, 0.0), Vector3D(0.2, 0.3, 0.0),
        ),
        _make_bone(
            "RightShoulder", "Spine", ["RightUpperArm"],
            Vector3D(-0.05, 0.4, 0.0), Vector3D(-0.09, 0.4, 0.0),
        ),
        _make_bone(
            "RightUpperArm", "RightShoulder", [],
            Vector3D(-0.09, 0.4, 0.0), Vector3D(-0.2, 0.3, 0.0),
        ),
        _make_bone(
            "LeftUpLeg", "Hips", [],
            Vector3D(0.05, 0.0, 0.0), Vector3D(0.05, -0.4, 0.0),
        ),
        _make_bone(
            "RightUpLeg", "Hips", [],
            Vector3D(-0.05, 0.0, 0.0), Vector3D(-0.05, -0.4, 0.0),
        ),
    ]
    return Avatar(name="humanoid", root_bone="Hips", bones=bones)


# ---------------------------------------------------------------------------
# Bone tests
# ---------------------------------------------------------------------------


class TestBone:
    def test_length_y_axis(self) -> None:
        bone = _make_bone(
            "Spine", "Hips", [], Vector3D(0.0, 0.1, 0.0), Vector3D(0.0, 0.4, 0.0)
        )
        assert abs(bone.length - 0.3) < 1e-9

    def test_length_x_axis(self) -> None:
        bone = _make_bone(
            "LeftUpperArm", "LeftShoulder", [],
            Vector3D(0.1, 0.4, 0.0), Vector3D(0.2, 0.4, 0.0),
        )
        assert abs(bone.length - 0.1) < 1e-9

    def test_length_diagonal(self) -> None:
        bone = _make_bone(
            "Forearm", "UpperArm", [],
            Vector3D(0.0, 0.0, 0.0), Vector3D(1.0, 1.0, 0.0),
        )
        assert abs(bone.length - 2.0 ** 0.5) < 1e-9

    def test_direction_unit_vector(self) -> None:
        bone = _make_bone(
            "Spine", "Hips", [], Vector3D(0.0, 0.0, 0.0), Vector3D(0.0, 3.0, 0.0)
        )
        d = bone.direction
        assert abs(d.x) < 1e-9
        assert abs(d.y - 1.0) < 1e-9
        assert abs(d.z) < 1e-9

    def test_zero_length_direction_identity(self) -> None:
        bone = _make_bone(
            "Degenerate", "Hips", [],
            Vector3D(0.0, 0.0, 0.0), Vector3D(0.0, 0.0, 0.0),
        )
        assert abs(bone.length) < 1e-9
        d = bone.direction
        assert abs(d.x) < 1e-9 and abs(d.y) < 1e-9 and abs(d.z) < 1e-9

    def test_parent_children_links(self) -> None:
        bone = _make_bone(
            "Spine", "Hips", ["Head", "LeftArm"],
            Vector3D(0.0, 0.1, 0.0), Vector3D(0.0, 0.4, 0.0),
        )
        assert bone.parent == "Hips"
        assert bone.children == ["Head", "LeftArm"]
        assert bone.is_root is False

    def test_root_bone(self) -> None:
        bone = _make_bone(
            "Hips", None, ["Spine"],
            Vector3D(0.0, 0.0, 0.0), Vector3D(0.0, 0.1, 0.0),
        )
        assert bone.is_root is True


# ---------------------------------------------------------------------------
# Avatar tests
# ---------------------------------------------------------------------------


class TestAvatar:
    def test_lookup_and_hierarchy(self) -> None:
        avatar = _make_human_avatar()
        spine = avatar.bone("Spine")
        assert spine.parent == "Hips"
        assert "LeftShoulder" in spine.children
        assert avatar.bone("LeftShoulder").parent == "Spine"
        assert avatar.bone("Hips").is_root

    def test_bone_count_and_names(self) -> None:
        avatar = _make_human_avatar()
        assert avatar.bone_count == 8
        assert avatar.bone_names == [
            "Hips", "Spine", "LeftShoulder", "LeftUpperArm",
            "RightShoulder", "RightUpperArm", "LeftUpLeg", "RightUpLeg",
        ]

    def test_missing_bone_raises(self) -> None:
        avatar = _make_human_avatar()
        try:
            avatar.bone("Nope")
            assert False, "Should have raised KeyError"
        except KeyError:
            pass

    def test_from_parent_pairs(self) -> None:
        avatar = Avatar.from_parent_pairs(
            name="test",
            pairs=[
                ("Hips", None),
                ("Spine", "Hips"),
                ("Head", "Spine"),
                ("Arm", "Spine"),
            ],
            root_bone="Hips",
        )
        assert avatar.bone_count == 4
        assert avatar.bone("Head").parent == "Spine"
        assert avatar.bone("Spine").children == ["Head", "Arm"]
        assert avatar.root_bone == "Hips"

    def test_metadata_roundtrip(self) -> None:
        avatar = _make_human_avatar()
        assert avatar.metadata == {}


class TestMixamoTemplate:
    def test_has_expected_bones(self) -> None:
        avatar = build_mixamo_avatar()
        expected = {
            "Hips", "Spine", "Spine1", "Spine2", "Neck", "Head",
            "LeftShoulder", "LeftUpperArm", "LeftForearm", "LeftHand",
            "RightShoulder", "RightUpperArm", "RightForearm", "RightHand",
            "LeftUpLeg", "LeftLeg", "LeftFoot", "LeftToeBase",
            "RightUpLeg", "RightLeg", "RightFoot", "RightToeBase",
        }
        assert set(avatar.bone_names) == expected
        assert avatar.root_bone == "Hips"

    def test_hierarchy_is_valid(self) -> None:
        avatar = build_mixamo_avatar()
        # Every non-root bone names an existing parent.
        for bone in avatar.bones:
            if bone.is_root:
                continue
            assert avatar.has_bone(bone.parent), bone.name

    def test_all_bones_have_positive_length(self) -> None:
        avatar = build_mixamo_avatar()
        for bone in avatar.bones:
            assert bone.length > 0.0, bone.name