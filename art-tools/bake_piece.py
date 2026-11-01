# Bakes a piece made of several separate objects (e.g. the user's piece_cleaning_table.blend: table, wood parts, fish,
# fillets, each with its own materials and its own UV square) into ONE texture set they all share, keeping them as
# separate named objects for the game.
#   - every visible mesh: transforms applied, armature modifiers dropped (a posed copy isn't needed for a static piece)
#   - one new UV layout across all of them ("bake": no overlaps, packed together); the materials still read their own
#     UVs while baking, so painted and Poliigon textures come through as they are
#   - VDW_RENAME="vdw_wood:table_wood,vdw_darkwood:table_darkwood" renames objects (the game swaps meshes named
#     vdw_wood/vdw_darkwood for Valheim's planks; renamed, the baked wood shows)
#   - writes <out>/<key>/<key>_model.fbx (centred, on the ground, real size) + <key>_Unity_{Albedo,MetallicSmoothness,
#     Normal}.png, and <key>_baked.blend. Never touches the source file. New folders only.
#   blender -b piece.blend --factory-startup --python bake_piece.py   env: VDW_OUT, VDW_KEY, VDW_SIZE (2048), VDW_SAMPLES (32)
import bpy, os
import numpy as np

OUT = os.environ["VDW_OUT"]; KEY = os.environ["VDW_KEY"]
SIZE = int(os.environ.get("VDW_SIZE", "2048")); SAMPLES = int(os.environ.get("VDW_SAMPLES", "32"))
RENAME = dict(p.split(":") for p in os.environ.get("VDW_RENAME", "").split(",") if ":" in p)
DIR = os.path.join(OUT, KEY)
if os.path.exists(DIR): raise SystemExit("exists, kept: " + DIR)
os.makedirs(DIR)

sc = bpy.context.scene
if bpy.context.object and bpy.context.object.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
objs = [o for o in sc.objects if o.type == 'MESH' and not o.hide_render and o.visible_get()]
print("PIECE objects", [o.name for o in objs])

# 1. plain static meshes at their real place and size
for o in objs:
    for m in list(o.modifiers):
        if m.type == 'ARMATURE': o.modifiers.remove(m)
    o.parent = None
for o in sc.objects: o.select_set(o in objs)
bpy.context.view_layer.objects.active = objs[0]
for o in objs:
    if o.data.users > 1: o.data = o.data.copy()
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
sc.tool_settings.use_uv_select_sync = True      # UV operators then act on every face, not a saved UV selection

# 1b. parts that keep Valheim's own wood in game (VDW_VANILLA="vdw_wood:wood,vdw_darkwood:wood2": object : its wood
#     material): left out of the bake, given UVs in metres for the planks' tiling. Any other faces on them (the bucket's
#     water) are split off into their own part, which is baked.
import bmesh
VANILLA = dict(p.split(":") for p in os.environ.get("VDW_VANILLA", "").split(",") if ":" in p)
def keep_faces(o, keep):
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if not keep(f)], context='FACES'); bm.to_mesh(o.data); bm.free()
vanilla_parts = []
for o in list(objs):
    if o.name not in VANILLA: continue
    wood = {i for i, m in enumerate(o.data.materials) if m and m.name == VANILLA[o.name]}
    if any(p.material_index not in wood for p in o.data.polygons):
        extra = o.copy(); extra.data = o.data.copy(); sc.collection.objects.link(extra)
        extra.name = o.name.replace("vdw_", "") + "_extra"
        keep_faces(extra, lambda f: f.material_index not in wood)
        objs.append(extra); print("PIECE", o.name, ": non-wood faces split off as", extra.name)
    keep_faces(o, lambda f: f.material_index in wood)
    objs.remove(o); vanilla_parts.append(o)
for o in vanilla_parts:
    for x in sc.objects: x.select_set(x is o)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.reveal(); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.0, area_weight=0.0, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    me_ = o.data; uvd = me_.uv_layers.active.data
    a3 = sum(p.area for p in me_.polygons)
    def uv_area(p):
        u = [uvd[i].uv for i in p.loop_indices]
        return abs(sum(u[k].x * u[(k + 1) % len(u)].y - u[(k + 1) % len(u)].x * u[k].y for k in range(len(u)))) / 2
    k = (a3 / max(sum(uv_area(p) for p in me_.polygons), 1e-9)) ** 0.5
    # VDW_PLANK_ROTATE (degrees, 90/180/270): turns the planks on these parts
    rot = int(os.environ.get("VDW_PLANK_ROTATE", "0")) % 360
    for d in uvd:
        x, y = d.uv.x * k, d.uv.y * k
        if rot == 90: x, y = -y, x
        elif rot == 180: x, y = -x, -y
        elif rot == 270: x, y = y, -x
        d.uv = (x, y)
    print(f"PIECE {o.name}: kept for Valheim's wood, UVs in metres (x{k:.2f}){f', planks turned {rot} degrees' if rot else ''}")

# 2. materials read each object's own UVs explicitly
def uvnode(nt, name):
    n = nt.nodes.new("ShaderNodeUVMap"); n.uv_map = name; return n
done = set()
for o in objs:
    src = o.data.uv_layers[0].name
    for m in o.data.materials:
        if not m or not m.use_nodes or m.name in done: continue
        done.add(m.name); nt = m.node_tree
        for n in list(nt.nodes):
            if n.type == 'TEX_IMAGE' and not n.inputs["Vector"].is_linked: nt.links.new(uvnode(nt, src).outputs["UV"], n.inputs["Vector"])
            if n.type == 'TEX_COORD' and n.outputs["UV"].is_linked:
                u = uvnode(nt, src)
                for l in list(n.outputs["UV"].links): nt.links.new(u.outputs["UV"], l.to_socket)
# every object's first UV layer is called the same, so one node name works for all
for o in objs: o.data.uv_layers[0].name = "UVMap"
for m in bpy.data.materials:
    if m.name in done:
        for n in m.node_tree.nodes:
            if n.type == 'UVMAP': n.uv_map = "UVMap"

# 3. one shared layout. Unwrapping several objects at once packs each into its own square (they overlap), so they're
#    joined into one for the unwrap and the bake, each face remembering its part, and split back by part at export.
names = [o.name for o in objs]
for i, o in enumerate(objs):
    a = o.data.attributes.new("vdw_part", 'INT', 'FACE')
    a.data.foreach_set("value", [i] * len(o.data.polygons))
for o in sc.objects: o.select_set(o in objs)
bpy.context.view_layer.objects.active = objs[0]
bpy.ops.object.join()
obj = bpy.context.view_layer.objects.active; obj.name = KEY + "_baking"; me = obj.data
me.uv_layers["UVMap"].active_render = True
me.uv_layers.active = me.uv_layers.new(name="bake", do_init=True)
hidden = sum(1 for p in me.polygons if p.hide)
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.reveal(); bpy.ops.mesh.select_all(action='SELECT')   # hidden faces too
if hidden: print("PIECE", hidden, "faces were hidden in Edit Mode: unwrapped too")
bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.003, area_weight=0.0, scale_to_bounds=False)
bpy.ops.uv.pack_islands(margin=0.003)
bpy.ops.object.mode_set(mode='OBJECT')
objs = [obj]
print("PIECE shared layout made:", len(me.polygons), "faces, parts", names)

# 4. per material: where colour, metallic and roughness come from
def output(nt): return next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL' and n.is_active_output)
chan = {}
for name in done:
    m = bpy.data.materials[name]; nt = m.node_tree; N = nt.nodes; out = output(nt)
    surf = out.inputs["Surface"].links[0].from_socket if out.inputs["Surface"].is_linked else None
    if surf is not None and surf.node.type == 'GROUP' and "Color Bake" in surf.node.outputs:
        # a Sanctus material (e.g. the stew bowl's wood): its own bake outputs
        g_ = surf.node
        chan[name] = {"Color": g_.outputs["Color Bake"], "Metallic": g_.outputs["Metallic Bake"] if "Metallic Bake" in g_.outputs else 0.0,
                      "Roughness": g_.outputs["Roughness Bake"], "Emission": (0.0, 0.0, 0.0, 1.0), "surface": surf}
        N.new("ShaderNodeEmission").name = "vdw_emit"; N.new("ShaderNodeTexImage").name = "vdw_target"
        print("PIECE", name, ": Sanctus", g_.node_tree.name); continue
    p = surf.node if surf is not None and surf.node.type == 'BSDF_PRINCIPLED' else next((n for n in N if n.type == 'BSDF_PRINCIPLED'), None)
    if p is None: raise SystemExit(f"{name}: no Principled BSDF to bake from")
    def pick(s):
        s = p.inputs[s]
        return s.links[0].from_socket if s.is_linked else (tuple(s.default_value) if hasattr(s.default_value, "__len__") else float(s.default_value))
    chan[name] = {"Color": pick("Base Color"), "Metallic": pick("Metallic"), "Roughness": pick("Roughness"), "surface": p.outputs["BSDF"]}
    es = p.inputs["Emission Strength"].default_value if "Emission Strength" in p.inputs else 0.0
    ec = p.inputs["Emission Color"] if "Emission Color" in p.inputs else None
    chan[name]["Emission"] = (ec.links[0].from_socket if ec is not None and ec.is_linked and es > 0
                              else (tuple(c * es for c in ec.default_value[:3]) + (1.0,) if ec is not None and es > 0 else (0.0, 0.0, 0.0, 1.0)))
    N.new("ShaderNodeEmission").name = "vdw_emit"
    N.new("ShaderNodeTexImage").name = "vdw_target"
print("PIECE materials", sorted(done))

sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = SAMPLES
sc.render.bake.margin = 6; sc.render.bake.use_clear = True
for o in sc.objects: o.select_set(o in objs)
bpy.context.view_layer.objects.active = objs[0]

def set_target(img):
    for name in done:
        N = bpy.data.materials[name].node_tree.nodes; t = N["vdw_target"]; t.image = img
        for n in N: n.select = False
        t.select = True; N.active = t
def bake_channel(ch, nc):
    img = bpy.data.images.new("bake_" + ch, SIZE, SIZE, alpha=False)
    if nc: img.colorspace_settings.name = 'Non-Color'
    for name in done:
        nt = bpy.data.materials[name].node_tree; L = nt.links; em = nt.nodes["vdw_emit"]
        for l in list(em.inputs["Color"].links): L.remove(l)
        v = chan[name][ch]
        if isinstance(v, bpy.types.NodeSocket): L.new(v, em.inputs["Color"])
        else: em.inputs["Color"].default_value = v if isinstance(v, tuple) else (v, v, v, 1.0)
        L.new(em.outputs["Emission"], output(nt).inputs["Surface"])
    set_target(img); bpy.ops.object.bake(type='EMIT'); print("PIECE baked", ch); return img
def px(img):
    a = np.empty(SIZE * SIZE * 4, np.float32); img.pixels.foreach_get(a); return a.reshape(SIZE, SIZE, 4)
def save(arr, name, nc):
    im = bpy.data.images.new(name, SIZE, SIZE, alpha=True)
    if nc: im.colorspace_settings.name = 'Non-Color'
    im.pixels.foreach_set(np.ascontiguousarray(arr, np.float32).ravel()); im.filepath_raw = os.path.join(DIR, name); im.file_format = 'PNG'; im.save(); print("  saved", name)

col = px(bake_channel("Color", False)); met = px(bake_channel("Metallic", True)); rough = px(bake_channel("Roughness", True))
glows = any(isinstance(chan[n]["Emission"], bpy.types.NodeSocket) or max(chan[n]["Emission"][:3]) > 0 for n in done)
emi = px(bake_channel("Emission", False)) if glows else None
for name in done:
    nt = bpy.data.materials[name].node_tree; nt.links.new(chan[name]["surface"], output(nt).inputs["Surface"])
nimg = bpy.data.images.new("bake_normal", SIZE, SIZE, alpha=False); nimg.colorspace_settings.name = 'Non-Color'
set_target(nimg); sc.render.bake.normal_space = 'TANGENT'; bpy.ops.object.bake(type='NORMAL'); nrm = px(nimg); print("PIECE baked Normal")

col[..., 3] = 1.0; save(col, KEY + "_Unity_Albedo.png", False)
ms = np.zeros_like(col); ms[..., 0] = ms[..., 1] = ms[..., 2] = met[..., 0]; ms[..., 3] = 1.0 - rough[..., 0]
save(ms, KEY + "_Unity_MetallicSmoothness.png", True)
nrm[..., 3] = 1.0; save(nrm, KEY + "_Unity_Normal.png", True)
if emi is not None and emi[..., :3].max() > 0.01: emi[..., 3] = 1.0; save(emi, KEY + "_Unity_Emission.png", False)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, KEY + "_baked.blend"))

# 5. the game model: the shared layout as each object's only UVs, one material, centred and standing on the origin
pts = np.concatenate([np.array([v.co[:] for v in o.data.vertices]) for o in objs + vanilla_parts]); lo, hi = pts.min(0), pts.max(0)
shift = np.array([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]])
plain = bpy.data.materials.new(KEY)
me.uv_layers.remove(me.uv_layers["UVMap"]); me.uv_layers["bake"].name = "UVMap"
for v in me.vertices: v.co = (v.co[0] + shift[0], v.co[1] + shift[1], v.co[2] + shift[2])
me.materials.clear(); me.materials.append(plain)
for p in me.polygons: p.material_index = 0
# split back into the named parts
import bmesh
parts = []
for i, name in enumerate(names):
    part = obj.copy(); part.data = me.copy(); sc.collection.objects.link(part)
    bm = bmesh.new(); bm.from_mesh(part.data); lay = bm.faces.layers.int["vdw_part"]
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f[lay] != i], context='FACES')
    bm.to_mesh(part.data); bm.free()
    part.data.attributes.remove(part.data.attributes["vdw_part"])
    new = RENAME.get(name, name)
    if new != name: print("PIECE renamed", name, "->", new)
    for coll in (bpy.data.objects, bpy.data.meshes):           # the joined originals still hold the names
        if coll.get(new) is not None: coll[new].name = new + "_joined"
    part.name = new; part.data.name = new
    part.modifiers.new("tri", 'TRIANGULATE')
    parts.append(part)
bpy.data.objects.remove(obj)
for o in vanilla_parts:                       # Valheim's wood goes on these in game: same place, plain material
    for v in o.data.vertices: v.co = (v.co[0] + shift[0], v.co[1] + shift[1], v.co[2] + shift[2])
    o.data.materials.clear(); o.data.materials.append(plain)
    o.modifiers.new("tri", 'TRIANGULATE')
objs = parts + vanilla_parts
for o in sc.objects: o.select_set(o in objs)
bpy.ops.export_scene.fbx(filepath=os.path.join(DIR, KEY + "_model.fbx"), use_selection=True, object_types={'MESH'},
                         global_scale=1.0, apply_unit_scale=True, apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y',
                         bake_space_transform=False, mesh_smooth_type='FACE', use_mesh_modifiers=True, path_mode='COPY', embed_textures=False)
print("PIECE exported", KEY, [o.name for o in objs], "size", tuple(round(float(x), 3) for x in (hi - lo)))
print("===== END =====")
