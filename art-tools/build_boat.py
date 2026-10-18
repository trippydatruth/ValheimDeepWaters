# The Fishing Boat: the user's rowing boat (boat.blend: hull "Plane_Plane.001", the oar "paddle.001" through the left
# oarlock) made into a Valheim ship model. Read-only on boat.blend; writes a new .blend, Unity maps and a rig json.
#   - transforms baked, scaled VDW_SCALE (1.4: a 4 m boat a 1.85 m viking fits in), origin at the keel under the
#     middle of the hull, bow toward -Y (Unity +Z, the ship's forward)
#   - two oars "oar.L" / "oar.R" from the one oar mesh, each with its origin at its oarlock ring; at rest the oar runs
#     straight out (local +X toward the blade, horizontal), blade squared (its face toward bow and stern)
#   - hull_Unity_* and oar_Unity_* maps from the boat / paddle textures
# env: VDW_SRC (boat.blend), VDW_TEX (textures folder), VDW_OUT (folder), VDW_SCALE
import bpy, bmesh, json, math, os
import numpy as np
from mathutils import Matrix, Vector

SRC_TEX = os.environ["VDW_TEX"]; OUT = os.environ["VDW_OUT"]; K = float(os.environ.get("VDW_SCALE", "1.4"))
# VDW_ZSCALE: the hull made taller (deeper sides, higher seats) on top of the overall scale; the oars keep their shape
ZS = float(os.environ.get("VDW_ZSCALE", "1.0"))
for d in ("Textures", "Models", "Blender Files"): os.makedirs(os.path.join(OUT, d), exist_ok=True)

hull_src = bpy.data.objects["Plane_Plane.001"]; oar_src = bpy.data.objects["paddle.001"]
def world_mesh(o, name):
    me = o.data.copy(); me.name = name; me.transform(o.matrix_world); return me
hull_me = world_mesh(hull_src, "hull"); oar_me = world_mesh(oar_src, "oar")

hc = np.array([v.co[:] for v in hull_me.vertices])
origin = Vector((0.0, float(hc[:, 1].min() + hc[:, 1].max()) / 2, float(hc[:, 2].min())))
place = Matrix.Scale(K, 4) @ Matrix.Translation(-origin)
hull_me.transform(place)
hull_me.transform(Matrix.Diagonal((1.0, 1.0, ZS, 1.0)))

# the bench the rower sits on (the user's note): the flat strip across the middle at about z -0.114
bench = hc[(np.abs(hc[:, 2] + 0.114) < 0.01) & (np.abs(hc[:, 0]) < 0.45) & (np.abs(hc[:, 1] + 0.12) < 0.25)]
bench_y = (float(bench[:, 1].min()), float(bench[:, 1].max())); bench_top = float(bench[:, 2].max())
print("BENCH y", bench_y, "top", bench_top)

# oarlock rings: loose parts of the hull with ~28 verts at |x| 0.554
RING = Vector((0.554, 0.156, 0.065))

# --- the oar, in its own frame: origin at the ring, +X along the shaft to the blade, +Y the blade's face normal
oc = np.array([v.co[:] for v in oar_me.vertices]); cen = oc.mean(0)
u, s, vt = np.linalg.svd(oc - cen); ax = vt[0]
t = (oc - cen) @ ax
if np.median(oc[t > np.percentile(t, 80)][:, 0]) > np.median(oc[t < np.percentile(t, 20)][:, 0]): ax = -ax; t = -t  # +ax toward the blade (outboard, -x)
blade = oc[t > np.percentile(t, 80)]; ub, sb, vtb = np.linalg.svd(blade - blade.mean(0)); nb = vtb[2]
nb = nb - ax * nb.dot(ax); nb /= np.linalg.norm(nb); zb = np.cross(ax, nb)
ring_l = np.array([-RING.x, RING.y, RING.z])
# where the shaft passes the ring: the point on the axis closest to the ring centre
p0 = cen + ax * ((ring_l - cen) @ ax)
R = np.array([ax, nb, zb])                     # rows: world -> oar frame
oar_me.transform(Matrix(((*R[0], 0), (*R[1], 0), (*R[2], 0), (0, 0, 0, 1))) @ Matrix.Translation(Vector((-p0).tolist())))
oar_me.transform(Matrix.Scale(K, 4))
lc = np.array([v.co[:] for v in oar_me.vertices])
print(f"OAR {np.ptp(lc[:, 0]):.2f} m, inboard {-lc[:, 0].min():.2f} m (handle end), outboard {lc[:, 0].max():.2f} m, shaft offset from ring {np.linalg.norm(p0 - ring_l) * K * 100:.1f} cm")

hull = bpy.data.objects.new("hull", hull_me); bpy.context.scene.collection.objects.link(hull)
pivots = {}
for side, sx in (("L", -1), ("R", 1)):
    me = oar_me if side == "L" else oar_me.copy()
    o = bpy.data.objects.new(f"oar.{side}", me); bpy.context.scene.collection.objects.link(o)
    piv = place @ Vector((sx * RING.x, RING.y, RING.z)); piv.z *= ZS
    o.location = piv
    o.rotation_euler = (0, 0, math.pi if sx < 0 else 0)   # +X straight out over its own side
    pivots[side] = list(piv)
for o in (hull_src, oar_src, bpy.data.objects["paddle"]): bpy.data.objects.remove(o)

# VDW_PLANKS=1: dressed in Valheim's own ship planks (the Longship's tiling "worn_shipplank", put on in game). The
# oarlock rings become their own object "oarlocks" (iron, not planks), and the hull is unwrapped in metres with a box
# projection per face: U along the boat and V up/around it on the sides and bottom, so planks run bow to stern; U
# across on the bow and transom, so their planks run side to side.
PLANKS = os.environ.get("VDW_PLANKS") == "1"
if PLANKS:
    bm = bmesh.new(); bm.from_mesh(hull_me); bm.verts.ensure_lookup_table()
    comp = {}; k = 0
    for v in bm.verts:
        if v.index in comp: continue
        st = [v]; comp[v.index] = k
        while st:
            x = st.pop()
            for e in x.link_edges:
                w = e.other_vert(x)
                if w.index not in comp: comp[w.index] = k; st.append(w)
        k += 1
    sizes = {c: sum(1 for i in comp.values() if i == c) for c in set(comp.values())}
    ring_parts = {c for c, n in sizes.items() if n < 40}
    ring_bm = bm.copy()
    bmesh.ops.delete(ring_bm, geom=[v for v in ring_bm.verts if comp[v.index] not in ring_parts], context='VERTS')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if comp[v.index] in ring_parts], context='VERTS')
    uvl = bm.loops.layers.uv.active or bm.loops.layers.uv.new("UVMap")
    bm.normal_update()
    for f in bm.faces:
        n = f.normal; ax = max(range(3), key=lambda i: abs(n[i]))
        for l in f.loops:
            x, y, z = l.vert.co
            if ax == 1: l[uvl].uv = (x, z)          # bow and transom: planks across
            elif ax == 0: l[uvl].uv = (y, z)        # sides: along the boat, up the side
            else: l[uvl].uv = (y, x)                # bottom, floor, benches: along the boat, across
    bm.to_mesh(hull_me); bm.free()
    ring_me = bpy.data.meshes.new("oarlocks"); ring_bm.to_mesh(ring_me); ring_bm.free()
    if ZS != 1.0:                                   # the rings keep their round shape: only their height on the hull moves
        rc = np.array([v.co[:] for v in ring_me.vertices]); comp_r = {}
        for v in ring_me.vertices: pass
        cz = float(np.mean(rc[:, 2]))
        for v in ring_me.vertices: v.co.z = cz + (v.co.z - cz) / ZS
    rings = bpy.data.objects.new("oarlocks", ring_me); bpy.context.scene.collection.objects.link(rings)
    print(f"PLANKS: hull unwrapped in metres, {len(ring_parts)} oarlock parts split off")

# materials (the importer gives each mesh its own texture set by name: hull_Unity_*, oar_Unity_*, oarlocks_Unity_*)
for o in bpy.data.objects:
    if o.type == 'MESH':
        o.data.materials.clear(); o.data.materials.append(bpy.data.materials.new(o.name.split(".")[0]))

def load(path):
    im = bpy.data.images.load(path); im.colorspace_settings.name = "Non-Color"; w, h = im.size
    return np.array(im.pixels[:], np.float32).reshape(h, w, 4)
def save(px, name):
    h, w = px.shape[:2]; im = bpy.data.images.new(name, w, h, alpha=True); im.colorspace_settings.name = "Non-Color"
    im.pixels[:] = px.ravel(); p = os.path.join(OUT, "Textures", name + ".png"); im.filepath_raw = p; im.file_format = 'PNG'; im.save(); print("MAP", name)
for src, dst, smooth in ((("boat", "hull", 0.22),) if not PLANKS else ()) + (("paddle", "oar", 0.28),):
    a = load(os.path.join(SRC_TEX, f"{src}_None_color.tga.png")); a[..., 3] = 1; save(a, f"{dst}_Unity_Albedo")
    n = load(os.path.join(SRC_TEX, f"{src}_None_nmap.tga.png")); n[..., 3] = 1; save(n, f"{dst}_Unity_Normal")
    ms = np.zeros_like(a); ms[..., 3] = smooth; save(ms, f"{dst}_Unity_MetallicSmoothness")
if PLANKS:
    # Stand-in planks (one tile = 1 m x 1 m, six planks across, butt joints staggered) for icons and in case the
    # game's own plank material can't be found; in game the hull wears Valheim's.
    S = 512; rng = np.random.default_rng(5); v_, u_ = (np.mgrid[0:S, 0:S] + 0.5) / S
    row = np.floor(v_ * 6).astype(int); seg = np.floor(u_ * 2 + row * 0.37).astype(int)
    tone = (np.sin(row * 12.9898 + seg * 78.233) * 43758.5453) % 1
    grain = 0.5 + 0.5 * np.sin(v_ * 260 + np.sin(u_ * 9 + row * 1.7) * 1.5 + tone * 6)   # long grain lines along each plank
    a = np.ones((S, S, 4), np.float32)
    base = np.array((0.36, 0.25, 0.16)) * (0.8 + 0.35 * tone[..., None]) * (0.88 + 0.12 * grain[..., None])
    seam = (np.abs(((v_ * 6) % 1) - 0.0) < 0.03) | (np.abs(((u_ * 2 + row * 0.37) % 1)) < 0.006)
    a[..., :3] = np.where(seam[..., None], base * 0.45, base); save(a, "hull_Unity_Albedo")
    h = grain * 0.2 - seam * 0.8; gy, gx = np.gradient(h); nn = np.dstack((-gx * 4, -gy * 4, np.ones_like(h))); nn /= np.linalg.norm(nn, axis=2, keepdims=True)
    n4 = np.ones((S, S, 4), np.float32); n4[..., :3] = nn * 0.5 + 0.5; save(n4, "hull_Unity_Normal")
    ms = np.zeros((S, S, 4), np.float32); ms[..., 3] = 0.18; save(ms, "hull_Unity_MetallicSmoothness")
    for k_, val in (("Albedo", (0.16, 0.16, 0.17, 1)), ("Normal", (0.5, 0.5, 1, 1)), ("MetallicSmoothness", (0.85, 0.85, 0.85, 0.45))):
        save(np.tile(np.array(val, np.float32), (16, 16, 1)), f"oarlocks_Unity_{k_}")

hb = np.array([v.co[:] for v in hull_me.vertices])
rig = {"scale": K, "length": float(np.ptp(hb[:, 1])), "beam": float(np.ptp(hb[:, 0])), "height": float(np.ptp(hb[:, 2])),
       "bench_y": [(y - origin.y) * K for y in bench_y], "bench_top": (bench_top - origin.z) * K * ZS, "zscale": ZS,
       "oarlock_L": pivots["L"], "oarlock_R": pivots["R"],
       "oar_inboard": float(-lc[:, 0].min()), "oar_outboard": float(lc[:, 0].max())}
json.dump(rig, open(os.path.join(OUT, "Textures", "fishing_boat_rig.json"), "w"), indent=1)
print("RIG", json.dumps(rig))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "Blender Files", "fishing_boat.blend"))
print("SAVED")
