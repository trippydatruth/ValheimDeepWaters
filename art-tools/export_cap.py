# Exports an angler cap (build_caps.py, baked by bake_wood_cooler.py VDW_KIND=cap) for the game like the sou'wester:
# the cap back in the body's centimetres, one material named after the model, only the baked atlas UVs, a vertex colour
# (red = 1: all of it moves rigidly with the head), and "fitref" - the body copy from the sou'wester's FBX - so the mod
# can line it up with the game's body mesh. Writes <out>/fisher_<tier>/fisher_<tier>_model.fbx and copies the maps.
#   blender -b fisher_<tier>_baked.blend --factory-startup --python export_cap.py
#   env: VDW_OUT (folder), VDW_TIER (beanie | bucket), VDW_TEX (the baked maps' folder)
import bpy, os, shutil, glob
from mathutils import Matrix
OUT, TIER, TEX = os.environ["VDW_OUT"], os.environ["VDW_TIER"], os.environ["VDW_TEX"]
KEY = "fisher_" + TIER
path = os.path.join(OUT, KEY, KEY + "_model.fbx")
if os.path.exists(path): raise SystemExit("exists, kept: " + path)
os.makedirs(os.path.dirname(path), exist_ok=True)
ob = bpy.data.objects["fisher"]; me = ob.data
for o in list(bpy.data.objects):
    if o is not ob: bpy.data.objects.remove(o)
if "Grain" in me.uv_layers: me.uv_layers.remove(me.uv_layers["Grain"])
me.uv_layers.active = me.uv_layers["UVMap"]; me.uv_layers["UVMap"].active_render = True
me.materials.clear(); me.materials.append(bpy.data.materials.new(KEY))
for p in me.polygons: p.material_index = 0
me.transform(Matrix.Scale(100.0, 4))                      # metres -> the body's centimetres
ob.name = KEY; me.name = KEY
ca = me.color_attributes.new("rigid", 'FLOAT_COLOR', 'POINT')
for i in range(len(me.vertices)): ca.data[i].color = (1.0, 0.0, 0.0, 1.0)
# the body copy, as the sou'wester carries it
bpy.ops.import_scene.fbx(filepath=r"C:\Users\tripp\Desktop\Valheim_DeepWaters\ValheimDeepWatersUnity\Assets\DeepWaters\fisher_hat\fisher_hat_model.fbx")
fit = bpy.data.objects["fitref"]
fit.parent = None; fit.data.transform(fit.matrix_world); fit.matrix_world = Matrix.Identity(4)
for o in list(bpy.data.objects):
    if o.name not in (KEY, "fitref"): bpy.data.objects.remove(o)
for o in bpy.data.objects: o.select_set(True)
bpy.context.view_layer.objects.active = ob
tri = ob.modifiers.new("tri", 'TRIANGULATE')
bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={'MESH'}, global_scale=1.0, apply_unit_scale=True,
                         apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y', bake_space_transform=True,
                         mesh_smooth_type='FACE', use_mesh_modifiers=True, bake_anim=False, path_mode='STRIP', embed_textures=False, colors_type='LINEAR')
for f in glob.glob(os.path.join(TEX, KEY + "_Unity_*.png")): shutil.copy(f, os.path.dirname(path))
print("EXPORTED", path)
