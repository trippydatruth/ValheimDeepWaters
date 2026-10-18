# The Rune of Njord as a necklace (the user's model, "rune relic.blend", object rune_relic_buff), made ready for Unity:
#   - scaled from the reference character it was fitted on (7.76 m tall in the file) to a Valheim neck (the cord loop
#     about 20 cm across) and centred on the loop, at the height of the back of the cord, pendant to the front (-Y),
#     so the mod can hang it from the chest bone in place of the vanilla belt
#   - the Substance Painter maps (BaseColor, Normal, OcclusionRoughnessMetallic) turned into the Unity set
#     (Albedo, MetallicSmoothness, Normal)
# Reads the user's files only; writes new ones (buff_rune_njord_*).
#   blender -b --python build_rune_necklace.py
import bpy, os, numpy as np, mathutils

ROOT = r"C:\Users\tripp\Desktop\Valheim_DeepWaters\Mesh\Rune relic"
SRC = os.path.join(ROOT, "rune relic.blend")
OUT = os.path.join(ROOT, "buff_rune_njord_v1.fbx")
PREFIX = "rune relic_DefaultMaterial_"
NECK = float(os.environ.get("VDW_NECK", "0.20"))     # cord loop width across, metres

bpy.ops.wm.open_mainfile(filepath=SRC)
for o in list(bpy.data.objects):
    if o.name != "rune_relic_buff": bpy.data.objects.remove(o, do_unlink=True)
ob = bpy.data.objects["rune_relic_buff"]
bpy.context.view_layer.objects.active = ob
ob.select_set(True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

v = np.array([tuple(x.co) for x in ob.data.vertices])
# the loop's centre: the sides (|x| near the widest) give the middle front-to-back (the pendant only hangs in front);
# its height is the back of the cord, the highest point, where it lies on the neck
xmin, xmax = v[:, 0].min(), v[:, 0].max()
side = v[np.abs(v[:, 0] - (xmin + xmax) / 2) > 0.4 * (xmax - xmin)]
centre = mathutils.Vector(((xmin + xmax) / 2, side[:, 1].mean(), v[:, 2].max()))
scale = NECK / (xmax - xmin)
for x in ob.data.vertices:
    x.co = (x.co - centre) * scale
ob.data.update()
v = np.array([tuple(x.co) for x in ob.data.vertices])
print("NECKLACE size", (v.max(0) - v.min(0)).round(3), "front", v[:, 1].min().round(3), "back", v[:, 1].max().round(3),
      "lowest", v[:, 2].min().round(3), "scale", round(scale, 4))

bpy.ops.export_scene.fbx(
    filepath=OUT, use_selection=True, object_types={'MESH'},
    global_scale=1.0, apply_unit_scale=True, apply_scale_options='FBX_SCALE_ALL',
    axis_forward='-Z', axis_up='Y', bake_space_transform=True,
    mesh_smooth_type='FACE', bake_anim=False, path_mode='COPY', embed_textures=False)
print("EXPORTED", OUT)

# ---- textures
def load(name):
    img = bpy.data.images.load(os.path.join(ROOT, PREFIX + name + ".png"))
    a = np.array(img.pixels[:], dtype=np.float32).reshape(img.size[1], img.size[0], 4)
    return a, img.size

def save(a, size, name):
    img = bpy.data.images.new(name, size[0], size[1], alpha=True)
    img.pixels = a.ravel()
    img.filepath_raw = os.path.join(ROOT, name + ".png")
    img.file_format = 'PNG'
    img.save()
    print("WROTE", img.filepath_raw)

base, size = load("BaseColor")
orm, _ = load("OcclusionRoughnessMetallic")
nrm, nsize = load("Normal")
save(base, size, "buff_rune_njord_Unity_Albedo")
ms = np.zeros_like(orm)
ms[..., 0] = ms[..., 1] = ms[..., 2] = orm[..., 2]     # metallic (B)
ms[..., 3] = 1.0 - orm[..., 1]                        # smoothness = 1 - roughness (G)
save(ms, size, "buff_rune_njord_Unity_MetallicSmoothness")
save(nrm, nsize, "buff_rune_njord_Unity_Normal")       # Substance's OpenGL normals are what Unity wants

# ---- the glow: the blue ring round the pendant's face. It's a dull teal in the albedo (blue just above red), found by
# colour, then filled out to the whole circular band between its inner and outer edges so it glows evenly
rgb = base[..., :3]
found = (rgb[..., 2] - rgb[..., 0]) > 0.04
ys, xs = np.nonzero(found)
cy, cx = (ys.min() + ys.max()) / 2, (xs.min() + xs.max()) / 2
rad = np.hypot(ys - cy, xs - cx)
r_in, r_out = np.percentile(rad, 4), np.percentile(rad, 96)
yy, xx = np.mgrid[0:size[1], 0:size[0]]
d = np.hypot(yy - cy, xx - cx)
soft = 3.0                                             # pixels of fade at each edge
band = np.clip((d - r_in) / soft + 0.5, 0, 1) * np.clip((r_out - d) / soft + 0.5, 0, 1)
blue = np.array([0.25, 0.62, 1.0], dtype=np.float32)   # brighter and bluer than the painted teal, so it reads as light
em = np.zeros_like(base)
em[..., :3] = band[..., None] * blue
em[..., 3] = 1
save(em, size, "buff_rune_njord_Unity_Emission")
print("RING centre", (round(cx), round(cy)), "radius", round(r_in, 1), "-", round(r_out, 1), "px")
