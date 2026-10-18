# The Dried Fish item (prep_dried) from the user's CGTrader "Hanged Dried Fish" (Mesh/cleaning table/models/HangedDriedFish.glb):
# one mesh of fish, string and hooks (56k faces, three 4K materials) cut down to VDW_FACES faces, its three materials baked
# into one VDW_TEX albedo on a fresh UV layout (the only UV layer left, as Unity reads the first), stood upright at
# VDW_HEIGHT metres with the origin at the middle of its base. The download is left untouched.
# Writes <out>/Blender Files/prep_dried.blend, <out>/Textures/prep_dried_Unity_Albedo.png, <out>/Models/prep_dried.fbx (via export_static).
# env: VDW_GLB, VDW_OUT, VDW_FACES (4000), VDW_TEX (1024), VDW_HEIGHT (0.55)
import bpy, os, math
import numpy as np
from mathutils import Matrix, Vector

GLB = os.environ["VDW_GLB"]; OUT = os.environ["VDW_OUT"]; NAME = "prep_dried"
FACES = int(os.environ.get("VDW_FACES", "4000")); TEX = int(os.environ.get("VDW_TEX", "1024")); HEIGHT = float(os.environ.get("VDW_HEIGHT", "0.55"))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
ms = [o for o in bpy.data.objects if o.type == 'MESH']
for o in bpy.data.objects: o.select_set(o in ms)
bpy.context.view_layer.objects.active = ms[0]
if len(ms) > 1: bpy.ops.object.join()
ob = bpy.context.view_layer.objects.active; ob.name = NAME; ob.data.name = NAME
ob.data.transform(ob.matrix_world); ob.parent = None; ob.matrix_world = Matrix()
for o in [o for o in bpy.data.objects if o is not ob]: bpy.data.objects.remove(o)
co = np.array([v.co[:] for v in ob.data.vertices]); lo, hi = co.min(0), co.max(0)
s = HEIGHT / (hi[2] - lo[2])
ob.data.transform(Matrix.Scale(s, 4) @ Matrix.Translation(Vector((-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]))))
print(f"source {len(ob.data.polygons)} faces, scaled x{s:.3f} to {HEIGHT} m tall")

# fewer faces
m = ob.modifiers.new("dec", 'DECIMATE'); m.ratio = min(1.0, FACES / len(ob.data.polygons)); m.use_collapse_triangulate = True
bpy.context.view_layer.objects.active = ob; bpy.ops.object.modifier_apply(modifier="dec")
print(f"decimated to {len(ob.data.polygons)} faces")

# bake the three materials' colour into one map on a new UV layout
src_uv = ob.data.uv_layers.active
bake_uv = ob.data.uv_layers.new(name="bake"); ob.data.uv_layers.active = bake_uv; src_uv.active_render = True
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.004); bpy.ops.object.mode_set(mode='OBJECT')
img = bpy.data.images.new(NAME + "_bake", TEX, TEX, alpha=False)
for mat in ob.data.materials:
    if not mat or not mat.use_nodes: continue
    n = mat.node_tree.nodes.new("ShaderNodeTexImage"); n.image = img; mat.node_tree.nodes.active = n   # the bake target
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 4
sc.render.bake.use_pass_direct = False; sc.render.bake.use_pass_indirect = False; sc.render.bake.margin = 6
ob.select_set(True); bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'})
px = np.array(img.pixels[:], dtype=np.float32).reshape(TEX, TEX, 4); px[..., 3] = 1.0
# warmer and a little lighter: the golden dried look of the user's reference photos, not the download's grey-brown
px[..., :3] = np.clip(np.power(np.clip(px[..., :3], 0, 1), 0.82) * np.array([1.2, 1.0, 0.7]), 0, 1)
TEXD = os.path.join(OUT, "Textures"); os.makedirs(TEXD, exist_ok=True)
out = bpy.data.images.new(NAME + "_Unity_Albedo", TEX, TEX, alpha=True); out.pixels.foreach_set(px.ravel())
out.filepath_raw = os.path.join(TEXD, NAME + "_Unity_Albedo.png"); out.file_format = 'PNG'; out.save(); print("MAP", out.filepath_raw)

# only the baked layout and one material remain
ob.data.uv_layers.remove(ob.data.uv_layers[src_uv.name]); ob.data.uv_layers["bake"].active_render = True
mat = bpy.data.materials.new(NAME); mat.use_nodes = True
t = mat.node_tree.nodes.new("ShaderNodeTexImage"); t.image = out; mat.node_tree.links.new(t.outputs["Color"], mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
ob.data.materials.clear(); ob.data.materials.append(mat)
for p in ob.data.polygons: p.material_index = 0
os.makedirs(os.path.join(OUT, "Blender Files"), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "Blender Files", NAME + ".blend")); print("SAVED")
