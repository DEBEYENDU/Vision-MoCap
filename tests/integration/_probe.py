import bpy
print("PROBE action API")
tests = {
    "has_fcurves": hasattr(bpy.types.Action, "fcurves"),
    "has_layers": hasattr(bpy.types.Action, "layers"),
    "has_action_slots": hasattr(bpy.types, "ActionSlot"),
}
print("PROBE", tests)
for name in dir(bpy.types.Action):
    if "fcurve" in name.lower() or "layer" in name.lower() or "channel" in name.lower():
        print("PROBE attr:", name)