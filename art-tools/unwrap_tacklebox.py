# Re-unwraps the tackle box so every UV island lies the same way: planks (Sanctus stylized_planks run along U) then run
# along the box. Each face is projected by the axis it faces most (box mapping):
#   faces looking front/back (Y)  -> U = X (along the box), V = Z
#   faces looking up/down (Z)     -> U = X, V = Y
#   faces looking at the ends (X) -> U = Y, V = Z
# Neighbouring faces of the same group stay joined (one island each); the islands are packed without rotation, all at
# the same texel size. Reads the rigged box (rig_tacklebox.py) and saves a copy.
#   blender -b tacklebox_rigged.blend --factory-startup --python unwrap_tacklebox.py   env: VDW_SAVE_TO
import bpy, bmesh, os
from mathutils import Vector

box = bpy.data.objects["tacklebox"]
for o in bpy.context.view_layer.objects: o.select_set(o is box)
bpy.context.view_layer.objects.active = box
bpy.ops.object.mode_set(mode='EDIT')
bm = bmesh.from_edit_mesh(box.data); uv = bm.loops.layers.uv.verify()
counts = {"Y": 0, "Z": 0, "X": 0}
for f in bm.faces:
    n = f.normal; ax = max(("X", abs(n.x)), ("Y", abs(n.y)), ("Z", abs(n.z)), key=lambda t: t[1])[0]
    counts[ax] += 1
    for l in f.loops:
        p = l.vert.co
        l[uv].uv = (p.x, p.z) if ax == "Y" else (p.x, p.y) if ax == "Z" else (p.y, p.z)
    # mirror back-facing projections so the texture isn't flipped (keeps planks' bevel the right way round)
    if (ax == "Y" and n.y > 0) or (ax == "Z" and n.z < 0) or (ax == "X" and n.x < 0):
        for l in f.loops: l[uv].uv = (-l[uv].uv[0], l[uv].uv[1])
bmesh.update_edit_mesh(box.data)
print(f"UNWRAP faces by direction: {counts}")
bpy.ops.mesh.select_all(action='SELECT')
# islands: split where the projection changes (the per-face UVs already differ there), then pack upright
bpy.ops.uv.select_all(action='SELECT')
try:
    bpy.ops.uv.pack_islands(udim_source='CLOSEST_UDIM', rotate=False, scale=True, merge_overlap=False, margin_method='FRACTION', margin=0.004, shape_method='CONCAVE')
except TypeError:
    bpy.ops.uv.pack_islands(rotate=False, margin=0.004)
bpy.ops.object.mode_set(mode='OBJECT')
import numpy as np
u = np.array([d.uv[:] for d in box.data.uv_layers.active.data]); print("UNWRAP uv range", u.min(0).round(3), u.max(0).round(3))
bpy.ops.wm.save_as_mainfile(filepath=os.environ["VDW_SAVE_TO"]); print("UNWRAP saved", os.environ["VDW_SAVE_TO"])
