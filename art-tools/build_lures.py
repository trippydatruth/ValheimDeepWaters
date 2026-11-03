# The six boss lures, built procedurally: one mesh each with a small painted atlas (albedo, metal/smoothness, normal,
# emission). Laid out like the other bait: along Y with the head (where the line ties on) toward -Y, up +Z, about
# 9 cm long (the importer doubles bait in game). Each glows in its boss's colour (the Leviathan Rod's sinews).
#   antler - Eikthyr Elver:   a spoon carved from an antler tine, a lightning rune burned in, a deer-hair tuft
#   root   - Elder Bass:      a jointed two-piece swimbait of twisted root, greydwarf-eye glow, a moss tail
#   ooze   - Bonemass Catfish: a bone jig head in a dripping ball of ooze, a bone hook guard
#   wyrm   - Moder Scale:     a cupped silver dragon scale set with a frozen tear, ice-blue streamers
#   ember  - Yagluthgill:     a black-metal spinner blade round a smouldering surtling core, a red tail
#   chitin - Queen Eel:       a carved chitin jig with a tentacle skirt and glowing eyes
# env: VDW_LURE (one of the above), VDW_OUT (folder), VDW_NAME (e.g. bait_lure_antler)
import bpy, bmesh, math, os
import numpy as np
from mathutils import Vector, Matrix, noise

LURE = os.environ["VDW_LURE"]; OUT = os.environ["VDW_OUT"]; NAME = os.environ["VDW_NAME"]
for d in ("Textures", "Models", "Blender Files"): os.makedirs(os.path.join(OUT, d), exist_ok=True)
for o in list(bpy.data.objects): bpy.data.objects.remove(o)

# ---------------------------------------------------------------- materials: a 6 x 6 atlas of tiles
GLOW = {"antler": (0.35, 0.9, 1.0), "root": (0.75, 0.95, 0.25), "ooze": (0.45, 1.0, 0.3),
        "wyrm": (0.4, 0.75, 1.0), "ember": (1.0, 0.35, 0.12), "chitin": (0.8, 0.35, 1.0), "crown": (0.55, 0.85, 1.0)}.get(LURE, (1.0, 1.0, 1.0))   # the everyday lures don't glow
# name: (colour, colour2 for the pattern, roughness, metallic, emission strength 0..1, pattern)
MATS = {
    "bone":    ((0.86, 0.8, 0.66), (0.62, 0.52, 0.38), 0.55, 0.0, 0.0, "streak"),
    "glow":    (GLOW, GLOW, 0.3, 0.0, 1.0, "flat"),
    "hair":    ((0.42, 0.3, 0.18), (0.25, 0.17, 0.1), 0.85, 0.0, 0.0, "streak"),
    "flint":   ((0.36, 0.33, 0.29), (0.14, 0.13, 0.13), 0.32, 0.0, 0.0, "noise"),   # dark, glossy, brown-grey knapped stone
    "bark":    ((0.3, 0.2, 0.12), (0.14, 0.09, 0.05), 0.85, 0.0, 0.0, "streak"),
    "moss":    ((0.25, 0.42, 0.12), (0.12, 0.22, 0.06), 0.9, 0.0, 0.0, "noise"),
    "ooze":    ((0.32, 0.55, 0.18), (0.12, 0.3, 0.06), 0.15, 0.0, 0.35, "noise"),
    "silver":  ((0.82, 0.85, 0.9), (0.55, 0.62, 0.72), 0.22, 1.0, 0.0, "frost"),
    "blackmetal": ((0.12, 0.12, 0.13), (0.05, 0.05, 0.06), 0.35, 1.0, 0.0, "noise"),
    "core":    ((0.25, 0.08, 0.04), (1.0, 0.45, 0.1), 0.6, 0.0, 0.0, "cracks"),
    "chitin":  ((0.16, 0.08, 0.2), (0.05, 0.02, 0.07), 0.25, 0.0, 0.0, "plates"),
    "steel":   ((0.55, 0.56, 0.58), (0.4, 0.4, 0.42), 0.3, 1.0, 0.0, "noise"),
    "red":     ((0.65, 0.1, 0.06), (0.35, 0.04, 0.03), 0.7, 0.0, 0.2, "streak"),
    # the everyday lures
    "feather": ((0.9, 0.88, 0.82), (0.38, 0.3, 0.24), 0.8, 0.0, 0.0, "barred"),
    "bronze":  ((0.78, 0.5, 0.25), (0.5, 0.3, 0.14), 0.25, 1.0, 0.0, "noise"),
    "wood":    ((0.72, 0.56, 0.36), (0.5, 0.36, 0.2), 0.6, 0.0, 0.0, "streak"),
    "crank":   ((0.12, 0.32, 0.14), (0.92, 0.8, 0.28), 0.35, 0.0, 0.0, "gradient_u"),   # green back, yellow belly
    "resin":   ((0.85, 0.55, 0.15), (0.55, 0.3, 0.06), 0.15, 0.0, 0.0, "noise"),
    "leather": ((0.45, 0.3, 0.18), (0.28, 0.17, 0.09), 0.7, 0.0, 0.0, "noise"),
    "guck":    ((0.22, 0.32, 0.14), (0.1, 0.16, 0.06), 0.3, 0.0, 0.0, "rings"),
    "iron":    ((0.3, 0.3, 0.32), (0.18, 0.18, 0.2), 0.45, 1.0, 0.0, "noise"),
    "scales":  ((0.85, 0.88, 0.92), (0.25, 0.35, 0.5), 0.25, 0.7, 0.0, "scales_u"),    # silver sides, blue-grey back
    "white":   ((0.92, 0.9, 0.84), (0.75, 0.72, 0.66), 0.4, 0.0, 0.0, "noise"),
    "linen":   ((0.88, 0.84, 0.72), (0.7, 0.64, 0.5), 0.8, 0.0, 0.0, "streak"),
    "rind":    ((0.92, 0.78, 0.72), (0.75, 0.5, 0.45), 0.5, 0.0, 0.0, "noise"),
    "curly":   ((0.75, 0.85, 0.2), (0.5, 0.6, 0.08), 0.3, 0.0, 0.0, "noise"),             # chartreuse
    "thread":  ((0.12, 0.1, 0.08), (0.05, 0.04, 0.03), 0.7, 0.0, 0.0, "streak"),
    "black":   ((0.04, 0.04, 0.04), (0.0, 0.0, 0.0), 0.3, 0.0, 0.0, "flat"),
    "belly":   ((0.92, 0.80, 0.28), (0.80, 0.66, 0.18), 0.35, 0.0, 0.0, "noise"),             # a crankbait's yellow belly
    # the Deep North (a 7th value is the material's own glow colour)
    "ice":     ((0.75, 0.9, 0.98), (0.5, 0.75, 0.92), 0.08, 0.0, 0.12, "frost", (0.55, 0.85, 1.0)),
    "frostcore": ((0.06, 0.14, 0.3), (0.4, 0.8, 1.0), 0.35, 0.0, 0.0, "cracks", (0.45, 0.85, 1.0)),
    "gold":    ((0.95, 0.75, 0.3), (0.7, 0.5, 0.15), 0.2, 1.0, 0.0, "noise"),
    "jewel":   ((0.6, 0.88, 1.0), (0.3, 0.6, 0.95), 0.05, 0.0, 0.8, "flat", (0.55, 0.85, 1.0)),
    "blubber": ((0.86, 0.78, 0.72), (0.7, 0.58, 0.52), 0.35, 0.0, 0.0, "noise"),
    "berry":   ((0.72, 0.06, 0.08), (0.45, 0.02, 0.04), 0.25, 0.0, 0.0, "noise"),
    "barka":   ((0.3, 0.23, 0.18), (0.78, 0.86, 0.95), 0.8, 0.0, 0.0, "streak"),
    # the designed baits (roadmap #7)
    "meat":    ((0.55, 0.12, 0.10), (0.86, 0.74, 0.68), 0.5, 0.0, 0.0, "streak"),                   # raw wolf meat, marbled with fat
    "gland":   ((0.55, 0.85, 1.0), (0.88, 0.97, 1.0), 0.12, 0.0, 0.7, "frost", (0.5, 0.85, 1.0)),   # a freeze gland, cold glow
    "entrail": ((0.62, 0.32, 0.42), (0.38, 0.14, 0.24), 0.22, 0.0, 0.0, "rings"),                   # wet guts
    "bloodsac":((0.32, 0.02, 0.03), (0.58, 0.07, 0.08), 0.1, 0.0, 0.0, "noise"),                    # a bloodbag
    "serpent": ((0.10, 0.36, 0.32), (0.55, 0.74, 0.55), 0.3, 0.3, 0.0, "scales_u"),                 # sea-serpent scale
    "eitr":    ((0.55, 0.30, 1.0), (0.80, 0.62, 1.0), 0.2, 0.0, 1.0, "flat", (0.62, 0.42, 1.0)),    # eitr, glowing violet
    "fat":     ((0.86, 0.55, 0.56), (0.74, 0.42, 0.44), 0.5, 0.0, 0.0, "noise"),                      # the pale marbling in meat
    "snow":    ((0.90, 0.94, 0.98), (0.78, 0.86, 0.95), 0.8, 0.0, 0.0, "noise"),                      # clumps of snow
}
G = 7    # 7 x 7 tiles (6 x 6 ran out with the designed baits' materials)
TILE = {name: (i % G, i // G) for i, name in enumerate(MATS)}
def tuv(name, u, v):
    tx, ty = TILE[name]; m = 0.02
    return ((tx + m + (1 - 2 * m) * (u % 1.0)) / G, (ty + m + (1 - 2 * m) * min(max(v, 0), 1)) / G)

bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
def face(vs, uvs, smooth=True):
    try: f = bm.faces.new(vs)
    except ValueError: return
    f.smooth = smooth
    for l, uv in zip(f.loops, uvs): l[uvl].uv = uv

def frame(t):
    t = t.normalized(); a = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
    a = (a - t * a.dot(t)).normalized(); return a, t.cross(a)

def tube(path, radii, mat, seg=12, caps=True, squash=1.0, smooth=True, twist=0.0):
    """A tube along a path (radius per point); squash flattens it across (x/width : z/height)."""
    path = [Vector(p) for p in path]; rings = []
    a = None
    for i, p in enumerate(path):
        t = (path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]).normalized()
        # each ring's frame carried on from the last (parallel transport): picking it afresh per point flipped where the
        # path turned through vertical, pinching hook bends into lumps
        if a is None: a, b = frame(t)
        else: a = (a - t * a.dot(t)).normalized(); b = t.cross(a)
        r = radii[i]; rr = r if not callable(r) else None
        ring = []
        for k in range(seg):
            ang = 2 * math.pi * k / seg + twist * i
            rad = rr if rr is not None else r(k / seg)
            ring.append(bm.verts.new(p + (a * math.cos(ang) * squash + b * math.sin(ang)) * rad))
        rings.append(ring)
    n = len(path) - 1
    for i in range(n):
        for k in range(seg):
            k2 = (k + 1) % seg
            face([rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]],
                 [tuv(mat, k / seg, i / n), tuv(mat, (k + 1) / seg, i / n), tuv(mat, (k + 1) / seg, (i + 1) / n), tuv(mat, k / seg, (i + 1) / n)], smooth)
    if caps:
        for ring, flip in ((rings[0], True), (rings[-1], False)):
            c = bm.verts.new(sum((v.co for v in ring), Vector()) / len(ring))
            for k in range(seg):
                vs = [ring[k], ring[(k + 1) % seg], c]
                face(vs[::-1] if flip else vs, [tuv(mat, 0.5, 0.5)] * 3, smooth)

def blob(c, r, mat, seg=16, rings=10, scale=(1, 1, 1), bump=0.0, seed=0.0, smooth=True):
    c = Vector(c); g = []
    for i in range(rings + 1):
        ph = math.pi * i / rings; row = []
        for k in range(seg):
            th = 2 * math.pi * k / seg
            d = Vector((math.sin(ph) * math.cos(th), math.cos(ph), math.sin(ph) * math.sin(th)))
            rr = r * (1 + bump * noise.noise(d * 2.5 + Vector((seed, seed, seed))))
            row.append(bm.verts.new(c + Vector((d.x * scale[0], d.y * scale[1], d.z * scale[2])) * rr))
        g.append(row)
    for i in range(rings):
        for k in range(seg):
            k2 = (k + 1) % seg
            face([g[i][k], g[i][k2], g[i + 1][k2], g[i + 1][k]], [tuv(mat, k / seg, i / rings), tuv(mat, (k + 1) / seg, i / rings), tuv(mat, (k + 1) / seg, (i + 1) / rings), tuv(mat, k / seg, (i + 1) / rings)], smooth)

def mark():
    """Where the next part starts in the mesh (for turn())."""
    return len(bm.verts)

def turn(n0, pivot, axis, deg):
    """Turns everything built since mark() n0 about an axis ('X', 'Y' or 'Z') through pivot."""
    bm.verts.ensure_lookup_table(); R = Matrix.Rotation(math.radians(deg), 3, axis); pivot = Vector(pivot)
    for v in bm.verts[n0:]: v.co = pivot + R @ (v.co - pivot)

def shift(n0, offset):
    bm.verts.ensure_lookup_table(); off = Vector(offset)
    for v in bm.verts[n0:]: v.co += off

def disc(r, n=18):
    return [(r * math.cos(2 * math.pi * k / n), r * math.sin(2 * math.pi * k / n)) for k in range(n)]

def plate(outline, thick, mat, cup=0.0, smooth=True):
    """A thin plate from a closed 2D outline in XY (z up), cupped by `cup` (z sag at the middle, metres)."""
    if sum(outline[i][0] * outline[(i + 1) % len(outline)][1] - outline[(i + 1) % len(outline)][0] * outline[i][1] for i in range(len(outline))) < 0:
        outline = outline[::-1]                    # counter-clockwise, so the faces point outward
    pts = [Vector((x, y, 0)) for x, y in outline]; c = sum(pts, Vector()) / len(pts)
    rmax = max((p - c).length for p in pts)
    def z(p): return -cup * (1 - ((p - c).length / rmax) ** 2)
    top = [bm.verts.new((p.x, p.y, z(p) + thick / 2)) for p in pts]; bot = [bm.verts.new((p.x, p.y, z(p) - thick / 2)) for p in pts]
    ct = bm.verts.new((c.x, c.y, -cup + thick / 2)); cb = bm.verts.new((c.x, c.y, -cup - thick / 2))
    n = len(pts); xs = [p.x for p in pts]; ys = [p.y for p in pts]
    def uv(p): return tuv(mat, (p.x - min(xs)) / (max(xs) - min(xs) + 1e-9), (p.y - min(ys)) / (max(ys) - min(ys) + 1e-9))
    for k in range(n):
        k2 = (k + 1) % n
        face([top[k], top[k2], ct], [uv(pts[k]), uv(pts[k2]), uv(c)], smooth)
        face([bot[k2], bot[k], cb], [uv(pts[k2]), uv(pts[k]), uv(c)], smooth)
        face([top[k2], top[k], bot[k], bot[k2]], [tuv(mat, 0, 0), tuv(mat, 0.1, 0), tuv(mat, 0.1, 0.1), tuv(mat, 0, 0.1)], False)

def spike(base, tip, r, mat, seg=6):
    tube([base, tip], [r, r * 0.05], mat, seg=seg)

def ring(c, axis, R, r, mat, seg=14, mseg=6):
    c = Vector(c); a, b = frame(Vector(axis)); pts = [c + (a * math.cos(2 * math.pi * k / seg) + b * math.sin(2 * math.pi * k / seg)) * R for k in range(seg + 1)]
    tube(pts, [r] * len(pts), mat, seg=mseg, caps=False)

# ---------------------------------------------------------------- hooks (from photographs of real ones, 2026-11-02)
# Each hook is ONE continuous wire - eye loop, shank, bend and point - drawn from a 2D outline (x toward the point side,
# y down the shank, in hook lengths), smoothed, tapering to a needle tip, its barb pushed out of the point's own surface.
# A treble's three wires are fused into one solid with an exact boolean union.
def _smooth(pts, n=5):
    """Catmull-Rom through the points, n samples a span."""
    P = [Vector(p) for p in pts]; out = []
    for i in range(len(P) - 1):
        p0, p1, p2, p3 = P[max(i - 1, 0)], P[i], P[i + 1], P[min(i + 2, len(P) - 1)]
        for k in range(n):
            t = k / n
            out.append(0.5 * (2 * p1 + (p2 - p0) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (3 * p1 - p0 - 3 * p2 + p3) * t * t * t))
    out.append(P[-1]); return out

def _even(pts, step, passes=4):
    """The points re-spaced evenly along the curve, then eased a little (an uneven outline made the wire wavy)."""
    pts = [Vector(p) for p in pts]; s = [0.0]
    for i in range(1, len(pts)): s.append(s[-1] + (pts[i] - pts[i - 1]).length)
    n = max(2, int(s[-1] / step)); out = []; j = 0
    for k in range(n + 1):
        target = s[-1] * k / n
        while j < len(s) - 2 and s[j + 1] < target: j += 1
        f = (target - s[j]) / max(s[j + 1] - s[j], 1e-12); out.append(pts[j].lerp(pts[j + 1], min(max(f, 0.0), 1.0)))
    for _ in range(passes):
        out = [out[0]] + [out[i - 1] * 0.25 + out[i] * 0.5 + out[i + 1] * 0.25 for i in range(1, len(out) - 1)] + [out[-1]]
    return out

def wire(path, radii, mat, barb=None, seg=8, smooth=True):
    """One wire: a ring at each path point (each frame carried on from the last), joined into a single tube; the start
    capped, the end drawn to a needle point. barb = (ring index, inward, height, sweep): that ring's inner side pushed
    out and swept back toward the bend - a barb in the wire's own surface."""
    path = [Vector(p) for p in path]; n = len(path) - 1; rings = []; a = None
    for i, p in enumerate(path):
        t = (path[min(i + 1, n)] - path[max(i - 1, 0)]).normalized()
        if a is None: a, b = frame(t)
        else: a = (a - t * a.dot(t)).normalized(); b = t.cross(a)
        rg = []
        for k in range(seg):
            dk = a * math.cos(2 * math.pi * k / seg) + b * math.sin(2 * math.pi * k / seg); q = p + dk * radii[i]
            if barb and i == barb[0]:
                inw = Vector(barb[1]); inw = (inw - t * inw.dot(t)).normalized(); w = max(0.0, dk.dot(inw)) ** 2
                q = q + inw * barb[2] * w - t * barb[3] * w
            rg.append(bm.verts.new(q))
        rings.append(rg)
    for i in range(n):
        for k in range(seg):
            k2 = (k + 1) % seg
            face([rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]],
                 [tuv(mat, k / seg, i / n), tuv(mat, k2 / seg, i / n), tuv(mat, k2 / seg, (i + 1) / n), tuv(mat, k / seg, (i + 1) / n)], smooth)
    c0 = bm.verts.new(sum((v.co for v in rings[0]), Vector()) / seg)
    for k in range(seg): face([rings[0][(k + 1) % seg], rings[0][k], c0], [tuv(mat, 0.5, 0.5)] * 3, smooth)
    c1 = bm.verts.new(path[-1] + (path[-1] - path[-2]).normalized() * radii[-1] * 3)
    for k in range(seg): face([rings[-1][k], rings[-1][(k + 1) % seg], c1], [tuv(mat, 0.5, 0.5)] * 3, smooth)

def _hook(ctrl, gap, eye, ax, d, L, r, mat, eye_loop=True, seg=6, smooth=True, xscale=1.0, eye_turned=None):
    """A hook from its 2D outline `ctrl` (with the eye loop in front if wanted); `gap` is a point inside its bend.
    eye_turned = index of an outline point: the eye loop turned a quarter round, out of the hook's plane, and set in line
    with the wire from that point up to the eye (the EWG's eye, in line with the first stretch above its offset)."""
    E, axn = Vector(eye), Vector(ax).normalized(); dn = Vector(d); dn = (dn - axn * dn.dot(axn)).normalized()
    P = lambda x, y: E + dn * (x * xscale * L) + axn * (y * L)
    pts3 = []
    if eye_loop:
        Re = r * 2.6           # the eye loop's radius; it closes onto the top of the shank
        if eye_turned is not None:
            u = (E - P(*ctrl[eye_turned])).normalized(); out = dn.cross(axn).normalized()   # along that stretch; out of the plane
            C = E + u * Re
            pts3 += [C - u * Re * math.cos(ph) + out * Re * math.sin(ph) for ph in np.linspace(math.radians(22), math.radians(345), 16)]
        else:
            pts3 += [P(-Re / L * math.sin(ph) / xscale, -Re / L + Re / L * math.cos(ph)) for ph in np.linspace(math.radians(22), math.radians(345), 16)]
    pts3 += [P(x, y) for x, y in ctrl]
    path = _even(_smooth(pts3, 8), r * 1.9, passes=2)   # (light easing: keeps the EWG's kink; rings ~2 wire widths apart - the triangle count)
    s = [0.0]
    for i in range(1, len(path)): s.append(s[-1] + (path[i] - path[i - 1]).length)
    S = s[-1]; tip = 0.2 * L; s0 = S - tip
    radii = [r if si <= s0 else r * (1 - 0.9 * ((si - s0) / tip) ** 1.3) for si in s]
    bi = min(range(len(path)), key=lambda i: abs(s[i] - (S - tip * 0.55)))
    wire(path, radii, mat, barb=(bi, P(*gap) - path[bi], r * 1.6, r * 3.5), seg=seg, smooth=smooth)

# outlines (x toward the point, y down the shank, in hook lengths), each traced from photos of the real thing
J_HOOK = ([(0, 0.02), (0, 0.3), (0, 0.6), (0.03, 0.75), (0.12, 0.83), (0.24, 0.84), (0.34, 0.78), (0.40, 0.66), (0.41, 0.5), (0.39, 0.34)], (0.2, 0.62))
# circle (traced from a Mustad Demon Perfect circle, in heights): a long straight shank, a wide round body two-thirds as
# wide as the hook is tall, its far side rising to a little above halfway and curling tight so the point aims flat back
# in at the shank
CIRCLE_HOOK = ([(0, 0.02), (0, 0.2), (0, 0.4), (0.005, 0.55), (0.03, 0.70), (0.08, 0.82), (0.16, 0.92), (0.27, 0.98), (0.38, 1.0),
                (0.50, 0.97), (0.61, 0.89), (0.69, 0.78), (0.73, 0.67), (0.72, 0.59), (0.68, 0.52), (0.62, 0.48), (0.55, 0.46), (0.49, 0.43), (0.45, 0.40)],   # the point aimed in and a little up
               (0.38, 0.72))
# EWG (traced from Gamakatsu's own photo of its EWG worm hook, in heights): from the eye the wire angles down TOWARD the
# point side to a sharp corner and back - the offset, a small "<" - then the shank runs nearly straight down into a
# wide round bottom, and the point comes back up leaning in at about 45 degrees to a little past halfway; the hook is
# nine-tenths as wide as it is tall - the extra wide gap
EWG_HOOK = ([(0, 0.02), (0.07, 0.07), (0.09, 0.13), (0.05, 0.20), (0.03, 0.27), (0.04, 0.45), (0.07, 0.62), (0.13, 0.78), (0.24, 0.91),
             (0.40, 0.98), (0.56, 0.99), (0.71, 0.93), (0.83, 0.83), (0.90, 0.73), (0.89, 0.70), (0.83, 0.63), (0.75, 0.57), (0.70, 0.54)],
            (0.45, 0.72))
TREBLE_PRONG = ([(0, 0.0), (0, 0.3), (0, 0.55), (0.02, 0.68), (0.10, 0.76), (0.21, 0.77), (0.30, 0.71), (0.35, 0.6), (0.36, 0.45), (0.34, 0.32)], (0.18, 0.58))

def hook(eye, length, mat, up=1.0, gape=None, r=0.0011, show_eye=True, tilt=0.0, faceted=False):
    """A J hook: the shank back along +Y from the eye, the bend curling up (+Z * up) and the point coming forward again.
    tilt (degrees) turns the whole hook about X at its eye, the shank dipping toward -Z. faceted: knapped stone."""
    n0 = len(bm.verts); eye = Vector(eye)
    _hook(*J_HOOK, eye, (0, 1, 0), (0, 0, up), length, r, mat, eye_loop=show_eye, seg=5 if faceted else 6, smooth=not faceted,
          xscale=(gape / (0.41 * length)) if gape else 1.0)
    if tilt:
        bm.verts.ensure_lookup_table(); R = Matrix.Rotation(math.radians(-tilt), 3, 'X')
        for v in bm.verts[n0:]: v.co = eye + R @ (v.co - eye)

def circle_hook(eye, length, mat, axis=(0, 1, 0), side=(0, 0, 1), r=0.0011, show_eye=True):
    _hook(*CIRCLE_HOOK, eye, axis, side, length, r, mat, eye_loop=show_eye, eye_turned=2)   # its eye turned, in line with the shank

# EWG Texas-rigged on a soft bait (Texas rig photos): the same hook, its point run straight on parallel to the shank so
# it lies along the bait, just under its back
EWG_TEXAS = (EWG_HOOK[0][:14] + [(0.90, 0.64), (0.895, 0.56), (0.89, 0.48), (0.885, 0.42)], EWG_HOOK[1])

def ewg_hook(eye, length, mat, axis=(0, 1, 0), side=(0, 0, 1), r=0.0011, show_eye=True, texas=None):
    """texas = the bait's thickness (m): rigged Texas-style - the eye at its nose, the shank along under its belly, the gap
    as deep as the bait and the point parallel, buried just under its back."""
    if texas:
        _hook(*EWG_TEXAS, eye, axis, side, length, r, mat, eye_loop=show_eye, eye_turned=2, xscale=texas / (0.9 * length))
    else:
        _hook(*EWG_HOOK, eye, axis, side, length, r, mat, eye_loop=show_eye, eye_turned=2)   # its eye turned, in line with the wire down to the offset's corner

def repaint(f0, mat, keep):
    """Faces made since face count f0 whose centre passes `keep` take `mat` (a second paint on one part: a belly)."""
    bm.faces.ensure_lookup_table()
    for f in bm.faces[f0:]:
        if keep(f.calc_center_median()):
            for l in f.loops: l[uvl].uv = tuv(mat, 0.5, 0.5)

def _fused(build):
    """Builds with `build` into a mesh of its own, fuses its overlapping pieces into one solid (exact boolean union with
    itself), then adds the result to the bait."""
    global bm, uvl
    main, main_uv = bm, uvl
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
    try: build()
    finally:
        me_t = bpy.data.meshes.new("vdw_fuse"); bm.to_mesh(me_t); bm.free(); bm, uvl = main, main_uv
    ob_t = bpy.data.objects.new("vdw_fuse", me_t); bpy.context.scene.collection.objects.link(ob_t)
    for o in bpy.data.objects:
        if o is not None and o.name in bpy.context.view_layer.objects: o.select_set(o is ob_t)
    bpy.context.view_layer.objects.active = ob_t
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.intersect_boolean(operation='UNION', use_self=True, solver='EXACT')
    bpy.ops.object.mode_set(mode='OBJECT')
    bm.from_mesh(me_t)
    bpy.data.objects.remove(ob_t); bpy.data.meshes.remove(me_t)

def treble(eye, length, mat, axis=(0, 0, -1), r=0.0009, spin=0.0):
    """A treble hook as lures carry them: three wires laid together as the shank, one of them bent round into the eye,
    each turning out into its own bend spaced a third of the way round - fused into one solid."""
    eye = Vector(eye); ax = Vector(axis).normalized(); a, b = frame(ax)
    def build():
        for k in range(3):
            th = math.radians(spin) + 2 * math.pi * k / 3; dk = a * math.cos(th) + b * math.sin(th)
            _hook(*TREBLE_PRONG, eye + dk * r * 0.95, ax, dk, length, r, mat, eye_loop=(k == 0))
    _fused(build)
def arc(p0, p1, bulge, n=16, wobble=0.0, seed=0.0):
    p0, p1 = Vector(p0), Vector(p1); m = (p0 + p1) / 2; d = p1 - p0; side = Vector((0, 0, 1))
    return [p0 + d * (i / n) + side * bulge * math.sin(math.pi * i / n) + Vector((wobble * noise.noise(Vector((i * 0.4, seed, 0))), 0, 0)) for i in range(n + 1)]

# ---------------------------------------------------------------- the six designs (metres; head at -Y)
L = 0.09
if LURE == "antler":
    # a curved antler tine, flattened into a spoon, tip toward the tail, glowing rune strip along the top
    # (squash scales the tube's height: < 1 flattens it into a spoon)
    path = arc((0, -0.045, 0), (0, 0.04, 0), 0.008, n=20)
    widths = [0.0065 + 0.0055 * math.sin(math.pi * min(1, i / 14)) * (1 - i / 22) for i in range(21)]
    FLAT = 0.42
    tube(path, widths, "bone", seg=16, squash=FLAT)
    rune = [p + Vector((0, 0, widths[i] * FLAT + 0.0003)) for i, p in enumerate(path)]
    tube(rune[3:16], [0.0009] * 13, "glow", seg=6)                                                 # the burned-in rune
    for k in range(3):                                                                             # rune ticks off it
        i = 5 + 4 * k; p = rune[i]
        spike(p, p + Vector((0.0045 * (1 if k % 2 else -1), 0.005, -0.0006)), 0.0008, "glow", seg=4)
    for k in range(14):                                                                            # deer-hair tuft
        a = 2 * math.pi * k / 14
        spike((0, 0.036, 0.001), (0.007 * math.cos(a), 0.062 + 0.006 * math.sin(3 * a), 0.006 * math.sin(a)), 0.0012, "hair", seg=4)
    # the same hook as the others, knapped from flint: its eye and shank set inside the antler, the bend out below the tail
    hook((0, 0.012, 0.0068), 0.034, "flint", up=-1, r=0.0013, show_eye=False, tilt=13, faceted=True)
    ring((0, -0.049, 0), (0, 0, 1), 0.003, 0.0008, "steel")
elif LURE == "root":
    # two jointed sections of twisted root, a greydwarf-eye glow at the head, moss trailing behind
    rad = lambda i, n, r0: (lambda u: r0 * (1 + 0.15 * math.sin(u * 2 * math.pi * 3 + i)))
    tube([(0, -0.045 + 0.04 * i / 10, 0.002 * math.sin(i)) for i in range(11)], [rad(i, 10, 0.009 * (0.75 + 0.25 * math.sin(math.pi * (0.2 + 0.8 * i / 10)))) for i in range(11)], "bark", seg=14, twist=0.25)
    ring((0, -0.003, 0), (0, 1, 0), 0.0065, 0.0012, "steel")
    tube([(0, 0.0, 0) , *[(0.002 * math.sin(i), 0.0 + 0.032 * i / 8, 0) for i in range(1, 9)]], [rad(i, 8, 0.0075 * (1 - 0.45 * i / 8)) for i in range(9)], "bark", seg=14, twist=0.3)
    for s in (-1, 1): blob((s * 0.0062, -0.036, 0.003), 0.0025, "glow", seg=10, rings=6)            # eyes
    for k in range(10):
        a = 2 * math.pi * k / 10
        tube(arc((0, 0.03, 0), (0.005 * math.cos(a), 0.06 + 0.005 * math.sin(2 * a), 0.005 * math.sin(a) - 0.004), 0.004, n=6, wobble=0.002, seed=k),
             [0.0016 * (1 - j / 7) + 0.0003 for j in range(7)], "moss", seg=5)
    hook((0, -0.02, -0.008), 0.03, "steel", up=-1)
    ring((0, -0.048, 0), (0, 0, 1), 0.003, 0.0008, "steel")
elif LURE == "ooze":
    blob((0, -0.02, 0), 0.0105, "bone", scale=(1, 1.1, 0.95))                                      # bone jig head
    blob((0, -0.006, 0.0), 0.0165, "ooze", scale=(1, 1.25, 1.0), bump=0.28, seed=3)                # the ooze around it
    for k, (x, y) in enumerate(((0.006, -0.008), (-0.007, 0.004), (0.002, 0.012))):                 # drips
        tube([(x, y, -0.012), (x, y, -0.022 - 0.004 * k)], [0.0028, 0.0012], "ooze", seg=8)
        blob((x, y, -0.024 - 0.004 * k), 0.0018, "ooze", seg=8, rings=5)
    for k in range(4): blob((0.012 * math.cos(k * 1.7), -0.006 + 0.012 * math.sin(k * 2.3), 0.008), 0.0016, "glow", seg=8, rings=5)  # glowing bubbles
    tube(arc((0, -0.03, 0.006), (0, 0.035, 0.012), 0.01, n=12), [0.0014] * 13, "bone", seg=6)        # bone hook guard
    hook((0, 0.008, 0.0), 0.04, "steel", up=1)
    ring((0, -0.032, 0.004), (1, 0, 0), 0.003, 0.0008, "steel")
elif LURE == "wyrm":
    out = [(0.017 * math.sin(math.pi * t) * (1.0 - 0.35 * t), -0.04 + 0.075 * t) for t in np.linspace(0, 1, 18)]
    out = out + [(-x, y) for x, y in reversed(out[1:-1])]
    plate(out, 0.0016, "silver", cup=0.004)                                                         # the scale, cupped
    tube([(0, -0.036, 0.0005), (0, 0.03, 0.0005)], [0.0013, 0.0004], "silver", seg=6)               # its ridge
    blob((0, -0.008, 0.003), 0.0042, "glow", seg=8, rings=4, scale=(1, 1.6, 0.8))                   # the frozen tear
    for k in (-1, 0, 1):                                                                            # streamers
        tube(arc((k * 0.003, 0.033, 0), (k * 0.008, 0.07, -0.003), 0.003, n=8, wobble=0.0015, seed=k), [0.0026 * (1 - j / 9) + 0.0005 for j in range(9)], "glow", seg=6, squash=0.25)   # flat ribbons
    treble((0, 0.012, -0.0055), 0.026, "steel", axis=(0, 0.5, -0.87))
    ring((0, -0.044, 0), (0, 0, 1), 0.0035, 0.0009, "steel")
elif LURE == "ember":
    tube([(0, -0.048, 0), (0, 0.03, 0)], [0.0007, 0.0007], "steel", seg=6)                           # the wire shaft
    blob((0, 0.0, 0), 0.0085, "core", scale=(1, 1.3, 1), bump=0.12, seed=7)                         # surtling core body
    for y in (-0.014, 0.014): blob((0, y, 0), 0.0028, "blackmetal", seg=10, rings=6)                # beads
    blade = [(0.011 * math.sin(math.pi * t) ** 0.8, -0.04 + 0.032 * t) for t in np.linspace(0, 1, 14)]
    blade = blade + [(-x, y) for x, y in reversed(blade[1:-1])]
    plate([(x * 0.9, y) for x, y in blade], 0.0012, "blackmetal", cup=0.0025)                      # spinner blade
    ring((0, -0.041, 0.002), (1, 0, 0), 0.0025, 0.0006, "steel")                                    # clevis
    for k in range(6):
        a = 2 * math.pi * k / 6
        spike((0, 0.03, 0), (0.006 * math.cos(a), 0.052, 0.006 * math.sin(a)), 0.0014, "red", seg=4) # red tail
    treble((0, 0.03, 0), 0.028, "steel", axis=(0, 1, 0))
    ring((0, -0.05, 0), (0, 0, 1), 0.003, 0.0008, "steel")
elif LURE == "chitin":
    blob((0, -0.022, 0), 0.0115, "chitin", scale=(1.15, 1.35, 0.85))                                # carved head
    for k in range(3): ring((0, -0.03 + k * 0.007, 0), (0, 1, 0), 0.0108 - 0.0015 * abs(k - 1), 0.0008, "chitin")  # plate ridges
    for s in (-1, 1): blob((s * 0.0085, -0.03, 0.004), 0.0025, "glow", seg=10, rings=6)              # eyes
    for k in range(8):                                                                               # tentacle skirt
        a = 2 * math.pi * k / 8
        p0 = Vector((0.0075 * math.cos(a), -0.012, 0.006 * math.sin(a)))
        pts = [p0 + Vector((0.004 * math.cos(a) * j / 9 + 0.003 * math.sin(j * 0.8 + k), 0.06 * j / 9, 0.004 * math.sin(a) * j / 9 + 0.002 * math.cos(j * 0.7 + k))) for j in range(10)]
        tube(pts, [0.0022 * (1 - j / 10) + 0.0004 for j in range(10)], "chitin" if k % 2 else "glow", seg=6)
    hook((0, -0.015, 0.002), 0.045, "steel", up=1)
    ring((0, -0.036, 0.004), (1, 0, 0), 0.003, 0.0008, "steel")

# ---------------------------------------------------------------- the everyday lures and trailers (no glow)
def fish_radii(n, head, belly, tail, peak=0.35):
    """A fish body's radius at n points from nose to tail: rounds up to `belly` at `peak`, tapers to `tail`."""
    out = []
    for i in range(n):
        t = i / (n - 1)
        out.append(head + (belly - head) * math.sin(math.pi / 2 * t / peak) if t < peak else tail + (belly - tail) * math.cos(math.pi / 2 * (t - peak) / (1 - peak)))
    return out

def eye(x, y, z, r):
    blob((x, y, z), r, "white", seg=10, rings=6)
    blob((x + math.copysign(r * 0.5, x), y, z), r * 0.55, "black", seg=8, rings=5)

if LURE == "feather_fly":
    hook((0, -0.018, 0), 0.023, "steel", up=-1, r=0.0006)
    tube([(0, -0.016, 0), (0, -0.004, 0.0004), (0, 0.006, 0)], [0.0016, 0.0023, 0.0015], "thread", seg=10)   # thread body
    for k in range(14):                                                                                       # hackle collar
        a = 2 * math.pi * k / 14
        spike((0, -0.016, 0), (0.0075 * math.cos(a), -0.013, 0.0075 * math.sin(a)), 0.0005, "feather", seg=4)
    for s in (-1, 1):                                                                                         # swept-back wings
        n0 = mark()
        plate([(0.0035 * math.sin(math.pi * t), -0.012 + 0.026 * t) for t in np.linspace(0, 1, 10)] + [(0, 0.014)], 0.0004, "feather")
        turn(n0, (0, -0.012, 0), 'Y', s * 22); shift(n0, (s * 0.0012, 0, 0.0028))
    for s in (-1, 0, 1): spike((0, 0.006, 0), (s * 0.002, 0.017, 0.0012), 0.0005, "feather", seg=4)            # tail
elif LURE == "flint_spinner":
    tube([(0, -0.048, 0), (0, 0.03, 0)], [0.0007, 0.0007], "steel", seg=6)
    ring((0, -0.05, 0), (0, 0, 1), 0.003, 0.0008, "steel")
    ring((0, -0.041, 0.002), (1, 0, 0), 0.0025, 0.0006, "steel")                                              # clevis
    leaf = [(0.011 * math.sin(math.pi * t) ** 0.8, -0.04 + 0.03 * t) for t in np.linspace(0, 1, 12)]
    plate(leaf + [(-x, y) for x, y in reversed(leaf[1:-1])], 0.0016, "flint", cup=0.002, smooth=False)        # knapped flint blade
    blob((0, -0.007, 0), 0.0034, "wood", seg=10, rings=6)
    blob((0, 0.004, 0), 0.0048, "wood", seg=12, rings=8, scale=(1, 1.35, 1))                                   # carved wood body
    blob((0, 0.015, 0), 0.0028, "black", seg=10, rings=6)
    for k in range(8):
        a = 2 * math.pi * k / 8
        spike((0, 0.03, 0), (0.006 * math.cos(a), 0.054, 0.006 * math.sin(a)), 0.0013, "feather", seg=4)
    treble((0, 0.03, 0), 0.026, "steel", axis=(0, 1, 0))
elif LURE == "leather_grub":
    tube([(0, -0.035 + 0.05 * i / 10, 0) for i in range(11)], fish_radii(11, 0.0042, 0.0058, 0.0035, 0.3), "leather", seg=12)
    curl = [(0, 0.015 + 0.012 * (1 - 0.4 * t) * math.sin(t * 1.6 * math.pi), -0.012 * (1 - 0.4 * t) * (1 - math.cos(t * 1.6 * math.pi))) for t in np.linspace(0, 1, 16)]
    tube(curl, [0.0045 * (1 - 0.75 * i / 15) for i in range(16)], "leather", seg=10, squash=0.32)            # curly tail
    ewg_hook((0, -0.036, -0.0035), 0.03, "steel", axis=(0, 1, 0), side=(0, 0, 1), texas=0.0115)   # Texas-rigged: the point through the body, under its back
elif LURE == "bronze_spoon":
    drop = [(0.015 * math.sin(math.pi * t) * (0.45 + 0.55 * t), -0.04 + 0.075 * t) for t in np.linspace(0, 1, 18)]
    plate(drop + [(-x, y) for x, y in reversed(drop[1:-1])], 0.0018, "bronze", cup=0.005)                   # hammered bronze spoon
    ring((0, -0.043, 0), (0, 0, 1), 0.0032, 0.0008, "steel")
    ring((0, 0.037, -0.001), (0, 0, 1), 0.003, 0.0008, "steel")
    treble((0, 0.040, -0.002), 0.026, "steel", axis=(0, 1, 0))
    for k in (-1, 0, 1): spike((0, 0.037, -0.002), (k * 0.003, 0.05, -0.004), 0.0011, "red", seg=4)          # red tag
elif LURE == "finewood_crank":
    f0 = len(bm.faces)
    tube([(0, -0.03 + 0.06 * i / 14, 0) for i in range(15)], fish_radii(15, 0.006, 0.011, 0.0035, 0.3), "crank", seg=16, squash=1.25)
    n0 = mark()
    plate([(0.0065, -0.03)] + [(0.0065 * math.cos(a), -0.038 - 0.009 * math.sin(a)) for a in np.linspace(0, math.pi, 12)] + [(-0.0065, -0.03)], 0.0012, "resin")
    turn(n0, (0, -0.03, 0), 'X', 32)                                                                           # diving lip, angled down
    for s in (-1, 1): eye(s * 0.0085, -0.021, 0.003, 0.0022)
    ring((0, -0.039, -0.004), (1, 0, 0), 0.0022, 0.0006, "steel")                                             # line tie on the lip
    # (its own green-to-yellow paint, the original look - the user kept it over a separate belly)
    for y, z in ((-0.009, -0.0125), (0.021, -0.0072)):                                                         # both trebles hang under it,
        treble((0, y, z), 0.02, "steel", axis=(0, 0.34, -0.94))                                                 # swept back as it's pulled along
elif LURE == "guck_crawler":
    tube([(0, -0.059, 0), (0, -0.053, 0), (0, -0.046, 0)], [0.0007, 0.0034, 0.0042], "iron", seg=12)           # bullet weight
    N = 128                                                                                                    # ribbed crawler: a ridge
    path = [(0.0025 * math.sin(i / 8 * 0.7), -0.045 + 0.095 * i / N, 0.0015 * math.sin(i / 8 * 0.5)) for i in range(N + 1)]   # every 4 rings
    tube(path, [0.0048 * (1 - 0.55 * i / N) * (1 + 0.16 * max(0.0, math.sin(2 * math.pi * i / 4))) for i in range(N + 1)], "guck", seg=12)
    for s in (-1, 1):                                                                                          # little claws
        tube(arc((s * 0.003, -0.036, 0), (s * 0.011, -0.05, 0.002), 0.002, n=5), [0.0018, 0.0016, 0.0014, 0.0012, 0.001, 0.0005], "guck", seg=8, squash=0.45)
    ewg_hook((0, -0.046, -0.003), 0.032, "iron", axis=(0, 1, 0), side=(0, 0, 1), show_eye=False, texas=0.009)                                                   # rigged weedless
elif LURE == "bone_jig":
    blob((0, -0.03, 0), 0.0072, "bone", scale=(0.85, 1.05, 0.95))                                             # carved bone head
    for s in (-1, 1): eye(s * 0.0056, -0.034, 0.002, 0.0019)
    ring((0, -0.031, 0.0078), (1, 0, 0), 0.0024, 0.0007, "iron")                                              # line tie on top
    tube([(0, -0.025, 0), (0, -0.022, 0)], [0.0042, 0.0042], "thread", seg=10, caps=False)                     # collar wrap
    for k in range(16):                                                                                        # feather skirt
        a = 2 * math.pi * k / 16
        spike((0, -0.023, 0), (0.0075 * math.cos(a), 0.016 + 0.004 * math.sin(3 * a), 0.0075 * math.sin(a)), 0.0012, "feather", seg=4)
    hook((0, -0.028, 0), 0.042, "iron", up=1, show_eye=False)
elif LURE == "silver_swimbait":
    tube([(0, -0.045 + 0.085 * i / 16, 0) for i in range(17)], fish_radii(17, 0.004, 0.0115, 0.0028, 0.32), "scales", seg=16, squash=1.35)
    n0 = mark(); plate(disc(0.0085, 16), 0.0016, "scales", cup=0.002); turn(n0, (0, 0, 0), 'X', 90); shift(n0, (0, 0.047, 0))  # paddle tail
    tube([(0, 0.038, 0), (0, 0.046, 0)], [0.0026, 0.0018], "scales", seg=10)                                  # tail stem
    for s in (-1, 1): eye(s * 0.0062, -0.035, 0.004, 0.0021)
    n0 = mark(); plate([(0.0, -0.01), (0.0015, 0.0), (0.0, 0.012), (-0.0015, 0.0)], 0.0008, "scales"); turn(n0, (0, 0, 0), 'Y', 90); shift(n0, (0, -0.005, 0.016))  # dorsal fin
    ring((0, -0.047, 0.001), (0, 0, 1), 0.0026, 0.0007, "steel")
    hook((0, -0.03, 0.006), 0.04, "steel", up=1, show_eye=False)
elif LURE == "linen_popper":
    tube([(0, -0.032 + 0.062 * i / 12, 0) for i in range(13)], [0.0078, 0.0085, 0.0088, 0.0088, 0.0085, 0.008, 0.0074, 0.0066, 0.0058, 0.005, 0.0042, 0.0035, 0.003], "white", seg=16)
    n0 = mark(); plate(disc(0.0076, 18), 0.0012, "red", cup=0.003); turn(n0, (0, 0, 0), 'X', 90); shift(n0, (0, -0.0325, 0))  # cupped face
    ring((0, -0.024, 0), (0, 1, 0), 0.0088, 0.0009, "red")
    for s in (-1, 1): eye(s * 0.0078, -0.026, 0.003, 0.0021)
    ring((0, -0.034, -0.001), (0, 0, 1), 0.0024, 0.0007, "steel")
    for k in range(10):
        a = 2 * math.pi * k / 10
        spike((0, 0.03, 0), (0.007 * math.cos(a), 0.054, 0.007 * math.sin(a)), 0.0012, "linen" if k % 2 else "feather", seg=4)
    treble((0, -0.004, -0.0095), 0.02, "steel", axis=(0, 0, -1))
    treble((0, 0.031, 0), 0.02, "steel", axis=(0, 1, 0))
elif LURE == "curly_tail":
    tube([(0, -0.02 + 0.03 * i / 8, 0) for i in range(9)], fish_radii(9, 0.0035, 0.0045, 0.003, 0.3), "curly", seg=12)
    curl = [(0, 0.01 + 0.01 * (1 - 0.4 * t) * math.sin(t * 1.6 * math.pi), -0.01 * (1 - 0.4 * t) * (1 - math.cos(t * 1.6 * math.pi))) for t in np.linspace(0, 1, 16)]
    tube(curl, [0.0038 * (1 - 0.75 * i / 15) for i in range(16)], "curly", seg=10, squash=0.32)
elif LURE == "boar_rind":
    side = [(0.006 * (0.6 + 0.4 * math.sin(math.pi * min(1, t * 1.6))), -0.03 + 0.05 * t) for t in np.linspace(0, 1, 12)]
    fork = [(0.003, 0.03), (0.0, 0.022), (-0.003, 0.03)]
    plate(side + fork[:1] + [(0.0, 0.022)] + [(-x, y) for x, y in reversed(side)], 0.0028, "rind", cup=0.0015)  # forked strip of rind
    ring((0, -0.026, 0), (0, 0, 1), 0.0012, 0.0005, "rind")
elif LURE == "feather_skirt":
    tube([(0, -0.004, 0), (0, 0.004, 0)], [0.0042, 0.0042], "thread", seg=12)
    for k in range(18):
        a = 2 * math.pi * k / 18
        spike((0, 0.002, 0), (0.0095 * math.cos(a), 0.048 + 0.004 * math.sin(4 * a), 0.0095 * math.sin(a)), 0.0014, "red" if k % 6 == 0 else "feather", seg=4)

# ---------------------------------------------------------------- the Deep North
def crystal(base, tip, r, mat, sides=6):
    """A faceted crystal shard from base to tip (flat-shaded, a short point at each end)."""
    base, tip = Vector(base), Vector(tip); d = tip - base
    tube([base - d * 0.12, base, base + d * 0.75, tip], [r * 0.25, r, r * 0.85, r * 0.08], mat, seg=sides, smooth=False)

if LURE == "crown":
    # Crown Lure (Fimbul Salmon): a faceted frostcore body with glowing cracks, a shard of the Frozen King's crown jewel set
    # in gold prongs on its back, a little gold crown band round the head, and icy streamers trailing behind
    tube([(0, -0.04 + 0.07 * i / 10, 0) for i in range(11)], fish_radii(11, 0.0045, 0.0105, 0.004, 0.32), "frostcore", seg=8, squash=0.85, smooth=False)
    tube([(0, -0.036, 0), (0, -0.031, 0)], [0.0068, 0.0072], "gold", seg=12, caps=False)                       # crown band
    for k in range(6):                                                                                          # its points
        a = math.pi * (0.15 + 0.7 * k / 5)
        spike((0.0072 * math.cos(a) * 0.85, -0.0335, 0.0072 * math.sin(a)), (0.0105 * math.cos(a) * 0.85, -0.035, 0.0105 * math.sin(a)), 0.0012, "gold", seg=4)
    crystal((0, -0.008, 0.007), (0, 0.006, 0.019), 0.0045, "jewel")                                           # the jewel shard
    for k in range(4):                                                                                          # gold prongs round it
        a = math.pi / 4 + math.pi / 2 * k
        tube([(0.0052 * math.cos(a), -0.008 + 0.0052 * math.sin(a), 0.0068), (0.0036 * math.cos(a), -0.006 + 0.0036 * math.sin(a), 0.0128)], [0.0009, 0.0006], "gold", seg=5)
    for k in (-1, 0, 1):                                                                                        # icy streamers
        tube(arc((k * 0.003, 0.028, 0), (k * 0.009, 0.068, -0.004), 0.003, n=8, wobble=0.0015, seed=k + 5), [0.0026 * (1 - j / 9) + 0.0005 for j in range(9)], "jewel" if k == 0 else "ice", seg=6, squash=0.25)
    treble((0, 0.012, -0.007), 0.028, "steel", axis=(0, 0, -1))
    ring((0, -0.043, 0.001), (0, 0, 1), 0.003, 0.0008, "gold")
elif LURE == "ice_spoon":
    # Ice Spoon: a cupped spoon of clear frosted ice in a silver rim, silver split rings, a red-free plain hook
    drop = [(0.014 * math.sin(math.pi * t) * (0.5 + 0.5 * t), -0.04 + 0.075 * t) for t in np.linspace(0, 1, 18)]
    out = drop + [(-x, y) for x, y in reversed(drop[1:-1])]
    plate(out, 0.0026, "ice", cup=0.005, smooth=False)                                                         # the ice
    rim = [Vector((x, y, -0.005 * (1 - ((Vector((x, y)) - Vector((0, -0.0025))).length / 0.04) ** 2) + 0.0012)) for x, y in out] # silver binding round it
    tube(rim + rim[:1], [0.0008] * (len(rim) + 1), "silver", seg=5, caps=False)
    ring((0, -0.043, 0), (0, 0, 1), 0.0032, 0.0008, "silver")
    ring((0, 0.037, -0.001), (0, 0, 1), 0.003, 0.0008, "silver")
    treble((0, 0.040, -0.002), 0.026, "silver", axis=(0, 1, 0))
elif LURE == "frostcore_jig":
    # Frostcore Jig: a frostcore head with glowing cracks on an iron hook, skirted with twigs of a frozen Barka branch
    blob((0, -0.03, 0), 0.0078, "frostcore", seg=10, rings=7, scale=(0.9, 1.1, 0.95), bump=0.18, seed=4)
    for s in (-1, 1): blob((s * 0.0058, -0.035, 0.0025), 0.0016, "jewel", seg=8, rings=5)                    # cold glowing eyes
    ring((0, -0.031, 0.0083), (1, 0, 0), 0.0024, 0.0007, "iron")                                             # line tie on top
    tube([(0, -0.024, 0), (0, -0.021, 0)], [0.0044, 0.0044], "thread", seg=10, caps=False)                    # collar wrap
    for k in range(12):                                                                                       # frozen-branch skirt
        a = 2 * math.pi * k / 12
        tip = Vector((0.008 * math.cos(a), 0.018 + 0.005 * math.sin(3 * a), 0.008 * math.sin(a)))
        tube([(0, -0.022, 0), (tip.x * 0.5, 0.0, tip.z * 0.5), tip], [0.0014, 0.0011, 0.0004], "barka", seg=5)
        if k % 3 == 0: spike((tip.x * 0.5, 0.0, tip.z * 0.5), (tip.x * 0.9, 0.004, tip.z * 0.9 + 0.003), 0.0007, "barka", seg=4)   # side twigs
    hook((0, -0.028, 0), 0.045, "iron", up=1, show_eye=False)
elif LURE == "northern_bait":
    # Northern Bait: a lump of seal blubber studded with crushed lingonberries
    blob((0, 0, 0), 0.012, "blubber", seg=14, rings=10, scale=(0.9, 1.25, 0.7), bump=0.22, seed=9)
    rnd = np.random.default_rng(5)
    for k in range(9):                                                                                        # berries pressed in
        th, ph = rnd.uniform(0, 2 * math.pi), rnd.uniform(0.35, 2.6)
        d = Vector((math.sin(ph) * math.cos(th) * 0.9, math.cos(ph) * 1.25, math.sin(ph) * math.sin(th) * 0.7))
        blob(d * 0.0118, rnd.uniform(0.0022, 0.003), "berry", seg=8, rings=6)

elif LURE == "frost_bait":
    # Frost Bait (Freeze Gland + Wolf Meat), after the user's picture (2026-11-02): a wide, faceted slab of frozen raw meat,
    # deep red marbled with pale fat, clumps of snow on its top and its ledges, and icicles hanging all round its edge
    f0 = len(bm.faces)
    blob((0, 0, 0), 0.0145, "meat", seg=13, rings=9, scale=(1.35, 1.1, 0.6), bump=0.24, seed=13, smooth=False)
    f1 = len(bm.faces)
    repaint(f0, "fat", lambda c: noise.noise(Vector((c.x * 260, c.y * 90, c.z * 260)) + Vector((3.1, 0.7, 1.3))) > 0.34)   # streaks of fat
    rnd = np.random.default_rng(21)
    RX, RY, RZ = 0.0145 * 1.35, 0.0145 * 1.1, 0.0145 * 0.6
    def top(x, y):                                       # the slab's upper surface, roughly
        q = 1 - (x / RX) ** 2 - (y / RY) ** 2
        return RZ * math.sqrt(max(q, 0.0)) * 0.95
    # snow lying on it (not lumps sat on top): for each patch a fine disc of points with a ragged edge, each dropped
    # straight down onto the slab, so the snow follows every facet it settles on - thickest and lumpy in the middle,
    # thinning to nothing at its edge
    from mathutils.bvhtree import BVHTree
    bm.faces.ensure_lookup_table()
    slab = BVHTree.FromPolygons([v.co.copy() for v in bm.verts], [[v.index for v in f.verts] for f in bm.faces[f0:f1]]) if (bm.verts.index_update() or True) else None
    def drop(x, y):
        hit, nrm, _, _ = slab.ray_cast(Vector((x, y, 0.05)), Vector((0, 0, -1)))
        return (hit, nrm if nrm.z > 0 else -nrm) if hit is not None else (None, None)
    NR, NS = 6, 18
    for pi_, (cx, cy, R) in enumerate(((0.002, -0.003, 0.0062), (-0.010, 0.006, 0.0045), (0.011, 0.004, 0.0042), (-0.004, -0.010, 0.0034), (0.008, -0.009, 0.0032), (0.000, 0.010, 0.0032))):
        rows = [[bm.verts.new(Vector((0, 0, 0)))]]
        h, n = drop(cx, cy); rows[0][0].co = (h if h is not None else Vector((cx, cy, top(cx, cy)))) + Vector((0, 0, 0.0017))
        ok = True
        for j in range(1, NR + 1):
            row = []
            for s in range(NS):
                a = 2 * math.pi * s / NS
                edge = R * (1 + 0.32 * noise.noise(Vector((math.cos(a) * 2.2, math.sin(a) * 2.2, pi_ * 3.7))))    # a ragged edge
                rr = edge * j / NR; x, y = cx + rr * math.cos(a), cy + rr * math.sin(a)
                h, n = drop(x, y)
                if h is None: h, n = Vector((x, y, top(x, y))), Vector((0, 0, 1))
                q = j / NR
                thick = 0.00012 + 0.0016 * (1 - q * q) ** 0.8 * (0.75 + 0.5 * noise.noise(Vector((x * 900, y * 900, pi_))))
                row.append(bm.verts.new(h + n * thick))
            rows.append(row)
        for s in range(NS):
            face([rows[0][0], rows[1][s], rows[1][(s + 1) % NS]], [tuv("snow", 0.5, 0.5)] * 3, False)
        for j in range(1, NR):
            for s in range(NS):
                s2 = (s + 1) % NS
                face([rows[j][s], rows[j + 1][s], rows[j + 1][s2], rows[j][s2]], [tuv("snow", 0.5, 0.5)] * 4, False)
    for k in range(30):                                                                                        # a sprinkle of flakes, lying flat
        x, y = rnd.uniform(-RX * 0.8, RX * 0.8), rnd.uniform(-RY * 0.8, RY * 0.8)
        if (x / RX) ** 2 + (y / RY) ** 2 < 0.64 and drop(x, y)[0] is not None: blob(tuple(drop(x, y)[0] + Vector((0, 0, 0.0001))), rnd.uniform(0.0004, 0.0007), "snow", seg=5, rings=3, scale=(1.0, 1.0, 0.35), smooth=False)
    for k in range(11):                                                                                        # icicles round the edge
        a = 2 * math.pi * k / 11 + rnd.uniform(-0.15, 0.15)
        if math.sin(a) > 0.75 and k % 2: continue                                                              # (fewer at the back)
        # its top sunk well into the meat (a little in from the edge, above the underside), the rest hanging below:
        # eight rings, tapering unevenly with small lumps and a slight crook, faceted like the slab
        base = Vector((RX * 0.72 * math.cos(a), RY * 0.72 * math.sin(a), -RZ * 0.1)); ln = rnd.uniform(0.009, 0.018); r0 = rnd.uniform(0.0016, 0.0024)
        lean = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), 0)) * 0.0008
        pts, rad = [], []
        for i in range(8):
            t = i / 7
            pts.append(base + Vector((0, 0, -ln * t)) + lean * math.sin(math.pi * t) + Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), 0)) * 0.00015 * t)
            rad.append(r0 * (1 - t) ** 0.85 * (1 + 0.12 * math.sin(i * 2.3 + k)) + r0 * 0.04)
        rad[-1] = r0 * 0.04
        tube(pts, rad, "ice", seg=8, smooth=False)
        if k % 3 == 0:                                                                                         # a short drip beside it
            b2 = base + Vector((math.cos(a + 1.6), math.sin(a + 1.6), 0)) * r0 * 1.1
            tube([b2, b2 + Vector((0, 0, -ln * 0.45)), b2 + Vector((0, 0, -ln * 0.7))], [r0 * 0.6, r0 * 0.3, r0 * 0.03], "ice", seg=6, smooth=False)
elif LURE == "deep_bait":
    # Abyssal Bait (Entrails + Ooze + Bloodbag): a glossy bloodbag wrapped in a coil of entrails, dripping glowing ooze
    blob((0, 0.003, 0), 0.0105, "bloodsac", seg=14, rings=10, scale=(1.0, 1.25, 0.9), bump=0.12, seed=7)
    path = []
    for i in range(46):                                     # entrails: a loose helix round the sac, wobbling
        t = i / 45; a = t * 2 * math.pi * 2.3
        rr = 0.0118 + 0.0016 * noise.noise(Vector((t * 6, 1.3, 0)))
        path.append((rr * math.cos(a), -0.014 + 0.033 * t, rr * math.sin(a) * 0.95 + 0.0015 * math.sin(t * 17)))
    tube(path, [0.0033 + 0.0006 * math.sin(i * 0.9) for i in range(len(path))], "entrail", seg=8)
    for (x, y, z, r) in [(0.004, -0.006, -0.012, 0.0024), (-0.006, 0.01, -0.011, 0.002), (0.008, 0.012, -0.009, 0.0016), (-0.002, 0.0, 0.012, 0.0019)]:
        blob((x, y, z), r, "ooze", seg=8, rings=6, scale=(1, 1, 1.5 if z < 0 else 0.7))   # drips hang, the top glob sits
elif LURE == "rune_bait":
    # Runed Lure (Silver + Eitr + Serpent Scale): a cupped sea-serpent scale in a silver rim, an eitr rune glowing on its
    # face, a drop of eitr set at the head, silver rings and a silver hook - a legendary lure
    drop = [(0.015 * math.sin(math.pi * t) * (0.55 + 0.45 * t), -0.042 + 0.078 * t) for t in np.linspace(0, 1, 18)]
    out = drop + [(-x, y) for x, y in reversed(drop[1:-1])]
    plate(out, 0.0026, "serpent", cup=0.005, smooth=False)
    def zs(x, y): return -0.005 * (1 - ((Vector((x, y)) - Vector((0, -0.003))).length / 0.042) ** 2) + 0.0018
    rim = [Vector((x, y, zs(x, y) - 0.0006)) for x, y in out]
    tube(rim + rim[:1], [0.0009] * (len(rim) + 1), "silver", seg=5, caps=False)
    for stroke in ([(0, 0.022), (0, -0.018)], [(0, 0.006), (-0.007, -0.006)], [(0, 0.006), (0.007, -0.006)], [(0, -0.008), (-0.005, -0.016)], [(0, -0.008), (0.005, -0.016)]):
        pts = [Vector((stroke[0][0] + (stroke[1][0] - stroke[0][0]) * s, stroke[0][1] + (stroke[1][1] - stroke[0][1]) * s, 0)) for s in np.linspace(0, 1, 6)]
        tube([(q.x, q.y, zs(q.x, q.y) + 0.0004) for q in pts], [0.0009] * 6, "eitr", seg=6)   # the rune, raised a hair
    blob((0, -0.036, 0.0016), 0.0032, "eitr", seg=10, rings=7, scale=(1, 1.2, 0.8))           # the eitr drop
    ring((0, -0.045, 0), (0, 0, 1), 0.0032, 0.0008, "silver")
    ring((0, 0.039, -0.001), (0, 0, 1), 0.003, 0.0008, "silver")
    treble((0, 0.042, -0.002), 0.026, "silver", axis=(0, 1, 0))

# the hook shapes side by side, for a look (not a bait): J, treble, circle, EWG - in a row along Z, each in its own Y-Z plane
if LURE == "hooks_demo":
    hook((0, -0.03, 0), 0.04, "steel", up=1)
    n0 = mark(); treble((0, -0.03, 0), 0.036, "steel", axis=(0, 1, 0)); shift(n0, (0, 0, 0.045))
    n0 = mark(); circle_hook((0, -0.03, 0), 0.04, "steel", axis=(0, 1, 0), side=(0, 0, 1)); shift(n0, (0, 0, 0.09))
    n0 = mark(); ewg_hook((0, -0.03, 0), 0.04, "steel", axis=(0, 1, 0), side=(0, 0, 1)); shift(n0, (0, 0, 0.14))
# clean up for Unity: weld points  that sit on top of each other (the poles of the round parts), drop degenerate faces,
# and hand over triangles - Unity otherwise splits the collapsed quads into zero-area triangles and rejects the normals
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
bmesh.ops.dissolve_degenerate(bm, dist=1e-8, edges=bm.edges)
bmesh.ops.triangulate(bm, faces=bm.faces, quad_method='BEAUTY')
me = bpy.data.meshes.new(NAME); bm.to_mesh(me); bm.free()
ob = bpy.data.objects.new(NAME, me); bpy.context.scene.collection.objects.link(ob)
co = np.array([v.co[:] for v in me.vertices]); print(f"LURE {LURE}: {len(co)} verts, {np.ptp(co, 0).round(3)} m")

# ---------------------------------------------------------------- paint the atlas
S = 1200; T = S // G; rng = np.random.default_rng(11)
def vnoise(sc_):
    g = rng.random((T // sc_ + 2, T // sc_ + 2)); yy, xx = np.mgrid[0:T, 0:T] / sc_
    x0, y0 = xx.astype(int), yy.astype(int); fx, fy = xx - x0, yy - y0; fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    return g[y0, x0] * (1 - fx) * (1 - fy) + g[y0, x0 + 1] * fx * (1 - fy) + g[y0 + 1, x0] * (1 - fx) * fy + g[y0 + 1, x0 + 1] * fx * fy
alb = np.zeros((S, S, 3), np.float32); rough = np.ones((S, S), np.float32); metal = np.zeros((S, S), np.float32)
emi = np.zeros((S, S, 3), np.float32); hgt = np.zeros((S, S), np.float32)
vv, uu = np.mgrid[0:T, 0:T] / T
for name, spec in MATS.items():
    c1, c2, r, m, e, pat = spec[:6]; own = spec[6] if len(spec) > 6 else None
    tx, ty = TILE[name]; ys, xs = slice(ty * T, (ty + 1) * T), slice(tx * T, (tx + 1) * T)
    n1, n2 = vnoise(32), vnoise(8)
    if pat == "streak": k = np.clip(0.5 + 0.5 * np.sin(uu * 70 + n1 * 6) * (0.6 + 0.4 * n2), 0, 1)
    elif pat == "cracks": k = np.clip((np.abs(vnoise(16) - 0.5) < 0.05).astype(float) + (np.abs(vnoise(24) - 0.5) < 0.04), 0, 1)
    elif pat == "plates": k = ((vv * 10) % 1 < 0.08).astype(float) * 0.9 + n2 * 0.1
    elif pat == "frost": k = np.clip((n2 - 0.45) * 3, 0, 1) * 0.5
    elif pat == "barred": k = ((vv * 9 + n1 * 0.6) % 1 < 0.45).astype(float) * 0.8
    elif pat == "rings": k = ((vv * 14) % 1 < 0.25).astype(float) * 0.7 + n2 * 0.2
    elif pat == "gradient_u": k = np.clip(0.5 - 0.5 * np.cos(uu * 2 * np.pi) + (n2 - 0.5) * 0.15, 0, 1) + ((vnoise(12) > 0.72) * (np.cos(uu * 2 * np.pi) > 0.2)) * -0.6
    elif pat == "scales_u": k = np.clip(0.5 + 0.5 * np.cos(uu * 2 * np.pi), 0, 1) * 0.8 + (np.abs(((vv * 30 + (uu * 30).astype(int) % 2 * 0.5) % 1) - 0.5) < 0.08) * 0.15
    elif pat == "noise": k = n1 * 0.6 + n2 * 0.4
    else: k = np.zeros_like(uu)
    col = np.array(c1)[None, None] * (1 - k[..., None]) + np.array(c2)[None, None] * k[..., None]
    col = col * (0.9 + 0.2 * n2[..., None])
    alb[ys, xs] = col; rough[ys, xs] = r + 0.1 * (n2 - 0.5); metal[ys, xs] = m; hgt[ys, xs] = k * 0.5 + n2 * 0.2
    if e > 0: emi[ys, xs] = np.array(own or (GLOW if name != "red" else (1.0, 0.25, 0.08))) * e * (0.7 + 0.3 * n1[..., None])
    if pat == "cracks": emi[ys, xs] = np.array(own or (1.0, 0.45, 0.1)) * k[..., None]              # glowing cracks (surtling core, frostcore)
    if pat == "frost": emi[ys, xs] = np.array(own or GLOW) * max(0.15, e) * k[..., None]
gy, gx = np.gradient(hgt * 3.0); nrm = np.dstack((-gx, -gy, np.ones_like(hgt))); nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
def save(arr, kind, alpha=None):
    a4 = np.ones((S, S, 4), np.float32); a4[..., :3] = np.clip(arr, 0, 1)
    if alpha is not None: a4[..., 3] = alpha
    im = bpy.data.images.new(kind, S, S, alpha=True); im.pixels[:] = a4.ravel(); p = os.path.join(OUT, "Textures", f"{NAME}_Unity_{kind}.png")
    im.filepath_raw = p; im.file_format = 'PNG'; im.save(); print("MAP", os.path.basename(p))
save(alb, "Albedo"); save(np.dstack((metal, metal, metal)), "MetallicSmoothness", alpha=np.clip(1 - rough, 0, 1)); save(nrm * 0.5 + 0.5, "Normal"); save(emi, "Emission")
ob.data.materials.append(bpy.data.materials.new(NAME))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "Blender Files", NAME + ".blend")); print("SAVED")
