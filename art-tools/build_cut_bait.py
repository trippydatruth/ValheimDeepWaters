# Cut Bait (a minnow, baitfish or bluegill cut up at the cleaning table), designed 2026-11-02: a thick chunk of baitfish -
# a slice of its body, silver-scaled skin round the outside (dark on the back), both ends cut on a slant showing pink flesh
# with the backbone in the middle, a stub of the dorsal fin still on top. Smooth-shaded, low triangle count.
# Slots: scales / back / flesh / bone / rim (a thin light pink ring round the edge of each cut face). Along Y like the other bait, up +Z. For bake_wood_cooler.py (VDW_KIND=lure,
# VDW_TIER=cut_bait).
#   blender -b --factory-startup --python build_cut_bait.py      env: VDW_OUT (new .blend)
import bpy, bmesh, os, math
import numpy as np
from mathutils import Vector, noise

OUT = os.environ["VDW_OUT"]
if os.path.exists(OUT): raise SystemExit("exists, kept: " + OUT)
bpy.ops.wm.read_factory_settings(use_empty=True)
bm = bmesh.new()
MATS = ["scales", "back", "flesh", "bone", "rim"]
SEG, ROWS = 24, 6
H, W, L = 0.0095, 0.0068, 0.017                          # half height, half width, length (m): a slice

def section(t, a):
    """the fish's cross-section: tall and narrow, its back a little pointed, its belly round"""
    s = 1 - 0.12 * (t - 0.5) ** 2 * 4                                                                   # a touch fuller mid-chunk
    z = H * s * math.cos(a) * (1.06 if math.cos(a) > 0 else 1.0)
    x = W * s * math.sin(a) * (1 - 0.22 * max(0.0, math.cos(a)) ** 2)                                   # a little thinner toward the back
    return x, z

def cut_y(t, z):                                                                                        # both ends cut on a slant
    return -L / 2 + L * t + (0.0035 * z / H) * (1 if t > 0.5 else -0.6)

rings = []
for i in range(ROWS + 1):
    t = i / ROWS; row = []
    for k in range(SEG):
        a = 2 * math.pi * k / SEG
        x, z = section(t, a)
        y = cut_y(t, z)
        lump = 1 + 0.03 * noise.noise(Vector((x * 400, y * 400, z * 400)))
        row.append(bm.verts.new((x * lump, y, z * lump)))
    rings.append(row)
for i in range(ROWS):
    for k in range(SEG):
        k2 = (k + 1) % SEG
        f = bm.faces.new((rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]))
        f.material_index = 1 if math.cos(2 * math.pi * (k + 0.5) / SEG) > 0.45 else 0                     # the dark back
# the cut faces: flesh, a little bulged and uneven, the backbone set in the middle
for end, ring in ((0, rings[0]), (1, rings[-1])):
    c = sum((v.co for v in ring), Vector()) / SEG
    inner = []
    for v in ring:                                                                                      # an inner ring, so the flesh isn't a flat fan
        p = c + (v.co - c) * 0.55; p.y += (0.0012 if end else -0.0012) * (1 + 0.4 * noise.noise(p * 600))
        inner.append(bm.verts.new(p))
    mid = bm.verts.new(c + Vector((0, 0.0016 if end else -0.0016, 0)))
    rim = [bm.verts.new(c + (v.co - c) * 0.88 + Vector((0, 0.0003 if end else -0.0003, 0))) for v in ring]   # a thin pale ring at the edge
    for k in range(SEG):
        k2 = (k + 1) % SEG
        fr = (ring[k], ring[k2], rim[k2], rim[k]) if end else (ring[k2], ring[k], rim[k], rim[k2])
        bm.faces.new(fr).material_index = 4
        ft = (rim[k], rim[k2], inner[k2], inner[k]) if end else (rim[k2], rim[k], inner[k], inner[k2])
        bm.faces.new(ft).material_index = 2
        fc = (inner[k], inner[k2], mid) if end else (inner[k2], inner[k], mid)
        bm.faces.new(fc).material_index = 2
# the backbone through the middle, its ends showing proud of the flesh, and two rib stubs
bb = bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.0012, radius2=0.0012, depth=L * 1.3)
bmesh.ops.rotate(bm, verts=bb["verts"], cent=(0, 0, 0), matrix=__import__("mathutils").Matrix.Rotation(math.radians(90), 3, 'X'))
bmesh.ops.translate(bm, verts=bb["verts"], vec=(0, 0, H * 0.22))
for f in {f for v in bb["verts"] for f in v.link_faces}: f.material_index = 3
# a stub of the dorsal fin on top
fin = [bm.verts.new((0, -L * 0.25, H * 1.0)), bm.verts.new((0, L * 0.2, H * 0.98)), bm.verts.new((0, L * 0.05, H * 1.5)), bm.verts.new((0, -L * 0.18, H * 1.42))]
f = bm.faces.new(fin); f.material_index = 1
bmesh.ops.solidify(bm, geom=[f], thickness=0.0006)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

me = bpy.data.meshes.new("bait"); bm.to_mesh(me); bm.free()
ob = bpy.data.objects.new("bait", me); bpy.context.scene.collection.objects.link(ob)
for n in MATS: me.materials.append(bpy.data.materials.new(n))
for p in me.polygons: p.use_smooth = True
grain = me.uv_layers.new(name="Grain")
for p in me.polygons:
    for li in p.loop_indices:
        c = me.vertices[me.loops[li].vertex_index].co; grain.data[li].uv = (c.y, math.atan2(c.z, c.x) * 0.01)
atlas = me.uv_layers.new(name="UVMap"); me.uv_layers.active = atlas; atlas.active_render = True
bpy.context.view_layer.objects.active = ob; ob.select_set(True)
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.006, scale_to_bounds=False)
bpy.ops.uv.pack_islands(margin=0.006); bpy.ops.object.mode_set(mode='OBJECT')
co = np.array([v.co for v in me.vertices])
print(f"CUT: {len(me.vertices)} points, {sum(len(p.vertices) - 2 for p in me.polygons)} triangles; {(co.max(0) - co.min(0)).round(3)} m")
os.makedirs(os.path.dirname(OUT), exist_ok=True); bpy.ops.wm.save_as_mainfile(filepath=OUT); print("SAVED", OUT)
