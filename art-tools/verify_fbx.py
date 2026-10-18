# Re-imports the FBX into an empty scene and reports what Unity will get.
import bpy, os
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=os.environ["VDW_FBX_OUT"], automatic_bone_orientation=False)
print("\n===== FBX CHECK =====")
for o in bpy.data.objects:
    print(f"  {o.type:9s} {o.name:22s} loc {tuple(round(v,3) for v in o.location)} rot {tuple(round(v,3) for v in o.rotation_euler)} scale {tuple(round(v,3) for v in o.scale)} dims {tuple(round(v,2) for v in o.dimensions)}")
arm = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
if arm:
    names = [b.name for b in arm.data.bones]
    print(f"  bones ({len(names)}):", ", ".join(names))
    print("  leaf/end bones present:", any(n.endswith("_end") for n in names))
mesh = next((o for o in bpy.data.objects if o.type == 'MESH'), None)
if mesh:
    print("  vertex groups:", len(mesh.vertex_groups), "| materials:", [m.name for m in mesh.data.materials],
          "| textures:", [i.name for i in bpy.data.images])
print("  clips:", [(a.name, tuple(int(x) for x in a.frame_range)) for a in bpy.data.actions])
print("===== END =====")
# Rest-pose world size and facing: head should be toward -Y in Blender (= +Z forward in Unity).
if arm and mesh:
    arm.data.pose_position = 'REST'
    bpy.context.view_layer.update()
    from mathutils import Vector
    dg = bpy.context.evaluated_depsgraph_get(); ev = mesh.evaluated_get(dg)
    pts = [mesh.matrix_world @ v.co for v in ev.to_mesh().vertices]; ev.to_mesh_clear()
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    print("  rest-pose world size (x, y, z):", tuple(round(v, 2) for v in (hi - lo)))
    head = arm.matrix_world @ arm.data.bones["Head"].head_local
    tail = arm.matrix_world @ arm.data.bones["Spine2"].head_local
    print("  Head bone at", tuple(round(v, 2) for v in head), "| Spine2 at", tuple(round(v, 2) for v in tail),
          "->", "head toward -Y (correct)" if head.y < tail.y else "head toward +Y (WRONG)")
