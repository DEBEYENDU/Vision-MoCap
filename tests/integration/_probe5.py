import bpy

print("PROBE nla ops:", [op for op in dir(bpy.ops.nla) if not op.startswith("_")])
for mod in dir(bpy.ops):
    if mod in ("nla", "object", "anim"):
        pass
print("PROBE object ops:", [op for op in dir(bpy.ops.object) if "bak" in op or "anim" in op])
print("PROBE top ops bake:", [op for op in dir(bpy.ops) if "bak" in op])