# Bakes a tackle box tier from the user's add-ons: Sanctus Library materials (wood, worn metal, leather) worn by
# Grungit (edge wear, scratches, cracks, then dirt in the cavities), into Unity maps on the box's own UVs.
#   1. the box (rig_tacklebox.py output) is scaled to VDW_LENGTH m like paint_tacklebox.py, and split into wood (lid,
#      base, the compartment dividers), metal (the latch on the front) and leather (the handle)
#   2. Grungit's Baker bakes its mask (AO / edges / cavities) to an image, as the add-on does
#   3. each part: Sanctus material -> Grungit (worn edges, scratches) -> Grungit Dirt -> baked to colour, metallic,
#      roughness (emission bakes, so lighting doesn't get baked in) and a tangent normal map
# Writes <out>/Textures/tacklebox_<tier>/tacklebox_<tier>_Unity_{Albedo,MetallicSmoothness,Normal}.png, the mask, and
# <out>/tacklebox_<tier>_baked.blend. Never overwrites a map unless VDW_REDO=1.
#   blender -b tacklebox_rigged.blend --factory-startup --python bake_tacklebox.py
#   env: VDW_OUT, VDW_TIER (t1), VDW_LENGTH (0.6), VDW_SIZE (1024), VDW_SAMPLES (64), VDW_REDO
import bpy, os, math
import numpy as np
from mathutils import Vector

OUT = os.environ["VDW_OUT"]; TIER = os.environ.get("VDW_TIER", "t1"); LENGTH = float(os.environ.get("VDW_LENGTH", "0.6"))
SIZE = int(os.environ.get("VDW_SIZE", "1024")); SAMPLES = int(os.environ.get("VDW_SAMPLES", "64")); REDO = os.environ.get("VDW_REDO") == "1"
SANCTUS = os.path.join(os.environ["APPDATA"], r"Blender Foundation\Blender\5.2\extensions\user_default\sanctus_library_starter\lib\materials")
GRUNGIT = os.path.join(os.environ["APPDATA"], r"Blender Foundation\Blender\5.2\scripts\addons\Grungit\grungit_data\Materials.blend")
TEXDIR = os.path.join(OUT, "Textures", f"tacklebox_{TIER}"); os.makedirs(TEXDIR, exist_ok=True)

# per tier: (Sanctus file, material, inputs) for wood / metal / handle, and the worn colours Grungit wears them to
TIERS = {
    "t1": dict(
        wood=(r"Stylized\stylized_planks.blend", "stylized_planks_04", {"Color1": (0.41, 0.27, 0.14, 1), "Color2": (0.25, 0.15, 0.08, 1), "Nails": 0.0, "Plank Height": 0.12, "Border Damage": 0.25, "Scale": 4.0}),
        wood_worn=(0.47, 0.31, 0.17, 1),
        metal=(r"Metals Worn\basic_worn_metal.blend", "basic_worn_metal_01", {"Color": (0.20, 0.19, 0.18, 1)}),
        metal_worn=(0.55, 0.55, 0.56, 1),
        handle=(r"Fabrics\pu_leather.blend", "pu_leather", {"Base Color": (0.22, 0.12, 0.06, 1), "Roughness": 0.55}),
        handle_worn=(0.35, 0.22, 0.12, 1)),
    "t2": dict(   # Iron-Bound: dark stained wood, iron straps and rim
        wood=(r"Stylized\stylized_planks.blend", "stylized_planks_04", {"Color1": (0.30, 0.19, 0.11, 1), "Color2": (0.17, 0.10, 0.05, 1), "Nails": 0.0, "Plank Height": 0.12, "Border Damage": 0.3, "Scale": 4.0}),
        wood_worn=(0.36, 0.24, 0.14, 1), bands=True,
        metal=(r"Metals Worn\basic_worn_metal.blend", "basic_worn_metal_01", {"Color": (0.30, 0.31, 0.33, 1)}),
        metal_worn=(0.6, 0.6, 0.62, 1),
        handle=(r"Fabrics\pu_leather.blend", "pu_leather", {"Base Color": (0.16, 0.09, 0.04, 1), "Roughness": 0.55}),
        handle_worn=(0.30, 0.18, 0.10, 1)),
    "t3": dict(   # Silver: pale birch, silver straps, rim, lock and handle
        wood=(r"Stylized\stylized_planks.blend", "stylized_planks_04", {"Color1": (0.70, 0.61, 0.46, 1), "Color2": (0.52, 0.43, 0.31, 1), "Nails": 0.0, "Plank Height": 0.12, "Border Damage": 0.2, "Scale": 4.0}),
        wood_worn=(0.78, 0.70, 0.56, 1), bands=True, handle_metal=True,
        metal=(r"Metals Worn\basic_worn_metal.blend", "basic_worn_metal_01", {"Color": (0.78, 0.80, 0.83, 1), "Roughness": 0.3}),
        metal_worn=(0.92, 0.93, 0.95, 1)),
    "t4": dict(   # Dvergr: blue-grey wood, hammered copper, a blue rune line round the lid
        wood=(r"Stylized\stylized_planks.blend", "stylized_planks_04", {"Color1": (0.28, 0.31, 0.37, 1), "Color2": (0.16, 0.18, 0.23, 1), "Nails": 0.0, "Plank Height": 0.12, "Border Damage": 0.2, "Scale": 4.0}),
        wood_worn=(0.36, 0.40, 0.46, 1), bands=True, handle_metal=True, glow=(0.25, 0.75, 1.0),
        metal=(r"Metals Worn\hammered_copper.blend", None, {}),
        metal_worn=(0.95, 0.62, 0.40, 1)),
}
T = TIERS[TIER]
# the wood is matched to paint_v3's tier colour afterwards (Sanctus' colours come out lighter than set)
MATCH = os.environ.get("VDW_MATCH_DIR")   # folder holding tacklebox_<tier>/tacklebox_<tier>_Unity_{Albedo,MetallicSmoothness}.png

box = bpy.data.objects["tacklebox"]; arm = bpy.data.objects["TackleBox_Rig"]; me = box.data
# ---------------------------------------------------------------- 1. real size, and the parts
co = np.array([v.co[:] for v in me.vertices]); lo, hi = co.min(0), co.max(0)
s = LENGTH / (hi[0] - lo[0])
arm.scale = (s, s, s); bpy.context.view_layer.update()
for o in (arm, box):
    for x in bpy.context.view_layer.objects: x.select_set(x is o)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
co = np.array([v.co[:] for v in me.vertices]); lo, hi = co.min(0), co.max(0)
k = (hi[2] - lo[2]) / 1.249                                   # 1 at the model's own (pre-scale) height
names = [m.name for m in me.materials]; i_lid, i_base, i_lock = names.index("lid"), names.index("base"), names.index("lock")
seam = lo[2] + 0.497 * k
lid_z = np.array([me.vertices[p.vertices[0]].co.z for p in me.polygons if p.material_index == i_lid])
lid_top = np.percentile(lid_z, 90)
WOOD, METAL, HANDLE = 0, 1, 2
part = []
for p in me.polygons:
    c = p.center; n = p.normal
    handle = p.material_index == i_lid and c.z > lid_top + 0.01 * k and abs(c.x) < 0.45 * hi[0]
    if handle: part.append(METAL if T.get("handle_metal") else HANDLE); continue
    if p.material_index == i_lock and c.y < lo[1] + 0.05 * k: part.append(METAL); continue
    part.append(WOOD)                                       # lid, base and the dividers (lock material inside)
# (the bands of the banded tiers are blended in afterwards per texel, from a second, all-metal bake: whole faces gave
# them stepped edges)
print(f"BAKE parts: wood {part.count(WOOD)}, metal {part.count(METAL)}, handle {part.count(HANDLE)} faces; box {tuple((hi - lo).round(3))} m")

# ---------------------------------------------------------------- materials from the libraries
def append_material(rel, name):
    with bpy.data.libraries.load(os.path.join(SANCTUS, rel)) as (src, dst):
        dst.materials = [name if name else src.materials[0]]      # None: the file's first material
    print(f"BAKE material {rel} -> {dst.materials[0].name}")
    return dst.materials[0]
with bpy.data.libraries.load(GRUNGIT) as (src, dst): dst.node_groups = ["Grungit v1.9.1", "Grungit Dirt v1.9.1", "Baker v1.8.3"]
G_MAIN, G_DIRT, G_BAKER = dst.node_groups

mask_img = bpy.data.images.new(f"tacklebox_{TIER}_mask", SIZE, SIZE, alpha=False); mask_img.colorspace_settings.name = 'Non-Color'

def build(rel, name, inputs, worn, metallic2, kind):
    m = append_material(rel, name).copy(); m.name = f"tb_{kind}"
    nt = m.node_tree; N, L = nt.nodes, nt.links
    grp = next(n for n in N if n.type == 'GROUP' and n.node_tree and 'Bake' in ''.join(o.name for o in n.outputs))
    for key, val in inputs.items():
        if key in grp.inputs: grp.inputs[key].default_value = val
    mtex = N.new("ShaderNodeTexImage"); mtex.image = mask_img; mtex.name = "vdw_mask"
    g = N.new("ShaderNodeGroup"); g.node_tree = G_MAIN
    L.new(mtex.outputs["Color"], g.inputs["Grungit Mask"])
    L.new(grp.outputs["Color Bake"], g.inputs["Base Color 1"])
    L.new(grp.outputs["Roughness Bake"], g.inputs["Roughness 1"])
    if "Metallic Bake" in grp.outputs: L.new(grp.outputs["Metallic Bake"], g.inputs["Metallic 1"])
    else: g.inputs["Metallic 1"].default_value = 0.0
    g.inputs["Base Color 2"].default_value = worn; g.inputs["Metallic 2"].default_value = metallic2
    g.inputs["Roughness 2"].default_value = 0.35 if metallic2 > 0.5 else 0.7
    g.inputs["Transition Color"].default_value = worn; g.inputs["Transition Amount"].default_value = 0.0
    g.inputs["Global Control"].default_value = float(os.environ.get("VDW_WEAR", "0.15")); g.inputs["Edge Wear Spread"].default_value = 0.5; g.inputs["Scratch Amount"].default_value = 0.6 if kind == "metal" else 0.3
    g.inputs["Cracks Amount"].default_value = 0.25 if kind == "wood" else 0.0; g.inputs["Grunge Amount"].default_value = 0.25
    g.inputs["Scale"].default_value = 1.0 / max(LENGTH, 0.1)      # the maps are sized for about a metre
    d = N.new("ShaderNodeGroup"); d.node_tree = G_DIRT
    L.new(mtex.outputs["Color"], d.inputs["Grungit Mask"])
    for a, b in (("Base Color", "Base Color"), ("Metallic", "Metallic"), ("Roughness", "Roughness"), ("Normal", "Normal")):
        if a in g.outputs and b in d.inputs: L.new(g.outputs[a], d.inputs[b])
    d.inputs["Dirt Base Color"].default_value = (0.20, 0.13, 0.08, 1)
    d.inputs["Overall Amount"].default_value = float(os.environ.get("VDW_DIRT", "0.25")); d.inputs["AO"].default_value = 0.3
    bsdf = N.new("ShaderNodeBsdfPrincipled"); bsdf.name = "vdw_bsdf"
    L.new(d.outputs["Color"], bsdf.inputs["Base Color"]); L.new(d.outputs["Metallic"], bsdf.inputs["Metallic"])
    L.new(d.outputs["Roughness"], bsdf.inputs["Roughness"]); L.new(d.outputs["Normal"], bsdf.inputs["Normal"])
    out = next(n for n in N if n.type == 'OUTPUT_MATERIAL' and n.is_active_output)
    L.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    em = N.new("ShaderNodeEmission"); em.name = "vdw_emit"
    target = N.new("ShaderNodeTexImage"); target.name = "vdw_target"
    m["vdw_dirt"] = d.name
    return m

mats = [build(*T["wood"], T["wood_worn"], 0.0, "wood"), build(*T["metal"], T["metal_worn"], 1.0, "metal"),
        build(*T["handle"], T["handle_worn"], 0.0, "handle") if "handle" in T else build(*T["metal"], T["metal_worn"], 1.0, "handle")]
me.materials.clear()
for m in mats: me.materials.append(m)
for p, part_i in zip(me.polygons, part): p.material_index = part_i

# ---------------------------------------------------------------- baking
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = SAMPLES
sc.render.bake.margin = 16; sc.render.bake.use_clear = True
for o in bpy.context.view_layer.objects: o.select_set(o is box)
bpy.context.view_layer.objects.active = box
box.modifiers["Armature"].show_render = False                 # bake the rest pose

def set_target(img):
    for m in mats:
        t = m.node_tree.nodes["vdw_target"]; t.image = img
        for n in m.node_tree.nodes: n.select = False
        t.select = True; m.node_tree.nodes.active = t

# 2. the Grungit mask: its Baker's combined output, emitted
mask_mat = bpy.data.materials.new("tb_maskbake"); mask_mat.use_nodes = True
mn = mask_mat.node_tree.nodes; ml = mask_mat.node_tree.links
for n in list(mn):
    if n.type != 'OUTPUT_MATERIAL': mn.remove(n)
bk = mn.new("ShaderNodeGroup"); bk.node_tree = G_BAKER; bk.inputs["Scale"].default_value = 0.5 * LENGTH
ml.new(bk.outputs["Output"], next(n for n in mn if n.type == 'OUTPUT_MATERIAL').inputs["Surface"])
mt = mn.new("ShaderNodeTexImage"); mt.image = mask_img; mn.active = mt
saved = [p.material_index for p in me.polygons]
me.materials.append(mask_mat)
for p in me.polygons: p.material_index = 3
bpy.ops.object.bake(type='EMIT'); print("BAKE mask done")
mask_img.filepath_raw = os.path.join(TEXDIR, f"tacklebox_{TIER}_GrungitMask.png"); mask_img.file_format = 'PNG'; mask_img.save()
for p, i in zip(me.polygons, saved): p.material_index = i
me.materials.pop(index=3)

# 3. the channels
def channel(socket_name, nc):
    img = bpy.data.images.new(f"bake_{socket_name}", SIZE, SIZE, alpha=False)
    if nc: img.colorspace_settings.name = 'Non-Color'
    for m in mats:
        N, L = m.node_tree.nodes, m.node_tree.links
        d = N[m["vdw_dirt"]]; em = N["vdw_emit"]; out = next(n for n in N if n.type == 'OUTPUT_MATERIAL' and n.is_active_output)
        for l in list(em.inputs["Color"].links): L.remove(l)
        L.new(d.outputs[socket_name], em.inputs["Color"]); L.new(em.outputs["Emission"], out.inputs["Surface"])
    set_target(img); bpy.ops.object.bake(type='EMIT'); return img

def px(img):
    a = np.empty(SIZE * SIZE * 4, np.float32); img.pixels.foreach_get(a); return a.reshape(SIZE, SIZE, 4)
def save(arr, name, nc):
    path = os.path.join(TEXDIR, name)
    if os.path.exists(path) and not REDO: print("  exists, kept:", path); return
    im = bpy.data.images.new(name, SIZE, SIZE, alpha=True)
    if nc: im.colorspace_settings.name = 'Non-Color'
    im.pixels.foreach_set(np.ascontiguousarray(arr, np.float32).ravel()); im.filepath_raw = path; im.file_format = 'PNG'; im.save(); print("  saved", path)

col = px(channel("Color", False)); print("BAKE colour done")
met = px(channel("Metallic", True)); print("BAKE metallic done")
rough = px(channel("Roughness", True)); print("BAKE roughness done")
# normal: the shaders back on, a tangent-space normal bake
for m in mats:
    N, L = m.node_tree.nodes, m.node_tree.links
    L.new(N["vdw_bsdf"].outputs["BSDF"], next(n for n in N if n.type == 'OUTPUT_MATERIAL' and n.is_active_output).inputs["Surface"])
nimg = bpy.data.images.new("bake_normal", SIZE, SIZE, alpha=False); nimg.colorspace_settings.name = 'Non-Color'
set_target(nimg); sc.render.bake.normal_space = 'TANGENT'; bpy.ops.object.bake(type='NORMAL'); print("BAKE normal done")
nrm = px(nimg)

def emit_bake(source, name, float_buf=False):
    """Bakes, for each part material, source(index, nodes, links) -> a colour socket or an RGB tuple, as emission."""
    img = bpy.data.images.new(name, SIZE, SIZE, alpha=False, float_buffer=float_buf); img.colorspace_settings.name = 'Non-Color'
    for i, m in enumerate(mats):
        N, L = m.node_tree.nodes, m.node_tree.links
        em = N["vdw_emit"]; out = next(n for n in N if n.type == 'OUTPUT_MATERIAL' and n.is_active_output)
        for l in list(em.inputs["Color"].links): L.remove(l)
        src = source(i, N, L)
        if isinstance(src, tuple): em.inputs["Color"].default_value = (*src, 1.0)
        else: L.new(src, em.inputs["Color"])
        L.new(em.outputs["Emission"], out.inputs["Surface"])
    set_target(img); bpy.ops.object.bake(type='EMIT'); return px(img)

# which texels are wood (for matching its colour) and where each texel is on the box (for the rune line)
pid = emit_bake(lambda i, N, L: ((1, 0, 0), (0, 1, 0), (0, 0, 1))[i], "bake_part")
wood = pid[..., 0] > 0.5
if MATCH:
    def load_px(path):
        im = bpy.data.images.load(path); im.colorspace_settings.name = 'Non-Color'
        a = np.empty(im.size[0] * im.size[1] * 4, np.float32); im.pixels.foreach_get(a); return a.reshape(im.size[1], im.size[0], 4)
    ref_dir = os.path.join(MATCH, f"tacklebox_{TIER}")
    ra = load_px(os.path.join(ref_dir, f"tacklebox_{TIER}_Unity_Albedo.png")); rm = load_px(os.path.join(ref_dir, f"tacklebox_{TIER}_Unity_MetallicSmoothness.png"))
    ref = ra[(rm[..., 0] < 0.5) & (ra[..., :3].sum(-1) > 0.05), :3]
    # the albedo was baked in sRGB space like the reference, so compare them directly
    gain = np.clip(np.median(ref, 0) / np.maximum(np.median(col[wood, :3], 0), 1e-3), 0.3, 3.0)
    col[wood, :3] = np.clip(col[wood, :3] * gain, 0, 1)
    print(f"BAKE wood matched to paint_v3: gain {gain.round(2)} (target {np.median(ref, 0).round(3)})")
def position(i, N, L):
    g = N.new("ShaderNodeNewGeometry"); sub = N.new("ShaderNodeVectorMath"); sub.operation = 'SUBTRACT'; sub.inputs[1].default_value = tuple(lo)
    div = N.new("ShaderNodeVectorMath"); div.operation = 'DIVIDE'; div.inputs[1].default_value = tuple(hi - lo)
    L.new(g.outputs["Position"], sub.inputs[0]); L.new(sub.outputs["Vector"], div.inputs[0]); return div.outputs["Vector"]
def obj_normal(i, N, L):
    g = N.new("ShaderNodeNewGeometry"); mad = N.new("ShaderNodeVectorMath"); mad.operation = 'MULTIPLY_ADD'
    mad.inputs[1].default_value = (0.5, 0.5, 0.5); mad.inputs[2].default_value = (0.5, 0.5, 0.5)
    L.new(g.outputs["True Normal"], mad.inputs[0]); return mad.outputs["Vector"]
P = None
if T.get("glow") or T.get("bands"):
    pos = emit_bake(position, "bake_pos", float_buf=True); P = lo + pos[..., :3] * (hi - lo)

if T.get("bands"):
    # a second bake with the wood faces in metal, blended in through a smooth band mask: two straps round each end and a
    # rim along the seam, on the outside surfaces only
    Nobj = emit_bake(obj_normal, "bake_nrm_obj", float_buf=True)[..., :3] * 2 - 1
    saved_idx = [p.material_index for p in me.polygons]
    for p in me.polygons:
        if p.material_index == WOOD: p.material_index = METAL
    m_col = px(channel("Color", False)); m_met = px(channel("Metallic", True)); m_rough = px(channel("Roughness", True))
    for m in mats:
        N, L = m.node_tree.nodes, m.node_tree.links
        L.new(N["vdw_bsdf"].outputs["BSDF"], next(n for n in N if n.type == 'OUTPUT_MATERIAL' and n.is_active_output).inputs["Surface"])
    mn_img = bpy.data.images.new("bake_normal_metal", SIZE, SIZE, alpha=False); mn_img.colorspace_settings.name = 'Non-Color'
    set_target(mn_img); bpy.ops.object.bake(type='NORMAL'); m_nrm = px(mn_img)
    for p, i in zip(me.polygons, saved_idx): p.material_index = i
    X, Y, Z = P[..., 0], P[..., 1], P[..., 2]
    outer = ((Nobj[..., 0] * X + Nobj[..., 1] * Y > 0) & (np.abs(Nobj[..., 2]) < 0.7)) | ((Z > seam) & (Nobj[..., 2] > 0.3)) | ((Z < seam) & (Nobj[..., 2] < -0.3))
    def sm(e0, e1, x): t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)
    from_end = hi[0] - np.abs(X); w = 0.004 * k / 0.259 * 0.259          # a soft edge about 1 mm wide
    strap = sm(0.14 * k - w, 0.14 * k + w, from_end) * (1 - sm(0.25 * k - w, 0.25 * k + w, from_end))
    rim = 1 - sm(0.03 * k - w, 0.03 * k + w, np.abs(Z - seam))
    band = np.clip(np.maximum(strap, rim), 0, 1) * outer * wood
    b4 = band[..., None]
    col = col * (1 - b4) + m_col * b4; met = met * (1 - b4) + m_met * b4; rough = rough * (1 - b4) + m_rough * b4
    nrm = nrm * (1 - b4) + m_nrm * b4
    wood = wood & (band < 0.5)
    print(f"BAKE bands blended: {(band > 0.5).sum()} texels")

emit = None
if T.get("glow"):
    band = wood & (P[..., 2] > seam) & (np.abs(P[..., 2] - (seam + 0.11 * k)) < 0.012 * k)
    runes = band & (np.sin(np.arctan2(P[..., 1], P[..., 0]) * 60) > -0.2)
    emit = np.zeros_like(col); emit[..., 3] = 1.0; emit[runes, :3] = T["glow"]
    col[runes, :3] = np.array(T["glow"]) * 0.5
    print(f"BAKE rune line: {runes.sum()} texels")

save(col, f"tacklebox_{TIER}_Unity_Albedo.png", False)
if emit is not None: save(emit, f"tacklebox_{TIER}_Unity_Emission.png", False)
ms = np.zeros_like(col); ms[..., 0] = ms[..., 1] = ms[..., 2] = met[..., 0]; ms[..., 3] = 1.0 - rough[..., 0]
save(ms, f"tacklebox_{TIER}_Unity_MetallicSmoothness.png", True)
nrm[..., 3] = 1.0; save(nrm, f"tacklebox_{TIER}_Unity_Normal.png", True)
box.modifiers["Armature"].show_render = True
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f"tacklebox_{TIER}_baked.blend"))
print("===== END =====")
