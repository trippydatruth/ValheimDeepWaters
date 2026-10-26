# The oilskin coat's trim, worn with the half-painted coat: a wide belt at the waist (hiding where the painted coat
# meets the skirt model) with a brass buckle at the front, and a cuff round each wrist where the painted sleeves end.
# The belt follows the outside of the skirt (and the body across the open front), weighted like the skirt top under
# it; the cuffs follow the forearms, weighted like the skin under them. Exported like the other gear: trim + fitref +
# the skeleton, in centimetres.   blender -b <coat>.blend --python build_coat_trim.py
#   env: VDW_OUT (folder), VDW_NAME (default fisher_coat_trim_v1), VDW_BELT_Z (m, belt centre; default the skirt's top
#        edge), VDW_BELT_W (cm wide, 7), VDW_CUFF_W (cm wide, 5)
import bpy, bmesh, os, math
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.interpolate import poly_3d_calc

OUT = os.environ["VDW_OUT"]; NAME = os.environ.get("VDW_NAME", "fisher_coat_trim_v1")
os.makedirs(OUT, exist_ok=True)
path = os.path.join(OUT, NAME + ".fbx")
if os.path.exists(path): raise SystemExit("exists, kept: " + path)
for o in list(bpy.data.objects):
    if o.mode != 'OBJECT' and o.name in bpy.context.view_layer.objects:
        bpy.context.view_layer.objects.active = o; bpy.ops.object.mode_set(mode='OBJECT')
arm = bpy.data.objects["Armature"]
for pb in arm.pose.bones: pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.rotation_euler = (0, 0, 0); pb.scale = (1, 1, 1)
bpy.context.view_layer.update()
coat, fit = bpy.data.objects["coat"], bpy.data.objects["fitref"]
BW = float(os.environ.get("VDW_BELT_W", "7")) / 100; CW = float(os.environ.get("VDW_CUFF_W", "5")) / 100
BONES = set(b.name for b in arm.data.bones if not b.name.startswith("vdw_skirt"))

def world_mesh(o):
    dg = bpy.context.evaluated_depsgraph_get(); e = o.evaluated_get(dg); me = e.to_mesh()
    vs = [e.matrix_world @ v.co for v in me.vertices]; polys = [tuple(p.vertices) for p in me.polygons]
    e.to_mesh_clear(); return vs, polys
fv, fp = world_mesh(fit); cv, cp = world_mesh(coat)
body_t = BVHTree.FromPolygons(fv, fp); coat_t = BVHTree.FromPolygons(cv, cp)
# the torso alone, for the belt (the arms hang beside the waist: rays from outside hit them first)
_fn = {g.index: g.name for g in fit.vertex_groups}
def _armish(i): return sum(g.weight for g in fit.data.vertices[i].groups if any(k in _fn[g.group] for k in ("Arm", "Hand"))) > 0.5
torso_t = BVHTree.FromPolygons(fv, [p for p in fp if not any(_armish(i) for i in p)])
def weights_at(obj, verts, polys, tree, p):
    loc, n, idx, d = tree.find_nearest(p)
    poly = polys[idx]; ws = poly_3d_calc([verts[i] for i in poly], loc); names = {g.index: g.name for g in obj.vertex_groups}; out = {}
    for i, w in zip(poly, ws):
        for g in obj.data.vertices[i].groups:
            nm = names[g.group]
            if nm in BONES: out[nm] = out.get(nm, 0) + g.weight * w
    top = sorted(out.items(), key=lambda kv: -kv[1])[:4]; s = sum(x for _, x in top) or 1
    return {k: x / s for k, x in top}

out = bmesh.new(); uvl = out.loops.layers.uv.new("UVMap"); dl = out.verts.layers.deform.verify()
names = sorted(BONES); idx_of = {n: i for i, n in enumerate(names)}
mat_of_face = {}
def vert(p, w):
    v = out.verts.new(p)
    for k, x in w.items(): v[dl][idx_of[k]] = x
    return v
def band(rows, u_of, mat, closed=True):
    """rows: list of rings (lists of (point, weights)), joined ring to ring into quads"""
    vr = [[vert(p, w) for p, w in r] for r in rows]
    n = len(vr[0])
    for a in range(len(vr) - 1):
        for i in range(n if closed else n - 1):
            j = (i + 1) % n
            q = [vr[a][i], vr[a][j], vr[a + 1][j], vr[a + 1][i]]
            try: f = out.faces.new(q)
            except ValueError: continue
            mat_of_face[f] = mat
            for l, (ri, ci) in zip(f.loops, ((a, i), (a, j), (a + 1, j), (a + 1, i))):
                l[uvl].uv = (0.15 + 0.7 * u_of(ci, n), 0.2 + 0.6 * ri / max(1, len(vr) - 1))
    return vr

# --- belt: round the torso at the skirt's top edge, on the outside of whatever is outermost (skirt or body)
skirt_top = max(p.z for p in cv if p.z < 1.5)
BZ = float(os.environ.get("VDW_BELT_Z", str(skirt_top - 0.01)))
ring_pts = [p for p in fv if abs(p.z - BZ) < 0.04 and abs(p.x) < 0.3]
cx = sum(p.x for p in ring_pts) / len(ring_pts); cy = sum(p.y for p in ring_pts) / len(ring_pts)
N = 40; BELT_OUT = 0.012; THICK = 0.006
BODY_EXTRA = 0.008          # across the open front it lies on the body, which bends most there (the stomach pushed through)
def surface(z, ang):
    """the outermost surface (skirt or torso) at this angle; on_body when it's the torso"""
    d = Vector((math.cos(ang), math.sin(ang), 0)); o = Vector((cx, cy, z)) + d * 0.6
    hits = [(t.ray_cast(o, -d, 1.0), t is torso_t) for t in (coat_t, torso_t)]
    hits = [(h, b) for h, b in hits if h[0] is not None]
    if not hits: return Vector((cx, cy, z)) + d * 0.15, d, True
    (h, b) = min(hits, key=lambda hb: hb[0][3]); return h[0], d, b
LEGS = ("LeftUpLeg", "RightUpLeg", "LeftLeg", "RightLeg")
def belt_weights(p, on_body):
    """the skin's weights where it lies on the body, the skirt's where it lies on the skirt; never the thighs (a belt
    goes round with the hips: following a thigh it bent with each step)"""
    w = weights_at(fit, fv, fp, body_t, p) if on_body else weights_at(coat, cv, cp, coat_t, p)
    legs = sum(w.pop(k, 0) for k in LEGS)
    if legs > 0: w["Hips"] = w.get("Hips", 0) + legs
    return w
rows = []
for z in (BZ - BW / 2, BZ + BW / 2):
    inner, outer = [], []
    for i in range(N):
        ang = 2 * math.pi * i / N - math.pi / 2                 # start at the front (-y)
        p, d, on_body = surface(z, ang)
        w = belt_weights(p, on_body); off = BELT_OUT + (BODY_EXTRA if on_body else 0)
        inner.append((p + d * off, w)); outer.append((p + d * (off + THICK), w))
    rows.append((inner, outer))
(b_in, b_out), (t_in, t_out) = rows
U = lambda i, n: i / n
band([b_out, t_out], U, "belt"); band([t_in, b_in], U, "belt")          # outside and inside faces
band([t_out, t_in], U, "belt"); band([b_in, b_out], U, "belt")          # top and bottom edges
# buckle: a brass frame at the front, standing just proud of the belt
fp0, fd, fb0 = surface(BZ, -math.pi / 2); fw = belt_weights(fp0, fb0)
c0 = fp0 + fd * (BELT_OUT + (BODY_EXTRA if fb0 else 0) + THICK + 0.004)
side, up = Vector((1, 0, 0)), Vector((0, 0, 1))
def frame(cen, wdt, hgt, bar, depth):
    o_ = [cen + side * sx * wdt / 2 + up * sy * hgt / 2 for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    i_ = [cen + side * sx * (wdt / 2 - bar) + up * sy * (hgt / 2 - bar) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    fr = [[(p, fw) for p in o_], [(p, fw) for p in i_]]
    bk = [[(p + fd * -depth, fw) for p in o_], [(p + fd * -depth, fw) for p in i_]]
    band([fr[0], fr[1]], U, "buckle"); band([bk[1], bk[0]], U, "buckle")
    band([bk[0], fr[0]], U, "buckle"); band([fr[1], bk[1]], U, "buckle")
frame(c0, 0.075, BW + 0.012, 0.012, 0.006)
# the tongue across the middle of the buckle
tw = [c0 + side * sx * 0.03 + up * sy * 0.004 for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
band([[(p, fw) for p in tw], [(p + fd * 0.004, fw) for p in tw]], U, "buckle")

# --- cuffs: round each forearm, ending at the wrist
cuffs = 0
for s in ("Left", "Right"):
    hand = arm.matrix_world @ arm.data.bones[s + "Hand"].head_local
    fore = arm.matrix_world @ arm.data.bones[s + "ForeArm"].head_local
    ax = (hand - fore).normalized(); ref = Vector((0, 0, 1)) if abs(ax.z) < 0.9 else Vector((1, 0, 0))
    e1 = ax.cross(ref).normalized(); e2 = ax.cross(e1).normalized()
    M = 20; rings = []
    for t, out_ in ((-0.01, 0.010), (CW * 0.5, 0.012), (CW, 0.010)):     # from just past the wrist back up the arm
        c = hand - ax * t; inn, outr = [], []
        for i in range(M):
            ang = 2 * math.pi * i / M; d = e1 * math.cos(ang) + e2 * math.sin(ang)
            h = body_t.ray_cast(c + d * 0.2, -d, 0.4)
            p = h[0] if h[0] is not None else c + d * 0.04
            w = weights_at(fit, fv, fp, body_t, p)
            inn.append((p + d * 0.004, w)); outr.append((p + d * out_, w))
        rings.append((inn, outr))
    band([r[1] for r in rings], U, "cuff")                                # the cuff's outside, flared in the middle
    band([rings[-1][0], rings[0][0]], U, "cuff")                          # inside
    band([rings[0][1], rings[0][0]], U, "cuff"); band([rings[-1][0], rings[-1][1]], U, "cuff")   # the two edges (the coat's own oilskin)
    cuffs += 1
bmesh.ops.recalc_face_normals(out, faces=[f for f, m in mat_of_face.items() if m in ("belt", "cuff")])
# both sides drawn (Unity culls back faces: parts of the belt vanished from some angles) - every face gets a reversed copy
for f, m in list(mat_of_face.items()):
    vs = [out.verts.new(v.co) for v in f.verts]
    for nv, ov in zip(vs, f.verts): nv[dl] = ov[dl]
    try: g = out.faces.new(list(reversed(vs)))
    except ValueError: continue
    for nl, ol in zip(g.loops, reversed(list(f.loops))): nl[uvl].uv = ol[uvl].uv
    mat_of_face[g] = m
me = bpy.data.meshes.new("coat_trim")
mats = ["belt", "buckle", "cuff"]
for m in mats: me.materials.append(bpy.data.materials.get(m) or bpy.data.materials.new(m))
for f, m in mat_of_face.items(): f.material_index = mats.index(m)
out.to_mesh(me); out.free()
for p in me.polygons: p.use_smooth = True
trim = bpy.data.objects.new("coat_trim", me); bpy.context.scene.collection.objects.link(trim)
for nm in names: trim.vertex_groups.new(name=nm)
# one mesh per material, named after it (the Unity importer finds each mesh's maps by its name: belt_Unity_*, buckle_Unity_*)
for o in bpy.data.objects: o.select_set(o == trim)
bpy.context.view_layer.objects.active = trim
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.separate(type='MATERIAL'); bpy.ops.object.mode_set(mode='OBJECT')
parts = [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith("coat_trim")]
for o in parts:
    m = o.data.materials[o.data.polygons[0].material_index].name if o.data.polygons else "belt"
    o.name = m + "_part"; o.data.name = m
for o in parts: o.name = o.name.replace("_part", "")
print(f"PARTS {[(o.name, len(o.data.polygons)) for o in parts]}")
print(f"TRIM belt at {BZ:.3f} m ({BW*100:.0f} cm wide, {N} round) with a buckle, {cuffs} cuffs: {len(me.polygons)} faces")

# into centimetres like the other gear, then out: trim + fitref (plain mesh) + skeleton
if arm.matrix_world != Matrix.Identity(4): raise SystemExit("the armature isn't at the origin")
for o in list(bpy.data.objects):
    if o is not arm and o not in parts and o.name != "fitref": bpy.data.objects.remove(o)
fit = bpy.data.objects["fitref"]
for m in [m for m in fit.modifiers if m.type == 'ARMATURE']: fit.modifiers.remove(m)
fit.data.transform(fit.matrix_world); fit.parent = None; fit.matrix_world = Matrix.Identity(4)
S = Matrix.Scale(100.0, 4)
for o in bpy.data.objects: o.select_set(o == arm)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
for b in arm.data.edit_bones: b.head = S @ b.head; b.tail = S @ b.tail
bpy.ops.object.mode_set(mode='OBJECT')
fit.data.transform(S)
for o in parts:
    o.data.transform(S); o.parent = arm
    o.modifiers.clear(); o.modifiers.new("Armature", 'ARMATURE').object = arm
for o in bpy.data.objects: o.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={'MESH', 'ARMATURE'}, global_scale=1.0, apply_unit_scale=True,
                         add_leaf_bones=False, use_armature_deform_only=False, armature_nodetype='NULL',
                         apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y', bake_space_transform=True,
                         mesh_smooth_type='FACE', bake_anim=False, path_mode='STRIP', embed_textures=False, colors_type='LINEAR')
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, NAME + ".blend"))
print("EXPORTED", path)
