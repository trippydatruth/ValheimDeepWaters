# Clears a painted-on gear texture (bake_shirt_paint.py output) from whole UV islands of the game body, e.g. the arms
# for the overalls: the bake's rays from the inner upper arm reach the overalls' side panel and painted yellow there.
# The islands are picked by a UV point inside them; the cleared area takes in the padding round the island's edge
# (the bake's margin) up to where another island is nearer. Colour alpha -> 0; the normal map (<name>_nrm.png, if there) -> flat.
#   blender -b --factory-startup --python clear_paint_islands.py
#   env: VDW_BODY_OBJ  body.obj from "vdw_debug paint dump"
#        VDW_TEX       the painted texture (.png); its _nrm.png is cleared too
#        VDW_UV        "u,v;u,v" one point inside each island to clear (arms: "0.43,0.62")
#        VDW_OUT       output folder (new; never overwrites), VDW_NAME new texture name
#        VDW_GROW      pixels past the island edge to clear, if no other island is nearer (default 32: the colour
#                      bake's margin is 16)
import bpy, numpy as np, os

BODY, TEX, OUT, NAME = os.environ["VDW_BODY_OBJ"], os.environ["VDW_TEX"], os.environ["VDW_OUT"], os.environ["VDW_NAME"]
GROW = int(os.environ.get("VDW_GROW", "32"))
pts = [tuple(float(c) for c in p.split(",")) for p in os.environ["VDW_UV"].split(";")]
out_png = os.path.join(OUT, NAME + ".png")
if os.path.exists(out_png): raise SystemExit("exists, kept: " + out_png)

bpy.ops.wm.obj_import(filepath=BODY)
me = [o for o in bpy.context.selected_objects if o.type == 'MESH'][0].data
uvl = me.uv_layers.active.data
img = bpy.data.images.load(TEX); n = img.size[0]
px = np.array(img.pixels[:], np.float32).reshape(n, n, 4)

# islands: faces joined across edges whose UVs match at both ends
parent = list(range(len(me.polygons)))
def find(a):
    while parent[a] != a: parent[a] = parent[parent[a]]; a = parent[a]
    return a
edge_faces = {}
for p in me.polygons:
    for li in p.loop_indices:
        l = me.loops[li]; e = me.edges[l.edge_index].key
        edge_faces.setdefault(e, []).append(p.index)
def uvat(p, v):
    for li in p.loop_indices:
        if me.loops[li].vertex_index == v: return tuple(round(c, 5) for c in uvl[li].uv)
for e, fs in edge_faces.items():
    if len(fs) != 2: continue
    a, b = me.polygons[fs[0]], me.polygons[fs[1]]
    if all(uvat(a, v) == uvat(b, v) for v in e): parent[find(fs[0])] = find(fs[1])

def raster(polys):
    m = np.zeros((n, n), bool)
    for p in polys:
        q = [np.array(uvl[li].uv[:]) * n for li in p.loop_indices]
        for k in range(1, len(q) - 1):
            a, b, c = q[0], q[k], q[k + 1]
            x0, x1 = int(max(0, min(a[0], b[0], c[0]) - 1)), int(min(n - 1, max(a[0], b[0], c[0]) + 1))
            y0, y1 = int(max(0, min(a[1], b[1], c[1]) - 1)), int(min(n - 1, max(a[1], b[1], c[1]) + 1))
            X, Y = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
            if abs(d) < 1e-12: continue
            l1 = ((b[1] - c[1]) * (X - c[0]) + (c[0] - b[0]) * (Y - c[1])) / d
            l2 = ((c[1] - a[1]) * (X - c[0]) + (a[0] - c[0]) * (Y - c[1])) / d
            m[y0:y1 + 1, x0:x1 + 1] |= (l1 >= -0.02) & (l2 >= -0.02) & (1 - l1 - l2 >= -0.02)
    return m

groups = {}
for p in me.polygons: groups.setdefault(find(p.index), []).append(p)
keys = {k: raster(fs) for k, fs in groups.items()}
pick = set()
for u, v in pts:
    x, y = int(u * n), int(v * n)
    hit = [k for k, m in keys.items() if m[y, x]]
    if not hit: raise SystemExit(f"no body island at uv {u},{v}")
    pick |= set(hit)
clear = np.zeros((n, n), bool); others = np.zeros((n, n), bool)
for k, m in keys.items():
    if k in pick: clear |= m
    else: others |= m
# the padding outside the islands (the bake's margin, up to VDW_GROW px) goes to whichever island is nearest: grow
# both sides a pixel at a time, a pixel taken by the first to reach it
grown, kept = clear.copy(), others & ~clear
for _ in range(GROW):
    def dil(m):
        g = m.copy(); g[1:] |= m[:-1]; g[:-1] |= m[1:]; g[:, 1:] |= m[:, :-1]; g[:, :-1] |= m[:, 1:]; return g
    gc, go = dil(grown), dil(kept)
    grown, kept = grown | (gc & ~kept), kept | (go & ~grown & ~gc)
before = (px[:, :, 3] > 0.01) & grown
print(f"CLEAR {len(pick)} islands, {grown.sum()} pixels; {before.sum()} of them were painted")
px[grown, 3] = 0

os.makedirs(OUT, exist_ok=True)
def save(arr, path, src):
    im = bpy.data.images.new(os.path.basename(path), n, n, alpha=True)
    im.colorspace_settings.name = src.colorspace_settings.name
    im.pixels = arr.ravel(); im.filepath_raw = path; im.file_format = 'PNG'; im.save(); print("SAVED", path)
save(px, out_png, img)
nrm_src = TEX[:-4] + "_nrm.png"
if os.path.exists(nrm_src):
    ni = bpy.data.images.load(nrm_src); ni.colorspace_settings.name = 'Non-Color'
    npx = np.array(ni.pixels[:], np.float32).reshape(n, n, 4)
    npx[grown, 0] = 0.5; npx[grown, 1] = 0.5; npx[grown, 2] = 1.0
    save(npx, os.path.join(OUT, NAME + "_nrm.png"), ni)
