# Sets the fisherman's gear up for weight painting in Blender, on Valheim's own player skeleton:
#   - "Armature": the player's bones, named and placed exactly as in the game (from the rip's player_male.prefab and the
#     body mesh's bind poses), plus vdw_skirt0..7 round the hips (the coat's skirt bones the mod swings in the wind)
#   - "fitref" (the body) carries Valheim's own skin weights (from body.asset), as a reference and a source
#   - every gear piece parented to the armature with weights copied from the body as a start, the coat's skirt partly
#     handed to the skirt bones - ready to paint
# Writes a new .blend. blender -b fisher_gear_v4.blend --python build_gear_rig.py
#   env: VDW_RIP (ExportedProject/Assets/Characters/Player/model), VDW_SAVE_TO
import bpy, bmesh, math, os, re
import numpy as np
from mathutils import Matrix, Vector
from mathutils.kdtree import KDTree

RIP = os.environ["VDW_RIP"]; SAVE_TO = os.environ["VDW_SAVE_TO"]
PIECES = ["shirt", "coat", "overalls", "boots", "hat"]
SKIRT = 8

# ---- the skeleton: names and parents from the prefab, rest poses from the body mesh's bind poses
pre = open(os.path.join(RIP, "player_male.prefab"), encoding="utf-8").read()
docs = re.split(r"^--- !u!(\d+) &(\d+)", pre, flags=re.M)
names, father, smr_bones = {}, {}, []
go_of = {}
for i in range(1, len(docs) - 2, 3):
    cls, fid, body_ = docs[i], docs[i + 1], docs[i + 2]
    if cls == "1": names[fid] = re.search(r"m_Name: (.*)", body_).group(1).strip()
    elif cls == "4":
        go_of[fid] = re.search(r"m_GameObject: \{fileID: (\d+)\}", body_).group(1)
        father[fid] = re.search(r"m_Father: \{fileID: (\d+)\}", body_).group(1)
    elif cls == "137": smr_bones = re.findall(r"- \{fileID: (\d+)\}", body_.split("m_Bones:")[1].split("m_BlendShapeWeights")[0])
bone_names = [names[go_of[f]] for f in smr_bones]
parent_of = {names[go_of[f]]: (names[go_of[father[f]]] if father[f] in go_of else None) for f in smr_bones}
asset = open(os.path.join(RIP, "body.asset"), encoding="utf-8").read()
bp = asset[asset.index("m_BindPose:"):asset.index("m_BoneNameHashes")]
mats = []
for blk in re.findall(r"- e00: [^\n]+(?:\n\s+e\d\d: [^\n]+){15}", bp):
    e = {k: float(v) for k, v in re.findall(r"e(\d\d): ([-0-9.eE]+)", blk)}
    mats.append(Matrix([[e[f"{r}{c}"] for c in range(4)] for r in range(4)]))
assert len(mats) == len(bone_names), (len(mats), len(bone_names))
S = 1e4                                       # body mesh units -> the scene's centimetres (checked: same axes)
rest = {n: m.inverted() for n, m in zip(bone_names, mats)}
head = {n: Vector(rest[n].translation) * S for n in bone_names}
print(f"\n===== GEAR RIG =====\n  {len(bone_names)} bones: {', '.join(bone_names[:8])} ...")

for o in [o for o in bpy.data.objects if o.type == 'ARMATURE']: bpy.data.objects.remove(o)
arm_d = bpy.data.armatures.new("Armature"); arm = bpy.data.objects.new("Armature", arm_d); bpy.context.scene.collection.objects.link(arm)
for o in bpy.data.objects: o.select_set(o == arm)
bpy.context.view_layer.objects.active = arm; arm.hide_set(False)
bpy.ops.object.mode_set(mode='EDIT')
children = {n: [c for c in bone_names if parent_of[c] == n] for n in bone_names}
for n in bone_names:
    b = arm_d.edit_bones.new(n); b.head = head[n]
    kids = [head[c] for c in children[n] if (head[c] - head[n]).length > 0.5]
    if len(kids) == 1 or (kids and n not in ("Hips",)): tail = sum(kids, Vector()) / len(kids)
    else:                                                     # a leaf (or the hips): along its own up axis
        ax = Vector(rest[n].col[1][:3]).normalized(); tail = head[n] + ax * 6.0
    if (tail - head[n]).length < 0.5: tail = head[n] + Vector((0, 0, 3))
    b.tail = tail
for n in bone_names:
    if parent_of[n] in arm_d.edit_bones: arm_d.edit_bones[n].parent = arm_d.edit_bones[parent_of[n]]
hips = arm_d.edit_bones["Hips"]; hip_c = hips.head.copy()
for i in range(SKIRT):                                         # the skirt bones: hanging from the hips, one per direction
    a = (i + 0.5) / SKIRT * 2 * math.pi
    b = arm_d.edit_bones.new(f"vdw_skirt{i}"); b.head = hip_c
    b.tail = hip_c + Vector((math.cos(a) * 22, math.sin(a) * 22, -45)); b.parent = hips
bpy.ops.object.mode_set(mode='OBJECT')
arm.show_in_front = True

# ---- the body (fitref) with Valheim's weights
fit = bpy.data.objects.get("fitref")
if fit is None:
    src = bpy.data.objects["PlayerCharacter_01"]; me = src.data.copy(); me.transform(src.matrix_world)
    fit = bpy.data.objects.new("fitref", me); bpy.context.scene.collection.objects.link(fit)
fit.hide_set(False); fit.vertex_groups.clear()
vd = asset[asset.index("m_VertexData:"):]
n = int(re.search(r"m_VertexCount: (\d+)", vd).group(1))
raw = bytes.fromhex(re.search(r"_typelessdata: ([0-9a-f]+)", vd).group(1))
P = np.frombuffer(raw[:n * 40], np.float32).reshape(n, 10)[:, :3] * S
s2 = (n * 40 + 15) // 16 * 16; s2 = (s2 + n * 8 + 15) // 16 * 16
sk = np.frombuffer(raw[s2:s2 + n * 32], np.uint8).reshape(n, 32)
W = sk[:, :16].copy().view(np.float32); I = sk[:, 16:].copy().view(np.uint32)
kd = KDTree(n)
for i, p in enumerate(P): kd.insert(p, i)
kd.balance()
groups = {nm: fit.vertex_groups.new(name=nm) for nm in bone_names}
for v in fit.data.vertices:
    _c, j, _d = kd.find(fit.matrix_world @ v.co)
    for k in range(4):
        if W[j, k] > 1e-4: groups[bone_names[I[j, k]]].add([v.index], float(W[j, k]), 'REPLACE')
def bind(ob):
    mw = ob.matrix_world.copy(); ob.parent = arm; ob.matrix_world = mw
    for m in [m for m in ob.modifiers if m.type == 'ARMATURE']: ob.modifiers.remove(m)
    md = ob.modifiers.new("Armature", 'ARMATURE'); md.object = arm
bind(fit)

# ---- the gear: weights from the body as a start (the mod's own rules, so painting starts from what's in game now):
# a blend of the body points near each vertex, only from its own side of the body's middle; the coat's skirt and the
# overalls' crotch follow both thighs more evenly the nearer the middle; the boots on one bone per point
FW = []                                                    # body vertex -> {bone: weight}
for v in fit.data.vertices:
    FW.append({fit.vertex_groups[g.group].name: g.weight for g in v.groups if g.weight > 1e-4})
FP = np.array([(fit.matrix_world @ v.co)[:] for v in fit.data.vertices])
hip_z = hip_c.z
# weights by closeness to the bones themselves (each bone a segment from its head to its child's): the body mesh is too
# sparse on the limbs to copy from (a thigh's nearest body points are at the knee). Fingers, jaw and the like skipped.
SKIP = ("Hand", "Thumb", "Index", "Middle", "Ring", "Pinky", "Jaw", "Toe", "Eye", "Head")
segs = []
for b in arm.data.bones:
    if b.name.startswith("vdw_") or any(k in b.name for k in SKIP) and b.name not in ("LeftHand", "RightHand", "Head"): continue
    h = arm.matrix_world @ b.head_local
    kids = [c for c in b.children if not c.name.startswith("vdw_") and not any(k in c.name for k in ("Thumb", "Index", "Middle", "Ring", "Pinky", "Shoulder", "Toe", "Jaw"))]
    tl = (arm.matrix_world @ kids[0].head_local) if len(kids) == 1 else (arm.matrix_world @ b.tail_local)
    segs.append((b.name, np.array(h[:]), np.array(tl[:])))
def bone_weights(p, sharp=6.0, mid=2.0):
    out = {}
    for nm, a, b in segs:
        side = -1 if nm.startswith("Left") else 1 if nm.startswith("Right") else 0
        if side and abs(p[0]) > mid and np.sign(p[0]) != side: continue
        ab = b - a; t_ = float(np.clip(np.dot(p - a, ab) / max(np.dot(ab, ab), 1e-6), 0, 1))
        d = float(np.linalg.norm(a + ab * t_ - p))
        out[nm] = 1.0 / (d + 1.0) ** sharp
    top = sorted(out.items(), key=lambda kv: -kv[1])[:3]; tot = sum(x for _, x in top) or 1.0
    return {k: v / tot for k, v in top}
def body_weights(p, sigma, K=10, mid=2.0):
    return bone_weights(p, 8.0 if sigma <= 1.0 else 6.0)
def _old_body_weights(p, sigma, K=10, mid=2.0):
    any_side = abs(p[0]) < mid
    d = np.linalg.norm(FP - p, axis=1)
    if not any_side:
        d = np.where((np.abs(FP[:, 0]) > mid) & (np.sign(FP[:, 0]) != np.sign(p[0])), np.inf, d)
    idx = np.argsort(d)[:K]; d0 = d[idx[0]]
    out = {}
    for j in idx:
        if not np.isfinite(d[j]): continue
        f = math.exp(-((d[j] - d0) / sigma) ** 2)
        for bn, w in FW[j].items(): out[bn] = out.get(bn, 0.0) + w * f
    tot = sum(out.values()) or 1.0
    return {k: v / tot for k, v in out.items()}
def mixw(a, b, m):
    out = {k: v * (1 - m) for k, v in a.items()}
    for k, v in b.items(): out[k] = out.get(k, 0.0) + v * m
    return out
for name in PIECES:
    ob = bpy.data.objects[name]; ob.vertex_groups.clear()
    vg = {}
    sigma = 1.0 if name == "boots" else 2.0 if name == "overalls" else 4.0
    for v in ob.data.vertices:
        p = np.array((ob.matrix_world @ v.co)[:])
        w = body_weights(p, sigma)
        skirt, crotch = name == "coat", name == "overalls"
        if (skirt or crotch) and p[2] < hip_z and not (crotch and p[2] < hip_z - 35):
            m = 0.5 * (1 - min(1.0, abs(p[0]) / (15.0 if skirt else 6.0)))
            if m > 0.01: w = mixw(w, body_weights(np.array([-p[0], p[1], p[2]]), sigma), m)
        if name == "boots": w = {max(w, key=w.get): 1.0}
        top = sorted(w.items(), key=lambda kv: -kv[1])[:4]; tot = sum(x for _, x in top) or 1.0
        for bn, x in top:
            if bn not in vg: vg[bn] = ob.vertex_groups.new(name=bn)
            vg[bn].add([v.index], x / tot, 'REPLACE')
    if name == "hat":                                       # the hat moves with the head alone
        ob.vertex_groups.clear(); g = ob.vertex_groups.new(name="Head"); g.add([v.index for v in ob.data.vertices], 1.0, 'REPLACE')
    bind(ob)
    print(f"  {name}: weighted to {len(ob.vertex_groups)} bones")
coat = bpy.data.objects["coat"]
sg = [coat.vertex_groups.new(name=f"vdw_skirt{i}") for i in range(SKIRT)]
hem = min((coat.matrix_world @ v.co).z for v in coat.data.vertices)
for v in coat.data.vertices:
    p = coat.matrix_world @ v.co
    t = min(1.0, max(0.0, (hip_c.z - 6 - p.z) / (hip_c.z - 6 - hem)))
    s = 0.35 * t * t * (3 - 2 * t)
    if s <= 0.001: continue
    for g in v.groups: g.weight *= (1 - s)
    a = (math.atan2(p.y - hip_c.y, p.x - hip_c.x) / (2 * math.pi)) % 1.0 * SKIRT
    b0 = int(a) % SKIRT; f1 = a - int(a)
    sg[b0].add([v.index], s * (1 - f1), 'ADD'); sg[(b0 + 1) % SKIRT].add([v.index], s * f1, 'ADD')
# tidy: drop empty groups from the gear so the lists stay short to paint
for name in PIECES:
    ob = bpy.data.objects[name]; used = {ob.vertex_groups[g.group].name for v in ob.data.vertices for g in v.groups if g.weight > 1e-4}   # by name: removing a group renumbers the rest
    for nm in [g.name for g in ob.vertex_groups if g.name not in used and not g.name.startswith("vdw_skirt")]: ob.vertex_groups.remove(ob.vertex_groups[nm])
for o in ("PlayerCharacter_01", "PlayerCharacter_01.001", "weighters"):
    if o in bpy.data.objects: bpy.data.objects[o].hide_set(True)
bpy.ops.wm.save_as_mainfile(filepath=SAVE_TO, copy=True); print("  saved", SAVE_TO)
print("===== END =====")
