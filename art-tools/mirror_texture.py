# Repairs one side of a symmetric model's textures from the other side: every texel on the bad side (by its position on
# the mesh) takes the texture at the mirror-image point on the good side (nearest surface point to (-x, y, z)).
# Colour-type maps are copied; the tangent-space normal map is mirrored properly (to object space, x flipped, back to
# the bad texel's own tangent frame). A soft band at the midline blends the two. Writes NEW files (never overwrites).
#   blender -b --python mirror_texture.py -- <model.fbx/.glb> <out_dir> <suffix> <bad: +x|-x> <map.png> [map.png ...]
#   maps whose name contains "Normal" are treated as normal maps. env: VDW_RES (work resolution, default = map size),
#   VDW_MIRROR_AXIS (x), VDW_BLEND (midline band, share of the half-width, 0.08)
import bpy, os, sys, math
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
a = sys.argv[sys.argv.index("--") + 1:]
model, out_dir, suffix, bad = a[0], a[1], a[2], a[3]; maps = a[4:]
AX = "xyz".index(os.environ.get("VDW_MIRROR_AXIS", "x")); BLEND = float(os.environ.get("VDW_BLEND", "0.08"))
bad_s = 1.0 if bad.startswith("+") else -1.0
PROJECT = os.environ.get("VDW_MIRROR_MODE", "project") == "project"   # "nearest" = old behaviour
bpy.ops.wm.read_factory_settings(use_empty=True)
if model.lower().endswith(".fbx"): bpy.ops.import_scene.fbx(filepath=model)
else: bpy.ops.import_scene.gltf(filepath=model)
ob = max((o for o in bpy.data.objects if o.type == 'MESH'), key=lambda o: len(o.data.vertices))
me = ob.data; me.calc_loop_triangles()
L_uv = np.array([d.uv[:] for d in me.uv_layers.active.data])      # read BEFORE calc_tangents (it reallocates the layer)
me.calc_tangents(uvmap=me.uv_layers.active.name)
co = np.array([v.co[:] for v in me.vertices])
half = float(np.abs(co[:, AX]).max())
tris = [(t.vertices[:], t.loops[:]) for t in me.loop_triangles]
bvh = BVHTree.FromPolygons([Vector(x) for x in co], [t[0] for t in tris], all_triangles=True)
L_tan = np.array([l.tangent[:] for l in me.loops]); L_bs = np.array([l.bitangent_sign for l in me.loops]); L_nrm = np.array([l.normal[:] for l in me.loops])
def load(path):
    im = bpy.data.images.load(path); im.colorspace_settings.name = 'Non-Color'
    W, H = im.size; px = np.empty(W * H * 4, np.float32); im.pixels.foreach_get(px); return im, px.reshape(H, W, 4)
ims = [load(p) for p in maps]
H, W = ims[0][1].shape[:2]
RES = int(os.environ.get("VDW_RES", str(W)))
print(f"  model {ob.name}: {len(me.polygons)} faces, half width {half:.3f}; maps {W}x{H}, working at {RES}")
# ---- rasterise: texel -> mesh position + tangent frame
pos = np.zeros((RES, RES, 3), np.float32); tan = np.zeros_like(pos); nrm = np.zeros_like(pos); bsg = np.ones((RES, RES), np.float32)
cov = np.zeros((RES, RES), bool)
for vi, li in tris:
    uv = L_uv[list(li)] * RES; P3 = co[list(vi)]
    x0, y0 = np.maximum(np.floor(uv.min(0)).astype(int) - 1, 0); x1, y1 = np.minimum(np.ceil(uv.max(0)).astype(int) + 1, RES - 1)
    if x1 < x0 or y1 < y0: continue
    xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
    (ax, ay), (bx, by), (cx, cy) = uv; den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
    if abs(den) < 1e-12: continue
    l1 = ((by - cy) * (xs - cx) + (cx - bx) * (ys - cy)) / den; l2 = ((cy - ay) * (xs - cx) + (ax - cx) * (ys - cy)) / den; l3 = 1 - l1 - l2
    ins = (l1 >= -0.01) & (l2 >= -0.01) & (l3 >= -0.01)
    if not ins.any(): continue
    yy, xx = (ys[ins] - 0.5).astype(int), (xs[ins] - 0.5).astype(int)
    w = np.stack([l1[ins], l2[ins], l3[ins]], 1)
    pos[yy, xx] = w @ P3; tan[yy, xx] = w @ L_tan[list(li)]; nrm[yy, xx] = w @ L_nrm[list(li)]; bsg[yy, xx] = L_bs[li[0]]; cov[yy, xx] = True
print(f"  {int(cov.sum())} texels on the mesh")
# ---- which texels to repair, and where their mirror image lands
side = pos[..., AX] * bad_s
fix = cov & (side > -BLEND * half)
wt = np.clip((side + BLEND * half) / (2 * BLEND * half), 0, 1); wt = wt * wt * (3 - 2 * wt)       # 0 at the good edge of the band .. 1 inside
ys_, xs_ = np.nonzero(fix)
src_uv = np.zeros((len(ys_), 2), np.float32); src_tan = np.zeros((len(ys_), 3), np.float32); src_nrm = np.zeros_like(src_tan); src_bs = np.ones(len(ys_), np.float32)
ok = np.zeros(len(ys_), bool)
for k, (y, x) in enumerate(zip(ys_, xs_)):
    p = Vector(pos[y, x]); p[AX] = -p[AX]
    ti = None
    if PROJECT and abs(pos[y, x][AX]) > 0.15 * half:
        # look straight across from outside the good side at the same height / place along the fish (models are
        # rarely exactly symmetric, and nearest points scramble the pattern where the two sides differ)
        o = Vector(p); o[AX] = -bad_s * half * 3; dvec = Vector((0, 0, 0)); dvec[AX] = bad_s
        loc, n_, ti, d = bvh.ray_cast(o, dvec)
        if ti is not None and loc[AX] * bad_s > 0: ti = None          # went through to the bad side
    if ti is None:
        loc, n_, ti, d = bvh.find_nearest(p)
    if ti is None: continue
    vi, li = tris[ti]; A, B, C = (Vector(co[i]) for i in vi)
    v0, v1, v2 = B - A, C - A, loc - A
    d00, d01, d11, d20, d21 = v0.dot(v0), v0.dot(v1), v1.dot(v1), v2.dot(v0), v2.dot(v1); dn = d00 * d11 - d01 * d01
    if abs(dn) < 1e-20: continue
    w1 = (d11 * d20 - d01 * d21) / dn; w2 = (d00 * d21 - d01 * d20) / dn; w = np.array([1 - w1 - w2, w1, w2])
    src_uv[k] = w @ L_uv[list(li)]; src_tan[k] = w @ L_tan[list(li)]; src_nrm[k] = w @ L_nrm[list(li)]; src_bs[k] = L_bs[li[0]]; ok[k] = True
print(f"  {len(ys_)} texels to repair ({int(ok.sum())} found a mirror point)")
def unit(v): return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-9)
os.makedirs(out_dir, exist_ok=True)
for (im, px), path in zip(ims, maps):
    is_n = "normal" in os.path.basename(path).lower()
    fx = np.clip(src_uv[:, 0] * W - 0.5, 0, W - 1.001); fy = np.clip(src_uv[:, 1] * H - 0.5, 0, H - 1.001)   # bilinear
    x0_, y0_ = fx.astype(int), fy.astype(int); ax_, ay_ = (fx - x0_)[:, None], (fy - y0_)[:, None]
    sample = (px[y0_, x0_] * (1 - ax_) * (1 - ay_) + px[y0_, x0_ + 1] * ax_ * (1 - ay_)
              + px[y0_ + 1, x0_] * (1 - ax_) * ay_ + px[y0_ + 1, x0_ + 1] * ax_ * ay_)
    if is_n:   # tangent space at the good point -> object space -> mirror -> tangent space at the bad texel
        ts = sample[:, :3] * 2 - 1
        T = unit(src_tan); N = unit(src_nrm); Bt = np.cross(N, T) * src_bs[:, None]
        obj = T * ts[:, :1] + Bt * ts[:, 1:2] + N * ts[:, 2:3]; obj[:, AX] *= -1
        T2 = unit(tan[ys_, xs_]); N2 = unit(nrm[ys_, xs_]); B2 = np.cross(N2, T2) * bsg[ys_, xs_][:, None]
        ts2 = np.stack([(obj * T2).sum(1), (obj * B2).sum(1), (obj * N2).sum(1)], 1)
        sample[:, :3] = unit(ts2) * 0.5 + 0.5
    # the repair is built on the work grid, scaled up to the map, and laid over the original: the good side keeps
    # every original pixel
    rep = np.zeros((RES, RES, 4), np.float32); wgt = np.zeros((RES, RES), np.float32)
    rep[ys_[ok], xs_[ok], :3] = sample[ok, :3]; rep[..., 3] = 1; wgt[ys_[ok], xs_[ok]] = wt[ys_, xs_][ok]
    if RES != W:
        def up(arr, ch):
            t_ = bpy.data.images.new("up_tmp", RES, RES, alpha=True); t_.colorspace_settings.name = 'Non-Color'
            a4 = np.ones((RES, RES, 4), np.float32); a4[..., :ch] = arr.reshape(RES, RES, ch)
            t_.pixels.foreach_set(a4.ravel()); t_.scale(W, H)
            b4 = np.empty(W * H * 4, np.float32); t_.pixels.foreach_get(b4); bpy.data.images.remove(t_); return b4.reshape(H, W, 4)[..., :ch]
        rep_u = up(rep[..., :3], 3); w_u = up(wgt[..., None], 1)
    else:
        rep_u, w_u = rep[..., :3], wgt[..., None]
    out = px.copy(); out[..., :3] = px[..., :3] * (1 - w_u) + rep_u * w_u
    name = os.path.splitext(os.path.basename(path))[0] + f"_{suffix}.png"; dst = os.path.join(out_dir, name)
    if os.path.exists(dst): raise RuntimeError("refusing to overwrite " + dst)
    ni = bpy.data.images.new(name, W, H, alpha=True); ni.colorspace_settings.name = 'Non-Color'
    ni.pixels.foreach_set(out.ravel()); ni.filepath_raw = dst; ni.file_format = 'PNG'; ni.save()
    print(f"  saved {dst}{' (normal map, mirrored in object space)' if is_n else ''}")
