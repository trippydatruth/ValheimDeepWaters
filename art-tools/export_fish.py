# Exports a rigged, animated fish as FBX for Unity (and Valheim): metres, -Z forward / Y up baked in, no leaf bones,
# deform bones only, every action baked as its own clip.   blender -b fish.blend --python export_fish.py
import bpy, os
# a file saved in Edit / Weight Paint mode: back to Object Mode first (in Edit Mode the armature modifier is off, so
# nothing deforms, and edits in progress aren't in the mesh data)
for _o in list(bpy.data.objects):
    if _o.mode != 'OBJECT' and _o.name in bpy.context.view_layer.objects:
        bpy.context.view_layer.objects.active = _o
        try: bpy.ops.object.mode_set(mode='OBJECT')
        except RuntimeError: pass

OUT = os.environ["VDW_FBX_OUT"]
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
meshes = [o for o in bpy.data.objects if o.type == 'MESH' and o.parent == arm]   # usually one; the worm mound has two

bpy.ops.object.mode_set(mode='OBJECT') if bpy.context.object and bpy.context.object.mode != 'OBJECT' else None
arm.data.pose_position = 'POSE'   # a file saved in Rest Position would bake every clip motionless
for o in [arm] + meshes:     # hidden objects can't be selected, so they'd be left out (the user hides the rig)
    o.hide_set(False); o.hide_viewport = False; o.hide_select = False
for o in bpy.context.view_layer.objects:
    o.select_set(False)
arm.select_set(True)
for m in meshes: m.select_set(True)
bpy.context.view_layer.objects.active = arm
for pb in arm.pose.bones:  # export from the rest pose; the clips carry the motion
    pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.scale = (1, 1, 1)
bpy.context.scene.frame_set(0)

bpy.ops.export_scene.fbx(
    filepath=OUT,
    use_selection=True,
    object_types={'ARMATURE', 'MESH'},
    global_scale=1.0,
    apply_unit_scale=True,
    apply_scale_options='FBX_SCALE_ALL',
    axis_forward='-Z', axis_up='Y',
    bake_space_transform=True,          # "Apply Transform": no -90 X rotation on the Unity side
    mesh_smooth_type='FACE',
    use_mesh_modifiers=False,           # the armature deforms it in Unity, so export the undeformed mesh
    add_leaf_bones=False,
    primary_bone_axis='Y', secondary_bone_axis='X',
    use_armature_deform_only=True,
    armature_nodetype='NULL',
    bake_anim=True,
    bake_anim_use_all_bones=True,
    bake_anim_use_nla_strips=False,
    bake_anim_use_all_actions=True,     # Swim, Thrash and Flop each become a clip
    bake_anim_force_startend_keying=True,
    bake_anim_step=1.0,
    bake_anim_simplify_factor=0.0,      # keep loops exact
    path_mode='COPY', embed_textures=True,
)
print("EXPORTED", OUT, os.path.getsize(OUT), "bytes")
