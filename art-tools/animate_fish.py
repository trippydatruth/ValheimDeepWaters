# Cleans up the rig and builds the Swim, Thrash and Flop actions for the Moder Scale Fish, then saves a new file.
#   blender -b moder_scale_fish_rigfixed.blend --python animate_fish.py      (VDW_SAVE_TO = output .blend)
#
# Every bone is keyed every frame from a formula, rotating around WORLD axes converted into each bone's own space,
# so the bend is right whatever each bone's roll is. Last frame = first frame, so every clip loops perfectly.
import bpy, math, os
from mathutils import Quaternion, Vector
# a file saved in Edit / Weight Paint mode: back to Object Mode first
for _o in list(bpy.data.objects):
    if _o.mode != 'OBJECT' and _o.name in bpy.context.view_layer.objects:
        bpy.context.view_layer.objects.active = _o
        try: bpy.ops.object.mode_set(mode='OBJECT')
        except RuntimeError: pass

SAVE_TO = os.environ.get("VDW_SAVE_TO", "")
FPS = 30
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
mesh = next((o for o in bpy.data.objects if o.type == 'MESH' and o.parent == arm), None) or next(o for o in bpy.data.objects if o.type == 'MESH')
scene = bpy.context.scene
scene.render.fps = FPS

# ---- clean-up: one bone collection holding every bone (the per-bone collections were only display groups)
for coll in list(arm.data.collections_all):
    arm.data.collections.remove(coll)
bones_coll = arm.data.collections.new("Bones")
for b in arm.data.bones:
    bones_coll.assign(b)
arm.data.pose_position = 'POSE'
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
for kind in ("Pectoral", "Pelvic"):
    for side in ("L", "R"):
        base, tip = arm.data.edit_bones.get(f"Fin.Upper.{kind}.{side}"), arm.data.edit_bones.get(f"Fin.Lower.{kind}.{side}")
        if base and tip and tip.parent != base:
            tip.parent = base
            tip.use_connect = (tip.head - base.tail).length < 0.01
            print("  fin tip attached:", tip.name, "->", base.name)
bpy.ops.object.mode_set(mode='OBJECT')
for md in mesh.modifiers:
    if md.type == 'ARMATURE':
        md.object = arm; md.use_vertex_groups = True; md.show_viewport = True; md.show_render = True

WORLD_Z = Vector((0, 0, 1))   # side to side (the swim bend)
WORLD_X = Vector((1, 0, 0))   # up and down (jaw, fin flaps)
WORLD_Y = Vector((0, 1, 0))   # roll along the body (head shake)

def local_axis(bone_name, world_axis):
    """A world axis expressed in the bone's own rest space (pose rotations are applied in that space)."""
    m = arm.data.bones[bone_name].matrix_local.to_3x3()
    return (m.inverted() @ world_axis).normalized()

def q(bone_name, world_axis, degrees):
    if bone_name not in arm.data.bones:
        return Quaternion()
    return Quaternion(local_axis(bone_name, world_axis), math.radians(degrees))

# The wave runs head to tail: Spine -> Spine1 -> Spine2 -> tail fin chains.
HAS = set(b.name for b in arm.data.bones)
SPINES = [n for n in ["Spine"] + [f"Spine{k}" for k in range(1, 10)] if n in HAS]
WAVE = [(n, i) for i, n in enumerate(SPINES)]
for k in range(1, 4):  # the tail fin chains continue the wave
    WAVE += [(f"{side}.Tail.Fin{k}", len(SPINES) + k - 1) for side in ("Top", "Bottom") if f"{side}.Tail.Fin{k}" in HAS]
STEPS = max(i for _, i in WAVE) + 1 if WAVE else 1
def frac(i): return i / max(1, STEPS - 1)   # 0 at the front of the body, 1 at the tail tip
DORSAL = [n for n in ("Dorsal.Fin.1", "Dorsal.Fin.2", "Dorsal.Fin.3", "Dorsal.Fin.4") if n in HAS]
PECTORAL = [n for n in ("Fin.Upper.Pectoral.L", "Fin.Lower.Pectoral.L", "Fin.Upper.Pectoral.R", "Fin.Lower.Pectoral.R") if n in HAS]
PELVIC = [n for n in ("Fin.Upper.Pelvic.L", "Fin.Lower.Pelvic.L", "Fin.Upper.Pelvic.R", "Fin.Lower.Pelvic.R") if n in HAS]
ALL = [b.name for b in arm.data.bones if b.name != "Root"]

def fin(n, out_deg):
    """A fin swung away from the body by out_deg (negative = in toward it), mirrored for the left and right fins.
    The tip bone follows its base and only adds a little flex."""
    side = -1 if n.endswith(".L") else 1
    if ".Lower." in n: out_deg *= 0.35
    return q(n, WORLD_Z, side * out_deg)

def pose_for(clip, phase):
    """Rotation (quaternion) for every animated bone at this point of the loop (phase 0..2pi)."""
    out = {}
    s = math.sin
    if clip == "Swim":
        lag = 3.6 / STEPS   # the same S-wave whether the fish has 6 bones or 12
        for name, i in WAVE: out[name] = q(name, WORLD_Z, (5 + 23 * frac(i)) * s(phase - lag * i))
        out["Head"] = q("Head", WORLD_Z, -3 * s(phase))
        out["LowerJaw"] = q("LowerJaw", WORLD_X, 3 + 2 * s(phase))
        for k, n in enumerate(DORSAL): out[n] = q(n, WORLD_Z, 4 * s(phase - 0.5 - 0.4 * k))
        for n in PECTORAL: out[n] = fin(n, 10 + 10 * s(2 * phase))   # gentle paddling, never into the body
        for n in PELVIC: out[n] = fin(n, 6 + 6 * s(2 * phase + 1))
    elif clip == "Thrash":
        lag = 2.7 / STEPS
        # A C-curl snapping one way then the other, travelling down the body (staggered, so the body never
        # turns around all at once), plus a fast shiver on top: some part is always moving.
        for name, i in WAVE:
            curl = 14 * (0.4 + 1.0 * frac(i)) * s(phase - 0.3 * i * 6 / STEPS)
            shiver = 4 * s(3 * phase - 0.6 * i * 6 / STEPS)
            out[name] = q(name, WORLD_Z, (12 + 40 * frac(i)) * s(phase - lag * i) + curl + shiver)
        out["Head"] = q("Head", WORLD_Z, -10 * s(phase + 0.5) + 3 * s(3 * phase)) @ q("Head", WORLD_Y, 10 * s(2 * phase + 0.9))
        out["LowerJaw"] = q("LowerJaw", WORLD_X, 18 + 14 * s(2 * phase + 0.6))
        out["UpperJaw"] = q("UpperJaw", WORLD_X, -4 - 3 * s(2 * phase + 0.6))
        for k, n in enumerate(DORSAL): out[n] = q(n, WORLD_Z, 10 * s(phase - 0.3 * k))
        for n in PECTORAL: out[n] = fin(n, 18 + 16 * s(3 * phase))   # flared wide and beating hard
        for n in PELVIC: out[n] = fin(n, 10 + 10 * s(3 * phase + 1))
    else:  # Flop: tired C-curls one way then the other (on land the fish lies on its side, so this reads as flopping)
        c = s(phase); c = math.copysign(abs(c) ** 0.6, c)  # snappier at the ends, hangs at the curl
        # While it holds a curl the tail still flicks and the jaw gasps, so it's never frozen.
        for name, i in WAVE: out[name] = q(name, WORLD_Z, (15 + 15 * frac(i)) * c + (2 + 7.5 * frac(i)) * s(4 * phase - 0.5 * i * 6 / STEPS))
        out["Head"] = q("Head", WORLD_Z, -12 * c + 2 * s(4 * phase + 1))
        out["LowerJaw"] = q("LowerJaw", WORLD_X, 6 + 10 * abs(c) + 4 * s(3 * phase))
        for n in PECTORAL: out[n] = fin(n, 14 + 10 * s(4 * phase))   # splayed out, twitching
        for n in PELVIC: out[n] = fin(n, 8 + 6 * s(4 * phase + 1))
    return out

CLIPS = {"Swim": 30, "Thrash": 15, "Flop": 30}  # all divide 30, so one 30-frame timeline loops every clip

if arm.animation_data is None:
    arm.animation_data_create()
for pb in arm.pose.bones:
    pb.rotation_mode = 'QUATERNION'

made = []
for clip, length in CLIPS.items():
    old = bpy.data.actions.get(clip)
    if old: bpy.data.actions.remove(old)
    act = bpy.data.actions.new(clip)
    act.use_fake_user = True          # keeps it even when nothing uses it
    arm.animation_data.action = act
    for f in range(length + 1):       # frame "length" equals frame 0: a perfect loop
        phase = 2 * math.pi * f / length
        pose = pose_for(clip, phase)
        for name in ALL:
            pb = arm.pose.bones[name]
            pb.rotation_quaternion = pose.get(name, Quaternion())
            pb.keyframe_insert("rotation_quaternion", frame=f, group=name)
    act.use_frame_range = True
    act.use_cyclic = True             # Blender treats it as a loop
    act.frame_start, act.frame_end = 0, length
    # Repeat forever in Blender's timeline, with no held pose past the end.
    for fc in act.fcurves:
        if not any(m.type == 'CYCLES' for m in fc.modifiers):
            fc.modifiers.new('CYCLES')
    made.append((clip, length, len(act.fcurves)))

arm.animation_data.action = bpy.data.actions["Swim"]   # Swim is the default
scene.frame_start, scene.frame_end = 0, 29   # 30 frames; frame 30 is frame 0 again, so 29 -> 0 never repeats a pose
for pb in arm.pose.bones: pb.rotation_quaternion = Quaternion()

# Verify: the mesh actually moves over the Swim loop.
def verts(frame):
    scene.frame_set(frame)
    dg = bpy.context.evaluated_depsgraph_get()
    ev = mesh.evaluated_get(dg); co = [v.co.copy() for v in ev.to_mesh().vertices]; ev.to_mesh_clear(); return co
a, b = verts(0), verts(8)
moved = sum(1 for p, r in zip(a, b) if (p - r).length > 0.001)
loop = max((p - r).length for p, r in zip(verts(0), verts(30)))
print("\n===== ANIMATE =====")
# Smallest movement between any two consecutive frames of each clip (the loop seam included): 0 would be a freeze.
for clip in CLIPS:
    arm.animation_data.action = bpy.data.actions[clip]
    frames = [verts(f) for f in range(0, 31)]
    steps = [max((p - r).length for p, r in zip(frames[f], frames[f + 1])) for f in range(30)]
    print(f"  {clip}: smallest frame-to-frame movement {min(steps):.3f} m, largest {max(steps):.3f} m")
arm.animation_data.action = bpy.data.actions["Swim"]
print("  clips:", made)
print(f"  Swim frame 0 -> 8: {moved} of {len(a)} vertices moved; frame 0 vs 30 max difference {loop:.5f} m (0 = seamless)")
if SAVE_TO:
    scene.frame_set(0)
    bpy.ops.wm.save_as_mainfile(filepath=SAVE_TO, copy=True)
    print("  saved:", SAVE_TO)
print("===== END =====\n")
