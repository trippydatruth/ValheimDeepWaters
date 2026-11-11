# Bakes a cooler tier from the user's add-ons, like bake_tacklebox.py: Sanctus Library materials worn by Grungit (edge
# wear, scratches, cracks, then dirt in the cavities), into Unity maps on the cooler's own UVs.
#   input: build_cooler.py's cooler_rig.blend (object "cooler", rig "Cooler_Rig", real size, the model's two materials:
#   the body - the ice chest's red - and the lid and handles - its white)
#   c1 Wooden Cooler: oak planks body, lighter oak lid and handles
#   c2 Iron-Banded Cooler: dark tarred planks, worn iron lid and handles
#   c3 Frost Cooler: Sanctus ice body, worn silver lid and handles
# Writes <out>/cooler_<tier>/cooler_<tier>_Unity_{Albedo,MetallicSmoothness,Normal}.png (+ the Grungit mask). New files only.
#   blender -b cooler_rig.blend --factory-startup --python bake_cooler.py   env: VDW_OUT, VDW_TIER, VDW_SIZE (1024, the most), VDW_SAMPLES (64)
import bpy, os
import numpy as np

OUT = os.environ["VDW_OUT"]; TIER = os.environ.get("VDW_TIER", "c1")
SIZE = min(1024, int(os.environ.get("VDW_SIZE", "1024"))); SAMPLES = int(os.environ.get("VDW_SAMPLES", "64"))   # textures: 1K at most (low-poly game)
SANCTUS = os.path.join(os.environ["APPDATA"], rf"Blender Foundation\Blender\{bpy.app.version[0]}.{bpy.app.version[1]}\extensions\user_default\sanctus_library_starter\lib\materials")
GRUNGIT = os.path.join(os.environ["APPDATA"], rf"Blender Foundation\Blender\{bpy.app.version[0]}.{bpy.app.version[1]}\scripts\addons\Grungit\grungit_data\Materials.blend")
TEXDIR = os.path.join(OUT, f"cooler_{TIER}")
if os.path.exists(os.path.join(TEXDIR, f"cooler_{TIER}_Unity_Albedo.png")): raise SystemExit("exists, kept: " + TEXDIR)
os.makedirs(TEXDIR, exist_ok=True)

PLANKS = r"Stylized\stylized_planks.blend"
TIERS = {
    "c1": dict(body=(PLANKS, "stylized_planks_04", {"Color1": (0.41, 0.27, 0.14, 1), "Color2": (0.25, 0.15, 0.08, 1), "Nails": 0.0, "Plank Height": 0.10, "Border Damage": 0.25, "Scale": 4.0}),
               body_worn=(0.47, 0.31, 0.17, 1), body_metal=0.0,
               trim=(PLANKS, "stylized_planks_04", {"Color1": (0.55, 0.38, 0.21, 1), "Color2": (0.40, 0.26, 0.14, 1), "Nails": 0.0, "Plank Height": 0.10, "Border Damage": 0.2, "Scale": 4.0}),
               trim_worn=(0.60, 0.44, 0.27, 1), trim_metal=0.0,
               front=(r"Metals Worn\basic_worn_metal.blend", "basic_worn_metal_01", {"Color": (0.70, 0.40, 0.22, 1)}), front_worn=(0.95, 0.62, 0.40, 1), front_metal=1.0),
    "c2": dict(body=(PLANKS, "stylized_planks_04", {"Color1": (0.22, 0.15, 0.09, 1), "Color2": (0.12, 0.08, 0.05, 1), "Nails": 0.0, "Plank Height": 0.10, "Border Damage": 0.3, "Scale": 4.0}),
               body_worn=(0.30, 0.21, 0.13, 1), body_metal=0.0,
               trim=(r"Metals Worn\basic_worn_metal.blend", "basic_worn_metal_01", {"Color": (0.30, 0.31, 0.33, 1)}),
               trim_worn=(0.6, 0.6, 0.62, 1), trim_metal=1.0,
               front=(r"Metals Worn\basic_worn_metal.blend", "basic_worn_metal_01", {"Color": (0.55, 0.42, 0.18, 1)}), front_worn=(0.85, 0.70, 0.40, 1), front_metal=1.0),
    # (Sanctus' ice is a see-through glass shader with no colour to bake: frosted pale planks instead, frost in the cavities)
    "c3": dict(body=(PLANKS, "stylized_planks_04", {"Color1": (0.70, 0.80, 0.88, 1), "Color2": (0.52, 0.62, 0.72, 1), "Nails": 0.0, "Plank Height": 0.10, "Border Damage": 0.2, "Scale": 4.0}),
               body_worn=(0.92, 0.96, 1.0, 1), body_metal=0.0,
               trim=(r"Metals Worn\basic_worn_metal.blend", "basic_worn_metal_01", {"Color": (0.78, 0.80, 0.83, 1), "Roughness": 0.3}),
               trim_worn=(0.92, 0.93, 0.95, 1), trim_metal=1.0,
               front=(r"Metals Worn\basic_worn_metal.blend", "basic_worn_metal_01", {"Color": (0.50, 0.70, 0.88, 1), "Roughness": 0.3}), front_worn=(0.85, 0.93, 1.0, 1), front_metal=1.0),
}
T = TIERS[TIER]

box = bpy.data.objects["cooler"]; me = box.data
co = np.array([v.co[:] for v in me.vertices]); lo, hi = co.min(0), co.max(0); LENGTH = float(hi[0] - lo[0])
names = [m.name for m in me.materials]
def whiteish(m): return m is not None and tuple(m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value)[1] >= 0.3
i_trim = next(i for i, m in enumerate(me.materials) if whiteish(m))
BODY, TRIM, FRONT = 0, 1, 2
# the little square on the front: lid-and-handle material, below the lid, facing forward (-Y); the handles face the sides
top = lo[2] + 0.8 * (hi[2] - lo[2])
part = [(FRONT if (p.center.z < top and p.normal.y < -0.5) else TRIM) if p.material_index == i_trim else BODY for p in me.polygons]
print(f"BAKE {TIER}: body {part.count(BODY)}, lid and handles {part.count(TRIM)}, front {part.count(FRONT)} faces; cooler {tuple((hi - lo).round(3))} m")

def append_material(rel, name):
    with bpy.data.libraries.load(os.path.join(SANCTUS, rel)) as (src, dst):
        dst.materials = [name if name else src.materials[0]]
    print(f"BAKE material {rel} -> {dst.materials[0].name}")
    return dst.materials[0]
with bpy.data.libraries.load(GRUNGIT) as (src, dst): dst.node_groups = ["Grungit v1.9.1", "Grungit Dirt v1.9.1", "Baker v1.8.3"]
G_MAIN, G_DIRT, G_BAKER = dst.node_groups
mask_img = bpy.data.images.new(f"cooler_{TIER}_mask", SIZE, SIZE, alpha=False); mask_img.colorspace_settings.name = 'Non-Color'

def build(rel, name, inputs, worn, metallic2, kind):
    m = append_material(rel, name).copy(); m.name = f"cool_{kind}"
    nt = m.node_tree; N, L = nt.nodes, nt.links
    grp = next((n for n in N if n.type == 'GROUP' and n.node_tree and 'Bake' in ''.join(o.name for o in n.outputs)), None)
    if grp is None: raise SystemExit(f"{rel}: no Sanctus group with bake outputs")
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
    g.inputs["Global Control"].default_value = float(os.environ.get("VDW_WEAR", "0.15")); g.inputs["Edge Wear Spread"].default_value = 0.5
    g.inputs["Scratch Amount"].default_value = 0.6 if metallic2 > 0.5 else 0.3
    g.inputs["Cracks Amount"].default_value = 0.25 if kind == "body" and TIER != "c3" else 0.0; g.inputs["Grunge Amount"].default_value = 0.25
    g.inputs["Scale"].default_value = 1.0 / max(LENGTH, 0.1)
    d = N.new("ShaderNodeGroup"); d.node_tree = G_DIRT
    L.new(mtex.outputs["Color"], d.inputs["Grungit Mask"])
    for a in ("Base Color", "Metallic", "Roughness", "Normal"):
        if a in g.outputs and a in d.inputs: L.new(g.outputs[a], d.inputs[a])
    d.inputs["Dirt Base Color"].default_value = (0.20, 0.13, 0.08, 1) if TIER != "c3" else (0.45, 0.55, 0.62, 1)
    d.inputs["Overall Amount"].default_value = float(os.environ.get("VDW_DIRT", "0.25")); d.inputs["AO"].default_value = 0.3
    bsdf = N.new("ShaderNodeBsdfPrincipled"); bsdf.name = "vdw_bsdf"
    L.new(d.outputs["Color"], bsdf.inputs["Base Color"]); L.new(d.outputs["Metallic"], bsdf.inputs["Metallic"])
    L.new(d.outputs["Roughness"], bsdf.inputs["Roughness"]); L.new(d.outputs["Normal"], bsdf.inputs["Normal"])
    out = next(n for n in N if n.type == 'OUTPUT_MATERIAL' and n.is_active_output)
    L.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    em = N.new("ShaderNodeEmission"); em.name = "vdw_emit"
    N.new("ShaderNodeTexImage").name = "vdw_target"
    m["vdw_dirt"] = d.name
    return m

mats = [build(*T["body"], T["body_worn"], T["body_metal"], "body"), build(*T["trim"], T["trim_worn"], T["trim_metal"], "trim"),
        build(*T["front"], T["front_worn"], T["front_metal"], "front")]
me.materials.clear()
for m in mats: me.materials.append(m)
for p, k in zip(me.polygons, part): p.material_index = k

sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = SAMPLES
sc.render.bake.margin = 16; sc.render.bake.use_clear = True
for o in bpy.context.view_layer.objects: o.select_set(o is box)
bpy.context.view_layer.objects.active = box
box.modifiers["Armature"].show_render = False

def set_target(img):
    for m in mats:
        t = m.node_tree.nodes["vdw_target"]; t.image = img
        for n in m.node_tree.nodes: n.select = False
        t.select = True; m.node_tree.nodes.active = t

# the Grungit mask from its Baker
mask_mat = bpy.data.materials.new("cool_maskbake"); mask_mat.use_nodes = True
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
mask_img.filepath_raw = os.path.join(TEXDIR, f"cooler_{TIER}_GrungitMask.png"); mask_img.file_format = 'PNG'; mask_img.save()
for p, i in zip(me.polygons, saved): p.material_index = i
me.materials.pop(index=3)

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
    im = bpy.data.images.new(name, SIZE, SIZE, alpha=True)
    if nc: im.colorspace_settings.name = 'Non-Color'
    im.pixels.foreach_set(np.ascontiguousarray(arr, np.float32).ravel()); im.filepath_raw = os.path.join(TEXDIR, name); im.file_format = 'PNG'; im.save(); print("  saved", name)

col = px(channel("Color", False)); met = px(channel("Metallic", True)); rough = px(channel("Roughness", True))
for m in mats:
    N, L = m.node_tree.nodes, m.node_tree.links
    L.new(N["vdw_bsdf"].outputs["BSDF"], next(n for n in N if n.type == 'OUTPUT_MATERIAL' and n.is_active_output).inputs["Surface"])
nimg = bpy.data.images.new("bake_normal", SIZE, SIZE, alpha=False); nimg.colorspace_settings.name = 'Non-Color'
set_target(nimg); sc.render.bake.normal_space = 'TANGENT'; bpy.ops.object.bake(type='NORMAL'); nrm = px(nimg)

# Sanctus' planks come out lighter than their colours (as on the tackle box): each wood part is scaled back to the
# colour asked for, the middle of its Color1 and Color2 (read as seen, like the albedo)
def emit_parts():
    img = bpy.data.images.new("bake_part", SIZE, SIZE, alpha=False); img.colorspace_settings.name = 'Non-Color'
    for i, m in enumerate(mats):
        N, L = m.node_tree.nodes, m.node_tree.links
        em = N["vdw_emit"]; out = next(n for n in N if n.type == 'OUTPUT_MATERIAL' and n.is_active_output)
        for l in list(em.inputs["Color"].links): L.remove(l)
        em.inputs["Color"].default_value = ((1, 0, 0, 1), (0, 1, 0, 1), (0, 0, 1, 1))[i]; L.new(em.outputs["Emission"], out.inputs["Surface"])
    set_target(img); bpy.ops.object.bake(type='EMIT'); return px(img)
pid = emit_parts()
for i, key in enumerate(("body", "trim")):
    rel, _n, inputs = T[key]
    if "Color1" not in inputs or T[key + "_metal"] > 0.5: continue
    sel = pid[..., i] > 0.5
    if sel.sum() < 100: continue
    want = (np.array(inputs["Color1"][:3]) + np.array(inputs["Color2"][:3])) / 2
    gain = np.clip(want / np.maximum(np.median(col[sel, :3], 0), 1e-3), 0.3, 3.0)
    col[sel, :3] = np.clip(col[sel, :3] * gain, 0, 1)
    print(f"BAKE {key} wood matched: gain {gain.round(2)} (to {want.round(3)})")

save(col, f"cooler_{TIER}_Unity_Albedo.png", False)
ms = np.zeros_like(col); ms[..., 0] = ms[..., 1] = ms[..., 2] = met[..., 0]; ms[..., 3] = 1.0 - rough[..., 0]
save(ms, f"cooler_{TIER}_Unity_MetallicSmoothness.png", True)
nrm[..., 3] = 1.0; save(nrm, f"cooler_{TIER}_Unity_Normal.png", True)
box.modifiers["Armature"].show_render = True
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f"cooler_{TIER}_baked.blend"))
print("===== END =====")
