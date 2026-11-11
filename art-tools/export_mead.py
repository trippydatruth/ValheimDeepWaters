# Exports a mead bottle for the game (build_lures mead, baked by bake_wood_cooler.py VDW_KIND=lure, tier = the buff key):
#   "liquid" - the mead (the key's own texture set, glowing)
#   "glass"  - the bottle's glass, split off so the importer makes it see-through (texture set glass_Unity_*: the bake
#              with its alpha set to VDW_GLASS_ALPHA)
#   "cork"   - the old bottle's cork and twine (Mesh\mead bottle\Models\mead_bottle.fbx), kept with their old texture
#              (set cork_Unity_*): the faces whose texture isn't the green glass, and everything above the lip
# to <VDW_OUT>/<key>/<key>_model.fbx with its textures. New files only.
#   blender -b <bait_<key>_baked.blend> --factory-startup --python export_mead.py
#   env: VDW_KEY (buff_angler_major), VDW_OUT, VDW_GLASS_ALPHA (0.3), VDW_OLD_DIR (Mesh\mead bottle)
import bpy, bmesh, os, shutil, colorsys
import numpy as np
from mathutils import Matrix

KEY = os.environ["VDW_KEY"]; OUT = os.path.join(os.environ["VDW_OUT"], KEY)
ALPHA = float(os.environ.get("VDW_GLASS_ALPHA", "0.3"))
OLD = os.environ.get("VDW_OLD_DIR", r"C:\Users\tripp\Desktop\Valheim_DeepWaters\Mesh\mead bottle")
LIP = 0.262                                              # the top of the new bottle's lip (build_lures mead)
if os.path.exists(OUT): raise SystemExit("exists, kept: " + OUT)
os.makedirs(OUT)
BAKED = os.path.join(os.path.dirname(bpy.data.filepath), "bait_" + KEY)

def flatten(ob):
    for md in list(ob.modifiers): ob.modifiers.remove(md)
    mw = ob.matrix_world.copy(); ob.parent = None
    ob.data.transform(mw); ob.matrix_world = Matrix.Identity(4)
    for vg in list(ob.vertex_groups): ob.vertex_groups.remove(vg)

def one_material(ob, name):
    me = ob.data; me.materials.clear(); me.materials.append(bpy.data.materials.get(name) or bpy.data.materials.new(name))
    for p in me.polygons: p.material_index = 0
    for s in ob.material_slots: s.link = 'DATA'

# the mead and the glass, split
liq = bpy.data.objects["bait"]
for o in list(bpy.data.objects):
    if o is not liq: bpy.data.objects.remove(o)
liq.data = liq.data.copy(); flatten(liq)
me = liq.data
if "Grain" in me.uv_layers: me.uv_layers.remove(me.uv_layers["Grain"])
glass_idx = {i for i, m in enumerate(me.materials) if m and "glass" in m.name}
glass = liq.copy(); glass.data = me.copy(); bpy.context.scene.collection.objects.link(glass)
for ob, keep_glass in ((liq, False), (glass, True)):
    bm = bmesh.new(); bm.from_mesh(ob.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if (f.material_index in glass_idx) != keep_glass], context='FACES')
    bm.to_mesh(ob.data); bm.free()
liq.name = liq.data.name = "liquid"; glass.name = glass.data.name = "glass"
one_material(liq, KEY); one_material(glass, "glass")

def keep_one_uv(ob):
    while len(ob.data.uv_layers) > 1: ob.data.uv_layers.remove(ob.data.uv_layers[-1])

# the old cork and twine: a hand-fixed one as it is (VDW_CORK: a .blend with an object "cork", prep_mead_fixed.py),
# or else cut out of the old bottle
CORK_BLEND = os.environ.get("VDW_CORK", "")
if CORK_BLEND:
    with bpy.data.libraries.load(CORK_BLEND) as (src, dst): dst.objects = ["cork"]
    cork = dst.objects[0]; bpy.context.scene.collection.objects.link(cork)
    cork.data = cork.data.copy(); flatten(cork); keep_one_uv(cork)
    cork.name = cork.data.name = "cork"; one_material(cork, "cork")
def old_cork():
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(OLD, "Models", "mead_bottle.fbx"))
    cork = next(o for o in bpy.data.objects if o not in before and o.type == 'MESH')
    for o in [o for o in bpy.data.objects if o not in before and o is not cork]: bpy.data.objects.remove(o)
    flatten(cork)
    im = bpy.data.images.load(os.path.join(OLD, "Textures", "mead_bottle_Unity_Albedo.png")); W, H = im.size
    px = np.array(im.pixels[:], np.float32).reshape(H, W, 4)
    co = np.array([v.co[:] for v in cork.data.vertices]); cx, cy = co[:, 0].mean(), co[:, 1].mean()
    bm = bmesh.new(); bm.from_mesh(cork.data); ul = bm.loops.layers.uv.active
    def is_glass(f):
        if f.calc_center_median().z > LIP: return False
        u = np.mean([l[ul].uv[0] for l in f.loops]) % 1.0; v = np.mean([l[ul].uv[1] for l in f.loops]) % 1.0
        r, g, b, _ = px[min(H - 1, int(v * H)), min(W - 1, int(u * W))]; h, s, _v = colorsys.rgb_to_hsv(r, g, b)
        return 45 < h * 360 < 150 and s > 0.1
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if is_glass(f)], context='FACES')
    # what's left of the old glass that wasn't green: the flat ring of the old lip (sticking out round the cork like a brim),
    # lone slivers, and two scraps down on the shoulder. Each separate piece is kept only if it's a real part: more than
    # two faces, not flat, and up at the neck or above.
    bm.faces.ensure_lookup_table(); seen = set(); junk = []
    for f in bm.faces:
        if f.index in seen: continue
        grp, stack = [], [f]; seen.add(f.index)
        while stack:
            x = stack.pop(); grp.append(x)
            for e in x.edges:
                for g in e.link_faces:
                    if g.index not in seen: seen.add(g.index); stack.append(g)
        zs = [v.co.z for g in grp for v in g.verts]
        if len(grp) <= 2 or max(zs) - min(zs) < 0.005 or max(zs) < 0.15: junk += grp
    bmesh.ops.delete(bm, geom=junk, context='FACES')
    print(f"EXPORT cork: dropped {len(junk)} faces of old glass scraps")
    bmesh.ops.translate(bm, verts=bm.verts, vec=(-cx, -cy, 0.0))      # the old bottle sat a few mm off centre
    bm.to_mesh(cork.data); bm.free()
    while len(cork.data.uv_layers) > 1: cork.data.uv_layers.remove(cork.data.uv_layers[-1])
    cork.name = cork.data.name = "cork"; one_material(cork, "cork")
    return cork
if not CORK_BLEND: cork = old_cork()
print(f"EXPORT liquid {len(liq.data.polygons)} faces, glass {len(glass.data.polygons)}, cork {len(cork.data.polygons)}")

for o in bpy.data.objects: o.select_set(o.type == 'MESH')
bpy.context.view_layer.objects.active = liq
for o in (liq, glass, cork): o.modifiers.new("tri", 'TRIANGULATE')
path = os.path.join(OUT, f"{KEY}_model.fbx")
bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={'MESH'}, global_scale=1.0, apply_unit_scale=True,
                         apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y', bake_space_transform=True,
                         mesh_smooth_type='FACE', use_mesh_modifiers=True, bake_anim=False, path_mode='COPY', embed_textures=False)
print("EXPORTED", path)

# the textures: the bake as the key's set, a see-through copy for the glass, the old bottle's for the cork
for m in ("Albedo", "Emission", "MetallicSmoothness", "Normal"):
    src = os.path.join(BAKED, f"bait_{KEY}_Unity_{m}.png")
    if os.path.exists(src): shutil.copy(src, os.path.join(OUT, f"{KEY}_Unity_{m}.png"))
    if m in ("MetallicSmoothness", "Normal") and os.path.exists(src): shutil.copy(src, os.path.join(OUT, f"glass_Unity_{m}.png"))
    old = os.path.join(OLD, "Textures", f"mead_bottle_Unity_{m}.png")
    if os.path.exists(old): shutil.copy(old, os.path.join(OUT, f"cork_Unity_{m}.png"))
a = bpy.data.images.load(os.path.join(BAKED, f"bait_{KEY}_Unity_Albedo.png")); w, h = a.size
p = np.array(a.pixels[:], np.float32).reshape(h, w, 4); p[..., 3] = ALPHA
g = bpy.data.images.new("glass_alb", w, h, alpha=True); g.pixels[:] = p.ravel()
g.filepath_raw = os.path.join(OUT, "glass_Unity_Albedo.png"); g.file_format = 'PNG'; g.save()
print("TEXTURES", sorted(os.listdir(OUT)))
