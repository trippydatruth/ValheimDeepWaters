# Fills jaw weights from two jaw bones the user placed (an upper and a lower, pointing forward from the hinge): every
# point ahead of the hinge goes to whichever jaw bone's segment is nearer, fading into the existing head weights over
# VDW_JAW_BLEND (share of the jaw's length) behind the snout-side of the hinge; points far out sideways (fins) are left
# alone. Renames the bones to the group names, parents them to Head, saves to VDW_SAVE_TO.
#   blender -b fish.blend --python auto_jaw_weights.py
#   env: VDW_SAVE_TO, VDW_UPPER_BONE / VDW_LOWER_BONE (the user's bones), VDW_UPPER / VDW_LOWER (group names: Upper.Jaw /
#        Lower.Jaw), VDW_JAW_BLEND (0.35), VDW_JAW_WIDTH (x the head's half width; 1.15)
import bpy, os
import numpy as np
UB, LB = os.environ["VDW_UPPER_BONE"], os.environ["VDW_LOWER_BONE"]
UG, LG = os.environ.get("VDW_UPPER", "Upper.Jaw"), os.environ.get("VDW_LOWER", "Lower.Jaw")
BLEND = float(os.environ.get("VDW_JAW_BLEND", "0.35")); JW = float(os.environ.get("VDW_JAW_WIDTH", "1.15"))
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
mesh = next(o for o in bpy.data.objects if o.type == 'MESH' and o.parent == arm)
for o in (arm, mesh): o.hide_set(False); o.hide_viewport = False
bu, bl = arm.data.bones[UB], arm.data.bones[LB]
hu, tu, hl, tl = (np.array(v[:]) for v in (bu.head_local, bu.tail_local, bl.head_local, bl.tail_local))
hinge_y = float((hu[1] + hl[1]) / 2); jaw_len = float(max(abs(tu[1] - hu[1]), abs(tl[1] - hl[1])))
to_arm = arm.matrix_world.inverted() @ mesh.matrix_world
co = np.array([(to_arm @ v.co)[:] for v in mesh.data.vertices])
def seg(p, a, b):
    ab = b - a; t = np.clip(((p - a) @ ab) / max(ab @ ab, 1e-12), 0, 1)
    return np.linalg.norm(p - (a + np.outer(t, ab)), axis=1)
du, dl = seg(co, hu, tu), seg(co, hl, tl)
# fade: 1 ahead of the hinge, easing to 0 over BLEND x the jaw length behind it (toward the tail = +y)
k = np.clip((hinge_y + BLEND * jaw_len - co[:, 1]) / max(BLEND * jaw_len, 1e-6), 0, 1); k = k * k * (3 - 2 * k)
def half_width(y):
    w = co[np.abs(co[:, 1] - y) < 0.01 * jaw_len * 4]
    return float(np.percentile(np.abs(w[:, 0]), 70)) if len(w) > 4 else 1e9
hw = np.array([half_width(y) for y in co[:, 1]]) if len(co) < 40000 else np.full(len(co), 1e9)
k[np.abs(co[:, 0]) > JW * hw] = 0
gu = mesh.vertex_groups.get(UG) or mesh.vertex_groups.new(name=UG); gl = mesh.vertex_groups.get(LG) or mesh.vertex_groups.new(name=LG)
nu = nl = 0
for i, v in enumerate(mesh.data.vertices):
    if k[i] <= 0.001: continue
    for g in v.groups:
        if g.group not in (gu.index, gl.index): g.weight *= (1 - k[i])
    if du[i] <= dl[i]: gu.add([i], float(k[i]), 'REPLACE'); nu += 1
    else: gl.add([i], float(k[i]), 'REPLACE'); nl += 1
for o in bpy.context.view_layer.objects: o.select_set(o == mesh)
bpy.context.view_layer.objects.active = mesh
bpy.ops.object.vertex_group_normalize_all(lock_active=False)
print(f"  hinge at y {hinge_y:.3f}, jaw {jaw_len:.3f} m long: {nu} points on {UG}, {nl} on {LG}")
# bones: named like their groups, riding on the head
bpy.context.view_layer.objects.active = arm
for o in bpy.context.view_layer.objects: o.select_set(o == arm)
bpy.ops.object.mode_set(mode='EDIT')
eb = arm.data.edit_bones
for old, new in ((UB, UG), (LB, LG)):
    b = eb[old]; b.name = new; b.use_deform = True
    if "Head" in eb and b.parent != eb["Head"]: b.parent = eb["Head"]; b.use_connect = False
bpy.ops.object.mode_set(mode='OBJECT')
print(f"  bones renamed {UB} -> {UG}, {LB} -> {LG}, parented to Head")
bpy.ops.wm.save_as_mainfile(filepath=os.environ["VDW_SAVE_TO"]); print("  saved", os.environ["VDW_SAVE_TO"])
