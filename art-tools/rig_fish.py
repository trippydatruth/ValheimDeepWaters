# Sizes a raw fish mesh and builds the Deep Waters fish rig on it automatically (same bone names as the Moder rig, so
# animate_fish.py works on it), then binds it.
#   The mesh must lie along Y with its head toward -Y.
#   env: VDW_LENGTH (metres nose to tail), VDW_SAVE_TO (new .blend), VDW_SPINES (spine bones, default 4)
import bpy, math, os
import numpy as np
from mathutils import Vector

L = float(os.environ.get("VDW_LENGTH", "2.0"))
NSPINE = int(os.environ.get("VDW_SPINES", "4"))
SAVE_TO = os.environ["VDW_SAVE_TO"]
mesh = next(o for o in bpy.data.objects if o.type == 'MESH')
scene = bpy.context.scene

# ---- 1. size and centre: nose-to-tail = L, body centred on the origin, then apply.
# First bake in any rotation/scale already on the object (e.g. stretched or turned by hand), so it's kept.
for o in bpy.context.view_layer.objects: o.select_set(False)
mesh.select_set(True); bpy.context.view_layer.objects.active = mesh
if mesh.matrix_world != mesh.matrix_world.Identity(4):
    print(f"  applying existing transform: rot {tuple(round(x, 3) for x in mesh.rotation_euler)} scale {tuple(round(x, 3) for x in mesh.scale)}")
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
co = np.array([mesh.matrix_world @ v.co for v in mesh.data.vertices])
lo, hi = co.min(0), co.max(0)
s = L / (hi[1] - lo[1])
central = co[np.abs(co[:, 0] - (lo[0] + hi[0]) / 2) < (hi[0] - lo[0]) * 0.08]
zc = float(np.median(central[:, 2]))
centre = Vector(((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, zc))
for o in bpy.context.view_layer.objects: o.select_set(False)
mesh.select_set(True); bpy.context.view_layer.objects.active = mesh
mesh.location = -centre * s
mesh.scale = (s, s, s)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
co = np.array([v.co[:] for v in mesh.data.vertices])
lo, hi = co.min(0), co.max(0)
print(f"\n===== RIG =====\n  scaled x{s:.4f}: size {tuple((hi - lo).round(2))}")

def f2y(f): return lo[1] + f * (hi[1] - lo[1])          # 0 = nose, 1 = tail tip
def window(f0, f1): return co[(co[:, 1] >= f2y(f0)) & (co[:, 1] <= f2y(f1))]
def midline_z(f):
    w = window(max(0, f - 0.04), min(1, f + 0.04))
    r = 0.04
    while len(w) < 3 and r < 0.5:      # low-poly bodies can have long bare stretches: widen the window
        r *= 1.5; w = window(max(0, f - r), min(1, f + r))
    c = w[np.abs(w[:, 0]) < max(0.02, 0.12 * (hi[0] - lo[0]) / 2)]
    if len(c) < 3: c = w
    return float((np.percentile(c[:, 2], 20) + np.percentile(c[:, 2], 80)) / 2)

# Where the tail fin begins: the body gets thin (half-width small) toward the back.
def half_width(f):
    w = window(max(0, f - 0.03), min(1, f + 0.03))
    return float(np.percentile(np.abs(w[:, 0]), 90)) if len(w) else 0.0
tail_start = float(os.environ["VDW_TAIL_START"]) if os.environ.get("VDW_TAIL_START") else next((f for f in np.arange(0.55, 0.95, 0.01) if half_width(f) < 0.18 * half_width(0.45)), 0.80)
print(f"  tail fin starts at {tail_start:.2f} of the length")

# ---- 2. armature
arm_data = bpy.data.armatures.new("Armature")
arm = bpy.data.objects.new("Armature", arm_data)
scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
eb = arm_data.edit_bones
def bone(name, head, tail, parent=None, connect=False, deform=True):
    b = eb.new(name); b.head = Vector(head); b.tail = Vector(tail)
    if parent: b.parent = eb[parent]; b.use_connect = connect
    b.use_deform = deform
    return b
def p(f, z=None, x=0.0): return (x, f2y(f), midline_z(f) if z is None else z)

body0 = 0.30                                   # head ends / spine begins
spine_fs = np.linspace(body0, tail_start, NSPINE + 1)
bone("Root", p(0.45), p(0.35), deform=False)
bone("Head", p(body0), p(0.05), "Root")
names = ["Spine"] + [f"Spine{k}" for k in range(1, NSPINE)]
prev = None
for k, n in enumerate(names):
    bone(n, p(spine_fs[k]), p(spine_fs[k + 1]), prev or "Root", connect=prev is not None)
    prev = n

# Tail fin: chains from the tail base to the top and bottom tips of the fin.
tw = window(tail_start, 1.0)
top_tip = tw[np.argmax(tw[:, 2])]; bot_tip = tw[np.argmin(tw[:, 2])]
base = np.array(p(tail_start))
for side, tip in (("Top", top_tip), ("Bottom", bot_tip)):
    pts = [base + (tip - base) * t for t in (0.0, 0.34, 0.67, 1.0)]
    parent = names[-1]
    for k in range(3):
        n = f"{side}.Tail.Fin{k + 1}"
        bone(n, pts[k], pts[k + 1], parent, connect=k > 0)
        parent = n

# Dorsal fins: the highest points of the back, ahead of the tail.
dorsal = 0
for f0, f1 in ((0.15, 0.42), (0.42, tail_start - 0.03)):
    w = window(f0, f1); w = w[np.abs(w[:, 0]) < 0.25 * (hi[0] - lo[0]) / 2]
    if len(w) == 0: continue
    tip = w[np.argmax(w[:, 2])]
    f = (tip[1] - lo[1]) / (hi[1] - lo[1])
    body_top = float(np.percentile(window(f - 0.03, f + 0.03)[:, 2], 75))
    if tip[2] - body_top < 0.05 * L: continue      # no real fin here
    dorsal += 1
    owner = names[min(len(names) - 1, max(0, int(np.searchsorted(spine_fs, f)) - 1))]
    bone(f"Dorsal.Fin.{dorsal}", (0, tip[1], body_top), tuple(tip), owner)

# Pectoral (front) and pelvic (belly) fins: the widest points on each side, below the midline.
# VDW_PECTORAL "f0,f1": where to look for the pectoral fins (the default finds the widest point low on the front -
# on Thor's Hammerhead that was the hammer's tips)
PEC = tuple(float(x) for x in os.environ.get("VDW_PECTORAL", "0.12,0.42").split(","))
for kind, f0, f1 in (("Pectoral", PEC[0], PEC[1]), ("Pelvic", max(0.42, PEC[1]), min(0.70, tail_start))):
    for side, sign in (("L", 1), ("R", -1)):
        w = window(f0, f1); w = w[(w[:, 0] * sign > 0)]
        # below the midline only, so antlers, horns or spikes on the back aren't taken for fins
        w = w[w[:, 2] < midline_z((f0 + f1) / 2) - 0.03 * L]
        if len(w) == 0: continue
        tip = w[np.argmax(w[:, 0] * sign)]
        f = (tip[1] - lo[1]) / (hi[1] - lo[1])
        root_x = sign * 0.45 * half_width(f)
        baseP = np.array((root_x, tip[1] - 0.03 * L, tip[2] + 0.02 * L))
        mid = baseP + (tip - baseP) * 0.5
        bone(f"Fin.Upper.{kind}.{side}", baseP, mid, "Root")
        bone(f"Fin.Lower.{kind}.{side}", mid, tip, f"Fin.Upper.{kind}.{side}", connect=True)
bpy.ops.object.mode_set(mode='OBJECT')
print("  bones:", [b.name for b in arm_data.bones])

# ---- 3. bind with smooth weights computed here. (Heat weighting fails on meshes made of many loose pieces,
# like whiskers and slime strands.) Body vertices blend between their nearest body bones by distance; each fin
# bone only takes the vertices out on its own fin; the tail fin bones only take the vertices behind the tail start.
for o in bpy.context.view_layer.objects: o.select_set(False)
mesh.select_set(True); arm.select_set(True); bpy.context.view_layer.objects.active = arm
bpy.ops.object.parent_set(type='ARMATURE_NAME')            # empty groups, one per bone
deform = [b for b in arm_data.bones if b.use_deform]
segs = {b.name: (np.array(b.head_local[:]), np.array(b.tail_local[:])) for b in deform}
def seg_dist(pt, a, b):
    ab = b - a; t = np.clip(np.dot(pt - a, ab) / max(np.dot(ab, ab), 1e-9), 0, 1); return float(np.linalg.norm(a + ab * t - pt))
body = ["Head"] + names
tail = [n for n in segs if ".Tail.Fin" in n]
fins = {}
for n in segs:
    if n.startswith("Fin.") or n.startswith("Dorsal"):
        key = n.replace("Upper.", "").replace("Lower.", "")
        fins.setdefault(key, []).append(n)
tail_y = f2y(tail_start - 0.02)
# Fin geometry: thin (two surfaces close together) or one-layer sheets. Only these vertices may follow a fin bone,
# so the solid body around a fin's base doesn't flap with the fin.
import bmesh
from mathutils.bvhtree import BVHTree
bmf = bmesh.new(); bmf.from_mesh(mesh.data); bmf.faces.ensure_lookup_table()
bvh = BVHTree.FromBMesh(bmf); THIN = 0.035 * L / 2.0
fcat = []
for f in bmf.faces:
    n = f.normal
    if n.length < 0.5: fcat.append(False); continue
    loc, hn, _i, dist = bvh.ray_cast(f.calc_center_median() - n * 1e-4, -n)
    fcat.append(loc is None or hn.dot(n) > 0 or dist < THIN)
finlike = np.zeros(len(mesh.data.vertices), dtype=bool)
for v in bmf.verts:
    fs = [fcat[f.index] for f in v.link_faces]
    finlike[v.index] = bool(fs) and sum(fs) > len(fs) / 2
bmf.free()
print(f"  fin-shaped vertices: {int(finlike.sum())} of {len(finlike)}")
for v in mesh.data.vertices:
    pt = np.array(v.co[:])
    cands = None
    for key, bones_ in fins.items():          # a fin's own vertices: fin-shaped, out past its base, close to its bones
        if not finlike[v.index]: break
        a = segs[bones_[0]][0]
        if "Dorsal" in key:
            ok = pt[2] > a[2] and min(seg_dist(pt, *segs[b]) for b in bones_) < 0.06 * L
        else:
            ok = pt[0] * a[0] > 0 and abs(pt[0]) > abs(a[0]) and min(seg_dist(pt, *segs[b]) for b in bones_) < 0.10 * L
        if ok:
            cands = bones_; break
    if cands is None:
        cands = (tail + [names[-1]]) if pt[1] > tail_y else body
    d = np.array([seg_dist(pt, *segs[n]) for n in cands]) + 1e-4
    w = (d.min() / d) ** 4
    order = np.argsort(-w)[:3]
    w = w[order] / w[order].sum()
    for n, wt in zip([cands[i] for i in order], w):
        if wt > 0.02: mesh.vertex_groups[n].add([v.index], float(wt), 'REPLACE')
bpy.context.view_layer.objects.active = mesh
bpy.ops.object.vertex_group_normalize_all(lock_active=False)
# VDW_RIGID_HEAD: everything ahead of this share of the length moves with the Head bone alone (a built-on head like
# Mjolnir's hammer bent between head and spine and flapped on fin bones), easing into the body weights over 0.06
if os.environ.get("VDW_RIGID_HEAD"):
    rf = float(os.environ["VDW_RIGID_HEAD"]); hg = mesh.vertex_groups["Head"]; n_r = 0
    for v in mesh.data.vertices:
        f = (v.co.y - lo[1]) / (hi[1] - lo[1])
        if f >= rf + 0.06: continue
        k = 1.0 - max(0.0, (f - rf) / 0.06); k = k * k * (3 - 2 * k)
        for g in v.groups:
            if mesh.vertex_groups[g.group].name != "Head": g.weight *= (1 - k)
        cur = next((g.weight for g in v.groups if mesh.vertex_groups[g.group].name == "Head"), 0.0)
        hg.add([v.index], cur * (1 - k) + k, 'REPLACE'); n_r += 1
    bpy.ops.object.vertex_group_normalize_all(lock_active=False)
    print(f"  rigid head: {n_r} vertices ahead of {rf:.2f} (+0.06 blend) moved to the Head bone")
counts = {g.name: 0 for g in mesh.vertex_groups}
for v in mesh.data.vertices:
    for g in v.groups:
        if g.weight > 0.05: counts[mesh.vertex_groups[g.group].name] += 1
print("  weighted vertices per bone:", counts)

# Test bend
def verts():
    dg = bpy.context.evaluated_depsgraph_get(); ev = mesh.evaluated_get(dg)
    c = [x.co.copy() for x in ev.to_mesh().vertices]; ev.to_mesh_clear(); return c
a = verts()
pb = arm.pose.bones[names[-1]]; pb.rotation_mode = 'XYZ'; pb.rotation_euler = (0, 0, math.radians(25))
bpy.context.view_layer.update(); b = verts(); pb.rotation_euler = (0, 0, 0)
print(f"  test bend of {names[-1]}: {sum(1 for x, y in zip(a, b) if (x - y).length > 0.001)} vertices moved")
bpy.ops.wm.save_as_mainfile(filepath=SAVE_TO)
print("  saved", SAVE_TO)
print("===== END =====")

