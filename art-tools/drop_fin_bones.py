# Hands the weights of chosen fin bones back to the body: every vertex weighted to a bone whose name contains one of
# VDW_DROP_FINS (comma list, e.g. "Pelvic") gives that weight to the nearest Spine/Head bone instead, then the empty
# groups are removed. For fish where rig_fish took part of the body for a fin (long thin bodies like the oarfish).
# The bones stay (the clips key them) but no longer move anything.
#   blender -b fish.blend --python drop_fin_bones.py      env: VDW_DROP_FINS, VDW_SAVE_TO
import bpy, os
import numpy as np
DROP = [s for s in os.environ["VDW_DROP_FINS"].split(",") if s]
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
mesh = next(o for o in bpy.data.objects if o.type == 'MESH' and o.parent == arm)
body = {b.name: (np.array(b.head_local[:]), np.array(b.tail_local[:])) for b in arm.data.bones
        if b.use_deform and (b.name == "Head" or b.name.startswith("Spine"))}
def seg(pt, a, b):
    ab = b - a; t = np.clip(np.dot(pt - a, ab) / max(np.dot(ab, ab), 1e-9), 0, 1); return float(np.linalg.norm(a + ab * t - pt))
gone = [g for g in mesh.vertex_groups if any(k in g.name for k in DROP)]
gi = {g.index for g in gone}; moved = 0
for v in mesh.data.vertices:
    w = sum(g.weight for g in v.groups if g.group in gi)
    if w <= 0: continue
    pt = np.array(v.co[:]); near = min(body, key=lambda n: seg(pt, *body[n]))
    cur = next((g.weight for g in v.groups if mesh.vertex_groups[g.group].name == near), 0.0)
    mesh.vertex_groups[near].add([v.index], cur + w, 'REPLACE'); moved += 1
for g in gone: mesh.vertex_groups.remove(g)
print(f"  {moved} vertices handed from {[g for g in DROP]} fin bones to the body")
bpy.ops.wm.save_as_mainfile(filepath=os.environ["VDW_SAVE_TO"]); print("  saved", os.environ["VDW_SAVE_TO"])
