# Jörmungandr's Scale: maps that turn the vanilla linen cape (mesh cape1, UVs in the strip u 0..0.31) into a cloak of
# world-serpent scales: overlapping dark sea-green scales with iridescent rims and a faint glow along the edges, and a
# gold clasp on the little patch at u 0.25..0.32, v 0..0.07. Covers the whole texture so any cape UV lands on scales.
# env: VDW_OUT (folder), VDW_NAME (file prefix)
import bpy, math, os
import numpy as np

OUT = os.environ["VDW_OUT"]; NAME = os.environ["VDW_NAME"]; os.makedirs(OUT, exist_ok=True)
S = 1024; ROWS = 44; COLS = 44                     # scales over the texture (the cape half is ~0.3 x 1 of it)
rng = np.random.default_rng(11)
v, u = (np.mgrid[0:S, 0:S] + 0.5) / S             # row 0 is v = 0 (Blender pixel order)

# Overlapping scales: rows laid from v = 1 (shoulders) down; each later row covers the one above where they overlap,
# so every scale shows its rounded free edge pointing down the cape.
d = np.full((S, S), 9.0, np.float32); su = np.zeros((S, S), np.float32); sv = np.zeros((S, S), np.float32); sid = np.zeros((S, S), np.int32)
R = 0.62
for j in range(ROWS + 1):
    cv = 1 - j / ROWS                                # the scale's root (top) line
    off = 0.5 * (j % 2)
    cu = (np.floor(u * COLS - off) + 0.5 + off) / COLS
    for k in (-1, 0, 1):
        cuk = cu + k / COLS
        du = (u - cuk) * COLS; dv = (cv - v) * ROWS  # dv > 0 below the root
        dist = np.sqrt(du * du + (dv * 0.85) ** 2) / R
        m = (dist < 1) & (dv > -0.15)
        d[m] = dist[m]; su[m] = du[m]; sv[m] = dv[m]; sid[m] = j * 1000 + np.round(cuk * COLS).astype(np.int32)[m] + k
hue = (np.sin(sid * 12.9898) * 43758.5453) % 1    # a steady random per scale

# colour: deep sea-green body, darker at the root, iridescent teal-to-gold rim, a pale central ridge
body = np.array((0.04, 0.17, 0.14)) * (0.7 + 0.6 * hue[..., None]) + np.array((0.0, 0.05, 0.07)) * (1 - hue[..., None])
rim = np.clip((d - 0.72) / 0.25, 0, 1)[..., None]
iri = np.array((0.15, 0.55, 0.5)) * (1 - hue[..., None]) + np.array((0.55, 0.5, 0.18)) * hue[..., None]
ridge = np.exp(-(su / 0.06) ** 2)[..., None] * np.clip(sv, 0, 1)[..., None] * 0.35
root = np.clip(1 - sv / 0.5, 0, 1)[..., None]
alb = body * (1 - 0.6 * root) + iri * rim * 0.9 + np.array((0.2, 0.35, 0.3)) * ridge
edge = (d > 0.93)[..., None]
alb = np.where(edge, np.array((0.01, 0.03, 0.03)), alb)
metal = 0.35 + 0.4 * rim[..., 0]; smooth = 0.62 + 0.2 * rim[..., 0] - 0.3 * edge[..., 0]
emi = np.array((0.05, 0.5, 0.45)) * (rim[..., 0] ** 3 * (0.4 + 0.6 * hue))[..., None] * 0.6
hgt = np.sqrt(np.clip(1 - d * d, 0, 1)) * 0.6 + np.clip(sv, 0, 1) * 0.25 + ridge[..., 0] * 0.5

# the clasp: polished gold disc with a green serpent's-eye gem
cu, cv, cr = 0.285, 0.035, 0.034
dc = np.hypot(u - cu, v - cv) / cr; clasp = (u > 0.24) & (u < 0.33) & (v < 0.08)
gold = np.array((0.85, 0.62, 0.22)) * (0.8 + 0.25 * np.cos(dc * 9))[..., None]
gem = dc < 0.45; slit = gem & (np.abs(u - cu) < cr * 0.06)
alb[clasp] = np.where(gem[clasp][:, None], np.array((0.15, 0.75, 0.3)), gold[clasp]); alb[clasp & slit] = (0.02, 0.02, 0.01)
metal[clasp] = np.where(gem[clasp], 0.2, 1.0); smooth[clasp] = 0.85
emi[clasp & gem] = (0.1, 0.9, 0.35); hgt[clasp] = np.where(gem[clasp], 1.0, 0.6 + 0.1 * np.cos(dc[clasp] * 9))

gy, gx = np.gradient(hgt * 6.0); nrm = np.dstack((-gx, -gy, np.ones_like(hgt))); nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
def save(arr3, kind, alpha=None):
    a4 = np.ones((S, S, 4), np.float32); a4[..., :3] = np.clip(arr3, 0, 1)
    if alpha is not None: a4[..., 3] = alpha
    im = bpy.data.images.new(kind, S, S, alpha=True); im.pixels[:] = a4.ravel(); p = os.path.join(OUT, f"{NAME}_{kind}.png")
    im.filepath_raw = p; im.file_format = 'PNG'; im.save(); print("MAP", os.path.basename(p))
save(alb, "Albedo"); save(np.dstack((metal, metal, metal)), "MetallicSmoothness", alpha=smooth); save(nrm * 0.5 + 0.5, "Normal"); save(emi, "Emission")
