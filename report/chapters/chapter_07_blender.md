# Chapter 7: Blender Integration

## 7.1 Overview

VisionMoCap includes a fully functional Blender add-on for importing
BVH exports with automatic rig mapping.  The add-on is self-contained
and installable as a `.zip` file.

## 7.2 Add-on Architecture

The add-on (`src/blender/addon/`) consists of three modules:

- **`__init__.py`** — Registration, `bl_info` metadata
- **`operators.py`** — Two operators:
  - `VISIONMOCAP_OT_import_bvh`: Imports BVH using Blender's built-in
    importer, remaps bone names to Mixamo or Rigify conventions, and
    optionally bakes animation to keyframes
  - `VISIONMOCAP_OT_bake_animation`: Bakes any armature's animation
    to keyframes with a single click
- **`panels.py`** — `VISIONMOCAP_PT_main` panel in the 3D View
  sidebar (N key → VisionMoCap tab)

## 7.3 Rig Mapping

The operator maps BVH bone names to target rig conventions:

**Mixamo:** Hips → Spine → Spine1 → Spine2 → Neck → Head …
**Rigify:** Hips → spine → spine.001 → spine.002 → neck → head …

## 7.4 Bridge Class

`BlenderExporter` (`src/blender/exporter.py`) runs outside Blender on
the VisionMoCap side.  It:
1. Exports the current animation as a temporary BVH file
2. Optionally launches Blender with the add-on pre-loaded
