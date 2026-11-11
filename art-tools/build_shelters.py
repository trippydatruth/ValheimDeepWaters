# The ice-fishing shelters (roadmap: Ice Fishing - Ice Shelter), built procedurally. Each is one object "bait" whose
# material slots are named for what they're made of, a "Grain" UV in metres along each part (wood), and a fresh
# "UVMap" atlas. Z up, the ground (the ice) at z = 0, the door facing +Y. Each has a clear spot in the middle for the
# fire (Valheim's own campfire is put there in game) under a real opening for its smoke: Valheim's smoke is physical,
# it rises and gathers under a roof and chokes the fire if it can't get out.
#   VDW_PIECE=igloo: the Ice Shelter - a dome of the game's ice blocks (slots "ice" and "snow", given Valheim's own ice
#       and snow materials in game, like the Ice Cube piece), laid in courses, snow packed in the joints and banked
#       round the foot, a block tunnel for the door, a snow bench at the back, a 1 m vent at the top.
#   VDW_PIECE=lavvu: the Hide Lavvu - the far north's pole tent: twelve peeled poles crossing at the top, a cover of
#       sewn hides closed above the door with wooden pins, open at the top for the smoke (the poles through it), a rolled
#       door flap, a cross pole high up, hide rugs, snow round the foot (no fire or seats: the middle clear for a hole).
#       (Sanctus + Grungit bake: bake_wood_cooler.py VDW_KIND=lure VDW_TIER=lavvu)
#   VDW_PIECE=ship_tent: the Ship-Tent - a Viking ship's tent: crossed gable boards at each end (Valheim's own carved
#       dragon head - the Dragon Head piece's - is set on each crossing in game, IceShelters.AddDragonHeads), a ridge
#       pole, a cover of sewn hides with Elaking hair along the ridge, a raised smoke hood on a timber-framed gap in the ridge, the
#       top of each gable left open, guy ropes and stakes. (bake: VDW_TIER=ship_tent)
#   Room inside each for the campfire (its stone ring ~1.6 m across) and for ice holes round it with an angler standing
#   at each: the tent's holes go in its front and back halves, the lavvu's and igloo's in a ring round the fire.
#   The hides are patchwork - separate pieces of two hides (slots "hide" and "hide2"), each lapped over the next and
#   stitched with sinew (patchwork()) - and the bake darkens them with smoke towards the vent and with grime along each
#   hide's edges (the "vdw_grime" vertex attribute).
#   env: VDW_PIECE, VDW_OUT (folder: <out>/Blender Files/<piece>.blend)
import bpy, bmesh, math, os, random
from mathutils import Vector

PIECE = os.environ["VDW_PIECE"]; OUT = os.environ["VDW_OUT"]
BF = os.path.join(OUT, "Blender Files"); os.makedirs(BF, exist_ok=True)
DEST = os.path.join(BF, f"{PIECE}.blend")
if os.path.exists(DEST): raise SystemExit("exists, kept: " + DEST)
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
rnd = random.Random(7)

MATS = {"igloo": ["ice", "snow"],
        "lavvu": ["hide", "hide2", "wood", "bark", "leather", "iron", "fur", "snow"],
        "ship_tent": ["hide", "hide2", "wood", "iron", "leather", "linen", "fur", "red", "snow"]}[PIECE]
bm = bmesh.new()
GRAIN = {}

def face(vs, mat, grain=("plank", Vector((1, 0, 0))), smooth=True):
    try: f = bm.faces.new(vs)
    except ValueError: return None
    f.material_index = MATS.index(mat); f.smooth = smooth; GRAIN[f] = grain
    return f

def frame(t):
    t = t.normalized(); a = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
    a = (a - t * a.dot(t)).normalized(); return a, t.cross(a)

def tube(path, radii, mat, seg=12, caps=True, smooth=True, closed=False, flat=None, side=None):
    """A tube along a path, a radius per point. flat: per point, the radius across `side` as a fraction (a carved
    board's thickness); side: the direction that's flattened (kept fixed along the path)."""
    path = [Vector(p) for p in path]; n = len(path); rings = []; a = None
    for i, p in enumerate(path):
        nxt = path[(i + 1) % n] if closed else path[min(i + 1, n - 1)]
        prv = path[(i - 1) % n] if closed else path[max(i - 1, 0)]
        t = (nxt - prv).normalized()
        if side is not None:
            b = (Vector(side) - t * Vector(side).dot(t)).normalized(); a = b.cross(t)
        elif a is None: a, b = frame(t)
        else: a = (a - t * a.dot(t)).normalized(); b = t.cross(a)
        fb = flat[i] if flat else 1.0
        rings.append([bm.verts.new(p + (a * math.cos(2 * math.pi * k / seg) + b * fb * math.sin(2 * math.pi * k / seg)) * radii[i]) for k in range(seg)])
    axis = ("axis", path[0], (path[-1] - path[0]).normalized() if (path[-1] - path[0]).length > 1e-6 else Vector((0, 0, 1)))
    for i in range(n if closed else n - 1):
        r0, r1 = rings[i], rings[(i + 1) % n]
        for k in range(seg):
            face([r0[k], r0[(k + 1) % seg], r1[(k + 1) % seg], r1[k]], mat, axis, smooth)
    if caps and not closed:
        for ring, flip in ((rings[0], True), (rings[-1], False)):
            c = bm.verts.new(sum((v.co for v in ring), Vector()) / seg)
            for k in range(seg):
                vs = [ring[k], ring[(k + 1) % seg], c]
                face(vs[::-1] if flip else vs, mat, ("plank", Vector((1, 0, 0))), smooth=False)

def box(c, size, mat, rot=0.0, grain=Vector((1, 0, 0))):
    c = Vector(c); sx, sy, sz = (s / 2 for s in size); cs, sn = math.cos(rot), math.sin(rot)
    def P(x, y, z): return bm.verts.new(c + Vector((x * cs - y * sn, x * sn + y * cs, z)))
    v = [P(x, y, z) for x in (-sx, sx) for y in (-sy, sy) for z in (-sz, sz)]
    g = ("plank", Vector((cs, sn, 0)) if grain.x else Vector((-sn, cs, 0)) if grain.y else Vector((0, 0, 1)))
    for q in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
        face([v[i] for i in q], mat, g, smooth=False)

def sheet(P, nu, nv, mat, thick, smooth=True, keep=None, grain=None):
    """A thin two-sided sheet from P(u, v) -> point (u, v in 0..1), thickness `thick` along its normal (inward = -n
    for a cover); keep(u, v) -> False drops a cell (a door, a vent). mat: a slot, or mat(u, v) -> a slot per cell
    (patchwork)."""
    g = grain or ("plank", Vector((1, 0, 0)))
    slot_of = mat if callable(mat) else (lambda u, v: mat)
    pts = [[Vector(P(i / nu, j / nv)) for j in range(nv + 1)] for i in range(nu + 1)]
    def N(i, j):
        du = pts[min(i + 1, nu)][j] - pts[max(i - 1, 0)][j]; dv = pts[i][min(j + 1, nv)] - pts[i][max(j - 1, 0)]
        return du.cross(dv).normalized()
    outer = [[bm.verts.new(pts[i][j]) for j in range(nv + 1)] for i in range(nu + 1)]
    inner = [[bm.verts.new(pts[i][j] - N(i, j) * thick) for j in range(nv + 1)] for i in range(nu + 1)]
    cells = [[keep is None or keep((i + 0.5) / nu, (j + 0.5) / nv) for j in range(nv)] for i in range(nu)]
    def on(i, j): return 0 <= i < nu and 0 <= j < nv and cells[i][j]
    for i in range(nu):
        for j in range(nv):
            if not cells[i][j]: continue
            mat = slot_of((i + 0.5) / nu, (j + 0.5) / nv)
            face([outer[i][j], outer[i + 1][j], outer[i + 1][j + 1], outer[i][j + 1]], mat, g, smooth)
            face([inner[i][j], inner[i][j + 1], inner[i + 1][j + 1], inner[i + 1][j]], mat, g, smooth)
            # the sheet's edges (where a cell has no neighbour): closed
            if not on(i - 1, j): face([outer[i][j], outer[i][j + 1], inner[i][j + 1], inner[i][j]], mat, g, False)
            if not on(i + 1, j): face([outer[i + 1][j], inner[i + 1][j], inner[i + 1][j + 1], outer[i + 1][j + 1]], mat, g, False)
            if not on(i, j - 1): face([outer[i][j], inner[i][j], inner[i + 1][j], outer[i + 1][j]], mat, g, False)
            if not on(i, j + 1): face([outer[i][j + 1], outer[i + 1][j + 1], inner[i + 1][j + 1], inner[i][j + 1]], mat, g, False)

# Sewn hides: each hide its own piece of leather, its edge lapped FLAP over the next hide's and resting on it (raised
# SEAM_T per hide under it, easing back down over BORDER), stitched along the lap with sinew. Each vertex carries
# "vdw_grime" (1 at a hide's edges, fading in over ~10 cm): the bake darkens and dirties the leather there.
SEAM_T, HIDE_T, FLAP, BORDER = 0.010, 0.008, 0.035, 0.08
GRIME = bm.verts.layers.float.new("vdw_grime")

def smooth01(x): x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)

def patchwork(P, out, nu, nv, panels, keep=None):
    """P(u, v) -> a point on the cover; out(p) -> roughly outward there; nu, nv: the cover's grid (its lines are kept
    inside each hide). panels: (u0, u1, v0, v1, slot, laps) - laps: {"u0"/"u1"/"v0"/"v1": w}, w > 0 where this hide
    laps over its neighbour (w = how many hides' thickness it rides over there); left out where it's under, or an
    open edge. keep(u, v) -> False drops a cell (a vent)."""
    def nrm(u, v, e=1e-3):
        du = Vector(P(u + e, v)) - Vector(P(u - e, v)); dv = Vector(P(u, v + e)) - Vector(P(u, v - e))
        n = du.cross(dv).normalized(); return n if n.dot(out(Vector(P(u, v)))) >= 0 else -n
    for (u0, u1, v0, v1, slot, laps) in panels:
        um, vm = (u0 + u1) / 2, (v0 + v1) / 2
        mu = (Vector(P(um + 1e-3, vm)) - Vector(P(um - 1e-3, vm))).length / 2e-3     # metres per unit u, v here
        mv = (Vector(P(um, vm + 1e-3)) - Vector(P(um, vm - 1e-3))).length / 2e-3
        def lines(a, b, n, m, lo, hi):
            fixed = {a, b}
            for dist in (FLAP, BORDER):
                if (b - a) * m > 2 * dist + 0.03: fixed |= {a + dist / m, b - dist / m}
            if lo: fixed.add(a - FLAP / m)
            if hi: fixed.add(b + FLAP / m)
            grid = [k / n for k in range(n + 1) if a < k / n < b and all(abs(k / n - f) * m > 0.03 for f in fixed)]
            return sorted(fixed | set(grid))
        us = lines(u0, u1, nu, mu, laps.get("u0"), laps.get("u1"))
        vs = lines(v0, v1, nv, mv, laps.get("v0"), laps.get("v1"))
        def dists(u, v): return {"u0": (u - u0) * mu, "u1": (u1 - u) * mu, "v0": (v - v0) * mv, "v1": (v1 - v) * mv}
        def lift(u, v):
            d = dists(u, v); return SEAM_T * sum(w * (1.0 if d[s] <= 0 else smooth01(1 - d[s] / BORDER)) for s, w in laps.items() if w)
        def grime(u, v):
            return max((1 - min(1.0, max(0.0, x) / 0.10)) ** 2 for x in dists(u, v).values())
        outer, inner = [], []
        for u in us:
            ro, ri = [], []
            for v in vs:
                n = nrm(u, v); p = Vector(P(u, v)) + n * lift(u, v); gr = grime(u, v)
                a_ = bm.verts.new(p); b_ = bm.verts.new(p - n * HIDE_T); a_[GRIME] = b_[GRIME] = gr
                ro.append(a_); ri.append(b_)
            outer.append(ro); inner.append(ri)
        NI, NJ = len(us) - 1, len(vs) - 1
        cells = [[keep is None or keep((us[i] + us[i + 1]) / 2, (vs[j] + vs[j + 1]) / 2) for j in range(NJ)] for i in range(NI)]
        def on(i, j): return 0 <= i < NI and 0 <= j < NJ and cells[i][j]
        g = ("plank", Vector((1, 0, 0)))
        for i in range(NI):
            for j in range(NJ):
                if not cells[i][j]: continue
                face([outer[i][j], outer[i + 1][j], outer[i + 1][j + 1], outer[i][j + 1]], slot, g)
                face([inner[i][j], inner[i][j + 1], inner[i + 1][j + 1], inner[i + 1][j]], slot, g)
                if not on(i - 1, j): face([outer[i][j], outer[i][j + 1], inner[i][j + 1], inner[i][j]], slot, g, False)
                if not on(i + 1, j): face([outer[i + 1][j], inner[i + 1][j], inner[i + 1][j + 1], outer[i + 1][j + 1]], slot, g, False)
                if not on(i, j - 1): face([outer[i][j], inner[i][j], inner[i + 1][j], outer[i + 1][j]], slot, g, False)
                if not on(i, j + 1): face([outer[i][j + 1], outer[i + 1][j + 1], inner[i + 1][j + 1], inner[i][j + 1]], slot, g, False)
        # the stitching: a running stitch of sinew down the middle of each lap, a little slanted
        for s, w in laps.items():
            if not w: continue
            along_u = s in ("v0", "v1")
            a, b, m = (u0, u1, mu) if along_u else (v0, v1, mv)
            fix = {"u0": u0 - FLAP / 2 / mu, "u1": u1 + FLAP / 2 / mu, "v0": v0 - FLAP / 2 / mv, "v1": v1 + FLAP / 2 / mv}[s]
            t, step, dash = a + 0.012 / m, 0.032 / m, 0.02 / m
            while t + dash < b - 0.012 / m:
                ends = []
                for tt, slant in ((t, -0.004), (t + dash, 0.004)):
                    uu, vv = (tt, fix + slant / mv) if along_u else (fix + slant / mu, tt)
                    ends.append((uu, vv))
                if keep is None or all(keep(uu, vv) for uu, vv in ends):
                    pts = [Vector(P(uu, vv)) + nrm(uu, vv) * (lift(uu, vv) + 0.0012) for uu, vv in ends]
                    tube(pts, [0.0026, 0.0026], "leather", seg=4, caps=False)
                t += step

def lump(x, y, s=1.0):
    return s * (0.5 * math.sin(x * 3.1 + y * 1.7) + 0.3 * math.sin(x * 7.3 - y * 5.1 + 1.3) + 0.2 * math.sin(x * 13.7 + y * 11.3 + 0.4))

def berm(R0, R1, H, mat, skip=None, seg=96, cx=0.0, cy=0.0):
    """Snow banked round a foot: a lumpy ring from radius R0 (against the wall, height H) out to R1 (the ground);
    skip(theta) -> True leaves a gap (the door)."""
    prof = [(R0 - 0.08, -0.02), (R0, H * 0.9), (R0 + (R1 - R0) * 0.25, H), (R0 + (R1 - R0) * 0.6, H * 0.55), (R1, -0.02)]
    # either side of a gap the bank slopes down into the ground over TAPER radians (it stopped dead there, its cut ends open)
    TAPER = 0.35
    gaps = [2 * math.pi * (k + 0.5) / seg for k in range(seg) if skip and skip(2 * math.pi * (k + 0.5) / seg)]
    def height(t):
        if not gaps: return 1.0
        d = min(abs(math.atan2(math.sin(t - g), math.cos(t - g))) for g in gaps) - math.pi / seg
        return smooth01(d / TAPER)
    for k in range(seg):
        t0, t1 = 2 * math.pi * k / seg, 2 * math.pi * (k + 1) / seg
        if skip and skip((t0 + t1) / 2): continue
        ring = []
        for t in (t0, t1):
            col = []; hk = height(t)
            for i, (r, z) in enumerate(prof):
                l = lump(math.cos(t) * r, math.sin(t) * r) * (0.35 * H if 0 < i < len(prof) - 1 else 0)
                col.append(bm.verts.new((cx + math.cos(t) * (r + l * 0.3), cy + math.sin(t) * (r + l * 0.3), max(-0.02, (z + l) * hk - 0.02 * (1 - hk)))))
            ring.append(col)
        for i in range(len(prof) - 1):
            face([ring[0][i], ring[1][i], ring[1][i + 1], ring[0][i + 1]], mat)

# ----------------------------------------------------------------------------------------------------------------
if PIECE == "igloo":
    A, B, T = 2.4, 2.75, 0.32          # the inside: 2.4 m radius at the floor, 2.75 m high (the vent's rim lower); walls 0.32
                                       # (an angler stands 1.85 m tall 1.75 m out from the fire, by a hole round it)
    VENT_R = 0.5                       # the vent's inside radius at the top: 1 m across
    GAP = 0.022                        # the joints between blocks (snow packed in them, set back from the faces)
    DOOR_W, DOOR_WALL = 0.65, 1.4      # the tunnel: 1.3 m wide inside, walls 1.4 m then a round arch: 2.05 m high
    phi_v = math.acos(VENT_R / A)
    def prof(phi, off):                # (r, z) on the dome's inside, pushed `off` out along its normal
        r, z = A * math.cos(phi), B * math.sin(phi)
        n = Vector((math.cos(phi) / A, math.sin(phi) / B)).normalized()
        return r + n.x * off, z + n.y * off
    # the profile by arc length, to lay courses of even height
    S = [0.0]; PH = [0.0]; K = 400
    for i in range(1, K + 1):
        p = phi_v * i / K; a, b = prof(PH[-1], 0), prof(p, 0)
        S.append(S[-1] + math.hypot(b[0] - a[0], b[1] - a[1])); PH.append(p)
    def phi_at(s):
        for i in range(1, len(S)):
            if S[i] >= s: return PH[i - 1] + (PH[i] - PH[i - 1]) * (s - S[i - 1]) / max(1e-9, S[i] - S[i - 1])
        return PH[-1]
    COURSES = 8; ch = S[-1] / COURSES
    def s_at_z(z):   # the arc length up the dome's inside at a height
        for i in range(1, len(S)):
            if prof(PH[i], 0)[1] >= z:
                z0_, z1_ = prof(PH[i - 1], 0)[1], prof(PH[i], 0)[1]
                return S[i - 1] + (S[i] - S[i - 1]) * (z - z0_) / max(1e-9, z1_ - z0_)
        return S[-1]
    def in_door(x, y, z, margin=0.0):
        if y < 0.6: return False
        top = DOOR_WALL + math.sqrt(max(0.0, DOOR_W ** 2 - x * x)) if abs(x) < DOOR_W else DOOR_WALL
        return abs(x) < DOOR_W + margin and z < top + margin

    def dome_block(s0, s1, t0, t1, mat, inset, gap, bulge):
        """A block of the dome between arc lengths s0..s1 and angles t0..t1 (its joints `gap` wide), from `inset` in
        from the inside face to `inset` in from the outside face."""
        nu, nv = 4, 3
        ga = gap / max(0.2, prof(phi_at((s0 + s1) / 2), 0)[0])
        us = [t0 + ga / 2 + (t1 - t0 - ga) * i / nu for i in range(nu + 1)]
        vs = [s0 + gap / 2 + (s1 - s0 - gap) * j / nv for j in range(nv + 1)]
        def P(t, s, off):
            r, z = prof(phi_at(s), off); return Vector((r * math.cos(t), r * math.sin(t), z))
        ins = [[bm.verts.new(P(u, v, inset)) for v in vs] for u in us]
        out = [[bm.verts.new(P(u, v, T - inset + bulge)) for v in vs] for u in us]
        g = ("plank", Vector((1, 0, 0)))
        for i in range(nu):
            for j in range(nv):
                face([out[i][j], out[i + 1][j], out[i + 1][j + 1], out[i][j + 1]], mat, g, False)
                face([ins[i][j], ins[i][j + 1], ins[i + 1][j + 1], ins[i + 1][j]], mat, g, False)
        for j in range(nv):
            face([out[0][j], out[0][j + 1], ins[0][j + 1], ins[0][j]], mat, g, False)
            face([out[nu][j], ins[nu][j], ins[nu][j + 1], out[nu][j + 1]], mat, g, False)
        for i in range(nu):
            face([out[i][0], ins[i][0], ins[i + 1][0], out[i + 1][0]], mat, g, False)
            face([out[i][nv], out[i + 1][nv], ins[i + 1][nv], ins[i][nv]], mat, g, False)

    def door_w(z):   # the tunnel's inside half-width at a height (0 above its arch)
        if z < DOOR_WALL: return DOOR_W
        h = z - DOOR_WALL
        return math.sqrt(DOOR_W ** 2 - h * h) if h < DOOR_W else 0.0
    blocks = 0
    for c in range(COURSES):
        s0, s1 = c * ch, (c + 1) * ch
        rm = prof(phi_at((s0 + s1) / 2), T / 2)[0]
        z0 = prof(phi_at(s0), 0)[1]; r0 = prof(phi_at(s0), 0)[0]
        w = door_w(z0)
        if w > 0:
            # a course the door passes through: its blocks laid on the arc from one side of the door round to the other
            ha = math.asin(min(1.0, (w + 0.01) / max(0.3, r0)))
            a0, span = math.pi / 2 + ha, 2 * math.pi - 2 * ha
            n = max(5, round(span * rm / 0.72))
            edges = [a0 + span * j / n for j in range(n + 1)]
        else:
            n = max(6, round(2 * math.pi * rm / 0.72))
            off = (0.5 if c % 2 else 0.0) + rnd.uniform(-0.15, 0.15)
            edges = [2 * math.pi * (j + off) / n for j in range(n + 1)]
        for j in range(n):
            t0, t1 = edges[j], edges[j + 1]
            dome_block(s0, s1, t0, t1, "ice", 0.0, GAP, rnd.uniform(-0.01, 0.025)); blocks += 1
            dome_block(s0, s1, t0, t1, "snow", 0.035, 0.0, 0.0)          # the snow packed in its joints, set back
        if w > 0:
            # a lintel over the tunnel: the door's cut runs the course's full height, but the tunnel's outside arch tops
            # out at DOOR_WALL + DOOR_W + T - above it the cut was an open gap; a block closes it, from a little under
            # the tunnel's top (overlapping it) to the course's top
            z_lin = DOOR_WALL + DOOR_W + T - 0.12
            z1 = prof(phi_at(s1), 0)[1]
            if z1 > z_lin + 0.03:
                s_lin = max(s0, s_at_z(z_lin))
                ga = 2 * math.asin(min(1.0, (w + 0.01) / max(0.3, r0)))
                dome_block(s_lin, s1, math.pi / 2 - ga / 2 - 0.01, math.pi / 2 + ga / 2 + 0.01, "ice", 0.0, GAP, 0.0); blocks += 1
                dome_block(s_lin, s1, math.pi / 2 - ga / 2 - 0.01, math.pi / 2 + ga / 2 + 0.01, "snow", 0.035, 0.0, 0.0)
    # the tunnel: courses of blocks round an arch, rings along +Y from inside the dome's wall out to the door
    def arch(u, off):
        """the tunnel's inside (u 0..1 from the left foot over the top to the right foot), pushed `off` outward"""
        wall, arc = DOOR_WALL, math.pi * DOOR_W; L = 2 * wall + arc; d = u * L
        if d < wall: return Vector((-DOOR_W - off, d))
        if d > wall + arc: return Vector((DOOR_W + off, L - d))
        a = math.pi - (d - wall) / DOOR_W
        return Vector(((DOOR_W + off) * math.cos(a), DOOR_WALL + (DOOR_W + off) * math.sin(a)))
    def y_meet(x, z):   # where a point of the tunnel (x, z) meets the dome's inside, going in along -Y
        rr = A * A * max(0.0, 1 - (min(z, B) / B) ** 2) - x * x
        return math.sqrt(max(0.0, rr))
    RING = 0.42; NB = 11; y_end = 3.6
    for ri in range(6):
        ya, yb = y_end - (ri + 1) * RING, y_end - ri * RING
        off = 0.5 if ri % 2 else 0.0
        for j in range(NB + (1 if off else 0)):
            u0, u1 = max(0.0, (j - off) / NB), min(1.0, (j + 1 - off) / NB)
            if u1 - u0 < 0.02: continue
            for mat, inset, gap in (("ice", 0.0, GAP), ("snow", 0.035, 0.0)):
                nu = 3; us = [u0 + (gap / 4.84) / 2 + (u1 - u0 - gap / 4.84) * i / nu for i in range(nu + 1)]
                # each end of the tunnel's innermost blocks cut to the dome's inside (and a little into its wall)
                starts = [y_meet(*arch(u, 0)) - 0.06 for u in us]
                if all(yb - gap / 2 <= st + 0.05 for st in starts): break
                ins = [[None, None] for _ in us]; out = [[None, None] for _ in us]
                for i, u in enumerate(us):
                    for k, y in enumerate((max(ya + gap / 2, starts[i]), yb - gap / 2)):
                        y = min(y, yb - gap / 2 - 0.05)
                        a, b = arch(u, inset), arch(u, T - inset)
                        ins[i][k] = bm.verts.new((a[0], y, a[1])); out[i][k] = bm.verts.new((b[0], y, b[1]))
                g = ("plank", Vector((0, 1, 0)))
                for i in range(nu):
                    face([out[i][0], out[i][1], out[i + 1][1], out[i + 1][0]], mat, g, False)
                    face([ins[i][0], ins[i + 1][0], ins[i + 1][1], ins[i][1]], mat, g, False)
                    face([out[i][0], out[i + 1][0], ins[i + 1][0], ins[i][0]], mat, g, False)
                    face([out[i][1], ins[i][1], ins[i + 1][1], out[i + 1][1]], mat, g, False)
                for i, flip in ((0, False), (nu, True)):
                    q = [out[i][0], ins[i][0], ins[i][1], out[i][1]]
                    face(q[::-1] if flip else q, mat, g, False)
                if mat == "ice": blocks += 1
    # snow banked round the foot (not across the door) and along the tunnel's sides
    berm(A + T - 0.02, A + T + 0.65, 0.5, "snow", skip=lambda t: abs(math.cos(t)) < 0.45 and math.sin(t) > 0)
    for sx in (-1, 1):
        x0 = sx * (DOOR_W + T - 0.02)
        for k in range(8):
            ya, yb = 1.7 + k * 0.25, 1.7 + (k + 1) * 0.25
            col = []
            for y in (ya, yb):
                env = smooth01((3.7 - y) / 0.6)   # sloping down into the ground at the tunnel's mouth (it ended open there)
                pr = [(0.0, -0.02), (0.0, 0.42), (0.18, 0.46), (0.42, 0.22), (0.6, -0.02)]
                col.append([bm.verts.new((x0 + sx * (dx + 0.03 * lump(y, dx)), y, max(-0.02, (z + 0.05 * lump(dx, y) * (0 < z < 0.4)) * env - 0.02 * (1 - env)))) for dx, z in pr])
            for i in range(4):
                q = [col[0][i], col[1][i], col[1][i + 1], col[0][i + 1]]
                face(q if sx > 0 else q[::-1], "snow")
    # a lip of snow round the vent
    rv, zv = prof(phi_v, T)
    tube([(rv * math.cos(2 * math.pi * k / 40), rv * math.sin(2 * math.pi * k / 40), zv - 0.02 + 0.015 * lump(k, 1)) for k in range(40)],
         [0.07 + 0.02 * lump(k, 2) for k in range(40)], "snow", seg=8, closed=True)
    # (no sleeping bench: the floor kept clear - a hole in the middle, room round it; build a seat if you want one)
    # packed snow round the tunnel where it meets the dome, hiding the seam: a collar following the tunnel's outside
    # arch, set where its outer face meets the dome's outer face
    def y_meet_out(x, z):
        rr = (A + T) ** 2 * max(0.0, 1 - (min(z, B + T) / (B + T)) ** 2) - x * x
        return math.sqrt(max(0.0, rr))
    collar = []
    for k in range(25):
        p = arch(k / 24, T - 0.04)
        collar.append((p[0], y_meet_out(p[0], p[1]) + 0.02 + 0.015 * lump(k, 4), max(-0.02, p[1])))
    tube(collar, [0.17 + 0.03 * lump(k, 5) for k in range(25)], "snow", seg=10)
    print(f"igloo: {blocks} ice blocks, vent {2 * VENT_R:.2f} m across at {B * math.sin(phi_v):.2f} m")

# ----------------------------------------------------------------------------------------------------------------
elif PIECE == "lavvu":
    R, H, NP = 2.8, 5.0, 12            # the poles' foot circle, where they'd meet, how many (5.6 m across: the fire,
                                       # holes round it 1.5 m out with 2.3 m over them, seats either side)
    TOP = H * (1 - 0.52 / R)           # the cover stops here: a smoke hole ~1.05 m across
    def rc(z): return R * (1 - z / H) + 0.05
    poles = [2 * math.pi * (k + 0.5) / NP + math.pi / 2 for k in range(NP)]   # (none dead centre over the door)
    # the two poles either side of the door spread to 25 degrees off it (from 15): leaning in over the doorway, they
    # caught the angler's head and shoulders
    poles[0], poles[-1] = math.pi / 2 + math.radians(25), math.pi / 2 + 2 * math.pi - math.radians(25)
    pole_line = []                     # each pole's foot and its line to where they meet
    for k, a in enumerate(poles):
        foot = Vector((R * math.cos(a), R * math.sin(a), -0.05))
        meet = Vector((0.07 * math.cos(a * 3 + 1), 0.07 * math.sin(a * 2), H - 0.15 + 0.06 * math.sin(k * 1.7)))
        d = meet - foot; tip = foot + d * rnd.uniform(1.12, 1.2); pole_line.append((foot, d))
        bend = Vector((-math.sin(a), math.cos(a), 0)) * 0.03 * math.sin(k * 2.3)
        path = [foot + d * f + bend * math.sin(math.pi * min(1, f)) for f in (0.0, 0.25, 0.5, 0.75, 1.0)] + [tip]
        tube(path, [0.045, 0.042, 0.038, 0.033, 0.03, 0.022], "wood", seg=10)
    # the cover: sewn hides over the poles - straight from pole to pole, sagging a little between them; open at the
    # door (1.2 m wide, walls to 1.95 m and an arched top to 2.25 m: walked through standing) and at the top
    DOOR = math.pi / 2
    def door_half(z):
        w = 0.6 if z < 1.95 else 0.6 * math.sqrt(max(0.0, 1 - ((z - 1.95) / 0.3) ** 2))
        return math.asin(min(1.0, w / rc(z))) if w > 0 else 0.0
    def cover(u, v):
        z = 0.02 + (TOP - 0.02) * v; dh = door_half(z)
        # round from the door's one side to the other; the door's outline only bends the last tenth either side, so the
        # hides' seams elsewhere run straight up (they kinked where the door's top curves in)
        q = 2 * u - 1; t = DOOR + math.pi + q * math.pi - math.copysign(dh * smooth01((abs(q) - 0.8) / 0.2), q)
        # straight from the pole on one side of it to the next (they're not evenly spaced at the door)
        tt = (t - poles[0]) % (2 * math.pi); rel = [p - poles[0] for p in poles] + [2 * math.pi]
        i = max(j for j in range(NP) if rel[j] <= tt); a0, a1 = rel[i], rel[i + 1]
        frac = (tt - a0) / (a1 - a0); half = (a1 - a0) / 2; dt = tt - (a0 + half)
        r = rc(z) * math.cos(half) / math.cos(dt) - 0.04 * (rc(z) / R) * math.sin(math.pi * frac)
        return (r * math.cos(t), r * math.sin(t), z)
    # patchwork: rows of hides (seams on the sheet's cell lines), each row's hides of two kinds, staggered like brickwork
    NU, NV, ROWS = NP * 8, 28, (8, 16, 23)
    PER_ROW = (7, 6, 5, 3)
    def row_of(v): return sum(v * NV > r for r in ROWS)
    def cuts(row):   # the hides' edges round a row, on cell lines
        n = PER_ROW[row]; off = (0.37 * row) % 1.0
        return sorted({round(((k + off) / n % 1.0) * NU) / NU for k in range(n)})
    def hide_of(u, v):
        row = row_of(v); cs = cuts(row); k = sum(u > c for c in cs)
        return "hide2" if random.Random(row * 31 + k % len(cs)).random() < 0.45 else "hide"
    # each hide its own piece: a row laps down over the row below (like shingles, shedding snow), and every other hide
    # in a row laps over its neighbours; stitched along each lap (patchwork)
    vb = [0.0] + [r / NV for r in ROWS] + [1.0]; panels = []
    for row in range(len(PER_ROW)):
        ub = [0.0] + [c for c in cuts(row) if 0.01 < c < 0.99] + [1.0]
        for k in range(len(ub) - 1):
            laps = {"v0": 2} if row > 0 else {}
            if k % 2: laps.update({"u0": 1, "u1": 1} if k < len(ub) - 2 else {"u0": 1})
            panels.append((ub[k], ub[k + 1], vb[row], vb[row + 1], hide_of((ub[k] + ub[k + 1]) / 2, (vb[row] + vb[row + 1]) / 2), laps))
    patchwork(cover, lambda p: Vector((p.x, p.y, 0.3)), NU, NV, panels)
    def on_cover(u, v, out=0.006):
        c = Vector(cover(u, v)); return c + Vector((c.x, c.y, 0)).normalized() * out
    z = 1.85
    while z < TOP - 0.15:
        c = Vector(cover(0.0, (z - 0.02) / (TOP - 0.02))); o = Vector((c.x, c.y, 0)).normalized()
        across = Vector((-o.y, o.x, 0))
        tube([c + o * 0.02 - across * 0.09, c + o * 0.03 + across * 0.09], [0.011, 0.009], "wood", seg=6)
        z += 0.24
    # the door flap rolled up over the door and tied
    c = Vector(cover(0.0, (2.27 - 0.02) / (TOP - 0.02))); o = Vector((c.x, c.y, 0)).normalized(); across = Vector((-o.y, o.x, 0))
    tube([c + o * 0.09 - across * 0.62, c + o * 0.1, c + o * 0.09 + across * 0.62], [0.085, 0.095, 0.085], "hide", seg=12)
    for s in (-0.4, 0.4):
        tube([c + o * 0.09 + across * s + Vector((0, 0, 0.1)), c + o * 0.2 + across * s, c + o * 0.09 + across * s - Vector((0, 0, 0.1))], [0.012] * 3, "leather", seg=5)
    # pegs at the foot of the cover between the poles
    for k in range(NP):
        a = poles[k] + math.pi / NP
        if abs(math.atan2(math.sin(a - DOOR), math.cos(a - DOOR))) < 0.4: continue
        p = Vector(((R + 0.12) * math.cos(a), (R + 0.12) * math.sin(a), 0))
        tube([p - Vector((0, 0, 0.1)), p + Vector((0, 0, 0.12))], [0.02, 0.016], "wood", seg=6)
        tube([p + Vector((0, 0, 0.08)), Vector(((R + 0.03) * math.cos(a), (R + 0.03) * math.sin(a), 0.1))], [0.007, 0.007], "leather", seg=5)
    # a cross pole high over the middle, lashed to two poles
    # resting on the inside of the two poles it's lashed to, its ends stopping at the poles (inside the cover)
    zc = 2.6
    def at_z(k):
        foot, d = pole_line[k]; return foot + d * ((zc - foot.z) / d.z)
    PA, PB = at_z(2), at_z(2 + NP // 2); ax_ = (PB - PA).normalized()
    A_, B_ = PA + ax_ * 0.065, PB - ax_ * 0.065
    tube([A_ - ax_ * 0.06, B_ + ax_ * 0.06], [0.035, 0.035], "bark", seg=10)
    for P_ in (A_, B_):   # lashed to the poles
        tube([P_ + Vector((0, 0, -0.05)), P_ + Vector((0, 0, 0.05))], [0.05, 0.05], "leather", seg=10, caps=False)
    # (no pot hook and chain: no fire, and it hung where you stand to fish the middle)
    # hide rugs either side under the low cover (no log seats, no fire: the middle of the floor clear for a hole)
    for sx in (-1, 1):
        for k, (cy, rot) in enumerate(((-0.55, 0.2), (0.5, -0.15))):
            cx = sx * 1.75
            pts = []
            for j in range(18):
                t = 2 * math.pi * j / 18; rr = 0.42 + 0.07 * math.sin(t * 3 + k) + 0.04 * math.sin(t * 5)
                pts.append((cx + rr * 0.75 * math.cos(t + rot), cy + rr * math.sin(t + rot)))
            c = bm.verts.new((cx, cy, 0.035)); vs = [bm.verts.new((x, y, 0.02)) for x, y in pts]
            for j in range(18): face([c, vs[j], vs[(j + 1) % 18]], "fur")
    berm(R + 0.12, R + 0.65, 0.35, "snow", skip=lambda t: abs(math.atan2(math.sin(t - DOOR), math.cos(t - DOOR))) < 0.32)

# ----------------------------------------------------------------------------------------------------------------
elif PIECE == "ship_tent":
    W, HR, L = 2.3, 3.3, 3.2           # half-width at the ground, the ridge's height, half the length (door at +Y):
                                       # the fire towards the back under the vent (VC), so there's room past it: the
                                       # front half clear from the door for walking and holes, 1.9 m+ over them
    BW, BT = 0.2, 0.065                # the gable boards: width, thickness
    VENT_Y, VENT_X = 0.58, 0.36        # the gap in the ridge for the smoke: |y - VC| < VENT_Y, x within VENT_X of the ridge
    def roof_z(x): return HR * (1 - abs(x) / W)
    # the gable frames: two boards crossing at the ridge, their ends cut just past the crossing - Valheim's own carved
    # dragon head (the Dragon Head piece's) sits on each crossing in game, looking out (IceShelters.AddDragonHeads)
    for gy in (-L - 0.02, L + 0.02):
        out = 1 if gy > 0 else -1
        for sx in (-1, 1):
            foot = Vector((-sx * (W + 0.06), gy, -0.08)); cross = Vector((0, gy, HR + 0.04))
            d = (cross - foot).normalized(); end = cross + d * 0.33   # (runs up into the collar, under the dragon head's neck)
            tube([foot, cross, end], [BW / 2] * 3, "wood", seg=4, flat=[BT / BW] * 3, side=(0, 1, 0), smooth=False)
            # an iron collar over the board's end, the head's neck socketed into it (its tipped base wholly inside, from
            # 0.27 to 0.40 along: IceShelters.AddDragonHeads), pegged through; it starts 0.25 out, clear of the other
            # board. A red painted band below the crossing.
            tube([cross + d * 0.25, cross + d * 0.40], [0.125, 0.125], "iron", seg=16, flat=[0.8, 0.8], side=(0, 1, 0))
            for f in (0.29, 0.36):
                tube([cross + d * f, cross + d * f + Vector((0, 0.13, 0))], [0.016, 0.02], "iron", seg=6)
                tube([cross + d * f, cross + d * f - Vector((0, 0.13, 0))], [0.016, 0.02], "iron", seg=6)
            tube([cross - d * 0.25, cross - d * 0.18], [BW / 2 + 0.004] * 2, "red", seg=4, flat=[(BT + 0.008) / (BW + 0.008)] * 2, side=(0, 1, 0), smooth=False, caps=False)
        # an iron strap and nails over the crossing, where the head is pegged on
        box((0, gy + out * 0.045, HR + 0.04), (0.16, 0.012, 0.22), "iron")
        for dz in (-0.07, 0.07):
            tube([Vector((0, gy + out * 0.05, HR + 0.04 + dz)), Vector((0, gy + out * 0.075, HR + 0.04 + dz))], [0.014, 0.01], "iron", seg=6)
    # the ridge pole in the crotches, and a middle rafter pair under the cover
    tube([(0, -L - 0.15, HR - 0.07), (0, 0, HR - 0.09), (0, L + 0.15, HR - 0.07)], [0.06, 0.06, 0.06], "wood", seg=12)
    # the cover: hides over the ridge to the ground each side, sagging a little between the gables; a gap at the ridge
    # in the middle for the smoke
    def cside(sx):
        def P(u, v):
            x = sx * W * u; y = -L + 2 * L * v
            sag = 0.07 * (1 - (y / L) ** 2) * (1 - u) + 0.04 * math.sin(math.pi * u) * (1 - (y / L) ** 2)
            return (x, y, roof_z(x) - sag + 0.01 * (u < 0.02))
        return P
    NU, NV, STRIPS, LOW = 22, 30, (0, 4, 9, 13, 17, 22, 26, 30), 12   # hides' edges on the sheet's cell lines
    VSHIFT = 7; VC = -VSHIFT * 2 * L / NV   # the vent (and the fire under it, IceShelters ShipTent FireAt) 7 cells (1.49 m) back
    def strip_of(v): return sum(v * NV > b for b in STRIPS[1:-1])
    # each hide its own piece (patchwork): the upper hides lap down over the lower ones (shedding snow), every other
    # strip laps over its neighbours; stitched along each lap
    for sx in (-1, 1):
        hide_of = lambda u, v, sx=sx: "hide2" if (strip_of(v) + (u * NU >= LOW) + (sx > 0)) % 2 else "hide"
        panels = []
        for k in range(len(STRIPS) - 1):
            v0, v1 = STRIPS[k] / NV, STRIPS[k + 1] / NV
            side = {"v0": 1} if k > 0 else {}
            if k < len(STRIPS) - 2: side["v1"] = 1
            side = side if k % 2 else {}
            for u0, u1, laps in ((0.0, LOW / NU, {"u1": 2}), (LOW / NU, 1.0, {})):
                panels.append((u0, u1, v0, v1, hide_of((u0 + u1) / 2, (v0 + v1) / 2), {**laps, **side}))
        patchwork(cside(sx), lambda p, sx=sx: Vector((sx, 0, 1)), NU, NV, panels,
                  keep=lambda u, v: not (u * W < VENT_X and abs(-L + 2 * L * v - VC) < VENT_Y))
    # a timber frame round the smoke gap, lying on the cover over its cut edges: rails down each side of the gap and
    # across the ridge at each end of it, the smoke hood's posts standing on them
    VU = 3 / NU; VV0, VV1 = (12 - VSHIFT) / NV, (18 - VSHIFT) / NV   # the gap's cut edges (cell lines): u < VU, v in VV0..VV1
    RR = 0.045
    def on_roof(sx, u, v, up=RR):
        p = Vector(cside(sx)(u, v)); n = Vector((sx * HR / W, 0, 1)).normalized() if u > 1e-3 else Vector((0, 0, 1))
        return p + n * (up + 0.01)
    for sx in (-1, 1):
        tube([on_roof(sx, VU + 0.008, VV0 - 0.012 + (VV1 - VV0 + 0.024) * f / 6) for f in range(7)], [RR] * 7, "wood", seg=8)
    for vv in (VV0 - 0.006, VV1 + 0.006):
        pts = [on_roof(-1, VU + 0.03 - (VU + 0.03) * f / 4, vv) for f in range(5)] + [on_roof(1, (VU + 0.03) * f / 4, vv) for f in range(1, 5)]
        pts[4] = pts[4] + Vector((0, 0, 0.01))
        tube(pts, [RR] * len(pts), "wood", seg=8)
        for sx in (-1, 1):   # pegged at the corners
            c = on_roof(sx, VU + 0.008, vv)
            tube([c, c + Vector((sx * 0.03, 0, 0.05))], [0.014, 0.012], "wood", seg=6)
    # Elaking hair along the ridge either side of the vent
    for ys in ((-L, VC - VENT_Y - 0.02), (VC + VENT_Y + 0.02, L)):
        n = 10; pts = [(0, ys[0] + (ys[1] - ys[0]) * i / n, HR + 0.005 - 0.07 * (1 - ((ys[0] + (ys[1] - ys[0]) * i / n) / L) ** 2)) for i in range(n + 1)]
        tube(pts, [0.09] * len(pts), "fur", seg=10, flat=[0.4] * len(pts), side=(0, 0, 1))
    # the smoke hood: a small hide roof on short posts over the gap, open at its sides
    HH, HW, HL = HR + 0.42, 0.78, VENT_Y + 0.18
    for sx in (-1, 1):
        sheet(lambda u, v, sx=sx: (sx * HW * u, VC - HL + 2 * HL * v, HH - 0.42 * u - 0.03 * (1 - ((-HL + 2 * HL * v) / HL) ** 2)), 6, 8, "hide", 0.012)
        for yy in (VC - VENT_Y + 0.05, VC + VENT_Y - 0.05):   # the posts, standing on the frame's side rails
            foot = on_roof(sx, VU + 0.008, (yy + L) / (2 * L), up=RR * 0.6)
            tube([foot, (sx * 0.5, yy, HH - 0.42 * 0.5 / HW - 0.02)], [0.027, 0.022], "wood", seg=6)
    tube([(0, VC - HL - 0.05, HH + 0.02), (0, VC + HL + 0.05, HH + 0.02)], [0.035, 0.035], "wood", seg=8)
    # the gables: the back closed with a hide panel, the front round the door; both up to the ridge (the smoke goes out
    # the vent in the roof)
    GT = HR - 0.01
    def gP(u, v, gy=-L + 0.03):
        z = GT * v; half = W * (1 - z / HR); return (-half + 2 * half * u, gy, z)
    patchwork(gP, lambda p: Vector((0, -1, 0)), 20, 14, [(0.0, 1.0, 0.0, 8 / 14, "hide", {}), (0.0, 1.0, 8 / 14, 1.0, "hide2", {"v0": 1})])
    def dw(z): return 0.62 if z < 1.9 else max(0.0, 0.62 * (1 - (z - 1.9) / 0.55))   # the door: 1.24 m wide, walls to 1.9 m, a point at 2.45 m
    for sx in (-1, 1):
        def fP(u, v, sx=sx):
            z = GT * v; half = W * (1 - z / HR); a, b = half, dw(z)
            x = a + (b - a) * u
            return (sx * x, L - 0.03, z)
        sheet(fP, 8, 14, "hide", 0.012)
    # the door flaps rolled up at the sides and tied to the boards
    for sx in (-1, 1):
        x = sx * 0.78
        tube([(x, L + 0.04, 0.15), (x, L + 0.06, 1.0), (x * 0.9, L + 0.04, 1.75)], [0.08, 0.09, 0.07], "hide", seg=10)
        for z in (0.6, 1.4):
            tube([(x - 0.1, L + 0.05, z), (x, L + 0.16, z), (x + 0.1, L + 0.05, z)], [0.011] * 3, "leather", seg=5)
    # stakes along the foot each side, tied to the cover's edge; guy ropes from each crossing out to a stake
    for sx in (-1, 1):
        for k in range(10):
            y = -L + 0.25 + k * (2 * L - 0.5) / 9
            p = Vector((sx * (W + 0.18), y, 0))
            tube([p - Vector((0, 0, 0.1)), p + Vector((0, 0, 0.14))], [0.022, 0.018], "wood", seg=6)
            tube([p + Vector((0, 0, 0.1)), Vector((sx * (W - 0.02), y, 0.06))], [0.007, 0.007], "linen", seg=5)
    for gy in (-1, 1):
        top = Vector((0, gy * (L + 0.05), HR + 0.1)); st = Vector((0, gy * (L + 1.5), 0))
        tube([top + (st - top) * f + Vector((0, 0, -0.08 * math.sin(math.pi * f))) for f in (0, 0.25, 0.5, 0.75, 1)], [0.009] * 5, "linen", seg=5)
        tube([st - Vector((0, 0, 0.1)), st + Vector((0, 0, 0.18))], [0.03, 0.024], "wood", seg=6)
    # hide rugs on the floor (no chest: the user didn't want one modelled)
    for sx in (-1, 1):
        cx, cy = sx * 1.4, 0.0; pts = []
        for j in range(18):
            t = 2 * math.pi * j / 18; rr = 0.5 + 0.08 * math.sin(t * 3 + sx) + 0.05 * math.sin(t * 5)
            pts.append((cx + rr * 0.7 * math.cos(t), cy + rr * 1.3 * math.sin(t)))
        c = bm.verts.new((cx, cy, 0.035)); vs = [bm.verts.new((x, y, 0.02)) for x, y in pts]
        for j in range(18): face([c, vs[j], vs[(j + 1) % 18]], "fur")
    # snow along the foot of both sides and the back
    for sx in (-1, 1):
        for k in range(32):
            ya, yb = -L - 0.1 + k * (2 * L + 0.2) / 32, -L - 0.1 + (k + 1) * (2 * L + 0.2) / 32
            col = []
            for y in (ya, yb):
                env = smooth01((L + 0.1 - abs(y)) / 1.0)   # sloping down into the ground over the last metre at each end
                pr = [(0.0, -0.02), (0.06, 0.3), (0.28, 0.33), (0.52, 0.14), (0.75, -0.02)]
                col.append([bm.verts.new((sx * (W + dx * max(0.3, env) + 0.04 * lump(y, dx)), y, max(-0.02, (z + 0.06 * lump(dx * 3, y) * (0 < z < 0.34)) * env))) for dx, z in pr])
            for i in range(4):
                q = [col[0][i], col[1][i], col[1][i + 1], col[0][i + 1]]
                face(q if sx > 0 else q[::-1], "snow")
else:
    raise SystemExit("unknown VDW_PIECE " + PIECE)

me = bpy.data.meshes.new("bait")
grain_of = {f.index: GRAIN[f] for f in bm.faces if f in GRAIN}
# every part's faces outward (the berms, banks and tunnel blocks were built inside out: unseen in Blender, which
# draws both sides, but culled in game)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
bm.normal_update()
bm.to_mesh(me); bm.free()
for m in MATS: me.materials.append(bpy.data.materials.new(m))
g = me.uv_layers.new(name="Grain")
for p in me.polygons:
    kind = grain_of.get(p.index, ("plank", Vector((1, 0, 0))))
    for li in p.loop_indices:
        c = me.vertices[me.loops[li].vertex_index].co
        if kind[0] == "axis":
            o, d = kind[1], kind[2]; rel = c - o; along = rel.dot(d); a, b = frame(d)
            g.data[li].uv = (along, math.atan2(rel.dot(b), rel.dot(a)) * 0.03)
        else:
            d = kind[1]; side = Vector((-d.y, d.x, 0)) if abs(d.z) < 0.5 else Vector((1, 0, 0))
            g.data[li].uv = (c.dot(d), c.dot(side) + c.z * 0.3)
uv = me.uv_layers.new(name="UVMap"); me.uv_layers.active = uv; uv.active_render = True
ob = bpy.data.objects.new("bait", me); bpy.context.scene.collection.objects.link(ob)
bpy.context.view_layer.objects.active = ob; ob.select_set(True)
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.remove_doubles(threshold=0.0001)
bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.002, scale_to_bounds=False)
bpy.ops.object.mode_set(mode='OBJECT')
used = sorted({p.material_index for p in me.polygons})
print(f"BUILT {PIECE}: {len(me.polygons)} faces, {len(me.vertices)} verts, materials {[MATS[i] for i in used]}, "
      f"{ob.dimensions.x:.2f} x {ob.dimensions.y:.2f} x {ob.dimensions.z:.2f} m")
bpy.ops.wm.save_as_mainfile(filepath=DEST)
print("SAVED", DEST)
