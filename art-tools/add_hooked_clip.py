# Adds a "Hooked" clip to a worm-like eel rig (Head, Spine..SpineN along +Y, head at -Y): the hook goes through
# the front, the body hangs down from it and wriggles in a C-curl that rolls from side to side, the tail flicking.
# 30 frames, loops. env: VDW_SAVE_TO (optional; else saves in place)
import bpy, math, os
import numpy as np
from mathutils import Quaternion, Vector

arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
mesh = next(o for o in bpy.data.objects if o.type == 'MESH')
HAS = {b.name for b in arm.data.bones}
SP = [n for n in ["Spine"] + [f"Spine{k}" for k in range(1, 40)] if n in HAS]
N = len(SP)
WX, WZ = Vector((1, 0, 0)), Vector((0, 0, 1))
def q(name, axis, deg):
    m = arm.data.bones[name].matrix_local.to_3x3()
    return Quaternion((m.inverted() @ axis).normalized(), math.radians(deg))

def pose(ph):
    s = math.sin
    out = {}
    # hang: the first segment turns the body straight down from the hook
    out["Head"] = q("Head", WX, 25 + 8 * s(ph + 0.5))                 # the head end lifts a little against the hook
    for k, n in enumerate(SP):
        u = (k + 0.5) / N
        if k == 0:
            hang = -80                                                   # body drops from the hook
        else:
            # C-curl that tightens and relaxes, and swings which way it curls (the wriggle)
            curl = 7 + (8 + 4 * s(2 * ph - u * 4)) * s(ph - u * 2.2)      # always a little curled, rolling one way then the other
            hang = curl
        side = 9 * u * s(ph * 2 - u * 5) + 4 * s(ph + 1.3)             # tail flicking side to side
        out[n] = q(n, WX, hang) @ q(n, WZ, side if k else 4 * s(ph))
    return out

old = bpy.data.actions.get("Hooked")
if old: bpy.data.actions.remove(old)
act = bpy.data.actions.new("Hooked"); act.use_fake_user = True
keep = arm.animation_data.action; arm.animation_data.action = act
LEN = 30
names = [b.name for b in arm.data.bones if b.name != "Root"]
for f in range(LEN + 1):
    p = pose(2 * math.pi * f / LEN)
    for n in names:
        pb = arm.pose.bones[n]; pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = p.get(n, Quaternion()); pb.keyframe_insert("rotation_quaternion", frame=f, group=n)
act.use_frame_range = True; act.use_cyclic = True; act.frame_start, act.frame_end = 0, LEN
for fc in act.fcurves:
    if not any(m.type == 'CYCLES' for m in fc.modifiers): fc.modifiers.new('CYCLES')

sc = bpy.context.scene
def verts(f):
    sc.frame_set(f); dg = bpy.context.evaluated_depsgraph_get(); ev = mesh.evaluated_get(dg)
    c = np.array([v.co[:] for v in ev.to_mesh().vertices]); ev.to_mesh_clear(); return c
fr = [verts(f) for f in range(LEN + 1)]
st = [np.linalg.norm(fr[f + 1] - fr[f], axis=1).max() for f in range(LEN)]
z = fr[0][:, 2]
print(f"\nHOOKED: smallest frame-to-frame {min(st) * 1000:.1f} mm, largest {max(st) * 1000:.1f} mm, loop seam {np.abs(fr[0] - fr[LEN]).max() * 1000:.2f} mm, hangs {(z.max() - z.min()) * 100:.1f} cm deep")
arm.animation_data.action = keep; sc.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=os.environ.get("VDW_SAVE_TO") or bpy.data.filepath)
print("HOOKED SAVED")


