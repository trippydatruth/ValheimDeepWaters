# Shrink-wraps the oilskin coat to the body: the sleeves, back and chest pulled in close over the skin (the shirt and
# overalls are painted on now, so nothing's under it), fading out below the waist so the skirt keeps its shape and
# swing; the collar is kept. Where it hugs the body its weights move to the body's (so tight cloth bends with the skin).
#   blender -b new_gear_rig.blend --python wrap_coat.py
#   env: VDW_SAVE_TO   the new .blend (never overwrites)
#        VDW_WRAP_GAP  cm off the skin (default 0.8; the export's VDW_COAT_OUT adds its own on top)
#        VDW_WRAP_TOP / VDW_WRAP_BOTTOM  metres: full wrap above TOP, none below BOTTOM (defaults 1.15 / 0.92)
#        VDW_PREVIEW   folder for before/after renders (optional)
import bpy, bmesh, os
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.interpolate import poly_3d_calc

SAVE = os.environ["VDW_SAVE_TO"]
if os.path.exists(SAVE): raise SystemExit("exists, kept: " + SAVE)
GAP = float(os.environ.get("VDW_WRAP_GAP", "0.8")) / 100
ARM_GAP = float(os.environ.get("VDW_WRAP_ARM_GAP", str(GAP * 100))) / 100
COLLAR_GAP = float(os.environ.get("VDW_WRAP_COLLAR_GAP", "1.2")) / 100      # the collar round the neck
arm = bpy.data.objects["Armature"]
for pb in arm.pose.bones: pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.rotation_euler = (0, 0, 0); pb.scale = (1, 1, 1)
bpy.context.view_layer.update()
# the wrap fades out above the hips (the seat stays loose: wrapped, the legs pushed through it as they swung back)
hips_z = (arm.matrix_world @ arm.data.bones["Hips"].head_local).z
TOP = float(os.environ.get("VDW_WRAP_TOP", str(hips_z + 0.25)))
BOTTOM = float(os.environ.get("VDW_WRAP_BOTTOM", str(hips_z + 0.08)))
print(f"HIPS at {hips_z:.3f} m: full wrap above {TOP:.3f}, none below {BOTTOM:.3f}")
coat, fit = bpy.data.objects["coat"], bpy.data.objects["fitref"]
CM, FM = coat.matrix_world, fit.matrix_world
CMi = CM.inverted()

def family(name):
    """which part of the body a bone belongs to: each coat point only snaps to the matching part of the body"""
    if name.startswith("Left") and any(k in name for k in ("Arm", "Hand", "Shoulder")): return "larm"
    if name.startswith("Right") and any(k in name for k in ("Arm", "Hand", "Shoulder")): return "rarm"
    if name in ("Neck", "Head", "Jaw"): return "head"
    return "torso"
def top_group(o, v, skip=()):
    best = max(((g.weight, o.vertex_groups[g.group].name) for g in v.groups if o.vertex_groups[g.group].name not in skip), default=(0, ""))
    return best[1]

# the body, split by part, for the nearest-point search
fv = [FM @ v.co for v in fit.data.vertices]
fam_polys = {}
for p in fit.data.polygons:
    fams = [family(top_group(fit, fit.data.vertices[i])) for i in p.vertices]
    fam = max(set(fams), key=fams.count)
    fam_polys.setdefault(fam, []).append(p)
trees = {fam: (BVHTree.FromPolygons(fv, [tuple(p.vertices) for p in ps]), ps) for fam, ps in fam_polys.items()}
whole = BVHTree.FromPolygons(fv, [tuple(p.vertices) for p in fit.data.polygons])
# "shoulder" bones count as arms for the body's faces too, so the torso's own search can't land on the arm, and back
fgroups = {g.index: g.name for g in fit.vertex_groups}
def body_weights(fam, loc, idx):
    poly = trees[fam][1][idx]
    ws = poly_3d_calc([fv[i] for i in poly.vertices], loc); out = {}
    for i, w in zip(poly.vertices, ws):
        for g in fit.data.vertices[i].groups: out[fgroups[g.group]] = out.get(fgroups[g.group], 0) + g.weight * w
    s = sum(out.values()) or 1; return {k: v / s for k, v in out.items()}

def smoothstep(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0))); return t * t * (3 - 2 * t)

pits = [arm.matrix_world @ arm.data.bones[b].head_local for b in ("LeftArm", "RightArm")]
PIT_R = float(os.environ.get("VDW_PIT_RADIUS", "0.14"))
bm = bmesh.new(); bm.from_mesh(coat.data); bm.verts.ensure_lookup_table()
cgroups = {g.index: g.name for g in coat.vertex_groups}
n = len(bm.verts)
P = [CM @ v.co for v in bm.verts]
F = [0.0] * n; D = [Vector() for _ in range(n)]; BW = [None] * n
for i, v in enumerate(bm.verts):
    cv = coat.data.vertices[i]
    fam = family(top_group(coat, cv, skip=tuple(f"vdw_skirt{k}" for k in range(8))))
    # the collar is wrapped round the neck too (left as it was, it stood off the neck and shoulders)
    f = 1.0 if fam in ("larm", "rarm", "head") else smoothstep(BOTTOM, TOP, P[i].z)
    if f <= 0: continue
    tree = trees.get(fam, (whole, None))[0]
    loc, nrm, idx, dist = tree.find_nearest(P[i])
    if loc is None: continue
    out = (P[i] - loc).normalized() if dist > 1e-5 else nrm
    if out.dot(nrm) < 0: out = nrm                               # a point inside the body goes back out along the skin's normal
    # sleeves get more room (the arm bends and twists most), and so does the torso round the armpits, where the
    # arm presses in against the side
    near_pit = min((P[i] - pit).length for pit in pits) < PIT_R
    gap = COLLAR_GAP if fam == "head" else ARM_GAP if fam in ("larm", "rarm") or near_pit else GAP
    D[i] = (loc + out * gap - P[i]) * f; F[i] = f
    BW[i] = body_weights(fam, loc, idx)

# smooth the pull (and its strength) over the surface, so the wrap blends into the loose skirt without kinks
adj = [[e.other_vert(v).index for e in v.link_edges] for v in bm.verts]
for _ in range(int(os.environ.get("VDW_WRAP_SMOOTH", "6"))):
    D = [D[i] * 0.5 + (sum((D[j] for j in adj[i]), Vector()) / len(adj[i])) * 0.5 if adj[i] else D[i] for i in range(n)]
    F = [F[i] * 0.5 + (sum(F[j] for j in adj[i]) / len(adj[i])) * 0.5 if adj[i] else F[i] for i in range(n)]
moved, pushed = 0, 0
for i, v in enumerate(bm.verts):
    if D[i].length < 1e-6: continue
    q = P[i] + D[i]
    loc, nrm, idx, dist = whole.find_nearest(q)
    if loc is not None:                                          # never closer than the gap (smoothing can pull a point in)
        inside = (q - loc).dot(nrm) < 0
        if inside or dist < GAP * 0.9:
            q = loc + nrm * GAP; pushed += 1
    v.co = CMi @ q; moved += 1
bm.to_mesh(coat.data); bm.free(); coat.data.update()

# weights: toward the body's where it hugs (by how much it's wrapped), the painted ones (and the skirt's) elsewhere
for i, cv in enumerate(coat.data.vertices):
    if BW[i] is None or F[i] <= 0.01: continue
    w = {cgroups[g.group]: g.weight * (1 - F[i]) for g in cv.groups}
    for k, x in BW[i].items(): w[k] = w.get(k, 0) + x * F[i]
    top = sorted(w.items(), key=lambda kv: -kv[1])[:4]; s = sum(x for _, x in top) or 1
    for g in list(cv.groups): coat.vertex_groups[g.group].remove([i])
    for k, x in top:
        (coat.vertex_groups.get(k) or coat.vertex_groups.new(name=k)).add([i], x / s, 'REPLACE')

# weight fixes (the painted weights had both):
#  - the collar follows the neck and chest, not the head: its Head/Jaw share goes to Spine2 (it stretched as the head turned)
#  - the coat's body never follows a thigh: UpLeg/Leg shares go to Hips (the back clung to each leg as it swung); the
#    skirt bones still swing it
def move_weight(i, cv, frm, to, share=1.0):
    if share <= 0.001: return False
    w = {cgroups[g.group]: g.weight for g in cv.groups}
    amt = 0.0
    for k in frm:
        if k in w: amt += w[k] * share; w[k] *= 1 - share
    w = {k: x for k, x in w.items() if x > 0.001}
    if amt <= 0.001: return False
    w[to] = w.get(to, 0) + amt
    for g in list(cv.groups): coat.vertex_groups[g.group].remove([i])
    for k, x in w.items():
        if x > 0.001: (coat.vertex_groups.get(k) or coat.vertex_groups.new(name=k)).add([i], x, 'REPLACE')
    return True
cgroups = {g.index: g.name for g in coat.vertex_groups}
collar = sum(move_weight(i, cv, ("Head", "Jaw"), "Spine2") for i, cv in enumerate(coat.data.vertices))
cgroups = {g.index: g.name for g in coat.vertex_groups}
# only the back: the front panels keep following the thighs (taken off them, a raised knee pushed out through the front
# when jumping). Blended across the sides by how far back the point is (the body's front is -y).
body_mid_y = (min(v.y for v in fv) + max(v.y for v in fv)) / 2
# the back keeps a light share (VDW_BACK_LEG_KEEP, default 30%): it still moves a little with the legs without
# clinging to them
BACK_KEEP = float(os.environ.get("VDW_BACK_LEG_KEEP", "0.3"))
def back_share(p): return (1 - BACK_KEEP) * smoothstep(body_mid_y - 0.03, body_mid_y + 0.05, p.y)
legs = sum(move_weight(i, cv, ("LeftUpLeg", "RightUpLeg", "LeftLeg", "RightLeg"), "Hips", back_share(CM @ cv.co))
           for i, cv in enumerate(coat.data.vertices))
# the hem follows the calves too (VDW_CALF_SHARE, default 40% at the hem, fading out by mid-thigh): the calf kicked
# back through the hem as you ran. Its side by which side of the body it's on (an even split at the middle).
CALF = float(os.environ.get("VDW_CALF_SHARE", "0.4"))
BACK_CALF = float(os.environ.get("VDW_BACK_CALF_SHARE", "0.7"))   # the back of the hem, where the calf kicks back into it
hem_z = min((CM @ v.co).z for v in coat.data.vertices)
knee_z = (arm.matrix_world @ arm.data.bones["LeftLeg"].head_local).z
calf_top = knee_z + 0.6 * (hips_z - knee_z)
calves = 0
cgroups = {g.index: g.name for g in coat.vertex_groups}
for i, cv in enumerate(coat.data.vertices):
    p = CM @ cv.co
    backness = smoothstep(body_mid_y - 0.03, body_mid_y + 0.05, p.y)
    s = (CALF + (BACK_CALF - CALF) * backness) * smoothstep(calf_top, hem_z, p.z)
    if s <= 0.005: continue
    w = {cgroups[g.group]: g.weight * (1 - s) for g in cv.groups}
    left = 1 - smoothstep(-0.04, 0.04, p.x)                      # the body's left is -x (+x carries the Right* weights)
    for side, part in (("LeftLeg", left), ("RightLeg", 1 - left)):
        if part > 0: w[side] = w.get(side, 0) + s * part
    top = sorted(w.items(), key=lambda kv: -kv[1])[:4]; tot = sum(x for _, x in top) or 1
    for g in list(cv.groups): coat.vertex_groups[g.group].remove([i])
    for k, x in top: (coat.vertex_groups.get(k) or coat.vertex_groups.new(name=k)).add([i], x / tot, 'REPLACE')
    calves += 1
print(f"WEIGHTS collar points off the head: {collar}; points off the thighs: {legs}; hem points on the calves: {calves} "
      f"(knee {knee_z:.2f} m, from {calf_top:.2f} m down)")

gaps = sorted(whole.find_nearest(CM @ v.co)[3] * 100 for v in coat.data.vertices if (CM @ v.co).z > TOP)
print(f"WRAPPED {moved} of {n} points ({pushed} pushed back out to the gap); above the waist the coat is now "
      f"{gaps[len(gaps) // 2]:.1f} cm off the skin (median), {gaps[0]:.1f}..{gaps[-1]:.1f} cm")
bpy.ops.wm.save_as_mainfile(filepath=SAVE, copy=True)
print("SAVED", SAVE)
