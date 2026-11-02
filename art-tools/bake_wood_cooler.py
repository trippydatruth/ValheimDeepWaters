# Textures a tier of the wooden ice chest (build_wood_cooler.py) from the user's add-ons, like bake_tacklebox.py:
# Sanctus materials (generic wood for the boards and grips - its grain following each board's long side through the
# model's "Grain" UVs - worn metal for iron or silver, rough gold for brass) worn by Grungit (edge wear, scratches,
# cracks) and Grungit Dirt (dirt or frost in the cavities), baked to Unity maps on the "UVMap" atlas.
#   c1 Wooden Cooler: oak, dark iron, brass        c2 Iron-Banded Cooler: dark tarred wood, worn steel, brass
#   c3 Frost Cooler: pale frosted wood, silver fittings, frost in the cracks
# VDW_KIND=tacklebox: the wooden tackle box (build_wood_tacklebox.py; wood, tray and iron), tiers t1 Wooden (oak,
#   dark iron), t2 Iron-Bound (dark stained wood, steel), t3 Silver (pale birch, silver), t4 Dvergr (blue-grey wood,
#   hammered copper, a blue rune line glowing round the top rail: an extra _Emission map); each painted (green, oxblood,
#   cream, navy) and worn back to the wood (VDW_PAINT=0 for bare wood)
# Writes <out>/cooler_<tier>/cooler_<tier>_Unity_{Albedo,MetallicSmoothness,Normal}.png, the mask, and
# <out>/cooler_<tier>_baked.blend (the live materials, for editing and rebaking). New files only.
#   blender -b cooler_wood_v1.blend --factory-startup --python bake_wood_cooler.py
#   env: VDW_OUT, VDW_TIER (c1), VDW_SIZE (2048), VDW_SAMPLES (32)
import bpy, os
import numpy as np

OUT = os.environ["VDW_OUT"]; TIER = os.environ.get("VDW_TIER", "c1")
KIND = os.environ.get("VDW_KIND", "cooler"); PREFIX = "tacklebox" if KIND == "tacklebox" else "cooler"
SIZE = int(os.environ.get("VDW_SIZE", "2048")); SAMPLES = int(os.environ.get("VDW_SAMPLES", "32"))
SANCTUS = os.path.join(os.environ["APPDATA"], r"Blender Foundation\Blender\5.2\extensions\user_default\sanctus_library_starter\lib\materials")
GRUNGIT = os.path.join(os.environ["APPDATA"], r"Blender Foundation\Blender\5.2\scripts\addons\Grungit\grungit_data\Materials.blend")
TEXDIR = os.path.join(OUT, f"{PREFIX}_{TIER}")
if os.path.exists(os.path.join(TEXDIR, f"{PREFIX}_{TIER}_Unity_Albedo.png")): raise SystemExit("exists, kept: " + TEXDIR)
os.makedirs(TEXDIR, exist_ok=True)

WOOD, METAL, GOLD = r"Wood\generic_wood.blend", r"Metals Worn\basic_worn_metal.blend", r"Metals Worn\gold_rough.blend"
COPPER = r"Metals Worn\hammered_copper.blend"
# per material slot: (Sanctus file, material, its inputs, the worn colour Grungit wears edges to, metallic of the wear,
#   wear amount, dirt colour, dirt amount)
TIERS = {
    "c1": dict(
        wood=(WOOD, "generic_wood_01", {"Light Color": (0.52, 0.34, 0.18, 1), "Dark Color": (0.30, 0.18, 0.09, 1), "Knots": 0.4, "Damage": 0.25, "Roughness": 0.7, "Clearcoat": 0.0, "Bump": 0.4}, (0.62, 0.45, 0.28, 1), 0.0, 0.35, (0.18, 0.12, 0.07, 1), 0.3),
        grip=(WOOD, "generic_wood_01", {"Light Color": (0.66, 0.48, 0.30, 1), "Dark Color": (0.45, 0.30, 0.17, 1), "Knots": 0.0, "Damage": 0.1, "Roughness": 0.6, "Clearcoat": 0.0}, (0.75, 0.6, 0.42, 1), 0.0, 0.3, (0.18, 0.12, 0.07, 1), 0.2),
        iron=(METAL, "basic_worn_metal_01", {"Color": (0.13, 0.13, 0.14, 1), "Roughness": 0.55}, (0.30, 0.30, 0.32, 1), 1.0, 0.36, (0.20, 0.13, 0.08, 1), 0.35),
        brass=(GOLD, "gold_rough", {"Color": (0.72, 0.52, 0.24, 1), "Roughness": 0.35}, (0.9, 0.75, 0.45, 1), 1.0, 0.3, (0.20, 0.17, 0.08, 1), 0.3)),
    "c2": dict(   # the swamp: tarred wood, nearly black, and brighter iron
        wood=(WOOD, "generic_wood_01", {"Light Color": (0.13, 0.08, 0.045, 1), "Dark Color": (0.045, 0.027, 0.015, 1), "Knots": 0.5, "Damage": 0.35, "Roughness": 0.45, "Clearcoat": 0.0, "Bump": 0.45}, (0.17, 0.11, 0.065, 1), 0.0, 0.4, (0.08, 0.09, 0.05, 1), 0.4),
        grip=(WOOD, "generic_wood_01", {"Light Color": (0.30, 0.20, 0.12, 1), "Dark Color": (0.15, 0.09, 0.05, 1), "Knots": 0.0, "Damage": 0.15, "Roughness": 0.55, "Clearcoat": 0.0}, (0.42, 0.30, 0.19, 1), 0.0, 0.35, (0.08, 0.09, 0.05, 1), 0.3),
        iron=(METAL, "basic_worn_metal_01", {"Color": (0.27, 0.28, 0.30, 1), "Roughness": 0.45}, (0.62, 0.62, 0.64, 1), 1.0, 0.55, (0.14, 0.12, 0.06, 1), 0.4),
        brass=(GOLD, "gold_rough", {"Color": (0.62, 0.45, 0.22, 1), "Roughness": 0.4}, (0.85, 0.7, 0.42, 1), 1.0, 0.35, (0.14, 0.12, 0.06, 1), 0.4)),
    "c3": dict(   # the mountains: grey weathered wood, bright silver, frost in the cracks
        wood=(WOOD, "generic_wood_01", {"Light Color": (0.36, 0.38, 0.41, 1), "Dark Color": (0.19, 0.21, 0.24, 1), "Knots": 0.3, "Damage": 0.2, "Roughness": 0.6, "Clearcoat": 0.0, "Bump": 0.35}, (0.52, 0.56, 0.60, 1), 0.0, 0.35, (0.85, 0.92, 1.0, 1), 0.4),
        grip=(WOOD, "generic_wood_01", {"Light Color": (0.45, 0.47, 0.50, 1), "Dark Color": (0.27, 0.29, 0.32, 1), "Knots": 0.0, "Damage": 0.1, "Roughness": 0.55, "Clearcoat": 0.0}, (0.6, 0.63, 0.66, 1), 0.0, 0.3, (0.85, 0.92, 1.0, 1), 0.3),
        iron=(METAL, "basic_worn_metal_01", {"Color": (0.74, 0.77, 0.80, 1), "Roughness": 0.3}, (0.92, 0.93, 0.95, 1), 1.0, 0.4, (0.93, 0.97, 1.0, 1), 0.35),
        brass=(METAL, "basic_worn_metal_01", {"Color": (0.62, 0.74, 0.86, 1), "Roughness": 0.3}, (0.88, 0.93, 1.0, 1), 1.0, 0.35, (0.93, 0.97, 1.0, 1), 0.35)),
}
TB_TIERS = {
    "t1": dict(
        wood=(WOOD, "generic_wood_01", {"Light Color": (0.52, 0.34, 0.18, 1), "Dark Color": (0.30, 0.18, 0.09, 1), "Knots": 0.4, "Damage": 0.25, "Roughness": 0.7, "Clearcoat": 0.0, "Bump": 0.4}, (0.62, 0.45, 0.28, 1), 0.0, 0.35, (0.18, 0.12, 0.07, 1), 0.3),
        tray=(WOOD, "generic_wood_01", {"Light Color": (0.66, 0.48, 0.30, 1), "Dark Color": (0.45, 0.30, 0.17, 1), "Knots": 0.0, "Damage": 0.1, "Roughness": 0.6, "Clearcoat": 0.0}, (0.75, 0.6, 0.42, 1), 0.0, 0.25, (0.18, 0.12, 0.07, 1), 0.2),
        iron=(METAL, "basic_worn_metal_01", {"Color": (0.13, 0.13, 0.14, 1), "Roughness": 0.55}, (0.30, 0.30, 0.32, 1), 1.0, 0.36, (0.20, 0.13, 0.08, 1), 0.35)),
    "t2": dict(   # Iron-Bound: dark stained wood, bright steel
        wood=(WOOD, "generic_wood_01", {"Light Color": (0.24, 0.15, 0.08, 1), "Dark Color": (0.11, 0.065, 0.035, 1), "Knots": 0.5, "Damage": 0.3, "Roughness": 0.55, "Clearcoat": 0.0, "Bump": 0.45}, (0.32, 0.21, 0.12, 1), 0.0, 0.35, (0.10, 0.09, 0.05, 1), 0.35),
        tray=(WOOD, "generic_wood_01", {"Light Color": (0.42, 0.28, 0.16, 1), "Dark Color": (0.24, 0.15, 0.08, 1), "Knots": 0.0, "Damage": 0.1, "Roughness": 0.55, "Clearcoat": 0.0}, (0.5, 0.36, 0.22, 1), 0.0, 0.25, (0.10, 0.09, 0.05, 1), 0.25),
        iron=(METAL, "basic_worn_metal_01", {"Color": (0.27, 0.28, 0.30, 1), "Roughness": 0.45}, (0.62, 0.62, 0.64, 1), 1.0, 0.5, (0.14, 0.12, 0.06, 1), 0.35)),
    "t3": dict(   # Silver: pale birch, silver
        wood=(WOOD, "generic_wood_01", {"Light Color": (0.66, 0.58, 0.44, 1), "Dark Color": (0.48, 0.40, 0.28, 1), "Knots": 0.3, "Damage": 0.2, "Roughness": 0.6, "Clearcoat": 0.0, "Bump": 0.35}, (0.76, 0.69, 0.56, 1), 0.0, 0.3, (0.22, 0.17, 0.10, 1), 0.3),
        tray=(WOOD, "generic_wood_01", {"Light Color": (0.74, 0.66, 0.52, 1), "Dark Color": (0.58, 0.50, 0.37, 1), "Knots": 0.0, "Damage": 0.1, "Roughness": 0.55, "Clearcoat": 0.0}, (0.82, 0.76, 0.64, 1), 0.0, 0.25, (0.22, 0.17, 0.10, 1), 0.2),
        iron=(METAL, "basic_worn_metal_01", {"Color": (0.74, 0.77, 0.80, 1), "Roughness": 0.3}, (0.92, 0.93, 0.95, 1), 1.0, 0.35, (0.20, 0.17, 0.12, 1), 0.3)),
    "t4": dict(   # Dvergr: blue-grey wood, hammered copper, a rune line
        wood=(WOOD, "generic_wood_01", {"Light Color": (0.25, 0.29, 0.35, 1), "Dark Color": (0.12, 0.15, 0.20, 1), "Knots": 0.3, "Damage": 0.2, "Roughness": 0.55, "Clearcoat": 0.0, "Bump": 0.35}, (0.36, 0.41, 0.48, 1), 0.0, 0.3, (0.08, 0.10, 0.13, 1), 0.3),
        tray=(WOOD, "generic_wood_01", {"Light Color": (0.38, 0.42, 0.48, 1), "Dark Color": (0.22, 0.26, 0.32, 1), "Knots": 0.0, "Damage": 0.1, "Roughness": 0.55, "Clearcoat": 0.0}, (0.48, 0.52, 0.58, 1), 0.0, 0.25, (0.08, 0.10, 0.13, 1), 0.2),
        iron=(COPPER, "hammered_copper", {"Color": (0.58, 0.30, 0.16, 1), "Roughness": 0.35, "Patina": 0.15}, (0.85, 0.55, 0.35, 1), 1.0, 0.35, (0.10, 0.14, 0.12, 1), 0.3),
        glow=(0.25, 0.75, 1.0)),
}
PAINT = {"t1": (0.055, 0.14, 0.075), "t2": (0.20, 0.03, 0.02), "t3": (0.62, 0.58, 0.48), "t4": (0.025, 0.06, 0.15)}
# how worn the paint is per tier: the low tiers mostly bare wood with the colour only clinging on, the high ones kept up
PAINT_WEAR = {"t1": 0.62, "t2": 0.55, "t3": 0.42, "t4": 0.32}
if KIND == "tacklebox" and os.environ.get("VDW_PAINT", "1") == "1":     # VDW_PAINT=0: bare wood (the first wooden boxes)
    for k, v in PAINT.items():
        TB_TIERS[k]["paint"] = v
        w = list(TB_TIERS[k]["wood"]); w[5] = PAINT_WEAR[k] * float(os.environ.get("VDW_PAINT_WEAR", "1")); TB_TIERS[k]["wood"] = tuple(w)
if KIND == "tacklebox": TIERS = TB_TIERS
T = TIERS[TIER]
SLOTS = ["wood", "tray", "iron"] if KIND == "tacklebox" else ["wood", "grip", "iron", "brass"]
box = bpy.data.objects[PREFIX]; me = box.data
me.uv_layers.active = me.uv_layers["UVMap"]; me.uv_layers["UVMap"].active_render = True
co = np.array([v.co[:] for v in me.vertices]); lo, hi = co.min(0), co.max(0); LENGTH = float(hi[0] - lo[0])

def append_material(rel, name):
    with bpy.data.libraries.load(os.path.join(SANCTUS, rel)) as (src, dst): dst.materials = [name]
    return dst.materials[0]
with bpy.data.libraries.load(GRUNGIT) as (src, dst): dst.node_groups = ["Grungit v1.9.1", "Grungit Dirt v1.9.1", "Baker v1.8.3"]
G_MAIN, G_DIRT, G_BAKER = dst.node_groups
mask_img = bpy.data.images.new(f"{PREFIX}_{TIER}_mask", SIZE, SIZE, alpha=False); mask_img.colorspace_settings.name = 'Non-Color'

def build(slot):
    rel, name, inputs, worn, worn_metal, wear, dirt_col, dirt = T[slot]
    m = append_material(rel, name).copy(); m.name = f"cool_{slot}_{TIER}"
    N, L = m.node_tree.nodes, m.node_tree.links
    grp = next(n for n in N if n.type == 'GROUP' and n.node_tree and any("Bake" in o.name for o in n.outputs))
    for k, v in inputs.items():
        if k in grp.inputs: grp.inputs[k].default_value = v
    if rel == WOOD:      # the grain along each board's long side: its "Grain" UVs (metres), U along the length
        uv = N.new("ShaderNodeUVMap"); uv.uv_map = "Grain"; uv.name = "vdw_grain"
        # stretched 5x along the board (U) so the grain runs straight instead of wavy
        mp = N.new("ShaderNodeMapping"); mp.name = "vdw_grain_stretch"; mp.inputs["Scale"].default_value = (float(os.environ.get("VDW_GRAIN_STRETCH", "0.2")), 1.0, 1.0)
        L.new(uv.outputs["UV"], mp.inputs["Vector"]); L.new(mp.outputs["Vector"], grp.inputs["Vector"])
        if "Scale" in grp.inputs: grp.inputs["Scale"].default_value = float(os.environ.get("VDW_WOOD_SCALE", "1.6"))
        # generic_wood's grain runs along V: turned a quarter about Z it runs along U, the board's length
        grp.inputs["Texture Rotation"].default_value = (0.0, 0.0, 1.5708)
    mtex = N.new("ShaderNodeTexImage"); mtex.image = mask_img; mtex.name = "vdw_mask"
    g = N.new("ShaderNodeGroup"); g.node_tree = G_MAIN; g.name = "vdw_grungit"
    L.new(mtex.outputs["Color"], g.inputs["Grungit Mask"])
    L.new(grp.outputs["Color Bake"], g.inputs["Base Color 1"]); L.new(grp.outputs["Roughness Bake"], g.inputs["Roughness 1"])
    if "Metallic Bake" in grp.outputs: L.new(grp.outputs["Metallic Bake"], g.inputs["Metallic 1"])
    else: g.inputs["Metallic 1"].default_value = 0.0
    g.inputs["Base Color 2"].default_value = worn; g.inputs["Metallic 2"].default_value = worn_metal
    if slot == "wood" and T.get("paint"):
        # painted wood (the tackle box): the paint on top with the grain faintly through it, worn back to the bare wood
        # (the Sanctus wood itself, not a flat colour) along the edges and scratches
        mx = N.new("ShaderNodeMix"); mx.data_type = 'RGBA'; mx.blend_type = 'OVERLAY'; mx.name = "vdw_paint"
        mx.inputs["Factor"].default_value = float(os.environ.get("VDW_PAINT_GRAIN", "0.35"))
        mx.inputs[6].default_value = (*T["paint"], 1.0); L.new(grp.outputs["Color Bake"], mx.inputs[7])
        L.new(mx.outputs[2], g.inputs["Base Color 1"]); L.new(grp.outputs["Color Bake"], g.inputs["Base Color 2"])
        for l in list(g.inputs["Roughness 1"].links): L.remove(l)
        g.inputs["Roughness 1"].default_value = 0.5; g.inputs["Roughness 2"].default_value = 0.7
    if not (slot == "wood" and T.get("paint")): g.inputs["Roughness 2"].default_value = 0.35 if worn_metal > 0.5 else 0.7
    g.inputs["Transition Color"].default_value = worn; g.inputs["Transition Amount"].default_value = 0.0
    g.inputs["Global Control"].default_value = wear * 0.7; g.inputs["Edge Wear Spread"].default_value = 0.5
    g.inputs["Scratch Amount"].default_value = 0.6 if worn_metal > 0.5 else 0.3
    g.inputs["Cracks Amount"].default_value = 0.25 if slot == "wood" else 0.0; g.inputs["Grunge Amount"].default_value = float(os.environ.get("VDW_GRUNGE", "0.45"))
    g.inputs["Scale"].default_value = 1.0 / max(LENGTH, 0.1)
    d = N.new("ShaderNodeGroup"); d.node_tree = G_DIRT; d.name = "vdw_dirt"
    L.new(mtex.outputs["Color"], d.inputs["Grungit Mask"])
    for a in ("Base Color", "Metallic", "Roughness", "Normal"):
        if a in g.outputs and a in d.inputs: L.new(g.outputs[a], d.inputs[a])
    if "Normal Bake" in grp.outputs and "Normal" in g.inputs: L.new(grp.outputs["Normal Bake"], g.inputs["Normal"])
    d.inputs["Dirt Base Color"].default_value = dirt_col; d.inputs["Overall Amount"].default_value = min(1.0, dirt + float(os.environ.get("VDW_DIRT_ADD", "0.15"))); d.inputs["AO"].default_value = 0.5
    bs = N.new("ShaderNodeBsdfPrincipled"); bs.name = "vdw_bsdf"
    for a, b in (("Color", "Base Color"), ("Metallic", "Metallic"), ("Roughness", "Roughness"), ("Normal", "Normal")): L.new(d.outputs[a], bs.inputs[b])
    out = next(n for n in N if n.type == 'OUTPUT_MATERIAL' and n.is_active_output); L.new(bs.outputs["BSDF"], out.inputs["Surface"])
    em = N.new("ShaderNodeEmission"); em.name = "vdw_emit"
    tg = N.new("ShaderNodeTexImage"); tg.name = "vdw_target"
    return m

names = [m.name for m in me.materials]
mats = [build(s) for s in SLOTS]
idx = {n: i for i, n in enumerate(names)}
remap = [SLOTS.index(n) if n in SLOTS else 0 for n in names]
before = [remap[p.material_index] for p in me.polygons]          # clearing the slots resets every face to the first
me.materials.clear()
for m in mats: me.materials.append(m)
for p, i in zip(me.polygons, before): p.material_index = i
print(f"BAKE {TIER}: " + ", ".join(f"{s} {sum(1 for p in me.polygons if p.material_index == i)} faces" for i, s in enumerate(SLOTS)))

sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = SAMPLES
sc.render.bake.margin = 8; sc.render.bake.use_clear = True
for o in bpy.context.view_layer.objects: o.select_set(o is box)
bpy.context.view_layer.objects.active = box
if "Armature" in box.modifiers: box.modifiers["Armature"].show_render = False
def set_target(img):
    for m in mats:
        t = m.node_tree.nodes["vdw_target"]; t.image = img
        for n in m.node_tree.nodes: n.select = False
        t.select = True; m.node_tree.nodes.active = t
# The inside of the box: a small closed space, all of it "tucked in" - baked shut, the Grungit mask read it as one deep
# cavity (Grungit Dirt filled it with dirt) and the edge shading went near black. So the surfaces inside the walls get
# their mask and shading baked with the lid open (VDW_AO_OPEN degrees; the tackle box's 105 by default; the shading over
# a shorter VDW_AO_DIST_INSIDE), and everything outside keeps the lid-shut bake (open, the lid's back edge pressed
# against the box and came out smudged).
AO_IN = float(os.environ.get("VDW_AO_DIST_INSIDE", "0.012"))
AO_OPEN = float(os.environ.get("VDW_AO_OPEN", "105" if KIND == "tacklebox" else "0"))
# the inside: within the walls' inner faces, from the floor up to the lid's underside (half sizes and heights, metres)
INSIDE = [float(v) for v in os.environ.get("VDW_INSIDE", "0.2015,0.0915,0.02,0.1775" if KIND == "tacklebox" else "0.272,0.142,0.035,0.3175").split(",")]
def bake_value(make, name, float_buf=True):
    """bakes, on every part, the colour socket make(nodes) gives as emission; returns its rgb"""
    img = bpy.data.images.new(name, SIZE, SIZE, alpha=False, float_buffer=float_buf); img.colorspace_settings.name = 'Non-Color'
    for m in mats:
        N, L = m.node_tree.nodes, m.node_tree.links; em = N["vdw_emit"]; out = next(n for n in N if n.type == 'OUTPUT_MATERIAL' and n.is_active_output)
        for l in list(em.inputs["Color"].links): L.remove(l)
        L.new(make(N), em.inputs["Color"]); L.new(em.outputs["Emission"], out.inputs["Surface"])
    set_target(img); bpy.ops.object.bake(type='EMIT')
    a = np.empty(SIZE * SIZE * 4, np.float32); img.pixels.foreach_get(a); return a.reshape(SIZE, SIZE, 4)[..., :3]
_rig = box.parent if box.parent and box.parent.type == 'ARMATURE' else None
def lid_open(on):
    if not AO_OPEN or _rig is None or "Armature" not in box.modifiers: return False
    pb = _rig.pose.bones["lid"]; pb.rotation_mode = 'XYZ'; pb.rotation_euler = (np.radians(AO_OPEN) if on else 0, 0, 0)
    box.modifiers["Armature"].show_render = on; bpy.context.view_layer.update(); return True
Prest = bake_value(lambda N: N.new("ShaderNodeNewGeometry").outputs["Position"], "bake_pos_rest")   # lid shut
inside = (np.abs(Prest[..., 0]) < INSIDE[0]) & (np.abs(Prest[..., 1]) < INSIDE[1]) & (Prest[..., 2] > INSIDE[2]) & (Prest[..., 2] < INSIDE[3])
# and the rim where lid meets box (the walls' top edges, the lid's underside round its edge): hidden shut, seen open
RIM = [float(v) for v in os.environ.get("VDW_RIM", "0.2275,0.1175,0.171,0.1778" if KIND == "tacklebox" else "0,0,0,0").split(",")]
inside |= (np.abs(Prest[..., 0]) < RIM[0]) & (np.abs(Prest[..., 1]) < RIM[1]) & (Prest[..., 2] > RIM[2]) & (Prest[..., 2] < RIM[3])
if not AO_OPEN: inside[:] = False
print(f"BAKE inside the box: {int(inside.sum())} pixels")
# the Grungit mask (AO / edges / cavities), as the add-on's Baker makes it
mm = bpy.data.materials.new("cool_maskbake"); mm.use_nodes = True; mn, ml = mm.node_tree.nodes, mm.node_tree.links
for n in list(mn):
    if n.type != 'OUTPUT_MATERIAL': mn.remove(n)
bk = mn.new("ShaderNodeGroup"); bk.node_tree = G_BAKER; bk.inputs["Scale"].default_value = 0.5 * LENGTH
ml.new(bk.outputs["Output"], next(n for n in mn if n.type == 'OUTPUT_MATERIAL').inputs["Surface"])
mt = mn.new("ShaderNodeTexImage"); mt.image = mask_img; mn.active = mt
saved = [p.material_index for p in me.polygons]; me.materials.append(mm)
for p in me.polygons: p.material_index = len(me.materials) - 1
bpy.ops.object.bake(type='EMIT')
if inside.any() and lid_open(True):
    shut = np.empty(SIZE * SIZE * 4, np.float32); mask_img.pixels.foreach_get(shut)
    bpy.ops.object.bake(type='EMIT'); lid_open(False)
    opened = np.empty(SIZE * SIZE * 4, np.float32); mask_img.pixels.foreach_get(opened)
    sel = np.repeat(inside.ravel(), 4)
    mask_img.pixels.foreach_set(np.where(sel, opened, shut)); mask_img.update()
print(f"BAKE mask done (inside with the lid open {AO_OPEN:.0f} deg)")
mask_img.filepath_raw = os.path.join(TEXDIR, f"{PREFIX}_{TIER}_GrungitMask.png"); mask_img.file_format = 'PNG'; mask_img.save()
for p, i in zip(me.polygons, saved): p.material_index = i
me.materials.pop(index=len(me.materials) - 1)

def channel(socket):
    img = bpy.data.images.new(f"bake_{socket}", SIZE, SIZE, alpha=False)
    if socket != "Color": img.colorspace_settings.name = 'Non-Color'
    for m in mats:
        N, L = m.node_tree.nodes, m.node_tree.links; em = N["vdw_emit"]; out = next(n for n in N if n.type == 'OUTPUT_MATERIAL' and n.is_active_output)
        for l in list(em.inputs["Color"].links): L.remove(l)
        inp = N["vdw_bsdf"].inputs["Base Color" if socket == "Color" else socket]      # whatever feeds the shader
        if inp.links: L.new(inp.links[0].from_socket, em.inputs["Color"])
        else: v = inp.default_value; em.inputs["Color"].default_value = tuple(v) if hasattr(v, "__len__") else (v, v, v, 1)
        L.new(em.outputs["Emission"], out.inputs["Surface"])
    set_target(img); bpy.ops.object.bake(type='EMIT')
    a = np.empty(SIZE * SIZE * 4, np.float32); img.pixels.foreach_get(a); return a.reshape(SIZE, SIZE, 4)
col = channel("Color"); met = channel("Metallic"); rough = channel("Roughness"); print("BAKE colour, metal, roughness done")
for m in mats:
    N, L = m.node_tree.nodes, m.node_tree.links
    L.new(N["vdw_bsdf"].outputs["BSDF"], next(n for n in N if n.type == 'OUTPUT_MATERIAL' and n.is_active_output).inputs["Surface"])
nimg = bpy.data.images.new("bake_normal", SIZE, SIZE, alpha=False); nimg.colorspace_settings.name = 'Non-Color'
set_target(nimg); sc.render.bake.normal_space = 'TANGENT'; bpy.ops.object.bake(type='NORMAL'); print("BAKE normal done")
nrm = np.empty(SIZE * SIZE * 4, np.float32); nimg.pixels.foreach_get(nrm); nrm = nrm.reshape(SIZE, SIZE, 4)
# edge shading: an ambient occlusion bake (the gaps between boards, where boards meet the posts, under the lid's
# overhang, round the fittings) darkens the colour, so the chest shows its depth in game light too
SHADE = float(os.environ.get("VDW_EDGE_SHADE", "0.6")); AO_DIST = float(os.environ.get("VDW_AO_DIST", "0.04"))
if SHADE > 0:
    def ao_of(dist):
        def make(N):
            ao = N.new("ShaderNodeAmbientOcclusion"); ao.samples = 16; ao.inputs["Distance"].default_value = dist; return ao.outputs["AO"]
        return bake_value(make, f"bake_ao_{dist}")[..., 0]
    aop = ao_of(AO_DIST)                                   # lid shut
    if inside.any() and lid_open(True):
        aop = np.where(inside, ao_of(AO_IN), aop); lid_open(False)
    print(f"BAKE edge shading: lid open {AO_OPEN:.0f} deg, inside {int(inside.sum())} pixels at {AO_IN * 100:.1f} cm")
    shade = 1.0 - SHADE * (1.0 - np.clip(aop, 0, 1))
    # the colour is sRGB values: shade it in linear light
    lin = np.where(col[..., :3] <= 0.04045, col[..., :3] / 12.92, ((col[..., :3] + 0.055) / 1.055) ** 2.4) * shade[..., None]
    col[..., :3] = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(np.maximum(lin, 0), 1 / 2.4) - 0.055)
    for m in mats:
        N, L = m.node_tree.nodes, m.node_tree.links
        L.new(N["vdw_bsdf"].outputs["BSDF"], next(n for n in N if n.type == 'OUTPUT_MATERIAL' and n.is_active_output).inputs["Surface"])
    print(f"BAKE edge shading: AO within {AO_DIST * 100:.0f} cm, {SHADE:.0%} at the darkest; average {shade.mean():.2f}")
# the rune line (t4): a band of marks round the outside of the top rail, glowing - an Emission map, and the albedo
# there in the glow's colour, darker
emit = None
if T.get("glow"):
    def emit_bake(make, name):
        img = bpy.data.images.new(name, SIZE, SIZE, alpha=False, float_buffer=True); img.colorspace_settings.name = 'Non-Color'
        for m in mats:
            N, L = m.node_tree.nodes, m.node_tree.links; em = N["vdw_emit"]; out = next(n for n in N if n.type == 'OUTPUT_MATERIAL' and n.is_active_output)
            for l in list(em.inputs["Color"].links): L.remove(l)
            L.new(make(N), em.inputs["Color"]); L.new(em.outputs["Emission"], out.inputs["Surface"])
        set_target(img); bpy.ops.object.bake(type='EMIT')
        a = np.empty(SIZE * SIZE * 4, np.float32); img.pixels.foreach_get(a); return a.reshape(SIZE, SIZE, 4)[..., :3]
    def pos(N): return N.new("ShaderNodeNewGeometry").outputs["Position"]
    def true_nrm(N): return N.new("ShaderNodeNewGeometry").outputs["True Normal"]
    P = emit_bake(pos, "bake_pos"); Nn = emit_bake(true_nrm, "bake_nrm")
    # which pixels are the box's wood: a bake of 1 on the wood material, 0 elsewhere
    for i, m in enumerate(mats):
        N, L = m.node_tree.nodes, m.node_tree.links; em = N["vdw_emit"]; out = next(n for n in N if n.type == 'OUTPUT_MATERIAL' and n.is_active_output)
        for l in list(em.inputs["Color"].links): L.remove(l)
        em.inputs["Color"].default_value = (1, 1, 1, 1) if i == 0 else (0, 0, 0, 1); L.new(em.outputs["Emission"], out.inputs["Surface"])
    wimg = bpy.data.images.new("bake_woodmask", SIZE, SIZE, alpha=False); wimg.colorspace_settings.name = 'Non-Color'
    set_target(wimg); bpy.ops.object.bake(type='EMIT')
    wa = np.empty(SIZE * SIZE * 4, np.float32); wimg.pixels.foreach_get(wa); wood_px = wa.reshape(SIZE, SIZE, 4)[..., 0] > 0.5
    rail_hi = float(os.environ.get("VDW_RUNE_Z1", "0.170")); rail_lo = float(os.environ.get("VDW_RUNE_Z0", "0.157"))
    side = (np.abs(Nn[..., 2]) < 0.3) & ((P[..., 0] * Nn[..., 0] + P[..., 1] * Nn[..., 1]) > 0)   # outward walls
    band = wood_px & side & (P[..., 2] > rail_lo) & (P[..., 2] < rail_hi)
    along = np.where(np.abs(Nn[..., 0]) > 0.5, P[..., 1], P[..., 0])                              # along each wall
    runes = band & (np.sin(along * 420) > -0.15) & (np.sin(along * 37 + P[..., 2] * 900) > -0.6)
    emit = np.zeros_like(col); emit[..., 3] = 1.0; emit[runes, :3] = T["glow"]
    col[runes, :3] = np.array(T["glow"]) * 0.5
    for m in mats:
        N, L = m.node_tree.nodes, m.node_tree.links
        L.new(N["vdw_bsdf"].outputs["BSDF"], next(n for n in N if n.type == 'OUTPUT_MATERIAL' and n.is_active_output).inputs["Surface"])
    print(f"BAKE rune line: {int(runes.sum())} pixels on the top rail")
def save(arr, name, nc):
    im = bpy.data.images.new(name, SIZE, SIZE, alpha=True)
    if nc: im.colorspace_settings.name = 'Non-Color'
    im.pixels.foreach_set(np.ascontiguousarray(arr, np.float32).ravel()); im.filepath_raw = os.path.join(TEXDIR, name); im.file_format = 'PNG'; im.save()
    print("  saved", im.filepath_raw)
save(col, f"{PREFIX}_{TIER}_Unity_Albedo.png", False)
if emit is not None: save(emit, f"{PREFIX}_{TIER}_Unity_Emission.png", False)
ms = np.zeros_like(col); ms[..., :3] = met[..., :1]; ms[..., 3] = 1.0 - rough[..., 0]
save(ms, f"{PREFIX}_{TIER}_Unity_MetallicSmoothness.png", True)
nrm[..., 3] = 1.0; save(nrm, f"{PREFIX}_{TIER}_Unity_Normal.png", True)
if "Armature" in box.modifiers: box.modifiers["Armature"].show_render = True
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f"{PREFIX}_{TIER}_baked.blend"), copy=True)
print("===== END =====")
