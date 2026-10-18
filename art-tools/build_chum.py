# Builds a chum bucket for one tier: the bucket (its own UVs and painted maps, untouched), a liquid surface inside it,
# and what's in it:
#   chum_basic   - bait minnows packed in (heads and tails out, a few over the rim, some floating on their side)
#   chum_blood   - minnows and curled leeches in blood
#   chum_abyssal - things up from the deep: tentacles curling out over the rim with glowing rings, glowing ooze and roe
#   chum_blubber - the Deep North: hacked chunks of whale blubber (grey skin, cream fat) in rendered oil, a few minnows
# Objects (each its own material / Unity texture set, named after the object): bucket, liquid, and fish / leech /
# tentacle / ooze. Origin at the middle of the bottom, VDW_HEIGHT tall, facing -Y.
# env: VDW_TIER, VDW_BUCKET (glb), VDW_BUCKET_TEX (Material_baseColor/metallicRoughness/normal), VDW_ASSETS (the Unity
#      Assets/DeepWaters folder, for bait_minnow and bait_leech), VDW_SAVE_TO, VDW_TEX_OUT (shared maps go here, the
#      tier's own in VDW_TEX_OUT/<tier>), VDW_HEIGHT (0.40)
import bpy, bmesh, glob, math, os, shutil
import numpy as np
from mathutils import Euler, Matrix, Vector, noise

TIER = os.environ["VDW_TIER"]; H = float(os.environ.get("VDW_HEIGHT", "0.40"))
OUT = os.environ["VDW_TEX_OUT"]; TOUT = os.path.join(OUT, TIER); os.makedirs(TOUT, exist_ok=True)
ASSETS = os.environ["VDW_ASSETS"]
sc = bpy.context.scene
for o in list(bpy.data.objects): bpy.data.objects.remove(o)

def link(name, me):
    o = bpy.data.objects.new(name, me); sc.collection.objects.link(o); return o

def join(name, mesh_list):
    objs = [link(name if i == 0 else "p", m) for i, m in enumerate(mesh_list)]
    for o in bpy.data.objects: o.select_set(o in objs)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1: bpy.ops.object.join()
    objs[0].data.name = name
    return objs[0]

# ---------------------------------------------------------------- bucket
bpy.ops.import_scene.gltf(filepath=os.environ["VDW_BUCKET"])
for o in [o for o in bpy.data.objects if o.type != 'MESH']: bpy.data.objects.remove(o)
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
for o in meshes:
    o.data.transform(o.matrix_world); o.parent = None; o.matrix_world = Matrix()
bpy.context.view_layer.objects.active = meshes[0]
for o in meshes: o.select_set(True)
if len(meshes) > 1: bpy.ops.object.join()
bucket = bpy.context.view_layer.objects.active; bucket.name = "bucket"; bucket.data.name = "bucket"
co = np.array([v.co[:] for v in bucket.data.vertices]); lo, hi = co.min(0), co.max(0)
s = H / (hi[2] - lo[2])
bot = co[co[:, 2] < lo[2] + 0.1 * (hi[2] - lo[2])]                  # centre on the body, not the handle
cx, cy = (bot[:, 0].min() + bot[:, 0].max()) / 2, (bot[:, 1].min() + bot[:, 1].max()) / 2
bucket.data.transform(Matrix.Scale(s, 4) @ Matrix.Translation((-cx, -cy, -lo[2])))
co = np.array([v.co[:] for v in bucket.data.vertices]); r = np.hypot(co[:, 0], co[:, 1])
RIM = float(co[:, 2].max()); LIQ = 0.86 * H
band = np.abs(co[:, 2] - LIQ) < 0.04 * H
R_IN = float(r[band].min()) * math.cos(math.pi / 12) * 0.97          # 12-sided: the flat sides are closer in
print(f"BUCKET {H * 100:.0f} cm, rim {RIM * 100:.1f} cm, liquid at {LIQ * 100:.1f} cm, inner radius {R_IN * 100:.1f} cm")

# ---------------------------------------------------------------- liquid
me = bpy.data.meshes.new("liquid"); bm = bmesh.new()
ring = [bm.verts.new((R_IN * math.cos(a), R_IN * math.sin(a), LIQ)) for a in np.linspace(0, 2 * math.pi, 40, endpoint=False)]
bmesh.ops.triangulate(bm, faces=[bm.faces.new(ring)])
uv = bm.loops.layers.uv.new("UVMap")
for f in bm.faces:
    for l in f.loops: l[uv].uv = (0.5 + l.vert.co.x / (2 * R_IN), 0.5 + l.vert.co.y / (2 * R_IN))
bm.to_mesh(me); bm.free(); liquid = link("liquid", me)

# ---------------------------------------------------------------- helpers for the contents
def rest_mesh(fbx, length):
    """A rigged model's mesh in its rest pose, centred, scaled to `length` along Y (head -Y)."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=fbx)
    new = [o for o in bpy.data.objects if o not in before]
    src = next(o for o in new if o.type == 'MESH')
    for o in new:
        if o.type == 'ARMATURE':
            if o.animation_data: o.animation_data.action = None
            for pb in o.pose.bones: pb.matrix_basis = Matrix()
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
    m = bpy.data.meshes.new_from_object(src.evaluated_get(dg), depsgraph=dg); m.transform(src.matrix_world)
    for o in new: bpy.data.objects.remove(o)
    c = np.array([v.co[:] for v in m.vertices]); lo_, hi_ = c.min(0), c.max(0)
    m.transform(Matrix.Scale(length / (hi_[1] - lo_[1]), 4) @ Matrix.Translation(-Vector(((lo_ + hi_) / 2).tolist())))
    return m

def bend(m, degrees):
    """Curls a mesh lying along Y (in the XY plane) by `degrees` over its length."""
    if abs(degrees) < 1: return
    c = np.array([v.co[:] for v in m.vertices]); L = c[:, 1].max() - c[:, 1].min()
    R = L / math.radians(abs(degrees)); sgn = 1 if degrees > 0 else -1
    for v in m.vertices:
        a = (v.co.y - c[:, 1].min()) / R - math.radians(abs(degrees)) / 2
        rr = R + sgn * v.co.x
        v.co.x, v.co.y = sgn * (R - rr * math.cos(a)), rr * math.sin(a)
    m.flip_normals()                 # the curl above mirrors x, which would leave the faces inside out

def place(m, x, y, dz, yaw, pitch, roll):
    """Turns (roll about its length, then pitch head-up, then yaw) and puts it at (x, y, liquid + dz), then pulls it in
    from the wall until everything below the rim is inside the bucket."""
    rot = Euler((math.radians(-pitch), math.radians(roll), math.radians(yaw)), 'YXZ').to_matrix().to_4x4()
    m.transform(Matrix.Translation((x, y, LIQ + dz)) @ rot)
    for _ in range(40):
        c = np.array([v.co[:] for v in m.vertices]); below = c[:, 2] < RIM
        over = (np.hypot(c[below, 0], c[below, 1]) - R_IN * 0.95).max() if below.any() else -1
        if over <= 0: break
        mid = Vector((float(c[:, 0].mean()), float(c[:, 1].mean()), 0))
        m.transform(Matrix.Translation(-mid.normalized() * min(over + 0.002, 0.01)))
    return m

def copy_maps(prefix_src, folder, prefix_dst):
    for k in ("Albedo", "MetallicSmoothness", "Normal"):
        f = glob.glob(os.path.join(folder, f"{prefix_src}_Unity_{k}.*"))
        if f: shutil.copy(f[0], os.path.join(TOUT, f"{prefix_dst}_Unity_{k}{os.path.splitext(f[0])[1]}"))

def save(px, path):
    h, w = px.shape[:2]; im = bpy.data.images.new(os.path.basename(path), w, h, alpha=True)
    im.pixels[:] = np.asarray(px, np.float32).ravel(); im.filepath_raw = path; im.file_format = 'PNG'; im.save()

rng = np.random.default_rng(7); N = 256
def vnoise(scale, n=N):
    g = rng.random((n // scale + 2, n // scale + 2)); yy, xx = np.mgrid[0:n, 0:n] / scale
    x0, y0 = xx.astype(int), yy.astype(int); fx, fy = xx - x0, yy - y0; fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    return g[y0, x0] * (1 - fx) * (1 - fy) + g[y0, x0 + 1] * fx * (1 - fy) + g[y0 + 1, x0] * (1 - fx) * fy + g[y0 + 1, x0 + 1] * fx * fy
swirl = 0.5 * vnoise(64) + 0.3 * vnoise(24) + 0.2 * vnoise(8)

# minnow layouts: (x, y, height above the surface, yaw, pitch (+ = head up), roll)
MINNOWS = [(0.02, 0.02, 0.07, 20, 70, 0), (-0.06, 0.05, 0.04, 140, 58, 25), (0.06, -0.05, 0.01, 250, 0, 90),
           (-0.04, -0.06, 0.03, 300, 50, -20), (0.07, 0.06, 0.05, 80, 64, 60), (-0.08, -0.005, 0.02, 200, -48, 10),
           (0.0, -0.09, 0.008, 15, 6, 95), (0.09, -0.01, 0.035, 330, 45, -35), (-0.02, 0.09, 0.006, 110, -8, 85)]
contents = []

if TIER in ("chum_basic", "chum_blood"):
    fish_src = rest_mesh(os.path.join(ASSETS, "bait_minnow", "bait_minnow_model.fbx"), 0.22 if TIER == "chum_basic" else 0.20)
    layout = MINNOWS if TIER == "chum_basic" else [MINNOWS[i] for i in (0, 2, 4, 5, 7)]
    contents.append(join("fish", [place(fish_src.copy(), *p) for p in layout]))
    copy_maps("bait_minnow", os.path.join(ASSETS, "bait_minnow"), "fish")

if TIER == "chum_blood":
    leech_src = rest_mesh(os.path.join(ASSETS, "bait_leech", "bait_leech_model.fbx"), 0.17)
    # (x, y, dz, yaw, pitch, roll, curl degrees): curled up in the blood, one rearing out, one coiled on the surface
    LEECH = [(-0.05, 0.03, 0.01, 60, 10, 0, 140), (0.04, 0.05, 0.035, 170, 55, 0, 70), (-0.02, -0.07, 0.004, 280, 0, 0, 220),
             (0.08, -0.04, 0.02, 20, 35, 0, 110), (-0.09, -0.04, 0.012, 230, 20, 0, 180), (0.01, -0.01, 0.006, 120, 0, 0, 260)]
    parts = []
    for (x, y, dz, yaw, pitch, roll, curl) in LEECH:
        m = leech_src.copy(); bend(m, curl); parts.append(place(m, x, y, dz, yaw, pitch, roll))
    contents.append(join("leech", parts))
    copy_maps("bait_leech", os.path.join(ASSETS, "bait_leech"), "leech")

if TIER == "chum_abyssal":
    # tentacles: tapered tubes rising out of the ooze, leaning out and curling over the rim
    def tentacle(angle, length, r0, tilt, bend, twist, base_r):
        """Grown step by step: it starts leaning `tilt` degrees out from straight up and bends `bend` degrees in all,
        more and more toward the tip (so the tip curls), twisting a little as it goes."""
        me = bpy.data.meshes.new("t"); bm = bmesh.new(); SEG, RING = 48, 12
        out = Vector((math.cos(angle), math.sin(angle), 0)); side = Vector((-out.y, out.x, 0))
        d = (Vector((0, 0, 1)) * math.cos(math.radians(tilt)) + out * math.sin(math.radians(tilt))).normalized()
        p = out * base_r + Vector((0, 0, LIQ - 0.05)); pts = [p.copy()]
        w = [((i + 0.5) / SEG) ** 1.6 for i in range(SEG)]; wsum = sum(w)
        for i in range(SEG):
            axis = side.copy(); axis.rotate(Matrix.Rotation(math.radians(twist * i / SEG), 3, d))
            d.rotate(Matrix.Rotation(math.radians(-bend * w[i] / wsum), 3, axis)); d.normalize()
            p = p + d * (length / SEG); pts.append(p.copy())
        rings = []
        for i, q in enumerate(pts):
            t = i / SEG; tan = (pts[min(i + 1, SEG)] - pts[max(i - 1, 0)]).normalized()
            a = side.cross(tan); a = a.normalized() if a.length > 1e-6 else tan.orthogonal().normalized(); b = tan.cross(a)
            rad = r0 * (1 - 0.9 * t ** 0.9)
            rings.append([bm.verts.new(q + (a * math.cos(k * 2 * math.pi / RING) + b * math.sin(k * 2 * math.pi / RING)) * rad) for k in range(RING)])
        uvl = bm.loops.layers.uv.new("UVMap")
        for i in range(SEG):
            for k in range(RING):
                k2 = (k + 1) % RING
                f = bm.faces.new((rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]))
                for l, (uu, vv) in zip(f.loops, ((k / RING, i / SEG), ((k + 1) / RING, i / SEG), ((k + 1) / RING, (i + 1) / SEG), (k / RING, (i + 1) / SEG))):
                    l[uvl].uv = (uu, vv)
        tip = bm.verts.new(pts[-1] + (pts[-1] - pts[-2]).normalized() * r0 * 0.1)
        for k in range(RING):
            f = bm.faces.new((rings[-1][k], rings[-1][(k + 1) % RING], tip))
            for l in f.loops: l[uvl].uv = (k / RING, 0.999)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
        c = np.array([v.co[:] for v in me.vertices])
        print(f"  tentacle at {math.degrees(angle):.0f} deg: top {c[:, 2].max() * 100:.1f} cm, reaches {np.hypot(c[:, 0], c[:, 1]).max() * 100:.1f} cm out")
        return me
    # (angle round the bucket, length, base radius, lean, total bend (- = outward), twist, how far out it rises):
    # one arcs out over the rim and curls down the outside, one coils up in a spiral, one curls back in over the ooze
    T = [(0.5, 0.42, 0.034, 20, -215, 15, 0.075), (2.7, 0.26, 0.029, -5, 330, 60, 0.07), (4.6, 0.24, 0.026, 25, 190, -30, 0.09)]
    contents.append(join("tentacle", [tentacle(*p) for p in T]))    # glowing ooze globs and a cluster of roe
    blobs = []
    for (x, y, rad, dz) in [(0.03, -0.06, 0.035, -0.008), (-0.07, -0.02, 0.028, -0.006), (0.08, 0.05, 0.03, -0.01), (-0.03, 0.08, 0.022, -0.004), (-0.1, 0.06, 0.018, -0.002)]:
        m = bpy.data.meshes.new("b"); bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=3, radius=rad)
        for v in bm.verts:
            n_ = noise.noise(v.co * (40 / rad * 0.02)); v.co *= 1 + 0.25 * n_; v.co.z *= 0.55
        bm.to_mesh(m); bm.free(); m.transform(Matrix.Translation((x, y, LIQ + dz))); blobs.append(m)
    for i in range(14):
        a = i * 2.4; rr = 0.012 * math.sqrt(i)
        m = bpy.data.meshes.new("e"); bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=2, radius=0.0075)
        bm.to_mesh(m); bm.free(); m.transform(Matrix.Translation((0.05 + rr * math.cos(a), 0.0 + rr * math.sin(a), LIQ + 0.002))); blobs.append(m)
    ooze = join("ooze", blobs)
    bm = bmesh.new(); bm.from_mesh(ooze.data); uvl = bm.loops.layers.uv.new("UVMap")       # spherical-ish UVs
    for f in bm.faces:
        for l in f.loops: l[uvl].uv = (0.5 + 0.5 * math.atan2(l.vert.co.y, l.vert.co.x) / math.pi, (l.vert.co.z - LIQ) * 8 + 0.5)
    bm.to_mesh(ooze.data); bm.free(); contents.append(ooze)
    # maps: tentacle - near-black purple skin, paler underside stripe, glowing teal rings and tip
    v = np.linspace(0, 1, N)[:, None] * np.ones((1, N)); u = np.ones((N, 1)) * np.linspace(0, 1, N)[None, :]
    skin = np.ones((N, N, 4), np.float32); under = np.clip(1 - np.abs(u - 0.5) * 4, 0, 1)
    base = np.array([0.05, 0.025, 0.07]) * (1 - under[..., None]) + np.array([0.22, 0.12, 0.2]) * under[..., None]
    skin[..., :3] = base * (0.8 + 0.4 * vnoise(16)[..., None])
    rings = np.clip(1 - np.abs(((v * 14) % 1) - 0.5) * 9, 0, 1) * under * (v < 0.92)
    tipglow = np.clip((v - 0.86) * 8, 0, 1)
    g = np.clip(rings + tipglow, 0, 1)[..., None]
    skin[..., :3] = skin[..., :3] * (1 - g) + np.array([0.2, 0.9, 0.8]) * g
    save(skin, os.path.join(TOUT, "tentacle_Unity_Albedo.png"))
    ms = np.zeros((N, N, 4), np.float32); ms[..., 3] = 0.7; save(ms, os.path.join(TOUT, "tentacle_Unity_MetallicSmoothness.png"))
    em = np.zeros((N, N, 4), np.float32); em[..., :3] = np.array([0.15, 1.0, 0.85]) * g; em[..., 3] = 1
    save(em, os.path.join(TOUT, "tentacle_Unity_Emission.png"))
    # ooze - bright green, wet, glowing
    oz = np.ones((N, N, 4), np.float32); oz[..., :3] = np.array([0.25, 0.9, 0.35]) * (0.7 + 0.3 * swirl[..., None])
    save(oz, os.path.join(TOUT, "ooze_Unity_Albedo.png"))
    ms = np.zeros((N, N, 4), np.float32); ms[..., 3] = 0.9; save(ms, os.path.join(TOUT, "ooze_Unity_MetallicSmoothness.png"))
    em = np.zeros((N, N, 4), np.float32); em[..., :3] = np.array([0.3, 1.0, 0.4]) * (0.6 + 0.4 * swirl[..., None]); em[..., 3] = 1
    save(em, os.path.join(TOUT, "ooze_Unity_Emission.png"))

if TIER == "chum_blubber":
    # hacked blocks of blubber: lumpy boxes, the skin side (+z of the block) grey-black, the cut sides cream fat.
    # UVs: u across the block, v = 0..0.25 skin, 0.25..1 fat (by how far below the skin the vertex is)
    def chunk(x, y, dz, sx, sy, sz, yaw, pitch, roll, seed):
        m = bpy.data.meshes.new("c"); bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=3, use_grid_fill=True)
        for v in bm.verts:
            v.co = Vector((v.co.x * sx, v.co.y * sy, v.co.z * sz))
            n_ = noise.noise(v.co * 30 + Vector((seed, seed * 2, 0)))
            v.co += v.co.normalized() * 0.006 * n_
            if v.co.z > sz * 0.3: v.co.z += 0.003 * noise.noise(v.co * 60)        # wrinkled skin
        uvl = bm.loops.layers.uv.new("UVMap")
        for fc in bm.faces:
            for l in fc.loops:
                c_ = l.vert.co; depth = (sz / 2 - c_.z) / sz
                l[uvl].uv = ((c_.x / sx + c_.y / sy) * 0.5 + 0.5, 0.25 + 0.75 * depth if fc.normal.z < 0.7 else 0.12 + 0.1 * (c_.x / sx + 0.5))
        bm.to_mesh(m); bm.free()
        return place(m, x, y, dz, yaw, pitch, roll)
    CH = [(0.0, 0.0, 0.02, 0.10, 0.07, 0.06, 15, 30, 10, 1), (-0.07, 0.04, 0.01, 0.08, 0.06, 0.05, 120, -15, 20, 2),
          (0.06, -0.05, 0.005, 0.07, 0.05, 0.05, 250, 10, -10, 3), (-0.04, -0.07, 0.015, 0.06, 0.05, 0.045, 300, 40, 0, 4),
          (0.07, 0.06, 0.03, 0.09, 0.05, 0.05, 70, 55, 30, 5), (0.03, 0.09, -0.005, 0.06, 0.045, 0.04, 200, 5, 80, 6)]
    contents.append(join("blubber", [chunk(*p) for p in CH]))
    fish_src = rest_mesh(os.path.join(ASSETS, "bait_minnow", "bait_minnow_model.fbx"), 0.20)
    contents.append(join("fish", [place(fish_src.copy(), *MINNOWS[i]) for i in (2, 5, 8)]))
    copy_maps("bait_minnow", os.path.join(ASSETS, "bait_minnow"), "fish")
    v = np.linspace(0, 1, N)[:, None] * np.ones((1, N))
    bl = np.ones((N, N, 4), np.float32)
    fat = np.array([0.93, 0.86, 0.72]) * (0.9 + 0.12 * vnoise(8)[..., None])
    fat = fat * (1 - 0.25 * np.clip(((v * 9 + 0.6 * vnoise(32)) % 1 < 0.08), 0, 1)[..., None])   # faint layered streaks
    pink = np.clip((0.4 - v) * 4, 0, 1)[..., None]                                             # pinkish just under the skin
    fat = fat * (1 - pink) + np.array([0.85, 0.55, 0.52]) * pink
    skin = np.array([0.12, 0.13, 0.15]) * (0.8 + 0.4 * vnoise(16)[..., None])
    s_ = np.clip((0.25 - v) * 40, 0, 1)[..., None]
    bl[..., :3] = fat * (1 - s_) + skin * s_
    save(bl, os.path.join(TOUT, "blubber_Unity_Albedo.png"))
    ms = np.zeros((N, N, 4), np.float32); ms[..., 3] = (0.55 + 0.25 * s_[..., 0]); save(ms, os.path.join(TOUT, "blubber_Unity_MetallicSmoothness.png"))

# ---------------------------------------------------------------- maps: bucket (shared), liquid (this tier)
def load(path):
    im = bpy.data.images.load(path); w, h = im.size; return np.array(im.pixels[:], np.float32).reshape(h, w, 4)
BT = os.environ["VDW_BUCKET_TEX"]
if not os.path.exists(os.path.join(OUT, "bucket_Unity_Albedo.png")):
    a = load(os.path.join(BT, "Material_baseColor.png")); a[..., 3] = 1; save(a, os.path.join(OUT, "bucket_Unity_Albedo.png"))
    mr = load(os.path.join(BT, "Material_metallicRoughness.png"))                     # glTF: G roughness, B metallic
    ms = np.zeros_like(mr); ms[..., :3] = mr[..., 2:3]; ms[..., 3] = 1 - mr[..., 1]; save(ms, os.path.join(OUT, "bucket_Unity_MetallicSmoothness.png"))
    shutil.copy(os.path.join(BT, "Material_normal.png"), os.path.join(OUT, "bucket_Unity_Normal.png"))
for k in ("Albedo", "MetallicSmoothness", "Normal"):
    shutil.copy(os.path.join(OUT, f"bucket_Unity_{k}.png"), os.path.join(TOUT, f"bucket_Unity_{k}.png"))
LIQ_COL = {"chum_basic": ((0.20, 0.15, 0.08), (0.36, 0.30, 0.16), None),
           "chum_blood": ((0.18, 0.01, 0.01), (0.42, 0.03, 0.03), None),
           "chum_abyssal": ((0.01, 0.04, 0.05), (0.08, 0.55, 0.35), (0.1, 0.8, 0.45)),
           "chum_blubber": ((0.55, 0.45, 0.22), (0.86, 0.76, 0.48), None)}[TIER]      # rendered whale oil
t = np.clip((swirl - 0.35) * 2.2, 0, 1)[..., None]
alb = np.ones((N, N, 4), np.float32); alb[..., :3] = np.array(LIQ_COL[0]) * (1 - t) + np.array(LIQ_COL[1]) * t
save(alb, os.path.join(TOUT, "liquid_Unity_Albedo.png"))
ms = np.zeros((N, N, 4), np.float32); ms[..., 3] = 0.82; save(ms, os.path.join(TOUT, "liquid_Unity_MetallicSmoothness.png"))
if LIQ_COL[2]:
    e = np.zeros((N, N, 4), np.float32); g = np.clip((swirl - 0.55) * 3.0, 0, 1)[..., None]; e[..., :3] = np.array(LIQ_COL[2]) * g; e[..., 3] = 1
    save(e, os.path.join(TOUT, "liquid_Unity_Emission.png"))

# ---------------------------------------------------------------- materials (previews), named after the objects
def material(name, glow):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name); mat.use_nodes = True
    nt = mat.node_tree; b = nt.nodes["Principled BSDF"]; L = nt.links.new
    for n_ in [n_ for n_ in nt.nodes if n_.type == 'TEX_IMAGE']: nt.nodes.remove(n_)
    def img(k, color=True):
        f = glob.glob(os.path.join(TOUT, f"{name}_Unity_{k}.*"))
        if not f: return None
        t_ = nt.nodes.new("ShaderNodeTexImage"); t_.image = bpy.data.images.load(f[0])
        if not color: t_.image.colorspace_settings.name = "Non-Color"
        return t_
    a = img("Albedo")
    if a: L(a.outputs["Color"], b.inputs["Base Color"])
    m = img("MetallicSmoothness", False)
    if m:
        sep = nt.nodes.new("ShaderNodeSeparateColor"); L(m.outputs["Color"], sep.inputs["Color"]); L(sep.outputs["Red"], b.inputs["Metallic"])
        inv = nt.nodes.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1; L(m.outputs["Alpha"], inv.inputs[1]); L(inv.outputs[0], b.inputs["Roughness"])
    nn = img("Normal", False)
    if nn:
        nm = nt.nodes.new("ShaderNodeNormalMap"); L(nn.outputs["Color"], nm.inputs["Color"]); L(nm.outputs["Normal"], b.inputs["Normal"])
    e = img("Emission")
    if e: L(e.outputs["Color"], b.inputs["Emission Color"]); b.inputs["Emission Strength"].default_value = glow
    return mat
for o in [bucket, liquid] + contents:
    o.data.materials.clear(); o.data.materials.append(material(o.name, 3.0))
for c_ in contents:
    cc = np.array([v.co[:] for v in c_.data.vertices])
    print(f"CONTENT {c_.name}: {len(cc)} verts, top {cc[:, 2].max() * 100:.1f} cm, widest {np.hypot(cc[:, 0], cc[:, 1]).max() * 100:.1f} cm")
for i in list(bpy.data.images):
    if i.users == 0: bpy.data.images.remove(i)
bpy.ops.wm.save_as_mainfile(filepath=os.environ["VDW_SAVE_TO"])
print("SAVED", os.environ["VDW_SAVE_TO"])
