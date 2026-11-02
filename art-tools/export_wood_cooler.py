# Exports the wooden ice chest (build_wood_cooler.py) or the wooden tackle box (build_wood_tacklebox.py, VDW_KIND=
# tacklebox) for the game, once per tier, like build_cooler.py did: the rig ("root" and the "lid" on the back hinge)
# and the mesh triangulated, with one plain material named after the model and only the baked atlas UVs (the "Grain"
# UVs that steer the procedural wood are left out - Unity reads the first UV layer), to
# <out>/<model>_<tier>/<model>_<tier>_model.fbx. New files only.
#   blender -b cooler_wood_v1.blend --factory-startup --python export_wood_cooler.py
#   env: VDW_OUT, VDW_TIERS (c1,c2,c3), VDW_KIND (cooler | tacklebox), VDW_SCALE (1: the whole model scaled evenly,
#        mesh and bones, e.g. 1.364 to bring the 0.44 m tackle box to the old box's 0.6 m - the baked UVs don't change)
import bpy, os
OUT = os.environ["VDW_OUT"]; KIND = os.environ.get("VDW_KIND", "cooler")
NAME, RIG = ("tacklebox", "TackleBox_Rig") if KIND == "tacklebox" else ("cooler", "Cooler_Rig")
TIERS = os.environ.get("VDW_TIERS", "t1,t2,t3,t4" if KIND == "tacklebox" else "c1,c2,c3").split(",")
SCALE = float(os.environ.get("VDW_SCALE", "1"))
ob, rig = bpy.data.objects[NAME], bpy.data.objects[RIG]
me = ob.data
if "Grain" in me.uv_layers: me.uv_layers.remove(me.uv_layers["Grain"])
me.uv_layers.active = me.uv_layers["UVMap"]; me.uv_layers["UVMap"].active_render = True
me.materials.clear(); me.materials.append(bpy.data.materials.get(NAME) or bpy.data.materials.new(NAME))
for p in me.polygons: p.material_index = 0
rig.data.pose_position = 'REST'
if SCALE != 1.0:
    from mathutils import Matrix
    me.transform(Matrix.Scale(SCALE, 4))
    bpy.context.view_layer.objects.active = rig; bpy.ops.object.mode_set(mode='EDIT')
    for eb in rig.data.edit_bones: eb.head *= SCALE; eb.tail *= SCALE
    bpy.ops.object.mode_set(mode='OBJECT')
co = [v.co for v in me.vertices]
print(f"EXPORT {NAME}: {max(c.x for c in co) - min(c.x for c in co):.3f} x {max(c.y for c in co) - min(c.y for c in co):.3f} x {max(c.z for c in co):.3f} m (scale {SCALE})")
for o in bpy.data.objects: o.select_set(o in (ob, rig))
bpy.context.view_layer.objects.active = rig
tri = ob.modifiers.new("tri", 'TRIANGULATE')
for t in TIERS:
    path = os.path.join(OUT, f"{NAME}_{t}", f"{NAME}_{t}_model.fbx")
    if os.path.exists(path): raise SystemExit("exists, kept: " + path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={'ARMATURE', 'MESH'},
                             global_scale=1.0, apply_unit_scale=True, apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y',
                             bake_space_transform=False, add_leaf_bones=False, primary_bone_axis='Y', secondary_bone_axis='X',
                             mesh_smooth_type='FACE', use_mesh_modifiers=True, bake_anim=False, path_mode='COPY', embed_textures=False)
    print("EXPORTED", path)
ob.modifiers.remove(tri)
