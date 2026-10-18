# Moves a rigged rod's reel crank to the other side: every vertex of the reel's turning part (weighted to Reel.Spool -
# drum, line, crank and knob) is mirrored across the reel's own centre plane (normal = the spool axle, through the
# Reel.Spool pivot), faces turned back the right way out. Weights, UVs and bones are kept. With VDW_PARTS (comma list of
# loose-part indices) those parts are mirrored instead (a crank that isn't on the spool bone).
#   blender -b rod_<id>_rigged.blend --python flip_crank.py     env: VDW_SAVE_TO, VDW_PARTS
import bpy, bmesh, os
import numpy as np
from mathutils import Vector
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE'); mesh = next(o for o in bpy.data.objects if o.type == 'MESH')
sp = arm.data.bones["Reel.Spool"]
pv = arm.matrix_world @ sp.head_local; ax = (arm.matrix_world.to_3x3() @ (sp.tail_local - sp.head_local)).normalized()
inv = mesh.matrix_world.inverted(); pv_m = inv @ pv; ax_m = (inv.to_3x3() @ ax).normalized()
bm = bmesh.new(); bm.from_mesh(mesh.data); bm.verts.ensure_lookup_table()
# VDW_ROD_AXIS=1: mirror across the plane through the rod's own axis (the blank's centre line) instead of the spool pivot -
# for a reel whose pivot sits off to one side of its housing (a spinning reel's crank shaft)
if os.environ.get("VDW_ROD_AXIS") == "1":
    co_ = np.array([v.co[:] for v in bm.verts]); zr = co_[:, 2]; top = co_[zr > zr.min() + 0.6 * np.ptp(zr)]
    pv_m = Vector((float(np.median(top[:, 0])), float(np.median(top[:, 1])), pv_m.z))
if os.environ.get("VDW_PARTS"):
    # loose parts, in vertex order of first appearance
    comp = [-1] * len(bm.verts); c = 0
    for v in bm.verts:
        if comp[v.index] >= 0: continue
        st = [v]; comp[v.index] = c
        while st:
            x = st.pop()
            for e in x.link_edges:
                y = e.other_vert(x)
                if comp[y.index] < 0: comp[y.index] = c; st.append(y)
        c += 1
    want = {int(p) for p in os.environ["VDW_PARTS"].split(",")}
    sel = {v.index for v in bm.verts if comp[v.index] in want}
else:
    dl = bm.verts.layers.deform.active; gi = mesh.vertex_groups["Reel.Spool"].index
    sel = {v.index for v in bm.verts if v[dl].get(gi, 0.0) > 0.5}
for i in sel:
    v = bm.verts[i]; d = (v.co - pv_m).dot(ax_m); v.co -= ax_m * (2 * d)
faces = [f for f in bm.faces if all(v.index in sel for v in f.verts)]
bmesh.ops.reverse_faces(bm, faces=faces)
bm.to_mesh(mesh.data); bm.free(); mesh.data.update()
print(f"  mirrored {len(sel)} vertices ({len(faces)} faces) across the reel plane at {tuple(round(x, 3) for x in pv_m)}, axle {tuple(round(x, 2) for x in ax_m)}")
if os.environ.get("VDW_ROD_AXIS") == "1":
    # the turning part moved off its old pivot: the reel bones mirror across the same plane, so it still turns in place
    pw = mesh.matrix_world @ pv_m; aw = (mesh.matrix_world.to_3x3() @ ax_m).normalized()
    ainv = arm.matrix_world.inverted(); pa = ainv @ pw; aa = (ainv.to_3x3() @ aw).normalized()
    def mir(p): d = (p - pa).dot(aa); return p - aa * (2 * d)
    for o in bpy.data.objects: o.select_set(o == arm)
    bpy.context.view_layer.objects.active = arm; bpy.ops.object.mode_set(mode='EDIT')
    for n in ("Reel.Spool", "Reel.Axis"):
        eb = arm.data.edit_bones.get(n)
        if eb: h, t = mir(eb.head.copy()), mir(eb.tail.copy()); eb.head, eb.tail = h, t
    bpy.ops.object.mode_set(mode='OBJECT'); print("  reel bones mirrored with it")
bpy.ops.wm.save_as_mainfile(filepath=os.environ["VDW_SAVE_TO"]); print("  saved", os.environ["VDW_SAVE_TO"])
