# Bakes a rigged fish's albedo from the full-detail source by NEAREST SURFACE POINT instead of ray casting: every texel
# of the fish's current UV layout is placed on the mesh (rest pose), the closest point on the source's surface is found,
# and the source texture is read at that point's UV. A ray bake looks along the face normal and on thin ridges or
# tangled scan spots can read the far side (pale belly colour on the back); nearest-point can't.
# Overwrites the albedo image the material uses (the pipeline's own map), saves the .blend (in place or VDW_SAVE_TO).
#   blender -b fish.blend --python nearest_bake.py
#   env: VDW_HI (prep_sourced_fish VDW_SAVE_HI .blend), VDW_PREP (prep .blend the rig was built from), VDW_SAVE_TO,
#        VDW_RES (working resolution, 1024; scaled up to the map's size), VDW_SRC_RES (source texture read at, 4096)
import bpy, os, math
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
RES = int(os.environ.get("VDW_RES", "1024")); SRC_RES = int(os.environ.get("VDW_SRC_RES", "4096"))
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
mesh = next(o for o in bpy.data.objects if o.type == 'MESH' and o.parent == arm)
arm.data.pose_position = 'REST'; bpy.context.view_layer.update()
def coords_of(path):
    with bpy.data.libraries.load(path) as (src, dst): dst.meshes = list(src.meshes)
    m = max(dst.meshes, key=lambda m: len(m.vertices)); a = np.array([v.co[:] for v in m.vertices])
    for x in dst.meshes: bpy.data.meshes.remove(x)
    return a
dg = bpy.context.evaluated_depsgraph_get(); ev = mesh.evaluated_get(dg); me = ev.to_mesh()
# VDW_LOCAL=1: work in the mesh's own coordinates (the user scaled the object without applying it - the source lines up
# with the mesh data, not the scaled object)
LOCAL = os.environ.get("VDW_LOCAL") == "1"
cur = np.array([(v.co if LOCAL else mesh.matrix_world @ v.co)[:] for v in me.vertices])
with bpy.data.libraries.load(os.environ["VDW_HI"]) as (src, dst): dst.objects = [n for n in src.objects if n == "hi_source"]
hi = dst.objects[0]; hm = hi.data
hm.calc_loop_triangles()
hraw = np.array([v.co[:] for v in hm.vertices])
if os.environ.get("VDW_PREP", "-") != "-":
    prep = coords_of(os.environ["VDW_PREP"])
    s = (cur[:, 1].max() - cur[:, 1].min()) / (prep[:, 1].max() - prep[:, 1].min()); off = cur.mean(0) - s * prep.mean(0)
else:   # no prep file: line the source's bounding box up with the mesh's (the prep was the source decimated, same box)
    s = (cur[:, 1].max() - cur[:, 1].min()) / (hraw[:, 1].max() - hraw[:, 1].min())
    off = (cur.min(0) + cur.max(0)) / 2 - s * (hraw.min(0) + hraw.max(0)) / 2
print(f"  lining the source up: scale {s:.4f}, offset {tuple(np.round(off, 4))}")
hco = hraw * s + off
huv = hm.uv_layers.active.data
tris = [(t.vertices[:], [huv[l].uv[:] for l in t.loops], t.material_index) for t in hm.loop_triangles]
bvh = BVHTree.FromPolygons([Vector(x) for x in hco], [t[0] for t in tris], all_triangles=True)
texs = {}
for i, m in enumerate(hm.materials):
    b = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None) if m and m.node_tree else None
    def up_to_image(sock, depth=0):      # the first image node feeding this socket (through mix / colour nodes)
        for l in sock.links:
            n = l.from_node
            if n.type == 'TEX_IMAGE' and n.image: return n
            if depth < 6:
                for s in n.inputs:
                    r = up_to_image(s, depth + 1)
                    if r: return r
        return None
    node = (up_to_image(b.inputs["Base Color"]) if b else None) or next((n for n in m.node_tree.nodes if n.type == 'TEX_IMAGE'), None)
    im = node.image.copy(); im.scale(SRC_RES, SRC_RES)
    a = np.empty(SRC_RES * SRC_RES * 4, np.float32); im.pixels.foreach_get(a); bpy.data.images.remove(im)
    a = a.reshape(SRC_RES, SRC_RES, 4)
    # the scan's atlas is black between its islands; points on an island's very edge (fin tips) read into that black.
    # Grow the islands' colour out over the black first.
    empty = a[..., :3].max(-1) < float(os.environ.get("VDW_SRC_EMPTY", "0.03"))
    # VDW_SRC_ALPHA_EMPTY: texels this see-through count as empty too (a texture's clear fin rims hold junk colour)
    if os.environ.get("VDW_SRC_ALPHA_EMPTY"): empty |= a[..., 3] < float(os.environ["VDW_SRC_ALPHA_EMPTY"])
    for _ in range(int(os.environ.get("VDW_SRC_GROW", "24"))):
        if not empty.any(): break
        acc = np.zeros((SRC_RES, SRC_RES, 3), np.float32); n = np.zeros((SRC_RES, SRC_RES), np.float32)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ok = ~np.roll(np.roll(empty, dy, 0), dx, 1)
            acc += np.roll(np.roll(a[..., :3], dy, 0), dx, 1) * ok[..., None]; n += ok
        f = empty & (n > 0); a[f, :3] = acc[f] / n[f, None]; empty &= ~f
    texs[i] = a
print(f"  source: {len(tris)} triangles, {len(texs)} texture(s) read at {SRC_RES}")
# ---- rasterise the fish's UV layout at RES: texel -> point on the mesh
uvl = me.uv_layers.active.data; me.calc_loop_triangles()
pos = np.zeros((RES, RES, 3), np.float32); cov = np.zeros((RES, RES), bool)
for t in me.loop_triangles:
    uv = np.array([uvl[l].uv[:] for l in t.loops]) * RES; P3 = cur[list(t.vertices)]
    x0, y0 = np.maximum(np.floor(uv.min(0)).astype(int) - 1, 0); x1, y1 = np.minimum(np.ceil(uv.max(0)).astype(int) + 1, RES - 1)
    if x1 < x0 or y1 < y0: continue
    xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
    (ax, ay), (bx, by), (cx, cy) = uv; den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
    if abs(den) < 1e-12: continue
    l1 = ((by - cy) * (xs - cx) + (cx - bx) * (ys - cy)) / den; l2 = ((cy - ay) * (xs - cx) + (ax - cx) * (ys - cy)) / den; l3 = 1 - l1 - l2
    ins = (l1 >= -0.01) & (l2 >= -0.01) & (l3 >= -0.01)
    if not ins.any(): continue
    yy, xx = (ys[ins] - 0.5).astype(int), (xs[ins] - 0.5).astype(int)
    pos[yy, xx] = l1[ins, None] * P3[0] + l2[ins, None] * P3[1] + l3[ins, None] * P3[2]; cov[yy, xx] = True
ev.to_mesh_clear()
print(f"  {int(cov.sum())} texels to fill")
# ---- nearest source point per texel, its UV, the colour there
col = np.zeros((RES, RES, 3), np.float32)
ys_, xs_ = np.nonzero(cov)
for y, x in zip(ys_, xs_):
    loc, nrm, ti, d = bvh.find_nearest(Vector(pos[y, x]))
    if ti is None: continue
    vi, uvs, mi = tris[ti]
    A, B, C = (Vector(hco[i]) for i in vi)
    v0, v1, v2 = B - A, C - A, loc - A
    d00, d01, d11, d20, d21 = v0.dot(v0), v0.dot(v1), v1.dot(v1), v2.dot(v0), v2.dot(v1)
    dn = d00 * d11 - d01 * d01
    if abs(dn) < 1e-20: w1 = w2 = 1 / 3
    else: w1 = (d11 * d20 - d01 * d21) / dn; w2 = (d00 * d21 - d01 * d20) / dn
    w0 = 1 - w1 - w2
    u = w0 * uvs[0][0] + w1 * uvs[1][0] + w2 * uvs[2][0]; v = w0 * uvs[0][1] + w1 * uvs[1][1] + w2 * uvs[2][1]
    tx = texs.get(mi, texs[0])
    col[y, x] = tx[int((v % 1) * (SRC_RES - 1)), int((u % 1) * (SRC_RES - 1)), :3]
# grow into the gaps round the islands so the edges don't show the background
for _ in range(12):
    grow = ~cov
    if not grow.any(): break
    acc = np.zeros_like(col); n = np.zeros((RES, RES))
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        sh = np.roll(np.roll(cov, dy, 0), dx, 1); acc += np.roll(np.roll(col, dy, 0), dx, 1) * sh[..., None]; n += sh
    new = grow & (n > 0); col[new] = acc[new] / n[new, None]; cov |= new
# ---- into the material's albedo, at its size
bs = next(n for n in mesh.data.materials[0].node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
alb = bs.inputs["Base Color"].links[0].from_node.image; W, H = alb.size
tmp = bpy.data.images.new("nb_tmp", RES, RES); a = np.ones((RES, RES, 4), np.float32); a[..., :3] = col
tmp.pixels.foreach_set(a.ravel()); tmp.scale(W, H)
b = np.empty(W * H * 4, np.float32); tmp.pixels.foreach_get(b); bpy.data.images.remove(tmp)
alb.pixels.foreach_set(b); alb.save(); print("  saved", bpy.path.abspath(alb.filepath))
bpy.data.objects.remove(hi) if hi.name in bpy.data.objects else None
arm.data.pose_position = 'POSE'
bpy.ops.wm.save_as_mainfile(filepath=os.environ.get("VDW_SAVE_TO") or bpy.data.filepath); print("  saved blend")
