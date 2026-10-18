# Re-unwraps a rigged fish along hand-style seams and bakes its current Unity maps onto the new layout.
#   Seams: straight down the middle (left / right half each its own island), around every fin (found by shape: thin
#   sheets), around the tail fin (behind the tail-fin bones), and each fin split into its two faces.
#   Source = the material's current _Unity_ maps on the current UVs.  Writes <NAME>_Unity_*.png (never overwrites),
#   a UV layout preview, and a new .blend.        env: VDW_BAKE_NAME, VDW_SAVE_TO, VDW_BAKE_SIZE, VDW_UV_PREVIEW,
#   VDW_TEX_DIR (where the maps go), VDW_FIN_THICKNESS (default 3.5 cm per 2 m of fish)
import bpy, bmesh, math, os
import numpy as np

SIZE = int(os.environ.get("VDW_BAKE_SIZE", "2048"))
NAME = os.environ["VDW_BAKE_NAME"]
SAVE_TO = os.environ["VDW_SAVE_TO"]
OUT_DIR = os.environ.get("VDW_TEX_DIR") or os.path.dirname(SAVE_TO)
PREVIEW = os.environ.get("VDW_UV_PREVIEW")

def pixels(img):
    a = np.empty(len(img.pixels), dtype=np.float32); img.pixels.foreach_get(a); return a.reshape(-1, 4)

arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
mesh = next(o for o in bpy.data.objects if o.type == 'MESH' and o.parent == arm)
arm.data.pose_position = 'REST'
scene = bpy.context.scene
if mesh.mode != 'OBJECT':      # a file saved in Edit Mode: leave it first, so the seams marked there are in the mesh
    bpy.context.view_layer.objects.active = mesh
    bpy.ops.object.mode_set(mode='OBJECT')
mat = mesh.material_slots[0].material
nt = mat.node_tree; nodes, links = nt.nodes, nt.links
out = next(n for n in nodes if n.type == 'OUTPUT_MATERIAL')
bsdf = next(n for n in nodes if n.type == 'BSDF_PRINCIPLED')
def linked_image(socket_name):
    l = next(l for l in links if l.to_node == bsdf and l.to_socket.name == socket_name)
    return l.from_node
src_albedo = linked_image("Base Color")
src_ms = linked_image("Metallic")
nmap = next(n for n in nodes if n.type == 'NORMAL_MAP')
# VDW_KEEP_SEAMS=1: unwrap along the seams already marked in the file (hand-placed) instead of making new ones.
KEEP_SEAMS = os.environ.get("VDW_KEEP_SEAMS") == "1"
# Hand-edited (custom) normals don't survive the bmesh round trip below; the geometry doesn't change, so they go back on.
saved_normals = [l.normal.copy() for l in mesh.data.loops] if mesh.data.has_custom_normals else None

# ---- 1. which part each face belongs to.
# A ray shot backward from each face (into the model) tells what the face is part of:
#   - it hits the INSIDE of a wall far away            -> body (closed volume)
#   - it hits the inside of a wall within a few cm     -> a two-sided fin (or whisker): cut around, split in two
#   - it hits nothing, or the OUTSIDE of something     -> a one-layer sheet (open fin): cut around, kept whole
# The body is cut straight down the middle (x = 0). The tail fin (behind the tail-fin bones) is cut off on its own.
from mathutils.bvhtree import BVHTree
_ys = [v.co.y for v in mesh.data.vertices]
THIN = float(os.environ.get("VDW_FIN_THICKNESS") or 0.035 * (max(_ys) - min(_ys)) / 2.0)   # scales with the fish
print(f"  fin thickness limit: {THIN * 100:.1f} cm")
bm = bmesh.new(); bm.from_mesh(mesh.data); bm.faces.ensure_lookup_table()
print(f"  open edges: {sum(1 for e in bm.edges if len(e.link_faces) == 1)}, "
      f"non-manifold edges: {sum(1 for e in bm.edges if len(e.link_faces) > 2)}")
bvh = BVHTree.FromBMesh(bm)
cat = {}
for f in bm.faces:
    n = f.normal
    if n.length < 0.5: cat[f.index] = "body"; continue
    loc, hn, _i, dist = bvh.ray_cast(f.calc_center_median() - n * 1e-4, -n)
    if loc is None or hn.dot(n) > 0:  cat[f.index] = "sheet"     # nothing behind it, or the outside of something
    elif dist < THIN:                 cat[f.index] = "thin"
    else:                             cat[f.index] = "body"
def neighbours(f): return [o for e in f.edges for o in e.link_faces if o != f]
for _ in range(3):   # smooth out speckle: a face follows a clear majority of its neighbours
    for f in bm.faces:
        nb = [cat[o.index] for o in neighbours(f)]
        if nb:
            top = max(set(nb), key=nb.count)
            if top != cat[f.index] and nb.count(top) / len(nb) > 0.65: cat[f.index] = top
print("  faces by type:", {c: list(cat.values()).count(c) for c in ("body", "thin", "sheet")})

# VDW_BODY_SEGMENTS=n: also cut the body across into n sections along its length (long eels: two 4 m strips
# would pack into a sliver of the texture)
NSEG = int(os.environ.get("VDW_BODY_SEGMENTS") or 1)
_by = [f.calc_center_median().y for f in bm.faces]; _ylo, _yhi = min(_by), max(_by)
def body_key(f):
    c = f.calc_center_median(); sd = "L" if c.x >= 0 else "R"
    if NSEG <= 1: return ("Body", sd)
    return ("Body", f"{sd}{min(NSEG - 1, int((c.y - _ylo) / (_yhi - _ylo + 1e-9) * NSEG))}")
key = {f.index: body_key(f) for f in bm.faces}
MIN_FIN = int(os.environ.get("VDW_MIN_FIN_FACES", "10"))
done = set(); nfin = 0
for f in bm.faces:
    if cat[f.index] == "body" or f.index in done: continue
    kind = cat[f.index]; patch = [f]; done.add(f.index); st = [f]
    while st:
        g = st.pop()
        for o in neighbours(g):
            if cat[o.index] == kind and o.index not in done: done.add(o.index); st.append(o); patch.append(o)
    if len(patch) < MIN_FIN: continue
    pts = np.array([v.co[:] for p in patch for v in p.verts]); c = pts.mean(0)
    if kind == "sheet":
        for p in patch: key[p.index] = (f"Sheet{nfin}", "one")
    else:
        _, _, vt = np.linalg.svd(pts - c, full_matrices=False)
        across = vt[2]                               # the direction through the fin's thickness
        if abs(across[0]) >= max(abs(across[1]), abs(across[2])): across = across * np.sign(across[0])   # +X side = a
        else: across = across * np.sign(across[2] if abs(across[2]) >= abs(across[1]) else across[1])
        for p in patch: key[p.index] = (f"Fin{nfin}", "a" if np.dot(p.normal[:], across) >= 0 else "b")
    print(f"  {kind:5s} fin {nfin}: {len(patch)} faces, centre {tuple(c.round(2))}, size {tuple((pts.max(0) - pts.min(0)).round(2))}")
    nfin += 1

# Tail fin: everything behind the base of the tail-fin bones, cut off on its own. Two-sided: split into left and
# right faces. One-layer: kept whole.
tb = arm.data.bones.get("Top.Tail.Fin1")
tail_y = None
if tb: tail_y = (mesh.matrix_world.inverted() @ arm.matrix_world @ tb.head_local).y
elif os.environ.get("VDW_TAIL_START"):   # a download's own rig: where the tail fin starts, as a share of the length from the nose
    _ys = [v.co.y for v in bm.verts]; tail_y = min(_ys) + float(os.environ["VDW_TAIL_START"]) * (max(_ys) - min(_ys))
if tail_y is not None:
    tail_faces = [f for f in bm.faces if f.calc_center_median().y > tail_y]
    one_layer = sum(cat[f.index] == "sheet" for f in tail_faces) > len(tail_faces) / 2
    for f in tail_faces:   # facing direction, or position where the fin's ridges make the direction ambiguous
        x = f.normal.x if abs(f.normal.x) > 0.3 else f.calc_center_median().x
        key[f.index] = ("Tail", "one" if one_layer else ("L" if x >= 0 else "R"))
    if not one_layer:
        for _ in range(6):     # ridged fins: a face joins the side most of its tail neighbours are on
            for f in tail_faces:
                nb = [key[o.index] for o in neighbours(f) if key[o.index][0] == "Tail"]
                other = ("Tail", "R" if key[f.index][1] == "L" else "L")
                if nb and nb.count(other) > len(nb) / 2: key[f.index] = other
    print(f"  tail fin: {len(tail_faces)} faces behind y = {tail_y:.2f} ({'one layer, kept whole' if one_layer else 'two-sided, split left/right'})")

# Clean up stray faces (a face whose neighbours all disagree with it joins them).
for _ in range(3):
    for f in bm.faces:
        nb = [key[o.index] for o in neighbours(f)]
        if nb and key[f.index] not in nb:
            key[f.index] = max(set(nb), key=nb.count)

# Optional check render: every region in its own colour.
REGION_RENDER = os.environ.get("VDW_REGION_RENDER")
if REGION_RENDER:
    import random
    rnd = random.Random(1); colours = {}
    for k in sorted(set(key.values())):
        colours[k] = (0.85, 0.75, 0.6) if k == ("Body", "L") else (0.55, 0.65, 0.85) if k == ("Body", "R") else (rnd.random(), rnd.random(), rnd.random())
    region_colours = [colours[key[f.index]] for f in bm.faces]

seams = 0
for e in bm.edges:
    lf = e.link_faces
    if not KEEP_SEAMS:
        e.seam = len(lf) == 2 and key[lf[0].index] != key[lf[1].index]
    seams += e.seam
counts = {}
for k in key.values(): counts[k] = counts.get(k, 0) + 1
print("  faces per region:", dict(sorted(counts.items())))
print("  seam edges:", seams, "(kept from the file)" if KEEP_SEAMS else "")

# ---- 2. unwrap into a new UV layer (the old one stays for reading the textures)
old_uv = mesh.data.uv_layers.active.name
bm.to_mesh(mesh.data); bm.free()
new_uv = mesh.data.uv_layers.new(name="UVSeams"); mesh.data.uv_layers.active = new_uv
for o in bpy.context.view_layer.objects: o.select_set(False)
bpy.context.view_layer.objects.active = mesh; mesh.select_set(True)
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.unwrap(method='ANGLE_BASED', fill_holes=True, correct_aspect=True, margin=0.0)
bpy.ops.uv.average_islands_scale()
# overlaps: on scans' tangled (non-manifold) spots the unwrap folds a few faces over their neighbours, which then show
# the neighbour's paint whatever is baked. Exactly those faces get their own islands (VDW_FIX_OVERLAP=0 skips).
if os.environ.get("VDW_FIX_OVERLAP", "1") == "1":
    bpy.context.scene.tool_settings.use_uv_select_sync = False
    bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.uv.select_all(action='DESELECT')
    try:
        bpy.ops.uv.select_overlap(extend=False)
        _bm = bmesh.from_edit_mesh(mesh.data); _uvl = _bm.loops.layers.uv.active
        _ov = [f for f in _bm.faces if all(l[_uvl].select for l in f.loops)]
        print(f"  overlapping faces after the unwrap: {len(_ov)}")
        if _ov:
            for f in _bm.faces: f.select = f in _ov
            bmesh.update_edit_mesh(mesh.data)
            bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.0, scale_to_bounds=False, correct_aspect=True)
            bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.uv.select_all(action='SELECT')
            bpy.ops.uv.average_islands_scale()
    except RuntimeError as ex:
        print("  overlap check skipped:", ex)
    bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.pack_islands(rotate=True, rotate_method='ANY', scale=True, margin_method='FRACTION', margin=0.004, shape_method='CONCAVE')
bpy.ops.object.mode_set(mode='OBJECT')

# islands + stretch report
bm = bmesh.new(); bm.from_mesh(mesh.data); uvl = bm.loops.layers.uv["UVSeams"]
bm.faces.ensure_lookup_table()
parent = list(range(len(bm.faces)))
def find(i):
    while parent[i] != i: parent[i] = parent[parent[i]]; i = parent[i]
    return i
for e in bm.edges:
    if e.seam or len(e.link_faces) != 2: continue
    a, b = e.link_faces
    ua = {l.vert.index: l[uvl].uv.copy() for l in a.loops}; ub = {l.vert.index: l[uvl].uv.copy() for l in b.loops}
    if all((ua[v.index] - ub[v.index]).length < 1e-5 for v in e.verts): parent[find(a.index)] = find(b.index)
isl = {}
for f in bm.faces: isl.setdefault(find(f.index), []).append(f)
big = sorted(isl.values(), key=lambda fs: -sum(f.calc_area() for f in fs))
print(f"  islands: {len(isl)} (largest 6 by surface: " + ", ".join(f"{key[fs[0].index][0]}/{key[fs[0].index][1]} {len(fs)} faces" for fs in big[:6]) + ")")
ratios = []
for f in bm.faces:
    a3 = f.calc_area()
    uv = [l[uvl].uv for l in f.loops]
    a2 = abs(sum(uv[i].x * uv[(i + 1) % len(uv)].y - uv[(i + 1) % len(uv)].x * uv[i].y for i in range(len(uv)))) / 2
    if a3 > 1e-9: ratios.append(a2 / a3)
r = np.array(ratios); r /= np.median(r)
print(f"  texel density spread (1 = even): 10th pct {np.percentile(r, 10):.2f}, 90th pct {np.percentile(r, 90):.2f}")
uv_faces = [[tuple(l[uvl].uv) for l in f.loops] for f in bm.faces]
seam_uv = [[tuple(l[uvl].uv) for l in f.loops if l.edge.seam] for f in bm.faces]
bm.free()

# ---- 3. bake the current maps onto the new layout
# Works from either a raw PBR material (separate metallic + roughness textures, e.g. straight from Tripo) or one
# already on Unity maps (MetallicSmoothness: metallic in colour, smoothness in alpha).
src_normal = nmap.inputs["Color"].links[0].from_node
rl = next((l for l in links if l.to_node == bsdf and l.to_socket.name == "Roughness"), None)
src_rough = rl.from_node if rl and rl.from_node.type == 'TEX_IMAGE' else None
for n in (src_ms, src_rough, src_normal):
    if n and n.image: n.image.colorspace_settings.name = 'Non-Color'   # data, not colour
nmap.inputs["Strength"].default_value = 1.0     # bake the normal map's full detail (Unity applies it at full strength)
uvnode = nodes.new("ShaderNodeUVMap"); uvnode.uv_map = old_uv
for n in (src_albedo, src_ms, src_rough, src_normal):
    if n: links.new(uvnode.outputs["UV"], n.inputs["Vector"])
nmap.uv_map = old_uv

scene.render.engine = 'CYCLES'; scene.cycles.device = 'CPU'
scene.render.bake.margin = 16; scene.render.bake.use_clear = True
scene.render.bake.use_selected_to_active = False   # a file saved after a high-to-low bake keeps this on
emit = nodes.new("ShaderNodeEmission")
def target(name, non_color, alpha=False):
    path = os.path.join(OUT_DIR, name + ".png")
    if "_Unity_" in name and os.path.exists(path):
        raise RuntimeError("refusing to overwrite " + path)
    img = bpy.data.images.new(name, SIZE, SIZE, alpha=alpha)
    if non_color: img.colorspace_settings.name = 'Non-Color'
    node = nodes.new("ShaderNodeTexImage"); node.image = img
    for n in nodes: n.select = False
    node.select = True; nodes.active = node
    return img, node
def bake_emit(socket, name, non_color):
    img, node = target(name, non_color)
    links.new(socket, emit.inputs["Color"]); links.new(emit.outputs["Emission"], out.inputs["Surface"])
    scene.cycles.samples = 4
    bpy.ops.object.bake(type='EMIT'); nodes.remove(node); print("  baked", name)
    return img
albedo = bake_emit(src_albedo.outputs["Color"], f"{NAME}_Unity_Albedo", False)
metal = bake_emit(src_ms.outputs["Color"], f"{NAME}_metal_tmp", True)
if src_rough:
    smooth = bake_emit(src_rough.outputs["Color"], f"{NAME}_smooth_tmp", True)
    sp_ = pixels(smooth); sp_[:, :3] = 1.0 - sp_[:, :3]; smooth.pixels.foreach_set(sp_.ravel())   # roughness -> smoothness
else:
    smooth = bake_emit(src_ms.outputs["Alpha"], f"{NAME}_smooth_tmp", True)
links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
nimg, nnode = target(f"{NAME}_Unity_Normal", True)
scene.cycles.samples = 8
scene.render.bake.normal_space = 'TANGENT'
scene.render.bake.normal_r, scene.render.bake.normal_g, scene.render.bake.normal_b = 'POS_X', 'POS_Y', 'POS_Z'
bpy.ops.object.bake(type='NORMAL'); nodes.remove(nnode); print("  baked", nimg.name)
# Spots where the source UVs had collapsed faces bake as normals pointing into the surface (olive); make them flat.
n_px = pixels(nimg); bad = n_px[:, 2] < 0.45; n_px[bad] = (0.5, 0.5, 1.0, 1.0); nimg.pixels.foreach_set(n_px.ravel())
print(f"  normal: flattened {bad.mean() * 100:.2f}% of pixels")

ms, _n = target(f"{NAME}_Unity_MetallicSmoothness", True, alpha=True); nodes.remove(_n)
m, s = pixels(metal), pixels(smooth)
px = np.empty_like(m); px[:, 0] = px[:, 1] = px[:, 2] = m[:, 0]; px[:, 3] = s[:, 0]
ms.pixels.foreach_set(px.ravel())
for img in (albedo, ms, nimg):
    img.filepath_raw = os.path.join(OUT_DIR, img.name + ".png"); img.file_format = 'PNG'; img.save()
    print("  saved", img.filepath_raw)

# ---- 4. material on the new maps, old UVs removed
src_imgs = [n.image for n in (src_albedo, src_ms, src_rough, src_normal) if n]
for n in list(nodes):
    if n not in (bsdf, out): nodes.remove(n)
def node_img(img, x, y):
    n = nodes.new("ShaderNodeTexImage"); n.image = img; n.location = (x, y); return n
a = node_img(albedo, -700, 300); sn = node_img(ms, -700, 0); nm = node_img(nimg, -700, -320)
links.new(a.outputs["Color"], bsdf.inputs["Base Color"]); links.new(sn.outputs["Color"], bsdf.inputs["Metallic"])
inv = nodes.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0; inv.location = (-350, -60)
links.new(sn.outputs["Alpha"], inv.inputs[1]); links.new(inv.outputs["Value"], bsdf.inputs["Roughness"])
nmap = nodes.new("ShaderNodeNormalMap"); nmap.location = (-350, -320)
links.new(nm.outputs["Color"], nmap.inputs["Color"]); links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
links.new(bsdf.outputs["BSDF"], out.inputs["Surface"]); nodes.active = a
for img in (metal, smooth): bpy.data.images.remove(img)
for img in src_imgs:
    if img and img.users == 0: bpy.data.images.remove(img)
mesh.data.uv_layers.remove(mesh.data.uv_layers[old_uv])
mesh.data.uv_layers["UVSeams"].name = "UVMap"
mesh.data.uv_layers["UVMap"].active_render = True
nmap.uv_map = "UVMap"

# ---- 5. UV layout preview: the new albedo with island outlines (white) and seams (red)
if PREVIEW:
    P = 1024
    base = pixels(albedo).reshape(SIZE, SIZE, 4)[::SIZE // P, ::SIZE // P].copy()
    def line(p, q, col):
        n = int(max(abs(p[0] - q[0]), abs(p[1] - q[1])) * P) + 2
        for t in np.linspace(0, 1, n):
            x = int(min(P - 1, max(0, (p[0] + (q[0] - p[0]) * t) * P))); y = int(min(P - 1, max(0, (p[1] + (q[1] - p[1]) * t) * P)))
            base[y, x] = col
    for fuv in uv_faces:
        for i in range(len(fuv)): line(fuv[i], fuv[(i + 1) % len(fuv)], (1, 1, 1, 1))
    prev = bpy.data.images.new("uv_preview", P, P, alpha=True); prev.pixels.foreach_set(base.ravel())
    prev.filepath_raw = PREVIEW; prev.file_format = 'PNG'; prev.save(); bpy.data.images.remove(prev)
    print("  preview", PREVIEW)

# Region check render (not saved into the file): each region in its own colour, from the side, top and below.
if REGION_RENDER:
    from mathutils import Vector
    attr = mesh.data.color_attributes.new("regions", 'BYTE_COLOR', 'CORNER')
    for poly in mesh.data.polygons:
        col = region_colours[poly.index]
        for li in poly.loop_indices: attr.data[li].color = (*col, 1.0)
    mesh.data.color_attributes.active_color = attr
    eng = scene.render.engine; scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.light = 'STUDIO'; scene.display.shading.color_type = 'VERTEX'
    rx, ry = scene.render.resolution_x, scene.render.resolution_y
    scene.render.resolution_x, scene.render.resolution_y = 1000, 500
    co = np.array([v.co[:] for v in mesh.data.vertices]); ctr = Vector(((co.min(0) + co.max(0)) / 2).tolist()); size = float((co.max(0) - co.min(0)).max())
    cd = bpy.data.cameras.new("RegionCam"); cd.type = 'ORTHO'; cd.ortho_scale = size * 1.08
    cam = bpy.data.objects.new("RegionCam", cd); scene.collection.objects.link(cam); old_cam = scene.camera; scene.camera = cam
    r90 = math.radians(90); r180 = math.radians(180)
    for view, d, rot in (("side", Vector((1, 0, 0)), (r90, 0, r90)), ("top", Vector((0, 0, 1)), (0, 0, r90)),
                         ("below", Vector((0, 0, -1)), (r180, 0, r90)), ("q", Vector((0.7, -0.5, 0.45)), None)):
        cam.location = ctr + d.normalized() * size * 4      # head on the left in side/top/below
        cam.rotation_euler = rot if rot else (ctr - cam.location).to_track_quat('-Z', 'Y').to_euler()
        scene.render.filepath = f"{REGION_RENDER}_{view}.png"; bpy.ops.render.render(write_still=True)
    scene.camera = old_cam; bpy.data.objects.remove(cam); bpy.data.cameras.remove(cd)
    mesh.data.color_attributes.remove(mesh.data.color_attributes["regions"])
    scene.render.engine = eng; scene.render.resolution_x, scene.render.resolution_y = rx, ry
    print("  region renders", REGION_RENDER)

if saved_normals is not None and len(saved_normals) == len(mesh.data.loops):
    mesh.data.normals_split_custom_set(saved_normals)
    print(f"  kept the hand-set normals ({len(saved_normals)} corners)")
arm.data.pose_position = 'POSE'
scene.render.engine = 'BLENDER_EEVEE_NEXT'
bpy.ops.wm.save_as_mainfile(filepath=SAVE_TO)
print("  saved blend", SAVE_TO)
print("SEAM UNWRAP DONE")






