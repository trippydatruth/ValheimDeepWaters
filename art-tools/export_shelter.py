# Exports an ice-fishing shelter (build_shelters.py) for Unity: <out>/<key>/<key>_model.fbx, Z up -> Y up like the
# other pieces. The lavvu and the Ship-Tent: one mesh on their baked atlas (bake_wood_cooler.py VDW_TIER=<piece>), the
# maps copied beside it renamed to the key. The igloo (VDW_SPLIT=1): split by material into the meshes "ice" and
# "snow" - no maps; in game they're given Valheim's own ice and snow (IceShelters.UseVanillaMaterials, by name).
#   blender -b "<shelter_vN>/Blender Files/<piece>.blend" --factory-startup --python export_shelter.py
#   env: VDW_OUT, VDW_KEY (piece_shelter_<piece>), VDW_TEX (the bake's bait_<piece> folder; not for the igloo),
#        VDW_SPLIT=1 (the igloo). New files only.
# With VDW_SPLIT the file's other meshes are joined in first (the igloo's bench and its hide's "fur", hide_fur.py), and
# split by material too: a part with maps of its own ("fur", "blanket") has them in VDW_TEX as <part>_Unity_*, copied
# as they are (the importer gives a mesh the set named after it).
import bpy, os, shutil, glob
OUT, KEY = os.environ["VDW_OUT"], os.environ["VDW_KEY"]
TEX, SPLIT = os.environ.get("VDW_TEX", ""), os.environ.get("VDW_SPLIT") == "1"
path = os.path.join(OUT, KEY, KEY + "_model.fbx")
if os.path.exists(path): raise SystemExit("exists, kept: " + path)
os.makedirs(os.path.dirname(path), exist_ok=True)
ob = bpy.data.objects["bait"]
if bpy.context.object and bpy.context.object.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
extra = [o for o in bpy.data.objects if o is not ob and o.type == 'MESH' and SPLIT]
for o in list(bpy.data.objects):
    if o is not ob and o not in extra: bpy.data.objects.remove(o)
if extra:
    for o in bpy.context.view_layer.objects: o.hide_set(False); o.select_set(o is ob or o in extra)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.join()
    for o in list(bpy.data.objects):                                    # (5.3 keeps the joined ones, unlinked)
        if o is not ob and not o.users_collection: bpy.data.objects.remove(o)
me = ob.data
if "Grain" in me.uv_layers: me.uv_layers.remove(me.uv_layers["Grain"])
for o in bpy.context.view_layer.objects: o.select_set(o is ob)
bpy.context.view_layer.objects.active = ob
if SPLIT:
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.separate(type='MATERIAL'); bpy.ops.object.mode_set(mode='OBJECT')
    for o in list(bpy.data.objects):
        n = o.data.materials[0].name.split(".")[0]
        o.name = o.data.name = n
        o.data.materials.clear(); o.data.materials.append(bpy.data.materials.new(n))
else:
    me.materials.clear(); me.materials.append(bpy.data.materials.new(KEY))
    ob.name = me.name = KEY
for o in bpy.data.objects: o.select_set(True)
bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={'MESH'}, global_scale=1.0, apply_unit_scale=True,
                         apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y', bake_space_transform=True,
                         mesh_smooth_type='FACE', bake_anim=False, path_mode='STRIP', embed_textures=False)
if TEX:
    maps = glob.glob(os.path.join(TEX, "*_Unity_*.png"))
    if not maps: raise SystemExit("no maps in " + TEX)
    for f in maps:
        name = os.path.basename(f) if SPLIT else KEY + "_Unity_" + os.path.basename(f).split("_Unity_", 1)[1]
        shutil.copy(f, os.path.join(os.path.dirname(path), name))
print("EXPORTED", path, ", ".join(f"{o.name} {len(o.data.polygons)} faces" for o in bpy.data.objects))
