# Builds the fish materials (what cleaning a catch gives, FishMaterials.cs), each a small static model with its own
# painted Unity maps (Albedo, MetallicSmoothness, Normal from a height map, Emission):
#   mat_scales  Fish Scales      - a little heap of round silvery scales, growth rings, a blue-green sheen
#   mat_oil     Fish Oil         - a stoppered clay flask, amber oil run down from the neck
#   mat_fins    Spiny Fins       - a spiny dorsal fin, pale rays through an olive-brown membrane
#   mat_roe     Fish Roe         - a cluster of orange eggs, glossy, each with its dark eye
#   mat_ink     Abyssal Ink      - a glossy black ink sac, faint violet veins glowing
#   mat_cinder  Cinder Scales    - charred scales cracked with glowing embers
#   mat_rime    Rime Scales      - frost-white scales going to ice blue, frost at the edges, a cold rim glow
#   mat_legend  Legendary Scale  - one broad scale, gold to bronze rings, a warm glow at the rim
#   mat_trophy  Trophy Fin       - a swept tail fin, crimson membrane between gold-tipped rays, tied with twine
# Writes <out>/Models/<key>.fbx, <out>/Textures/<key>/<key>_Unity_*.png, <out>/Blender Files/fishmats.blend.
# Existing maps / models are kept (never overwritten) unless VDW_REDO=1.
#   env: VDW_OUT (folder), VDW_ONLY (comma list of keys, optional), VDW_REDO
import bpy, bmesh, math, os
import numpy as np
from mathutils import Matrix, Vector

OUT = os.environ["VDW_OUT"]; N = 512
ONLY = set(filter(None, os.environ.get("VDW_ONLY", "").split(",")))
REDO = os.environ.get("VDW_REDO") == "1"
for d in ("Models", "Textures", "Blender Files", "Previews"): os.makedirs(os.path.join(OUT, d), exist_ok=True)
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
sc = bpy.context.scene
rng = np.random.default_rng(11)

# ---------------------------------------------------------------- texture helpers (arrays [v, u], v = 0 at the bottom)
V, U = np.mgrid[0:N, 0:N] / (N - 1)
def vnoise(scale):
    """Value noise, tileable (cells wrap round)."""
    c = max(1, N // scale); g = rng.random((c, c)); y, x = np.mgrid[0:N, 0:N] * (c / N)
    x0, y0 = x.astype(int), y.astype(int); fx, fy = x - x0, y - y0; fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a, b_, c_, d = g[y0 % c, x0 % c], g[y0 % c, (x0 + 1) % c], g[(y0 + 1) % c, x0 % c], g[(y0 + 1) % c, (x0 + 1) % c]
    return a * (1 - fx) * (1 - fy) + b_ * fx * (1 - fy) + c_ * (1 - fx) * fy + d * fx * fy
def fbm(*scales): return sum(vnoise(s) * w for s, w in zip(scales, (0.5, 0.3, 0.2, 0.1)))
def mix(a, b, t): t = np.asarray(t)[..., None]; return np.asarray(a) * (1 - t) + np.asarray(b) * t
def smooth(e0, e1, x): t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)

def save(arr, path, nc=False):
    if os.path.exists(path) and not REDO: print("  exists, kept:", path); return bpy.data.images.load(path)
    rgba = np.ones((N, N, 4), np.float32); rgba[..., :arr.shape[-1]] = arr
    im = bpy.data.images.new(os.path.basename(path), N, N, alpha=True)
    if nc: im.colorspace_settings.name = 'Non-Color'
    im.pixels.foreach_set(rgba.ravel()); im.filepath_raw = path; im.file_format = 'PNG'; im.save(); return im

def write_maps(key, alb, metal, smooth_, height, emit=None, bump=6.0):
    d = os.path.join(OUT, "Textures", key); os.makedirs(d, exist_ok=True); p = lambda k: os.path.join(d, f"{key}_Unity_{k}.png")
    ms = np.zeros((N, N, 4), np.float32); ms[..., :3] = np.asarray(metal)[..., None] if np.ndim(metal) else metal; ms[..., 3] = smooth_
    gx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * bump; gy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * bump
    n = np.stack([-gx, -gy, np.ones_like(gx)], -1); n /= np.linalg.norm(n, axis=-1, keepdims=True)
    imgs = {"Albedo": save(np.clip(alb, 0, 1), p("Albedo")), "MetallicSmoothness": save(np.clip(ms, 0, 1), p("MetallicSmoothness"), True),
            "Normal": save(n * 0.5 + 0.5, p("Normal"), True)}
    if emit is not None: imgs["Emission"] = save(np.clip(emit, 0, 1), p("Emission"))
    return imgs

# ---------------------------------------------------------------- mesh helpers
def tube(path, radius, ring=14, flat=1.0, cap_tip=True):
    """A tube along `path` (list of Vectors), radius(t) for t in 0..1; UV u round, v along. flat squashes the side axis."""
    me = bpy.data.meshes.new("t"); bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap"); S = len(path) - 1
    tan0 = (path[1] - path[0]).normalized(); ref = Vector((0, 0, 1)) if abs(tan0.z) < 0.9 else Vector((1, 0, 0))
    a = ref.cross(tan0).normalized(); rings = []
    for i, q in enumerate(path):
        tan = (path[min(i + 1, S)] - path[max(i - 1, 0)]).normalized()
        a = (a - tan * a.dot(tan)).normalized(); b = tan.cross(a); r = radius(i / S)
        rings.append([bm.verts.new(q + (a * math.cos(k * 2 * math.pi / ring) * flat + b * math.sin(k * 2 * math.pi / ring)) * r) for k in range(ring)])
    for i in range(S):
        for k in range(ring):
            k2 = (k + 1) % ring; f = bm.faces.new((rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]))
            for l, uv in zip(f.loops, ((k / ring, i / S), ((k + 1) / ring, i / S), ((k + 1) / ring, (i + 1) / S), (k / ring, (i + 1) / S))): l[uvl].uv = uv
    for end, ring_, step, v_ in ((0, rings[0], path[0] - path[1], 0.0), (1, rings[-1], path[-1] - path[-2], 1.0)):
        c = bm.verts.new((path[0] if end == 0 else path[-1]) + step.normalized() * radius(end) * (0.3 if end or not cap_tip else 0.5))
        for k in range(ring):
            vs = (ring_[(k + 1) % ring], ring_[k], c) if end == 0 else (ring_[k], ring_[(k + 1) % ring], c)
            f = bm.faces.new(vs)
            for l in f.loops: l[uvl].uv = (k / ring, v_)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free(); return me

def sheet(points_fn, nu, nv, thickness, uv_fn):
    """A thin sheet from a (nu x nv) grid of points_fn(i/(nu-1), j/(nv-1)) -> Vector, given thickness by solidify."""
    me = bpy.data.meshes.new("s"); bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
    g = [[bm.verts.new(points_fn(i / (nu - 1), j / (nv - 1))) for j in range(nv)] for i in range(nu)]
    for i in range(nu - 1):
        for j in range(nv - 1):
            f = bm.faces.new((g[i][j], g[i + 1][j], g[i + 1][j + 1], g[i][j + 1]))
            for l in f.loops: l[uvl].uv = uv_fn(l.vert.co)
    bm.verts.ensure_lookup_table(); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("tmp", me); sc.collection.objects.link(o)
    m = o.modifiers.new("solid", 'SOLIDIFY'); m.thickness = thickness; m.offset = 0.0; m.use_even_offset = False
    dg = bpy.context.evaluated_depsgraph_get(); out = bpy.data.meshes.new_from_object(o.evaluated_get(dg), depsgraph=dg)
    bpy.data.objects.remove(o); return out

def plate(outline, nr, nt, dome, ridge, thickness):
    """A curved plate: polar grid round the origin, edge at outline(theta) (metres), domed, with a ridge along +Y.
    UVs planar over the plate's bounding square."""
    W = max(outline(t) for t in np.linspace(0, 2 * math.pi, 256)) * 1.02
    def pt(i, j):
        th = j * 2 * math.pi; R = outline(th); rho = max(i, 1e-3) ** 0.9
        x, y = rho * R * math.cos(th), rho * R * math.sin(th); rr = math.hypot(x, y) / W
        return Vector((x, y, dome * (1 - rr * rr) + ridge * max(0, 1 - abs(x) / (0.25 * W)) * (0.3 + 0.7 * max(0, y / W + 0.5))))
    return sheet(pt, nr, nt, thickness, lambda c: (0.5 + c.x / (2 * W), 0.5 + c.y / (2 * W))), W

def fan(L, spread, rays, sweep, cup, thickness, scallop=0.15, spike=0.0):
    """A fin / gill fan from the origin toward +Y: rays spread over `spread` degrees (swept back by `sweep`), a scalloped
    edge between the rays (spikes past it at the rays), corrugated. UVs planar: u = 0.5 + x / 2L, v = y / L."""
    S = math.radians(spread); sw = math.radians(sweep)
    def edge(s): k = s * (rays - 1); f = k - math.floor(k); return L * (1 - scallop * math.sin(math.pi * f) + spike * max(0, 1 - min(f, 1 - f) * 12))
    def pt(i, j):
        th = -S / 2 + j * S + sw * i; r = 0.004 + (edge(j) - 0.004) * i
        k = j * (rays - 1); f = k - math.floor(k)
        return Vector((r * math.sin(th), r * math.cos(th), cup * (j - 0.5) ** 2 * i + 0.0025 * math.sin(math.pi * f) * i))
    return sheet(pt, 24, (rays - 1) * 10 + 1, thickness, lambda c: (0.5 + c.x / (2 * L), c.y / L))

def curve(fn, n=64): return [fn(i / n) for i in range(n + 1)]
def fan_coords(L, spread, rays, sweep):
    """For a fan's planar UVs: per pixel radius fraction rf (0 base .. 1 edge-ish), position between rays s (0 at a ray)."""
    X = (U - 0.5) * 2 * L; Y = V * L; r = np.hypot(X, Y) + 1e-9; rf = r / L
    th = np.arctan2(X, Y) - math.radians(sweep) * rf
    k = (th + math.radians(spread) / 2) / math.radians(spread) * (rays - 1)
    return rf, np.abs(k - np.round(k)), k


def join(parts):
    """One mesh from (mesh, matrix) parts; the source meshes are removed."""
    bm = bmesh.new()
    for me, mx in parts:
        me.transform(mx); bm.from_mesh(me); bpy.data.meshes.remove(me)
    out = bpy.data.meshes.new("j"); bm.to_mesh(out); bm.free(); return out

def sphere(r, seg=12, rings=8):
    me = bpy.data.meshes.new("sp"); bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=r, calc_uvs=True)
    bm.to_mesh(me); bm.free(); return me

def lathe(profile, height, ring=18):
    """A round vessel along +Z: radius profile(t) for t 0 (base) .. 1 (top). UV u round, v up."""
    return tube(curve(lambda t: Vector((0, 0, height * t)), 24), profile, ring=ring)

def M(loc=(0, 0, 0), rot=(0, 0, 0), s=1.0):
    r = Matrix.Rotation(rot[2], 4, "Z") @ Matrix.Rotation(rot[1], 4, "Y") @ Matrix.Rotation(rot[0], 4, "X")
    return Matrix.Translation(Vector(loc)) @ r @ Matrix.Scale(s, 4)

def ROUND(th):
    """A fish scale's outline, a little flat at the root."""
    return 0.03 * (1 + 0.06 * math.sin(th)) * (1 - 0.15 * max(0, -math.sin(th)) ** 2)

def heap(n, seed, size=1.0):
    """A small heap of n scales, overlapping and tilted."""
    rnd = np.random.default_rng(seed); parts = []
    for i in range(n):
        me, _ = plate(ROUND, 10, 48, 0.004, 0.0, 0.0018)
        a = rnd.uniform(0, 2 * math.pi); r = 0.022 * math.sqrt(i / n) * 1.6
        rot = (rnd.uniform(-0.35, 0.35), rnd.uniform(-0.35, 0.35), rnd.uniform(0, 6.28))
        parts.append((me, M((r * math.cos(a), r * math.sin(a), 0.004 * i), rot, size * rnd.uniform(0.8, 1.1))))
    return join(parts)

def scale_rings(W=0.031):
    """Per pixel over a plate's planar UVs: growth rings round the root, radial ridges, and the distance out (0..1)."""
    X, Y = (U - 0.5) * 2 * W, (V - 0.5) * 2 * W; rr = np.hypot(X, Y) / W
    root = np.hypot(X, Y + 0.022); rings = 0.5 + 0.5 * np.sin(root * 900 + 2 * vnoise(32))
    radial = 0.5 + 0.5 * np.cos(np.arctan2(X, Y + 0.022) * 40)
    return rings, radial, rr

ITEMS = {}
def item(key):
    def reg(fn): ITEMS[key] = fn; return fn
    return reg

@item("mat_scales")
def fish_scales():
    me = heap(7, 3); rings, radial, rr = scale_rings(); n = fbm(32, 12)
    alb = mix((0.80, 0.83, 0.86), (0.42, 0.55, 0.60), smooth(0.2, 1.0, rr) * 0.7 + 0.3 * n)
    alb = mix(alb, (0.55, 0.72, 0.68), 0.25 * radial * smooth(0.3, 0.9, rr)); alb *= (0.9 + 0.1 * rings)[..., None]
    return me, write_maps("mat_scales", alb, 0.6, 0.7 + 0.1 * rings, 0.5 * rings + 0.2 * radial, None, 3.0), 0.0

@item("mat_oil")
def fish_oil():
    def body(t):
        if t < 0.72: return 0.012 + 0.024 * math.sin(math.pi * min(t / 0.7, 1.0)) ** 0.8
        return 0.010 + 0.002 * math.sin((t - 0.72) * 40)
    flask = lathe(body, 0.10); cork = lathe(lambda t: 0.0085 + 0.001 * t, 0.018, ring=12)
    me = join([(flask, M()), (cork, M((0, 0, 0.095)))])
    n = fbm(40, 14, 5); clay = mix((0.42, 0.28, 0.18), (0.58, 0.42, 0.28), n)
    run = smooth(0.06, 0.0, np.abs(((U * 5 + 0.3 * vnoise(24)) % 1) - 0.5) * (1.4 - V)) * smooth(0.45, 0.85, V + 0.15 * vnoise(16))
    alb = mix(clay, (0.78, 0.52, 0.12), run); alb = mix(alb, (0.55, 0.40, 0.25), smooth(0.92, 0.95, V))
    return me, write_maps("mat_oil", alb, 0.0, 0.25 + 0.6 * run, 0.4 * n - 0.3 * run, None, 3.0), 0.0

@item("mat_fins")
def spiny_fins():
    L, SP, RY, SW = 0.13, 85, 9, -15
    me = fan(L, SP, RY, SW, 0.015, 0.003, scallop=0.25, spike=0.22)
    rf, s, k = fan_coords(L, SP, RY, SW); ray = smooth(0.14, 0.03, s); n = fbm(32, 12, 4)
    memb = mix((0.30, 0.28, 0.16), (0.52, 0.44, 0.26), 0.5 * n + 0.4 * rf)
    alb = mix(memb, (0.88, 0.84, 0.72), ray); alb = mix(alb, (0.20, 0.17, 0.10), smooth(0.7, 0.85, vnoise(12)) * (1 - ray) * 0.6)
    return me, write_maps("mat_fins", alb, 0.0, 0.35 + 0.3 * ray, 0.7 * ray + 0.2 * n, None, 4.0), 0.0

@item("mat_roe")
def fish_roe():
    rnd = np.random.default_rng(8); parts = []
    pts = []
    while len(pts) < 44:                                    # eggs packed into a low mound, not touching through each other
        p = Vector((rnd.uniform(-1, 1) * 0.022, rnd.uniform(-1, 1) * 0.032, 0))
        if (p.x / 0.022) ** 2 + (p.y / 0.032) ** 2 > 1: continue
        p.z = 0.016 * (1 - (p.x / 0.022) ** 2 - (p.y / 0.032) ** 2) ** 0.5 * rnd.uniform(0.3, 1.0)
        if all((p - q).length > 0.0095 for q in pts): pts.append(p)
        elif rnd.random() < 0.002: break
    for p in pts: parts.append((sphere(rnd.uniform(0.0056, 0.0066)), M(tuple(p))))
    me = join(parts)
    n = fbm(16, 6); dot = smooth(0.06, 0.03, np.hypot((U * 12) % 1 - 0.5, (V * 8) % 1 - 0.35))   # a dark eye on each egg
    alb = mix(mix((0.92, 0.42, 0.10), (0.98, 0.62, 0.20), smooth(0.2, 0.8, V) * 0.7 + 0.3 * n), (0.25, 0.10, 0.05), dot * 0.8)
    return me, write_maps("mat_roe", alb, 0.0, 0.9, 0.2 * n, None, 2.0), 0.0

@item("mat_ink")
def abyssal_ink():
    path = curve(lambda t: Vector((0.006 * math.sin(t * 3), -0.05 + 0.10 * t, 0.004 * math.sin(t * 5))))
    sac = tube(path, lambda t: 0.004 + 0.028 * math.sin(math.pi * min(1, t * 1.15)) ** 0.7 * (1 - 0.55 * t), ring=18, flat=0.8)
    n = fbm(40, 14, 5); vein = smooth(0.035, 0.0, np.abs(vnoise(20) - 0.5)) * smooth(0.2, 0.5, n)
    alb = mix((0.03, 0.02, 0.05), (0.10, 0.06, 0.14), n); alb = mix(alb, (0.45, 0.25, 0.75), vein * 0.6)
    em = np.asarray((0.55, 0.25, 0.95)) * (vein * 0.7)[..., None]
    return sac, write_maps("mat_ink", alb, 0.0, 0.92, 0.3 * n + 0.3 * vein, em, 2.0), 1.0

@item("mat_cinder")
def cinder_scales():
    me = heap(6, 5); rings, radial, rr = scale_rings(); n = fbm(32, 12, 4)
    alb = mix((0.06, 0.05, 0.05), (0.20, 0.16, 0.14), 0.6 * n + 0.4 * rings)
    crack = smooth(0.035, 0.0, np.abs(fbm(24, 9) - 0.5)) * smooth(0.2, 0.6, rr); edge = smooth(0.75, 0.98, rr)
    alb = mix(alb, (0.95, 0.40, 0.08), crack); em = np.asarray((1.0, 0.40, 0.08)) * (crack * 0.95 + edge * 0.25)[..., None]
    return me, write_maps("mat_cinder", alb, 0.0, 0.2 + 0.2 * rings, 0.5 * rings - 0.4 * crack, em, 3.0), 1.5

@item("mat_rime")
def rime_scales():
    me = heap(7, 9); rings, radial, rr = scale_rings(); n = fbm(32, 12, 4)
    alb = mix((0.90, 0.95, 1.0), (0.38, 0.58, 0.82), smooth(0.25, 1.0, rr) * 0.8 + 0.2 * n); alb *= (0.92 + 0.08 * rings)[..., None]
    frost = smooth(0.78, 0.95, rr + 0.12 * (fbm(48, 16) - 0.5)); alb = mix(alb, (0.97, 0.99, 1.0), frost)
    em = np.asarray((0.35, 0.75, 1.0)) * (smooth(0.85, 1.0, rr) * 0.45)[..., None]
    return me, write_maps("mat_rime", alb, 0.1, 0.85 - 0.4 * frost, 0.4 * rings + 0.4 * frost, em, 3.0), 1.0

@item("mat_legend")
def legendary_scale():
    def out(th): return 0.06 * (1 + 0.08 * math.sin(th)) * (1 - 0.2 * max(0, -math.sin(th)) ** 2)
    me, W = plate(out, 16, 72, 0.010, 0.002, 0.004)
    rings, radial, rr = scale_rings(W); n = fbm(40, 14, 4)
    alb = mix((0.95, 0.78, 0.32), (0.55, 0.32, 0.12), smooth(0.2, 1.0, rr) * 0.7 + 0.3 * n); alb *= (0.85 + 0.15 * rings)[..., None]
    alb = mix(alb, (0.40, 0.75, 0.70), 0.18 * radial * smooth(0.4, 0.9, rr))     # a sea-green sheen across the ridges
    em = np.asarray((1.0, 0.75, 0.30)) * (smooth(0.82, 1.0, rr) * 0.6 + 0.1 * rings)[..., None]
    return me, write_maps("mat_legend", alb, 0.7, 0.85, 0.6 * rings + 0.2 * radial, em, 4.0), 1.2

@item("mat_trophy")
def trophy_fin():
    L, SP, RY, SW = 0.15, 75, 12, 0
    fin = fan(L, SP, RY, SW, 0.02, 0.003, scallop=0.30, spike=0.0)
    wrap = tube(curve(lambda t: Vector((0.007 * math.cos(t * 6.28 * 3), 0.006 + 0.012 * t, 0.007 * math.sin(t * 6.28 * 3))), 48), lambda t: 0.0016, ring=6)
    me = join([(fin, M()), (wrap, M())])
    rf, s, k = fan_coords(L, SP, RY, SW); ray = smooth(0.12, 0.03, s); n = fbm(32, 12, 4)
    memb = mix((0.45, 0.06, 0.06), (0.75, 0.18, 0.10), 0.5 * n + 0.5 * rf)
    alb = mix(memb, (0.90, 0.82, 0.62), ray); tip = smooth(0.82, 0.95, rf) * ray; alb = mix(alb, (0.95, 0.75, 0.25), tip)
    alb = mix(alb, (0.55, 0.42, 0.25), smooth(0.12, 0.08, rf))                    # the twine round the root
    return me, write_maps("mat_trophy", alb, 0.0, 0.4 + 0.3 * tip, 0.6 * ray + 0.2 * n, None, 4.0), 0.0

# ---------------------------------------------------------------- build, material, export
def material(key, imgs, glow):
    m = bpy.data.materials.new(key); m.use_nodes = True; nt = m.node_tree; Nn, L = nt.nodes, nt.links
    b = next(n for n in Nn if n.type == 'BSDF_PRINCIPLED')
    def tex(k, y):
        t = Nn.new("ShaderNodeTexImage"); t.image = imgs[k]; t.location = (-700, y); return t
    a = tex("Albedo", 300); L.new(a.outputs["Color"], b.inputs["Base Color"])
    s = tex("MetallicSmoothness", 0); s.image.colorspace_settings.name = 'Non-Color'
    sep = Nn.new("ShaderNodeSeparateColor"); L.new(s.outputs["Color"], sep.inputs["Color"]); L.new(sep.outputs["Red"], b.inputs["Metallic"])
    inv = Nn.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
    L.new(s.outputs["Alpha"], inv.inputs[1]); L.new(inv.outputs["Value"], b.inputs["Roughness"])
    nn = tex("Normal", -320); nn.image.colorspace_settings.name = 'Non-Color'; nm = Nn.new("ShaderNodeNormalMap")
    L.new(nn.outputs["Color"], nm.inputs["Color"]); L.new(nm.outputs["Normal"], b.inputs["Normal"])
    if "Emission" in imgs:
        e = tex("Emission", -650); L.new(e.outputs["Color"], b.inputs["Emission Color"]); b.inputs["Emission Strength"].default_value = glow
    Nn.active = a; return m

print("\n===== FISH MATERIALS =====")
objs = []
for key, fn in ITEMS.items():
    if ONLY and key not in ONLY: continue
    me, imgs, glow = fn(); me.name = key
    c = np.array([v.co[:] for v in me.vertices]); me.transform(Matrix.Translation(-Vector(((c.min(0) + c.max(0)) / 2).tolist())))
    me.materials.append(material(key, imgs, glow)); me.shade_smooth() if hasattr(me, "shade_smooth") else None
    ob = bpy.data.objects.new(key, me); sc.collection.objects.link(ob); objs.append(ob)
    path = os.path.join(OUT, "Models", key + ".fbx")
    size = c.max(0) - c.min(0)
    if os.path.exists(path) and not REDO: print(f"  {key}: exists, kept {path}"); continue
    for o in bpy.data.objects: o.select_set(o is ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={'MESH'}, global_scale=1.0, apply_unit_scale=True,
                             apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y', bake_space_transform=True,
                             mesh_smooth_type='FACE', bake_anim=False, path_mode='COPY', embed_textures=True)
    print(f"  {key}: {len(me.vertices)} verts, size {tuple((size * 100).round(1))} cm -> {os.path.basename(path)}")
x = 0.0
for ob in objs: ob.location = (x, 0, 0); x += 0.26
blend = os.path.join(OUT, "Blender Files", "fishmats.blend")
if not os.path.exists(blend) or ONLY: bpy.ops.wm.save_as_mainfile(filepath=blend if not ONLY else blend.replace(".blend", "_part.blend"))

R = os.environ.get("VDW_RENDER")
if R:
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 32; sc.view_settings.view_transform = 'Standard'
    wd = bpy.data.worlds.new("w"); wd.use_nodes = True; sc.world = wd; wd.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.055, 0.07, 1)
    ld = bpy.data.lights.new("key", 'SUN'); ld.energy = 3.5; lo = bpy.data.objects.new("key", ld); sc.collection.objects.link(lo); lo.rotation_euler = (0.6, 0.2, 0.8)
    cd = bpy.data.cameras.new("C"); cd.type = 'ORTHO'; cam = bpy.data.objects.new("C", cd); sc.collection.objects.link(cam); sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = 500, 500
    for ob in objs:
        for o in objs: o.hide_render = o is not ob
        c = np.array([ob.matrix_world @ v.co for v in ob.data.vertices]); tgt = Vector(((c.min(0) + c.max(0)) / 2).tolist())
        cd.ortho_scale = float((c.max(0) - c.min(0)).max()) * 1.3
        cam.location = tgt + Vector((0.45, -0.35, 1.0)).normalized() * 2; cam.rotation_euler = (tgt - cam.location).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = f"{R}_{ob.name}.png"; bpy.ops.render.render(write_still=True)
print("===== END =====")
