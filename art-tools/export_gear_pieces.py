# Exports hand-edited worn gear pieces (fisher_gear_ingame_*.blend: belt, buckle, cuff, boot_rims ...) exactly as the user
# shaped and weighted them: pieces + fitref (plain mesh, for the mod to line it up) + skeleton, in centimetres, like
# build_coat_trim.py / build_boot_rims.py did. Each piece's material is renamed for its textures (<mat>_Unity_*.png).
#   blender -b fisher_gear_ingame_v2.blend --python export_gear_pieces.py
#   env: VDW_OUT (fbx path, never overwrites), VDW_PARTS "object=material,..." (e.g. "belt=belt,buckle=buckle,cuff=cuff")
import bpy, os
from mathutils import Matrix

OUT = os.environ["VDW_OUT"]
if os.path.exists(OUT): raise SystemExit("exists, kept: " + OUT)
PARTS = dict(kv.split("=") for kv in os.environ["VDW_PARTS"].split(","))
for o in list(bpy.data.objects):
    if o.mode != 'OBJECT' and o.name in bpy.context.view_layer.objects:
        bpy.context.view_layer.objects.active = o; bpy.ops.object.mode_set(mode='OBJECT')
arm = bpy.data.objects["Armature"]
if arm.matrix_world != Matrix.Identity(4): raise SystemExit("the armature isn't at the origin - the cm conversion assumes it is")
arm.animation_data_clear()   # a blend with the recorded game poses keyed (Game_anims_*) would re-pose the rig over the reset
for pb in arm.pose.bones: pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.rotation_euler = (0, 0, 0); pb.scale = (1, 1, 1)
bpy.context.view_layer.update()
fit = bpy.data.objects["fitref"]
parts = []
for name, mat in PARTS.items():
    o = bpy.data.objects[name]
    mw = o.matrix_world.copy(); o.parent = None; o.data.transform(mw); o.matrix_world = Matrix.Identity(4)
    missing = [g.name for g in o.vertex_groups if g.name not in arm.data.bones]
    if missing: raise SystemExit(f"{name}: vertex groups with no bone: {missing}")
    loose = sum(1 for v in o.data.vertices if not any(g.weight > 0 for g in v.groups))
    if loose: raise SystemExit(f"{name}: {loose} points have no weights")
    o.data.materials.clear(); o.data.materials.append(bpy.data.materials.new(mat))
    parts.append(o); print(f"PART {name}: {len(o.data.polygons)} faces, material {mat}")
for o in list(bpy.data.objects):
    if o is not arm and o is not fit and o not in parts: bpy.data.objects.remove(o)
for m in [m for m in fit.modifiers if m.type == 'ARMATURE']: fit.modifiers.remove(m)
fit.data.transform(fit.matrix_world); fit.parent = None; fit.matrix_world = Matrix.Identity(4)
# centimetres
S = Matrix.Scale(100.0, 4)
for o in bpy.data.objects: o.select_set(o == arm)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
for b in arm.data.edit_bones: b.head = S @ b.head; b.tail = S @ b.tail
bpy.ops.object.mode_set(mode='OBJECT')
fit.data.transform(S)
for o in parts:
    o.data.transform(S); o.parent = arm
    o.modifiers.clear(); o.modifiers.new("Armature", 'ARMATURE').object = arm
    for p in o.data.polygons: p.use_smooth = True
for o in bpy.data.objects: o.hide_set(False); o.hide_viewport = False; o.hide_select = False; o.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.export_scene.fbx(filepath=OUT, use_selection=True, object_types={'MESH', 'ARMATURE'}, global_scale=1.0, apply_unit_scale=True,
                         add_leaf_bones=False, use_armature_deform_only=False, armature_nodetype='NULL',
                         apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y', bake_space_transform=True,
                         mesh_smooth_type='FACE', bake_anim=False, path_mode='STRIP', embed_textures=False, colors_type='LINEAR')
print("EXPORTED", OUT)
