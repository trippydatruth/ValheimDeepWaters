# Keys an upper and a lower jaw bone (the user's Upper.Jaw / Lower.Jaw) into every clip of a fish whose model has its
# mouth open: works out how far each bone turns (about the armature's X axis) for the two lips to meet, then keys
#   Swim (the idle swim): shut, breathing a hair;  Thrash: snapping;  Flop: gasping;  Hooked: chomping.
# Every clip still loops. blender -b fish.blend --python key_jaw_bones.py
#   env: VDW_SAVE_TO, VDW_UPPER (Upper.Jaw), VDW_LOWER (Lower.Jaw), VDW_SHUT_SHARE (where the lips meet, 0 = upper lip's
#        height .. 1 = lower lip's; 0.5), VDW_OVERCLOSE (extra turn so the lips press together, 1.05)
#   VDW_UPPER=- : only a lower jaw (e.g. a download's own jaw bone): it closes up to the upper lip, found on the mesh as
#        the lowest point of the snout that the jaw doesn't move
#   VDW_OPEN_DEG=n : the mouth is modelled SHUT - rest stays shut and the jaw opens (drops) up to n degrees instead
import bpy, math, os
# a file saved in Edit / Weight Paint mode: back to Object Mode first (in Edit Mode the armature modifier is off, so
# nothing deforms, and edits in progress aren't in the mesh data)
for _o in list(bpy.data.objects):
    if _o.mode != 'OBJECT' and _o.name in bpy.context.view_layer.objects:
        bpy.context.view_layer.objects.active = _o
        try: bpy.ops.object.mode_set(mode='OBJECT')
        except RuntimeError: pass
from mathutils import Matrix
UP, LO = os.environ.get("VDW_UPPER", "Upper.Jaw"), os.environ.get("VDW_LOWER", "Lower.Jaw")
SHARE = float(os.environ.get("VDW_SHUT_SHARE", "0.5")); OVER = float(os.environ.get("VDW_OVERCLOSE", "1.05"))
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
arm.data.pose_position = 'POSE'      # saved in Rest Position, nothing would move (the sign test below would fail too)
keep =arm.animation_data.action if arm.animation_data else None
if arm.animation_data: arm.animation_data.action = None
for pb in arm.pose.bones: pb.rotation_mode = 'QUATERNION'; pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0)
bpy.context.view_layer.update()
bl = arm.data.bones[LO]
bu = arm.data.bones[UP] if UP != "-" else None
if bu: z_meet = bu.tail_local.z + (bl.tail_local.z - bu.tail_local.z) * SHARE
else:
    mesh = next(o for o in bpy.data.objects if o.type == 'MESH' and o.parent == arm)
    gi = mesh.vertex_groups[LO].index; to_arm = arm.matrix_world.inverted() @ mesh.matrix_world
    pts = [(to_arm @ v.co, next((g.weight for g in v.groups if g.group == gi), 0.0)) for v in mesh.data.vertices]
    y0 = min(p.y for p, w in pts); L_ = max(p.y for p, w in pts) - y0
    tip_y = bl.tail_local.y
    snout = [p.z for p, w in pts if w < 0.15 and abs(p.y - tip_y) < 0.03 * L_ and abs(p.x) < 0.02 * L_]
    z_meet = min(snout) if snout else bl.head_local.z
    print(f"  upper lip (lowest unmoved snout point near the jaw tip): z {z_meet:.3f}, from {len(snout)} points")
def local_q(bone, angle):
    r = bone.matrix_local.to_3x3()
    return (r.inverted() @ Matrix.Rotation(angle, 3, 'X') @ r).to_quaternion()
def shut_angle(bone):
    """angle about X that brings the bone's tip to z_meet (searched, then the sign checked on the posed bone)"""
    h, t = bone.head_local, bone.tail_local
    dy, dz = t.y - h.y, t.z - h.z; r = math.hypot(dy, dz)
    target = math.asin(max(-1.0, min(1.0, (z_meet - h.z) / r)))
    now = math.atan2(dz, abs(dy))
    a = (target - now) * OVER
    pb = arm.pose.bones[bone.name]
    for s in (1, -1):
        pb.rotation_quaternion = local_q(bone, s * a); bpy.context.view_layer.update()
        if abs(pb.tail.z - z_meet) < abs(t.z - z_meet) * 0.5: pb.rotation_quaternion = (1, 0, 0, 0); return s * a
    pb.rotation_quaternion = (1, 0, 0, 0); return -a
OPEN = float(os.environ.get("VDW_OPEN_DEG", "0"))
def drop_angle(bone, deg):        # the sign of turn that moves the tip down (opens a lower jaw / lifts an upper one)
    pb = arm.pose.bones[bone.name]; base = bone.tail_local.z
    pb.rotation_quaternion = local_q(bone, math.radians(deg)); bpy.context.view_layer.update(); down = pb.tail.z < base
    pb.rotation_quaternion = (1, 0, 0, 0); bpy.context.view_layer.update()
    return math.radians(deg) if down else -math.radians(deg)
if OPEN:
    al = drop_angle(bl, OPEN); au = -drop_angle(bu, OPEN * 0.25) if bu else 0.0
    print(f"  mouth modelled shut: {LO} opens {OPEN:.0f} deg")
else: au, al = (shut_angle(bu) if bu else 0.0), shut_angle(bl)
if not OPEN: print(f"  lips meet at z {z_meet:.3f}: {UP} turns {math.degrees(au):.1f} deg, {LO} {math.degrees(al):.1f} deg to shut")
def shut(name, t):          # 1 = shut, 0 = open as modelled
    n = name.lower()
    if "thrash" in n: return 1.0 - 0.9 * (0.5 - 0.5 * math.cos(2 * math.pi * t)) ** 2      # snaps open and shut
    if "flop" in n:   return 0.55 + 0.35 * math.cos(2 * math.pi * t)                       # gasping
    if "hook" in n:   return 0.6 + 0.4 * math.cos(4 * math.pi * t)                         # chomping
    return 0.96 + 0.04 * math.cos(2 * math.pi * t)                                         # swim / idle: shut
for act in bpy.data.actions:
    f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
    for bn, ang in (((UP, au), (LO, al)) if bu else ((LO, al),)):
        path = f'pose.bones["{bn}"].rotation_quaternion'
        for c in [c for c in act.fcurves if c.data_path == path]: act.fcurves.remove(c)
        cs = [act.fcurves.new(path, index=i, action_group=bn) for i in range(4)]
        for fr in range(f0, f1 + 1):
            s_ = shut(act.name, (fr - f0) / max(1, f1 - f0))
            q = local_q(arm.data.bones[bn], ang * ((1 - s_) if OPEN else s_))
            for i in range(4): cs[i].keyframe_points.insert(fr, q[i], options={'FAST'})
        for c in cs: c.update()
    print(f"  keyed {act.name} ({f0}-{f1})")
if arm.animation_data: arm.animation_data.action = keep or bpy.data.actions.get("Swim")
bpy.ops.wm.save_as_mainfile(filepath=os.environ["VDW_SAVE_TO"]); print("  saved", os.environ["VDW_SAVE_TO"])
