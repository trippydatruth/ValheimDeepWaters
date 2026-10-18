# Gives one-layer surfaces (single-face fins, spines, crests) a back side, so they still show in Unity, whose
# Standard shader culls back faces. A face is one-sided when a ray cast backward from it hits nothing, or hits the
# FRONT of some other surface (on a closed surface it always hits the back of the far wall first). Several rays
# per face (centre + toward each corner): any one saying "open" flags it, as does any face on an open edge. Each flagged face gets a reversed copy
# with the same UVs, material and bone weights.   env: VDW_SAVE_TO
import bpy, bmesh, os
# a file saved in Edit / Weight Paint mode: back to Object Mode first (in Edit Mode the armature modifier is off, so
# nothing deforms, and edits in progress aren't in the mesh data)
for _o in list(bpy.data.objects):
    if _o.mode != 'OBJECT' and _o.name in bpy.context.view_layer.objects:
        bpy.context.view_layer.objects.active = _o
        try: bpy.ops.object.mode_set(mode='OBJECT')
        except RuntimeError: pass
from mathutils.bvhtree import BVHTree

arm = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
mesh = next(o for o in bpy.data.objects if o.type == 'MESH' and (arm is None or o.parent == arm))
# Hand-edited (custom) normals don't survive a trip through bmesh: note them now and put them back afterwards.
custom = mesh.data.has_custom_normals
orig_normals = [l.normal.copy() for l in mesh.data.loops] if custom else []
orig_faces = len(mesh.data.polygons)
bm = bmesh.new(); bm.from_mesh(mesh.data); bm.normal_update(); bm.faces.ensure_lookup_table()
tree = BVHTree.FromBMesh(bm)
xs = [v.co for v in bm.verts]
L = max(max(c[i] for c in xs) - min(c[i] for c in xs) for i in range(3))

def open_behind(p, n):
    d = -n
    hit = tree.ray_cast(p + d * L * 1e-4, d, L * 3)
    return hit[0] is None or hit[1].dot(d) < 0

flag = []
for f in bm.faces:
    n = f.normal
    if n.length < 0.5: continue
    c = f.calc_center_median()
    pts = [c] + [c.lerp(v.co, 0.6) for v in f.verts]
    # also any face on an open edge: it's part of a sheet (stacked fins can fool the ray test)
    if any(e.is_boundary for e in f.edges) or any(open_behind(p, n) for p in pts):
        flag.append(f)

before = len(bm.faces)
res = bmesh.ops.duplicate(bm, geom=flag + list({e for f in flag for e in f.edges}) + list({v for f in flag for v in f.verts}))
new_faces = [g for g in res["geom"] if isinstance(g, bmesh.types.BMFace)]
bmesh.ops.reverse_faces(bm, faces=new_faces, flip_multires=False)

# The normals to put back: each original corner keeps its own; each corner of a reversed copy takes the reverse of the
# same corner on the face it was copied from. (Faces and corners keep their order through bmesh; copies come last.)
loop_normals = None
if custom:
    bm.faces.index_update(); bm.faces.ensure_lookup_table()
    starts = [p.loop_start for p in mesh.data.polygons]
    src_of = {}
    for a, b in res["face_map"].items():
        src, dst = (a, b) if a.index < before else (b, a)
        src_of[dst] = src
    vert_src = {}
    for a, b in res["vert_map"].items():
        vert_src[b] = a; vert_src.setdefault(a, a)
    loop_normals = list(orig_normals)
    for f in bm.faces[before:]:
        src = src_of[f]
        by_vert = {l.vert: orig_normals[starts[src.index] + i] for i, l in enumerate(src.loops)}
        for l in f.loops:
            n = by_vert.get(vert_src.get(l.vert, l.vert))
            loop_normals.append(-n if n is not None else -f.normal)

bm.to_mesh(mesh.data); bm.free(); mesh.data.update()
if loop_normals is not None and len(loop_normals) == len(mesh.data.loops):
    mesh.data.normals_split_custom_set(loop_normals)
    print(f"  kept the hand-set normals ({len(orig_normals)} corners) and gave the {len(new_faces)} copies reversed ones")
elif custom:
    print("  WARNING: couldn't carry the hand-set normals across (corner count changed)")
print(f"BACKFACES {mesh.name}: {len(flag)} of {before} faces were one-sided; added {len(new_faces)} reversed copies -> {len(mesh.data.polygons)} faces")
bpy.ops.wm.save_as_mainfile(filepath=os.environ["VDW_SAVE_TO"])
print("SAVED", os.environ["VDW_SAVE_TO"])
