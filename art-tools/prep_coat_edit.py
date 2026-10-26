# Readies a hand-edited coat for export_fisher_gear.py: the edited object becomes "coat" on the main Armature at rest.
#  - VDW_EDITED (default "coat.002") replaces "coat"; its own armature (a posed copy) is dropped
#  - back-face copies (a face duplicated facing the other way) are removed: the export makes the back faces itself
#  - points with no weights take their weighted neighbours' average
# Writes VDW_SAVE_TO; never touches the edited file.   blender -b <edited>.blend --python prep_coat_edit.py
import bpy, bmesh, os
from mathutils import Matrix
from mathutils.bvhtree import BVHTree

SAVE = os.environ["VDW_SAVE_TO"]
if os.path.exists(SAVE): raise SystemExit("exists, kept: " + SAVE)
for _o in list(bpy.data.objects):                                  # saved in Edit/Weight Paint mode: back to Object mode
    if _o.mode != 'OBJECT' and _o.name in bpy.context.view_layer.objects:
        bpy.context.view_layer.objects.active = _o; bpy.ops.object.mode_set(mode='OBJECT')
arm = bpy.data.objects["Armature"]
for pb in arm.pose.bones: pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.rotation_euler = (0, 0, 0); pb.scale = (1, 1, 1)
ed = bpy.data.objects[os.environ.get("VDW_EDITED", "coat.002")]
other_arm = next((m.object for m in ed.modifiers if m.type == 'ARMATURE' and m.object and m.object != arm), None)
if "coat" in bpy.data.objects and bpy.data.objects["coat"] != ed: bpy.data.objects.remove(bpy.data.objects["coat"])
mw = ed.matrix_world.copy()
ed.parent = None; ed.data.transform(mw); ed.matrix_world = Matrix.Identity(4)
for m in [m for m in ed.modifiers if m.type == 'ARMATURE']: ed.modifiers.remove(m)
ed.parent = arm; ed.modifiers.new("Armature", 'ARMATURE').object = arm
if other_arm is not None: bpy.data.objects.remove(other_arm)
ed.name = "coat"; ed.data.name = "coat"
missing = [g.name for g in ed.vertex_groups if g.name not in arm.data.bones]
if missing: raise SystemExit(f"vertex groups with no bone in the Armature: {missing}")

# back-face copies: of each pair facing opposite ways, keep the one facing away from the body
fit = bpy.data.objects["fitref"]; fb = bmesh.new(); fb.from_mesh(fit.data); fb.transform(fit.matrix_world); ft = BVHTree.FromBMesh(fb)
b = bmesh.new(); b.from_mesh(ed.data)
groups = {}
for f in b.faces: groups.setdefault(frozenset(v.co.to_tuple(5) for v in f.verts), []).append(f)
drop = []
for g in groups.values():
    if len(g) != 2 or g[0].normal.dot(g[1].normal) >= 0: continue
    c = g[0].calc_center_median(); loc, n, _i, d = ft.find_nearest(c)
    out = (c - loc).normalized() if loc is not None and d > 1e-5 else n
    drop.append(g[0] if g[0].normal.dot(out) < g[1].normal.dot(out) else g[1])
bmesh.ops.delete(b, geom=drop, context='FACES')
bmesh.ops.remove_doubles(b, verts=b.verts, dist=1e-6)            # the copies' points, now shared
b.to_mesh(ed.data); b.free(); ed.data.update()
print(f"PREP removed {len(drop)} back-face copies; coat now {len(ed.data.vertices)} points, {len(ed.data.polygons)} faces")

# unweighted points: their neighbours' weights (repeated, so a run of them fills in from the edge)
me = ed.data; names = {g.index: g.name for g in ed.vertex_groups}
adj = {v.index: set() for v in me.vertices}
for e in me.edges: a, c = e.vertices; adj[a].add(c); adj[c].add(a)
def wts(i): return {names[g.group]: g.weight for g in me.vertices[i].groups if g.weight > 0.001}
todo = [v.index for v in me.vertices if sum(g.weight for g in v.groups) < 0.01]
filled = 0
for _ in range(10):
    left = []
    for i in todo:
        acc = {}; nb = [j for j in adj[i] if j not in todo]
        if not nb: left.append(i); continue
        for j in nb:
            for k, x in wts(j).items(): acc[k] = acc.get(k, 0) + x / len(nb)
        for k, x in acc.items(): ed.vertex_groups[k].add([i], x, 'REPLACE')
        filled += 1
    if not left or len(left) == len(todo): todo = left; break
    todo = left
print(f"PREP weighted {filled} points from their neighbours; {len(todo)} still unweighted")
bpy.ops.wm.save_as_mainfile(filepath=SAVE, copy=True)
print("SAVED", SAVE)
