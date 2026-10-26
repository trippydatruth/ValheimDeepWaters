# Raises the coat skirt's inner top corners (where the front opening meets the top edge) so they reach up under the
# painted lapel edge, easing the next points down the opening edge less, and keeps them just off the skin.
#   blender -b <tucked>.blend --python raise_skirt_corners.py
#   env: VDW_SAVE_TO (new .blend), VDW_CORNER_UP (cm the corners rise, default 7), VDW_CORNER_REACH (cm down the
#        opening edge the rise fades over, default 12), VDW_CORNER_GAP (cm off the skin, default 0.3)
import bpy, bmesh, os
from mathutils import Vector
from mathutils.bvhtree import BVHTree

SAVE = os.environ["VDW_SAVE_TO"]
if os.path.exists(SAVE): raise SystemExit("exists, kept: " + SAVE)
UP = float(os.environ.get("VDW_CORNER_UP", "7")) / 100
REACH = float(os.environ.get("VDW_CORNER_REACH", "12")) / 100
GAP = float(os.environ.get("VDW_CORNER_GAP", "0.3")) / 100
coat = bpy.data.objects["coat"]; fit = bpy.data.objects["fitref"]; M = coat.matrix_world; Mi = M.inverted()
fb = bmesh.new(); fb.from_mesh(fit.data); fb.transform(fit.matrix_world); ft = BVHTree.FromBMesh(fb)
b = bmesh.new(); b.from_mesh(coat.data)
P = {v: M @ v.co for v in b.verts}
skirt_top = max(p.z for v, p in P.items() if p.z < 1.5)
front = [v for v in b.verts if any(e.is_boundary for e in v.link_edges) and P[v].y < -0.05 and P[v].z < 1.5]
moved = []
for side in (1, -1):
    edge = [v for v in front if P[v].x * side > 0]
    corner = min((v for v in edge if P[v].z > skirt_top - 0.03), key=lambda v: abs(P[v].x), default=None)
    if corner is None: continue
    cz = P[corner].z
    for v in edge:
        # the opening edge: points below the corner, near it in x (not the top edge running out to the side)
        if v is not corner and (P[v].z > cz - 0.005 or abs(P[v].x) > abs(P[corner].x) + 0.06): continue
        f = 1.0 if v is corner else max(0.0, 1 - (cz - P[v].z) / REACH)
        if f <= 0: continue
        q = P[v] + Vector((0, 0, UP * f))
        loc, n, _i, d = ft.find_nearest(q)
        if loc is not None: q = loc + n * GAP
        v.co = Mi @ q; moved.append((v.index, round(P[v].z, 3), round(q.z, 3)))
# the collar (VDW_COLLAR_MIN, cm): every point of it at least this far off the skin (it sank into the neck as the
# head turned)
CMIN = float(os.environ.get("VDW_COLLAR_MIN", "0")) / 100
pushed = 0
if CMIN > 0:
    shoulder = min((bpy.data.objects["Armature"].matrix_world @ bpy.data.objects["Armature"].data.bones[s + "Arm"].head_local).z for s in ("Left", "Right"))
    for v in b.verts:
        p = M @ v.co
        if p.z < shoulder - 0.12: continue
        loc, n, _i, d = ft.find_nearest(p)
        if loc is None or d >= CMIN: continue
        out = (p - loc).normalized() if d > 1e-5 else n
        if out.dot(n) < 0: out = n
        v.co = Mi @ (loc + out * CMIN); pushed += 1
    print(f"COLLAR {pushed} points pushed out to {CMIN*100:.1f} cm off the skin")
b.to_mesh(coat.data); b.free(); coat.data.update()
print(f"CORNERS raised {len(moved)} points (index, z before, z after): {moved}")
bpy.ops.wm.save_as_mainfile(filepath=SAVE, copy=True)
print("SAVED", SAVE)
