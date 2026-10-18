# Rigs a small curled creature (grub, larva) WITHOUT straightening it: a bone chain follows its own curved centre
# line, and it animates by curling tighter / uncurling in its curl plane plus a sideways wriggle.
#   Clips Swim (gentle, on the hook), Thrash (hard curl-uncurl), Flop (rolling squirm), all looping.
#   env: VDW_LINE (centre line .npy from eel_centerline.py, in the source .blend's units), VDW_SIZE (metres, longest
#        extent), VDW_SEGMENTS (default 6), VDW_TEX_DIR (Unity maps written here), VDW_NAME, VDW_SAVE_TO
import bpy, os, math
import numpy as np
from mathutils import Vector, Quaternion, Matrix

LINE = np.load(os.environ["VDW_LINE"]); SIZE = float(os.environ["VDW_SIZE"]); NSEG = int(os.environ.get("VDW_SEGMENTS", "6"))
TEX = os.environ["VDW_TEX_DIR"]; NAME = os.environ["VDW_NAME"]
mesh = next(o for o in bpy.data.objects if o.type == 'MESH'); mesh.name = NAME; me = mesh.data
for o in bpy.context.view_layer.objects: o.select_set(False)
mesh.select_set(True); bpy.context.view_layer.objects.active = mesh
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
co = np.array([v.co[:] for v in me.vertices])
# curl plane: the centre line's best-fit plane. Lay it out: curl plane = X-Z (side view shows the C), the chord along Y
c0 = LINE.mean(0); _, _, vt = np.linalg.svd(LINE - c0, full_matrices=False)
chord = LINE[-1] - LINE[0]; ax_y = chord / np.linalg.norm(chord)
nrm = vt[2]; ax_x = np.cross(ax_y, nrm); ax_x /= np.linalg.norm(ax_x)
# the C bulges toward +Z (back up), so it rests on its ends and belly like a grub on its side
ax_z = np.cross(ax_x, ax_y)
mid = LINE[len(LINE) // 2]
if np.dot(mid - (LINE[0] + LINE[-1]) / 2, ax_z) < 0: ax_z = -ax_z; ax_x = -ax_x
R = np.stack([ax_x, ax_y, ax_z])
def tf(p): return (p - c0) @ R.T
co = tf(co); line = tf(LINE)
lo, hi = co.min(0), co.max(0); s = SIZE / float((hi - lo).max())
ctr = np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]])
co = (co - ctr) * s; line = (line - ctr) * s
for i, v in enumerate(me.vertices): v.co = co[i]
me.update()
lo, hi = co.min(0), co.max(0)
print(f"\n===== RIG CURLED =====\n  size {tuple(((hi - lo) * 100).round(1))} cm (scale x{s:.4f}), resting on its underside at z 0")

# bone chain along the centre line
seg = np.linalg.norm(np.diff(line, axis=0), axis=1); S = np.concatenate([[0], np.cumsum(seg)]); Ltot = S[-1]
def at(t): return np.array([np.interp(t * Ltot, S, line[:, i]) for i in range(3)])
arm_data = bpy.data.armatures.new("Armature"); arm = bpy.data.objects.new("Armature", arm_data)
bpy.context.scene.collection.objects.link(arm); bpy.context.view_layer.objects.active = arm
for o in bpy.context.view_layer.objects: o.select_set(False)
arm.select_set(True); bpy.ops.object.mode_set(mode='EDIT'); eb = arm_data.edit_bones
mid_t = 0.5
r = eb.new("Root"); r.head = Vector(at(mid_t)); r.tail = Vector(at(mid_t) + [0, 0, 0.01]); r.use_deform = False
names = [f"Spine{k}" if k else "Spine" for k in range(NSEG)]
ts = np.linspace(0, 1, NSEG + 1)
# chain grows from the middle outward both ways so curling bends both ends toward each other
half = NSEG // 2
order = list(range(half, NSEG)) + list(range(half - 1, -1, -1))
for k in range(NSEG):
    b = eb.new(names[k]); b.use_deform = True
    if k >= half: b.head, b.tail = Vector(at(ts[k])), Vector(at(ts[k + 1]))          # toward the tail end
    else:         b.head, b.tail = Vector(at(ts[k + 1])), Vector(at(ts[k]))          # toward the head end
    b.align_roll(Vector((1, 0, 0)))
for k in range(NSEG):
    b = eb[names[k]]
    if k == half or k == half - 1: b.parent = eb["Root"]
    elif k > half: b.parent = eb[names[k - 1]]; b.use_connect = True
    else: b.parent = eb[names[k + 1]]; b.use_connect = True
bpy.ops.object.mode_set(mode='OBJECT')

# weights: by position along the centre line, blended between neighbouring segments
for o in bpy.context.view_layer.objects: o.select_set(False)
mesh.select_set(True); arm.select_set(True); bpy.context.view_layer.objects.active = arm
bpy.ops.object.parent_set(type='ARMATURE_NAME')
a_ = line[:-1]; ab = line[1:] - a_
def u_of(p):
    t = np.clip(np.einsum('ij,ij->i', p - a_, ab) / np.einsum('ij,ij->i', ab, ab), 0, 1)
    d = np.linalg.norm(a_ + ab * t[:, None] - p, axis=1); k = int(np.argmin(d))
    return (S[k] + t[k] * seg[k]) / Ltot
centres = (ts[:-1] + ts[1:]) / 2
for i in range(len(co)):
    u = u_of(co[i])
    if u <= centres[0]: mesh.vertex_groups[names[0]].add([i], 1.0, 'REPLACE'); continue
    if u >= centres[-1]: mesh.vertex_groups[names[-1]].add([i], 1.0, 'REPLACE'); continue
    j = int(np.searchsorted(centres, u)) - 1; t = (u - centres[j]) / (centres[j + 1] - centres[j])
    if 1 - t > 0.001: mesh.vertex_groups[names[j]].add([i], 1 - t, 'REPLACE')
    if t > 0.001: mesh.vertex_groups[names[j + 1]].add([i], t, 'REPLACE')
# smooth the weights across the surface so thick, curved parts blend instead of jumping between segments
for o in bpy.context.view_layer.objects: o.select_set(False)
mesh.select_set(True); bpy.context.view_layer.objects.active = mesh
gi = {g.name: g.index for g in mesh.vertex_groups}; G = len(mesh.vertex_groups); nv = len(me.vertices)
Wt = np.zeros((nv, G))
for v in me.vertices:
    for g in v.groups: Wt[v.index, g.group] = g.weight
nb = [[] for _ in range(nv)]
for e in me.edges: a0, b0 = e.vertices; nb[a0].append(b0); nb[b0].append(a0)
for _ in range(int(os.environ.get('VDW_SMOOTH', '8'))):
    Wt = 0.4 * Wt + 0.6 * np.array([Wt[n].mean(0) if n else Wt[i] for i, n in enumerate(nb)])
Wt /= np.maximum(Wt.sum(1, keepdims=True), 1e-9)
for g in mesh.vertex_groups:
    g.remove(list(range(nv)))
    idx = np.nonzero(Wt[:, g.index] > 0.01)[0]
    for i in idx: g.add([int(i)], float(Wt[i, g.index]), 'REPLACE')
print("  bones:", [b.name for b in arm_data.bones])

# Unity maps from the Substance export + material
def load(n, nc=False):
    p = os.path.join(TEX, n)
    if not os.path.exists(p): return None
    im = bpy.data.images.load(p)
    if nc: im.colorspace_settings.name = 'Non-Color'
    return im
alb = load(f"{NAME}_Unity_Albedo.png"); orm = load("OcclusionRoughnessMetallic.png", True); nrmi = load(f"{NAME}_Unity_Normal.png", True)
ms = None
if orm:
    w, h = orm.size; p = np.empty(w * h * 4, dtype=np.float32); orm.pixels.foreach_get(p); p = p.reshape(-1, 4)
    out = np.empty_like(p); out[:, :3] = p[:, 2:3]; out[:, 3] = 1.0 - p[:, 1]
    path = os.path.join(TEX, f"{NAME}_Unity_MetallicSmoothness.png")
    ms = bpy.data.images.new(f"{NAME}_Unity_MetallicSmoothness", w, h, alpha=True); ms.colorspace_settings.name = 'Non-Color'
    ms.pixels.foreach_set(out.ravel()); ms.filepath_raw = path; ms.file_format = 'PNG'
    if not os.path.exists(path): ms.save()
mat = bpy.data.materials.new(NAME); mat.use_nodes = True; nt = mat.node_tree; N, L = nt.nodes, nt.links
bs = next(n for n in N if n.type == 'BSDF_PRINCIPLED')
def tex(img):
    t = N.new("ShaderNodeTexImage"); t.image = img; return t
a = tex(alb); L.new(a.outputs["Color"], bs.inputs["Base Color"])
if ms:
    sn = tex(ms); L.new(sn.outputs["Color"], bs.inputs["Metallic"])
    inv = N.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
    L.new(sn.outputs["Alpha"], inv.inputs[1]); L.new(inv.outputs["Value"], bs.inputs["Roughness"])
if nrmi:
    nn = tex(nrmi); nm = N.new("ShaderNodeNormalMap"); L.new(nn.outputs["Color"], nm.inputs["Color"]); L.new(nm.outputs["Normal"], bs.inputs["Normal"])
N.active = a; me.materials.clear(); me.materials.append(mat)
if orm: bpy.data.images.remove(orm)

# animation: curl = rotate every segment about X (the curl plane's normal), outer ends curl toward each other
WX, WZ = Vector((1, 0, 0)), Vector((0, 0, 1))
# curl in the plane the body is curled in; the wriggle lifts the body out of that plane a little
CURL_AX = Vector(np.cross(line[len(line) // 2] - line[0], line[-1] - line[len(line) // 2]).tolist()).normalized()
LIFT_AX = Vector((0, 1, 0))
print(f"  curl axis {tuple(round(x, 2) for x in CURL_AX)}")
def q(name, axis, deg):
    m = arm.data.bones[name].matrix_local.to_3x3(); return Quaternion((m.inverted() @ axis).normalized(), math.radians(deg))
def pose(curl, wiggle, ph):
    out = {}
    for k, nm_ in enumerate(names):
        side = 1 if k >= half else -1                      # tail half and head half curl opposite ways = tighter C
        dist = (k - half + 0.5) if k >= half else (half - 1 - k + 0.5)
        out[nm_] = q(nm_, CURL_AX, side * curl) @ q(nm_, LIFT_AX, wiggle * math.sin(ph - dist * 1.1))
    return out
CLIPS = {"Swim": 30, "Thrash": 15, "Flop": 30}
def clip_pose(c, ph):
    s_ = math.sin
    if c == "Swim":   return pose(5 * s_(ph), 4, ph)                         # breathing curl + slow wriggle
    if c == "Thrash": return pose(-3 + 11 * s_(ph) + 3 * s_(3 * ph), 7, 2 * ph)   # curl tight, snap open
    return pose(8 * s_(ph) + 2 * s_(2 * ph + 1), 6, ph + 0.7)           # Flop: squirming on the ground
if arm.animation_data is None: arm.animation_data_create()
for pb in arm.pose.bones: pb.rotation_mode = 'QUATERNION'
for c, n_ in CLIPS.items():
    act = bpy.data.actions.new(c); act.use_fake_user = True; arm.animation_data.action = act
    for f in range(n_ + 1):
        pz = clip_pose(c, 2 * math.pi * f / n_)
        for nm_ in names:
            arm.pose.bones[nm_].rotation_quaternion = pz[nm_]; arm.pose.bones[nm_].keyframe_insert("rotation_quaternion", frame=f, group=nm_)
    act.use_frame_range = True; act.use_cyclic = True; act.frame_start, act.frame_end = 0, n_
    for fc in act.fcurves:
        if not any(m.type == 'CYCLES' for m in fc.modifiers): fc.modifiers.new('CYCLES')
arm.animation_data.action = bpy.data.actions["Swim"]
sc = bpy.context.scene; sc.render.fps = 30; sc.frame_start, sc.frame_end = 0, 29
def verts(f):
    sc.frame_set(f); dg = bpy.context.evaluated_depsgraph_get(); ev = mesh.evaluated_get(dg)
    c_ = np.array([v.co[:] for v in ev.to_mesh().vertices]); ev.to_mesh_clear(); return c_
for c in CLIPS:
    arm.animation_data.action = bpy.data.actions[c]
    fr = [verts(f) for f in range(31)]
    st = [np.linalg.norm(fr[f + 1] - fr[f], axis=1).max() for f in range(30)]
    print(f"  {c}: smallest frame-to-frame movement {min(st) * 1000:.1f} mm, largest {max(st) * 1000:.1f} mm, loop seam {np.abs(fr[0] - fr[30]).max() * 1000:.2f} mm")
arm.animation_data.action = bpy.data.actions["Swim"]; sc.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=os.environ["VDW_SAVE_TO"]); print("  saved", os.environ["VDW_SAVE_TO"])
print("===== END =====")



