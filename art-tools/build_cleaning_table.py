# The Fish Cleaning Table, its three add-ons and the fish dishes, built procedurally like the lures (build_lures.py):
# one mesh each with a small painted atlas (albedo, metal/smoothness, normal, emission). Pieces stand on their base
# (origin at the middle of the base, up +Z, front toward -Y); dishes sit on the ground the same way.
#   piece_cleaning_table   a plank gutting table: a cutting board with a fish and a knife, a bucket of scraps
#   piece_cleaning_ext1    Filleting Knife Rack: two posts and a bar hung with knives, a whetstone on a shelf
#                          (VDW_KNIVES = the Sketchfab kitchen knife set glb: its blades, wooden handles)
#   piece_cleaning_ext2    Brining Barrel: a hooped barrel of brine, its lid leaning on it, a ladle, a salt sack
#   piece_cleaning_ext3    Drying Line: forked posts and a top bar, jute lines hung with split fish
#   food_fishermans_stew, food_fin_soup, food_roe_flatbread, food_ink_noodles, food_ember_fillet, food_rime_salmon,
#   food_grilled_fillet, food_travel_rations   (dishes, after the photos in Mesh/cleaning table/Reference)
#   prep_fillet, prep_roe, prep_dried          (the table's prepared ingredients)
#   bait_stinkbait, buff_lantern_float          (the Bog Witch's brews; float_lantern = the lantern float at bobber size, on the line)
#   piece_feast_<forest|mountain|ocean|plains|mistlands|ashlands|deepnorth>  the fish feasts: board/pot + food_full/half/low stages
# env: VDW_PIECE (one of the above), VDW_OUT (folder), VDW_NAME (defaults to VDW_PIECE)
import bpy, bmesh, math, os
import numpy as np
from mathutils import Vector, Matrix, noise

PIECE = os.environ["VDW_PIECE"]; OUT = os.environ["VDW_OUT"]; NAME = os.environ.get("VDW_NAME", PIECE)
LURE = PIECE
for d in ("Textures", "Models", "Blender Files"): os.makedirs(os.path.join(OUT, d), exist_ok=True)
for o in list(bpy.data.objects): bpy.data.objects.remove(o)

GLOW = (1.0, 0.45, 0.12)    # embers
# name: (colour, colour2 for the pattern, roughness, metallic, emission strength 0..1, pattern[, own glow colour])
MATS = {
    "wood":     ((0.52, 0.38, 0.24), (0.34, 0.23, 0.13), 0.8, 0.0, 0.0, "streak"),
    "darkwood": ((0.30, 0.21, 0.13), (0.17, 0.11, 0.06), 0.75, 0.0, 0.0, "streak"),
    "iron":     ((0.26, 0.26, 0.27), (0.14, 0.13, 0.13), 0.55, 1.0, 0.0, "noise"),
    "steel":    ((0.74, 0.75, 0.76), (0.52, 0.52, 0.54), 0.3, 0.45, 0.0, "noise"),      # half metallic: fully metallic read black with nothing to reflect
    "stone":    ((0.42, 0.41, 0.39), (0.25, 0.25, 0.24), 0.9, 0.0, 0.0, "noise"),
    "flesh":    ((0.88, 0.50, 0.38), (0.96, 0.78, 0.66), 0.45, 0.0, 0.0, "streak"),
    "fishskin": ((0.70, 0.74, 0.76), (0.28, 0.36, 0.40), 0.3, 0.5, 0.0, "scales_u"),
    "rope":     ((0.62, 0.52, 0.34), (0.42, 0.34, 0.20), 0.9, 0.0, 0.0, "streak"),
    "ember":    ((0.30, 0.08, 0.03), (1.0, 0.45, 0.10), 0.7, 0.0, 0.0, "cracks"),
    "coal":     ((0.06, 0.05, 0.05), (0.14, 0.12, 0.11), 0.85, 0.0, 0.0, "noise"),
    "ice":      ((0.80, 0.92, 0.98), (0.55, 0.78, 0.92), 0.1, 0.0, 0.1, "frost", (0.55, 0.85, 1.0)),
    "oil":      ((0.62, 0.40, 0.08), (0.80, 0.56, 0.16), 0.08, 0.0, 0.0, "noise"),
    "stew":     ((0.45, 0.28, 0.14), (0.62, 0.42, 0.22), 0.3, 0.0, 0.0, "noise"),
    "carrot":   ((0.90, 0.45, 0.10), (0.75, 0.32, 0.06), 0.5, 0.0, 0.0, "rings"),
    "broth":    ((0.78, 0.62, 0.30), (0.88, 0.74, 0.40), 0.1, 0.0, 0.0, "noise"),
    "fins":     ((0.82, 0.76, 0.60), (0.50, 0.44, 0.28), 0.5, 0.0, 0.0, "streak"),
    "onion":    ((0.92, 0.88, 0.76), (0.80, 0.70, 0.55), 0.4, 0.0, 0.0, "rings"),
    "bread":    ((0.80, 0.60, 0.34), (0.55, 0.36, 0.16), 0.85, 0.0, 0.0, "noise"),
    "roe":      ((0.95, 0.50, 0.12), (1.0, 0.68, 0.25), 0.1, 0.0, 0.0, "noise"),
    "berry":    ((0.70, 0.07, 0.10), (0.45, 0.03, 0.06), 0.25, 0.0, 0.0, "noise"),
    "ink":      ((0.02, 0.02, 0.03), (0.08, 0.05, 0.12), 0.15, 0.0, 0.2, "noise", (0.55, 0.25, 0.95)),
    "puff":     ((0.86, 0.78, 0.45), (0.68, 0.56, 0.26), 0.6, 0.0, 0.0, "noise"),
    "grilled":  ((0.80, 0.46, 0.30), (0.25, 0.12, 0.06), 0.4, 0.0, 0.0, "barred"),
    "cinder":   ((0.08, 0.06, 0.06), (1.0, 0.42, 0.08), 0.3, 0.0, 0.0, "cracks"),
    "vineberry":((0.36, 0.10, 0.42), (0.20, 0.04, 0.26), 0.2, 0.0, 0.0, "noise"),
    "rimeflesh":((0.92, 0.60, 0.50), (0.96, 0.96, 1.0), 0.3, 0.0, 0.05, "frost", (0.6, 0.85, 1.0)),
    "slate":    ((0.20, 0.22, 0.25), (0.12, 0.13, 0.15), 0.5, 0.0, 0.0, "noise"),
    "leather":  ((0.42, 0.28, 0.16), (0.26, 0.16, 0.08), 0.7, 0.0, 0.0, "noise"),
    # the dishes, after the reference photos (Mesh/cleaning table/Reference)
    "redstew":  ((0.62, 0.20, 0.08), (0.78, 0.34, 0.12), 0.18, 0.0, 0.0, "noise"),       # thick red-orange stew
    "potato":   ((0.88, 0.78, 0.42), (0.74, 0.62, 0.30), 0.6, 0.0, 0.0, "noise"),
    "pepper":   ((0.72, 0.06, 0.06), (0.52, 0.03, 0.04), 0.25, 0.0, 0.0, "noise"),
    "scallion": ((0.30, 0.68, 0.18), (0.18, 0.48, 0.10), 0.4, 0.0, 0.0, "noise"),
    "zucchini": ((0.86, 0.90, 0.66), (0.20, 0.42, 0.14), 0.4, 0.0, 0.0, "rind"),        # pale flesh, dark green rim
    "whitefish":((0.94, 0.92, 0.86), (0.80, 0.76, 0.68), 0.45, 0.0, 0.0, "flake"),      # cooked white fish, flaking in layers
    "skin":     ((0.50, 0.52, 0.54), (0.26, 0.28, 0.30), 0.3, 0.3, 0.0, "noise"),
    "cream":    ((0.96, 0.94, 0.88), (0.88, 0.86, 0.78), 0.35, 0.0, 0.0, "noise"),
    "dill":     ((0.22, 0.44, 0.12), (0.12, 0.30, 0.06), 0.6, 0.0, 0.0, "noise"),
    "pewter":   ((0.70, 0.70, 0.68), (0.55, 0.55, 0.53), 0.35, 0.8, 0.0, "noise"),
    "inkbroth": ((0.30, 0.24, 0.20), (0.40, 0.32, 0.24), 0.08, 0.0, 0.0, "noise"),       # a dark smoky broth, so the black noodles show
    "salmon":   ((0.95, 0.42, 0.22), (1.0, 0.82, 0.70), 0.3, 0.0, 0.0, "lines"),          # salmon with its white fat lines
    "curedsalmon": ((0.85, 0.16, 0.10), (1.0, 0.62, 0.52), 0.2, 0.0, 0.0, "lines"),      # deep red, cured
    "grilledsalmon": ((0.92, 0.48, 0.22), (0.22, 0.10, 0.04), 0.3, 0.0, 0.0, "bars"),   # glazed, with grill bars
    "cloudberry": ((0.98, 0.66, 0.18), (0.88, 0.48, 0.08), 0.3, 0.0, 0.0, "noise"),
    "cloth":    ((0.80, 0.74, 0.60), (0.62, 0.55, 0.42), 0.9, 0.0, 0.0, "barred"),
    "dried":    ((0.62, 0.44, 0.24), (0.40, 0.26, 0.12), 0.7, 0.0, 0.0, "streak"),
    "staves":   ((0.50, 0.36, 0.22), (0.30, 0.20, 0.11), 0.75, 0.0, 0.0, "staves"),
    "brine":    ((0.18, 0.24, 0.22), (0.30, 0.36, 0.30), 0.05, 0.0, 0.0, "noise"),
    "linen":    ((0.86, 0.82, 0.70), (0.70, 0.64, 0.50), 0.9, 0.0, 0.0, "noise"),
    "bark":     ((0.36, 0.25, 0.16), (0.16, 0.11, 0.07), 0.9, 0.0, 0.0, "streak"),      # rough branch bark (the drying rack)
    "driedfish":((0.80, 0.54, 0.22), (0.34, 0.20, 0.09), 0.35, 0.2, 0.0, "scales_u"),   # golden-brown dried fish, dark back
    # the Bog Witch's brews
    "stink":    ((0.26, 0.24, 0.12), (0.12, 0.10, 0.05), 0.3, 0.0, 0.0, "noise"),       # rolled stinkbait, wet and dark
    "pebble":   ((0.62, 0.55, 0.32), (0.40, 0.36, 0.20), 0.7, 0.0, 0.0, "noise"),       # pungent pebbles
    "floatred": ((0.72, 0.10, 0.07), (0.50, 0.06, 0.04), 0.3, 0.0, 0.0, "noise"),
    "floatwhite": ((0.92, 0.90, 0.84), (0.80, 0.78, 0.72), 0.35, 0.0, 0.0, "noise"),
    "candle":   ((1.0, 0.82, 0.40), (1.0, 0.62, 0.20), 0.4, 0.0, 1.0, "flat", (1.0, 0.7, 0.3)),
    "glass":    ((0.78, 0.86, 0.80), (0.62, 0.72, 0.66), 0.05, 0.0, 0.0, "noise"),
    "gold":     ((0.88, 0.68, 0.30), (0.62, 0.44, 0.16), 0.3, 0.8, 0.0, "noise"),       # brass fittings
    "eitr":     ((0.55, 0.30, 1.0), (0.80, 0.62, 1.0), 0.2, 0.0, 1.0, "flat", (0.62, 0.42, 1.0)),
}
G = 8    # 8 x 8 tiles
TILE = {name: (i % G, i // G) for i, name in enumerate(MATS)}
def tuv(name, u, v):
    tx, ty = TILE[name]; m = 0.02
    u = u if 0.0 <= u <= 1.0 else u % 1.0          # the far edge stays at 1 (wrapping it to 0 squeezed the whole tile into one face)
    return ((tx + m + (1 - 2 * m) * u) / G, (ty + m + (1 - 2 * m) * min(max(v, 0), 1)) / G)

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


def crystal(base, tip, r, mat, sides=6):
    """A faceted crystal shard from base to tip (flat-shaded, a short point at each end)."""
    base, tip = Vector(base), Vector(tip); d = tip - base
    tube([base - d * 0.12, base, base + d * 0.75, tip], [r * 0.25, r, r * 0.85, r * 0.08], mat, seg=sides, smooth=False)


# ---------------------------------------------------------------- more shapes for furniture
def box(c, size, mat, rot=0.0, tilt=(0.0, 0.0)):
    """A box centred on c (size x, y, z), turned rot degrees about Z (and tilted about X, Y). Grain runs along its
    longest side; each face maps the whole tile."""
    c = Vector(c); sx, sy, sz = (s / 2 for s in size)
    R = Matrix.Rotation(math.radians(rot), 3, 'Z') @ Matrix.Rotation(math.radians(tilt[1]), 3, 'Y') @ Matrix.Rotation(math.radians(tilt[0]), 3, 'X')
    P = [c + R @ Vector((x, y, z)) for z in (-sz, sz) for y in (-sy, sy) for x in (-sx, sx)]
    v = [bm.verts.new(p) for p in P]
    long_x = size[0] >= size[1]
    quads = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
    for q in quads:
        uvs = [(0, 0), (1, 0), (1, 1), (0, 1)] if long_x else [(0, 0), (0, 1), (1, 1), (1, 0)]
        face([v[i] for i in q], [tuv(mat, a, b) for a, b in uvs], smooth=False)

def surface(z, r, mat, seg=22, c=(0, 0, 0)):
    """A flat disc facing up (liquid, brine) at height z."""
    lathe([(r, z), (0.0, z)], mat, seg, c, cap=False)

def lathe(profile, mat, seg=20, c=(0, 0, 0), cap=True):
    """A round shape about Z through c from a (radius, height) profile, bottom to top. UV u round, v along it."""
    c = Vector(c); rings = []
    for r, z in profile:
        rings.append([bm.verts.new(c + Vector((r * math.cos(2 * math.pi * k / seg), r * math.sin(2 * math.pi * k / seg), z))) for k in range(seg)])
    n = len(profile) - 1
    for i in range(n):
        for k in range(seg):
            k2 = (k + 1) % seg
            face([rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]],
                 [tuv(mat, k / seg, i / n), tuv(mat, (k + 1) / seg, i / n), tuv(mat, (k + 1) / seg, (i + 1) / n), tuv(mat, k / seg, (i + 1) / n)])
    if cap and profile[0][0] > 1e-4:                        # close the bottom
        m = bm.verts.new(c + Vector((0, 0, profile[0][1])))
        for k in range(seg): face([rings[0][(k + 1) % seg], rings[0][k], m], [tuv(mat, 0.5, 0.5)] * 3)

def bowl(c, r, h, mat, inner_mat=None, seg=22):
    """A turned bowl: out and up the outside, over the rim and down inside to a floor."""
    lathe([(r * 0.55, 0), (r * 0.8, h * 0.08), (r * 0.96, h * 0.45), (r, h), (r * 0.9, h * 0.98), (r * 0.84, h * 0.45), (r * 0.5, h * 0.2), (0.0, h * 0.18)], mat, seg, c)

def pole(p0, p1, r, mat, seg=8):
    tube([p0, p1], [r, r * 0.92], mat, seg=seg)

def fish(c, L, mat="fishskin", rot=0.0, flat=0.55):
    """A whole fish lying on its side along X: body, tail fin and a dorsal fin."""
    n0 = mark()
    path = [(L * (t - 0.5), 0, 0) for t in np.linspace(0, 1, 12)]
    radii = [L * 0.11 * math.sin(math.pi * min(1, (t + 0.08) / 0.95)) ** 0.7 + L * 0.008 for t in np.linspace(0, 1, 12)]
    tube(path, radii, mat, seg=12, squash=flat)
    plate([(L * 0.48 + L * 0.16 * abs(s), L * 0.12 * s) for s in np.linspace(-1, 1, 9)] + [(L * 0.47, 0)], L * 0.01, "fins")
    shift(n0, c); turn(n0, c, 'Z', rot)

def roundfish(L, mat, eye_mat="coal", fat=1.0):
    """A whole fish hanging head up from z=0 down to z=-L: a round body, flattened side to side, its tail fin below,
    a dorsal fin on its back and an eye on each side. Built at the origin facing -Y (its side toward the viewer)."""
    n0 = mark()
    path = [(0.0, 0.0, -0.86 * L * t) for t in np.linspace(0, 1, 12)]
    radii = [L * fat * (0.03 + 0.07 * math.sin(math.pi * min(1.0, (t + 0.15) / 0.95)) ** 0.6) * (0.4 if t > 0.92 else 1.0) for t in np.linspace(0, 1, 12)]
    tube(path, radii, mat, seg=10, smooth=False)
    scale_since(n0, (0, 0, 0), (1.0, 0.5, 1.0))
    n1 = mark(); plate([(0.0, 0.0), (0.09 * L, -0.16 * L), (0.02 * L, -0.11 * L), (0.0, -0.13 * L), (-0.02 * L, -0.11 * L), (-0.09 * L, -0.16 * L)], 0.006, "fins", smooth=False)
    turn(n1, (0, 0, 0), 'X', 90); shift(n1, (0, 0, -0.85 * L))                                                # tail fin
    n2 = mark(); plate([(0.0, 0.0), (0.06 * L, 0.03 * L), (0.07 * L, -0.12 * L), (0.0, -0.16 * L)], 0.004, "fins", smooth=False)
    turn(n2, (0, 0, 0), 'X', 90); shift(n2, (0.1 * L, 0, -0.3 * L))                                           # dorsal fin
    for s in (-1, 1): blob((0.0, s * L * 0.045 * fat, -0.07 * L), 0.016 * L, eye_mat, seg=6, rings=4)            # eyes

def scale_since(n0, pivot, s):
    bm.verts.ensure_lookup_table(); pivot = Vector(pivot)
    for v in bm.verts[n0:]: v.co = pivot + Vector(((v.co - pivot).x * s[0], (v.co - pivot).y * s[1], (v.co - pivot).z * s[2]))

# ---------------------------------------------------------------- the pieces and dishes (metres)
if PIECE == "piece_cleaning_table":
    H = 0.86
    for i, y in enumerate((-0.23, 0.0, 0.23)): box((0, y, H), (1.6, 0.21, 0.06), "wood", rot=0.4 * (i - 1))   # plank top
    for x in (-0.7, 0.7):
        for y in (-0.27, 0.27): box((x, y, H / 2 - 0.015), (0.09, 0.09, H - 0.03), "darkwood")               # legs
        box((x, 0, 0.22), (0.07, 0.56, 0.07), "darkwood")                                                     # end rails
    box((0, 0.27, 0.22), (1.4, 0.06, 0.06), "darkwood")                                                       # back stretcher
    box((-0.25, -0.05, H + 0.045), (0.5, 0.32, 0.035), "darkwood", rot=6)                                     # cutting board
    fish((-0.27, -0.05, H + 0.085), 0.42, rot=8)
    box((0.12, -0.12, H + 0.035), (0.16, 0.035, 0.006), "steel", rot=-20)                                     # knife blade
    box((0.23, -0.16, H + 0.04), (0.1, 0.03, 0.022), "leather", rot=-20)                                      # its handle
    for k, (x, y) in enumerate(((0.35, 0.1), (0.45, 0.0), (0.4, -0.06))):                                      # scales and offcuts
        blob((x, y, H + 0.04), 0.022, "flesh", seg=10, rings=6, scale=(1.3, 1, 0.4), bump=0.2, seed=k)
    bowl((0.62, 0.05, H + 0.03), 0.11, 0.07, "darkwood")                                                      # a bowl of scales
    blob((0.62, 0.05, H + 0.08), 0.07, "fishskin", seg=12, rings=6, scale=(1, 1, 0.3), bump=0.25, seed=5)
    lathe([(0.15, 0), (0.17, 0.32), (0.155, 0.32), (0.135, 0.03), (0.0, 0.03)], "darkwood", 18, (0.95, 0.1, 0))   # bucket by the end
    ring((0.95, 0.1, 0.07), (0, 0, 1), 0.153, 0.008, "iron"); ring((0.95, 0.1, 0.26), (0, 0, 1), 0.165, 0.008, "iron")
    blob((0.95, 0.1, 0.27), 0.12, "flesh", seg=12, rings=6, scale=(1, 1, 0.35), bump=0.35, seed=8)            # scraps
    fish((0.95, 0.12, 0.33), 0.22, rot=60)
    tube([(-0.78, -0.27, H - 0.02), (-0.78, -0.27, H - 0.2)], [0.006, 0.006], "rope", seg=5)                  # a hook hanging off the corner
    hook((-0.78, -0.27, H - 0.2), 0.08, "iron", up=-1, r=0.004)
elif PIECE == "piece_cleaning_ext1":
    for x in (-0.45, 0.45): pole((x, 0, 0), (x, 0, 1.3), 0.045, "darkwood")                                 # posts
    box((0, 0, 1.18), (1.05, 0.08, 0.1), "wood")                                                               # rack bar
    box((0, -0.12, 0.62), (0.95, 0.26, 0.04), "wood")                                                          # shelf
    for x in (-0.45, 0.45): box((x, -0.12, 0.55), (0.04, 0.22, 0.1), "darkwood")                              # its brackets
    KN = os.environ.get("VDW_KNIVES")
    if KN:                                                                                                     # the user's knife set: its blades, wooden handles
        bpy.ops.import_scene.gltf(filepath=KN)
        src = [o for o in bpy.data.objects if o.type == 'MESH']
        def dims(o): p = np.array([o.matrix_world @ v.co for v in o.data.vertices]); return p.max(0) - p.min(0), p
        knives = sorted([o for o in src if dims(o)[0][0] < 0.5 * dims(o)[0][2]], key=lambda o: -dims(o)[0][1])[:6]   # flat blades only (not the round steel)
        img = next(n.image for o in knives for m in o.data.materials if m and m.use_nodes for n in m.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image)
        W, Hh = img.size; px = np.array(img.pixels[:], dtype=np.float32).reshape(Hh, W, 4)
        longest = max(dims(o)[0][1] for o in knives); S = 0.42 / longest
        for i, o in enumerate(knives):
            size, pts = dims(o); cen = (pts.max(0) + pts.min(0)) / 2
            kuv = o.data.uv_layers.active.data
            new = lambda q: Vector(((q[2] - cen[2]) * S, (q[0] - cen[0]) * S, (q[1] - cen[1]) * S))   # length up, blade width across, thin toward the viewer
            top = max(new(o.matrix_world @ v.co).z for v in o.data.vertices)
            x = -0.36 + 0.144 * i; z0 = 1.125 - top
            for poly in o.data.polygons:
                uvc = np.mean([kuv[li].uv[:] for li in poly.loop_indices], axis=0)
                r = px[min(Hh - 1, int(uvc[1] % 1 * Hh)), min(W - 1, int(uvc[0] % 1 * W)), :3]
                handle = float(r @ np.array([0.3, 0.59, 0.11])) < 0.2
                vs = []; uvs = []
                for li, vi in zip(poly.loop_indices, poly.vertices):
                    q = new(o.matrix_world @ o.data.vertices[vi].co)
                    vs.append(bm.verts.new((x + q.x, -0.05 + q.y, z0 + q.z)))
                    uvs.append(tuv("darkwood" if handle else "steel", 0.5 + q.x * 6, 0.5 + q.z * 3))
                face(vs, uvs, smooth=True)
        for o in list(bpy.data.objects): bpy.data.objects.remove(o)
    else:
        for k, x in enumerate(np.linspace(-0.33, 0.33, 5)):                                                    # knives
            L = 0.22 + 0.06 * (k % 3)
            box((x, -0.05, 1.12 - 0.07), (0.035, 0.03, 0.12), "leather")
            box((x, -0.05, 1.12 - 0.13 - L / 2), (0.045 - 0.008 * (k % 2), 0.006, L), "steel", tilt=(0, 3 * (k - 2)))
    box((-0.15, -0.14, 0.67), (0.26, 0.07, 0.05), "stone")                                                     # whetstone
    fish((0.2, -0.12, 0.69), 0.3, rot=10)
elif PIECE == "piece_cleaning_ext2":
    # Brining Barrel: a staved barrel with iron hoops, its lid leaning against it, a ladle hooked on the rim, a salt sack
    prof = [(0.27 * (1 + 0.12 * math.sin(math.pi * t)), 0.82 * t) for t in np.linspace(0, 1, 9)]
    lathe(prof + [(0.265, 0.82), (0.25, 0.76)], "staves", 24)                                                   # staves, open top
    surface(0.74, 0.252, "brine", 24)                                                            # brine inside
    for z in (0.1, 0.4, 0.72): ring((0, 0, z), (0, 0, 1), 0.27 * (1 + 0.12 * math.sin(math.pi * z / 0.82)) + 0.004, 0.012, "iron", seg=24)
    n0 = mark(); lathe([(0.0, 0.0), (0.27, 0.0), (0.27, 0.035), (0.0, 0.035)], "darkwood", 20)                  # the lid, leaning
    turn(n0, (0, 0, 0), 'X', 78); shift(n0, (0.05, -0.36, 0.27 * math.sin(math.radians(78)) + 0.005))   # its rim rests on the ground
    box((0.05, -0.395, 0.27), (0.06, 0.035, 0.3), "darkwood", tilt=(-12, 0))                                    # its handle bar
    pole((0.18, 0.1, 0.84), (0.32, 0.16, 1.02), 0.012, "darkwood")                                              # ladle handle
    blob((0.12, 0.07, 0.76), 0.05, "darkwood", seg=10, rings=6, scale=(1, 1, 0.55))                             # ladle bowl in the brine
    blob((-0.42, -0.08, 0.15), 0.17, "linen", seg=12, rings=8, scale=(1, 0.9, 1.15), bump=0.12, seed=4)         # salt sack
    tube([(-0.42, -0.08, 0.32), (-0.42, -0.08, 0.38)], [0.05, 0.035], "linen", seg=10)                          # its tied neck
    ring((-0.42, -0.08, 0.33), (0, 0, 1), 0.05, 0.007, "rope", seg=12)
    for k in range(6): box((-0.30 + 0.025 * k, -0.18, 0.006), (0.03, 0.03, 0.012), "cream", rot=30 * k)        # spilled salt
elif PIECE == "piece_cleaning_ext3":
    # Drying Line (after the reference photos): rough bark poles crossed at each end, a long branch laid in the forks,
    # whole dried fish hung from iron S-hooks by the mouth, a pair tied by the tails, and two split fish pegged on
    rnd = np.random.default_rng(12)
    def branch(p0, p1, r, n=6):
        pts = arc(p0, p1, rnd.uniform(-0.03, 0.03), n=n, wobble=0.015, seed=rnd.uniform(0, 9))
        tube(pts, [r * (1.1 - 0.25 * i / n) for i in range(n + 1)], "bark", seg=7)
    TOP = 1.62
    for x in (-0.85, 0.85):                                                                                    # crossed poles at each end
        branch((x - 0.28, -0.12, 0), (x + 0.1, 0.04, TOP + 0.14), 0.04)
        branch((x + 0.28, 0.12, 0), (x - 0.1, -0.04, TOP + 0.14), 0.04)
        ring((x, 0, TOP), (1, 0, 0), 0.05, 0.008, "rope", seg=10)                                              # lashing
    branch((0.62, -0.05, 0.42), (1.18, 0.05, 0.12), 0.025)                                                    # a brace on one end
    branch((-1.08, 0, TOP + 0.02), (1.08, 0, TOP - 0.01), 0.035, n=10)                                        # the crossbar
    def shook(x, z0, drop):
        """An iron S-hook over the bar, its lower curl ending at z0 - drop."""
        tube([(x, 0, z0 + 0.03), (x + 0.03, 0, z0 + 0.05), (x + 0.04, 0, z0), (x, 0, z0 - 0.05), (x, 0, z0 - drop + 0.03), (x - 0.02, 0, z0 - drop)], [0.004] * 6, "iron", seg=5)
    for k, x in enumerate((-0.6, -0.36, -0.14, 0.12, 0.34, 0.58)):
        L = rnd.uniform(0.48, 0.62); drop = rnd.uniform(0.12, 0.2)
        shook(x, TOP, drop)
        n0 = mark(); roundfish(L, "driedfish" if k % 3 else "fishskin"); turn(n0, (0, 0, 0), 'Z', rnd.uniform(-25, 25)); shift(n0, (x - 0.02, 0, TOP - drop))
    tube([(0.8, 0, TOP), (0.8, 0, TOP - 0.18)], [0.005, 0.005], "rope", seg=4)                                 # a pair tied by the tails, head down
    for s in (-1, 1):
        n0 = mark(); roundfish(0.5, "driedfish"); turn(n0, (0, 0, 0), 'Y', 180); turn(n0, (0, 0, 0), 'Z', 70 * s); shift(n0, (0.8 + 0.025 * s, 0.0, TOP - 0.18 - 0.5 * 1.02))   # tail tied at the rope's end
    for k, x in enumerate((-0.9, -0.95)):                                                                      # split fish pegged on the left
        n0 = mark(); L = 0.3
        half = [(0.06 * math.sin(math.pi * min(1, (t + 0.05) / 0.9)) * (1 - 0.3 * t), -L * t) for t in np.linspace(0, 1, 9)]
        plate(half + [(-a, b) for a, b in reversed(half[1:-1])], 0.01, "driedfish", smooth=False)
        turn(n0, (0, 0, 0), 'X', 90); shift(n0, (x + 0.12 * k + 0.25, 0.02 + 0.02 * k, TOP - 0.03))
# ---------------------------------------------------------------- dishes (after the reference photos)
def scale_since(n0, pivot, s):
    bm.verts.ensure_lookup_table(); pivot = Vector(pivot)
    for v in bm.verts[n0:]: v.co = pivot + Vector(((v.co - pivot).x * s[0], (v.co - pivot).y * s[1], (v.co - pivot).z * s[2]))

def wide_bowl(r=0.125, h=0.075, mat="darkwood", fill=0.8, liquid=None, seg=24):
    """A wide turned bowl with a thick lip, filled to fill x its height with liquid (returns the liquid level)."""
    lathe([(r * 0.55, 0.0), (r * 0.62, h * 0.12), (r * 0.9, h * 0.45), (r, h), (r * 0.9, h * 1.0), (r * 0.86, h * 0.55), (r * 0.6, h * 0.22), (0.0, h * 0.2)], mat, seg)
    lvl = h * fill
    if liquid: surface(lvl, r * (0.86 + 0.04 * fill), liquid, seg)
    return lvl

def chunk(c, size, mat, rot=0.0, sink=0.45, seed=0):
    """A chunky low-poly piece sitting in liquid at height c[2]: sink is how much of it is under."""
    rnd = np.random.default_rng(seed)
    x, y, z = c; sz = size[2]
    box((x, y, z + sz * (0.5 - sink)), size, mat, rot=rot, tilt=(rnd.uniform(-15, 15), rnd.uniform(-15, 15)))

def coin(c, r, t, mat, tilt=(0, 0)):
    n0 = mark(); lathe([(0.0, -t / 2), (r, -t / 2), (r, t / 2), (0.0, t / 2)], mat, 10)
    turn(n0, (0, 0, 0), 'X', tilt[0]); turn(n0, (0, 0, 0), 'Y', tilt[1]); shift(n0, c)

def fillet(c, L, W, T, mat, rot=0.0):
    """A thick fish fillet, tapering to the tail end, flat-shaded; an optional skin underneath."""
    n0 = mark()
    out = [(L * (s - 0.5), W * 0.5 * (1 - 0.45 * s ** 1.5) * (0.85 + 0.15 * math.sin(math.pi * s))) for s in np.linspace(0, 1, 8)]
    plate(out + [(x, -y) for x, y in reversed(out)], T, mat, cup=-T * 0.4, smooth=False)
    turn(n0, (0, 0, 0), 'Z', rot); shift(n0, c)

if PIECE == "food_fishermans_stew":
    lvl = wide_bowl(liquid="redstew", fill=0.84)
    n0 = mark(); fish((0, 0, 0), 0.2, mat="fishskin", flat=0.6); turn(n0, (0, 0, 0), 'Z', -12); shift(n0, (-0.005, 0.0, lvl + 0.004))   # the whole fish, half in
    rnd = np.random.default_rng(2)
    for k in range(7):                                                                                          # potato and carrot chunks
        a = rnd.uniform(0, 2 * math.pi); r = rnd.uniform(0.05, 0.09)
        chunk((r * math.cos(a), r * math.sin(a), lvl), (0.024, 0.02, 0.018), "potato" if k % 2 else "carrot", rot=rnd.uniform(0, 90), seed=k)
    for k in range(6):                                                                                          # pepper strips
        a = rnd.uniform(0, 2 * math.pi); r = rnd.uniform(0.03, 0.09)
        chunk((r * math.cos(a), r * math.sin(a), lvl + 0.006), (0.034, 0.008, 0.006), "pepper", rot=rnd.uniform(0, 180), sink=0.2, seed=10 + k)
    for k in range(12):                                                                                         # scallion on top of the fish
        chunk((rnd.uniform(-0.04, 0.04), rnd.uniform(-0.015, 0.015), lvl + 0.022), (0.006, 0.006, 0.005), "scallion", rot=rnd.uniform(0, 90), sink=0.0, seed=20 + k)
elif PIECE == "food_fin_soup":
    lvl = wide_bowl(mat="darkwood", liquid="broth", fill=0.8)
    fillet((0.0, 0.01, lvl + 0.004), 0.1, 0.06, 0.022, "whitefish", rot=20)                                     # a big fillet, skin up
    box((0.0, 0.01, lvl + 0.017), (0.085, 0.045, 0.004), "skin", rot=20)
    fillet((-0.05, -0.04, lvl + 0.002), 0.07, 0.045, 0.016, "whitefish", rot=-30)
    rnd = np.random.default_rng(5)
    for k in range(5):
        a = rnd.uniform(0, 2 * math.pi); r = rnd.uniform(0.055, 0.09)
        coin((r * math.cos(a), r * math.sin(a), lvl + 0.002), 0.016, 0.007, "carrot" if k % 2 else "zucchini", tilt=(rnd.uniform(-20, 20), rnd.uniform(-20, 20)))
    n0 = mark(); plate([(0.05 * t, 0.045 * math.sin(math.pi * t) * (1 - 0.3 * t)) for t in np.linspace(0, 1, 9)] + [(0.0, 0.0)], 0.003, "fins")
    turn(n0, (0, 0, 0), 'X', 75); shift(n0, (0.05, 0.04, lvl - 0.01))                                           # a fin standing out of it
    for k in range(16):                                                                                         # herbs on the broth
        a = rnd.uniform(0, 2 * math.pi); r = rnd.uniform(0.01, 0.1)
        box((r * math.cos(a), r * math.sin(a), lvl + 0.001), (0.008, 0.004, 0.002), "dill", rot=rnd.uniform(0, 180))
elif PIECE == "food_roe_flatbread":
    n0 = mark(); lathe([(0.0, 0.0), (0.13, 0.0), (0.15, 0.012), (0.135, 0.008), (0.0, 0.006)], "pewter", 28); scale_since(n0, (0, 0, 0), (1.25, 0.8, 1))   # oval pewter plate
    rnd = np.random.default_rng(6)
    for side in (-1, 1):
        cx = side * 0.075
        n0 = mark(); lathe([(0.0, 0.006), (0.058, 0.006), (0.062, 0.02), (0.056, 0.026), (0.0, 0.026)], "bread", 18); scale_since(n0, (0, 0, 0), (0.85, 1.0, 1)); shift(n0, (cx, 0, 0))
        n0 = mark(); lathe([(0.0, 0.026), (0.053, 0.026), (0.05, 0.031), (0.0, 0.032)], "cream", 18); scale_since(n0, (0, 0, 0), (0.85, 1.0, 1)); shift(n0, (cx, 0, 0))
        for k in range(70):                                                                                     # a domed heap of roe
            r, a = 0.046 * math.sqrt(rnd.random()), rnd.uniform(0, 2 * math.pi)
            x, y = r * math.cos(a) * 0.85, r * math.sin(a)
            blob((cx + x, y, 0.034 + 0.012 * (1 - (r / 0.046) ** 2) + rnd.uniform(0, 0.003)), 0.0055, "roe", seg=6, rings=4)
        for k in range(3):                                                                                      # dill sprigs
            a = rnd.uniform(0, 2 * math.pi); p0 = Vector((cx + 0.02 * math.cos(a), 0.02 * math.sin(a), 0.05))
            tube([p0, p0 + Vector((0.025 * math.cos(a + 0.5), 0.025 * math.sin(a + 0.5), 0.004))], [0.0012, 0.0008], "dill", seg=4)
            for j in range(4):
                q = p0 + Vector((0.006 * j * math.cos(a + 0.5), 0.006 * j * math.sin(a + 0.5), 0.001 * j))
                spike(q, q + Vector((0.008 * math.cos(a + 1.6 + j), 0.008 * math.sin(a + 1.6 + j), 0.002)), 0.0007, "dill", seg=3)
    for k, (x, y) in enumerate(((0.0, 0.06), (0.02, -0.065), (-0.015, -0.06))): blob((x, y, 0.016), 0.009, "cloudberry", seg=8, rings=6, bump=0.25, seed=k)
elif PIECE == "food_ink_noodles":
    lvl = wide_bowl(liquid="inkbroth", fill=0.78)
    rnd = np.random.default_rng(3)
    for k in range(14):                                                                                         # coils of black noodles at the surface
        a0 = rnd.uniform(0, 2 * math.pi); r0 = rnd.uniform(0.02, 0.08); pts = []
        for t in np.linspace(0, 1, 12):
            a = a0 + t * rnd.uniform(1.5, 3.0); r = r0 * (1 - 0.3 * t) + 0.012 * math.sin(t * 10 + k)
            pts.append((r * math.cos(a), r * math.sin(a), lvl + 0.002 * math.sin(t * 7 + k)))
        tube(pts, [0.0045] * 12, "ink", seg=5)
    for k, (x, y) in enumerate(((0.02, 0.02), (-0.035, 0.01), (0.01, -0.04), (0.05, -0.01))):                 # white fish pieces
        blob((x, y, lvl + 0.006), 0.018, "whitefish", seg=7, rings=5, scale=(1.2, 1, 0.75), bump=0.2, seed=k)
    for k in range(6):                                                                                          # carrot strips
        a = rnd.uniform(0, 2 * math.pi); r = rnd.uniform(0.03, 0.08)
        chunk((r * math.cos(a), r * math.sin(a), lvl + 0.004), (0.04, 0.005, 0.004), "carrot", rot=rnd.uniform(0, 180), sink=0.1, seed=k)
    for k in range(5): ring((rnd.uniform(-0.06, 0.06), rnd.uniform(-0.06, 0.06), lvl + 0.007), (0, 0, 1), 0.007, 0.0025, "scallion", seg=8, mseg=4)
    for k, (x, y) in enumerate(((0.06, 0.04), (-0.05, -0.05))): blob((x, y, lvl + 0.01), 0.015, "puff", seg=8, rings=6, bump=0.3, seed=k)
elif PIECE == "food_ember_fillet":
    box((0, 0, 0.012), (0.32, 0.2, 0.024), "slate")                                                             # slate board
    for k in range(3): fillet((-0.02 + 0.015 * k, -0.06 + 0.06 * k, 0.04), 0.13, 0.065, 0.03, "grilledsalmon", rot=-15 + 6 * k)
    for k in range(3):                                                                                          # cinder scales, glowing
        n0 = mark(); plate([(0.016 * math.cos(a), 0.016 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 10)], 0.003, "cinder")
        turn(n0, (0, 0, 0), 'X', 15); shift(n0, (0.12, -0.07 + 0.07 * k, 0.03))
    for k, (x, y) in enumerate(((-0.12, 0.07), (-0.13, -0.05), (-0.11, -0.075))): blob((x, y, 0.034), 0.011, "vineberry", seg=8, rings=5)
elif PIECE == "food_rime_salmon":
    box((0, 0, 0.012), (0.32, 0.2, 0.024), "wood")                                                              # a wooden board
    fillet((0.07, 0.03, 0.045), 0.12, 0.08, 0.035, "curedsalmon", rot=10)                                       # the rest of the side
    for k in range(5): crystal((0.03 + 0.02 * k, 0.03 + 0.005 * k, 0.06), (0.03 + 0.02 * k, 0.035, 0.075 + 0.005 * (k % 2)), 0.005, "ice")   # rime on it
    for k in range(7):                                                                                          # thin slices fanned like fallen dominoes
        n0 = mark(); out = [(0.05 * math.cos(a), 0.024 * math.sin(a) * (1 - 0.25 * math.cos(a))) for a in np.linspace(0, 2 * math.pi, 16, endpoint=False)]
        plate(out, 0.004, "curedsalmon", cup=0.004, smooth=False)
        turn(n0, (0, 0, 0), 'Y', 24); turn(n0, (0, 0, 0), 'Z', 8); shift(n0, (-0.13 + 0.028 * k, -0.035, 0.032 + 0.004 * k))   # overlapping, leaning on the next
    for k, (x, y) in enumerate(((0.13, -0.07), (0.12, -0.05), (-0.13, 0.07), (0.0, -0.08))): blob((x, y, 0.03), 0.009, "berry", seg=8, rings=5)
    for k in range(10): box((0.04 + 0.006 * k, 0.02 + (k % 3) * 0.012, 0.064), (0.004, 0.004, 0.003), "coal")     # peppercorns
elif PIECE == "food_grilled_fillet":
    box((0, 0, 0.01), (0.22, 0.12, 0.02), "wood")
    fillet((0, 0, 0.034), 0.15, 0.07, 0.028, "grilledsalmon", rot=5)
elif PIECE == "food_travel_rations":
    box((0, 0, 0.004), (0.26, 0.26, 0.008), "cloth", rot=45)                                                    # a cloth, opened out
    for k in range(3):                                                                                          # dried fish strips
        fillet((-0.03 + 0.03 * k, 0.0, 0.016), 0.16, 0.035, 0.01, "dried", rot=80 + 8 * k)
    for k, (x, y) in enumerate(((0.07, 0.06), (0.08, 0.035), (0.06, 0.08))): blob((x, y, 0.018), 0.01, "cloudberry", seg=8, rings=6, bump=0.25, seed=k)
    lathe([(0.0, 0.008), (0.022, 0.008), (0.026, 0.05), (0.016, 0.06), (0.0, 0.06)], "darkwood", 12, (-0.08, -0.07, 0))   # a little honey pot
    ring((-0.08, -0.07, 0.035), (0, 0, 1), 0.026, 0.003, "rope", seg=12)
elif PIECE.startswith("piece_feast_"):
    # The fish feasts (roadmap #18): a serving board or pot that stays, and the food on it in three stages the mod
    # switches between as the feast is eaten - "food_full", "food_half", "food_low" (separate meshes, same atlas).
    import bmesh as _bmesh
    def make_stage(name, items):
        global bm, uvl
        keep_bm, keep_uvl = bm, uvl
        bm = _bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
        for fn in items:                                                                       # each piece of food 1.45x about its own foot: heaped, readable platters
            n0 = len(bm.verts); fn(); bm.verts.ensure_lookup_table()
            vs = bm.verts[n0:]
            if not vs: continue
            cx = sum(v.co.x for v in vs) / len(vs); cy = sum(v.co.y for v in vs) / len(vs); cz = min(v.co.z for v in vs)
            for v in vs: v.co = Vector((cx + (v.co.x - cx) * 1.45, cy + (v.co.y - cy) * 1.45, cz + (v.co.z - cz) * 1.45))
        _bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
        _bmesh.ops.dissolve_degenerate(bm, dist=1e-8, edges=bm.edges)
        _bmesh.ops.triangulate(bm, faces=bm.faces, quad_method='BEAUTY')
        m2 = bpy.data.meshes.new(name); bm.to_mesh(m2); bm.free()
        o2 = bpy.data.objects.new(name, m2); bpy.context.scene.collection.objects.link(o2)
        print(f"  {name}: {len(m2.polygons)} faces, {len(items)} part(s)")
        bm, uvl = keep_bm, keep_uvl
    def stages(items):
        n = len(items)
        make_stage("food_full", items)
        make_stage("food_half", items[: max(1, round(n * 0.55))])
        make_stage("food_low", items[: max(1, round(n * 0.22))])
    rnd = np.random.default_rng(31)
    def board(w=1.0, d=0.6, mat="wood", h=0.09):
        box((0, 0, h - 0.025), (w, d, 0.05), mat)                                                             # the serving board
        for sx in (-1, 1):
            box((sx * (w / 2 - 0.08), 0, (h - 0.05) / 2), (0.08, d - 0.08, h - 0.05), "darkwood")              # its feet
        return h
    def lying_fish(x, y, z, L, mat, rot):
        def f(): fish((x, y, z), L, mat=mat, rot=rot, flat=0.55)
        return f
    FEAST = PIECE[len("piece_feast_"):]
    if FEAST == "forest":                 # Lakeside Fish Fry: fried lake fish on a board, forest mushrooms, a bowl of oil
        top = board()
        n0 = mark(); bowl((0, 0, 0), 0.09, 0.05, "darkwood"); surface(0.04, 0.078, "oil", 18); shift(n0, (0.36, 0.17, top))
        items = []
        for k in range(8):
            x = -0.36 + 0.1 * k; y = -0.08 + 0.12 * (k % 2)
            items.append(lying_fish(x, y, top + 0.02, 0.24, "driedfish", 80 + rnd.uniform(-15, 15)))
        for k in range(6):
            x, y = rnd.uniform(-0.4, 0.3), rnd.uniform(-0.24, 0.24)
            items.append((lambda x=x, y=y, k=k: (pole((x, y, top), (x, y, top + 0.03), 0.009, "cream"), blob((x, y, top + 0.035), 0.022, "berry" if k % 2 else "dried", seg=10, rings=5, scale=(1, 1, 0.5)))))
        rnd.shuffle(items); stages(items)
    elif FEAST == "mountain":             # Fin and Onion Hotpot: a big iron pot of fin broth on a board, onions round it
        top = board(0.9, 0.6)
        lathe([(0.14, top), (0.24, top + 0.04), (0.26, top + 0.2), (0.245, top + 0.2), (0.235, top + 0.06), (0.0, top + 0.05)], "iron", 22)
        ring((0, 0, top + 0.2), (0, 0, 1), 0.255, 0.012, "iron")
        for s in (-1, 1): ring((s * 0.26, 0, top + 0.17), (1, 0, 0), 0.04, 0.008, "iron")
        surface(top + 0.17, 0.24, "broth", 22); items = []                                                  # the broth stays with the pot
        for k in range(4):
            def fin(k=k):
                n0 = mark(); plate([(0.06 * t, 0.06 * math.sin(math.pi * t) * (1 - 0.3 * t)) for t in np.linspace(0, 1, 9)] + [(0.0, 0.0)], 0.004, "fins")
                turn(n0, (0, 0, 0), 'X', 70); turn(n0, (0, 0, 0), 'Z', 90 * k); shift(n0, (0.08 * math.cos(1.57 * k), 0.08 * math.sin(1.57 * k), top + 0.16))
            items.append(fin)
        for k in range(6):
            a = 0.6 + k * 0.85; x, y = 0.36 * math.cos(a), 0.22 * math.sin(a)
            items.append(lambda x=x, y=y: blob((x, y, top + 0.035), 0.035, "onion", seg=10, rings=7, scale=(1, 1, 0.9)))
        for k in range(3): items.append(lambda k=k: chunk((-0.05 + 0.06 * k, 0.03 * k, top + 0.17), (0.05, 0.03, 0.02), "whitefish", rot=40 * k, seed=k))
        stages(items)
    elif FEAST == "ocean":                # Sea-Fish Spread: whole sea fish on a bed of fresh seaweed, a bowl of roe
        top = board()
        for k in range(14):                                                                                    # the seaweed bed
            x, y = rnd.uniform(-0.42, 0.42), rnd.uniform(-0.22, 0.22)
            n0 = mark(); plate([(0.07 * math.cos(a), 0.02 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 10, endpoint=False)], 0.004, "scallion", smooth=False)
            turn(n0, (0, 0, 0), 'Z', rnd.uniform(0, 180)); shift(n0, (x, y, top + 0.003))
        n0 = mark(); bowl((0, 0, 0), 0.08, 0.05, "darkwood"); shift(n0, (0.36, 0.18, top))
        items = [lambda: [blob((0.36 + rnd.uniform(-0.05, 0.05), 0.18 + rnd.uniform(-0.05, 0.05), top + 0.045), 0.009, "roe", seg=6, rings=4) for _ in range(30)]]
        for k in range(5):
            items.append(lying_fish(-0.32 + 0.15 * k, -0.04 + 0.08 * (k % 2), top + 0.03, 0.32, "fishskin", 75 + rnd.uniform(-10, 10)))
        stages(items)
    elif FEAST == "plains":               # Roe and Barley Platter: loaves, bread heaped with roe, fillets
        top = board()
        items = []
        for k in range(3):
            x = -0.3 + 0.3 * k
            items.append(lambda x=x: blob((x, -0.14, top + 0.05), 0.1, "bread", seg=12, rings=7, scale=(1.3, 0.8, 0.55)))
        for k in range(4):
            x = -0.33 + 0.22 * k
            def roe_bread(x=x):
                lathe([(0.0, top), (0.07, top), (0.075, top + 0.02), (0.0, top + 0.022)], "bread", 14, (x, 0.12, 0))
                for _ in range(22):
                    r, a = 0.055 * math.sqrt(rnd.random()), rnd.uniform(0, 2 * math.pi)
                    blob((x + r * math.cos(a), 0.12 + r * math.sin(a), top + 0.03 + 0.012 * (1 - r / 0.055)), 0.007, "roe", seg=6, rings=4)
            items.append(roe_bread)
        for k in range(3): items.append(lambda k=k: fillet((0.3, -0.12 + 0.06 * k, top + 0.02), 0.16, 0.06, 0.02, "salmon", rot=10 * k))
        rnd.shuffle(items); stages(items)
    elif FEAST == "mistlands":            # Abyssal Ink Banquet: bowls of black noodles, ink-dark fish, jotun puffs
        top = board(mat="darkwood")
        bowls = [(-0.28, 0.1), (0.0, 0.12), (0.28, 0.1)]
        for (bx, by) in bowls:
            n0 = mark(); bowl((0, 0, 0), 0.1, 0.06, "darkwood"); surface(0.045, 0.088, "inkbroth", 18); shift(n0, (bx, by, top))
        items = []
        for (bx, by) in bowls:
            def noodles(bx=bx, by=by):
                for k in range(6):
                    a0 = rnd.uniform(0, 2 * math.pi); pts = []
                    for t in np.linspace(0, 1, 10):
                        a = a0 + t * 2.5; r = 0.06 * (1 - 0.4 * t)
                        pts.append((bx + r * math.cos(a), by + r * math.sin(a), top + 0.047 + 0.012 * t * (1 - t)))
                    tube(pts, [0.004] * 10, "ink", seg=5)
            items.append(noodles)
        for k in range(3): items.append(lying_fish(-0.25 + 0.25 * k, -0.15, top + 0.025, 0.26, "ink", 85))
        for k in range(5): items.append(lambda k=k: blob((-0.4 + 0.2 * k, -0.24 + 0.02 * (k % 2), top + 0.025), 0.025, "puff", seg=8, rings=6, bump=0.3, seed=k))
        stages(items)
    elif FEAST == "ashlands":             # Ember Fish Platter: grilled salmon on a slate slab, glowing cinder scales, vineberries
        top = board(mat="darkwood"); box((0, 0, top + 0.012), (0.9, 0.5, 0.024), "slate"); top += 0.024
        items = []
        for k in range(6): items.append(lambda k=k: fillet((-0.32 + 0.13 * k, -0.05 + 0.1 * (k % 2), top + 0.02), 0.15, 0.07, 0.03, "grilledsalmon", rot=-10 + 4 * k))
        for k in range(6):
            def scale_(k=k):
                n0 = mark(); plate([(0.02 * math.cos(a), 0.02 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 10, endpoint=False)], 0.003, "cinder")
                turn(n0, (0, 0, 0), 'X', 15); shift(n0, (-0.35 + 0.14 * k, 0.18, top + 0.008))
            items.append(scale_)
        for k in range(8): items.append(lambda k=k: blob((-0.38 + 0.1 * k, -0.2, top + 0.012), 0.013, "vineberry", seg=8, rings=5))
        rnd.shuffle(items); stages(items)
    elif FEAST == "deepnorth":            # Rime Fish Smorgasbord: cured salmon slices, dried fish, lingonberries, rime
        top = board()
        items = []
        for r_ in range(2):
            def slices(r_=r_):
                for k in range(6):
                    n0 = mark(); out = [(0.05 * math.cos(a), 0.024 * math.sin(a) * (1 - 0.25 * math.cos(a))) for a in np.linspace(0, 2 * math.pi, 14, endpoint=False)]
                    plate(out, 0.004, "curedsalmon", cup=0.004, smooth=False)
                    turn(n0, (0, 0, 0), 'Y', 24); shift(n0, (-0.38 + 0.028 * k, -0.12 + 0.14 * r_, top + 0.012 + 0.004 * k))
            items.append(slices)
        for k in range(4):
            def dfish(k=k):
                n0 = mark(); roundfish(0.26, "driedfish", fat=0.6); turn(n0, (0, 0, 0), 'Y', 90); turn(n0, (0, 0, 0), 'X', 90)
                shift(n0, (0.28, -0.15 + 0.08 * k, top + 0.015))
            items.append(dfish)
        for k in range(10): items.append(lambda k=k: blob((rnd.uniform(-0.1, 0.12), rnd.uniform(-0.2, 0.2), top + 0.012), 0.012, "berry", seg=8, rings=5))
        for k in range(5): items.append(lambda k=k: crystal((-0.05 + 0.04 * k, 0.2, top), (-0.05 + 0.04 * k, 0.21, top + 0.05 + 0.02 * (k % 2)), 0.012, "ice"))
        rnd.shuffle(items); stages(items)
elif PIECE.startswith("tacklebox_"):
    # Hildir's lost tackle boxes (roadmap #20): a wooden box with brass corners, a handle and her mark, and its dungeon on it
    KIND = PIECE[len("tacklebox_"):]
    L, Wd, H = 0.44, 0.22, 0.18
    box((0, 0, H * 0.4), (L, Wd, H * 0.8), "darkwood")                                                         # the body
    box((0, 0, H * 0.86), (L + 0.01, Wd + 0.01, H * 0.16), "wood", tilt=(-4 if KIND == "swamp" else 0, 0))       # the lid, a little askew on the swamp one
    for sx in (-1, 1):
        for sy in (-1, 1):
            box((sx * (L / 2 - 0.012), sy * (Wd / 2 - 0.012), H * 0.5), (0.03, 0.03, H * 1.0), "gold")           # brass corners
    tube([(-0.07, 0, H * 0.95), (-0.06, 0, H * 1.12), (0.06, 0, H * 1.12), (0.07, 0, H * 0.95)], [0.008] * 4, "leather", seg=6)   # handle
    box((0, -Wd / 2 - 0.004, H * 0.62), (0.05, 0.008, 0.05), "gold")                                           # the clasp
    for k, (x, z) in enumerate(((-0.1, 0.06), (0.1, 0.06))): box((x, -Wd / 2 - 0.003, z), (0.12, 0.004, 0.012), "floatred")   # her painted mark
    rnd = np.random.default_rng(23)
    if KIND == "swamp":
        for k in range(9):
            blob((rnd.uniform(-L / 2, L / 2), rnd.uniform(-Wd / 2, Wd / 2), H * 0.95 + rnd.uniform(0, 0.01)), rnd.uniform(0.025, 0.045), "scallion", seg=8, rings=5, scale=(1, 1, 0.35), bump=0.4, seed=k)   # moss
        for k in range(4): blob((rnd.uniform(-L / 2, L / 2), -Wd / 2 - 0.01, rnd.uniform(0.02, 0.12)), 0.012, "ooze" if "ooze" in TILE else "stink", seg=6, rings=4, scale=(1, 0.5, 1.6))
    elif KIND == "mountain":
        for k in range(8):
            x, y = rnd.uniform(-L / 2, L / 2), rnd.uniform(-Wd / 2, Wd / 2)
            crystal((x, y, H * 0.94), (x + rnd.uniform(-0.02, 0.02), y, H * 0.94 + rnd.uniform(0.03, 0.07)), 0.012, "ice")   # frost on the lid
        for k in range(6): box((rnd.uniform(-L / 2, L / 2), -Wd / 2 - 0.004, rnd.uniform(0.02, 0.14)), (0.05, 0.006, 0.02), "ice")
    else:
        for z in (H * 0.25, H * 0.55):
            box((0, 0, z), (L + 0.012, Wd + 0.012, 0.018), "iron")                                                # dvergr iron bands
        for k in range(3): blob((-0.12 + 0.12 * k, -Wd / 2 - 0.01, H * 0.4), 0.01, "eitr", seg=8, rings=5)       # eitr rivets, glowingelif PIECE == "bait_stinkbait":
    # Stinkbait: a few dark rolled balls of guts and fish oil with pungent pebbles pressed in (about 5 cm; baits show at x2)
    rnd = np.random.default_rng(14)
    for k, (x, y, r) in enumerate(((0.0, 0.0, 0.012), (0.017, 0.008, 0.009), (-0.014, 0.01, 0.0085), (0.006, -0.015, 0.008))):
        blob((x, y, r * 0.8), r, "stink", seg=10, rings=7, scale=(1, 1, 0.8), bump=0.3, seed=k)
        for j in range(4):
            a = rnd.uniform(0, 2 * math.pi); b = rnd.uniform(0.3, 1.2)
            blob((x + r * math.cos(a) * math.sin(b), y + r * math.sin(a) * math.sin(b), r * 0.8 + r * 0.75 * math.cos(b)), r * 0.28, "pebble", seg=6, rings=4, bump=0.3, seed=k * 10 + j)
elif PIECE in ("buff_lantern_float", "float_lantern"):
    # Lantern Float: a red and white float with a little iron cage on top holding a burning candle wick
    lathe([(0.0, 0.0), (0.012, 0.01), (0.024, 0.035), (0.026, 0.05)], "floatwhite", 16)
    lathe([(0.026, 0.05), (0.024, 0.065), (0.012, 0.09), (0.0, 0.1)], "floatred", 16)
    pole((0, 0, -0.03), (0, 0, 0.002), 0.003, "darkwood")                                                     # the stem below
    for k in range(4):                                                                                         # cage bars
        a = k * math.pi / 2 + 0.4
        tube([(0.009 * math.cos(a), 0.009 * math.sin(a), 0.095), (0.012 * math.cos(a), 0.012 * math.sin(a), 0.125), (0.0, 0.0, 0.14)], [0.0012] * 3, "iron", seg=4)
    ring((0, 0, 0.097), (0, 0, 1), 0.01, 0.0015, "iron", seg=10)
    lathe([(0.0, 0.098), (0.005, 0.098), (0.005, 0.112), (0.0, 0.112)], "cream", 8)                            # the candle stub
    blob((0, 0, 0.118), 0.004, "candle", seg=8, rings=5, scale=(1, 1, 1.7))                                   # its flame
    ring((0, 0, 0.142), (1, 0, 0), 0.005, 0.0012, "iron", seg=8)                                               # line loop
    if PIECE == "float_lantern": scale_since(0, (0, 0, 0), (2.6, 2.6, 2.6))                                  # the float on the line, at the bobber's size (45 cm)
elif PIECE == "prep_fillet":
    fillet((0, -0.025, 0.012), 0.2, 0.07, 0.022, "salmon", rot=4)
    fillet((0.01, 0.035, 0.012), 0.18, 0.065, 0.02, "whitefish", rot=-6)
elif PIECE == "prep_roe":
    lathe([(0.04, 0.0), (0.055, 0.02), (0.058, 0.07), (0.05, 0.085), (0.046, 0.085), (0.052, 0.07), (0.05, 0.02), (0.0, 0.012)], "darkwood", 16)   # a small crock
    surface(0.07, 0.05, "brine", 16)
    rnd = np.random.default_rng(9)
    for k in range(40):
        r, a = 0.044 * math.sqrt(rnd.random()), rnd.uniform(0, 2 * math.pi)
        blob((r * math.cos(a), r * math.sin(a), 0.074 + 0.012 * (1 - (r / 0.044) ** 2)), 0.0055, "roe", seg=6, rings=4)
elif PIECE == "prep_dried":
    # a handful of slender dried fish (after the photos), tied at the tails with twine
    for k in range(5):
        n0 = mark(); roundfish(0.22, "driedfish", fat=0.6); turn(n0, (0, 0, 0), 'Y', 90)                                # lay it along X, head toward +X
        turn(n0, (0, 0, 0), 'X', 90); shift(n0, (0.0, 0.0, 0.012 + 0.007 * (k % 2))); turn(n0, (-0.19, 0, 0), 'Z', -16 + 8 * k)   # fanned out from the tied tails
    ring((-0.175, 0.0, 0.016), (1, 0, 0), 0.02, 0.003, "rope", seg=12)


# clean up for Unity: weld points  that sit on top of each other (the poles of the round parts), drop degenerate faces,
# and hand over triangles - Unity otherwise splits the collapsed quads into zero-area triangles and rejects the normals
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
bmesh.ops.dissolve_degenerate(bm, dist=1e-8, edges=bm.edges)
bmesh.ops.triangulate(bm, faces=bm.faces, quad_method='BEAUTY')
me = bpy.data.meshes.new(NAME); bm.to_mesh(me); bm.free()
ob = bpy.data.objects.new(NAME, me); bpy.context.scene.collection.objects.link(ob)

# Pieces: the wood goes into meshes of its own ("vdw_wood", "vdw_darkwood") with UVs in metres, laid along each face's
# longer side, so the mod can dress them in Valheim's own tiling planks; the rest keeps the atlas.
if PIECE.startswith("piece_"):
    REV = {v: k for k, v in TILE.items()}
    def mat_of(f, layer):
        u, v = f.loops[0][layer].uv
        return REV.get((min(G - 1, int(u * G)), min(G - 1, int(v * G))))
    src = bmesh.new(); src.from_mesh(me); suv = src.loops.layers.uv.active
    WOOD_SPLIT = (("vdw_wood", ("wood", "staves")),) if PIECE.startswith("piece_feast_") else (("vdw_wood", ("wood", "staves")), ("vdw_darkwood", ("darkwood",)))   # feasts keep their dark wood in the main mesh
    for gname, mats in WOOD_SPLIT:
        b2 = src.copy(); uv2 = b2.loops.layers.uv.active
        bmesh.ops.delete(b2, geom=[f for f in b2.faces if mat_of(f, uv2) not in mats], context='FACES')
        if not b2.faces: b2.free(); continue
        for f in b2.faces:
            n = f.normal; ax = max(range(3), key=lambda i: abs(n[i])); a_, b_ = [i for i in range(3) if i != ax]
            ea = max(l.vert.co[a_] for l in f.loops) - min(l.vert.co[a_] for l in f.loops)
            eb = max(l.vert.co[b_] for l in f.loops) - min(l.vert.co[b_] for l in f.loops)
            if eb > ea: a_, b_ = b_, a_                      # the grain runs along the face's longer side
            for l in f.loops: l[uv2].uv = (l.vert.co[a_], l.vert.co[b_])
        m2 = bpy.data.meshes.new(gname); b2.to_mesh(m2); b2.free()
        o2 = bpy.data.objects.new(gname, m2); bpy.context.scene.collection.objects.link(o2)
        print(f"  {gname}: {len(m2.polygons)} faces")
    gone = {m for _, ms in WOOD_SPLIT for m in ms}
    bmesh.ops.delete(src, geom=[f for f in src.faces if mat_of(f, suv) in gone], context='FACES')
    src.to_mesh(me); src.free()
co = np.array([v.co[:] for v in me.vertices]); print(f"PIECE {PIECE}: {len(co)} verts, {np.ptp(co, 0).round(3)} m")

def smooth_(e0, e1, x): t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)
# ---------------------------------------------------------------- paint the atlas
S = 1600; T = S // G; rng = np.random.default_rng(11)
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
    elif pat == "flake": k = np.clip(((vv * 7 + 0.15 * n1) % 1 < 0.12).astype(float) * 0.8 + n2 * 0.25, 0, 1)
    elif pat == "lines": k = np.clip((np.abs(((uu * 6 + vv * 2 + 0.2 * n1) % 1) - 0.5) < 0.05).astype(float) * 0.9 + n2 * 0.1, 0, 1)
    elif pat == "bars": k = np.clip(((uu * 4 + 0.08 * n1) % 1 < 0.34).astype(float) + (n2 - 0.5) * 0.3, 0, 1)
    elif pat == "rind": k = np.clip(smooth_(0.36, 0.46, np.hypot(uu - 0.5, vv - 0.5)) + 0.15 * (n2 - 0.5), 0, 1)
    elif pat == "staves": k = np.clip(((uu * 14) % 1 < 0.07).astype(float) * 0.9 + 0.5 + 0.5 * np.sin(vv * 40 + n1 * 5) * 0.4, 0, 1)
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
