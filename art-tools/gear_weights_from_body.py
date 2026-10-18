# Gives every gear piece the body's own skin weights (fitref = the game's body with Valheim's weights): each gear point
# takes the nearest point on the body's surface and blends that triangle's three corner weights by where it lands -
# for gear modelled tight round the body. Keeps at most 4 bones a point, normalised. The hat (and anything in
# VDW_RIGID "piece=Bone,...") goes on one bone whole.
# The coat below the hips (faces with a "coat" material) is handed more and more to the hips and the two nearest of the
# skirt bones vdw_skirt0..7 the mod swings (VDW_SKIRT, the share at the back of the hem: 0.8, VDW_SKIRT_FRONT at the front: 0.35;
# 0 = off), so the hem swings and
# trails; the front panels stay mostly on the thighs so a raised knee doesn't punch through. Within 30 cm of the middle the
# coat below the hips is evened between the legs (the back seam would otherwise follow one thigh).
#   blender -b new_gear_rig.blend --python gear_weights_from_body.py      env: VDW_SAVE_TO, VDW_RIGID ("hat=Head"), VDW_SKIRT
import bpy, os
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
for _o in list(bpy.data.objects):
    if _o.mode != 'OBJECT' and _o.name in bpy.context.view_layer.objects:
        bpy.context.view_layer.objects.active = _o; bpy.ops.object.mode_set(mode='OBJECT')
SAVE_TO = os.environ["VDW_SAVE_TO"]
RIGID = dict(kv.split("=") for kv in os.environ.get("VDW_RIGID", "hat=Head").split(",") if kv)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
fit = bpy.data.objects["fitref"]; fm = fit.data; fm.calc_loop_triangles()
fw = fit.matrix_world
tris = [t.vertices[:] for t in fm.loop_triangles]
fco = [fw @ v.co for v in fm.vertices]
bvh = BVHTree.FromPolygons(fco, tris, all_triangles=True)
names = [g.name for g in fit.vertex_groups]
fwts = [{names[g.group]: g.weight for g in v.groups if g.weight > 1e-5} for v in fm.vertices]
import math
SKIRT = float(os.environ.get("VDW_SKIRT", "0.8")); NSK = 8
hip = arm.matrix_world @ arm.data.bones["Hips"].head_local
def smooth(t): t = min(1.0, max(0.0, t)); return t * t * (3 - 2 * t)
FRONT = float(os.environ.get("VDW_SKIRT_FRONT", "0.35")); MID = 0.30
def body_at(p):
    loc, _n, ti, d = bvh.find_nearest(p)
    a, b, c = (fco[i] for i in tris[ti])
    w = barycentric_transform(loc, a, b, c, (1, 0, 0), (0, 1, 0), (0, 0, 1))
    acc = {}
    for wi, vi in zip(w, tris[ti]):
        for nm, x in fwts[vi].items(): acc[nm] = acc.get(nm, 0.0) + max(wi, 0.0) * x
    return acc, d
for ob in [o for o in bpy.data.objects if o.type == 'MESH' and o != fit]:
    ob.vertex_groups.clear(); me = ob.data; mw = ob.matrix_world
    if ob.name in RIGID:
        g = ob.vertex_groups.new(name=RIGID[ob.name]); g.add([v.index for v in me.vertices], 1.0, 'REPLACE')
        print(f"  {ob.name}: all {len(me.vertices)} points on {RIGID[ob.name]}"); continue
    groups = {}; far = []; nsk = 0
    vmat = {}
    for poly in me.polygons:
        mn = (me.materials[poly.material_index].name.lower() if me.materials and me.materials[poly.material_index] else "")
        for vi in poly.vertices: vmat.setdefault(vi, "coat" if "coat" in mn else mn)
    coat_z = [(mw @ me.vertices[i].co).z for i, k in vmat.items() if k == "coat"]
    hem = min(coat_z) if coat_z else 0.0
    for v in me.vertices:
        p = mw @ v.co
        acc, d = body_at(p); far.append(d)
        mi = vmat.get(v.index)
        if mi == "coat" and p.z < hip.z + 0.05 and abs(p.x) < MID:
            # near the middle (the back seam): even between the legs, half and half at the seam, so it can't follow one thigh
            m = 0.5 * (1 - abs(p.x) / MID)
            other, _ = body_at(type(p)((-p.x, p.y, p.z)))
            t0, t1 = sum(acc.values()) or 1.0, sum(other.values()) or 1.0
            acc = {k: acc.get(k, 0.0) / t0 * (1 - m) + other.get(k, 0.0) / t1 * m for k in set(acc) | set(other)}
        if SKIRT > 0 and mi == "coat" and p.z < hip.z - 0.04:
            # the share on the swinging bones: most at the back, least at the front, where the panels hang over the thighs
            r = math.hypot(p.x - hip.x, p.y - hip.y) or 1.0
            back = 0.5 + 0.5 * (p.y - hip.y) / r                     # 1 behind (+Y), 0 in front
            s = (FRONT + (SKIRT - FRONT) * back) * smooth((hip.z - 0.04 - p.z) / max(hip.z - 0.04 - hem, 1e-3))
            tot0 = sum(acc.values()) or 1.0
            acc = {k: x / tot0 * (1 - s) for k, x in acc.items()}
            a_ = (math.atan2(p.y - hip.y, p.x - hip.x) / (2 * math.pi)) % 1.0 * NSK; b0 = int(a_) % NSK; f1 = a_ - int(a_)
            for nm, x in (("Hips", 0.35 * s), (f"vdw_skirt{b0}", 0.65 * s * (1 - f1)), (f"vdw_skirt{(b0 + 1) % NSK}", 0.65 * s * f1)):
                acc[nm] = acc.get(nm, 0.0) + x
            nsk += 1
        top = sorted(acc.items(), key=lambda kv: -kv[1])[:4]; tot = sum(x for _, x in top) or 1.0
        for nm, x in top:
            if x / tot < 1e-3: continue
            if nm not in groups: groups[nm] = ob.vertex_groups.new(name=nm)
            groups[nm].add([v.index], x / tot, 'REPLACE')
    far.sort()
    print(f"  {ob.name}: {len(me.vertices)} points from the body ({nsk} partly on the skirt), {len(groups)} bones; distance to the body: median "
          f"{far[len(far) // 2] * 100:.1f} cm, 95% within {far[int(len(far) * 0.95)] * 100:.1f} cm, farthest {far[-1] * 100:.1f} cm")
bpy.ops.wm.save_as_mainfile(filepath=SAVE_TO); print("  saved", SAVE_TO)
