# Readies the remade fisherman's gear (new_gear_rig.blend, painted, in metres) for export_fisher_gear.py, which wants
# the old layout: one object per piece - shirt, coat, overalls, boots, hat - and the scene in centimetres.
#   - "coat" is split by material into shirt + coat, "overalls" into overalls + boots (material "boot" -> "boots")
#   - everything (meshes, armature) scaled x100 into centimetres, transforms applied, weights and UVs kept
# Writes VDW_SAVE_TO; never touches the painted file.   blender -b new_gear_rig.blend --python gear_split_for_export.py
import bpy, bmesh, os
from mathutils import Matrix
for _o in list(bpy.data.objects):
    if _o.mode != 'OBJECT' and _o.name in bpy.context.view_layer.objects:
        bpy.context.view_layer.objects.active = _o; bpy.ops.object.mode_set(mode='OBJECT')
SAVE_TO = os.environ["VDW_SAVE_TO"]
arm = bpy.data.objects["Armature"]
for o in bpy.data.objects: o.hide_set(False); o.hide_viewport = False
for pb in arm.pose.bones: pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.rotation_euler = (0, 0, 0); pb.scale = (1, 1, 1)
PIECE = {"shirt": "shirt", "coat": "coat", "overalls": "overalls", "boot": "boots", "boots": "boots", "hat": "hat"}

def split(ob):
    """one object per material, named by PIECE (the object keeps the first; copies take the rest)"""
    me = ob.data
    used = sorted({p.material_index for p in me.polygons})
    outs = []
    for mi in used:
        m = me.materials[mi]; name = PIECE.get(m.name.lower(), m.name.lower())
        part = ob.copy(); part.data = me.copy(); bpy.context.scene.collection.objects.link(part)
        bm = bmesh.new(); bm.from_mesh(part.data)
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index != mi], context='FACES')
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
        bm.to_mesh(part.data); bm.free()
        part.data.materials.clear(); part.data.materials.append(m); m.name = name
        for p in part.data.polygons: p.material_index = 0
        part.name = name + "__new"; part.data.name = name
        outs.append(part)
    bpy.data.objects.remove(ob)
    for p in outs: p.name = p.name.replace("__new", "")
    print(f"  split into {[ (p.name, len(p.data.polygons)) for p in outs ]}")
for nm in ("coat", "overalls"):
    if nm in bpy.data.objects and len({p.material_index for p in bpy.data.objects[nm].data.polygons}) > 1: split(bpy.data.objects[nm])

# metres -> centimetres: the armature's bones and every mesh's data
S = Matrix.Scale(100.0, 4)
for o in bpy.data.objects: o.select_set(o == arm)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
for b in arm.data.edit_bones: b.head = S @ b.head; b.tail = S @ b.tail
bpy.ops.object.mode_set(mode='OBJECT')
for o in bpy.data.objects:
    if o.type == 'MESH': o.data.transform(S); o.data.update()
need = ["shirt", "coat", "overalls", "boots", "hat", "fitref"]
missing = [n for n in need if n not in bpy.data.objects]
if missing: raise SystemExit(f"missing pieces after the split: {missing}")
for n in need:
    o = bpy.data.objects[n]; me = o.data
    tot = [sum(g.weight for g in v.groups) for v in me.vertices]
    print(f"  {n}: {len(me.vertices)} points, {len(me.polygons)} faces, {len(o.vertex_groups)} groups, {sum(1 for t in tot if t < 0.01)} unweighted, "
          f"height {min(v.co.z for v in me.vertices):.1f}..{max(v.co.z for v in me.vertices):.1f} cm")
bpy.ops.wm.save_as_mainfile(filepath=SAVE_TO); print("  saved", SAVE_TO)
