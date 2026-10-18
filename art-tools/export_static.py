# Exports a static (unrigged) model as FBX for Unity: metres, -Z forward / Y up baked in, every mesh in the file.
#   blender -b piece.blend --python export_static.py      env: VDW_FBX_OUT
import bpy, os

OUT = os.environ["VDW_FBX_OUT"]
for o in bpy.context.view_layer.objects:
    o.select_set(o.type == 'MESH')
bpy.context.view_layer.objects.active = next(o for o in bpy.context.view_layer.objects if o.type == 'MESH')
# VDW_TRIANGULATE=1: hand Unity triangles (it otherwise drops twisted quads as "self-intersecting")
if os.environ.get("VDW_TRIANGULATE") == "1":
    for o in bpy.context.view_layer.objects:
        if o.type == 'MESH': o.modifiers.new("vdw_tri", 'TRIANGULATE').quad_method = 'BEAUTY'
bpy.ops.export_scene.fbx(
    filepath=OUT, use_selection=True, object_types={'MESH'},
    global_scale=1.0, apply_unit_scale=True, apply_scale_options='FBX_SCALE_ALL',
    axis_forward='-Z', axis_up='Y', bake_space_transform=True,
    mesh_smooth_type='FACE', use_mesh_modifiers=True, bake_anim=False,
    path_mode='COPY', embed_textures=False,
)
print("EXPORTED", OUT, os.path.getsize(OUT), "bytes")
