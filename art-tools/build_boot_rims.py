# The rubber boots' rims as a small model of their own, for the overalls painted onto the body (bake_shirt_paint.py):
# a short cuff round each boot top, standing a little off the leg, skinned like the boots where they meet the overalls.
# Exported like the other gear (export_fisher_gear.py): the cuffs + fitref (the body, for the mod to line it up) + the
# skeleton, in centimetres.
#   blender -b new_gear_rig.blend --python build_boot_rims.py
#   env: VDW_OUT (folder), VDW_NAME (default fisher_boot_rims_v1)
#        VDW_RIM_OUT (cm the cuff stands off the boot, default 0.8), VDW_RIM_DOWN (cm it reaches down, default 3.5)
import bpy, bmesh, os, math
from mathutils import Vector, Matrix

OUT = os.environ["VDW_OUT"]; NAME = os.environ.get("VDW_NAME", "fisher_boot_rims_v1")
OUTW = float(os.environ.get("VDW_RIM_OUT", "0.8")) / 100; DOWN = float(os.environ.get("VDW_RIM_DOWN", "3.5")) / 100
os.makedirs(OUT, exist_ok=True)
path = os.path.join(OUT, NAME + ".fbx")
if os.path.exists(path): raise SystemExit("exists, kept: " + path)
for o in list(bpy.data.objects):
    if o.mode != 'OBJECT' and o.name in bpy.context.view_layer.objects:
        bpy.context.view_layer.objects.active = o; bpy.ops.object.mode_set(mode='OBJECT')
arm = bpy.data.objects["Armature"]
for pb in arm.pose.bones: pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.rotation_euler = (0, 0, 0); pb.scale = (1, 1, 1)
src = bpy.data.objects["overalls"]; me = src.data; M = src.matrix_world
boot = [i for i, m in enumerate(me.materials) if m and m.name.lower().startswith("boot")][0]

bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
uvl = bm.loops.layers.uv.active
# where the boots meet the overalls: edges with a boot face on one side and an overalls face on the other
seam = [e for e in bm.edges if len(e.link_faces) == 2 and len({f.material_index == boot for f in e.link_faces}) == 2]
if not seam: raise SystemExit("no boot/overalls seam found")
groups = {g.index: g.name for g in src.vertex_groups}
def weights(v): return {groups[g.group]: g.weight for g in me.vertices[v.index].groups if g.weight > 0.001}
def boot_uv(v):
    for l in v.link_loops:
        if l.face.material_index == boot: return l[uvl].uv.copy()
    return Vector((0.5, 0.5))

# the body, so the cuff's lip can run in to the skin (the boots stand 1-2 cm off the leg; painted on, there's no boot
# wall there, and from above you'd see down the gap)
from mathutils.bvhtree import BVHTree
_fit = bpy.data.objects["fitref"]; _fb = bmesh.new(); _fb.from_mesh(_fit.data); _fb.transform(_fit.matrix_world)
body_t = BVHTree.FromBMesh(_fb)
out = bmesh.new(); ouv = out.loops.layers.uv.new("UVMap")
dl = out.verts.layers.deform.verify()
names = sorted({n for e in seam for v in e.verts for n in weights(v)})
for side in (1, -1):
    vs = sorted({v for e in seam for v in e.verts if (M @ v.co).x * side > 0}, key=lambda v: v.index)
    if not vs: continue
    pts = [M @ v.co for v in vs]; c = sum(pts, Vector()) / len(pts)
    ring = sorted(zip(vs, pts), key=lambda vp: math.atan2(vp[1].y - c.y, vp[1].x - c.x))   # round the leg
    rows = []
    for v, p in ring:
        o = Vector((p.x - c.x, p.y - c.y, 0)).normalized()
        w = weights(v); uv = boot_uv(v)
        made = []
        skin = body_t.find_nearest(p)[0] or (p - o * 0.002)
        inner = Vector((skin.x, skin.y, p.z)) + o * 0.002           # just off the skin, level with the boot top
        for q in (inner + Vector((0, 0, 0.005)),                  # top, at the skin
                  p + o * OUTW + Vector((0, 0, 0.005)),            # top, outside
                  p + o * (OUTW * 0.8) - Vector((0, 0, DOWN))):    # bottom of the cuff
            nv = out.verts.new(q)
            for n, x in w.items(): nv[dl][names.index(n)] = x
            made.append((nv, uv))
        rows.append(made)
    n = len(rows)
    for i in range(n):
        a, b = rows[i], rows[(i + 1) % n]
        for k in (0, 1):                                            # the lip, then the cuff's face
            quad = [a[k][0], b[k][0], b[k + 1][0], a[k + 1][0]]
            f = out.faces.new(quad)
            for l, (_v, uv) in zip(f.loops, (a[k], b[k], b[k + 1], a[k + 1])): l[ouv].uv = uv
    print(f"RIM side {side}: {n} points round the boot top at z {c.z:.3f}")
bmesh.ops.recalc_face_normals(out, faces=out.faces)
# both sides drawn (back faces are culled in game, and the cuff is open at both ends)
dup = bmesh.ops.duplicate(out, geom=list(out.faces))
bmesh.ops.reverse_faces(out, faces=[g for g in dup["geom"] if isinstance(g, bmesh.types.BMFace)])
rme = bpy.data.meshes.new("boot_rims"); out.to_mesh(rme); out.free(); bm.free()
for p in rme.polygons: p.use_smooth = False
rims = bpy.data.objects.new("boot_rims", rme); bpy.context.scene.collection.objects.link(rims)   # made in world space
for nm in names: rims.vertex_groups.new(name=nm)
mat = bpy.data.materials.get("boots") or bpy.data.materials.new("boots"); rme.materials.append(mat)
print(f"RIMS {len(rme.polygons)} faces, groups {names}")

# into centimetres like the other gear (gear_split_for_export.py), then out: cuffs + fitref (plain mesh) + skeleton
if arm.matrix_world != Matrix.Identity(4): raise SystemExit("the armature isn't at the origin - the cm conversion assumes it is")
for o in list(bpy.data.objects):
    if o not in (arm, rims) and o.name != "fitref": bpy.data.objects.remove(o)
fit = bpy.data.objects["fitref"]
for m in [m for m in fit.modifiers if m.type == 'ARMATURE']: fit.modifiers.remove(m)
fit.data.transform(fit.matrix_world); fit.parent = None; fit.matrix_world = Matrix.Identity(4)
S = Matrix.Scale(100.0, 4)
for o in bpy.data.objects: o.select_set(o == arm)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
for b in arm.data.edit_bones: b.head = S @ b.head; b.tail = S @ b.tail
bpy.ops.object.mode_set(mode='OBJECT')
fit.data.transform(S); rims.data.transform(S)
rims.parent = arm; rims.modifiers.new("Armature", 'ARMATURE').object = arm
for o in bpy.data.objects: o.select_set(True)
bpy.context.view_layer.objects.active = rims
bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={'MESH', 'ARMATURE'}, global_scale=1.0, apply_unit_scale=True,
                         add_leaf_bones=False, use_armature_deform_only=False, armature_nodetype='NULL',
                         apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y', bake_space_transform=True,
                         mesh_smooth_type='FACE', bake_anim=False, path_mode='STRIP', embed_textures=False, colors_type='LINEAR')
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, NAME + ".blend"))
print("EXPORTED", path)
