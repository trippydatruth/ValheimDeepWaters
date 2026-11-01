# Repaints overalls colour that spilled onto the boots in a painted legs texture (bake_shirt_paint.py: where the overalls'
# cuff overlaps the boot top, the bake caught yellow on the boot). Each boot's top line is found on the body (per
# direction round the leg: how high the boot colour reaches); overalls colour below it gets the boot colour beside it.
#   blender -b --factory-startup --python fix_boot_spill.py
#   env: VDW_BODY_OBJ  body.obj from "vdw_debug paint dump"
#        VDW_TEX       the painted legs colour (.png); its _nrm.png is copied alongside unchanged
#        VDW_OUT       output folder (new; never overwrites), VDW_NAME new texture name
#        VDW_OTHER_GR  green/red ratio below which a pixel is boot (brown), not overalls (yellow) (default 0.8)
#        VDW_BELOW_CM  overalls colour this far under the line is left (the line itself), default 0.4
#        VDW_LINE      or: the boot colour goes up to this height (the rig's metres, e.g. 0.455 = under the middle of
#                      the boot rim model, which sits 0.44-0.48), so the colour change is hidden under the rim
#        VDW_BODY_H    the body's height in the rig's metres (fitref: 2.005)
import bpy, os, shutil, math
import numpy as np

BODY, TEX, OUT, NAME = (os.environ[k] for k in ("VDW_BODY_OBJ", "VDW_TEX", "VDW_OUT", "VDW_NAME"))
GR = float(os.environ.get("VDW_OTHER_GR", "0.8")); BELOW = float(os.environ.get("VDW_BELOW_CM", "0.4")) / 100
out_png = os.path.join(OUT, NAME + ".png")
if os.path.exists(out_png): raise SystemExit("exists, kept: " + out_png)
bpy.ops.wm.obj_import(filepath=BODY)
me = [o for o in bpy.context.selected_objects if o.type == 'MESH'][0].data
V = np.array([v.co[:] for v in me.vertices]); uvl = me.uv_layers.active.data
img = bpy.data.images.load(TEX); n = img.size[0]
px = np.array(img.pixels[:], np.float32).reshape(n, n, 4)
ext = V.max(0) - V.min(0); UP = int(np.argmax(ext)); unit = ext[UP] / float(os.environ.get("VDW_BODY_H", "2.005"))
LINE = float(os.environ.get("VDW_LINE", "0") or 0)
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
cloth = has & (px[:, :, 3] > 0.5)
boot = cloth & (px[:, :, 1] < GR * px[:, :, 0])
yel = cloth & ~boot
h = pos[:, :, UP].copy()
if np.median(h[boot]) > np.median(h[yel]): h = -h            # height grows away from the feet
h = (h - h[has].min()) / unit                              # height above the soles, rig metres
lat = [i for i in range(3) if i != UP]
spill = np.zeros((n, n), bool); BINS = 36
for side in (-1, 1):                                       # each leg (the texture may hold only one: mirrored UVs)
    leg = has & (np.sign(pos[:, :, lat[0]]) == side)
    bl = boot & leg
    if bl.sum() < 50: continue
    cx, cz = pos[:, :, lat[0]][bl].mean(), pos[:, :, lat[1]][bl].mean()
    ang = np.arctan2(pos[:, :, lat[1]] - cz, pos[:, :, lat[0]] - cx)
    bi = ((ang + np.pi) / (2 * np.pi) * BINS).astype(int) % BINS
    top = np.full(BINS, np.nan)
    for k in range(BINS):
        sel = bl & (bi == k)
        if sel.sum() > 5: top[k] = np.percentile(h[sel], 98)
    ok = np.isfinite(top)
    if ok.sum() < 3: continue
    ix = np.arange(BINS); top = np.interp(ix, ix[ok], top[ok], period=BINS)
    for _ in range(2): top = (np.roll(top, 1) + 2 * top + np.roll(top, -1)) / 4
    line = np.maximum(top[bi] + BELOW, LINE) if LINE else top[bi]
    s = yel & leg & (h < line - BELOW) & (h > line - 0.15)
    spill |= s
    print(f"BOOT leg {side}: top line {top.min():.2f}..{top.max():.2f} m up, {int(s.sum())} overalls pixels under it")
# boot colour into the spill, from the boot pixels beside it (texture space), else the boots' average
c = px.copy(); good = boot.copy(); need = spill.copy()
for _ in range(64):
    if not need.any(): break
    acc = np.zeros((n, n, 3), np.float32); cnt = np.zeros((n, n), np.float32)
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
        acc += np.roll(np.roll(c[:, :, :3] * good[:, :, None], dy, 0), dx, 1); cnt += np.roll(np.roll(good, dy, 0), dx, 1)
    f = need & (cnt > 0); c[f, :3] = acc[f] / cnt[f][:, None]; good |= f; need &= ~f
if need.any(): c[need, :3] = px[boot, :3].mean(0)
print(f"FIXED {int(spill.sum())} pixels ({int(need.sum())} from the average)")
os.makedirs(OUT, exist_ok=True)
o = bpy.data.images.new(NAME, n, n, alpha=True); o.pixels = c.ravel(); o.filepath_raw = out_png; o.file_format = 'PNG'; o.save()
if os.path.exists(TEX[:-4] + "_nrm.png"): shutil.copyfile(TEX[:-4] + "_nrm.png", os.path.join(OUT, NAME + "_nrm.png"))
print("SAVED", out_png)
