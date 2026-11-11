# Readies a hand-fixed mead bottle (a .blend with "glass", "liquid" and "cork" objects, e.g. Mesh\mead bottle\Blender
# Files\fixedmodel.blend) for the Sanctus + Grungit bake and export:
#   <out>/Blender Files/mead_bottle_<v>_restyled.blend - glass + liquid joined as one object "bait" (slots "glass" and
#       "mead"), transforms applied, a "Grain" UV and a fresh "UVMap" atlas unwrapped (bake_wood_cooler.py VDW_KIND=lure)
#   <out>/Blender Files/mead_cork_<v>.blend - the cork as it is (its UVs and old texture kept), transforms applied
#       (export_mead.py VDW_CORK)
# The source file is only read.
#   blender -b <fixed>.blend --factory-startup --python prep_mead_fixed.py      env: VDW_OUT (folder), VDW_V (v4)
import bpy, os, math
from mathutils import Matrix

OUT = os.environ["VDW_OUT"]; V = os.environ.get("VDW_V", "v4")
BF = os.path.join(OUT, "Blender Files"); os.makedirs(BF, exist_ok=True)
RESTYLED = os.path.join(BF, f"mead_bottle_{V}_restyled.blend"); CORK = os.path.join(BF, f"mead_cork_{V}.blend")
for p in (RESTYLED, CORK):
    if os.path.exists(p): raise SystemExit("exists, kept: " + p)

def flatten(ob):
    for md in list(ob.modifiers): ob.modifiers.remove(md)
    ob.data = ob.data.copy()
    mw = ob.matrix_world.copy(); ob.parent = None
    ob.data.transform(mw); ob.matrix_world = Matrix.Identity(4)

glass, liquid, cork = (bpy.data.objects[n] for n in ("glass", "liquid", "cork"))
for o in (glass, liquid, cork): flatten(o)

# the cork on its own
keep = {cork}
for o in list(bpy.data.objects):
    if o not in (glass, liquid, cork): bpy.data.objects.remove(o)
for o in (glass, liquid): o.hide_render = False
bpy.ops.wm.save_as_mainfile(filepath=CORK, copy=True)   # (glass and liquid are dropped from it below by export)
print("SAVED", CORK)

# glass + liquid: one object, a slot each
mg, ml = bpy.data.materials.new("glass"), bpy.data.materials.new("mead")
for o, m in ((glass, mg), (liquid, ml)):
    o.data.materials.clear(); o.data.materials.append(m)
    for p in o.data.polygons: p.material_index = 0
    for l in list(o.data.uv_layers): o.data.uv_layers.remove(l)
bpy.data.objects.remove(cork)
for o in bpy.context.view_layer.objects: o.select_set(o in (glass, liquid))
bpy.context.view_layer.objects.active = glass
bpy.ops.object.join()
ob = bpy.context.view_layer.objects.active; me = ob.data
ob.name = me.name = "bait"
# "Grain" (metres): up the bottle and round it
grain = me.uv_layers.new(name="Grain")
for p in me.polygons:
    for li in p.loop_indices:
        c = me.vertices[me.loops[li].vertex_index].co
        grain.data[li].uv = (c.z, math.atan2(c.y, c.x) * 0.01)
atlas = me.uv_layers.new(name="UVMap"); me.uv_layers.active = atlas; atlas.active_render = True
ob.select_set(True)
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.006, scale_to_bounds=False)
bpy.ops.object.mode_set(mode='OBJECT')
print(f"BAIT {len(me.polygons)} faces, slots {[m.name for m in me.materials]}")
bpy.ops.wm.save_as_mainfile(filepath=RESTYLED)
print("SAVED", RESTYLED)
