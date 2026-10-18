# Builds a Unity emission map from a fish's albedo: the parts painted as glowing (picked by colour) keep their
# colour, everything else is black. In Unity: Standard material -> Emission on -> this map, colour white,
# intensity ~1-3 (Valheim's bloom makes it glow, even in the dark).
#   Picks pixels by hue (degrees, centre +/- width), minimum saturation and minimum brightness, with soft edges.
#   Runs on a .blend: also wires the map into the material (Emission Color, strength VDW_GLOW_STRENGTH) and saves a
#   new .blend, then renders a dark-scene preview with Cycles.
#   env: VDW_GLOW_HUE, VDW_GLOW_HUE_WIDTH, VDW_GLOW_MIN_SAT, VDW_GLOW_MIN_VAL, VDW_GLOW_NAME (e.g. yagluthgill),
#        VDW_TEX_DIR, VDW_SAVE_TO, VDW_GLOW_STRENGTH (default 3), VDW_GLOW_PREVIEW (png prefix), VDW_GLOW_MASK_ONLY=1
#   Several colours: VDW_GLOW_BANDS="hue,width,minsat,minval;hue,width,minsat,minval" (replaces the four above).
import bpy, os, math
import numpy as np

HUE = float(os.environ.get("VDW_GLOW_HUE", "0")); HW = float(os.environ.get("VDW_GLOW_HUE_WIDTH", "25"))
MIN_S = float(os.environ.get("VDW_GLOW_MIN_SAT", "0.45")); MIN_V = float(os.environ.get("VDW_GLOW_MIN_VAL", "0.45"))
NAME = os.environ["VDW_GLOW_NAME"]; TEX_DIR = os.environ["VDW_TEX_DIR"]
SAVE_TO = os.environ.get("VDW_SAVE_TO", ""); STRENGTH = float(os.environ.get("VDW_GLOW_STRENGTH", "3"))
PREVIEW = os.environ.get("VDW_GLOW_PREVIEW", "")

# textures moved since the .blend was saved (e.g. into a Textures folder): find them by file name
for im in bpy.data.images:
    if im.source == 'FILE' and im.filepath and not im.packed_file and not os.path.exists(bpy.path.abspath(im.filepath)):
        cand = os.path.join(os.environ.get('VDW_TEX_SEARCH') or TEX_DIR, os.path.basename(bpy.path.abspath(im.filepath)))
        if os.path.exists(cand):
            im.filepath = cand; im.reload(); print('  relinked', os.path.basename(cand))
mesh = next(o for o in bpy.data.objects if o.type == 'MESH' and o.material_slots)
mat = mesh.material_slots[0].material; nt = mat.node_tree; nodes, links = nt.nodes, nt.links
bsdf = next(n for n in nodes if n.type == 'BSDF_PRINCIPLED')
alb_node = next(l.from_node for l in links if l.to_node == bsdf and l.to_socket.name == "Base Color")
alb = alb_node.image; W, H = alb.size
px = np.empty(W * H * 4, dtype=np.float32); alb.pixels.foreach_get(px); px = px.reshape(H, W, 4)
rgb = px[:, :, :3]

# HSV
mx = rgb.max(2); mn = rgb.min(2); d = mx - mn + 1e-6
s = np.where(mx > 1e-6, (mx - mn) / (mx + 1e-6), 0); v = mx
r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
def ramp(x, lo, width): return np.clip((x - lo) / width, 0, 1)
bands = [tuple(float(x) for x in b.split(',')) for b in os.environ['VDW_GLOW_BANDS'].split(';')] if os.environ.get('VDW_GLOW_BANDS') else [(HUE, HW, MIN_S, MIN_V)]
mask = np.zeros(h.shape, dtype=np.float32)
for hue_, hw_, ms_, mv_ in bands:
    dh = np.abs(((h - hue_) + 180) % 360 - 180)
    mask = np.maximum(mask, (1 - ramp(dh, hw_, 12)) * ramp(s, ms_, 0.12) * ramp(v, mv_, 0.12))

# VDW_GLOW_FILL_HOLES=1: small areas fully enclosed by glow (e.g. a white eye centre inside a glowing ring) glow too
if os.environ.get("VDW_GLOW_FILL_HOLES") == "1":
    from collections import deque
    step = max(1, W // 512); sm = mask[::step, ::step] > 0.3; sh, sw = sm.shape
    seen = sm.copy(); filled = np.zeros_like(sm); limit = sh * sw * 0.002
    for y0 in range(sh):
        for x0 in range(sw):
            if seen[y0, x0]: continue
            q = deque([(y0, x0)]); seen[y0, x0] = True; region = []; edge = False
            while q:
                y, x = q.popleft(); region.append((y, x))
                if y in (0, sh - 1) or x in (0, sw - 1): edge = True
                for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                    if 0 <= ny < sh and 0 <= nx < sw and not seen[ny, nx]:
                        seen[ny, nx] = True; q.append((ny, nx))
            if not edge and len(region) < limit:
                for y, x in region: filled[y, x] = True
    if filled.any():
        big = np.repeat(np.repeat(filled, step, 0), step, 1)[:H, :W]
        mask = np.maximum(mask, big.astype(np.float32))
    print(f"  filled {int(filled.sum())} enclosed pixels (at 1/{step} scale)")
# soften: 3x3 box blur twice (no scipy in Blender)
def blur(a):
    p = np.pad(a, 1, mode='edge')
    return sum(p[1 + dy:H + 1 + dy, 1 + dx:W + 1 + dx] for dy in (-1, 0, 1) for dx in (-1, 0, 1)) / 9
mask = blur(blur(mask))
glow = rgb * mask[:, :, None]
# brighten so the glow colour is vivid regardless of how dark it was painted
peak = np.maximum(glow.max(2, keepdims=True), 1e-6)
glow = np.where(mask[:, :, None] > 0, glow / np.maximum(peak, 0.35) * mask[:, :, None], 0)
cover = float((mask > 0.5).mean() * 100)
used = float((rgb.max(2) > 0.02).mean() * 100)
print(f"  glow covers {cover:.1f}% of the texture ({cover / max(used, 1e-6) * 100:.1f}% of the painted area)")

path = os.path.join(TEX_DIR, f"{NAME}_Unity_Emission.png")
if os.path.exists(path) and not os.environ.get("VDW_GLOW_OVERWRITE_OWN"):
    raise RuntimeError("refusing to overwrite " + path)
em = bpy.data.images.new(f"{NAME}_Unity_Emission", W, H, alpha=False)
out = np.ones((H, W, 4), dtype=np.float32); out[:, :, :3] = np.clip(glow, 0, 1)
em.pixels.foreach_set(out.ravel()); em.filepath_raw = path; em.file_format = 'PNG'; em.save()
print("  saved", path)
if os.environ.get("VDW_GLOW_MASK_ONLY") == "1": raise SystemExit

# wire into the material (Blender preview; in Unity set it on the Standard material by hand)
for n in [n for n in nodes if n.type == 'TEX_IMAGE' and n.image and "_Unity_Emission" in n.image.name]: nodes.remove(n)
en = nodes.new("ShaderNodeTexImage"); en.image = em; en.location = (-700, -650)
links.new(en.outputs["Color"], bsdf.inputs["Emission Color"]); bsdf.inputs["Emission Strength"].default_value = STRENGTH
nodes.active = alb_node
if SAVE_TO:
    bpy.ops.wm.save_as_mainfile(filepath=SAVE_TO); print("  saved", SAVE_TO)

if PREVIEW:
    from mathutils import Vector
    arm = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
    if arm: arm.data.pose_position = 'REST'
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 24
    sc.render.resolution_x, sc.render.resolution_y = 900, 500
    wd = bpy.data.worlds.new("dark"); wd.use_nodes = True; wd.node_tree.nodes["Background"].inputs[0].default_value = (0.02, 0.025, 0.035, 1)
    sc.world = wd; sc.view_settings.view_transform = 'Standard'
    co = np.array([mesh.matrix_world @ vv.co for vv in mesh.data.vertices]); ctr = Vector(((co.min(0) + co.max(0)) / 2).tolist()); L = float((co.max(0) - co.min(0)).max())
    cd = bpy.data.cameras.new("G"); cd.type = 'ORTHO'; cd.ortho_scale = 1.15 * L
    cam = bpy.data.objects.new("G", cd); sc.collection.objects.link(cam); sc.camera = cam
    cam.location = ctr + Vector((1.0, -1.05, 0.5)).normalized() * L * 3
    cam.rotation_euler = (ctr - cam.location).to_track_quat('-Z', 'Y').to_euler()
    for name, sun, strength in (("lit", 3.0, STRENGTH), ("dark", 0.15, STRENGTH), ("noglow", 0.15, 0.0)):
        for o in [o for o in bpy.data.objects if o.type == 'LIGHT']: bpy.data.objects.remove(o)
        ld = bpy.data.lights.new("S", 'SUN'); ld.energy = sun
        lo_ = bpy.data.objects.new("S", ld); sc.collection.objects.link(lo_); lo_.rotation_euler = (math.radians(50), 0, math.radians(30))
        bsdf.inputs["Emission Strength"].default_value = strength
        sc.render.filepath = f"{PREVIEW}_{name}.png"; bpy.ops.render.render(write_still=True)
    print("  previews", PREVIEW)
print("GLOW DONE")


