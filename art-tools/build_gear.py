# Builds a reel or a line (spool) for the tackle screen's Reel and Line slots (Tackle.json), one per tier, as one mesh
# object "tackle" with material slots for bake_wood_cooler.py (VDW_KIND=gear) and export_wood_cooler.py (VDW_KIND=gear):
#   reels - a drum reel on its side (axis X): two side plates (wooden discs with a metal rim, spoked wheels, or toothed
#           dvergr plates), the wound line between them, a crank with a wooden knob, and a foot to sit on the rod.
#           Slots: plate, metal, grip, line (+ glow: the hub of the dvergr, flametal and frostcore reels).
#   lines - a wooden bobbin wound with the line, its loose end hanging off. Slots: flange, line, metal.
# The line's "Grain" UVs run round the spool, so the procedural wood the bake uses for it reads as wound fibres.
#   blender -b --factory-startup --python build_gear.py      env: VDW_GEAR (reel_bronze ... line_moose), VDW_OUT (new .blend)
import bpy, bmesh, os, math
from mathutils import Vector, Matrix

GEAR, OUT = os.environ["VDW_GEAR"], os.environ["VDW_OUT"]
if os.path.exists(OUT): raise SystemExit("exists, kept: " + OUT)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
parts = []          # (bmesh, material)

def add(bm, mat): parts.append((bm, mat))

def cyl(a, b, r, mat, seg=24, r2=None):
    a, b = Vector(a), Vector(b); d = b - a
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r if r2 is None else r2, depth=d.length)
    q = Vector((0, 0, 1)).rotation_difference(d.normalized())
    bmesh.ops.transform(bm, matrix=Matrix.Translation((a + b) / 2) @ q.to_matrix().to_4x4(), verts=bm.verts)
    add(bm, mat)

def box(c, size, mat, rot=None):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    m = Matrix.Translation(Vector(c)) @ (rot.to_4x4() if rot else Matrix()) @ Matrix.Diagonal((*size, 1.0))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=min(size) * 0.18, segments=1, affect='EDGES', clamp_overlap=True)
    add(bm, mat)

def ring(x, R, r, mat, seg=32, rseg=8):
    """a torus round the X axis at x"""
    bm = bmesh.new(); rings = []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        rings.append([bm.verts.new((x + r * math.sin(b), (R + r * math.cos(b)) * math.cos(a), (R + r * math.cos(b)) * math.sin(a)))
                      for b in (2 * math.pi * j / rseg for j in range(rseg))])
    for i in range(seg):
        for j in range(rseg):
            bm.faces.new((rings[i][j], rings[(i + 1) % seg][j], rings[(i + 1) % seg][(j + 1) % rseg], rings[i][(j + 1) % rseg]))
    add(bm, mat)

def sphere(c, r, mat, squash=1.0):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=14, v_segments=8, radius=r)
    bmesh.ops.transform(bm, matrix=Matrix.Translation(Vector(c)) @ Matrix.Diagonal((squash, 1.0, 1.0, 1.0)), verts=bm.verts)
    add(bm, mat)

def wound(x0, x1, Rw, r, mat, seg=40, rseg=6):
    """line wound round the X axis between x0 and x1, outer radius Rw: a core, and one strand of radius r spiralling across
    it touching turn to turn, so the wraps show as ridges"""
    cyl((x0, 0, 0), (x1, 0, 0), Rw - 1.6 * r, mat, seg=seg)
    turns = (x1 - x0 - 2 * r) / (2 * r); n = int(turns * seg) + 1; Rc = Rw - r
    bm = bmesh.new(); rings = []
    for i in range(n + 1):
        t = i / n; a = 2 * math.pi * turns * t; x = x0 + r + t * (x1 - x0 - 2 * r)
        c = Vector((x, Rc * math.cos(a), Rc * math.sin(a)))
        radial = Vector((0, math.cos(a), math.sin(a))); tang = Vector((0, -math.sin(a), math.cos(a)))
        side = Vector((1, 0, 0))                                   # the tube's section: in the plane of the radial and X
        rings.append([bm.verts.new(c + r * (math.cos(b) * radial + math.sin(b) * side)) for b in (2 * math.pi * j / rseg for j in range(rseg))])
    for i in range(n):
        for j in range(rseg):
            bm.faces.new((rings[i][j], rings[i + 1][j], rings[i + 1][(j + 1) % rseg], rings[i][(j + 1) % rseg]))
    for rg in (rings[0], rings[-1]): bm.faces.new(rg)              # cap the ends
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    add(bm, mat)

X = lambda deg: Matrix.Rotation(math.radians(deg), 3, 'X')

if GEAR.startswith("reel_"):
    STYLE = {"reel_bronze": "wood", "reel_iron": "spoked5", "reel_silver": "spoked8", "reel_blackmetal": "solid",
             "reel_dvergr": "gear", "reel_flametal": "spoked6", "reel_frostcore": "wood"}[GEAR]
    GLOW = GEAR in ("reel_dvergr", "reel_flametal", "reel_frostcore")
    R, W = 0.045, 0.030                               # plate radius, the drum's width between the plates
    PT = 0.006 if STYLE == "solid" else 0.0045        # plate thickness
    for s in (-1, 1):
        x = s * (W / 2 + PT / 2)
        if STYLE in ("wood", "solid", "gear"):
            cyl((x - PT / 2, 0, 0), (x + PT / 2, 0, 0), R, "plate", seg=40)
            if STYLE == "wood": ring(x, R, 0.0026, "metal")                       # a metal tyre round the wooden plate
            if STYLE == "gear":                                                    # dvergr teeth round the rim
                for k in range(22):
                    a = 2 * math.pi * k / 22
                    box((x, (R + 0.002) * math.cos(a), (R + 0.002) * math.sin(a)), (PT * 0.9, 0.0045, 0.006), "plate", X(math.degrees(a) - 90))
            if STYLE == "solid" or GEAR == "reel_frostcore":                        # rivets round the face
                for k in range(8):
                    a = 2 * math.pi * k / 8
                    cyl((x, (R - 0.008) * math.cos(a), (R - 0.008) * math.sin(a)), (x + s * (PT / 2 + 0.0015), (R - 0.008) * math.cos(a), (R - 0.008) * math.sin(a)), 0.0024, "metal", seg=10)
        else:                                                                       # a spoked wheel: rim, hub and spokes
            n = int(STYLE[6:])
            ring(x, R - 0.003, 0.0034, "plate")
            cyl((x - PT / 2, 0, 0), (x + PT / 2, 0, 0), 0.014, "plate", seg=24)
            for k in range(n):
                a = 2 * math.pi * (k + 0.5) / n; mid = (0.014 + R - 0.006) / 2
                box((x, mid * math.cos(a), mid * math.sin(a)), (PT * 0.8, 0.0055 if n < 8 else 0.004, R - 0.02), "plate", X(math.degrees(a) - 90))
            if n == 8:                                                              # silver: little bosses on the rim
                for k in range(8):
                    a = 2 * math.pi * k / 8
                    sphere((x + s * 0.002, (R - 0.003) * math.cos(a), (R - 0.003) * math.sin(a)), 0.0032, "metal")
        # the hub: a cap, or the glowing core
        if GLOW: sphere((x + s * 0.004, 0, 0), 0.0115, "glow", squash=0.55)
        else: cyl((x, 0, 0), (x + s * (PT / 2 + 0.004), 0, 0), 0.0085, "metal", seg=16)
    cyl((-W / 2, 0, 0), (W / 2, 0, 0), 0.012, "metal", seg=20)                    # the drum
    wound(-W / 2 + 0.0004, W / 2 - 0.0004, 0.034, 0.0011, "line")                # the line wound on it
    # the crank on the right: an arm across the plate and a wooden knob
    xo = W / 2 + PT + (0.012 if GLOW else 0.0045)
    tip = Vector((xo + 0.004, 0.022, 0.024))
    box(((xo + 0.002), tip.y / 2, tip.z / 2), (0.004, 0.009, math.hypot(tip.y, tip.z) + 0.006), "metal", X(-math.degrees(math.atan2(tip.y, tip.z))))
    cyl((tip.x, tip.y, tip.z), (tip.x + 0.02, tip.y, tip.z), 0.0062, "grip", seg=16, r2=0.0052)
    sphere((tip.x + 0.021, tip.y, tip.z), 0.0055, "grip")
    # the foot it's lashed to the rod by: a strut down from each plate to a bar under the reel
    for s in (-1, 1):
        box((s * (W / 2 + PT / 2), 0, -R - 0.004), (PT, 0.012, 0.012), "metal")
    box((0, 0, -R - 0.011), (W + 2 * PT + 0.016, 0.014, 0.004), "metal")

else:                     # a line: a wooden bobbin wound with it
    FR, L = 0.030, 0.044                               # flange radius, the length between the flanges
    for s in (-1, 1):
        cyl((s * L / 2, 0, 0), (s * (L / 2 + 0.005), 0, 0), FR, "flange", seg=36)
        ring(s * (L / 2 + 0.0025), FR, 0.0018, "flange", seg=36, rseg=6)
        cyl((s * (L / 2 + 0.005), 0, 0), (s * (L / 2 + 0.007), 0, 0), 0.0045, "metal", seg=12)   # the pin's ends
    cyl((-L / 2, 0, 0), (L / 2, 0, 0), 0.010, "flange", seg=20)                    # the core
    wound(-L / 2 + 0.0003, L / 2 - 0.0003, 0.0235, 0.0011, "line")                # the line wound on it
    # its loose end, off the top and down over the front
    pts = [Vector((0.006, 0.0, 0.0236)), Vector((0.008, -0.012, 0.0215)), Vector((0.009, -0.0225, 0.012)), Vector((0.01, -0.027, -0.004)), Vector((0.012, -0.026, -0.02))]
    for a, b in zip(pts, pts[1:]): cyl(a, b, 0.0011, "line", seg=6)

# ---------------------------------------------------------------- one object, materials, UVs
MATS = [m for m in ("plate", "flange", "metal", "grip", "line", "glow") if any(p[1] == m for p in parts)]
me = bpy.data.meshes.new("tackle"); bm_all = bmesh.new()
for bm, mat in parts:
    m2 = bpy.data.meshes.new("tmp"); bm.to_mesh(m2); bm.free()
    for p in m2.polygons: p.material_index = MATS.index(mat)
    bm_all.from_mesh(m2); bpy.data.meshes.remove(m2)
bm_all.to_mesh(me); bm_all.free()
ob = bpy.data.objects.new("tackle", me); bpy.context.scene.collection.objects.link(ob)
for name in MATS: me.materials.append(bpy.data.materials.new(name))
for p in me.polygons: p.use_smooth = True
# "Grain" UVs (metres): along each part's long side - and round the spool on the wound line, so its fibres wrap round
grain = me.uv_layers.new(name="Grain"); li_line = MATS.index("line")
for p in me.polygons:
    co = [me.vertices[me.loops[li].vertex_index].co for li in p.loop_indices]
    if p.material_index == li_line:
        for li, c in zip(p.loop_indices, co):
            ang = math.atan2(c.z, c.y); r = math.hypot(c.y, c.z)
            grain.data[li].uv = (ang * r * 6.0, c.x)         # U round the spool (stretched: the bake squeezes U), V across
        continue
    nrm = p.normal; ax = max(range(3), key=lambda i: abs(nrm[i])); a, b = [i for i in range(3) if i != ax]
    ea = max(c[a] for c in co) - min(c[a] for c in co); eb = max(c[b] for c in co) - min(c[b] for c in co)
    u, v = (a, b) if ea >= eb else (b, a)
    for li, c in zip(p.loop_indices, co): grain.data[li].uv = (c[u], c[v])
atlas = me.uv_layers.new(name="UVMap"); me.uv_layers.active = atlas; atlas.active_render = True
bpy.context.view_layer.objects.active = ob; ob.select_set(True)
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.006, scale_to_bounds=False)
bpy.ops.uv.pack_islands(margin=0.006)
bpy.ops.object.mode_set(mode='OBJECT')
co = [v.co for v in me.vertices]
print(f"GEAR {GEAR}: {len(me.vertices)} points, {sum(len(p.vertices) - 2 for p in me.polygons)} triangles; "
      f"{max(c.x for c in co) - min(c.x for c in co):.3f} x {max(c.y for c in co) - min(c.y for c in co):.3f} x {max(c.z for c in co) - min(c.z for c in co):.3f} m; slots {MATS}")
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("SAVED", OUT)
