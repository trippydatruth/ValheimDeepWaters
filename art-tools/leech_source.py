import bpy, os
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE'); mesh = next(o for o in bpy.data.objects if o.type == 'MESH' and o.parent == arm)
neck = arm.matrix_world @ arm.data.bones["c_neck13_bn"].head_local; pelvis = arm.matrix_world @ arm.data.bones["c_pelvis_bn"].head_local
print("HEADPOS neck13", tuple(round(x, 3) for x in neck), "pelvis", tuple(round(x, 3) for x in pelvis))
mw = mesh.matrix_world.copy(); mesh.parent = None; mesh.matrix_world = mw
for m in list(mesh.modifiers): mesh.modifiers.remove(m)
for g in list(mesh.vertex_groups): mesh.vertex_groups.remove(g)
for o in [o for o in bpy.data.objects if o is not mesh]: bpy.data.objects.remove(o)
for a in list(bpy.data.actions): bpy.data.actions.remove(a)
bpy.context.view_layer.update()
for o in bpy.data.objects: o.select_set(False)
mesh.select_set(True); bpy.context.view_layer.objects.active = mesh; bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
mesh.name = "bait_leech"
for uv in list(mesh.data.uv_layers)[1:]: mesh.data.uv_layers.remove(uv)
mat = bpy.data.materials.new("bait_leech"); mat.use_nodes = True; nt = mat.node_tree; b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
T = os.environ["TEXD"]
a = nt.nodes.new("ShaderNodeTexImage"); a.image = bpy.data.images.load(os.path.join(T, "bait_leech_Unity_Albedo.png")); nt.links.new(a.outputs["Color"], b.inputs["Base Color"])
n = nt.nodes.new("ShaderNodeTexImage"); n.image = bpy.data.images.load(os.path.join(T, "bait_leech_Unity_Normal.png")); n.image.colorspace_settings.name = 'Non-Color'
nm = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(n.outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
nt.nodes.active = a
mesh.data.materials.clear(); mesh.data.materials.append(mat)
for m in list(bpy.data.materials):
    if m.users == 0: bpy.data.materials.remove(m)
for m in list(bpy.data.meshes):
    if m.users == 0: bpy.data.meshes.remove(m)
for i in list(bpy.data.images):
    if i.users == 0: bpy.data.images.remove(i)
bpy.ops.wm.save_as_mainfile(filepath=os.environ["OUT"]); print("SAVED", [o.name for o in bpy.data.objects], len(mesh.data.vertices))

