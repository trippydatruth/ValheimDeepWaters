# Fixes stretching between the legs on painted gear weights: points near the middle, between the thighs, are blended
# toward an even share of the hips and both thighs (the further from the middle, the less), then smoothed there.
# Measures the stretch in a walking stride before and after. Writes a new .blend.
#   blender -b rig.blend --python fix_crotch_weights.py      env: VDW_SAVE_TO
import bpy, math, os
import numpy as np
from mathutils import Vector, Quaternion
SAVE_TO = os.environ["VDW_SAVE_TO"]
arm = bpy.data.objects["Armature"]
hip = arm.matrix_world @ arm.data.bones["Hips"].head_local
REGIONS = {   # piece: (half-width of the middle zone cm, top z, bottom z, hips share at the middle)
    "overalls": (7.0, hip.z + 2, hip.z - 30, 0.5),
    "coat":     (14.0, hip.z - 4, 0.0, 0.4),
}
def stride(on):
    pb = arm.pose.bones
    for b in pb: b.rotation_mode = 'QUATERNION'; b.rotation_quaternion = Quaternion()
    if on:
        for name, deg in (("LeftUpLeg", -40), ("RightUpLeg", 30), ("LeftLeg", 35), ("RightLeg", 25)):
            b = pb[name]; m = (arm.matrix_world @ b.bone.matrix_local).to_3x3().inverted() @ Vector((1, 0, 0))
            b.rotation_quaternion = Quaternion(m.normalized(), math.radians(deg))
    bpy.context.view_layer.update()
def lengths(ob):
    dg = bpy.context.evaluated_depsgraph_get(); me = ob.evaluated_get(dg).to_mesh()
    co = np.array([(ob.matrix_world @ v.co)[:] for v in me.vertices]); e = np.array([ed.vertices[:] for ed in me.edges])
    ob.evaluated_get(dg).to_mesh_clear(); return np.linalg.norm(co[e[:, 0]] - co[e[:, 1]], axis=1)
def report(tag):
    stride(False); r = {n: lengths(bpy.data.objects[n]) for n in REGIONS}
    stride(True)
    for n in REGIONS:
        st = lengths(bpy.data.objects[n]) / np.maximum(r[n], 1e-6)
        print(f"  {tag} {n}: edges stretched >1.6x: {(st > 1.6).sum()}, >2x: {(st > 2).sum()}, max {st.max():.1f}x")
    stride(False)
report("before")
for name, (half, top, bot, hshare) in REGIONS.items():
    ob = bpy.data.objects[name]
    vg = {g.name: g for g in ob.vertex_groups}
    for bn in ("Hips", "LeftUpLeg", "RightUpLeg"):
        if bn not in vg: vg[bn] = ob.vertex_groups.new(name=bn)
    sel = []
    for v in ob.data.vertices:
        p = ob.matrix_world @ v.co
        if not (bot <= p.z <= top) or abs(p.x) > half: continue
        # full blend at the middle, none at the zone's edge; and easing in below the top
        k = (1 - abs(p.x) / half) ** 1.5 * min(1.0, (top - p.z) / 4.0)
        if k <= 0.01: continue
        cur = {ob.vertex_groups[g.group].name: g.weight for g in v.groups}
        tot = sum(cur.values()) or 1.0
        target = {"Hips": hshare, "LeftUpLeg": (1 - hshare) / 2, "RightUpLeg": (1 - hshare) / 2}
        new = {b: w / tot * (1 - k) for b, w in cur.items()}
        for b, w in target.items(): new[b] = new.get(b, 0.0) + w * k
        for b, w in new.items(): vg[b].add([v.index], w, 'REPLACE')
        sel.append(v.index)
    # smooth the weights across the zone (and a ring round it) so there's no seam at its edge
    for o in bpy.data.objects: o.select_set(o == ob)
    bpy.context.view_layer.objects.active = ob
    for v in ob.data.vertices: v.select = v.index in set(sel)
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_more(); bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
    ob.data.use_paint_mask_vertex = True
    bpy.ops.object.vertex_group_smooth(group_select_mode='ALL', factor=0.5, repeat=4)
    bpy.ops.object.vertex_group_normalize_all(group_select_mode='ALL', lock_active=False)
    ob.data.use_paint_mask_vertex = False
    bpy.ops.object.mode_set(mode='OBJECT')
    print(f"  {name}: blended {len(sel)} points between the legs")
report("after")
bpy.ops.wm.save_as_mainfile(filepath=SAVE_TO, copy=True); print("  saved", SAVE_TO)
