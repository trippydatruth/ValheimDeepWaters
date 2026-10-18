# Looks at a downloaded model before it goes through the fish pipeline: lists its objects (type, points, faces,
# materials, size), its images (and whether they still load), and renders it from the side, top and front with its
# textures, axes marked (red +X, green +Y, blue +Z), so the head direction and stray parts can be read off.
#   blender -b source.blend --python inspect_source.py      env: VDW_PREVIEW (png prefix)
import bpy, os, math
import numpy as np
from mathutils import Vector
PREV = os.environ["VDW_PREVIEW"]
scene = bpy.context.scene
for o in bpy.data.objects:
    d = o.dimensions
    extra = ""
    if o.type == 'MESH':
        extra = f"{len(o.data.vertices)} pts {len(o.data.polygons)} faces mats={[m.name for m in o.data.materials if m]}"
        extra += f" mods={[m.type for m in o.modifiers]} parent={o.parent.name if o.parent else None}"
    print(f"  OBJ {o.type:9s} {o.name:30s} dims=({d.x:.3f},{d.y:.3f},{d.z:.3f}) {extra}")
for a in bpy.data.actions: print(f"  ACTION {a.name} frames {tuple(a.frame_range)}")
for im in bpy.data.images:
    ok = im.has_data or (im.packed_file is not None)
    if not ok:
        try: im.reload(); ok = im.size[0] > 0
        except Exception: ok = False
    print(f"  IMG {im.name:40s} {tuple(im.size)} packed={im.packed_file is not None} ok={ok} {im.filepath}")
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
for o in bpy.data.objects:
    if o.type == 'ARMATURE': o.data.pose_position = 'REST'
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
pts = []
for o in meshes:
    e = o.evaluated_get(dg); m = e.to_mesh()
    step = max(1, len(m.vertices) // 20000); pts += [tuple(e.matrix_world @ m.vertices[i].co) for i in range(0, len(m.vertices), step)]
    e.to_mesh_clear()
P = np.array(pts); lo, hi = P.min(0), P.max(0); ctr = Vector(((lo + hi) / 2).tolist()); size = float((hi - lo).max())
print(f"  WORLD bounds lo={lo.round(3)} hi={hi.round(3)} size={size:.3f}")
# axis markers
for i, col in enumerate(((1, 0, 0, 1), (0, 1, 0, 1), (0, 0, 1, 1))):
    mat = bpy.data.materials.new(f"axis{i}"); mat.diffuse_color = col
    bpy.ops.mesh.primitive_cylinder_add(radius=size * 0.01, depth=size * 0.6)
    c = bpy.context.object; c.data.materials.append(mat)
    d = [0, 0, 0]; d[i] = 1; dv = Vector(d)
    c.location = ctr + dv * size * 0.3
    c.rotation_euler = dv.to_track_quat('Z', 'Y').to_euler()
scene.render.engine = 'BLENDER_WORKBENCH'; scene.render.use_border = False
scene.display.shading.light = 'STUDIO'; scene.display.shading.color_type = 'TEXTURE'
scene.render.resolution_x, scene.render.resolution_y = 800, 500
cd = bpy.data.cameras.new("C"); cd.type = 'ORTHO'; cd.ortho_scale = size * 1.4
cam = bpy.data.objects.new("C", cd); scene.collection.objects.link(cam); scene.camera = cam
for view, d in (("posX", (1, 0, 0)), ("posY", (0, 1, 0)), ("posZ", (0, 0, 1)), ("q", (0.6, -0.6, 0.5))):
    dv = Vector(d).normalized(); cam.location = ctr + dv * size * 4
    cam.rotation_euler = (0, 0, 0) if view == "posZ" else (ctr - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = f"{PREV}_{view}.png"; bpy.ops.render.render(write_still=True)
print("INSPECT DONE")

