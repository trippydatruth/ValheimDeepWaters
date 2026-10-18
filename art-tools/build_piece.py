# Turns a Tripo PBR .obj (BaseColor / Metallic / Roughness / Normal) into a buildable piece model:
#   - one mesh, standing on its base: origin at the middle of the base, bottom at 0
#   - scaled to VDW_HEIGHT metres tall, facing -Y in Blender (exports facing +Z in Unity)
#   - Unity maps at VDW_TEX_SIZE: <name>_Unity_Albedo / _MetallicSmoothness (R metallic, A 1-roughness) / _Normal
#   - a material wired with those maps (so emission_map.py can run on the saved .blend)
# env: VDW_OBJ, VDW_TEX_DIR (Tripo textures), VDW_NAME, VDW_OUT_TEX (folder for the Unity maps), VDW_SAVE_TO,
#      VDW_HEIGHT (1.8), VDW_TEX_SIZE (2048), VDW_TURN (extra degrees about Z if the model faces the wrong way)
import bpy, glob, math, os
import numpy as np
from mathutils import Matrix, Vector

NAME = os.environ["VDW_NAME"]; HEIGHT = float(os.environ.get("VDW_HEIGHT", "1.8"))
SIZE = int(os.environ.get("VDW_TEX_SIZE", "2048")); OUT = os.environ["VDW_OUT_TEX"]; TEX = os.environ["VDW_TEX_DIR"]
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
bpy.ops.wm.obj_import(filepath=os.environ["VDW_OBJ"])
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
for o in bpy.data.objects: o.select_set(o in meshes)
bpy.context.view_layer.objects.active = meshes[0]
if len(meshes) > 1: bpy.ops.object.join()
ob = bpy.context.view_layer.objects.active; ob.name = NAME; ob.data.name = NAME
ob.data.transform(ob.matrix_world); ob.matrix_world = Matrix()
turn = float(os.environ.get("VDW_TURN", "0"))
if turn: ob.data.transform(Matrix.Rotation(math.radians(turn), 4, 'Z'))

co = np.array([v.co[:] for v in ob.data.vertices])
lo, hi = co.min(0), co.max(0)
s = HEIGHT / (hi[2] - lo[2])
base = co[co[:, 2] < lo[2] + 0.05 * (hi[2] - lo[2])]                 # the bottom 5%: centre the base on the origin
cx, cy = (base[:, 0].min() + base[:, 0].max()) / 2, (base[:, 1].min() + base[:, 1].max()) / 2
ob.data.transform(Matrix.Scale(s, 4) @ Matrix.Translation((-cx, -cy, -lo[2])))
ob.data.update()
co = np.array([v.co[:] for v in ob.data.vertices])
print(f"PIECE {NAME}: {len(co)} verts, size {((co.max(0) - co.min(0)) * 100).round(1)} cm, base footprint "
      f"{((base.max(0) - base.min(0))[:2] * s * 100).round(1)} cm")

# ---------------------------------------------------------------- Unity maps
def find(kind):
    f = glob.glob(os.path.join(TEX, f"*_{kind}.png")); return f[0] if f else None
def load(path):
    im = bpy.data.images.load(path)
    if im.size[0] != SIZE: im.scale(SIZE, SIZE)
    return np.array(im.pixels[:], dtype=np.float32).reshape(SIZE, SIZE, 4)
def save(px, kind):
    im = bpy.data.images.new(f"{NAME}_Unity_{kind}", SIZE, SIZE, alpha=True)
    im.pixels[:] = px.ravel(); path = os.path.join(OUT, f"{NAME}_Unity_{kind}.png")
    im.filepath_raw = path; im.file_format = 'PNG'; im.save(); print("MAP", os.path.basename(path)); return path
os.makedirs(OUT, exist_ok=True)
alb = load(find("BaseColor")); alb[..., 3] = 1.0
p_alb = save(alb, "Albedo")
met = load(find("Metallic")) if find("Metallic") else np.zeros_like(alb)
rough = load(find("Roughness")) if find("Roughness") else np.full_like(alb, 0.8)
ms = np.zeros_like(alb); ms[..., :3] = met[..., :1]; ms[..., 3] = 1.0 - rough[..., 0]
p_ms = save(ms, "MetallicSmoothness")
p_nrm = save(load(find("Normal")), "Normal")
print(f"STATS metallic {met[..., 0].mean():.2f}, smoothness {ms[..., 3].mean():.2f}")

# ---------------------------------------------------------------- material (for previews and emission_map.py)
mat = bpy.data.materials.new(NAME); mat.use_nodes = True
nt = mat.node_tree; b = nt.nodes["Principled BSDF"]; L = nt.links.new
def img(path, color=True):
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(path)
    if not color: t.image.colorspace_settings.name = "Non-Color"
    return t
a = img(p_alb); L(a.outputs["Color"], b.inputs["Base Color"])
m = img(p_ms, False); sep = nt.nodes.new("ShaderNodeSeparateColor"); L(m.outputs["Color"], sep.inputs["Color"]); L(sep.outputs["Red"], b.inputs["Metallic"])
inv = nt.nodes.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0; L(m.outputs["Alpha"], inv.inputs[1]); L(inv.outputs[0], b.inputs["Roughness"])
n = img(p_nrm, False); nm = nt.nodes.new("ShaderNodeNormalMap"); L(n.outputs["Color"], nm.inputs["Color"]); L(nm.outputs["Normal"], b.inputs["Normal"])
ob.data.materials.clear(); ob.data.materials.append(mat)
for i in list(bpy.data.images):
    if i.users == 0: bpy.data.images.remove(i)
bpy.ops.wm.save_as_mainfile(filepath=os.environ["VDW_SAVE_TO"])
print("SAVED", os.environ["VDW_SAVE_TO"])
