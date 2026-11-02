# Exports the wooden ice chest (build_wood_cooler.py) for the game, once per tier, like build_cooler.py did: the rig
# ("root" and the "lid" on the back hinge) and the mesh triangulated, with one plain material named "cooler" and only
# the baked atlas UVs (the "Grain" UVs that steer the procedural wood are left out - Unity reads the first UV layer),
# to <out>/cooler_<tier>/cooler_<tier>_model.fbx. New files only.
#   blender -b cooler_wood_v1.blend --factory-startup --python export_wood_cooler.py
#   env: VDW_OUT, VDW_TIERS (c1,c2,c3)
import bpy, os
OUT = os.environ["VDW_OUT"]; TIERS = os.environ.get("VDW_TIERS", "c1,c2,c3").split(",")
ob, rig = bpy.data.objects["cooler"], bpy.data.objects["Cooler_Rig"]
me = ob.data
if "Grain" in me.uv_layers: me.uv_layers.remove(me.uv_layers["Grain"])
me.uv_layers.active = me.uv_layers["UVMap"]; me.uv_layers["UVMap"].active_render = True
me.materials.clear(); me.materials.append(bpy.data.materials.get("cooler") or bpy.data.materials.new("cooler"))
for p in me.polygons: p.material_index = 0
rig.data.pose_position = 'REST'
for o in bpy.data.objects: o.select_set(o in (ob, rig))
bpy.context.view_layer.objects.active = rig
tri = ob.modifiers.new("tri", 'TRIANGULATE')
for t in TIERS:
    path = os.path.join(OUT, f"cooler_{t}", f"cooler_{t}_model.fbx")
    if os.path.exists(path): raise SystemExit("exists, kept: " + path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={'ARMATURE', 'MESH'},
                             global_scale=1.0, apply_unit_scale=True, apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y',
                             bake_space_transform=False, add_leaf_bones=False, primary_bone_axis='Y', secondary_bone_axis='X',
                             mesh_smooth_type='FACE', use_mesh_modifiers=True, bake_anim=False, path_mode='COPY', embed_textures=False)
    print("EXPORTED", path)
ob.modifiers.remove(tri)
