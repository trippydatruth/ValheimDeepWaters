# Bakes a food model made of several objects and materials (e.g. the user's Mesh\custom food\Stew.blend: a Sanctus wood
# bowl, Poliigon broth, carrots, corn, peas and a hand-painted fish) into ONE texture set on one mesh, for the game.
#   - every visible mesh is joined into one object (same transform kept, so procedural textures don't shift), and given
#     a new non-overlapping UV layout; the materials still read their own UVs while baking
#   - Sanctus materials (a group with "Color Bake" outputs, like the bowl's generic_wood) get light Grungit wear and dirt
#     (edges, scratches, dirt in the cavities); plain and painted materials (the food) are baked as they are
#   - writes <out>/<key>/<key>_model.fbx + <key>_Unity_{Albedo,MetallicSmoothness,Normal}.png, the model at real size,
#     standing on the origin; plus <key>_baked.blend. Never touches the source file. New folders only.
#   blender -b Stew.blend --factory-startup --python bake_food.py   env: VDW_OUT (new folder), VDW_KEY, VDW_SIZE (1024, the most),
#   VDW_SAMPLES (32), VDW_WEAR (0.12), VDW_DIRT (0.15)
import bpy, os
import numpy as np

OUT = os.environ["VDW_OUT"]; KEY = os.environ.get("VDW_KEY", "food_fishermans_stew")
SIZE = min(1024, int(os.environ.get("VDW_SIZE", "1024"))); SAMPLES = int(os.environ.get("VDW_SAMPLES", "32"))   # textures: 1K at most (low-poly game)
DIR = os.path.join(OUT, KEY)
if os.path.exists(DIR): raise SystemExit("exists, kept: " + DIR)
os.makedirs(DIR)
GRUNGIT = os.path.join(os.environ["APPDATA"], rf"Blender Foundation\Blender\{bpy.app.version[0]}.{bpy.app.version[1]}\scripts\addons\Grungit\grungit_data\Materials.blend")

sc = bpy.context.scene
meshes = [o for o in sc.objects if o.type == 'MESH' and not o.hide_render and o.visible_get()]
if not meshes: raise SystemExit("no meshes")
main = max(meshes, key=lambda o: max(o.dimensions))
print("FOOD joining", [o.name for o in meshes], "into", main.name)

# 1. one object (the others take the main one's transform; here they all share it)
bpy.ops.object.mode_set(mode='OBJECT') if bpy.context.object and bpy.context.object.mode != 'OBJECT' else None
for o in sc.objects: o.select_set(o in meshes)
bpy.context.view_layer.objects.active = main
bpy.ops.object.join()
obj = bpy.context.view_layer.objects.active; obj.name = KEY; me = obj.data; me.name = KEY
src_uv = me.uv_layers[0].name

# VDW_SWAP="slot=other.blend|material": a plain material slot takes a material from another file (e.g. a board with
# no texture takes the stew bowl's Sanctus wood, so the dishes match). Sanctus materials then get Grungit as usual.
for spec in [s for s in os.environ.get("VDW_SWAP", "").split(";") if "=" in s]:
    slot, rest = spec.split("=", 1); path, name = rest.rsplit("|", 1)
    with bpy.data.libraries.load(path) as (src, dst): dst.materials = [name]
    new = dst.materials[0]
    if new is None: raise SystemExit(f"no material {name} in {path}")
    for i, m in enumerate(me.materials):
        if m and m.name == slot: me.materials[i] = new; print(f"FOOD {slot}: takes {name} from {os.path.basename(path)}")

# 2. every texture in every material reads the original UVs explicitly (the bake layout is added next)
def uvnode(nt, name):
    n = nt.nodes.new("ShaderNodeUVMap"); n.uv_map = name; return n
for m in me.materials:
    if not m or not m.use_nodes: continue
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type == 'TEX_IMAGE' and not n.inputs["Vector"].is_linked:
            nt.links.new(uvnode(nt, src_uv).outputs["UV"], n.inputs["Vector"])
        if n.type == 'TEX_COORD' and n.outputs["UV"].is_linked:
            u = uvnode(nt, src_uv)
            for l in list(n.outputs["UV"].links): nt.links.new(u.outputs["UV"], l.to_socket)
FIT = [s for s in os.environ.get("VDW_FIT", "").split(",") if s]
me.uv_layers.active = me.uv_layers[src_uv]
bake_uv = me.uv_layers.new(name="bake", do_init=True)          # a copy of the model's own UVs
me.uv_layers[src_uv].active_render = True; me.uv_layers.active = bake_uv

def fit_into_free_space(names):
    """Keeps the model's own UV layout and moves only these materials' UV islands, together, scaled to the largest
    empty rectangle left in the 0-1 square (turned 90 degrees if that fits bigger)."""
    import bmesh
    bm = bmesh.new(); bm.from_mesh(me); uvl = bm.loops.layers.uv["bake"]
    idx = {i for i, m in enumerate(me.materials) if m and m.name in names}
    G = 256; occ = np.zeros((G, G), bool)
    for f in bm.faces:
        if f.material_index in idx: continue
        pts = [l[uvl].uv.copy() for l in f.loops]
        for k in range(1, len(pts) - 1):
            a, b, c = pts[0], pts[k], pts[k + 1]
            area = (b.x - a.x) * (c.y - a.y) - (c.x - a.x) * (b.y - a.y)
            x0 = max(0, int(min(a.x, b.x, c.x) * G) - 1); x1 = min(G - 1, int(max(a.x, b.x, c.x) * G) + 1)
            y0 = max(0, int(min(a.y, b.y, c.y) * G) - 1); y1 = min(G - 1, int(max(a.y, b.y, c.y) * G) + 1)
            if x1 < x0 or y1 < y0: continue
            if abs(area) < 1e-12: occ[y0:y1 + 1, x0:x1 + 1] = True; continue
            yy, xx = np.mgrid[y0:y1 + 1, x0:x1 + 1]; px_ = (xx + 0.5) / G; py_ = (yy + 0.5) / G
            w0 = ((b.x - px_) * (c.y - py_) - (c.x - px_) * (b.y - py_)) / area
            w1 = ((c.x - px_) * (a.y - py_) - (a.x - px_) * (c.y - py_)) / area
            ins = (w0 >= -0.01) & (w1 >= -0.01) & (1 - w0 - w1 >= -0.01)
            occ[yy[ins], xx[ins]] = True
    # a small gap around what's there, so bake margins don't bleed into the moved islands
    pad = 3; o2 = occ.copy()
    for dy in range(-pad, pad + 1):
        for dx in range(-pad, pad + 1):
            o2 |= np.roll(np.roll(occ, dy, 0), dx, 1)
    o2[:pad, :] = o2[-pad:, :] = True; o2[:, :pad] = o2[:, -pad:] = True
    # largest empty rectangle (histogram method)
    best = (0, 0, 0, 0, 0)   # area, x, y, w, h  in cells
    hgt = np.zeros(G, int)
    for y in range(G):
        hgt = np.where(o2[y], 0, hgt + 1); st = []
        for x in range(G + 1):
            h = hgt[x] if x < G else 0; start = x
            while st and st[-1][1] >= h:
                s, sh = st.pop(); a_ = sh * (x - s)
                if a_ > best[0]: best = (a_, s, y - sh + 1, x - s, sh)
                start = s
            st.append((start, h))
    _, rx, ry, rw, rh = best
    loops = [l for f in bm.faces if f.material_index in idx for l in f.loops]
    us = np.array([[l[uvl].uv.x, l[uvl].uv.y] for l in loops]); lo_, hi_ = us.min(0), us.max(0); size = hi_ - lo_
    W, H = rw / G, rh / G
    s_up = min(W / size[0], H / size[1]); s_rot = min(W / size[1], H / size[0])
    rot = s_rot > s_up; s = max(s_up, s_rot) * 0.98
    for l in loops:
        u = (l[uvl].uv.x - lo_[0]); v = (l[uvl].uv.y - lo_[1])
        if rot: u, v = v, size[0] - u
        bw, bh = (size[1], size[0]) if rot else (size[0], size[1])
        l[uvl].uv.x = rx / G + (W - bw * s) / 2 + u * s
        l[uvl].uv.y = ry / G + (H - bh * s) / 2 + v * s
    bm.to_mesh(me); bm.free()
    print(f"FOOD {', '.join(names)}: fitted into the free space at ({rx / G:.2f}, {ry / G:.2f}) {W:.2f} x {H:.2f}, "
          f"scale {s:.2f}{', turned' if rot else ''}; everything else keeps its own UVs")

if FIT:
    fit_into_free_space(FIT)
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
if not FIT: bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.006, area_weight=0.0, scale_to_bounds=False)
# parts that deserve more of the texture (a hand-painted piece), e.g. VDW_FOCUS="fish:2.5": their UVs are scaled up
# before packing, so they keep their detail
focus = dict((k, float(v)) for k, v in (p.split(":") for p in os.environ.get("VDW_FOCUS", "").split(",") if ":" in p))
if focus and not FIT:
    import bmesh
    bpy.ops.object.mode_set(mode='OBJECT')
    bm = bmesh.new(); bm.from_mesh(me); uvl = bm.loops.layers.uv["bake"]
    for name, k in focus.items():
        idx = next((i for i, m in enumerate(me.materials) if m and m.name == name), None)
        if idx is None: continue
        loops = [l for f in bm.faces if f.material_index == idx for l in f.loops]
        if not loops: continue
        cx = sum(l[uvl].uv.x for l in loops) / len(loops); cy = sum(l[uvl].uv.y for l in loops) / len(loops)
        for l in loops: l[uvl].uv.x = cx + (l[uvl].uv.x - cx) * k; l[uvl].uv.y = cy + (l[uvl].uv.y - cy) * k
        print(f"FOOD {name}: {k}x the texture space")
    bm.to_mesh(me); bm.free()
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
if not FIT: bpy.ops.uv.pack_islands(margin=0.004)    # with VDW_FIT the model's own layout is kept as it is
bpy.ops.object.mode_set(mode='OBJECT')
print("FOOD bake layout made:", len(me.polygons), "faces")

co = np.array([v.co[:] for v in me.vertices]); LENGTH = float((co.max(0) - co.min(0)).max())

# 3. per material: where its colour, metallic, roughness come from, and the surface used for the normal bake
with bpy.data.libraries.load(GRUNGIT) as (src, dst): dst.node_groups = ["Grungit v1.9.1", "Grungit Dirt v1.9.1", "Baker v1.8.3"]
G_MAIN, G_DIRT, G_BAKER = dst.node_groups
mask_img = bpy.data.images.new(KEY + "_mask", SIZE, SIZE, alpha=False); mask_img.colorspace_settings.name = 'Non-Color'
def output(nt): return next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL' and n.is_active_output)

any_sanctus = False
import math
GRILL = [s for s in os.environ.get("VDW_GRILL", "").split(",") if s]
GRILL_GAP = float(os.environ.get("VDW_GRILL_GAP", "0.03")); GRILL_ANGLE = float(os.environ.get("VDW_GRILL_ANGLE", "60")); GRILL_OFFSET = float(os.environ.get("VDW_GRILL_OFFSET", "0"))
OBJ_SCALE = max(obj.matrix_world.to_scale().x, 1e-6)   # the joined object keeps its scale: object units x this = metres
chan = {}   # material name -> {"Color": socket|value, "Metallic": ..., "Roughness": ..., "surface": socket}
for m in me.materials:
    nt = m.node_tree; N, L = nt.nodes, nt.links; out = output(nt)
    surf = out.inputs["Surface"].links[0].from_socket if out.inputs["Surface"].is_linked else None
    sanctus = surf.node if surf is not None and surf.node.type == 'GROUP' and "Color Bake" in surf.node.outputs else None
    if sanctus is not None:
        # Sanctus wood/metal: Grungit edge wear, scratches and dirt on top (like the tackle boxes and coolers)
        mtex = N.new("ShaderNodeTexImage"); mtex.image = mask_img; mtex.interpolation = 'Linear'
        L.new(uvnode(nt, "bake").outputs["UV"], mtex.inputs["Vector"])
        g = N.new("ShaderNodeGroup"); g.node_tree = G_MAIN
        L.new(mtex.outputs["Color"], g.inputs["Grungit Mask"])
        L.new(sanctus.outputs["Color Bake"], g.inputs["Base Color 1"])
        L.new(sanctus.outputs["Roughness Bake"], g.inputs["Roughness 1"])
        g.inputs["Metallic 1"].default_value = 0.0
        if "Normal" in g.inputs and "Normal Bake" in sanctus.outputs: L.new(sanctus.outputs["Normal Bake"], g.inputs["Normal"])
        base = tuple(sanctus.inputs["Light Color"].default_value) if "Light Color" in sanctus.inputs else (0.3, 0.2, 0.1, 1)
        worn = tuple(min(1.0, c * 1.6) for c in base[:3]) + (1.0,)
        g.inputs["Base Color 2"].default_value = worn; g.inputs["Metallic 2"].default_value = 0.0; g.inputs["Roughness 2"].default_value = 0.75
        g.inputs["Transition Color"].default_value = worn; g.inputs["Transition Amount"].default_value = 0.0
        g.inputs["Global Control"].default_value = float(os.environ.get("VDW_WEAR", "0.12")); g.inputs["Edge Wear Spread"].default_value = 0.5
        g.inputs["Scratch Amount"].default_value = 0.3; g.inputs["Cracks Amount"].default_value = 0.0; g.inputs["Grunge Amount"].default_value = 0.2
        g.inputs["Scale"].default_value = 1.0 / max(LENGTH, 0.01)
        d = N.new("ShaderNodeGroup"); d.node_tree = G_DIRT
        L.new(mtex.outputs["Color"], d.inputs["Grungit Mask"])
        for a in ("Base Color", "Metallic", "Roughness", "Normal"):
            if a in g.outputs and a in d.inputs: L.new(g.outputs[a], d.inputs[a])
        d.inputs["Dirt Base Color"].default_value = (0.12, 0.08, 0.05, 1)
        d.inputs["Overall Amount"].default_value = float(os.environ.get("VDW_DIRT", "0.15")); d.inputs["AO"].default_value = 0.3
        bsdf = N.new("ShaderNodeBsdfPrincipled")
        L.new(d.outputs["Color"], bsdf.inputs["Base Color"]); L.new(d.outputs["Metallic"], bsdf.inputs["Metallic"])
        L.new(d.outputs["Roughness"], bsdf.inputs["Roughness"]); L.new(d.outputs["Normal"], bsdf.inputs["Normal"])
        chan[m.name] = {"Color": d.outputs["Color"], "Metallic": d.outputs["Metallic"], "Roughness": d.outputs["Roughness"], "Emission": (0.0, 0.0, 0.0, 1.0), "surface": bsdf.outputs["BSDF"]}
        any_sanctus = True
        print("FOOD", m.name, ": Sanctus", sanctus.node_tree.name, "+ Grungit")
    else:
        p = surf.node if surf is not None and surf.node.type == 'BSDF_PRINCIPLED' else next((n for n in N if n.type == 'BSDF_PRINCIPLED'), None)
        def pick(name):
            s = p.inputs[name]
            return s.links[0].from_socket if s.is_linked else (tuple(s.default_value) if hasattr(s.default_value, "__len__") else float(s.default_value))
        chan[m.name] = {"Color": pick("Base Color"), "Metallic": pick("Metallic"), "Roughness": pick("Roughness"), "surface": p.outputs["BSDF"]}
        # glow: the emission colour where the material has some (e.g. cinder scales in an atlas), else none
        es = p.inputs["Emission Strength"].default_value if "Emission Strength" in p.inputs else 0.0
        ec = p.inputs["Emission Color"] if "Emission Color" in p.inputs else None
        chan[m.name]["Emission"] = (ec.links[0].from_socket if ec is not None and ec.is_linked and es > 0
                                    else (tuple(c * es for c in ec.default_value[:3]) + (1.0,) if ec is not None and es > 0 else (0.0, 0.0, 0.0, 1.0)))
        if m.name in GRILL:
            # VDW_GRILL="fillet": browned like it's been cooked, patchy searing, and charred diagonal grill bars laid
            # across its real shape (object space), about GRILL_GAP apart
            src_col = chan[m.name]["Color"]
            def as_socket(v):
                if isinstance(v, bpy.types.NodeSocket): return v
                rgb = N.new("ShaderNodeRGB"); rgb.outputs[0].default_value = v if isinstance(v, tuple) else (v, v, v, 1); return rgb.outputs[0]
            brown = N.new("ShaderNodeMix"); brown.data_type = 'RGBA'; brown.blend_type = 'MULTIPLY'
            brown.inputs["Factor"].default_value = 0.92
            L.new(as_socket(src_col), brown.inputs["A"]); brown.inputs["B"].default_value = (0.66, 0.40, 0.22, 1)
            tc = N.new("ShaderNodeTexCoord")
            noise = N.new("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value = 0.5 * OBJ_SCALE / max(GRILL_GAP, 1e-3)
            noise.inputs["Detail"].default_value = 4; L.new(tc.outputs["Object"], noise.inputs["Vector"])
            sear_r = N.new("ShaderNodeMapRange"); sear_r.inputs["To Min"].default_value = 0.65; sear_r.inputs["To Max"].default_value = 1.05
            L.new(noise.outputs["Fac"], sear_r.inputs["Value"])
            sear = N.new("ShaderNodeMix"); sear.data_type = 'RGBA'; sear.blend_type = 'MULTIPLY'; sear.inputs["Factor"].default_value = 1.0
            L.new(brown.outputs["Result"], sear.inputs["A"]); L.new(sear_r.outputs["Result"], sear.inputs["B"])
            # bars: a 60-degree turn in the fillet's flat plane, then sharp stripes along it
            rot = N.new("ShaderNodeVectorRotate"); rot.rotation_type = 'Z_AXIS'; rot.inputs["Angle"].default_value = math.radians(GRILL_ANGLE)
            L.new(tc.outputs["Object"], rot.inputs["Vector"])
            sep = N.new("ShaderNodeSeparateXYZ"); L.new(rot.outputs["Vector"], sep.inputs["Vector"])
            # VDW_GRILL_OFFSET (metres) slides the bars along, e.g. onto grill marks painted in the texture
            shift = N.new("ShaderNodeMath"); shift.operation = 'SUBTRACT'; shift.inputs[1].default_value = GRILL_OFFSET / OBJ_SCALE
            L.new(sep.outputs["X"], shift.inputs[0])
            div = N.new("ShaderNodeMath"); div.operation = 'DIVIDE'; div.inputs[1].default_value = GRILL_GAP / OBJ_SCALE
            L.new(shift.outputs[0], div.inputs[0])
            frac = N.new("ShaderNodeMath"); frac.operation = 'PINGPONG'; frac.inputs[1].default_value = 0.5; L.new(div.outputs[0], frac.inputs[0])
            bar = N.new("ShaderNodeMapRange"); bar.inputs["From Min"].default_value = 0.035; bar.inputs["From Max"].default_value = 0.05
            bar.inputs["To Min"].default_value = 0.95; bar.inputs["To Max"].default_value = 0.0; L.new(frac.outputs[0], bar.inputs["Value"])
            char = N.new("ShaderNodeMix"); char.data_type = 'RGBA'; char.blend_type = 'MIX'
            L.new(bar.outputs["Result"], char.inputs["Factor"]); L.new(sear.outputs["Result"], char.inputs["A"])
            char.inputs["B"].default_value = (0.045, 0.022, 0.01, 1)
            # VDW_GRILL_BARS=0: browning and searing only, no bars (e.g. when the texture has its own painted marks)
            done_col = char.outputs["Result"] if os.environ.get("VDW_GRILL_BARS", "1") != "0" else sear.outputs["Result"]
            chan[m.name]["Color"] = done_col; chan[m.name]["Roughness"] = 0.68   # cooked: drier, less shiny
            L.new(done_col, p.inputs["Base Color"])
            print(f"FOOD {m.name}: browned and grill-marked (bars {GRILL_GAP * 100:.0f} cm apart)")
        print("FOOD", m.name, ": as painted/set")
    N.new("ShaderNodeEmission").name = "vdw_emit"
    t = N.new("ShaderNodeTexImage"); t.name = "vdw_target"

sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = SAMPLES
sc.render.bake.margin = 8; sc.render.bake.use_clear = True
for o in sc.objects: o.select_set(o is obj)
bpy.context.view_layer.objects.active = obj

def set_target(img):
    for m in me.materials:
        N = m.node_tree.nodes; t = N["vdw_target"]; t.image = img
        for n in N: n.select = False
        t.select = True; N.active = t

# Grungit's mask (only the Sanctus parts read it)
if any_sanctus:
    mm = bpy.data.materials.new("vdw_maskbake"); mm.use_nodes = True; mn = mm.node_tree.nodes
    for n in list(mn):
        if n.type != 'OUTPUT_MATERIAL': mn.remove(n)
    bk = mn.new("ShaderNodeGroup"); bk.node_tree = G_BAKER; bk.inputs["Scale"].default_value = 0.5 * LENGTH
    mm.node_tree.links.new(bk.outputs["Output"], output(mm.node_tree).inputs["Surface"])
    mt = mn.new("ShaderNodeTexImage"); mt.image = mask_img; mn.active = mt
    # every other material's selected image is cleared by the bake: point them at a throwaway one, so a painted
    # texture that's the selected node (the fish's) isn't wiped
    set_target(bpy.data.images.new("vdw_throwaway", 8, 8))
    saved = [p.material_index for p in me.polygons]
    me.materials.append(mm); k = len(me.materials) - 1
    for p in me.polygons: p.material_index = k
    bpy.ops.object.bake(type='EMIT'); print("FOOD Grungit mask baked")
    for p, i in zip(me.polygons, saved): p.material_index = i
    me.materials.pop(index=k)

def bake_channel(name, nc):
    img = bpy.data.images.new("bake_" + name, SIZE, SIZE, alpha=False)
    if nc: img.colorspace_settings.name = 'Non-Color'
    for m in me.materials:
        nt = m.node_tree; N, L = nt.nodes, nt.links; em = N["vdw_emit"]
        for l in list(em.inputs["Color"].links): L.remove(l)
        v = chan[m.name][name]
        if isinstance(v, bpy.types.NodeSocket): L.new(v, em.inputs["Color"])
        else: em.inputs["Color"].default_value = v if isinstance(v, tuple) else (v, v, v, 1.0)
        L.new(em.outputs["Emission"], output(nt).inputs["Surface"])
    set_target(img); bpy.ops.object.bake(type='EMIT'); print("FOOD baked", name); return img
def px(img):
    a = np.empty(SIZE * SIZE * 4, np.float32); img.pixels.foreach_get(a); return a.reshape(SIZE, SIZE, 4)
def save(arr, name, nc):
    im = bpy.data.images.new(name, SIZE, SIZE, alpha=True)
    if nc: im.colorspace_settings.name = 'Non-Color'
    im.pixels.foreach_set(np.ascontiguousarray(arr, np.float32).ravel()); im.filepath_raw = os.path.join(DIR, name); im.file_format = 'PNG'; im.save(); print("  saved", name)

col = px(bake_channel("Color", False)); met = px(bake_channel("Metallic", True)); rough = px(bake_channel("Roughness", True))
glows = any(isinstance(chan[m.name]["Emission"], bpy.types.NodeSocket) or max(chan[m.name]["Emission"][:3]) > 0 for m in me.materials)
emi = px(bake_channel("Emission", False)) if glows else None
for m in me.materials:
    nt = m.node_tree; nt.links.new(chan[m.name]["surface"], output(nt).inputs["Surface"])
nimg = bpy.data.images.new("bake_normal", SIZE, SIZE, alpha=False); nimg.colorspace_settings.name = 'Non-Color'
set_target(nimg); sc.render.bake.normal_space = 'TANGENT'; bpy.ops.object.bake(type='NORMAL'); nrm = px(nimg); print("FOOD baked Normal")

col[..., 3] = 1.0; save(col, KEY + "_Unity_Albedo.png", False)
ms = np.zeros_like(col); ms[..., 0] = ms[..., 1] = ms[..., 2] = met[..., 0]; ms[..., 3] = 1.0 - rough[..., 0]
save(ms, KEY + "_Unity_MetallicSmoothness.png", True)
nrm[..., 3] = 1.0; save(nrm, KEY + "_Unity_Normal.png", True)
if emi is not None and emi[..., :3].max() > 0.01: emi[..., 3] = 1.0; save(emi, KEY + "_Unity_Emission.png", False)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, KEY + "_baked.blend"))

# 4. the game model: the bake layout as its only UVs, real size, standing on the origin, one material
me.uv_layers.remove(me.uv_layers[src_uv]); me.uv_layers[0].name = "UVMap"
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
co = np.array([v.co[:] for v in me.vertices]); lo, hi = co.min(0), co.max(0)
shift = np.array([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]])
for v in me.vertices: v.co = (v.co[0] + shift[0], v.co[1] + shift[1], v.co[2] + shift[2])
me.materials.clear(); plain = bpy.data.materials.new(KEY); me.materials.append(plain)
for p in me.polygons: p.material_index = 0
obj.modifiers.new("tri", 'TRIANGULATE')
bpy.ops.export_scene.fbx(filepath=os.path.join(DIR, KEY + "_model.fbx"), use_selection=True, object_types={'MESH'},
                         global_scale=1.0, apply_unit_scale=True, apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y',
                         # True: the turn into Unity's Y-up goes into the mesh itself. Static items use only the mesh
                         # (not the object's rotation), so without it the food lies on its side in game.
                         bake_space_transform=True, mesh_smooth_type='FACE', use_mesh_modifiers=True, path_mode='COPY', embed_textures=False)
print("FOOD exported", KEY, "size", tuple(round(float(x), 3) for x in (hi - lo)))
print("===== END =====")
