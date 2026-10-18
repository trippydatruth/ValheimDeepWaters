# Re-tints a fish's albedo: brightens it (gamma lift + gain) and pulls its colour toward a tint while keeping the
# painted light/dark detail (scales, spots). Writes a NEW albedo next to the old one, points the material at it and
# saves a new .blend (the old map and file are left alone).
#   blender -b fish.blend --python tint_albedo.py
#   env: VDW_NAME (new map name, e.g. greydwarf_goby_prep_v2_moss -> <name>_Unity_Albedo.png), VDW_SAVE_TO,
#        VDW_TINT "r,g,b" (0-1), VDW_TINT_AMOUNT (0-1, default 0.45), VDW_GAMMA (default 0.8), VDW_GAIN (default 1.3),
#        VDW_KEEP_HUES "lo-hi,lo-hi" (hue degrees left untinted, e.g. orange flecks "15-45")
import bpy, os, colorsys
import numpy as np
NAME = os.environ["VDW_NAME"]; SAVE_TO = os.environ["VDW_SAVE_TO"]
TINT = np.array([float(x) for x in os.environ.get("VDW_TINT", "0.36,0.45,0.2").split(",")], np.float32)
AMT = float(os.environ.get("VDW_TINT_AMOUNT", "0.45")); GAMMA = float(os.environ.get("VDW_GAMMA", "0.8"))
GAIN = float(os.environ.get("VDW_GAIN", "1.3"))
KEEP = [tuple(float(y) for y in x.split("-")) for x in os.environ.get("VDW_KEEP_HUES", "").split(",") if x]
mesh = max((o for o in bpy.data.objects if o.type == 'MESH'), key=lambda o: len(o.data.vertices))
mat = mesh.data.materials[0]; bs = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
node = bs.inputs["Base Color"].links[0].from_node; src = node.image
out_path = os.path.join(os.path.dirname(bpy.path.abspath(src.filepath)), f"{NAME}_Unity_Albedo.png")
if os.path.exists(out_path) or os.path.exists(SAVE_TO): raise RuntimeError("refusing to overwrite")
W, H = src.size; px = np.empty(W * H * 4, np.float32); src.pixels.foreach_get(px); px = px.reshape(-1, 4)
c = np.clip(px[:, :3], 0, 1)
lum0 = c.mean(1)
b = np.clip(np.power(c, GAMMA) * GAIN, 0, 1)                     # brighter
lum = b.mean(1, keepdims=True)
tinted = np.clip(lum * TINT / TINT.mean(), 0, 1)                 # same brightness, tint colour
amt = np.full((len(c), 1), AMT, np.float32)
if KEEP:   # leave chosen hues (e.g. orange flecks) mostly as they are
    mx, mn = c.max(1), c.min(1); sat = (mx - mn) / np.maximum(mx, 1e-4)
    hsv_h = np.array([colorsys.rgb_to_hsv(*p)[0] * 360 for p in c[::1]]) if len(c) < 300000 else None
    if hsv_h is None:   # vectorised hue
        r, g, bb = c[:, 0], c[:, 1], c[:, 2]; d = np.maximum(mx - mn, 1e-6)
        h = np.where(mx == r, ((g - bb) / d) % 6, np.where(mx == g, (bb - r) / d + 2, (r - g) / d + 4)) * 60
    else: h = hsv_h
    for lo_, hi_ in KEEP:
        sel = (h >= lo_) & (h <= hi_) & (sat > 0.25)
        amt[sel, 0] *= 0.25
out = b * (1 - amt) + tinted * amt
px[:, :3] = out; px[:, 3] = 1
img = bpy.data.images.new(f"{NAME}_Unity_Albedo", W, H, alpha=True)
img.pixels.foreach_set(px.ravel()); img.filepath_raw = out_path; img.file_format = 'PNG'; img.save()
node.image = img
print(f"  albedo {src.name} -> {out_path}: mean brightness {lum0.mean():.3f} -> {out.mean():.3f}")
bpy.ops.wm.save_as_mainfile(filepath=SAVE_TO); print("  saved", SAVE_TO)
