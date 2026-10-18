# Cleans a Sketchfab/glTF rigged fish .blend into the Deep Waters layout and builds the mod's clips from its own:
#   - keeps only the armature and the skinned mesh (empties, stray meshes, unused materials/collections removed)
#   - bakes every parent/object scale and rotation into the rig (location keys rescaled to match), sizes the fish
#     to VDW_LENGTH metres nose to tail, head toward -Y, top up, centred
#   - clips at 30 fps, all looping: Swim (its swim), Thrash (swim, faster and stronger), Flop (swim, slow and wide),
#     Hooked (its idle). Other clips (death etc.) are removed.
#   - Unity maps: <NAME>_Unity_Albedo / _Normal from the packed textures, _MetallicSmoothness (wet scales)
#   env: VDW_NAME, VDW_LENGTH, VDW_TEX_DIR, VDW_SAVE_TO, VDW_SWIM, VDW_IDLE (action name parts)
import bpy, os, math
import numpy as np
from mathutils import Matrix, Quaternion, Vector

NAME = os.environ["VDW_NAME"]; LENGTH = float(os.environ["VDW_LENGTH"]); TEX = os.environ["VDW_TEX_DIR"]
SWIM_KEY = os.environ.get("VDW_SWIM", "Swim"); IDLE_KEY = os.environ.get("VDW_IDLE", "Idle")
scene = bpy.context.scene

arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
mesh = max((o for o in bpy.data.objects if o.type == 'MESH' and any(m.type == 'ARMATURE' for m in o.modifiers)), key=lambda o: len(o.data.vertices))
src_actions = {a.name: a for a in bpy.data.actions}
swim_src = next(a for n, a in src_actions.items() if SWIM_KEY.lower() in n.lower())
idle_src = next((a for n, a in src_actions.items() if IDLE_KEY.lower() in n.lower()), None)
print(f"\n===== CLEAN =====\n  armature {arm.name}, mesh {mesh.name}, swim '{swim_src.name}' {tuple(swim_src.frame_range)}, idle '{idle_src.name if idle_src else None}'")

# ---- 1. sample the source clips (bone-local rotation + location per frame) before touching anything
def sample(action, frames):
    arm.animation_data.action = action
    out = []
    for f in frames:
        scene.frame_set(int(f)); scene.frame_subframe = f - int(f) if False else 0.0
        # evaluate the f-curves directly at a fractional frame
        pose = {}
        for pb in arm.pose.bones:
            q = [None] * 4; l = [0.0, 0.0, 0.0]; hasq = False
            for i in range(4):
                fc = action.fcurves.find(f'pose.bones["{pb.name}"].rotation_quaternion', index=i)
                if fc: q[i] = fc.evaluate(f); hasq = True
            for i in range(3):
                fc = action.fcurves.find(f'pose.bones["{pb.name}"].location', index=i)
                if fc: l[i] = fc.evaluate(f)
            if hasq:
                q = [q[i] if q[i] is not None else (1.0 if i == 0 else 0.0) for i in range(4)]
            else:
                q = [1.0, 0.0, 0.0, 0.0]
            pose[pb.name] = (Quaternion(q).normalized(), Vector(l))
        out.append(pose)
    return out

sf0, sf1 = swim_src.frame_range; src_fps = scene.render.fps
swim_len = sf1 - sf0                                   # source frames per cycle
def resample(action, a0, a1, n_out):
    return sample(action, [a0 + (a1 - a0) * k / n_out for k in range(n_out + 1)])
SW = resample(swim_src, sf0, sf1, 30)                  # one swim cycle -> 30 frames (1 s at 30 fps if the source is 1 s)
def smooth_cycle(frames, r=2):
    """Circular smoothing of a looping clip: removes held keys (dead stops) without changing the loop."""
    n = len(frames) - 1; out = []
    for i in range(n):
        pose = {}
        for b in frames[0]:
            q0 = frames[i][b][0]; acc = Quaternion((0, 0, 0, 0)); l = Vector((0, 0, 0)); wsum = 0
            for d in range(-r, r + 1):
                q, lv = frames[(i + d) % n][b]; w = 1.0 / (1 + abs(d))
                if q0.dot(q) < 0: q = -q
                acc = Quaternion(tuple(acc[j] + w * q[j] for j in range(4))); l += lv * w; wsum += w
            pose[b] = (acc.normalized(), l / wsum)
        out.append(pose)
    out.append(out[0])
    return out
SW = smooth_cycle(SW)
seam = max((SW[0][b][0].rotation_difference(SW[-1][b][0])).angle for b in SW[0])
print(f"  source swim: {swim_len:.0f} frames at {src_fps} fps; loop seam {math.degrees(seam):.2f} deg")
_hk = [sf0 + (sf1 - sf0) * (k + 0.25) / 45 for k in range(45)]  # quarter-step offset: no two samples mirror each other at either turn
_th = [sf0 + (sf1 - sf0) * (k + 0.25) / 15 for k in range(15)]
TH = smooth_cycle(sample(swim_src, _th + [_th[0]]), 1)
HK = smooth_cycle(sample(swim_src, _hk + [_hk[0]]), 3)  # for Hooked (sampled now, the source clips are removed later)
ID = None
if idle_src:
    i0, i1 = idle_src.frame_range
    n_id = max(30, int(round((i1 - i0) / src_fps * 30)))
    ID = resample(idle_src, i0, i1, n_id)

# ---- 2. bake the hierarchy: armature and mesh to world space, then scale/rotate into place
for o in bpy.context.view_layer.objects: o.select_set(False)
world_arm = arm.matrix_world.copy(); world_mesh = mesh.matrix_world.copy()
arm.parent = None; arm.matrix_world = world_arm
mesh.parent = arm; mesh.matrix_parent_inverse = arm.matrix_world.inverted(); mesh.matrix_world = world_mesh
# remove everything else
for o in list(bpy.data.objects):
    if o not in (arm, mesh): bpy.data.objects.remove(o)
for c in list(bpy.data.collections):
    if c.name != "Collection": bpy.data.collections.remove(c)
for o in (arm, mesh):
    if o.name not in scene.collection.objects and not any(o.name in c.objects for c in bpy.data.collections): scene.collection.objects.link(o)

# rest-pose mesh in world space: find nose/tail and the top
arm.data.pose_position = 'REST'; bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get(); ev = mesh.evaluated_get(dg)
W = np.array([mesh.matrix_world @ v.co for v in ev.to_mesh().vertices]); ev.to_mesh_clear()
ax = int(np.argmax(W.max(0) - W.min(0)))
lo, hi = W[:, ax].min(), W[:, ax].max(); L0 = hi - lo
def thick(f0, f1):
    s = W[(W[:, ax] >= lo + f0 * L0) & (W[:, ax] <= lo + f1 * L0)]
    o_ = [i for i in range(3) if i != ax]; return float(np.percentile(s[:, o_[0]], 90) - np.percentile(s[:, o_[0]], 10)) + float(np.percentile(s[:, o_[1]], 90) - np.percentile(s[:, o_[1]], 10))
head_at_hi = thick(0.75, 0.9) > thick(0.1, 0.25)          # the head end is the thick end (the tail end is a thin stalk + fin)
long_dir = np.zeros(3); long_dir[ax] = 1.0 if head_at_hi else -1.0   # direction toward the head
others = [i for i in range(3) if i != ax]
height_ax = max(others, key=lambda i: W[:, i].ptp())       # the fish is taller than it is wide
up = np.zeros(3); up[height_ax] = 1.0
# which way is up: the dorsal side is further from the centre line than the belly at mid-body? use fin spread: the
# dorsal fin sticks out more -> more vertices beyond the 80th percentile on the top side
# which way is up: a fish's back is darker than its belly. Read the albedo under each vertex (rest pose) and put the
# darker half on top. (VDW_FLIP_UP=1 turns it over if a model is painted the other way.)
_mat = next(s.material for s in mesh.material_slots if s.material)
_bs = next(n for n in _mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
_img = next(l.from_node.image for l in _mat.node_tree.links if l.to_node == _bs and l.to_socket.name == "Base Color")
_w, _h = _img.size; _px = np.empty(_w * _h * 4, dtype=np.float32); _img.pixels.foreach_get(_px); _px = _px.reshape(_h, _w, 4)
_uv = mesh.data.uv_layers.active.data; _lum = np.zeros(len(W)); _cnt = np.zeros(len(W))
for poly in mesh.data.polygons:
    for li in poly.loop_indices:
        u, v = _uv[li].uv; vi = mesh.data.loops[li].vertex_index
        _lum[vi] += _px[min(_h - 1, int((v % 1) * _h)), min(_w - 1, int((u % 1) * _w)), :3].mean(); _cnt[vi] += 1
_lum /= np.maximum(_cnt, 1)
_hc = W[:, height_ax]; _q1, _q3 = np.percentile(_hc, 30), np.percentile(_hc, 70)
_top_dark = _lum[_hc >= _q3].mean() < _lum[_hc <= _q1].mean()
if not _top_dark: up = -up
if os.environ.get("VDW_FLIP_UP") == "1": up = -up
print(f"  texture brightness: high side {_lum[_hc >= _q3].mean():.2f}, low side {_lum[_hc <= _q1].mean():.2f} -> darker side is the back")
side = np.cross(-long_dir, up)                               # target frame: head -> -Y, up -> +Z, side -> +X
R = Matrix((tuple(side), tuple(-long_dir), tuple(up)))       # rows: world axis vectors -> new x, y, z
k = LENGTH / L0
centre = Vector(((W.min(0) + W.max(0)) / 2).tolist())
T = Matrix.Scale(k, 4) @ R.to_4x4() @ Matrix.Translation(-centre)
print(f"  long axis {'XYZ'[ax]}, head at the {'high' if head_at_hi else 'low'} end, up = {tuple(up)}; source length {L0:.3f} -> {LENGTH} m (x{k:.4f})")

# new armature transform: T applied on top of the world transform, then baked into the bones
arm.matrix_world = T @ arm.matrix_world
mesh_world = mesh.matrix_world.copy()
total_scale = arm.matrix_world.to_scale()[0]
for o in bpy.context.view_layer.objects: o.select_set(False)
arm.select_set(True); bpy.context.view_layer.objects.active = arm
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True, properties=False)
for o in bpy.context.view_layer.objects: o.select_set(False)
mesh.select_set(True); bpy.context.view_layer.objects.active = mesh
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True, properties=False)
mesh.parent = arm; mesh.matrix_parent_inverse = Matrix.Identity(4)
for md in mesh.modifiers:
    if md.type == 'ARMATURE': md.object = arm
print(f"  rig baked; bone-space locations scale by x{total_scale:.4f}")

# ---- 3. clips
for a in list(bpy.data.actions): bpy.data.actions.remove(a)
arm.animation_data_clear(); arm.animation_data_create()
for pb in arm.pose.bones: pb.rotation_mode = 'QUATERNION'
def amp(q, s):
    if s == 1.0: return q
    if q.w < 0: q = -q                                   # shortest rotation, so scaling never wraps around
    ax_, ang = q.to_axis_angle(); return Quaternion(ax_, ang * s)
def make(name, frames_pose, scale_rot=1.0):
    act = bpy.data.actions.new(name); act.use_fake_user = True; arm.animation_data.action = act
    for f, pose in enumerate(frames_pose):
        for bn, (q, l) in pose.items():
            pb = arm.pose.bones.get(bn)
            if pb is None: continue
            pb.rotation_quaternion = amp(q, scale_rot); pb.location = l * total_scale
            pb.keyframe_insert("rotation_quaternion", frame=f, group=bn); pb.keyframe_insert("location", frame=f, group=bn)
    n = len(frames_pose) - 1
    act.use_frame_range = True; act.use_cyclic = True; act.frame_start, act.frame_end = 0, n
    for fc in act.fcurves:
        if not any(m.type == 'CYCLES' for m in fc.modifiers): fc.modifiers.new('CYCLES')
    return act
make("Swim", SW)
make("Thrash", TH, float(os.environ.get("VDW_THRASH_AMP", "1.35")))          # twice as fast (15 frames), stronger bends

# Flop: half speed over 30 frames = half a cycle would not loop; instead a full cycle stretched to 30 frames at
# wider bends reads as slow writhing on land
make("Flop", SW, float(os.environ.get("VDW_FLOP_AMP", "1.6")))
# Hooked: a live bait fish on the hook swims weakly and steadily: its swim, slower (1.5 s) and a little smaller
make("Hooked", HK, 0.8)
arm.animation_data.action = bpy.data.actions["Swim"]
scene.render.fps = 30; scene.frame_start, scene.frame_end = 0, 29
for pb in arm.pose.bones: pb.rotation_quaternion = Quaternion(); pb.location = (0, 0, 0)
arm.data.pose_position = 'POSE'

# ---- 4. materials and Unity maps
mat = next(s.material for s in mesh.material_slots if s.material)
for m in list(bpy.data.materials):
    if m != mat: bpy.data.materials.remove(m)
mesh.data.materials.clear(); mesh.data.materials.append(mat); mat.name = NAME
nt = mat.node_tree; N, Lk = nt.nodes, nt.links
bs = next(n for n in N if n.type == 'BSDF_PRINCIPLED')
albn = next(l.from_node for l in Lk if l.to_node == bs and l.to_socket.name == "Base Color")
nmn = next((n for n in N if n.type == 'NORMAL_MAP'), None)
nrm_img = nmn.inputs["Color"].links[0].from_node.image if nmn and nmn.inputs["Color"].links else None
def save_as(img, fname, nc=False):
    path = os.path.join(TEX, fname)
    if img.packed_file: img.unpack(method='REMOVE') if False else None
    w, h = img.size; px = np.empty(w * h * 4, dtype=np.float32); img.pixels.foreach_get(px)
    new = bpy.data.images.new(os.path.splitext(fname)[0], w, h, alpha=True)
    if nc: new.colorspace_settings.name = 'Non-Color'
    new.pixels.foreach_set(px); new.filepath_raw = path; new.file_format = 'PNG'; new.save()
    return new, px.reshape(-1, 4)
alb, apx = save_as(albn.image, f"{NAME}_Unity_Albedo.png")
albn.image = alb
if nrm_img:
    nimg, _ = save_as(nrm_img, f"{NAME}_Unity_Normal.png", True); nmn.inputs["Color"].links[0].from_node.image = nimg
lum = apx[:, :3].mean(1)
ms = np.zeros_like(apx); ms[:, :3] = 0.0; ms[:, 3] = np.clip(0.6 + 0.3 * (lum - lum.mean()), 0.35, 0.85)   # wet, shiny scales
w, h = alb.size
msi = bpy.data.images.new(f"{NAME}_Unity_MetallicSmoothness", w, h, alpha=True); msi.colorspace_settings.name = 'Non-Color'
msi.pixels.foreach_set(ms.ravel()); msi.filepath_raw = os.path.join(TEX, f"{NAME}_Unity_MetallicSmoothness.png"); msi.file_format = 'PNG'; msi.save()
for l in list(bs.inputs["Metallic"].links) + list(bs.inputs["Roughness"].links): Lk.remove(l)
sn = N.new("ShaderNodeTexImage"); sn.image = msi; Lk.new(sn.outputs["Color"], bs.inputs["Metallic"])
inv = N.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
Lk.new(sn.outputs["Alpha"], inv.inputs[1]); Lk.new(inv.outputs["Value"], bs.inputs["Roughness"])
for uv in list(mesh.data.uv_layers)[1:]:
    used = any(n.type == 'UVMAP' and n.uv_map == uv.name for n in N)
    if not used: mesh.data.uv_layers.remove(uv)
for img in list(bpy.data.images):
    if img.users == 0: bpy.data.images.remove(img)
for m in list(bpy.data.meshes):
    if m.users == 0: bpy.data.meshes.remove(m)
mesh.name = NAME; arm.name = "Armature"

# ---- 5. checks
def verts(f):
    scene.frame_set(f); dg = bpy.context.evaluated_depsgraph_get(); ev = mesh.evaluated_get(dg)
    c = np.array([mesh.matrix_world @ v.co for v in ev.to_mesh().vertices]); ev.to_mesh_clear(); return c
arm.data.pose_position = 'REST'; R0 = verts(0); arm.data.pose_position = 'POSE'
print(f"  rest size {tuple((R0.max(0) - R0.min(0)).round(3))} m, centre {tuple(((R0.max(0) + R0.min(0)) / 2).round(3))}")
for a in bpy.data.actions:
    arm.animation_data.action = a; n = int(a.frame_range[1])
    fr = [verts(f) for f in range(n + 1)]
    st = [np.linalg.norm(fr[i + 1] - fr[i], axis=1).max() for i in range(n)]
    print(f"  {a.name}: {n} frames, smallest frame-to-frame {min(st) * 1000:.1f} mm, largest {max(st) * 1000:.1f} mm, loop seam {np.abs(fr[0] - fr[-1]).max() * 1000:.2f} mm")
arm.animation_data.action = bpy.data.actions["Swim"]; scene.frame_set(0)
print("  objects:", [o.name for o in bpy.data.objects], "| images:", [i.name for i in bpy.data.images])
bpy.ops.wm.save_as_mainfile(filepath=os.environ["VDW_SAVE_TO"]); print("  saved", os.environ["VDW_SAVE_TO"])
print("===== END =====")






