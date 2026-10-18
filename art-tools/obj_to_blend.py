import bpy, os
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
bpy.ops.wm.obj_import(filepath=os.environ["OBJ"])
m = next(o for o in bpy.data.objects if o.type == 'MESH'); m.name = "bait_worm"
for o in bpy.context.view_layer.objects: o.select_set(False)
m.select_set(True); bpy.context.view_layer.objects.active = m
m.scale = tuple(s * 0.01 for s in m.scale); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)   # cm -> m
mat = bpy.data.materials.new("worm"); mat.use_nodes = True; nt = mat.node_tree; b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(os.environ["TEX"]); nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
m.data.materials.clear(); m.data.materials.append(mat)
bpy.ops.wm.save_as_mainfile(filepath=os.environ["OUT"])
