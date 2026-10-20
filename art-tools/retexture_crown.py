# Njord's Regalia from a generated crown model (Mesh/Crown/fisherman_crown.fbx, after Mesh/Crown/crown.png): sized to
# a Valheim head, re-seamed and unwrapped again, recoloured after the reference - dark iron and bronze, copper worn onto the raised edges, darker in
# the cracks, the band's inside plain hammered metal instead of the generator's smears, the gems clear green and blue
# with real faceted stones set over them, the bone beads ivory. Never writes over the source files.
#   blender -b --python retexture_crown.py
# env: VDW_SRC (fbx), VDW_TEX (its texture folder: Color.jpg, Normal.png), VDW_OUT (folder), VDW_NAME
#      (buff_regalia_njord), VDW_DIAMETER (0.22 m across the outside), VDW_GEMS (1)
import bpy, bmesh, os, math, colorsys
import numpy as np
from mathutils import Vector, Matrix
import functools
print = functools.partial(print, flush=True)

SRC = os.environ["VDW_SRC"]; TEXDIR = os.environ["VDW_TEX"]; OUT = os.environ["VDW_OUT"]; NAME = os.environ.get("VDW_NAME", "buff_regalia_njord")
DIAM = float(os.environ.get("VDW_DIAMETER", "0.22"))
for d in ("Models", "Textures", "Blender Files"): os.makedirs(os.path.join(OUT, d), exist_ok=True)
TEX = os.path.join(OUT, "Textures")
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
bpy.ops.import_scene.fbx(filepath=SRC)
crown = next(o for o in bpy.data.objects if o.type == 'MESH')
for o in list(bpy.data.objects):
    if o != crown: bpy.data.objects.remove(o)
me = crown.data; me.transform(crown.matrix_world); crown.matrix_world = Matrix(); crown.name = NAME
# sized to a head, base at z = 0, centred; the shield (front) stays toward -Y
co = np.array([v.co[:] for v in me.vertices])
lo, hi = co.min(0), co.max(0); k = DIAM / max(hi[0] - lo[0], hi[1] - lo[1])
me.transform(Matrix.Translation((0, 0, 0)) @ Matrix.Scale(k, 4)); co = np.array([v.co[:] for v in me.vertices])
c = (co.min(0) + co.max(0)) / 2; me.transform(Matrix.Translation((-c[0], -c[1], -co[:, 2].min()))); me.update()
bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:]); bm.to_mesh(me); bm.free(); me.update()   # the generator's normals faced inward
co = np.array([v.co[:] for v in me.vertices])
print(f"CROWN {len(me.vertices)} verts, scaled x{k:.3f}: {np.ptp(co[:, 0]):.3f} x {np.ptp(co[:, 1]):.3f} x {np.ptp(co[:, 2]):.3f} m")

# ---------------------------------------------------------------- the rune areas smoothed (the generator left them lumpy)
RUNES = os.environ.get("VDW_RUNES", "1") == "1"
BAND_Z = (0.0155, 0.0265)                                   # the rune row round the lower rim (m, for a 0.22 m crown)
SKIP_ANG = [(0.0, 0.33), (-1.58, 0.3), (1.58, 0.3), (math.pi, 0.3), (-math.pi, 0.3)]   # the V pieces: fish, leaves, back
PLATE_Z = 0.068                                             # the rune points' diamond plates sit above this
def ang_ok(a): return all(abs(a - c_) > w_ for c_, w_ in SKIP_ANG)
plates = []; shield = None
if RUNES:
    bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table(); bm.normal_update()
    def radial_n(v):
        r_ = math.hypot(v.co.x, v.co.y); return (v.normal.x * v.co.x + v.normal.y * v.co.y) / max(r_, 1e-6)
    band = {v for v in bm.verts if BAND_Z[0] - 0.002 <= v.co.z <= BAND_Z[1] + 0.002 and radial_n(v) > 0.55 and ang_ok(math.atan2(v.co.x, -v.co.y))}
    for _ in range(8):                                     # even the band's radius out (keeps each vertex's angle and height)
        newr = {}
        for v in band:
            ns = [e.other_vert(v) for e in v.link_edges if e.other_vert(v) in band]
            if ns: newr[v] = 0.5 * math.hypot(v.co.x, v.co.y) + 0.5 * np.mean([math.hypot(n.co.x, n.co.y) for n in ns])
        for v, r_ in newr.items():
            s_ = r_ / max(math.hypot(v.co.x, v.co.y), 1e-6); v.co.x *= s_; v.co.y *= s_
    tops = [v for v in bm.verts if v.co.z > PLATE_Z and radial_n(v) > 0.7]
    groups = []
    for v in sorted(tops, key=lambda v: math.atan2(v.co.x, -v.co.y)):
        a = math.atan2(v.co.x, -v.co.y)
        if groups and abs(a - groups[-1][-1][0]) < 0.12: groups[-1].append((a, v))
        else: groups.append([(a, v)])
    for g_ in groups:
        if len(g_) < 6: continue
        vs = [v for _, v in g_]; cen = sum((v.co for v in vs), Vector()) / len(vs)
        n_ = sum((v.normal for v in vs), Vector()).normalized()
        for v in vs: v.co -= n_ * (v.co - cen).dot(n_)        # the plate flattened onto its own plane
        ext = max((v.co - cen).length for v in vs)
        plates.append((np.array(cen[:]), np.array(n_[:]), ext))
    sv = [v for v in bm.verts if abs(math.atan2(v.co.x, -v.co.y)) < 0.24 and 0.031 < v.co.z < 0.07 and radial_n(v) > 0.7]
    if len(sv) > 6:                                         # the shield's face, flattened for its two rows of runes
        cen = sum((v.co for v in sv), Vector()) / len(sv); n_ = sum((v.normal for v in sv), Vector()).normalized()
        for v in sv: v.co -= n_ * (v.co - cen).dot(n_)
        shield = (np.array(cen[:]), np.array(n_[:]), max((v.co - cen).length for v in sv))
    bm.to_mesh(me); bm.free(); me.update()
    co = np.array([v.co[:] for v in me.vertices])
    print(f"  smoothed: {len(band)} rune-row verts, {len(plates)} diamond plates, shield {'yes' if shield else 'no'}")

def load(name):
    im = bpy.data.images.load(os.path.join(TEXDIR, name)); w, h = im.size
    return np.array(im.pixels[:], np.float32).reshape(h, w, 4)
A0 = load("Color.jpg"); RES = A0.shape[0]
N0 = load("Normal.png")

# ---------------------------------------------------------------- per texel: where on the crown, facing where, how convex
bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
convex = np.zeros(len(bm.verts), np.float32)
for v in bm.verts:
    if not v.link_edges: continue
    convex[v.index] = -np.mean([(e.other_vert(v).co - v.co).normalized().dot(v.normal) for e in v.link_edges])
bm.free()
ev = np.array([e.vertices[:] for e in me.edges]); broad = convex.copy()
for _ in range(10):                                         # convexity spread over the neighbourhood: broad light and shade
    acc = np.zeros_like(broad); cnt = np.zeros_like(broad)
    np.add.at(acc, ev[:, 0], broad[ev[:, 1]]); np.add.at(acc, ev[:, 1], broad[ev[:, 0]]); np.add.at(cnt, ev[:, 0], 1); np.add.at(cnt, ev[:, 1], 1)
    broad = 0.5 * broad + 0.5 * acc / np.maximum(cnt, 1)
vn = np.array([v.normal[:] for v in me.vertices], np.float32)
me.calc_loop_triangles()
uvs = np.zeros(len(me.loops) * 2); me.uv_layers.active.data.foreach_get("uv", uvs); uvs = uvs.reshape(-1, 2)
q_all = uvs * RES - 0.5
P = np.zeros((RES, RES, 3), np.float32); NN = np.zeros((RES, RES, 3), np.float32); CV = np.zeros((RES, RES), np.float32); CVS = np.zeros((RES, RES), np.float32); HIT = np.zeros((RES, RES), bool)
for tri in me.loop_triangles:
    q = q_all[list(tri.loops)]; vi = list(tri.vertices)
    x0, y0 = np.floor(q.min(0)).astype(int); x1, y1 = np.ceil(q.max(0)).astype(int)
    x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, RES - 1), min(y1, RES - 1)
    if x1 < x0 or y1 < y0: continue
    gx, gy = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1))
    (ax, ay), (bx, by), (cx, cy) = q
    den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
    if abs(den) < 1e-12: continue
    w0 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / den; w1 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / den; w2 = 1 - w0 - w1
    m = (w0 >= -0.02) & (w1 >= -0.02) & (w2 >= -0.02)
    if not m.any(): continue
    yy, xx = gy[m], gx[m]; W = np.stack([w0[m], w1[m], w2[m]], 1)
    P[yy, xx] = W @ co[vi]; NN[yy, xx] = W @ vn[vi]; CV[yy, xx] = W @ convex[vi]; CVS[yy, xx] = W @ broad[vi]; HIT[yy, xx] = True
print(f"  rasterised: {HIT.mean() * 100:.0f}% of the atlas in use")
ANG = np.arctan2(P[..., 0], -P[..., 1]); RR = np.hypot(P[..., 0], P[..., 1])
RAD = np.where(RR > 1e-5, (NN[..., 0] * P[..., 0] + NN[..., 1] * P[..., 1]) / np.maximum(RR, 1e-5) / np.maximum(np.linalg.norm(NN, axis=2), 1e-5), 0)
GROOVE = np.zeros((RES, RES), np.float32)
band_t = np.zeros((RES, RES), bool); plate_t = np.zeros((RES, RES), np.int32) - 1
if RUNES:
    ok = np.ones((RES, RES), bool)
    for c_, w_ in SKIP_ANG: ok &= np.abs(ANG - c_) > w_
    band_t = HIT & (P[..., 2] >= BAND_Z[0]) & (P[..., 2] <= BAND_Z[1]) & (RAD > 0.55) & ok
    for k_, (cen, n_, ext) in enumerate(plates):
        d_ = P - cen
        m_ = HIT & (np.abs(d_ @ n_) < 0.0015) & (np.linalg.norm(d_, axis=2) < ext * 1.05) & ((NN @ n_) / np.maximum(np.linalg.norm(NN, axis=2), 1e-6) > 0.8)
        plate_t[m_] = k_
    shield_t = np.zeros((RES, RES), bool)
    if shield:
        d_ = P - shield[0]
        shield_t = HIT & (np.abs(d_ @ shield[1]) < 0.0015) & (np.linalg.norm(d_, axis=2) < shield[2] * 1.05) & ((NN @ shield[1]) / np.maximum(np.linalg.norm(NN, axis=2), 1e-6) > 0.8)
N0[:] = (0.5, 0.5, 1.0, 1.0)                                 # the generator's normal map was the other half of the blobs: flat

# ---------------------------------------------------------------- the new colours
rgb = A0[..., :3]
mx_, mn_ = rgb.max(2), rgb.min(2); val = mx_; sat = np.where(mx_ > 1e-4, (mx_ - mn_) / np.maximum(mx_, 1e-4), 0)
hue = np.zeros_like(val)
r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
d = np.maximum(mx_ - mn_, 1e-5)
hue = np.where(mx_ == r, ((g - b) / d) % 6, np.where(mx_ == g, (b - r) / d + 2, (r - g) / d + 4)) / 6.0
lum = rgb @ np.array([0.299, 0.587, 0.114], np.float32)
gem = (sat > 0.28) & (val > 0.22) & (hue > 0.33) & (hue < 0.72)
greenish = gem & (hue < 0.5)
bone = (~gem) & (val > 0.62) & (sat < 0.35) & (r - b > 0.035)
radial = np.zeros_like(lum)
pxy = P[..., :2]; rr = np.linalg.norm(pxy, axis=2)
radial = np.where(rr > 1e-5, (NN[..., 0] * pxy[..., 0] + NN[..., 1] * pxy[..., 1]) / np.maximum(rr, 1e-5) / np.maximum(np.linalg.norm(NN, axis=2), 1e-5), 0)
inner = HIT & (radial < -0.45) & (~gem) & (~bone)

rng = np.random.default_rng(7)
def smooth_noise(scale):
    n = rng.random((RES // scale + 2, RES // scale + 2)).astype(np.float32)
    yy, xx = np.mgrid[0:RES, 0:RES] / scale
    y0, x0 = yy.astype(int), xx.astype(int); fy, fx = yy - y0, xx - x0
    return (n[y0, x0] * (1 - fx) * (1 - fy) + n[y0, x0 + 1] * fx * (1 - fy) + n[y0 + 1, x0] * (1 - fx) * fy + n[y0 + 1, x0 + 1] * fx * fy)
noise = 0.6 * smooth_noise(48) + 0.4 * smooth_noise(9)

# metal, painted from scratch (none of the generator's smudges): bronze with broad patches and a fine hammered grain,
# lighter where the shape bulges, darker in its hollows, worn to copper on the sharpest edges
IRON = np.array([0.075, 0.062, 0.052]); BRONZE = np.array([0.30, 0.21, 0.13]); LIGHT = np.array([0.56, 0.43, 0.29])
patches = 0.6 * smooth_noise(96) + 0.4 * smooth_noise(24); hammer = 0.5 * smooth_noise(7) + 0.5 * smooth_noise(3)
t = np.clip(0.46 + (patches - 0.5) * 0.45 + (hammer - 0.5) * 0.14 + np.clip(CVS * 5, -0.3, 0.3), 0, 1)
metal_col = np.where(t[..., None] < 0.55, IRON + (BRONZE - IRON) * (t[..., None] / 0.55), BRONZE + (LIGHT - BRONZE) * ((t[..., None] - 0.55) / 0.45))
edge = np.clip((CV - 0.07) * 7, 0, 1)
cavity = np.clip((-CV - 0.03) * 10, 0, 1) * 0.6 + np.clip(-CVS * 8, 0, 1) * 0.4
metal_col = metal_col * (1 - 0.6 * cavity[..., None]) + (np.array([0.66, 0.42, 0.26]) - metal_col) * (0.45 * edge[..., None])
A = metal_col.astype(np.float32)
# the band's inside: plain hammered dark metal
A[inner] = (np.array([0.15, 0.12, 0.10]) * (0.8 + 0.4 * hammer[inner, None]))
# bone beads: clean ivory, shaded by their shape
A[bone] = np.array([0.84, 0.77, 0.62]) * (0.85 + 0.3 * np.clip(CVS[bone, None] * 6 + 0.5, 0, 1) - 0.15)
# where the painted gems were: dark metal settings - the faceted stones set over them carry the colour
A[gem] = BRONZE * 0.55 + (hammer[gem, None] - 0.5) * 0.04
greenish_at = greenish.copy()
# the two fish under the shield stand proud of the band: a carved scale pattern on them
if RUNES:
    Rb_ = float(np.median(RR[band_t])) if band_t.any() else 0.105
    fish = HIT & (np.abs(ANG) < 0.6) & (P[..., 2] < 0.04) & (RR > Rb_ + 0.0025) & (RAD > 0.2) & ~gem & ~bone
    if RUNES and shield: fish &= ~shield_t
    sz = 0.0026; u_ = ANG * Rb_ / sz; v_ = P[..., 2] / sz
    row_ = np.floor(v_); u2 = u_ + 0.5 * (row_ % 2); fu = u2 - np.floor(u2) - 0.5; fv = v_ - row_
    dsc = np.hypot(fu, fv * 0.9)
    line_ = np.clip(1 - np.abs(dsc - 0.5) / 0.09, 0, 1) * (fv > 0.05)
    A[fish] = A[fish] * (1 - 0.6 * line_[fish, None]) + (np.array([0.62, 0.46, 0.30]) - A[fish]) * (0.18 * np.clip(0.5 - dsc[fish], 0, 1)[:, None])
    print(f"  fish scales on {int(fish.sum())} texels")# ---------------------------------------------------------------- crisp runes carved into the smoothed areas
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
    WORD = "f u th a r k g n t z o d m a".split()
    def carve(mask, sx, sy, segs):
        """Grooves for the strokes (in the area's own 2D coordinates sx, sy) on the texels in mask."""
        if not len(segs) or not mask.any(): return 0
        S_ = np.array(segs, np.float32); px_, py_ = sx[mask][:, None], sy[mask][:, None]; best = np.full(px_.shape[0], 9.0, np.float32)
        for c0 in range(0, len(S_), 48):
            s_ = S_[c0:c0 + 48]; ax_, ay_, bx_, by_, ww = [s_[:, i][None, :] for i in range(5)]
            dx, dy = bx_ - ax_, by_ - ay_
            tt = np.clip(((px_ - ax_) * dx + (py_ - ay_) * dy) / np.maximum(dx * dx + dy * dy, 1e-14), 0, 1)
            best = np.minimum(best, (np.hypot(px_ - (ax_ + tt * dx), py_ - (ay_ + tt * dy)) / ww).min(1))
        groove = np.clip((1.25 - best) * 3, 0, 1); rim = np.clip((2.0 - best) * 1.5, 0, 1) - groove
        ii, jj = np.nonzero(mask)
        A[ii, jj] = A[ii, jj] * (1 - 0.8 * groove[:, None]) + (np.array([0.62, 0.45, 0.30]) - A[ii, jj]) * (0.25 * np.clip(rim, 0, 1)[:, None])
        GROOVE[ii, jj] = np.maximum(GROOVE[ii, jj], groove)
        return int((groove > 0.5).sum())
    # the rim row: arc length round the crown across, height up; runes run left to right seen from outside
    Rb = float(np.median(RR[band_t])) if band_t.any() else 0.105
    h_ = (BAND_Z[1] - BAND_Z[0]) * 0.72; zc = (BAND_Z[0] + BAND_Z[1]) / 2 - h_ / 2
    segs = []; k_ = 0; s_ = -math.pi * Rb
    while s_ < math.pi * Rb:
        a0, a1 = s_ / Rb, (s_ + 0.6 * h_) / Rb
        if ang_ok(a0) and ang_ok(a1):
            for (x0, y0), (x1, y1) in GL[WORD[k_ % len(WORD)]]:
                segs.append((s_ + x0 * h_, zc + y0 * h_, s_ + x1 * h_, zc + y1 * h_, 0.085 * h_))
            k_ += 1
        s_ += 1.35 * h_
    n_band = carve(band_t, ANG * Rb, P[..., 2], segs)
    # each diamond plate: one big rune, upright, centred
    n_pl = 0
    for k2, (cen, n_, ext) in enumerate(plates):
        up = np.array([0, 0, 1.0]) - n_ * n_[2]; up /= max(np.linalg.norm(up), 1e-6); right = np.cross(up, n_)
        d_ = P - cen; sx, sy = d_ @ right, d_ @ up
        h2 = ext * 0.95; glyph = GL[["o", "d", "z", "t", "g", "m"][k2 % 6]]
        segs = [((x0 - 0.3) * h2, (y0 - 0.5) * h2, (x1 - 0.3) * h2, (y1 - 0.5) * h2, 0.075 * h2) for (x0, y0), (x1, y1) in glyph]
        n_pl += carve(plate_t == k2, sx, sy, segs)
    if shield:                                              # the shield: two rows, as on the reference
        cen, n_, ext = shield
        up = np.array([0, 0, 1.0]) - n_ * n_[2]; up /= max(np.linalg.norm(up), 1e-6); right = np.cross(up, n_)
        d_ = P - cen; sx, sy = d_ @ right, d_ @ up
        h3 = ext * 0.32; segs = []
        for row, word, yc in ((0, "f u th a r".split(), 0.42), (1, "s m m s".split(), -0.05)):
            w_tot = (len(word) - 1) * 0.85 * h3 + 0.6 * h3; x_ = -w_tot / 2
            for gname in word:
                for (x0, y0), (x1, y1) in GL[gname]:
                    segs.append((x_ + x0 * h3, yc * ext + (y0 - 0.5) * h3, x_ + x1 * h3, yc * ext + (y1 - 0.5) * h3, 0.08 * h3))
                x_ += 0.85 * h3
        n_pl += carve(shield_t, sx, sy, segs)
    print(f"  runes carved: {k_} round the rim ({n_band} texels), one on each of {len(plates)} plates ({n_pl} texels)")
A = np.clip(A, 0, 1)

MET = np.where(bone, 0.0, 0.55 - 0.25 * cavity).astype(np.float32); MET[inner] = 0.45
SM = np.where(bone, 0.35, 0.40 + 0.25 * edge - 0.15 * cavity + (hammer - 0.5) * 0.1).astype(np.float32)
SM *= 1 - 0.5 * GROOVE; MET *= 1 - 0.6 * GROOVE                # the grooves duller than the metal round them
E = np.zeros_like(A)
print(f"  texels: gems {gem.sum()}, bone {bone.sum()}, inside {inner.sum()}")

# ---------------------------------------------------------------- faceted stones over the painted gems
if os.environ.get("VDW_GEMS", "1") == "1":
    from collections import deque
    lab = np.full((RES, RES), -1, np.int32); comps = []
    ys, xs = np.nonzero(gem & HIT)
    for y, x in zip(ys, xs):
        if lab[y, x] >= 0: continue
        qd = deque([(y, x)]); lab[y, x] = len(comps); pts = []
        while qd:
            cy_, cx_ = qd.popleft(); pts.append((cy_, cx_))
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = cy_ + dy, cx_ + dx
                if 0 <= ny < RES and 0 <= nx < RES and lab[ny, nx] < 0 and gem[ny, nx] and HIT[ny, nx]:
                    lab[ny, nx] = len(comps); qd.append((ny, nx))
        comps.append(np.array(pts))
    stones = []
    for pts in comps:
        if len(pts) < 40: continue
        p3 = P[pts[:, 0], pts[:, 1]]; n3 = NN[pts[:, 0], pts[:, 1]]
        cen = p3.mean(0); ext = np.ptp(p3, axis=0).max()
        if ext > 0.05 or ext < 0.004: continue                 # a stray patch, not one stone
        nrm = n3.mean(0); nrm /= max(np.linalg.norm(nrm), 1e-6)
        if (nrm[0] * cen[0] + nrm[1] * cen[1]) < 0: continue    # inside the band
        best = pts[np.argmax(val[pts[:, 0], pts[:, 1]])]
        green_ = greenish_at[pts[:, 0], pts[:, 1]].mean() > 0.5
        stones.append([cen, nrm, ext, best, len(pts), green_])
    merged = []                                                 # one gem split over several UV islands
    for s in sorted(stones, key=lambda s: -s[4]):
        if all(np.linalg.norm(s[0] - m[0]) > 0.012 for m in merged): merged.append(s)
    bm = bmesh.new(); bm.from_mesh(me); uvl = bm.loops.layers.uv.active
    for cen, nrm, ext, best, _, green_ in merged:
        y_, x_ = best; sl = (slice(max(y_ - 2, 0), y_ + 3), slice(max(x_ - 2, 0), x_ + 3))
        A[sl] = (0.05, 0.42, 0.22) if green_ else (0.05, 0.20, 0.62); MET[sl] = 0.0; SM[sl] = 0.9
        E[sl] = (0.02, 0.2, 0.1) if green_ else (0.02, 0.1, 0.3)
        rad = float(np.clip(ext * 0.72, 0.005, 0.0135))
        g = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)["verts"]
        z = Vector(nrm); x_ = Vector((0, 0, 1)).cross(z); x_ = x_.normalized() if x_.length > 1e-4 else Vector((1, 0, 0)); y_ = z.cross(x_)
        R = Matrix((x_, y_, z)).transposed()
        for v in g:
            lv = Vector((v.co.x * rad, v.co.y * rad * 1.15, max(v.co.z, -0.2) * rad * 0.55))
            v.co = Vector(cen) + R @ lv - z * rad * 0.1
        fs = {f for v in g for f in v.link_faces}
        u, vv = (best[1] + 0.5) / RES, (best[0] + 0.5) / RES
        for f in fs:
            f.smooth = False
            for l in f.loops: l[uvl].uv = (u, vv)
    bm.to_mesh(me); bm.free(); me.update()
    print(f"  faceted stones set: {len(merged)}")

# ---------------------------------------------------------------- new seams and a clean unwrap; the new colours baked onto it
OLD = me.uv_layers.active.name
def as_image(arr, name, color=True):
    im = bpy.data.images.new(name, RES, RES, alpha=True, float_buffer=not color)
    if not color: im.colorspace_settings.name = "Non-Color"
    im.pixels[:] = np.ascontiguousarray(arr, np.float32).ravel(); return im
ones = np.ones((RES, RES), np.float32)
src_img = {"alb": as_image(np.dstack([A, ones]), "src_alb"), "met": as_image(np.dstack([MET, MET, MET, ones]), "src_met", False),
           "sm": as_image(np.dstack([SM, SM, SM, ones]), "src_sm", False), "em": as_image(np.dstack([E, ones]), "src_em"),
           "nrm": as_image(N0, "src_nrm", False)}
new = me.uv_layers.new(name="UVMap"); me.uv_layers.active = new
bpy.context.view_layer.objects.active = crown; crown.select_set(True)
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.mark_seam(clear=True)
bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.0, area_weight=0.0)
bpy.ops.uv.select_all(action='SELECT'); bpy.ops.uv.seams_from_islands()          # the new seams, along the crown's hard edges
bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=0.003)                             # unwrapped again on them: less stretching
bpy.ops.uv.select_all(action='SELECT'); bpy.ops.uv.average_islands_scale()
bpy.ops.uv.pack_islands(rotate=True, scale=True, margin=0.004)
bpy.ops.object.mode_set(mode='OBJECT')
new = me.uv_layers["UVMap"]; me.uv_layers.active = new; new.active_render = True
print(f"  re-seamed and unwrapped: {sum(1 for e in me.edges if e.use_seam)} seam edges")

sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 4
sc.render.bake.margin = 12; sc.render.bake.use_clear = True
mat = bpy.data.materials.new(NAME + "_bake"); mat.use_nodes = True; nt = mat.node_tree; bs = nt.nodes["Principled BSDF"]; out = nt.nodes["Material Output"]
uvn = nt.nodes.new("ShaderNodeUVMap"); uvn.uv_map = OLD
def tex(im):
    t_ = nt.nodes.new("ShaderNodeTexImage"); t_.image = im; t_.interpolation = 'Closest' if im.name == "src_never" else 'Linear'
    nt.links.new(uvn.outputs["UV"], t_.inputs["Vector"]); return t_
nm = nt.nodes.new("ShaderNodeNormalMap"); nm.uv_map = OLD
nt.links.new(tex(src_img["nrm"]).outputs[0], nm.inputs["Color"]); nt.links.new(nm.outputs[0], bs.inputs["Normal"])
me.materials.clear(); me.materials.append(mat)
target = nt.nodes.new("ShaderNodeTexImage")
def bake_emit(key, color=True):
    im = bpy.data.images.new(f"{NAME}_{key}_baked", RES, RES, alpha=True)
    if not color: im.colorspace_settings.name = "Non-Color"
    em = nt.nodes.new("ShaderNodeEmission"); nt.links.new(tex(src_img[key]).outputs[0], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"]); target.image = im; nt.nodes.active = target
    bpy.ops.object.bake(type='EMIT'); return np.array(im.pixels[:], np.float32).reshape(RES, RES, 4)
bA = bake_emit("alb"); bM = bake_emit("met", False)[..., 0]; bS = bake_emit("sm", False)[..., 0]; bE = bake_emit("em")
nt.links.new(bs.outputs[0], out.inputs["Surface"])
imn = bpy.data.images.new(f"{NAME}_nrm_baked", RES, RES, alpha=True); imn.colorspace_settings.name = "Non-Color"
target.image = imn; nt.nodes.active = target; sc.render.bake.normal_space = 'TANGENT'
bpy.ops.object.bake(type='NORMAL'); bN = np.array(imn.pixels[:], np.float32).reshape(RES, RES, 4)
me.uv_layers.remove(me.uv_layers[OLD])
print("  baked albedo, metal, smoothness, emission and normal onto the new unwrap")

# ---------------------------------------------------------------- written out (Unity names) and the material for previews
def save(arr, kind, color=True):
    im = bpy.data.images.new(f"{NAME}_{kind}", RES, RES, alpha=True)
    if not color: im.colorspace_settings.name = "Non-Color"
    im.pixels[:] = np.ascontiguousarray(arr, np.float32).ravel(); p = os.path.join(TEX, f"{NAME}_Unity_{kind}.png")
    im.filepath_raw = p; im.file_format = 'PNG'; im.save(); return p
bA[..., 3] = 1; bE[..., 3] = 1; bN[..., 3] = 1
p_a = save(bA, "Albedo"); p_m = save(np.dstack([bM, bM, bM, bS]), "MetallicSmoothness", False)
p_n = save(bN, "Normal", False); p_e = save(bE, "Emission")
mat = bpy.data.materials.new(NAME); mat.use_nodes = True; nt = mat.node_tree; bs = nt.nodes["Principled BSDF"]
def tex2(p, col=True):
    t_ = nt.nodes.new("ShaderNodeTexImage"); t_.image = bpy.data.images.load(p)
    if not col: t_.image.colorspace_settings.name = "Non-Color"
    return t_
nt.links.new(tex2(p_a).outputs[0], bs.inputs["Base Color"])
tm = tex2(p_m, False); sep = nt.nodes.new("ShaderNodeSeparateColor"); nt.links.new(tm.outputs[0], sep.inputs[0]); nt.links.new(sep.outputs[0], bs.inputs["Metallic"])
inv = nt.nodes.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1; nt.links.new(tm.outputs["Alpha"], inv.inputs[1]); nt.links.new(inv.outputs[0], bs.inputs["Roughness"])
nm = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(tex2(p_n, False).outputs[0], nm.inputs["Color"]); nt.links.new(nm.outputs[0], bs.inputs["Normal"])
nt.links.new(tex2(p_e).outputs[0], bs.inputs["Emission Color"]); bs.inputs["Emission Strength"].default_value = 1.0
me.materials.clear(); me.materials.append(mat)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "Blender Files", f"{NAME}.blend"))
print("SAVED")