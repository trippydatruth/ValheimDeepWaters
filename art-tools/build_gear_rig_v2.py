# Sets the remade fisherman's gear (new_gear.blend) up for weight painting on Valheim's own player skeleton, at the
# game's true size (1 Blender unit = 1 m; the player stands about 2 m to the top of the head):
#   - "Armature": the player's bones, named, parented and placed exactly as in the game (rip's player_male.prefab +
#     the body mesh's bind poses), plus vdw_skirt0..7 round the hips (the coat skirt bones the mod swings in the wind)
#   - "fitref": the player body (the file's "player" mesh, which is the game's body) with Valheim's own skin weights
#     copied from body.asset - a reference to paint against and to copy from
#   - every other mesh parented to the armature with starting weights by closeness to the bones (sides kept apart,
#     fingers / toes / jaw skipped): faces with a hat material on the head alone, boot material on one bone per point,
#     coat material below the hips partly handed to the skirt bones and evened between the legs near the middle
# The meshes are scaled from centimetres to metres in the mesh data (no object scale left to apply).
# Never touches the input file: writes VDW_SAVE_TO.   blender -b new_gear.blend --python build_gear_rig_v2.py
#   env: VDW_RIP (ExportedProject/Assets/Characters/Player/model), VDW_SAVE_TO, VDW_BODY (body mesh name, "player")
import bpy, math, os, re
import numpy as np
from mathutils import Matrix, Vector
from mathutils.kdtree import KDTree
for _o in list(bpy.data.objects):
    if _o.mode != 'OBJECT' and _o.name in bpy.context.view_layer.objects:
        bpy.context.view_layer.objects.active = _o; bpy.ops.object.mode_set(mode='OBJECT')
RIP = os.environ["VDW_RIP"]; SAVE_TO = os.environ["VDW_SAVE_TO"]; BODY = os.environ.get("VDW_BODY", "player")
if os.path.exists(SAVE_TO): raise SystemExit("refusing to overwrite " + SAVE_TO)
CM = 0.01                     # the file is modelled in centimetres; everything below is built in metres
SKIRT = 8

# ---- 0. centimetres -> metres, baked into the mesh data
for o in [o for o in bpy.data.objects if o.type == 'MESH']:
    o.data.transform(o.matrix_world); o.matrix_world = Matrix.Identity(4)
    o.data.transform(Matrix.Scale(CM, 4)); o.data.update()

# ---- 1. the skeleton: names and parents from the prefab, rest poses from the body mesh's bind poses
pre = open(os.path.join(RIP, "player_male.prefab"), encoding="utf-8").read()
docs = re.split(r"^--- !u!(\d+) &(\d+)", pre, flags=re.M)
names, father, go_of, smr_bones = {}, {}, {}, []
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
S = 1e4 * CM                                  # body mesh units -> metres (1e4 gave the file's centimetres)
rest = {n: m.inverted() for n, m in zip(bone_names, mats)}
head = {n: Vector(rest[n].translation) * S for n in bone_names}
print(f"\n===== GEAR RIG v2 =====\n  {len(bone_names)} bones: {', '.join(bone_names[:8])} ...")

for o in [o for o in bpy.data.objects if o.type == 'ARMATURE']: bpy.data.objects.remove(o)
arm_d = bpy.data.armatures.new("Armature"); arm = bpy.data.objects.new("Armature", arm_d); bpy.context.scene.collection.objects.link(arm)
for o in bpy.data.objects: o.select_set(o == arm)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
children = {n: [c for c in bone_names if parent_of[c] == n] for n in bone_names}
for n in bone_names:
    b = arm_d.edit_bones.new(n); b.head = head[n]
    kids = [head[c] for c in children[n] if (head[c] - head[n]).length > 0.5 * CM]
    if len(kids) == 1 or (kids and n != "Hips"): tail = sum(kids, Vector()) / len(kids)
    else: tail = head[n] + Vector(rest[n].col[1][:3]).normalized() * 6.0 * CM
    if (tail - head[n]).length < 0.5 * CM: tail = head[n] + Vector((0, 0, 3 * CM))
    b.tail = tail
for n in bone_names:
    if parent_of[n] in arm_d.edit_bones: arm_d.edit_bones[n].parent = arm_d.edit_bones[parent_of[n]]
hip_c = arm_d.edit_bones["Hips"].head.copy()
for i in range(SKIRT):
    a = (i + 0.5) / SKIRT * 2 * math.pi
    b = arm_d.edit_bones.new(f"vdw_skirt{i}"); b.head = hip_c
    b.tail = hip_c + Vector((math.cos(a) * 22, math.sin(a) * 22, -45)) * CM; b.parent = arm_d.edit_bones["Hips"]
bpy.ops.object.mode_set(mode='OBJECT')
arm.show_in_front = True; arm.data.display_type = 'STICK'

def bind(ob):
    ob.parent = arm; ob.matrix_parent_inverse = Matrix.Identity(4)
    for m in [m for m in ob.modifiers if m.type == 'ARMATURE']: ob.modifiers.remove(m)
    md = ob.modifiers.new("Armature", 'ARMATURE'); md.object = arm

# ---- 2. the body (fitref) with Valheim's own weights, by nearest point of the game's body mesh
fit = bpy.data.objects[BODY]; fit.name = "fitref"; fit.vertex_groups.clear()
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
far = 0.0
for v in fit.data.vertices:
    _c, j, d = kd.find(v.co); far = max(far, d)
    for k in range(4):
        if W[j, k] > 1e-4: groups[bone_names[I[j, k]]].add([v.index], float(W[j, k]), 'REPLACE')
print(f"  fitref: {len(fit.data.vertices)} points, Valheim's weights copied (farthest match {far * 100:.2f} cm)")
bind(fit)

# ---- 3. the gear: starting weights by closeness to the bones (each a segment from its head to its child's)
SKIP = ("Hand", "Thumb", "Index", "Middle", "Ring", "Pinky", "Jaw", "Toe", "Eye", "Head")
segs = []
for b in arm.data.bones:
    if b.name.startswith("vdw_") or any(k in b.name for k in SKIP) and b.name not in ("LeftHand", "RightHand", "Head"): continue
    kids = [c for c in b.children if not c.name.startswith("vdw_") and not any(k in c.name for k in ("Thumb", "Index", "Middle", "Ring", "Pinky", "Shoulder", "Toe", "Jaw"))]
    tl = kids[0].head_local if len(kids) == 1 else b.tail_local
    segs.append((b.name, np.array(b.head_local[:]), np.array(tl[:])))
def bone_weights(p, sharp, mid=2.0 * CM):
    out = {}
    for nm, a, b in segs:
        side = -1 if nm.startswith("Left") else 1 if nm.startswith("Right") else 0
        if side and abs(p[0]) > mid and np.sign(p[0]) != side: continue
        ab = b - a; t_ = float(np.clip(np.dot(p - a, ab) / max(np.dot(ab, ab), 1e-9), 0, 1))
        d = float(np.linalg.norm(a + ab * t_ - p)) / CM          # in centimetres, as tuned
        out[nm] = 1.0 / (d + 1.0) ** sharp
    top = sorted(out.items(), key=lambda kv: -kv[1])[:3]; tot = sum(x for _, x in top) or 1.0
    return {k: v / tot for k, v in top}
def mixw(a, b, m):
    out = {k: v * (1 - m) for k, v in a.items()}
    for k, v in b.items(): out[k] = out.get(k, 0.0) + v * m
    return out
def kind_of(mat):
    m = (mat.name if mat else "").lower()
    return "hat" if "hat" in m else "boot" if "boot" in m else "coat" if "coat" in m else "overalls" if "overall" in m else "cloth"
hem_z = {}
for ob in [o for o in bpy.data.objects if o.type == 'MESH' and o != fit]:
    ob.vertex_groups.clear(); me = ob.data
    vk = {}                                                     # a point's kind: from the faces round it (first wins)
    for poly in me.polygons:
        k = kind_of(me.materials[poly.material_index] if me.materials else None)
        for vi in poly.vertices: vk.setdefault(vi, k)
    vg = {}
    def put(vi, w):
        top = sorted(w.items(), key=lambda kv: -kv[1])[:4]; tot = sum(x for _, x in top) or 1.0
        for bn, x in top:
            if bn not in vg: vg[bn] = ob.vertex_groups.new(name=bn)
            vg[bn].add([vi], x / tot, 'REPLACE')
    for v in me.vertices:
        k = vk.get(v.index, "cloth"); p = np.array(v.co[:])
        if k == "hat": put(v.index, {"Head": 1.0}); continue
        w = bone_weights(p, 8.0 if k == "boot" else 6.0)
        if k in ("coat", "overalls") and p[2] < hip_c.z and not (k == "overalls" and p[2] < hip_c.z - 35 * CM):
            m = 0.5 * (1 - min(1.0, abs(p[0]) / ((15.0 if k == "coat" else 6.0) * CM)))
            if m > 0.01: w = mixw(w, bone_weights(np.array([-p[0], p[1], p[2]]), 6.0), m)
        if k == "boot": w = {max(w, key=w.get): 1.0}
        put(v.index, w)
    coat_v = [v for v in me.vertices if vk.get(v.index) == "coat"]
    if coat_v:                                                  # the coat's skirt: partly on the skirt bones toward the hem
        sg = [ob.vertex_groups.new(name=f"vdw_skirt{i}") for i in range(SKIRT)]
        hem = min(v.co.z for v in coat_v)
        for v in coat_v:
            t = min(1.0, max(0.0, (hip_c.z - 6 * CM - v.co.z) / max(hip_c.z - 6 * CM - hem, 1e-6)))
            s = 0.35 * t * t * (3 - 2 * t)
            if s <= 0.001: continue
            for g in v.groups: g.weight *= (1 - s)
            a = (math.atan2(v.co.y - hip_c.y, v.co.x - hip_c.x) / (2 * math.pi)) % 1.0 * SKIRT
            b0 = int(a) % SKIRT; f1 = a - int(a)
            sg[b0].add([v.index], s * (1 - f1), 'ADD'); sg[(b0 + 1) % SKIRT].add([v.index], s * f1, 'ADD')
    used = {ob.vertex_groups[g.group].name for v in me.vertices for g in v.groups if g.weight > 1e-4}   # by name: removing a group renumbers the rest
    for nm in [g.name for g in ob.vertex_groups if g.name not in used and not g.name.startswith("vdw_skirt")]: ob.vertex_groups.remove(ob.vertex_groups[nm])
    bind(ob)
    kinds = sorted(set(vk.values()))
    print(f"  {ob.name}: {len(me.vertices)} points ({', '.join(kinds)}), weighted to {len(ob.vertex_groups)} bones")

# ---- 4. a scene in metres, the body shown as a see-through reference
sc = bpy.context.scene; sc.unit_settings.system = 'METRIC'; sc.unit_settings.scale_length = 1.0; sc.unit_settings.length_unit = 'METERS'
fit.display_type = 'WIRE'; fit.hide_render = True
co = np.array([v.co[:] for v in fit.data.vertices])
print(f"  player body: {co[:, 2].max():.3f} m to the top of the head, arms {np.ptp(co[:, 0]):.3f} m across (T-pose)")
for sp in (s for a in bpy.data.screens for ar in a.areas if ar.type == 'VIEW_3D' for s in ar.spaces if s.type == 'VIEW_3D'):
    sp.clip_start = 0.01; sp.clip_end = 100.0
bpy.ops.wm.save_as_mainfile(filepath=SAVE_TO); print("  saved", SAVE_TO)
print("===== END =====")
