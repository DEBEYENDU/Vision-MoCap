"""Blender operators for importing and baking VisionMoCap animations."""

from __future__ import annotations

import bpy
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper

# ---------------------------------------------------------------------------
# Bone-name mappings: BVH source → target rig bone
# ---------------------------------------------------------------------------
# Source bone names come from the Mixamo preset used by BvhExporter.
# Target names follow Mixamo (identical) and Rigify (Meta-Rig) conventions.

_MIXAMO_MAP: dict[str, str] = {
    "Hips": "Hips",
    "Spine": "Spine",
    "Spine1": "Spine1",
    "Spine2": "Spine2",
    "Neck": "Neck",
    "Head": "Head",
    "LeftShoulder": "LeftShoulder",
    "LeftUpperArm": "LeftUpperArm",
    "LeftForearm": "LeftForearm",
    "LeftHand": "LeftHand",
    "RightShoulder": "RightShoulder",
    "RightUpperArm": "RightUpperArm",
    "RightForearm": "RightForearm",
    "RightHand": "RightHand",
    "LeftUpLeg": "LeftUpLeg",
    "LeftLeg": "LeftLeg",
    "LeftFoot": "LeftFoot",
    "LeftToeBase": "LeftToeBase",
    "RightUpLeg": "RightUpLeg",
    "RightLeg": "RightLeg",
    "RightFoot": "RightFoot",
    "RightToeBase": "RightToeBase",
}

_RIGIFY_MAP: dict[str, str] = {
    "Hips": "spine",
    "Spine": "spine.001",
    "Spine1": "spine.002",
    "Spine2": "spine.003",
    "Neck": "neck",
    "Head": "head",
    "LeftShoulder": "shoulder.L",
    "LeftUpperArm": "upper_arm.L",
    "LeftForearm": "forearm.L",
    "LeftHand": "hand.L",
    "RightShoulder": "shoulder.R",
    "RightUpperArm": "upper_arm.R",
    "RightForearm": "forearm.R",
    "RightHand": "hand.R",
    "LeftUpLeg": "thigh.L",
    "LeftLeg": "shin.L",
    "LeftFoot": "foot.L",
    "LeftToeBase": "foot.L",
    "RightUpLeg": "thigh.R",
    "RightLeg": "shin.R",
    "RightFoot": "foot.R",
    "RightToeBase": "foot.R",
}


def _get_bone_map(target_rig_type: str) -> dict[str, str]:
    if target_rig_type == "RIGIFY":
        return _RIGIFY_MAP
    return _MIXAMO_MAP


# ---------------------------------------------------------------------------
# Operator: Import BVH
# ---------------------------------------------------------------------------


class VISIONMOCAP_OT_import_bvh(Operator, ImportHelper):
    """Import a VisionMoCap BVH file and optionally map to a target rig."""

    bl_idname = "visionmocap.import_bvh"
    bl_label = "Import BVH"
    bl_description = "Import a VisionMoCap BVH animation file"
    bl_options = {"REGISTER", "UNDO"}

    filename_ext = ".bvh"

    filter_glob: bpy.props.StringProperty(
        default="*.bvh",
        options={"HIDDEN"},
    )

    target_rig: bpy.props.EnumProperty(
        name="Target Rig",
        description="Rig type for bone name mapping",
        items=[
            ("NONE", "None (keep BVH armature)", "Import without remapping"),
            ("MIXAMO", "Mixamo Rig", "Map to Mixamo bone naming"),
            ("RIGIFY", "Rigify (Meta-Rig)", "Map to Rigify bone naming"),
        ],
        default="MIXAMO",
    )

    auto_bake: bpy.props.BoolProperty(
        name="Auto-Bake",
        description="Bake animation to keyframes after import",
        default=True,
    )

    def execute(self, context: bpy.types.Context) -> set[str]:
        result = self._import_bvh(context)
        if result != {"FINISHED"}:
            return result

        if self.target_rig != "NONE":
            result = self._remap_to_rig(context)
            if result != {"FINISHED"}:
                return result

        if self.auto_bake:
            self._bake_animation(context)

        self.report({"INFO"}, f"Imported {self.filepath}")
        return {"FINISHED"}

    def _import_bvh(self, context: bpy.types.Context) -> set[str]:
        """Run Blender's built-in BVH importer."""
        prev_objects = set(bpy.data.objects)
        result = bpy.ops.import_anim.bvh(
            filepath=self.filepath,
            axis_forward="Z",
            axis_up="Y",
            global_scale=1.0,
            use_fps_scale=False,
            update_scene_fps=False,
            update_scene_duration=False,
        )
        if "FINISHED" not in result:
            self.report({"ERROR"}, "Failed to import BVH file.")
            return {"CANCELLED"}

        new_objects = set(bpy.data.objects) - prev_objects
        armatures = [o for o in new_objects if o.type == "ARMATURE"]
        if not armatures:
            self.report({"ERROR"}, "No armature found in BVH file.")
            return {"CANCELLED"}

        context.view_layer.objects.active = armatures[0]
        armatures[0].select_set(True)
        self._imported_armature = armatures[0].name
        return {"FINISHED"}

    def _remap_to_rig(self, context: bpy.types.Context) -> set[str]:
        """Rename imported BVH bones to match the target rig convention."""
        arm = bpy.data.armatures.get(self._imported_armature)
        if arm is None:
            return {"CANCELLED"}

        arm_obj = bpy.data.objects.get(self._imported_armature)
        if arm_obj is None:
            return {"CANCELLED"}

        bone_map = _get_bone_map(self.target_rig)
        context.view_layer.objects.active = arm_obj
        bpy.ops.object.mode_set(mode="EDIT")

        for eb in arm.edit_bones:
            target = bone_map.get(eb.name)
            if target and target != eb.name and target in arm.edit_bones:
                eb.name = target

        bpy.ops.object.mode_set(mode="OBJECT")
        return {"FINISHED"}

    def _bake_animation(self, context: bpy.types.Context) -> None:
        """Bake the imported animation to keyframes on the armature."""
        arm_obj = bpy.data.objects.get(self._imported_armature)
        if arm_obj is None:
            return

        context.view_layer.objects.active = arm_obj
        arm_obj.select_set(True)

        frames = set()
        if arm_obj.animation_data and arm_obj.animation_data.action:
            for fc in arm_obj.animation_data.action.fcurves:
                for kp in fc.keyframe_points:
                    frames.add(int(kp.co[0]))

        if not frames:
            return

        start = min(frames)
        end = max(frames)

        bpy.ops.object.mode_set(mode="POSE")
        bpy.ops.nla.bake(
            frame_start=start,
            frame_end=end,
            step=1,
            only_selected=False,
            visual_keyings=True,
            clear_constraints=False,
            clear_parents=False,
            bake_types={"POSE"},
        )
        bpy.ops.object.mode_set(mode="OBJECT")


# ---------------------------------------------------------------------------
# Operator: Bake Animation
# ---------------------------------------------------------------------------


class VISIONMOCAP_OT_bake_animation(Operator):
    """Bake the active armature's animation to keyframes."""

    bl_idname = "visionmocap.bake_animation"
    bl_label = "Bake Animation"
    bl_description = "Bake the active armature animation to keyframes"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context: bpy.types.Context) -> set[str]:
        arm_obj = context.active_object
        if arm_obj is None or arm_obj.type != "ARMATURE":
            self.report({"ERROR"}, "Select an armature first.")
            return {"CANCELLED"}

        if not context.scene.frame_start or not context.scene.frame_end:
            self.report({"ERROR"}, "Set the scene frame range first.")
            return {"CANCELLED"}

        context.view_layer.objects.active = arm_obj
        bpy.ops.object.mode_set(mode="POSE")
        bpy.ops.nla.bake(
            frame_start=context.scene.frame_start,
            frame_end=context.scene.frame_end,
            step=1,
            only_selected=False,
            visual_keyings=True,
            clear_constraints=False,
            clear_parents=False,
            bake_types={"POSE"},
        )
        bpy.ops.object.mode_set(mode="OBJECT")
        self.report({"INFO"}, "Animation baked.")
        return {"FINISHED"}
