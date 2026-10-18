# Exports the fisherman's gear for Unity, one FBX per equipment slot, flat-shaded (Valheim's faceted look):
#   fisher_chest = shirt + coat, fisher_legs = overalls + boots, fisher_hat = hat
# Each carries "fitref" (the player body as modelled round, so the mod can line the gear up with the game's body mesh)
# and a vertex colour (red) = how much a vertex moves rigidly with one bone (the hat: all of it with the head; the coat's
# skirt more and more with the hips toward the hem).   blender -b fisher_gear_v4.blend --python export_fisher_gear.py
#   env: VDW_OUT (Models folder)
import bpy, os
OUT = os.environ["VDW_OUT"]; os.makedirs(OUT, exist_ok=True)
fit = bpy.data.objects.get("fitref") or bpy.data.objects.get("PlayerCharacter_01")
if fit.name != "fitref":
    me = fit.data.copy(); me.transform(fit.matrix_world); fit = bpy.data.objects.new("fitref", me); bpy.context.scene.collection.objects.link(fit)
fit.hide_set(False); fit.hide_viewport = False
# with a painted rig (build_gear_rig.py): the skeleton goes in the FBX with the gear; the body reference stays a plain mesh
ARM = bpy.data.objects.get("Armature")
if ARM is not None:
    mw = fit.matrix_world.copy(); fit.parent = None; fit.matrix_world = mw
    for m in [m for m in fit.modifiers if m.type == 'ARMATURE']: fit.modifiers.remove(m)
    ARM.hide_set(False)
for o in bpy.data.objects:
    if o.type == 'MESH': o.hide_set(False)
def sm(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0))); return t * t * (3 - 2 * t)
# the coat below the hips follows the hips (not each leg), so its skirt can't stretch between the legs; the mod adds cloth there
RIGID = {"hat": lambda z: 1.0, "coat": lambda z: 0.45 * sm(104.0, 84.0, z)}
# a little more room: the shirt off the body, the coat off the shirt (they clipped slightly as the body moved)
# a little more room, each piece moved away from the body (both walls of the cloth together - pushing along the normals
# drove the inside wall into the body)
INFLATE = {"shirt": float(os.environ.get("VDW_SHIRT_OUT", "0.4")), "overalls": float(os.environ.get("VDW_OVERALLS_OUT", "0.4")),
           "coat": float(os.environ.get("VDW_COAT_OUT", "1.2")), "boots": float(os.environ.get("VDW_BOOTS_OUT", "0"))}
import bmesh as _bm
from mathutils.bvhtree import BVHTree as _BVH
_fb = _bm.new(); _fb.from_mesh(fit.data); _fb.transform(fit.matrix_world); _ft = _BVH.FromBMesh(_fb)
for nm_, by in INFLATE.items():
    o_ = bpy.data.objects[nm_]; b_ = _bm.new(); b_.from_mesh(o_.data); inv = o_.matrix_world.inverted().to_3x3()
    for v in b_.verts:
        p = o_.matrix_world @ v.co; loc, nn, i, dd = _ft.find_nearest(p)
        if loc is None: continue
        away = (p - loc).normalized() if (p - loc).length > 1e-3 else nn
        v.co += inv @ (away * by)
    b_.to_mesh(o_.data); b_.free()
for name in ("shirt", "coat", "overalls", "boots", "hat"):
    ob = bpy.data.objects[name]; me = ob.data
    for p in me.polygons: p.use_smooth = False                      # flat shading
    if "rigid" in me.color_attributes: me.color_attributes.remove(me.color_attributes["rigid"])
    ca = me.color_attributes.new("rigid", 'FLOAT_COLOR', 'POINT'); f = RIGID.get(name, lambda z: 0.0)
    for v in me.vertices:
        r = f((ob.matrix_world @ v.co).z); ca.data[v.index].color = (r, 0.0, 0.0, 1.0)
    me.color_attributes.active_color = ca
    if me.materials: me.materials[0].name = name
    print(f"  {name}: flat shaded, {len(me.polygons)} faces")
# the shirt is only ever worn under the coat: the parts the coat hides go, so it can't poke through it when they move
import bmesh
from mathutils.bvhtree import BVHTree
def bvh(o):
    b = bmesh.new(); b.from_mesh(o.data); b.transform(o.matrix_world); t = BVHTree.FromBMesh(b); b.free(); return t
coat_t, body_t = bvh(bpy.data.objects["coat"]), bvh(fit)
sh = bpy.data.objects["shirt"]; b = bmesh.new(); b.from_mesh(sh.data); b.transform(sh.matrix_world)
hidden = []
for f in b.faces:
    c = f.calc_center_median(); loc, n, _i, d = body_t.find_nearest(c)
    out = (c - loc).normalized() if loc is not None and (c - loc).length > 1e-4 else f.normal
    hits = 0
    for tilt in ((0, 0, 0), (0, 0, 0.35), (0, 0, -0.35), (0.6, 0, 0), (-0.6, 0, 0)):   # straight out, up/down and from either side: covered from all five
        dirn = (out + __import__('mathutils').Vector(tilt)).normalized()
        if coat_t.ray_cast(c + dirn * 0.05, dirn, 9.0)[0] is not None: hits += 1
    if os.environ.get("VDW_SHIRT_TRIM", "1") == "1" and (hits == 5 or abs(c.x) > 21.0): hidden.append(f)          # the sleeves always (the coat's cover the arms)
# and the kept part grown by a few rings of faces on every side, so no gap opens at the coat's edges as it moves
keep = set(b.faces) - set(hidden)
for _ in range(int(os.environ.get("VDW_SHIRT_GROW", "4"))):
    keep |= {o for f in keep for e in f.edges for o in e.link_faces}
hidden = [f for f in hidden if f not in keep or abs(f.calc_center_median().x) > 21.0]
print(f"  shirt: {len(hidden)} of {len(b.faces)} faces hidden under the coat - removed")
bmesh.ops.delete(b, geom=hidden, context='FACES')
b.transform(sh.matrix_world.inverted()); b.to_mesh(sh.data); b.free()
# both sides drawn (VDW_TWO_SIDED, on): Unity's shaders cull back faces, so the inside of the coat, the hat brim's
# underside and the cuffs vanished from behind. Every face gets a reversed copy (same UVs, weights and vertex colour),
# which the back-face culling then shows only from the inside.
if os.environ.get("VDW_TWO_SIDED", "1") == "1":
    for nm_ in ("shirt", "coat", "overalls", "boots", "hat"):
        o_ = bpy.data.objects[nm_]; b_ = bmesh.new(); b_.from_mesh(o_.data); n0 = len(b_.faces)
        dup = bmesh.ops.duplicate(b_, geom=list(b_.faces))
        bmesh.ops.reverse_faces(b_, faces=[g for g in dup["geom"] if isinstance(g, bmesh.types.BMFace)])
        b_.to_mesh(o_.data); b_.free(); o_.data.update()
        print(f"  {nm_}: two-sided, {n0} -> {len(o_.data.polygons)} faces")
# VDW_SPLIT_COAT=1: the coat is its own (cape) item, fisher_coat, and fisher_chest is the shirt alone (the tunic)
SETS = (("fisher_chest", ["shirt"]), ("fisher_coat", ["coat"])) if os.environ.get("VDW_SPLIT_COAT") == "1" else (("fisher_chest", ["shirt", "coat"]),)
for key, parts in SETS + (("fisher_legs", ["overalls", "boots"]), ("fisher_hat", ["hat"])):
    path = os.path.join(OUT, key + os.environ.get("VDW_SUFFIX", "_v2") + ".fbx")
    if os.path.exists(path): print("  exists, kept:", path); continue
    for o in bpy.data.objects: o.select_set(o.name in parts + ["fitref"] + (["Armature"] if ARM is not None else []))
    bpy.context.view_layer.objects.active = bpy.data.objects[parts[0]]
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={'MESH', 'ARMATURE'}, global_scale=1.0, apply_unit_scale=True,
                             add_leaf_bones=False, use_armature_deform_only=False, armature_nodetype='NULL',
                             apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y', bake_space_transform=True,
                             mesh_smooth_type='FACE', bake_anim=False, path_mode='STRIP', embed_textures=False, colors_type='LINEAR')
    print(f"  exported {key}: {parts} + fitref -> {os.path.basename(path)}")
