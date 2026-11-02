# Builds a wooden tackle box in the style of the wooden ice chest (build_wood_cooler.py), smaller and made to carry:
# square corner posts standing a little proud as feet, plank panels between them with small gaps, a planked lid with
# iron corner caps, iron brackets on the posts, two hinges at the back, a hasp latch at the front and one carry handle
# on top (iron uprights and a wooden grip; the mod hangs the box from its highest point in the hand). Inside, a
# lift-out tray of tackle compartments sits on ledges above a deep well. No side handles, drain or bottle opener.
# Rigged like the other boxes (TackleBoxes.cs / LidDriver): "root" (the body) and "lid" (head on the hinge along the
# back top edge, pointing forward across the lid). Standing on the origin, the back toward +Y.
# Materials: wood (the box), tray (the tray and its dividers, lighter), iron. UV layers "UVMap" (packed, for baking) and
# "Grain" (metres, the long way of each part along U, for the procedural wood) - as the cooler.
#   blender -b --factory-startup --python build_wood_tacklebox.py
#   env: VDW_OUT (new .blend, never overwrites), VDW_WIDTH (0.44: the box's length, metres),
#        VDW_STYLE: flush (default) - no corner posts or feet: flush boards meeting in box-jointed corners (the boards
#        overlap turn and turn about up each corner), thin iron strips round the bottom and the rim, and a tall arched
#        iron carrying handle with a wooden grip, so it reads apart from the cooler; posts - the first version (posts and
#        feet like the cooler, a low handle); VDW_HILDIR: swamp | mountain | mistlands - Hildir's lost boxes (her mark,
#        and moss / ice / dvergr bands with eitr rivets); ashlands - glowing embers caught in it
import bpy, bmesh, math, os
from mathutils import Vector, Matrix

OUT = os.environ["VDW_OUT"]
if os.path.exists(OUT): raise SystemExit("exists, kept: " + OUT)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
S = float(os.environ.get("VDW_WIDTH", "0.44")) / 0.44          # everything below is for 0.44 m long
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
for m in list(bpy.data.meshes): bpy.data.meshes.remove(m)

W, D = 0.44, 0.22            # length (x), depth (y)
ZB = 0.175                   # top of the body
LID0, LID1 = 0.177, 0.207    # the lid
P = 0.032                    # corner post section
BT = 0.012                   # board thickness
STYLE = os.environ.get("VDW_STYLE", "flush")
REC = 0.007 if STYLE == "posts" else 0.0   # how far the panels sit back from the posts' faces (flush: no posts)
RAIL_OUT = 0.003 if STYLE == "posts" else 0.0
MATS = ["wood", "tray", "iron"]
parts = []

def add(bm, mat, bone="root", bevel=0.0):
    parts.append((bm, mat, bone, bevel))

def box(c, size, mat, bone="root", bevel=0.0015):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.transform(bm, matrix=Matrix.Translation(Vector(c)) @ Matrix.Diagonal((*size, 1.0)), verts=bm.verts)
    add(bm, mat, bone, bevel)

def cyl(a, b, r, mat, bone="root", seg=12):
    a, b = Vector(a), Vector(b); d = b - a
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=d.length)
    q = Vector((0, 0, 1)).rotation_difference(d.normalized())
    bmesh.ops.transform(bm, matrix=Matrix.Translation((a + b) / 2) @ q.to_matrix().to_4x4(), verts=bm.verts)
    add(bm, mat, bone, 0.0)

def torus(c, R, r, axis, mat, bone="root", seg=10, rseg=6):
    bm = bmesh.new(); rings = []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        rings.append([bm.verts.new(((R + r * math.cos(b)) * math.cos(a), (R + r * math.cos(b)) * math.sin(a), r * math.sin(b)))
                      for b in (2 * math.pi * j / rseg for j in range(rseg))])
    for i in range(seg):
        for j in range(rseg):
            bm.faces.new((rings[i][j], rings[(i + 1) % seg][j], rings[(i + 1) % seg][(j + 1) % rseg], rings[i][(j + 1) % rseg]))
    q = Vector((0, 0, 1)).rotation_difference(Vector(axis).normalized())
    bmesh.ops.transform(bm, matrix=Matrix.Translation(Vector(c)) @ q.to_matrix().to_4x4(), verts=bm.verts)
    add(bm, mat, bone, 0.0)

def rivet(c, normal, bone="root"):
    n = Vector(normal).normalized(); c = Vector(c)
    cyl(c - n * 0.001, c + n * 0.0025, 0.0028, "iron", bone, seg=8)

# ---------------------------------------------------------------- the body
if STYLE == "posts":   # posts and plank panels, like the cooler
    for x in (-W / 2 + P / 2, W / 2 - P / 2):
        for y in (-D / 2 + P / 2, D / 2 - P / 2): box((x, y, ZB / 2), (P, P, ZB), "wood", bevel=0.003)
    ROWS = [(0.020, 0.046, 0.004), (0.047, 0.110, 0.0), (0.111, 0.150, 0.0), (0.151, ZB, 0.003)]   # skirt, 2 boards, top rail
    inner_x, inner_y = W - 2 * P + 0.014, D - 2 * P + 0.014
    for side in (-1, 1):
        for z0, z1, out in ROWS:
            box((0, side * (D / 2 - REC - BT / 2 + out), (z0 + z1) / 2), (inner_x, BT, z1 - z0), "wood", bevel=0.002)
            box((side * (W / 2 - REC - BT / 2 + out), 0, (z0 + z1) / 2), (BT, inner_y, z1 - z0), "wood", bevel=0.002)
    box((0, 0, 0.026), (W - 0.03, D - 0.03, 0.010), "wood", bevel=0.0)          # the floor of the well
else:                  # flush boards, box-jointed: each course of boards overlaps the next at the corners in turn
    NROW = 6; gapz = 0.0012; hz = (ZB - (NROW - 1) * gapz) / NROW
    for i in range(NROW):
        z0 = i * (hz + gapz); zc = z0 + hz / 2
        long_full = i % 2 == 0          # this course: front/back run the full length (sides tuck in), next course the other way
        lx = W if long_full else W - 2 * BT
        ly = D - 2 * BT if long_full else D
        for side in (-1, 1):
            box((0, side * (D / 2 - BT / 2), zc), (lx, BT, hz), "wood", bevel=0.0015)
            box((side * (W / 2 - BT / 2), 0, zc), (BT, ly, hz), "wood", bevel=0.0015)
    box((0, 0, 0.009), (W - 2 * BT + 0.002, D - 2 * BT + 0.002, 0.012), "wood", bevel=0.0)   # the floor
    # thin iron strips round the bottom and the rim (the corners' joints left showing between them)
    TS, HS = 0.0025, 0.013
    for z in (HS / 2, ZB - HS / 2):
        for side in (-1, 1):
            box((0, side * (D / 2 + TS / 2), z), (W + 2 * TS, TS, HS), "iron", "root", 0.0006)
            box((side * (W / 2 + TS / 2), 0, z), (TS, D, HS), "iron", "root", 0.0006)
            for x in (-0.17, -0.06, 0.06, 0.17): rivet((x, side * (D / 2 + TS), z), (0, side, 0))
            for y in (-0.06, 0.06): rivet((side * (W / 2 + TS), y, z), (side, 0, 0))

# ---------------------------------------------------------------- inside: ledges and a lift-out tray of compartments
IN_X, IN_Y = W / 2 - REC - BT, D / 2 - REC - BT        # inner faces of the walls
TZ = 0.112                                             # the tray's underside (the well below it)
for sx in (-1, 1):                                     # ledges along the ends, the tray rests on them
    box((sx * (IN_X - 0.005), 0, TZ - 0.004), (0.010, 2 * IN_Y - 0.004, 0.008), "tray", bevel=0.0)
TX, TY = IN_X - 0.003, IN_Y - 0.003                    # the tray, a whisker inside the walls
TT, TH = 0.004, 0.048                                  # wall thickness, height
box((0, 0, TZ + TT / 2), (2 * TX, 2 * TY, TT), "tray", bevel=0.0)          # its floor
for s in (-1, 1):
    box((0, s * (TY - TT / 2), TZ + TH / 2), (2 * TX, TT, TH), "tray", bevel=0.001)   # its long sides
    box((s * (TX - TT / 2), 0, TZ + TH / 2), (TT, 2 * TY - 2 * TT, TH), "tray", bevel=0.001)   # its ends
DH = TH - 0.008                                        # dividers a little lower than the sides
box((0, 0.012, TZ + DH / 2), (2 * TX - 2 * TT, TT, DH), "tray", bevel=0.0)    # the long divider: a narrow back row
for x in (-0.12, -0.06, 0.0, 0.06, 0.12):              # front row: six small slots for hooks and lures
    box((x, (0.012 - TY) / 2, TZ + DH / 2), (TT, TY - 0.012 - TT, DH), "tray", bevel=0.0)
for x in (-0.07, 0.07):                                # back row: three long slots for floats and line
    box((x, (0.012 + TY) / 2, TZ + DH / 2), (TT, TY - 0.012 - TT, DH), "tray", bevel=0.0)
# finger holes to lift the tray out: two wooden pulls on the long divider
for x in (-0.03, 0.03): cyl((x, 0.006, TZ + DH + 0.004), (x, 0.018, TZ + DH + 0.004), 0.004, "tray", seg=8)

# ---------------------------------------------------------------- the lid: three planks across, with gaps
OV = 0.006; LW, LD = W + 2 * OV, D + 2 * OV; n = 3; gap = 0.0025
pw = (LD - (n - 1) * gap) / n
for i in range(n):
    y0 = -LD / 2 + i * (pw + gap)
    box((0, y0 + pw / 2, (LID0 + LID1) / 2), (LW, pw, LID1 - LID0), "wood", "lid", bevel=0.003)
box((0, 0, LID0 - 0.003), (W - 2 * P - 0.004, D - 2 * P - 0.004, 0.006), "wood", "lid", bevel=0.0)   # batten underneath, holding the planks

# ---------------------------------------------------------------- iron: lid corner caps, post brackets
T = 0.003; CAP = 0.045
for sx in (-1, 1):
    for sy in (-1, 1):
        cx, cy = sx * (LW / 2 - CAP / 2 + 0.001), sy * (LD / 2 - CAP / 2 + 0.001)
        zc = (LID0 + LID1) / 2; h = LID1 - LID0 + 0.003
        box((cx, sy * (LD / 2 + T / 2), zc), (CAP, T, h), "iron", "lid", 0.0008)
        box((sx * (LW / 2 + T / 2), cy, zc), (T, CAP, h), "iron", "lid", 0.0008)
        box((cx, cy, LID1 + T / 2), (CAP, CAP, T), "iron", "lid", 0.0008)
        rivet((cx + sx * 0.008, sy * (LD / 2 + T), zc), (0, sy, 0), "lid")
        rivet((sx * (LW / 2 + T), cy + sy * 0.008, zc), (sx, 0, 0), "lid")
        rivet((cx + sx * 0.008, cy + sy * 0.008, LID1 + T), (0, 0, 1), "lid")
        for z0, z1 in (((0.140, 0.162), (0.024, 0.044)) if STYLE == "posts" else ()):   # brackets on the posts
            zc = (z0 + z1) / 2; h = z1 - z0
            box((sx * (W / 2 - P / 2), sy * (D / 2 + T / 2 + 0.0005), zc), (P, T, h), "iron", "root", 0.0008)
            box((sx * (W / 2 + T / 2 + 0.0005), sy * (D / 2 - P / 2), zc), (T, P, h), "iron", "root", 0.0008)
            rivet((sx * (W / 2 - 0.016), sy * (D / 2 + T + 0.0005), zc), (0, sy, 0))
            rivet((sx * (W / 2 + T + 0.0005), sy * (D / 2 - 0.016), zc), (sx, 0, 0))

# ---------------------------------------------------------------- hinges at the back
OUTF = 0.0 if STYLE == "posts" else 0.0025      # flush: the rim's iron strip stands this proud of the boards
HY = D / 2 + 0.004 + OUTF
for x in (-0.12, 0.12):
    box((x, LD / 2 - 0.025, LID1 + T / 2), (0.036, 0.05, T), "iron", "lid", 0.0008)
    box((x, LD / 2 + T / 2, LID0 + 0.008), (0.036, T, 0.02), "iron", "lid", 0.0008)
    box((x, D / 2 - REC + RAIL_OUT + OUTF + T / 2, 0.160), (0.036, T, 0.034), "iron", "root", 0.0008)
    cyl((x - 0.018, HY, LID0 - 0.001), (x + 0.018, HY, LID0 - 0.001), 0.0045, "iron", "root")
    for dx in (-0.009, 0.009): rivet((x + dx, LD / 2 - 0.035, LID1 + T), (0, 0, 1), "lid")

# ---------------------------------------------------------------- the hasp latch (front, middle)
RAIL = -(D / 2 - REC + RAIL_OUT + OUTF)
box((0, -LD / 2 - T / 2, LID0 + 0.014), (0.042, T, 0.028), "iron", "lid", 0.0008)
box((0, RAIL - 0.002 - T / 2, 0.158), (0.024, T, 0.046), "iron", "lid", 0.0008)
box((0, (-LD / 2 + RAIL - 0.002) / 2, LID0 - 0.002), (0.024, -LD / 2 - RAIL + 0.002 + T, T), "iron", "lid", 0.0008)
cyl((-0.012, -LD / 2 - 0.003, LID0 + 0.004), (0.012, -LD / 2 - 0.003, LID0 + 0.004), 0.0035, "iron", "lid")
box((0, -(D / 2 - REC) - T / 2, 0.128), (0.034, T, 0.022), "iron", "root", 0.0008)   # (flush: on the boards, below the rim strip)
torus((0, RAIL - 0.003, 0.143), 0.0065, 0.002, (1, 0, 0), "iron")
for dx in (-0.013, 0.013): rivet((dx, -LD / 2 - T, LID0 + 0.014), (0, -1, 0), "lid")

# ---------------------------------------------------------------- the carry handle on top
if STYLE == "posts":   # iron uprights and a wooden grip, low
    GZ = LID1 + T + 0.038
    for sx in (-1, 1):
        x = sx * 0.075
        box((x, 0, LID1 + T / 2), (0.03, 0.04, T), "iron", "lid", 0.0008)
        cyl((x, 0, LID1 + T), (x, 0, GZ + 0.004), 0.0045, "iron", "lid", seg=10)
        cyl((x - sx * 0.002, 0, GZ), (x + sx * 0.006, 0, GZ), 0.008, "iron", "lid", seg=10)
        for dy in (-0.012, 0.012): rivet((x, dy, LID1 + T), (0, 0, 1), "lid")
    cyl((-0.072, 0, GZ), (0.072, 0, GZ), 0.010, "tray", "lid", seg=12)
else:                  # a tall arched iron handle (a toolbox's), its ends in lugs on the lid, a wooden grip on top
    HX, R, GZ = 0.105, 0.028, LID1 + T + float(os.environ.get("VDW_HANDLE_H", "0.065"))   # half-width, corner radius, the top's height
    for sx in (-1, 1):
        x = sx * HX
        box((x, 0, LID1 + T / 2), (0.034, 0.03, T), "iron", "lid", 0.0008)                       # lug plate
        box((x, 0, LID1 + T + 0.011), (0.006, 0.022, 0.022), "iron", "lid", 0.0008)              # the lug standing up
        torus((x, 0, LID1 + T + 0.014), 0.0065, 0.0022, (1, 0, 0), "iron", "lid", seg=10, rseg=6)   # the eye the rod turns in
        for dx in (-0.011, 0.011): rivet((x + dx, 0, LID1 + T), (0, 0, 1), "lid")
        # the rod: up the side, round the corner, along the top
        cyl((x, 0, LID1 + T + 0.014), (x, 0, GZ - R), 0.0055, "iron", "lid", seg=10)
        pts = [(x - sx * R * (1 - math.cos(a)), 0, GZ - R + R * math.sin(a)) for a in (math.pi / 2 * k / 6 for k in range(7))]
        for a, b in zip(pts, pts[1:]): cyl(a, b, 0.0055, "iron", "lid", seg=10)
        cyl((x - sx * R, 0, GZ), (sx * 0.06, 0, GZ), 0.0055, "iron", "lid", seg=10)
    cyl((-0.062, 0, GZ), (0.062, 0, GZ), 0.012, "tray", "lid", seg=14)                           # the wooden grip

# ---------------------------------------------------------------- Hildir's lost boxes (VDW_HILDIR=swamp|mountain|mistlands)
# her red painted mark on the front, and what each picked up where it was lost: moss and bog slime (Sunken Crypts),
# ice and icicles (Frost Caves), dvergr iron bands with glowing eitr rivets (the Mistlands ruins). Extra materials:
# mark, moss, ice, eitr.
HILDIR = os.environ.get("VDW_HILDIR", "")
def blob(c, r, mat, bone="root", squash=0.4, seed=0, seg=8, rings=5):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=r)
    rr = __import__("random").Random(seed)
    for v in bm.verts: v.co *= 1 + rr.uniform(-0.25, 0.25)
    bmesh.ops.transform(bm, matrix=Matrix.Translation(Vector(c)) @ Matrix.Diagonal((1.0, 1.0, squash, 1.0)), verts=bm.verts)
    add(bm, mat, bone, 0.0)
def spike(base, tip, r, mat, bone="root", seg=6):
    a, b = Vector(base), Vector(tip); d = b - a
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=0.0, depth=d.length)
    q = Vector((0, 0, 1)).rotation_difference(d.normalized())
    bmesh.ops.transform(bm, matrix=Matrix.Translation((a + b) / 2) @ q.to_matrix().to_4x4(), verts=bm.verts)
    add(bm, mat, bone, 0.0)
if HILDIR:
    import random
    rnd = random.Random({"swamp": 3, "mountain": 5, "mistlands": 7}.get(HILDIR, 1))
    mz = 0.083 if HILDIR == "mistlands" else 0.064     # (between the dvergr bands on the mistlands box)
    for x in (-0.11, 0.11): box((x, -D / 2 - 0.0009, mz), (0.10, 0.0018, 0.011), "mark", bevel=0.0)    # her mark
    if HILDIR == "ashlands":    # (the box first lost in the swamp, now the Ashlands') embers caught in the lid and the joints
        for k in range(16):
            x = rnd.uniform(-LW / 2 + 0.02, LW / 2 - 0.02); y = rnd.uniform(-LD / 2 + 0.015, LD / 2 - 0.015)
            if abs(x) < 0.13 and abs(y) < 0.03: continue
            blob((x, y, LID1 + 0.001), rnd.uniform(0.004, 0.009), "ember", "lid", 0.6, 60 + k, seg=8, rings=5)
        for k in range(14):     # and smouldering in the body's seams
            sx = rnd.choice((-1, 1)); along = rnd.uniform(-0.18, 0.18)
            c = (along, sx * (D / 2 + 0.001), rnd.uniform(0.02, 0.15)) if rnd.random() < 0.65 else (sx * (W / 2 + 0.001), along * 0.45, rnd.uniform(0.02, 0.15))
            blob(c, rnd.uniform(0.004, 0.008), "ember", "root", 0.8, 80 + k, seg=8, rings=5)
    elif HILDIR == "swamp":
        for k in range(10):     # moss on the lid, thicker toward one end
            x = rnd.uniform(-LW / 2 + 0.03, LW / 2 - 0.12); y = rnd.uniform(-LD / 2 + 0.02, LD / 2 - 0.02)
            if abs(x) > 0.08 or abs(y) > 0.03: blob((x, y, LID1 + 0.004), rnd.uniform(0.018, 0.034), "moss", "lid", 0.35, k)
        for k in range(9):      # and creeping up the lower boards
            sx = rnd.choice((-1, 1)); along = rnd.uniform(-0.18, 0.18)
            if rnd.random() < 0.6: c = (along, sx * (D / 2 + 0.002), rnd.uniform(0.012, 0.05))
            else: c = (sx * (W / 2 + 0.002), along * 0.45, rnd.uniform(0.012, 0.05))
            blob(c, rnd.uniform(0.014, 0.026), "moss", "root", 0.6, 20 + k)
    elif HILDIR == "mountain":
        for k in range(6):      # clusters of stubby ice crystals grown on the lid
            x = rnd.uniform(-LW / 2 + 0.04, LW / 2 - 0.04); y = rnd.uniform(-LD / 2 + 0.03, LD / 2 - 0.03)
            if abs(x) < 0.14 and abs(y) < 0.035: continue       # clear of the handle
            for j in range(3):
                bx, by = x + rnd.uniform(-0.012, 0.012), y + rnd.uniform(-0.01, 0.01)
                spike((bx, by, LID1 - 0.002), (bx + rnd.uniform(-0.012, 0.012), by + rnd.uniform(-0.008, 0.008), LID1 + rnd.uniform(0.016, 0.034)), rnd.uniform(0.008, 0.013), "ice", "lid")
        for k in range(11):     # icicles off the lid's front and side edges
            if k < 8: x, y = rnd.uniform(-LW / 2 + 0.02, LW / 2 - 0.02), -LD / 2 - 0.002
            else: x, y = rnd.choice((-1, 1)) * (LW / 2 + 0.002), rnd.uniform(-0.08, 0.08)
            if abs(x) < 0.04 and y < 0: continue                 # not over the hasp
            spike((x, y, LID0 + 0.004), (x, y, LID0 - rnd.uniform(0.015, 0.045)), rnd.uniform(0.004, 0.007), "ice", "lid")
        for k in range(7):      # (the Deep North's) snow drifted against the handle's feet and the lid's corners
            x = rnd.choice((-1, 1)) * rnd.uniform(0.04, LW / 2 - 0.04); y = rnd.uniform(-LD / 2 + 0.025, LD / 2 - 0.025)
            blob((x, y, LID1 + 0.002), rnd.uniform(0.022, 0.04), "snow", "lid", 0.28, 40 + k, seg=10, rings=6)
    elif HILDIR == "mistlands":
        for z in (0.052, 0.112):   # dvergr iron bands round the body, studded with eitr rivets
            for side in (-1, 1):
                box((0, side * (D / 2 + 0.002), z), (W + 0.008, 0.004, 0.016), "iron", "root", 0.0008)
                box((side * (W / 2 + 0.002), 0, z), (0.004, D + 0.008, 0.016), "iron", "root", 0.0008)
            for x in (-0.15, -0.05, 0.05, 0.15):
                blob((x, -D / 2 - 0.0055, z), 0.0058, "eitr", "root", 1.0, int(x * 100), seg=8, rings=5)
                blob((x, D / 2 + 0.0055, z), 0.0058, "eitr", "root", 1.0, int(x * 100) + 50, seg=8, rings=5)
        # cobwebs (the Mistlands' spiders): thin strands, spokes from a hub out to where they're tied and rings across
        def strand(a, b, bone="lid"): cyl(a, b, 0.00045, "web", bone, seg=4)
        def web(hub, anchors, rings=(0.32, 0.52, 0.7, 0.86), closed=True, seed=0, bone="lid"):
            rr = random.Random(seed); hub = Vector(hub); A = [Vector(a) for a in anchors]
            for a in A: strand(hub, a, bone)
            for f in rings:
                for i in range(len(A) if closed else len(A) - 1):
                    p = hub + (A[i] - hub) * (f + rr.uniform(-0.05, 0.05)); q = hub + (A[(i + 1) % len(A)] - hub) * (f + rr.uniform(-0.05, 0.05))
                    strand(p, q, bone)
        z0 = LID1 + T; HX_, R_, GZ_ = 0.105, 0.028, LID1 + T + float(os.environ.get("VDW_HANDLE_H", "0.065"))
        c45 = (-HX_ + R_ * (1 - math.cos(math.pi / 4)), 0, GZ_ - R_ + R_ * math.sin(math.pi / 4))
        # filling one half of the handle's arch: tied to the lid, up the rod, round its corner and under the grip
        web((-0.062, 0, z0 + 0.03), [(-0.012, 0, z0 + 0.001), (-0.05, 0, z0 + 0.001), (-0.09, 0, z0 + 0.001), (-HX_ + 0.005, 0, z0 + 0.024),
                                     (-HX_ + 0.005, 0, GZ_ - R_), c45, (-0.072, 0, GZ_ - 0.005), (-0.03, 0, GZ_ - 0.012)], seed=1)
        # a small one in the arch's other corner
        web((HX_ - 0.022, 0, GZ_ - 0.022), [(HX_ - 0.005, 0, GZ_ - 0.05), (HX_ - 0.005, 0, GZ_ - R_), (-c45[0], 0, c45[2]), (HX_ - 0.045, 0, GZ_ - 0.005)],
            rings=(0.35, 0.6, 0.85), closed=False, seed=2)
        # a tent of web from that handle's foot down to the lid toward the corner
        web((HX_ + 0.03, 0.0, z0 + 0.012), [(HX_ + 0.004, 0, z0 + 0.04), (HX_ + 0.075, -0.035, z0 + 0.001), (HX_ + 0.085, 0.01, z0 + 0.001),
                                            (HX_ + 0.05, 0.055, z0 + 0.001), (HX_ + 0.01, 0.045, z0 + 0.001), (HX_ + 0.012, -0.05, z0 + 0.001)], seed=3)
        # and two on the body's front (yf: just proud of the iron bands; the box's corner edge at x = W/2)
        yf, yc, xc = -D / 2 - 0.0045, -D / 2 - 0.001, W / 2 + 0.001
        # from the top right corner, under the lid's iron corner, down and to the left to the bottom, as far over as
        # the right side of Hildir's right mark
        web((0.197, -D / 2 - 0.011, 0.11), [(xc, yc, ZB - 0.005), (0.185, yf, ZB - 0.006), (0.163, yf, 0.09), (0.163, yf, 0.004),
                                            (0.205, yf, 0.004), (xc, yc, 0.035), (xc, yc, 0.11)], seed=4, bone="root")
        # from the latch down to the bottom, where the front lure hangs (the lure ends up caught in front of it)
        web((-0.048, -D / 2 - 0.009, 0.068), [(-0.018, yf - 0.002, 0.137), (-0.068, yf, 0.12), (-0.1, yf, 0.05), (-0.082, yf, 0.004),
                                              (-0.028, yf, 0.004), (-0.018, yf - 0.002, 0.118)], seed=5, bone="root")
        # the back: from its top corner on the other end, down and along to the bottom (the front's corner web turned round)
        web((-0.197, D / 2 + 0.011, 0.11), [(-xc, -yc, ZB - 0.005), (-0.185, -yf, ZB - 0.006), (-0.163, -yf, 0.09), (-0.163, -yf, 0.004),
                                            (-0.205, -yf, 0.004), (-xc, -yc, 0.035), (-xc, -yc, 0.11)], seed=6, bone="root")
        xs = W / 2 + 0.0045     # the ends' faces, just proud of their bands
        # the near end: across its lower front corner
        web((-xs - 0.007, -0.065, 0.05), [(-xc, yc, 0.004), (-xc, yc, 0.06), (-xc, yc, 0.105), (-xs, -0.02, 0.1), (-xs, 0.005, 0.045), (-xs, -0.03, 0.004)],
            seed=7, bone="root")
        # the far end: its lower back corner, behind the lure hanging there
        web((xs + 0.007, 0.07, 0.045), [(xc, -yc, 0.004), (xc, -yc, 0.055), (xc, -yc, 0.095), (xs, 0.035, 0.085), (xs, 0.02, 0.035), (xs, 0.04, 0.004)],
            seed=8, bone="root")
    MATS += [m for m in ("mark", "moss", "ice", "snow", "eitr", "ember", "web") if any(p[1] == m for p in parts)]

# ---------------------------------------------------------------- one object, materials, UVs, bones
me = bpy.data.meshes.new("tacklebox"); bm_all = bmesh.new(); lid_verts = []
for bm, mat, bone, bevel in parts:
    if bevel > 0: bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=1, affect='EDGES', clamp_overlap=True)
    off = len(bm_all.verts)
    m2 = bpy.data.meshes.new("tmp"); bm.to_mesh(m2); bm.free()
    for p in m2.polygons: p.material_index = MATS.index(mat)
    bm_all.from_mesh(m2); bm_all.verts.ensure_lookup_table()
    if bone == "lid": lid_verts += list(range(off, len(bm_all.verts)))
    bpy.data.meshes.remove(m2)
bm_all.to_mesh(me); bm_all.free()
ob = bpy.data.objects.new("tacklebox", me); bpy.context.scene.collection.objects.link(ob)
for mname in MATS: me.materials.append(bpy.data.materials.get(mname) or bpy.data.materials.new(mname))
for p in me.polygons: p.use_smooth = False
grain = me.uv_layers.new(name="Grain")
for p in me.polygons:
    nrm = p.normal; ax = max(range(3), key=lambda i: abs(nrm[i])); a, b = [i for i in range(3) if i != ax]
    co = [me.vertices[me.loops[li].vertex_index].co for li in p.loop_indices]
    ea = max(c[a] for c in co) - min(c[a] for c in co); eb = max(c[b] for c in co) - min(c[b] for c in co)
    u, v = (a, b) if ea >= eb else (b, a)
    for li, c in zip(p.loop_indices, co): grain.data[li].uv = (c[u], c[v])
atlas = me.uv_layers.new(name="UVMap"); me.uv_layers.active = atlas; atlas.active_render = True
bpy.context.view_layer.objects.active = ob; ob.select_set(True)
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.004, scale_to_bounds=False)
bpy.ops.uv.pack_islands(margin=0.004)
bpy.ops.object.mode_set(mode='OBJECT')
if S != 1.0: me.transform(Matrix.Scale(S, 4))
ad = bpy.data.armatures.new("TackleBox_Rig"); rig = bpy.data.objects.new("TackleBox_Rig", ad); bpy.context.scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig; bpy.ops.object.mode_set(mode='EDIT')
r = ad.edit_bones.new("root"); r.head = (0, 0, 0); r.tail = (0, 0, 0.08 * S)
l = ad.edit_bones.new("lid"); l.head = (0, HY * S, LID0 * S); l.tail = (0, -D / 2 * S, LID0 * S); l.parent = r
bpy.ops.object.mode_set(mode='OBJECT')
g_root, g_lid = ob.vertex_groups.new(name="root"), ob.vertex_groups.new(name="lid")
lid_set = set(lid_verts)
g_root.add([i for i in range(len(me.vertices)) if i not in lid_set], 1.0, 'REPLACE'); g_lid.add(sorted(lid_set), 1.0, 'REPLACE')
ob.parent = rig; md = ob.modifiers.new("Armature", 'ARMATURE'); md.object = rig
tris = sum(len(p.vertices) - 2 for p in me.polygons)
print(f"TACKLEBOX {len(me.vertices)} points, {tris} triangles, {len(parts)} parts; lid {len(lid_set)} points; "
      f"{W * S:.2f} x {D * S:.2f} x {(GZ + 0.012) * S:.3f} m (body {ZB * S:.3f}, style {STYLE})")
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("SAVED", OUT)
