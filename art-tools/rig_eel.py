# Rigs a straightened eel (lying along Y, head toward -Y): Root, Head, a long Spine chain to the tail tip, plus a bone
# for each pincer and gill flap. Separate mesh pieces are identified by where they sit:
#   pincers = the two biggest pieces hanging below the front of the head; gills = the two pieces reaching furthest
#   out sideways behind the head; every other piece (hairs/whiskers) is solid with the head.
# Body weights blend linearly between neighbouring chain bones along Y, so the body bends smoothly like a rope.
#   env: VDW_SPINES (default 14), VDW_HEAD_END (fraction of length where the head ends, default auto), VDW_SAVE_TO
import bpy, bmesh, os, math
import numpy as np
from mathutils import Vector

NSP = int(os.environ.get("VDW_SPINES", "14")); SAVE_TO = os.environ["VDW_SAVE_TO"]
mesh = next(o for o in bpy.data.objects if o.type == 'MESH'); me = mesh.data
co = np.array([v.co[:] for v in me.vertices]); n = len(co)
bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
comp = np.full(n, -1); c = 0
for v in bm.verts:
    if comp[v.index] >= 0: continue
    st = [v]; comp[v.index] = c
    while st:
        u = st.pop()
        for e in u.link_edges:
            w = e.other_vert(u)
            if comp[w.index] < 0: comp[w.index] = c; st.append(w)
    c += 1
main = int(np.argmax(np.bincount(comp)))
body = co[comp == main]
y0, y1 = co[:, 1].min(), co[:, 1].max(); L = y1 - y0
by0, by1 = body[:, 1].min(), body[:, 1].max()
def mid_z(y, w=0.04 * L):
    s = body[np.abs(body[:, 1] - y) < w]; return float(np.median(s[:, 2])) if len(s) else 0.0
def mid_x(y, w=0.04 * L):
    s = body[np.abs(body[:, 1] - y) < w]; return float(np.median(s[:, 0])) if len(s) else 0.0

pieces = []
for k in range(c):
    if k == main: continue
    p = co[comp == k]; pieces.append((k, p))
# gills: the two pieces reaching furthest out sideways (relative to the head's middle)
hx = mid_x(by0 + 0.08 * L)
reach = sorted(pieces, key=lambda kp: -np.abs(kp[1][:, 0] - hx).max())
gills = []
for k, p in reach:
    side = np.sign(p[:, 0].mean() - hx)
    if all(np.sign(q[:, 0].mean() - hx) != side for _, q in gills): gills.append((k, p))
    if len(gills) == 2: break
# pincers: the two biggest remaining pieces that hang below the head's middle
rest = [kp for kp in pieces if kp[0] not in [g[0] for g in gills]]
hz = mid_z(by0 + 0.08 * L)
pinc = sorted([kp for kp in rest if kp[1][:, 2].min() < hz - 0.05 * L], key=lambda kp: -len(kp[1]))[:2]
pinc.sort(key=lambda kp: kp[1][:, 0].mean())            # left (x>0 is L) handled below
if os.environ.get("VDW_NO_PIECE_BONES") == "1":           # loose bits are teeth/spikes, not gills or pincers
    gills, pinc = [], []
HEAD_END = float(os.environ.get("VDW_HEAD_END") or 0) * L + y0 if os.environ.get("VDW_HEAD_END") else max(g[1][:, 1].min() for g in gills) if gills else by0 + 0.1 * L
print(f"\n===== RIG EEL =====\n  length {L:.2f}, body {by0:.2f}..{by1:.2f}, head ends at y {HEAD_END:.2f}")
print("  gills:", [(k, len(p)) for k, p in gills], " pincers:", [(k, len(p)) for k, p in pinc])

arm_data = bpy.data.armatures.new("Armature"); arm = bpy.data.objects.new("Armature", arm_data)
bpy.context.scene.collection.objects.link(arm); bpy.context.view_layer.objects.active = arm
for o in bpy.context.view_layer.objects: o.select_set(False)
arm.select_set(True)
bpy.ops.object.mode_set(mode='EDIT'); eb = arm_data.edit_bones
def bone(name, h, t, parent=None, connect=False, deform=True):
    b = eb.new(name); b.head = Vector(h); b.tail = Vector(t); b.use_deform = deform
    if parent: b.parent = eb[parent]; b.use_connect = connect
    return b
def P(y): return (mid_x(y), y, mid_z(y))
bone("Root", P(HEAD_END), (mid_x(HEAD_END), HEAD_END + 0.05 * L, mid_z(HEAD_END)), deform=False)
bone("Head", P(HEAD_END), P(by0 + 0.02 * L), "Root")
ys = np.linspace(HEAD_END, by1, NSP + 1)
names = ["Spine"] + [f"Spine{k}" for k in range(1, NSP)]
for k, nm in enumerate(names):
    bone(nm, P(ys[k]), P(ys[k + 1]), "Root" if k == 0 else names[k - 1], connect=k > 0)
def piece_bone(name, p):
    d = np.linalg.norm(p[:, None, :] - body[None, ::3, :], axis=2).min(1)
    base = p[np.argmin(d)]; tip = p[np.argmax(np.linalg.norm(p - base, axis=1))]
    bone(name, tuple(base), tuple(tip), "Head")
for k, p in gills: piece_bone("Gill." + ("L" if p[:, 0].mean() > hx else "R"), p)
for k, p in pinc: piece_bone("Pincer." + ("L" if p[:, 0].mean() > hx else "R"), p)
bpy.ops.object.mode_set(mode='OBJECT')

# bind
for o in bpy.context.view_layer.objects: o.select_set(False)
mesh.select_set(True); arm.select_set(True); bpy.context.view_layer.objects.active = arm
bpy.ops.object.parent_set(type='ARMATURE_NAME')
vg = mesh.vertex_groups
piece_bone_of = {}
for k, p in gills: piece_bone_of[k] = "Gill." + ("L" if p[:, 0].mean() > hx else "R")
for k, p in pinc: piece_bone_of[k] = "Pincer." + ("L" if p[:, 0].mean() > hx else "R")
centres = [(ys[k] + ys[k + 1]) / 2 for k in range(NSP)]
chain = [("Head", HEAD_END - 0.03 * L)] + list(zip(names, centres))
for i in range(n):
    k = comp[i]
    if k != main:
        vg[piece_bone_of.get(k, "Head")].add([i], 1.0, 'REPLACE'); continue
    y = co[i, 1]
    if y <= chain[0][1]: vg["Head"].add([i], 1.0, 'REPLACE'); continue
    if y >= chain[-1][1]: vg[chain[-1][0]].add([i], 1.0, 'REPLACE'); continue
    for j in range(len(chain) - 1):
        (a, ya), (b, yb) = chain[j], chain[j + 1]
        if ya <= y <= yb:
            t = (y - ya) / (yb - ya)
            if 1 - t > 0.001: vg[a].add([i], 1 - t, 'REPLACE')
            if t > 0.001: vg[b].add([i], t, 'REPLACE')
            break
cnt = {g.name: sum(1 for v in me.vertices for gg in v.groups if gg.group == g.index and gg.weight > 0.05) for g in vg}
print("  bones:", [b.name for b in arm_data.bones])
print("  weighted vertices per bone:", cnt)
bpy.ops.wm.save_as_mainfile(filepath=SAVE_TO)
print("  saved", SAVE_TO)
print("===== END =====")
