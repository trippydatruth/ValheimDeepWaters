# Traces the centre line of a fish whose body curls (a thick front and a coiled tail, where eel_centerline's surface
# slicing zigzags): starts at the snout, steps along the body, and at each step re-centres on the cross-section of the
# main piece (the median of the points in a thin slab across the current direction, within a search radius), turning
# with the body. Stops at the tail tip. Saves <VDW_OUT>_line.npy (head first, for straighten_eel.py) and a render.
#   blender -b fish.blend --python trace_centerline.py
#   env: VDW_OUT, VDW_STEP (share of the length, 0.02), VDW_RADIUS (search radius, share of the length, 0.12),
#        VDW_START_DIR "x,y,z" (first direction, default +Y: head toward -Y)
import bpy, os, math
import numpy as np
from mathutils import Vector
OUT = os.environ["VDW_OUT"]
mesh = max((o for o in bpy.data.objects if o.type == 'MESH'), key=lambda o: len(o.data.vertices))
me = mesh.data
co = np.array([(mesh.matrix_world @ v.co)[:] for v in me.vertices])
# main piece only (spikes and loose bits would pull the centre off)
par = np.arange(len(co))
def f(i):
    while par[i] != i: par[i] = par[par[i]]; i = par[i]
    return i
for e in me.edges:
    a, b = f(e.vertices[0]), f(e.vertices[1])
    if a != b: par[a] = b
roots = np.array([f(i) for i in range(len(co))]); main = roots == np.bincount(roots).argmax()
P = co[main]
L = float(np.ptp(co[:, 1])); STEP = float(os.environ.get("VDW_STEP", "0.02")) * L; RAD = float(os.environ.get("VDW_RADIUS", "0.12")) * L
d0 = np.array([float(x) for x in os.environ.get("VDW_START_DIR", "0,1,0").split(",")]); d0 /= np.linalg.norm(d0)
# start: the snout = the main piece's furthest point against the start direction, moved onto the first cross-section
s = P @ d0; tip = P[np.argmin(s)].copy()
# VDW_TRACE_FROM: start tracing this far back (share of the length) where the body is solid - an open mouth splits the
# head's cross-sections in two; the head part of the line is a straight run from there to the snout
FROM = float(os.environ.get("VDW_TRACE_FROM", "0.0"))
PLANAR = os.environ.get("VDW_PLANAR") == "1"
if PLANAR: d0 = np.array([0.0, d0[1], d0[2]]) / max(np.linalg.norm(d0[1:]), 1e-9)
p0 = tip + d0 * (FROM * L)
slab0 = P[np.abs((P - p0) @ d0) < STEP * 0.6]
p = np.median(slab0, 0) if len(slab0) else p0
for shrink in (0.7, 0.5, 0.38):
    if len(slab0) == 0: break
    r_ = np.linalg.norm((slab0 - p) - np.outer((slab0 - p) @ d0, d0), axis=1)
    if (r_ < RAD * shrink).sum() >= 6: p = np.median(slab0[r_ < RAD * shrink], 0)
if PLANAR and len(slab0):
    p = p0.copy(); p[0] = 0.0; p[2] = 0.5 * (np.percentile(slab0[:, 2], 15) + np.percentile(slab0[:, 2], 85))
snout = p - d0 * ((p - tip) @ d0)                                   # the snout, at the body's centre height
n_head = max(2, int(((p - snout) @ d0) / STEP))
line = [snout + (p - snout) * (i / n_head) for i in range(n_head)] + [p.copy()]
d = d0.copy(); total = float((p - snout) @ d0)
for it in range(2000):
    q = p + d * STEP
    rel = P - q; along = rel @ d
    sel = (np.abs(along) < STEP * 0.6) & (np.linalg.norm(rel - np.outer(along, d), axis=1) < RAD)
    if sel.sum() < 6: break
    S_ = P[sel]; c = np.median(S_, 0)
    if PLANAR:   # a body that bends in its own side plane: centre between the slab's lower and upper edges (15th / 85th
        # percentile across the body in that plane, so a few thin spikes or fin edges don't count), sideways kept at 0
        perp = np.array([0.0, -d[2], d[1]]); perp /= max(np.linalg.norm(perp), 1e-9)
        o = (S_ - q) @ perp
        c = q + perp * 0.5 * (np.percentile(o, 15) + np.percentile(o, 85)); c[0] = 0.0
    else:
        for shrink in (0.7, 0.5, 0.38):     # re-centre on the solid tube: thin spikes and fin edges fall outside
            r_ = np.linalg.norm((S_ - c) - np.outer((S_ - c) @ d, d), axis=1)
            keep = r_ < RAD * shrink
            if keep.sum() >= 6: c = np.median(S_[keep], 0)
    c = c - d * ((c - q) @ d)          # back onto the slab's plane
    nd = c - p; n = np.linalg.norm(nd)
    if n < 1e-9: break
    nd /= n; d = d * 0.5 + nd * 0.5; d /= np.linalg.norm(d)        # turn smoothly with the body
    p = c; line.append(p.copy()); total += n
line = np.array(line)
k = np.ones(5) / 5
if len(line) > 6:
    sm = np.array([np.convolve(np.pad(line[:, i], 2, mode='edge'), k, 'valid') for i in range(3)]).T
    sm[0], sm[-1] = line[0], line[-1]; line = sm
np.save(OUT + "_line.npy", line)
print(f"  traced {len(line)} points, length {total:.3f} (bounding length {L:.3f}); ends {line[0].round(3)} -> {line[-1].round(3)}")
# render the line through the see-through mesh
cu = bpy.data.curves.new("CL", 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = L * 0.008
sp = cu.splines.new('POLY'); sp.points.add(len(line) - 1)
for i, x in enumerate(line): sp.points[i].co = (*x, 1)
ob = bpy.data.objects.new("CL", cu); bpy.context.scene.collection.objects.link(ob)
mr = bpy.data.materials.new("r"); mr.diffuse_color = (1, 0, 0, 1); cu.materials.append(mr)
sc = bpy.context.scene; sc.render.engine = 'BLENDER_WORKBENCH'; sc.render.use_border = False
sc.display.shading.show_xray = True; sc.display.shading.xray_alpha = 0.35; sc.display.shading.color_type = 'MATERIAL'
sc.render.resolution_x, sc.render.resolution_y = 900, 600
ctr = Vector(((co.min(0) + co.max(0)) / 2).tolist())
cd = bpy.data.cameras.new("C"); cd.type = 'ORTHO'; cd.ortho_scale = L * 1.15; cam = bpy.data.objects.new("C", cd); sc.collection.objects.link(cam); sc.camera = cam
for view, dv in (("side", (1, 0, 0)), ("top", (0, 0.001, 1))):
    cam.location = ctr + Vector(dv).normalized() * L * 4; cam.rotation_euler = (ctr - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = f"{OUT}_{view}.png"; bpy.ops.render.render(write_still=True)
