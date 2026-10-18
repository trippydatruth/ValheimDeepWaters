# Zips a gaping mouth shut on an unrigged fish mesh (head toward -Y, top +Z): along the snout, the gap between the
# roof and the floor of the open mouth is found on the midline (as add_jaw.py does); every point near the gap is pulled
# toward the line between the lips - the upper lip down, the lower lip up, each by half the gap - easing off with
# distance, and whatever sits inside the gap (tongue, gill rakers) is flattened onto the line, out of sight. Rotating a
# jaw shut instead pushed the scans' inner mouth geometry out through the lips. Saves to VDW_SAVE_TO.
#   blender -b prep.blend --python close_mouth.py
#   env: VDW_SAVE_TO, VDW_MOUTH_GAP (smallest gap, share of the head's height, 0.06), VDW_MOUTH_CORNER (share of the
#        length from the nose where the lips meet; default: where the gap closes), VDW_MOUTH_REACH (how far the pull
#        eases off, share of the head's height, 0.45), VDW_PREVIEW (png prefix: side view before/after)
import bpy, math, os
import numpy as np
from mathutils import Vector
SAVE_TO = os.environ["VDW_SAVE_TO"]
GAP = float(os.environ.get("VDW_MOUTH_GAP", "0.06")); REACH = float(os.environ.get("VDW_MOUTH_REACH", "0.45"))
PREV = os.environ.get("VDW_PREVIEW", "")
mesh = max((o for o in bpy.data.objects if o.type == 'MESH'), key=lambda o: len(o.data.vertices))
me = mesh.data
co = np.array([v.co[:] for v in me.vertices]); lo, hi = co.min(0), co.max(0); L = hi[1] - lo[1]
headp = co[co[:, 1] < lo[1] + 0.3 * L]
H = float(np.percentile(headp[:, 2], 98) - np.percentile(headp[:, 2], 2))

def render(tag):
    if not PREV: return
    sc = bpy.context.scene; sc.render.engine = 'BLENDER_WORKBENCH'; sc.render.use_border = False
    sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'TEXTURE'; sc.display.shading.show_backface_culling = True
    sc.render.resolution_x, sc.render.resolution_y = 700, 450
    cam = bpy.data.objects.get("mcam")
    if cam is None:
        cd = bpy.data.cameras.new("mcam"); cd.type = 'ORTHO'; cd.ortho_scale = 0.42 * L
        cam = bpy.data.objects.new("mcam", cd); sc.collection.objects.link(cam)
    sc.camera = cam
    tgt = Vector((0, lo[1] + 0.15 * L, float(np.median(headp[:, 2]))))
    for nm, d in (("side", (1, 0, 0)), ("q", (0.8, -0.7, 0.2))):
        cam.location = tgt + Vector(d).normalized() * 3 * L; cam.rotation_euler = (tgt - cam.location).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = f"{PREV}_{tag}_{nm}.png"; bpy.ops.render.render(write_still=True)
render("before")

# ---- the gap on the midline, slice by slice from the nose
sl = []
for f in np.arange(0.0, 0.34, 0.005):
    y0 = lo[1] + f * L
    w = co[np.abs(co[:, 1] - y0) < 0.006 * L]
    if len(w) < 4: continue
    half = float(np.percentile(np.abs(w[:, 0]), 90))
    mid = w[np.abs(w[:, 0]) < max(0.2 * half, 0.004 * L)]
    if len(mid) < 4: continue
    z = np.sort(mid[:, 2]); g = np.diff(z); i = int(np.argmax(g))
    if g[i] > GAP * H: sl.append((y0, (z[i] + z[i + 1]) / 2, g[i]))
    elif sl and y0 - sl[-1][0] > 0.02 * L: break
if len(sl) < 3: raise SystemExit("  no open mouth found - nothing changed")
ys = np.array([s[0] for s in sl]); zc = np.array([s[1] for s in sl]); gp = np.array([s[2] for s in sl])
y_corner = lo[1] + float(os.environ["VDW_MOUTH_CORNER"]) * L if os.environ.get("VDW_MOUTH_CORNER") else float(ys.max())
# the gap shrinks to nothing at the corner; the lip line runs on straight to it
fit = np.polyfit(ys, zc, 1)
def line(y): return float(np.interp(y, ys, zc)) if y <= ys.max() else float(np.polyval(fit, y))
def gap(y):
    if y >= y_corner: return 0.0
    g = float(np.interp(y, ys, gp))
    return g * min(1.0, (y_corner - y) / max(1e-5, 0.35 * (y_corner - ys.min())))
print(f"  head height {H:.3f} m; mouth from {(ys.min() - lo[1]) / L:.2f} to the corner at {(y_corner - lo[1]) / L:.2f} of the length, widest gap {gp.max():.3f} m")

# ---- zip it: pull toward the lip line by half the gap, easing off over REACH x the head height
reach = REACH * H; moved = 0
for v in me.vertices:
    x, y, z = v.co
    d = gap(y)
    if d <= 1e-5: continue
    c = line(y); dz = z - c; half = d / 2
    if abs(dz) <= half:                               # inside the opening: flattened onto the line
        nz = c + dz * 0.04
    else:
        e = (abs(dz) - half) / reach; k = max(0.0, 1.0 - e); k = k * k * (3 - 2 * k)
        nz = z - math.copysign(half * k, dz)
    if abs(nz - z) > 1e-7: v.co.z = nz; moved += 1
me.update()
print(f"  {moved} points pulled shut")
render("after")
for o in list(bpy.data.objects):
    if o.name == "mcam": bpy.data.objects.remove(o)
bpy.ops.wm.save_as_mainfile(filepath=SAVE_TO); print("  saved", SAVE_TO)
