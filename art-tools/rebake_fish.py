# Re-unwraps a fish into a clean UV layout and bakes its existing textures onto it as Unity Standard-shader maps:
#   <name>_Unity_Albedo.png             colour
#   <name>_Unity_MetallicSmoothness.png R = metallic, A = smoothness (1 - roughness)
#   <name>_Unity_Normal.png             tangent-space normal map (OpenGL, as Unity expects), re-baked for the new UVs
# Output names always contain "_Unity_" and the script never overwrites any other file (Windows names aren't
# case-sensitive, so e.g. "_Normal" would otherwise replace an original "_normal").
# Then rebuilds the material on the new maps, removes the old UVs and saves a new .blend.
#   blender -b fish.blend --python rebake_fish.py      env: VDW_BAKE_SIZE, VDW_BAKE_NAME, VDW_SAVE_TO
import bpy, math, os
import numpy as np

def pixels(img):
    a = np.empty(len(img.pixels), dtype=np.float32); img.pixels.foreach_get(a); return a.reshape(-1, 4)

SIZE = int(os.environ.get("VDW_BAKE_SIZE", "2048"))
NAME = os.environ.get("VDW_BAKE_NAME", "fish")
SAVE_TO = os.environ["VDW_SAVE_TO"]
OUT_DIR = os.path.dirname(SAVE_TO)

mesh = next(o for o in bpy.data.objects if o.type == 'MESH')
arm = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
mat = mesh.material_slots[0].material
nt = mat.node_tree
nodes, links = nt.nodes, nt.links
scene = bpy.context.scene

if arm: arm.data.pose_position = 'REST'   # bake the undeformed fish

# Data textures hold numbers, not colours.
for n in nodes:
    if n.type == 'TEX_IMAGE' and n.image and any(k in (n.image.name + n.image.filepath).lower() for k in ("metal", "rough", "normal")):
        n.image.colorspace_settings.name = 'Non-Color'

# ---- 1. clean UVs on a new layer (the old one stays for reading the textures)
old_uv = mesh.data.uv_layers.active.name
new_uv = mesh.data.uv_layers.new(name="UVClean")
mesh.data.uv_layers.active = new_uv
for o in bpy.context.view_layer.objects: o.select_set(False)
bpy.context.view_layer.objects.active = mesh; mesh.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
bpy.ops.uv.pack_islands(rotate=True, rotate_method='ANY', scale=True, margin_method='FRACTION', margin=0.004, shape_method='CONCAVE')
bpy.ops.object.mode_set(mode='OBJECT')
print("  islands packed on", new_uv.name)

# Textures keep reading the OLD layout.
uvnode = nodes.new("ShaderNodeUVMap"); uvnode.uv_map = old_uv
tex = {}
for n in nodes:
    if n.type == 'TEX_IMAGE':
        links.new(uvnode.outputs["UV"], n.inputs["Vector"])
        key = (n.image.name + " " + bpy.path.basename(n.image.filepath)).lower()
        tex["normal" if "normal" in key else "metal" if "metal" in key else "rough" if "rough" in key else "color"] = n
    if n.type == 'NORMAL_MAP':
        n.uv_map = old_uv
        n.inputs["Strength"].default_value = 1.0   # bake the normal map's real detail (Unity applies it at full strength)

# ---- 2. bake
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.render.bake.margin = 16
scene.render.bake.use_clear = True
out = next(n for n in nodes if n.type == 'OUTPUT_MATERIAL')
bsdf = next(n for n in nodes if n.type == 'BSDF_PRINCIPLED')
emit = nodes.new("ShaderNodeEmission")

def target(name, non_color):
    img = bpy.data.images.new(name, SIZE, SIZE, alpha=False, float_buffer=False)
    if non_color: img.colorspace_settings.name = 'Non-Color'
    node = nodes.new("ShaderNodeTexImage"); node.image = img
    for n in nodes: n.select = False
    node.select = True; nodes.active = node
    return img, node

def bake_emit(source_node, name, non_color, samples=4):
    img, node = target(name, non_color)
    links.new(source_node.outputs["Color"], emit.inputs["Color"])
    links.new(emit.outputs["Emission"], out.inputs["Surface"])
    scene.cycles.samples = samples
    bpy.ops.object.bake(type='EMIT')
    nodes.remove(node)
    print("  baked", name)
    return img

albedo = bake_emit(tex["color"], f"{NAME}_Unity_Albedo", False)
metal = bake_emit(tex["metal"], f"{NAME}_metal_tmp", True)
rough = bake_emit(tex["rough"], f"{NAME}_rough_tmp", True)

# Normal: the real material, baked as tangent-space normals for the new UVs.
links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
nimg, nnode = target(f"{NAME}_Unity_Normal", True)
scene.cycles.samples = 8
scene.render.bake.normal_space = 'TANGENT'
scene.render.bake.normal_r, scene.render.bake.normal_g, scene.render.bake.normal_b = 'POS_X', 'POS_Y', 'POS_Z'  # OpenGL (Unity)
bpy.ops.object.bake(type='NORMAL')
nodes.remove(nnode)
print("  baked", nimg.name)

# ---- 3. Unity maps
# Patches where the old UVs had collapsed faces come out pointing into the surface (olive); make them flat instead.
n_px = pixels(nimg)
bad = n_px[:, 2] < 0.45
n_px[bad] = (0.5, 0.5, 1.0, 1.0)
nimg.pixels.foreach_set(n_px.ravel())
print(f"  normal: flattened {bad.mean() * 100:.2f}% of pixels (collapsed old UVs)")

ms = bpy.data.images.new(f"{NAME}_Unity_MetallicSmoothness", SIZE, SIZE, alpha=True, float_buffer=False)
ms.colorspace_settings.name = 'Non-Color'
m, r = pixels(metal), pixels(rough)
px = np.empty_like(m)
px[:, 0] = px[:, 1] = px[:, 2] = m[:, 0]
px[:, 3] = 1.0 - r[:, 0]
ms.pixels.foreach_set(px.ravel())

def save(img):
    path = os.path.join(OUT_DIR, img.name + ".png")
    if "_Unity_" not in img.name:
        raise RuntimeError("refusing to write a file without _Unity_ in its name: " + path)
    img.filepath_raw = path; img.file_format = 'PNG'
    img.save()
    print("  saved", img.filepath_raw)
for img in (albedo, ms, nimg):
    save(img)

# ---- 4. the material on the new maps only; old UVs and old textures gone
for n in list(nodes):
    if n not in (bsdf, out): nodes.remove(n)
def node_img(img, x, y):
    n = nodes.new("ShaderNodeTexImage"); n.image = img; n.location = (x, y); return n
a = node_img(albedo, -700, 300)
s = node_img(ms, -700, 0)
nm = node_img(nimg, -700, -320)
links.new(a.outputs["Color"], bsdf.inputs["Base Color"])
links.new(s.outputs["Color"], bsdf.inputs["Metallic"])
inv = nodes.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0; inv.location = (-350, -60)
links.new(s.outputs["Alpha"], inv.inputs[1]); links.new(inv.outputs["Value"], bsdf.inputs["Roughness"])
nmap = nodes.new("ShaderNodeNormalMap"); nmap.location = (-350, -320)
links.new(nm.outputs["Color"], nmap.inputs["Color"]); links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
nodes.active = a   # the viewport's texture preview shows the colour map
for img in (metal, rough):
    bpy.data.images.remove(img)

mesh.data.uv_layers.remove(mesh.data.uv_layers[old_uv])
mesh.data.uv_layers["UVClean"].name = "UVMap"
mesh.data.uv_layers["UVMap"].active = True
mesh.data.uv_layers["UVMap"].active_render = True
nmap.uv_map = "UVMap"
if arm: arm.data.pose_position = 'POSE'
scene.render.engine = 'BLENDER_EEVEE_NEXT'

bpy.ops.wm.save_as_mainfile(filepath=SAVE_TO)
print("  saved blend", SAVE_TO)
print("REBAKE DONE")

