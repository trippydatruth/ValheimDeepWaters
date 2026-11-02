# Builds a wooden ice chest in Blender from simple parts, the way one could really be made from wood (after the user's
# reference, 2026-11-01): four square corner posts standing a little proud as feet, plank panels between them with
# small gaps, a planked lid, iron corner brackets and lid caps with rivets, two hinges at the back, a hasp latch at the
# front, a pull handle on the front, iron side handles with wooden grips, a bottle opener and a brass drain with a chain.
# Rigged like the old cooler for the mod (Coolers.cs / LidDriver): "root" (the body) and "lid" (head on the hinge along
# the back top edge, pointing forward across the lid). 0.6 m wide, standing on the origin, the back toward +Y.
# Materials: wood, grip (the side handles' wooden grips), iron, brass. Two UV layers: "UVMap" (packed, for baking) and
# "Grain" (metres, the long way of each part along U, for the procedural wood).
#   blender -b --factory-startup --python build_wood_cooler.py
#   env: VDW_OUT (new .blend, never overwrites; a preview_*.png beside it), VDW_WIDTH (0.6)
import bpy, bmesh, math, os
from mathutils import Vector, Matrix

OUT = os.environ["VDW_OUT"]
if os.path.exists(OUT): raise SystemExit("exists, kept: " + OUT)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
S = float(os.environ.get("VDW_WIDTH", "0.6")) / 0.6           # everything below is for 0.6 m wide
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
for m in list(bpy.data.meshes): bpy.data.meshes.remove(m)

W, D = 0.60, 0.34            # width (x), depth (y)
ZB = 0.315                   # top of the body
LID0, LID1 = 0.317, 0.360    # the lid
P = 0.05                     # corner post section
BT = 0.018                   # board thickness
REC = 0.010                  # how far the panels sit back from the posts' faces
MATS = ["wood", "grip", "iron", "brass"]
parts = []                   # (bmesh, material, bone, grain axis or None, bevel)

def add(bm, mat, bone="root", bevel=0.0):
    parts.append((bm, mat, bone, bevel))

def box(c, size, mat, bone="root", bevel=0.002, rot=None):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    M = Matrix.Diagonal((*size, 1.0))
    if rot is not None: M = rot.to_4x4() @ M
    bmesh.ops.transform(bm, matrix=Matrix.Translation(Vector(c)) @ M, verts=bm.verts)
    add(bm, mat, bone, bevel)

def cyl(a, b, r, mat, bone="root", seg=12, cap=True):
    a, b = Vector(a), Vector(b); d = b - a
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=cap, segments=seg, radius1=r, radius2=r, depth=d.length)
    q = Vector((0, 0, 1)).rotation_difference(d.normalized())
    bmesh.ops.transform(bm, matrix=Matrix.Translation((a + b) / 2) @ q.to_matrix().to_4x4(), verts=bm.verts)
    add(bm, mat, bone, 0.0)

def torus(c, R, r, axis, mat, bone="root", seg=10, rseg=6):
    bm = bmesh.new(); rings = []
    for i in range(seg):
        a = 2 * math.pi * i / seg; ring = []
        for j in range(rseg):
            b = 2 * math.pi * j / rseg
            ring.append(bm.verts.new(((R + r * math.cos(b)) * math.cos(a), (R + r * math.cos(b)) * math.sin(a), r * math.sin(b))))
        rings.append(ring)
    for i in range(seg):
        for j in range(rseg):
            bm.faces.new((rings[i][j], rings[(i + 1) % seg][j], rings[(i + 1) % seg][(j + 1) % rseg], rings[i][(j + 1) % rseg]))
    q = Vector((0, 0, 1)).rotation_difference(Vector(axis).normalized())
    bmesh.ops.transform(bm, matrix=Matrix.Translation(Vector(c)) @ q.to_matrix().to_4x4(), verts=bm.verts)
    add(bm, mat, bone, 0.0)

def rivet(c, normal, bone="root"):
    n = Vector(normal).normalized(); c = Vector(c)
    cyl(c - n * 0.001, c + n * 0.003, 0.0035, "iron", bone, seg=8)

# ---------------------------------------------------------------- the body
xs, ys = (-W / 2 + P / 2, W / 2 - P / 2), (-D / 2 + P / 2, D / 2 - P / 2)
for x in xs:
    for y in ys: box((x, y, ZB / 2), (P, P, ZB), "wood", bevel=0.004)
ROWS = [(0.035, 0.078, 0.006), (0.080, 0.178, 0.0), (0.180, 0.278, 0.0), (0.280, ZB, 0.004)]   # (z0, z1, extra out)
inner_x, inner_y = W - 2 * P + 0.02, D - 2 * P + 0.02           # boards run 1 cm into the posts
for side in (-1, 1):
    for z0, z1, out in ROWS:
        # front (-y) and back (+y)
        yc = side * (D / 2 - REC - BT / 2 + out)
        box((0, yc, (z0 + z1) / 2), (inner_x, BT, z1 - z0), "wood", bevel=0.003)
        # left (-x) and right (+x)
        xc = side * (W / 2 - REC - BT / 2 + out)
        box((xc, 0, (z0 + z1) / 2), (BT, inner_y, z1 - z0), "wood", bevel=0.003)
box((0, 0, 0.0425), (W - 0.04, D - 0.04, 0.015), "wood", bevel=0.0)       # the floor

# ---------------------------------------------------------------- the lid: four planks across, with gaps
OV = 0.008; LW, LD = W + 2 * OV, D + 2 * OV; n = 4; gap = 0.003
pw = (LD - (n - 1) * gap) / n
for i in range(n):
    y0 = -LD / 2 + i * (pw + gap)
    box((0, y0 + pw / 2, (LID0 + LID1) / 2), (LW, pw, LID1 - LID0), "wood", "lid", bevel=0.004)

# ---------------------------------------------------------------- iron: lid corner caps, body corner brackets
T = 0.004; CAP = 0.065
for sx in (-1, 1):
    for sy in (-1, 1):
        cx, cy = sx * (LW / 2 - CAP / 2 + 0.001), sy * (LD / 2 - CAP / 2 + 0.001)
        zc = (LID0 + LID1) / 2; h = LID1 - LID0 + 0.004
        box((cx, sy * (LD / 2 + T / 2), zc), (CAP, T, h), "iron", "lid", 0.001)            # front/back face
        box((sx * (LW / 2 + T / 2), cy, zc), (T, CAP, h), "iron", "lid", 0.001)            # end face
        box((cx, cy, LID1 + T / 2), (CAP, CAP, T), "iron", "lid", 0.001)                   # top
        rivet((cx + sx * 0.012, sy * (LD / 2 + T), zc), (0, sy, 0), "lid")
        rivet((sx * (LW / 2 + T), cy + sy * 0.012, zc), (sx, 0, 0), "lid")
        rivet((cx + sx * 0.012, cy + sy * 0.012, LID1 + T), (0, 0, 1), "lid")
        # body brackets wrapping each post near the top and the bottom
        for z0, z1 in ((0.255, 0.290), (0.040, 0.072)):
            zc = (z0 + z1) / 2; h = z1 - z0; L = P               # on the post only
            box((sx * (W / 2 - L / 2), sy * (D / 2 + T / 2 + 0.0005), zc), (L, T, h), "iron", "root", 0.001)
            box((sx * (W / 2 + T / 2 + 0.0005), sy * (D / 2 - L / 2), zc), (T, L, h), "iron", "root", 0.001)
            rivet((sx * (W / 2 - 0.014), sy * (D / 2 + T + 0.0005), zc), (0, sy, 0))
            rivet((sx * (W / 2 - 0.036), sy * (D / 2 + T + 0.0005), zc), (0, sy, 0))
            rivet((sx * (W / 2 + T + 0.0005), sy * (D / 2 - 0.014), zc), (sx, 0, 0))
            rivet((sx * (W / 2 + T + 0.0005), sy * (D / 2 - 0.036), zc), (sx, 0, 0))

# ---------------------------------------------------------------- hinges at the back
HY = D / 2 + 0.006
for x in (-0.17, 0.17):
    box((x, LD / 2 - 0.035, LID1 + T / 2), (0.05, 0.07, T), "iron", "lid", 0.001)        # leaf on the lid's top
    box((x, LD / 2 + T / 2, LID0 + 0.012), (0.05, T, 0.03), "iron", "lid", 0.001)        # down the lid's back edge
    box((x, D / 2 - REC + 0.004 + T / 2, 0.285), (0.05, T, 0.055), "iron", "root", 0.001)   # leaf down the back rail
    cyl((x - 0.025, HY, LID0 - 0.001), (x + 0.025, HY, LID0 - 0.001), 0.006, "iron", "root")   # the knuckle
    for dx in (-0.013, 0.013):
        rivet((x + dx, LD / 2 - 0.045, LID1 + T), (0, 0, 1), "lid"); rivet((x + dx, D / 2 - REC + 0.004 + T, 0.27), (0, 1, 0))

# ---------------------------------------------------------------- the hasp latch (front, middle)
FY = -D / 2                                        # the posts' front face
box((0, -LD / 2 - T / 2, LID0 + 0.02), (0.06, T, 0.04), "iron", "lid", 0.001)           # plate on the lid's front edge
RAIL = -(D / 2 - REC + 0.004)                     # the top rail's front face (it stands 4 mm proud of the boards)
box((0, RAIL - 0.002 - T / 2, 0.283), (0.034, T, 0.07), "iron", "lid", 0.001)           # the hasp strap, flat down the rail
box((0, (-LD / 2 + RAIL - 0.002) / 2, LID0 - 0.002), (0.034, -LD / 2 - RAIL + 0.002 + T, T), "iron", "lid", 0.001)   # bent under the lid
cyl((-0.017, -LD / 2 - 0.004, LID0 + 0.006), (0.017, -LD / 2 - 0.004, LID0 + 0.006), 0.0045, "iron", "lid")   # its knuckle
box((0, -(D / 2 - REC) - T / 2, 0.235), (0.05, T, 0.03), "iron", "root", 0.001)          # staple plate on the board below
torus((0, RAIL - 0.004, 0.258), 0.009, 0.0028, (1, 0, 0), "iron")                       # the staple, through the hasp
for dx in (-0.018, 0.018): rivet((dx, -LD / 2 - T, LID0 + 0.02), (0, -1, 0), "lid")

# ---------------------------------------------------------------- the front pull handle
PY = -(D / 2 - REC)                    # front face of the front boards (they sit REC back from the posts)
box((0, PY - T / 2, 0.198), (0.17, T, 0.036), "iron", "root", 0.001)
for x in (-0.06, 0.06):
    cyl((x, PY - T, 0.205), (x, PY - 0.03, 0.205), 0.005, "iron")                        # arms out from the plate
    cyl((x, PY - 0.03, 0.205), (x, PY - 0.034, 0.163), 0.005, "iron")                    # ... and hanging down
    rivet((x + (0.025 if x > 0 else -0.025), PY - T, 0.198), (0, -1, 0))
cyl((-0.066, PY - 0.034, 0.163), (0.066, PY - 0.034, 0.163), 0.0065, "iron")             # the grip bar

# ---------------------------------------------------------------- side handles: iron brackets and a wooden grip
for sx in (-1, 1):
    SX = sx * (W / 2 - REC)            # the side boards' face
    box((SX + sx * T / 2, 0, 0.225), (T, 0.13, 0.05), "iron", "root", 0.001)
    for y in (-0.05, 0.05):
        cyl((SX + sx * T, y, 0.235), (SX + sx * 0.04, y, 0.235), 0.005, "iron")
        cyl((SX + sx * 0.04, y, 0.235), (SX + sx * 0.045, y, 0.19), 0.005, "iron")
        rivet((SX + sx * T, y * 1.15, 0.212), (sx, 0, 0))
    cyl((SX + sx * 0.045, -0.06, 0.19), (SX + sx * 0.045, 0.06, 0.19), 0.013, "grip", seg=12)

# ---------------------------------------------------------------- bottle opener (front, upper right)
bx, bz = 0.20, 0.235
box((bx, PY - T / 2, bz), (0.044, T, 0.075), "iron", "root", 0.008)                     # its plate, rounded
MY = PY - T                                                                                # the plate's face
# the mouth: two cheeks, a roof, and a tooth bent down at the front, open underneath for the cap to hook in
for sx in (-1, 1): box((bx + sx * 0.0145, MY - 0.009, bz + 0.016), (0.004, 0.018, 0.026), "iron", "root", 0.001)
box((bx, MY - 0.009, bz + 0.0305), (0.033, 0.018, 0.004), "iron", "root", 0.001)          # roof
box((bx, MY - 0.0185, bz + 0.022), (0.033, 0.004, 0.017), "iron", "root", 0.001)          # the tooth
for sx in (-1, 1): rivet((bx + sx * 0.011, MY, bz - 0.025), (0, -1, 0))

# ---------------------------------------------------------------- brass drain plug and its chain (front, low right)
dx, dz = 0.21, 0.105
cyl((dx, PY + 0.002, dz), (dx, PY - 0.012, dz), 0.012, "brass", seg=14)                   # the spout
cyl((dx, PY - 0.012, dz), (dx, PY - 0.022, dz), 0.0145, "brass", seg=14)                  # the cap
torus((dx + 0.016, PY - 0.016, dz - 0.004), 0.004, 0.0012, (0, 1, 0), "brass", seg=8, rseg=4)
for i in range(4):                                                                          # a short chain hanging off it
    torus((dx + 0.02 + i * 0.004, PY - 0.012, dz - 0.012 - i * 0.009), 0.0045, 0.0011, (1, 0, 0) if i % 2 else (0, 1, 0), "brass", seg=8, rseg=4)
box((dx + 0.034, PY - T / 2, dz - 0.05), (0.012, T, 0.012), "brass", "root", 0.001)        # where the chain's pinned

# ---------------------------------------------------------------- one object, materials, UVs, bones
me = bpy.data.meshes.new("cooler"); bm_all = bmesh.new()
mat_layer_faces = []
lid_verts = []
for bm, mat, bone, bevel in parts:
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=1, affect='EDGES', clamp_overlap=True)
    off = len(bm_all.verts)
    m2 = bpy.data.meshes.new("tmp"); bm.to_mesh(m2); bm.free()
    for p in m2.polygons: p.material_index = MATS.index(mat)
    bm_all.from_mesh(m2)
    bm_all.verts.ensure_lookup_table()
    if bone == "lid": lid_verts += list(range(off, len(bm_all.verts)))
    bpy.data.meshes.remove(m2)
bm_all.to_mesh(me); bm_all.free()
ob = bpy.data.objects.new("cooler", me); bpy.context.scene.collection.objects.link(ob)
for mname in MATS:
    m = bpy.data.materials.get(mname) or bpy.data.materials.new(mname); me.materials.append(m)
for p in me.polygons: p.use_smooth = False
# "Grain": each face projected along its normal, in metres, U along the face's longer side
grain = me.uv_layers.new(name="Grain")
for p in me.polygons:
    nrm = p.normal; ax = max(range(3), key=lambda i: abs(nrm[i])); a, b = [i for i in range(3) if i != ax]
    co = [me.vertices[me.loops[li].vertex_index].co for li in p.loop_indices]
    ea = max(c[a] for c in co) - min(c[a] for c in co); eb = max(c[b] for c in co) - min(c[b] for c in co)
    u, v = (a, b) if ea >= eb else (b, a)
    for li, c in zip(p.loop_indices, co): grain.data[li].uv = (c[u], c[v])
# "UVMap": a packed atlas for baking
atlas = me.uv_layers.new(name="UVMap"); me.uv_layers.active = atlas; atlas.active_render = True
bpy.context.view_layer.objects.active = ob; ob.select_set(True)
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.004, scale_to_bounds=False)
bpy.ops.uv.pack_islands(margin=0.004)
bpy.ops.object.mode_set(mode='OBJECT')
# scale and the rig
if S != 1.0: me.transform(Matrix.Scale(S, 4))
ad = bpy.data.armatures.new("Cooler_Rig"); rig = bpy.data.objects.new("Cooler_Rig", ad); bpy.context.scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig; bpy.ops.object.mode_set(mode='EDIT')
r = ad.edit_bones.new("root"); r.head = (0, 0, 0); r.tail = (0, 0, 0.1 * S)
l = ad.edit_bones.new("lid"); l.head = (0, HY * S, LID0 * S); l.tail = (0, -D / 2 * S, LID0 * S); l.parent = r
bpy.ops.object.mode_set(mode='OBJECT')
g_root, g_lid = ob.vertex_groups.new(name="root"), ob.vertex_groups.new(name="lid")
lid_set = set(lid_verts)
g_root.add([i for i in range(len(me.vertices)) if i not in lid_set], 1.0, 'REPLACE'); g_lid.add(sorted(lid_set), 1.0, 'REPLACE')
ob.parent = rig; md = ob.modifiers.new("Armature", 'ARMATURE'); md.object = rig
tris = sum(len(p.vertices) - 2 for p in me.polygons)
print(f"COOLER {len(me.vertices)} points, {tris} triangles, {len(parts)} parts; lid {len(lid_set)} points; {W * S:.2f} x {D * S:.2f} x {(LID1 + 0.004) * S:.3f} m")
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("SAVED", OUT)
