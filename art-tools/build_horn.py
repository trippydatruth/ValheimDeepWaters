# The Horn of Aegir: one horn from viking_horns.glb (VDW_PICK: the mesh name), scaled to VDW_LENGTH metres along its
# length, with its narrow end (the mouthpiece) at the origin and the bell pointing -Y (forward, +Z in Unity), its
# curve rising upward. Unity maps from the glTF material: albedo, metallic/smoothness (glTF G = roughness,
# B = metallic), normal. Saves a .blend; export with export_static.py.
# env: VDW_GLB, VDW_PICK, VDW_LENGTH (0.6), VDW_NAME, VDW_TEX_OUT, VDW_SAVE_TO
import bpy, os
import numpy as np
from mathutils import Matrix, Vector

NAME = os.environ["VDW_NAME"]; OUT = os.environ["VDW_TEX_OUT"]; LENGTH = float(os.environ.get("VDW_LENGTH", "0.6"))
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
bpy.ops.import_scene.gltf(filepath=os.environ["VDW_GLB"])
keep = bpy.data.objects[os.environ["VDW_PICK"]]
for o in list(bpy.data.objects):
    if o is not keep: bpy.data.objects.remove(o)
keep.data.transform(keep.matrix_world); keep.parent = None; keep.matrix_world = Matrix()
keep.name = NAME; keep.data.name = NAME
co = np.array([v.co[:] for v in keep.data.vertices])
ax = int(np.argmax(np.ptp(co, 0)))                                  # the long axis
lo, hi = co[:, ax].min(), co[:, ax].max()
def width_at(end):
    sel = co[np.abs(co[:, ax] - end) < 0.06 * (hi - lo)]; o = [i for i in range(3) if i != ax]
    return np.ptp(sel[:, o[0]]) * np.ptp(sel[:, o[1]])
narrow_lo = width_at(lo) < width_at(hi)
tip = lo if narrow_lo else hi
tip_pts = co[np.abs(co[:, ax] - tip) < 0.03 * (hi - lo)]; tip_c = tip_pts.mean(0)
# map: long axis -> -Y (bell forward), narrow end at the origin; the curve's bulge -> +Z (up)
sgn = 1 if narrow_lo else -1                                         # direction from the tip to the bell along ax
long_v = np.zeros(3); long_v[ax] = sgn
mid = co[np.abs(co[:, ax] - (lo + hi) / 2) < 0.05 * (hi - lo)].mean(0)
bulge = mid - tip_c; bulge -= long_v * bulge.dot(long_v); bulge /= max(np.linalg.norm(bulge), 1e-6)
side = np.cross(long_v, bulge)
src = Matrix((Vector(long_v), Vector(bulge), Vector(side))).transposed()      # columns in model space
dst = Matrix((Vector((0, -1, 0)), Vector((0, 0, 1)), Vector((0, 0, 1)).cross(Vector((0, -1, 0))))).transposed()
R = (dst @ src.inverted()).to_4x4()
s = LENGTH / (hi - lo)
keep.data.transform(Matrix.Scale(s, 4) @ R @ Matrix.Translation(Vector((-tip_c).tolist())))
keep.data.update()
c2 = np.array([v.co[:] for v in keep.data.vertices])
print(f"HORN {NAME}: {len(c2)} verts, {np.ptp(c2, 0).round(3)} m, mouthpiece at origin, bell toward -Y")

# Unity maps from the material's images
mat = keep.data.materials[0]; nt = mat.node_tree; bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
def img_into(socket):
    for l in nt.links:
        if l.to_socket == socket:
            n = l.from_node
            while n.type != 'TEX_IMAGE' and n.inputs:
                ls = [k for k in nt.links if k.to_node == n]
                if not ls: break
                n = ls[0].from_node
            if n.type == 'TEX_IMAGE': return n.image
    return None
def px(img):
    w, h = img.size; return np.array(img.pixels[:], np.float32).reshape(h, w, 4), w, h
def save(arr, w, h, kind):
    im = bpy.data.images.new(f"{NAME}_Unity_{kind}", w, h, alpha=True); im.pixels[:] = arr.ravel()
    p = os.path.join(OUT, f"{NAME}_Unity_{kind}.png"); im.filepath_raw = p; im.file_format = 'PNG'; im.save(); print("MAP", os.path.basename(p))
os.makedirs(OUT, exist_ok=True)
alb = img_into(bsdf.inputs["Base Color"]); a, w, h = px(alb); a[..., 3] = 1; save(a, w, h, "Albedo")
mr = img_into(bsdf.inputs["Roughness"]) or img_into(bsdf.inputs["Metallic"])
if mr:
    m, w2, h2 = px(mr); ms = np.zeros_like(m); ms[..., :3] = m[..., 2:3]; ms[..., 3] = 1 - m[..., 1]; save(ms, w2, h2, "MetallicSmoothness")
nrm = img_into(bsdf.inputs["Normal"])
if nrm: n_, w3, h3 = px(nrm); save(n_, w3, h3, "Normal")
bpy.ops.wm.save_as_mainfile(filepath=os.environ["VDW_SAVE_TO"])
print("SAVED", os.environ["VDW_SAVE_TO"])
