# Hangs lures off a static box model (Hildir's lost tackle boxes): each lure's own model (Assets/DeepWaters/
# bait_lure_<id>/bait_lure_<id>_model.fbx) on a short line hooked over the lid's edge - one down the front, one down an
# end - kept as its own object named after the lure, so the importer gives it the lure's own texture set (copy
# bait_lure_<id>_Unity_*.png into the box's folder). The lines are an object "fishing_line" with a tiny texture set of
# their own, written next to the blend (fishing_line_Unity_*.png). On a rigged box (a lid that opens) the lines hook
# onto the rim under the lid instead, and the lures and line are bound to the "root" bone so they stay on the body.
#   blender -b tacklebox_<k>.blend --factory-startup --python hang_lures.py
#   env: VDW_ASSETS (Assets/DeepWaters), VDW_LURES ("guck_crawler,ooze"), VDW_OUT (new .blend), VDW_LURE_SCALE (1.4)
import bpy, bmesh, os, math
import numpy as np
from mathutils import Vector, Matrix

ASSETS, OUT = os.environ["VDW_ASSETS"], os.environ["VDW_OUT"]
LURES = os.environ["VDW_LURES"].split(","); LS = float(os.environ.get("VDW_LURE_SCALE", "1.4"))
if os.path.exists(OUT): raise SystemExit("exists, kept: " + OUT)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
box = bpy.data.objects["tacklebox"]
co = np.array([box.matrix_world @ v.co for v in box.data.vertices])
lo, hi = co.min(0), co.max(0)
# the lid's lower edge: the lowest point of the lid planks' front, read from the lid bone's weights
lid_g = box.vertex_groups.get("lid")
lid_z = [ (box.matrix_world @ v.co).z for v in box.data.vertices if lid_g and any(g.group == lid_g.index and g.weight > 0.5 for g in v.groups)]
LID0 = float(np.percentile(lid_z, 2)) if lid_z else hi[2] - 0.04
# the body's front and end faces (below the lid's overhang), for the lures to lie against
body = co[co[:, 2] < LID0 - 0.01]; front_y, end_x = float(np.percentile(body[:, 1], 0.5)), float(np.percentile(body[:, 0], 99.5))
RIG = box.parent if box.parent and box.parent.type == 'ARMATURE' and os.environ.get("VDW_RIGGED", "1") == "1" else None
HOOK_Z = LID0 - 0.006 if RIG else LID0          # rigged: hooked on the rim just under the lid, so the lid opens free of it
# where each hangs: (top of the line, which way out)
SPOTS = [((-0.07 if len(LURES) > 1 else 0.08, front_y - 0.002, HOOK_Z), (0, -1, 0)), ((end_x + 0.002, -0.03, HOOK_Z), (1, 0, 0))]
def bind(o):
    """on a rigged box: the object follows the root bone (the body)"""
    if RIG is None: return
    g = o.vertex_groups.new(name="root"); g.add(list(range(len(o.data.vertices))), 1.0, 'REPLACE')
    o.parent = RIG; md = o.modifiers.new("Armature", 'ARMATURE'); md.object = RIG
line_bm = bmesh.new()
def line(a, b, r=0.0009):
    a, b = Vector(a), Vector(b); d = b - a
    t = bmesh.new(); bmesh.ops.create_cone(t, cap_ends=True, segments=6, radius1=r, radius2=r, depth=d.length)
    q = Vector((0, 0, 1)).rotation_difference(d.normalized())
    bmesh.ops.transform(t, matrix=Matrix.Translation((a + b) / 2) @ q.to_matrix().to_4x4(), verts=t.verts)
    m = bpy.data.meshes.new("t"); t.to_mesh(m); t.free(); line_bm.from_mesh(m); bpy.data.meshes.remove(m)
for k, lure in enumerate(LURES):
    key = f"bait_lure_{lure}"
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(ASSETS, key, key + "_model.fbx"))
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == 'MESH']
    for o in new:
        if o.type != 'MESH': bpy.data.objects.remove(o)
    for o in meshes:                      # bake each mesh's transform into it, then join them into one object
        mw = o.matrix_world.copy(); o.parent = None; o.data.transform(mw); o.matrix_world = Matrix.Identity(4)
        for md in list(o.modifiers): o.modifiers.remove(md)
    for o in bpy.data.objects: o.select_set(o in meshes)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1: bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active; ob.name = key; ob.data.name = key
    v = np.array([p.co[:] for p in ob.data.vertices]); c = (v.min(0) + v.max(0)) / 2; size = v.max(0) - v.min(0)
    ax = int(np.argmax(size))                                   # the lure's length, turned to hang straight down
    rot = Matrix.Identity(3)
    if ax == 0: rot = Matrix.Rotation(math.radians(90), 3, 'Y')
    elif ax == 1: rot = Matrix.Rotation(math.radians(-90), 3, 'X')
    ob.data.transform(Matrix.Translation(-Vector(c)))
    ob.data.transform((rot * LS).to_4x4())
    (sx, sy, sz), out = SPOTS[k % len(SPOTS)]
    v = np.array([p.co[:] for p in ob.data.vertices]); ext = v.max(0) - v.min(0)
    # its flat side to the box: the thinner of its two short sides points out from the wall
    out_axis = 0 if out[0] != 0 else 1
    if ext[out_axis] > ext[1 - out_axis]: ob.data.transform(Matrix.Rotation(math.radians(90), 4, 'Z'))
    v = np.array([p.co[:] for p in ob.data.vertices]); ext = v.max(0) - v.min(0); top = v[:, 2].max()
    drop = 0.03 + 0.01 * k                                      # line length below the lid's edge
    out_v = Vector(out); off = ext[out_axis] / 2 + 0.004       # lying against the boards, just clear of them
    hang = Vector((sx, sy, sz - drop)) + out_v * off
    ob.data.transform(Matrix.Translation(hang - Vector((0, 0, top))))
    # the line: hooked over the edge (the lid's, or the rim's under the lid), down to the lure's eye
    edge_top = Vector((sx, sy, sz + (0.002 if RIG else 0.006))); line(edge_top - out_v * 0.012, edge_top + out_v * 0.002); line(edge_top + out_v * 0.002, hang)
    bind(ob)
    print(f"LURE {key}: {size.round(3)} m at {tuple(round(x, 3) for x in hang)}")
lm = bpy.data.meshes.new("fishing_line"); line_bm.to_mesh(lm); line_bm.free()
lo_ = bpy.data.objects.new("fishing_line", lm); bpy.context.scene.collection.objects.link(lo_)
uv = lm.uv_layers.new(name="UVMap")
for d in uv.data: d.uv = (0.5, 0.5)
mat = bpy.data.materials.new("fishing_line"); lm.materials.append(mat); bind(lo_)
# the line's texture set: dark, a little shiny
folder = os.path.dirname(OUT)
for name, rgba in (("Albedo", (0.06, 0.06, 0.05, 1)), ("MetallicSmoothness", (0, 0, 0, 0.55)), ("Normal", (0.5, 0.5, 1, 1))):
    im = bpy.data.images.new(f"fishing_line_Unity_{name}", 4, 4, alpha=True)
    if name != "Albedo": im.colorspace_settings.name = 'Non-Color'
    im.pixels = list(rgba) * 16; im.filepath_raw = os.path.join(folder, f"fishing_line_Unity_{name}.png"); im.file_format = 'PNG'; im.save()
bpy.ops.wm.save_as_mainfile(filepath=OUT, copy=True)
print("SAVED", OUT)
