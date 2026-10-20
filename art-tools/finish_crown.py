# Finishes a hand-edited Njord's Regalia crown (.blend from retexture_crown.py, then edited by hand): the row of gems on
# one section of the band is copied to the other three (mirrored front/back and left/right), stray loose vertices are
# removed, the seams are finished (the existing ones kept; the crown split into its outside and inside, each ring cut
# once at the back) so the unwrap is clean in as few islands as possible, and it is painted straight onto that unwrap:
# bronze with copper-worn edges and dark hollows, the inside plain hammered metal, the gems green and blue, crisp runes
# round the rim, on the shield and on each diamond point, the fish scaled. Never saves over its input.
#   blender -b <crown.blend> --python finish_crown.py
# env: VDW_OUT (folder), VDW_NAME (buff_regalia_njord), VDW_RES (2048), VDW_RUNES (1), VDW_MIRROR_GEMS (1; 0 when rebuilding a crown that has them all),
#      VDW_UNWRAP (smart | charts)
import bpy, bmesh, os, math
import numpy as np
from mathutils import Vector, Matrix
import functools
print = functools.partial(print, flush=True)

OUT = os.environ["VDW_OUT"]; NAME = os.environ.get("VDW_NAME", "buff_regalia_njord"); RES = int(os.environ.get("VDW_RES", "2048"))
RUNES = os.environ.get("VDW_RUNES", "1") == "1"
for d in ("Models", "Textures", "Blender Files"): os.makedirs(os.path.join(OUT, d), exist_ok=True)
TEX = os.path.join(OUT, "Textures")
crown = next(o for o in bpy.data.objects if o.type == 'MESH'); me = crown.data
bpy.context.view_layer.objects.active = crown
if crown.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')       # saved mid-edit: its edits written back first
def ang(x, y): return math.atan2(x, -y)                      # 0 = front (-Y), + toward +X

# ---------------------------------------------------------------- loose parts: strays removed, the gem row copied round
bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
bmesh.ops.dissolve_degenerate(bm, dist=1e-6, edges=bm.edges[:])          # zero-area slivers (one took 91% of the unwrap)
flat = [f for f in bm.faces if f.calc_area() < 1e-11]
if flat: bmesh.ops.delete(bm, geom=flat, context='FACES')
stray = [v for v in bm.verts if not v.link_faces]
bmesh.ops.delete(bm, geom=stray, context='VERTS')
bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
seen = set(); parts = []
for v in bm.verts:
    if v.index in seen: continue
    st = [v]; seen.add(v.index); comp = []
    while st:
        u = st.pop(); comp.append(u)
        for e in u.link_edges:
            w = e.other_vert(u)
            if w.index not in seen: seen.add(w.index); st.append(w)
    parts.append(comp)
def centre(vs): return sum((v.co for v in vs), Vector()) / len(vs)
gems = [p for p in parts if 20 <= len(p) <= 60 and 0.028 < centre(p).z < 0.045 and 0.35 < ang(centre(p).x, centre(p).y) < 1.3]
gems.sort(key=lambda p: ang(centre(p).x, centre(p).y))
print(f"CROWN {len(bm.verts)} verts; {len(stray)} stray vertices removed; gem row: {len(gems)} gems at "
      f"{[round(math.degrees(ang(centre(p).x, centre(p).y))) for p in gems]} deg")
body = max(parts, key=len)
bco = np.array([v.co[:] for v in body])
def band_r(a, z):
    """How far out the band's surface is at this angle and height (its outermost point there)."""
    ba = np.arctan2(bco[:, 0], -bco[:, 1]); m = (np.abs(((ba - a + np.pi) % (2 * np.pi)) - np.pi) < 0.06) & (np.abs(bco[:, 2] - z) < 0.004)
    return float(np.hypot(bco[m, 0], bco[m, 1]).max()) if m.any() else None
gl = bm.faces.layers.int.get("vdw_gem") or bm.faces.layers.int.new("vdw_gem")
MIRROR = os.environ.get("VDW_MIRROR_GEMS", "1") == "1"     # 0: the crown already has all its gems (rebuilding an edited finish)
if not MIRROR: gems = []
for i, p in enumerate(gems):                                 # 1 green, 2 blue, alternating along the row
    for f in {f for v in p for f in v.link_faces}: f[gl] = 1 + i % 2
copies = 0
for sx, sy in ((-1, 1), (1, -1), (-1, -1)):
    Mt = Matrix.Diagonal((sx, sy, 1, 1))
    for i, p in enumerate(gems):
        faces = list({f for v in p for f in v.link_faces})
        dup = bmesh.ops.duplicate(bm, geom=faces)
        nv = [g for g in dup["geom"] if isinstance(g, bmesh.types.BMVert)]; nf = [g for g in dup["geom"] if isinstance(g, bmesh.types.BMFace)]
        for v in nv: v.co = Mt @ v.co
        if sx * sy < 0: bmesh.ops.reverse_faces(bm, faces=nf)
        c0 = centre(p); c1 = centre(nv)                        # sit as deep in the band there as the original does here
        r_src = band_r(ang(c0.x, c0.y), c0.z); r_dst = band_r(ang(c1.x, c1.y), c1.z)
        if r_src and r_dst:
            d = r_dst - r_src; rad = Vector((c1.x, c1.y, 0)).normalized()
            for v in nv: v.co += rad * d
        for f in nf: f[gl] = 1 + (i + (1 if sx * sy < 0 else 0)) % 2
        copies += 1
bm.to_mesh(me); bm.free(); me.update()
print(f"  gems copied to the other three sections: {copies}")

# ---------------------------------------------------------------- spikes and folds relaxed (they pinch any unwrap)
bm = bmesh.new(); bm.from_mesh(me)
gl = bm.faces.layers.int["vdw_gem"]
fixed = 0
for _ in range(4):
    bm.verts.ensure_lookup_table(); bm.normal_update()
    cones = []
    for v in bm.verts:
        if v.is_boundary or not v.link_faces or any(f[gl] for f in v.link_faces): continue
        defect = 2 * math.pi - sum(l.calc_angle() for l in v.link_loops)
        folded = any(e.link_faces[0].normal.dot(e.link_faces[1].normal) < -0.3 for e in v.link_edges if len(e.link_faces) == 2)
        if abs(defect) > 1.0 or folded: cones.append(v)
    if not cones: break
    three = [v for v in cones if len(v.link_faces) == 3]
    if three: bmesh.ops.dissolve_verts(bm, verts=three)
    bm.verts.ensure_lookup_table()
    rest = [v for v in cones if v.is_valid]
    for v in rest:                                          # pulled to the middle of its neighbours (with them a little)
        ring = [e.other_vert(v) for e in v.link_edges]
        if ring: v.co = sum((w.co for w in ring), Vector()) / len(ring)
    fixed += len(cones)
bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
bm.to_mesh(me); bm.free(); me.update()
print(f"  mesh tidied: {fixed} spike/fold vertices relaxed")

# ---------------------------------------------------------------- seams: yours kept; the rest split by which way the surface faces
# Charts like a cube map wrapped round the crown: outward, inward, up, down and the two sideways directions, each split
# in quarters round the ring (cut at 45 and 135 degrees each side). Normals are smoothed first (the generated mesh is
# noisy) and scraps are folded into their neighbours, so each chart is a fairly flat stretch that unfolds cleanly.
bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table(); bm.edges.ensure_lookup_table()
gl = bm.faces.layers.int["vdw_gem"]
F = len(bm.faces); fn = np.array([f.normal[:] for f in bm.faces]); fc = np.array([f.calc_center_median()[:] for f in bm.faces]); fa = np.array([f.calc_area() for f in bm.faces])
adj = [[h.index for e in f.edges for h in e.link_faces if h is not f] for f in bm.faces]
for _ in range(4):
    sm = fn * fa[:, None]
    for i in range(F):
        for j in adj[i]: sm[i] += fn[j] * fa[j]
    fn = sm / np.maximum(np.linalg.norm(sm, axis=1, keepdims=True), 1e-12)
r_ = fc[:, :2] / np.maximum(np.linalg.norm(fc[:, :2], axis=1, keepdims=True), 1e-9)
nr = fn[:, 0] * r_[:, 0] + fn[:, 1] * r_[:, 1]; nt = -fn[:, 0] * r_[:, 1] + fn[:, 1] * r_[:, 0]; nz = fn[:, 2]
comp_ = np.stack([nr, nt, nz], 1); axis_ = np.abs(comp_).argmax(1); sign_ = (comp_[np.arange(F), axis_] > 0).astype(int)
a_ = np.arctan2(fc[:, 0], -fc[:, 1]); quad = np.floor(((a_ + math.pi / 4) % (2 * math.pi)) / (math.pi / 2)).astype(int)
lab = (axis_ * 2 + sign_) * 4 + quad
gem_f = np.array([f[gl] for f in bm.faces])
for _ in range(3):                                          # ragged borders tidied
    new = lab.copy()
    for i in range(F):
        if not adj[i]: continue
        vals, cnts = np.unique(lab[adj[i]], return_counts=True)
        if cnts.max() * 2 > len(adj[i]) and vals[cnts.argmax()] != lab[i]: new[i] = vals[cnts.argmax()]
    lab = new
def components():
    seen = np.full(F, -1); comps = []
    for i in range(F):
        if seen[i] >= 0: continue
        st = [i]; seen[i] = len(comps); c = [i]
        while st:
            k = st.pop()
            for j in adj[k]:
                if seen[j] < 0 and lab[j] == lab[i] and gem_f[j] == gem_f[i]: seen[j] = len(comps); st.append(j); c.append(j)
        comps.append(c)
    return comps
for _ in range(6):                                          # scraps folded into the neighbour they share most border with
    changed = 0
    for c in components():
        if len(c) >= 80 or gem_f[c[0]]: continue
        cs = set(c); border = [lab[j] for k in c for j in adj[k] if j not in cs and not gem_f[j]]
        if not border: continue
        vals, cnts = np.unique(border, return_counts=True); lab[c] = vals[cnts.argmax()]; changed += 1
    if not changed: break
user_seams = sum(e.seam for e in bm.edges)
for e in bm.edges:
    lf = e.link_faces
    if len(lf) == 2 and lab[lf[0].index] != lab[lf[1].index] and not (lf[0][gl] or lf[1][gl]): e.seam = True
bm.to_mesh(me); bm.free(); me.update()
print(f"  seams: {user_seams} of yours kept, {sum(e.use_seam for e in me.edges)} in all; {len(components())} charts")
# ---------------------------------------------------------------- unwrapped on those seams
for l in list(me.uv_layers): me.uv_layers.remove(l)
uvl = me.uv_layers.new(name="UVMap"); me.uv_layers.active = uvl
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
if os.environ.get("VDW_UNWRAP", "smart") == "smart":                   # Blender's projection unwrap: least stretch, more islands
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.003, area_weight=0.0)
else:
    bpy.ops.uv.unwrap(method='CONFORMAL', fill_holes=True, margin=0.003)
bpy.ops.uv.select_all(action='SELECT'); bpy.ops.uv.average_islands_scale()
bpy.ops.uv.pack_islands(rotate=True, scale=True, margin=0.004, shape_method='CONCAVE')   # packed by outline, not bounding box
bpy.ops.object.mode_set(mode='OBJECT')
uvl = me.uv_layers["UVMap"]

# ---------------------------------------------------------------- per texel of the new unwrap: where, facing where, how convex, which part
co = np.array([v.co[:] for v in me.vertices], np.float32); vn = np.array([v.normal[:] for v in me.vertices], np.float32)
bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
convex = np.zeros(len(bm.verts), np.float32)
for v in bm.verts:
    if v.link_edges: convex[v.index] = -np.mean([(e.other_vert(v).co - v.co).normalized().dot(v.normal) for e in v.link_edges])
bm.free()
ev = np.array([e.vertices[:] for e in me.edges]); broad = convex.copy()
for _ in range(10):
    acc = np.zeros_like(broad); cnt = np.zeros_like(broad)
    np.add.at(acc, ev[:, 0], broad[ev[:, 1]]); np.add.at(acc, ev[:, 1], broad[ev[:, 0]]); np.add.at(cnt, ev[:, 0], 1); np.add.at(cnt, ev[:, 1], 1)
    broad = 0.5 * broad + 0.5 * acc / np.maximum(cnt, 1)
gemf = np.zeros(len(me.polygons), np.int32); me.attributes["vdw_gem"].data.foreach_get("value", gemf)
me.calc_loop_triangles()
uvs = np.zeros(len(me.loops) * 2); uvl.data.foreach_get("uv", uvs); q_all = uvs.reshape(-1, 2) * RES - 0.5
P = np.zeros((RES, RES, 3), np.float32); NN = np.zeros((RES, RES, 3), np.float32); CV = np.zeros((RES, RES), np.float32)
CVS = np.zeros((RES, RES), np.float32); GEM = np.zeros((RES, RES), np.int32); HITS = np.zeros((RES, RES), np.int32)
uv_area = np.zeros(len(me.loop_triangles)); xyz_area = np.zeros(len(me.loop_triangles))
for ti, tri in enumerate(me.loop_triangles):
    q = q_all[list(tri.loops)]; vi = list(tri.vertices)
    uv_area[ti] = abs(np.cross(q[1] - q[0], q[2] - q[0])) / 2; xyz_area[ti] = tri.area
    x0, y0 = np.floor(q.min(0)).astype(int); x1, y1 = np.ceil(q.max(0)).astype(int)
    x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, RES - 1), min(y1, RES - 1)
    if x1 < x0 or y1 < y0: continue
    gx, gy = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1))
    (ax, ay), (bx, by), (cx, cy) = q
    den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
    if abs(den) < 1e-12: continue
    w0 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / den; w1 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / den; w2 = 1 - w0 - w1
    inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
    near = (w0 >= -0.03) & (w1 >= -0.03) & (w2 >= -0.03)
    if not near.any(): continue
    HITS[gy[inside], gx[inside]] += 1
    yy, xx = gy[near], gx[near]; W = np.stack([w0[near], w1[near], w2[near]], 1)
    P[yy, xx] = W @ co[vi]; NN[yy, xx] = W @ vn[vi]; CV[yy, xx] = W @ convex[vi]; CVS[yy, xx] = W @ broad[vi]; GEM[yy, xx] = gemf[tri.polygon_index]
HIT = np.linalg.norm(NN, axis=2) > 0
# the unwrap's quality: islands, overlaps, stretch
ratio = (uv_area / max(uv_area.sum(), 1e-9)) / (xyz_area / max(xyz_area.sum(), 1e-12) + 1e-12)
bad = ((ratio < 0.33) | (ratio > 3)) & (xyz_area > np.median(xyz_area) * 0.1)
bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table(); fseen = set(); islands = 0
for f in bm.faces:
    if f.index in fseen: continue
    islands += 1; st = [f]; fseen.add(f.index)
    while st:
        g = st.pop()
        for e in g.edges:
            if e.seam: continue
            for h in e.link_faces:
                if h.index not in fseen: fseen.add(h.index); st.append(h)
bm.free()
print(f"  unwrap: {islands} islands, {HIT.mean() * 100:.0f}% of the texture used, overlapping texels {(HITS > 1).sum() / max((HITS > 0).sum(), 1) * 100:.2f}%, "
      f"stretched faces {bad.mean() * 100:.1f}%")

# ---------------------------------------------------------------- painted (from scratch)
ANG = np.arctan2(P[..., 0], -P[..., 1]); RR = np.hypot(P[..., 0], P[..., 1]); nl = np.maximum(np.linalg.norm(NN, axis=2), 1e-6)
RAD = np.where(RR > 1e-5, (NN[..., 0] * P[..., 0] + NN[..., 1] * P[..., 1]) / np.maximum(RR, 1e-5) / nl, 0)
rng = np.random.default_rng(7)
def smooth_noise(scale):
    n = rng.random((RES // scale + 2, RES // scale + 2)).astype(np.float32)
    yy, xx = np.mgrid[0:RES, 0:RES] / scale; y0, x0 = yy.astype(int), xx.astype(int); fy, fx = yy - y0, xx - x0
    return (n[y0, x0] * (1 - fx) * (1 - fy) + n[y0, x0 + 1] * fx * (1 - fy) + n[y0 + 1, x0] * (1 - fx) * fy + n[y0 + 1, x0 + 1] * fx * fy)
IRON = np.array([0.075, 0.062, 0.052]); BRONZE = np.array([0.30, 0.21, 0.13]); LIGHT = np.array([0.56, 0.43, 0.29])
patches = 0.6 * smooth_noise(96) + 0.4 * smooth_noise(24); hammer = 0.5 * smooth_noise(7) + 0.5 * smooth_noise(3)
t = np.clip(0.46 + (patches - 0.5) * 0.45 + (hammer - 0.5) * 0.14 + np.clip(CVS * 5, -0.3, 0.3), 0, 1)
A = np.where(t[..., None] < 0.55, IRON + (BRONZE - IRON) * (t[..., None] / 0.55), BRONZE + (LIGHT - BRONZE) * ((t[..., None] - 0.55) / 0.45)).astype(np.float32)
edge = np.clip((CV - 0.07) * 7, 0, 1); cavity = np.clip((-CV - 0.03) * 10, 0, 1) * 0.6 + np.clip(-CVS * 8, 0, 1) * 0.4
A = A * (1 - 0.6 * cavity[..., None]) + (np.array([0.66, 0.42, 0.26]) - A) * (0.45 * edge[..., None])
inner = HIT & (RAD < -0.45) & (GEM == 0)
A[inner] = np.array([0.15, 0.12, 0.10]) * (0.8 + 0.4 * hammer[inner, None])
MET = (0.55 - 0.25 * cavity).astype(np.float32); MET[inner] = 0.45
SM = (0.40 + 0.25 * edge - 0.15 * cavity + (hammer - 0.5) * 0.1).astype(np.float32)
E = np.zeros_like(A)
for g, base, glow in ((1, (0.04, 0.40, 0.21), (0.02, 0.18, 0.09)), (2, (0.04, 0.19, 0.60), (0.02, 0.09, 0.28))):
    m = GEM == g
    shade = np.clip(0.75 + CV[m] * 4, 0.5, 1.4)[:, None]
    A[m] = np.clip(np.array(base) * shade + np.clip(edge[m] * 0.35, 0, 0.35)[:, None], 0, 1); MET[m] = 0.0; SM[m] = 0.9; E[m] = glow
print(f"  gem texels: green {(GEM == 1).sum()}, blue {(GEM == 2).sum()}; inside {inner.sum()}")

if RUNES:
    GL = {  # Elder Futhark in a 0.6 x 1 box
        "f": [((0, 0), (0, 1)), ((0, .75), (.5, 1)), ((0, .5), (.5, .75))], "u": [((0, 0), (0, 1)), ((0, 1), (.5, .7)), ((.5, .7), (.5, 0))],
        "th": [((0, 0), (0, 1)), ((0, .7), (.45, .5)), ((.45, .5), (0, .3))], "a": [((0, 0), (0, 1)), ((0, 1), (.5, .75)), ((0, .7), (.5, .45))],
        "r": [((0, 0), (0, 1)), ((0, 1), (.45, .78)), ((.45, .78), (0, .55)), ((0, .55), (.5, 0))], "k": [((.5, 1), (0, .5)), ((0, .5), (.5, 0))],
        "g": [((0, 0), (.6, 1)), ((0, 1), (.6, 0))], "t": [((.3, 0), (.3, 1)), ((.3, 1), (0, .7)), ((.3, 1), (.6, .7))],
        "z": [((.3, 0), (.3, 1)), ((.3, .6), (0, 1)), ((.3, .6), (.6, 1))], "n": [((.3, 0), (.3, 1)), ((.05, .65), (.55, .4))],
        "o": [((.3, 1), (.58, .62)), ((.58, .62), (.3, .3)), ((.3, .3), (.02, .62)), ((.02, .62), (.3, 1)), ((.3, .3), (0, 0)), ((.3, .3), (.6, 0))],
        "d": [((0, 0), (0, 1)), ((.6, 0), (.6, 1)), ((0, 1), (.6, 0)), ((0, 0), (.6, 1))], "m": [((0, 0), (0, 1)), ((.6, 0), (.6, 1)), ((0, 1), (.6, .55)), ((.6, 1), (0, .55))],
        "s": [((.5, 1), (.08, .64)), ((.08, .64), (.52, .36)), ((.52, .36), (.1, 0))],
    }
    GROOVE = np.zeros((RES, RES), np.float32)
    def carve(mask, sx, sy, segs):
        if not len(segs) or not mask.any(): return 0
        S_ = np.array(segs, np.float32); px_, py_ = sx[mask][:, None], sy[mask][:, None]; best = np.full(px_.shape[0], 9.0, np.float32)
        for c0 in range(0, len(S_), 48):
            s_ = S_[c0:c0 + 48]; ax_, ay_, bx_, by_, ww = [s_[:, i][None, :] for i in range(5)]
            dx, dy = bx_ - ax_, by_ - ay_
            tt = np.clip(((px_ - ax_) * dx + (py_ - ay_) * dy) / np.maximum(dx * dx + dy * dy, 1e-14), 0, 1)
            best = np.minimum(best, (np.hypot(px_ - (ax_ + tt * dx), py_ - (ay_ + tt * dy)) / ww).min(1))
        groove = np.clip((1.25 - best) * 3, 0, 1); rim = np.clip(np.clip((2.0 - best) * 1.5, 0, 1) - groove, 0, 1)
        ii, jj = np.nonzero(mask)
        A[ii, jj] = A[ii, jj] * (1 - 0.8 * groove[:, None]) + (np.array([0.62, 0.45, 0.30]) - A[ii, jj]) * (0.25 * rim[:, None])
        GROOVE[ii, jj] = np.maximum(GROOVE[ii, jj], groove); return int((groove > 0.5).sum())
    def frame(mask):
        """A flat area's own 2D coordinates: right and up as seen from outside, centred."""
        cen = P[mask].mean(0); n_ = (NN[mask] / nl[mask][:, None]).mean(0); n_ /= max(np.linalg.norm(n_), 1e-6)
        up = np.array([0, 0, 1.0]) - n_ * n_[2]; up /= max(np.linalg.norm(up), 1e-6); right = np.cross(up, n_)
        d_ = P - cen; return d_ @ right, d_ @ up, np.abs(d_ @ right)[mask].max(), np.abs(d_ @ up)[mask].max()
    # the rim row, below the gems
    BAND_Z = (0.0145, 0.0245); SKIP = [(0.0, 0.33), (-1.58, 0.3), (1.58, 0.3), (math.pi, 0.3), (-math.pi, 0.3)]
    def ang_ok(a): return all(abs(((a - c_ + math.pi) % (2 * math.pi)) - math.pi) > w_ for c_, w_ in SKIP)
    ok = np.ones((RES, RES), bool)
    for c_, w_ in SKIP: ok &= np.abs(((ANG - c_ + np.pi) % (2 * np.pi)) - np.pi) > w_
    # the lower rail measured every 2 degrees (it isn't level all round): where it stands proud of the band above it
    cand = HIT & (P[..., 2] > 0.004) & (P[..., 2] < 0.034) & (RAD > 0.5) & ok & (GEM == 0)
    NB = 180; bins = ((ANG + np.pi) / (2 * np.pi) * NB).astype(int) % NB
    z0s = np.full(NB, np.nan); z1s = np.full(NB, np.nan)
    for b in range(NB):
        m = cand & (bins == b)
        if m.sum() < 30: continue
        zz, rr_ = P[..., 2][m], RR[m]
        ref = np.median(rr_[(zz > 0.029) & (zz < 0.034)]) if ((zz > 0.029) & (zz < 0.034)).any() else np.median(rr_)
        rail = zz[rr_ > ref + 0.0012]
        if len(rail) > 10: z0s[b], z1s[b] = np.percentile(rail, 8), np.percentile(rail, 92)
    good = ~np.isnan(z0s)
    if good.sum() > 10:                                       # gaps filled, then eased round the ring
        idx = np.arange(NB); z0s = np.interp(idx, idx[good], z0s[good], period=NB); z1s = np.interp(idx, idx[good], z1s[good], period=NB)
        k5 = np.ones(21) / 21; z0s = np.convolve(np.r_[z0s[-10:], z0s, z0s[:10]], k5, 'valid'); z1s = np.convolve(np.r_[z1s[-10:], z1s, z1s[:10]], k5, 'valid')
    else:
        z0s[:] = BAND_Z[0]; z1s[:] = BAND_Z[1]
    zlo, zhi = z0s[bins], z1s[bins]
    band_t = cand & (P[..., 2] >= zlo - 0.0005) & (P[..., 2] <= zhi + 0.0005)
    Rb = float(np.median(RR[band_t])) if band_t.any() else 0.104
    def rail_at(a):
        b = int(((a + math.pi) / (2 * math.pi) * NB)) % NB; return z0s[b], z1s[b]
    WORD = "f u th a r k g n t z o d m a".split(); segs = []; k_ = 0
    h_ = float(np.median(z1s - z0s)) * 0.7; s_ = -math.pi * Rb
    print(f"  lower rail: {np.median(z0s) * 1000:.1f}-{np.median(z1s) * 1000:.1f} mm up (varies {np.ptp(z0s) * 1000:.1f} mm round the ring)")
    while s_ < math.pi * Rb:
        a0 = s_ / Rb
        if ang_ok(a0) and ang_ok((s_ + 0.6 * h_) / Rb):
            r0, r1 = rail_at(a0 + 0.3 * h_ / Rb); hh = min(h_, (r1 - r0) * 0.72); zc = (r0 + r1) / 2 - hh / 2
            for (x0, y0), (x1, y1) in GL[WORD[k_ % len(WORD)]]:
                segs.append((s_ + x0 * hh, zc + y0 * hh, s_ + x1 * hh, zc + y1 * hh, 0.085 * hh))
            k_ += 1
        s_ += 1.35 * h_
    n_band = carve(band_t, ANG * Rb, P[..., 2], segs)
    # the shield's face: two rows, as on the reference
    shield_t = HIT & (np.abs(ANG) < 0.22) & (P[..., 2] > 0.033) & (P[..., 2] < 0.068) & (RAD > 0.75) & (GEM == 0)
    n_sh = 0
    if shield_t.sum() > 500:
        sx, sy, wx, wy = frame(shield_t); h3 = min(wx * 2 / 4.6, wy * 0.42); segs = []
        for word, yc in (("f u th a r".split(), 0.42), ("s m m s".split(), -0.08)):
            w_tot = (len(word) - 1) * 0.85 * h3 + 0.6 * h3; x_ = -w_tot / 2
            for gname in word:
                for (x0, y0), (x1, y1) in GL[gname]:
                    segs.append((x_ + x0 * h3, yc * wy + (y0 - 0.5) * h3, x_ + x1 * h3, yc * wy + (y1 - 0.5) * h3, 0.08 * h3))
                x_ += 0.85 * h3
        n_sh = carve(shield_t, sx, sy, segs)
    # each diamond point's outer face: one rune
    tops = HIT & (P[..., 2] > 0.068) & (RAD > 0.7)
    pa = np.round(ANG[tops], 2); centres = []
    for a in np.sort(np.unique(pa)):
        if not centres or a - centres[-1][-1] > 0.15: centres.append([a])
        else: centres[-1].append(a)
    n_pl = 0
    for k2, grp in enumerate(centres):
        a0 = float(np.mean(grp)); m = tops & (np.abs(((ANG - a0 + np.pi) % (2 * np.pi)) - np.pi) < 0.12)
        if m.sum() < 200: continue
        sx, sy, wx, wy = frame(m); h2 = min(wx, wy) * 0.95
        glyph = GL[["o", "d", "z", "t", "g", "m"][k2 % 6]]
        n_pl += carve(m, sx, sy, [((x0 - 0.3) * h2, (y0 - 0.5) * h2, (x1 - 0.3) * h2, (y1 - 0.5) * h2, 0.075 * h2) for (x0, y0), (x1, y1) in glyph])
    # the fish below the shield: carved scales
    fish = HIT & (np.abs(ANG) < 0.6) & (P[..., 2] < 0.04) & (RR > Rb + 0.0025) & (RAD > 0.2) & (GEM == 0) & ~shield_t
    sz = 0.0026; u_ = ANG * Rb / sz; v_ = P[..., 2] / sz; row_ = np.floor(v_); u2 = u_ + 0.5 * (row_ % 2)
    fu = u2 - np.floor(u2) - 0.5; fv = v_ - row_; dsc = np.hypot(fu, fv * 0.9)
    line_ = np.clip(1 - np.abs(dsc - 0.5) / 0.09, 0, 1) * (fv > 0.05)
    A[fish] = A[fish] * (1 - 0.6 * line_[fish, None]) + (np.array([0.62, 0.46, 0.30]) - A[fish]) * (0.18 * np.clip(0.5 - dsc[fish], 0, 1)[:, None])
    SM *= 1 - 0.5 * GROOVE; MET *= 1 - 0.6 * GROOVE
    print(f"  runes: {k_} round the rim, shield {n_sh} texels, {len(centres)} diamond points ({n_pl} texels); fish scales {fish.sum()} texels")

# padding: each island's colour bled a few texels into the empty space (no dark seams once mip-mapped)
def pad(img, filled, n=10):
    img = img.copy(); filled = filled.copy()
    for _ in range(n):
        acc = np.zeros_like(img); cnt = np.zeros(filled.shape, np.float32)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            sh = np.roll(np.roll(filled, dy, 0), dx, 1); acc += np.roll(np.roll(img, dy, 0), dx, 1) * sh[..., None] if img.ndim == 3 else np.roll(np.roll(img, dy, 0), dx, 1) * sh
            cnt += sh
        grow = (~filled) & (cnt > 0)
        if img.ndim == 3: img[grow] = acc[grow] / cnt[grow][:, None]
        else: img[grow] = acc[grow] / cnt[grow]
        filled |= grow
    return img
A = pad(np.clip(A, 0, 1), HIT); MET = pad(MET, HIT); SM = pad(SM, HIT); E = pad(E, HIT)

# ---------------------------------------------------------------- written out (Unity names), material, blend
def save(arr, kind, color=True):
    im = bpy.data.images.new(f"{NAME}_{kind}", RES, RES, alpha=True)
    if not color: im.colorspace_settings.name = "Non-Color"
    im.pixels[:] = np.ascontiguousarray(arr, np.float32).ravel(); p = os.path.join(TEX, f"{NAME}_Unity_{kind}.png")
    im.filepath_raw = p; im.file_format = 'PNG'; im.save(); return p
ones = np.ones((RES, RES), np.float32)
p_a = save(np.dstack([A, ones]), "Albedo"); p_m = save(np.dstack([MET, MET, MET, SM]), "MetallicSmoothness", False)
p_n = save(np.dstack([ones * 0.5, ones * 0.5, ones, ones]), "Normal", False); p_e = save(np.dstack([E, ones]), "Emission")
mat = bpy.data.materials.new(NAME + "_v7"); mat.use_nodes = True; nt = mat.node_tree; bs = nt.nodes["Principled BSDF"]
def tex(p, col=True):
    t_ = nt.nodes.new("ShaderNodeTexImage"); t_.image = bpy.data.images.load(p)
    if not col: t_.image.colorspace_settings.name = "Non-Color"
    return t_
nt.links.new(tex(p_a).outputs[0], bs.inputs["Base Color"])
tm = tex(p_m, False); sep = nt.nodes.new("ShaderNodeSeparateColor"); nt.links.new(tm.outputs[0], sep.inputs[0]); nt.links.new(sep.outputs[0], bs.inputs["Metallic"])
inv = nt.nodes.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1; nt.links.new(tm.outputs["Alpha"], inv.inputs[1]); nt.links.new(inv.outputs[0], bs.inputs["Roughness"])
nt.links.new(tex(p_e).outputs[0], bs.inputs["Emission Color"]); bs.inputs["Emission Strength"].default_value = 1.0
me.materials.clear(); me.materials.append(mat)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "Blender Files", f"{NAME}.blend"))
print("SAVED")
