# Builds a source .blend from a download: imports the FBX / OBJ and wires its PBR maps (BaseColor, Normal,
# Roughness, Metallic, matched by name in the given folder) into one Principled material, packed into the file, so the
# fish pipeline (prep_sourced_fish.py) can start from it. Never overwrites.
#   blender -b --python make_source_blend.py -- <model.fbx|.obj|.glb> <maps_dir> <maps name part, or - for any> <out.blend>
# A .glb carries its own materials: maps_dir - keeps them (images packed).
import bpy, os, sys, glob
fbx, maps_dir, part, out = sys.argv[sys.argv.index("--") + 1:]
if part == "-": part = ""            # "-" = any map in the folder
if os.path.exists(out): raise SystemExit("refusing to overwrite " + out)
bpy.ops.wm.read_factory_settings(use_empty=True)
ext = os.path.splitext(fbx)[1].lower()
if ext in ('.glb', '.gltf'): bpy.ops.import_scene.gltf(filepath=fbx)
elif ext == '.obj': bpy.ops.wm.obj_import(filepath=fbx)
else: bpy.ops.import_scene.fbx(filepath=fbx)
if maps_dir == '-':
    for im in bpy.data.images:
        if im.size[0] and not im.packed_file: im.pack()
    os.makedirs(os.path.dirname(out), exist_ok=True); bpy.ops.wm.save_as_mainfile(filepath=out); print('  saved', out); raise SystemExit
def find(kind):
    c = [p for p in glob.glob(os.path.join(maps_dir, "*.png")) if kind.lower() in os.path.basename(p).lower() and part.lower() in os.path.basename(p).lower()]
    return sorted(c, key=os.path.getmtime)[-1] if c else None
maps = {k: find(k) for k in ("BaseColor", "Normal", "Roughness", "Metallic")}
print("  maps:", {k: os.path.basename(v) if v else None for k, v in maps.items()})
mat = bpy.data.materials.new("source"); mat.use_nodes = True; nt = mat.node_tree; N, L = nt.nodes, nt.links
bs = next(n for n in N if n.type == 'BSDF_PRINCIPLED')
def tex(path, nc, y):
    t = N.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(path); t.location = (-600, y)
    if nc: t.image.colorspace_settings.name = 'Non-Color'
    return t
if maps["BaseColor"]: L.new(tex(maps["BaseColor"], False, 300).outputs["Color"], bs.inputs["Base Color"])
if maps["Roughness"]: L.new(tex(maps["Roughness"], True, 0).outputs["Color"], bs.inputs["Roughness"])
if maps["Metallic"]: L.new(tex(maps["Metallic"], True, -250).outputs["Color"], bs.inputs["Metallic"])
if maps["Normal"]:
    nm = N.new("ShaderNodeNormalMap"); L.new(tex(maps["Normal"], True, -500).outputs["Color"], nm.inputs["Color"]); L.new(nm.outputs["Normal"], bs.inputs["Normal"])
for o in bpy.data.objects:
    if o.type == 'MESH': o.data.materials.clear(); o.data.materials.append(mat)
for im in bpy.data.images:
    if im.filepath: im.pack()
os.makedirs(os.path.dirname(out), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=out); print("  saved", out)
