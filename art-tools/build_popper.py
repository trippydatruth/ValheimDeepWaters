# Builds the Sparkler Popper (bait lure_sparkler) as one mesh object "bait" with material slots for bake_wood_cooler.py
# and export_wood_cooler.py (VDW_KIND=lure): a carved finewood popper body (painted cream, a red head with a cupped
# face), glass eyes, a line tie, a belly and a tail hook on split rings, a feather tail, and one of Hildir's sparklers
# bound along its back with linen wraps, its tip glowing. Laid out like the other bait: along Y, the head (where the
# line ties on) toward -Y, up +Z, about 9 cm (the importer doubles bait in game).
#   Slots: wood, cream, red, eye, metal, thread, feather, spark, glow.
#   blender -b --factory-startup --python build_popper.py      env: VDW_OUT (new .blend)
import bpy, bmesh, os, math
from mathutils import Vector, Matrix

OUT = os.environ["VDW_OUT"]
if os.path.exists(OUT): raise SystemExit("exists, kept: " + OUT)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
parts = []

def add(bm, mat): parts.append((bm, mat))

def lathe(profile, mat, seg=24):
    """a solid of revolution round the Y axis from (radius, y) points; ends closed when the radius is 0"""
    bm = bmesh.new(); rings = []
    for r, y in profile:
        if r <= 1e-6: rings.append([bm.verts.new((0, y, 0))]); continue
        rings.append([bm.verts.new((r * math.cos(2 * math.pi * k / seg), y, r * math.sin(2 * math.pi * k / seg))) for k in range(seg)])
    for a, b in zip(rings, rings[1:]):
        if len(a) == 1 and len(b) == 1: continue
        for k in range(seg):
            if len(a) == 1: bm.faces.new((a[0], b[(k + 1) % seg], b[k]))
            elif len(b) == 1: bm.faces.new((a[k], a[(k + 1) % seg], b[0]))
            else: bm.faces.new((a[k], a[(k + 1) % seg], b[(k + 1) % seg], b[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    add(bm, mat)

def tube(pts, radii, mat, seg=8, caps=True):
    pts = [Vector(p) for p in pts]; bm = bmesh.new(); rings = []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        a = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0)); a = (a - t * a.dot(t)).normalized(); b = t.cross(a)
        rings.append([bm.verts.new(p + (a * math.cos(2 * math.pi * k / seg) + b * math.sin(2 * math.pi * k / seg)) * radii[i]) for k in range(seg)])
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(seg): bm.faces.new((r0[k], r0[(k + 1) % seg], r1[(k + 1) % seg], r1[k]))
    if caps:
        for rg in (rings[0], rings[-1]): bm.faces.new(rg)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    add(bm, mat)

def sphere(c, r, mat, scale=(1, 1, 1), useg=12, vseg=8):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=useg, v_segments=vseg, radius=r)
    bmesh.ops.transform(bm, matrix=Matrix.Translation(Vector(c)) @ Matrix.Diagonal((*scale, 1)), verts=bm.verts)
    add(bm, mat)

def ring(c, axis, R, r, mat, seg=16):
    c = Vector(c); ax = Vector(axis).normalized()
    a = Vector((0, 0, 1)) if abs(ax.z) < 0.9 else Vector((1, 0, 0)); a = (a - ax * a.dot(ax)).normalized(); b = ax.cross(a)
    pts = [c + (a * math.cos(2 * math.pi * k / seg) + b * math.sin(2 * math.pi * k / seg)) * R for k in range(seg + 1)]
    tube(pts, [r] * len(pts), mat, seg=6, caps=False)

def hook(eye, length, gape, mat, r=0.0011):
    """a J hook hanging down (-Z) from its eye, the point curling back up toward +Y, with a barb"""
    eye = Vector(eye); pts = [eye + Vector((0, 0, -length * 0.7 * i / 5)) for i in range(6)]
    c = eye + Vector((0, gape / 2, -length * 0.7))
    for i in range(1, 9):
        a = math.pi + math.pi * i / 8
        pts.append(c + Vector((0, math.cos(a) * gape / 2, math.sin(a) * gape / 2)))
    pts.append(pts[-1] + Vector((0, 0, length * 0.3)))
    tube(pts, [r] * len(pts), mat, seg=6)
    tip = pts[-1]; tube([tip, tip + Vector((0, -0.0035, -0.004))], [r * 1.1, r * 0.15], mat, seg=5)   # barb
    ring(eye + Vector((0, 0, 0.0025)), (1, 0, 0), 0.0025, 0.0006, mat)                                 # its eye

# ---------------------------------------------------------------- the body: a cupped face, a fat head, tapering back
def body_r(y):   # radius along the body, from the face (-0.032) to the tail (0.030)
    t = min(1.0, max(0.0, (y + 0.032) / 0.062))
    return 0.0088 * (1 - 0.62 * t ** 1.6) * (0.93 + 0.07 * math.sin(math.pi * min(1, t * 2.2)))
ys = [-0.0325 + 0.0625 * i / 20 for i in range(21)]
HEAD = 9                                                # the first rings are the red head
lathe([(0.0, -0.0275), (0.0045, -0.029), (0.0068, -0.0315), (body_r(-0.0325) * 0.98, -0.0325)] + [(body_r(y), y) for y in ys[1:HEAD + 1]], "red", seg=28)
lathe([(body_r(y), y) for y in ys[HEAD:]] + [(0.0, 0.031)], "cream", seg=28)
ring((0, -0.0325, 0), (0, 1, 0), body_r(-0.0325) * 0.98, 0.0007, "wood", seg=28)                       # the face's lip, worn bare
for s in (-1, 1):                                                                                       # glass eyes
    y = -0.0245; r0 = body_r(y)
    sphere((s * r0 * 0.82, y, r0 * 0.48), 0.0024, "eye", scale=(0.7, 1, 1))
ring((0, -0.0335, -0.0045), (1, 0, 0), 0.0022, 0.0006, "metal")                                          # the line tie under the face
# ---------------------------------------------------------------- the hooks, on split rings
for y in (-0.004, 0.031):
    z = -body_r(y) - 0.0018 if y < 0.03 else 0.0
    ring((0, y, z), (1, 0, 0), 0.0022, 0.0006, "metal")
    hook((0, y, z - 0.0026), 0.017, 0.008, "metal")
# a feather tail
for k in range(9):
    a = 2 * math.pi * k / 9
    tube([(0, 0.029, 0), (0.0065 * math.cos(a), 0.052 + 0.003 * math.sin(2 * a), 0.0065 * math.sin(a) + 0.002)], [0.0013, 0.0002], "feather", seg=4)
# ---------------------------------------------------------------- the sparkler on its back, bound with linen
top = lambda y: body_r(y) + 0.0016
tube([(0, -0.019, top(-0.019)), (0, 0.022, top(0.022) + 0.0004)], [0.0017, 0.0017], "spark", seg=10)   # the coating
tube([(0, 0.022, top(0.022) + 0.0004), (0, 0.034, top(0.03) + 0.004), (0, 0.04, top(0.03) + 0.009)], [0.0005] * 3, "metal", seg=6)   # its bare wire, bent up at the tail
sphere((0, -0.0205, top(-0.019)), 0.0021, "glow", scale=(1, 1.3, 1))                                    # the lit tip
for y in (-0.011, 0.002, 0.015):                                                                        # linen wraps
    for d in (-0.0008, 0.0008):
        r0 = body_r(y + d)
        pts = [Vector((0, y + d, 0)) + Vector((math.cos(a) * (r0 + 0.0004), 0, math.sin(a) * (r0 + 0.0004))) for a in [2 * math.pi * k / 20 for k in range(21)]]
        pts = [p if p.z < r0 * 0.7 else Vector((p.x * 1.0, p.y, max(p.z, top(y) + 0.0012 * (1 - abs(p.x) / 0.004)))) for p in pts]
        tube(pts, [0.0006] * len(pts), "thread", seg=5, caps=False)

# ---------------------------------------------------------------- one object, materials, UVs
MATS = [m for m in ("wood", "cream", "red", "eye", "metal", "thread", "feather", "spark", "glow") if any(p[1] == m for p in parts)]
me = bpy.data.meshes.new("bait"); bm_all = bmesh.new()
for bm, mat in parts:
    m2 = bpy.data.meshes.new("tmp"); bm.to_mesh(m2); bm.free()
    for p in m2.polygons: p.material_index = MATS.index(mat)
    bm_all.from_mesh(m2); bpy.data.meshes.remove(m2)
bm_all.to_mesh(me); bm_all.free()
ob = bpy.data.objects.new("bait", me); bpy.context.scene.collection.objects.link(ob)
for name in MATS: me.materials.append(bpy.data.materials.new(name))
for p in me.polygons: p.use_smooth = True
# "Grain" UVs (metres): the wood grain runs along the body (Y), round it the other way
grain = me.uv_layers.new(name="Grain")
for p in me.polygons:
    for li in p.loop_indices:
        c = me.vertices[me.loops[li].vertex_index].co
        grain.data[li].uv = (c.y, math.atan2(c.z, c.x) * 0.008)
atlas = me.uv_layers.new(name="UVMap"); me.uv_layers.active = atlas; atlas.active_render = True
bpy.context.view_layer.objects.active = ob; ob.select_set(True)
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.006, scale_to_bounds=False)
bpy.ops.uv.pack_islands(margin=0.006)
bpy.ops.object.mode_set(mode='OBJECT')
co = [v.co for v in me.vertices]
print(f"POPPER: {len(me.vertices)} points, {sum(len(p.vertices) - 2 for p in me.polygons)} triangles; "
      f"{max(c.x for c in co) - min(c.x for c in co):.3f} x {max(c.y for c in co) - min(c.y for c in co):.3f} x {max(c.z for c in co) - min(c.z for c in co):.3f} m; slots {MATS}")
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("SAVED", OUT)
