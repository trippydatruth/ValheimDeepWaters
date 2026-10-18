# Builds the worm mound ("pickable_worm"): the middle soil mound from pickableworm.blend, shrunk to VDW_MOUND_DIAM
# across, with the front half of the Earth Worm sticking up out of its centre, rigged as a little chain and wriggling.
#   Objects: "mound" (static mesh, its own material) and "worm" (skinned to Armature: Root > Seg1..SegN).
#   Clip: Swim (2 s loop) - the worm sways and twists, reaching and curling, never quite the same twice.
#   Origin = ground level at the mound's centre. Head of the worm up (+Z).
# Run from an empty blend:  blender -b --python build_worm_mound.py
# env: VDW_MOUND_BLEND, VDW_WORM_BLEND (straightened worm, along Y, head at -Y), VDW_SAVE_TO,
#      VDW_MOUND_DIAM (0.7), VDW_WORM_LEN (full worm length to scale to, 0.40), VDW_WORM_OUT (how much shows, 0.20)
import bpy, bmesh, math, os
import numpy as np
from mathutils import Matrix, Quaternion, Vector

DIAM = float(os.environ.get("VDW_MOUND_DIAM", "0.7"))
WLEN = float(os.environ.get("VDW_WORM_LEN", "0.40"))
WOUT = float(os.environ.get("VDW_WORM_OUT", "0.20"))
BURY = 0.03                       # the worm goes this far down into the soil
NSEG = 6
sc = bpy.context.scene; sc.render.fps = 30
for o in list(bpy.data.objects): bpy.data.objects.remove(o)

def append_meshes(path):
    with bpy.data.libraries.load(path) as (src, dst): dst.objects = src.objects
    out = []
    for o in dst.objects:
        if o is None: continue
        if o.type == 'MESH': sc.collection.objects.link(o); out.append(o)
    return out

# ---------------------------------------------------------------- mound: the biggest loose part (the middle one)
src = append_meshes(os.environ["VDW_MOUND_BLEND"])[0]
src.data = src.data.copy()
src.data.transform(src.matrix_world); src.matrix_world = Matrix()
bm = bmesh.new(); bm.from_mesh(src.data); bm.verts.ensure_lookup_table()
seen = {}; parts = []
for v in bm.verts:
    if v.index in seen: continue
    st = [v]; seen[v.index] = len(parts); comp = []
    while st:
        x = st.pop(); comp.append(x)
        for e in x.link_edges:
            w = e.other_vert(x)
            if w.index not in seen: seen[w.index] = len(parts); st.append(w)
    parts.append(comp)
parts.sort(key=len, reverse=True)
# the middle mound is the big part closest to the origin; worms (tall, thin parts) are dropped
def centre(p): c = np.array([v.co[:] for v in p]); return (c.min(0) + c.max(0)) / 2
discs = [p for p in parts if len(p) == len(parts[0])]
keep = min(discs, key=lambda p: np.linalg.norm(centre(p)[:2]))
keep_set = set(keep)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if v not in keep_set], context='VERTS')
c = np.array([v.co[:] for v in bm.verts]); lo, hi = c.min(0), c.max(0)
s = DIAM / max(hi[0] - lo[0], hi[1] - lo[1])
mid = (lo + hi) / 2
for v in bm.verts:
    v.co = Vector(((v.co.x - mid[0]) * s, (v.co.y - mid[1]) * s, (v.co.z - lo[2]) * s - 0.01))
bm.to_mesh(src.data); bm.free()
mound = src; mound.name = "mound"; mound.data.name = "mound"
mc = np.array([v.co[:] for v in mound.data.vertices])
r = np.hypot(mc[:, 0], mc[:, 1])
top = float(mc[r < DIAM * 0.06, 2].max()) if (r < DIAM * 0.06).any() else float(mc[:, 2].max())
print(f"MOUND {len(mound.data.vertices)} verts, {DIAM * 100:.0f} cm across, {mc[:, 2].max() * 100:.1f} cm high, centre top {top * 100:.1f} cm")

# ---------------------------------------------------------------- worm: front half, standing up out of the centre
w = append_meshes(os.environ["VDW_WORM_BLEND"])[0]
w.data = w.data.copy()
w.data.transform(w.matrix_world); w.matrix_world = Matrix()
for m in list(w.modifiers): w.modifiers.remove(m)
w.vertex_groups.clear()
wc = np.array([v.co[:] for v in w.data.vertices])
L0 = wc[:, 1].max() - wc[:, 1].min()
k = WLEN / L0
head_y = wc[:, 1].min()
cut_y = head_y + (WOUT + BURY) / k           # keep the head end, up to this far back
bm = bmesh.new(); bm.from_mesh(w.data)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.y > cut_y], context='VERTS')
cx, cz = (wc[:, 0].min() + wc[:, 0].max()) / 2, (wc[:, 2].min() + wc[:, 2].max()) / 2
base_z = top - BURY
for v in bm.verts:
    x, y, z = (v.co.x - cx) * k, (v.co.y - cut_y) * k, (v.co.z - cz) * k
    v.co = Vector((x, z, -y + base_z))        # head (-Y) up: y -> -z
bm.normal_update()
bm.to_mesh(w.data); bm.free()
w.name = "worm"; w.data.name = "worm"
wc = np.array([v.co[:] for v in w.data.vertices])
print(f"WORM half: {len(wc)} verts, {wc[:, 2].min() * 100:.1f} to {wc[:, 2].max() * 100:.1f} cm (shows {(wc[:, 2].max() - top) * 100:.1f} cm), thickness {(wc[:, 0].max() - wc[:, 0].min()) * 100:.1f} cm")

# ---------------------------------------------------------------- rig
arm_data = bpy.data.armatures.new("Armature"); arm = bpy.data.objects.new("Armature", arm_data)
sc.collection.objects.link(arm); bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
z0, z1 = float(wc[:, 2].min()), float(wc[:, 2].max())
root = arm_data.edit_bones.new("Root"); root.head = (0, 0, 0); root.tail = (0, 0, 0.05)
prev = root; heads = []
for i in range(NSEG):
    a = z0 + (z1 - z0) * i / NSEG; b = z0 + (z1 - z0) * (i + 1) / NSEG
    bn = arm_data.edit_bones.new(f"Seg{i + 1}"); bn.head = (0, 0, a); bn.tail = (0, 0, b); bn.parent = prev
    bn.use_connect = i > 0; prev = bn; heads.append(a)
bpy.ops.object.mode_set(mode='OBJECT')

# worm: smooth weights along its height between neighbouring segments; the buried end stays on Seg1
seg_len = (z1 - z0) / NSEG
groups = [w.vertex_groups.new(name=f"Seg{i + 1}") for i in range(NSEG)]
for v in w.data.vertices:
    t = (v.co.z - z0) / seg_len - 0.5          # 0 = middle of Seg1
    i = int(math.floor(t)); f = t - i
    for j, wt in ((i, 1 - f), (i + 1, f)):
        j = min(max(j, 0), NSEG - 1)
        if wt > 0: groups[j].add([v.index], wt, 'ADD')
w.parent = arm; mod = w.modifiers.new("Armature", 'ARMATURE'); mod.object = arm
mound.parent = arm                             # rides along, not skinned

# ---------------------------------------------------------------- materials (named after the objects)
for o, name in ((mound, "mound"), (w, "worm")):
    o.data.materials.clear()
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    o.data.materials.append(m)

# ---------------------------------------------------------------- Swim: the wriggle
def q(name, axis, deg):
    mm = arm.data.bones[name].matrix_local.to_3x3()
    return Quaternion((mm.inverted() @ axis).normalized(), math.radians(deg))
WX, WY, WZ = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
LEN = 60
act = bpy.data.actions.new("Swim"); act.use_fake_user = True
arm.animation_data_create(); arm.animation_data.action = act
for f in range(LEN + 1):
    p = 2 * math.pi * f / LEN
    reach = 0.5 + 0.5 * math.sin(p)                             # slowly reaching up, then curling over
    for i in range(NSEG):
        u = (i + 1) / NSEG
        amp = (4 + 9 * u) * (1.2 - 0.5 * reach)                 # the tip moves most; more when curled
        bx = amp * math.sin(2 * p - u * 3.2) + (1 - reach) * 10 * u     # sway one way, plus the curl-over
        by = amp * 0.8 * math.sin(3 * p - u * 2.6 + 1.1)                 # and the other, out of step: it circles
        tw = 6 * math.sin(p + u)                                         # a little twist
        pb = arm.pose.bones[f"Seg{i + 1}"]; pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = q(pb.name, WX, bx) @ q(pb.name, WY, by) @ q(pb.name, WZ, tw)
        pb.keyframe_insert("rotation_quaternion", frame=f, group=pb.name)
act.use_frame_range = True; act.use_cyclic = True; act.frame_start, act.frame_end = 0, LEN
for fc in act.fcurves: fc.modifiers.new('CYCLES')

# check: loop seam and how far the tip travels
def tip():
    sc.frame_set(f); dg = bpy.context.evaluated_depsgraph_get(); ev = w.evaluated_get(dg); me = ev.to_mesh()
    c = np.array([v.co[:] for v in me.vertices]); ev.to_mesh_clear(); return c
fr = []
for f in range(LEN + 1):
    fr.append(tip())
tips = np.array([x[np.argmax(x[:, 2])] for x in fr])
print(f"SWIM: loop seam {np.abs(fr[0] - fr[LEN]).max() * 1000:.3f} mm, tip wanders {np.ptp(tips[:, 0]) * 100:.1f} x {np.ptp(tips[:, 1]) * 100:.1f} cm, "
      f"lowest base {min(x[:, 2].min() for x in fr) * 100:.1f} cm")
sc.frame_set(0)
for pb in arm.pose.bones: pb.rotation_quaternion = Quaternion()
bpy.ops.wm.save_as_mainfile(filepath=os.environ["VDW_SAVE_TO"])
print("SAVED", os.environ["VDW_SAVE_TO"])
