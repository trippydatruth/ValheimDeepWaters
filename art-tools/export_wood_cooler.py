# Exports the wooden ice chest (build_wood_cooler.py) or the wooden tackle box (build_wood_tacklebox.py, VDW_KIND=
# tacklebox) for the game, once per tier, like build_cooler.py did: the rig ("root" and the "lid" on the back hinge)
# and the mesh triangulated, with one plain material named after the model and only the baked atlas UVs (the "Grain"
# UVs that steer the procedural wood are left out - Unity reads the first UV layer), to
# <out>/<model>_<tier>/<model>_<tier>_model.fbx. New files only.
#   blender -b cooler_wood_v1.blend --factory-startup --python export_wood_cooler.py
#   env: VDW_OUT, VDW_TIERS (c1,c2,c3), VDW_KIND (cooler | tacklebox), VDW_SCALE (1: the whole model scaled evenly,
#        mesh and bones, e.g. 1.364 to bring the 0.44 m tackle box to the old box's 0.6 m - the baked UVs don't change),
#        VDW_STATIC=1: no rig - the mesh alone, lid shut, its material named after each model (<model>_<tier>), as the
#        importer's static models want (Hildir's lost tackle boxes)
import bpy, os
OUT = os.environ["VDW_OUT"]; KIND = os.environ.get("VDW_KIND", "cooler")
NAME, RIG = {"tacklebox": ("tacklebox", "TackleBox_Rig"), "gear": ("tackle", "")}.get(KIND, ("cooler", "Cooler_Rig"))   # gear: a reel or line (build_gear.py), static
TIERS = os.environ.get("VDW_TIERS", "t1,t2,t3,t4" if KIND == "tacklebox" else "c1,c2,c3").split(",")
SCALE = float(os.environ.get("VDW_SCALE", "1")); STATIC = os.environ.get("VDW_STATIC") == "1" or KIND == "gear"
ob, rig = bpy.data.objects[NAME], bpy.data.objects.get(RIG)
me = ob.data
if "Grain" in me.uv_layers: me.uv_layers.remove(me.uv_layers["Grain"])
me.uv_layers.active = me.uv_layers["UVMap"]; me.uv_layers["UVMap"].active_render = True
me.materials.clear(); me.materials.append(bpy.data.materials.get(NAME) or bpy.data.materials.new(NAME))
for p in me.polygons: p.material_index = 0
if rig: rig.data.pose_position = 'REST'
# extra objects that go with the box: lures hung by hang_lures.py and their line, each with its own texture set
extras = [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith(("bait_lure_", "fishing_line"))]
if SCALE != 1.0:
    from mathutils import Matrix
    me.transform(Matrix.Scale(SCALE, 4))
    for o in extras: o.data.transform(Matrix.Scale(SCALE, 4))
    if rig:
        bpy.context.view_layer.objects.active = rig; bpy.ops.object.mode_set(mode='EDIT')   # (before the rig is dropped)
        for eb in rig.data.edit_bones: eb.head *= SCALE; eb.tail *= SCALE
        bpy.ops.object.mode_set(mode='OBJECT')
co = [v.co for v in me.vertices]
print(f"EXPORT {NAME}: {max(c.x for c in co) - min(c.x for c in co):.3f} x {max(c.y for c in co) - min(c.y for c in co):.3f} x {max(c.z for c in co):.3f} m (scale {SCALE})")
if STATIC:   # the rig dropped: the mesh as it stands at rest, on its own
    for md in list(ob.modifiers):
        if md.type == 'ARMATURE': ob.modifiers.remove(md)
    mw = ob.matrix_world.copy(); ob.parent = None; ob.matrix_world = mw
    for vg in list(ob.vertex_groups): ob.vertex_groups.remove(vg)
    if rig: bpy.data.objects.remove(rig)
    rig = None
if STATIC:
    for o in extras:
        for md in list(o.modifiers): o.modifiers.remove(md)
        o.parent = None
        for vg in list(o.vertex_groups): o.vertex_groups.remove(vg)
for o in bpy.data.objects: o.select_set(o in (ob, rig) or o in extras)
bpy.context.view_layer.objects.active = rig or ob
if extras: print("EXPORT with", ", ".join(o.name for o in extras))
tri = ob.modifiers.new("tri", 'TRIANGULATE')
for t in TIERS:
    path = os.path.join(OUT, f"{NAME}_{t}", f"{NAME}_{t}_model.fbx")
    if os.path.exists(path): raise SystemExit("exists, kept: " + path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if STATIC: me.materials[0].name = f"{NAME}_{t}"
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={'MESH'} if STATIC else {'ARMATURE', 'MESH'},
                             global_scale=1.0, apply_unit_scale=True, apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y',
                             bake_space_transform=False, add_leaf_bones=False, primary_bone_axis='Y', secondary_bone_axis='X',
                             mesh_smooth_type='FACE', use_mesh_modifiers=True, bake_anim=False, path_mode='COPY', embed_textures=False)
    print("EXPORTED", path)
ob.modifiers.remove(tri)
