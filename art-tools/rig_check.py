# Check render for a rigged fish: from the side, every vertex coloured by the bone that moves it most (tail-fin bones
# red/orange, spine bones in blues, head white, fins green/yellow), and from above at the strongest bend of Swim and
# Thrash, so the tail start and the fin weights can be judged.
#   blender -b fish.blend --python rig_check.py      env: VDW_PREVIEW (png prefix)
import bpy, math, os
import numpy as np
# a file saved in Edit / Weight Paint mode: back to Object Mode first (in Edit Mode the armature modifier is off, so
# nothing deforms, and edits in progress aren't in the mesh data)
for _o in list(bpy.data.objects):
    if _o.mode != 'OBJECT' and _o.name in bpy.context.view_layer.objects:
        bpy.context.view_layer.objects.active = _o
        try: bpy.ops.object.mode_set(mode='OBJECT')
        except RuntimeError: pass
PREV = os.environ["VDW_PREVIEW"]
scene = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
mesh = next(o for o in bpy.data.objects if o.type == 'MESH' and o.parent == arm)
def colour(name):
    if ".Tail.Fin" in name: return (1.0, 0.25 + 0.15 * int(name[-1]), 0.1)
    if name == "Head": return (0.95, 0.95, 0.95)
    if name.startswith("Spine"):
        k = int(name[5:] or 0); return (0.1, 0.25 + 0.15 * k, 0.9 - 0.12 * k)
    if "Dorsal" in name: return (0.95, 0.9, 0.1)
    if "Pectoral" in name: return (0.1, 0.85, 0.2)
    if "Pelvic" in name: return (0.6, 0.95, 0.4)
    if name == "Jaw": return (0.9, 0.2, 0.9)
    return (0.5, 0.5, 0.5)
me = mesh.data
attr = me.color_attributes.new("bonecol", 'BYTE_COLOR', 'POINT')
for v in me.vertices:
    g = max(v.groups, key=lambda g: g.weight, default=None)
    attr.data[v.index].color = (*colour(mesh.vertex_groups[g.group].name), 1.0) if g else (0, 0, 0, 1)
me.color_attributes.active_color = attr
scene.render.engine = 'BLENDER_WORKBENCH'; scene.render.use_border = False
scene.display.shading.light = 'STUDIO'
scene.render.resolution_x, scene.render.resolution_y = 1000, 500
co = np.array([v.co[:] for v in me.vertices]); L = float(co[:, 1].max() - co[:, 1].min())
cd = bpy.data.cameras.new("C"); cd.type = 'ORTHO'; cd.ortho_scale = L * 1.25
cam = bpy.data.objects.new("C", cd); scene.collection.objects.link(cam); scene.camera = cam
r90 = math.radians(90)
def shoot(view, colour_type):
    scene.display.shading.color_type = colour_type
    if view.startswith("side"): cam.location = (L * 4, 0, 0); cam.rotation_euler = (r90, 0, r90)
    else: cam.location = (0, 0, L * 4); cam.rotation_euler = (0, 0, r90)
    scene.render.filepath = f"{PREV}_{view}.png"; bpy.ops.render.render(write_still=True)
arm.data.pose_position = 'REST'; shoot("side_bones", 'VERTEX')
arm.data.pose_position = 'POSE'
for clip in ("Swim", "Thrash"):
    act = bpy.data.actions.get(clip)
    if not act: continue
    arm.animation_data_create(); arm.animation_data.action = act
    f0, f1 = (int(x) for x in act.frame_range)
    best, bf = -1, f0      # the frame where the tail is furthest to the side
    tail_idx = np.nonzero(co[:, 1] > co[:, 1].max() - 0.1 * L)[0]
    for f in range(f0, f1 + 1, 2):
        scene.frame_set(f); dg = bpy.context.evaluated_depsgraph_get(); ev = mesh.evaluated_get(dg); m = ev.to_mesh()
        x = max(abs(m.vertices[int(i)].co.x) for i in tail_idx); ev.to_mesh_clear()
        if x > best: best, bf = x, f
    scene.frame_set(bf); shoot(f"top_{clip}", 'TEXTURE')
print("RIG CHECK DONE")
