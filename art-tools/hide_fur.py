# Hair cards on a hide: the igloo's bench blanket (the user's bench in shelter_v13 igloo.blend, its blanket faces on
# the material "blanket"). Laid like a deer hide (the user's photo): parted along a spine down the blanket's length,
# lying out to both sides and back toward the tail (-X), hanging straight down over a drape; deer tan in the middle,
# belly white toward the edges. Two coats: a shorter under-coat and a longer top coat lifted higher.
# The cards take one clump each from the fur atlas (shelter_vN/Textures/fur_Unity_*: the user's hair-card sheet,
# left half tan, right half white). They make the mesh "fur", material "fur" (the importer cuts it out by alpha).
# Run it in the open file (Blender's Text Editor or exec), or headless:
#   blender -b <igloo.blend> --factory-startup --python hide_fur.py      env: VDW_FUR_TEX (the folder of fur_Unity_*)
import bpy, bmesh, math, os
import numpy as np
from mathutils import Vector, Matrix

TEXD = os.environ.get("VDW_FUR_TEX", r"C:\Users\tripp\Desktop\Valheim_DeepWaters\Mesh\ice fishing\shelter_v14\Textures")
DENSITY = 0.0007          # m^2 of hide per card
SEED = 11

def build():
    src = next(o for o in bpy.data.objects if o.type == 'MESH' and any(m and m.name.split(".")[0] == "blanket" for m in o.data.materials))
    slot = next(i for i, m in enumerate(src.data.materials) if m and m.name.split(".")[0] == "blanket")
    M = src.matrix_world; R3 = M.to_3x3()
    if src.mode == 'EDIT': src.update_from_editmode()
    me0 = src.data
    tris, segs = [], []
    faces = [p for p in me0.polygons if p.material_index == slot]
    fset = {p.index for p in faces}
    for p in faces:
        n = (R3 @ p.normal).normalized(); ws = [M @ me0.vertices[v].co for v in p.vertices]
        for i in range(1, len(ws) - 1):
            a, b, c = ws[0], ws[i], ws[i + 1]; tris.append((a, b, c, n, ((b - a).cross(c - a)).length / 2))
    count = {}
    for p in faces:
        for ek in p.edge_keys: count[ek] = count.get(ek, 0) + 1
    segs = [(M @ me0.vertices[a].co, M @ me0.vertices[b].co) for (a, b), c in count.items() if c == 1]   # the hide's outline
    area = sum(t[4] for t in tris)
    tops = [t for t in tris if t[3].z > 0.9] or tris
    ys = [v.y for t in tops for v in t[:3]]; YC = (min(ys) + max(ys)) / 2

    def edge_dist(p):
        best = 9.0
        for a, b in segs:
            ab = b - a; t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-12)))
            best = min(best, (a + ab * t - p).length)
        return best

    im = bpy.data.images.load(os.path.join(TEXD, "fur_Unity_Albedo.png"), check_existing=True)
    W, H = im.size; a = np.array(im.pixels[:], np.float32).reshape(H, W, 4)[:, :W // 2, 3]   # the clumps: from the tan half
    W2 = W // 2
    k = 8; small = a[:H - H % k, :W2 - W2 % k].reshape(H // k, k, W2 // k, k).max((1, 3)) > 0.3
    lab = np.zeros(small.shape, int); boxes = []
    for y0 in range(small.shape[0]):
        for x0 in range(small.shape[1]):
            if not small[y0, x0] or lab[y0, x0]: continue
            nn = len(boxes) + 1; st = [(y0, x0)]; lab[y0, x0] = nn; yy_, xx_ = [], []
            while st:
                y, x = st.pop(); yy_.append(y); xx_.append(x)
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < small.shape[0] and 0 <= xx < small.shape[1] and small[yy, xx] and not lab[yy, xx]:
                        lab[yy, xx] = nn; st.append((yy, xx))
            # u in the tan half's own 0 - 1 (the atlas's u is half that; + 0.5 for the white half)
            boxes.append((min(xx_) * k / W2, (max(xx_) + 1) * k / W2, min(yy_) * k / H, (max(yy_) + 1) * k / H, len(yy_)))
    boxes = [b for b in boxes if b[4] > 0.01 * small.size]

    rng = np.random.default_rng(SEED)
    cum = np.cumsum([t[4] for t in tris]); cum /= cum[-1]
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap"); COLS = 3

    def flow(p):
        side = 1.0 if p.y >= YC else -1.0
        off = min(1.0, abs(p.y - YC) / 0.08)            # parts cleanly at the spine
        tail = 0.55 + 0.25 * (1 - off)                   # head at +X, the hair runs back toward the tail
        return Vector((-tail, side * off, -0.9 * off))

    ncard = int(area / DENSITY); whites = 0
    for layer in range(2):                               # under-coat, then top coat
        for _ in range(ncard // 2):
            t = tris[int(np.searchsorted(cum, rng.random()))]
            r1, r2 = rng.random(), rng.random()
            if r1 + r2 > 1: r1, r2 = 1 - r1, 1 - r2
            p = t[0] + (t[1] - t[0]) * r1 + (t[2] - t[0]) * r2; n = t[3]
            F = flow(p); d = F - n * F.dot(n)
            if d.length < 1e-4: d = Vector((-1, 0, 0))
            d.normalize(); d = Matrix.Rotation(rng.uniform(-0.25, 0.25), 3, n) @ d
            sv = n.cross(d).normalized()
            # belly white toward the outline, ragged; tan in the middle
            ed = edge_dist(p); thr = 0.075 + 0.035 * math.sin(p.x * 23.0) * math.cos(p.y * 17.0)
            white = rng.random() < min(1.0, max(0.0, (thr + 0.04 - ed) / 0.06))
            whites += white
            u0, u1, v0, v1, _ = boxes[rng.integers(len(boxes))]
            aspect = (u1 - u0) * W2 / max((v1 - v0) * H, 1)
            ln = rng.uniform(0.09, 0.13) * (1.1 if layer else 0.9); wd = float(np.clip(ln * aspect, 0.035, 0.075))
            base = 0.003 + 0.008 * layer
            lift = rng.uniform(0.018, 0.035) * (1.2 if layer else 0.8)
            root = p - d * ln * 0.3
            ua, ub = (0.5 + u0 * 0.5, 0.5 + u1 * 0.5) if white else (u0 * 0.5, u1 * 0.5)
            for sgn in (1, -1):
                grid = []
                for tt in (0.0, 0.5, 1.0):
                    h = base + lift * (0.6 * tt + 0.4 * tt ** 2) - (0.0005 if sgn < 0 else 0)
                    grid.append([bm.verts.new(root + d * ln * tt * (1 - 0.15 * tt) + sv * ((c / (COLS - 1) - 0.5) * wd * (1 + 0.25 * tt)) + n * h) for c in range(COLS)])
                for i in range(2):
                    for c in range(COLS - 1):
                        q = [grid[i][c], grid[i][c + 1], grid[i + 1][c + 1], grid[i + 1][c]]
                        uv = [(ua + (ub - ua) * cc / (COLS - 1), v1 - (v1 - v0) * ii / 2) for ii, cc in ((i, c), (i, c + 1), (i + 1, c + 1), (i + 1, c))]
                        if sgn > 0: q, uv = q[::-1], uv[::-1]
                        f = bm.faces.new(q)
                        for l, x in zip(f.loops, uv): l[uvl].uv = x

    for name in ("fur", "blanket_fur"):
        old = bpy.data.objects.get(name)
        if old: bpy.data.objects.remove(old)
    me = bpy.data.meshes.new("fur"); bm.to_mesh(me); bm.free()
    for pp in me.polygons: pp.use_smooth = True
    ob = bpy.data.objects.new("fur", me)
    (src.users_collection[0] if src.users_collection else bpy.context.scene.collection).objects.link(ob)
    m = bpy.data.materials.get("fur") or bpy.data.materials.new("fur")
    nt = m.node_tree; bs = nt.nodes["Principled BSDF"]
    for nd in [nd for nd in nt.nodes if nd.type in ('TEX_IMAGE', 'NORMAL_MAP')]: nt.nodes.remove(nd)
    ti = nt.nodes.new("ShaderNodeTexImage"); ti.image = im
    nt.links.new(ti.outputs["Color"], bs.inputs["Base Color"]); nt.links.new(ti.outputs["Alpha"], bs.inputs["Alpha"])
    tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = bpy.data.images.load(os.path.join(TEXD, "fur_Unity_Normal.png"), check_existing=True)
    tn.image.colorspace_settings.name = "Non-Color"
    nm = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(tn.outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], bs.inputs["Normal"])
    bs.inputs["Roughness"].default_value = 0.8
    try: m.surface_render_method = 'DITHERED'
    except Exception: pass
    me.materials.append(m)
    old_m = bpy.data.materials.get("blanket_fur")
    if old_m and old_m.users == 0: bpy.data.materials.remove(old_m)
    return {"cards": ncard, "white": whites, "faces": len(me.polygons), "hide_m2": round(area, 3)}

RESULT = build()
print("HIDE FUR", RESULT)
