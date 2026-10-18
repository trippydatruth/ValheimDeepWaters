# Copies vertex weights from another .blend's fish mesh (same vertex order) onto this file's mesh.
# VDW_COPY_POSITIONS=1 also copies vertex positions (e.g. teeth moved by hand); faces must be identical.
import bpy, os
import numpy as np
SRC = os.environ["VDW_WEIGHTS_FROM"]; SAVE_TO = os.environ["VDW_SAVE_TO"]
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
mesh = next(o for o in bpy.data.objects if o.type == 'MESH' and o.parent == arm)
with bpy.data.libraries.load(SRC, link=False) as (src, dst):
    dst.objects = [n for n in src.objects]
srcmesh = next(o for o in dst.objects if o and o.type == 'MESH')
a = np.array([v.co[:] for v in mesh.data.vertices]); b = np.array([v.co[:] for v in srcmesh.data.vertices])
assert a.shape == b.shape, "different vertex count - weights can't be copied 1:1"
assert [tuple(p.vertices) for p in mesh.data.polygons] == [tuple(p.vertices) for p in srcmesh.data.polygons], "different faces"
moved = np.linalg.norm(a - b, axis=1) > 1e-5
if moved.any():
    assert os.environ.get("VDW_COPY_POSITIONS") == "1", f"{moved.sum()} vertices moved - set VDW_COPY_POSITIONS=1 to copy them too"
    for i in np.nonzero(moved)[0]: mesh.data.vertices[i].co = srcmesh.data.vertices[i].co
    mesh.data.update()
    print(f"  copied {moved.sum()} moved vertex positions (vertex {np.nonzero(moved)[0].min()}..{np.nonzero(moved)[0].max()})")
names = [g.name for g in srcmesh.vertex_groups]
for g in list(mesh.vertex_groups): mesh.vertex_groups.remove(g)
for n in names: mesh.vertex_groups.new(name=n)
for v in srcmesh.data.vertices:
    for g in v.groups:
        mesh.vertex_groups[names[g.group]].add([v.index], g.weight, 'REPLACE')
cnt = {g.name: 0 for g in mesh.vertex_groups}
for v in mesh.data.vertices:
    for g in v.groups:
        if g.weight > 0.05: cnt[mesh.vertex_groups[g.group].name] += 1
print("  copied weights:", cnt)
for o in dst.objects:      # drop the temporary copies
    if o: bpy.data.objects.remove(o)
for m in list(bpy.data.meshes):
    if m.users == 0: bpy.data.meshes.remove(m)
for a_ in list(bpy.data.armatures):
    if a_.users == 0: bpy.data.armatures.remove(a_)
for ac in list(bpy.data.actions):
    if ac.name not in ("Swim", "Thrash", "Flop"): bpy.data.actions.remove(ac)
print("  actions:", [x.name for x in bpy.data.actions])
bpy.ops.wm.save_as_mainfile(filepath=SAVE_TO)
print("  saved", SAVE_TO)

