# Smooths a painted-on coat's colour over the middle of the back. The game body's texture is mirrored left/right, so the
# grunge beside the spine meets its own mirror image at the centre-back seam (a Rorschach look). Within VDW_WIDTH_CM of
# the spine the colour eases into a heavily blurred copy of itself (the blotches' detail gone, its overall tint kept);
# beyond that it's untouched. Run it on the colour before edge_shade.py (the blur would smear the shaded edges).
#   blender -b --factory-startup --python smooth_back_colour.py
#   env: VDW_BODY_OBJ  body.obj from "vdw_debug paint dump"
#        VDW_TEX       the painted colour (.png, RGBA)
#        VDW_OUT       output folder (new; never overwrites), VDW_NAME new texture name
#        VDW_WIDTH_CM  how far either side of the spine the smoothing reaches (default 15; full in the middle third)
#        VDW_BLUR_PX   blur radius in texture pixels (default 14)
#        VDW_AMOUNT    0..1 how much of the blurred copy at the spine (default 1)
import bpy, os
import numpy as np

BODY, TEX, OUT, NAME = (os.environ[k] for k in ("VDW_BODY_OBJ", "VDW_TEX", "VDW_OUT", "VDW_NAME"))
WIDTH = float(os.environ.get("VDW_WIDTH_CM", "15")) / 100; BLUR = int(os.environ.get("VDW_BLUR_PX", "14"))
AMOUNT = float(os.environ.get("VDW_AMOUNT", "1"))
out_png = os.path.join(OUT, NAME + ".png")
if os.path.exists(out_png): raise SystemExit("exists, kept: " + out_png)
bpy.ops.wm.obj_import(filepath=BODY)
me = [o for o in bpy.context.selected_objects if o.type == 'MESH'][0].data
V = np.array([v.co[:] for v in me.vertices]); uvl = me.uv_layers.active.data
img = bpy.data.images.load(TEX); n = img.size[0]
px = np.array(img.pixels[:], np.float32).reshape(n, n, 4)
ext = V.max(0) - V.min(0); UP = int(np.argmax(ext)); unit = ext[UP] / 2.005           # the rig's metres (fitref 2.005 tall)
pos = np.zeros((n, n, 3), np.float32); has = np.zeros((n, n), bool)
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
cloth = px[:, :, 3] > 0.5
lat = [i for i in range(3) if i != UP]
SIDE = lat[int(np.argmax([ext[i] for i in lat]))]           # left-right (the widest way, arms out)
DEPTH = [i for i in lat if i != SIDE][0]                    # front-back
mid = V[:, SIDE].min() + ext[SIDE] / 2
dx = np.abs(pos[:, :, SIDE] - mid) / unit                   # metres from the body's middle line
# which way is the back: the coat is open at the front, closed at the back - the side with cloth on the middle line
core = has & cloth & (dx < 0.02)
zc = V[:, DEPTH].min() + ext[DEPTH] / 2
back_sign = 1 if np.median(pos[:, :, DEPTH][core]) > zc else -1
back = has & ((pos[:, :, DEPTH] - zc) * back_sign > 0)
print(f"BACK side {back_sign:+d}, {int((back & cloth).sum())} coat pixels on the back")
# blur the cloth colour (only cloth pixels count), in linear light, with a box blur run three times (~gaussian)
def srgb2lin(c): return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
def lin2srgb(c): return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(np.maximum(c, 0), 1 / 2.4) - 0.055)
lin = srgb2lin(px[:, :, :3]); w = cloth.astype(np.float32)
def box(a, r):
    k = 2 * r + 1; cs = np.cumsum(np.pad(a, ((r + 1, r), (0, 0)) + ((0, 0),) * (a.ndim - 2), mode='constant'), axis=0)
    a = (cs[k:] - cs[:-k]); cs = np.cumsum(np.pad(a, ((0, 0), (r + 1, r)) + ((0, 0),) * (a.ndim - 2), mode='constant'), axis=1)
    return cs[:, k:] - cs[:, :-k]
num = lin * w[:, :, None]; den = w.copy()
for _ in range(3): num = box(num, BLUR // 2); den = box(den, BLUR // 2)
blur = num / np.maximum(den, 1e-6)[:, :, None]
t = np.clip((dx - WIDTH / 3) / (WIDTH - WIDTH / 3), 0, 1); f = 1 - t * t * (3 - 2 * t)   # 1 in the middle third, 0 past WIDTH
f = f * back * cloth * AMOUNT
lin = lin * (1 - f[:, :, None]) + blur * f[:, :, None]
px[:, :, :3] = lin2srgb(lin)
print(f"SMOOTHED {int((f > 0.01).sum())} pixels within {WIDTH * 100:.0f} cm of the spine (blur {BLUR}px)")
os.makedirs(OUT, exist_ok=True)
o = bpy.data.images.new(NAME, n, n, alpha=True); o.pixels = px.ravel(); o.filepath_raw = out_png; o.file_format = 'PNG'; o.save()
print("SAVED", out_png)
