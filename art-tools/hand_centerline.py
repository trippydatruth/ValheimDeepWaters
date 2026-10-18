# A centre line placed by hand on a side render (trace_centerline's "side" view: orthographic from +X, ortho scale
# 1.15 x the length over VDW_W pixels, centred on the mesh's bounding box; head on the left): pixel points snout first
# become a smooth line in the side plane (x = 0), saved as <VDW_OUT>_line.npy for straighten_eel.py, plus a check render.
#   blender -b fish.blend --python hand_centerline.py   env: VDW_OUT, VDW_PX "x,y;x,y;...", VDW_W (900), VDW_H (600)
import bpy, os
import numpy as np
from mathutils import Vector
OUT = os.environ["VDW_OUT"]; W = int(os.environ.get("VDW_W", "900")); H = int(os.environ.get("VDW_H", "600"))
mesh = max((o for o in bpy.data.objects if o.type == 'MESH'), key=lambda o: len(o.data.vertices))
co = np.array([(mesh.matrix_world @ v.co)[:] for v in mesh.data.vertices]); lo, hi = co.min(0), co.max(0); ctr = (lo + hi) / 2
L = float(np.ptp(co[:, 1])); s = W / (L * 1.15)
px = np.array([[float(a) for a in p.split(",")] for p in os.environ["VDW_PX"].split(";")])
pts = np.stack([np.zeros(len(px)), ctr[1] + (px[:, 0] - W / 2) / s, ctr[2] + (H / 2 - px[:, 1]) / s], 1)
# dense, evenly spaced along the polyline, then smoothed
seg = np.linalg.norm(np.diff(pts, axis=0), axis=1); cum = np.concatenate([[0], np.cumsum(seg)])
u = np.linspace(0, cum[-1], 80); line = np.stack([np.interp(u, cum, pts[:, i]) for i in range(3)], 1)
k = np.ones(5) / 5; sm = np.array([np.convolve(np.pad(line[:, i], 2, mode='edge'), k, 'valid') for i in range(3)]).T
sm[0], sm[-1] = line[0], line[-1]; line = sm
np.save(OUT + "_line.npy", line); print(f"  hand line: {len(line)} points, length {cum[-1]:.3f} (bounding length {L:.3f})")
cu = bpy.data.curves.new("CL", 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = L * 0.008
sp = cu.splines.new('POLY'); sp.points.add(len(line) - 1)
for i, x in enumerate(line): sp.points[i].co = (*x, 1)
ob = bpy.data.objects.new("CL", cu); bpy.context.scene.collection.objects.link(ob)
mr = bpy.data.materials.new("r"); mr.diffuse_color = (1, 0, 0, 1); cu.materials.append(mr)
sc = bpy.context.scene; sc.render.engine = 'BLENDER_WORKBENCH'; sc.render.use_border = False
sc.display.shading.show_xray = True; sc.display.shading.xray_alpha = 0.35; sc.display.shading.color_type = 'MATERIAL'
sc.render.resolution_x, sc.render.resolution_y = W, H
cd = bpy.data.cameras.new("C"); cd.type = 'ORTHO'; cd.ortho_scale = L * 1.15; cam = bpy.data.objects.new("C", cd); sc.collection.objects.link(cam); sc.camera = cam
c = Vector(ctr.tolist())
for view, dv in (("side", (1, 0, 0)), ("top", (0, 0.001, 1))):
    cam.location = c + Vector(dv).normalized() * L * 4; cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = f"{OUT}_{view}.png"; bpy.ops.render.render(write_still=True)
