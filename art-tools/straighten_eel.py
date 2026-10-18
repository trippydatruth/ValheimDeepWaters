# Straightens a coiled eel mesh: lays its centre line out along Y (head toward -Y), keeps the belly down, and
# scales it to VDW_LENGTH metres nose to tail.
#   body (largest connected piece): each vertex keeps its distance along the centre line and its sideways/up
#     offset from it; "up" along the body is the direction away from the cream belly (found from the texture)
#   other pieces (head, pincers, gills, hairs, spikes): each moves as one solid piece with the spot of the body
#     it is attached to (VDW_HEAD_RIGID: the first fraction of the body is treated as solid with the head)
#   env: VDW_LINE (centre line .npy, head first), VDW_LENGTH, VDW_SAVE_TO, VDW_RENDER (png prefix)
import bpy, bmesh, os, math
import numpy as np
from mathutils import Vector

LINE = np.load(os.environ["VDW_LINE"]); LEN = float(os.environ.get("VDW_LENGTH", "4.0"))
HEAD_RIGID = float(os.environ.get("VDW_HEAD_RIGID", "0.0"))
mesh = next(o for o in bpy.data.objects if o.type == 'MESH')
for o in bpy.context.view_layer.objects: o.select_set(False)
mesh.select_set(True); bpy.context.view_layer.objects.active = mesh
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
me = mesh.data
co = np.array([v.co[:] for v in me.vertices]); n = len(co)

# pieces
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

# centre line, arc length
P = LINE.copy(); seg = np.linalg.norm(np.diff(P, axis=0), axis=1); S = np.concatenate([[0], np.cumsum(seg)]); Ltot = S[-1]
T = np.gradient(P, axis=0); T /= np.linalg.norm(T, axis=1, keepdims=True)

# belly direction from the texture: cream = bright and unsaturated
mat = mesh.material_slots[0].material; bsdf = next(nn for nn in mat.node_tree.nodes if nn.type == 'BSDF_PRINCIPLED')
img = next(l.from_node.image for l in mat.node_tree.links if l.to_node == bsdf and l.to_socket.name == "Base Color")
W, H = img.size; px = np.empty(W * H * 4, dtype=np.float32); img.pixels.foreach_get(px); px = px.reshape(H, W, 4)
uvl = me.uv_layers.active.data
vcol = np.zeros((n, 3)); cnt = np.zeros(n)
for poly in me.polygons:
    for li in poly.loop_indices:
        u, v = uvl[li].uv; vi = me.loops[li].vertex_index
        vcol[vi] += px[min(H - 1, int(v * H)), min(W - 1, int(u * W)), :3]; cnt[vi] += 1
vcol /= np.maximum(cnt, 1)[:, None]
mx = vcol.max(1); mn = vcol.min(1); sat = (mx - mn) / (mx + 1e-6)
belly = (mx > 0.55) & (sat < 0.3) & (comp == main)
print(f"\n===== STRAIGHTEN =====\n  belly-coloured body vertices: {belly.sum()} of {(comp == main).sum()}")

# nearest point on the centre line (projection onto segments) -> s, foot point
def project(p):
    a = P[:-1]; ab = P[1:] - a
    t = np.clip(np.einsum('ij,ij->i', p - a, ab) / np.einsum('ij,ij->i', ab, ab), 0, 1)
    foot = a + ab * t[:, None]; d = np.linalg.norm(foot - p, axis=1); k = int(np.argmin(d))
    return S[k] + t[k] * seg[k], foot[k], d[k]
def interp(arr, s):
    return np.array([np.interp(s, S, arr[:, i]) for i in range(arr.shape[1])])

proj = [project(co[i]) for i in range(n)]
s_of = np.array([p[0] for p in proj]); foot = np.array([p[1] for p in proj]); dist = np.array([p[2] for p in proj])

# up vectors along the line: away from the belly, smoothed
K = len(P); up = np.zeros((K, 3)); have = np.zeros(K, bool)
for k in range(K):
    sel = belly & (np.abs(s_of - S[k]) < 0.6 * Ltot / K + 1e-6)
    if sel.sum() >= 2:
        off = co[sel] - foot[sel]; off -= np.outer(off @ T[k], T[k])
        dvec = -off.mean(0)
        if np.linalg.norm(dvec) > 1e-6: up[k] = dvec / np.linalg.norm(dvec); have[k] = True
print(f"  up direction found from the belly at {have.sum()} of {K} line points")
# VDW_PLANAR_UP=1: the body curls in its own side plane (x = 0): "up" is the in-plane perpendicular of the line on the
# back's side (the side the start of the line has +Z on) - the belly colour can be misleading on painted creatures
if os.environ.get("VDW_PLANAR_UP") == "1":
    ex = np.array([1.0, 0.0, 0.0])
    up = np.cross(T, ex); up /= np.maximum(np.linalg.norm(up, axis=1, keepdims=True), 1e-9)
    if up[0][2] < 0: up = -up
    have[:] = True; print("  up: in the side plane, toward the back")
# No belly to go by (a one-colour creature like a worm): "up" is the normal of the plane it's curled in.
if have.sum() < 3:
    _, _, vt = np.linalg.svd(P - P.mean(0), full_matrices=False)
    nrm_ = vt[2] if vt[2][2] >= 0 else -vt[2]
    up = np.tile(nrm_, (K, 1)); have[:] = True
    print(f"  no belly colour: up = the curl's plane normal {tuple(nrm_.round(3))}")
# fill gaps by carrying the nearest known up along the line (parallel transport), then smooth
if not have.any(): up[0] = np.array([0, 0, 1.0]); have[0] = True
first = int(np.argmax(have))
for k in range(first - 1, -1, -1): up[k] = up[k + 1]
for k in range(first + 1, K):
    if not have[k]: up[k] = up[k - 1]
for _ in range(6):
    up = np.array([up[max(0, k - 1)] + 2 * up[k] + up[min(K - 1, k + 1)] for k in range(K)])
    up -= (np.einsum('ij,ij->i', up, T))[:, None] * T; up /= np.linalg.norm(up, axis=1, keepdims=True)
side = np.cross(T, up)

def frame(s):
    t = interp(T, s); t /= np.linalg.norm(t); u = interp(up, s); u -= (u @ t) * t; u /= np.linalg.norm(u)
    return interp(P, s), t, u, np.cross(t, u)
def to_straight(p, s):   # p in original space, mapped with the frame at s
    o, t, u, sd = frame(s)
    d = p - o
    return np.array([d @ sd, -Ltot / 2 + s + d @ t, d @ u])

new = np.zeros_like(co)
s_head = HEAD_RIGID * Ltot
for i in np.nonzero(comp == main)[0]:
    s = s_of[i]
    new[i] = to_straight(co[i], max(s, s_head) if s < s_head else s) if s >= s_head else to_straight(co[i], s_head)
# separate pieces: solid, with the body spot they're nearest to
pieces = [k for k in range(c) if k != main]
body_idx = np.nonzero(comp == main)[0]
for k in pieces:
    idx = np.nonzero(comp == k)[0]
    # anchor: the piece's vertex closest to the body surface, then that body spot's line position
    dmin = np.inf; anchor_s = 0.0
    for i in idx:
        d = np.linalg.norm(co[body_idx] - co[i], axis=1); j = int(np.argmin(d))
        if d[j] < dmin: dmin = d[j]; anchor_s = s_of[body_idx[j]]
    anchor_s = max(anchor_s, s_head) if anchor_s < s_head else anchor_s
    for i in idx: new[i] = to_straight(co[i], anchor_s)
    cc = co[idx].mean(0)
    print(f"  piece {k:2d}: {len(idx):4d} verts, centre {cc.round(2)}, touches body at {anchor_s / Ltot:.2f} of the length (gap {dmin:.3f})")

# scale to length, centre
lo, hi = new.min(0), new.max(0); s_ = LEN / (hi[1] - lo[1])
new = (new - np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, 0])) * s_
zc = float(np.median(new[comp == main][:, 2])); new[:, 2] -= zc
# VDW_FLATTEN=1: take out the leftover gentle waves (the centre line from the coil isn't perfectly centred): measure
# the middle of the body every few cm along it, smooth that, and shift each cross-section back onto the straight line.
# Everything in front of the neck (head and its pieces) moves together with the neck, so the head isn't bent.
if os.environ.get("VDW_FLATTEN") == "1":
    # only the solid tube of the body counts: spikes, fins and other thin bits are left out of the measurement
    from mathutils.bvhtree import BVHTree
    for i, v in enumerate(bm.verts): v.co = Vector(new[i])
    bm.normal_update(); bvh = BVHTree.FromBMesh(bm); thin_lim = 0.035 * (new[:, 1].ptp()) / 2
    tube = np.zeros(n, dtype=bool)
    for fc in bm.faces:
        nn = fc.normal
        if nn.length < 0.5: continue
        loc, hn, _i, dd = bvh.ray_cast(fc.calc_center_median() - nn * 1e-4, -nn)
        if loc is not None and hn.dot(nn) <= 0 and dd >= thin_lim:
            for v in fc.verts: tube[v.index] = True
    tube &= (comp == main)
    print(f"  body-tube vertices used for the measurement: {tube.sum()} of {(comp == main).sum()}")
    bodyn = new[tube]; ylo, yhi = new[comp == main][:, 1].min(), new[comp == main][:, 1].max()
    neck = ylo + float(os.environ.get("VDW_NECK", "0.125")) * (yhi - ylo)
    grid = np.linspace(neck, yhi, 80); win = (yhi - ylo) * 0.03
    mx_, mz_ = [], []
    for g in grid:
        sl = bodyn[np.abs(bodyn[:, 1] - g) < win]
        if len(sl) < 4: sl = bodyn[np.argsort(np.abs(bodyn[:, 1] - g))[:6]]
        # middle = halfway between the 10th and 90th percentile (spikes and fins barely move it)
        mx_.append((sl[:, 0].min() + sl[:, 0].max()) / 2)
        mz_.append((sl[:, 2].min() + sl[:, 2].max()) / 2)
    def sm(a, r=3):
        a = np.array(a); w = np.exp(-0.5 * (np.arange(-r, r + 1) / (r / 2)) ** 2); w /= w.sum()
        return np.convolve(np.pad(a, r, mode='edge'), w, mode='valid')
    mx_, mz_ = sm(mx_), sm(mz_)
    before = float(np.ptp(mz_)), float(np.ptp(mx_))
    for i in range(n):
        y = new[i, 1] if comp[i] == main else min(new[comp == comp[i]][:, 1].max(), neck)
        y = max(y, neck) if comp[i] == main else neck if y <= neck else y
        new[i, 0] -= np.interp(y, grid, mx_) - mx_[0]
        new[i, 2] -= np.interp(y, grid, mz_) - mz_[0]
    print(f"  flattened: up/down wave {before[0] * 100:.1f} cm and side wave {before[1] * 100:.1f} cm taken out")
    zc = float(np.median(new[comp == main][:, 2])); new[:, 2] -= zc
for i, v in enumerate(me.vertices): v.co = new[i]
me.update()
lo, hi = new.min(0), new.max(0)
print(f"  straightened: size {tuple((hi - lo).round(2))} (x, y, z), scale x{s_:.4f}")

SAVE = os.environ.get("VDW_SAVE_TO")
if SAVE: bpy.ops.wm.save_as_mainfile(filepath=SAVE); print("  saved", SAVE)
R = os.environ.get("VDW_RENDER")
if R:
    sc = bpy.context.scene; sc.render.use_border = False; sc.render.resolution_percentage = 100; sc.render.engine = 'BLENDER_WORKBENCH'; sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'TEXTURE'
    sc.render.resolution_x, sc.render.resolution_y = 1000, 450
    cd = bpy.data.cameras.new("C"); cd.type = 'ORTHO'; cd.ortho_scale = LEN * 1.1
    cam = bpy.data.objects.new("C", cd); sc.collection.objects.link(cam); sc.camera = cam
    r90 = math.radians(90)
    for view, loc, rot in (("side", (10, 0, 0), (r90, 0, r90)), ("top", (0, 0, 10), (0, 0, r90)), ("below", (0, 0, -10), (math.radians(180), 0, r90))):
        cam.location = loc; cam.rotation_euler = rot
        sc.render.filepath = f"{R}_{view}.png"; bpy.ops.render.render(write_still=True)
    cd.ortho_scale = LEN * 0.45
    for view, d in (("head_q", Vector((0.8, -1, 0.5))), ("head_front", Vector((0, -1, 0.15)))):
        tgt = Vector((0, -LEN / 2 + LEN * 0.12, 0))
        cam.location = tgt + d.normalized() * 10; cam.rotation_euler = (tgt - cam.location).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = f"{R}_{view}.png"; bpy.ops.render.render(write_still=True)
print("===== END =====")


