# The Pearl of Njord: a big lustrous pearl in a silver bezel with prongs, on a silver plate, mounted on a short loop of
# leather belt. One mesh, one atlas (pearl | silver | leather) with albedo, ORM, normal and a soft pearly emission.
# The clasp faces -Y (forward, +Z in Unity); origin at the back of the plate (where it sits on a belt).
# env: VDW_OUT (folder), VDW_NAME
import bpy, bmesh, math, os
import numpy as np
from mathutils import Vector

OUT = os.environ["VDW_OUT"]; NAME = os.environ["VDW_NAME"]; os.makedirs(OUT, exist_ok=True)
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
TILES = {"pearl": (0.0, 0.0, 0.5, 0.5), "silver": (0.5, 0.0, 1.0, 0.5), "leather": (0.0, 0.5, 1.0, 1.0)}
def tuv(t, u, v): a, b, c, d = TILES[t]; return (a + (c - a) * u, b + (d - b) * v)
bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
SMOOTH = [True]
def face(vs, uvs):
    f = bm.faces.new(vs); f.smooth = SMOOTH[0]
    for l, uv in zip(f.loops, uvs): l[uvl].uv = uv

def sphere(c, r, tile, seg=24, rings=16, squash=(1, 1, 1)):
    c = Vector(c); g = []
    for i in range(rings + 1):
        ph = math.pi * i / rings
        g.append([bm.verts.new(c + Vector((math.sin(ph) * math.cos(2 * math.pi * k / seg) * squash[0], math.cos(ph) * squash[1], math.sin(ph) * math.sin(2 * math.pi * k / seg) * squash[2])) * r) for k in range(seg)])
    for i in range(rings):
        for k in range(seg):
            k2 = (k + 1) % seg
            face([g[i][k], g[i][k2], g[i + 1][k2], g[i + 1][k]], [tuv(tile, k / seg, i / rings), tuv(tile, (k + 1) / seg, i / rings), tuv(tile, (k + 1) / seg, (i + 1) / rings), tuv(tile, k / seg, (i + 1) / rings)])

def tube(path, radii, tile, seg=16, caps=True):
    rings = []
    for i, p in enumerate(path):
        p = Vector(p); t = (Vector(path[min(i + 1, len(path) - 1)]) - Vector(path[max(i - 1, 0)])).normalized()
        a = Vector((1, 0, 0)) if abs(t.x) < 0.9 else Vector((0, 0, 1)); a = (a - t * a.dot(t)).normalized(); b = t.cross(a)
        rings.append([bm.verts.new(p + (a * math.cos(2 * math.pi * k / seg) + b * math.sin(2 * math.pi * k / seg)) * radii[i]) for k in range(seg)])
    for i in range(len(path) - 1):
        for k in range(seg):
            k2 = (k + 1) % seg
            face([rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]], [tuv(tile, k / seg, i / (len(path) - 1)), tuv(tile, (k + 1) / seg, i / (len(path) - 1)), tuv(tile, (k + 1) / seg, (i + 1) / (len(path) - 1)), tuv(tile, k / seg, (i + 1) / (len(path) - 1))])
    if caps:
        for ring, flip in ((rings[0], True), (rings[-1], False)):
            c = bm.verts.new(sum((v.co for v in ring), Vector()) / len(ring))
            for k in range(seg):
                vs = [ring[k], ring[(k + 1) % seg], c]
                face(vs[::-1] if flip else vs, [tuv(tile, .5, .5)] * 3)

def box_strap(path, w, h, tile):
    """A flat strap (rectangular section) along a path in the XZ... plane, width along Z."""
    rings = []
    for i, p in enumerate(path):
        p = Vector(p); t = (Vector(path[min(i + 1, len(path) - 1)]) - Vector(path[max(i - 1, 0)])).normalized()
        up = Vector((0, 0, 1)); n = t.cross(up).normalized()
        rings.append([bm.verts.new(p + n * dx + up * dz) for dx, dz in ((-h / 2, -w / 2), (h / 2, -w / 2), (h / 2, w / 2), (-h / 2, w / 2))])
    for i in range(len(path) - 1):
        for k in range(4):
            k2 = (k + 1) % 4
            face([rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]], [tuv(tile, k / 4, i / (len(path) - 1)), tuv(tile, (k + 1) / 4, i / (len(path) - 1)), tuv(tile, (k + 1) / 4, (i + 1) / (len(path) - 1)), tuv(tile, k / 4, (i + 1) / (len(path) - 1))])
    for ring, flip in ((rings[0], True), (rings[-1], False)):
        face(ring[::-1] if flip else ring, [tuv(tile, 0, 0), tuv(tile, 0.1, 0), tuv(tile, 0.1, 0.1), tuv(tile, 0, 0.1)])

# metres; forward = -Y. The leather strap runs along X behind the plate, curving back like a piece of belt
strap = [(x, 0.012 + 0.6 * x * x, 0.0) for x in np.linspace(-0.11, 0.11, 23)]
SMOOTH[0] = False; box_strap(strap, 0.05, 0.007, "leather"); SMOOTH[0] = True
# silver back plate (a short wide cylinder facing forward), bezel cup, six prongs
tube([(0, 0.006, 0), (0, -0.004, 0)], [0.042, 0.042], "silver", seg=32)
tube([(0, -0.003, 0), (0, -0.016, 0), (0, -0.022, 0)], [0.031, 0.032, 0.027], "silver", seg=32, caps=False)
for k in range(6):
    a = 2 * math.pi * k / 6 + 0.26; d = Vector((math.cos(a), 0, math.sin(a)))
    tube([tuple(d * 0.03 + Vector((0, -0.018, 0))), tuple(d * 0.026 + Vector((0, -0.034, 0))), tuple(d * 0.016 + Vector((0, -0.046, 0)))], [0.0042, 0.0036, 0.0028], "silver", seg=8)
# a twisted silver rope ring round the plate's rim
for k in range(2):
    pts = [(math.cos(t) * (0.042 + 0.002 * math.cos(9 * t + k * math.pi)), -0.001 + 0.002 * math.sin(9 * t + k * math.pi), math.sin(t) * (0.042 + 0.002 * math.cos(9 * t + k * math.pi))) for t in np.linspace(0, 2 * math.pi, 73)]
    tube(pts, [0.0022] * len(pts), "silver", seg=6, caps=False)
# the pearl
sphere((0, -0.034, 0), 0.032, "pearl", seg=40, rings=28, squash=(1, 0.96, 1))

me = bpy.data.meshes.new(NAME); bm.to_mesh(me); bm.free()
ob = bpy.data.objects.new(NAME, me); bpy.context.scene.collection.objects.link(ob)
co = np.array([v.co[:] for v in me.vertices]); print(f"PEARL {len(co)} verts, {np.ptp(co, 0).round(3)} m")

# ---- maps
S = 1024; rng = np.random.default_rng(3)
def noise(scale):
    g = rng.random((S // scale + 2, S // scale + 2)); yy, xx = np.mgrid[0:S, 0:S] / scale
    x0, y0 = xx.astype(int), yy.astype(int); fx, fy = xx - x0, yy - y0; fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    return g[y0, x0] * (1 - fx) * (1 - fy) + g[y0, x0 + 1] * fx * (1 - fy) + g[y0 + 1, x0] * (1 - fx) * fy + g[y0 + 1, x0 + 1] * fx * fy
N1, N2, N3 = noise(64), noise(16), noise(4)
alb = np.zeros((S, S, 3), np.float32); rough = np.zeros((S, S), np.float32); metal = np.zeros((S, S), np.float32); emi = np.zeros((S, S, 3), np.float32); hgt = np.zeros((S, S), np.float32)
def reg(t): a, b, c, d = TILES[t]; return slice(int(b * S), int(d * S)), slice(int(a * S), int(c * S))
ys, xs = reg("pearl"); irid = N1[ys, xs][..., None]                     # lustre: white with a blush of pink and blue
alb[ys, xs] = np.array((0.95, 0.93, 0.9)) * (1 - 0.25 * irid) + np.array((0.98, 0.85, 0.9)) * 0.15 * irid + np.array((0.85, 0.92, 1.0)) * 0.1 * (1 - irid)
rough[ys, xs] = 0.12; metal[ys, xs] = 0.15; emi[ys, xs] = np.array((0.55, 0.65, 0.75)) * (0.6 + 0.4 * irid); hgt[ys, xs] = N3[ys, xs] * 0.05
ys, xs = reg("silver"); alb[ys, xs] = np.array((0.82, 0.83, 0.85)) * (0.85 + 0.2 * N2[ys, xs][..., None]); rough[ys, xs] = 0.22 + 0.15 * N3[ys, xs]; metal[ys, xs] = 1.0; hgt[ys, xs] = N2[ys, xs] * 0.1
ys, xs = reg("leather")
v = np.mgrid[0:ys.stop - ys.start, 0:xs.stop - xs.start][1] / (xs.stop - xs.start)
stitch = (np.abs(((v * 60) % 1) - 0.5) < 0.18) & ((np.abs(np.mgrid[0:ys.stop - ys.start, 0:1][0] / (ys.stop - ys.start) - 0.12) < 0.02) | (np.abs(np.mgrid[0:ys.stop - ys.start, 0:1][0] / (ys.stop - ys.start) - 0.88) < 0.02))
alb[ys, xs] = np.where(stitch[..., None], np.array((0.75, 0.65, 0.5)), np.array((0.28, 0.16, 0.09)) * (0.75 + 0.5 * N2[ys, xs][..., None]))
rough[ys, xs] = 0.7; metal[ys, xs] = 0.0; hgt[ys, xs] = N3[ys, xs] * 0.3 + stitch * 0.4
gy, gx = np.gradient(hgt * 2.0); nrm = np.dstack((-gx, -gy, np.ones_like(hgt))); nrm /= np.linalg.norm(nrm, axis=2, keepdims=True); nrm = nrm * 0.5 + 0.5
def save(arr3, kind, alpha=None):
    a4 = np.ones((S, S, 4), np.float32); a4[..., :3] = np.clip(arr3, 0, 1)
    if alpha is not None: a4[..., 3] = alpha
    im = bpy.data.images.new(kind, S, S, alpha=True); im.pixels[:] = a4.ravel(); p = os.path.join(OUT, f"{NAME}_Unity_{kind}.png")
    im.filepath_raw = p; im.file_format = 'PNG'; im.save(); print("MAP", os.path.basename(p))
save(alb, "Albedo"); save(np.dstack((metal, metal, metal)), "MetallicSmoothness", alpha=1 - rough); save(nrm, "Normal"); save(emi, "Emission")
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "..", "Blender Files", NAME + ".blend"))
print("SAVED")
