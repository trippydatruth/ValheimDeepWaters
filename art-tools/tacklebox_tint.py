# Measures each tackle box tier's wood colour match: how the game's albedo compares with a plain bake of the live
# materials (bake_tacklebox.py VDW_EDITED=1 on an edit blend without tints), as a linear-light multiply for
# make_tacklebox_edit.py's VDW_TINTS. Prints the VDW_TINTS line.
#   blender -b --factory-startup --python tacklebox_tint.py
#   env: VDW_GAME (folder of tacklebox_<tier>\...Unity_*.png), VDW_TEST (the plain bakes' Textures folder), VDW_TIERS
import bpy, os
import numpy as np
GAME, TEST = os.environ["VDW_GAME"], os.environ["VDW_TEST"]
def load(p):
    im = bpy.data.images.load(p); im.colorspace_settings.name = 'Non-Color'
    a = np.empty(im.size[0] * im.size[1] * 4, np.float32); im.pixels.foreach_get(a); return a.reshape(im.size[1], im.size[0], 4)
def lin(c): return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
out = []
for t in os.environ.get("VDW_TIERS", "t1,t2,t3,t4").split(","):
    ga = load(os.path.join(GAME, f"tacklebox_{t}", f"tacklebox_{t}_Unity_Albedo.png"))
    gm = load(os.path.join(GAME, f"tacklebox_{t}", f"tacklebox_{t}_Unity_MetallicSmoothness.png"))
    ta = load(os.path.join(TEST, f"tacklebox_{t}", f"tacklebox_{t}_Unity_Albedo.png"))
    tm = load(os.path.join(TEST, f"tacklebox_{t}", f"tacklebox_{t}_Unity_MetallicSmoothness.png"))
    wood = (gm[..., 0] < 0.5) & (tm[..., 0] < 0.5) & (ga[..., :3].sum(-1) > 0.05) & (ta[..., :3].sum(-1) > 0.05)
    g = np.median(lin(ga[wood, :3]), 0) / np.maximum(np.median(lin(ta[wood, :3]), 0), 1e-4)
    # check: the game's wood against the plain bake times that tint, per texel (sRGB difference)
    pred = ta[..., :3].copy(); pl = lin(pred) * g
    pred = np.where(pl <= 0.0031308, pl * 12.92, 1.055 * np.power(pl, 1 / 2.4) - 0.055)
    err = np.abs(pred[wood] - ga[wood, :3]).mean()
    print(f"TINT {t}: {g.round(3)} over {wood.sum()} wood texels; mean difference after it {err:.3f}")
    out.append(f"{t}={g[0]:.3f},{g[1]:.3f},{g[2]:.3f}")
print("VDW_TINTS=" + ";".join(out))
