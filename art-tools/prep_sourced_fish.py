# Turns a downloaded fish (Sketchfab glTF import, as saved by the Sketchfab add-on) into the one-mesh, one-material
# starting point the fish pipeline expects (rig_fish -> animate_fish -> seam_unwrap -> add_backfaces -> export_fish):
#   - drops stray parts (no material, 12-face marker cubes, anything VDW_DROP matches; VDW_KEEP keeps only matching
#     parts), takes skinned parts in their rest shape, joins the rest into one "hi" mesh
#   - turns it so its length runs along Y, head toward -Y, top up +Z: long axis by PCA, head = the fuller end,
#     top = the side the fins stick out more (overrides: VDW_FLIP_HEAD=1, VDW_FLIP_UP=1, VDW_ROLL=deg about the
#     length; VDW_FLAT=1 for a flatfish: its thinnest axis becomes up)
#   - "lo" = a welded copy, decimated to VDW_FACES (default 12000) when bigger, with a fresh UV layout
#   - bakes hi onto lo (colour + tangent normals, so scan detail and the source's normal maps are kept)
#   - writes <NAME>_Unity_Albedo / _MetallicSmoothness (wet scales) / _Normal and wires them the way seam_unwrap reads
#   - saves a new .blend with only "lo" (named VDW_NAME), sized VDW_LENGTH metres, plus side/top check renders
#   blender -b source.blend --python prep_sourced_fish.py
#   env: VDW_NAME, VDW_LENGTH, VDW_TEX_DIR, VDW_SAVE_TO, VDW_PREVIEW (png prefix), VDW_FACES, VDW_BAKE_SIZE (2048)
import bpy, bmesh, math, os, re
import numpy as np
from mathutils import Vector, Matrix

NAME = os.environ["VDW_NAME"]; L = float(os.environ["VDW_LENGTH"]); TEX = os.environ["VDW_TEX_DIR"]
SAVE_TO = os.environ["VDW_SAVE_TO"]; PREV = os.environ.get("VDW_PREVIEW", "")
FACES = int(os.environ.get("VDW_FACES", "12000")); SIZE = int(os.environ.get("VDW_BAKE_SIZE", "2048"))
KEEP = os.environ.get("VDW_KEEP"); DROP = os.environ.get("VDW_DROP")
os.makedirs(TEX, exist_ok=True)
# VDW_SAVE_HI=path: only save the joined, oriented, sized full-detail source ("hi", exactly as the bake saw it) to that
# .blend and stop - for re-baking onto a mesh the user has since rigged or edited
SAVE_HI = os.environ.get("VDW_SAVE_HI")
if not SAVE_HI:
    for k in ("Albedo", "MetallicSmoothness", "Normal"):
        if os.path.exists(os.path.join(TEX, f"{NAME}_Unity_{k}.png")): raise RuntimeError(f"refusing to overwrite {NAME}_Unity_{k}")
    if os.path.exists(SAVE_TO): raise RuntimeError("refusing to overwrite " + SAVE_TO)
scene = bpy.context.scene
print(f"\n===== PREP {NAME} =====")

# ---- 1. which parts to keep
for a in bpy.data.objects:
    if a.type == 'ARMATURE': a.data.pose_position = 'REST'
    a.animation_data_clear()
    if a.type == 'MESH' and a.data.shape_keys: a.active_shape_key_index = 0
bpy.context.view_layer.update()
keep = []
for o in bpy.data.objects:
    if o.type != 'MESH': continue
    mats = [m for m in o.data.materials if m]
    why = None
    if not mats: why = "no material"
    elif len(o.data.polygons) == 12 and len(o.data.vertices) == 24: why = "marker cube"
    elif KEEP and not re.search(KEEP, o.name): why = "not in VDW_KEEP"
    elif DROP and re.search(DROP, o.name): why = "VDW_DROP"
    if why: print(f"  dropped {o.name} ({why})"); continue
    keep.append(o)
dg = bpy.context.evaluated_depsgraph_get()
parts = []
for o in keep:   # each part as plain mesh data in world space, rest shape (armature / shape keys evaluated)
    e = o.evaluated_get(dg); me = bpy.data.meshes.new_from_object(e, preserve_all_data_layers=True, depsgraph=dg)
    me.transform(o.matrix_world); parts.append(me)
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
objs = []
for me in parts:
    ob = bpy.data.objects.new("part", me); scene.collection.objects.link(ob); objs.append(ob)
for ob in objs:   # same UV layer name everywhere, so the join keeps one layer
    for i, uv in enumerate(ob.data.uv_layers): uv.name = "UVMap" if i == 0 else f"UVExtra{i}"
bpy.context.view_layer.update()
for o in list(scene.objects): o.select_set(o in objs)
bpy.context.view_layer.objects.active = objs[0]
if len(objs) > 1: bpy.ops.object.join()
hi = bpy.context.view_layer.objects.active; hi.name = "hi"
hi.vertex_groups.clear()   # the source rig's weights: the Deep Waters rig weights it afresh
print(f"  kept {len(keep)} parts: {len(hi.data.vertices)} points, {len(hi.data.polygons)} faces, materials {[m.name for m in hi.data.materials]}")

# ---- 1a. unlit materials (glTF KHR_materials_unlit: scans come as image -> Emission, no BSDF) become a plain
# Principled BSDF on the same image, so the colour bake and the back/belly test can read them.
for m in hi.data.materials:
    if m is None or not m.node_tree: continue
    nt_ = m.node_tree
    if any(n.type == 'BSDF_PRINCIPLED' for n in nt_.nodes): continue
    img = next((n for n in nt_.nodes if n.type == 'TEX_IMAGE' and n.image), None)
    outn = next((n for n in nt_.nodes if n.type == 'OUTPUT_MATERIAL'), None)
    if img is None or outn is None: continue
    b = nt_.nodes.new("ShaderNodeBsdfPrincipled")
    nt_.links.new(img.outputs["Color"], b.inputs["Base Color"]); nt_.links.new(b.outputs["BSDF"], outn.inputs["Surface"])
    print(f"  unlit material {m.name}: now a Principled BSDF on {img.image.name}")
# ---- 1b. cut-out fins: faces drawn see-through by their colour map's alpha (cheap models' fins are flat cards) are
# cut down to the painted outline - diced fine, and the pieces that land on clear texture removed. Unity draws
# fish opaque, so a card would show as a solid rectangle.
def alpha_map(m):
    if m is None or not m.node_tree: return None
    b = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if b is None or not b.inputs["Alpha"].links: return None
    n = b.inputs["Alpha"].links[0].from_node
    if n.type != 'TEX_IMAGE' or n.image is None: return None
    c = n.image.copy(); c.scale(512, 512)
    a = np.empty(512 * 512 * 4, np.float32); c.pixels.foreach_get(a); bpy.data.images.remove(c)
    a = a.reshape(512, 512, 4)[:, :, 3]
    return a if a.min() < 0.5 else None   # (any see-through at all: checked against ACUT below)
# VDW_ALPHA_CUT (0.5): below it a texel counts as clear. Lower it for models whose fin membranes are see-through but
# still meant to show (Unity draws them opaque anyway).
ACUT = float(os.environ.get("VDW_ALPHA_CUT", "0.5"))
amaps = {i: alpha_map(m) for i, m in enumerate(hi.data.materials)}
if any(v is not None for v in amaps.values()):
    bm = bmesh.new(); bm.from_mesh(hi.data); uvl_ = bm.loops.layers.uv.get("UVMap")
    def a_at(am, uv): return am[int((uv[1] % 1) * 511.999), int((uv[0] % 1) * 511.999)]
    def face_uv(f): return np.array([l[uvl_].uv[:] for l in f.loops])
    cards = []
    for f in bm.faces:
        am = amaps.get(f.material_index)
        if am is None: continue
        uv = face_uv(f); lo2, hi2 = uv.min(0), uv.max(0)
        g = np.stack(np.meshgrid(np.linspace(lo2[0], hi2[0], 8), np.linspace(lo2[1], hi2[1], 8)), -1).reshape(-1, 2)
        if min(a_at(am, p) for p in g) < ACUT: cards.append(f)
    if cards:
        edges = list({e for f in cards for e in f.edges})
        bmesh.ops.subdivide_edges(bm, edges=edges, cuts=12, use_grid_fill=True)
        gone = []
        for f in bm.faces:
            am = amaps.get(f.material_index)
            if am is None: continue
            if a_at(am, face_uv(f).mean(0)) < ACUT: gone.append(f)
        bmesh.ops.delete(bm, geom=gone, context='FACES')
        bm.to_mesh(hi.data); print(f"  cut-out fins: {len(cards)} card faces diced, {len(gone)} clear pieces removed")
    bm.free()

# ---- 2. orientation
co = np.array([v.co[:] for v in hi.data.vertices]); c0 = co.mean(0)
_, _, vt = np.linalg.svd((co - c0)[::max(1, len(co) // 50000)], full_matrices=False)
ax_len, ax_mid, ax_thin = vt[0], vt[1], vt[2]
if os.environ.get("VDW_FLAT") == "1": up, side = ax_thin, ax_mid
else: up, side = ax_mid, ax_thin
def proj(a): return (co - c0) @ a
t = proj(ax_len); tn = (t - t.min()) / (t.max() - t.min())
# head = the fuller end: compare the body's cross-section (spread across the up axis) near each end
u = proj(up)
def spread(sel): return float(np.percentile(u[sel], 90) - np.percentile(u[sel], 10)) if sel.sum() > 10 else 0.0
front, back = spread(tn < 0.25), spread(tn > 0.6) * 0 + spread((tn > 0.55) & (tn < 0.8))
head_neg = front >= back           # True: the low end of ax_len is the head
if os.environ.get("VDW_FLIP_HEAD") == "1": head_neg = not head_neg
# top: fish carry more fin (and a darker back) above; use how far the outline reaches either way along "up",
# over the middle of the body (dorsal fin vs belly)
mid = (tn > 0.25) & (tn < 0.6)
top_pos = (np.percentile(u[mid], 99) - np.median(u[mid])) >= (np.median(u[mid]) - np.percentile(u[mid], 1))
# Better, when the parts are textured: a fish's back is darker than its belly (countershading; a flatfish's eyed
# side is darker than its blind side). Sample each point's colour from its material's colour map.
small = {}
def colour_map(m):
    if m is None or not m.node_tree: return None
    b = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if b is None or not b.inputs["Base Color"].links: return None
    n = b.inputs["Base Color"].links[0].from_node
    if n.type != 'TEX_IMAGE' or n.image is None: return None
    if n.image.name not in small:
        c = n.image.copy(); c.scale(256, 256)
        a = np.empty(256 * 256 * 4, np.float32); c.pixels.foreach_get(a); bpy.data.images.remove(c)
        small[n.image.name] = a.reshape(256, 256, 4)[:, :, :3].mean(2)
    return small[n.image.name]
me_ = hi.data; uvl = me_.uv_layers.get("UVMap")
if uvl is not None:
    vl = np.full(len(me_.vertices), np.nan)
    for p in me_.polygons:
        if p.material_index >= len(me_.materials): continue
        cm = colour_map(me_.materials[p.material_index])
        if cm is None: continue
        for li in p.loop_indices:
            uv = uvl.data[li].uv; vl[me_.loops[li].vertex_index] = cm[int((uv.y % 1) * 255.999), int((uv.x % 1) * 255.999)]
    ok = ~np.isnan(vl) & mid
    if ok.sum() > 50:
        um = np.median(u[ok]); above, below = ok & (u > um), ok & (u < um)
        la, lb = float(vl[above].mean()), float(vl[below].mean())
        print(f"  brightness above {la:.3f} / below {lb:.3f} (the darker side is the back)")
        if abs(la - lb) > 0.02: top_pos = la < lb
if os.environ.get("VDW_FLIP_UP") == "1": top_pos = not top_pos
# VDW_UP_AXIS=z: trust the download's own up (+Z after the glTF import) instead of guessing - for modelled fish
# whose spread fins make the guessed axis come out tilted
if os.environ.get("VDW_UP_AXIS", "").lower() == "z":
    zz = np.array([0.0, 0.0, 1.0]); zz = zz - ax_len * np.dot(zz, ax_len); up = zz / np.linalg.norm(zz); top_pos = True
    print("  up: the download's own +Z")
Y =Vector((-ax_len if head_neg else ax_len).tolist()) * -1   # +Y = toward the tail
Z = Vector((up if top_pos else -up).tolist())
X = Y.cross(Z).normalized(); Z = X.cross(Y).normalized()
R = Matrix((X, Y, Z))      # rows: world -> fish frame
roll = math.radians(float(os.environ.get("VDW_ROLL", "0")))
M = Matrix.Rotation(roll, 4, 'Y') @ R.to_4x4() @ Matrix.Translation(Vector((-c0).tolist()))
hi.data.transform(M)
co = np.array([v.co[:] for v in hi.data.vertices]); lo_, hi_ = co.min(0), co.max(0)
s = L / (hi_[1] - lo_[1]); ctr = (lo_ + hi_) / 2
hi.data.transform(Matrix.Diagonal((s, s, s, 1)) @ Matrix.Translation(Vector((-ctr).tolist())))
if R.determinant() < 0: hi.data.flip_normals()
hi.data.update()
# the whole world -> fish-frame transform, kept on the object (carry_source_rig.py moves a download's own rig with it)
TOT = Matrix.Diagonal((s, s, s, 1)) @ Matrix.Translation(Vector((-ctr).tolist())) @ M
hi["vdw_prep_matrix"] = [x for row in TOT for x in row]
co = np.array([v.co[:] for v in hi.data.vertices]); print(f"  oriented: size {tuple((co.max(0) - co.min(0)).round(3))} m (head -Y, top +Z)")
if SAVE_HI:
    for m in hi.data.materials:      # the same material fixes the bake below makes (alpha, metal off)
        b = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None) if m and m.node_tree else None
        if b:
            for sock in ("Alpha", "Metallic", "Transmission Weight"):
                if sock in b.inputs:
                    for l in list(b.inputs[sock].links): m.node_tree.links.remove(l)
                    b.inputs[sock].default_value = 1.0 if sock == "Alpha" else 0.0
    for im in bpy.data.images:
        if im.users and not im.packed_file: im.pack()
    hi.name = "hi_source"
    bpy.data.libraries.write(SAVE_HI, {hi}, fake_user=True, compress=True)
    print("  saved the oriented source to", SAVE_HI); raise SystemExit(0)

# ---- 3. lo: welded, decimated copy with one fresh UV layout
lo = hi.copy(); lo.data = hi.data.copy(); lo.name = NAME; scene.collection.objects.link(lo)
bm = bmesh.new(); bm.from_mesh(lo.data)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=L * 0.0004)   # a bigger weld fuses a scan's thin fins into tangled faces
bm.to_mesh(lo.data); bm.free()
for o in bpy.context.view_layer.objects: o.select_set(o == lo)
bpy.context.view_layer.objects.active = lo
decimated = len(lo.data.polygons) > FACES
if decimated:
    d = lo.modifiers.new("dec", 'DECIMATE'); d.ratio = FACES / len(lo.data.polygons); d.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier=d.name)
# loose crumbs a scan leaves behind (a few faces floating off the body)
bm = bmesh.new(); bm.from_mesh(lo.data); bm.verts.ensure_lookup_table()
seen = set(); groups = []
for v in bm.verts:
    if v.index in seen: continue
    st = [v]; seen.add(v.index); g = [v]
    while st:
        w = st.pop()
        for e in w.link_edges:
            o2 = e.other_vert(w)
            if o2.index not in seen: seen.add(o2.index); st.append(o2); g.append(o2)
    groups.append(g)
big = max(len(g) for g in groups)
# only on decimated scans: a modelled fish's small loose parts are eyes and teeth
crumbs = [v for g in groups if len(g) < max(12, big * 0.002) for v in g] if decimated else []
if crumbs: bmesh.ops.delete(bm, geom=crumbs, context='VERTS')
bm.to_mesh(lo.data); bm.free()
print(f"  lo: {len(lo.data.polygons)} faces ({len(groups)} pieces, {len(crumbs)} crumb points removed)")
while len(lo.data.uv_layers): lo.data.uv_layers.remove(lo.data.uv_layers[0])
lo.data.uv_layers.new(name="UVMap")
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.004)
bpy.ops.object.mode_set(mode='OBJECT')
lo.data.materials.clear()
mat = bpy.data.materials.new(NAME); mat.use_nodes = True; lo.data.materials.append(mat)
nt = mat.node_tree; N, Lk = nt.nodes, nt.links
bs = next(n for n in N if n.type == 'BSDF_PRINCIPLED')

# ---- 4. bake hi -> lo
scene.render.engine = 'CYCLES'; scene.cycles.device = 'CPU'; scene.cycles.samples = 4
bk = scene.render.bake
bk.use_selected_to_active = True; bk.cage_extrusion = L * 0.01; bk.max_ray_distance = L * 0.03; bk.margin = 16
for o in bpy.context.view_layer.objects: o.select_set(o in (hi, lo))
bpy.context.view_layer.objects.active = lo
def bake_into(kind, non_color, **kw):
    img = bpy.data.images.new(f"{NAME}_{kind}_bake", SIZE, SIZE, alpha=False)
    if non_color: img.colorspace_settings.name = 'Non-Color'
    tn_ = N.new("ShaderNodeTexImage"); tn_.image = img
    for n in N: n.select = False
    tn_.select = True; N.active = tn_
    bpy.ops.object.bake(**kw); N.remove(tn_); print("  baked", kind); return img
for m in hi.data.materials:   # source fins drawn see-through still bake as their colour
    if m and m.node_tree:
        b = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if b:
            for l in list(b.inputs["Alpha"].links): m.node_tree.links.remove(l)
            b.inputs["Alpha"].default_value = 1.0
            for sock in ("Metallic", "Transmission Weight"):   # a metal's diffuse colour bakes black
                if sock in b.inputs:
                    for l in list(b.inputs[sock].links): m.node_tree.links.remove(l)
                    b.inputs[sock].default_value = 0.0
col = bake_into("color", False, type='DIFFUSE', pass_filter={'COLOR'})
bk.normal_space = 'TANGENT'
nrm = bake_into("normal", True, type='NORMAL')

def px(img):
    a = np.empty(len(img.pixels), np.float32); img.pixels.foreach_get(a); return a.reshape(-1, 4)
def save(arr, kind, nc):
    im = bpy.data.images.new(f"{NAME}_Unity_{kind}", SIZE, SIZE, alpha=True)
    if nc: im.colorspace_settings.name = 'Non-Color'
    im.pixels.foreach_set(np.ascontiguousarray(arr, np.float32).ravel())
    im.filepath_raw = os.path.join(TEX, f"{NAME}_Unity_{kind}.png"); im.file_format = 'PNG'; im.save(); print("  saved", im.filepath_raw)
    return im
a = px(col); a[:, 3] = 1; alb = save(a, "Albedo", False)
lum = a[:, :3].mean(1); ms = np.zeros_like(a); ms[:, 3] = np.clip(0.6 + 0.3 * (lum - lum.mean()), 0.35, 0.85)
msi = save(ms, "MetallicSmoothness", True)
n_ = px(nrm); bad = n_[:, 2] < 0.45; n_[bad] = (0.5, 0.5, 1.0, 1.0); n_[:, 3] = 1; nri = save(n_, "Normal", True)
print(f"  normal: flattened {bad.mean() * 100:.2f}% of pixels")
def tex(img, y):
    t_ = N.new("ShaderNodeTexImage"); t_.image = img; t_.location = (-700, y); return t_
Lk.new(tex(alb, 300).outputs["Color"], bs.inputs["Base Color"])
sn = tex(msi, 0); Lk.new(sn.outputs["Color"], bs.inputs["Metallic"])
inv = N.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
Lk.new(sn.outputs["Alpha"], inv.inputs[1]); Lk.new(inv.outputs["Value"], bs.inputs["Roughness"])
nm = N.new("ShaderNodeNormalMap"); Lk.new(tex(nri, -320).outputs["Color"], nm.inputs["Color"]); Lk.new(nm.outputs["Normal"], bs.inputs["Normal"])

# ---- 5. keep only lo, save, check renders
bpy.data.objects.remove(hi)
for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.images):
    for d_ in list(coll):
        if d_.users == 0: coll.remove(d_)
bpy.ops.object.shade_smooth()
bk.use_selected_to_active = False   # don't leave the high-to-low setting in the file
scene.render.engine = 'BLENDER_EEVEE_NEXT'
bpy.ops.wm.save_as_mainfile(filepath=SAVE_TO); print("  saved", SAVE_TO)
if PREV:
    scene.render.engine = 'BLENDER_WORKBENCH'; scene.render.use_border = False
    scene.display.shading.light = 'STUDIO'; scene.display.shading.color_type = 'TEXTURE'
    scene.render.resolution_x, scene.render.resolution_y = 1000, 500
    cd = bpy.data.cameras.new("C"); cd.type = 'ORTHO'; cd.ortho_scale = L * 1.15
    cam = bpy.data.objects.new("C", cd); scene.collection.objects.link(cam); scene.camera = cam
    r90 = math.radians(90)
    for view, loc, rot in (("side", (L * 4, 0, 0), (r90, 0, r90)), ("top", (0, 0, L * 4), (0, 0, r90))):
        cam.location = loc; cam.rotation_euler = rot
        scene.render.filepath = f"{PREV}_{view}.png"; bpy.ops.render.render(write_still=True)
print("PREP DONE")
