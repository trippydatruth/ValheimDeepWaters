# Paints the tackle box (rig_tacklebox.py output) in four tiers and exports it rigged for Unity. The box comes untextured
# (plain lid / base / lock colours) but unwrapped; each texel's place on the box is found by rasterizing the UVs, and the
# maps are painted from that: planks and grain on the wood, bands round the edges, the lock and the handle in metal.
#   t1 Tackle Box             warm oak, dark iron lock, leather-wrapped handle
#   t2 Iron-Bound Tackle Box  dark stained wood, iron corner straps and rims
#   t3 Silver Tackle Box      pale birch, silver straps, rims, lock and handle
#   t4 Dvergr Tackle Box      blue-grey wood, dvergr copper straps, a faint blue rune line round the lid (emission)
# The three materials become one; the box is scaled to VDW_LENGTH m long (0.6) with its rig; one FBX for all tiers.
# Writes <out>/Models/tacklebox.fbx, <out>/Textures/tacklebox_<tier>/tacklebox_<tier>_Unity_*.png, <out>/Previews.
#   blender -b tacklebox_rigged.blend --factory-startup --python paint_tacklebox.py    env: VDW_OUT, VDW_LENGTH, VDW_REDO
import bpy, math, os
import numpy as np
from mathutils import Matrix, Vector

OUT = os.environ["VDW_OUT"]; LENGTH = float(os.environ.get("VDW_LENGTH", "0.6")); N = 1024
REDO = os.environ.get("VDW_REDO") == "1"
for d in ("Models", "Textures", "Previews"): os.makedirs(os.path.join(OUT, d), exist_ok=True)
box = bpy.data.objects["tacklebox"]; arm = bpy.data.objects["TackleBox_Rig"]; me = box.data
rng = np.random.default_rng(5)

# ---------------------------------------------------------------- where each texel is on the box
co = np.array([v.co[:] for v in me.vertices]); names = [m.name for m in me.materials]
lo, hi = co.min(0), co.max(0)
seam = (co[:, 2].max() + co[:, 2].min()) * 0.0 + 0.497 * (hi[2] / 1.249)
uvl = me.uv_layers.active.data
P = np.zeros((N, N, 3), np.float32); Nn = np.zeros((N, N, 3), np.float32); MAT = np.full((N, N), -1, np.int16)
me.calc_loop_triangles()
for tri in me.loop_triangles:
    uv = np.array([uvl[l].uv[:] for l in tri.loops]) * (N - 1)
    pos = co[list(tri.vertices)]; nrm = np.array(tri.normal[:])
    x0, y0 = np.floor(uv.min(0)).astype(int); x1, y1 = np.ceil(uv.max(0)).astype(int)
    x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, N - 1), min(y1, N - 1)
    if x1 < x0 or y1 < y0: continue
    xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
    (ax, ay), (bx, by), (cx, cy) = uv
    d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
    if abs(d) < 1e-9: continue
    w0 = ((by - cy) * (xs - cx) + (cx - bx) * (ys - cy)) / d; w1 = ((cy - ay) * (xs - cx) + (ax - cx) * (ys - cy)) / d; w2 = 1 - w0 - w1
    inside = (w0 >= -0.01) & (w1 >= -0.01) & (w2 >= -0.01)
    if not inside.any(): continue
    yy, xx = (ys[inside] - 0.5).astype(int), (xs[inside] - 0.5).astype(int)
    P[yy, xx] = w0[inside, None] * pos[0] + w1[inside, None] * pos[1] + w2[inside, None] * pos[2]
    Nn[yy, xx] = nrm; MAT[yy, xx] = tri.material_index
covered = MAT >= 0
print(f"PAINT texels covered {covered.mean() * 100:.0f}%")

# ---------------------------------------------------------------- 3D noise
G = 48; lat = rng.random((G, G, G)).astype(np.float32)
def noise3(p, scale):
    q = p * scale; i = np.floor(q).astype(int); f = q - i; f = f * f * (3 - 2 * f)
    def L(dx, dy, dz): return lat[(i[..., 0] + dx) % G, (i[..., 1] + dy) % G, (i[..., 2] + dz) % G]
    x00 = L(0, 0, 0) * (1 - f[..., 0]) + L(1, 0, 0) * f[..., 0]; x10 = L(0, 1, 0) * (1 - f[..., 0]) + L(1, 1, 0) * f[..., 0]
    x01 = L(0, 0, 1) * (1 - f[..., 0]) + L(1, 0, 1) * f[..., 0]; x11 = L(0, 1, 1) * (1 - f[..., 0]) + L(1, 1, 1) * f[..., 0]
    y0 = x00 * (1 - f[..., 1]) + x10 * f[..., 1]; y1 = x01 * (1 - f[..., 1]) + x11 * f[..., 1]
    return y0 * (1 - f[..., 2]) + y1 * f[..., 2]
def fbm3(p, s): return noise3(p, s) * 0.5 + noise3(p, s * 2.1) * 0.3 + noise3(p, s * 4.3) * 0.2
def mix(a, b, t): t = np.asarray(t, np.float32)[..., None]; return np.asarray(a, np.float32) * (1 - t) + np.asarray(b, np.float32) * t
def smooth(e0, e1, x): t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)

X, Y, Z = P[..., 0], P[..., 1], P[..., 2]
is_lid, is_base, is_lock = MAT == names.index("lid"), MAT == names.index("base"), MAT == names.index("lock")
# only the latch on the front face is metal; other faces in the lock material (the compartment dividers inside) are wood
divider = is_lock & (Y > lo[1] + 0.05 * (hi[2] / 1.249))
is_lock = is_lock & ~divider
lid_top = np.percentile(co[co[:, 2] > seam][:, 2], 90)                      # the lid's body; the handle stands above it
handle = is_lid & (Z > lid_top + 0.01 * (hi[2] / 1.249)) & (np.abs(X) < 0.45 * hi[0])
inner = (np.abs(X) < hi[0] - 0.08) & (np.abs(Y) < hi[1] - 0.08) & (((Nn[..., 2] > 0.5) & is_base & (Z > 0.05)) | ((Nn[..., 2] < -0.5) & is_lid))
# planks: on the base horizontal boards (lines in z), on the lid boards running along the box (lines in y)
plank_v = np.where(is_lid, (Y - lo[1]) / 0.19, Z / 0.16)
plank_id = np.floor(plank_v); plank_f = plank_v - plank_id
groove = smooth(0.05, 0.0, np.minimum(plank_f, 1 - plank_f))
grain = 0.5 + 0.5 * np.sin((np.where(is_lid, Y, Z) * 90 + plank_id * 7) + 6 * fbm3(P, 3.0) + X * 2.0)
knots = smooth(0.78, 0.86, fbm3(P + plank_id[..., None] * 0.37, 6.0))
# bands: two straps wrapped round the box near each end (not the whole edge: the domed lid's sides lie close to the
# box's edges, so an edge test caught most of the lid), and a rim along the seam
k = hi[2] / 1.249                                                             # 1 at the model's own size
from_end = hi[0] - np.abs(X)
strap = (from_end > 0.14 * k) & (from_end < 0.25 * k) & ~inner & (is_base | (is_lid & ~handle))
rim = (np.abs(Z - seam) < 0.03 * k) & ~inner & ~is_lock
n_fine = fbm3(P, 14.0)

TIERS = {
    "t1": dict(wood=((0.55, 0.36, 0.20), (0.38, 0.23, 0.12)), metal=(0.22, 0.22, 0.24), bands=False, handle=(0.30, 0.18, 0.10), handle_metal=False, glow=None),
    "t2": dict(wood=((0.36, 0.24, 0.15), (0.22, 0.14, 0.08)), metal=(0.30, 0.31, 0.33), bands=True, handle=(0.26, 0.15, 0.08), handle_metal=False, glow=None),
    "t3": dict(wood=((0.74, 0.66, 0.52), (0.55, 0.47, 0.36)), metal=(0.75, 0.77, 0.80), bands=True, handle=(0.75, 0.77, 0.80), handle_metal=True, glow=None),
    "t4": dict(wood=((0.30, 0.33, 0.38), (0.18, 0.20, 0.25)), metal=(0.70, 0.42, 0.24), bands=True, handle=(0.70, 0.42, 0.24), handle_metal=True, glow=(0.25, 0.75, 1.0)),
}

def save(arr, path, nc=False):
    if os.path.exists(path) and not REDO: print("  exists, kept:", path); return
    rgba = np.ones((N, N, 4), np.float32); rgba[..., :arr.shape[-1]] = arr
    im = bpy.data.images.new(os.path.basename(path), N, N, alpha=True)
    if nc: im.colorspace_settings.name = 'Non-Color'
    im.pixels.foreach_set(rgba.ravel()); im.filepath_raw = path; im.file_format = 'PNG'; im.save()

def dilate(a, mask, n=12):
    """Spreads painted texels into the empty space round each UV island, so filtering doesn't bleed black in."""
    a = a.copy(); m = mask.copy()
    for _ in range(n):
        acc = np.zeros_like(a); cnt = np.zeros(m.shape, np.float32)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            sm = np.roll(m, (dy, dx), (0, 1)); acc += np.roll(a, (dy, dx), (0, 1)) * sm[..., None]; cnt += sm
        grow = (~m) & (cnt > 0); a[grow] = acc[grow] / cnt[grow][:, None]; m |= grow
    return a

for tier, t in TIERS.items():
    wood = mix(t["wood"][0], t["wood"][1], grain * 0.55 + knots * 0.5 + 0.25 * n_fine)
    wood = mix(wood, np.array(t["wood"][1]) * 0.6, groove * 0.8)
    wood = np.where(inner[..., None], wood * 0.72, wood)                        # the inside is shadowed
    wood = np.where(divider[..., None], np.clip(wood * 1.15, 0, 1), wood)        # the dividers: lighter, thinner boards
    # brushed metal: fine streaks along the box, a little darker in places, not blotchy
    brush = 0.5 + 0.5 * np.sin(X * 900 * k + 4 * noise3(P, 40.0))
    metal = np.asarray(t["metal"], np.float32) * (0.82 + 0.1 * brush + 0.08 * noise3(P, 6.0))[..., None]
    alb = wood.copy(); metal_mask = is_lock.copy()
    if t["bands"]: metal_mask |= strap | rim
    alb[metal_mask] = metal[metal_mask]
    alb[handle] = (metal[handle] if t["handle_metal"] else mix(t["handle"], np.array(t["handle"]) * 0.7, grain * 0.5)[handle])
    if t["handle_metal"]: metal_mask |= handle
    ms = np.zeros((N, N, 4), np.float32)
    ms[..., 0] = np.where(metal_mask, 0.9, 0.0); ms[..., 3] = np.where(metal_mask, 0.55 - 0.2 * n_fine, np.where(handle, 0.35, 0.12 + 0.08 * grain))
    height = np.where(metal_mask, 0.6 + 0.1 * n_fine, 0.4 * grain - 0.9 * groove)
    gx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * 4.0; gy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * 4.0
    nm = np.stack([-gx, -gy, np.ones_like(gx)], -1); nm /= np.linalg.norm(nm, axis=-1, keepdims=True)
    emit = None
    if t["glow"] is not None:   # a thin rune line round the lid, just above the seam
        band = is_lid & ~inner & (np.abs(Z - (seam + 0.11 * hi[2] / 1.249)) < 0.012 * hi[2] / 1.249)
        runes = band & (np.sin(np.arctan2(Y, X) * 60) > -0.2)
        emit = np.zeros((N, N, 3), np.float32); emit[runes] = t["glow"]; alb[runes] = np.array(t["glow"]) * 0.5
    d = os.path.join(OUT, "Textures", f"tacklebox_{tier}"); os.makedirs(d, exist_ok=True)
    p = lambda k: os.path.join(d, f"tacklebox_{tier}_Unity_{k}.png")
    save(np.clip(dilate(alb, covered), 0, 1), p("Albedo"))
    save(np.clip(dilate(ms, covered), 0, 1), p("MetallicSmoothness"), True)
    save(dilate(nm * 0.5 + 0.5, covered), p("Normal"), True)
    if emit is not None: save(np.clip(dilate(emit, covered), 0, 1), p("Emission"))
    print(f"PAINT {tier} done")

# ---------------------------------------------------------------- one material, real size, export
for p in me.polygons: p.material_index = 0
mat = bpy.data.materials.new("tacklebox"); me.materials.clear(); me.materials.append(mat)
s = LENGTH / (hi[0] - lo[0])
for o in bpy.context.view_layer.objects: o.select_set(False)
arm.scale = (s, s, s); bpy.context.view_layer.update()
for o in (arm, box):
    for x in bpy.context.view_layer.objects: x.select_set(x is o)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
print(f"PAINT scaled x{s:.3f}: {tuple(round(v, 3) for v in (Vector(hi) - Vector(lo)) * s)} m")
path = os.path.join(OUT, "Models", "tacklebox.fbx")
if not os.path.exists(path) or REDO:
    for o in bpy.context.view_layer.objects: o.select_set(o in (arm, box))
    bpy.context.view_layer.objects.active = arm
    tri = box.modifiers.new("vdw_tri", 'TRIANGULATE'); tri.quad_method = 'BEAUTY'
    ad = arm.animation_data
    if ad: ad.action = None
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={'ARMATURE', 'MESH'}, global_scale=1.0, apply_unit_scale=True,
                             apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y', bake_space_transform=False,
                             add_leaf_bones=False, primary_bone_axis='Y', secondary_bone_axis='X', mesh_smooth_type='FACE',
                             use_mesh_modifiers=True, bake_anim=False, path_mode='COPY', embed_textures=False)
    box.modifiers.remove(tri)
    print("PAINT exported", path)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "tacklebox_painted.blend"))
print("===== END =====")
