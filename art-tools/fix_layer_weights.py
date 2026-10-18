# Layers under the coat move with the coat: the shirt (and the overalls' bib above the waist) take their weights from the
# coat's nearest surface, so they can't drift through it. And the coat's weights round the armpits are smoothed, so the
# sleeve bends there instead of folding into the side. Writes a new .blend.
#   blender -b rig.blend --python fix_layer_weights.py      env: VDW_SAVE_TO
import bpy, os
SAVE_TO = os.environ["VDW_SAVE_TO"]
arm = bpy.data.objects["Armature"]
def head(n): return arm.matrix_world @ arm.data.bones[n].head_local
coat = bpy.data.objects["coat"]; waist = head("Spine").z
def from_coat(ob, zmin):
    keep = {}                                              # below zmin: the piece keeps its own weights
    for v in ob.data.vertices:
        if (ob.matrix_world @ v.co).z < zmin:
            keep[v.index] = {ob.vertex_groups[g.group].name: g.weight for g in v.groups}
    for g in coat.vertex_groups:
        if g.name not in ob.vertex_groups: ob.vertex_groups.new(name=g.name)
    dt = ob.modifiers.new("from coat", 'DATA_TRANSFER'); dt.object = coat
    dt.use_vert_data = True; dt.data_types_verts = {'VGROUP_WEIGHTS'}; dt.vert_mapping = 'POLYINTERP_NEAREST'
    dt.layers_vgroup_select_src = 'ALL'; dt.layers_vgroup_select_dst = 'NAME'; dt.mix_mode = 'REPLACE'
    for o in bpy.data.objects: o.select_set(o == ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_move_to_index(modifier=dt.name, index=0)
    bpy.ops.object.modifier_apply(modifier=dt.name)
    for idx, ws in keep.items():                           # put the lower part back as it was
        for g in ob.vertex_groups: g.remove([idx])
        for n, w in ws.items(): ob.vertex_groups[n].add([idx], w, 'REPLACE')
    print(f"  {ob.name}: weights from the coat above z {zmin:.0f} cm ({len(ob.data.vertices) - len(keep)} points)")
if os.environ.get("VDW_SHIRT_FROM_COAT", "0") == "1": from_coat(bpy.data.objects["shirt"], -1e9)
if os.environ.get("VDW_BIB_FROM_COAT", "0") == "1": from_coat(bpy.data.objects["overalls"], waist + 4)
# armpits: smooth the coat's weights in a band round each shoulder joint
sx = abs(head("LeftArm").x); top = head("LeftArm").z
sel = set()
for v in coat.data.vertices:
    p = coat.matrix_world @ v.co
    if abs(abs(p.x) - sx) < 9 and top - 28 < p.z < top + 6: sel.add(v.index)
for o in bpy.data.objects: o.select_set(o == coat)
bpy.context.view_layer.objects.active = coat
for v in coat.data.vertices: v.select = v.index in sel
bpy.ops.object.mode_set(mode='WEIGHT_PAINT'); coat.data.use_paint_mask_vertex = True
bpy.ops.object.vertex_group_smooth(group_select_mode='BONE_DEFORM', factor=0.5, repeat=6)
bpy.ops.object.vertex_group_normalize_all(group_select_mode='BONE_DEFORM', lock_active=False)
coat.data.use_paint_mask_vertex = False; bpy.ops.object.mode_set(mode='OBJECT')
print(f"  coat: armpit weights smoothed on {len(sel)} points")
bpy.ops.wm.save_as_mainfile(filepath=SAVE_TO, copy=True); print("  saved", SAVE_TO)
