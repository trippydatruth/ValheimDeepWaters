# Builds the seven boss trophies (the material each great fish drops), each a small static model with its own painted
# Unity maps (Albedo, MetallicSmoothness, Normal from a height map, Emission):
#   bossmat_eikthyr_elver    Storm Barbel     - a curling whisker, slate grey, lightning crackling along it
#   bossmat_elder_bass       Elder Scale      - a broad shield of a scale, bark-brown growth rings, moss, a faint old glow
#   bossmat_bonemass_catfish Mire Whisker     - a drooping slimy whisker with swollen ooze blisters, glowing slime
#   bossmat_moder_scale      Frostwyrm Scale  - a pointed ridged dragon scale, ice white to deep blue, cold-lit rim
#   bossmat_yagluthgill      Ember Gill       - a fan of charred gill rakers, embers glowing between them
#   bossmat_queen_eel        Queen's Fang     - a curved fang, ivory to a violet-black root that glows
#   bossmat_fimbul_salmon    Rimefrost Fin    - a swept fin of frost-white spines, ice-blue membrane, a blue glow
# Writes <out>/Models/<key>.fbx, <out>/Textures/<key>/<key>_Unity_*.png, <out>/Blender Files/bossmats.blend, previews.
# Existing maps / models are kept (never overwritten).
#   env: VDW_OUT (folder), VDW_RENDER (png prefix, optional), VDW_ONLY (comma list of keys, optional)
import bpy, bmesh, math, os
import numpy as np
from mathutils import Matrix, Vector

OUT = os.environ["VDW_OUT"]; N = 512
ONLY = set(filter(None, os.environ.get("VDW_ONLY", "").split(",")))
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
    if os.path.exists(path): print("  exists, kept:", path); return bpy.data.images.load(path)
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

ITEMS = {}
def item(key):
    def reg(fn): ITEMS[key] = fn; return fn
    return reg

@item("bossmat_eikthyr_elver")
def storm_barbel():
    me = tube(curve(lambda t: Vector((0.05 * math.sin(t * 5.0) * t, -0.15 + 0.30 * t, 0.02 * math.sin(t * 3.1)))), lambda t: 0.012 * (1 - t) ** 0.8 + 0.0018)
    segs = 0.5 + 0.5 * np.cos(V * 2 * math.pi * 22); n = fbm(32, 12, 4)
    alb = mix((0.10, 0.13, 0.17), (0.22, 0.27, 0.32), 0.2 * segs + 0.8 * n)
    bolt = np.zeros_like(U)
    for u0, ph in ((0.25, 0.0), (0.75, 1.7), (0.5, 3.1)):
        zig = 0.05 * np.sign(np.sin(V * 40 + ph)) * np.abs(np.sin(V * 40 + ph)) ** 0.3 + 0.03 * (vnoise(16) - 0.5)
        bolt = np.maximum(bolt, smooth(0.022, 0.006, np.abs(U - u0 - zig)))
    alb = mix(alb, (0.75, 0.9, 1.0), bolt); h = 0.6 * segs + 0.3 * n - 0.4 * bolt
    em = np.asarray((0.35, 0.65, 1.0)) * (bolt[..., None] * 0.9 + 0.15 * smooth(0.7, 1.0, V)[..., None])
    return me, write_maps("bossmat_eikthyr_elver", alb, 0.15, 0.55 + 0.2 * bolt, h, em), 2.0

@item("bossmat_elder_bass")
def elder_scale():
    out = lambda th: 0.085 * (1 + 0.12 * math.sin(th)) * (1 - 0.18 * max(0, -math.sin(th)) ** 3)
    me, W = plate(out, 16, 72, 0.012, 0.0, 0.006)
    X, Y = (U - 0.5) * 2 * W, (V - 0.5) * 2 * W; base = np.hypot(X, Y + 0.075) + 0.004 * (fbm(48, 16) - 0.5)
    rings = 0.5 + 0.5 * np.sin(base * 320); grain = fbm(64, 24, 8, 3)
    alb = mix((0.20, 0.13, 0.07), (0.38, 0.26, 0.14), 0.6 * rings + 0.4 * grain)
    moss = smooth(0.62, 0.78, fbm(40, 12) + 0.3 * smooth(0.06, 0.09, np.hypot(X, Y)))
    alb = mix(alb, (0.22, 0.32, 0.10), moss)
    groove = smooth(0.15, 0.0, rings)
    em = np.asarray((0.25, 0.55, 0.15)) * (groove * (1 - moss) * 0.35)[..., None]
    return me, write_maps("bossmat_elder_bass", alb, 0.0, 0.2 + 0.2 * rings * (1 - moss), 0.7 * rings + 0.3 * grain + 0.3 * moss, em, 4.0), 1.0

@item("bossmat_bonemass_catfish")
def mire_whisker():
    blis = [(0.25, 0.9), (0.48, 0.7), (0.66, 0.6), (0.82, 0.45)]
    r = lambda t: (0.010 * (1 - t) ** 0.7 + 0.0022) * (1 + sum(a * math.exp(-((t - c) / 0.035) ** 2) for c, a in blis))
    me = tube(curve(lambda t: Vector((0.03 * math.sin(t * 2.4), -0.14 + 0.28 * t, -0.06 * t * t + 0.015 * math.sin(t * 6)))), r, ring=16)
    n = fbm(24, 10, 4); slime = smooth(0.52, 0.66, fbm(30, 9) + 0.25 * np.exp(-((V[..., None] - np.array([c for c, _ in blis])) / 0.04) ** 2).max(-1))
    alb = mix(mix((0.16, 0.19, 0.11), (0.30, 0.34, 0.20), n), (0.35, 0.65, 0.18), slime)
    alb = mix(alb, (0.08, 0.09, 0.05), smooth(0.65, 0.8, vnoise(20)) * (1 - slime))
    em = np.asarray((0.35, 0.95, 0.25)) * (slime * 0.7)[..., None]
    return me, write_maps("bossmat_bonemass_catfish", alb, 0.0, 0.6 + 0.35 * slime, 0.5 * n + 0.4 * slime, em, 3.0), 1.5

@item("bossmat_moder_scale")
def frostwyrm_scale():
    def out(th):
        s = math.sin(th); c = math.cos(th)
        return 0.07 * (1 + 0.95 * max(0, s) ** 5) * (1 - 0.25 * max(0, -s)) * (1 - 0.08 * c * c)
    me, W = plate(out, 18, 80, 0.008, 0.007, 0.005)
    X, Y = (U - 0.5) * 2 * W, (V - 0.5) * 2 * W; th = np.arctan2(Y, X)
    R = 0.07 * (1 + 0.95 * np.maximum(0, np.sin(th)) ** 5) * (1 - 0.25 * np.maximum(0, -np.sin(th))) * (1 - 0.08 * np.cos(th) ** 2)
    rr = np.hypot(X, Y) / R; stri = 0.5 + 0.5 * np.sin(np.arctan2(X, Y + 0.07) * 90 + 3 * vnoise(32)); ridge = smooth(0.012, 0.0, np.abs(X))
    alb = mix((0.80, 0.90, 0.98), (0.30, 0.48, 0.75), smooth(0.3, 1.0, rr)); alb = mix(alb, (0.95, 0.98, 1.0), ridge * 0.7)
    alb *= (0.92 + 0.08 * stri)[..., None]
    rim = smooth(0.8, 0.97, rr); em = np.asarray((0.35, 0.75, 1.0)) * (0.5 * rim + 0.35 * ridge)[..., None]
    return me, write_maps("bossmat_moder_scale", alb, 0.1, 0.85 + 0.1 * ridge, 0.3 * stri + 0.6 * ridge - 0.3 * rr, em, 4.0), 1.5

@item("bossmat_yagluthgill")
def ember_gill():
    L, SP, RY, SW = 0.15, 110, 13, 0.0
    me = fan(L, SP, RY, SW, 0.02, 0.004, scallop=0.12, spike=0.06)
    rf, s, k = fan_coords(L, SP, RY, SW); rib = smooth(0.18, 0.04, s); n = fbm(24, 8, 3)
    char = mix((0.05, 0.04, 0.04), (0.16, 0.13, 0.12), n); memb = mix((0.45, 0.07, 0.03), (0.85, 0.28, 0.06), smooth(0.9, 0.2, rf) * n)
    alb = mix(memb, char, rib)
    crack = smooth(0.62, 0.72, fbm(40, 14) + 0.2 * (1 - rf)) * (1 - rib)
    em = np.asarray((1.0, 0.42, 0.08)) * ((1 - rib) * 0.35 * smooth(1.0, 0.3, rf) + crack * 0.9)[..., None]
    return me, write_maps("bossmat_yagluthgill", alb, 0.0, 0.25 + 0.3 * (1 - rib), 0.8 * rib + 0.2 * n, em, 4.0), 1.5

@item("bossmat_queen_eel")
def queens_fang():
    A = math.radians(60); R = 0.20 / A
    me = tube(curve(lambda t: Vector((0, R * math.sin(A * t) - 0.10, R * (1 - math.cos(A * t)))), 48), lambda t: 0.022 * (1 - t) ** 1.15 + 0.0004, ring=16, flat=0.8)
    groove = 0.5 + 0.5 * np.cos(U * 2 * math.pi * 7 + 0.4 * vnoise(32)); n = fbm(48, 16, 6)
    root = smooth(0.28, 0.06, V)
    alb = mix(mix((0.80, 0.76, 0.66), (0.95, 0.92, 0.84), smooth(0.2, 0.9, V)), (0.20, 0.07, 0.26), root)
    alb *= (0.9 + 0.1 * groove * (1 - V * 0.8))[..., None]; alb = mix(alb, (0.98, 0.96, 0.9), smooth(0.93, 1.0, V))
    em = np.asarray((0.65, 0.2, 0.95)) * (root * (0.5 + 0.5 * n) * 0.8)[..., None]
    return me, write_maps("bossmat_queen_eel", alb, 0.0, 0.8 + 0.1 * V, 0.4 * groove * (1 - V) + 0.2 * n, em, 3.0), 1.5

@item("bossmat_fimbul_salmon")
def rimefrost_fin():
    L, SP, RY, SW = 0.20, 70, 11, -25
    me = fan(L, SP, RY, SW, 0.03, 0.004, scallop=0.18, spike=0.10)
    rf, s, k = fan_coords(L, SP, RY, SW); spine = smooth(0.14, 0.03, s); n = fbm(32, 12, 4)
    memb = mix((0.30, 0.52, 0.78), (0.62, 0.82, 0.96), n * 0.6 + 0.4 * rf)
    frost = smooth(0.78, 0.95, rf + 0.15 * (fbm(48, 16) - 0.5))
    alb = mix(mix(memb, (0.92, 0.96, 1.0), spine), (0.95, 0.98, 1.0), frost)
    crystals = smooth(0.7, 0.85, vnoise(6)) * frost
    em = np.asarray((0.3, 0.7, 1.0)) * ((1 - spine) * (1 - frost) * 0.45 + spine * smooth(0.6, 1.0, rf) * 0.8)[..., None]
    return me, write_maps("bossmat_fimbul_salmon", alb, 0.0, 0.75 + 0.15 * spine - 0.3 * frost, 0.6 * spine + 0.4 * frost + 0.3 * crystals, em, 4.0), 1.2

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

print("\n===== BOSS MATERIALS =====")
objs = []
for key, fn in ITEMS.items():
    if ONLY and key not in ONLY: continue
    me, imgs, glow = fn(); me.name = key
    c = np.array([v.co[:] for v in me.vertices]); me.transform(Matrix.Translation(-Vector(((c.min(0) + c.max(0)) / 2).tolist())))
    me.materials.append(material(key, imgs, glow)); me.shade_smooth() if hasattr(me, "shade_smooth") else None
    ob = bpy.data.objects.new(key, me); sc.collection.objects.link(ob); objs.append(ob)
    path = os.path.join(OUT, "Models", key + ".fbx")
    size = c.max(0) - c.min(0)
    if os.path.exists(path): print(f"  {key}: exists, kept {path}"); continue
    for o in bpy.data.objects: o.select_set(o is ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={'MESH'}, global_scale=1.0, apply_unit_scale=True,
                             apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y', bake_space_transform=True,
                             mesh_smooth_type='FACE', bake_anim=False, path_mode='COPY', embed_textures=True)
    print(f"  {key}: {len(me.vertices)} verts, size {tuple((size * 100).round(1))} cm -> {os.path.basename(path)}")
x = 0.0
for ob in objs: ob.location = (x, 0, 0); x += 0.26
blend = os.path.join(OUT, "Blender Files", "bossmats.blend")
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
