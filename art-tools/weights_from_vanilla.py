# Copies a vanilla Valheim armour's skin weights onto worn gear pieces (e.g. the Eitr-weave robe's onto the coat's
# collar/skirt and belt, so a long coat bends with the legs the way Valheim's own robe does). Shapes and UVs untouched.
#   1. reads the vanilla mesh and the player body from the game rip's Unity .asset files (positions, triangles, 4 bone
#      weights per point; bones from their name hashes = CRC32 of "Armature/Hips/...")
#   2. lines the rip's space up on this file's fitref (the same game body): of the 48 axis turns, the one whose body
#      points land nearest after matching the bounding boxes, then a fine fit (scale + move) on the nearest points
#   3. every point of each piece takes the nearest spot on the vanilla mesh and blends that triangle's corner weights
#      by where it lands; at most 4 bones, normalised
#   blender -b fisher_gear_ingame_v2.blend --python weights_from_vanilla.py
#   env: VDW_VANILLA (.asset of the worn mesh), VDW_BODY_ASSET (the rip's Player body.asset), VDW_PIECES (objects,
#        comma list), VDW_SAVE_TO (new .blend, never overwrites)
import bpy, os, re, struct, zlib, itertools, numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

VAN, BODY, SAVE_TO = os.environ["VDW_VANILLA"], os.environ["VDW_BODY_ASSET"], os.environ["VDW_SAVE_TO"]
PIECES = [p for p in os.environ["VDW_PIECES"].split(",") if p]
if os.path.exists(SAVE_TO): raise SystemExit("exists, kept: " + SAVE_TO)
for o in list(bpy.data.objects):
    if o.mode != 'OBJECT' and o.name in bpy.context.view_layer.objects:
        bpy.context.view_layer.objects.active = o; bpy.ops.object.mode_set(mode='OBJECT')
arm = bpy.data.objects["Armature"]
for pb in arm.pose.bones: pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.rotation_euler = (0, 0, 0); pb.scale = (1, 1, 1)
bpy.context.view_layer.update()

FMT = {0: ('f', 4), 1: ('e', 2), 2: ('B', 1), 3: ('b', 1), 4: ('H', 2), 5: ('h', 2), 6: ('B', 1), 7: ('b', 1), 8: ('H', 2), 9: ('h', 2), 10: ('I', 4), 11: ('i', 4)}
NP = {'f': np.float32, 'e': np.float16, 'B': np.uint8, 'b': np.int8, 'H': np.uint16, 'h': np.int16, 'I': np.uint32, 'i': np.int32}
def read_asset(path):
    t = open(path, encoding="utf-8").read()
    vd = t[t.index("m_VertexData:"):]
    n = int(re.search(r"m_VertexCount: (\d+)", vd).group(1))
    ch = [tuple(int(x) for x in m) for m in re.findall(r"- stream: (\d+)\s+offset: (\d+)\s+format: (\d+)\s+dimension: (\d+)", vd)]
    raw = bytes.fromhex(re.search(r"_typelessdata: ([0-9a-f]+)", vd).group(1))
    strides = {}
    for s, off, f, d in ch:
        if d: strides[s] = max(strides.get(s, 0), off + (d & 0xF) * FMT[f][1])
    starts, pos = {}, 0
    for s in sorted(strides):
        starts[s] = pos; pos = (pos + n * strides[s] + 15) // 16 * 16
    def channel(i):
        s, off, f, d = ch[i]; d &= 0xF; code, size = FMT[f]
        a = np.frombuffer(raw, np.uint8, n * strides[s], starts[s]).reshape(n, strides[s])[:, off:off + d * size]
        return a.copy().view(NP[code]).reshape(n, d).astype(np.float64 if code in 'fe' else np.int64)
    P = channel(0)
    W, I = channel(12), channel(13)
    ib = bytes.fromhex(re.search(r"m_IndexBuffer: ([0-9a-f]+)", t).group(1))
    fmt = int(re.search(r"m_IndexFormat: (\d+)", t).group(1))
    T = np.frombuffer(ib, np.uint16 if fmt == 0 else np.uint32).astype(np.int64).reshape(-1, 3)
    h = bytes.fromhex(re.search(r"m_BoneNameHashes: ([0-9a-f]+)", t).group(1))
    hashes = struct.unpack("<%dI" % (len(h) // 4), h)
    return P, T, W, I, hashes

# bone hash -> our bone name
def path(b):
    p = []
    while b: p.insert(0, b.name); b = b.parent
    return "Armature/" + "/".join(p)
by_hash = {zlib.crc32(path(b).encode()): b.name for b in arm.data.bones}

VP, VT, VW, VI, VH = read_asset(VAN)
BP, _bt, _bw, _bi, _bh = read_asset(BODY)
vbones = [by_hash.get(x) for x in VH]
if any(b is None for b in vbones): raise SystemExit(f"bones not in the Armature: {[i for i, b in enumerate(vbones) if b is None]}")
print(f"VANILLA {os.path.basename(VAN)}: {len(VP)} points, {len(VT)} triangles, {len(vbones)} bones")

# --- the rip's space onto fitref (world), through the body both share
fit = bpy.data.objects["fitref"]; dg = bpy.context.evaluated_depsgraph_get(); fe = fit.evaluated_get(dg); fme = fe.to_mesh()
FP = np.array([tuple(fe.matrix_world @ v.co) for v in fme.vertices]); fe.to_mesh_clear()
kd = KDTree(len(FP))
for i, p in enumerate(FP): kd.insert(p, i)
kd.balance()
def score(A): return float(np.mean([kd.find(p)[2] for p in A[::3]]))
best = None
for perm in itertools.permutations(range(3)):
    for sg in itertools.product((1, -1), repeat=3):
        R = np.zeros((3, 3))
        for r in range(3): R[r, perm[r]] = sg[r]
        A = BP @ R.T
        s = (FP.max(0) - FP.min(0)).mean() / (A.max(0) - A.min(0)).mean()
        A = A * s; A += (FP.max(0) + FP.min(0)) / 2 - (A.max(0) + A.min(0)) / 2
        e = score(A)
        if best is None or e < best[0]: best = (e, R, s, A)
e, R, s, A = best
t = A.mean(0) - s * (BP @ R.T).mean(0)
# fine fit: similarity from the body points to their nearest fitref points, a few rounds
M = np.eye(4); M[:3, :3] = s * R; M[:3, 3] = t
for _ in range(5):
    A = BP @ M[:3, :3].T + M[:3, 3]
    B = np.array([kd.find(p)[0] for p in A])
    ma, mb = A.mean(0), B.mean(0); U_, S_, Vt = np.linalg.svd((B - mb).T @ (A - ma))
    D = np.eye(3); D[2, 2] = np.sign(np.linalg.det(U_ @ Vt)); Rr = U_ @ D @ Vt
    sc = (S_ * np.diag(D)).sum() / ((A - ma) ** 2).sum()
    step = np.eye(4); step[:3, :3] = sc * Rr; step[:3, 3] = mb - sc * Rr @ ma; M = step @ M
A = BP @ M[:3, :3].T + M[:3, 3]
print(f"FIT body onto fitref: mean {np.mean([kd.find(p)[2] for p in A]) * 100:.2f} cm, max {max(kd.find(p)[2] for p in A) * 100:.2f} cm")
VPw = VP @ M[:3, :3].T + M[:3, 3]
print(f"VANILLA placed: z {VPw[:, 2].min():.2f}..{VPw[:, 2].max():.2f} m")

# --- the weights
bvh = BVHTree.FromPolygons([Vector(p) for p in VPw], [tuple(int(x) for x in tri) for tri in VT], all_triangles=True)
def weights_at(p):
    loc, n, ti, d = bvh.find_nearest(p)
    a, b, c = (Vector(VPw[k]) for k in VT[ti])
    v0, v1, v2 = b - a, c - a, loc - a
    d00, d01, d11, d20, d21 = v0.dot(v0), v0.dot(v1), v1.dot(v1), v2.dot(v0), v2.dot(v1)
    den = d00 * d11 - d01 * d01 or 1e-12
    bv = (d11 * d20 - d01 * d21) / den; bw = (d00 * d21 - d01 * d20) / den; bu = 1 - bv - bw
    acc = {}
    for k, f in zip(VT[ti], (bu, bv, bw)):
        for j in range(4):
            if VW[k, j] > 1e-5: acc[vbones[VI[k, j]]] = acc.get(vbones[VI[k, j]], 0) + max(f, 0) * VW[k, j]
    top = sorted(acc.items(), key=lambda kv: -kv[1])[:4]; tot = sum(x for _, x in top) or 1
    return [(k, x / tot) for k, x in top], d

# VDW_BLEND "piece=object": on that piece the copied weights only take over below the other object (the belt): the
# piece's own weights above it (a collar shaped unlike the robe's stays put), fading over VDW_BLEND_BAND m under it (the
# front panel under the belt otherwise took thigh weights and flipped up with a raised knee)
BLEND = dict(kv.split("=") for kv in os.environ.get("VDW_BLEND", "").split(",") if kv)
BAND = float(os.environ.get("VDW_BLEND_BAND", "0.15"))
def smooth(t): t = min(1.0, max(0.0, t)); return t * t * (3 - 2 * t)
# VDW_BLEND_BACK=1: the copied weights on the back half only (the body faces -Y; from VDW_BLEND_BACK_Y m behind the hip
# joints, fully 12 cm further back)
BACK_ONLY = os.environ.get("VDW_BLEND_BACK", "0") == "1"
back_y0 = (arm.matrix_world @ arm.data.bones["Hips"].head_local).y + float(os.environ.get("VDW_BLEND_BACK_Y", "-0.06"))
for name in PIECES:
    o = bpy.data.objects[name]; me = o.data; mw = o.matrix_world
    names = {g.index: g.name for g in o.vertex_groups}
    own = [{names[g.group]: g.weight for g in v.groups if g.weight > 1e-5} for v in me.vertices]
    top_z = None
    if name in BLEND:
        ref = bpy.data.objects[BLEND[name]]; zs = [(ref.matrix_world @ v.co).z for v in ref.data.vertices]; top_z = min(zs)
        # and not above the hip joints: a point in front of them with any thigh weight swings up over the belt as the knee
        # comes up (sitting, crouching)
        hip_z = min((arm.matrix_world @ arm.data.bones[b].head_local).z for b in ("LeftUpLeg", "RightUpLeg"))
        top_z = min(top_z, hip_z)
    for g in list(o.vertex_groups): o.vertex_groups.remove(g)
    far = 0; dmax = 0; kept = 0
    for v, mine in zip(me.vertices, own):
        p = mw @ v.co; ws, d = weights_at(p); dmax = max(dmax, d); far += d > 0.08
        if top_z is not None:
            f = smooth((top_z - p.z) / BAND)                 # 0 at the belt's lower edge and above, 1 a band below
            if BACK_ONLY:
                # the back only (the seat): the front flares well ahead of the thighs, and wholly on a thigh bone it
                # swung up over the belt when sitting; there the piece's own weights (thigh, hips and shin) do better
                f *= smooth((p.y - back_y0) / 0.12)
            acc = {k: (1 - f) * x for k, x in mine.items()}
            for k, x in ws: acc[k] = acc.get(k, 0) + f * x
            top = sorted(acc.items(), key=lambda kv: -kv[1])[:4]; tot = sum(x for _, x in top) or 1
            ws = [(k, x / tot) for k, x in top]; kept += f < 0.5
        for k, x in ws:
            g = o.vertex_groups.get(k) or o.vertex_groups.new(name=k); g.add([v.index], x, 'REPLACE')
    print(f"WEIGHTS {name}: {len(me.vertices)} points, {len(o.vertex_groups)} bones, farthest {dmax * 100:.1f} cm from the robe"
          + (f", {kept} mostly kept their own weights (above / just under {BLEND[name]})" if top_z is not None else ""))
bpy.ops.wm.save_as_mainfile(filepath=SAVE_TO, copy=True)
print("SAVED", SAVE_TO)
