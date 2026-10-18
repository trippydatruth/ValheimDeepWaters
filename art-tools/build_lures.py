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
    # the Deep North (a 7th value is the material's own glow colour)
    "ice":     ((0.75, 0.9, 0.98), (0.5, 0.75, 0.92), 0.08, 0.0, 0.12, "frost", (0.55, 0.85, 1.0)),
    "frostcore": ((0.06, 0.14, 0.3), (0.4, 0.8, 1.0), 0.35, 0.0, 0.0, "cracks", (0.45, 0.85, 1.0)),
    "gold":    ((0.95, 0.75, 0.3), (0.7, 0.5, 0.15), 0.2, 1.0, 0.0, "noise"),
    "jewel":   ((0.6, 0.88, 1.0), (0.3, 0.6, 0.95), 0.05, 0.0, 0.8, "flat", (0.55, 0.85, 1.0)),
    "blubber": ((0.86, 0.78, 0.72), (0.7, 0.58, 0.52), 0.35, 0.0, 0.0, "noise"),
    "berry":   ((0.72, 0.06, 0.08), (0.45, 0.02, 0.04), 0.25, 0.0, 0.0, "noise"),
    "barka":   ((0.3, 0.23, 0.18), (0.78, 0.86, 0.95), 0.8, 0.0, 0.0, "streak"),
}
G = 6
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
    for i, p in enumerate(path):
        t = path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]
        a, b = frame(t)
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

def blob(c, r, mat, seg=16, rings=10, scale=(1, 1, 1), bump=0.0, seed=0.0):
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
            face([g[i][k], g[i][k2], g[i + 1][k2], g[i + 1][k]], [tuv(mat, k / seg, i / rings), tuv(mat, (k + 1) / seg, i / rings), tuv(mat, (k + 1) / seg, (i + 1) / rings), tuv(mat, k / seg, (i + 1) / rings)])

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

def hook(eye, length, mat, up=1.0, gape=None, r=0.0011, show_eye=True, tilt=0.0, faceted=False):
    """A J hook: shank back along +Y from the eye, the bend curling up (+Z * up) and the point forward, with a barb. tilt (degrees) turns
    the whole hook about X at its eye, the shank dipping toward -Z."""
    n0 = len(bm.verts)
    eye = Vector(eye); gape = gape or length * 0.42; pts = []
    for i in range(7): pts.append(eye + Vector((0, length * 0.75 * i / 6, 0)))
    bc = eye + Vector((0, length * 0.75, up * gape / 2))
    for i in range(1, 9):
        a = -math.pi / 2 + math.pi * i / 8
        pts.append(bc + Vector((0, math.cos(a) * gape / 2, up * math.sin(a) * gape / 2)))
    tipb = pts[-1]; pts.append(tipb + Vector((0, -length * 0.28, up * 0.002)))
    tube(pts, [r] * len(pts), mat, seg=5 if faceted else 6, smooth=not faceted)   # faceted: knapped stone
    spike(pts[-1] + Vector((0, length * 0.04, 0)), pts[-1] + Vector((0, length * 0.12, -up * 0.004)), r * 1.2, mat, seg=4)  # barb
    if show_eye: ring(eye - Vector((0, 0.003, 0)), (0, 0, 1), 0.0028, 0.0007, mat)                                # eye
    if tilt:
        bm.verts.ensure_lookup_table(); R = Matrix.Rotation(math.radians(-tilt), 3, 'X')
        for v in bm.verts[n0:]: v.co = eye + R @ (v.co - eye)

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
    hook((0, 0.025, -0.004), 0.03, "steel", up=-1)
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
    hook((0, 0.03, 0), 0.03, "steel", up=1)
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
    hook((0, 0.03, 0), 0.028, "steel", up=1)
elif LURE == "leather_grub":
    tube([(0, -0.035 + 0.05 * i / 10, 0) for i in range(11)], fish_radii(11, 0.0042, 0.0058, 0.0035, 0.3), "leather", seg=12)
    curl = [(0, 0.015 + 0.012 * (1 - 0.4 * t) * math.sin(t * 1.6 * math.pi), -0.012 * (1 - 0.4 * t) * (1 - math.cos(t * 1.6 * math.pi))) for t in np.linspace(0, 1, 16)]
    tube(curl, [0.0045 * (1 - 0.75 * i / 15) for i in range(16)], "leather", seg=10, squash=0.32)            # curly tail
    hook((0, -0.033, 0), 0.03, "steel", up=1)
elif LURE == "bronze_spoon":
    drop = [(0.015 * math.sin(math.pi * t) * (0.45 + 0.55 * t), -0.04 + 0.075 * t) for t in np.linspace(0, 1, 18)]
    plate(drop + [(-x, y) for x, y in reversed(drop[1:-1])], 0.0018, "bronze", cup=0.005)                   # hammered bronze spoon
    ring((0, -0.043, 0), (0, 0, 1), 0.0032, 0.0008, "steel")
    ring((0, 0.037, -0.001), (0, 0, 1), 0.003, 0.0008, "steel")
    hook((0, 0.039, -0.002), 0.028, "steel", up=-1)
    for k in (-1, 0, 1): spike((0, 0.037, -0.002), (k * 0.003, 0.05, -0.004), 0.0011, "red", seg=4)          # red tag
elif LURE == "finewood_crank":
    tube([(0, -0.03 + 0.06 * i / 14, 0) for i in range(15)], fish_radii(15, 0.006, 0.011, 0.0035, 0.3), "crank", seg=16, squash=1.25)
    n0 = mark()
    plate([(0.0065, -0.03)] + [(0.0065 * math.cos(a), -0.038 - 0.009 * math.sin(a)) for a in np.linspace(0, math.pi, 12)] + [(-0.0065, -0.03)], 0.0012, "resin")
    turn(n0, (0, -0.03, 0), 'X', 32)                                                                           # diving lip, angled down
    for s in (-1, 1): eye(s * 0.0085, -0.021, 0.003, 0.0022)
    ring((0, -0.039, -0.004), (1, 0, 0), 0.0022, 0.0006, "steel")                                             # line tie on the lip
    hook((0, -0.008, -0.012), 0.022, "steel", up=-1)
    hook((0, 0.03, 0), 0.022, "steel", up=-1)
elif LURE == "guck_crawler":
    tube([(0, -0.059, 0), (0, -0.053, 0), (0, -0.046, 0)], [0.0007, 0.0034, 0.0042], "iron", seg=12)           # bullet weight
    path = [(0.0025 * math.sin(i * 0.7), -0.045 + 0.095 * i / 16, 0.0015 * math.sin(i * 0.5)) for i in range(17)]
    tube(path, [0.0048 * (1 - 0.55 * i / 16) for i in range(17)], "guck", seg=12)                              # ribbed crawler
    for s in (-1, 1):                                                                                          # little claws
        tube(arc((s * 0.003, -0.036, 0), (s * 0.011, -0.05, 0.002), 0.002, n=5), [0.0018, 0.0016, 0.0014, 0.0012, 0.001, 0.0005], "guck", seg=8, squash=0.45)
    hook((0, -0.043, 0), 0.03, "iron", up=1, show_eye=False)                                                   # rigged weedless
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
    hook((0, -0.006, -0.0095), 0.022, "steel", up=-1)
    hook((0, 0.03, 0), 0.022, "steel", up=-1)
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
    hook((0, 0.012, -0.007), 0.032, "steel", up=-1)
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
    hook((0, 0.039, -0.002), 0.028, "silver", up=-1)
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

# clean up for Unity: weld points that sit on top of each other (the poles of the round parts), drop degenerate faces,
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
