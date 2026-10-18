# Turns a Substance Painter "Unreal Engine 4 (Packed)" export into the Unity map set the mod's importer reads:
#   <set>_BaseColor -> <out>_Unity_Albedo                      (alpha 1)
#   <set>_OcclusionRoughnessMetallic -> <out>_Unity_MetallicSmoothness   (R = metallic, A = 1 - roughness)
#   <set>_Normal -> <out>_Unity_Normal                         (DirectX green flipped to Unity's OpenGL; VDW_NORMAL_GL=1 keeps it)
# Ambient occlusion (ORM red) is multiplied into the albedo a little (VDW_AO, 0.5), as Valheim's shaders take no AO map.
# Tone, for colours that read too loud under Valheim's light and bloom: VDW_SAT / VDW_VAL multiply the albedo's saturation /
# brightness, VDW_SMOOTH the smoothness (all 1 = as painted).
#   blender -b --python painter_to_unity.py -- <dir> <set prefix> <out dir> <out name>     (refuses to overwrite)
import bpy, os, sys
import numpy as np
src_dir, pre, out_dir, out = sys.argv[sys.argv.index("--") + 1:]
AO = float(os.environ.get("VDW_AO", "0.5")); GL = os.environ.get("VDW_NORMAL_GL") == "1"
def load(kind):
    p = os.path.join(src_dir, f"{pre}_{kind}.png")
    if not os.path.exists(p): return None, None
    im = bpy.data.images.load(p); im.colorspace_settings.name = 'Non-Color' if kind != "BaseColor" else 'sRGB'
    a = np.empty(im.size[0] * im.size[1] * 4, np.float32); im.pixels.foreach_get(a)
    return a.reshape(im.size[1], im.size[0], 4), im.size
def save(a, kind, nc):
    p = os.path.join(out_dir, f"{out}_Unity_{kind}.png")
    if os.path.exists(p): raise SystemExit("refusing to overwrite " + p)
    im = bpy.data.images.new(f"{out}_{kind}", a.shape[1], a.shape[0], alpha=True)
    if nc: im.colorspace_settings.name = 'Non-Color'
    im.pixels.foreach_set(np.ascontiguousarray(a, np.float32).ravel()); im.filepath_raw = p; im.file_format = 'PNG'; im.save(); print("  saved", p)
col, size = load("BaseColor"); orm, _ = load("OcclusionRoughnessMetallic"); nrm, _ = load("Normal")
if col is None: raise SystemExit(f"no {pre}_BaseColor.png in {src_dir}")
alb = col.copy(); alb[..., 3] = 1.0
if orm is not None and orm.shape == col.shape:
    alb[..., :3] *= (1 - AO) + AO * orm[..., :1]
SAT, VAL = float(os.environ.get("VDW_SAT", "1")), float(os.environ.get("VDW_VAL", "1"))
if SAT != 1 or VAL != 1:
    rgb = alb[..., :3]; grey = rgb.mean(-1, keepdims=True)
    alb[..., :3] = np.clip((grey + (rgb - grey) * SAT) * VAL, 0, 1)
save(alb, "Albedo", False)
ms = np.zeros_like(col); ms[..., 3] = 0.5
if orm is not None: ms = np.zeros_like(orm); ms[..., 0] = ms[..., 1] = ms[..., 2] = orm[..., 2]; ms[..., 3] = 1.0 - orm[..., 1]
ms[..., 3] = np.clip(ms[..., 3] * float(os.environ.get("VDW_SMOOTH", "1")), 0, 1)
save(ms, "MetallicSmoothness", True)
if nrm is not None:
    n = nrm.copy(); n[..., 3] = 1.0
    if not GL: n[..., 1] = 1.0 - n[..., 1]
    save(n, "Normal", True)
print(f"  {pre} -> {out}: {size[0]}x{size[1]}, AO {AO}, sat x{SAT} val x{VAL} smooth x{os.environ.get('VDW_SMOOTH', '1')}, normal {'kept (OpenGL)' if GL else 'green flipped (DirectX -> OpenGL)'}")
