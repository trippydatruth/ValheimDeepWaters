# Preview render of a fish file for checking: side view and a three-quarter view from above, textured, rest pose,
# back faces culled (as Unity draws them).    blender -b fish.blend --python fish_preview.py   env: VDW_PREVIEW (png prefix)
import bpy, math, os
import numpy as np
# a file saved in Edit / Weight Paint mode: back to Object Mode first (in Edit Mode the armature modifier is off, so
# nothing deforms, and edits in progress aren't in the mesh data)
for _o in list(bpy.data.objects):
    if _o.mode != 'OBJECT' and _o.name in bpy.context.view_layer.objects:
        bpy.context.view_layer.objects.active = _o
        try: bpy.ops.object.mode_set(mode='OBJECT')
        except RuntimeError: pass
from mathutils import Vector
PREV = os.environ["VDW_PREVIEW"]
scene = bpy.context.scene
for a in bpy.data.objects:
    if a.type == 'ARMATURE': a.data.pose_position = 'REST'
mesh = max((o for o in bpy.data.objects if o.type == 'MESH'), key=lambda o: len(o.data.vertices))
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get(); ev = mesh.evaluated_get(dg); m = ev.to_mesh()
co = np.array([(ev.matrix_world @ v.co)[:] for v in m.vertices]); ev.to_mesh_clear()
lo, hi = co.min(0), co.max(0); ctr = Vector(((lo + hi) / 2).tolist()); L = float((hi - lo).max())
scene.render.engine = 'BLENDER_WORKBENCH'; scene.render.use_border = False
sh = scene.display.shading; sh.light = 'STUDIO'; sh.color_type = 'TEXTURE'; sh.show_backface_culling = True
scene.render.resolution_x, scene.render.resolution_y = (int(x) for x in os.environ.get("VDW_RES", "1000x560").split("x"))
cd = bpy.data.cameras.new("C"); cd.type = 'ORTHO'; cd.ortho_scale = L * 1.12
# VDW_FOCUS=head: a close-up of the front fifth; VDW_ENGINE=cycles: lit, with the normal map (engravings) showing
if os.environ.get("VDW_FOCUS") == "head":
    cd.ortho_scale = L * 0.42; ctr = Vector((ctr.x, lo[1] + 0.13 * L, ctr.z)); L = L * 0.4
if os.environ.get("VDW_ENGINE") == "cycles":
    scene.render.engine = 'CYCLES'; scene.cycles.device = 'CPU'; scene.cycles.samples = 32; scene.view_settings.view_transform = 'Standard'
    wd = bpy.data.worlds.new("w"); wd.use_nodes = True; scene.world = wd; wd.node_tree.nodes["Background"].inputs[0].default_value = (0.25, 0.27, 0.3, 1)
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", 'SUN')); sun.data.energy = 4; sun.rotation_euler = (0.9, 0.2, -0.6); scene.collection.objects.link(sun)
cam = bpy.data.objects.new("C", cd); scene.collection.objects.link(cam); scene.camera = cam
VIEWS = {"side": (1, 0, 0), "quarter": (0.75, 0.35, 0.55), "other": (-1, 0, 0), "top": (0, 0.001, 1), "front": (0.25, -1, 0.2), "below": (0.3, -0.35, -1), "headq": (0.8, -0.9, 0.5)}
for view in os.environ.get("VDW_VIEWS", "side,quarter").split(","):
    d = VIEWS[view]
    cam.location = ctr + Vector(d).normalized() * L * 4
    cam.rotation_euler = (ctr - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = f"{PREV}_{view}.png"; bpy.ops.render.render(write_still=True)
print("PREVIEW DONE")
