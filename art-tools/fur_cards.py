# Hair cards for a rigged rod's fur grip (the Ice Fishing Rod, build_lures.py ice_rod -> rig_rod2.py): small curved
# planes rooted round the grip in staggered rows, lying back toward the butt and lifting a little at the tips, each
# one both ways round, all on the stiff Rod.Handle bone. Their texture is the user's hair-card sheet (8 clumps on
# black: an albedo, a normal map and an alpha mask); each card takes one clump, found from the mask, its root at the
# clump's top. The albedo is turned to wolf grey. The cards are a mesh of their own, "fur", with their own maps
# (fur_Unity_*), which the importer cuts out by alpha. Saves a new .blend, the FBX (armature, rod and fur) and,
# with VDW_PREVIEW, renders it.
#   blender -b <rod>_rigged.blend --factory-startup --python fur_cards.py
#   env: VDW_SHEET (folder with the sheet: albedo.jpg, normal.jpg, alpha.jpg), VDW_TEX_OUT (where fur_Unity_* go),
#        VDW_SAVE_TO (.blend), VDW_FBX, VDW_Z0 / VDW_Z1 (the fur's span up the rod, m), VDW_R (the grip's radius under it),
#        VDW_ROWS (6), VDW_PER_ROW (16), VDW_PREVIEW (png, optional),
#        VDW_FUR_DARK / VDW_FUR_LIGHT (the fur's colour range, "r,g,b"; the Ice Rod: the Elaking's sandy grey-tan coat)
import bpy, bmesh, os, math
import numpy as np
from mathutils import Vector

SHEET = os.environ["VDW_SHEET"]; TEX = os.environ["VDW_TEX_OUT"]
for p in (os.environ["VDW_SAVE_TO"], os.environ["VDW_FBX"]):
    if os.path.exists(p): raise SystemExit("exists, kept: " + p)
Z0, Z1, R = float(os.environ.get("VDW_Z0", "0.06")), float(os.environ.get("VDW_Z1", "0.205")), float(os.environ.get("VDW_R", "0.0205"))
ROWS, PER = int(os.environ.get("VDW_ROWS", "6")), int(os.environ.get("VDW_PER_ROW", "16"))
rng = np.random.default_rng(31)

def load(name):
    im = bpy.data.images.load(os.path.join(SHEET, name)); w, h = im.size
    return np.array(im.pixels[:], np.float32).reshape(h, w, 4)   # (bottom row first, as UVs run)
def save(px, kind):
    h, w = px.shape[:2]; im = bpy.data.images.new(f"fur_{kind}", w, h, alpha=True); im.pixels[:] = np.clip(px, 0, 1).ravel()
    path = os.path.join(TEX, f"fur_Unity_{kind}.png"); im.filepath_raw = path; im.file_format = 'PNG'; im.save(); return path

# ---- the maps: wolf grey albedo with the mask in its alpha, the sheet's normals, low smoothness
os.makedirs(TEX, exist_ok=True)
alb, nrm, msk = load("albedo.jpg"), load("normal.jpg"), load("alpha.jpg")
H, W = msk.shape[:2]
a = msk[..., :3].mean(-1)
lum = alb[..., :3] @ np.array([0.3, 0.59, 0.11], np.float32)
lo, hi = np.percentile(lum[a > 0.5], [5, 95])
g = np.clip((lum - lo) / max(hi - lo, 1e-3), 0, 1)                       # the sheet's shading, 0 - 1
# ... laid between the fur's dark and light colours (VDW_FUR_DARK / VDW_FUR_LIGHT, "r,g,b" as stored; default wolf grey)
dark = np.array([float(x) for x in os.environ.get("VDW_FUR_DARK", "0.27,0.28,0.29").split(",")], np.float32)
light = np.array([float(x) for x in os.environ.get("VDW_FUR_LIGHT", "0.76,0.77,0.80").split(",")], np.float32)
out = np.zeros_like(alb); out[..., :3] = dark + (light - dark) * g[..., None]; out[..., 3] = a
p_alb = save(out, "Albedo")
p_nrm = save(np.concatenate([nrm[..., :3], np.ones((H, W, 1), np.float32)], -1), "Normal")
ms = np.zeros_like(alb); ms[..., 3] = 0.22; p_ms = save(ms, "MetallicSmoothness")

# ---- the clumps: joined patches of the mask, found on a coarse grid
k = 8; small = a[:H - H % k, :W - W % k].reshape(H // k, k, W // k, k).max((1, 3)) > 0.3
lab = np.zeros(small.shape, int); boxes = []
for y0 in range(small.shape[0]):
    for x0 in range(small.shape[1]):
        if not small[y0, x0] or lab[y0, x0]: continue
        n = len(boxes) + 1; st = [(y0, x0)]; lab[y0, x0] = n; ys, xs = [], []
        while st:
            y, x = st.pop(); ys.append(y); xs.append(x)
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                yy, xx = y + dy, x + dx
                if 0 <= yy < small.shape[0] and 0 <= xx < small.shape[1] and small[yy, xx] and not lab[yy, xx]:
                    lab[yy, xx] = n; st.append((yy, xx))
        boxes.append((min(xs) * k / W, (max(xs) + 1) * k / W, min(ys) * k / H, (max(ys) + 1) * k / H, len(ys)))
boxes = [b for b in boxes if b[4] > 0.01 * small.size]
print(f"FUR: {len(boxes)} clumps in the sheet")

# ---- the cards
bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
COLS = 5
for row in range(ROWS):
    for j in range(PER):
        u0, u1, v0, v1, _ = boxes[rng.integers(len(boxes))]
        aspect = (u1 - u0) * W / max((v1 - v0) * H, 1)
        ln = rng.uniform(0.038, 0.05); wd = float(np.clip(ln * aspect, 0.014, 0.05))
        th = 2 * math.pi * (j + 0.5 * (row % 2)) / PER + rng.uniform(-0.1, 0.1)
        zr = Z1 - (Z1 - Z0 - 0.03) * row / max(ROWS - 1, 1) - rng.uniform(0, 0.006)   # rows from the top down
        lift = rng.uniform(0.006, 0.011)
        for side in (1, -1):
            grid = []
            for i, t in enumerate((0.0, 0.5, 1.0)):                          # root, middle, tip
                rr = R + 0.0006 + lift * t ** 1.5 - (0.0004 if side < 0 else 0)
                z = zr - ln * t
                rowv = []
                for c in range(COLS):
                    s = (c / (COLS - 1) - 0.5) * wd
                    ang = th + s / rr
                    rowv.append(bm.verts.new((rr * math.cos(ang), rr * math.sin(ang), z)))
                grid.append(rowv)
            for i in range(2):
                for c in range(COLS - 1):
                    q = [grid[i][c], grid[i][c + 1], grid[i + 1][c + 1], grid[i + 1][c]]
                    uv = [(u0 + (u1 - u0) * cc / (COLS - 1), v1 - (v1 - v0) * ii / 2) for ii, cc in ((i, c), (i, c + 1), (i + 1, c + 1), (i + 1, c))]
                    if side < 0: q, uv = q[::-1], uv[::-1]
                    f = bm.faces.new(q)
                    for l, x in zip(f.loops, uv): l[uvl].uv = x
me = bpy.data.meshes.new("fur"); bm.to_mesh(me); bm.free()
fur = bpy.data.objects.new("fur", me); bpy.context.scene.collection.objects.link(fur)
for p in me.polygons: p.use_smooth = True
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
rod = next(o for o in bpy.data.objects if o.type == 'MESH' and o.name != "fur")
fur.parent = arm; md = fur.modifiers.new("Armature", 'ARMATURE'); md.object = arm
vg = fur.vertex_groups.new(name="Rod.Handle"); vg.add(list(range(len(me.vertices))), 1.0, 'REPLACE')
print(f"FUR: {ROWS * PER} cards, {len(me.polygons)} faces, from {Z0:.3f} to {Z1:.3f} m")

# a material to see it by (the importer makes the game's own from fur_Unity_*)
m = bpy.data.materials.new("fur"); nt = m.node_tree; b = nt.nodes["Principled BSDF"]
ti = nt.nodes.new("ShaderNodeTexImage"); ti.image = bpy.data.images.load(p_alb)
nt.links.new(ti.outputs["Color"], b.inputs["Base Color"]); nt.links.new(ti.outputs["Alpha"], b.inputs["Alpha"])
tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = bpy.data.images.load(p_nrm); tn.image.colorspace_settings.name = "Non-Color"
nm = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(tn.outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
b.inputs["Roughness"].default_value = 0.8
me.materials.append(m)

# ---- a part to wear a vanilla material in game (VDW_SPLIT_FROM = the baked blend, VDW_SPLIT_MAT = its material, e.g.
# "gold"; VDW_SPLIT_NAME = the new mesh, e.g. "bloodgold"): the rod's faces of that material, found by their atlas UVs
# (the rig re-cuts the mesh, so face numbers don't carry over; the UVs do), go into a mesh of their own with tiling box
# UVs (VDW_SPLIT_TILE m per repeat). The game swaps its material for the vanilla one; its own small maps are a fallback.
if os.environ.get("VDW_SPLIT_FROM"):
    sname, smat, tile = os.environ.get("VDW_SPLIT_NAME", "bloodgold"), os.environ.get("VDW_SPLIT_MAT", "gold"), float(os.environ.get("VDW_SPLIT_TILE", "0.08"))
    with bpy.data.libraries.load(os.environ["VDW_SPLIT_FROM"]) as (src, dst): dst.objects = ["bait"]
    bme = dst.objects[0].data
    slot = next(i for i, mm in enumerate(bme.materials) if mm and mm.name.startswith(f"cool_{smat}_"))
    buv = bme.uv_layers["UVMap"].data
    T = np.array([[buv[li].uv[:] for li in p.loop_indices] for p in bme.polygons if p.material_index == slot and len(p.loop_indices) == 3], np.float64)
    bpy.data.objects.remove(dst.objects[0])                             # (only its mesh was wanted)
    rme = rod.data
    ruv = rme.uv_layers.active.data
    C = np.array([np.mean([ruv[li].uv[:] for li in p.loop_indices], 0) for p in rme.polygons])
    a, b, c = T[:, 0], T[:, 1], T[:, 2]
    v0, v1 = b - a, c - a; d00, d01, d11 = (v0 * v0).sum(1), (v0 * v1).sum(1), (v1 * v1).sum(1); den = d00 * d11 - d01 ** 2 + 1e-18
    pick = np.zeros(len(C), bool)
    for i0 in range(0, len(C), 256):                                    # barycentric: a face is gold if its UV centre is in a gold triangle
        v2 = C[i0:i0 + 256, None, :] - a[None]
        d20, d21 = (v2 * v0[None]).sum(2), (v2 * v1[None]).sum(2)
        v = (d11 * d20 - d01 * d21) / den; w = (d00 * d21 - d01 * d20) / den
        pick[i0:i0 + 256] = ((v >= -1e-5) & (w >= -1e-5) & (v + w <= 1 + 1e-5)).any(1)
    rod_ob = rod
    part = rod_ob.copy(); part.data = rme.copy(); part.name = part.data.name = sname; bpy.context.scene.collection.objects.link(part)
    for ob_, keep in ((rod_ob, ~pick), (part, pick)):
        bm_ = bmesh.new(); bm_.from_mesh(ob_.data); bm_.faces.ensure_lookup_table()
        bmesh.ops.delete(bm_, geom=[f for f in bm_.faces if not keep[f.index]], context='FACES')
        bmesh.ops.delete(bm_, geom=[v for v in bm_.verts if not v.link_faces], context='VERTS')
        if ob_ is part:                                                 # box UVs, in metres
            uvl_ = bm_.loops.layers.uv.active; mw = ob_.matrix_world
            for f in bm_.faces:
                n = (mw.to_3x3() @ f.normal); ax = max(range(3), key=lambda k: abs(n[k])); o = [k for k in range(3) if k != ax]
                for l in f.loops:
                    w_ = mw @ l.vert.co; l[uvl_].uv = (w_[o[0]] / tile, w_[o[1]] / tile)
        bm_.to_mesh(ob_.data); bm_.free()
    pm = bpy.data.materials.new(sname); pm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.62, 0.2, 0.04, 1)
    pm.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = 0.8; pm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.4
    if os.environ.get("VDW_SPLIT_LOOK"):                                # (preview only: the vanilla texture, from the asset rip)
        ti_ = pm.node_tree.nodes.new("ShaderNodeTexImage"); ti_.image = bpy.data.images.load(os.environ["VDW_SPLIT_LOOK"]); ti_.interpolation = 'Linear'
        pm.node_tree.links.new(ti_.outputs["Color"], pm.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
    part.data.materials.clear(); part.data.materials.append(pm)
    # the fallback maps: a red-orange gold, softly mottled, metallic
    N_ = 64; yy, xx = np.mgrid[0:N_, 0:N_] / N_
    mot = 0.5 + 0.25 * np.sin(xx * 2 * math.pi * 3 + np.sin(yy * 2 * math.pi * 2) * 2) * np.cos(yy * 2 * math.pi * 3 + np.sin(xx * 2 * math.pi) * 1.5)
    al = np.zeros((N_, N_, 4), np.float32); al[..., 0] = 0.72 + 0.2 * mot; al[..., 1] = 0.30 + 0.2 * mot; al[..., 2] = 0.06 + 0.06 * mot; al[..., 3] = 1
    def save_set(px, kind):
        im = bpy.data.images.new(f"{sname}_{kind}", N_, N_, alpha=True); im.pixels[:] = np.clip(px, 0, 1).ravel()
        im.filepath_raw = os.path.join(TEX, f"{sname}_Unity_{kind}.png"); im.file_format = 'PNG'; im.save()
    save_set(al, "Albedo")
    msk_ = np.zeros((N_, N_, 4), np.float32); msk_[..., 0] = 0.77; msk_[..., 3] = 0.5; save_set(msk_, "MetallicSmoothness")
    nn = np.zeros((N_, N_, 4), np.float32); nn[..., 0] = 0.5; nn[..., 1] = 0.5; nn[..., 2] = 1; nn[..., 3] = 1; save_set(nn, "Normal")
    print(f"SPLIT {sname}: {int(pick.sum())} of {len(pick)} faces (the baked '{smat}', {len(T)} triangles)")
bpy.ops.wm.save_as_mainfile(filepath=os.environ["VDW_SAVE_TO"])

# ---- the FBX: armature, the rod and its fur, triangulated
parts = [o for o in bpy.data.objects if o.type == 'MESH']             # the rod, its fur and any split part
for o in bpy.data.objects: o.select_set(o in parts or o == arm)
bpy.context.view_layer.objects.active = arm
tris = [o.modifiers.new("tri", 'TRIANGULATE') for o in parts]
os.makedirs(os.path.dirname(os.environ["VDW_FBX"]), exist_ok=True)
bpy.ops.export_scene.fbx(filepath=os.environ["VDW_FBX"], use_selection=True, object_types={'ARMATURE', 'MESH'},
                         global_scale=1.0, apply_unit_scale=True, apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y',
                         bake_space_transform=False, add_leaf_bones=False, primary_bone_axis='Y', secondary_bone_axis='X',
                         mesh_smooth_type='FACE', use_mesh_modifiers=True, bake_anim=False, path_mode='COPY', embed_textures=False)
for o, t in zip(parts, tris): o.modifiers.remove(t)
print("EXPORTED", os.environ["VDW_FBX"])

# ---- a look at it
if os.environ.get("VDW_PREVIEW"):
    sc = bpy.context.scene; out = os.environ["VDW_PREVIEW"]
    names = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]
    sc.render.engine = 'BLENDER_EEVEE' if 'BLENDER_EEVEE' in names else 'BLENDER_EEVEE_NEXT'
    w = bpy.data.worlds.new("w"); w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.55, 0.62, 0.72, 1); sc.world = w
    bpy.ops.object.light_add(type='SUN', rotation=(math.radians(50), 0, math.radians(30))); bpy.context.object.data.energy = 3.0
    for name, loc, look, lens in (("grip", (0.22, -0.18, 0.2), (0, 0, 0.13), 55), ("whole", (0.9, -0.9, 0.7), (0, 0, 0.45), 35),
                                  ("reel", (-0.22, 0.24, 0.34), (0, 0.04, 0.25), 60)):
        bpy.ops.object.camera_add(location=loc); c = bpy.context.object
        c.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); c.data.lens = lens; c.data.clip_start = 0.005; sc.camera = c
        sc.render.resolution_x = sc.render.resolution_y = 1200; sc.render.filepath = out.replace(".png", f"_{name}.png")
        bpy.ops.render.render(write_still=True)
    print("PREVIEW", out)
