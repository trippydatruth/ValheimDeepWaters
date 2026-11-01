# Puts the gear rig's bones back at their proper rest positions (copied from a reference blend whose rig is right) and,
# when VDW_POSES is given, re-keys the recorded game poses (as Game_anims_* blends have them) on the fixed rig.
# The meshes and weights are left exactly as they are; only bones that moved are reset. Saves a new file.
#   blender -b <edited.blend> --python fix_rig_rest.py
#   env: VDW_OUT (new .blend, never overwrites), VDW_REF (a blend with the right rig, e.g. Ingame_bake_v1\fisher_gear_ingame_v2.blend),
#        VDW_POSES (optional: folder of the game's pose_<name>.json recordings, to re-key the animation)
import bpy, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

OUT = os.environ["VDW_OUT"]
if os.path.exists(OUT): raise SystemExit("exists, kept: " + OUT)
for o in list(bpy.data.objects):
    if o.mode != 'OBJECT' and o.name in bpy.context.view_layer.objects:
        bpy.context.view_layer.objects.active = o; bpy.ops.object.mode_set(mode='OBJECT')
arm = bpy.data.objects["Armature"]
with bpy.data.libraries.load(os.environ["VDW_REF"]) as (src, dst): dst.armatures = list(src.armatures)
ref = next(a for a in dst.armatures if "Hips" in a.bones)
want = {b.name: (b.head_local.copy(), b.tail_local.copy(), b.matrix_local.copy()) for b in ref.bones}
for o in bpy.data.objects: o.select_set(o == arm)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
moved = []
for eb in arm.data.edit_bones:
    if eb.name not in want: continue
    h, t, m = want[eb.name]
    if (eb.head - h).length > 1e-4 or (eb.tail - t).length > 1e-4:
        moved.append(f"{eb.name} {(eb.head - h).length * 100:.1f} cm")
        eb.head = h; eb.tail = t; eb.align_roll(m.to_3x3().col[2])
bpy.ops.object.mode_set(mode='OBJECT')
for a in dst.armatures: bpy.data.armatures.remove(a)
print("RIG reset", len(moved), "bones:", ", ".join(moved) or "none")

poses = os.environ.get("VDW_POSES")
if poses:
    import valheim_pose
    P = valheim_pose.Poses(poses, arm)   # also drops the old (moved-rig) keys
    sc = bpy.context.scene; sc.render.fps = 15; sc.render.fps_base = 1
    for pb in arm.pose.bones: pb.rotation_mode = 'QUATERNION'
    arm.animation_data_create(); act = bpy.data.actions.new("valheim_poses"); act.use_fake_user = True; arm.animation_data.action = act
    def key(f):
        for n in P.names:
            pb = arm.pose.bones[n]
            for path in ("location", "rotation_quaternion", "scale"): pb.keyframe_insert(path, frame=f)
    for m in list(sc.timeline_markers): sc.timeline_markers.remove(m)
    P.reset(); bpy.context.view_layer.update(); key(0); sc.timeline_markers.new("rest", frame=0)
    first = ("idle", "run", "jog", "sneak", "crouch", "sit_chair", "sit_ground")
    order = [c for c in first if c in P.data["clips"]] + [c for c in P.data["clips"] if c not in first]
    f0, GAP = 10, 10
    for clip in order:
        sc.timeline_markers.new(clip, frame=f0)
        for i in range(P.frames(clip)): P.apply(clip, i); key(f0 + i)
        print("KEYED", clip, f0, "-", f0 + P.frames(clip) - 1); f0 += P.frames(clip) + GAP
    fcs = list(getattr(act, "fcurves", []) or [])
    for layer in getattr(act, "layers", []):
        for strip in layer.strips:
            for cb in strip.channelbags: fcs += list(cb.fcurves)
    for fc in fcs:
        for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
    sc.frame_start = 0; sc.frame_end = f0 - GAP; sc.frame_set(10)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT, copy=True); print("SAVED", OUT)
