# Builds one hook model per hook tier from Hook.obj (modelled in cm), each scaled to its tier's length, centred on
# its bounds. The six normal tiers share the steel textures; the Golden Hook gets solid gold (gold albedo that keeps
# the painted detail, fully metallic and polished) and a soft gold glow (emission map).
#   Writes Models\hook_<id>.fbx (static, embedded textures), Textures\hook_Unity_* and hook_golden_Unity_*,
#   Blender Files\hooks.blend (all hooks side by side) and preview renders.
#   env: VDW_OBJ, VDW_TEX_DIR, VDW_MODEL_DIR, VDW_SAVE_TO, VDW_RENDER (png prefix)
import bpy, os, math
import numpy as np
from mathutils import Vector

TIERS = [("tiny", 0.05), ("small", 0.07), ("medium", 0.09), ("large", 0.12), ("heavy", 0.15), ("giant", 0.19), ("golden", 0.22), ("fimbul", 0.24)]
GOLD = np.array([1.0, 0.76, 0.30])            # sRGB gold
TEX = os.environ["VDW_TEX_DIR"]; MODELS = os.environ["VDW_MODEL_DIR"]

for o in list(bpy.data.objects): bpy.data.objects.remove(o)
bpy.ops.wm.obj_import(filepath=os.environ["VDW_OBJ"])
src = next(o for o in bpy.data.objects if o.type == 'MESH')
for o in bpy.context.view_layer.objects: o.select_set(False)
src.select_set(True); bpy.context.view_layer.objects.active = src
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
co = np.array([v.co[:] for v in src.data.vertices]); lo, hi = co.min(0), co.max(0)
length = float((hi - lo).max())
centre = Vector(((lo + hi) / 2).tolist())
for v in src.data.vertices: v.co = (v.co - centre) / length        # unit length, centred
src.data.update()
print(f"\n===== HOOKS =====\n  source hook {length:.2f} units long (cm), proportions {tuple(((hi - lo) / length).round(3))}")

def px_of(img):
    a = np.empty(img.size[0] * img.size[1] * 4, dtype=np.float32); img.pixels.foreach_get(a); return a.reshape(-1, 4)
def save_img(name, data, w, h, alpha=False, nc=False):
    path = os.path.join(TEX, name + ".png")
    im = bpy.data.images.new(name, w, h, alpha=alpha)
    if nc: im.colorspace_settings.name = 'Non-Color'
    im.pixels.foreach_set(data.ravel()); im.filepath_raw = path; im.file_format = 'PNG'
    if not os.path.exists(path): im.save(); print("  saved", path)
    else: print("  exists, kept:", path)
    return im
def load(name, nc=False):
    im = bpy.data.images.load(os.path.join(TEX, name))
    if nc: im.colorspace_settings.name = 'Non-Color'
    return im

base = load("Hook_DefaultMaterial_BaseColor.png"); orm = load("Hook_DefaultMaterial_OcclusionRoughnessMetallic.png", True)
nrm = load("Hook_DefaultMaterial_Normal.png", True)
W, H = base.size; bp = px_of(base); op = px_of(orm)
steel_nrm = save_img("hook_Unity_Normal", px_of(nrm), W, H, nc=True)        # shared by every hook
# gold maps: the painted light/dark detail carried onto gold
lum = bp[:, :3].mean(1); painted = lum > 0.02
rel = np.clip(lum / max(lum[painted].mean(), 1e-3), 0.55, 1.25)[:, None]
ga = np.ones_like(bp); ga[:, :3] = np.clip(GOLD * rel, 0, 1); ga[~painted, :3] = GOLD * 0.8
gold_alb = save_img("hook_golden_Unity_Albedo", ga, W, H)
gms = np.empty_like(op); gms[:, :3] = 1.0; gms[:, 3] = np.clip(0.85 + 0.1 * (1.0 - op[:, 1]), 0, 1)   # metal, polished
gold_ms = save_img("hook_golden_Unity_MetallicSmoothness", gms, W, H, alpha=True, nc=True)
ge = np.ones_like(bp); ge[:, :3] = np.clip(np.array([0.95, 0.55, 0.12]) * (0.7 + 0.3 * rel), 0, 1)   # warm amber glow under the metal
gold_em = save_img("hook_golden_Unity_Emission", ge, W, H)

def material(name, alb, msi, nmi, emi=None, strength=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; N, L = nt.nodes, nt.links
    b = next(n for n in N if n.type == 'BSDF_PRINCIPLED')
    def tex(img, x, y):
        t = N.new("ShaderNodeTexImage"); t.image = img; t.location = (x, y); return t
    a = tex(alb, -700, 300); L.new(a.outputs["Color"], b.inputs["Base Color"])
    s = tex(msi, -700, 0); L.new(s.outputs["Color"], b.inputs["Metallic"])
    inv = N.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
    L.new(s.outputs["Alpha"], inv.inputs[1]); L.new(inv.outputs["Value"], b.inputs["Roughness"])
    n_ = tex(nmi, -700, -320); nm = N.new("ShaderNodeNormalMap")
    L.new(n_.outputs["Color"], nm.inputs["Color"]); L.new(nm.outputs["Normal"], b.inputs["Normal"])
    if emi is not None:
        e = tex(emi, -700, -650); L.new(e.outputs["Color"], b.inputs["Emission Color"]); b.inputs["Emission Strength"].default_value = strength
    N.active = a
    return m
gold = material("hook_golden", gold_alb, gold_ms, steel_nrm, gold_em, 0.8)
# the Fimbul Hook: rime-forged ice-blue metal, frost crust in the painted crevices, a cold blue glow
ICE = np.array([0.62, 0.80, 0.95])
fa = np.ones_like(bp); fa[:, :3] = np.clip(ICE * rel, 0, 1); fa[~painted, :3] = ICE * 0.8
crev = (rel[:, 0] < 0.85)                                          # darker painted detail: frost settles there
fa[crev, :3] = np.clip(fa[crev, :3] * 0.4 + 0.6 * np.array([0.93, 0.97, 1.0]), 0, 1)
fimbul_alb = save_img("hook_fimbul_Unity_Albedo", fa, W, H)
fms = np.empty_like(op); fms[:, :3] = 1.0; fms[:, 3] = np.clip(0.80 + 0.1 * (1.0 - op[:, 1]), 0, 1); fms[crev, :3] = 0.2; fms[crev, 3] = 0.35
fimbul_ms = save_img("hook_fimbul_Unity_MetallicSmoothness", fms, W, H, alpha=True, nc=True)
fe = np.ones_like(bp); fe[:, :3] = np.clip(np.array([0.25, 0.65, 1.0]) * (0.5 + 0.5 * rel), 0, 1); fe[crev, :3] *= 0.35
fimbul_em = save_img("hook_fimbul_Unity_Emission", fe, W, H)
fimbul = material("hook_fimbul", fimbul_alb, fimbul_ms, steel_nrm, fimbul_em, 1.2)

# Each hook in the material of its recipe: (colour, metallic, smoothness). The painted light/dark detail is kept.
LOOKS = {
    "tiny":   ((0.09, 0.075, 0.06), 0.0, 0.30),    # knapped flint: brown-black stone, a faint sheen, not metal
    "small":  ((0.93, 0.53, 0.36), 1.0, 0.70),     # copper
    "medium": ((0.68, 0.45, 0.24), 1.0, 0.58),     # bronze: browner than gold
    "large":  ((0.30, 0.30, 0.32), 1.0, 0.40),     # forged iron: dark and a little rough
    "heavy":  ((0.30, 0.30, 0.32), 1.0, 0.40),     # iron, with a silver point and barb (below)
    "giant":  ((0.13, 0.15, 0.16), 1.0, 0.62),     # black metal, a faint cool sheen
}
SILVER = ((0.97, 0.97, 0.99), 1.0, 0.92)
# the point and barb: the free end opposite the eye (the eye is the top of the hook)
sco = np.array([v.co[:] for v in src.data.vertices])
eye = sco[np.argmax(sco[:, 2])]; yc = (sco[:, 1].min() + sco[:, 1].max()) / 2
far_side = (sco[:, 1] - yc) * (eye[1] - yc) < 0
tipv = sco[far_side][np.argmax(sco[far_side][:, 2])]
barb_v = np.linalg.norm(sco - tipv, axis=1) < 0.16                 # within 16% of the hook's length of the point
uvd = src.data.uv_layers.active.data
barb_mask = np.zeros((H, W), dtype=bool)
def side(p, q, s): return (p[..., 0] - s[0]) * (q[1] - s[1]) - (q[0] - s[0]) * (p[..., 1] - s[1])
for poly in src.data.polygons:
    if not all(barb_v[v] for v in poly.vertices): continue
    pts = np.array([uvd[li].uv[:] for li in poly.loop_indices]) * [W, H]
    x0, y0 = np.floor(pts.min(0)).astype(int); x1, y1 = np.ceil(pts.max(0)).astype(int)
    xs, ys = np.meshgrid(np.arange(max(0, x0 - 2), min(W, x1 + 3)), np.arange(max(0, y0 - 2), min(H, y1 + 3)))
    P = np.stack([xs + 0.5, ys + 0.5], -1)
    for k in range(1, len(pts) - 1):
        a_, b_, c_ = pts[0], pts[k], pts[k + 1]
        d1, d2, d3 = side(P, a_, b_), side(P, b_, c_), side(P, c_, a_)
        ins = ~(((d1 < 0) | (d2 < 0) | (d3 < 0)) & ((d1 > 0) | (d2 > 0) | (d3 > 0)))
        barb_mask[ys[ins], xs[ins]] = True
for _ in range(3):
    p_ = np.pad(barb_mask, 1); barb_mask = p_[1:-1, 1:-1] | p_[:-2, 1:-1] | p_[2:, 1:-1] | p_[1:-1, :-2] | p_[1:-1, 2:]
barb_mask = barb_mask.ravel()
print(f"  heavy hook: silver point and barb on {barb_v.sum()} vertices ({barb_mask.mean() * 100:.1f}% of the texture)")
rough_detail = (0.5 - op[:, 1])                                     # the painted roughness variation
mats = {"golden": gold, "fimbul": fimbul}
for tid, (col, metal, smooth) in LOOKS.items():
    alb = np.ones_like(bp); alb[:, :3] = np.clip(np.array(col) * rel, 0, 1); alb[~painted, :3] = np.array(col) * 0.8
    msx = np.empty_like(op); msx[:, :3] = metal; msx[:, 3] = np.clip(smooth + 0.3 * rough_detail, 0, 1)
    if tid == "heavy":
        sc_, sm_, ss_ = SILVER
        alb[barb_mask, :3] = np.clip(np.array(sc_) * rel[barb_mask], 0, 1)
        msx[barb_mask, :3] = sm_; msx[barb_mask, 3] = np.clip(ss_ + 0.3 * rough_detail[barb_mask], 0, 1)
    ai = save_img(f"hook_{tid}_Unity_Albedo", alb, W, H)
    mi = save_img(f"hook_{tid}_Unity_MetallicSmoothness", msx, W, H, alpha=True, nc=True)
    mats[tid] = material(f"hook_{tid}", ai, mi, steel_nrm)

objs = []
x = 0.0
for tid, L in TIERS:
    me = src.data.copy(); me.name = f"hook_{tid}"
    for v in me.vertices: v.co = v.co * L
    me.materials.clear(); me.materials.append(mats[tid])
    ob = bpy.data.objects.new(f"hook_{tid}", me); bpy.context.scene.collection.objects.link(ob)
    objs.append((tid, L, ob))
bpy.data.objects.remove(src); bpy.context.view_layer.update()
for img in list(bpy.data.images):
    if img.users == 0: bpy.data.images.remove(img)

# export each at the origin, then lay them out side by side in the .blend for viewing
ONLY = set(filter(None, os.environ.get("VDW_ONLY", "").split(",")))   # export just these (others keep their FBX)
for tid, L, ob in objs:
    if ONLY and tid not in ONLY: continue
    ob.location = (0, 0, 0)
    for o in bpy.data.objects: o.select_set(False)
    ob.select_set(True); bpy.context.view_layer.objects.active = ob
    path = os.path.join(MODELS, f"hook_{tid}.fbx")
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={'MESH'}, global_scale=1.0, apply_unit_scale=True,
                             apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y', bake_space_transform=True,
                             mesh_smooth_type='FACE', bake_anim=False, path_mode='COPY', embed_textures=True)
    d = np.array([v.co[:] for v in ob.data.vertices]); size = d.max(0) - d.min(0)
    print(f"  hook_{tid}: {L * 100:.0f} cm long, size {tuple((size * 100).round(1))} cm -> {os.path.basename(path)} ({os.path.getsize(path) // 1024} KB)")
x = 0.0
for tid, L, ob in objs:
    ob.location = (0, x + L / 2, 0); x += L + 0.03
bpy.ops.wm.save_as_mainfile(filepath=os.environ["VDW_SAVE_TO"]); print("  saved", os.environ["VDW_SAVE_TO"])

R = os.environ.get("VDW_RENDER")
if R:
    sc = bpy.context.scene; sc.render.use_border = False; sc.render.resolution_percentage = 100
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 48; sc.view_settings.view_transform = 'Standard'
    wd = bpy.data.worlds.new("w"); wd.use_nodes = True; bg = wd.node_tree.nodes["Background"]; sc.world = wd
    ld = bpy.data.lights.new("key", 'SUN'); ld.energy = 3.0; lo_ = bpy.data.objects.new("key", ld); sc.collection.objects.link(lo_); lo_.rotation_euler = (0.7, 0.3, 0.9)
    cd = bpy.data.cameras.new("C"); cd.type = 'ORTHO'
    cam = bpy.data.objects.new("C", cd); sc.collection.objects.link(cam); sc.camera = cam
    # line-up from the side (hooks lie in the y-z plane), with a 10 cm bar
    bar = bpy.data.meshes.new("bar"); bar.from_pydata([(0.01, 0, -0.14), (0.01, 0.1, -0.14), (0.01, 0.1, -0.132), (0.01, 0, -0.132)], [], [(0, 1, 2, 3)])
    bo = bpy.data.objects.new("bar", bar); sc.collection.objects.link(bo)
    bm_ = bpy.data.materials.new("barm"); bm_.use_nodes = True; next(n for n in bm_.node_tree.nodes if n.type == 'BSDF_PRINCIPLED').inputs["Base Color"].default_value = (0.9, 0.9, 0.9, 1); bar.materials.append(bm_)
    sky0 = wd.node_tree.nodes.new("ShaderNodeTexSky"); sky0.sky_type = 'NISHITA'; sky0.sun_elevation = math.radians(35)
    wd.node_tree.links.new(sky0.outputs["Color"], bg.inputs["Color"]); bg.inputs[1].default_value = 0.6   # a sky for the metals to reflect
    sc.render.resolution_x, sc.render.resolution_y = 1600, 500; cd.ortho_scale = x + 0.06
    cam.location = (3, x / 2 - 0.015, -0.01); cam.rotation_euler = (math.radians(90), 0, math.radians(90))
    sc.render.film_transparent = True; sc.render.image_settings.color_mode = 'RGBA'
    sc.render.filepath = f"{R}_lineup.png"; bpy.ops.render.render(write_still=True)
    # each hook close up
    sc.render.resolution_x, sc.render.resolution_y = 400, 500
    for tid, L, ob in objs:
        for t2, L2, o2 in objs: o2.hide_render = o2 is not ob
        cd.ortho_scale = L * 1.25; tgt = ob.location.copy()
        cam.location = tgt + Vector((1, 0.35, 0.25)).normalized() * 2; cam.rotation_euler = (tgt - cam.location).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = f"{R}_close_{tid}.png"; bpy.ops.render.render(write_still=True)
    for t2, L2, o2 in objs: o2.hide_render = False
    sc.render.film_transparent = False
    bo.hide_render = True
    # the golden hook: daylight and night
    sky = wd.node_tree.nodes.new("ShaderNodeTexSky"); sky.sky_type = 'NISHITA'; sky.sun_elevation = math.radians(35)
    g = next(ob for tid, L, ob in objs if tid == "golden")
    for tid, L, ob in objs: ob.hide_render = ob is not g
    gb = next(n for n in gold.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    sc.render.resolution_x, sc.render.resolution_y = 600, 700; cd.ortho_scale = 0.3
    tgt = g.location.copy(); cam.location = tgt + Vector((1, 0.35, 0.25)).normalized() * 2; cam.rotation_euler = (tgt - cam.location).to_track_quat('-Z', 'Y').to_euler()
    for name, bgc, sun, strength in (("gold_day", None, 3.0, 0.8), ("gold_night", (0.01, 0.012, 0.025, 1), 0.15, 2.5), ("gold_night_noglow", (0.01, 0.012, 0.025, 1), 0.15, 0.0)):
        if bgc is None:   # daylight: a real sky for the gold to reflect
            if sky.outputs[0].links == (): pass
            wd.node_tree.links.new(sky.outputs["Color"], bg.inputs["Color"]); bg.inputs[1].default_value = 0.6
        else:
            for l in list(bg.inputs["Color"].links): wd.node_tree.links.remove(l)
            bg.inputs[0].default_value = bgc; bg.inputs[1].default_value = 1.0
        ld.energy = sun; gb.inputs["Emission Strength"].default_value = strength
        sc.render.filepath = f"{R}_{name}.png"; bpy.ops.render.render(write_still=True)
print("===== END =====")







