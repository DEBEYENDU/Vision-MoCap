"""Headless Blender integration test for VisionMoCap.

Run from VisionMoCap:
    <blender> --background --python tests/integration/blender_headless_test.py

Creates a rigged character armature, imports the VisionMoCap BVH export
via the add-on operator, remaps bones, bakes the animation, and saves an
animated .blend.  Prints machine-readable verification results.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import bpy

ADDON_DIR = Path(__file__).resolve().parent.parent.parent / "src" / "blender" / "addon"
BVH_PATH = Path(
    r"C:\Users\GOD KAKAROT\VisionMoCap\demo\sample_exports\walk_cycle.bvh"
)
OUTPUT_DIR = Path(r"C:\Users\GOD KAKAROT\VisionMoCap\demo\sample_exports")
ANIMATED_BLEND = OUTPUT_DIR / "rigged_character_visionmocap_animated.blend"

RESULTS: dict = {"stage": "started"}


def _log(msg: str) -> None:
    print(f"[VISIONMOCAP-TEST] {msg}", flush=True)


def _ensure_addon_registered() -> bool:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "visionmocap_addon", ADDON_DIR / "__init__.py"
    )
    addon = importlib.util.module_from_spec(spec)
    sys.modules["visionmocap_addon"] = addon
    spec.loader.exec_module(addon)
    for bl_cls in getattr(addon, "_classes", ()):
        try:
            from bpy.utils import register_class

            register_class(bl_cls)
        except Exception:
            pass
    return True


def _make_rigged_character() -> str:
    """Create a rigged Mixamo-named armature (the 'character')."""
    bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
    arm_obj = bpy.context.active_object
    arm_obj.name = "RiggedCharacter"
    arm_data = arm_obj.data
    arm_data.name = "RiggedCharacterArmature"

    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.mode_set(mode="EDIT")

    for eb in list(arm_data.edit_bones):
        if eb.name != "Bone":
            continue
        arm_data.edit_bones.remove(eb)

    names = [
        "Hips", "Spine", "Spine1", "Spine2", "Neck", "Head",
        "LeftShoulder", "LeftUpperArm", "LeftForearm", "LeftHand",
        "RightShoulder", "RightUpperArm", "RightForearm", "RightHand",
        "LeftUpLeg", "LeftLeg", "LeftFoot", "LeftToeBase",
        "RightUpLeg", "RightLeg", "RightFoot", "RightToeBase",
    ]
    parents = {
        "Hips": None,
        "Spine": "Hips", "Spine1": "Spine", "Spine2": "Spine1",
        "Neck": "Spine2", "Head": "Neck",
        "LeftShoulder": "Spine1", "LeftUpperArm": "LeftShoulder",
        "LeftForearm": "LeftUpperArm", "LeftHand": "LeftForearm",
        "RightShoulder": "Spine1", "RightUpperArm": "RightShoulder",
        "RightForearm": "RightUpperArm", "RightHand": "RightForearm",
        "LeftUpLeg": "Hips", "LeftLeg": "LeftUpLeg",
        "LeftFoot": "LeftLeg", "LeftToeBase": "LeftFoot",
        "RightUpLeg": "Hips", "RightLeg": "RightUpLeg",
        "RightFoot": "RightLeg", "RightToeBase": "RightFoot",
    }
    lengths = {
        "Hips": 0.10, "Spine": 0.15, "Spine1": 0.15, "Spine2": 0.10,
        "Neck": 0.05, "Head": 0.10,
        "LeftShoulder": 0.03, "LeftUpperArm": 0.07, "LeftForearm": 0.07,
        "LeftHand": 0.05, "RightShoulder": 0.03, "RightUpperArm": 0.07,
        "RightForearm": 0.07, "RightHand": 0.05,
        "LeftUpLeg": 0.30, "LeftLeg": 0.30, "LeftFoot": 0.10,
        "LeftToeBase": 0.10, "RightUpLeg": 0.30, "RightLeg": 0.30,
        "RightFoot": 0.10, "RightToeBase": 0.10,
    }
    x_offsets = {
        "Hips": 0.0, "Spine": 0.0, "Spine1": 0.0, "Spine2": 0.0,
        "Neck": 0.0, "Head": 0.0,
        "LeftShoulder": -0.03, "LeftUpperArm": -0.07, "LeftForearm": -0.07,
        "LeftHand": -0.05, "RightShoulder": 0.03, "RightUpperArm": 0.07,
        "RightForearm": 0.07, "RightHand": 0.05,
        "LeftUpLeg": -0.05, "LeftLeg": 0.0, "LeftFoot": 0.0,
        "LeftToeBase": 0.0, "RightUpLeg": 0.05, "RightLeg": 0.0,
        "RightFoot": 0.0, "RightToeBase": 0.0,
    }

    for name in names:
        eb = arm_data.edit_bones.new(name)
        parent = parents[name]
        if parent is None:
            eb.head = (0.0, 0.0, 0.0)
            eb.tail = (0.0, 0.0, 0.10)
        else:
            p = arm_data.edit_bones[parent]
            eb.parent = p
            eb.head = (p.tail[0], p.tail[1], p.tail[2])
            eb.tail = (
                eb.head[0] + x_offsets[name],
                eb.head[1],
                eb.head[2] + lengths[name],
            )

    bpy.ops.object.mode_set(mode="OBJECT")
    _log(f"Created rigged character with {len(arm_data.bones)} bones")
    return arm_obj.name


def main() -> None:
    start = time.perf_counter()
    _log(f"Blender {bpy.app.version_string} | BVH: {BVH_PATH}")

    if not BVH_PATH.exists():
        RESULTS.update({"stage": "failed", "error": f"missing BVH {BVH_PATH}"})
        _log(f"FAILED: missing BVH {BVH_PATH}")
        return

    char_name = _make_rigged_character()
    RESULTS["character_bones"] = len(
        bpy.data.armatures["RiggedCharacterArmature"].bones
    )

    _ensure_addon_registered()
    res = bpy.ops.visionmocap.import_bvh(
        filepath=str(BVH_PATH),
        target_rig="MIXAMO",
        auto_bake=True,
    )
    _log(f"import_bvh -> {res}")
    if "FINISHED" not in str(res):
        RESULTS.update({"stage": "failed", "error": f"import_bvh {res}"})
        _log(f"FAILED: import_bvh {res}")
        return

    bvh_arm = [
        o for o in bpy.data.objects
        if o.type == "ARMATURE" and o.name != char_name
    ]
    if not bvh_arm:
        RESULTS.update({"stage": "failed", "error": "no BVH armature found"})
        _log("FAILED: no BVH armature found")
        return

    bvh_obj = bvh_arm[0]
    RESULTS["bvh_bones"] = len(bvh_obj.data.bones)

    bvh_obj.animation_data_create()
    action = bvh_obj.animation_data.action
    if action is None:
        RESULTS.update({"stage": "failed", "error": "no animation action"})
        _log("FAILED: no animation data on imported armature")
        return

    RESULTS["action_name"] = action.name
    RESULTS["fcurves"] = -1
    if hasattr(action, "frame_range"):
        frames = {int(action.frame_range[0]), int(action.frame_range[1])}
    else:
        RESULTS["fcurves"] = len(action.fcurves)
        frames = set()
        for fc in action.fcurves:
            for kp in fc.keyframe_points:
                frames.add(int(kp.co[0]))
    RESULTS["frame_start"] = min(frames) if frames else -1
    RESULTS["frame_end"] = max(frames) if frames else -1

    bpy.context.scene.frame_start = RESULTS["frame_start"]
    bpy.context.scene.frame_end = RESULTS["frame_end"]
    bpy.context.scene.render.fps = 24

    bpy.ops.wm.save_as_mainfile(filepath=str(ANIMATED_BLEND))
    RESULTS["blend_file"] = str(ANIMATED_BLEND)
    RESULTS["stage"] = "success"
    RESULTS["elapsed_s"] = round(time.perf_counter() - start, 2)
    _log(f"SUCCESS: {ANIMATED_BLEND} exists={ANIMATED_BLEND.exists()}")


if __name__ == "__main__":
    main()
    print("[VISIONMOCAP-RESULTS] " + json.dumps(RESULTS), flush=True)