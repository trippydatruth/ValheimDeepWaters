# The Shrine of Njord: the Fisherman's Totem's maps recoloured - sea-weathered blue-grey driftwood with turquoise
# glowing inlays in place of the warm wood and gold. Reads the fisher maps, writes new <VDW_NAME>_Unity_* maps.
# env: VDW_SRC (folder with buff_totem_fisher_Unity_*), VDW_OUT, VDW_NAME
import bpy, os, colorsys
import numpy as np

SRC = os.environ["VDW_SRC"]; OUT = os.environ["VDW_OUT"]; NAME = os.environ["VDW_NAME"]; os.makedirs(OUT, exist_ok=True)
def load(kind):
    im = bpy.data.images.load(os.path.join(SRC, f"buff_totem_fisher_Unity_{kind}.png")); im.colorspace_settings.name = "Non-Color"
    w, h = im.size; return np.array(im.pixels[:], np.float32).reshape(h, w, 4)
def save(a4, kind):
    h, w = a4.shape[:2]; im = bpy.data.images.new(kind, w, h, alpha=True); im.colorspace_settings.name = "Non-Color"
    im.pixels[:] = np.clip(a4, 0, 1).ravel(); p = os.path.join(OUT, f"{NAME}_Unity_{kind}.png")
    im.filepath_raw = p; im.file_format = 'PNG'; im.save(); print("MAP", os.path.basename(p))

alb = load("Albedo"); emi = load("Emission"); rgb = alb[..., :3]
glow = np.clip(emi[..., :3].max(2) / max(emi[..., :3].max(), 1e-4), 0, 1)
inlay = np.clip((glow - 0.05) / 0.35, 0, 1)[..., None]               # where the gold was
lum = rgb @ np.array((0.3, 0.55, 0.15), np.float32)
# wood: keep its light and grain, tint toward cold blue-grey with a little sea-green in the dark crevices
wood = lum[..., None] * np.array((0.78, 0.95, 1.08)) * 1.05 + (1 - lum[..., None]) * np.array((0.0, 0.03, 0.04)) * 0.6
wood = wood * 0.9 + np.array((0.02, 0.04, 0.05))
# inlays: turquoise sea glass, brighter where the gold was brightest
stone = np.array((0.25, 0.85, 0.9)) * (0.45 + 0.75 * lum[..., None])
out = alb.copy(); out[..., :3] = wood * (1 - inlay) + stone * inlay
save(out, "Albedo")
e = emi.copy(); e[..., :3] = glow[..., None] * np.array((0.3, 0.95, 1.0)); save(e, "Emission")
# metal map and normal are shared as-is (copied by the caller)
