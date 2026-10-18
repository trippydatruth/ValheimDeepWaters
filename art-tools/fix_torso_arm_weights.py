# The coat's (and shirt's / overalls') torso shouldn't follow the arms: on points inside the shoulder line, the share
# of arm bones (shoulder / upper arm / forearm / hand) is moved to the spine bone at that height, easing in across the
# armpit so the sleeve still follows the arm. Writes a new .blend.
#   blender -b rig.blend --python fix_torso_arm_weights.py      env: VDW_SAVE_TO, VDW_EDGE (cm in from the armpit, 4)
import bpy, os
SAVE_TO = os.environ["VDW_SAVE_TO"]; EDGE = float(os.environ.get("VDW_EDGE", "4"))
arm = bpy.data.objects["Armature"]
def head(n): return arm.matrix_world @ arm.data.bones[n].head_local
ARMB = [b.name for b in arm.data.bones if any(k in b.name for k in ("Shoulder", "Arm", "Hand", "Thumb", "Index", "Middle", "Ring", "Pinky"))]
# where the torso ends sideways: just inside the upper-arm joints
sx = min(abs(head("LeftArm").x), abs(head("RightArm").x))
spines = sorted([(head(n).z, n) for n in ("Hips", "Spine", "Spine1", "Spine2", "Neck")])
def spine_at(z):
    best = spines[0][1]
    for hz, n in spines:
        if z >= hz: best = n
    return best
for name in ("coat", "shirt", "overalls"):
    ob = bpy.data.objects.get(name)
    if ob is None: continue
    moved = 0
    for v in ob.data.vertices:
        p = ob.matrix_world @ v.co
        inner = sx - EDGE                                  # fully torso inside this; full arm at the joint
        k = 1.0 if abs(p.x) <= inner else max(0.0, (sx - abs(p.x)) / EDGE)
        if k <= 0.0 or p.z > head("Neck").z: continue
        armw = sum(g.weight for g in v.groups if ob.vertex_groups[g.group].name in ARMB)
        if armw < 1e-3: continue
        take = armw * k
        for g in v.groups:
            if ob.vertex_groups[g.group].name in ARMB: g.weight *= (1 - k)
        sp = spine_at(p.z)
        vg = ob.vertex_groups.get(sp) or ob.vertex_groups.new(name=sp)
        cur = next((g.weight for g in v.groups if ob.vertex_groups[g.group].name == sp), 0.0)
        vg.add([v.index], cur + take, 'REPLACE'); moved += 1
    print(f"  {name}: {moved} torso points taken off the arm bones (torso inside |x| {sx:.1f} cm)")
# the boots' soles: with the foot, so a lifted foot's sole can't drop through the bottom of the boot
b = bpy.data.objects.get("boots")
if b is not None:
    n = 0
    for v in b.data.vertices:
        p = b.matrix_world @ v.co
        if p.z > 6.0: continue
        side = "Left" if any(b.vertex_groups[g.group].name.startswith("Left") for g in v.groups if g.weight > 0.3) else "Right"
        for g in v.groups: g.weight = 0.0
        (b.vertex_groups.get(side + "Foot") or b.vertex_groups.new(name=side + "Foot")).add([v.index], 1.0, 'REPLACE'); n += 1
    print(f"  boots: {n} sole points on the foot bones")
bpy.ops.wm.save_as_mainfile(filepath=SAVE_TO, copy=True); print("  saved", SAVE_TO)
