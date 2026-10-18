# Read-only inspection of a rigged fish: run with  blender -b file.blend --python inspect_rig.py
# Prints the rig setup and test-bends a bone to see whether the mesh follows. Saves nothing.
import bpy, math
from mathutils import Vector

print("\n===== RIG INSPECTION =====")
print("Blender", bpy.app.version_string)
arms = [o for o in bpy.data.objects if o.type == 'ARMATURE']
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
print("Armatures:", [a.name for a in arms])
print("Meshes:", [(m.name, len(m.data.vertices)) for m in meshes])

for a in arms:
    print(f"\n-- Armature '{a.name}' (data '{a.data.name}')")
    print("   loc", tuple(round(v, 3) for v in a.location), "rot", tuple(round(math.degrees(v), 1) for v in a.rotation_euler),
          "scale", tuple(round(v, 3) for v in a.scale))
    print("   pose_position:", a.data.pose_position)
    print("   bones:")
    for b in a.data.bones:
        print(f"     {b.name:18s} deform={b.use_deform}  parent={b.parent.name if b.parent else '-'}  "
              f"head={tuple(round(v,2) for v in b.head_local)} tail={tuple(round(v,2) for v in b.tail_local)}")
    print("   actions on it:", a.animation_data.action.name if a.animation_data and a.animation_data.action else None)

for m in meshes:
    print(f"\n-- Mesh '{m.name}'")
    print("   parent:", m.parent.name if m.parent else None, "| parent_type:", m.parent_type, "| parent_bone:", m.parent_bone or "-")
    print("   loc", tuple(round(v, 3) for v in m.location), "rot", tuple(round(math.degrees(v), 1) for v in m.rotation_euler),
          "scale", tuple(round(v, 3) for v in m.scale))
    print("   modifiers:")
    for md in m.modifiers:
        extra = ""
        if md.type == 'ARMATURE':
            extra = f" object={md.object.name if md.object else None} vertex_groups={md.use_vertex_groups} envelopes={md.use_bone_envelopes} viewport={md.show_viewport} render={md.show_render}"
        print(f"     {md.name} [{md.type}]{extra}")
    if not any(md.type == 'ARMATURE' for md in m.modifiers):
        print("   !! NO ARMATURE MODIFIER")
    # Vertex groups vs bones, and how many vertices each group actually weights.
    counts = {g.index: 0 for g in m.vertex_groups}
    for v in m.data.vertices:
        for g in v.groups:
            if g.weight > 0.001:
                counts[g.group] = counts.get(g.group, 0) + 1
    bone_names = set(b.name for a in arms for b in a.data.bones)
    print("   vertex groups (name: weighted verts, matches a bone?):")
    for g in m.vertex_groups:
        print(f"     {g.name:18s} {counts.get(g.index, 0):6d}  {'bone' if g.name in bone_names else '!! NO SUCH BONE'}")
    unweighted = sum(1 for v in m.data.vertices if not any(gg.weight > 0.001 for gg in v.groups))
    print("   vertices with no weight at all:", unweighted)

# Test: bend a spine bone and see whether the evaluated mesh moves.
if arms and meshes:
    a = arms[0]
    m = next((mm for mm in meshes if any(md.type == 'ARMATURE' for md in mm.modifiers)), meshes[0])
    dg = bpy.context.evaluated_depsgraph_get()
    before = [v.co.copy() for v in m.evaluated_get(dg).to_mesh().vertices]
    m.evaluated_get(dg).to_mesh_clear()
    for name in ("Tail", "Spine3", "Spine2"):
        pb = a.pose.bones.get(name)
        if pb:
            pb.rotation_mode = 'XYZ'
            pb.rotation_euler = (0, 0, math.radians(30))
            print(f"\nTest: rotated pose bone '{name}' 30 deg around Z")
            break
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = m.evaluated_get(dg)
    after = [v.co.copy() for v in ev.to_mesh().vertices]
    ev.to_mesh_clear()
    moved = sum(1 for p, q in zip(before, after) if (p - q).length > 0.001)
    print(f"Test result: {moved} of {len(before)} vertices moved")
print("===== END =====\n")
