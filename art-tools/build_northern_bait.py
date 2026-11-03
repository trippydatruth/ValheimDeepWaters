# The Northern Bait ("seal blubber rolled in crushed lingonberries"), designed 2026-11-02: a cut chunk of seal blubber - a
# rounded block, its top a cap of dark speckled seal hide, its cut sides glossy cream fat - rolled in lingonberries:
# about ten round berries pressed into the fat, some whole with their little dark crowns, so plenty of blubber shows.
#   body:     an icosphere pushed into a rounded block (a superellipsoid), remeshed with QuadriFlow into even quads,
#             smooth-shaded; its top faces are the hide
#   berries:  low icospheres set onto the surface (cast in from outside), squashed along the surface when crushed
# Saves one object "bait" with slots blubber / hide / berry / black, a "Grain" UV and a fresh "UVMap" atlas - ready for
# bake_wood_cooler.py (VDW_KIND=lure, VDW_TIER=northern_bait).
#   blender -b --factory-startup --python build_northern_bait.py      env: VDW_OUT (new .blend)
import bpy, bmesh, os, math
import numpy as np
from mathutils import Vector, Matrix, noise
from mathutils.bvhtree import BVHTree

OUT = os.environ["VDW_OUT"]
if os.path.exists(OUT): raise SystemExit("exists, kept: " + OUT)
bpy.ops.wm.read_factory_settings(use_empty=True)
rnd = np.random.default_rng(7)
SC = bpy.context.scene

def obj_from_bm(bm, name):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); SC.collection.objects.link(ob); return ob

# ---------------------------------------------------------------- the blubber block
AX, AY, AZ = 0.0125, 0.0175, 0.0095                  # half sizes (m): along the bait (Y) it's longest
E = 4.2                                              # superellipsoid exponent: a roughly cut block
bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=5, radius=1.0)
for v in bm.verts:
    d = v.co.normalized()
    sx, sy, sz = (abs(c) ** (2 / E) * (1 if c >= 0 else -1) for c in d)
    p = Vector((sx * AX, sy * AY, sz * AZ))
    p *= 1 + 0.09 * noise.noise(d * 1.6 + Vector((1.3, 4.1, 0.2))) + 0.03 * noise.noise(d * 5.0)      # lumpy, cut unevenly
    p.z += 0.0022 * (p.y / AY) * (1 if p.z > 0 else 0.3)                                                # its top cut on a slant
    if p.z > 0: p.x *= 1 - 0.12 * (p.z / AZ); p.y *= 1 - 0.08 * (p.z / AZ)                              # narrower toward the hide
    v.co = p
body = obj_from_bm(bm, "bait")
for o in SC.objects: o.select_set(o is body)
bpy.context.view_layer.objects.active = body
bpy.ops.object.quadriflow_remesh(target_faces=700, use_mesh_symmetry=False, use_preserve_sharp=False, use_preserve_boundary=False, smooth_normals=True)
me = body.data
for name in ("blubber", "hide", "berry", "black"): me.materials.append(bpy.data.materials.new(name))
for p in me.polygons:
    p.use_smooth = True
    p.material_index = 0
print(f"BODY: {len(me.polygons)} faces after QuadriFlow")

# ---------------------------------------------------------------- the hide: a skin laid over the top, its edge smooth
sb = bmesh.new(); vmap = {}
for p in me.polygons:
    if p.center.z < AZ * 0.45: continue
    vs = []
    for i in p.vertices:
        if i not in vmap: vmap[i] = sb.verts.new(me.vertices[i].co)
        vs.append(vmap[i])
    sb.faces.new(vs)
edge_z = lambda c: AZ * 0.6 + 0.0011 * noise.noise(Vector((c.x * 260, c.y * 260, 0.4)))                 # where the hide ends, ragged
bmesh.ops.delete(sb, geom=[f for f in sb.faces if all(v.co.z < edge_z(v.co) for v in f.verts)], context='FACES')
for _ in range(5):                                                                                      # its outline eased round
    sb.verts.ensure_lookup_table()
    moved = {}
    for v in sb.verts:
        if not v.is_boundary: continue
        nb = [e.other_vert(v) for e in v.link_edges if e.is_boundary]
        if len(nb) == 2: moved[v] = v.co * 0.4 + (nb[0].co + nb[1].co) * 0.3
    for v, c in moved.items(): v.co = c
dg0 = bpy.context.evaluated_depsgraph_get(); tree0 = BVHTree.FromObject(body, dg0)
for v in sb.verts:                                                                                     # a thin skin, thinning at its edge
    hit, nrm, _, _ = tree0.find_nearest(v.co)
    if hit is None: continue
    v.co = hit + nrm * (0.00005 if v.is_boundary else 0.0004)
for f in sb.faces: f.material_index = 1; f.smooth = True
hm = bpy.data.meshes.new("hide"); sb.to_mesh(hm); sb.free()
bmb = bmesh.new(); bmb.from_mesh(me); bmb.from_mesh(hm); bmb.to_mesh(me); bmb.free(); bpy.data.meshes.remove(hm)
# ---------------------------------------------------------------- lingonberries, crushed and whole
dg = bpy.context.evaluated_depsgraph_get(); tree = BVHTree.FromObject(body, dg)
bm = bmesh.new(); bm.from_mesh(me)
def on_surface(d):
    """where a ray in from outside, along -d, meets the block, and its normal there"""
    hit, nrm, _, _ = tree.ray_cast(d.normalized() * 0.08, -d.normalized())
    return hit, nrm
def berry(c, r, n, crushed):
    t = len(bm.verts)
    res = bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=r)   # (round and light: ~180 triangles a berry)
    q = n.to_track_quat('Z', 'Y').to_matrix().to_4x4()
    sq = Matrix.Diagonal((1.08, 1.04, 0.8, 1)) if crushed else Matrix.Diagonal((1, 1, 0.95, 1))   # (round berries, the pressed ones only a little flattened)           # crushed: flat along the surface
    bmesh.ops.transform(bm, matrix=Matrix.Translation(c + n * (r * (0.35 if crushed else 0.6))) @ q @ sq, verts=res["verts"])
    for v in res["verts"]:                                                                              # broken, not round
        v.co += (v.co - c).normalized() * r * (0.06 if crushed else 0.03) * noise.noise(v.co * 2500)
    for f in {f for v in res["verts"] for f in v.link_faces}: f.material_index = 2; f.smooth = True
    return res
placed = []
for k in range(14):
    d = Vector((rnd.normal(), rnd.normal(), abs(rnd.normal()) * 0.9 - 0.25))                             # all over, fewer underneath
    hit, n = on_surface(d)
    if hit is None or any((hit - p).length < 0.0055 for p in placed): continue
    placed.append(hit)
    whole = k % 3 == 0
    rb = rnd.uniform(0.0019, 0.0023) if whole else rnd.uniform(0.0014, 0.0024)
    berry(hit, rb, n, crushed=not whole)
    if whole:                                                                                           # its dark crown, seated on top
        tip = hit + n * (rb * 0.55 + rb * 0.85)
        cr = bmesh.ops.create_cone(bm, cap_ends=True, segments=5, radius1=0.0007, radius2=0.0011, depth=0.0005)
        bmesh.ops.transform(bm, matrix=Matrix.Translation(tip) @ n.to_track_quat('Z', 'Y').to_matrix().to_4x4(), verts=cr["verts"])
        for f in {f for v in cr["verts"] for f in v.link_faces}: f.material_index = 3
for k in range(8):                                                                                      # crumbs of berry skin
    d = Vector((rnd.normal(), rnd.normal(), rnd.normal() * 0.6 + 0.2))
    hit, n = on_surface(d)
    if hit is None: continue
    cb = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=rnd.uniform(0.0005, 0.0009))
    bmesh.ops.transform(bm, matrix=Matrix.Translation(hit) @ n.to_track_quat('Z', 'Y').to_matrix().to_4x4() @ Matrix.Diagonal((1, 1, 0.45, 1)), verts=cb["verts"])
    for f in {f for v in cb["verts"] for f in v.link_faces}: f.material_index = 2
bm.to_mesh(me); bm.free()

# ---------------------------------------------------------------- UVs
grain = me.uv_layers.new(name="Grain")
for p in me.polygons:
    for li in p.loop_indices:
        c = me.vertices[me.loops[li].vertex_index].co; grain.data[li].uv = (c.y, c.x)
atlas = me.uv_layers.new(name="UVMap"); me.uv_layers.active = atlas; atlas.active_render = True
for l in [l for l in me.uv_layers if l.name not in ("Grain", "UVMap")]: me.uv_layers.remove(l)
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.004, scale_to_bounds=False)
bpy.ops.uv.pack_islands(margin=0.004); bpy.ops.object.mode_set(mode='OBJECT')
counts = np.bincount([p.material_index for p in me.polygons], minlength=len(me.materials))
co = np.array([v.co for v in me.vertices])
print(f"NORTHERN: {len(me.vertices)} points, {sum(len(p.vertices) - 2 for p in me.polygons)} triangles; {(co.max(0) - co.min(0)).round(3)} m; "
      + ", ".join(f"{m.name} {c}" for m, c in zip(me.materials, counts)) + f"; {len(placed)} berries")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT); print("SAVED", OUT)
