# The Frost Bait (Freeze Gland + Wolf Meat), after the user's picture (2026-11-02): a slab of frozen raw meat marbled with
# fat, snow lying on its top and icicles hanging round its edge - smooth-shaded, on clean topology.
#   meat:     an icosphere pushed into a wide, lumpy slab, remeshed with QuadriFlow (Blender's quad remesher) into even
#             quads; its fat marbling is painted in by the bake (bake_wood_cooler.py "marble")
#   snow:     lying on the meat: the meat's own faces in each patch, copied, subdivided and lifted along their normals -
#             deepest and lumpy in the middle, thinning to nothing at a ragged edge (the Real Snow add-on isn't published
#             for Blender 5.2; its merged metaballs made thin slabs with steep, dark-rimmed edges here)
#   icicles:  tapering, lumpy, their tops buried in the meat
# Saves one object "bait" with slots meat / fat / snow / ice, a "Grain" UV and a fresh "UVMap" atlas - ready for
# bake_wood_cooler.py (VDW_KIND=lure, VDW_TIER=frost_bait), like restyle_lure.py's output.
#   blender -b --factory-startup --python build_frost_bait.py      env: VDW_OUT (new .blend)
import bpy, bmesh, os, math
import numpy as np
from mathutils import Vector, Matrix, noise

OUT = os.environ["VDW_OUT"]
if os.path.exists(OUT): raise SystemExit("exists, kept: " + OUT)
bpy.ops.wm.read_factory_settings(use_empty=True)
rnd = np.random.default_rng(21)
SC = bpy.context.scene

def obj_from_bm(bm, name):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); SC.collection.objects.link(ob); return ob

def apply_mod(ob, mod):
    for o in SC.objects: o.select_set(o is ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier=mod.name)

# ---------------------------------------------------------------- the meat
RX, RY, RZ = 0.0196, 0.016, 0.0088
bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=5, radius=1.0)
for v in bm.verts:
    d = v.co.normalized()
    lump = 1 + 0.16 * noise.noise(d * 1.6 + Vector((3.1, 0.4, 2.2))) + 0.07 * noise.noise(d * 4.0 + Vector((0.7, 5.1, 1.3)))
    p = Vector((d.x * RX, d.y * RY, d.z * RZ)) * lump
    p.z = p.z * (0.82 if p.z < 0 else 1.0) + 0.0012 * noise.noise(d * 6.0)                        # a flatter underside
    v.co = p
meat = obj_from_bm(bm, "meat")
for o in SC.objects: o.select_set(o is meat)
bpy.context.view_layer.objects.active = meat
bpy.ops.object.quadriflow_remesh(target_faces=900, use_mesh_symmetry=False, use_preserve_sharp=False, use_preserve_boundary=False, smooth_normals=True)
for p in meat.data.polygons: p.use_smooth = True
print(f"MEAT: {len(meat.data.polygons)} faces after QuadriFlow")

# ---------------------------------------------------------------- the snow, as Real Snow makes it
from mathutils.bvhtree import BVHTree
dg = bpy.context.evaluated_depsgraph_get()
mm = meat.data
tree = BVHTree.FromObject(meat, dg)
up = [p for p in mm.polygons if p.normal.z > 0.55 and p.center.z > RZ * 0.25]
patches = [(0.003, -0.002, 0.0068), (-0.010, 0.006, 0.0050), (0.011, 0.005, 0.0046), (-0.004, -0.009, 0.0038), (0.009, -0.008, 0.0034)]
def depth(c):                                           # how deep the snow lies here: 1 at a patch's middle, 0 past its ragged edge
    d = 0.0
    for cx, cy, R in patches:
        q = math.hypot(c.x - cx, c.y - cy) / (R * (1 + 0.3 * noise.noise(Vector((c.x * 380, c.y * 380, cx * 90)))))
        if q < 1: d = max(d, (1 - q * q) ** 0.7)
    return d
# Snow lying on the meat: the meat's own faces in each patch, copied, subdivided and lifted along their normals - deepest
# and lumpy in the middle, thinning to nothing at the ragged edge, so it hugs the slab with no sides to cast a dark rim
# (merged metaballs made thin slabs with steep edges)
sb = bmesh.new(); vmap = {}
for p in up:
    if max(depth(mm.vertices[i].co) for i in p.vertices) <= 0.0: continue
    vs = []
    for i in p.vertices:
        if i not in vmap: vmap[i] = sb.verts.new(mm.vertices[i].co)
        vs.append(vmap[i])
    sb.faces.new(vs)
bmesh.ops.subdivide_edges(sb, edges=list(sb.edges), cuts=2, use_grid_fill=True, smooth=0.6)
sb.normal_update()
for v in sb.verts:
    hit, nrm, _, _ = tree.find_nearest(v.co)
    if hit is None: continue
    nrm = nrm if nrm.z > 0 else -nrm
    d = depth(hit)
    lump = 0.75 + 0.5 * noise.noise(hit * 1100) + 0.25 * noise.noise(hit * 3000)
    v.co = hit + nrm * (0.00006 + 0.0019 * d * lump)
# the faces that lie wholly outside every patch go (they would be a bare film over the meat)
bmesh.ops.delete(sb, geom=[f for f in sb.faces if all(depth(v.co) <= 0.0 for v in f.verts)], context='FACES')
# the edge softened: cutting whole faces away left it stepped, so the outline is eased round (each edge point moved
# toward its neighbours along the edge, then the rows just inside after it) and the edge set down onto the meat
for _ in range(6):
    sb.verts.ensure_lookup_table()
    edge = [v for v in sb.verts if v.is_boundary]
    moved = {}
    for v in edge:
        nb = [e.other_vert(v) for e in v.link_edges if e.is_boundary]
        if len(nb) == 2: moved[v] = v.co * 0.4 + (nb[0].co + nb[1].co) * 0.3
    for v, c in moved.items(): v.co = c
inner = {e.other_vert(v) for v in sb.verts if v.is_boundary for e in v.link_edges if not e.other_vert(v).is_boundary}
for _ in range(3):
    for v in inner:
        nb = [e.other_vert(v) for e in v.link_edges]
        v.co = v.co * 0.5 + sum((n.co for n in nb), Vector()) * (0.5 / len(nb))
for v in sb.verts:
    hit, nrm, _, _ = tree.find_nearest(v.co)
    if hit is None: continue
    nrm = nrm if nrm.z > 0 else -nrm
    if v.is_boundary: v.co = hit + nrm * 0.00004                                                       # the edge lying on the meat
    elif (v.co - hit).length < 0.00004: v.co = hit + nrm * 0.00006
snow = obj_from_bm(sb, "snow")
dec = snow.modifiers.new("dec", 'DECIMATE'); dec.ratio = 0.45; apply_mod(snow, dec)          # (the triangle count: the lumps keep their shape at half)
for p in snow.data.polygons: p.use_smooth = True
print(f"SNOW: {len(snow.data.polygons)} faces, lying on the meat")
# ---------------------------------------------------------------- icicles round the edge, tops buried in the meat
bm = bmesh.new()
def surface_below(x, y):
    hit = tree.ray_cast(Vector((x, y, -0.05)), Vector((0, 0, 1)))[0]
    return hit.z if hit is not None else -RZ * 0.8
for k in range(12):
    a = 2 * math.pi * k / 12 + rnd.uniform(-0.15, 0.15)
    if math.sin(a) > 0.7 and k % 2: continue
    x, y = RX * 0.78 * math.cos(a), RY * 0.78 * math.sin(a)
    z0 = surface_below(x, y) + 0.0025                                                                  # its top inside the meat
    ln = rnd.uniform(0.009, 0.017); r0 = rnd.uniform(0.0015, 0.0022); seg = 7; n = 7
    lean = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), 0)) * 0.0007
    rings = []
    for i in range(n):
        t = i / (n - 1); c = Vector((x, y, z0 - ln * t)) + lean * math.sin(math.pi * t)
        rr = r0 * (1 - t) ** 0.9 * (1 + 0.1 * math.sin(i * 2.1 + k)) + r0 * 0.03
        rings.append([bm.verts.new(c + Vector((math.cos(2 * math.pi * s / seg), math.sin(2 * math.pi * s / seg), 0)) * rr * (1 + 0.08 * noise.noise(Vector((s, i, k)))))
                      for s in range(seg)])
    for i in range(n - 1):
        for s in range(seg):
            bm.faces.new((rings[i][s], rings[i][(s + 1) % seg], rings[i + 1][(s + 1) % seg], rings[i + 1][s]))
    tip = bm.verts.new(Vector((x, y, z0 - ln - r0 * 0.6)) + lean * 0.0)
    for s in range(seg): bm.faces.new((rings[-1][s], rings[-1][(s + 1) % seg], tip))
    top = bm.verts.new(Vector((x, y, z0 + r0 * 0.3)))
    for s in range(seg): bm.faces.new((rings[0][(s + 1) % seg], rings[0][s], top))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
ice = obj_from_bm(bm, "ice")
for p in ice.data.polygons: p.use_smooth = True

# ---------------------------------------------------------------- one object, slots, UVs
for name in ("meat", "fat", "snow", "ice"): bpy.data.materials.new(name)
meat.data.materials.append(bpy.data.materials["meat"]); meat.data.materials.append(bpy.data.materials["fat"])
# (the fat marbling is painted into the meat's texture by the bake - per face it came out blocky on the even quads)
snow.data.materials.clear(); snow.data.materials.append(bpy.data.materials["snow"])
ice.data.materials.append(bpy.data.materials["ice"])
for o in SC.objects: o.select_set(o in (meat, snow, ice))
bpy.context.view_layer.objects.active = meat
bpy.ops.object.join()
ob = bpy.context.view_layer.objects.active; ob.name = ob.data.name = "bait"
me = ob.data
for l in list(me.uv_layers): me.uv_layers.remove(l)
grain = me.uv_layers.new(name="Grain")
for p in me.polygons:
    for li in p.loop_indices:
        c = me.vertices[me.loops[li].vertex_index].co; grain.data[li].uv = (c.x, c.y)
atlas = me.uv_layers.new(name="UVMap"); me.uv_layers.active = atlas; atlas.active_render = True
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.004, scale_to_bounds=False)
bpy.ops.uv.pack_islands(margin=0.004); bpy.ops.object.mode_set(mode='OBJECT')
counts = np.bincount([p.material_index for p in me.polygons], minlength=len(me.materials))
co = np.array([v.co for v in me.vertices])
print(f"FROST: {len(me.vertices)} points, {len(me.polygons)} faces, {sum(len(p.vertices) - 2 for p in me.polygons)} triangles; {(co.max(0) - co.min(0)).round(3)} m; " + ", ".join(f"{m.name} {c}" for m, c in zip(me.materials, counts)))
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT); print("SAVED", OUT)
