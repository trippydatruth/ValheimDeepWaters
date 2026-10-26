# Blends the coat skirt's top into the painted coat: points near the skirt's top edge are pulled in to just off the
# skin, easing back to the skirt's own shape further down, so the skirt grows out of the paint instead of standing
# off the body with a ledge at the waist.
#   blender -b <prepped>.blend --python tuck_skirt_top.py
#   env: VDW_SAVE_TO (new .blend), VDW_TUCK_GAP (cm off the skin at the top, default 0.3),
#        VDW_TUCK_FADE (cm down over which it eases back, default 14)
import bpy, bmesh, os
from mathutils.bvhtree import BVHTree

SAVE = os.environ["VDW_SAVE_TO"]
if os.path.exists(SAVE): raise SystemExit("exists, kept: " + SAVE)
GAP = float(os.environ.get("VDW_TUCK_GAP", "0.3")) / 100
FADE = float(os.environ.get("VDW_TUCK_FADE", "14")) / 100
arm = bpy.data.objects["Armature"]; coat = bpy.data.objects["coat"]; fit = bpy.data.objects["fitref"]
M = coat.matrix_world; Mi = M.inverted()
hips = (arm.matrix_world @ arm.data.bones["Hips"].head_local).z
shoulder = min((arm.matrix_world @ arm.data.bones[b].head_local).z for b in ("LeftArm", "RightArm"))
fb = bmesh.new(); fb.from_mesh(fit.data); fb.transform(fit.matrix_world); ft = BVHTree.FromBMesh(fb)

def smooth(t): t = min(1.0, max(0.0, t)); return t * t * (3 - 2 * t)
b = bmesh.new(); b.from_mesh(coat.data)
skirt = [v for v in b.verts if (M @ v.co).z < shoulder - 0.15]            # the collar is left alone
top = max((M @ v.co).z for v in skirt)
moved = 0
for v in skirt:
    p = M @ v.co
    f = 1 - smooth((top - p.z) / FADE)                                     # 1 at the top edge, 0 FADE below it
    if f <= 0.001: continue
    loc, n, _i, d = ft.find_nearest(p)
    if loc is None: continue
    out = (p - loc).normalized() if d > 1e-5 else n
    if out.dot(n) < 0: out = n
    target = loc + out * GAP
    if (p - loc).length <= GAP: continue                                   # already that close
    v.co = Mi @ (p.lerp(target, f)); moved += 1
b.to_mesh(coat.data); b.free(); coat.data.update()
print(f"TUCK skirt top at {top:.3f} m (hips {hips:.3f}): {moved} points eased in to {GAP*100:.1f} cm off the skin over {FADE*100:.0f} cm")
bpy.ops.wm.save_as_mainfile(filepath=SAVE, copy=True)
print("SAVED", SAVE)
