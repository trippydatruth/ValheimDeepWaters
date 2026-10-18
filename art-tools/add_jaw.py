# Gives a rigged fish with an OPEN mouth a working jaw: finds the lower jaw, adds a Jaw bone hinged at the corner of the
# mouth (parented to the head), weights the lower jaw and its teeth to it, and keys it into every clip - Swim breathes
# slowly, Thrash snaps shut, Flop gasps, Hooked (if any) chomps - every clip still looping seamlessly.
#   The mesh must lie along Y with its head toward -Y (as rig_fish / rig_eel leave it).
#   Finding the mouth: along the snout, the vertices on the midline (|x| small) have an empty gap between the roof and
#   the floor of an open mouth; the mouth runs back to where that gap closes (the corner = the hinge). A fish whose
#   mouth is closed has no such gap and is left alone.
#   blender -b fish.blend --python add_jaw.py      env: VDW_SAVE_TO (new .blend), VDW_JAW_PREVIEW (png prefix, optional),
#        VDW_JAW_GAP (smallest gap, share of the head's height; default 0.06), VDW_JAW_MAX_DEG (largest close, default 35)
import bpy, math, os
import numpy as np
from mathutils import Matrix, Vector

SAVE_TO = os.environ["VDW_SAVE_TO"]
GAP_SHARE = float(os.environ.get("VDW_JAW_GAP", "0.06"))
MAX_DEG = float(os.environ.get("VDW_JAW_MAX_DEG", "35"))
PREVIEW = os.environ.get("VDW_JAW_PREVIEW", "")

arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
mesh = max((o for o in bpy.data.objects if o.type == 'MESH' and any(m.type == 'ARMATURE' for m in o.modifiers)),
           key=lambda o: len(o.data.vertices))
if "Jaw" in arm.data.bones:
    raise SystemExit("already has a Jaw bone")

# ---- 1. find the open mouth (rest pose, in the armature's space)
to_arm = arm.matrix_world.inverted() @ mesh.matrix_world
co = np.array([(to_arm @ v.co)[:] for v in mesh.data.vertices])
lo, hi = co.min(0), co.max(0)
L = hi[1] - lo[1]
head = co[co[:, 1] < lo[1] + 0.3 * L]
H = float(np.percentile(head[:, 2], 98) - np.percentile(head[:, 2], 2))
thr = GAP_SHARE * H

slices = []                                     # (y, gap centre z, gap bottom z, gap top z, gap size)
for f in np.arange(0.0, 0.32, 0.01):
    y0 = lo[1] + f * L
    w = co[np.abs(co[:, 1] - y0) < 0.008 * L]
    if len(w) < 4: continue
    half = float(np.percentile(np.abs(w[:, 0]), 90))
    mid = w[np.abs(w[:, 0]) < max(0.18 * half, 0.004 * L)]
    if len(mid) < 4: continue
    z = np.sort(mid[:, 2])
    g = np.diff(z)
    i = int(np.argmax(g))
    if g[i] > thr:
        slices.append((y0, (z[i] + z[i + 1]) / 2, z[i], z[i + 1], g[i]))
    elif slices and y0 - slices[-1][0] > 0.025 * L:
        break                                   # the gap has closed: past the corner of the mouth

print(f"\n===== JAW =====\n  length {L:.2f} m, head height {H:.2f} m, gap needed {thr:.3f} m, mouth slices {len(slices)}")
# A mouth opened only a crack is too thin to find: VDW_JAW_LINE="z at the snout,z at the corner" (with VDW_JAW_CORNER
# and VDW_JAW_CLOSE_DEG) gives the line between the lips by hand.
manual = os.environ.get("VDW_JAW_LINE")
if manual:
    z_front, z_back = (float(x) for x in manual.split(","))
    slices = [(float(lo[1]), z_front, z_front, z_front, 0.0)]
elif len(slices) < 3:
    print("  no open mouth found - nothing changed")
    raise SystemExit(0)

ys = np.array([s[0] for s in slices]); zc = np.array([s[1] for s in slices])
y_nose, y_corner = float(ys.min()), float(ys.max())
# The gap on the midline often closes (tongue, mouth floor) before the lips meet at the side; VDW_JAW_CORNER (share of the
# length from the nose) puts the hinge where the lips really meet, the mouth line carried back to it in a straight line.
fit = np.polyfit(ys, zc, 1) if len(ys) > 1 else None
if os.environ.get("VDW_JAW_CORNER"):
    y_corner = lo[1] + float(os.environ["VDW_JAW_CORNER"]) * L
def gap_z(y):
    if manual: return float(np.interp(y, [y_nose, y_corner], [z_front, z_back]))
    return float(np.interp(y, ys, zc)) if y <= ys.max() else float(np.polyval(fit, y))
hinge = Vector((0.0, y_corner, gap_z(y_corner)))
front = min(slices, key=lambda s: s[0])
# how far it turns to shut: the widest part of the opening as seen from the hinge (teeth can make the very front read
# narrow), a little extra so the lips meet; VDW_JAW_CLOSE_DEG sets it by hand
if os.environ.get("VDW_JAW_CLOSE_DEG"):
    close = math.radians(float(os.environ["VDW_JAW_CLOSE_DEG"]))
else:
    widest = max((math.atan2(s[4], max(1e-4, y_corner - s[0])) for s in slices if y_corner - s[0] > 0.01 * L), default=0.0)
    close = min(math.radians(MAX_DEG), widest * 1.15)
print(f"  mouth from y {y_nose:.3f} to the corner at {y_corner:.3f} (hinge z {hinge.z:.3f}); it closes in {math.degrees(close):.1f} deg")

# ---- 2. the Jaw bone, under the head
bpy.context.view_layer.objects.active = arm
for o in bpy.context.view_layer.objects: o.select_set(o == arm)
bpy.ops.object.mode_set(mode='EDIT')
eb = arm.data.edit_bones
parent = eb.get("Head") or next((b for b in eb if b.parent is None), None)
jaw = eb.new("Jaw")
jaw.head = hinge
jaw.tail = Vector((0.0, lo[1] + 0.02 * L, front[2]))      # out to the lower lip at the snout
jaw.roll = 0.0
jaw.parent = parent
jaw.use_deform = True
bpy.ops.object.mode_set(mode='OBJECT')

# ---- 3. weights: the lower jaw (below the gap, ahead of the corner) follows Jaw, easing into the head near the hinge
blend = float(os.environ.get("VDW_JAW_BLEND", "0.3")) * (y_corner - y_nose)   # longer: the skin bends, not folds
vg = mesh.vertex_groups.new(name="Jaw")
moved = 0
# fins sticking out sideways (big pectorals, gill covers) never go with the jaw: only points within the head's own
# width at that slice (VDW_JAW_WIDTH x the slice's 70th-percentile half width)
JW = float(os.environ.get("VDW_JAW_WIDTH", "99"))
def head_half(y):
    w = co[np.abs(co[:, 1] - y) < 0.012 * L]
    return float(np.percentile(np.abs(w[:, 0]), 70)) if len(w) > 4 else 1e9
for v in mesh.data.vertices:
    p = co[v.index]
    if p[1] > y_corner + 0.01 * L or p[2] >= gap_z(p[1]): continue
    if JW < 90 and abs(p[0]) > JW * head_half(p[1]): continue
    t = (y_corner + 0.01 * L - p[1]) / max(1e-5, blend)
    w = max(0.0, min(1.0, t)); w = w * w * (3 - 2 * w)
    if w <= 0.001: continue
    for g in v.groups: g.weight *= (1.0 - w)
    vg.add([v.index], w, 'REPLACE')
    moved += 1
print(f"  {moved} vertices on the lower jaw")

# VDW_JAW_REST_SHUT=1: shut the mouth in the model itself (the rest shape, which the still/ground model and the idle
# swim show); the clips then open it from there. Scanned fish come with their mouths gaping.
REST_SHUT = os.environ.get("VDW_JAW_REST_SHUT") == "1"
if REST_SHUT:
    rest0 = arm.data.bones["Jaw"].matrix_local.to_3x3()
    pb0 = arm.pose.bones["Jaw"]; pb0.rotation_mode = 'QUATERNION'
    keep0 = arm.animation_data.action if arm.animation_data else None
    if arm.animation_data: arm.animation_data.action = None
    pb0.rotation_quaternion = (rest0.inverted() @ Matrix.Rotation(close, 3, 'X') @ rest0).to_quaternion(); bpy.context.view_layer.update()
    t_c = pb0.tail.z; pb0.rotation_quaternion = (1, 0, 0, 0); bpy.context.view_layer.update(); t_o = pb0.tail.z
    if arm.animation_data: arm.animation_data.action = keep0
    sgn0 = 1.0 if t_c > t_o else -1.0
    from_arm = to_arm.inverted(); jg = vg.index; n_s = 0
    for v in mesh.data.vertices:
        w = next((g.weight for g in v.groups if g.group == jg), 0.0)
        if w <= 0.001: continue
        p = Vector(co[v.index]) - hinge
        p = Matrix.Rotation(sgn0 * close * w, 3, 'X') @ p
        v.co = from_arm @ (p + hinge); n_s += 1
    mesh.data.update()
    print(f"  mouth shut in the model: {n_s} vertices turned {math.degrees(close):.1f} deg about the hinge")

# ---- 4. animation: close angle per clip (fraction of a full close; negative opens wider), keyed every frame
rest = arm.data.bones["Jaw"].matrix_local.to_3x3()
def local_q(angle):                                  # rotation about the armature's X axis, in the bone's own space
    return (rest.inverted() @ Matrix.Rotation(angle, 3, 'X') @ rest).to_quaternion()

# which way closes: the jaw tip must go up (tested with no clip playing, or the clip would set the pose back)
pb = arm.pose.bones["Jaw"]; pb.rotation_mode = 'QUATERNION'
act_keep = arm.animation_data.action if arm.animation_data else None
if arm.animation_data: arm.animation_data.action = None
pb.rotation_quaternion = local_q(close); bpy.context.view_layer.update()
tip_closed = pb.tail.z
pb.rotation_quaternion = (1, 0, 0, 0); bpy.context.view_layer.update()
tip_open = pb.tail.z
sign = 1.0 if tip_closed > tip_open else -1.0
print(f"  closing turns the jaw {'+' if sign > 0 else '-'} about X (tip {tip_open:.3f} -> {tip_closed:.3f})")

def profile(name, t):
    n = name.lower()
    if "thrash" in n:   return -0.12 + 1.07 * (0.5 - 0.5 * math.cos(2 * math.pi * t)) ** 2      # one hard snap
    if "flop" in n:     return 0.2 + 0.6 * (0.5 - 0.5 * math.cos(2 * math.pi * t))              # gasping
    if "hook" in n:     return 0.1 + 0.8 * (0.5 - 0.5 * math.cos(4 * math.pi * t)) ** 1.5       # chomping
    return 0.12 + 0.3 * (0.5 - 0.5 * math.cos(2 * math.pi * t))                                 # swim: breathing

path = 'pose.bones["Jaw"].rotation_quaternion'
for act in bpy.data.actions:
    f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
    for c in [c for c in act.fcurves if c.data_path == path]: act.fcurves.remove(c)
    curves = [act.fcurves.new(path, index=i, action_group="Jaw") for i in range(4)]
    for fr in range(f0, f1 + 1):
        t = (fr - f0) / max(1, f1 - f0)
        pr = profile(act.name, t)
        if REST_SHUT:      # the model is already shut: swim (idle) stays shut, breathing a hair; the others open from shut
            pr = (0.96 + 0.04 * math.cos(2 * math.pi * t)) if not any(k in act.name.lower() for k in ("thrash", "flop", "hook")) else pr
            pr = pr - 1.0
        q = local_q(sign * close * pr)
        for i in range(4): curves[i].keyframe_points.insert(fr, q[i], options={'FAST'})
    for c in curves: c.update()
    print(f"  keyed {act.name} frames {f0}-{f1}")

# ---- 5. previews: mouth as modelled, and shut
if PREVIEW:
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'; sc.display.shading.color_type = 'TEXTURE'; sc.render.use_border = False
    sc.render.resolution_x, sc.render.resolution_y = 700, 500
    cd = bpy.data.cameras.new("jawcam"); cam = bpy.data.objects.new("jawcam", cd); sc.collection.objects.link(cam); sc.camera = cam
    cd.type = 'ORTHO'; cd.ortho_scale = 0.45 * L
    target = arm.matrix_world @ Vector((0, lo[1] + 0.15 * L, hinge.z))
    cam.location = target + Vector((3 * L, 0, 0)); cam.rotation_euler = Vector((-1, 0, 0)).to_track_quat('-Z', 'Y').to_euler()
    for tag, a in (("open", 0.0), ("shut", sign * close)):
        pb.rotation_quaternion = local_q(a); bpy.context.view_layer.update()
        sc.render.filepath = PREVIEW + f"_{tag}.png"; bpy.ops.render.render(write_still=True)
    pb.rotation_quaternion = (1, 0, 0, 0)
    bpy.data.objects.remove(cam)
if arm.animation_data: arm.animation_data.action = act_keep

bpy.ops.wm.save_as_mainfile(filepath=SAVE_TO)
print(f"  saved {SAVE_TO}\n===== END =====")
