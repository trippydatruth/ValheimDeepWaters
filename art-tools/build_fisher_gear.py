# Fisherman's gear (armour set) around the Valheim player body, from the user's fishermengear.blend:
#   chest  = shirt (the user's, fixed) + an open oilskin raincoat (built here): one model, the body slot, so a cape
#            (Jormungandr's Scale) still goes over it
#   legs   = bib overalls (the user's, fixed) + black rubber boots (built here)
#   helmet = a sou'wester (built here, after the user's first reference photo)
# Everything is modelled in the scene's units (cm), which are the game's body mesh space x 1e-4 (checked against the
# rip's body.asset: same 975/1010 points, no axis change). Each FBX carries a copy of the body ("fitref") so the mod can
# find that mapping again whatever the importer does, and vertex colour R = how much a vertex follows one bone rigidly
# (hat: the head; coat skirt: the hips) instead of the body under it.
#   blender -b fishermengear.blend --python build_fisher_gear.py
#   env: VDW_OUT (the Fishermen gear folder), VDW_BODY_ASSET (rip body.asset, for the bone regions), VDW_RENDER (png prefix)
import bpy, bmesh, math, os, re, struct
def sm(e0, e1, x):
    import numpy as _np
    q = _np.clip((x - e0) / (e1 - e0), 0, 1); return q * q * (3 - 2 * q)
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

OUT = os.environ["VDW_OUT"]
for d in ("Blender Files", "Models", "Textures", "Previews"): os.makedirs(os.path.join(OUT, d), exist_ok=True)
sc = bpy.context.scene
print("\n===== FISHER GEAR =====")

# ---------------------------------------------------------------- the body, its bone regions
body_ob = bpy.data.objects['PlayerCharacter_01']
def world_mesh(ob, name):
    me = ob.data.copy(); me.name = name; me.transform(ob.matrix_world)
    for v in me.vertices: pass
    return me
body_me = world_mesh(body_ob, "body_world")
BV = np.array([v.co[:] for v in body_me.vertices])

def body_asset_regions(path):
    """Dominant bone index per vertex of the rip's body.asset, and its positions (x 1e4 = scene cm)."""
    t = open(path, encoding="utf-8").read(); vd = t[t.index("m_VertexData:"):]
    n = int(re.search(r"m_VertexCount: (\d+)", vd).group(1))
    raw = bytes.fromhex(re.search(r"_typelessdata: ([0-9a-f]+)", vd).group(1))
    P = np.frombuffer(raw[:n * 40], np.float32).reshape(n, 10)[:, :3] * 1e4
    s2 = (n * 40 + 15) // 16 * 16; s2 = (s2 + n * 8 + 15) // 16 * 16        # stream 2 (weights, indices) after uv stream
    sk = np.frombuffer(raw[s2:s2 + n * 32], np.uint8).reshape(n, 32)
    W = sk[:, :16].copy().view(np.float32); I = sk[:, 16:].copy().view(np.uint32)
    return P, I[np.arange(n), W.argmax(1)]
AP, ADOM = body_asset_regions(os.environ["VDW_BODY_ASSET"])
kd = KDTree(len(AP))
for i, p in enumerate(AP): kd.insert(p, i)
kd.balance()
BONE = np.array([ADOM[kd.find(p)[1]] for p in BV])
print(f"  body: {len(BV)} points, fit to body.asset max error {max(kd.find(p)[2] for p in BV):.3f} cm")
HIPS, SPINE, SPINE1, SPINE2, NECK, HEAD, JAW = 0, 1, 2, 3, 4, 5, 6
SHOULDER, UPPERARM, FOREARM, HAND = (7, 26), (8, 27), (9, 28), (10, 29)
FINGERS = set(range(11, 26)) | set(range(30, 45))
UPLEG, LEG, FOOT, TOE = (45, 49), (46, 50), (47, 51), (48, 52)
ARMS = set(UPPERARM) | set(FOREARM) | set(HAND) | FINGERS

def bvh_of(meshes, face_filter=None):
    bm = bmesh.new()
    for me in meshes:
        tmp = bmesh.new(); tmp.from_mesh(me)
        if face_filter is not None and me == body_me:
            kill = [f for f in tmp.faces if not face_filter(f)]
            bmesh.ops.delete(tmp, geom=kill, context='FACES')
        tmpme = bpy.data.meshes.new("t"); tmp.to_mesh(tmpme); tmp.free(); bm.from_mesh(tmpme); bpy.data.meshes.remove(tmpme)
    bm.normal_update(); return BVHTree.FromBMesh(bm), bm
def face_bones(f): return {int(BONE[v.index]) for v in f.verts}
body_bvh, _ = bvh_of([body_me])

def gap_to(bvh, p):
    loc, nrm, i, d = bvh.find_nearest(p)
    if loc is None: return 1e9, Vector((0, 0, 1)), p
    s = 1 if (p - loc).dot(nrm) >= 0 else -1
    return s * d, nrm, loc

def push_out(me, refs, passes=6, reach=1e9):
    """Moves vertices out until each is at least its gap off every reference surface: refs = [(bvh, gap_fn(co))]."""
    for _ in range(passes):
        moved = 0; disp = np.zeros((len(me.vertices), 3))
        for v in me.vertices:
            for bvh, gfn in refs:
                g = gfn(v.co)
                if g is None: continue
                d, n, loc = gap_to(bvh, v.co)
                if -reach < d < g: disp[v.index] += np.array(n[:]) * (g - d); moved += 1
        if moved == 0: break
        # smooth the displacement a little so nothing spikes
        nb = [[] for _ in me.vertices]
        for e in me.edges: a, b = e.vertices; nb[a].append(b); nb[b].append(a)
        sm = np.array([disp[i] * 0.6 + (disp[nb[i]].mean(0) * 0.4 if nb[i] else 0) for i in range(len(disp))])
        sm = np.where(np.linalg.norm(sm, axis=1, keepdims=True) < np.linalg.norm(disp, axis=1, keepdims=True), disp, sm)
        for v in me.vertices: v.co += Vector(sm[v.index].tolist())
    me.update()

def outward(me, ref_bvh):
    """Consistent winding, then the whole thing turned so faces point away from what it covers."""
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    inward = 0
    for f in bm.faces:
        d, n, loc = gap_to(ref_bvh, f.calc_center_median())
        if (f.calc_center_median() - loc).dot(f.normal) < 0: inward += 1
    if inward > len(bm.faces) / 2: bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free(); me.update(); return inward

def link(name, me):
    o = bpy.data.objects.new(name, me); sc.collection.objects.link(o); return o
def solidify(ob, t, offset=-1.0):
    m = ob.modifiers.new("thick", 'SOLIDIFY'); m.thickness = t; m.offset = offset; m.use_even_offset = False; m.use_rim = True
    dg = bpy.context.evaluated_depsgraph_get(); me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), depsgraph=dg)
    ob.modifiers.clear(); old = ob.data; ob.data = me; bpy.data.meshes.remove(old)

# ---------------------------------------------------------------- 1. the user's shirt and overalls, fixed
shirt = link("shirt", world_mesh(bpy.data.objects['PlayerCharacter_01.001'], "shirt"))
over = link("overalls", world_mesh(bpy.data.objects['weighters'], "overalls"))
for ob in (shirt, over):
    flipped = outward(ob.data, body_bvh)
    print(f"  {ob.name}: {flipped} faces were facing into the body - turned")
push_out(shirt.data, [(body_bvh, lambda c: 0.8)])
shirt_bvh, _ = bvh_of([shirt.data])
# the overalls: off the body, over the shirt where they cover it; tucked into the boots below the knee
def over_gap(c): return 0.9
push_out(over.data, [(body_bvh, over_gap), (shirt_bvh, lambda c: 0.6 if c.z > 110 else None)])
BOOT_TOP = 43.0
bm = bmesh.new(); bm.from_mesh(over.data)
bmesh.ops.delete(bm, geom=[f for f in bm.faces if max(v.co.z for v in f.verts) < 30.0], context='FACES')
bm.to_mesh(over.data); bm.free()
for v in over.data.vertices:                       # snug below the boot top so the boots go over them
    if v.co.z < BOOT_TOP + 4:
        d, n, loc = gap_to(body_bvh, v.co); k = min(1.0, (BOOT_TOP + 4 - v.co.z) / 6.0)
        if d > 0.9: v.co = v.co - n * (d - 0.9) * k
over.data.update()
over_bvh, _ = bvh_of([over.data])

# ---------------------------------------------------------------- 2. the coat: one piece - the upper half offset from the body
# (torso, shoulders and sleeves in one continuous surface, so the sleeves are part of the coat), a skirt lofted down from
# its waist, an open front with straight edges and a turned-up collar
ENV_FACE = lambda f: not (face_bones(f) & (ARMS | {HEAD, JAW}))
torso_env_bvh, _ = bvh_of([body_me, shirt.data, over.data], ENV_FACE)
NT = 36
def section(z, cx, cy, ease):
    """Radius at each angle round (cx, cy) at height z: first front-facing hit from outside on body+shirt+overalls
    (arms left out), plus ease; holes (between the legs) bridged from the neighbours."""
    r = np.full(NT, np.nan)
    for k in range(NT):
        a = 2 * math.pi * k / NT; d = Vector((math.cos(a), math.sin(a), 0))
        loc, nrm, i, dist = torso_env_bvh.ray_cast(Vector((cx, cy, z)) + d * 80, -d, 80)
        if loc is not None and nrm.dot(d) > 0.05: r[k] = (Vector((loc.x - cx, loc.y - cy, 0))).length
    ok = ~np.isnan(r)
    if ok.sum() < 3: return None
    idx = np.arange(NT); r = np.interp(idx, idx[ok], r[ok], period=NT)
    for _ in range(3): r = np.maximum(r, (np.roll(r, 2) + np.roll(r, -2)) / 2)   # a coat hangs: no dips
    return r + ease
torso_pts = BV[np.isin(BONE, [HIPS, SPINE, SPINE1, SPINE2])]
CY0 = float((torso_pts[:, 1].min() + torso_pts[:, 1].max()) / 2)
def centre(z): return 0.0, CY0
COLLAR, HEM, WAIST = 168.0, 52.0, 100.0
front = -math.pi / 2
def opening(z):                     # half-angle of the open front, radians: a V at the collar, wider down to the hem
    t = (COLLAR - z) / (COLLAR - HEM)
    return math.radians(16 + 14 * min(1, t * 3) + 6 * t)
def angle_of(p): return math.atan2(p.y - CY0, p.x)
def from_front(a): return ((a - front + math.pi) % (2 * math.pi)) - math.pi
def joint(a, b):
    pa, pb = BV[BONE == a], BV[BONE == b]
    d = np.linalg.norm(pa[:, None] - pb[None], axis=2); i, j = np.unravel_index(np.argsort(d, axis=None)[:6], d.shape)
    return Vector(((pa[i].mean(0) + pb[j].mean(0)) / 2).tolist())

# upper: the body above the waist without head, hands and legs; sleeves cut square just short of the wrist
bm = bmesh.new(); bm.from_mesh(body_me)
drop = {HEAD, JAW} | set(HAND) | FINGERS | set(LEG) | set(FOOT) | set(TOE)
bmesh.ops.delete(bm, geom=[f for f in bm.faces if face_bones(f) & drop], context='FACES')
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.05)          # the body's seams (split for its UVs) closed
for side, sx in ((0, -1), (1, 1)):
    el, wr = joint(UPPERARM[side], FOREARM[side]), joint(FOREARM[side], HAND[side]); u = (wr - el).normalized()
    geom = [g for g in bm.verts[:] + bm.edges[:] + bm.faces[:] if (g.co.x if isinstance(g, bmesh.types.BMVert) else
            (g.verts[0].co.x if isinstance(g, bmesh.types.BMEdge) else g.calc_center_median().x)) * sx > 28]
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=wr - u * 2.0, plane_no=u, clear_outer=True)
bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, WAIST), plane_no=(0, 0, -1), clear_outer=True)
# the neck hole: what's round the neck above the collar line
bmesh.ops.delete(bm, geom=[f for f in bm.faces if all(v.co.z > COLLAR - 2 and math.hypot(v.co.x, v.co.y - CY0) < 11 for v in f.verts)], context='FACES')
# and a clean neckline along one plane (low at the front, higher at the back), round the neck only
def neck_z(y): return COLLAR + 0.22 * (y - CY0)
_ng = [g for g in bm.verts[:] + bm.edges[:] + bm.faces[:] if all(math.hypot(v.co.x, v.co.y - CY0) < 17 and v.co.z > COLLAR - 14 for v in (g.verts if not isinstance(g, bmesh.types.BMVert) else [g]))]
bmesh.ops.bisect_plane(bm, geom=_ng, plane_co=(0, CY0, COLLAR), plane_no=Vector((0, -0.22, 1)).normalized(), clear_outer=True)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
upper = link("coat_upper", bpy.data.meshes.new("coat_upper")); bm.to_mesh(upper.data); bm.free()
ss = upper.modifiers.new("ss", 'SUBSURF'); ss.levels = 1
dg = bpy.context.evaluated_depsgraph_get(); me_up = bpy.data.meshes.new_from_object(upper.evaluated_get(dg), depsgraph=dg)
bpy.data.objects.remove(upper)
# out from what it covers (body, shirt, overalls - one surface): every point set at its distance off that surface, then
# smoothed, a few times over, so it drapes evenly instead of showing every muscle; roomier down the sleeves
under_bvh, _ = bvh_of([body_me, shirt.data, over.data], lambda f: not (face_bones(f) & ({HEAD, JAW} | set(HAND) | FINGERS)))
def dist_for(p): return 3.0 + 1.2 * float(sm(32, 50, abs(p.x)))
bm = bmesh.new(); bm.from_mesh(me_up); bm.normal_update()
for v in bm.verts:                                   # a first step out along the body's normals
    n = v.normal.copy()
    if v.is_boundary and abs(v.co.z - WAIST) < 0.6: n.z = 0; n.normalize()
    v.co += n * dist_for(v.co)
inner = [v for v in bm.verts if not v.is_boundary]
for it in range(6):
    for v in bm.verts:
        loc, nrm, _i, d = under_bvh.find_nearest(v.co)
        if loc is None: continue
        dv = v.co - loc
        dirn = dv.normalized() if dv.length > 1e-4 and dv.dot(nrm) > 0 else nrm
        target = loc + dirn * dist_for(v.co)
        v.co = v.co.lerp(target, 0.7 if it < 5 else 1.0) if (it < 5 or (v.co - loc).length < dist_for(v.co) * 0.85) else v.co
    if it < 5:
        for _ in range(4): bmesh.ops.smooth_vert(bm, verts=inner, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
for v in bm.verts:
    if v.is_boundary and v.co.z < WAIST + 3: v.co.z = WAIST
bm.to_mesh(me_up); bm.free()
# open front: the faces in the V cut away, then the edge pulled onto the line of the opening so it runs straight
bm = bmesh.new(); bm.from_mesh(me_up)
bmesh.ops.delete(bm, geom=[f for f in bm.faces if abs(f.calc_center_median().x) < 26 and abs(from_front(angle_of(f.calc_center_median()))) < opening(f.calc_center_median().z)], context='FACES')
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
for v in bm.verts:
    if not v.is_boundary or abs(v.co.x) > 26 or v.co.z > COLLAR - 1: continue
    da = from_front(angle_of(v.co))
    if abs(da) < opening(v.co.z) + 0.35:
        r = math.hypot(v.co.x, v.co.y - CY0); a = front + math.copysign(opening(v.co.z), da)
        v.co.x, v.co.y = r * math.cos(a), CY0 + r * math.sin(a)
# skirt: the waist edge, in order round the back from one front edge to the other, lofted down and flared
bm.verts.ensure_lookup_table()
waist = [v for v in bm.verts if v.is_boundary and v.co.z < WAIST + 4]
for v in waist: v.co.z = WAIST
# walked along the edge itself (sorting by angle can step back and forth and leave holes), from the end at the
# wearer's left front edge round the back to the other
ws = set(waist)
nbr = {v: [e.other_vert(v) for e in v.link_edges if e.is_boundary and e.other_vert(v) in ws] for v in waist}
ends = [v for v in waist if len(nbr[v]) == 1]
cur = min(ends, key=lambda v: (angle_of(v.co) - (front + opening(WAIST))) % (2 * math.pi)) if ends else waist[0]
chain, prev_v = [cur], None
while True:
    nx = [w for w in nbr[cur] if w is not prev_v and w not in chain]
    if not nx: break
    prev_v, cur = cur, nx[0]; chain.append(cur)
waist = chain
print(f"  coat: upper half {len(bm.verts)} points, waist edge {len(waist)}")
wa = np.unwrap([angle_of(v.co) for v in waist]); wr_ = [math.hypot(v.co.x, v.co.y - CY0) for v in waist]
_seg = [0.0] + [(waist[i + 1].co - waist[i].co).length for i in range(len(waist) - 1)]
tpars = np.cumsum(_seg) / sum(_seg)                         # 0 at one front edge, 1 at the other, by length along the edge
print(f"  waist edge: {len(wa)} points from {math.degrees(wa[0]):.0f} to {math.degrees(wa[-1]):.0f} deg, steps back {int((np.diff(wa) * np.sign(wa[-1] - wa[0]) < 0).sum())}")
going = 1.0 if wa[-1] > wa[0] else -1.0
op0 = opening(WAIST); span0 = 2 * math.pi - 2 * op0
prev = waist
for z in np.linspace(WAIST, HEM, 13)[1:]:
    sec = section(z, 0.0, CY0, 0.0); f_ = (WAIST - z) / (WAIST - HEM)
    op = opening(z); span = 2 * math.pi - 2 * op; row = []
    for tpar, r0 in zip(tpars, wr_):
        a = (front + op + span * tpar) if going > 0 else (front - op - span * tpar)
        rs = float(np.interp(((a % (2 * math.pi)) / (2 * math.pi)) * NT, np.arange(NT + 1), np.append(sec, sec[0]))) if sec is not None else 0
        ease = 2.8 + 3.2 * f_ ** 1.3
        r = r0 * (1 + 0.12 * f_)
        r += max(0.0, rs + ease - r) * float(sm(0.0, 0.4, f_))          # out over the legs gradually, no step at the waist
        row.append(bm.verts.new((r * math.cos(a), CY0 + r * math.sin(a), z)))
    for k in range(len(row) - 1):
        bm.faces.new((prev[k], prev[k + 1], row[k + 1], row[k]))
    prev = row
coat_body = bpy.data.meshes.new("coat"); bm.to_mesh(coat_body); bm.free()
coat = link("coat", coat_body)
# quads all over (the drape came off the body's triangles), keeping its edges: front, hem, cuffs, neckline
def quad_remesh(ob, faces):
    for o in bpy.data.objects: o.select_set(o == ob)
    bpy.context.view_layer.objects.active = ob
    n0 = len(ob.data.polygons)
    try:
        bpy.ops.object.quadriflow_remesh(target_faces=faces, use_preserve_sharp=False, use_preserve_boundary=True, use_mesh_symmetry=False, seed=1)
        print(f"  {ob.name}: quad remesh {n0} -> {len(ob.data.polygons)} faces, all quads: {all(len(p.vertices) == 4 for p in ob.data.polygons)}")
    except Exception as ex:
        print(f"  {ob.name}: quad remesh failed ({ex}); joining triangles instead")
        bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.tris_convert_to_quads(); bpy.ops.object.mode_set(mode='OBJECT')
quad_remesh(coat, 2600)
quad_remesh(shirt, 700); push_out(shirt.data, [(body_bvh, lambda c: 0.8)])   # the user's shirt, in quads too
bm = bmesh.new(); bm.from_mesh(coat.data); bm.verts.ensure_lookup_table()
# collar: grown out of the coat's own neckline edge (one seamless mesh) - each edge point carries a column of quads in
# and up over the shoulder to round the neck, up 3 cm, then folded out and down; lower toward the front edges
_nk = BV[(BONE == NECK) & (BV[:, 2] > 171)]; NX = float(np.abs(_nk[:, 0]).max()) + 2.2; NY = float((_nk[:, 1].max() - _nk[:, 1].min()) / 2) + 2.2
NCY = float((_nk[:, 1].max() + _nk[:, 1].min()) / 2)
def neck_r(a): return 1.0 / math.sqrt((math.cos(a) / NX) ** 2 + (math.sin(a) / NY) ** 2)
# the neckline as one path along the coat's edge: from the top of one front edge, round the back of the neck, to the top
# of the other (the coat's whole edge is one loop - front edges, neckline, hem - so the path is the part of it over the top)
bnd = [v for v in bm.verts if v.is_boundary]
def on_front_edge(v): return abs(from_front(math.atan2(v.co.y - CY0, v.co.x))) < opening(v.co.z) + 0.3 and v.co.z > WAIST + 20
cL = max((v for v in bnd if on_front_edge(v) and v.co.x < 0), key=lambda v: v.co.z)
cR = max((v for v in bnd if on_front_edge(v) and v.co.x > 0), key=lambda v: v.co.z)
def bnext(v, prev):
    return [e.other_vert(v) for e in v.link_edges if e.is_boundary and e.other_vert(v) is not prev]
# step off the left corner the way that leads away from the front edge (round the neck), and follow the edge to the right corner
best = None
for first in bnext(cL, None):
    path, prev, cur = [cL], cL, first
    while cur is not cR and len(path) < 400:
        path.append(cur); nx = bnext(cur, prev)
        if not nx: break
        prev, cur = cur, nx[0]
    if cur is cR:
        path.append(cR)
        if best is None or max(v.co.z for v in path) > max(v.co.z for v in best) or len(path) < len(best): best = path
chain = [v for v in (best or [])]
chains = [chain]
op = opening(COLLAR) + 0.05; cols = []
for v in chain:
    a = math.atan2(v.co.y - CY0, v.co.x); d = Vector((math.cos(a), math.sin(a), 0)); r = neck_r(a)
    kt = 0.45 + 0.55 * float(sm(op, op + 0.7, abs(from_front(a))))
    back = max(0.0, d.y)                                    # 0 at the sides and front, 1 straight behind
    zt = max(neck_z(NCY + r * d.y) + 2.5 * back, v.co.z + 1.5)
    nk = Vector((r * d.x, NCY + r * d.y, zt)) + d * 0.4
    col = [v] + [bm.verts.new(v.co.lerp(nk, f)) for f in (0.33, 0.66)] + [bm.verts.new(nk)]
    for rr, dz in ((0.2, 3.0 + 1.5 * back), (1.6, 3.2 + 1.5 * back), (3.2, 1.4 + 0.8 * back)):
        col.append(bm.verts.new(nk + d * rr * kt + Vector((0, 0, dz * kt))))
    cols.append(col)
for i in range(len(cols) - 1):
    for j in range(len(cols[0]) - 1):
        bm.faces.new((cols[i][j], cols[i + 1][j], cols[i + 1][j + 1], cols[i][j + 1]))
# the band over the shoulders lifted clear of the body, shirt and overalls under it
for _ in range(3):
    for col in cols:
        for j, v in enumerate(col[1:4], 1):
            loc, nrm, _i, d = under_bvh.find_nearest(v.co)
            if loc is None: continue
            want = 2.6 if j < 3 else 1.6
            if (1 if (v.co - loc).dot(nrm) >= 0 else -1) * d < want: v.co = loc + nrm * want
bm.to_mesh(coat.data); bm.free()
print(f"  coat: collar grown from {len(chain)} neckline points ({len(chains)} edge piece(s) found), {len(chain) - 1} x {len(cols[0]) - 1} quads")
outward(coat.data, body_bvh)
# buttons: toggles down the wearer's left front edge (+x side of the opening) - painted on, so the coat stays one mesh
coat_bvh_, _ = bvh_of([coat.data])
bm = bmesh.new(); bm.from_mesh(coat.data)
BUTTON_AT = []
for z in (148, 134, 120, 106):
    a = front + opening(z) + 0.14; cx, cy = centre(min(z, 150)); d = Vector((math.cos(a), math.sin(a), 0))
    loc, nrm, _i, _d = coat_bvh_.ray_cast(Vector((cx, cy, z)) + d * 60, -d, 60)
    if loc is None: continue
    p = loc + nrm * 0.3; BUTTON_AT.append(p.copy())
bm.to_mesh(coat.data); bm.free()

# ---------------------------------------------------------------- 3. boots: the feet and shins, off the body, flat soles
bm = bmesh.new(); bm.from_mesh(body_me)
keep = set(FOOT) | set(TOE) | set(LEG)
bmesh.ops.delete(bm, geom=[f for f in bm.faces if not (face_bones(f) & keep) or min(v.co.z for v in f.verts) > BOOT_TOP], context='FACES')
bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, BOOT_TOP), plane_no=(0, 0, 1), clear_outer=True)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
bm.normal_update()
for v in bm.verts:                                    # out by 2.4 cm (2.8 round the ankle), never below the ground
    off = 2.4 + 0.4 * math.exp(-((v.co.z - 12) / 6) ** 2)
    n = v.normal.copy(); n.z *= 0.5
    v.co += n.normalized() * off
    if v.co.z < 0.0: v.co.z = 0.0
boots = link("boots", bpy.data.meshes.new("boots")); bm.to_mesh(boots.data); bm.free()
push_out(boots.data, [(over_bvh, lambda c: 0.7 if c.z > 28 else None)])
quad_remesh(boots, 900)
def keep_big(ob, n_keep):
    bm = bmesh.new(); bm.from_mesh(ob.data); seen = set(); parts = []
    for v in bm.verts:
        if v in seen: continue
        part, stack = [v], [v]; seen.add(v)
        while stack:
            x = stack.pop()
            for e in x.link_edges:
                w = e.other_vert(x)
                if w not in seen: seen.add(w); stack.append(w); part.append(w)
        parts.append(part)
    parts.sort(key=len, reverse=True)
    drop = [v for p in parts[n_keep:] for v in p]
    bmesh.ops.delete(bm, geom=drop, context='VERTS'); bm.to_mesh(ob.data); bm.free()
    print(f"  {ob.name}: kept {n_keep} pieces, dropped {len(parts) - n_keep} stray bits ({len(drop)} points)")
keep_big(boots, 2)
outward(boots.data, body_bvh)

# ---------------------------------------------------------------- 4. sou'wester (the user's first photo): a smooth dome, the brim long at the back
hp = BV[(BONE == HEAD) & (BV[:, 2] > 183)]
hc = Vector((0.0, float((hp[:, 1].min() + hp[:, 1].max()) / 2) + 1.0, 186.0))
RX = float(np.abs(hp[:, 0]).max()) + 2.4; RY = float((hp[:, 1].max() - hp[:, 1].min()) / 2) + 2.2; TOPZ = float(BV[:, 2].max()) + 3.2
def brim_z(ang):                      # the band: above the brows in front, lower at the back
    back = (math.sin(ang) + 1) / 2    # +y is the back
    return 193.0 - 7.0 * back
NH, NR = 32, 8
bm = bmesh.new(); crown = []
for j in range(NR):
    t = j / NR; row = []
    for k in range(NH):
        ang = 2 * math.pi * k / NH; zb = brim_z(ang)
        # an ellipsoid dome: from the band up to the top, its sides bulging a little like a filled sou'wester crown
        e = math.asin(min(1.0, max(-1.0, (zb - hc.z) / (TOPZ - hc.z)))); el = e + (math.pi / 2 - e) * t
        rx, ry = RX * math.cos(el) * (1 + 0.05 * math.sin(2 * el)), RY * math.cos(el) * (1 + 0.05 * math.sin(2 * el))
        row.append(bm.verts.new((hc.x + rx * math.cos(ang), hc.y + ry * math.sin(ang), hc.z + (TOPZ - hc.z) * math.sin(el))))
    crown.append(row)
top_v = bm.verts.new((hc.x, hc.y, TOPZ))
for j in range(NR - 1):
    for k in range(NH): bm.faces.new((crown[j][k], crown[j][(k + 1) % NH], crown[j + 1][(k + 1) % NH], crown[j + 1][k]))
bm.verts.remove(top_v)
TOP_IDS = set(range((NR - 1) * NH, NR * NH))   # the crown's top ring (filled with a quad grid below)
# brim: 5 cm at the front (tipped down a little), 7 at the sides, 13 at the back sloping down over the neck
prev = crown[0]
for step in (0.35, 0.7, 1.0):
    row = []
    for k in range(NH):
        ang = 2 * math.pi * k / NH; back = (math.sin(ang) + 1) / 2; side = abs(math.cos(ang))
        w = 5.0 + 2.0 * side + 8.0 * back ** 2; drop = math.radians(14 + 34 * back ** 1.5) + math.radians(8) * step
        d = Vector((math.cos(ang), math.sin(ang), 0)); c = crown[0][k].co
        row.append(bm.verts.new(c + d * w * step * math.cos(drop) - Vector((0, 0, w * step * math.sin(drop)))))
    for k in range(NH): bm.faces.new((prev[k], prev[(k + 1) % NH], row[(k + 1) % NH], row[k]))
    prev = row
hat = link("hat", bpy.data.meshes.new("hat")); bm.to_mesh(hat.data); bm.free()
for o in bpy.data.objects: o.select_set(o == hat)
bpy.context.view_layer.objects.active = hat
for v in hat.data.vertices: v.select = v.index in TOP_IDS
for e in hat.data.edges: e.select = all(i in TOP_IDS for i in e.vertices)
for p_ in hat.data.polygons: p_.select = False
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_mode(type='EDGE')
bpy.ops.mesh.fill_grid(span=8, offset=0); bpy.ops.object.mode_set(mode='OBJECT')
print(f"  hat: top filled - {sum(1 for p_ in hat.data.polygons if len(p_.vertices) != 4)} faces that aren't quads")
outward(hat.data, body_bvh)

# ---------------------------------------------------------------- 5. thickness, UVs
for ob, t in ((shirt, 0.25), (over, 0.35), (coat, 0.5), (boots, 0.4), (hat, 0.5)):
    bpy.context.view_layer.objects.active = ob
    for o in bpy.data.objects: o.select_set(o == ob)
    solidify(ob, t)
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.006)
    bpy.ops.object.mode_set(mode='OBJECT')
    for p in ob.data.polygons: p.use_smooth = True
    print(f"  {ob.name}: {len(ob.data.vertices)} verts, {len(ob.data.polygons)} faces")

# ---------------------------------------------------------------- 6. paint (texel -> body position) and rigidity colours
N = 1024
rng = np.random.default_rng(3)
def raster(ob):
    me = ob.data; uvl = me.uv_layers.active.data; me.calc_loop_triangles()
    co = np.array([v.co[:] for v in me.vertices]); vn = np.array([v.normal[:] for v in me.vertices])
    pos = np.zeros((N, N, 3), np.float32); nor = np.zeros((N, N, 3), np.float32); cov = np.zeros((N, N), bool)
    for tri in me.loop_triangles:
        uv = np.array([uvl[l].uv[:] for l in tri.loops]) * N; P3 = co[list(tri.vertices)]; N3 = vn[list(tri.vertices)]
        x0, y0 = np.maximum(np.floor(uv.min(0)).astype(int) - 1, 0); x1, y1 = np.minimum(np.ceil(uv.max(0)).astype(int) + 1, N - 1)
        if x1 < x0 or y1 < y0: continue
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        (ax, ay), (bx, by), (cx_, cy_) = uv; den = (by - cy_) * (ax - cx_) + (cx_ - bx) * (ay - cy_)
        if abs(den) < 1e-9: continue
        l1 = ((by - cy_) * (xs - cx_) + (cx_ - bx) * (ys - cy_)) / den; l2 = ((cy_ - ay) * (xs - cx_) + (ax - cx_) * (ys - cy_)) / den; l3 = 1 - l1 - l2
        ins = (l1 >= -0.03) & (l2 >= -0.03) & (l3 >= -0.03)
        if not ins.any(): continue
        yy, xx = (ys[ins] - 0.5).astype(int), (xs[ins] - 0.5).astype(int)
        pos[yy, xx] = l1[ins, None] * P3[0] + l2[ins, None] * P3[1] + l3[ins, None] * P3[2]
        nor[yy, xx] = l1[ins, None] * N3[0] + l2[ins, None] * N3[1] + l3[ins, None] * N3[2]; cov[yy, xx] = True
    for _ in range(4):
        acc = np.zeros_like(pos); nacc = np.zeros_like(pos); n = np.zeros((N, N))
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            sh = np.roll(np.roll(cov, dy, 0), dx, 1); acc += np.roll(np.roll(pos, dy, 0), dx, 1) * sh[..., None]
            nacc += np.roll(np.roll(nor, dy, 0), dx, 1) * sh[..., None]; n += sh
        new = ~cov & (n > 0); pos[new] = acc[new] / n[new, None]; nor[new] = nacc[new] / n[new, None]; cov |= new
    return pos, nor, cov
def noise3(pos, scale, seed):
    r = np.random.default_rng(seed); n = int(260 / scale) + 4; g = r.random((n, n, n)).astype(np.float32)
    q = (pos - np.array([-100, -100, -30])) / scale; i = np.floor(q).astype(int); f = q - i; f = f * f * (3 - 2 * f); i = np.clip(i, 0, n - 2)
    out = 0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (f[..., 0] if dx else 1 - f[..., 0]) * (f[..., 1] if dy else 1 - f[..., 1]) * (f[..., 2] if dz else 1 - f[..., 2])
                out = out + w * g[i[..., 0] + dx, i[..., 1] + dy, i[..., 2] + dz]
    return out
def sm(e0, e1, x): q = np.clip((x - e0) / (e1 - e0), 0, 1); return q * q * (3 - 2 * q)
def mix(a, b, w): return np.asarray(a, np.float32) * (1 - w[..., None]) + np.asarray(b, np.float32) * w[..., None]
def save(arr, path, nc=False):
    if os.path.exists(path): print("  exists, kept:", path); return bpy.data.images.load(path)
    rgba = np.ones((N, N, 4), np.float32); rgba[..., :arr.shape[-1]] = arr
    im = bpy.data.images.new(os.path.basename(path), N, N, alpha=True)
    if nc: im.colorspace_settings.name = 'Non-Color'
    im.pixels.foreach_set(rgba.ravel()); im.filepath_raw = path; im.file_format = 'PNG'; im.save(); return im
def write_set(name, alb, smooth, height, metal=0.0, bump=3.0):
    d = os.path.join(OUT, "Textures", name); os.makedirs(d, exist_ok=True); p = lambda k: os.path.join(d, f"{name}_Unity_{k}.png")
    ms = np.zeros((N, N, 4), np.float32); ms[..., :3] = metal; ms[..., 3] = smooth
    gx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * bump; gy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * bump
    nn = np.stack([-gx, -gy, np.ones_like(gx)], -1); nn /= np.linalg.norm(nn, axis=-1, keepdims=True)
    return {"Albedo": save(np.clip(alb, 0, 1), p("Albedo")), "MetallicSmoothness": save(np.clip(ms, 0, 1), p("MetallicSmoothness"), True),
            "Normal": save(nn * 0.5 + 0.5, p("Normal"), True)}

YELLOW = (0.96, 0.74, 0.06)
def oilskin(pos, nor, base, seed):
    """Waxed / rubberised cloth: big soft creases and a fine crinkle in the height, darker in the creases."""
    crease = noise3(pos, 14.0, seed) * 0.55 + noise3(pos, 5.0, seed + 1) * 0.3 + noise3(pos, 1.6, seed + 2) * 0.15
    h = crease; alb = np.broadcast_to(np.asarray(base, np.float32), pos.shape).copy() * (0.9 + 0.16 * crease[..., None])
    return alb, h
maps = {}
# shirt: navy and cream stripes round the body (pic 2)
pos, nor, cov = raster(shirt)
st = (np.sin(pos[..., 2] / 3.4 * math.pi) > 0.15).astype(np.float32)
alb = mix((0.92, 0.90, 0.84), (0.08, 0.11, 0.24), st) * (0.92 + 0.1 * noise3(pos, 2.0, 5)[..., None])
maps["shirt"] = write_set("shirt", alb, 0.2, 0.3 * noise3(pos, 1.5, 6) + 0.1 * st, bump=2.0)
# overalls: yellow oilskin, darker straps and a chrome clasp at each strap's front
pos, nor, cov = raster(over)
alb, h = oilskin(pos, nor, (0.93, 0.66, 0.05), 11)
seam = sm(0.25, 0.0, np.abs(pos[..., 0]))  * (pos[..., 2] < 100)   # front fly seam
alb = mix(alb, (0.55, 0.38, 0.03), seam * 0.6)
clasp = np.zeros(pos.shape[:2], np.float32)
for sx in (-9.0, 9.0):
    clasp = np.maximum(clasp, sm(1.3, 0.8, np.hypot(pos[..., 0] - sx, pos[..., 2] - 147.0)) * (pos[..., 1] < 0))
alb = mix(alb, (0.75, 0.76, 0.78), clasp)
maps["overalls"] = write_set("overalls", alb, 0.62 + 0.25 * clasp, 0.6 * h - 0.6 * seam, metal=0.0, bump=2.0)
# coat: yellow oilskin, black toggles, pocket flaps, seam lines, a darker inside
pos, nor, cov = raster(coat)
alb, h = oilskin(pos, nor, YELLOW, 21)
btn = np.zeros(pos.shape[:2], np.float32)
for bp in BUTTON_AT:
    btn = np.maximum(btn, sm(1.25, 0.95, np.linalg.norm(pos - np.array(bp[:]), axis=-1)))
pocket = np.zeros(pos.shape[:2], np.float32)
for sx in (-1, 1):
    in_x = sm(5, 4, np.abs(np.abs(pos[..., 0]) - 15)) * (np.sign(pos[..., 0]) == sx)
    pocket = np.maximum(pocket, in_x * sm(0.6, 0.0, np.abs(pos[..., 2] - 100)) * (pos[..., 1] < 0))
alb = mix(alb, (0.55, 0.40, 0.02), pocket * 0.8)
alb = mix(alb, (0.04, 0.04, 0.05), btn)
inside = np.clip(-(nor * 0).sum(-1), 0, 1)
maps["coat"] = write_set("coat", alb, np.clip(0.7 + 0.15 * btn - 0.1 * pocket, 0, 1), 0.6 * h - 0.8 * pocket + 0.5 * btn, bump=2.0)
# boots: black rubber, a dark grey sole band and a rolled top
pos, nor, cov = raster(boots)
sole = sm(2.6, 1.8, pos[..., 2]); rim = sm(BOOT_TOP - 3.5, BOOT_TOP - 2.5, pos[..., 2])
alb = mix(np.full(pos.shape, 0.035, np.float32) * (0.85 + 0.3 * noise3(pos, 2.0, 31)[..., None]), (0.16, 0.15, 0.14), sole)
alb = mix(alb, (0.06, 0.06, 0.065), rim)
maps["boots"] = write_set("boots", alb, 0.78 - 0.45 * sole, 0.3 * noise3(pos, 4.0, 32) + 0.5 * rim - 0.4 * sole + 0.2 * (np.sin(pos[..., 0] * 3) > 0.6) * sole, bump=4.0)
# hat: yellow oilskin with stitched panel seams on the crown and rows of stitching on the brim
pos, nor, cov = raster(hat)
alb, h = oilskin(pos, nor, YELLOW, 41)
ang = np.arctan2(pos[..., 1] - hc.y, pos[..., 0] - hc.x)
panel = sm(0.465, 0.49, np.abs(((ang / (2 * math.pi) * 6) % 1) - 0.5)) * (pos[..., 2] > 193.5)
rr = np.hypot(pos[..., 0] - hc.x, pos[..., 1] - hc.y)
stitch = ((np.sin(rr * 2.4) > 0.92) & (pos[..., 2] < 191)).astype(np.float32)
alb = mix(alb, (0.62, 0.45, 0.02), np.clip(panel + 0.6 * stitch, 0, 1))
maps["hat"] = write_set("hat", alb, 0.72, 0.6 * h + 0.4 * panel + 0.3 * stitch, bump=2.0)

def material(name, imgs):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; Nn, L = nt.nodes, nt.links
    b = next(n for n in Nn if n.type == 'BSDF_PRINCIPLED')
    def tex(k, y):
        t = Nn.new("ShaderNodeTexImage"); t.image = imgs[k]; t.location = (-700, y); return t
    L.new(tex("Albedo", 300).outputs["Color"], b.inputs["Base Color"])
    s = tex("MetallicSmoothness", 0); s.image.colorspace_settings.name = 'Non-Color'
    sep = Nn.new("ShaderNodeSeparateColor"); L.new(s.outputs["Color"], sep.inputs["Color"]); L.new(sep.outputs["Red"], b.inputs["Metallic"])
    inv = Nn.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
    L.new(s.outputs["Alpha"], inv.inputs[1]); L.new(inv.outputs["Value"], b.inputs["Roughness"])
    nn = tex("Normal", -320); nn.image.colorspace_settings.name = 'Non-Color'; nm = Nn.new("ShaderNodeNormalMap")
    L.new(nn.outputs["Color"], nm.inputs["Color"]); L.new(nm.outputs["Normal"], b.inputs["Normal"])
    return m
for ob in (shirt, over, coat, boots, hat):
    ob.data.materials.clear(); ob.data.materials.append(material(ob.name, maps[ob.name]))

# rigidity (vertex colour R): the hat moves with the head alone; the coat's skirt more and more with the hips toward the hem
def set_rigid(ob, fn):
    ca = ob.data.color_attributes.new("rigid", 'FLOAT_COLOR', 'POINT')
    for v in ob.data.vertices: r = float(fn(v.co)); ca.data[v.index].color = (r, 0, 0, 1)
set_rigid(hat, lambda c: 1.0)
set_rigid(coat, lambda c: 0.55 * float(sm(100, HEM, c.z)))
for ob in (shirt, over, boots): set_rigid(ob, lambda c: 0.0)

# ---------------------------------------------------------------- 7. export: chest (shirt + coat), legs (overalls + boots), helmet
fitref = link("fitref", body_me.copy()); fitref.data.name = "fitref"
for ob in list(sc.collection.objects):
    if ob.name not in ("shirt", "overalls", "coat", "boots", "hat", "fitref"): ob.hide_set(True); ob.hide_render = True
def export(key, parts):
    path = os.path.join(OUT, "Models", key + ".fbx")
    if os.path.exists(path): print("  exists, kept:", path); return
    for o in bpy.data.objects: o.select_set(o.name in parts + ["fitref"])
    bpy.context.view_layer.objects.active = bpy.data.objects[parts[0]]
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={'MESH'}, global_scale=1.0, apply_unit_scale=True,
                             apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y', bake_space_transform=True,
                             mesh_smooth_type='FACE', bake_anim=False, path_mode='STRIP', embed_textures=False, colors_type='LINEAR')
    print(f"  exported {key}: {parts} + fitref -> {os.path.basename(path)}")
export("fisher_chest", ["shirt", "coat"])
export("fisher_legs", ["overalls", "boots"])
export("fisher_hat", ["hat"])
for img in list(bpy.data.images):
    if img.users == 0: bpy.data.images.remove(img)
blend = os.path.join(OUT, "Blender Files", "fisher_gear_v1.blend")
if not os.path.exists(blend): bpy.ops.wm.save_as_mainfile(filepath=blend, copy=True); print("  saved", blend)

# ---------------------------------------------------------------- 8. preview
R = os.environ.get("VDW_RENDER")
if R:
    fitref.hide_render = True; body_ob.hide_set(False); body_ob.hide_render = False
    for o in (bpy.data.objects['PlayerCharacter_01.001'], bpy.data.objects['weighters']): o.hide_render = True
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 24; sc.render.use_border = False
    sc.view_settings.view_transform = 'Standard'; sc.render.resolution_x, sc.render.resolution_y = 700, 1000
    wd = bpy.data.worlds.new("w"); wd.use_nodes = True; sc.world = wd; wd.node_tree.nodes["Background"].inputs[0].default_value = (0.45, 0.48, 0.52, 1)
    ld = bpy.data.lights.new("k", 'SUN'); ld.energy = 3.0; lo = bpy.data.objects.new("k", ld); sc.collection.objects.link(lo); lo.rotation_euler = (0.7, 0.2, -0.6)
    cd = bpy.data.cameras.new("C"); cd.type = 'ORTHO'; cd.ortho_scale = 215; cam = bpy.data.objects.new("C", cd); sc.collection.objects.link(cam); sc.camera = cam
    for nm, d in (("front", (0.35, -1, 0.15)), ("back", (-0.5, 1, 0.2)), ("side", (1, -0.2, 0.1))):
        c = Vector((0, 0, 102)); cam.location = c + Vector(d).normalized() * 500; cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = f"{R}_{nm}.png"; bpy.ops.render.render(write_still=True)
    cd.ortho_scale = 45
    c = Vector((0, -4, 188)); cam.location = c + Vector((0.6, -1, 0.35)).normalized() * 300; cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = f"{R}_hat.png"; bpy.ops.render.render(write_still=True)
print("===== END =====")