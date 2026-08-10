import bpy

bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
bpy.ops.object.mode_set(mode="OBJECT")
obj = bpy.context.active_object
obj.animation_data_create()
act = bpy.data.actions.new("test")
obj.animation_data.action = act

slot = act.slots.new(name="slot", id_type="OBJECT")
print("PROBE slot type:", type(slot).__name__)
print("PROBE slot attrs:", [a for a in dir(slot) if not a.startswith("_")])
if hasattr(slot, "channels"):
    print("PROBE channel elem attrs:", [a for a in dir(slot.channels) if not a.startswith("_")][:50])