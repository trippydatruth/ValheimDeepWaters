# UVs for the fisherman's gear, cut like a garment's pattern pieces, on whatever topology the meshes have now:
#   coat     - left front, right front, back (split at the side seams), each sleeve (cut along its underside), collar
#   shirt    - front, back, each sleeve (underside)
#   overalls - bib + front of the legs, back of the legs (side seams down the outside of each leg, inner-leg seam)
#   boots    - each boot: shaft cut down the back, the sole on its own
#   hat      - crown cut at the back, brim on its own (cut at the back)
# Islands are unwrapped angle-based (conformal for long tubes), packed per object with a margin, the user's seams on
# other edges cleared first. Writes a new .blend (VDW_SAVE_TO), UV layout previews (VDW_UV_PREVIEW prefix), and an FBX
# per object for Substance Painter (VDW_FBX_DIR, optional) - triangulated, no materials but one slot per piece.
#   blender -b fisher_gear_v1.blend --python gear_unwrap.py
import bpy, bmesh, math, os
import numpy as np
from mathutils import Vector

SAVE_TO = os.environ["VDW_SAVE_TO"]; PREV = os.environ.get("VDW_UV_PREVIEW"); FBX = os.environ.get("VDW_FBX_DIR")
PIECES = ["coat", "shirt", "overalls", "boots", "hat"]
body = bpy.data.objects.get("fitref") or bpy.data.objects.get("PlayerCharacter_01")
BV = np.array([(body.matrix_world @ v.co)[:] for v in body.data.vertices])
CY = float((BV[(BV[:, 2] > 100) & (BV[:, 2] < 160)][:, 1].min() + BV[(BV[:, 2] > 100) & (BV[:, 2] < 160)][:, 1].max()) / 2)
from mathutils.bvhtree import BVHTree
_bb = bmesh.new(); _bb.from_mesh(body.data); _bb.transform(body.matrix_world); BODY = BVHTree.FromBMesh(_bb)
def outer(f):
    """The cloth's outside layer (faces looking away from the body); its inside layer is cut off as its own islands."""
    c = f.calc_center_median(); loc, n, _i, d = BODY.find_nearest(c)
    if loc is None: return True
    away = (c - loc).normalized() if (c - loc).length > 1e-4 else n
    return f.normal.dot(away) > -0.25
print("\n===== GEAR UNWRAP =====")

def pca_axis(pts):
    c = pts.mean(0); u, s, vt = np.linalg.svd(pts - c); a = vt[0]
    return c, a / np.linalg.norm(a)

def tube_angle(p, c, axis, down):
    """Angle round a tube's axis, 0 on the side facing `down` (the seam goes there)."""
    d = p - c; d = d - axis * d.dot(axis)
    side = np.cross(axis, down)
    return math.atan2(d.dot(side), d.dot(down))

def cut(ob, region_of, tube_seams):
    """region_of(face) -> label; seams between labels, plus inside each tube label where the round angle wraps."""
    me = ob.data; bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
    for e in bm.edges: e.seam = False
    lab = {f: region_of(f) + ("" if outer(f) else ".in") for f in bm.faces}
    # tidy speckle: a face takes the label most of its neighbours have
    for _ in range(5):
        new = {}
        for f in bm.faces:
            nb = [lab[o] for e in f.edges for o in e.link_faces if o is not f]
            if nb:
                best = max(set(nb), key=nb.count)
                if nb.count(best) > len(nb) / 2 and best != lab[f]: new[f] = best
        lab.update(new)
    ang = {}
    for name, (c, axis, down) in tube_seams.items():
        for f in bm.faces:
            if lab[f] in (name, name + ".in"): ang[f] = tube_angle(np.array(f.calc_center_median()[:]), c, axis, down)
    n_seam = 0
    for e in bm.edges:
        if len(e.link_faces) != 2: continue
        a, b = e.link_faces
        s = lab[a] != lab[b]
        if not s and lab[a].replace(".in", "") in tube_seams and a in ang and b in ang:
            # the wrap: one face just one side of the seam line, the other just the other side
            s = ang[a] * ang[b] < 0 and abs(ang[a]) < 1.2 and abs(ang[b]) < 1.2
        if s: e.seam = True; n_seam += 1
    counts = {}
    for f in bm.faces: counts[lab[f]] = counts.get(lab[f], 0) + 1
    planar = [f.index for f in bm.faces if lab[f].replace(".in", "") in PLANAR]
    bm.to_mesh(me); bm.free()
    print(f"  {ob.name}: {n_seam} seam edges, regions {counts}")
    return planar

def regions_coat(ob):
    co = np.array([v.co[:] for v in ob.data.vertices])
    top = co[:, 2].max()
    arm_x = 24.0
    slv = {}
    for s, sgn in (("sleeve.L", 1), ("sleeve.R", -1)):
        pts = co[(co[:, 0] * sgn > arm_x + 4)]
        c, a = pca_axis(pts); a = a * (1 if a[0] * sgn > 0 else -1)
        slv[s] = (c, a, np.array([0.0, 0.0, -1.0]))
    def region(f):
        p = f.calc_center_median()
        if p.z > top - 7 and math.hypot(p.x, p.y - CY) < 19: return "collar"
        if abs(p.x) > arm_x and p.z > 112: return "sleeve.L" if p.x > 0 else "sleeve.R"
        side = math.atan2(p.y - CY, p.x)                     # front is -y
        if p.y - CY < 0 and abs(math.cos(side)) < 0.96: return "front.L" if p.x > 0 else "front.R"
        return "back" if p.y > CY else ("front.L" if p.x > 0 else "front.R")
    return region, slv

def regions_shirt(ob):
    co = np.array([v.co[:] for v in ob.data.vertices]); arm_x = 22.0
    slv = {}
    for s, sgn in (("sleeve.L", 1), ("sleeve.R", -1)):
        pts = co[(co[:, 0] * sgn > arm_x)]
        if len(pts) < 10: print(f"  shirt: no {s} found"); continue
        c, a = pca_axis(pts); slv[s] = (c, a, np.array([0.0, 0.0, -1.0]))
    def region(f):
        p = f.calc_center_median()
        if abs(p.x) > arm_x: return "sleeve.L" if p.x > 0 else "sleeve.R"
        return "front" if p.y < CY else "back"
    return region, slv

def regions_overalls(ob):
    def region(f):
        p = f.calc_center_median()
        if p.z < 95:                                          # the legs: front / back of each, so side and inner seams
            leg = "L" if p.x > 0 else "R"
            return ("front." if p.y < CY + 1.5 else "back.") + leg
        return "front" if p.y < CY else "back"
    return region, {}

def regions_boots(ob):
    def region(f):
        p = f.calc_center_median(); leg = "L" if p.x > 0 else "R"
        if f.normal.z < -0.7 and p.z < 3: return "sole." + leg
        return "boot." + leg
    tubes = {}
    co = np.array([v.co[:] for v in ob.data.vertices])
    for leg, sgn in (("L", 1), ("R", -1)):
        pts = co[(co[:, 0] * sgn > 0) & (co[:, 2] > 12)]
        c = pts.mean(0); tubes["boot." + leg] = (c, np.array([0.0, 0.0, 1.0]), np.array([0.0, 1.0, 0.0]))   # seam at the back (+y)
    return region, tubes

def regions_hat(ob):
    co = np.array([v.co[:] for v in ob.data.vertices]); c = co.mean(0)
    band = None
    def region(f):
        # the brim: faces mostly facing up/down and outside the crown's footprint; crown: the rest
        p = f.calc_center_median(); r = math.hypot(p.x - c[0], p.y - c[1])
        return "brim" if (abs(f.normal.z) > 0.55 and p.z < 192 and r > 13) or p.z < 183 else "crown"
    axis = np.array([0.0, 0.0, 1.0]); back = np.array([0.0, 1.0, 0.0])
    return region, {}

PLANAR = {"crown", "brim", "sole.L", "sole.R"}       # unwrapped as seen from above, not cut open
RULES = {"coat": regions_coat, "shirt": regions_shirt, "overalls": regions_overalls, "boots": regions_boots, "hat": regions_hat}

for name in PIECES:
    ob = bpy.data.objects.get(name)
    if ob is None: print(f"  {name}: not in the file"); continue
    region, tubes = RULES[name](ob)
    planar = set(cut(ob, region, tubes))
    for o in bpy.data.objects: o.select_set(o == ob)
    bpy.context.view_layer.objects.active = ob
    # replace the UVs on the active layer
    for p in ob.data.polygons: p.select = p.index not in planar
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_mode(type='FACE')
    bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=0.004)
    bpy.ops.object.mode_set(mode='OBJECT')
    if planar:
        uvl = ob.data.uv_layers.active.data
        for p in ob.data.polygons:
            if p.index in planar:
                for li in p.loop_indices:
                    v = ob.data.vertices[ob.data.loops[li].vertex_index].co
                    uvl[li].uv = (v.x * 0.01, v.y * 0.01 * (1 if p.normal.z >= 0 else -1))   # underside mirrored, so it isn't flipped
    for p in ob.data.polygons: p.select = True
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.average_islands_scale()
    bpy.ops.uv.pack_islands(rotate=True, margin=0.006)
    bpy.ops.object.mode_set(mode='OBJECT')
    # stretch check: UV area vs 3-D area per face
    me = ob.data; uvl = me.uv_layers.active.data
    ratios = []
    for p in me.polygons:
        uv = [uvl[i].uv for i in p.loop_indices]
        a = 0.0
        for k in range(1, len(uv) - 1):
            a += abs((uv[k].x - uv[0].x) * (uv[k + 1].y - uv[0].y) - (uv[k + 1].x - uv[0].x) * (uv[k].y - uv[0].y)) / 2
        if p.area > 1e-6: ratios.append(a / p.area)
    r = np.array(ratios); r = r / np.median(r)
    print(f"  {name}: texel density spread 10th {np.percentile(r, 10):.2f} / 90th {np.percentile(r, 90):.2f}, UV coverage {r.sum() * np.median(ratios):.0%}")

bpy.ops.wm.save_as_mainfile(filepath=SAVE_TO, copy=True); print("  saved", SAVE_TO)

if PREV:
    for name in PIECES:
        ob = bpy.data.objects.get(name)
        if ob is None: continue
        N = 1024; img = np.ones((N, N, 4), np.float32); img[..., :3] = 0.12
        me = ob.data; uvl = me.uv_layers.active.data
        for e in me.edges:
            pass
        for p in me.polygons:
            pts = [uvl[i].uv * (N - 1) for i in p.loop_indices]
            for k in range(len(pts)):
                a_, b_ = pts[k], pts[(k + 1) % len(pts)]
                n = int(max(abs(b_.x - a_.x), abs(b_.y - a_.y))) + 1
                for t in np.linspace(0, 1, n + 1):
                    x = int(a_.x + (b_.x - a_.x) * t); y = int(a_.y + (b_.y - a_.y) * t)
                    if 0 <= x < N and 0 <= y < N: img[y, x, :3] = (0.95, 0.8, 0.2)
        im = bpy.data.images.new(f"uv_{name}", N, N, alpha=True); im.pixels.foreach_set(img.ravel())
        im.filepath_raw = f"{PREV}_{name}.png"; im.file_format = 'PNG'; im.save()

if FBX:
    # one FBX for Substance Painter: the five pieces, each its own material (= its own texture set), in metres
    os.makedirs(FBX, exist_ok=True)
    path = os.path.join(FBX, "fisher_gear_painter.fbx")
    if os.path.exists(path): print("  exists, kept:", path)
    else:
        for o in bpy.data.objects: o.select_set(o.name in PIECES)
        bpy.context.view_layer.objects.active = bpy.data.objects[PIECES[0]]
        for name in PIECES:
            ob = bpy.data.objects[name]
            if ob.data.materials: ob.data.materials[0].name = name
        bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={'MESH'}, global_scale=0.01, apply_unit_scale=True,
                                 axis_forward='-Z', axis_up='Y', mesh_smooth_type='FACE', path_mode='STRIP',
                                 embed_textures=False, bake_anim=False)
        print("  exported", path)
print("===== END =====")
