import bpy

props = bpy.ops.nla.bake.get_rna_type().properties
print("PROBE nla.bake props:")
for p in props:
    print("PROBE  -", p.identifier, type(p).__name__)