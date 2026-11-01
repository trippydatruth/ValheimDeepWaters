# Paints extra cloth folds where cloth bunches - behind and round the knees, out from the crotch, round the ankles
# above the boots (overalls) and out from the armpits (coat) - into a wrinkle edit blend's hand-paint images
# (make_wrinkle_edit.py: wrinkle_paint_<material>, grey = flat). New images in the new blend's folder; the user can
# keep painting over them in Texture Paint. The folds are placed from the rig's bones on each piece's rest shape.
#   blender -b fisher_wrinkles_edit_vN.blend --python paint_folds.py
#   env: VDW_OUT (new .blend, never overwrites), VDW_SPOTS "overalls=knee,crotch,ankle;coat=armpit" (default),
#        VDW_FOLD_AMP (0..0.5, default 0.3: how high the painted folds rise)
import bpy, os, math
import numpy as np
from mathutils import Vector

OUT = os.environ["VDW_OUT"]
if os.path.exists(OUT): raise SystemExit("exists, kept: " + OUT)
DIR = os.path.dirname(OUT); os.makedirs(DIR, exist_ok=True)
SPOTS = {k: v.split(",") for k, v in (kv.split("=") for kv in os.environ.get("VDW_SPOTS", "overalls=knee,crotch,ankle;coat=armpit").split(";"))}
AMP = float(os.environ.get("VDW_FOLD_AMP", "0.3"))
PIECE_OF = {"overalls": "overalls", "coat": "coat_paint"}
arm = bpy.data.objects["Armature"]; arm.animation_data_clear()
for pb in arm.pose.bones: pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.rotation_euler = (0, 0, 0); pb.scale = (1, 1, 1)
bpy.context.view_layer.update()
def head(b): return np.array(arm.matrix_world @ arm.data.bones[b].head_local)
BACK = np.array((0, 1, 0.0))                      # the rig's +y is the body's back

def ridges(phase, sharp=3.0):
    """narrow raised folds with soft hollows between (0.5+0.5cos)^sharp, centred so the cloth's average stays put"""
    p = (0.5 + 0.5 * np.cos(phase)) ** sharp
    return p - 0.5 ** sharp * 0.8

def wobble(P, f, a, seed):
    """a slow sideways wander so no fold is a perfect line"""
    return a * (np.sin(P[:, 0] * f + seed) + 0.6 * np.sin(P[:, 1] * f * 1.7 + seed * 2.3) + 0.4 * np.sin(P[:, 2] * f * 1.3 + seed * 0.7))

def smooth01(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)

def folds(spot, P, Nn, piece_ob):
    h = np.zeros(len(P))
    if spot == "knee":
        for i, sd in enumerate(("Left", "Right")):
            K = head(sd + "Leg")
            d = P - K; dz = d[:, 2]; side = np.sign(K[0]) if abs(K[0]) > 1e-4 else (1 if sd == "Left" else -1)
            near = np.exp(-(dz / 0.08) ** 2) * (np.linalg.norm(d[:, :2], axis=1) < 0.16) * (d[:, 0] * side > -0.06)
            back = smooth01(Nn @ BACK, -0.3, 0.5)              # strong behind the knee, light at the front
            # creases across the back of the knee, curving up at the sides (as a bent knee leaves them)
            lat = np.abs(d[:, 0] - 0.0)
            phase = (dz - 2.5 * lat ** 2 + wobble(P, 25, 0.006, i * 3)) / 0.045 * 2 * math.pi
            h += near * (0.35 + 0.65 * back) * ridges(phase, 2.5) * 0.5
    elif spot == "ankle":
        bm = [i for i, m in enumerate(piece_ob.data.materials) if m and m.name == "boot"]
        me = piece_ob.data; rest = np.array([a.vector[:] for a in me.attributes["vdw_rest"].data])
        top = {}
        for p in me.polygons:                                # each boot's top: the highest boot point on its side
            if p.material_index in bm:
                for v in p.vertices:
                    s = 1 if rest[v][0] > 0 else -1; top[s] = max(top.get(s, -9), rest[v][2])
        for s, tz in top.items():
            dz = P[:, 2] - tz
            zone = (P[:, 0] * s > 0) * smooth01(dz, -0.005, 0.015) * (1 - smooth01(dz, 0.07, 0.13))
            ang = np.arctan2(P[:, 1], P[:, 0] - (0.1 * s))
            # rings bunched over the boot top, tilting and breaking round the leg
            phase = (dz + 0.012 * np.sin(ang * 3 + s) + wobble(P, 30, 0.005, s * 5)) / 0.04 * 2 * math.pi
            h += zone * ridges(phase, 2.5) * 0.55
    elif spot == "crotch":
        L, R = head("LeftUpLeg"), head("RightUpLeg")
        C = (L + R) / 2; C[2] -= 0.07
        d = P - C; r = np.linalg.norm(d[:, [0, 2]], axis=1)
        ring = smooth01(r, 0.02, 0.05) * (1 - smooth01(r, 0.13, 0.22)) * (np.abs(d[:, 1]) < 0.2)
        # creases fanning up and out from the crotch over the thighs and seat (the trousers' "whiskers")
        theta = np.arctan2(d[:, 2], np.abs(d[:, 0]))
        up = smooth01(theta, -0.9, -0.2)                     # not straight down the inner legs
        phase = (theta + wobble(P, 20, 0.05, 7)) * 7
        h += ring * up * ridges(phase, 3) * 1.8
    elif spot == "armpit":
        for i, sd in enumerate(("Left", "Right")):
            A = head(sd + "Arm"); S = head("Spine2") if "Spine2" in arm.data.bones else head("Spine1")
            Pp = A + (S - A) * np.array((0.25, 0.25, 0)); Pp[2] = A[2] - 0.07     # just under the shoulder joint
            d = P - Pp; r = np.linalg.norm(d, axis=1)
            ring = smooth01(r, 0.015, 0.04) * (1 - smooth01(r, 0.10, 0.17))
            # folds fanning out from the armpit across the chest, the back and down the inner sleeve
            out = d.copy(); out[:, 1] = 0
            theta = np.arctan2(d[:, 2], np.abs(d[:, 0]) + np.abs(d[:, 1]) * 0.6)
            phase = (theta + wobble(P, 22, 0.06, 11 + i)) * 6
            h += ring * ridges(phase, 3) * 1.8
    return h

def raster(ob, mat_index):
    """per pixel of the material's paint image: rest position and normal, from its faces in UV space"""
    me = ob.data; n = 1024
    rest = np.array([a.vector[:] for a in me.attributes["vdw_rest"].data])
    # rest normals from the rest positions
    vn = np.zeros_like(rest)
    for p in me.polygons:
        vs = list(p.vertices); a, b, c = rest[vs[0]], rest[vs[1]], rest[vs[2]]
        fn = np.cross(b - a, c - a); vn[vs] += fn
    vn /= np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-9)
    uvl = me.uv_layers.active.data
    pos = np.zeros((n, n, 3), np.float32); nor = np.zeros((n, n, 3), np.float32); has = np.zeros((n, n), bool)
    for p in me.polygons:
        if p.material_index != mat_index: continue
        vs = list(p.vertices); li = list(p.loop_indices)
        for k in range(1, len(vs) - 1):
            tri = (0, k, k + 1)
            a, b, c = (np.array(uvl[li[t]].uv[:]) * n for t in tri)
            x0, x1 = int(max(0, min(a[0], b[0], c[0]) - 1)), int(min(n - 1, max(a[0], b[0], c[0]) + 1))
            y0, y1 = int(max(0, min(a[1], b[1], c[1]) - 1)), int(min(n - 1, max(a[1], b[1], c[1]) + 1))
            if x1 < x0 or y1 < y0: continue
            X, Y = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            dd = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
            if abs(dd) < 1e-12: continue
            l1 = ((b[1] - c[1]) * (X - c[0]) + (c[0] - b[0]) * (Y - c[1])) / dd
            l2 = ((c[1] - a[1]) * (X - c[0]) + (a[0] - c[0]) * (Y - c[1])) / dd
            l3 = 1 - l1 - l2; ins = (l1 >= -0.01) & (l2 >= -0.01) & (l3 >= -0.01)
            if not ins.any(): continue
            A, B, Cc = (rest[vs[t]] for t in tri); NA, NB, NC = (vn[vs[t]] for t in tri)
            sl = (slice(y0, y1 + 1), slice(x0, x1 + 1))
            for j in range(3):
                pos[sl + (j,)] = np.where(ins, l1 * A[j] + l2 * B[j] + l3 * Cc[j], pos[sl + (j,)])
                nor[sl + (j,)] = np.where(ins, l1 * NA[j] + l2 * NB[j] + l3 * NC[j], nor[sl + (j,)])
            has[sl] |= ins
    nor /= np.maximum(np.linalg.norm(nor, axis=2, keepdims=True), 1e-9)
    return pos, nor, has

for mat_name, spots in SPOTS.items():
    ob = bpy.data.objects[PIECE_OF[mat_name]]
    mi = [i for i, m in enumerate(ob.data.materials) if m and m.name == mat_name][0]
    pos, nor, has = raster(ob, mi)
    P = pos[has].astype(np.float64); Nn = nor[has].astype(np.float64)
    h = np.zeros(len(P))
    for sp in spots:
        hs = folds(sp, P, Nn, ob); h += hs; print(f"FOLDS {mat_name} {sp}: {int((np.abs(hs) > 0.02).sum())} pixels")
    n = has.shape[0]
    hm = np.zeros((n, n)); hm[has] = np.clip(h, -1, 1) * AMP
    # spread the values a few pixels past the UV islands' edges, so the bake reading near an edge sees no step
    cov = has.copy()
    for _ in range(6):
        acc = np.zeros_like(hm); cnt = np.zeros_like(hm)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            acc += np.roll(np.roll(hm * cov, dy, 0), dx, 1); cnt += np.roll(np.roll(cov, dy, 0), dx, 1)
        fill = ~cov & (cnt > 0); hm[fill] = acc[fill] / cnt[fill]; cov |= fill
    # the image the material's wrinkle node reads
    nt = bpy.data.materials[mat_name].node_tree
    tx = next(nd for nd in nt.nodes if nd.type == 'TEX_IMAGE' and nd.image and nd.image.name.startswith("wrinkle_paint"))
    path = os.path.join(DIR, f"wrinkle_paint_{mat_name}.png")
    # plain data (Non-Color): the value is the height, 0.5 = flat
    im = bpy.data.images.new(f"wrinkle_paint_{mat_name}_folds", n, n); im.colorspace_settings.name = 'Non-Color'
    px = np.ones((n, n, 4), np.float32); px[:, :, :3] = (0.5 + hm)[:, :, None]
    im.pixels = px.ravel(); im.filepath_raw = path; im.file_format = 'PNG'; im.save()
    im.filepath = path; im.source = 'FILE'; im.reload(); im.colorspace_settings.name = 'Non-Color'; tx.image = im
    print("PAINTED", path)
bpy.ops.wm.save_as_mainfile(filepath=OUT, copy=True, relative_remap=True)
print("SAVED", OUT)
