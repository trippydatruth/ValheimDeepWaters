# Bakes the wrinkles set up in a wrinkle edit blend (make_wrinkle_edit.py: the pieces' own normal maps + the "VDW
# Wrinkles" node) onto the game body as a painted piece's normal map, keeping an existing painted colour as it is (its
# fixes, like the overalls' arms and crotch, stay). Writes <name>.png (the kept colour), <name>_nrm.png and previews.
#   blender -b fisher_wrinkles_edit_vN.blend --python bake_wrinkles.py
#   env: VDW_BODY_OBJ  body.obj from "vdw_debug paint dump"
#        VDW_PIECE     overalls | coat_paint
#        VDW_KEEP      the painted colour to keep (e.g. fisher_overalls_paint_v9.png); its _nrm.png is the "before"
#        VDW_OUT       output folder (new; never overwrites), VDW_NAME texture name
#        VDW_REACH     metres the bake looks out from the body (overalls 0.10, coat 0.08 as their paint bakes)
import bpy, bmesh, os, itertools, shutil, math
import numpy as np
from mathutils import Matrix, Vector
from mathutils.kdtree import KDTree

BODY, PIECE, KEEP, OUT, NAME = (os.environ[k] for k in ("VDW_BODY_OBJ", "VDW_PIECE", "VDW_KEEP", "VDW_OUT", "VDW_NAME"))
REACH = float(os.environ.get("VDW_REACH", "0.10"))
if os.path.exists(os.path.join(OUT, NAME + "_nrm.png")): raise SystemExit("exists, kept: " + OUT)
os.makedirs(OUT, exist_ok=True)
arm = bpy.data.objects["Armature"]; arm.animation_data_clear()
for pb in arm.pose.bones: pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.rotation_euler = (0, 0, 0); pb.scale = (1, 1, 1)
bpy.context.view_layer.update()

# --- the game body, smooth-shaded as the game draws it (as bake_shirt_paint.py)
bpy.ops.wm.obj_import(filepath=BODY)
body = [o for o in bpy.context.selected_objects if o.type == 'MESH'][0]; body.name = "game_body"
bme = body.data; bme.transform(body.matrix_world); body.matrix_world = Matrix.Identity(4)
for p in bme.polygons: p.use_smooth = True
acc = {}
for v in bme.vertices: acc.setdefault(tuple(round(c, 5) for c in v.co), Vector()).__iadd__(v.normal)
bme.normals_split_custom_set_from_vertices([acc[tuple(round(c, 5) for c in v.co)].normalized() for v in bme.vertices])
bv = [v.co.copy() for v in bme.vertices]; kd = KDTree(len(bv))
for i, v in enumerate(bv): kd.insert(v, i)
kd.balance()

def world_mesh(o):
    dg = bpy.context.evaluated_depsgraph_get(); e = o.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(e); me.transform(o.matrix_world)
    ob = bpy.data.objects.new(o.name + "_baked", me); bpy.context.scene.collection.objects.link(ob); return ob
# --- the rig's body copy (fitref) lined up with the game body: the best of the 48 axis turns (as bake_shirt_paint.py)
fit = world_mesh(bpy.data.objects["fitref"]); fv = [v.co.copy() for v in fit.data.vertices]
def box(pts):
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))
blo, bhi = box(bv); bsize = bhi - blo; bc = (blo + bhi) / 2
sample = fv[::max(1, len(fv) // 200)]; best = None
for perm in itertools.permutations(range(3)):
    for signs in itertools.product((1, -1), repeat=3):
        R = Matrix(((0, 0, 0), (0, 0, 0), (0, 0, 0)))
        for r in range(3): R[r][perm[r]] = signs[r]
        t = [R @ p for p in fv]; lo, hi = box(t); s = max(bsize) / max(hi - lo); off = bc - (lo + hi) / 2 * s
        err = sum(kd.find(R @ p * s + off)[2] for p in sample) / len(sample)
        if best is None or err < best[0]: best = (err, R, s, off)
err, R, s, off = best
M = Matrix.Translation(off) @ (R.to_4x4() @ Matrix.Scale(s, 4))
print(f"FIT mean error {err / s * 100:.2f} cm (body units per metre {s:.3f})")
bpy.data.objects.remove(fit)

# --- the piece on the game body, each material's faces its own object (with the piece's own materials, wrinkles and
# all); the wrinkle pattern reads the rest position in metres (vdw_rest), only the fold depth needs the body's units
src = bpy.data.objects[PIECE]
if "vdw_rest" not in src.data.attributes: raise SystemExit("no vdw_rest on " + PIECE + ": not a make_wrinkle_edit.py blend")
piece = world_mesh(src); piece.data.transform(M)
if R.determinant() < 0: piece.data.flip_normals()
for m in bpy.data.materials:
    if not m.use_nodes: continue
    for n in m.node_tree.nodes:
        if n.type == 'GROUP' and n.node_tree and n.node_tree.name == "VDW Wrinkles": n.inputs["Units per metre"].default_value = s
sc = bpy.context.scene; sc.collection.objects.link(piece) if piece.name not in sc.collection.objects else None
parts = []
for mi, mat in enumerate(piece.data.materials):
    me = piece.data.copy(); bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index != mi], context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.to_mesh(me); bm.free()
    if not me.polygons: continue
    me.materials.clear(); me.materials.append(mat)
    for p in me.polygons: p.material_index = 0
    ob = bpy.data.objects.new(f"{PIECE}_part{mi}", me); sc.collection.objects.link(ob); parts.append(ob)
piece.hide_render = True
for o in bpy.data.objects:
    if o.type == 'MESH' and o not in parts and o is not body: o.hide_render = True

keep = bpy.data.images.load(KEEP); n = keep.size[0]
nrm = bpy.data.images.new("normal", n, n, alpha=True, float_buffer=True); nrm.generated_color = (0.5, 0.5, 1, 1)
nrm.colorspace_settings.name = 'Non-Color'
bmat = bpy.data.materials.new("body_target"); bmat.use_nodes = True
tn = bmat.node_tree.nodes.new("ShaderNodeTexImage"); tn.image = nrm; bmat.node_tree.nodes.active = tn
bme.materials.clear(); bme.materials.append(bmat)
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 4
for o in bpy.data.objects: o.select_set(o in parts)
body.select_set(True); bpy.context.view_layer.objects.active = body
bpy.ops.object.bake(type='NORMAL', normal_space='TANGENT', margin=16, use_selected_to_active=True,
                    cage_extrusion=REACH / 2 * s, max_ray_distance=REACH * s)
# flat wherever the kept colour isn't painted (the arms, the skin): only the painted cloth carries folds
ka = np.array(keep.pixels[:], np.float32).reshape(n, n, 4)[:, :, 3]
npx = np.array(nrm.pixels[:], np.float32).reshape(n, n, 4)
npx[ka < 0.01, :3] = (0.5, 0.5, 1.0); npx[:, :, 3] = 1
out = bpy.data.images.new(NAME + "_nrm", n, n, alpha=True); out.colorspace_settings.name = 'Non-Color'
out.pixels = npx.ravel(); out.filepath_raw = os.path.join(OUT, NAME + "_nrm.png"); out.file_format = 'PNG'; out.save()
shutil.copyfile(KEEP, os.path.join(OUT, NAME + ".png"))
print("BAKED", out.filepath_raw, "(colour kept from", os.path.basename(KEEP) + ")")

# --- previews: the game body with the kept colour and the old / new normal map, lit from the side
for o in bpy.data.objects:
    if o.type == 'MESH': o.hide_render = o is not body
pm = bpy.data.materials.new("preview"); pm.use_nodes = True; nt = pm.node_tree
bs = next(x for x in nt.nodes if x.type == 'BSDF_PRINCIPLED'); bs.inputs["Roughness"].default_value = 0.6
skin = nt.nodes.new("ShaderNodeRGB"); skin.outputs[0].default_value = (0.55, 0.33, 0.22, 1)
ct = nt.nodes.new("ShaderNodeTexImage"); ct.image = bpy.data.images.load(os.path.join(OUT, NAME + ".png"))
mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'
nt.links.new(ct.outputs["Alpha"], mix.inputs["Factor"]); nt.links.new(skin.outputs[0], mix.inputs[6]); nt.links.new(ct.outputs["Color"], mix.inputs[7])
nt.links.new(mix.outputs[2], bs.inputs["Base Color"])
nti = nt.nodes.new("ShaderNodeTexImage"); nm = nt.nodes.new("ShaderNodeNormalMap")
nt.links.new(nti.outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], bs.inputs["Normal"])
bme.materials.clear(); bme.materials.append(pm)
sc.render.engine = 'BLENDER_EEVEE' if 'BLENDER_EEVEE' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE_NEXT'
sc.render.resolution_x, sc.render.resolution_y = 450, 800
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; w.node_tree.nodes["Background"].inputs[1].default_value = 0.25
up = (M.to_3x3() @ Vector((0, 0, 1))).normalized(); fwd = (M.to_3x3() @ Vector((0, -1, 0))).normalized(); side = fwd.cross(up)
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", 'SUN')); sc.collection.objects.link(sun); sun.data.energy = 4
ld = (fwd * 0.5 + side * 0.8 + up * 0.5).normalized(); sun.rotation_euler = (-ld).to_track_quat('-Z', 'Y').to_euler()
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
big = max(bsize); cam.data.type = 'ORTHO'; cam.data.ortho_scale = big * 0.6; cam.data.clip_start = big * 0.01; cam.data.clip_end = big * 20
before = KEEP[:-4] + "_nrm.png"
for label, path in (("before", before), ("after", out.filepath_raw)):
    if not os.path.exists(path): continue
    nti.image = bpy.data.images.load(path); nti.image.colorspace_settings.name = 'Non-Color'
    for view, d in (("front", fwd), ("side", (fwd + side).normalized()), ("back", -fwd)):
        ld = (d * 0.5 + d.cross(up).normalized() * -0.8 + up * 0.5).normalized()        # lit from the viewer's side, raking
        sun.rotation_euler = (-ld).to_track_quat('-Z', 'Y').to_euler()
        cam.location = bc + d * big * 3 - up * big * (0.15 if PIECE == "overalls" else -0.15)
        cam.rotation_euler = (-d).to_track_quat('-Z', 'Y' if abs(up.y) > 0.5 else 'Z').to_euler()
        zf = d; xr = up.cross(zf).normalized(); yu = zf.cross(xr)
        loc = cam.location.copy(); cam.matrix_world = Matrix((xr, yu, zf)).transposed().to_4x4(); cam.location = loc
        sc.render.filepath = os.path.join(OUT, f"preview_{label}_{view}.png"); bpy.ops.render.render(write_still=True)
print("DONE")
