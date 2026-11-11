# The rod rack and the rod holder (roadmap: playtest notes 2026-11-07), built procedurally and set up for the
# Sanctus + Grungit bake (bake_wood_cooler.py VDW_KIND=lure, tier rack_round / rod_holder): one object "bait" whose
# material slots are the bake's materials (wood, darkwood, iron, leather, linen, bark), a "Grain" UV in metres along
# each part, and a fresh "UVMap" atlas. Z up, the base on the ground at z = 0.
#   VDW_PIECE=rack_round: a round standing rack for ten rods, after the user's floor-rack photos - a round oak base with
#       iron-ringed sockets for the butts, a turned centre post with a knob, and a ring of iron clips up top for the blanks.
#       Slots: SLOTS rods at radius SLOT_R, butts in the sockets at z = BASE_H, held by the clips at z = CLIP_Z.
#   VDW_PIECE=rod_holder: a forked oak stake for the shore - driven into the ground, a Y fork at the top for the rod
#       to rest in, bound with leather where the fork splits, and an iron ring lower down to keep the butt steady.
#   env: VDW_PIECE, VDW_OUT (folder: <out>/Blender Files/<piece>.blend)
import bpy, bmesh, math, os
from mathutils import Vector

PIECE = os.environ["VDW_PIECE"]; OUT = os.environ["VDW_OUT"]
BF = os.path.join(OUT, "Blender Files"); os.makedirs(BF, exist_ok=True)
DEST = os.path.join(BF, f"{PIECE}.blend")
if os.path.exists(DEST): raise SystemExit("exists, kept: " + DEST)
for o in list(bpy.data.objects): bpy.data.objects.remove(o)

MATS = ["wood", "darkwood", "iron", "leather", "linen", "bark"]
bm = bmesh.new()
GRAIN = {}            # face -> how its grain runs: ("axis", origin, direction) or ("plank", direction)

def face(vs, mat, grain, smooth=True):
    try: f = bm.faces.new(vs)
    except ValueError: return None
    f.material_index = MATS.index(mat); f.smooth = smooth; GRAIN[f] = grain
    return f

def frame(t):
    t = t.normalized(); a = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
    a = (a - t * a.dot(t)).normalized(); return a, t.cross(a)

def tube(path, radii, mat, seg=16, caps=True, smooth=True, closed=False):
    """A tube along a path, a radius per point (a turned post, a branch, a band); closed: the path is a loop (a ring)."""
    path = [Vector(p) for p in path]; n = len(path); rings = []; a = None
    for i, p in enumerate(path):
        nxt = path[(i + 1) % n] if closed else path[min(i + 1, n - 1)]
        prv = path[(i - 1) % n] if closed else path[max(i - 1, 0)]
        t = (nxt - prv).normalized()
        if a is None: a, b = frame(t)
        else: a = (a - t * a.dot(t)).normalized(); b = t.cross(a)
        rings.append([bm.verts.new(p + (a * math.cos(2 * math.pi * k / seg) + b * math.sin(2 * math.pi * k / seg)) * radii[i]) for k in range(seg)])
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

def turned(zr, mat, seg=24, at=(0, 0)):
    """A turned part up the Z axis from (z, radius) pairs; a radius of 0 at an end just means it's capped there (a ring
    of zero radius would collapse its faces)."""
    zr = [(z, r) for z, r in zr if r > 1e-5]
    tube([(at[0], at[1], z) for z, r in zr], [r for z, r in zr], mat, seg=seg)

def ring(center, R, r, mat, seg=32, rseg=8, z_axis=True):
    c = Vector(center)
    path = [c + Vector((R * math.cos(2 * math.pi * k / seg), R * math.sin(2 * math.pi * k / seg), 0)) for k in range(seg)]
    tube(path, [r] * seg, mat, seg=rseg, closed=True)

def box(c, size, mat, rot=0.0, grain=Vector((1, 0, 0))):
    c = Vector(c); sx, sy, sz = (s / 2 for s in size); cs, sn = math.cos(rot), math.sin(rot)
    def P(x, y, z): return bm.verts.new(c + Vector((x * cs - y * sn, x * sn + y * cs, z)))
    v = [P(x, y, z) for x in (-sx, sx) for y in (-sy, sy) for z in (-sz, sz)]
    g = ("plank", Vector((cs, sn, 0)) if grain.x else Vector((-sn, cs, 0)) if grain.y else Vector((0, 0, 1)))
    for q in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
        face([v[i] for i in q], mat, g, smooth=False)

if PIECE == "rack_round":
    SLOTS, SLOT_R, BASE_H, CLIP_Z = 10, 0.30, 0.075, 1.02
    # the base: a thick round of oak planks, bevelled, an iron band round its edge, sockets for the butts
    turned([(0.0, 0.0), (0.0, 0.385), (0.012, 0.392), (0.06, 0.392), (0.072, 0.384), (BASE_H, 0.37), (BASE_H, 0.0)], "wood", seg=48)
    tube([(0, 0, 0.022), (0, 0, 0.052)], [0.395, 0.395], "iron", seg=48, caps=False)
    for k in range(SLOTS):
        a = 2 * math.pi * k / SLOTS; x, y = SLOT_R * math.cos(a), SLOT_R * math.sin(a)
        turned([(BASE_H - 0.004, 0.034), (BASE_H + 0.006, 0.034), (BASE_H + 0.012, 0.03), (BASE_H + 0.012, 0.024), (BASE_H + 0.002, 0.024), (BASE_H + 0.002, 0.0)], "iron", seg=16, at=(x, y))
    # three feet under the base, so it stands on uneven ground
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.3
        box((0.29 * math.cos(a), 0.29 * math.sin(a), -0.012), (0.16, 0.07, 0.024), "darkwood", rot=a)
    # the centre post: turned oak with rings, an iron collar at the foot and under the clip ring, a knob on top
    turned([(BASE_H, 0.06), (BASE_H + 0.03, 0.055), (BASE_H + 0.05, 0.042), (0.25, 0.036), (0.27, 0.044), (0.29, 0.036),
            (0.55, 0.034), (0.57, 0.042), (0.59, 0.034), (0.85, 0.033), (0.87, 0.04), (0.89, 0.033), (CLIP_Z + 0.06, 0.032),
            (CLIP_Z + 0.08, 0.04), (1.2, 0.035), (1.24, 0.05), (1.29, 0.054), (1.33, 0.04), (1.355, 0.018), (1.36, 0.0)], "wood", seg=20)
    tube([(0, 0, BASE_H + 0.002), (0, 0, BASE_H + 0.03)], [0.066, 0.064], "iron", seg=20, caps=False)
    # the clip ring: an oak disc with a leather-lined iron clip at each slot, open to the outside for the rod
    turned([(CLIP_Z - 0.03, 0.0), (CLIP_Z - 0.03, 0.29), (CLIP_Z - 0.024, 0.3), (CLIP_Z, 0.3), (CLIP_Z + 0.006, 0.29), (CLIP_Z + 0.006, 0.0)], "wood", seg=48)
    tube([(0, 0, CLIP_Z - 0.028), (0, 0, CLIP_Z + 0.004)], [0.036, 0.036], "iron", seg=20, caps=False)
    for k in range(SLOTS):
        a = 2 * math.pi * k / SLOTS; u = Vector((math.cos(a), math.sin(a), 0)); v = Vector((-math.sin(a), math.cos(a), 0))
        c = u * (SLOT_R + 0.03) + Vector((0, 0, CLIP_Z - 0.012))
        # a U of iron round the rod, its mouth outward
        arc = [c + (u * math.cos(t) * -1 + v * math.sin(t)) * 0.026 for t in [math.pi * (i / 10 - 0.5) * 1.6 for i in range(11)]]
        tube(arc, [0.0055] * len(arc), "iron", seg=8)
        arc_in = [c + (u * math.cos(t) * -1 + v * math.sin(t)) * 0.0215 for t in [math.pi * (i / 10 - 0.5) * 1.5 for i in range(11)]]
        tube(arc_in, [0.004] * len(arc_in), "leather", seg=6)
        box(u * (SLOT_R - 0.005) + Vector((0, 0, CLIP_Z - 0.012)), (0.04, 0.018, 0.012), "iron", rot=a)   # its strap into the disc
    # a carved band on the base's top between the sockets (darker oak inlay)
    ring((0, 0, BASE_H + 0.001), 0.2, 0.006, "darkwood", seg=48, rseg=6)
elif PIECE == "rod_holder":
    # A forked stake, like a bank stick: the rod's butt goes on the ground and the rod leans into the fork. Driven
    # 0.25 m into the ground; the fork's crotch at 0.62 m, its tines up to 0.78 m; the rod rests in it at about 0.665 m.
    stake = [(0.0, 0.0, -0.25), (0.0, 0.0, -0.18), (0.004, 0.0, 0.1), (0.0, 0.003, 0.4), (0.0, 0.0, 0.62)]
    tube(stake, [0.004, 0.022, 0.028, 0.026, 0.026], "bark", seg=14)
    for side in (1, -1):
        tine = [(0.0, 0.0, 0.6), (0.028 * side, 0.004, 0.68), (0.06 * side, 0.0, 0.75), (0.07 * side, -0.004, 0.785)]
        tube(tine, [0.022, 0.018, 0.015, 0.011], "bark", seg=12)
        tube([(0.07 * side, -0.004, 0.785), (0.071 * side, -0.004, 0.792)], [0.011, 0.007], "wood", seg=12)   # cut ends, bare wood
    tube([(0, 0, 0.62), (0, 0, 0.625)], [0.026, 0.02], "wood", seg=14)
    # leather bound round the crotch, a few turns
    for z in (0.565, 0.58, 0.595):
        tube([(0, 0, z), (0, 0, z + 0.011)], [0.0295, 0.0295], "leather", seg=14, caps=False)
    tube([(0.02, -0.022, 0.57), (0.034, -0.03, 0.54), (0.03, -0.036, 0.51)], [0.004, 0.0035, 0.003], "leather", seg=6)   # its loose end
else:
    raise SystemExit("unknown VDW_PIECE " + PIECE)

me = bpy.data.meshes.new("bait")
# Grain (metres): along each part's length, round it; planks run along their direction
grain_of = {f.index: GRAIN[f] for f in bm.faces if f in GRAIN}
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
bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.003, scale_to_bounds=False)
bpy.ops.object.mode_set(mode='OBJECT')
used = sorted({p.material_index for p in me.polygons})
print(f"BUILT {PIECE}: {len(me.polygons)} faces, {len(me.vertices)} verts, materials {[MATS[i] for i in used]}, "
      f"{ob.dimensions.x:.2f} x {ob.dimensions.y:.2f} x {ob.dimensions.z:.2f} m")
bpy.ops.wm.save_as_mainfile(filepath=DEST)
print("SAVED", DEST)
