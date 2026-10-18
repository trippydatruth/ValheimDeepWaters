# Gives a hammerhead shark Mjolnir's head as ONE seamless mesh: the shark's head is cut off at the neck, the neck runs
# on as a thick round handle, and the handle grows straight into a hole in the back of a bevelled, flared hammer
# block - every join is real shared edges, no separate parts. Domed eyes sit on the hammer's two end faces.
# Works on the unrigged prep mesh (head toward -Y, top +Z, length along Y) and saves to VDW_SAVE_TO. New faces get the
# UV of a plain spot of the old texture (recolor_fish repaints the head, grip and eyes by position afterwards).
#   blender -b prep.blend --python mjolnir_head.py
#   env: VDW_SAVE_TO, VDW_HEAD (share of the length from the nose the hammer covers, 0.13), VDW_CUT (where the neck is
#        cut, 0.18), VDW_BLOCK "length,depth,height" as shares of the length (0.30,0.10,0.11),
#        VDW_HANDLE (handle radius as a share of the block's height, 0.62), VDW_PREVIEW (png prefix)
import bpy, bmesh, math, os
import numpy as np
from mathutils import Vector
SAVE_TO = os.environ["VDW_SAVE_TO"]
HEAD = float(os.environ.get("VDW_HEAD", "0.13")); CUT = float(os.environ.get("VDW_CUT", "0.20"))
BL, BD, BH = (float(x) for x in os.environ.get("VDW_BLOCK", "0.34,0.10,0.11").split(","))
HANDLE = float(os.environ.get("VDW_HANDLE", "0.62"))
def sm(e0, e1, x): q = min(max((x - e0) / (e1 - e0), 0.0), 1.0); return q * q * (3 - 2 * q)
mesh = max((o for o in bpy.data.objects if o.type == 'MESH'), key=lambda o: len(o.data.vertices))
me = mesh.data
co = np.array([v.co[:] for v in me.vertices]); ylo, yhi = co[:, 1].min(), co[:, 1].max(); L = yhi - ylo
y_cut = ylo + CUT * L
bm = bmesh.new(); bm.from_mesh(me); uvl = bm.loops.layers.uv.active
target = Vector((0, ylo + 0.4 * L, float(np.percentile(co[:, 2], 80))))
spot = min(bm.faces, key=lambda f: (f.calc_center_median() - target).length).loops[0][uvl].uv.copy()
mat_i = 0

# ---- 1. cut the head off at the neck
# sliced on a plane (deleting whole faces left long low-poly triangles reaching forward as flaps beside the handle)
nf0 = len(bm.faces)
bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces), dist=1e-6,
                       plane_co=(0, y_cut, 0), plane_no=(0, 1, 0), clear_inner=True)
gone = [None] * max(0, nf0 - len(bm.faces))
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
bnd = [e for e in bm.edges if len(e.link_faces) == 1]
loops, seen = [], set()
for e in bnd:                                   # group boundary edges into loops
    if e in seen: continue
    grp, st = [], [e]; seen.add(e)
    while st:
        x = st.pop(); grp.append(x)
        for v in x.verts:
            for e2 in v.link_edges:
                if e2 not in seen and len(e2.link_faces) == 1: seen.add(e2); st.append(e2)
    loops.append(grp)
neck_edges = max(loops, key=lambda g: sum(e.calc_length() for e in g) - 50 * abs(np.mean([v.co.y for e in g for v in e.verts]) - y_cut))
neck = list({v for e in neck_edges for v in e.verts})
nc = Vector(np.mean([v.co[:] for v in neck], 0).tolist())
def ang(p, c): return math.atan2(p.z - c.z, p.x - c.x)
neck.sort(key=lambda v: ang(v.co, nc))
nr = np.array([math.hypot(v.co.x - nc.x, v.co.z - nc.z) for v in neck]); na = np.array([ang(v.co, nc) for v in neck])
print(f"  cut at {CUT:.2f} of the length: {len(gone)} head faces off, neck loop {len(neck)} points, half width {nr.max():.3f} m")

# ---- 2. the hammer block (its own grid, flared ends, bevelled), in front of the neck
hl, hd, hh = BL * L / 2, BD * L / 2, BH * L / 2
yc = ylo + hd * 0.8; zc = nc.z
# built in its own bmesh (bmesh ops on the shark's bmesh dropped the shark), then appended into the shark's
b2 = bmesh.new(); bmesh.ops.create_cube(b2, size=2.0)
bmesh.ops.subdivide_edges(b2, edges=list(b2.edges), cuts=20, use_grid_fill=True)
# round the box (a superellipsoid: every point pushed onto |x|^n + |y|^n + |z|^n = 1) - clean, even rounded corners;
# bevels on the fine grid overlapped and streaked
RN = float(os.environ.get("VDW_ROUND", "7"))
for v in b2.verts:
    p = v.co; s = (abs(p.x) ** RN + abs(p.y) ** RN + abs(p.z) ** RN) ** (1.0 / RN); v.co = p / s
# half way between a hammerhead's cephalofoil and Mjolnir: thinner through the span, rounded front edge, the span
# swept back toward the ends like the shark's "wings", but Mjolnir's flared, flat-faced ends (where the eyes are)
SWEEP = float(os.environ.get("VDW_SWEEP", "0.55")); BULGE = float(os.environ.get("VDW_BULGE", "0.35"))
for v in b2.verts:
    x0, y0, z0 = v.co; a = abs(x0)
    flare = max(0.0, (a - 0.72) / 0.28) ** 2
    fz = 1.0 - 0.22 * sm(0.2, 0.7, a) + 0.32 * flare
    fy = 1.0 + 0.15 * flare
    y = y0 * hd * fy
    if y0 < 0: y += y0 * BULGE * hd * (1 - a * a)                          # the front edge bows forward in the middle
    y += SWEEP * hd * max(0.0, (a - 0.3) / 0.7) ** 2                        # ends swept back (the back's middle stays flat)
    v.co = Vector((x0 * hl, yc + y, zc + z0 * hh * fz))
bmesh.ops.recalc_face_normals(b2, faces=b2.faces); b2.normal_update()
# the mouth: a crescent groove under the front of the hammer, curving back toward the ends, like a hammerhead's
MW, MD = 0.18 * hd, 0.16 * hh; n_mouth = 0
for v in b2.verts:
    if not v.link_faces or np.mean([f.normal.z for f in v.link_faces]) > -0.75: continue
    xx, yy = v.co.x, v.co.y - yc
    if abs(xx) > 0.45 * hl: continue
    ym = hd * (-0.35 + 0.55 * (xx / (0.45 * hl)) ** 2)
    d = abs(yy - ym)
    if d < MW: v.co.z += MD * (1 - (d / MW) ** 2) * sm(0.45 * hl, 0.35 * hl, abs(xx)); n_mouth += 1
print(f"  mouth groove: {n_mouth} points raised into the underside")
tmp = bpy.data.meshes.new("block"); b2.to_mesh(tmp); b2.free()
# keep the shark's vertices by position (bm.from_mesh appends, but element references go stale)
neck_co = [v.co.copy() for v in neck]
bm.to_mesh(me); bm.free()
bm = bmesh.new(); bm.from_mesh(me); n0 = len(bm.verts); f0 = len(bm.faces)
bm.from_mesh(tmp); bpy.data.meshes.remove(tmp)
bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table(); uvl = bm.loops.layers.uv.active
from mathutils.kdtree import KDTree
kd = KDTree(n0)
for i in range(n0): kd.insert(bm.verts[i].co, i)
kd.balance()
neck = [bm.verts[kd.find(c)[1]] for c in neck_co]
bv = {bm.verts[i] for i in range(n0, len(bm.verts))}
bf = [bm.faces[i] for i in range(f0, len(bm.faces))]
bm.normal_update()
# the neck's opening in the back of the hammer: an oval as wide as the flaring neck and as tall as the back's flat
# part allows, so the neck grows into the hammer instead of narrowing into a handle
back_y = max(v.co.y for v in bv if abs(v.co.x) < hl * 0.2 and abs(v.co.z - zc) < hh * 0.5)
backf = [f for f in bf if f.normal.y > 0.9 and abs(f.calc_center_median().x) < hl * 0.15]
z_flat = max(abs(f.calc_center_median().z - zc) for f in backf) if backf else hh * 0.6
nz_h = max(abs(v.co.z - nc.z) for v in neck)
ax_h = min(nr.max() * 1.35, 0.42 * hl); az_h = min(nz_h, z_flat * 0.9)
hole = [f for f in bf if f.normal.y > 0.8
        and (f.calc_center_median().x / ax_h) ** 2 + ((f.calc_center_median().z - zc) / az_h) ** 2 < 1.0]
hc = Vector((0, back_y, zc))
bmesh.ops.delete(bm, geom=hole, context='FACES_ONLY')
hole_v = sorted({v for v in bv if v.is_valid and any(len(e.link_faces) == 1 for e in v.link_edges)},
                key=lambda v: ang(v.co, hc))
# the opening's edge follows the grid in steps; spread its points evenly round a true oval (keeping their order)
for i, v in enumerate(hole_v):
    a_ = ang(hole_v[0].co, hc) + 2 * math.pi * i / len(hole_v)
    v.co.x, v.co.z = hc.x + ax_h * math.cos(a_), hc.z + az_h * math.sin(a_)
rh = max(ax_h, az_h)
print(f"  hammer head {2 * hl:.2f} x {2 * hd:.2f} x {2 * hh:.2f} m, neck opening {len(hole_v)} points, {2 * ax_h:.2f} x {2 * az_h:.2f} m (neck {2 * nr.max():.2f} wide, {2 * nz_h:.2f} tall)")
# domed eyes in the middle of each end face
re_ = 0.45 * min(hd, hh); n_eye = 0
for v in bv:
    if not v.is_valid or abs(abs(v.co.x) - hl) > 1e-4: continue
    d = math.hypot(v.co.y - (yc + SWEEP * hd), v.co.z - zc)     # the end faces sit swept back
    if d < re_: v.co.x += math.copysign(0.55 * re_ * (1 - (d / re_) ** 2), v.co.x); n_eye += 1

# ---- 3. the handle: rings from the neck's shape to the round hole, bridged at both ends
K = len(hole_v); ha = np.array([ang(v.co, hc) for v in hole_v]); hr = np.array([math.hypot(v.co.x, v.co.z - zc) for v in hole_v])
def neck_r(a):                                    # the neck's radius at an angle (periodic interpolation)
    o = np.argsort(na); aa, rr = na[o], nr[o]
    f_ = lambda q: float(np.interp(q, np.concatenate([aa - 2 * math.pi, aa, aa + 2 * math.pi]), np.concatenate([rr, rr, rr])))
    return float(np.mean([f_(a + d_) for d_ in np.linspace(-0.45, 0.45, 9)]))      # smoothed: the neck's ridges don't run on
rings = []
for s in (0.1, 0.22, 0.36, 0.5, 0.64, 0.78, 0.9):
    y = y_cut + (back_y - y_cut) * s; c = Vector((nc.x * (1 - s), y, nc.z * (1 - s) + zc * s))
    k = s ** 1.7; bulge = 1.0                     # keeps the neck's shape, then flares into the hammer near the end
    ring = []
    for a, r_end in zip(ha, hr):
        r = (neck_r(a) * (1 - k) + r_end * k) * bulge
        ring.append(bm.verts.new((c.x + r * math.cos(a), y, c.z + r * math.sin(a))))
    rings.append(ring)
rings.append(hole_v)
new_faces = []
for r0, r1_ in zip(rings, rings[1:]):
    for i in range(K):
        new_faces.append(bm.faces.new((r0[i], r0[(i + 1) % K], r1_[(i + 1) % K], r1_[i])))
# neck loop (M points) to the first ring (K points): a ribbon of triangles, advancing whichever side is behind
A, B = neck, rings[0]; M = len(A)
aA = [ang(v.co, nc) for v in A]; aB = list(ha)
iA = int(np.argmin(aA)); iB = int(np.argmin(aB)); i = j = 0
def un(x, base): return x if x >= base else x + 2 * math.pi
baseA, baseB = aA[iA], aB[iB]
while i < M or j < K:
    a_cur, a_nxt = A[(iA + i) % M], A[(iA + i + 1) % M]; b_cur, b_nxt = B[(iB + j) % K], B[(iB + j + 1) % K]
    na_ = un(aA[(iA + i + 1) % M], baseA) if i < M - 1 else baseA + 2 * math.pi
    nb_ = un(aB[(iB + j + 1) % K], baseB) if j < K - 1 else baseB + 2 * math.pi
    if j >= K or (i < M and na_ <= nb_):
        new_faces.append(bm.faces.new((a_cur, a_nxt, b_cur))); i += 1
    else:
        new_faces.append(bm.faces.new((a_cur, b_nxt, b_cur))); j += 1
bm.normal_update()
for f in new_faces + bf:      # a small real patch of UV round the plain spot (one shared UV point left the baked
    if f.is_valid:            # normal map with no tangent there: dark blotches)
        f.material_index = mat_i
        n = f.normal; ax = max(range(3), key=lambda i: abs(n[i]))
        a1, a2 = [i for i in range(3) if i != ax]
        for l in f.loops: l[uvl].uv = (spot.x + l.vert.co[a1] * 0.0015, spot.y + l.vert.co[a2] * 0.0015)   # tiny: stays on plain skin
# soften both joins into fillets: the neck flaring into the hammer's back, and the cut neck into the first ring
near_back = [v for v in bv if v.is_valid and abs(v.co.y - back_y) < 0.35 * hd
             and (v.co.x / (ax_h * 1.6)) ** 2 + ((v.co.z - zc) / (az_h * 1.8)) ** 2 < 1.0]
join_back = list(set(near_back) | set(hole_v) | set(rings[-2]) | set(rings[-3]))
join_neck = list(set(neck) | set(rings[0]) | set(rings[1]))
for _ in range(int(os.environ.get("VDW_FILLET", "8"))):
    bmesh.ops.smooth_vert(bm, verts=join_back, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bmesh.ops.smooth_vert(bm, verts=join_neck, factor=0.4, use_axis_x=True, use_axis_y=True, use_axis_z=True)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
open_e = sum(1 for e in bm.edges if len(e.link_faces) == 1); nonman = sum(1 for e in bm.edges if len(e.link_faces) > 2)
bm.to_mesh(me); bm.free(); me.update()
for p in me.polygons: p.use_smooth = True
c2 = np.array([v.co[:] for v in me.vertices]); lo2, hi2 = c2.min(0), c2.max(0); L2 = hi2[1] - lo2[1]
print(f"  handle {len(new_faces)} faces; eye domes {n_eye} points; open edges {open_e}, non-manifold {nonman}")
print(f"  share of the new length: hammer ends at {(back_y - lo2[1]) / L2:.3f}, handle ends at {(y_cut - lo2[1]) / L2:.3f}")
# where the hammer is, as shares of the length from the nose (survives rig_fish's rescale), for recolor_fish's mouth
# and engravings: centre, half depth, half length, half height, sweep, mouth curve (back share, curve, half width)
mesh["vdw_hammer"] = [(yc - lo2[1]) / L2, hd / L2, hl / L2, hh / L2, SWEEP, -0.35, 0.55, 0.45]
# every face's normal outward (the user found inward-facing faces on the neck blend: they shaded dark)
for o in bpy.context.view_layer.objects: o.select_set(o == mesh)
bpy.context.view_layer.objects.active = mesh
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.normals_make_consistent(inside=False); bpy.ops.object.mode_set(mode='OBJECT')
print("  normals recalculated outward")
bpy.ops.wm.save_as_mainfile(filepath=SAVE_TO); print("  saved", SAVE_TO)

P = os.environ.get("VDW_PREVIEW")
if P:
    sc = bpy.context.scene; sc.render.engine = 'BLENDER_WORKBENCH'; sc.render.use_border = False
    sh = sc.display.shading; sh.light = 'STUDIO'; sh.color_type = 'MATERIAL'; sh.show_backface_culling = True
    sc.render.resolution_x, sc.render.resolution_y = 1000, 600
    cd = bpy.data.cameras.new("C"); cd.type = 'ORTHO'; cd.ortho_scale = L * 0.5; cam = bpy.data.objects.new("C", cd); sc.collection.objects.link(cam); sc.camera = cam
    ctr = Vector((0, ylo + L * 0.13, zc))
    for nm, d in (("q", (0.7, -0.5, 0.45)), ("side", (1, 0, 0.05)), ("top", (0, 0.05, 1)), ("end", (1, -0.3, 0.1))):
        cam.location = ctr + Vector(d).normalized() * L * 3; cam.rotation_euler = (ctr - cam.location).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = f"{P}_{nm}.png"; bpy.ops.render.render(write_still=True)
