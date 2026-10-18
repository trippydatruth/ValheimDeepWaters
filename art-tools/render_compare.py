# Renders the fish (colour texture only, flat light) from the side and from above, to compare texture placement.
import bpy, os
from mathutils import Vector
OUT = os.environ["VDW_RENDER_OUT"]
scene = bpy.context.scene
arm = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
if arm: arm.data.pose_position = 'REST'
scene.render.engine = 'BLENDER_WORKBENCH'
scene.display.shading.light = 'FLAT'
scene.display.shading.color_type = 'TEXTURE'
scene.render.resolution_x, scene.render.resolution_y = 700, 420
cd = bpy.data.cameras.new("C"); cd.type = 'ORTHO'; cd.ortho_scale = 4.4
cam = bpy.data.objects.new("C", cd); scene.collection.objects.link(cam); scene.camera = cam
for view, pos in (("side", Vector((10, 0.1, 0.45))), ("top", Vector((0, 0.1, 10)))):
    cam.location = pos
    cam.rotation_euler = (Vector((0, 0.1, 0.45)) - pos).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = f"{OUT}_{view}.png"
    bpy.ops.render.render(write_still=True)
print("RENDERED")
