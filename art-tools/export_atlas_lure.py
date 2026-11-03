# Exports a bait built by build_lures.py with its own painted atlas (the original bait look) for Unity, like the first
# lures: the mesh with its axis turn baked in (the lure on the line uses the bare mesh), smooth normals kept, one
# material named after the model; writes <out>/<key>/<key>_model.fbx and copies the four maps beside it.
#   blender -b <key>.blend --factory-startup --python export_atlas_lure.py      env: VDW_OUT, VDW_KEY, VDW_TEX (maps folder)
import bpy, os, shutil, glob
OUT, KEY, TEX = os.environ["VDW_OUT"], os.environ["VDW_KEY"], os.environ["VDW_TEX"]
path = os.path.join(OUT, KEY, KEY + "_model.fbx")
if os.path.exists(path): raise SystemExit("exists, kept: " + path)
os.makedirs(os.path.dirname(path), exist_ok=True)
ob = next(o for o in bpy.data.objects if o.type == 'MESH')
for o in list(bpy.data.objects):
    if o is not ob: bpy.data.objects.remove(o)
me = ob.data
me.materials.clear(); me.materials.append(bpy.data.materials.new(KEY))
ob.name = me.name = KEY
for o in bpy.data.objects: o.select_set(True)
bpy.context.view_layer.objects.active = ob
bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={'MESH'}, global_scale=1.0, apply_unit_scale=True,
                         apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y', bake_space_transform=True,
                         mesh_smooth_type='FACE', bake_anim=False, path_mode='STRIP', embed_textures=False)
for f in glob.glob(os.path.join(TEX, KEY + "_Unity_*.png")): shutil.copy(f, os.path.dirname(path))
print("EXPORTED", path, f"{len(me.polygons)} faces")
