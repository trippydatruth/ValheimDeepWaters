# Builds a themed fishing rod from scratch, laid out like the hand-made rods (rod along +Z, 2.85 m, guides and the
# reel on the +Y side, butt at z = 0): butt cap, grip, reel seat with a side-mounted centre-pin reel (drum turns about
# X), fore-grip, a tapered blank, five guides getting smaller toward the tip, a tip-top and a modelled line.
# Every part is UV-mapped into a tile of one texture atlas, painted procedurally per theme (albedo, ORM, normal,
# emission). Writes an OBJ in centimetres for rig_rod2.py, the maps, and the reel's bounding box (for the turning part).
# env: VDW_THEME (blackmetal | yggdrasil | ashwood | haldor | leviathan | frostwood), VDW_OUT (folder), VDW_NAME
import bpy, bmesh, json, math, os
import numpy as np
from mathutils import Matrix, Vector

THEME = os.environ["VDW_THEME"]; OUT = os.environ["VDW_OUT"]; NAME = os.environ["VDW_NAME"]
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(abs(hash(THEME)) % 2**31)
for o in list(bpy.data.objects): bpy.data.objects.remove(o)

# ---------------------------------------------------------------- atlas tiles (u0, v0, u1, v1)
TILES = {"blank": (0.0, 0.0, 0.25, 1.0), "grip": (0.25, 0.5, 0.5, 1.0), "metal": (0.25, 0.0, 0.5, 0.5),
         "accent": (0.5, 0.5, 0.75, 1.0), "core": (0.5, 0.25, 0.75, 0.5), "glowtrim": (0.5, 0.0, 0.75, 0.25),
         "line": (0.75, 0.875, 1.0, 1.0), "tendril": (0.75, 0.5, 1.0, 0.875), "bone": (0.75, 0.0, 1.0, 0.5)}
def tuv(tile, u, v):
    a, b, c, d = TILES[tile]; return (a + (c - a) * u, b + (d - b) * v)

bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
parts = []                                    # (name, tile) per loose part, in creation order
def face(verts, uvs):
    f = bm.faces.new(verts)
    for l, uv in zip(f.loops, uvs): l[uvl].uv = uv
    return f

def tube(path, radii, tile, seg=14, cap0=True, cap1=True, vscale=1.0, name="tube"):
    """A tube along a list of points with a radius per point."""
    rings = []
    for i, p in enumerate(path):
        p = Vector(p); t = (Vector(path[min(i + 1, len(path) - 1)]) - Vector(path[max(i - 1, 0)])).normalized()
        a = Vector((1, 0, 0)) if abs(t.x) < 0.9 else Vector((0, 1, 0)); a = (a - t * a.dot(t)).normalized(); b = t.cross(a)
        rings.append([bm.verts.new(p + (a * math.cos(k * 2 * math.pi / seg) + b * math.sin(k * 2 * math.pi / seg)) * radii[i]) for k in range(seg)])
    L = [0.0]
    for i in range(1, len(path)): L.append(L[-1] + (Vector(path[i]) - Vector(path[i - 1])).length)
    tot = max(L[-1], 1e-6)
    for i in range(len(path) - 1):
        for k in range(seg):
            k2 = (k + 1) % seg; u0, u1 = k / seg, (k + 1) / seg; v0, v1 = L[i] / tot * vscale, L[i + 1] / tot * vscale
            face([rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]],
                 [tuv(tile, u0, v0 % 1.0001), tuv(tile, u1, v0 % 1.0001), tuv(tile, u1, min(v1, 1)), tuv(tile, u0, min(v1, 1))])
    for cap, ring, flip in ((cap0, rings[0], True), (cap1, rings[-1], False)):
        if not cap: continue
        c = bm.verts.new(sum((v.co for v in ring), Vector()) / len(ring))
        for k in range(seg):
            vs = [ring[k], ring[(k + 1) % seg], c]
            if flip: vs = vs[::-1]
            face(vs, [tuv(tile, 0.1, 0.02), tuv(tile, 0.2, 0.02), tuv(tile, 0.15, 0.05)])
    parts.append((name, tile))

def straight(z0, z1, r0, r1, tile, seg=14, n=None, xy=(0, 0), **kw):
    n = n or max(2, int((z1 - z0) / 0.03) + 1)
    zs = np.linspace(z0, z1, n); path = [(xy[0], xy[1], z) for z in zs]
    tube(path, list(np.linspace(r0, r1, n)), tile, seg, **kw)

def torus(center, axis, R, r, tile, seg=20, mseg=8, name="ring"):
    ax = Vector(axis).normalized(); a = Vector((1, 0, 0)) if abs(ax.x) < 0.9 else Vector((0, 1, 0)); a = (a - ax * a.dot(ax)).normalized(); b = ax.cross(a)
    grid = []
    for i in range(seg):
        th = 2 * math.pi * i / seg; d = a * math.cos(th) + b * math.sin(th)
        grid.append([bm.verts.new(Vector(center) + d * (R + r * math.cos(2 * math.pi * j / mseg)) + ax * r * math.sin(2 * math.pi * j / mseg)) for j in range(mseg)])
    for i in range(seg):
        for j in range(mseg):
            i2, j2 = (i + 1) % seg, (j + 1) % mseg
            face([grid[i][j], grid[i2][j], grid[i2][j2], grid[i][j2]],
                 [tuv(tile, i / seg, j / mseg), tuv(tile, (i + 1) / seg, j / mseg), tuv(tile, (i + 1) / seg, (j + 1) / mseg), tuv(tile, i / seg, (j + 1) / mseg)])
    parts.append((name, tile))

def disc(center, axis, r_out, width, tile, seg=24, name="disc"):
    """A short closed cylinder along `axis` (a reel drum or plate)."""
    ax = Vector(axis).normalized(); c = Vector(center)
    tube([tuple(c - ax * width / 2), tuple(c + ax * width / 2)], [r_out, r_out], tile, seg, name=name)

def sphere(center, r, tile, seg=12, rings=8, squash=1.0, name="sphere"):
    c = Vector(center); vs = []
    for i in range(rings + 1):
        ph = math.pi * i / rings
        vs.append([bm.verts.new(c + Vector((math.sin(ph) * math.cos(2 * math.pi * k / seg), math.sin(ph) * math.sin(2 * math.pi * k / seg), math.cos(ph) * squash)) * r) for k in range(seg)])
    for i in range(rings):
        for k in range(seg):
            k2 = (k + 1) % seg
            face([vs[i][k], vs[i][k2], vs[i + 1][k2], vs[i + 1][k]],
                 [tuv(tile, k / seg, i / rings), tuv(tile, (k + 1) / seg, i / rings), tuv(tile, (k + 1) / seg, (i + 1) / rings), tuv(tile, k / seg, (i + 1) / rings)])
    parts.append((name, tile))

def spike(base, direction, length, width, tile, name="spike"):
    """A four-sided pyramid (a fang, a flame tongue, a thorn)."""
    d = Vector(direction).normalized(); a = Vector((1, 0, 0)) if abs(d.x) < 0.9 else Vector((0, 1, 0)); a = (a - d * a.dot(d)).normalized(); b = d.cross(a)
    B = Vector(base); quad = [bm.verts.new(B + (a * x + b * y) * width) for x, y in ((1, 0), (0, 1), (-1, 0), (0, -1))]
    tip = bm.verts.new(B + d * length)
    for k in range(4): face([quad[k], quad[(k + 1) % 4], tip], [tuv(tile, k / 4, 0), tuv(tile, (k + 1) / 4, 0), tuv(tile, k / 4 + 0.125, 1)])
    face(quad[::-1], [tuv(tile, .5, .5)] * 4)
    parts.append((name, tile))

# ---------------------------------------------------------------- the rod (metres)
L = 2.85; Z_CAP, Z_GRIP, Z_SEAT, Z_FORE, Z_BLANK = 0.045, 0.42, 0.56, 0.63, 0.63
R_BLANK0, R_BLANK1 = 0.0135, 0.0032
REEL = Vector((0.0, 0.07, 0.49)); DRUM_R, DRUM_W = 0.048, 0.034
cfg = {
    "blackmetal": dict(grip_r=0.022, cap="metal", seat="metal", fore="grip", reel="metal", rim="metal", knob="accent", guide="metal", wrap="grip", extra=["inlay", "trim"]),
    "yggdrasil":  dict(grip_r=0.022, cap="tendril", seat="tendril", fore="tendril", reel="metal", rim="metal", knob="core", guide="metal", wrap="tendril", extra=["roots", "core"]),
    "ashwood":    dict(grip_r=0.023, cap="metal", seat="metal", fore="grip", reel="metal", rim="metal", knob="core", guide="metal", wrap="metal", extra=["flames", "core"], reel_type="conventional"),
    "haldor":     dict(grip_r=0.022, cap="accent", seat="accent", fore="grip", reel="accent", rim="accent", knob="accent", guide="accent", wrap="accent", extra=["bands", "horn", "gem"], reel_type="conventional"),
    "leviathan":  dict(grip_r=0.023, cap="bone", seat="bone", fore="grip", reel="metal", rim="bone", knob="core", guide="bone", wrap="bone", extra=["sinews", "fang", "teeth"], reel_type="spinning", grip_z=45),
    "frostwood":  dict(grip_r=0.022, cap="metal", seat="metal", fore="grip", reel="metal", rim="accent", knob="core", guide="metal", wrap="grip", extra=["inlay", "core", "icicles"]),
}[THEME]
REEL_TYPE = cfg.get("reel_type", "centrepin")
# Parts whose name starts with "turn_" are the reel's turning part (rigged to Reel.Spool, about X through PIVOT).

straight(0.0, Z_CAP, cfg["grip_r"] * 1.15, cfg["grip_r"] * 1.1, cfg["cap"], name="cap")
straight(Z_CAP, Z_GRIP, cfg["grip_r"], cfg["grip_r"] * 0.92, "grip", name="grip")
straight(Z_GRIP, Z_SEAT, 0.0165, 0.0165, cfg["seat"], name="seat")
straight(Z_SEAT, Z_FORE, cfg["grip_r"] * 0.85, R_BLANK0 * 1.15, cfg["fore"], name="fore")
straight(Z_BLANK, L, R_BLANK0, R_BLANK1, "blank", seg=12, n=60, name="blank")
if REEL_TYPE == "centrepin":
    # a side-mounted centre-pin reel: a foot onto the seat, two plates and the drum between them, a knob on the -X side
    PIVOT = REEL
    straight(0.47, 0.51, 0.006, 0.006, cfg["seat"], seg=8, xy=(0, 0.03), name="foot")
    disc(REEL, (1, 0, 0), DRUM_R * 0.82, DRUM_W, cfg["reel"], name="turn_drum")
    disc(REEL + Vector((DRUM_W / 2 + 0.003, 0, 0)), (1, 0, 0), DRUM_R, 0.006, cfg["rim"], name="turn_plate_in")
    disc(REEL - Vector((DRUM_W / 2 + 0.003, 0, 0)), (1, 0, 0), DRUM_R, 0.006, cfg["rim"], name="turn_plate_out")
    crank = REEL - Vector((DRUM_W / 2 + 0.008, 0, 0)) + Vector((0, 0.026, 0))
    tube([tuple(REEL - Vector((DRUM_W / 2 + 0.007, 0, 0))), tuple(crank)], [0.004, 0.004], cfg["reel"], seg=8, name="turn_crank")
    sphere(crank - Vector((0.012, 0, 0)), 0.009, cfg["knob"], name="turn_knob")
    LINE_START = (0, REEL.y + DRUM_R * 0.82, REEL.z)
    PLATE_OUT = REEL - Vector((DRUM_W / 2 + 0.006, 0, 0)); PLATE_R = DRUM_R
elif REEL_TYPE == "conventional":
    # a conventional (baitcasting / trolling) reel on top of the seat: round side frames joined by bars, a wide spool
    # between them, a level-wind bar in front, a star drag, and a two-knob power crank on the +X side
    C = Vector((0.0, 0.05, 0.49)); FR, HW, SR = 0.034, 0.036, 0.027        # frame radius, half width, spool radius
    PIVOT = C
    straight(0.455, 0.525, 0.008, 0.008, cfg["seat"], seg=8, xy=(0, 0.022), name="foot")
    for s_ in (1, -1):
        disc(C + Vector((s_ * HW, 0, 0)), (1, 0, 0), FR, 0.009, cfg["rim"], name="frame")
        torus(C + Vector((s_ * (HW + 0.0045), 0, 0)), (1, 0, 0), FR * 0.98, 0.0028, "accent", seg=28, mseg=6, name="frame_rim")
    for (dy, dz) in ((-0.022, 0.02), (-0.022, -0.02), (0.026, -0.012)):        # pillars joining the frames
        tube([(-HW, C.y + dy, C.z + dz), (HW, C.y + dy, C.z + dz)], [0.0035, 0.0035], cfg["reel"], seg=8, name="pillar")
    disc(C, (1, 0, 0), SR, HW * 2 - 0.012, "line", name="turn_spool")             # line wound on the spool
    disc(C, (1, 0, 0), SR * 1.08, 0.004, cfg["reel"], name="turn_spool_flange")
    # level-wind: a bar across the front with a little line guide that rides it
    tube([(-HW, C.y + 0.012, C.z + FR * 0.95), (HW, C.y + 0.012, C.z + FR * 0.95)], [0.0028, 0.0028], cfg["reel"], seg=8, name="levelwind")
    torus((0.008, C.y + 0.018, C.z + FR * 0.95), (0, 0, 1), 0.005, 0.0015, cfg["guide"], seg=12, mseg=6, name="levelwind_guide")
    # star drag between the frame and the crank
    for k in range(6):
        a = 2 * math.pi * k / 6; d = Vector((0, math.cos(a), math.sin(a)))
        spike(C + Vector((HW + 0.011, 0, 0)), d, 0.016, 0.004, cfg["rim"], name="star")
    # the power crank: a shaft out of the +X frame, a long arm across, a knob at each end
    tube([tuple(C + Vector((HW + 0.004, 0, 0))), tuple(C + Vector((HW + 0.02, 0, 0)))], [0.004, 0.004], cfg["reel"], seg=8, name="turn_shaft")
    tube([tuple(C + Vector((HW + 0.02, 0, -0.036))), tuple(C + Vector((HW + 0.02, 0, 0.036)))], [0.0045, 0.0045], cfg["reel"], seg=8, name="turn_crank")
    for s_ in (1, -1):
        e = C + Vector((HW + 0.02, 0, s_ * 0.036))
        tube([tuple(e), tuple(e + Vector((0.006, 0, 0))), tuple(e + Vector((0.02, 0, 0)))], [0.0045, 0.0075, 0.0065], cfg["knob"], seg=10, name="turn_knob")
    LINE_START = (0, C.y + 0.018, C.z + FR * 0.95)
    PLATE_OUT = C - Vector((HW + 0.005, 0, 0)); PLATE_R = FR
elif REEL_TYPE == "spinning":
    # an open-face spinning reel hanging off the seat on a curved stem (guide side, +Y): a foot on the seat, the stem
    # sweeping down to a round gear housing, a rotor with a wire bail over the spool, the spool pointing up the rod
    # with its drag knob in front, and a flat crank arm out of the housing side with a big round knob (+X)
    BODY = Vector((0.0, 0.118, 0.462)); HR_ = 0.03
    PIVOT = BODY
    straight(0.448, 0.532, 0.0085, 0.0085, cfg["seat"], seg=8, xy=(0, 0.021), name="foot")
    # a tall S-curve like a real spinning reel: out from the foot, leaning back toward the butt, then down into the body
    stem = [(0, 0.024, 0.492), (0, 0.04, 0.5), (0, 0.056, 0.502), (0, 0.072, 0.494), (0, 0.086, 0.478), (0, 0.097, 0.462), (0, BODY.y - HR_ * 0.65, 0.452)]
    tube(stem, [0.0055, 0.006, 0.0066, 0.0075, 0.0088, 0.0105, 0.012], cfg["reel"], seg=10, name="stem")
    # gear housing: a fat disc across X with a raised side cover, blending into a rounded back
    disc(BODY, (1, 0, 0), HR_, 0.042, cfg["reel"], seg=28, name="housing")
    disc(BODY + Vector((0.023, 0, 0)), (1, 0, 0), HR_ * 0.68, 0.006, "accent", seg=24, name="side_cover")
    disc(BODY - Vector((0.023, 0, 0)), (1, 0, 0), HR_ * 0.55, 0.005, cfg["reel"], seg=20, name="side_cover2")
    # rotor (a cup round the spool shaft) with two arms, then the spool and its drag knob, all up the rod (+Z)
    RZ0, RZ1, SZ1 = BODY.z + HR_ * 0.7, BODY.z + HR_ * 0.7 + 0.03, BODY.z + HR_ * 0.7 + 0.064
    straight(RZ0, RZ1, 0.022, 0.026, cfg["reel"], seg=24, xy=(0, BODY.y), name="rotor")
    for s_ in (1, -1):
        tube([(s_ * 0.022, BODY.y, RZ0 + 0.006), (s_ * 0.03, BODY.y, RZ1 + 0.004)], [0.0045, 0.0038], cfg["reel"], seg=8, name="rotor_arm")
    straight(RZ1, SZ1 - 0.006, 0.0215, 0.0215, "glowtrim", seg=24, xy=(0, BODY.y), name="spool_line")
    torus((0, BODY.y, SZ1 - 0.004), (0, 0, 1), 0.024, 0.0035, "accent", seg=28, mseg=6, name="spool_lip")
    straight(RZ1 - 0.002, RZ1 + 0.003, 0.0255, 0.0255, "accent", seg=24, xy=(0, BODY.y), name="spool_base")
    straight(SZ1 - 0.002, SZ1 + 0.012, 0.014, 0.011, cfg["knob"], seg=16, xy=(0, BODY.y), name="drag_knob")
    # the bail: a wire arc from one rotor arm over the far side of the spool to the other, with the line roller
    arc = []
    for i in range(17):
        a = math.pi * i / 16; arc.append((0.031 * math.cos(a), BODY.y + 0.031 * math.sin(a) * 1.05, RZ1 + 0.006 + 0.004 * math.sin(a)))
    tube(arc, [0.0017] * len(arc), "accent", seg=6, name="bail")
    straight(RZ1 + 0.002, RZ1 + 0.012, 0.004, 0.004, "accent", seg=8, xy=(0.031, BODY.y), name="line_roller")
    # crank: shaft out of the +X side cover, a flat arm, a big round knob turned to face out
    S0 = BODY + Vector((0.026, 0, 0)); S1 = BODY + Vector((0.042, 0, 0))
    tube([tuple(S0), tuple(S1)], [0.0045, 0.0045], "accent", seg=10, name="turn_shaft")
    K = S1 + Vector((0, 0.026, -0.04))
    tube([tuple(S1), tuple(S1 + Vector((0, 0.012, -0.018))), tuple(K)], [0.0048, 0.0042, 0.0038], "accent", seg=8, name="turn_crank")
    disc(K + Vector((0.009, 0, 0)), (1, 0, 0), 0.0135, 0.014, "bone", seg=20, name="turn_knob")
    LINE_START = (0.031, BODY.y, RZ1 + 0.007)
    PLATE_OUT = None; PLATE_R = HR_
    HY, NOSE, H1, HR = BODY.y, SZ1, RZ1, 0.024                           # for the spool-front teeth and core below
else:
    # a spin cast reel on top of the seat: a closed housing with a cone nose the line leaves through, a thumb button at
    # the back, and the crank on the +X side
    H0, H1, NOSE = 0.445, 0.515, 0.575; HY, HR = 0.048, 0.03
    PIVOT = Vector((0.0, HY, 0.48))
    straight(0.45, 0.52, 0.008, 0.008, cfg["seat"], seg=8, xy=(0, 0.022), name="foot")
    zs = list(np.linspace(H0, NOSE, 16))
    rr = [HR * (0.6 + 0.4 * math.sin(min(1, (z - H0) / 0.018) * math.pi / 2)) if z < H1 else HR * (1 - 0.72 * ((z - H1) / (NOSE - H1)) ** 0.9) for z in zs]
    tube([(0, HY, z) for z in zs], rr, cfg["reel"], seg=20, name="housing")
    torus((0, HY, H1), (0, 0, 1), HR * 1.01, 0.0035, "glowtrim", seg=24, mseg=6, name="nose_ring")
    tube([(0, HY + HR * 0.75, H0 + 0.004), (0, HY + HR * 1.05, H0 - 0.006)], [0.0055, 0.0045], cfg["rim"], seg=10, name="thumb_button")
    tube([(0.0, HY, 0.48), (0.024 + HR * 0.6, HY, 0.48)], [0.0042, 0.0042], cfg["reel"], seg=8, name="turn_shaft")
    tube([(0.024 + HR * 0.6, HY, 0.48), (0.024 + HR * 0.6, HY + 0.034, 0.48)], [0.004, 0.004], cfg["reel"], seg=8, name="turn_crank")
    sphere(Vector((0.024 + HR * 0.6 + 0.008, HY + 0.034, 0.48)), 0.0085, cfg["knob"], squash=1.4, name="turn_knob")
    LINE_START = (0, HY, NOSE)
    PLATE_OUT = None; PLATE_R = HR
# guides: on short feet off the +Y side, smaller toward the tip; then the tip-top
GZ = [0.95, 1.35, 1.75, 2.15, 2.5]
for i, gz in enumerate(GZ):
    t = (gz - Z_BLANK) / (L - Z_BLANK); rb = R_BLANK0 + (R_BLANK1 - R_BLANK0) * t
    gr = 0.013 - 0.0018 * i; stand = rb + gr + 0.006
    torus((0, stand, gz), (0, 0, 1), gr, 0.0018, cfg["guide"], name="guide")
    tube([(0, rb * 0.8, gz), (0, stand - gr, gz)], [0.0016, 0.0016], cfg["guide"], seg=6, name="guide_foot")
    straight(gz - 0.012, gz + 0.012, rb * 1.25, rb * 1.25, cfg["wrap"], seg=10, name="whip")
torus((0, R_BLANK1 + 0.004, L - 0.004), (0, 0, 1), 0.004, 0.0012, cfg["guide"], name="tiptop")
# the line: off the top of the drum, through each guide, to the tip
line_pts = [LINE_START] + [(0, (R_BLANK0 + (R_BLANK1 - R_BLANK0) * ((gz - Z_BLANK) / (L - Z_BLANK))) + 0.013 - 0.0018 * i + 0.006, gz) for i, gz in enumerate(GZ)] + [(0, R_BLANK1 + 0.004, L)]
tube(line_pts, [0.0009] * len(line_pts), "line", seg=5, cap0=False, cap1=False, name="line")

# theme extras
if "inlay" in cfg["extra"]:            # gold inlay ring above the grip
    straight(Z_FORE - 0.004, Z_FORE + 0.018, R_BLANK0 * 1.3, R_BLANK0 * 1.3, "accent", name="inlay")
if "trim" in cfg["extra"]:             # gold trim round the rims of both reel plates (turns with the reel)
    for s_ in (1, -1):
        torus(REEL + Vector((s_ * (DRUM_W / 2 + 0.003), 0, 0)), (1, 0, 0), DRUM_R, 0.0032, "accent", seg=28, mseg=6, name="turn_plate_trim")
if "roots" in cfg["extra"]:            # root tendrils spiralling up the lower blank
    for k in range(3):
        pts, rr = [], []
        for i in range(90):
            t = i / 89; z = Z_FORE - 0.05 + t * 1.15; rb = R_BLANK0 + (R_BLANK1 - R_BLANK0) * ((z - Z_BLANK) / (L - Z_BLANK))
            a = k * 2 * math.pi / 3 + t * 5.5 * math.pi
            pts.append((math.cos(a) * (rb + 0.003), math.sin(a) * (rb + 0.003), z)); rr.append(0.0035 * (1 - 0.8 * t) + 0.0008)
        tube(pts, rr, "tendril", seg=6, name="root")
if "core" in cfg["extra"]:             # a glowing core on the outer plate (it turns with a centre-pin drum)
    if REEL_TYPE in ("spincast", "spinning"):
        sphere(Vector((0, HY, NOSE - 0.008)), 0.0085, "core", name="core")
    else:
        sphere(PLATE_OUT - Vector((0.006, 0, 0)), PLATE_R * 0.42, "core", squash=0.55, name=("turn_core" if REEL_TYPE == "centrepin" else "core"))
if "gem" in cfg["extra"]:              # an emerald set in the outer plate
    sphere(PLATE_OUT - Vector((0.004, 0, 0)), PLATE_R * 0.3, "core", squash=0.6, name="gem")
if "flames" in cfg["extra"]:           # flame tongues round the reel rim (on a conventional reel, round both frames)
    rims = [PIVOT] if REEL_TYPE == "centrepin" else [PIVOT + Vector((s_ * 0.036, 0, 0)) for s_ in (1, -1)]
    for ci, rc in enumerate(rims):
        for k in range(10):
            a = 2 * math.pi * (k + 0.5 * ci) / 10; d = Vector((0, math.cos(a), math.sin(a)))
            if REEL_TYPE != "centrepin" and d.y < -0.55: continue                # not down into the seat
            spike(rc + d * (PLATE_R * 0.95), d + Vector((0, 0, 0.35)), 0.018 + 0.008 * (k % 2), 0.006, "core",
                  name=("turn_flame" if REEL_TYPE == "centrepin" else "flame"))
if "bands" in cfg["extra"]:            # gold-leaf bands along the blank
    for z in (0.8, 1.15, 1.55, 1.95, 2.35, 2.7):
        rb = R_BLANK0 + (R_BLANK1 - R_BLANK0) * ((z - Z_BLANK) / (L - Z_BLANK))
        straight(z - 0.008, z + 0.008, rb * 1.3, rb * 1.3, "accent", seg=12, name="band")
if "horn" in cfg["extra"]:             # Haldor's little mead horn on a cord below the reel seat
    hp = [(0.0, 0.03, 0.42), (0.004, 0.045, 0.38), (0.01, 0.055, 0.345)]
    tube(hp, [0.0008] * 3, "grip", seg=5, name="cord")
    horn = [(0.01 + 0.012 * math.sin(t * 1.4), 0.055 + 0.02 * t, 0.345 - 0.06 * t + 0.02 * t * t) for t in np.linspace(0, 1, 10)]
    tube(horn, list(np.linspace(0.009, 0.002, 10)), "accent", seg=10, name="horn")
if "sinews" in cfg["extra"]:           # six sinew bands, one per great fish, glowing in its colour
    for k, z in enumerate((0.78, 1.12, 1.46, 1.8, 2.14, 2.48)):
        rb = R_BLANK0 + (R_BLANK1 - R_BLANK0) * ((z - Z_BLANK) / (L - Z_BLANK))
        torus((0, 0, z), (0, 0, 1), rb * 1.18, rb * 0.42, "glowtrim", seg=16, mseg=6, name=f"sinew{k}")
if "fang" in cfg["extra"]:             # a fang past the tip
    spike((0, -R_BLANK1 * 0.5, L - 0.03), (0, -0.4, -1), 0.05, 0.006, "bone", name="fang")
if "icicles" in cfg["extra"]:          # ice crystals round the reel's outer rim (they turn with the centre-pin drum)
    for k in range(12):
        a = 2 * math.pi * k / 12; d = Vector((0, math.cos(a), math.sin(a)))
        spike(PLATE_OUT + d * PLATE_R * 0.92, d + Vector((-0.25, 0, 0)), 0.012 + 0.006 * (k % 3 == 0), 0.0035, "glowtrim", name="turn_icicle")
if "teeth" in cfg["extra"]:            # teeth: round the spin cast's nose like a jaw, or spokes on a centre-pin plate
    if REEL_TYPE == "spinning":
        for k in range(10):
            a = 2 * math.pi * k / 10; d = Vector((math.cos(a), math.sin(a), 0))
            spike(Vector((0, HY, NOSE - 0.003)) + d * 0.022, d * 0.5 + Vector((0, 0, 1)), 0.011 + 0.004 * (k % 2), 0.0028, "bone", name="tooth")
    elif REEL_TYPE == "spincast":
        for k in range(10):
            a = 2 * math.pi * k / 10; d = Vector((math.cos(a), math.sin(a), 0))
            base = Vector((0, HY, H1 + 0.004)) + d * HR * 0.98
            spike(base, d * 0.35 + Vector((0, 0, 1)), 0.022 + 0.006 * (k % 2), 0.0042, "bone", name="tooth")
    else:
        for k in range(8):
            a = 2 * math.pi * k / 8; d = Vector((0, math.cos(a), math.sin(a)))
            spike(PLATE_OUT + d * PLATE_R * 0.3, d, PLATE_R * 0.62, 0.004, "bone", name="turn_tooth")

me = bpy.data.meshes.new(NAME); bm.to_mesh(me); bm.free()
ob = bpy.data.objects.new(NAME, me); bpy.context.scene.collection.objects.link(ob)
co = np.array([v.co[:] for v in me.vertices])
print(f"ROD {THEME}: {len(co)} verts, {len(parts)} parts, {np.ptp(co[:, 2]):.2f} m, {np.ptp(co[:, 0]) * 100:.1f} x {np.ptp(co[:, 1]) * 100:.1f} cm across")

# the turning part of the reel, by loose-part index (parts are built in order, so index = order of creation)
spool_parts = [i for i, (nm, _) in enumerate(parts) if nm.startswith("turn_")]

# ---------------------------------------------------------------- textures
S = 1024
alb = np.zeros((S, S, 3), np.float32); rough = np.full((S, S), 0.6, np.float32); metal = np.zeros((S, S), np.float32); emi = np.zeros((S, S, 3), np.float32)
hgt = np.zeros((S, S), np.float32)
def noise(scale, n=S):
    g = rng.random((n // scale + 2, n // scale + 2)); yy, xx = np.mgrid[0:n, 0:n] / scale
    x0, y0 = xx.astype(int), yy.astype(int); fx, fy = xx - x0, yy - y0; fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    return g[y0, x0] * (1 - fx) * (1 - fy) + g[y0, x0 + 1] * fx * (1 - fy) + g[y0 + 1, x0] * (1 - fx) * fy + g[y0 + 1, x0 + 1] * fx * fy
N1, N2, N3 = noise(64), noise(16), noise(4)
def region(tile):
    a, b, c, d = TILES[tile]; return slice(int(b * S), int(d * S)), slice(int(a * S), int(c * S))
def uvgrid(tile):
    ys, xs = region(tile); h, w = ys.stop - ys.start, xs.stop - xs.start
    v, u = np.mgrid[0:h, 0:w]; return ys, xs, u / max(w - 1, 1), v / max(h - 1, 1)
def paint(tile, col, r=None, m=None, e=None, h=None):
    ys, xs = region(tile)
    alb[ys, xs] = col
    if r is not None: rough[ys, xs] = r
    if m is not None: metal[ys, xs] = m
    if e is not None: emi[ys, xs] = e
    if h is not None: hgt[ys, xs] = h

def wood(tile, base, dark, grain=40):
    ys, xs, u, v = uvgrid(tile); n = N2[ys, xs] * 0.6 + N3[ys, xs] * 0.4
    g = (np.sin((u * 6 + n * 3) * grain * 0.2 + v * 2) * 0.5 + 0.5) ** 3
    col = np.array(base) * (1 - g[..., None] * 0.6) + np.array(dark) * g[..., None] * 0.6
    paint(tile, col * (0.85 + 0.3 * N1[ys, xs][..., None]), r=0.75, m=0.0, h=g * 0.3)
def metal_tile(tile, base, rough_v=0.35, met=1.0, wear=0.15):
    ys, xs, u, v = uvgrid(tile); n = N2[ys, xs]
    paint(tile, np.array(base) * (1 - wear + wear * 2 * n[..., None]), r=rough_v + 0.15 * N3[ys, xs], m=met, h=n * 0.1)
def wrap(tile, base, thread, cross=True):
    ys, xs, u, v = uvgrid(tile)
    if cross:
        p1 = np.abs(((u * 6 + v * 30) % 1) - 0.5) < 0.12; p2 = np.abs(((u * 6 - v * 30) % 1) - 0.5) < 0.12; m = (p1 | p2)
    else:
        m = np.abs(((v * 60) % 1) - 0.5) < 0.3
    col = np.where(m[..., None], np.array(thread), np.array(base)) * (0.85 + 0.3 * N3[ys, xs][..., None])
    paint(tile, col, r=0.85, m=0.0, h=m * 0.5)
def scales(tile, base, edge):
    ys, xs, u, v = uvgrid(tile); su, sv = u * 10, v * 40
    row = np.floor(sv); su = su + (row % 2) * 0.5; fu, fv = su % 1 - 0.5, sv % 1
    d = np.sqrt(fu ** 2 + (fv - 0.1) ** 2)
    m = np.clip((d - 0.42) * 12, 0, 1)
    col = np.array(base) * (1 - m[..., None]) + np.array(edge) * m[..., None]
    paint(tile, col * (0.8 + 0.4 * N2[ys, xs][..., None]), r=0.45, m=0.1, h=1 - d)
def flat(tile, col, r=0.5, m=0.0, e=None):
    ys, xs, u, v = uvgrid(tile)
    paint(tile, np.array(col) * (0.9 + 0.2 * N2[ys, xs][..., None]), r=r, m=m, e=None if e is None else np.array(e) * np.ones_like(alb[ys, xs]))

if THEME == "blackmetal":
    metal_tile("blank", (0.09, 0.09, 0.1), 0.35, 0.9, 0.25)
    wrap("grip", (0.55, 0.38, 0.22), (0.86, 0.82, 0.7))
    metal_tile("metal", (0.08, 0.08, 0.09), 0.3, 1.0, 0.3)
    metal_tile("accent", (0.95, 0.72, 0.28), 0.25, 1.0, 0.1)
    flat("core", (0.95, 0.72, 0.28), 0.25, 1.0); flat("glowtrim", (0.9, 0.85, 0.7))
    flat("line", (0.88, 0.85, 0.75), 0.8); flat("tendril", (0.86, 0.82, 0.7), 0.85); flat("bone", (0.85, 0.82, 0.72))
elif THEME == "yggdrasil":
    wood("blank", (0.78, 0.74, 0.62), (0.45, 0.42, 0.38), 50)
    ys, xs, u, v = uvgrid("blank")                         # eitr runes in a column down the front of the blank
    rune = ((np.abs(u - 0.25) < 0.05) & ((v * 26) % 1 < 0.55) & (N3[ys, xs] > 0.38)) | ((np.abs(u - 0.75) < 0.04) & ((v * 18 + 0.3) % 1 < 0.4) & (N3[ys, xs] > 0.45))
    alb[ys, xs][rune] = (0.55, 0.65, 1.0); emi[ys, xs] = np.where(rune[..., None], np.array([0.35, 0.45, 1.0]), 0)
    wood("grip", (0.6, 0.57, 0.5), (0.35, 0.33, 0.3), 30); wrap("grip", (0.55, 0.52, 0.46), (0.3, 0.32, 0.4), cross=True)
    ys, xs, u, v = uvgrid("metal"); car = np.array((0.08, 0.14, 0.16)) * (0.7 + 0.9 * N2[ys, xs][..., None]) + np.array((0.1, 0.2, 0.2)) * (N1[ys, xs] > 0.6)[..., None]
    paint("metal", car, r=0.15, m=0.2, e=np.array((0.01, 0.025, 0.07)) * (N1[ys, xs] > 0.62)[..., None])
    flat("core", (0.6, 0.7, 1.0), 0.2, 0.0, e=(0.55, 0.65, 1.0)); flat("glowtrim", (0.3, 0.4, 0.9), e=(0.3, 0.4, 0.9))
    wood("tendril", (0.36, 0.3, 0.24), (0.2, 0.17, 0.14), 20); flat("line", (0.75, 0.8, 0.95), 0.5); flat("accent", (0.5, 0.55, 0.7)); flat("bone", (0.8, 0.78, 0.7))
elif THEME == "ashwood":
    ys, xs, u, v = uvgrid("blank")                         # charred blackwood with ember cracks
    crack = np.abs(N2[ys, xs] - 0.5) < 0.006
    crack |= np.abs(noise(32)[ys, xs] - 0.5) < 0.004
    col = np.array((0.07, 0.06, 0.06)) * (0.7 + 0.6 * N3[ys, xs][..., None])
    alb[ys, xs] = np.where(crack[..., None], np.array((1.0, 0.45, 0.1)), col); rough[ys, xs] = 0.85; metal[ys, xs] = 0.0
    emi[ys, xs] = np.where(crack[..., None], np.array((1.0, 0.35, 0.05)), 0); hgt[ys, xs] = 1 - crack * 1.0
    scales("grip", (0.45, 0.16, 0.1), (0.15, 0.05, 0.04))
    metal_tile("metal", (0.95, 0.45, 0.15), 0.3, 1.0, 0.2)
    flat("core", (1.0, 0.55, 0.15), 0.3, 0.0, e=(1.0, 0.45, 0.08)); flat("glowtrim", (1.0, 0.5, 0.1), e=(1.0, 0.4, 0.05))
    metal_tile("accent", (0.95, 0.5, 0.2), 0.3); flat("line", (0.9, 0.6, 0.35), 0.6); flat("tendril", (0.2, 0.1, 0.08)); flat("bone", (0.3, 0.25, 0.22))
elif THEME == "haldor":
    wood("blank", (0.32, 0.14, 0.08), (0.14, 0.05, 0.03), 60)
    ys, xs, u, v = uvgrid("blank"); flecks = N3[ys, xs] > 0.8                         # flecks of gold leaf
    alb[ys, xs][flecks] = (0.95, 0.75, 0.3); metal[ys, xs][flecks] = 1.0; rough[ys, xs][flecks] = 0.25
    wrap("grip", (0.48, 0.07, 0.06), (0.95, 0.75, 0.3), cross=False)
    metal_tile("metal", (0.9, 0.7, 0.3), 0.25); metal_tile("accent", (0.98, 0.78, 0.35), 0.2, 1.0, 0.08)
    flat("core", (0.1, 0.65, 0.3), 0.05, 0.0, e=(0.02, 0.15, 0.06)); flat("glowtrim", (0.98, 0.78, 0.35), 0.2, 1.0)
    flat("line", (0.92, 0.88, 0.75), 0.7); flat("tendril", (0.5, 0.1, 0.08)); flat("bone", (0.9, 0.85, 0.7))
elif THEME == "leviathan":
    scales("blank", (0.06, 0.12, 0.18), (0.02, 0.04, 0.06))
    ys, xs, u, v = uvgrid("blank"); irid = (np.sin(v * 80 + u * 12) * 0.5 + 0.5)[..., None]
    alb[ys, xs] = alb[ys, xs] * (0.8 + 0.4 * irid) + np.array((0.0, 0.05, 0.06)) * irid; rough[ys, xs] = 0.3; metal[ys, xs] = 0.3
    scales("grip", (0.18, 0.2, 0.22), (0.05, 0.06, 0.07))
    ys, xs, u, v = uvgrid("bone"); bonec = np.array((0.86, 0.82, 0.7)) * (0.8 + 0.3 * N2[ys, xs][..., None]) - np.array((0.2, 0.2, 0.2)) * (N3[ys, xs] > 0.75)[..., None]
    paint("bone", bonec, r=0.55, m=0.0)
    metal_tile("metal", (0.05, 0.09, 0.13), 0.28, 0.85, 0.25)                    # abyssal reel body
    # the six sinews share one tile: a colour band per great fish across u (Moder blue, Bonemass green, Eikthyr
    # cyan, Elder green-gold, Yagluth red, Queen purple) - each band glows
    ys, xs, u, v = uvgrid("glowtrim")
    cols = np.array([(0.35, 0.75, 1.0), (0.45, 1.0, 0.3), (0.4, 0.95, 1.0), (0.75, 0.95, 0.25), (1.0, 0.3, 0.25), (0.85, 0.35, 1.0)])
    band = np.clip((u * 6).astype(int), 0, 5); c6 = cols[band] * (0.7 + 0.3 * np.sin(v * 40)[..., None])
    alb[ys, xs] = c6; emi[ys, xs] = c6 * 0.9; rough[ys, xs] = 0.4
    flat("core", (0.4, 0.9, 1.0), 0.2, 0.0, e=(0.35, 0.85, 1.0)); flat("line", (0.6, 0.95, 1.0), 0.4)
    metal_tile("accent", (0.82, 0.84, 0.86), 0.25, 0.9, 0.08); flat("tendril", (0.1, 0.15, 0.2))   # silver-bone trim

elif THEME == "frostwood":
    wood("blank", (0.74, 0.77, 0.8), (0.46, 0.52, 0.6), 45)                     # pale, frost-grey Timberwood
    ys, xs, u, v = uvgrid("blank"); vein = np.abs(noise(24)[ys, xs] - 0.5) < 0.012   # faint glowing frost veins
    alb[ys, xs] = np.where(vein[..., None], np.array((0.7, 0.9, 1.0)), alb[ys, xs]); emi[ys, xs] = np.where(vein[..., None], np.array((0.3, 0.6, 0.9)), 0)
    wrap("grip", (0.45, 0.33, 0.22), (0.78, 0.68, 0.52))                         # moose sinew wrapped over the grip
    metal_tile("metal", (0.76, 0.83, 0.9), 0.22, 1.0, 0.15)                      # icy silver
    metal_tile("accent", (0.22, 0.45, 0.78), 0.2, 0.5, 0.12)                     # frostcore blue
    flat("core", (0.55, 0.85, 1.0), 0.15, 0.0, e=(0.45, 0.8, 1.0)); flat("glowtrim", (0.7, 0.9, 1.0), 0.05, 0.0, e=(0.35, 0.7, 1.0))
    flat("line", (0.85, 0.92, 0.98), 0.5); flat("tendril", (0.4, 0.45, 0.5)); flat("bone", (0.85, 0.88, 0.9))

# the sinew rings take one fish's colour each: put each ring's UVs into its own sixth of the glowtrim tile
if THEME == "leviathan":
    me2 = ob.data; uvd = me2.uv_layers[0].data
    import collections
    # find which loose part each vertex belongs to (creation order == part order)
    bm2 = bmesh.new(); bm2.from_mesh(me2); bm2.verts.ensure_lookup_table(); comp = np.full(len(me2.vertices), -1); k = 0
    for vv in bm2.verts:
        if comp[vv.index] >= 0: continue
        st = [vv]; comp[vv.index] = k
        while st:
            x = st.pop()
            for e in x.link_edges:
                w = e.other_vert(x)
                if comp[w.index] < 0: comp[w.index] = k; st.append(w)
        k += 1
    bm2.free()
    sinews = [i for i, (nm, _) in enumerate(parts) if nm.startswith("sinew")]
    a, b, c, d = TILES["glowtrim"]
    for poly in me2.polygons:
        pidx = comp[poly.vertices[0]]
        if pidx in sinews:
            j = sinews.index(pidx)
            for li in poly.loop_indices:
                uu, vv2 = uvd[li].uv
                fu = (uu - a) / (c - a); uvd[li].uv = (a + (c - a) * ((j + 0.15 + 0.7 * fu) / 6), vv2)

# normal map from the height field (OpenGL / +Y up), soft
gy, gx = np.gradient(hgt * 2.0)
nrm = np.dstack((-gx, -gy, np.ones_like(hgt))); nrm /= np.linalg.norm(nrm, axis=2, keepdims=True); nrm = nrm * 0.5 + 0.5
def save(arr3, name, alpha=None):
    a4 = np.ones((S, S, 4), np.float32); a4[..., :3] = np.clip(arr3, 0, 1)
    if alpha is not None: a4[..., 3] = alpha
    im = bpy.data.images.new(name, S, S, alpha=True); im.pixels[:] = a4.ravel()
    p = os.path.join(OUT, name + ".png"); im.filepath_raw = p; im.file_format = 'PNG'; im.save(); return p
save(alb, f"{NAME}_src_albedo"); save(nrm, f"{NAME}_src_normal")
save(np.dstack((np.ones_like(rough), np.clip(rough, 0.03, 1), metal)), f"{NAME}_src_orm")
if emi.max() > 0: save(emi, f"{NAME}_Unity_Emission")
mat = bpy.data.materials.new(NAME); ob.data.materials.append(mat)
bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active = ob
# A conventional reel sits on top of the rod with its guides (user's choice), unlike the centre-pin and spinning reels
# that hang below: everything built on the +Y (bottom) side is mirrored to -Y. The crank stays on +X; the faces are
# turned back outward by the apply. The bend marker that rig_rod2 adds stays on +Y, which is still "down".
if REEL_TYPE == "conventional":
    ob.scale = (1, -1, 1); bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    ob.data.flip_normals()                 # the apply mirrors the faces but leaves them inside out
    PIVOT = Vector((PIVOT.x, -PIVOT.y, PIVOT.z))
    print("MIRRORED to -Y (reel and guides on top)")
bpy.ops.wm.obj_export(filepath=os.path.join(OUT, NAME + ".obj"), export_selected_objects=True, global_scale=100.0,
                      export_materials=False, export_normals=True, export_uv=True)
json.dump({"spool_parts": spool_parts, "pivot_cm": [PIVOT.x * 100, PIVOT.y * 100, PIVOT.z * 100], "reel_type": REEL_TYPE, "grip_z_cm": cfg.get("grip_z", 30),
           "seat_z_cm": Z_FORE * 100 + 1, "glow": bool(emi.max() > 0)},
          open(os.path.join(OUT, NAME + "_rig.json"), "w"))
print("WROTE", os.path.join(OUT, NAME + ".obj"))
