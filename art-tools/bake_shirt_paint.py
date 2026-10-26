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
UNIT = s                                                   # body units per metre (s is reused further down)
print(f"FIT mean error {err / s * 100:.2f} cm (body units per metre {s:.3f}, mirrored {R.determinant() < 0})")

# --- the piece, in the game body's space
piece = world_mesh(bpy.data.objects[PIECE])
piece.data.transform(M)
if R.determinant() < 0: piece.data.flip_normals()
bpy.data.objects.remove(fit)

# emission materials: the piece shows its colour map (for the colour bake) or plain white (for the coverage mask)
# VDW_ALBEDO is one colour map, or "material=path;material=path" for a piece with several (the overalls and boots)
albedo = dict(kv.split("=", 1) for kv in ALBEDO.split(";")) if "=" in ALBEDO else None
def emit_mat(name, image=None):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    o = nt.nodes.new("ShaderNodeOutputMaterial"); e = nt.nodes.new("ShaderNodeEmission")
    if image is not None:
        tx = nt.nodes.new("ShaderNodeTexImage"); tx.image = image; nt.links.new(tx.outputs["Color"], e.inputs["Color"])
    else: e.inputs["Color"].default_value = (1, 1, 1, 1)
    nt.links.new(e.outputs["Emission"], o.inputs["Surface"]); return m
slots = [m.name if m else "" for m in piece.data.materials]
if albedo is None: col_mats = [emit_mat("bake_colour", bpy.data.images.load(ALBEDO))] * max(1, len(slots))
else:
    missing = [s for s in slots if s not in albedo]
    if missing: raise SystemExit(f"no colour map for material(s) {missing} (have {list(albedo)})")
    col_mats = [emit_mat("bake_" + s, bpy.data.images.load(albedo[s])) for s in slots]
m_white = emit_mat("bake_white")

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
# rays start half the reach out from the body and look the whole reach (VDW_REACH, metres): the shirt sits 0.1-1 cm off
# the skin (5 cm is plenty); the baggy overalls' seat hangs further
reach = float(os.environ.get("VDW_REACH", "0.05"))
bk.cage_extrusion = reach / 2 * s
bk.max_ray_distance = reach * s
bk.target = 'IMAGE_TEXTURES'
# one object per material: the bake read every face of a two-material piece with the first material (the overalls
# came out in the boots' colours), so each material's faces become their own object, all baked from at once
parts = []
for mi in range(max(1, len(slots))):
    me = piece.data.copy(); bmp = bmesh.new(); bmp.from_mesh(me)
    bmesh.ops.delete(bmp, geom=[f for f in bmp.faces if f.material_index != mi], context='FACES')
    bmesh.ops.delete(bmp, geom=[v for v in bmp.verts if not v.link_faces], context='VERTS')
    bmp.to_mesh(me); bmp.free()
    if not me.polygons: continue
    ob = bpy.data.objects.new(f"{PIECE}_part{mi}", me); sc.collection.objects.link(ob); parts.append((mi, ob))
piece.hide_render = True
def bake(mats, image, margin, btype='EMIT'):
    for mi, ob in parts:
        ob.data.materials.clear(); ob.data.materials.append(mats[mi])
        for p in ob.data.polygons: p.material_index = 0
    tn.image = image; bm_mat.node_tree.nodes.active = tn
    for o in bpy.data.objects: o.select_set(False)
    for mi, ob in parts: ob.select_set(True)
    body.select_set(True); bpy.context.view_layer.objects.active = body
    bk.margin = margin
    bpy.ops.object.bake(type=btype, normal_space='TANGENT', margin=margin, use_selected_to_active=True, cage_extrusion=bk.cage_extrusion, max_ray_distance=bk.max_ray_distance)
# The game blends neighbouring pixels (and smaller mip levels), so a mask that stops dead at a UV island's edge goes
# part see-through along the body's UV seams - dark rings at the waist and thighs (fisher_overalls_paint_v1). The mask
# is grown outward into the texture's unused space below (not with the bake's own margin: that also filled the gaps
# inside the islands where no cloth was hit). The colour gets the bake's margin.
MARGIN = int(os.environ.get("VDW_MARGIN", "16"))
bake([m_white] * max(1, len(slots)), mask_img, 0)
bake(col_mats, col_img, MARGIN)

# --- volume (optional): painted cloth lies flat on the skin, so its folds are baked in instead
#   VDW_AO        0..1: shadow in the cloth's own folds and creases (ambient occlusion of the piece alone), into the colour
#   VDW_NORMALS   "material=path;..." the piece's own normal maps, baked to <name>_nrm.png in the body's tangent space
#   VDW_WRINKLES  strength of soft cloth folds added to that normal map (0 = none); VDW_WRINKLE_SCALE folds per metre
AO = float(os.environ.get("VDW_AO", "0"))
NRM = os.environ.get("VDW_NORMALS", "")
WRINKLE = float(os.environ.get("VDW_WRINKLES", "0"))
ao_img = nrm_img = None
if AO > 0:
    def ao_mat():
        m = bpy.data.materials.new("bake_ao"); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
        o = nt.nodes.new("ShaderNodeOutputMaterial"); e = nt.nodes.new("ShaderNodeEmission"); a = nt.nodes.new("ShaderNodeAmbientOcclusion")
        a.only_local = True; a.samples = 32; a.inputs["Distance"].default_value = 0.12 * s   # folds within 12 cm
        nt.links.new(a.outputs["AO"], e.inputs["Color"]); nt.links.new(e.outputs["Emission"], o.inputs["Surface"])
        return m
    ao_img = target("ao", (1, 1, 1, 1)); sc.cycles.samples = 64
    bake([ao_mat()] * max(1, len(slots)), ao_img, MARGIN); sc.cycles.samples = 4
if NRM or WRINKLE > 0:
    if "=" in NRM: nmaps = dict(kv.split("=", 1) for kv in NRM.split(";"))
    else: nmaps = {sl: NRM for sl in (slots or [""])} if NRM else {}
    def nrm_mat(slot):
        m = bpy.data.materials.new("bake_nrm_" + slot); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
        o = nt.nodes.new("ShaderNodeOutputMaterial"); bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
        nt.links.new(bs.outputs[0], o.inputs["Surface"]); nrm = None
        if slot in nmaps:
            tx = nt.nodes.new("ShaderNodeTexImage"); tx.image = bpy.data.images.load(nmaps[slot]); tx.image.colorspace_settings.name = 'Non-Color'
            nm = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(tx.outputs["Color"], nm.inputs["Color"]); nrm = nm.outputs["Normal"]
        if WRINKLE > 0:
            tc = nt.nodes.new("ShaderNodeTexCoord"); wv = nt.nodes.new("ShaderNodeTexWave"); wv.bands_direction = 'Z'
            wv.inputs["Scale"].default_value = float(os.environ.get("VDW_WRINKLE_SCALE", "9")) / s
            wv.inputs["Distortion"].default_value = 7; wv.inputs["Detail"].default_value = 3; wv.inputs["Detail Roughness"].default_value = 0.4
            nt.links.new(tc.outputs["Object"], wv.inputs["Vector"])
            bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = WRINKLE; bp.inputs["Distance"].default_value = 0.01 * s
            nt.links.new(wv.outputs["Fac"], bp.inputs["Height"])
            if nrm is not None: nt.links.new(nrm, bp.inputs["Normal"])
            nrm = bp.outputs["Normal"]
        if nrm is not None: nt.links.new(nrm, bs.inputs["Normal"])
        return m
    nrm_img = target("normal", (0.5, 0.5, 1, 1))
    bake([nrm_mat(sl) for sl in (slots or [""])], nrm_img, MARGIN, 'NORMAL')

# --- combine: colour with the mask as alpha (grown a pixel so seams don't show a hairline of skin)
import numpy as np
n = SIZE
mpx = list(mask_img.pixels); cpx = list(col_img.pixels)
cov = np.array(mpx, dtype=np.float32).reshape(n, n, 4)[:, :, 0] >= 0.5
# where the body's UV islands are (its triangles drawn into the texture)
occ = np.zeros((n, n), bool)
uvl = bme.uv_layers.active.data
for poly in bme.polygons:
    pts = [uvl[li].uv * n for li in poly.loop_indices]
    for k in range(1, len(pts) - 1):
        a, b, c = pts[0], pts[k], pts[k + 1]
        x0, x1 = int(max(0, min(a.x, b.x, c.x) - 1)), int(min(n - 1, max(a.x, b.x, c.x) + 1))
        y0, y1 = int(max(0, min(a.y, b.y, c.y) - 1)), int(min(n - 1, max(a.y, b.y, c.y) + 1))
        if x1 < x0 or y1 < y0: continue
        X, Y = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        d = (b.y - c.y) * (a.x - c.x) + (c.x - b.x) * (a.y - c.y)
        if abs(d) < 1e-9: continue
        l1 = ((b.y - c.y) * (X - c.x) + (c.x - b.x) * (Y - c.y)) / d
        l2 = ((c.y - a.y) * (X - c.x) + (a.x - c.x) * (Y - c.y)) / d
        inside = (l1 >= -0.02) & (l2 >= -0.02) & (1 - l1 - l2 >= -0.02)
        occ[y0:y1 + 1, x0:x1 + 1] |= inside
# VDW_NECKLINE=<object>: the paint ends exactly along the lower edge of that object's collar (the worn collar model),
# going VDW_NECK_OVERLAP cm up under it - painted higher, a yellow band showed on the neck between paint and collar
NECKLINE = os.environ.get("VDW_NECKLINE", "")
NECK_TEX = os.environ.get("VDW_NECKLINE_TEX", "")     # or: end where this painted texture (the shirt) ends round the neck
if (NECKLINE and NECKLINE in bpy.data.objects) or NECK_TEX:
    import math
    pos = np.zeros((n, n, 3), np.float32); has = np.zeros((n, n), bool)
    for poly in bme.polygons:
        vi = list(poly.vertices); li = list(poly.loop_indices)
        for k in range(1, len(vi) - 1):
            tri = (0, k, k + 1)
            a, b, c = (uvl[li[t]].uv * n for t in tri); A, B, C = (bme.vertices[vi[t]].co for t in tri)
            x0, x1 = int(max(0, min(a.x, b.x, c.x) - 1)), int(min(n - 1, max(a.x, b.x, c.x) + 1))
            y0, y1 = int(max(0, min(a.y, b.y, c.y) - 1)), int(min(n - 1, max(a.y, b.y, c.y) + 1))
            if x1 < x0 or y1 < y0: continue
            X, Y = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            d = (b.y - c.y) * (a.x - c.x) + (c.x - b.x) * (a.y - c.y)
            if abs(d) < 1e-9: continue
            l1 = ((b.y - c.y) * (X - c.x) + (c.x - b.x) * (Y - c.y)) / d
            l2 = ((c.y - a.y) * (X - c.x) + (a.x - c.x) * (Y - c.y)) / d
            l3 = 1 - l1 - l2; ins = (l1 >= -0.02) & (l2 >= -0.02) & (l3 >= -0.02)
            for j in range(3):
                pos[y0:y1 + 1, x0:x1 + 1, j] = np.where(ins, l1 * A[j] + l2 * B[j] + l3 * C[j], pos[y0:y1 + 1, x0:x1 + 1, j])
            has[y0:y1 + 1, x0:x1 + 1] |= ins
    R3 = M.to_3x3(); up = (R3 @ Vector((0, 0, 1))).normalized(); ex = (R3 @ Vector((1, 0, 0))).normalized(); ey = up.cross(ex)
    neck_w = arm.matrix_world @ arm.data.bones["Neck"].head_local
    nc = M @ neck_w
    shoulder_w = min((arm.matrix_world @ arm.data.bones[sd + "Arm"].head_local).z for sd in ("Left", "Right"))
    col = bpy.data.objects[NECKLINE] if NECKLINE in bpy.data.objects else bpy.data.objects["coat_paint"]
    cdg = col.evaluated_get(bpy.context.evaluated_depsgraph_get()); cme = cdg.to_mesh()
    cw = [cdg.matrix_world @ v.co for v in cme.vertices]
    cpts = [] if NECK_TEX else [M @ p for p in cw if p.z > shoulder_w - 0.02 and (Vector((p.x, p.y, 0)) - Vector((neck_w.x, neck_w.y, 0))).length < 0.16]
    cdg.to_mesh_clear()
    BINS = 48; low = np.full(BINS, np.inf)
    for q in cpts:
        r = q - nc; az = math.atan2(r.dot(ey), r.dot(ex)); bi = int((az + math.pi) / (2 * math.pi) * BINS) % BINS
        low[bi] = min(low[bi], r.dot(up))
    ok = np.isfinite(low)
    if NECK_TEX:
        ti = bpy.data.images.load(NECK_TEX); ta = np.array(ti.pixels[:], dtype=np.float32).reshape(ti.size[1], ti.size[0], 4)[:, :, 3]
        if ta.shape != (n, n): raise SystemExit("VDW_NECKLINE_TEX must be the same size")
        rel = pos - np.array(nc, np.float32); h = rel @ np.array(up, np.float32)
        radial = np.linalg.norm(rel - h[..., None] * np.array(up, np.float32), axis=2)
        zone = has & (radial < 0.14 * s) & (h > -0.10 * s)
        cut = zone & (ta < 0.5) & cov
        RAISE = float(os.environ.get("VDW_NECK_RAISE", "0"))     # 0 = the shirt's line, 1 = the collar's (VDW_NECKLINE)
        if RAISE > 0:
            # per direction round the neck: the shirt's top edge and the collar's lower edge; the line between them
            BN = 48
            azb = ((np.arctan2(rel @ np.array(ey, np.float32), rel @ np.array(ex, np.float32)) + np.pi) / (2 * np.pi) * BN).astype(int) % BN
            stop = np.full(BN, np.nan)
            for k in range(BN):
                sel = zone & (ta >= 0.5) & (azb == k)
                if sel.any(): stop[k] = h[sel].max()
            col2 = bpy.data.objects[NECKLINE]; cdg2 = col2.evaluated_get(bpy.context.evaluated_depsgraph_get()); cme2 = cdg2.to_mesh()
            clow = np.full(BN, np.inf)
            for v in cme2.vertices:
                pw = cdg2.matrix_world @ v.co
                if pw.z < shoulder_w - 0.02 or (Vector((pw.x, pw.y, 0)) - Vector((neck_w.x, neck_w.y, 0))).length >= 0.16: continue
                r = (M @ pw) - nc; kk = int((math.atan2(r.dot(ey), r.dot(ex)) + math.pi) / (2 * math.pi) * BN) % BN
                clow[kk] = min(clow[kk], r.dot(up))
            cdg2.to_mesh_clear()
            ix = np.arange(BN)
            okS = np.isfinite(stop); okC = np.isfinite(clow)
            stop = np.interp(ix, ix[okS], stop[okS], period=BN); clow = np.interp(ix, ix[okC], clow[okC], period=BN)
            line = stop + RAISE * (clow - stop)
            # a clean, even line: smoothed round the neck, read between the directions (not stepped per direction)
            SM = int(os.environ.get("VDW_NECK_SMOOTH", "5"))
            for _ in range(SM): line = (np.roll(line, 1) + 2 * line + np.roll(line, -1)) / 4
            azc = (np.arctan2(rel @ np.array(ey, np.float32), rel @ np.array(ex, np.float32)) + np.pi) / (2 * np.pi) * BN
            lpx = np.interp(azc, np.arange(BN + 1), np.append(line, line[0]))
            if os.environ.get("VDW_NECK_FLAT", "0") == "1": lpx = np.full_like(lpx, float(np.mean(line)))   # one level all round
            cut = zone & cov & (h > lpx)
            # and no holes under it: the skin between the coat and the line is painted too (its colour from the nearest coat)
            band = zone & (h <= lpx) & (h > lpx - float(os.environ.get("VDW_NECK_FILL_DEPTH", "6")) / 100 * s)
            # holes under the line are filled on the back half of the neck only (the coat is open at the front)
            back = (M.to_3x3() @ Vector((0, 1, 0))).normalized()          # the rig's +y is the body's back
            behind = (rel @ np.array(back, np.float32)) > 0.01 * s
            fill = band & ~cov & behind
            cov = cov | fill
            print(f"NECKLINE filled {int(fill.sum())} pixels under the line")
            print(f"NECKLINE raised {RAISE:.2f} of the way to the collar: on average {np.mean(line - stop) / s * 100:.1f} cm above the shirt's line")
        cov = cov & ~cut
        print(f"NECKLINE cut {int(cut.sum())} pixels round the neck where {os.path.basename(NECK_TEX)} has none")
    elif ok.sum() >= 3:
        idx = np.arange(BINS); low = np.interp(idx, idx[ok], low[ok], period=BINS)
        OVER = float(os.environ.get("VDW_NECK_OVERLAP", "0.8")) / 100 * s
        rel = pos - np.array(nc, np.float32)
        h = rel @ np.array(up, np.float32)
        az = np.arctan2(rel @ np.array(ey, np.float32), rel @ np.array(ex, np.float32))
        radial = np.linalg.norm(rel - h[..., None] * np.array(up, np.float32), axis=2)
        bi = (((az + np.pi) / (2 * np.pi)) * BINS).astype(int) % BINS
        cut = has & (radial < 0.14 * s) & (h > low[bi] + OVER)
        cov = cov & ~cut
        print(f"NECKLINE cut {int(cut.sum())} pixels above the collar's lower edge ({int(ok.sum())} of {BINS} directions from the collar)")
    else: print("NECKLINE: no collar points found, not cut")
# a pixel's grow everywhere first (rays along a seam, like the spine's, can miss: a hairline of skin), then MARGIN
# pixels more, but only into pixels no island uses
g = cov.copy()
g[1:, :] |= cov[:-1, :]; g[:-1, :] |= cov[1:, :]; g[:, 1:] |= cov[:, :-1]; g[:, :-1] |= cov[:, 1:]
cov = g.copy()
for _ in range(MARGIN):
    s = g.copy()
    s[1:, :] |= g[:-1, :]; s[:-1, :] |= g[1:, :]; s[:, 1:] |= g[:, :-1]; s[:, :-1] |= g[:, 1:]
    g = np.where(occ, cov, s)
grown = g.ravel().astype(np.float32).tolist()
print(f"MASK islands use {occ.mean() * 100:.1f}% of the texture; covered {cov.mean() * 100:.2f}% -> {g.mean() * 100:.2f}% with the margin")
# the bake comes out linear (a float image); the PNG is an ordinary sRGB image, so the colour is converted on the way
# (written as is, every mid-tone came out darker - fisher_shirt_paint_v1)
def to_srgb(c): return c * 12.92 if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055
# the colour at the cloth's edge and in the margin comes from the nearest cloth pixel that was really hit (edge rays that
# missed left the black background, and the bake's margin spread it into a dark rim)
c4 = np.array(cpx, dtype=np.float32).reshape(n, n, 4)
core = np.array(mpx, dtype=np.float32).reshape(n, n, 4)[:, :, 0] >= 0.99
valid = core & (c4[:, :, :3].max(axis=2) > 0.02)
need = g & ~valid
for _ in range(MARGIN + 4):
    if not need.any(): break
    acc = np.zeros_like(c4[:, :, :3]); cnt = np.zeros((n, n), np.float32)
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
        sv = np.roll(np.roll(valid, dy, 0), dx, 1); sc_ = np.roll(np.roll(c4[:, :, :3], dy, 0), dx, 1)
        acc += sc_ * sv[:, :, None]; cnt += sv
    fill = need & (cnt > 0)
    c4[fill, :3] = acc[fill] / cnt[fill][:, None]
    valid = valid | fill; need = need & ~fill
cpx = c4.ravel().tolist()
if ao_img is not None:                                   # the folds' shadow, into the colour
    aop = np.array(ao_img.pixels[:], dtype=np.float32).reshape(-1, 4)[:, 0]
    shade = 1 - AO * (1 - np.clip(aop, 0, 1))
    shade[~cov.ravel()] = 1.0                            # past the cloth's edge the bake is black: no shadow in the margin
    c4 = np.array(cpx, dtype=np.float32).reshape(-1, 4); c4[:, :3] *= shade[:, None]; cpx = c4.ravel().tolist()
    print(f"AO folds shading: average {shade[g.ravel()].mean():.2f} where covered")
if nrm_img is not None:                                  # the normal map: raw values (not colour), flat outside the cloth
    n4 = np.array(nrm_img.pixels[:], dtype=np.float32).reshape(-1, 4)
    flat = ~g.ravel(); n4[flat, :3] = (0.5, 0.5, 1.0); n4[:, 3] = 1.0
    nimg = bpy.data.images.new(NAME + "_nrm", n, n, alpha=True); nimg.colorspace_settings.name = 'Non-Color'
    nimg.pixels = n4.ravel().tolist(); nimg.filepath_raw = os.path.join(OUT, NAME + "_nrm.png"); nimg.file_format = 'PNG'; nimg.save()
    print(f"NORMALS {nimg.filepath_raw}")
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
show = {body}
if NECKLINE and NECKLINE in bpy.data.objects:             # the collar in the previews too, to check the neckline meets it
    cr = bpy.data.objects[NECKLINE]; cr.data = cr.data.copy(); cr.data.transform(M @ cr.matrix_world); cr.matrix_world = Matrix.Identity(4)
    cm = bpy.data.materials.new("collar_preview"); cm.diffuse_color = (0.95, 0.75, 0.1, 1); cr.data.materials.clear(); cr.data.materials.append(cm)
    if R.determinant() < 0: cr.data.flip_normals()
    show.add(cr)
for o in bpy.data.objects:
    if o.type == 'MESH': o.hide_render = o not in show
sc.render.engine = 'BLENDER_WORKBENCH'; sh = sc.display.shading; sh.light = 'STUDIO'; sh.color_type = 'TEXTURE'
sc.render.resolution_x = 600; sc.render.resolution_y = 800
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
big = max(bsize)
cam.data.type = 'ORTHO'; cam.data.ortho_scale = big * 1.05
cam.data.clip_start = big * 0.01; cam.data.clip_end = big * 20  # the game body is tiny in its own units
upax = max(range(3), key=lambda i: bsize[i])                   # the body's height
thin = min([i for i in range(3) if i != upax], key=lambda i: bsize[i])   # front-to-back is its thinnest side
for label, sign in (("front", -1), ("back", 1)):
    d = Vector((0, 0, 0)); d[thin] = sign
    cam.location = bc + d * big * 3
    cam.rotation_euler = (-d).to_track_quat('-Z', 'Y' if upax == 1 else 'Z').to_euler()
    sc.render.filepath = os.path.join(OUT, f"preview_{label}.png"); bpy.ops.render.render(write_still=True)
if len(show) > 1:                                          # close-ups of the neck from four sides
    nk = M @ (arm.matrix_world @ arm.data.bones["Neck"].head_local)
    upv = (M.to_3x3() @ Vector((0, 0, 1))).normalized()
    cam.data.ortho_scale = 0.35 * UNIT; sc.render.resolution_x = sc.render.resolution_y = 600
    for label, ang in (("front", -90), ("left", 0), ("back", 90), ("right", 180)):
        a = math.radians(ang) if 'math' in dir() else ang * 3.14159265 / 180
        d = (M.to_3x3() @ Vector((__import__('math').cos(a), __import__('math').sin(a), 0))).normalized()
        cam.location = nk + d * big * 3 + upv * 0.02 * UNIT
        zf = d.normalized(); xr = upv.cross(zf).normalized(); yu = zf.cross(xr)            # looking along -d, upright
        cam.matrix_world = Matrix((xr, yu, zf)).transposed().to_4x4() @ Matrix.Identity(4); cam.location = nk + d * big * 3 + upv * 0.02 * UNIT
        sc.render.filepath = os.path.join(OUT, f"neck_{label}.png"); bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, NAME + "_bake.blend"))
print("DONE")
