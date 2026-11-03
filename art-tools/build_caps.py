# Builds the two angler caps round the player's head, from the body copy ("fitref") in the sou'wester's FBX, so they sit
# where the sou'wester does:
#   beanie - the Ice Angler's Watch Cap: a snug fisherman's watch cap worn high on the head, above the ears - ribbed knit,
#            a thick folded cuff, a small leather tag on the cuff (the user's references, 2026-11-02)
#   bucket - the Sun Angler's Cap: a cotton bucket hat with a leather band and cloth loops, its brim sloping down all
#            round, and a fisher's tackle on it: a red-and-white float, a little lure fish, two hooks through the crown
#            and a feathered fly tucked in the band
# One mesh object "fisher" (bake_wood_cooler.py / export_cap.py, VDW_KIND=cap), built in the body's centimetres and
# scaled to metres for baking (the Sanctus patterns are sized in metres); export_cap.py scales it back and adds fitref.
#   blender -b --factory-startup --python build_caps.py      env: VDW_CAP (beanie | bucket), VDW_OUT (new .blend)
import bpy, bmesh, os, math
import numpy as np
from mathutils import Vector, Matrix

CAP, OUT = os.environ["VDW_CAP"], os.environ["VDW_OUT"]
if os.path.exists(OUT): raise SystemExit("exists, kept: " + OUT)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
FBX = r"C:\Users\tripp\Desktop\Valheim_DeepWaters\ValheimDeepWatersUnity\Assets\DeepWaters\fisher_hat\fisher_hat_model.fbx"
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=FBX)
fit = bpy.data.objects["fitref"]
BV = np.array([fit.matrix_world @ v.co for v in fit.data.vertices])
from mathutils.bvhtree import BVHTree
BVH = BVHTree.FromPolygons([tuple(map(float, v)) for v in BV], [tuple(p.vertices) for p in fit.data.polygons])   # the body, to fit the beanie to the head itself
for o in list(bpy.data.objects): bpy.data.objects.remove(o)

# the head, as build_fisher_gear.py fitted the sou'wester (cm; +y is the back of the head, -y the face)
hp = BV[BV[:, 2] > 183]
HC = Vector((0.0, float((hp[:, 1].min() + hp[:, 1].max()) / 2) + 1.0, 186.0))
RX = float(np.abs(hp[:, 0]).max()) + 2.4; RY = float((hp[:, 1].max() - hp[:, 1].min()) / 2) + 2.2; HEADTOP = float(BV[:, 2].max())
print(f"HEAD centre {tuple(round(c, 1) for c in HC)}, RX {RX:.1f}, RY {RY:.1f}, top {HEADTOP:.1f}")

parts = []
def add(bm, mat): parts.append((bm, mat))

def shell(z_of, r_of, mat, nh, rows, close_top=True, thick=0.0):
    """a surface round the head: row j (0..rows) at angle a has height z_of(j, a) and radial scale r_of(j, a) of the
    head ellipse (RX, RY round HC); closed at the top with one point; thick > 0 adds an inner wall (cm)"""
    bm = bmesh.new(); grid = []
    for j in range(rows + 1):
        row = []
        for k in range(nh):
            a = 2 * math.pi * k / nh; s = r_of(j, a)
            row.append(bm.verts.new((HC.x + RX * s * math.cos(a), HC.y + RY * s * math.sin(a), z_of(j, a))))
        grid.append(row)
    for j in range(rows):
        for k in range(nh): bm.faces.new((grid[j][k], grid[j][(k + 1) % nh], grid[j + 1][(k + 1) % nh], grid[j + 1][k]))
    if close_top:
        c = bm.verts.new((HC.x, HC.y, max(v.co.z for v in grid[-1]) + 0.05))
        for k in range(nh): bm.faces.new((grid[-1][k], grid[-1][(k + 1) % nh], c))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if thick > 0:
        r = bmesh.ops.solidify(bm, geom=list(bm.faces), thickness=thick)
    add(bm, mat)
    return grid

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

def sphere(c, r, mat, scale=(1, 1, 1), useg=14, vseg=10, frame=None, zcut=None):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=useg, v_segments=vseg, radius=r)
    if zcut is not None:   # keep one half: zcut=+1 the top, -1 the bottom
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z * zcut < -1e-6], context='VERTS')
        edge = [e for e in bm.edges if e.is_boundary]
        if edge: bmesh.ops.edgeloop_fill(bm, edges=edge)
    M = Matrix.Diagonal((*scale, 1))
    if frame is not None: M = frame @ M
    bmesh.ops.transform(bm, matrix=Matrix.Translation(Vector(c)) @ M, verts=bm.verts)
    add(bm, mat)

def box(c, size, mat, frame=Matrix.Identity(4)):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.transform(bm, matrix=Matrix.Translation(Vector(c)) @ frame @ Matrix.Diagonal((*size, 1)), verts=bm.verts)
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=min(size) * 0.25, segments=1, affect='EDGES', clamp_overlap=True)
    add(bm, mat)

def surface(a, z, s):
    """the point on the hat's surface at angle a, height z, radial scale s; its outward normal and the tangent round it"""
    p = Vector((HC.x + RX * s * math.cos(a), HC.y + RY * s * math.sin(a), z))
    n = Vector((math.cos(a) / RX, math.sin(a) / RY, 0)).normalized(); t = Vector((0, 0, 1)).cross(n)
    return p, n, t

def frame_at(n, t):
    """a 4x4 rotation taking local x -> tangent, y -> outward, z -> up"""
    return Matrix((-t, n, Vector((0, 0, 1)))).transposed().to_4x4()      # (-t: right-handed, so faces point outward)

def hook(top, n, t, length, gape, mat, r=0.11, flip=1):
    """a J hook hanging from `top`: the shank down, the bend curling out (along n) and its point back up, with a barb"""
    top = Vector(top); pts = [top + Vector((0, 0, -length * 0.65 * i / 5)) for i in range(6)]
    c = top + Vector((0, 0, -length * 0.65)) + n * (gape / 2) * flip
    for i in range(1, 9):
        a = math.pi + math.pi * i / 8
        pts.append(c + n * (math.cos(a) * gape / 2) * flip + Vector((0, 0, math.sin(a) * gape / 2)))
    pts.append(pts[-1] + Vector((0, 0, length * 0.3)))
    tube(pts, [r] * len(pts), mat, seg=6)
    tip = pts[-1]; tube([tip, tip + Vector((0, 0, -0.35)) - n * 0.3 * flip], [r * 1.1, r * 0.15], mat, seg=5)   # the barb
    eye = [top + Vector((0, 0, 0.28)) + (t * math.cos(2 * math.pi * k / 12) * 0.28 + Vector((0, 0, 1)) * math.sin(2 * math.pi * k / 12) * 0.28) for k in range(13)]
    tube(eye, [r * 0.8] * 13, mat, seg=5, caps=False)

if CAP == "beanie":
    # Fitted to the head itself (v2, "more snug"): rays out from inside the skull find the head's surface in every
    # direction (smoothed, so the body's low-poly facets don't show), and the cap sits a set distance off it - thin knit
    # over the crown, the folded cuff thicker - so it hugs the head like the references instead of standing off it.
    NH = 120; RIBS = 30                                    # 4 points to a rib, round the head
    # the ribs are mostly in the baked normal map (bake_wood_cooler.py reads "vdw_ribs"): the mesh only hints at them, so it
    # stays smooth instead of faceted
    RIB_GEO = 0.15
    sl = BV[(BV[:, 2] > 189) & (BV[:, 2] < 195)]
    C = Vector((0.0, float((sl[:, 1].min() + sl[:, 1].max()) / 2), 192.0))   # inside the skull, at brow height
    def dirv(a, el): return Vector((math.cos(a) * math.cos(el), math.sin(a) * math.cos(el), math.sin(el)))
    def head_r(a, el):
        d = dirv(a, el); hit, _, _, _ = BVH.ray_cast(C + d * 40.0, -d, 60.0)
        return (hit - C).length if hit is not None else None
    # its lower edge: above the brows in front, a little lower at the back, clear of the ears
    zb = lambda a: 191.6 - 1.6 * (math.sin(a) + 1) / 2
    CUFF_H = 4.6                                           # the folded cuff's height (cm)
    def el_at(a, z, guess=0.0):                            # the elevation from C that meets the head at height z
        el = guess
        for _ in range(6):
            r = head_r(a, el) or 10.0; el = math.asin(max(-0.95, min(0.95, (z - C.z) / r)))
        return el
    # rows: the cuff's (by height) then the crown's (by elevation up to the top); off = cm off the head, rib = rib depth
    CUFF = [(0.0, 0.25, 0.0), (0.3, 0.75, 0.2), (0.9, 1.05, 0.32), (2.3, 1.15, 0.27), (3.7, 1.15, 0.27), (4.3, 1.08, 0.25), (4.55, 0.95, 0.2), (4.6, 0.8, 0.1)]
    NR = 10
    rows = []    # per row, per angle: (elevation, offset, rib depth)
    for z_off, off, rd in CUFF:
        rows.append([(el_at(2 * math.pi * k / NH, zb(2 * math.pi * k / NH) + z_off), off, rd) for k in range(NH)])
    cuff_rows = len(rows)
    el_top = [rows[-1][k][0] - 0.16 for k in range(NH)]  # the crown starts tucked inside the cuff's top
    for j in range(NR + 1):
        t = j / NR
        rows.append([(el_top[k] + (math.pi / 2 - 1e-3 - el_top[k]) * math.sin(t * math.pi / 2) ** 0.9,
                      (0.72 + 0.08 * min(1.0, t * 3)) + 0.27 * math.sin(t * math.pi) + 0.35 * t ** 2,       # knit standing a little off the crown, fuller toward the top
                      0.22 * (1 - t) ** 1.3) for k in range(NH)])
    # the head's distance in each direction, smoothed round and up the head
    R = np.array([[head_r(2 * math.pi * k / NH, rows[j][k][0]) or np.nan for k in range(NH)] for j in range(len(rows))])
    for j in range(len(rows)):
        bad = np.isnan(R[j])
        if bad.all(): R[j] = R[j - 1]
        elif bad.any(): R[j][bad] = np.nanmean(R[j])
    W = 9; R_raw = R.copy()
    for _ in range(3):
        R = np.stack([np.convolve(np.concatenate([r[-W:], r, r[:W]]), np.ones(2 * W + 1) / (2 * W + 1), mode='same')[W:-W] for r in R])
        R[1:-1] = (R[:-2] + 2 * R[1:-1] + R[2:]) / 4
    def smooth1(R):
        R = np.stack([np.convolve(np.concatenate([r[-W:], r, r[:W]]), np.ones(2 * W + 1) / (2 * W + 1), mode='same')[W:-W] for r in R])
        R[1:-1] = (R[:-2] + 2 * R[1:-1] + R[2:]) / 4; return R
    # smoothed but kept off the head: never under it, then eased once more (a hair under at most, inside the knit's thickness)
    R = np.maximum(R, R_raw); R = smooth1(R); R = np.maximum(R, R_raw)
    # the crown smoothed further (the body's low-poly head showed through as lumps): it may dip a little toward the head,
    # inside the room its knit stands off it, never into it
    for _ in range(4):
        Rc = smooth1(R.copy()); R[cuff_rows + 3:] = np.maximum(Rc[cuff_rows + 3:], R_raw[cuff_rows + 3:] - 0.4)   # (not the rows tucked under the cuff)
    def pt(j, k):
        a = 2 * math.pi * k / NH; el, off, rd = rows[j][k]
        return C + dirv(a, el) * (R[j][k] + off + RIB_GEO * rd * math.cos(RIBS * a))
    def grid(j0, j1, close_top, thick):
        bm = bmesh.new(); g = [[bm.verts.new(pt(j, k)) for k in range(NH)] for j in range(j0, j1)]
        for j in range(len(g) - 1):
            for k in range(NH): bm.faces.new((g[j][k], g[j][(k + 1) % NH], g[j + 1][(k + 1) % NH], g[j + 1][k]))
        if close_top:
            c = bm.verts.new(sum((v.co for v in g[-1]), Vector()) / NH + Vector((0, 0, 0.1)))
            for k in range(NH): bm.faces.new((g[-1][k], g[-1][(k + 1) % NH], c))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bmesh.ops.solidify(bm, geom=list(bm.faces), thickness=thick)
        add(bm, "wool")
    grid(0, cuff_rows, False, 0.45)                        # the folded cuff
    grid(cuff_rows, len(rows), True, 0.4)                  # the crown
    # a small leather tag stitched on the cuff, front left
    k = int(round((math.radians(-90 + 32) % (2 * math.pi)) / (2 * math.pi) * NH)) % NH
    p = (pt(3, k) + pt(4, k)) / 2; a = 2 * math.pi * k / NH
    n = Vector((math.cos(a), math.sin(a), 0)); t = Vector((0, 0, 1)).cross(n)
    box(p + n * 0.15, (1.25, 0.22, 1.9), "leather", frame_at(n, t))
    box(p + n * 0.29, (0.55, 0.08, 1.1), "metal", frame_at(n, t))        # its little metal plate
    MATS = ("wool", "leather", "metal")
    gaps = [(pt(j, k) - C).length - R_raw[j][k] for j in range(len(rows)) for k in range(0, NH, 10)]
    print(f"BEANIE fitted: off the head {min(gaps):.2f}..{max(gaps):.2f} cm")

else:   # bucket
    NH = 96
    zb = lambda a: 192.6 - 2.0 * (math.sin(a) + 1) / 2     # the band's lower edge: low on the brow, lower at the back
    TOP = HEADTOP + 2.8
    BASE_S = 1.06                                          # the crown's sides: a little roomy, tapering in toward the top
    def head_s(z): return max(0.25, math.cos(math.asin(min(1.0, max(-1.0, (z - HC.z) / (HEADTOP + 2.0 - HC.z))))))
    S0 = lambda a: head_s(zb(a)) * BASE_S
    NR = 12
    def crown_z(j, a):
        t = j / NR; z0 = zb(a)
        return z0 + (TOP - z0) * min(1.0, t * 1.12) - (0.0 if t < 0.85 else 0.9 * (t - 0.85) / 0.15 * 0)
    def crown_s(j, a):
        t = j / NR
        s = S0(a) * (1 - 0.14 * t)                         # tapering up
        if t > 0.78: s *= max(0.0, math.cos(min(1.0, (t - 0.78) / 0.22) * math.pi / 2)) ** 0.6 * 0.98 + 0.02   # the rounded top edge
        return max(s, 0.02)
    shell(crown_z, crown_s, "cloth", NH, NR, close_top=True, thick=0.35)
    # the brim: out and down all round, a gentle wave in it
    BR = [(0.0, 0.0), (0.33, 1.0), (0.66, 2.0), (1.0, 3.0)]
    def brim_pt(j, a):
        w = 7.8 * BR[j][0]; drop = math.radians(34 + 4 * math.sin(3 * a + 0.5)) + math.radians(6) * BR[j][0]
        s0 = S0(a); p = Vector((HC.x + RX * s0 * math.cos(a), HC.y + RY * s0 * math.sin(a), zb(a) + 0.2))
        d = Vector((math.cos(a) / RX, math.sin(a) / RY, 0)).normalized()
        return p + d * w * math.cos(drop) - Vector((0, 0, w * math.sin(drop)))
    bm = bmesh.new(); grid = [[bm.verts.new(brim_pt(j, 2 * math.pi * k / NH)) for k in range(NH)] for j in range(len(BR))]
    for j in range(len(BR) - 1):
        for k in range(NH): bm.faces.new((grid[j][k], grid[j][(k + 1) % NH], grid[j + 1][(k + 1) % NH], grid[j + 1][k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bmesh.ops.solidify(bm, geom=list(bm.faces), thickness=0.35); add(bm, "cloth")
    # rows of stitching round the brim
    for f in (0.28, 0.55, 0.82):
        pts = []
        for k in range(NH + 1):
            a = 2 * math.pi * k / NH; w = 7.8 * f; drop = math.radians(34 + 4 * math.sin(3 * a + 0.5)) + math.radians(6) * f
            s0 = S0(a); p = Vector((HC.x + RX * s0 * math.cos(a), HC.y + RY * s0 * math.sin(a), zb(a) + 0.2))
            d = Vector((math.cos(a) / RX, math.sin(a) / RY, 0)).normalized()
            nrm = (Vector((0, 0, 1)) * math.cos(drop) + d * math.sin(drop))
            pts.append(p + d * w * math.cos(drop) - Vector((0, 0, w * math.sin(drop))) + nrm * 0.12)
        tube(pts, [0.045] * len(pts), "thread", seg=4, caps=False)
    # the leather band round the bottom of the crown, and cloth loops over it
    BAND0, BAND1 = 0.5, 2.9
    def band_z(j, a): return zb(a) + (BAND0, BAND0 + 0.1, BAND1 - 0.1, BAND1)[j]
    def band_s(j, a):
        t = (BAND0 + 0.1 * (j > 0) + (BAND1 - BAND0 - 0.2) * (j > 1)) / (TOP - zb(a)) / 1.12
        return crown_s(t * NR, a) + (0.0, 0.02, 0.02, 0.0)[j]
    shell(band_z, band_s, "leather", NH, 3, close_top=False)
    for a_deg in (-130, -60, 20, 95, 160):
        a = math.radians(a_deg); z = zb(a) + (BAND0 + BAND1) / 2
        p, n, t = surface(a, z, band_s(1, a) + 0.025)
        box(p + n * 0.32, (0.9, 0.22, 3.0), "cloth", frame_at(n, t))
    # the tackle on it: front is -y (a = -90 deg)
    def on_band(a_deg, out=0.25):
        a = math.radians(a_deg); z = zb(a) + (BAND0 + BAND1) / 2
        p, n, t = surface(a, z, band_s(1, a) + 0.03); return p + n * out, n, t
    def on_crown(a_deg, z_above, out):
        """a point on the crown z_above the band's lower edge, `out` off its surface"""
        a = math.radians(a_deg); z = zb(a) + z_above; jt = (z - zb(a)) / (TOP - zb(a)) / 1.12
        p, n, t = surface(a, z, crown_s(jt * NR, a)); return p + n * out, n, t
    # 1. a red-and-white float pinned to the crown on the right, above the band, on a wire through the cloth
    c, n, t = on_crown(-30, BAND1 + 2.2, 1.6)
    sphere(c, 1.7, "red", zcut=1, useg=18, vseg=12); sphere(c, 1.7, "white", zcut=-1, useg=18, vseg=12)
    tube([c + Vector((0, 0, 1.6)), c + Vector((0, 0, 2.3))], [0.3, 0.24], "white", seg=8)                # its stem
    tube([c - Vector((0, 0, 1.6)), c - Vector((0, 0, 2.2))], [0.2, 0.06], "white", seg=6)
    top = c + Vector((0, 0, 2.3)); pin, _, _ = on_crown(-30, BAND1 + 5.2, 0.05)
    tube([top, (top + pin) / 2 + n * 0.5, pin], [0.1, 0.1, 0.1], "metal", seg=5)                          # the wire into the crown
    # 2. a little lure fish on the crown, front left, its nose hooked into the band and its body up the side
    rad = [0.35, 0.8, 1.1, 1.2, 1.1, 0.95, 0.7, 0.45, 0.22]
    body = [on_crown(-122 - 3.2 * i, BAND1 - 0.6 + 0.85 * i, rad[i] * 0.75 + 0.15)[0] for i in range(9)]
    n0 = on_crown(-122, BAND1, 0)[1]
    tube(body, rad, "lure", seg=12)
    tdir = (body[-1] - body[-2]).normalized(); side = tdir.cross(n0).normalized()
    for s_ in (-1, 1): tube([body[-1], body[-1] + tdir * 1.3 + side * 0.8 * s_], [0.45, 0.06], "lure", seg=6)   # tail
    for s_ in (-1, 1): sphere(body[1] + side * 0.62 * s_ + n0 * 0.35, 0.2, "black")
    hook(body[0] + Vector((0, 0, 0.2)), n0, side, 2.6, 1.1, "metal", r=0.13)                                # the hook it hangs from
    # 3. two hooks through the crown, front
    for a_deg, zo in ((-80, BAND1 + 2.6), (-102, BAND1 + 4.2)):
        p, n, t = on_crown(a_deg, zo, 0.2)
        hook(p, n, t, 3.4, 1.4, "metal", r=0.14)
    # 4. a fly tucked in the band on the left: a black head, blue and pink feathers sweeping back, its hook showing
    p, n, t = on_band(-168, 0.4)
    sphere(p + n * 0.4, 0.65, "black")
    for k, (mat, ang, ln) in enumerate((("feather_b", 20, 5.8), ("feather_b", 6, 6.4), ("feather_b", -8, 5.4), ("feather_p", 13, 4.8), ("feather_p", -1, 4.2))):
        d = (t * math.cos(math.radians(ang)) + Vector((0, 0, math.sin(math.radians(ang))))).normalized()
        q0 = p + n * 0.45; q1 = q0 + d * ln * 0.5 + n * 0.35; q2 = q0 + d * ln + n * 0.15
        tube([q0, q1, q2], [0.48, 0.58, 0.08], mat, seg=6)
    hook(p - t * 0.5 + Vector((0, 0, -0.3)), n, t, 2.4, 1.1, "metal", r=0.12)
    MATS = ("cloth", "leather", "thread", "metal", "red", "white", "lure", "black", "feather_b", "feather_p")

# ---------------------------------------------------------------- one object in metres, materials, UVs
MATS = [m for m in MATS if any(p[1] == m for p in parts)]
me = bpy.data.meshes.new("fisher"); bm_all = bmesh.new()
for bm, mat in parts:
    m2 = bpy.data.meshes.new("tmp"); bm.to_mesh(m2); bm.free()
    for p in m2.polygons: p.material_index = MATS.index(mat)
    bm_all.from_mesh(m2); bpy.data.meshes.remove(m2)
bm_all.to_mesh(me); bm_all.free()
me.transform(Matrix.Scale(0.01, 4))                       # cm -> m (export_cap.py undoes it)
ob = bpy.data.objects.new("fisher", me); bpy.context.scene.collection.objects.link(ob)
if CAP == "beanie": ob["vdw_ribs"] = [float(RIBS), C.x * 0.01, C.y * 0.01, C.z * 0.01]   # rib count and the axis they run round (m)
for name in MATS: me.materials.append(bpy.data.materials.new(name))
for p in me.polygons: p.use_smooth = True
grain = me.uv_layers.new(name="Grain")                    # (no wood on the caps; the bake wants the layer)
for p in me.polygons:
    for li in p.loop_indices:
        c = me.vertices[me.loops[li].vertex_index].co; grain.data[li].uv = (c.x, c.z)
atlas = me.uv_layers.new(name="UVMap"); me.uv_layers.active = atlas; atlas.active_render = True
bpy.context.view_layer.objects.active = ob; ob.select_set(True)
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(50), island_margin=0.004, scale_to_bounds=False)
bpy.ops.uv.pack_islands(margin=0.004)
bpy.ops.object.mode_set(mode='OBJECT')
co = np.array([v.co for v in me.vertices])
print(f"CAP {CAP}: {len(me.vertices)} points, {sum(len(p.vertices) - 2 for p in me.polygons)} triangles; "
      f"{(co.max(0) - co.min(0)).round(3)} m; slots {MATS}")
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("SAVED", OUT)
