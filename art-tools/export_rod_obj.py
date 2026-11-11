# A rod built and baked like a lure (build_lures.py ice_rod -> restyle_lure.py -> bake_wood_cooler.py VDW_KIND=lure)
# out as the OBJ rig_rod2.py reads: the baked "bait" mesh alone, in centimetres, rod along +Z, its baked atlas UVs.
#   blender -b <bait_<tier>_baked.blend> --factory-startup --python export_rod_obj.py
#   env: VDW_OBJ (the .obj to write; new files only)
import bpy, os
OUT = os.environ["VDW_OBJ"]
if os.path.exists(OUT): raise SystemExit("exists, kept: " + OUT)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
ob = bpy.data.objects["bait"]; me = ob.data
for md in list(ob.modifiers): ob.modifiers.remove(md)
mw = ob.matrix_world.copy(); ob.parent = None; me.transform(mw); ob.matrix_world.identity()
if "Grain" in me.uv_layers: me.uv_layers.remove(me.uv_layers["Grain"])
me.uv_layers.active = me.uv_layers["UVMap"]
for o in bpy.data.objects: o.select_set(o == ob)
bpy.context.view_layer.objects.active = ob
# (the importer's default axes, both ways: rig_rod2.py reads it back as it was)
bpy.ops.wm.obj_export(filepath=OUT, export_selected_objects=True, global_scale=100.0, export_uv=True, export_normals=True,
                      export_materials=False, apply_modifiers=False)
co = [v.co for v in me.vertices]
print(f"EXPORTED {OUT}: {len(co)} verts, {max(c.z for c in co) - min(c.z for c in co):.3f} m long")
