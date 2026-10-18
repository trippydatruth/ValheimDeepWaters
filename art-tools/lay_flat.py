# Lays a rigged, animated flatfish down: it is rigged and animated standing on edge like any fish (so its swim bends
# side to side), then turned a quarter about its length so it lies flat with its darker (eyed) side up - the swim
# becomes the up-and-down ripple a flatfish swims with. Armature and mesh are turned together and the turn applied,
# so the clips (bone-local) follow.     blender -b fish.blend --python lay_flat.py      env: VDW_SAVE_TO
import bpy, math, os
import numpy as np
from mathutils import Matrix
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
mesh = next(o for o in bpy.data.objects if o.type == 'MESH' and o.parent == arm)
me = mesh.data
bs = next(n for n in me.materials[0].node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
img = bs.inputs["Base Color"].links[0].from_node.image
W, H = img.size; px = np.empty(W * H * 4, np.float32); img.pixels.foreach_get(px); lum = px.reshape(H, W, 4)[:, :, :3].mean(2)
uvl = me.uv_layers.active.data
side = {1: [], -1: []}
for p in me.polygons:
    if abs(p.normal.x) < 0.6: continue
    u = np.mean([uvl[li].uv[:] for li in p.loop_indices], 0)
    side[1 if p.normal.x > 0 else -1].append(lum[int((u[1] % 1) * (H - 1)), int((u[0] % 1) * (W - 1))])
lp, ln = float(np.mean(side[1])), float(np.mean(side[-1]))
up_x = 1 if lp < ln else -1                       # the darker side goes up
ang = -math.pi / 2 * up_x                         # Ry(-90) takes +X to +Z
print(f"  +X side brightness {lp:.3f}, -X side {ln:.3f}: {'+X' if up_x > 0 else '-X'} side up")
R = Matrix.Rotation(ang, 4, 'Y')
for o in bpy.context.view_layer.objects: o.select_set(o in (arm, mesh))
bpy.context.view_layer.objects.active = arm
arm.matrix_world = R @ arm.matrix_world
bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
co = np.array([(mesh.matrix_world @ v.co)[:] for v in me.vertices]); print(f"  size now {tuple((co.max(0) - co.min(0)).round(3))}")
bpy.ops.wm.save_as_mainfile(filepath=os.environ["VDW_SAVE_TO"]); print("  saved", os.environ["VDW_SAVE_TO"])
