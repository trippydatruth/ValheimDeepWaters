# Re-bakes a rigged fish's Unity albedo and normal maps straight from the full-detail source (saved by
# prep_sourced_fish.py with VDW_SAVE_HI), onto the fish's CURRENT UV layout - for faces the first bake missed (they came
# out blank/white), or after the mesh was edited or rigged. The source is lined up with the rigged mesh by matching the
# prep mesh (rig_fish re-centres and resizes): uniform scale from the lengths, offset from the means.
# Overwrites the images the material already uses (the pipeline's own maps) and saves the .blend in place or to VDW_SAVE_TO.
#   blender -b fish_seams.blend --python rebake_from_source.py
#   env: VDW_HI (the VDW_SAVE_HI .blend), VDW_PREP (the prep .blend the rig was built from), VDW_SAVE_TO,
#        VDW_CAGE (cage / ray reach, share of the length; 0.02 / 0.06)
import bpy, os
import numpy as np
from mathutils import Matrix, Vector
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
mesh = next(o for o in bpy.data.objects if o.type == 'MESH' and o.parent == arm)
arm.data.pose_position = 'REST'; bpy.context.view_layer.update()
CAGE = float(os.environ.get("VDW_CAGE", "0.02"))
def coords_of(path):
    with bpy.data.libraries.load(path) as (src, dst): dst.meshes = list(src.meshes)
    m = max(dst.meshes, key=lambda m: len(m.vertices)); a = np.array([v.co[:] for v in m.vertices])
    for x in dst.meshes: bpy.data.meshes.remove(x)
    return a
prep = coords_of(os.environ["VDW_PREP"])
cur = np.array([(mesh.matrix_world @ v.co)[:] for v in mesh.data.vertices])
s = (cur[:, 1].max() - cur[:, 1].min()) / (prep[:, 1].max() - prep[:, 1].min())
off = cur.mean(0) - s * prep.mean(0)
print(f"  lining the source up: scale {s:.4f}, offset {tuple(off.round(4))}")
with bpy.data.libraries.load(os.environ["VDW_HI"]) as (src, dst): dst.objects = [n for n in src.objects if n == "hi_source"]
hi = dst.objects[0]; bpy.context.scene.collection.objects.link(hi)
hi.matrix_world = Matrix.Translation(Vector(off.tolist())) @ Matrix.Diagonal((s, s, s, 1))
L = float(cur[:, 1].max() - cur[:, 1].min())
nt = mesh.data.materials[0].node_tree; N = nt.nodes
bs = next(n for n in N if n.type == 'BSDF_PRINCIPLED')
alb = bs.inputs["Base Color"].links[0].from_node.image
nrm = next(n for n in N if n.type == 'NORMAL_MAP').inputs["Color"].links[0].from_node.image
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 4
bk = sc.render.bake; bk.use_selected_to_active = True; bk.cage_extrusion = CAGE * L; bk.max_ray_distance = 3 * CAGE * L
bk.margin = 16; bk.use_clear = True; bk.normal_space = 'TANGENT'
for o in bpy.context.view_layer.objects: o.select_set(o in (hi, mesh))
bpy.context.view_layer.objects.active = mesh
def bake_to(img, kind, **kw):
    t = N.new("ShaderNodeTexImage"); t.image = img
    for n in N: n.select = False
    t.select = True; N.active = t
    bpy.ops.object.bake(type=kind, **kw); N.remove(t)
bake_to(alb, 'DIFFUSE', pass_filter={'COLOR'}); print("  baked albedo from the source")
bake_to(nrm, 'NORMAL'); print("  baked normals from the source")
# VDW_FILL_WHITE=1: photo-scans show the white backdrop where their pieces overlap (strips along the back and belly);
# near-white, colourless texels are treated as missing and filled from the surrounding scales
if os.environ.get("VDW_FILL_WHITE") == "1":
    W, H = alb.size; a = np.empty(W * H * 4, np.float32); alb.pixels.foreach_get(a); a = a.reshape(H, W, 4)
    mx, mn = a[..., :3].max(-1), a[..., :3].min(-1)
    bad = (mn > float(os.environ.get("VDW_WHITE_MIN", "0.78"))) & ((mx - mn) < 0.10)
    n_bad = int(bad.sum())
    for _ in range(96):
        if not bad.any(): break
        acc = np.zeros((H, W, 3), np.float32); cnt = np.zeros((H, W), np.float32)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
            ok = ~np.roll(np.roll(bad, dy, 0), dx, 1) & (np.roll(np.roll(a[..., :3].max(-1), dy, 0), dx, 1) > 0.02)
            acc += np.roll(np.roll(a[..., :3], dy, 0), dx, 1) * ok[..., None]; cnt += ok
        fill = bad & (cnt > 0); a[fill, :3] = acc[fill] / cnt[fill, None]; bad &= ~fill
    alb.pixels.foreach_set(a.ravel()); print(f"  white backdrop texels filled: {n_bad}")
for img in (alb, nrm):
    img.save(); print("  saved", bpy.path.abspath(img.filepath))
# how many faces still came out blank
W, H = alb.size; px = np.empty(W * H * 4, np.float32); alb.pixels.foreach_get(px); px = px.reshape(H, W, 4)
uvl = mesh.data.uv_layers.active.data; blank = 0
for p in mesh.data.polygons:
    u = np.mean([uvl[i].uv[:] for i in p.loop_indices], 0)
    if px[int(min(H - 1, u[1] * H)), int(min(W - 1, u[0] * W)), :3].max() < 0.02: blank += 1
print(f"  faces still blank: {blank} of {len(mesh.data.polygons)}")
bpy.data.objects.remove(hi); bk.use_selected_to_active = False
arm.data.pose_position = 'POSE'; sc.render.engine = 'BLENDER_EEVEE_NEXT'
bpy.ops.wm.save_as_mainfile(filepath=os.environ.get("VDW_SAVE_TO") or bpy.data.filepath); print("  saved blend")
