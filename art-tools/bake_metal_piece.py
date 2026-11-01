# Textures a piece whose painted part should be worn metal, on the user's own UVs, from the add-ons: Sanctus worn metal,
# then Grungit edge wear, scratches and dirt (as the coolers' metal). Parts named vdw_wood / vdw_darkwood keep Valheim's
# planks in game: their own UVs are kept and scaled to metres for the planks' tiling. E.g. piece_cleaning_ext1.blend
# (the Filleting Knife Rack): the knives part is metal, the rack is planks.
#   blender -b piece.blend --factory-startup --python bake_metal_piece.py
#   env: VDW_OUT (new folder), VDW_KEY (the painted object = the model key), VDW_SIZE (1024), VDW_SAMPLES (32),
#        VDW_METAL_COLOR ("0.56,0.57,0.6"), VDW_WEAR (0.2), VDW_DIRT (0.2), VDW_PLANK_ROTATE (0/90/180/270)
# Writes <out>/<key>/<key>_model.fbx (centred, on the ground, real size) + <key>_Unity_{Albedo,MetallicSmoothness,Normal}.png
import bpy, os, math
import numpy as np

OUT = os.environ["VDW_OUT"]; KEY = os.environ["VDW_KEY"]
SIZE = int(os.environ.get("VDW_SIZE", "1024")); SAMPLES = int(os.environ.get("VDW_SAMPLES", "32"))
COLOR = tuple(float(x) for x in os.environ.get("VDW_METAL_COLOR", "0.56,0.57,0.6").split(",")) + (1.0,)
SANCTUS = os.path.join(os.environ["APPDATA"], r"Blender Foundation\Blender\5.2\extensions\user_default\sanctus_library_starter\lib\materials")
GRUNGIT = os.path.join(os.environ["APPDATA"], r"Blender Foundation\Blender\5.2\scripts\addons\Grungit\grungit_data\Materials.blend")
DIR = os.path.join(OUT, KEY)
if os.path.exists(DIR): raise SystemExit("exists, kept: " + DIR)
os.makedirs(DIR)

sc = bpy.context.scene
if bpy.context.object and bpy.context.object.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')   # saved in Edit Mode
objs = [o for o in sc.objects if o.type == 'MESH' and not o.hide_render and o.visible_get()]
for o in objs:
    for m in list(o.modifiers):
        if m.type == 'ARMATURE': o.modifiers.remove(m)
    o.parent = None
    if o.data.users > 1: o.data = o.data.copy()
for o in sc.objects: o.select_set(o in objs)
bpy.context.view_layer.objects.active = objs[0]
# VDW_SCALE: the whole piece bigger or smaller (about the world origin), before anything is measured or baked
SCALE = float(os.environ.get("VDW_SCALE", "1"))
if SCALE != 1.0:
    for o in objs:
        o.location = o.location * SCALE; o.scale = o.scale * SCALE
    bpy.context.view_layer.update()
    print(f"METAL scaled x{SCALE}")
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
painted = bpy.data.objects[KEY]; me = painted.data
print("METAL parts", [o.name for o in objs], "painted:", KEY)

# stray scraps: tiny loose pieces (under 12 vertices) far from everything else, left over from editing - they'd
# stretch the model's size and push it off centre in game. Only this baked copy is changed.
import bmesh
for o in objs:
    bm = bmesh.new(); bm.from_mesh(o.data); bm.verts.ensure_lookup_table()
    seen = set(); parts = []
    for v in bm.verts:
        if v.index in seen: continue
        st = [v]; idx = []; seen.add(v.index)
        while st:
            x = st.pop(); idx.append(x.index)
            for e in x.link_edges:
                w = e.other_vert(x)
                if w.index not in seen: seen.add(w.index); st.append(w)
        parts.append(idx)
    big = [bm.verts[i].co for p in parts if len(p) >= 12 for i in p]
    if not big: bm.free(); continue
    lo_ = np.array([min(c[k] for c in big) for k in range(3)]); hi_ = np.array([max(c[k] for c in big) for k in range(3)])
    drop = []
    for p in parts:
        if len(p) >= 12: continue
        c = np.array(bm.verts[p[0]].co[:])
        if np.max(np.maximum(lo_ - c, c - hi_)) > 0.25: drop += [bm.verts[i] for i in p]
    if drop:
        print(f"METAL {o.name}: dropped {len(drop)} stray vertices far from the model")
        bmesh.ops.delete(bm, geom=drop, context='VERTS'); bm.to_mesh(o.data)
    bm.free()

# 1. Valheim's planks on the wood parts: their own UVs, scaled to metres (and turned if asked)
rot = int(os.environ.get("VDW_PLANK_ROTATE", "0")) % 360
for o in objs:
    if not o.name.startswith(("vdw_wood", "vdw_darkwood")): continue
    d = o.data; uvd = d.uv_layers.active.data
    def uv_area(p):
        u = [uvd[i].uv for i in p.loop_indices]
        return abs(sum(u[k].x * u[(k + 1) % len(u)].y - u[(k + 1) % len(u)].x * u[k].y for k in range(len(u)))) / 2
    k = (sum(p.area for p in d.polygons) / max(sum(uv_area(p) for p in d.polygons), 1e-9)) ** 0.5
    for t in uvd:
        x, y = t.uv.x * k, t.uv.y * k
        if rot == 90: x, y = -y, x
        elif rot == 180: x, y = -x, -y
        elif rot == 270: x, y = y, -x
        t.uv = (x, y)
    print(f"METAL {o.name}: Valheim's planks, its UVs scaled to metres (x{k:.2f})")

# 2. the painted part: one worn-metal material from the add-ons, on its own UVs
co = np.array([v.co[:] for v in me.vertices]); LENGTH = float((co.max(0) - co.min(0)).max())
with bpy.data.libraries.load(os.path.join(SANCTUS, r"Metals Worn\basic_worn_metal.blend")) as (src, dst):
    dst.materials = ["basic_worn_metal_01"]
mat = dst.materials[0].copy(); mat.name = KEY + "_metal"
with bpy.data.libraries.load(GRUNGIT) as (src, dst): dst.node_groups = ["Grungit v1.9.1", "Grungit Dirt v1.9.1", "Baker v1.8.3"]
G_MAIN, G_DIRT, G_BAKER = dst.node_groups
mask = bpy.data.images.new(KEY + "_mask", SIZE, SIZE, alpha=False); mask.colorspace_settings.name = 'Non-Color'
nt = mat.node_tree; N, L = nt.nodes, nt.links
grp = next(n for n in N if n.type == 'GROUP' and n.node_tree and "Color Bake" in n.outputs)
if "Color" in grp.inputs: grp.inputs["Color"].default_value = COLOR
mtex = N.new("ShaderNodeTexImage"); mtex.image = mask
g = N.new("ShaderNodeGroup"); g.node_tree = G_MAIN
L.new(mtex.outputs["Color"], g.inputs["Grungit Mask"])
L.new(grp.outputs["Color Bake"], g.inputs["Base Color 1"]); L.new(grp.outputs["Roughness Bake"], g.inputs["Roughness 1"])
if "Metallic Bake" in grp.outputs: L.new(grp.outputs["Metallic Bake"], g.inputs["Metallic 1"])
else: g.inputs["Metallic 1"].default_value = 1.0
worn = tuple(min(1.0, c * 1.35) for c in COLOR[:3]) + (1.0,)
g.inputs["Base Color 2"].default_value = worn; g.inputs["Metallic 2"].default_value = 1.0; g.inputs["Roughness 2"].default_value = 0.3
g.inputs["Transition Color"].default_value = worn; g.inputs["Transition Amount"].default_value = 0.0
g.inputs["Global Control"].default_value = float(os.environ.get("VDW_WEAR", "0.2")); g.inputs["Edge Wear Spread"].default_value = 0.5
g.inputs["Scratch Amount"].default_value = 0.6; g.inputs["Cracks Amount"].default_value = 0.0; g.inputs["Grunge Amount"].default_value = 0.25
g.inputs["Scale"].default_value = 1.0 / max(LENGTH, 0.01)
dn = N.new("ShaderNodeGroup"); dn.node_tree = G_DIRT
L.new(mtex.outputs["Color"], dn.inputs["Grungit Mask"])
for a in ("Base Color", "Metallic", "Roughness", "Normal"):
    if a in g.outputs and a in dn.inputs: L.new(g.outputs[a], dn.inputs[a])
dn.inputs["Dirt Base Color"].default_value = (0.16, 0.11, 0.07, 1)
dn.inputs["Overall Amount"].default_value = float(os.environ.get("VDW_DIRT", "0.2")); dn.inputs["AO"].default_value = 0.3
bsdf = N.new("ShaderNodeBsdfPrincipled")
for a, b in (("Color", "Base Color"), ("Metallic", "Metallic"), ("Roughness", "Roughness"), ("Normal", "Normal")): L.new(dn.outputs[a], bsdf.inputs[b])
out = next(n for n in N if n.type == 'OUTPUT_MATERIAL' and n.is_active_output)
L.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
# VDW_METAL_MATS="a,b": only these material slots become metal; the others are baked as they are (a Principled
# material's own colour/roughness, or a shader group's "Color" input, e.g. a water shader). Unset: the whole part.
METAL_MATS = [s for s in os.environ.get("VDW_METAL_MATS", "").split(",") if s]
if METAL_MATS:
    for i, m in enumerate(me.materials):
        if m and m.name in METAL_MATS: me.materials[i] = mat
else:
    me.materials.clear(); me.materials.append(mat)
    for p in me.polygons: p.material_index = 0
print("METAL material: Sanctus basic_worn_metal_01", COLOR[:3], "+ Grungit", f"on {METAL_MATS}" if METAL_MATS else "on the whole part")

# where every material's colour, metallic, roughness come from, and an emission + target node in each
def outnode(t): return next(n for n in t.nodes if n.type == 'OUTPUT_MATERIAL' and n.is_active_output)
chan = {}
for m in {m for m in me.materials if m}:
    t = m.node_tree
    if m is mat:
        chan[m.name] = {"Color": dn.outputs["Color"], "Metallic": dn.outputs["Metallic"], "Roughness": dn.outputs["Roughness"]}
    else:
        o = outnode(t); s = o.inputs["Surface"].links[0].from_socket if o.inputs["Surface"].is_linked else None
        p = s.node if s is not None and s.node.type == 'BSDF_PRINCIPLED' else next((n for n in t.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if p is not None:
            def pick(name):
                x = p.inputs[name]
                return x.links[0].from_socket if x.is_linked else (tuple(x.default_value) if hasattr(x.default_value, "__len__") else float(x.default_value))
            chan[m.name] = {"Color": pick("Base Color"), "Metallic": pick("Metallic"), "Roughness": pick("Roughness")}
        else:   # a shader group (water): its colour, wet and glossy
            gnode = s.node if s is not None else None
            c = tuple(gnode.inputs["Color"].default_value) if gnode is not None and "Color" in gnode.inputs else (0.3, 0.3, 0.3, 1)
            chan[m.name] = {"Color": c, "Metallic": 0.0, "Roughness": 0.08}
        print("METAL", m.name, ": baked as set")
    t.nodes.new("ShaderNodeEmission").name = "vdw_emit"; t.nodes.new("ShaderNodeTexImage").name = "vdw_target"
    chan[m.name]["surface"] = outnode(t).inputs["Surface"].links[0].from_socket if m is not mat else bsdf.outputs["BSDF"]
mats_all = [bpy.data.materials[n] for n in chan]

sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = SAMPLES
sc.render.bake.margin = 8; sc.render.bake.use_clear = True
for o in sc.objects: o.select_set(o is painted)
bpy.context.view_layer.objects.active = painted
def px(img):
    a = np.empty(SIZE * SIZE * 4, np.float32); img.pixels.foreach_get(a); return a.reshape(SIZE, SIZE, 4)
def save(arr, name, nc):
    im = bpy.data.images.new(name, SIZE, SIZE, alpha=True)
    if nc: im.colorspace_settings.name = 'Non-Color'
    im.pixels.foreach_set(np.ascontiguousarray(arr, np.float32).ravel()); im.filepath_raw = os.path.join(DIR, name); im.file_format = 'PNG'; im.save(); print("  saved", name)
def target_to(img):
    for m in mats_all:
        T = m.node_tree.nodes; tg = T["vdw_target"]; tg.image = img
        for n in T: n.select = False
        tg.select = True; T.active = tg

# the Grungit mask from its Baker
mm = bpy.data.materials.new("vdw_maskbake"); mm.use_nodes = True; mn = mm.node_tree.nodes
for n in list(mn):
    if n.type != 'OUTPUT_MATERIAL': mn.remove(n)
bk = mn.new("ShaderNodeGroup"); bk.node_tree = G_BAKER; bk.inputs["Scale"].default_value = 0.5 * LENGTH
mm.node_tree.links.new(bk.outputs["Output"], next(n for n in mn if n.type == 'OUTPUT_MATERIAL').inputs["Surface"])
mt = mn.new("ShaderNodeTexImage"); mt.image = mask; mn.active = mt
target_to(bpy.data.images.new("vdw_throwaway", 8, 8))     # nothing else's selected image gets cleared by the bake
saved = [p.material_index for p in me.polygons]
me.materials.append(mm); k_ = len(me.materials) - 1
for p in me.polygons: p.material_index = k_
bpy.ops.object.bake(type='EMIT'); print("METAL Grungit mask baked")
for p, i in zip(me.polygons, saved): p.material_index = i
me.materials.pop(index=k_)

def bake(ch, nc):
    img = bpy.data.images.new("bake_" + ch, SIZE, SIZE, alpha=False)
    if nc: img.colorspace_settings.name = 'Non-Color'
    for m in mats_all:
        t = m.node_tree; e = t.nodes["vdw_emit"]
        for l in list(e.inputs["Color"].links): t.links.remove(l)
        v = chan[m.name][ch]
        if isinstance(v, bpy.types.NodeSocket): t.links.new(v, e.inputs["Color"])
        else: e.inputs["Color"].default_value = v if isinstance(v, tuple) else (v, v, v, 1.0)
        t.links.new(e.outputs["Emission"], outnode(t).inputs["Surface"])
    target_to(img); bpy.ops.object.bake(type='EMIT'); print("METAL baked", ch); return px(img)
col = bake("Color", False); met = bake("Metallic", True); rough = bake("Roughness", True)
for m in mats_all: m.node_tree.links.new(chan[m.name]["surface"], outnode(m.node_tree).inputs["Surface"])
nimg = bpy.data.images.new("bake_normal", SIZE, SIZE, alpha=False); nimg.colorspace_settings.name = 'Non-Color'
target_to(nimg); sc.render.bake.normal_space = 'TANGENT'; bpy.ops.object.bake(type='NORMAL'); nrm = px(nimg); print("METAL baked Normal")
col[..., 3] = 1.0; save(col, KEY + "_Unity_Albedo.png", False)
ms = np.zeros_like(col); ms[..., 0] = ms[..., 1] = ms[..., 2] = met[..., 0]; ms[..., 3] = 1.0 - rough[..., 0]
save(ms, KEY + "_Unity_MetallicSmoothness.png", True)
nrm[..., 3] = 1.0; save(nrm, KEY + "_Unity_Normal.png", True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, KEY + "_baked.blend"))

# 3. the game model: centred, on the ground, one plain material
pts = np.concatenate([np.array([v.co[:] for v in o.data.vertices]) for o in objs]); lo, hi = pts.min(0), pts.max(0)
shift = np.array([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]])
plain = bpy.data.materials.new(KEY)
for o in objs:
    for v in o.data.vertices: v.co = (v.co[0] + shift[0], v.co[1] + shift[1], v.co[2] + shift[2])
    o.data.materials.clear(); o.data.materials.append(plain)
    for p in o.data.polygons: p.material_index = 0
    o.modifiers.new("tri", 'TRIANGULATE')
for o in sc.objects: o.select_set(o in objs)
bpy.ops.export_scene.fbx(filepath=os.path.join(DIR, KEY + "_model.fbx"), use_selection=True, object_types={'MESH'},
                         global_scale=1.0, apply_unit_scale=True, apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y',
                         bake_space_transform=False, mesh_smooth_type='FACE', use_mesh_modifiers=True, path_mode='COPY', embed_textures=False)
print("METAL exported", KEY, [o.name for o in objs], "size", tuple(round(float(x), 3) for x in (hi - lo)))
print("===== END =====")
