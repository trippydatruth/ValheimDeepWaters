# The Pearl of Njord as a whole belt (the user's remake, pearl_relic.fbx), made ready for Unity:
#   - scaled to a Valheim waist (about 38 cm across) and centred on the belt loop, pearl to the front (-Y),
#     so the mod can sit it on the hips in place of the vanilla belt
#   - the Substance Painter maps (BaseColor, Normal, OcclusionRoughnessMetallic) turned into the Unity set
#     (Albedo, MetallicSmoothness, Normal) plus an Emission map for the pearl's glow
# Reads the user's files only; writes new ones.
#   blender -b --python build_pearl_belt.py
import bpy, os, numpy as np, mathutils

ROOT = r"C:\Users\tripp\Desktop\Valheim_DeepWaters\Mesh\pearl of njord"
SRC = os.path.join(ROOT, "Models", "pearl_relic.fbx")
OUT = os.path.join(ROOT, "Models", "pearl_relic_v2.fbx")
TEX = os.path.join(ROOT, "Textures")
PREFIX = "pearl_relic_pearl_relic_material_"
WAIST = float(os.environ.get("VDW_WAIST", "0.38"))   # belt width across, metres

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=SRC)
ob = next(o for o in bpy.context.scene.objects if o.type == 'MESH')
bpy.context.view_layer.objects.active = ob
ob.select_set(True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

v = np.array([tuple(x.co) for x in ob.data.vertices])
# the loop's centre: the sides (|x| near the widest) give the middle front-to-back, the pearl only sticks out in front
xmin, xmax = v[:, 0].min(), v[:, 0].max()
side = v[np.abs(v[:, 0] - (xmin + xmax) / 2) > 0.4 * (xmax - xmin)]
centre = mathutils.Vector(((xmin + xmax) / 2, side[:, 1].mean(), (v[:, 2].min() + v[:, 2].max()) / 2))
scale = WAIST / (xmax - xmin)
for x in ob.data.vertices:
    x.co = (x.co - centre) * scale
ob.data.update()
v = np.array([tuple(x.co) for x in ob.data.vertices])
print("BELT size", (v.max(0) - v.min(0)).round(3), "front", v[:, 1].min().round(3), "back", v[:, 1].max().round(3), "scale", round(scale, 4))

bpy.ops.export_scene.fbx(
    filepath=OUT, use_selection=True, object_types={'MESH'},
    global_scale=1.0, apply_unit_scale=True, apply_scale_options='FBX_SCALE_ALL',
    axis_forward='-Z', axis_up='Y', bake_space_transform=True,
    mesh_smooth_type='FACE', bake_anim=False, path_mode='COPY', embed_textures=False)
print("EXPORTED", OUT)

# ---- textures
def load(name):
    img = bpy.data.images.load(os.path.join(TEX, PREFIX + name + ".png"))
    a = np.array(img.pixels[:], dtype=np.float32).reshape(img.size[1], img.size[0], 4)
    return a, img.size

def save(a, size, name):
    img = bpy.data.images.new(name, size[0], size[1], alpha=True)
    img.pixels = a.ravel()
    img.filepath_raw = os.path.join(TEX, name + ".png")
    img.file_format = 'PNG'
    img.save()
    print("WROTE", img.filepath_raw)

base, size = load("BaseColor")
orm, _ = load("OcclusionRoughnessMetallic")
nrm, nsize = load("Normal")
save(base, size, "pearl_relic_Unity_Albedo")
ms = np.zeros_like(orm)
ms[..., 0] = ms[..., 1] = ms[..., 2] = orm[..., 2]     # metallic (B)
ms[..., 3] = 1.0 - orm[..., 1]                        # smoothness = 1 - roughness (G)
save(ms, size, "pearl_relic_Unity_MetallicSmoothness")
save(nrm, nsize, "pearl_relic_Unity_Normal")           # Substance's OpenGL normals are what Unity wants

# the glow: the pearl and its pale setting (bright, unsaturated), not the leather or the dark rim
rgb = base[..., :3]
mx, mn = rgb.max(-1), rgb.min(-1)
sat = np.where(mx > 1e-4, (mx - mn) / np.maximum(mx, 1e-4), 0)
glow = np.clip((mx - 0.62) / 0.2, 0, 1) * np.clip((0.35 - sat) / 0.15, 0, 1)
em = np.zeros_like(base)
em[..., :3] = rgb * glow[..., None]
em[..., 3] = 1
save(em, size, "pearl_relic_Unity_Emission")
print("GLOW share", round(float((glow > 0.5).mean()), 4))
