# Replaces teeth that were only painted on (projected from the front, so they smear from other angles) with real
# modelled teeth, and repaints the inside of the mouth a plain dark colour.
#   1. finds the mouth roof: faces near the front whose texture is the painted teeth (pink/ivory/black stripes)
#   2. finds the mouth floor: upward-facing faces just under the roof
#   3. points both at a dark, even patch of the model's own texture (by moving their UVs; the texture isn't edited)
#   4. adds cone teeth along the front rims of the roof (pointing down) and the floor (pointing up), coloured from a
#      pale bone-coloured patch of the same texture, joined into the fish mesh
# The mesh must lie along Y with its head toward -Y.      env: VDW_SAVE_TO, VDW_DRY_RUN=1 (report only), VDW_CHECK_RENDER
import bpy, bmesh, math, os
import numpy as np
from mathutils import Vector

SAVE_TO = os.environ.get("VDW_SAVE_TO", "")
DRY = os.environ.get("VDW_DRY_RUN") == "1"
mesh = next(o for o in bpy.data.objects if o.type == 'MESH')
mat = mesh.material_slots[0].material
nt = mat.node_tree
bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
img = next(l.from_node.image for l in nt.links if l.to_node == bsdf and l.to_socket.name == "Base Color")
W, H = img.size
px = np.empty(W * H * 4, dtype=np.float32); img.pixels.foreach_get(px); px = px.reshape(H, W, 4)[:, :, :3]
def sample(u, v): return px[min(H - 1, max(0, int(v * H))), min(W - 1, max(0, int(u * W)))]

bm = bmesh.new(); bm.from_mesh(mesh.data); bm.faces.ensure_lookup_table(); bm.verts.ensure_lookup_table()
uvl = bm.loops.layers.uv.active
co = np.array([v.co[:] for v in bm.verts]); lo, hi = co.min(0), co.max(0); L = hi[1] - lo[1]
front = lo[1] + 0.16 * L          # the mouth is in the front 16% of the fish

# ---- 1. mouth roof: faces whose texture is mostly painted teeth
def teethish(c):
    warm = c[0] > c[1] + 0.03 and c[0] > c[2]          # pink gums / ivory teeth (the skin is teal: R < G)
    return warm or c.max() < 0.10                     # or the black gaps between painted teeth
roof = set()
for f in bm.faces:
    if f.calc_center_median().y > front: continue
    uv = [l[uvl].uv.copy() for l in f.loops]
    pts = uv + [sum(uv, Vector((0, 0))) / len(uv)] + [(uv[i] + uv[(i + 1) % len(uv)]) / 2 for i in range(len(uv))]
    pts += [(p + pts[len(uv)]) / 2 for p in uv]
    share = np.mean([teethish(sample(p.x, p.y)) for p in pts])
    if share > 0.4 and f.normal.z < 0.3: roof.add(f.index)
# fill: a face surrounded mostly by roof faces is roof too
for _ in range(2):
    for f in bm.faces:
        if f.index in roof or f.calc_center_median().y > front or f.normal.z > 0.3: continue
        nb = [o.index for e in f.edges for o in e.link_faces if o != f]
        if nb and sum(n in roof for n in nb) >= 2: roof.add(f.index)
rc = np.array([bm.faces[i].calc_center_median()[:] for i in roof])
print(f"  mouth roof: {len(roof)} faces, x {rc[:,0].min():+.3f}..{rc[:,0].max():+.3f}, y {rc[:,1].min():+.3f}..{rc[:,1].max():+.3f}, z {rc[:,2].min():+.3f}..{rc[:,2].max():+.3f}")

# ---- 2. mouth floor: faces under the roof, facing up, between the roof and the bottom lip
roof_zmin = rc[:, 2].min()
floor = set()
xs, ys_ = np.abs(rc[:, 0]).max() + 0.02, rc[:, 1].max() + 0.03
for f in bm.faces:
    c = f.calc_center_median()
    if f.index in roof or c.y > ys_ or abs(c.x) > xs: continue
    if f.normal.z > 0.35 and roof_zmin - 0.14 < c.z < roof_zmin + 0.005:
        # nothing solid between it and the roof (it must look up into the mouth gap)
        floor.add(f.index)
fc = np.array([bm.faces[i].calc_center_median()[:] for i in floor]) if floor else np.zeros((1, 3))
print(f"  mouth floor: {len(floor)} faces, x {fc[:,0].min():+.3f}..{fc[:,0].max():+.3f}, y {fc[:,1].min():+.3f}..{fc[:,1].max():+.3f}, z {fc[:,2].min():+.3f}..{fc[:,2].max():+.3f}")

# ---- 3. texture patches: the darkest even patch (mouth inside) and the palest bone-coloured even patch (teeth)
step = max(1, W // 512); small = px[::step, ::step]; sh, sw = small.shape[:2]; win = 6
best_dark = best_bone = None
for y in range(0, sh - win, 2):
    for x in range(0, sw - win, 2):
        w = small[y:y + win, x:x + win].reshape(-1, 3); m = w.mean(0); sd = w.std(0).mean()
        if sd > 0.035: continue
        lum = m.mean()
        dark_score = lum + sd * 2 + max(0.0, m[1] - m[0]) * 0.5               # dark, even, not too teal
        if best_dark is None or dark_score < best_dark[0]: best_dark = (dark_score, x, y, m)
        if m[0] >= m[1] - 0.01 and m[1] >= m[2] - 0.02 and m[0] - m[2] < 0.25:   # warm-neutral = bone / ivory
            bone_score = -lum + sd * 2
            if best_bone is None or bone_score < best_bone[0]: best_bone = (bone_score, x, y, m)
def patch_uv(b): return ((b[1] + win / 2) * step / W, (b[2] + win / 2) * step / H), win * step / W * 0.35
dark_uv, dark_r = patch_uv(best_dark); bone_uv, bone_r = patch_uv(best_bone)
print(f"  inside-of-mouth colour {tuple(best_dark[3].round(3))} at uv {tuple(round(x, 4) for x in dark_uv)}")
print(f"  tooth colour {tuple(best_bone[3].round(3))} at uv {tuple(round(x, 4) for x in bone_uv)}")

# ---- 4. rims: roof/floor boundary edges whose neighbour lies further out (the lip), not further in (the throat)
def rim_points(faces, spacing):
    cx = np.array([bm.faces[i].calc_center_median()[:] for i in faces]); back = Vector((0, cx[:, 1].max(), cx[:, 2].mean()))
    segs = []
    for i in faces:
        for e in bm.faces[i].edges:
            others = [o for o in e.link_faces if o.index not in faces]
            if not others: continue
            mid = (e.verts[0].co + e.verts[1].co) / 2
            out = others[0].calc_center_median()
            def flat(p): return Vector((p.x, p.y - back.y, 0)).length
            if flat(out) > flat(mid) - 0.002 and mid.y < back.y - 0.02:
                segs.append((e.verts[0].co.copy(), e.verts[1].co.copy()))
    pts = []
    for a, b in segs:
        n = max(1, int((b - a).length / (spacing / 3)))
        pts += [a.lerp(b, t) for t in np.linspace(0, 1, n + 1)]
    # keep only the outermost rim: seen from the back of the mouth, a point is dropped when another point in the
    # same direction lies further out (inner edges of the floor, ridges inside the mouth)
    def polar(p):
        d = Vector((p.x, p.y - back.y)); return math.atan2(d.x, -d.y), d.length
    pol = [polar(p) for p in pts]
    outer = []
    for p, (a, r) in zip(pts, pol):
        win = 0.6 * spacing / max(r, 1e-3)
        if not any(abs(a2 - a) < win and r2 > r + 0.15 * spacing for a2, r2 in pol): outer.append(p)
    pts = outer
    # thin to one point per `spacing`, front to back, both sides
    pts.sort(key=lambda p: (p.y, p.x)); kept = []
    for p in pts:
        if all((p - q).length >= spacing for q in kept): kept.append(p)
    return kept, back
SPACING = 0.012 * L
upper, upper_back = rim_points(roof, SPACING)
lower, lower_back = rim_points(floor, SPACING) if floor else ([], None)
print(f"  teeth positions: {len(upper)} upper, {len(lower)} lower (spacing {SPACING * 100:.1f} cm)")
if DRY:
    print("DRY RUN DONE"); raise SystemExit

# ---- apply: mouth inside -> dark patch
rng = np.random.default_rng(7)
for i in roof | floor:
    for l in bm.faces[i].loops:
        l[uvl].uv = (dark_uv[0] + rng.uniform(-dark_r, dark_r), dark_uv[1] + rng.uniform(-dark_r, dark_r))

# ---- apply: teeth (6-sided cones, base sunk into the gum)
gap = max(0.02, float(np.median([p.z for p in upper])) - (float(np.median([p.z for p in lower])) if lower else roof_zmin - 0.08))
def add_tooth(base, down, back_pt, front_len):
    # longest at the front of the mouth, shorter toward the corners
    depth = min(1.0, (base.y - (lo[1])) / max(1e-6, back_pt.y - lo[1]))
    length = front_len * (1.0 - 0.55 * depth) * rng.uniform(0.85, 1.1)
    radius = length * 0.26
    inward = Vector((-base.x, back_pt.y - base.y, 0)); inward = inward.normalized() if inward.length > 1e-6 else Vector((0, 1, 0))
    axis = (Vector((0, 0, down)) + inward * 0.25).normalized()
    b0 = base - axis * radius * 0.8                      # sink the base into the gum
    side = axis.orthogonal().normalized(); side2 = axis.cross(side)
    ring = [bm.verts.new(b0 + (side * math.cos(a) + side2 * math.sin(a)) * radius) for a in np.linspace(0, 2 * math.pi, 7)[:-1]]
    tip = bm.verts.new(b0 + axis * (length + radius * 0.8))
    faces = []
    for k in range(6):
        faces.append(bm.faces.new((ring[k], ring[(k + 1) % 6], tip) if down < 0 else (ring[(k + 1) % 6], ring[k], tip)))
    faces.append(bm.faces.new(ring[::-1] if down < 0 else ring))    # cap (hidden inside the gum)
    for f in faces:
        f.material_index = 0; f.smooth = False
        for l in f.loops:
            l[uvl].uv = (bone_uv[0] + rng.uniform(-bone_r, bone_r), bone_uv[1] + rng.uniform(-bone_r, bone_r))
    return len(faces)
front_len = min(0.55 * gap, 0.035 * L)
n_new = 0
for p in upper: n_new += add_tooth(p, -1, upper_back, front_len)
for p in lower: n_new += add_tooth(p, +1, lower_back, front_len * 0.8)
bm.normal_update()
bm.to_mesh(mesh.data); mesh.data.update()
print(f"  added {len(upper) + len(lower)} teeth ({n_new} faces), tooth length up to {front_len * 100:.1f} cm (mouth gap {gap * 100:.1f} cm)")

CHECK = os.environ.get("VDW_CHECK_RENDER")
if CHECK:
    s = bpy.context.scene; s.render.engine = 'BLENDER_WORKBENCH'; s.display.shading.light = 'STUDIO'; s.display.shading.color_type = 'TEXTURE'
    s.render.resolution_x, s.render.resolution_y = 500, 400
    T = Vector((0, lo[1] + 0.07 * L, float(np.median([p.z for p in upper])) - gap / 2))
    cd = bpy.data.cameras.new("Chk"); cd.type = 'ORTHO'; cd.ortho_scale = 0.3 * L
    cam = bpy.data.objects.new("Chk", cd); s.collection.objects.link(cam); s.camera = cam
    for name, d in (("front", (0, -1, 0.05)), ("side", (1, -0.05, 0.02)), ("q", (0.7, -0.7, 0.15)), ("below", (0.3, -0.6, -0.75)), ("sideR", (-1, -0.2, 0)), ("open", (0.25, -1, -0.12))):
        cam.location = T + Vector(d).normalized() * 5
        cam.rotation_euler = (T - cam.location).to_track_quat('-Z', 'Y').to_euler()
        s.render.filepath = f"{CHECK}_{name}.png"; bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam); bpy.data.cameras.remove(cd)
    s.render.engine = 'BLENDER_EEVEE_NEXT'
if SAVE_TO:
    bpy.ops.wm.save_as_mainfile(filepath=SAVE_TO)
    print("  saved", SAVE_TO)
print("MOUTH FIX DONE")
