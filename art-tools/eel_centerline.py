# Finds the centre line of a coiled eel mesh: the two ends of the body by distance measured along the surface,
# then slices along that surface distance from the tail; each slice's middle is a centre-line point.
# Reports both ends, the length, and renders the line (red) through the see-through mesh.
import bpy, bmesh, os, math, heapq
import numpy as np
from mathutils import Vector

OUT = os.environ["VDW_OUT"]
mesh = next(o for o in bpy.data.objects if o.type == 'MESH')
bm = bmesh.new(); bm.from_mesh(mesh.data); bm.verts.ensure_lookup_table()
co = np.array([mesh.matrix_world @ v.co for v in bm.verts])
n = len(co)
adj = [[] for _ in range(n)]
for e in bm.edges:
    a, b = e.verts[0].index, e.verts[1].index; d = float(np.linalg.norm(co[a] - co[b]))
    adj[a].append((b, d)); adj[b].append((a, d))
def dijkstra(src):
    dist = np.full(n, np.inf); dist[src] = 0; h = [(0.0, src)]
    while h:
        d, u = heapq.heappop(h)
        if d > dist[u]: continue
        for w, l in adj[u]:
            nd = d + l
            if nd < dist[w]: dist[w] = nd; heapq.heappush(h, (nd, w))
    return dist
# connected pieces
comp = np.full(n, -1); c = 0
for i in range(n):
    if comp[i] >= 0: continue
    st = [i]; comp[i] = c
    while st:
        u = st.pop()
        for w, _ in adj[u]:
            if comp[w] < 0: comp[w] = c; st.append(w)
    c += 1
sizes = np.bincount(comp); main = int(np.argmax(sizes))
print(f"\n===== CL =====\n  {n} verts, {c} connected pieces, main piece {sizes[main]} verts")
start = int(np.nonzero(comp == main)[0][0])
d0 = dijkstra(start); d0[comp != main] = -1
a = int(np.argmax(d0)); da = dijkstra(a); da[comp != main] = -1
b = int(np.argmax(da)); db = dijkstra(b)
print(f"  end A v{a} at {co[a].round(2)}   end B v{b} at {co[b].round(2)}   surface distance {da[b]:.2f}")
np.save(os.environ["VDW_OUT"] + "_ends.npy", np.array([a, b]))
# centre line from end A
nb = 60; L = da[b]
pts = []
for k in range(nb):
    lo_, hi_ = L * k / nb, L * (k + 1) / nb
    sel = (comp == main) & (da >= lo_) & (da < hi_)
    if sel.sum() < 3: continue
    pts.append(np.median(co[sel], axis=0))
pts = np.array(pts)
# refine: smooth the line, resample evenly, re-slice the body square to the line (nearest point), repeat
def smooth(p, r=3):
    w = np.exp(-0.5 * (np.arange(-r, r + 1) / (r / 2)) ** 2); w /= w.sum()
    pad = np.vstack([p[:1].repeat(r, 0), p, p[-1:].repeat(r, 0)])
    out = np.array([np.convolve(pad[:, i], w, mode="valid") for i in range(3)]).T
    out[0], out[-1] = p[0], p[-1]
    return out
def resample(p, m):
    s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))])
    t = np.linspace(0, s[-1], m)
    return np.array([np.interp(t, s, p[:, i]) for i in range(3)]).T
body = co[comp == main]
for it in range(4):
    pts = resample(smooth(pts, 3), 48)
    d = np.linalg.norm(body[:, None, :] - pts[None, :, :], axis=2); near = d.argmin(1)
    new = []
    for k in range(len(pts)):
        sel = body[near == k]
        new.append(sel.mean(0) if len(sel) >= 3 else pts[k])
    new = np.array(new); new[0] = 0.5 * (new[0] + co[a]); new[-1] = co[b]   # keep the line running to the very tips
    pts = new
pts = resample(smooth(pts, 2), 48)
seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
print(f"  centre line: {len(pts)} points, length {seg.sum():.2f} (model units)")
for k in range(0, len(pts), 6): print(f"    {k:2d}: {pts[k].round(2)}")
np.save(os.environ["VDW_OUT"] + "_line.npy", pts)
# render
cu = bpy.data.curves.new("CL", 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 0.03
sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
for i, p in enumerate(pts): sp.points[i].co = (*p, 1)
ob = bpy.data.objects.new("CL", cu); bpy.context.scene.collection.objects.link(ob)
m = bpy.data.materials.new("red"); m.diffuse_color = (1, 0, 0, 1); cu.materials.append(m)
for idx, col in ((a, (0, 1, 0, 1)), (b, (0, 0.4, 1, 1))):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.08, location=co[idx]); s = bpy.context.object
    mm = bpy.data.materials.new("m"); mm.diffuse_color = col; s.data.materials.append(mm)
sc = bpy.context.scene; sc.render.engine = 'BLENDER_WORKBENCH'; sc.display.shading.light = 'STUDIO'
sc.display.shading.color_type = 'MATERIAL'; sc.display.shading.show_xray = True; sc.display.shading.xray_alpha = 0.35
sc.render.resolution_x, sc.render.resolution_y = 700, 600
ctr = Vector(((co.min(0) + co.max(0)) / 2).tolist()); size = float((co.max(0) - co.min(0)).max())
cd = bpy.data.cameras.new("C"); cd.type = 'ORTHO'; cd.ortho_scale = size * 1.7
cam = bpy.data.objects.new("C", cd); sc.collection.objects.link(cam); sc.camera = cam
for view, d in (("top", (0, 0, 1)), ("side", (1, 0, 0)), ("front", (0, -1, 0)), ("q", (1, -1, 0.8))):
    cam.location = ctr + Vector(d).normalized() * size * 3
    cam.rotation_euler = (ctr - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = f"{OUT}_{view}.png"; bpy.ops.render.render(write_still=True)
print("===== END =====")

