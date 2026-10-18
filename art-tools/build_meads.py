# Makes the mead/tonic bottle variants from the one painted bottle: the green glass (and the liquid painted in it) is
# re-coloured per family, the cork and twine stay. Tier: minor duller, normal richer, major brighter with a glowing
# liquid (an emission map from the bright body of the bottle).
#   Writes <out>/<id>/<id>_Unity_Albedo.png (+ _Emission.png for glowing tiers) for every variant.
# env: VDW_ALBEDO (the bottle's Unity albedo), VDW_OUT (folder), VDW_PREVIEW (png contact sheet, optional)
import bpy, os
import numpy as np

FAMILIES = {"angler": 38, "steady": 205, "grip": None}          # hue for the glass; None = keep the painted green
TIERS = {"minor": (0.68, 0.75, 0.0), "medium": (1.0, 1.1, 0.0), "major": (1.08, 1.25, 1.0)}   # value, saturation, glow

im = bpy.data.images.load(os.environ["VDW_ALBEDO"]); W, H = im.size
px = np.array(im.pixels[:], np.float32).reshape(H, W, 4); rgb = px[..., :3]
mx = rgb.max(2); mn = rgb.min(2); d = mx - mn + 1e-6; s = np.where(mx > 1e-6, (mx - mn) / (mx + 1e-6), 0); v = mx
r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
# the glass: green hues; soft edges so the boundary with the cork/twine doesn't fringe
glass = np.clip((h - 45) / 10, 0, 1) * np.clip((150 - h) / 10, 0, 1) * np.clip((s - 0.08) / 0.07, 0, 1)
print(f"GLASS covers {glass.mean() * 100:.1f}% of the texture")

def hsv2rgb(h, s, v):
    h = (h % 360) / 60; i = np.floor(h).astype(int) % 6; f = h - np.floor(h)
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    out = np.zeros(h.shape + (3,), np.float32)
    for k, (a, b_, c) in enumerate(((v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q))):
        m = i == k; out[m, 0], out[m, 1], out[m, 2] = a[m], b_[m], c[m]
    return out

def save(arr, path):
    im2 = bpy.data.images.new(os.path.basename(path), W, H, alpha=True); im2.pixels[:] = arr.ravel()
    im2.filepath_raw = path; im2.file_format = 'PNG'; im2.save()

# one-off variants: key -> (hue, (value, saturation, glow))
EXTRA = {"buff_angler_north": (350, (0.95, 1.35, 1.0))}       # Lingonberry Angler's Mead: deep berry red, glowing
ONLY = set(filter(None, os.environ.get("VDW_ONLY", "").split(",")))   # write just these keys
OUT = os.environ["VDW_OUT"]; thumbs = []
variants = [(f"buff_{fam}_{tier}", hue, tv) for fam, hue in FAMILIES.items() for tier, tv in TIERS.items()]
variants += [(k, hue, tv) for k, (hue, tv) in EXTRA.items()]
for key, hue, (vk, sk, glow) in variants:
        if ONLY and key not in ONLY: continue
        nh = h if hue is None else hue + (h - 85) * 0.25             # keep a little of the painted variation
        ns = np.clip(s * sk * (1.15 if hue is not None else 1.0), 0, 1)
        nv = np.clip(v * vk, 0, 1)
        col = hsv2rgb(nh, ns, nv)
        out = px.copy(); out[..., :3] = rgb * (1 - glass[..., None]) + col * glass[..., None]; out[..., 3] = 1
        os.makedirs(os.path.join(OUT, key), exist_ok=True)
        save(out, os.path.join(OUT, key, f"{key}_Unity_Albedo.png"))
        if glow:
            # the brighter body of the bottle (the liquid) glows; the dark neck and base don't
            lit = glass * np.clip((v - 0.35) / 0.2, 0, 1)
            deep = hsv2rgb(nh, np.clip(ns * 1.4, 0, 1), np.clip(v * 0.9, 0, 1))   # a deeper, more saturated glow
            e = np.zeros_like(px); e[..., :3] = deep * lit[..., None] * 0.55; e[..., 3] = 1
            save(e, os.path.join(OUT, key, f"{key}_Unity_Emission.png"))
        thumbs.append((key, out))
        print("VARIANT", key, "glow" if glow else "")
