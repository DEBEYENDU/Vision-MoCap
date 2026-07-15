"""UI panels for the VisionMoCap Blender add-on."""

from __future__ import annotations

import bpy
from bpy.types import Panel


class VISIONMOCAP_PT_main(Panel):
    """Main panel in the 3D View sidebar."""

    bl_label = "VisionMoCap"
    bl_idname = "VISIONMOCAP_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "VisionMoCap"

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout

        box = layout.box()
        box.label(text="Import", icon="IMPORT")
        box.operator(
            "visionmocap.import_bvh",
            text="Import BVH…",
            icon="ARMATURE_DATA",
        )

        box = layout.box()
        box.label(text="Baking", icon="ACTION")
        row = box.row()
        row.prop(context.scene, "frame_start")
        row.prop(context.scene, "frame_end")
        box.operator(
            "visionmocap.bake_animation",
            text="Bake Animation",
            icon="KEYINGSET",
        )

        box = layout.box()
        box.label(text="Info", icon="INFO")
        arm = context.active_object
        if arm and arm.type == "ARMATURE":
            box.label(text=f"Armature: {arm.name}")
            box.label(text=f"Bones: {len(arm.data.bones)}")
        else:
            box.label(text="No armature selected")
