"""VisionMoCap Blender Add-on — Import mocap data with rig mapping.

Install this add-on inside Blender (Edit → Preferences → Add-ons → Install…)
then find the panel in the 3D View sidebar (N key → VisionMoCap tab).
"""

from __future__ import annotations

bl_info = {
    "name": "VisionMoCap — Motion Capture Importer",
    "author": "VisionMoCap Team",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > VisionMoCap",
    "description": (
        "Import VisionMoCap BVH exports with automated "
        "Mixamo / Rigify rig mapping"
    ),
    "category": "Animation",
}

from .operators import (
    VISIONMOCAP_OT_import_bvh,
    VISIONMOCAP_OT_bake_animation,
)
from .panels import VISIONMOCAP_PT_main


_classes = (
    VISIONMOCAP_OT_import_bvh,
    VISIONMOCAP_OT_bake_animation,
    VISIONMOCAP_PT_main,
)


def register() -> None:
    from bpy.utils import register_class
    for cls in _classes:
        register_class(cls)


def unregister() -> None:
    from bpy.utils import unregister_class
    for cls in reversed(_classes):
        unregister_class(cls)
