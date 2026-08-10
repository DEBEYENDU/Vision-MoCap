import bpy

bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
bpy.ops.object.mode_set(mode="OBJECT")
obj = bpy.context.active_object
obj.animation_data_create()
act = bpy.data.actions.new("test")
obj.animation_data.action = act

slot = act.slots.new(name="slot", id_type="OBJECT")
h = slot.handle
print("PROBE handle type:", type(h).__name__)
print("PROBE handle py_type:", getattr(h, "py_type", None))
print("PROBE handle attrs:", [a for a in dir(h) if not a.startswith("_")][:60])
ch = h.channels
print("PROBE has channels:", hasattr(h, "channels"), type(h.channels).__name__ if hasattr(h, "channels") else None)
if hasattr(h, "channels") and hasattr(h.channels, "new"):
    print("PROBE channels.new method exists")