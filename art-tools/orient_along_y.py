# Lays a gently curved creature along Y without straightening it: chord (end A -> end B of the centre line) becomes
# +Y with end A (the head) at -Y, the body's flattest side down, scaled to VDW_LENGTH along Y, centred, resting at z 0.
import bpy, os
import numpy as np
from mathutils import Matrix, Vector
L = np.load(os.environ["VDW_LINE"]); LEN = float(os.environ["VDW_LENGTH"])
m = next(o for o in bpy.data.objects if o.type == 'MESH'); co = np.array([v.co[:] for v in m.data.vertices])
y = L[-1] - L[0]; y /= np.linalg.norm(y)
rest = co - co.mean(0); rest -= np.outer(rest @ y, y)
_, _, vt = np.linalg.svd(rest, full_matrices=False); z = vt[1]          # thinnest direction across the body = up
z -= (z @ y) * y; z /= np.linalg.norm(z); x = np.cross(y, z)
R = np.stack([x, y, z]); c = (co @ R.T)
lo, hi = c.min(0), c.max(0); s = LEN / (hi[1] - lo[1])
c = (c - [(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]]) * s
for i, v in enumerate(m.data.vertices): v.co = c[i]
m.data.update(); print("ORIENT size", ((c.max(0) - c.min(0)) * 100).round(2), "cm")
bpy.ops.wm.save_as_mainfile(filepath=os.environ["OUT"])
