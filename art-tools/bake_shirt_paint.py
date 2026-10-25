# Bakes a fisherman's gear piece onto the game's own body as a painted-on armour texture (the vanilla way: a chest
# item's material sets _ChestTex on the player body). Colour from the piece's own texture, alpha = where the cloth
# covers the skin (see-through elsewhere).
#   blender -b new_gear_rig.blend --python bake_shirt_paint.py
#   env: VDW_BODY_OBJ   body.obj from "vdw_debug paint dump" (the game body, bind pose, with its UVs)
#        VDW_ALBEDO     the piece's colour map (shirt_Unity_Albedo.png)
#        VDW_PIECE      object to bake (default "shirt")
#        VDW_OUT        output folder (new; never overwrites): <out>/<name>.png, preview_front.png, preview_back.png
#        VDW_NAME       texture name (default fisher_shirt_paint_v1)
#        VDW_SIZE       texture size (default 1024)
import bpy, bmesh, os, itertools, math
from mathutils import Matrix, Vector
from mathutils.kdtree import KDTree

BODY, ALBEDO, OUT = os.environ["VDW_BODY_OBJ"], os.environ["VDW_ALBEDO"], os.environ["VDW_OUT"]
PIECE = os.environ.get("VDW_PIECE", "shirt"); NAME = os.environ.get("VDW_NAME", "fisher_shirt_paint_v1")
SIZE = int(os.environ.get("VDW_SIZE", "1024"))
os.makedirs(OUT, exist_ok=True)
out_png = os.path.join(OUT, NAME + ".png")
if os.path.exists(out_png): raise SystemExit("exists, kept: " + out_png)

arm = bpy.data.objects["Armature"]
for pb in arm.pose.bones: pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.rotation_euler = (0, 0, 0); pb.scale = (1, 1, 1)
bpy.context.view_layer.update()

def world_mesh(o):
    """the object's mesh as it's shown (armature at rest), in world space, as a new plain object"""
    dg = bpy.context.evaluated_depsgraph_get(); e = o.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(e); me.transform(o.matrix_world)
    ob = bpy.data.objects.new(o.name + "_baked", me); bpy.context.scene.collection.objects.link(ob)
    return ob

# --- the game body
bpy.ops.wm.obj_import(filepath=BODY)
body = [o for o in bpy.context.selected_objects if o.type == 'MESH'][0]
body.name = "game_body"
bme = body.data; bme.transform(body.matrix_world); body.matrix_world = Matrix.Identity(4)
bv = [v.co.copy() for v in bme.vertices]
kd = KDTree(len(bv))
for i, v in enumerate(bv): kd.insert(v, i)
kd.balance()

# --- line the rig's copy of the body (fitref) up with the game body: any of the 48 axis turns, scaled and moved by
# the bounding boxes, the best being the one whose points land nearest (as the mod's FisherGear.FitToBody does)
fit = world_mesh(bpy.data.objects["fitref"])
fv = [v.co.copy() for v in fit.data.vertices]
def box(pts):
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))); return lo, hi
blo, bhi = box(bv); bsize = bhi - blo; bc = (blo + bhi) / 2
sample = fv[::max(1, len(fv) // 200)]
best = None
for perm in itertools.permutations(range(3)):
    for signs in itertools.product((1, -1), repeat=3):
        R = Matrix(((0, 0, 0), (0, 0, 0), (0, 0, 0)))
        for r in range(3): R[r][perm[r]] = signs[r]
        t = [R @ p for p in fv]; lo, hi = box(t); s = max(bsize) / max(hi - lo); off = bc - (lo + hi) / 2 * s
        err = sum(kd.find(R @ p * s + off)[2] for p in sample) / len(sample)
        if best is None or err < best[0]: best = (err, R, s, off)
err, R, s, off = best
M = Matrix.Translation(off) @ (R.to_4x4() @ Matrix.Scale(s, 4))
print(f"FIT mean error {err / s * 100:.2f} cm (body units per metre {s:.3f}, mirrored {R.determinant() < 0})")

# --- the piece, in the game body's space
piece = world_mesh(bpy.data.objects[PIECE])
piece.data.transform(M)
if R.determinant() < 0: piece.data.flip_normals()
bpy.data.objects.remove(fit)

# emission materials: the piece shows its colour map (for the colour bake) or plain white (for the coverage mask)
img = bpy.data.images.load(ALBEDO)
def emit_mat(name, image=None):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    o = nt.nodes.new("ShaderNodeOutputMaterial"); e = nt.nodes.new("ShaderNodeEmission")
    if image is not None:
        tx = nt.nodes.new("ShaderNodeTexImage"); tx.image = image; nt.links.new(tx.outputs["Color"], e.inputs["Color"])
    else: e.inputs["Color"].default_value = (1, 1, 1, 1)
    nt.links.new(e.outputs["Emission"], o.inputs["Surface"]); return m
m_col, m_white = emit_mat("bake_colour", img), emit_mat("bake_white")

# the body gets a target image node (active) in its material
def target(name, fill):
    im = bpy.data.images.new(name, SIZE, SIZE, alpha=True, float_buffer=True)
    im.generated_color = fill; return im
col_img, mask_img = target("colour", (0, 0, 0, 1)), target("mask", (0, 0, 0, 1))
bm_mat = bpy.data.materials.new("body_target"); bm_mat.use_nodes = True
tn = bm_mat.node_tree.nodes.new("ShaderNodeTexImage")
bme.materials.clear(); bme.materials.append(bm_mat)

sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 4
bk = sc.render.bake; bk.use_selected_to_active = True; bk.use_cage = False
bk.cage_extrusion = 0.025 * s           # rays start 2.5 cm out from the body...
bk.max_ray_distance = 0.05 * s          # ...and reach 5 cm: the cloth sits 0.1-1 cm off the skin
bk.target = 'IMAGE_TEXTURES'
def bake(mat, image, margin):
    piece.data.materials.clear(); piece.data.materials.append(mat)
    tn.image = image; bm_mat.node_tree.nodes.active = tn
    for o in bpy.data.objects: o.select_set(False)
    piece.select_set(True); body.select_set(True); bpy.context.view_layer.objects.active = body
    bk.margin = margin
    bpy.ops.object.bake(type='EMIT', margin=margin, use_selected_to_active=True, cage_extrusion=bk.cage_extrusion, max_ray_distance=bk.max_ray_distance)
bake(m_white, mask_img, 0)
bake(m_col, col_img, 8)

# --- combine: colour with the mask as alpha (grown a pixel so seams don't show a hairline of skin)
n = SIZE
mpx = list(mask_img.pixels); cpx = list(col_img.pixels)
cov = [mpx[i * 4] for i in range(n * n)]
grown = cov[:]
for y in range(n):
    for x in range(n):
        if cov[y * n + x] >= 0.5: continue
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            xx, yy = x + dx, y + dy
            if 0 <= xx < n and 0 <= yy < n and cov[yy * n + xx] >= 0.5: grown[y * n + x] = 1.0; break
# the bake comes out linear (a float image); the PNG is an ordinary sRGB image, so the colour is converted on the way
# (written as is, every mid-tone came out darker - fisher_shirt_paint_v1)
def to_srgb(c): return c * 12.92 if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055
cpx = [to_srgb(max(0.0, c)) if (i & 3) != 3 else c for i, c in enumerate(cpx)]
out = bpy.data.images.new(NAME, n, n, alpha=True)
px = [0.0] * (n * n * 4)
for i in range(n * n):
    a = 1.0 if grown[i] >= 0.5 else 0.0
    px[i * 4:i * 4 + 3] = cpx[i * 4:i * 4 + 3]; px[i * 4 + 3] = a
out.pixels = px
out.filepath_raw = out_png; out.file_format = 'PNG'; out.save()
covered = sum(1 for g in grown if g >= 0.5)
print(f"BAKED {out_png}: {covered} of {n * n} pixels covered ({covered / (n * n) * 100:.1f}%)")

# --- previews: the body painted with it over a skin colour
pv = bpy.data.images.new("preview", n, n)
skin = (0.55, 0.33, 0.22)
pp = [0.0] * (n * n * 4)
for i in range(n * n):
    a = 1.0 if grown[i] >= 0.5 else 0.0
    for k in range(3): pp[i * 4 + k] = cpx[i * 4 + k] * a + skin[k] * (1 - a)
    pp[i * 4 + 3] = 1
pv.pixels = pp
tn.image = pv
for o in bpy.data.objects:
    if o.type == 'MESH': o.hide_render = o is not body
sc.render.engine = 'BLENDER_WORKBENCH'; sh = sc.display.shading; sh.light = 'STUDIO'; sh.color_type = 'TEXTURE'
sc.render.resolution_x = 600; sc.render.resolution_y = 800
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = max(bsize) * 1.05
up = Vector((0, 0, 1)) if bsize.z == max(bsize) else Vector((0, 1, 0))
depth = [i for i in range(3) if i != (2 if up.z else 1)]
thin = min(depth, key=lambda i: bsize[i])                       # front-to-back is the body's thinnest side
for label, sign in (("front", -1), ("back", 1)):
    d = Vector((0, 0, 0)); d[thin] = sign
    cam.location = bc + d * max(bsize) * 3
    cam.rotation_euler = (-d).to_track_quat('-Z', 'Z' if up.z else 'Y').to_euler()
    sc.render.filepath = os.path.join(OUT, f"preview_{label}.png"); bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, NAME + "_bake.blend"))
print("DONE")
