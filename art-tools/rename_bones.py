# Renames bones so they drive the vertex groups the user painted (a bone moves only the group with its exact name),
# optionally parenting them to another bone; weights are not touched. Saves to VDW_SAVE_TO.
#   blender -b fish.blend --python rename_bones.py    env: VDW_RENAME "old=new,old=new", VDW_PARENT (e.g. Head), VDW_SAVE_TO
import bpy, os
# a file saved in Edit / Weight Paint mode: back to Object Mode first (in Edit Mode the armature modifier is off, so
# nothing deforms, and edits in progress aren't in the mesh data)
for _o in list(bpy.data.objects):
    if _o.mode != 'OBJECT' and _o.name in bpy.context.view_layer.objects:
        bpy.context.view_layer.objects.active = _o
        try: bpy.ops.object.mode_set(mode='OBJECT')
        except RuntimeError: pass
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
pairs = [p.split("=") for p in os.environ["VDW_RENAME"].split(",") if p]
arm.hide_set(False); arm.hide_viewport = False
for o in bpy.context.view_layer.objects: o.select_set(o == arm)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT'); eb = arm.data.edit_bones; par = os.environ.get("VDW_PARENT")
for old, new in pairs:
    if old not in eb: print(f"  no bone {old}"); continue
    b = eb[old]; b.name = new; b.use_deform = True
    if par and par in eb and b.parent != eb[par]: b.parent = eb[par]; b.use_connect = False
    print(f"  bone {old} -> {new}" + (f", parent {par}" if par else ""))
bpy.ops.object.mode_set(mode='OBJECT')
mesh = next((o for o in bpy.data.objects if o.type == 'MESH' and o.parent == arm), None)
if mesh:
    names = {b.name for b in arm.data.bones}
    for old, new in pairs:
        g = mesh.vertex_groups.get(new)
        n = sum(1 for v in mesh.data.vertices for x in v.groups if g and x.group == g.index and x.weight > 0.01)
        print(f"  group {new}: {n} weighted points, bone present: {new in names}")
bpy.ops.wm.save_as_mainfile(filepath=os.environ["VDW_SAVE_TO"]); print("  saved", os.environ["VDW_SAVE_TO"])
