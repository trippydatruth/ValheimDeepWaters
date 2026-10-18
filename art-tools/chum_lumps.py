# Replaces the whole bait fish in a chum bucket with chum: a heap of irregular lumps and chunks (ground fish, scraps)
# piled in the liquid and poking up through it, with small bits floating on the surface. The "fish" object goes; a
# "chunks" object takes its place with its own painted maps (chunks_Unity_*) in VDW_TEX_OUT.
#   blender -b chum_<tier>.blend --python chum_lumps.py
#   env: VDW_SAVE_TO, VDW_TEX_OUT, VDW_TINT (basic | blood | blubber - the meat's colour), VDW_COUNT (lumps, 26)
import bpy, bmesh, math, os
import numpy as np
from mathutils import Matrix, Vector, noise
TINT = os.environ.get("VDW_TINT", "basic"); OUT = os.environ["VDW_TEX_OUT"]; os.makedirs(OUT, exist_ok=True)
for o in [o for o in bpy.data.objects if o.name.lower().startswith("fish")]: bpy.data.objects.remove(o)
liq = next(o for o in bpy.data.objects if o.name.lower().startswith("liquid"))
lc = np.array([(liq.matrix_world @ v.co)[:] for v in liq.data.vertices])
LIQ = float(np.median(lc[:, 2])); R = float(np.hypot(lc[:, 0], lc[:, 1]).max()) * 0.86
rng = np.random.default_rng(11)
def lump(c, size, flat, seed):
    """An icosphere pushed about by noise into a ragged chunk, flattened a little, turned at random."""
    me = bpy.data.meshes.new("l"); bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
    off = Vector((seed * 3.1, seed * 1.7, seed * 2.3))
    for v in bm.verts:
        n1 = noise.noise(v.co * 1.6 + off); n2 = noise.noise(v.co * 4.0 + off * 2)
        v.co *= 1 + 0.6 * n1 + 0.22 * n2
        v.co.z *= flat
    uvl = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:                                 # box-ish projection; the texture is all-over meat, seams don't show
        n = f.normal; ax = max(range(3), key=lambda i: abs(n[i]))
        for l in f.loops:
            p = l.vert.co; a, b = [p[i] for i in range(3) if i != ax]
            l[uvl].uv = (0.5 + a * 0.35 + seed * 0.13 % 1, 0.5 + b * 0.35 + seed * 0.29 % 1)
    rot = Matrix.Rotation(rng.uniform(0, 6.28), 4, 'Z') @ Matrix.Rotation(rng.uniform(-0.6, 0.6), 4, 'X')
    bm.transform(Matrix.Translation(c) @ rot @ Matrix.Diagonal((size, size * rng.uniform(0.7, 1.2), size, 1)))
    bm.to_mesh(me); bm.free(); return me
N = int(os.environ.get("VDW_COUNT", "40")); parts = []
for i in range(N):
    a = rng.uniform(0, 2 * math.pi); r = R * math.sqrt(rng.uniform(0, 1))
    big = i < N * 0.45
    size = rng.uniform(0.022, 0.034) if big else rng.uniform(0.009, 0.018)
    # the heap rises in the middle: big lumps sit higher there, small bits float at the surface all round
    dz = (0.022 * (1 - r / R) + rng.uniform(-0.006, 0.01)) if big else rng.uniform(-0.002, 0.004)
    parts.append(lump(Vector((r * math.cos(a), r * math.sin(a), LIQ + dz)), size, rng.uniform(0.4, 0.7), i + 1))
me = bpy.data.meshes.new("chunks"); bm = bmesh.new()
for m in parts: bm.from_mesh(m); bpy.data.meshes.remove(m)
bm.to_mesh(me); bm.free()
ob = bpy.data.objects.new("chunks", me); bpy.context.scene.collection.objects.link(ob)
for p in ob.data.polygons: p.use_smooth = True
# maps: wet ground meat - the tier's colour mottled darker and lighter, pale gristle and bone flecks, a few silver skin bits
Nn = 256; yy, xx = np.mgrid[0:Nn, 0:Nn] / Nn
def vn(scale):
    g = rng.random((scale + 2, scale + 2)); X, Y = xx * scale, yy * scale; x0, y0 = X.astype(int), Y.astype(int); fx, fy = X - x0, Y - y0
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    return g[y0, x0] * (1 - fx) * (1 - fy) + g[y0, x0 + 1] * fx * (1 - fy) + g[y0 + 1, x0] * (1 - fx) * fy + g[y0 + 1, x0 + 1] * fx * fy
base, dark = {"basic": ((0.55, 0.36, 0.30), (0.30, 0.17, 0.13)), "blood": ((0.50, 0.10, 0.09), (0.22, 0.03, 0.03)),
              "blubber": ((0.78, 0.62, 0.50), (0.45, 0.30, 0.24))}[TINT]
m1 = 0.5 * vn(4) + 0.3 * vn(12) + 0.2 * vn(30)
col = np.array(base) * m1[..., None] + np.array(dark) * (1 - m1[..., None])
fl = np.clip((vn(22) - 0.86) * 8, 0, 1)[..., None] * 0.6; col = col * (1 - fl) + np.array([0.80, 0.70, 0.60]) * fl     # sparse soft gristle                # gristle / bone
skin = (np.clip((vn(10) - 0.84) * 6, 0, 1)[..., None] * 0.7) if TINT != "blood" else np.zeros_like(fl)
col = col * (1 - skin) + np.array([0.60, 0.63, 0.66]) * skin                                                      # silver skin
def save(px, name, nc=False):
    im = bpy.data.images.new(name, Nn, Nn, alpha=True)
    if nc: im.colorspace_settings.name = 'Non-Color'
    a = np.ones((Nn, Nn, 4), np.float32); a[..., :px.shape[-1]] = px
    im.pixels.foreach_set(a.ravel()); p = os.path.join(OUT, name + ".png"); im.filepath_raw = p; im.file_format = 'PNG'; im.save(); return im
alb = save(col, "chunks_Unity_Albedo")
ms = np.zeros((Nn, Nn, 4), np.float32); ms[..., 3] = 0.55 + 0.25 * m1 + 0.2 * skin[..., 0]; save(ms, "chunks_Unity_MetallicSmoothness", True)
mat = bpy.data.materials.new("chunks"); mat.use_nodes = True; nt = mat.node_tree
t = nt.nodes.new("ShaderNodeTexImage"); t.image = alb; nt.links.new(t.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
ob.data.materials.append(mat)
print(f"  {N} lumps in the {TINT} chum (liquid at z {LIQ:.3f}, radius {R:.3f}), {len(ob.data.polygons)} faces")
bpy.ops.wm.save_as_mainfile(filepath=os.environ["VDW_SAVE_TO"]); print("  saved", os.environ["VDW_SAVE_TO"])
