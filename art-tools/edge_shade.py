# Shades the edges of a painted-on gear piece (bake_shirt_paint.py colour: alpha = where the cloth is), so each piece
# has a defined edge and stands off what's beside it (the coat's hem and cuffs over the overalls, the bib and straps
# over the shirt). The colour darkens toward the cloth's real edges, measured over the body's surface (in 3D), so the
# body texture's UV seams, where the cloth carries on across the cut, aren't shaded.
#   blender -b --factory-startup --python edge_shade.py
#   env: VDW_BODY_OBJ  body.obj from "vdw_debug paint dump"
#        VDW_TEX       the painted colour (.png, RGBA); its _nrm.png is copied alongside unchanged
#        VDW_OUT       output folder (new; never overwrites), VDW_NAME new texture name
#        VDW_EDGE_CM   how far in from the edge the shading reaches (default 3.5)
#        VDW_EDGE_DARK how dark right at the edge (0..1, default 0.45 = 45% darker)
#        VDW_OTHER_GR  green/red ratio (e.g. 0.8): cloth with less green than that for its red (the overalls' brown
#                      boots, not the yellow) is another part: the yellow is shaded where it meets it, the boots aren't
#        VDW_SKIP_UV   "u,v;..." body islands whose edges aren't cloth edges (e.g. the overalls' cleared arms 0.43,0.62)
import bpy, os, shutil
import numpy as np
from mathutils.kdtree import KDTree

BODY, TEX, OUT, NAME = (os.environ[k] for k in ("VDW_BODY_OBJ", "VDW_TEX", "VDW_OUT", "VDW_NAME"))
EDGE = float(os.environ.get("VDW_EDGE_CM", "3.5")) / 100; DARK = float(os.environ.get("VDW_EDGE_DARK", "0.45"))
out_png = os.path.join(OUT, NAME + ".png")
if os.path.exists(out_png): raise SystemExit("exists, kept: " + out_png)
bpy.ops.wm.obj_import(filepath=BODY)
me = [o for o in bpy.context.selected_objects if o.type == 'MESH'][0].data
V = np.array([v.co[:] for v in me.vertices]); uvl = me.uv_layers.active.data
img = bpy.data.images.load(TEX); n = img.size[0]
px = np.array(img.pixels[:], np.float32).reshape(n, n, 4)
# body units per metre: the body is about 1.85 m tall
unit = (V.max(0) - V.min(0)).max() / 1.85

# each texel's place on the body (both mirrored halves share the texture: one half is enough)
pos = np.zeros((n, n, 3), np.float32); has = np.zeros((n, n), bool); isl = np.full((n, n), -1, np.int32)
for p in me.polygons:
    vi = list(p.vertices); li = list(p.loop_indices)
    for k in range(1, len(vi) - 1):
        a, b, c = (np.array(uvl[li[t]].uv[:]) * n for t in (0, k, k + 1)); A, B, C = (V[vi[t]] for t in (0, k, k + 1))
        x0, x1 = int(max(0, min(a[0], b[0], c[0]))), int(min(n - 1, max(a[0], b[0], c[0]) + 1))
        y0, y1 = int(max(0, min(a[1], b[1], c[1]))), int(min(n - 1, max(a[1], b[1], c[1]) + 1))
        X, Y = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(d) < 1e-12: continue
        l1 = ((b[1] - c[1]) * (X - c[0]) + (c[0] - b[0]) * (Y - c[1])) / d
        l2 = ((c[1] - a[1]) * (X - c[0]) + (a[0] - c[0]) * (Y - c[1])) / d
        l3 = 1 - l1 - l2; ins = (l1 >= 0) & (l2 >= 0) & (l3 >= 0)
        sl = (slice(y0, y1 + 1), slice(x0, x1 + 1))
        for j in range(3): pos[sl + (j,)] = np.where(ins, l1 * A[j] + l2 * B[j] + l3 * C[j], pos[sl + (j,)])
        has[sl] |= ins
cloth = has & (px[:, :, 3] > 0.5)
bare = has & (px[:, :, 3] <= 0.5)
GR = float(os.environ.get("VDW_OTHER_GR", "0") or 0)
if GR > 0:
    luma = px[:, :, 0] * 0.3 + px[:, :, 1] * 0.59 + px[:, :, 2] * 0.11
    other = cloth & ((px[:, :, 1] < GR * px[:, :, 0]) | (luma < 0.08)); cloth &= ~other; bare |= other
    print(f"PARTS {int(other.sum())} pixels count as another part")
# skip islands whose bare part isn't next to the cloth's edge for real (e.g. cleared arms): their texels don't count
skip = np.zeros((n, n), bool)
for s in filter(None, os.environ.get("VDW_SKIP_UV", "").split(";")):
    u, v = (float(c) for c in s.split(",")); x, y = int(u * n), int(v * n)
    # flood the bare region from that point in texture space
    from collections import deque
    q = deque([(y, x)]); seen = np.zeros((n, n), bool)
    while q:
        yy, xx = q.popleft()
        if yy < 0 or xx < 0 or yy >= n or xx >= n or seen[yy, xx] or not has[yy, xx]: continue
        seen[yy, xx] = True; q.extend(((yy + 1, xx), (yy - 1, xx), (yy, xx + 1), (yy, xx - 1)))
    skip |= seen
bare &= ~skip
B = pos[bare]; kd = KDTree(len(B))
for i, p in enumerate(B): kd.insert(p, i)
kd.balance()
ys, xs = np.nonzero(cloth); dist = np.empty(len(ys), np.float32)
for i, (y, x) in enumerate(zip(ys, xs)): dist[i] = kd.find(pos[y, x])[2] / unit
t = np.clip(dist / EDGE, 0, 1); shade = 1 - DARK * (1 - t * t * (3 - 2 * t))          # smooth: darkest at the edge
# the margin past the islands (filled by the bake) takes the shade of the nearest cloth texel, so mips don't lighten edges
sh = np.ones((n, n), np.float32); sh[ys, xs] = shade
pad = ~has & (px[:, :, 3] > 0.5); cur = cloth.copy()
for _ in range(16):
    acc = np.zeros((n, n), np.float32); cnt = np.zeros((n, n), np.float32)
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        acc += np.roll(np.roll(sh * cur, dy, 0), dx, 1); cnt += np.roll(np.roll(cur, dy, 0), dx, 1)
    f = pad & ~cur & (cnt > 0); sh[f] = acc[f] / cnt[f]; cur |= f
# darken in linear light (the PNG holds sRGB values)
c = px[:, :, :3]; lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4) * sh[:, :, None]
px[:, :, :3] = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(lin, 1 / 2.4) - 0.055)
print(f"EDGE shaded {int((shade < 0.99).sum())} of {len(shade)} cloth pixels within {EDGE * 100:.1f} cm of an edge, {DARK * 100:.0f}% darker at it")
os.makedirs(OUT, exist_ok=True)
o = bpy.data.images.new(NAME, n, n, alpha=True); o.pixels = px.ravel(); o.filepath_raw = out_png; o.file_format = 'PNG'; o.save()
if os.path.exists(TEX[:-4] + "_nrm.png"): shutil.copyfile(TEX[:-4] + "_nrm.png", os.path.join(OUT, NAME + "_nrm.png"))
print("SAVED", out_png)
