# Readies a bait built by build_lures.py for the Sanctus + Grungit bake (bake_wood_cooler.py VDW_KIND=lure): the shape
# is kept, but instead of build_lures' painted atlas each face gets a material slot named after its atlas tile (bone,
# steel, feather...), the "Grain" UVs run along the bait, and a fresh "UVMap" atlas is unwrapped. One object "bait".
#   blender -b <build_lures output>.blend --factory-startup --python restyle_lure.py      env: VDW_OUT (new .blend)
import bpy, os, re, math
import numpy as np

OUT = os.environ["VDW_OUT"]
if os.path.exists(OUT): raise SystemExit("exists, kept: " + OUT)
# build_lures.py's atlas: its MATS names in order, G x G tiles
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "build_lures.py"), encoding="utf-8").read()
block = src[src.index("MATS = {"):]; block = block[:block.index("\n}")]
NAMES = re.findall(r'^\s*"([a-z_]+)":', block, re.M)
G = int(re.search(r"^G = (\d+)", src, re.M).group(1))

ob = next(o for o in bpy.data.objects if o.type == 'MESH'); me = ob.data
uv = me.uv_layers.active
used, idx = [], []
for p in me.polygons:
    u = np.mean([uv.data[li].uv[0] for li in p.loop_indices]); v = np.mean([uv.data[li].uv[1] for li in p.loop_indices])
    name = NAMES[min(G - 1, int(v * G)) * G + min(G - 1, int(u * G))]
    if name not in used: used.append(name)
    idx.append(used.index(name))
me.materials.clear()
for n in used: me.materials.append(bpy.data.materials.new(n))
for p, i in zip(me.polygons, idx): p.material_index = i
for l in list(me.uv_layers): me.uv_layers.remove(l)
# "Grain" (metres): along the bait (Y), round it - so wood, feathers and thread run its length
grain = me.uv_layers.new(name="Grain")
for p in me.polygons:
    for li in p.loop_indices:
        c = me.vertices[me.loops[li].vertex_index].co
        grain.data[li].uv = (c.y, math.atan2(c.z, c.x) * 0.01)
atlas = me.uv_layers.new(name="UVMap"); me.uv_layers.active = atlas; atlas.active_render = True
ob.name = me.name = "bait"
for o in list(bpy.data.objects):
    if o is not ob: bpy.data.objects.remove(o)
bpy.context.view_layer.objects.active = ob; ob.select_set(True)
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.006, scale_to_bounds=False)
bpy.ops.uv.pack_islands(margin=0.006)
bpy.ops.object.mode_set(mode='OBJECT')
print(f"RESTYLE: {len(me.polygons)} faces ({sum(len(p.vertices) - 2 for p in me.polygons)} triangles), slots " + ", ".join(f"{n} {idx.count(i)}" for i, n in enumerate(used)))
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT); print("SAVED", OUT)
