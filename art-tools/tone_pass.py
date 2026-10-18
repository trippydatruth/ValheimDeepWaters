# Valheim tone pass for albedo maps (roadmap #11). Valheim's own textures are darker, softer and lower in contrast than
# ours (style audit, 2026-10-18: median brightness 0.35 vs our 0.49, half our fine detail). Per map:
#   - brightness pulled toward VDW_TARGET (0.38, median of the painted texels), never darkened more than VDW_MAX_DARK
#     (0.35) and never brightened
#   - contrast eased toward the map's mean by VDW_CONTRAST (0.85 = keep 85%)
#   - the finest detail softened: VDW_SOFTEN (0.45) of a masked blur (radius = map width / 400) mixed in; the black
#     padding between UV islands is left out of the blur so island edges keep their colour
# Colours (hue, saturation) are kept. Always reads the ORIGINAL from VDW_BACKUP (copying it there the first time), so it can
# be re-run with new settings without stacking.
#   blender -b --python tone_pass.py -- <albedo.png> [<albedo.png> ...]    env: VDW_BACKUP (folder), the settings above
import bpy, os, sys, shutil
import numpy as np
files = sys.argv[sys.argv.index("--") + 1:]
BK = os.environ["VDW_BACKUP"]; os.makedirs(BK, exist_ok=True)
TARGET = float(os.environ.get("VDW_TARGET", "0.38")); MAXD = float(os.environ.get("VDW_MAX_DARK", "0.35"))
CON = float(os.environ.get("VDW_CONTRAST", "0.85")); SOFT = float(os.environ.get("VDW_SOFTEN", "0.45"))
def box(a, r, axis):
    c = np.cumsum(np.pad(a, [(r + 1, r) if i == axis else (0, 0) for i in range(a.ndim)], mode="edge"), axis=axis)
    n = a.shape[axis]
    return (np.take(c, range(2 * r + 1, 2 * r + 1 + n), axis=axis) - np.take(c, range(0, n), axis=axis)) / (2 * r + 1)
def blur(a, r):
    for _ in range(2):
        a = box(box(a, r, 0), r, 1)
    return a
# VDW_PIXEL (block size at a 2048 map, scaled to the map; 0 = off) / VDW_PIXEL_BLUR: the pixel-and-blur look. The UV islands
# come from the model FBX beside the map (the importer's <folder>_model.fbx), rasterised at the map's size.
PIX_ON = float(os.environ.get("VDW_PIXEL", "0")); PBLUR = float(os.environ.get("VDW_PIXEL_BLUR", "2.5"))
def islands(p, W, H):
    d = os.path.dirname(p); fb = os.path.join(d, os.path.basename(d) + "_model.fbx")
    if not os.path.exists(fb):
        c = [f for f in os.listdir(d) if f.lower().endswith(".fbx")]
        if not c: print("  no model for islands, pixel step skipped:", p); return None
        fb = os.path.join(d, c[0])
    for o in list(bpy.data.objects): bpy.data.objects.remove(o)
    bpy.ops.import_scene.fbx(filepath=fb)
    import bmesh
    isl = np.full((H, W), -1, np.int32); nid = 0
    for ob in [o for o in bpy.data.objects if o.type == 'MESH' and not o.name.lower().startswith("fitref")]:
        bm = bmesh.new(); bm.from_mesh(ob.data); uvl = bm.loops.layers.uv.active
        if uvl is None: bm.free(); continue
        bm.faces.ensure_lookup_table()
        # faces joined where they share an edge with the same UVs on both ends = one island
        parent = list(range(len(bm.faces)))
        def find(i):
            while parent[i] != i: parent[i] = parent[parent[i]]; i = parent[i]
            return i
        for e in bm.edges:
            lf = e.link_faces
            if len(lf) != 2: continue
            def uvs(f):
                return {l.vert.index: tuple(round(c, 5) for c in l[uvl].uv) for l in f.loops if l.vert in e.verts}
            if uvs(lf[0]) == uvs(lf[1]): parent[find(lf[0].index)] = find(lf[1].index)
        ids = {}
        for f in bm.faces:
            r_ = find(f.index); gid = ids.setdefault(r_, nid + len(ids))
            uv = np.array([l[uvl].uv[:] for l in f.loops]) * (W, H)
            for k in range(1, len(uv) - 1):
                tri = uv[[0, k, k + 1]]
                x0, y0 = np.maximum(np.floor(tri.min(0)).astype(int), 0); x1, y1 = np.minimum(np.ceil(tri.max(0)).astype(int), (W - 1, H - 1))
                if x1 < x0 or y1 < y0: continue
                xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
                (ax, ay), (bx, by), (cx, cy) = tri; den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
                if abs(den) < 1e-12: continue
                l1 = ((by - cy) * (xs - cx) + (cx - bx) * (ys - cy)) / den; l2 = ((cy - ay) * (xs - cx) + (ax - cx) * (ys - cy)) / den
                ins = (l1 >= -0.02) & (l2 >= -0.02) & (1 - l1 - l2 >= -0.02)
                isl[(ys[ins] - 0.5).astype(int), (xs[ins] - 0.5).astype(int)] = gid
        nid += len(ids); bm.free()
    # texels outside every island take the nearest island (grown out), so padding blocks stay with their neighbour
    for _ in range(16):
        e_ = isl < 0
        if not e_.any(): break
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nb = np.roll(np.roll(isl, dy, 0), dx, 1); fill = e_ & (nb >= 0); isl[fill] = nb[fill]; e_ = isl < 0
    return isl
def pixel_soft(a, isl, px, pblur):
    hh_, ww_ = isl.shape
    by_, bx_ = np.meshgrid(np.arange(hh_) // px, np.arange(ww_) // px, indexing='ij')
    block = (by_ * ((ww_ + px - 1) // px) + bx_).astype(np.int64)
    _, key = np.unique(block * (int(isl.max()) + 2) + (isl + 1), return_inverse=True); key = key.reshape(hh_, ww_)
    cnt = np.bincount(key.ravel()); out = np.empty_like(a)
    for ch in range(a.shape[2]): out[..., ch] = (np.bincount(key.ravel(), weights=a[..., ch].ravel()) / cnt)[key]
    for _ in range(max(1, int(round(pblur * 1.5)))):
        acc = out.copy(); n = np.ones((hh_, ww_, 1), np.float32)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            same = (np.roll(np.roll(isl, dy, 0), dx, 1) == isl)[..., None]
            acc += np.roll(np.roll(out, dy, 0), dx, 1) * same; n += same
        out = acc / n
    return out
for p in files:
    orig =os.path.join(BK, os.path.basename(os.path.dirname(p)) + "__" + os.path.basename(p))
    if not os.path.exists(orig): shutil.copy2(p, orig)
    im = bpy.data.images.load(orig, check_existing=False); W, H = im.size
    a = np.empty(W * H * 4, np.float32); im.pixels.foreach_get(a); a = a.reshape(H, W, 4); bpy.data.images.remove(im)
    rgb = a[..., :3].copy()
    m = rgb.max(-1) > 0.03
    if m.sum() < 100: print("  skipped (empty):", p); continue
    # soften: masked blur, mixed in
    r = max(1, W // 400)
    mf = m.astype(np.float32)
    bl = blur(rgb * mf[..., None], r) / np.maximum(blur(mf, r), 1e-4)[..., None]
    rgb = np.where(m[..., None], rgb * (1 - SOFT) + bl * SOFT, rgb)
    # contrast toward the map's mean colour
    mean = rgb[m].mean(0)
    rgb = np.where(m[..., None], mean + (rgb - mean) * CON, rgb)
    # brightness toward the target
    med = float(np.median(rgb.max(-1)[m]))
    k = 1.0 if med <= TARGET else max(1 - MAXD, TARGET / med)
    rgb = np.where(m[..., None], rgb * k, rgb)
    # Valheim look (as recolor_fish.py): pixelated into PIX-texel blocks, then a soft blur, both kept inside each UV island
    if PIX_ON:
        isl = islands(p, W, H)
        if isl is not None:
            px = max(2, int(round(W * PIX_ON / 2048)))
            rgb = np.where(m[..., None], pixel_soft(rgb, isl, px, PBLUR), rgb)
            print(f"  pixelated in {px}-texel blocks, blur {PBLUR}")
    a[..., :3] = np.clip(rgb, 0, 1)
    out = bpy.data.images.new("tone", W, H, alpha=True); out.pixels.foreach_set(a.ravel())
    out.filepath_raw = p; out.file_format = 'PNG'; out.save(); bpy.data.images.remove(out)
    print(f"  {os.path.basename(p)}: median {med:.2f} -> x{k:.2f}, contrast {CON}, soften {SOFT} (r {r})")
