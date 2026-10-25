# Builds the terminal tackle (Tackle.json: weights and the leader), each a small static model with its own painted
# Unity maps (Albedo, MetallicSmoothness, Normal from a height map). Shown a little larger than life, like the hooks,
# so they read on the ground and in hand:
#   tackle_split_shot      Split Shot      - dull lead shot, each with its pinch slit: three on a length of line, two loose
#   tackle_bullet_weight   Bullet Weight   - a copper cone with a hole through the nose, a little patina
#   tackle_egg_sinker      Egg Sinker      - a hammered bronze egg, holed at both ends
#   tackle_pyramid_sinker  Pyramid Sinker  - a four-sided iron pyramid, rust in the corners, a wire eye on top
#   tackle_leader          Leader Line     - a small wooden spool wound with pale leader line, the end trailing off
# Writes <out>/Models/<key>.fbx, <out>/Textures/<key>/<key>_Unity_*.png, <out>/Blender Files/tackle.blend,
# <out>/Previews/<key>.png. Existing maps / models are kept (never overwritten) unless VDW_REDO=1.
#   env: VDW_OUT (folder), VDW_ONLY (comma list of keys, optional), VDW_REDO, VDW_RENDER=1 for previews
import bpy, bmesh, math, os
import numpy as np
from mathutils import Matrix, Vector

OUT = os.environ["VDW_OUT"]; N = 512
ONLY = set(filter(None, os.environ.get("VDW_ONLY", "").split(",")))
REDO = os.environ.get("VDW_REDO") == "1"
for d in ("Models", "Textures", "Blender Files", "Previews"): os.makedirs(os.path.join(OUT, d), exist_ok=True)
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
sc = bpy.context.scene
rng = np.random.default_rng(23)

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

def write_maps(key, alb, metal, smooth_, height, bump=6.0):
    d = os.path.join(OUT, "Textures", key); os.makedirs(d, exist_ok=True); p = lambda k: os.path.join(d, f"{key}_Unity_{k}.png")
    ms = np.zeros((N, N, 4), np.float32); ms[..., :3] = np.asarray(metal)[..., None] if np.ndim(metal) else metal; ms[..., 3] = smooth_
    gx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * bump; gy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * bump
    n = np.stack([-gx, -gy, np.ones_like(gx)], -1); n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return {"Albedo": save(np.clip(alb, 0, 1), p("Albedo")), "MetallicSmoothness": save(np.clip(ms, 0, 1), p("MetallicSmoothness"), True),
            "Normal": save(n * 0.5 + 0.5, p("Normal"), True)}

# ---------------------------------------------------------------- mesh helpers
def tube(path, radius, ring=14, flat=1.0):
    """A tube along `path` (list of Vectors), radius(t) for t in 0..1, capped; UV u round, v along."""
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
        c = bm.verts.new((path[0] if end == 0 else path[-1]) + step.normalized() * radius(end) * 0.3)
        for k in range(ring):
            vs = (ring_[(k + 1) % ring], ring_[k], c) if end == 0 else (ring_[k], ring_[(k + 1) % ring], c)
            f = bm.faces.new(vs)
            for l in f.loops: l[uvl].uv = (k / ring, v_)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free(); return me

def curve(fn, n=64): return [fn(i / n) for i in range(n + 1)]
def lathe(profile, height, ring=24, n=32):
    """A round body along +Z: radius profile(t) for t 0 (base) .. 1 (top). UV u round, v up."""
    return tube(curve(lambda t: Vector((0, 0, height * t)), n), profile, ring=ring)

def remap_uv(me, u0, u1, v0, v1):
    """Squeezes a mesh's whole UV square into a part of the texture (so pieces share one map)."""
    if len(me.uv_layers):
        for l in (me.uv_layers.active or me.uv_layers[0]).data: l.uv = (u0 + l.uv[0] * (u1 - u0), v0 + l.uv[1] * (v1 - v0))
        return
    # Blender 5: a bmesh UV layer comes through as a plain corner attribute
    for d in me.attributes["UVMap"].data: d.vector = (u0 + d.vector[0] * (u1 - u0), v0 + d.vector[1] * (v1 - v0))

def sphere(r, seg=18, rings=12):
    me = bpy.data.meshes.new("sp"); bm = bmesh.new(); bm.loops.layers.uv.new("UVMap")   # calc_uvs needs a layer to fill
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=r, calc_uvs=True)
    bm.to_mesh(me); bm.free(); return me

def join(parts):
    """One mesh from (mesh, matrix) parts; the source meshes are removed."""
    bm = bmesh.new()
    for me, mx in parts:
        me.transform(mx); bm.from_mesh(me); bpy.data.meshes.remove(me)
    out = bpy.data.meshes.new("j"); bm.to_mesh(out); bm.free(); return out

def M(loc=(0, 0, 0), rot=(0, 0, 0), s=1.0):
    r = Matrix.Rotation(rot[2], 4, "Z") @ Matrix.Rotation(rot[1], 4, "Y") @ Matrix.Rotation(rot[0], 4, "X")
    sm = Matrix.Diagonal((*s, 1.0)) if isinstance(s, tuple) else Matrix.Scale(s, 4)
    return Matrix.Translation(Vector(loc)) @ r @ sm

ITEMS = {}
def item(key):
    def reg(fn): ITEMS[key] = fn; return fn
    return reg

# ---------------------------------------------------------------- the items

@item("tackle_split_shot")
def split_shot():
    # lead shot (left 85% of the map) and the line (right strip). Each shot's slit runs along one meridian (u near 0/1).
    parts = []
    line = tube(curve(lambda t: Vector((-0.035 + 0.07 * t, 0.004 * math.sin(t * 3.2), 0.0)), 24), lambda t: 0.0009, ring=8)
    remap_uv(line, 0.88, 1.0, 0.0, 1.0); parts.append((line, M()))
    for x in (-0.018, 0.0, 0.017):                                   # pinched on the line
        me = sphere(0.0065); remap_uv(me, 0.0, 0.85, 0.0, 1.0)
        parts.append((me, M((x, 0.004 * math.sin((x + 0.035) / 0.07 * 3.2), 0.0), (0, 0, 1.5708), (1.0, 1.0, 0.92))))
    for loc, rot in (((0.006, 0.022, -0.002), (0.4, 0.2, 0.9)), ((-0.026, -0.018, -0.002), (1.1, 0.3, 2.2))):   # two loose
        me = sphere(0.0062); remap_uv(me, 0.0, 0.85, 0.0, 1.0); parts.append((me, M(loc, rot, (1.0, 1.0, 0.92))))
    me = join(parts)
    n = fbm(48, 16, 6); u = U / 0.85
    slit = np.where(U < 0.85, smooth(0.035, 0.0, np.minimum(np.abs(u - 0.0), np.abs(u - 1.0))), 0.0)
    oxide = smooth(0.62, 0.8, fbm(24, 8))                            # white lead bloom in patches
    alb = mix((0.40, 0.42, 0.45), (0.30, 0.31, 0.34), n * 0.6)
    alb = mix(alb, (0.66, 0.67, 0.66), oxide * 0.55); alb = mix(alb, (0.10, 0.10, 0.11), slit * 0.9)
    linec = U >= 0.88; alb[linec] = (0.78, 0.82, 0.80)
    metal = np.where(linec, 0.0, 0.55 - 0.3 * oxide); sm = np.where(linec, 0.6, 0.38 - 0.15 * oxide)
    return me, write_maps("tackle_split_shot", alb, metal, sm, 0.4 * n - 0.8 * slit, 3.0)

@item("tackle_bullet_weight")
def bullet_weight():
    L = 0.05
    prof = lambda t: max(0.0016, 0.0115 * (1 - t ** 1.7) ** 0.62) if t < 0.995 else 0.0016
    me = lathe(prof, L, ring=28, n=40)
    n = fbm(40, 14, 5); streak = smooth(0.55, 0.85, fbm(64, 4))
    alb = mix((0.74, 0.44, 0.26), (0.52, 0.28, 0.16), n * 0.7)              # copper, darker where handled
    alb = mix(alb, (0.30, 0.52, 0.42), smooth(0.7, 0.9, fbm(20, 6)) * 0.45)   # a little verdigris
    alb = mix(alb, (0.36, 0.20, 0.12), streak * 0.4)
    hole = smooth(0.94, 0.985, V); base = smooth(0.03, 0.0, V)
    alb = mix(alb, (0.06, 0.04, 0.03), hole); alb = mix(alb, (0.40, 0.24, 0.15), base * 0.6)
    return me, write_maps("tackle_bullet_weight", alb, 0.85 - 0.4 * hole, 0.55 - 0.25 * n, 0.3 * n - 0.6 * hole, 3.0)

@item("tackle_egg_sinker")
def egg_sinker():
    L = 0.052
    prof = lambda t: max(0.0022, 0.0165 * math.sin(math.pi * t) ** 0.75 * (1 + 0.08 * (0.5 - t)))
    me = lathe(prof, L, ring=28, n=36)
    dents = vnoise(16) * 0.6 + vnoise(36) * 0.4                             # hammer marks
    n = fbm(32, 12, 5)
    alb = mix((0.68, 0.52, 0.30), (0.46, 0.33, 0.18), n * 0.7)              # bronze
    alb = mix(alb, (0.82, 0.66, 0.40), smooth(0.65, 0.85, dents) * 0.35)    # polished high spots
    ends = smooth(0.06, 0.015, np.minimum(V, 1 - V))
    alb = mix(alb, (0.07, 0.05, 0.03), ends)
    return me, write_maps("tackle_egg_sinker", alb, 0.85 - 0.5 * ends, 0.5 + 0.15 * dents, 0.6 * dents + 0.2 * n - 0.7 * ends, 4.0)

@item("tackle_pyramid_sinker")
def pyramid_sinker():
    S, H = 0.042, 0.05
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
    b = [bm.verts.new(Vector((sx * S / 2, sy * S / 2, 0))) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    top = bm.verts.new(Vector((0, 0, H)))
    for i in range(4):
        f = bm.faces.new((b[i], b[(i + 1) % 4], top))
        # each side gets a quarter of the map's lower 75%; the base the top band
        for l in f.loops:
            p = l.vert.co; side = (b[(i + 1) % 4].co - b[i].co).normalized()
            uu = 0.5 + p.dot(side) / S; l[uvl].uv = (i * 0.25 + 0.25 * max(0.0, min(1.0, uu)), 0.75 * p.z / H)
    f = bm.faces.new(b[::-1])
    for l in f.loops: l[uvl].uv = (0.5 + l.vert.co.x / S * 0.9, 0.875 + l.vert.co.y / S * 0.22)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.0018, segments=2, affect='EDGES')   # soft cast edges
    pm = bpy.data.meshes.new("pyr"); bm.to_mesh(pm); bm.free()
    eye = tube(curve(lambda t: Vector((0.0065 * math.sin(2 * math.pi * t), 0, H + 0.0055 - 0.0065 * math.cos(2 * math.pi * t))), 32),
               lambda t: 0.0012, ring=8)
    remap_uv(eye, 0.9, 1.0, 0.76, 0.99)
    me = join([(pm, M()), (eye, M())])
    n = fbm(40, 14, 5); rust = smooth(0.58, 0.78, fbm(24, 8))
    edge = smooth(0.06, 0.0, np.minimum((U * 4) % 1, 1 - (U * 4) % 1))      # rust gathers at the corners
    alb = mix((0.33, 0.34, 0.36), (0.22, 0.23, 0.25), n * 0.7)              # dark iron
    r = np.clip(rust + edge * 0.6, 0, 1)
    alb = mix(alb, (0.46, 0.25, 0.13), r * 0.75)
    wire = (U >= 0.9) & (V >= 0.76); alb[wire] = (0.55, 0.55, 0.56)
    return me, write_maps("tackle_pyramid_sinker", alb, np.where(wire, 0.9, 0.7 - 0.5 * r), np.where(wire, 0.6, 0.35 - 0.2 * r), 0.35 * n + 0.3 * r, 3.0)

@item("tackle_leader")
def leader():
    # one map: wood flanges (v < 0.14 and v > 0.86), the wound line between; the loose end uses the line part
    L = 0.034
    def prof(t):
        if t < 0.1 or t > 0.9: return 0.018                            # flanges
        if t < 0.14 or t > 0.86: return 0.0105                         # the core showing at the edges of the winding
        return 0.0135 + 0.0006 * math.sin(t * 60)                      # the wound line, bumpy
    me = lathe(prof, L, ring=32, n=60)
    end = tube(curve(lambda t: Vector((0.0135 + 0.03 * t, -0.004 - 0.02 * t * t, L * (0.5 - 0.25 * t))), 24), lambda t: 0.0007, ring=6)
    remap_uv(end, 0.0, 1.0, 0.3, 0.7)
    me = join([(me, M()), (end, M())])
    wood = (V < 0.14) | (V > 0.86)
    grain = 0.5 + 0.5 * np.sin(U * 80 + 6 * vnoise(24))
    walb = mix((0.52, 0.36, 0.21), (0.38, 0.25, 0.14), grain * 0.6 + 0.4 * fbm(32, 8))
    wraps = 0.5 + 0.5 * np.sin(V * 900 + 3 * vnoise(48))                # the turns of line
    lalb = mix((0.80, 0.86, 0.88), (0.62, 0.70, 0.74), wraps * 0.5)     # pale fluorocarbon
    alb = np.where(wood[..., None], walb, lalb)
    return me, write_maps("tackle_leader", alb, 0.0, np.where(wood, 0.25, 0.7), np.where(wood, 0.4 * grain, 0.5 * wraps), 3.0)

# ---------------------------------------------------------------- build, material, export
def material(key, imgs):
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
    Nn.active = a; return m

print("\n===== TACKLE =====")
objs = []
for key, fn in ITEMS.items():
    if ONLY and key not in ONLY: continue
    me, imgs = fn(); me.name = key
    c = np.array([v.co[:] for v in me.vertices]); me.transform(Matrix.Translation(-Vector(((c.min(0) + c.max(0)) / 2).tolist())))
    me.materials.append(material(key, imgs))
    for p in me.polygons: p.use_smooth = True
    ob = bpy.data.objects.new(key, me); sc.collection.objects.link(ob); objs.append(ob)
    path = os.path.join(OUT, "Models", key + ".fbx")
    size = c.max(0) - c.min(0)
    if os.path.exists(path) and not REDO: print(f"  {key}: exists, kept {path}"); continue
    for o in bpy.data.objects: o.select_set(o is ob)
    bpy.context.view_layer.objects.active = ob
    tri = ob.modifiers.new("vdw_tri", 'TRIANGULATE'); tri.quad_method = 'BEAUTY'     # Unity drops twisted quads otherwise
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={'MESH'}, global_scale=1.0, apply_unit_scale=True,
                             apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y', bake_space_transform=True,
                             mesh_smooth_type='FACE', use_mesh_modifiers=True, bake_anim=False, path_mode='COPY', embed_textures=True)
    ob.modifiers.remove(tri)
    print(f"  {key}: {len(me.vertices)} verts, size {tuple((size * 100).round(1))} cm -> {os.path.basename(path)}")
x = 0.0
for ob in objs: ob.location = (x, 0, 0); x += 0.1
blend = os.path.join(OUT, "Blender Files", "tackle.blend" if not ONLY else "tackle_part.blend")
if not os.path.exists(blend) or REDO or ONLY: bpy.ops.wm.save_as_mainfile(filepath=blend)

if os.environ.get("VDW_RENDER") == "1":
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 48; sc.view_settings.view_transform = 'Standard'
    wd = bpy.data.worlds.new("w"); wd.use_nodes = True; sc.world = wd; wd.node_tree.nodes["Background"].inputs[0].default_value = (0.32, 0.33, 0.36, 1)
    ld = bpy.data.lights.new("key", 'SUN'); ld.energy = 3.5; lo = bpy.data.objects.new("key", ld); sc.collection.objects.link(lo); lo.rotation_euler = (0.6, 0.2, 0.8)
    cd = bpy.data.cameras.new("C"); cd.type = 'ORTHO'; cam = bpy.data.objects.new("C", cd); sc.collection.objects.link(cam); sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = 500, 500
    for ob in objs:
        for o in objs: o.hide_render = o is not ob
        c = np.array([ob.matrix_world @ v.co for v in ob.data.vertices]); tgt = Vector(((c.min(0) + c.max(0)) / 2).tolist())
        cd.ortho_scale = float((c.max(0) - c.min(0)).max()) * 1.4
        cam.location = tgt + Vector((0.5, -0.6, 0.65)).normalized() * 0.5; cam.rotation_euler = (tgt - cam.location).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = os.path.join(OUT, "Previews", ob.name + ".png"); bpy.ops.render.render(write_still=True)
print("===== END =====")
