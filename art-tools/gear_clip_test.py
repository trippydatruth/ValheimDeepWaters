# Measures how much worn gear clips in Valheim's own poses (valheim_pose.py + VdwPoseSampler.cs JSON): for every
# sampled frame of every clip,
#   - body points that come out through a cloth piece (the body under the cloth at rest; posed, the cloth crosses the line
#     from the point's own bone out to it, by more than 5 mm), counted and summed by depth
#   - for a belt: cloth points just under it that come out past it (the coat showing past the belt)
# Import and call: gear_clip_test.score(poses, cloth, body, belt=None) -> dict
import bpy, numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

def _world(o):
    dg = bpy.context.evaluated_depsgraph_get(); e = o.evaluated_get(dg); me = e.to_mesh()
    vs = [e.matrix_world @ v.co for v in me.vertices]; polys = [tuple(p.vertices) for p in me.polygons]
    e.to_mesh_clear(); return vs, polys

def covered(cloth, body, reach=0.12):
    """body points under the cloth at rest: within reach of it and on its inner side"""
    cv, cp = _world(cloth); bv, _ = _world(body); t = BVHTree.FromPolygons(cv, cp)
    out = []
    for i, p in enumerate(bv):
        loc, n, idx, d = t.find_nearest(p)
        if loc is not None and d < reach and (p - loc).dot(n) < 0: out.append(i)
    return out

def _core(body, i, arm):
    """the bone a body point mostly follows, and so the line from that bone out to the point (posed)"""
    v = body.data.vertices[i]
    g = max(v.groups, key=lambda g: g.weight, default=None)
    if g is None or arm is None: return None
    pb = arm.pose.bones.get(body.vertex_groups[g.group].name)
    return None if pb is None else (arm.matrix_world @ pb.head, arm.matrix_world @ pb.tail)

def frame_score(cloth, body, cov, belt=None, belt_band=None):
    cv, cp = _world(cloth); bv, _ = _world(body); t = BVHTree.FromPolygons(cv, cp)
    arm = next((m.object for m in body.modifiers if m.type == 'ARMATURE'), None)
    n = 0; depth = 0.0
    for i in cov:
        # through the cloth = the cloth crosses the line from the point's own bone out to it (a thigh that has simply
        # come out from under the hem, past the cloth's edge, isn't clipping)
        seg = _core(body, i, arm); p = bv[i]
        if seg is None: continue
        a, b = seg; ab = b - a; t_ = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-9))); c = a + ab * t_
        d = p - c; L = d.length
        if L < 1e-4: continue
        hit, nrm, idx, dist = t.ray_cast(c, d.normalized(), L)
        if hit is not None and L - dist > 0.005: n += 1; depth += L - dist
    bn = 0; bdepth = 0.0
    if belt is not None:
        bvv, bp = _world(belt); bt = BVHTree.FromPolygons(bvv, bp)
        for i in belt_band:
            loc, nrm, idx, d = bt.find_nearest(cv[i])
            if loc is None: continue
            s = (cv[i] - loc).dot(nrm)
            if s > 0.003: bn += 1; bdepth += s
    return n, depth, bn, bdepth

def score(P, cloth, body, belt=None, clips=None, verbose=False):
    P.reset(); bpy.context.view_layer.update()
    cov = covered(cloth, body)
    band = []
    if belt is not None:
        bz = [(belt.matrix_world @ v.co).z for v in belt.data.vertices]; lo, hi = min(bz) - 0.04, max(bz)
        cv, _ = _world(cloth); band = [i for i, p in enumerate(cv) if lo <= p.z <= hi]
    tot = {"through": 0, "depth_cm": 0.0, "belt": 0, "belt_cm": 0.0, "worst": {}}
    for clip in (clips or P.data["clips"].keys()):
        for f in range(P.frames(clip)):
            P.apply(clip, f)
            n, d, bn, bd = frame_score(cloth, body, cov, belt, band)
            tot["through"] += n; tot["depth_cm"] += d * 100; tot["belt"] += bn; tot["belt_cm"] += bd * 100
            w = tot["worst"].get(clip, (0, 0)); tot["worst"][clip] = (max(w[0], n), max(w[1], bn))
            if verbose: print(f"  {clip} {f}: {n} through ({d * 100:.1f} cm), belt {bn}")
    P.reset(); bpy.context.view_layer.update()
    tot["covered"] = len(cov); tot["band"] = len(band)
    return tot
