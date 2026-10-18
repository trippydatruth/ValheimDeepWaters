# Gives a fish whose material has only a colour map (raw glTF / OBJ downloads) the Unity map set the other tools expect:
#   <NAME>_Unity_Albedo (its colour map), _MetallicSmoothness (wet scales: not metal, smoothness from brightness),
#   _Normal (flat, or VDW_NORMAL if given), wired into the Principled BSDF. Never overwrites.
#   blender -b fish.blend --python prep_unity_material.py      env: VDW_NAME, VDW_TEX_DIR, VDW_SAVE_TO, VDW_NORMAL (optional)
import bpy, os
import numpy as np

NAME = os.environ["VDW_NAME"]; TEX = os.environ["VDW_TEX_DIR"]
mesh = max((o for o in bpy.data.objects if o.type == 'MESH'), key=lambda o: len(o.data.vertices))
mat = mesh.data.materials[0]; nt = mat.node_tree; N, L = nt.nodes, nt.links
bs = next(n for n in N if n.type == 'BSDF_PRINCIPLED')
src = bs.inputs["Base Color"].links[0].from_node.image
W, H = src.size; px = np.empty(W * H * 4, np.float32); src.pixels.foreach_get(px); px = px.reshape(-1, 4)

def save(arr, kind, nc=False):
    path = os.path.join(TEX, f"{NAME}_Unity_{kind}.png")
    if os.path.exists(path): print("  exists, kept:", path); return bpy.data.images.load(path)
    im = bpy.data.images.new(f"{NAME}_Unity_{kind}", W, H, alpha=True)
    if nc: im.colorspace_settings.name = 'Non-Color'
    im.pixels.foreach_set(np.ascontiguousarray(arr, np.float32).ravel()); im.filepath_raw = path; im.file_format = 'PNG'; im.save()
    print("  saved", path); return im

a = px.copy(); a[:, 3] = 1; alb = save(a, "Albedo")
lum = px[:, :3].mean(1); ms = np.zeros_like(px); ms[:, 3] = np.clip(0.6 + 0.3 * (lum - lum.mean()), 0.35, 0.85)
msi = save(ms, "MetallicSmoothness", True)
if os.environ.get("VDW_NORMAL"):
    ni = bpy.data.images.load(os.environ["VDW_NORMAL"])
    if tuple(ni.size) != (W, H): ni.scale(W, H)                 # match the colour map
    npx = np.empty(len(ni.pixels), np.float32); ni.pixels.foreach_get(npx)
    nrm = save(npx.reshape(-1, 4), "Normal", True)
else:
    flat = np.zeros_like(px); flat[:] = (0.5, 0.5, 1.0, 1.0); nrm = save(flat, "Normal", True)

for l in list(bs.inputs["Base Color"].links) + list(bs.inputs["Metallic"].links) + list(bs.inputs["Roughness"].links) + list(bs.inputs["Normal"].links):
    L.remove(l)
def tex(img, y):
    t = N.new("ShaderNodeTexImage"); t.image = img; t.location = (-700, y); return t
L.new(tex(alb, 300).outputs["Color"], bs.inputs["Base Color"])
s = tex(msi, 0); L.new(s.outputs["Color"], bs.inputs["Metallic"])
inv = N.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
L.new(s.outputs["Alpha"], inv.inputs[1]); L.new(inv.outputs["Value"], bs.inputs["Roughness"])
nm = N.new("ShaderNodeNormalMap"); L.new(tex(nrm, -320).outputs["Color"], nm.inputs["Color"]); L.new(nm.outputs["Normal"], bs.inputs["Normal"])
mat.name = NAME
for img in list(bpy.data.images):
    if img.users == 0: bpy.data.images.remove(img)
bpy.ops.wm.save_as_mainfile(filepath=os.environ["VDW_SAVE_TO"]); print("  saved", os.environ["VDW_SAVE_TO"])
