import bpy, os
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE'); mesh = next(o for o in bpy.data.objects if o.type == 'MESH' and o.parent == arm)
act = next(a for a in bpy.data.actions if a.name.startswith("SKM") and a.name.endswith(os.environ["POSE"]))
arm.animation_data.action = act; bpy.context.scene.frame_set(int(os.environ.get("FRAME", "1")))
bpy.context.view_layer.update()
for o in bpy.data.objects: o.select_set(False)
mesh.select_set(True); bpy.context.view_layer.objects.active = mesh
mod = next(m for m in mesh.modifiers if m.type == 'ARMATURE')
bpy.ops.object.modifier_apply(modifier=mod.name)                 # freeze the posed shape
print("POSED with", act.name)
bpy.ops.wm.save_as_mainfile(filepath=os.environ["OUT"])
