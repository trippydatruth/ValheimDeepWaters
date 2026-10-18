# Turns the user's Tripo drying rack (Mesh/cleaning table/drying rack/Source) into the Drying Line piece:
#   - laid along X (front toward -Y), scaled to VDW_LENGTH metres long, origin at the middle of its base, feet at z 0
#   - every leg that stopped short of the ground is lengthened along its own axis until it reaches it
#   - the hanging fish are spread evenly along the bar (each with its line), the lines and hooks made thicker
#   - the fish repainted golden-brown and dried (luminance kept, a darker back), the rest of the texture left alone
#   - Unity maps at VDW_TEX (1024): piece_cleaning_ext3_Unity_Albedo / _MetallicSmoothness / _Normal
# env: VDW_R (the drying rack folder), VDW_LENGTH (2.3), VDW_TEX (1024)
import bpy, bmesh, math, os
import numpy as np
from mathutils import Matrix, Vector

R = os.environ["VDW_R"]; SRC = os.path.join(R, "Source"); NAME = "piece_cleaning_ext3"
LENGTH = float(os.environ.get("VDW_LENGTH", "2.3")); TEX = int(os.environ.get("VDW_TEX", "1024"))
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
bpy.ops.import_scene.fbx(filepath=next(os.path.join(SRC, f) for f in os.listdir(SRC) if f.lower().endswith(".fbx")))
ob = next(o for o in bpy.data.objects if o.type == 'MESH'); ob.name = NAME; ob.data.name = NAME
ob.data.transform(ob.matrix_world); ob.matrix_world = Matrix()
for o in [o for o in bpy.data.objects if o is not ob]: bpy.data.objects.remove(o)

me = ob.data
co = np.array([v.co[:] for v in me.vertices])
lo, hi = co.min(0), co.max(0)
if (hi[1] - lo[1]) > (hi[0] - lo[0]): me.transform(Matrix.Rotation(math.radians(90), 4, 'Z'))   # the bar along X
co = np.array([v.co[:] for v in me.vertices]); lo, hi = co.min(0), co.max(0)
s = LENGTH / (hi[0] - lo[0])
me.transform(Matrix.Scale(s, 4) @ Matrix.Translation(Vector((-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]))))

# ---------------------------------------------------------------- loose parts
bm = bmesh.new(); bm.from_mesh(me)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0005 * s)        # Tripo splits the mesh at every UV seam: weld it back into its real parts
bm.verts.ensure_lookup_table()
parts, seen = [], set()
for v in bm.verts:
    if v.index in seen: continue
    stack, part = [v], []
    seen.add(v.index)
    while stack:
        x = stack.pop(); part.append(x)
        for e in x.link_edges:
            y = e.other_vert(x)
            if y.index not in seen: seen.add(y.index); stack.append(y)
    parts.append(part)
H = max(v.co.z for v in bm.verts)
def info(part):
    p = np.array([v.co[:] for v in part]); c = p.mean(0); u, sv, vt = np.linalg.svd(p - c, full_matrices=False)
    axis = Vector(vt[0]); ext = p.max(0) - p.min(0)
    return p, c, axis, sv, ext
kinds = []
for part in parts:
    p, c, axis, sv, ext = info(part)
    length = float(np.ptp((p - c) @ np.array(axis[:])))
    thick = float(sv[1] / max(1, len(part)) ** 0.5) if len(sv) > 1 else 0.0
    if length > 0.35 * H and ext[0] < 0.15 * LENGTH or length > 0.5 * LENGTH: k = "pole"
    elif max(ext[0], ext[1]) < 0.02 * LENGTH and ext[2] > 0.04 * H: k = "line"        # thin and hanging: a line or hook
    elif len(part) > 100 and ext[2] > 0.15 * H and p[:, 2].min() > 0.2 * H: k = "fish"   # small pieces up by the bar are hook parts
    else: k = "other"
    kinds.append(k)
    if os.environ.get("VDW_DEBUG"): print(f"PART {k:5s} verts {len(part):4d} c {np.round(c, 2)} ext {np.round(ext, 2)} zmin {p[:, 2].min():.2f} axis {np.round(axis[:], 2)}")
print("PARTS", {k: kinds.count(k) for k in set(kinds)})

# ground the legs: a pole whose low end stops above the ground is stretched along its axis, about its top end
for part, k in zip(parts, kinds):
    if k != "pole": continue
    p, c, axis, sv, ext = info(part)
    if abs(axis.z) < 0.5: continue                          # a horizontal bar or brace
    if axis.z < 0: axis = -axis
    proj = [(v.co - Vector(c)).dot(axis) for v in part]
    top = max(proj); low = min(proj); zlow = min(v.co.z for v in part)
    if zlow < 0.01 or zlow > 0.45 * H: continue
    f = (top - low + zlow / axis.z) / (top - low)
    for v, t in zip(part, proj):
        v.co += axis * ((t - top) * (f - 1))                 # top stays, the rest stretches toward the ground
    print(f"  leg grounded: lifted {zlow:.3f} m, stretched x{f:.3f}")

# spread the fish along the bar, each taking everything hanging over it (its line, hook and the hook's top) with it
fish = [(part, info(part)[1]) for part, k in zip(parts, kinds) if k == "fish"]
hang = [(part, info(part)[1]) for part, k in zip(parts, kinds) if k in ("line", "other") and info(part)[1][2] > 0.5 * H and abs(info(part)[1][0]) < 0.38 * LENGTH]
if len(fish) > 1:
    fish.sort(key=lambda f: f[1][0])
    x0, x1 = fish[0][1][0], fish[-1][1][0]
    groups = {id(part): [] for part, _ in fish}
    for hp, hc in hang: groups[id(min(fish, key=lambda f: abs(f[1][0] - hc[0]))[0])].append(hp)
    for i, (part, c) in enumerate(fish):
        dx = x0 + (x1 - x0) * i / (len(fish) - 1) - c[0]
        for v in part: v.co.x += dx
        for hp in groups[id(part)]:
            for v in hp: v.co.x += dx
        print(f"  fish {i}: x {c[0]:.2f} -> {c[0] + dx:.2f} with {len(groups[id(part)])} hanging part(s)")
# lines and hooks: three times as thick (about their own axis)
for part, k in zip(parts, kinds):
    if k != "line": continue
    p, c, axis, sv, ext = info(part); c = Vector(c)
    for v in part:
        d = v.co - c; along = axis * d.dot(axis); v.co = c + along + (d - along) * 2.5

bm.to_mesh(me); me.update()
co = np.array([v.co[:] for v in me.vertices]); me.transform(Matrix.Translation(Vector((0, 0, -co[:, 2].min()))))
co = np.array([v.co[:] for v in me.vertices]); print("SIZE", (co.max(0) - co.min(0)).round(3))

# ---------------------------------------------------------------- maps: fish repainted dried, all at TEX
def load(key):
    f = next((os.path.join(SRC, n) for n in os.listdir(SRC) if key in n), None)
    if not f: return None
    im = bpy.data.images.load(f); im.scale(TEX, TEX)
    return np.array(im.pixels[:], dtype=np.float32).reshape(TEX, TEX, 4)
alb, met, nrm, rough = load("BaseColor"), load("Metallic"), load("Normal"), load("Roughness")
# which texels the fish cover: their UV triangles rasterised
mask = np.zeros((TEX, TEX), bool)
uvl = me.uv_layers.active.data; fish_verts = set(v.index for part, k in zip(parts, kinds) if k == "fish" for v in part)
for poly in me.polygons:
    if poly.vertices[0] not in fish_verts: continue
    uv = np.array([uvl[li].uv[:] for li in poly.loop_indices]) * (TEX - 1)
    for t in range(1, len(uv) - 1):
        a, b, c = uv[0], uv[t], uv[t + 1]
        x0, y0 = np.floor(np.minimum(np.minimum(a, b), c)).astype(int); x1, y1 = np.ceil(np.maximum(np.maximum(a, b), c)).astype(int)
        x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, TEX - 1), min(y1, TEX - 1)
        if x1 < x0 or y1 < y0: continue
        yy, xx = np.mgrid[y0:y1 + 1, x0:x1 + 1]
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(d) < 1e-9: continue
        l1 = ((b[1] - c[1]) * (xx - c[0]) + (c[0] - b[0]) * (yy - c[1])) / d
        l2 = ((c[1] - a[1]) * (xx - c[0]) + (a[0] - c[0]) * (yy - c[1])) / d
        inside = (l1 >= -0.02) & (l2 >= -0.02) & (l1 + l2 <= 1.04)
        mask[yy[inside], xx[inside]] = True
# grow the mask a few texels so no grey seam shows at the island edges
for _ in range(3):
    m = mask.copy(); m[1:] |= mask[:-1]; m[:-1] |= mask[1:]; m[:, 1:] |= mask[:, :-1]; m[:, :-1] |= mask[:, 1:]; mask = m
lum = (alb[..., :3] @ np.array([0.3, 0.59, 0.11]))[..., None]
# the fins are loose little parts: also take any light, unsaturated (silver) texel - the bark is brown, the hooks dark
sat = alb[..., :3].max(-1) - alb[..., :3].min(-1)
mask |= (sat < 0.12) & (lum[..., 0] > 0.32)
gold, dark = np.array([0.86, 0.58, 0.24]), np.array([0.30, 0.17, 0.07])
dried = dark * (1 - np.clip(lum * 1.3, 0, 1)) + gold * np.clip(lum * 1.3, 0, 1)
alb[..., :3] = np.where(mask[..., None], dried, alb[..., :3])
print(f"  fish texels repainted: {mask.mean() * 100:.1f}% of the map")
TEXD = os.path.join(R, "Textures"); os.makedirs(TEXD, exist_ok=True)
def save(arr, kind, nc=False):
    im = bpy.data.images.new(kind, TEX, TEX, alpha=True)
    if nc: im.colorspace_settings.name = 'Non-Color'
    im.pixels.foreach_set(np.clip(arr, 0, 1).ravel()); p = os.path.join(TEXD, f"{NAME}_Unity_{kind}.png")
    im.filepath_raw = p; im.file_format = 'PNG'; im.save(); print("MAP", os.path.basename(p)); return im
ia = save(alb, "Albedo")
ms = np.zeros((TEX, TEX, 4), np.float32)
ms[..., 0] = met[..., 0] if met is not None else 0.0
ms[..., 3] = 1 - (rough[..., 0] if rough is not None else 0.8)
save(ms, "MetallicSmoothness", True)
if nrm is not None: save(nrm, "Normal", True)
mat = bpy.data.materials.new(NAME); mat.use_nodes = True
t = mat.node_tree.nodes.new("ShaderNodeTexImage"); t.image = ia; mat.node_tree.links.new(t.outputs["Color"], mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
me.materials.clear(); me.materials.append(mat)
os.makedirs(os.path.join(R, "Blender Files"), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(R, "Blender Files", NAME + ".blend")); print("SAVED")
