# Puts the user's own fillet models where build_cleaning_table.py (run with VDW_FILLET_MARKERS=1) recorded its fillets,
# then saves <NAME>_composed.blend for bake_food.py (dishes) or bake_piece.py (feasts) to bake into one texture set.
#   - the piece's own procedural atlas goes on a material (albedo, metal/smoothness, normal, emission) so it bakes as it is
#   - salmon spots (salmon, curedsalmon, grilledsalmon) take the salmon fillet: grilled ones with its own painted texture
#     (browning and grill marks), raw and cured ones with the clean texture; whitefish spots take the white fish fillet
#   - each copy is laid along the old fillet (its narrow end toward +X), sized to its length, width and thickness, turned
#     to its angle and stood on its foot; feast fillets keep their 1.45x growth
#   blender -b --factory-startup --python swap_fillets.py
#   env: VDW_OUT (the build folder), VDW_NAME, VDW_SALMON (fbx), VDW_SALMON_RAW (png), VDW_WHITE (fbx)
import bpy, os, json, math
import numpy as np
from mathutils import Vector, Matrix

OUT = os.environ["VDW_OUT"]; NAME = os.environ["VDW_NAME"]
BF = os.path.join(OUT, "Blender Files"); TX = os.path.join(OUT, "Textures")
bpy.ops.wm.open_mainfile(filepath=os.path.join(BF, NAME + ".blend"))
markers = json.load(open(os.path.join(BF, NAME + "_fillets.json")))
sc = bpy.context.scene

# 1. the atlas as a material on the piece's own meshes (not the wood parts, which get Valheim's planks in game)
def img(kind, nc):
    p = os.path.join(TX, f"{NAME}_Unity_{kind}.png")
    if not os.path.exists(p): return None
    i = bpy.data.images.load(p)
    if nc: i.colorspace_settings.name = 'Non-Color'
    return i
atlas = bpy.data.materials.new(NAME + "_atlas"); atlas.use_nodes = True; nt = atlas.node_tree; N, L = nt.nodes, nt.links
bsdf = N["Principled BSDF"]
def tex(i):
    t = N.new("ShaderNodeTexImage"); t.image = i; return t
a = tex(img("Albedo", False)); L.new(a.outputs["Color"], bsdf.inputs["Base Color"])
ms = img("MetallicSmoothness", True)
if ms:
    t = tex(ms); L.new(t.outputs["Color"], bsdf.inputs["Metallic"])
    inv = N.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
    L.new(t.outputs["Alpha"], inv.inputs[1]); L.new(inv.outputs[0], bsdf.inputs["Roughness"])
nm = img("Normal", True)
if nm:
    t = tex(nm); n = N.new("ShaderNodeNormalMap"); L.new(t.outputs["Color"], n.inputs["Color"]); L.new(n.outputs["Normal"], bsdf.inputs["Normal"])
em = img("Emission", False)
if em is not None:
    px = np.empty(em.size[0] * em.size[1] * 4, np.float32); em.pixels.foreach_get(px)
    if px.reshape(-1, 4)[:, :3].max() > 0.01:
        t = tex(em); L.new(t.outputs["Color"], bsdf.inputs["Emission Color"]); bsdf.inputs["Emission Strength"].default_value = 1.0
        print("SWAP atlas has emission")
parts = {}
# VDW_WOOD="other.blend|material": the wood (the atlas's wood and darkwood tiles, and any vdw_wood part) takes that
# material instead - e.g. the Sanctus wood of the stew bowl and grilled fillet board. The planks parts are renamed
# "board_wood" so the game doesn't swap them for Valheim's planks.
wood = None
if os.environ.get("VDW_WOOD"):
    path_, name_ = os.environ["VDW_WOOD"].rsplit("|", 1)
    with bpy.data.libraries.load(path_) as (src, dst): dst.materials = [name_]
    wood = dst.materials[0]
WOOD_TILES = {(0, 0), (1, 0)}           # build_cleaning_table.py's tiles 0 and 1 (8 x 8): wood, darkwood
for o in list(sc.objects):
    if o.type != 'MESH': continue
    if o.name.startswith(("vdw_wood", "vdw_darkwood")):
        if wood is None: continue
        o.data.materials.clear(); o.data.materials.append(wood); o.name = "board_wood" if o.name.startswith("vdw_wood") else "board_darkwood"
        parts[o.name] = o; print("SWAP", o.name, ": Sanctus wood (no planks)"); continue
    o.data.materials.clear(); o.data.materials.append(atlas); parts[o.name] = o
    if wood is not None and len(o.data.polygons):
        o.data.materials.append(wood); uvd = o.data.uv_layers.active.data; n_ = 0
        for p in o.data.polygons:
            u = sum(uvd[i].uv.x for i in p.loop_indices) / p.loop_total; v = sum(uvd[i].uv.y for i in p.loop_indices) / p.loop_total
            if (int(u * 8), int(v * 8)) in WOOD_TILES: p.material_index = 1; n_ += 1
        if n_: print(f"SWAP {o.name}: {n_} wood faces take the Sanctus wood")

# 2. the user's fillets, laid out the same way as the old ones: long along X, narrow end at +X, foot at z = 0
def load_fillet(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == 'MESH']
    for o in sc.objects: o.select_set(o in meshes)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1: bpy.ops.object.join()
    f = bpy.context.view_layer.objects.active
    for o in new:
        if o is not f and o.name in bpy.data.objects: bpy.data.objects.remove(o)
    f.parent = None
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    co = np.array([v.co[:] for v in f.data.vertices])
    xy = co[:, :2] - co[:, :2].mean(0)
    w, v = np.linalg.eigh(xy.T @ xy); ax = v[:, np.argmax(w)]                   # its long direction, flat on the ground
    ang = math.atan2(ax[1], ax[0])
    f.data.transform(Matrix.Rotation(-ang, 4, 'Z'))
    co = np.array([v.co[:] for v in f.data.vertices]); lo, hi = co.min(0), co.max(0); mid = (lo + hi) / 2
    f.data.transform(Matrix.Translation(Vector((-mid[0], -mid[1], -lo[2]))))
    co = np.array([v.co[:] for v in f.data.vertices])
    half = lambda s: np.ptp(co[s, 1]) if s.any() else 0
    if half(co[:, 0] > 0.2 * co[:, 0].max()) > half(co[:, 0] < 0.2 * co[:, 0].min()):   # wider at +X: turn it round
        f.data.transform(Matrix.Rotation(math.pi, 4, 'Z'))
    co = np.array([v.co[:] for v in f.data.vertices]); size = co.max(0) - co.min(0)
    f.hide_render = True; f.hide_set(True)
    print(f"SWAP fillet {os.path.basename(path)}: {size.round(3)} m")
    return f, size
salmon, s_size = load_fillet(os.environ["VDW_SALMON"])
white, w_size = load_fillet(os.environ["VDW_WHITE"])
painted = salmon.data.materials[0]
raw = painted.copy(); raw.name = "salmon_raw"
rimg = bpy.data.images.load(os.environ["VDW_SALMON_RAW"])
for nd in raw.node_tree.nodes:
    if nd.type == 'TEX_IMAGE' and nd.outputs["Color"].is_linked and any(l.to_socket.name == "Base Color" for l in nd.outputs["Color"].links): nd.image = rimg

# cured salmon: the clean texture, darker and redder (VDW_CURED_TINT "r,g,b" multiplies it), like the cured slices
cured = raw.copy(); cured.name = "salmon_cured"
tint = tuple(float(x) for x in os.environ.get("VDW_CURED_TINT", "0.72,0.30,0.26").split(",")) + (1.0,)
cn, cl = cured.node_tree.nodes, cured.node_tree.links
cb = next(nd for nd in cn if nd.type == 'BSDF_PRINCIPLED')
if cb.inputs["Base Color"].is_linked:
    srcs = cb.inputs["Base Color"].links[0].from_socket
    mul = cn.new("ShaderNodeMix"); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs["Factor"].default_value = 1.0
    cl.new(srcs, mul.inputs["A"]); mul.inputs["B"].default_value = tint; cl.new(mul.outputs["Result"], cb.inputs["Base Color"])
    cb.inputs["Roughness"].default_value = 0.25                                      # cured: a little glossier
print("SWAP cured salmon tint", tint[:3])

# 3. a copy at every marker, joined into the part it belongs to
placed = []
for k, mk in enumerate(markers):
    src, size = (white, w_size) if mk["mat"] == "whitefish" else (salmon, s_size)
    g = mk["grow"]
    o = src.copy(); o.data = src.data.copy(); sc.collection.objects.link(o); o.hide_render = False; o.hide_set(False)
    if src is salmon:
        o.data.materials.clear()
        o.data.materials.append(painted if mk["mat"] == "grilledsalmon" else cured if mk["mat"] == "curedsalmon" else raw)
    sx, sy, sz = mk["L"] * g / size[0], mk["W"] * g / size[1], mk["T"] * g * 1.3 / size[2]
    c = mk["c"]
    o.matrix_world = (Matrix.Translation(Vector((c[0], c[1], c[2] - mk["T"] * g / 2))) @ Matrix.Rotation(math.radians(mk["rot"]), 4, 'Z')
                      @ Matrix.Diagonal((sx, sy, sz, 1.0)))
    part = parts.get(mk["part"])
    if part is None: raise SystemExit(f"marker {k}: no part {mk['part']}")
    placed.append((o, part))
    print(f"SWAP {mk['mat']} -> {mk['part']} at {np.round(c, 3)}, {mk['L'] * g:.3f} x {mk['W'] * g:.3f} m")

# VDW_SNAP=1: toppings that sat on the old fillet (rime crystals, peppercorns) float over the new one; each loose bit of
# the part above a fillet drops straight down onto the fillet's real surface (found by a ray), sitting a hair into it
if os.environ.get("VDW_SNAP", "") == "1":
    import bmesh
    from mathutils.bvhtree import BVHTree
    for o, part in placed:
        dg = bpy.context.evaluated_depsgraph_get(); bmf = bmesh.new(); bmf.from_object(o, dg); bmf.transform(o.matrix_world)
        tree = BVHTree.FromBMesh(bmf); fx = [v.co for v in bmf.verts]
        flo = Vector((min(p.x for p in fx), min(p.y for p in fx), min(p.z for p in fx))); fhi = Vector((max(p.x for p in fx), max(p.y for p in fx), max(p.z for p in fx)))
        bmp = bmesh.new(); bmp.from_mesh(part.data); bmp.verts.ensure_lookup_table()
        seen = set(); moved = 0
        for v0 in bmp.verts:
            if v0.index in seen: continue
            st = [v0]; isl = []; seen.add(v0.index)
            while st:
                x = st.pop(); isl.append(x)
                for e in x.link_edges:
                    w_ = e.other_vert(x)
                    if w_.index not in seen: seen.add(w_.index); st.append(w_)
            cx = sum(v.co.x for v in isl) / len(isl); cy = sum(v.co.y for v in isl) / len(isl); lo_z = min(v.co.z for v in isl)
            size_ = max(max(v.co.x for v in isl) - min(v.co.x for v in isl), max(v.co.y for v in isl) - min(v.co.y for v in isl))
            if not (flo.x <= cx <= fhi.x and flo.y <= cy <= fhi.y) or size_ > 0.5 * (fhi.x - flo.x): continue
            if lo_z < flo.z + 0.5 * (fhi.z - flo.z): continue                      # under or beside it: not a topping
            hit = tree.ray_cast(Vector((cx, cy, fhi.z + 0.1)), Vector((0, 0, -1)))
            if hit[0] is None: continue
            dz = hit[0].z - lo_z - 0.0015
            for v in isl: v.co.z += dz
            moved += 1
        bmp.to_mesh(part.data); bmp.free(); bmf.free()
        if moved: print(f"SWAP {moved} topping(s) settled onto the fillet")
for o, part in placed:
    for x in sc.objects: x.select_set(x in (o, part))
    bpy.context.view_layer.objects.active = part
    bpy.ops.object.join()
bpy.data.objects.remove(salmon); bpy.data.objects.remove(white)

# VDW_QUADS=1: triangles joined back into quads on every mesh (the export triangulates again for the game)
if os.environ.get("VDW_QUADS", "") == "1":
    for o in [o for o in sc.objects if o.type == 'MESH' and len(o.data.polygons)]:
        for x in sc.objects: x.select_set(x is o)
        bpy.context.view_layer.objects.active = o
        n0 = len(o.data.polygons)
        bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.tris_convert_to_quads(face_threshold=math.radians(40), shape_threshold=math.radians(40), uvs=True)
        bpy.ops.object.mode_set(mode='OBJECT')
        print(f"SWAP {o.name}: {n0} -> {len(o.data.polygons)} faces (tris to quads)")
for o in sc.objects:
    if o.type == 'MESH' and len(o.data.polygons) == 0: print("SWAP empty part kept:", o.name)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(BF, NAME + "_composed.blend"))
print("SWAP saved", NAME + "_composed.blend")
