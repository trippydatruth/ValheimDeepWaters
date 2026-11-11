# Rebakes the Fisherman's gear trim after the user remodels it in fisher_gear_ingame_*.blend (all gear as worn in game):
#   all from the add-ons (Sanctus + Grungit wear) on the user's own UVs:
#   - belt: pu_leather; buckle: basic_worn_metal in brass
#   - cuff: fabric in the coat's average colour x VDW_CUFF_DARK (oilskin, a shade darker than the coat)
#   - boot_rims: rubber in the boots' colour
#   (carrying the old textures over by a selected-to-active bake smeared: the remodelled pieces are too different)
#   - hat: its UVs put back from the old file (same mesh), so the installed hat textures still fit
#   - the overalls paint (body texture): texels the paint missed round the crotch filled from the paint around them
# Writes everything new to VDW_OUT (never overwrites): <piece>_Unity_*.png, fisher_overalls_paint_<ver>.png (+ _nrm),
# fisher_gear_ingame_v2.blend with it all applied, and preview_front/back/side.png.
#   blender -b <user's fisher_gear_ingame_v1.blend> --python bake_gear_trim.py
#   env: VDW_OLD (the blend with the installed pieces, e.g. the .blend1), VDW_OUT, VDW_UNITY (Assets\DeepWaters),
#        VDW_SIZE (1024, the most), VDW_CUFF_DARK (1.05), VDW_PAINT_VER (v4)
import bpy, os, math, numpy as np
from mathutils import Vector

OLD, OUT, U = os.environ["VDW_OLD"], os.environ["VDW_OUT"], os.environ["VDW_UNITY"]
SIZE = min(1024, int(os.environ.get("VDW_SIZE", "1024"))); DARK = float(os.environ.get("VDW_CUFF_DARK", "1.05"))   # the weave and wear darken it a little more
VER = os.environ.get("VDW_PAINT_VER", "v4")
if os.path.exists(OUT): raise SystemExit("exists, kept: " + OUT)
os.makedirs(OUT)
SANCTUS = os.path.join(os.environ["APPDATA"], rf"Blender Foundation\Blender\{bpy.app.version[0]}.{bpy.app.version[1]}\extensions\user_default\sanctus_library_starter\lib\materials")
GRUNGIT = os.path.join(os.environ["APPDATA"], rf"Blender Foundation\Blender\{bpy.app.version[0]}.{bpy.app.version[1]}\scripts\addons\Grungit\grungit_data\Materials.blend")

for o in list(bpy.data.objects):
    if o.mode != 'OBJECT' and o.name in bpy.context.view_layer.objects:
        bpy.context.view_layer.objects.active = o; bpy.ops.object.mode_set(mode='OBJECT')
arm = bpy.data.objects["Armature"]
for pb in arm.pose.bones: pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.rotation_euler = (0, 0, 0); pb.scale = (1, 1, 1)
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 16
sc.render.bake.margin = 16

def px(img):
    w, h = img.size; a = np.empty(w * h * 4, np.float32); img.pixels.foreach_get(a); return a.reshape(h, w, 4)
def save(arr, path, nc=False):
    if os.path.exists(path): raise SystemExit("exists: " + path)
    h, w = arr.shape[:2]; im = bpy.data.images.new(os.path.basename(path), w, h, alpha=True)
    if nc: im.colorspace_settings.name = 'Non-Color'
    im.pixels.foreach_set(np.ascontiguousarray(arr, np.float32).ravel()); im.filepath_raw = path; im.file_format = 'PNG'; im.save()
    print("  saved", os.path.basename(path)); return im
def load(path, nc=False):
    im = bpy.data.images.load(path, check_existing=True)
    if nc: im.colorspace_settings.name = 'Non-Color'
    return im

# ------------------------------------------------------------------ the installed hat, for its UVs
with bpy.data.libraries.load(OLD, link=False) as (src, dst):
    dst.objects = [n for n in src.objects if n == "hat"]
old = {}
for o in dst.objects:
    base = o.name.split(".")[0]; o.name = "old_" + base; o.parent = None
    for m in list(o.modifiers): o.modifiers.remove(m)
    sc.collection.objects.link(o); old[base] = o
    o.matrix_world = bpy.data.objects[base].matrix_world.copy()      # same place as before (both on the same rig)
bpy.context.view_layer.update()

# hat: its old UVs back
hat, oh = bpy.data.objects["hat"], old["hat"]
assert len(hat.data.loops) == len(oh.data.loops), "hat mesh changed"
uvn, uvo = hat.data.uv_layers.active.data, oh.data.uv_layers.active.data
for i in range(len(uvn)): uvn[i].uv = uvo[i].uv
print("HAT UVs put back")

# the pieces bake at rest, without their rig
saved_mods = {}
for n in ("boot_rims", "cuff", "belt", "buckle"):
    o = bpy.data.objects[n]; saved_mods[n] = [(m, m.show_render, m.show_viewport) for m in o.modifiers]
    for m in o.modifiers: m.show_render = m.show_viewport = False
bpy.context.view_layer.update()

def tex(N, path, nc=False, alpha=False):
    t = N.new("ShaderNodeTexImage"); t.image = load(path, nc); return t.outputs["Alpha" if alpha else "Color"]

def write_set(prefix, col, met, smo, nrm):
    a = col.copy(); a[..., 3] = 1; save(a, os.path.join(OUT, f"{prefix}_Unity_Albedo.png"))
    ms = met.copy(); ms[..., 3] = smo[..., 0]; save(ms, os.path.join(OUT, f"{prefix}_Unity_MetallicSmoothness.png"), True)
    n = nrm.copy(); n[..., 3] = 1; save(n, os.path.join(OUT, f"{prefix}_Unity_Normal.png"), True)

# ------------------------------------------------------------------ belt (leather) and buckle (brass), from the add-ons
with bpy.data.libraries.load(GRUNGIT) as (src, dst): dst.node_groups = ["Grungit v1.9.1", "Grungit Dirt v1.9.1", "Baker v1.8.3"]
G_MAIN, G_DIRT, G_BAKER = dst.node_groups

def addon_set(obj, rel, inputs, worn, metallic2, size, length):
    with bpy.data.libraries.load(os.path.join(SANCTUS, rel)) as (src, dst):
        dst.materials = ["basic_worn_metal_01" if "basic_worn_metal_01" in src.materials else src.materials[0]]
    m = dst.materials[0].copy(); nt = m.node_tree; N, L = nt.nodes, nt.links
    grp = next(n for n in N if n.type == 'GROUP' and n.node_tree and 'Bake' in ''.join(o.name for o in n.outputs))
    for k, v in inputs.items():
        if k in grp.inputs: grp.inputs[k].default_value = v
    mask = bpy.data.images.new(obj.name + "_mask", size, size, alpha=False); mask.colorspace_settings.name = 'Non-Color'
    # the Grungit mask from its Baker
    mm = bpy.data.materials.new("maskbake"); mm.use_nodes = True; mn, ml = mm.node_tree.nodes, mm.node_tree.links
    for n in list(mn):
        if n.type != 'OUTPUT_MATERIAL': mn.remove(n)
    bk = mn.new("ShaderNodeGroup"); bk.node_tree = G_BAKER; bk.inputs["Scale"].default_value = 0.5 * length
    ml.new(bk.outputs["Output"], next(n for n in mn if n.type == 'OUTPUT_MATERIAL').inputs["Surface"])
    t = mn.new("ShaderNodeTexImage"); t.image = mask; mn.active = t
    obj.data.materials.clear(); obj.data.materials.append(mm)
    for o in bpy.context.view_layer.objects: o.select_set(o is obj)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.bake(type='EMIT', use_selected_to_active=False, margin=16, use_clear=True)
    mt = N.new("ShaderNodeTexImage"); mt.image = mask
    g = N.new("ShaderNodeGroup"); g.node_tree = G_MAIN
    L.new(mt.outputs["Color"], g.inputs["Grungit Mask"])
    L.new(grp.outputs["Color Bake"], g.inputs["Base Color 1"]); L.new(grp.outputs["Roughness Bake"], g.inputs["Roughness 1"])
    if "Metallic Bake" in grp.outputs: L.new(grp.outputs["Metallic Bake"], g.inputs["Metallic 1"])
    else: g.inputs["Metallic 1"].default_value = 0.0
    if "Normal Bake" in grp.outputs and "Normal" in g.inputs: L.new(grp.outputs["Normal Bake"], g.inputs["Normal"])
    g.inputs["Base Color 2"].default_value = worn; g.inputs["Metallic 2"].default_value = metallic2
    g.inputs["Roughness 2"].default_value = 0.35 if metallic2 > 0.5 else 0.6
    g.inputs["Transition Color"].default_value = worn; g.inputs["Transition Amount"].default_value = 0.0
    g.inputs["Global Control"].default_value = 0.2; g.inputs["Edge Wear Spread"].default_value = 0.5
    g.inputs["Scratch Amount"].default_value = 0.5; g.inputs["Cracks Amount"].default_value = 0.0 if metallic2 > 0.5 else 0.2
    g.inputs["Grunge Amount"].default_value = 0.25; g.inputs["Scale"].default_value = 1.0 / max(length, 0.05)
    d = N.new("ShaderNodeGroup"); d.node_tree = G_DIRT; L.new(mt.outputs["Color"], d.inputs["Grungit Mask"])
    for a in ("Base Color", "Metallic", "Roughness", "Normal"):
        if a in g.outputs and a in d.inputs: L.new(g.outputs[a], d.inputs[a])
    d.inputs["Dirt Base Color"].default_value = (0.12, 0.08, 0.05, 1); d.inputs["Overall Amount"].default_value = 0.2; d.inputs["AO"].default_value = 0.3
    bsdf = N.new("ShaderNodeBsdfPrincipled")
    for a, b in (("Color", "Base Color"), ("Metallic", "Metallic"), ("Roughness", "Roughness"), ("Normal", "Normal")):
        L.new(d.outputs[a], bsdf.inputs[b])
    out = next(n for n in N if n.type == 'OUTPUT_MATERIAL' and n.is_active_output)
    em = N.new("ShaderNodeEmission"); target = N.new("ShaderNodeTexImage")
    obj.data.materials.clear(); obj.data.materials.append(m)
    def bake(sock, nc, kind='EMIT'):
        img = bpy.data.images.new(f"{obj.name}_{sock}", size, size, alpha=False)
        if nc: img.colorspace_settings.name = 'Non-Color'
        for l in list(em.inputs["Color"].links): L.remove(l)
        if kind == 'EMIT': L.new(d.outputs[sock], em.inputs["Color"]); L.new(em.outputs["Emission"], out.inputs["Surface"])
        else: L.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
        target.image = img; N.active = target
        bpy.ops.object.bake(type=kind, use_selected_to_active=False, normal_space='TANGENT', margin=16, use_clear=True); return px(img)
    col = bake("Color", False); met = bake("Metallic", True); rough = bake("Roughness", True); nrm = bake("Normal", True, 'NORMAL')
    smo = 1.0 - rough
    return col, met, smo, nrm

def length_of(o):
    vs = [o.matrix_world @ v.co for v in o.data.vertices]
    return max(max(v[i] for v in vs) - min(v[i] for v in vs) for i in range(3))

belt = bpy.data.objects["belt"]
write_set("belt", *addon_set(belt, r"Fabrics\pu_leather.blend",
                             {"Base Color": (0.075, 0.035, 0.015, 1), "Roughness": 0.55, "Scale": 6.0, "Bump": 0.6},
                             (0.16, 0.09, 0.05, 1), 0.0, SIZE, math.pi * length_of(belt)))
print("BELT Sanctus pu_leather + Grungit")
buckle = bpy.data.objects["buckle"]
write_set("buckle", *addon_set(buckle, r"Metals Worn\basic_worn_metal.blend",
                               {"Base Color": (0.55, 0.38, 0.12, 1), "Color": (0.55, 0.38, 0.12, 1)},
                               (0.75, 0.58, 0.25, 1), 1.0, 256, length_of(buckle)))
print("BUCKLE Sanctus basic_worn_metal (brass) + Grungit")

# cuffs: the coat's oilskin, darker; rims: rubber in the boots' colour (the textures' pixels are sRGB, the add-ons want linear)
def lin(c): return tuple(float(x) ** 2.2 for x in c)
def mean_rgb(path):
    a = px(load(path)); return a[a[..., :3].sum(-1) > 0.05, :3].mean(0)
coat_mean = mean_rgb(os.path.join(U, "fisher_coat_skirt", "coat_Unity_Albedo.png"))
cuff_c = lin(coat_mean * DARK); cuff_c2 = lin(coat_mean * DARK * 0.85)
cuff = bpy.data.objects["cuff"]
write_set("cuff", *addon_set(cuff, r"Fabrics\fabric.blend",
                             {"Fabric Color 1": (*cuff_c, 1), "Fabric Color 2": (*cuff_c2, 1), "Color": (1, 1, 1, 1), "Roughness": 0.45, "AO": 0.3},
                             (*lin(coat_mean * DARK * 1.15), 1), 0.0, SIZE, length_of(cuff)))
print(f"CUFF Sanctus fabric, coat {coat_mean.round(3)} x {DARK} + Grungit")
boot_mean = mean_rgb(os.path.join(U, "fisher_boot_rims", "boots_Unity_Albedo.png"))
rims = bpy.data.objects["boot_rims"]
write_set("boots", *addon_set(rims, r"Synthetics\rubber.blend", {"Color": (*lin(boot_mean), 1)},
                              (*lin(boot_mean * 1.3), 1), 0.0, SIZE, length_of(rims)))
print(f"RIMS Sanctus rubber, boots {boot_mean.round(3)} + Grungit")

# ------------------------------------------------------------------ the overalls paint round the crotch
T = os.path.join(U, "Textures")
body = bpy.data.objects["body_painted"]; bm = body.data; Mw = body.matrix_world
ov = px(load(os.path.join(T, "fisher_overalls_paint_v3.png"))); on = px(load(os.path.join(T, "fisher_overalls_paint_v3_nrm.png"), True))
H, W = ov.shape[:2]; region = np.zeros((H, W), bool); uvd = bm.uv_layers.active.data
for p in bm.polygons:
    c = Mw @ p.center
    if abs(c.x) < 0.14 and 0.76 < c.z < 1.12:
        uvs = np.array([uvd[l].uv for l in p.loop_indices]) * (W, H)
        for k in range(1, len(uvs) - 1):                               # each triangle of the face, padded 3 px
            tri = uvs[[0, k, k + 1]]; lo = np.floor(tri.min(0) - 3).astype(int); hi = np.ceil(tri.max(0) + 3).astype(int)
            xs, ys = np.meshgrid(np.arange(lo[0], hi[0]), np.arange(lo[1], hi[1]))
            P = np.stack([xs + 0.5, ys + 0.5], -1); a, b, cc = tri
            v0, v1 = b - a, cc - a; den = v0[0] * v1[1] - v1[0] * v0[1]
            if abs(den) < 1e-9: continue
            w1 = ((P[..., 0] - a[0]) * v1[1] - v1[0] * (P[..., 1] - a[1])) / den
            w2 = (v0[0] * (P[..., 1] - a[1]) - (P[..., 0] - a[0]) * v0[1]) / den
            pad = 3.0 / max(np.linalg.norm(v0), np.linalg.norm(v1), 1)
            inside = (w1 >= -pad) & (w2 >= -pad) & (w1 + w2 <= 1 + pad)
            region[np.clip(ys[inside], 0, H - 1), np.clip(xs[inside], 0, W - 1)] = True
hole = region & (ov[..., 3] < 0.999)
print(f"CROTCH {int(region.sum())} texels in the area, {int(hole.sum())} not fully covered")
known = ~hole
for it in range(200):                                                # fill from the paint around, a ring at a time
    if not (~known & region).any(): break
    acc = np.zeros_like(ov); accn = np.zeros_like(on); cnt = np.zeros((H, W), np.float32)
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        k = np.roll(known, (dy, dx), (0, 1)); acc += np.roll(ov, (dy, dx), (0, 1)) * k[..., None]
        accn += np.roll(on, (dy, dx), (0, 1)) * k[..., None]; cnt += k
    grow = ~known & region & (cnt > 0)
    ov[grow] = acc[grow] / cnt[grow, None]; on[grow] = accn[grow] / cnt[grow, None]; known |= grow
ov[hole, 3] = 1.0; on[hole, 3] = 1.0
save(ov, os.path.join(OUT, f"fisher_overalls_paint_{VER}.png")); save(on, os.path.join(OUT, f"fisher_overalls_paint_{VER}_nrm.png"), True)

# ------------------------------------------------------------------ the gear with the new textures, for a look
for o in old.values(): bpy.data.objects.remove(o)
for n, mods in saved_mods.items():
    for m, r, v in mods: m.show_render, m.show_viewport = r, v
def unity_mat(name, a, ms, n):
    m = bpy.data.materials.new(name); m.use_nodes = True; N, L = m.node_tree.nodes, m.node_tree.links; bs = N["Principled BSDF"]
    L.new(tex(N, a), bs.inputs["Base Color"])
    if ms and os.path.exists(ms):
        t = N.new("ShaderNodeTexImage"); t.image = load(ms, True); sep = N.new("ShaderNodeSeparateColor"); L.new(t.outputs["Color"], sep.inputs["Color"])
        L.new(sep.outputs["Red"], bs.inputs["Metallic"]); inv = N.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1
        L.new(t.outputs["Alpha"], inv.inputs[1]); L.new(inv.outputs[0], bs.inputs["Roughness"])
    if n and os.path.exists(n):
        nm = N.new("ShaderNodeNormalMap"); L.new(tex(N, n, True), nm.inputs["Color"]); L.new(nm.outputs["Normal"], bs.inputs["Normal"])
    return m
for obj, pre in ((rims, "boots"), (cuff, "cuff"), (belt, "belt"), (buckle, "buckle")):
    obj.data.materials.clear(); obj.data.materials.append(unity_mat(pre, *(os.path.join(OUT, f"{pre}_Unity_{c}.png") for c in ("Albedo", "MetallicSmoothness", "Normal"))))
# the body's overalls layer -> the fixed paint
for n in body.data.materials[0].node_tree.nodes:
    if n.type == 'TEX_IMAGE' and n.image and n.image.name.startswith("fisher_overalls_paint_v3"):
        n.image = load(os.path.join(OUT, f"fisher_overalls_paint_{VER}.png")); n.label = f"fisher_overalls_paint_{VER}"
bpy.data.orphans_purge(do_recursive=True)
for i in bpy.data.images:
    if i.source == 'FILE' and i.filepath and os.path.exists(bpy.path.abspath(i.filepath)) and not i.packed_file: i.pack()
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "fisher_gear_ingame_v2.blend"), copy=True)
print("SAVED fisher_gear_ingame_v2.blend")
