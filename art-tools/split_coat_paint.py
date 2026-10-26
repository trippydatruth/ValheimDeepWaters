# Splits the (wrapped) coat into the part painted onto the body and the part kept as a model:
#   coat_paint  the sleeves and the upper body - baked onto the body (bake_shirt_paint.py, VDW_PIECE=coat_paint)
#   coat        the collar and the skirt from the waist down - exported as the worn model (fisher_coat_skirt)
# The two overlap in a band at the waist, so no gap shows between paint and model.
#   blender -b new_gear_rig_coatwrap_vN.blend --python split_coat_paint.py
#   env: VDW_SAVE_TO (new .blend), VDW_PAINT_FROM / VDW_MODEL_TO (m above the hips: paint above, model below; 0.14 / 0.24)
import bpy, bmesh, os

SAVE = os.environ["VDW_SAVE_TO"]
if os.path.exists(SAVE): raise SystemExit("exists, kept: " + SAVE)
arm = bpy.data.objects["Armature"]; coat = bpy.data.objects["coat"]; M = coat.matrix_world
hips = (arm.matrix_world @ arm.data.bones["Hips"].head_local).z
PAINT_FROM = hips + float(os.environ.get("VDW_PAINT_FROM", "0.14"))
MODEL_TO = hips + float(os.environ.get("VDW_MODEL_TO", "0.24"))
shoulder_z = max((arm.matrix_world @ arm.data.bones[b].head_local).z for b in ("LeftArm", "RightArm"))
COLLAR_FROM = shoulder_z + float(os.environ.get("VDW_COLLAR_FROM", "0.04"))
NECK_Z = (arm.matrix_world @ arm.data.bones["Neck"].head_local).z + float(os.environ.get("VDW_NECK_PAINT", "0.01"))
names = {g.index: g.name for g in coat.vertex_groups}
# which part of the body a collar face lies over: painted over the shoulders and upper back, not over the neck
from mathutils.kdtree import KDTree
_fit = bpy.data.objects["fitref"]; _fn = {g.index: g.name for g in _fit.vertex_groups}
_fkd = KDTree(len(_fit.data.vertices))
for _v in _fit.data.vertices: _fkd.insert(_fit.matrix_world @ _v.co, _v.index)
_fkd.balance()
def over_neck(p):
    hits = _fkd.find_n(p, 3); w = 0.0
    for _co, i, _d in hits:
        w += sum(g.weight for g in _fit.data.vertices[i].groups if _fn[g.group] in ("Neck", "Head", "Jaw"))
    return w / max(1, len(hits)) > 0.5
def w(v, pred): return sum(g.weight for g in coat.data.vertices[v.index].groups if pred(names[g.group]))
ARM = lambda n: any(k in n for k in ("Arm", "ForeArm", "Hand")) and not n.endswith("Shoulder")

bm = bmesh.new(); bm.from_mesh(coat.data); bm.verts.ensure_lookup_table()
paint, model = set(), set()
for f in bm.faces:
    collar = any(w(v, lambda n: n == "Neck") > 0.1 for v in f.verts)
    sleeve = sum(w(v, ARM) for v in f.verts) / len(f.verts) > 0.5
    z = (M @ f.calc_center_median()).z
    # the collar stays a model, and is painted too: where it meets the shoulders the paint fills under it (painted
    # without it, a strip of skin showed across the upper back)
    # only the collar itself stays a model (above the shoulders); its lower part on the shoulders is painted only
    # the part above it isn't painted as well: the collar stands off the neck, so its painted copy showed as a yellow
    # band on the neck under it
    # (painted only below the base of the neck, where it lies on the shoulders and upper back - left out entirely, a
    # strip of skin showed across the upper back)
    if collar:
        if z > COLLAR_FROM: model.add(f.index)
        paint.add(f.index)      # all painted; the bake cuts the paint along the collar's lower edge (VDW_NECKLINE)
        continue
    if sleeve: paint.add(f.index); continue
    if z > PAINT_FROM: paint.add(f.index)
    if z < MODEL_TO: model.add(f.index)
bm.free()

def keep_only(ob, faces):
    b = bmesh.new(); b.from_mesh(ob.data); b.faces.ensure_lookup_table()
    bmesh.ops.delete(b, geom=[f for f in b.faces if f.index not in faces], context='FACES')
    bmesh.ops.delete(b, geom=[v for v in b.verts if not v.link_faces], context='VERTS')
    b.to_mesh(ob.data); b.free(); ob.data.update()
cp = coat.copy(); cp.data = coat.data.copy(); cp.name = "coat_paint"; cp.data.name = "coat_paint"
bpy.context.scene.collection.objects.link(cp)
keep_only(cp, paint); keep_only(coat, model)
# the collar reaches down to the paint: its lower edge (where the faces painted only were cut off) is pulled in to the
# skin, so it meets the painted coat instead of floating above it
from mathutils.bvhtree import BVHTree
fit = bpy.data.objects["fitref"]; fb = bmesh.new(); fb.from_mesh(fit.data); fb.transform(fit.matrix_world); ft = BVHTree.FromBMesh(fb)
TUCK = float(os.environ.get("VDW_COLLAR_TUCK", "0.3")) / 100
b = bmesh.new(); b.from_mesh(coat.data); Mi = M.inverted(); tucked = 0
for v in b.verts:
    p = M @ v.co
    if p.z < MODEL_TO + 0.05 or not any(e.is_boundary for e in v.link_edges): continue      # the collar's edges only
    if p.z > COLLAR_FROM + 0.04: continue                                                     # its bottom edge, not its top
    loc, n, _i, d = ft.find_nearest(p)
    if loc is None: continue
    v.co = Mi @ (loc + n * TUCK); tucked += 1
b.to_mesh(coat.data); b.free(); coat.data.update()
print(f"TUCKED {tucked} points of the collar's lower edge in to the skin")
print(f"SPLIT hips {hips:.3f}: painted {len(paint)} faces (sleeves + body above {PAINT_FROM:.2f} m), "
      f"model {len(model)} faces (collar + skirt below {MODEL_TO:.2f} m)")
bpy.ops.wm.save_as_mainfile(filepath=SAVE, copy=True)
print("SAVED", SAVE)
