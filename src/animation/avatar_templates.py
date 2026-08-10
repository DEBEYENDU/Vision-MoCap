"""Shared avatar templates for the VisionMoCap animation subsystem.

Defines pre-built Avatar skeletons that pair with the SkeletonMapper
presets.  Having the template here (instead of the GUI layer) lets the
MotionToAnimationConverter and exporters share a single definition of
the reference skeleton.
"""

from __future__ import annotations

from src.animation.avatar import Avatar
from src.animation.bone import Bone
from src.core.models import Vector3D


def build_mixamo_avatar() -> Avatar:
    """Build an Avatar matching the bones of the Mixamo skeleton preset."""
    bones_data: list[tuple[str, str | None, list[str], Vector3D, Vector3D]] = [
        # (name, parent, children, head, tail)
        ("Hips",         None,  ["Spine", "LeftUpLeg", "RightUpLeg"],
         Vector3D(0.0, 0.0, 0.0), Vector3D(0.0, 0.1, 0.0)),
        ("Spine",        "Hips",  ["Spine1"],
         Vector3D(0.0, 0.1, 0.0), Vector3D(0.0, 0.25, 0.0)),
        ("Spine1",       "Spine", ["Spine2", "LeftShoulder", "RightShoulder"],
         Vector3D(0.0, 0.25, 0.0), Vector3D(0.0, 0.4, 0.0)),
        ("Spine2",       "Spine1",["Neck"],
         Vector3D(0.0, 0.4, 0.0), Vector3D(0.0, 0.5, 0.0)),
        ("Neck",         "Spine2",["Head"],
         Vector3D(0.0, 0.5, 0.0), Vector3D(0.0, 0.55, 0.0)),
        ("Head",         "Neck",  [],
         Vector3D(0.0, 0.55, 0.0), Vector3D(0.0, 0.65, 0.0)),
        ("LeftShoulder", "Spine1",["LeftUpperArm"],
         Vector3D(0.05, 0.25, 0.0), Vector3D(0.08, 0.25, 0.0)),
        ("LeftUpperArm", "LeftShoulder",["LeftForearm"],
         Vector3D(0.08, 0.25, 0.0), Vector3D(0.15, 0.22, 0.0)),
        ("LeftForearm",  "LeftUpperArm",["LeftHand"],
         Vector3D(0.15, 0.22, 0.0), Vector3D(0.22, 0.18, 0.0)),
        ("LeftHand",     "LeftForearm",[],
         Vector3D(0.22, 0.18, 0.0), Vector3D(0.27, 0.16, 0.0)),
        ("RightShoulder","Spine1",["RightUpperArm"],
         Vector3D(-0.05, 0.25, 0.0), Vector3D(-0.08, 0.25, 0.0)),
        ("RightUpperArm","RightShoulder",["RightForearm"],
         Vector3D(-0.08, 0.25, 0.0), Vector3D(-0.15, 0.22, 0.0)),
        ("RightForearm", "RightUpperArm",["RightHand"],
         Vector3D(-0.15, 0.22, 0.0), Vector3D(-0.22, 0.18, 0.0)),
        ("RightHand",    "RightForearm",[],
         Vector3D(-0.22, 0.18, 0.0), Vector3D(-0.27, 0.16, 0.0)),
        ("LeftUpLeg",    "Hips", ["LeftLeg"],
         Vector3D(0.05, 0.0, 0.0), Vector3D(0.05, -0.3, 0.0)),
        ("LeftLeg",      "LeftUpLeg",["LeftFoot"],
         Vector3D(0.05, -0.3, 0.0), Vector3D(0.05, -0.6, 0.0)),
        ("LeftFoot",     "LeftLeg",["LeftToeBase"],
         Vector3D(0.05, -0.6, 0.0), Vector3D(0.05, -0.7, 0.05)),
        ("LeftToeBase",  "LeftFoot",[],
         Vector3D(0.05, -0.7, 0.05), Vector3D(0.05, -0.7, 0.15)),
        ("RightUpLeg",   "Hips", ["RightLeg"],
         Vector3D(-0.05, 0.0, 0.0), Vector3D(-0.05, -0.3, 0.0)),
        ("RightLeg",     "RightUpLeg",["RightFoot"],
         Vector3D(-0.05, -0.3, 0.0), Vector3D(-0.05, -0.6, 0.0)),
        ("RightFoot",    "RightLeg",["RightToeBase"],
         Vector3D(-0.05, -0.6, 0.0), Vector3D(-0.05, -0.7, 0.05)),
        ("RightToeBase", "RightFoot",[],
         Vector3D(-0.05, -0.7, 0.05), Vector3D(-0.05, -0.7, 0.15)),
    ]
    bones = [
        Bone(
            name=name, parent=parent, children=children,
            head_position=head, tail_position=tail,
        )
        for name, parent, children, head, tail in bones_data
    ]
    return Avatar(name="MixamoRig", root_bone="Hips", bones=bones)