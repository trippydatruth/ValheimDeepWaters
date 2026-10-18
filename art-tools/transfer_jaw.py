# Carries the user's jaw (bones + painted weights) from an older rig of the SAME mesh (same vertex order, e.g. before
# straightening) onto a new rig: the jaw groups are copied vertex by vertex (taking that weight away from the other
# groups, mostly the head), and the jaw bones are rebuilt on the new rig at the matching spot - each bone's head and tail
# are placed by the jaw vertices' positions (old -> new, averaged near each end), parented to Head.
#   blender -b new_rig.blend --python transfer_jaw.py      env: VDW_OLD (old .blend), VDW_JAWS "Upper.Jaw,Lower.Jaw", VDW_SAVE_TO
import bpy, os
import numpy as np
# a file saved in Edit / Weight Paint mode: back to Object Mode first (in Edit Mode the armature modifier is off, so
# nothing deforms, and edits in progress aren't in the mesh data)
for _o in list(bpy.data.objects):
    if _o.mode != 'OBJECT' and _o.name in bpy.context.view_layer.objects:
        bpy.context.view_layer.objects.active = _o
        try: bpy.ops.object.mode_set(mode='OBJECT')
        except RuntimeError: pass
from mathutils import Vector
JAWS = os.environ.get("VDW_JAWS", "Upper.Jaw,Lower.Jaw").split(",")
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
mesh = next(o for o in bpy.data.objects if o.type == 'MESH' and o.parent == arm)
with bpy.data.libraries.load(os.environ["VDW_OLD"]) as (src, dst): dst.objects = list(src.objects)
oarm = next(o for o in dst.objects if o and o.type == 'ARMATURE'); omesh = next(o for o in dst.objects if o and o.type == 'MESH' and o.parent == oarm)
if len(omesh.data.vertices) != len(mesh.data.vertices): raise SystemExit("meshes differ - can't copy by vertex")
o2a = oarm.matrix_world.inverted() @ omesh.matrix_world; n2a = arm.matrix_world.inverted() @ mesh.matrix_world
oco = np.array([(o2a @ v.co)[:] for v in omesh.data.vertices]); nco = np.array([(n2a @ v.co)[:] for v in mesh.data.vertices])
jw = {}
for jn in JAWS:
    gi = omesh.vertex_groups[jn].index
    jw[jn] = np.array([next((g.weight for g in v.groups if g.group == gi), 0.0) for v in omesh.data.vertices])
tot = sum(jw.values())
for v in mesh.data.vertices:
    t = float(tot[v.index])
    if t > 1e-4:
        for g in v.groups: g.weight *= (1 - min(t, 1.0))
for jn in JAWS:
    g = mesh.vertex_groups.get(jn) or mesh.vertex_groups.new(name=jn)
    for i in np.nonzero(jw[jn] > 1e-4)[0]: g.add([int(i)], float(jw[jn][i]), 'REPLACE')
    print(f"  {jn}: {int((jw[jn] > 0.01).sum())} points copied")
for o in bpy.context.view_layer.objects: o.select_set(o == mesh)
bpy.context.view_layer.objects.active = mesh
bpy.ops.object.vertex_group_normalize_all(lock_active=False)
# bones: map each old bone end into the new mesh through its nearest jaw vertices (their old -> new offset)
def map_pt(p_old, jn):
    m = jw[jn] > 0.3
    idx = np.nonzero(m)[0] if m.any() else np.arange(len(oco))
    d = np.linalg.norm(oco[idx] - p_old, axis=1); near = idx[np.argsort(d)[:12]]
    return p_old + (nco[near] - oco[near]).mean(0)
ends = {jn: (map_pt(np.array(oarm.data.bones[jn].head_local[:]), jn), map_pt(np.array(oarm.data.bones[jn].tail_local[:]), jn)) for jn in JAWS}
bpy.context.view_layer.objects.active = arm
for o in bpy.context.view_layer.objects: o.select_set(o == arm)
bpy.ops.object.mode_set(mode='EDIT'); eb = arm.data.edit_bones
for jn in JAWS:
    b = eb.get(jn) or eb.new(jn); b.head = Vector(ends[jn][0].tolist()); b.tail = Vector(ends[jn][1].tolist())
    b.use_deform = True; b.parent = eb["Head"]; b.use_connect = False
    print(f"  bone {jn}: head {tuple(ends[jn][0].round(3))} tail {tuple(ends[jn][1].round(3))}")
bpy.ops.object.mode_set(mode='OBJECT')
for o in dst.objects:
    if o: bpy.data.objects.remove(o)
bpy.ops.wm.save_as_mainfile(filepath=os.environ["VDW_SAVE_TO"]); print("  saved", os.environ["VDW_SAVE_TO"])
