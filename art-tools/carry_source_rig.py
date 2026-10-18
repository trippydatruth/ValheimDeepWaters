# For downloads that come rigged and animated (e.g. DigitalLife3D's fish): keeps the download's OWN skeleton, skin
# weights and swim cycle instead of the Deep Waters rig. Run on the prep file (prep_sourced_fish.py output, which
# records its world -> fish transform as "vdw_prep_matrix"):
#   - the source armature is moved by that same transform and its transform applied (true size, head -Y, up +Z);
#     pose location keys are scaled with it
#   - the prepped (decimated, re-UV'd, baked) mesh takes its weights from the source's skinned meshes, nearest face
#     interpolated (a part the source didn't skin, like a loose eye, takes the body's weights where it sits)
#   - the swim cycle becomes "Swim" (starting at frame 0); "Thrash" (bigger and twice as fast) and "Flop" (bigger,
#     slower) are made from it by scaling each bone's turn away from rest. Every other action / NLA track is dropped.
#   blender -b <id>_prep_v1.blend --python carry_source_rig.py
#   env: VDW_SOURCE (<id>_source.blend), VDW_SAVE_TO, VDW_THRASH ("1.8,0.5" = amplitude, time), VDW_FLOP ("2.0,1.4")
import bpy, os, math
import numpy as np
from mathutils import Matrix, Quaternion
SAVE_TO = os.environ["VDW_SAVE_TO"]
if os.path.exists(SAVE_TO): raise SystemExit("refusing to overwrite " + SAVE_TO)
lo = next(o for o in bpy.data.objects if o.type == 'MESH')
TOT = Matrix([lo["vdw_prep_matrix"][r * 4:r * 4 + 4] for r in range(4)])
k = TOT.to_scale()[0]
print(f"\n===== CARRY SOURCE RIG ({lo.name}) =====\n  prep transform scale {k:.4f}")

with bpy.data.libraries.load(os.environ["VDW_SOURCE"]) as (src, dst):
    dst.objects = list(src.objects); dst.actions = list(src.actions)
sc = bpy.context.scene
for o in dst.objects:
    if o: sc.collection.objects.link(o)
bpy.context.view_layer.update()
arm = next(o for o in dst.objects if o and o.type == 'ARMATURE')
arm.data.pose_position = 'REST'; bpy.context.view_layer.update()
# ---- the source's skinned meshes, in rest pose, moved into the fish frame, joined (vertex groups merge by name)
skinned = [o for o in dst.objects if o and o.type == 'MESH' and any(m.type == 'ARMATURE' and m.object == arm for m in o.modifiers)]
parts = []
for o in skinned:
    me = o.data.copy(); me.transform(TOT @ o.matrix_world)
    ob = bpy.data.objects.new("src_" + o.name, me); sc.collection.objects.link(ob)   # the mesh keeps its group names
    parts.append(ob)
for o in bpy.context.view_layer.objects: o.select_set(o in parts)
bpy.context.view_layer.objects.active = parts[0]
if len(parts) > 1: bpy.ops.object.join()
srcm = bpy.context.view_layer.objects.active
print(f"  source skin: {len(skinned)} meshes, {len(srcm.data.vertices)} points, {len(srcm.vertex_groups)} groups")
# ---- the armature: into the fish frame, transform applied
mw = TOT @ arm.matrix_world
arm.parent = None; arm.matrix_world = mw
for o in dst.objects:                                          # the download's empties and original meshes go
    if o and o != arm and o.name in bpy.data.objects: bpy.data.objects.remove(o)
bpy.context.view_layer.update()
for o in bpy.data.objects: o.select_set(o == arm)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
arm.name = "Armature"; arm.data.name = "Armature"
# ---- weights onto the prepped mesh
lo.vertex_groups.clear()
for g in srcm.vertex_groups: lo.vertex_groups.new(name=g.name)
# nearest point on the source surface, its triangle's three weights blended by barycentric position
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
sm_ = srcm.data; sm_.calc_loop_triangles()
tris = [t.vertices[:] for t in sm_.loop_triangles]
bvh = BVHTree.FromPolygons([v.co for v in sm_.vertices], tris, all_triangles=True)
sw = [{srcm.vertex_groups[g.group].name: g.weight for g in v.groups if g.weight > 1e-5} for v in sm_.vertices]
for v in lo.data.vertices:
    loc, _n, ti, _d = bvh.find_nearest(v.co)
    if ti is None: continue
    a, b, c_ = (sm_.vertices[i].co for i in tris[ti])
    w = barycentric_transform(loc, a, b, c_, (1, 0, 0), (0, 1, 0), (0, 0, 1))
    acc = {}
    for wi, vi in zip(w, tris[ti]):
        for nm, x in sw[vi].items(): acc[nm] = acc.get(nm, 0.0) + max(wi, 0.0) * x
    for nm, x in acc.items():
        if x > 1e-4: lo.vertex_groups[nm].add([v.index], x, 'REPLACE')
for o in bpy.data.objects: o.select_set(o == lo)
bpy.context.view_layer.objects.active = lo
bpy.ops.object.vertex_group_limit_total(group_select_mode='ALL', limit=4)
bpy.ops.object.vertex_group_normalize_all(lock_active=False)
used = {lo.vertex_groups[g.group].name for v in lo.data.vertices for g in v.groups if g.weight > 1e-4}
for nm in [g.name for g in lo.vertex_groups if g.name not in used]: lo.vertex_groups.remove(lo.vertex_groups[nm])
bpy.data.objects.remove(srcm)
lo.parent = arm; lo.matrix_parent_inverse = Matrix.Identity(4)
md = lo.modifiers.new("Armature", 'ARMATURE'); md.object = arm
print(f"  {lo.name}: {len(lo.data.vertices)} points weighted to {len(lo.vertex_groups)} bones")

# ---- clips
ad = arm.animation_data or arm.animation_data_create()
swim_src = ad.action or (ad.nla_tracks[0].strips[0].action if ad.nla_tracks and ad.nla_tracks[0].strips else None) or next(iter(dst.actions))
for t in list(ad.nla_tracks): ad.nla_tracks.remove(t)
for a in list(bpy.data.actions):
    if a != swim_src: bpy.data.actions.remove(a)
swim = swim_src; swim.name = "Swim"
f0 = swim.frame_range[0]
for c in swim.fcurves:
    for kp in c.keyframe_points:
        kp.co[0] -= f0; kp.handle_left[0] -= f0; kp.handle_right[0] -= f0
        if c.data_path.endswith("location"): kp.co[1] *= k; kp.handle_left[1] *= k; kp.handle_right[1] *= k
    c.update()
def bone_of(path): return path.split('"')[1] if '"' in path else None
def derive(name, amp, tscale):
    a = swim.copy(); a.name = name
    by_bone = {}
    for c in a.fcurves:
        if c.data_path.endswith("rotation_quaternion"): by_bone.setdefault(bone_of(c.data_path), {})[c.array_index] = c
    for b, cs in by_bone.items():
        if len(cs) != 4: continue
        n = len(cs[0].keyframe_points)
        if any(len(cs[i].keyframe_points) != n for i in range(4)): continue
        for j in range(n):
            q = Quaternion([cs[i].keyframe_points[j].co[1] for i in range(4)])
            ax, ang = q.to_axis_angle()
            if ang > math.pi: ang -= 2 * math.pi
            q2 = Quaternion(ax, ang * amp)
            for i in range(4):
                kp = cs[i].keyframe_points[j]; kp.co[1] = q2[i]; kp.interpolation = 'BEZIER'
    for c in a.fcurves:
        for kp in c.keyframe_points:
            kp.co[0] *= tscale; kp.handle_left[0] *= tscale; kp.handle_right[0] *= tscale
            if c.data_path.endswith("rotation_quaternion"): kp.handle_left_type = kp.handle_right_type = 'AUTO_CLAMPED'
        c.update()
    a.use_fake_user = True
    return a
ta, tt = (float(x) for x in os.environ.get("VDW_THRASH", "1.8,0.5").split(","))
fa, ft = (float(x) for x in os.environ.get("VDW_FLOP", "2.0,1.4").split(","))
derive("Thrash", ta, tt); derive("Flop", fa, ft)
swim.use_fake_user = True; ad.action = swim
for a in bpy.data.actions: print(f"  clip {a.name}: frames {tuple(round(x, 1) for x in a.frame_range)}, {len(a.fcurves)} curves")
arm.data.pose_position = 'POSE'; arm.show_in_front = True
bpy.ops.wm.save_as_mainfile(filepath=SAVE_TO); print("  saved", SAVE_TO)
print("===== END =====")
