import bpy

BVH = r"C:\Users\GOD KAKAROT\VisionMoCap\demo\sample_exports\walk_cycle.bvh"
bpy.ops.import_anim.bvh(filepath=BVH, axis_forward="Z", axis_up="Y")
obj = [o for o in bpy.data.objects if o.type == "ARMATURE"][0]
act = obj.animation_data.action if obj.animation_data else None
print("PROBE action:", act)
for attr in ("fcurves", "frame_range", "duration", "layers", "slots"):
    print("PROBE has", attr, "=", hasattr(act, attr) if act else None)
if act and hasattr(act, "frame_range"):
    print("PROBE frame_range:", act.frame_range)
if act:
    print("PROBE slots:", len(act.slots), [ (s.name, list(getattr(s, "channels", []))[:2]) for s in act.slots ] if act.slots else None)
print("PROBE obj fcurves:", len(obj.animation_data.action.fcurves) if obj.animation_data and obj.animation_data.action else "none")