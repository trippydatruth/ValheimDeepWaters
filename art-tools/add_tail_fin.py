# Adds a rounded tail fin to a fish whose model has none (the burbot scan tapers to a point): a fan in the tail stalk's
# own vertical plane (following the stalk where the scan's pose curves it), widest straight back, narrowing to low
# ridges that run forward along the top and bottom (a burbot's tail runs on into its long dorsal and anal fins). One
# surface (add_backfaces.py gives it a back later), a slightly scalloped edge for the fin rays. Its UVs lay the whole fin
# over one small patch of the tail's skin (round the UV of the skin at the stalk's root, VDW_FIN_UV_SPAN wide - the
# nearest-skin UV per point smeared the paint into bands), so it bakes in the tail's own marbling. Run on the prep
# file, before rig_fish.py (the mesh along Y, head toward -Y, top +Z).
#   blender -b <fish>_prep.blend --factory-startup --python add_tail_fin.py
#   env: VDW_SAVE_TO (a new .blend), VDW_FIN_CENTRE (y of the fan's centre, m; default 0.89 of the half-length back),
#        VDW_FIN_LENGTH (radius straight back, m; default 0.095 x the fish's length), VDW_FIN_SWEEP (degrees each way
#        from straight back; default 165), VDW_FIN_UV_SPAN (UV width the fin covers; default 0.035),
#        VDW_FIN_HEIGHT (the oval's half-height, m; default 0.45 x its length)
import bpy, bmesh, math, os
import numpy as np

SAVE = os.environ["VDW_SAVE_TO"]
if os.path.exists(SAVE): raise SystemExit("exists, kept: " + SAVE)
o = next(ob for ob in bpy.data.objects if ob.type == 'MESH')
if o.mode != 'OBJECT':
    bpy.context.view_layer.objects.active = o; bpy.ops.object.mode_set(mode='OBJECT')
M = o.matrix_world; Mi = M.inverted()
co = np.array([(M @ v.co)[:] for v in o.data.vertices])
y0, y1 = co[:, 1].min(), co[:, 1].max(); L = y1 - y0
yc = float(os.environ.get("VDW_FIN_CENTRE", y1 - 0.055 * L))
R0 = float(os.environ.get("VDW_FIN_LENGTH", 0.095 * L))
SWEEP = math.radians(float(os.environ.get("VDW_FIN_SWEEP", 165)))

# the stalk's centre line (x, z) along y, from slices of the tail
ys, xs, zs = [], [], []
for y in np.linspace(yc - 0.12 * L, y1, 14):
    s = co[np.abs(co[:, 1] - y) < 0.008 * L]
    if len(s) >= 3:
        ys.append(y); xs.append((s[:, 0].min() + s[:, 0].max()) / 2); zs.append((s[:, 2].min() + s[:, 2].max()) / 2)
ys, xs, zs = map(np.array, (ys, xs, zs))
def centre(y): return float(np.interp(y, ys, xs)), float(np.interp(y, ys, zs))
cx, cz = centre(yc)
print(f"ADD TAIL FIN on {o.name}: length {L:.3f} m, fan centre y {yc:.3f} (x {cx:.3f}, z {cz:.3f}), radius {R0:.3f}")

# skin to take the paint from: the tail's outer surface on the +X side
uv_layer = o.data.uv_layers.active.data
skin_uv = {}
for poly in o.data.polygons:
    for li in poly.loop_indices:
        skin_uv.setdefault(o.data.loops[li].vertex_index, uv_layer[li].uv[:])
# the patch: the +X skin at the stalk's root, mid-height
ry = yc - 0.12 * L; rx, rz = centre(ry)
side = [i for i in range(len(co)) if abs(co[i, 1] - ry) < 0.01 * L and co[i, 0] > rx]
j = min(side, key=lambda i: abs(co[i, 2] - rz))
uv0 = skin_uv[j]; SPAN = float(os.environ.get("VDW_FIN_UV_SPAN", 0.035)); S = SPAN / (2 * R0)
print(f"  paint patch: UV {uv0[0]:.3f}, {uv0[1]:.3f} (skin at y {co[j, 1]:.3f}), {SPAN} wide")

HT = float(os.environ.get("VDW_FIN_HEIGHT", 0.45 * R0))
def radius(th):
    # an oval paddle, R0 long and HT high: centred a little forward of the tip, so its front narrows over the stalk into
    # low ridges along the top and bottom (the round fan read as a lollipop on the tip)
    r = R0 * HT / math.sqrt((HT * math.cos(th)) ** 2 + (R0 * math.sin(th)) ** 2)
    return r * (1 + 0.03 * math.sin(th * 18))             # a slightly scalloped edge (the fin rays)

bm = bmesh.new(); bm.from_mesh(o.data)
uvl = bm.loops.layers.uv.active
mi = 0
NA, rings = 41, (0.35, 0.62, 0.84, 1.0)
centre_v = bm.verts.new(Mi @ __import__("mathutils").Vector((cx, yc, cz)))
grid = []
for k in range(NA):
    th = -SWEEP + 2 * SWEEP * k / (NA - 1)
    col = []
    for f in rings:
        r = radius(th) * f
        y = yc + r * math.cos(th); z = cz + r * math.sin(th)
        x, _ = centre(min(y, ys.max()))
        col.append(bm.verts.new(Mi @ __import__("mathutils").Vector((x, y, z))))
    grid.append(col)
bm.verts.ensure_lookup_table()
new_faces = []
for k in range(NA - 1):
    a, b = grid[k], grid[k + 1]
    new_faces.append(bm.faces.new((centre_v, a[0], b[0])))
    for j in range(len(rings) - 1):
        new_faces.append(bm.faces.new((a[j], a[j + 1], b[j + 1], b[j])))
# all facing +X (the side the paint is taken from); add_backfaces.py adds the other side
for f in new_faces:
    f.material_index = mi
    f.normal_update()
    if (M.to_3x3() @ f.normal).x < 0: f.normal_flip()
    for l in f.loops:
        w = M @ l.vert.co
        l[uvl].uv = (uv0[0] + (w.y - yc) * S, uv0[1] + (w.z - cz) * S)
    f.smooth = True
bm.to_mesh(o.data); bm.free(); o.data.update()
print(f"  added {len(new_faces)} faces ({NA} spokes x {len(rings)} rings); new length {max(y1, yc + R0) - y0:.3f} m")
bpy.ops.wm.save_as_mainfile(filepath=SAVE)
print("  saved", SAVE)
