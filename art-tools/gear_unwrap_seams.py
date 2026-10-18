# Unwraps the fisherman's gear along the seams the user marked (nothing re-cut), evens the texel density, packs each
# piece into its own 0-1 square, and writes a new .blend, UV layout previews and one FBX for Substance Painter
# (each piece its own material = texture set, metres, smooth shading kept).
#   blender -b fisher_gear_v3.blend --python gear_unwrap_seams.py
#   env: VDW_SAVE_TO, VDW_UV_PREVIEW (png prefix), VDW_FBX (path)
import bpy, os
import numpy as np
PIECES = ["coat", "shirt", "overalls", "boots", "hat"]
SAVE_TO = os.environ["VDW_SAVE_TO"]; PREV = os.environ.get("VDW_UV_PREVIEW"); FBX = os.environ.get("VDW_FBX")
print("\n===== GEAR UNWRAP (user's seams) =====")
for name in PIECES:
    ob = bpy.data.objects[name]
    for o in bpy.data.objects: o.select_set(o == ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_mode(type='FACE'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=0.004)
    bpy.ops.uv.average_islands_scale()
    bpy.ops.uv.pack_islands(rotate=True, margin=0.006)
    bpy.ops.object.mode_set(mode='OBJECT')
    me = ob.data; uvl = me.uv_layers.active.data; ratios = []
    for p in me.polygons:
        uv = [uvl[i].uv for i in p.loop_indices]; a = 0.0
        for k in range(1, len(uv) - 1):
            a += abs((uv[k].x - uv[0].x) * (uv[k + 1].y - uv[0].y) - (uv[k + 1].x - uv[0].x) * (uv[k].y - uv[0].y)) / 2
        if p.area > 1e-6: ratios.append(a / p.area)
    r = np.array(ratios); r /= np.median(r)
    print(f"  {name}: {sum(e.use_seam for e in me.edges)} seams, texel density 10th {np.percentile(r, 10):.2f} / 90th {np.percentile(r, 90):.2f}")
bpy.ops.wm.save_as_mainfile(filepath=SAVE_TO, copy=True); print("  saved", SAVE_TO)
if PREV:
    N = 1024
    for name in PIECES:
        me = bpy.data.objects[name].data; uvl = me.uv_layers.active.data
        img = np.ones((N, N, 4), np.float32); img[..., :3] = 0.12
        for p in me.polygons:
            pts = [uvl[i].uv * (N - 1) for i in p.loop_indices]
            for k in range(len(pts)):
                a_, b_ = pts[k], pts[(k + 1) % len(pts)]; n = int(max(abs(b_.x - a_.x), abs(b_.y - a_.y))) + 1
                for t in np.linspace(0, 1, n + 1):
                    x = int(a_.x + (b_.x - a_.x) * t); y = int(a_.y + (b_.y - a_.y) * t)
                    if 0 <= x < N and 0 <= y < N: img[y, x, :3] = (0.95, 0.8, 0.2)
        im = bpy.data.images.new(f"uv_{name}", N, N, alpha=True); im.pixels.foreach_set(img.ravel())
        im.filepath_raw = f"{PREV}_{name}.png"; im.file_format = 'PNG'; im.save()
if FBX:
    if os.path.exists(FBX): print("  exists, kept:", FBX)
    else:
        os.makedirs(os.path.dirname(FBX), exist_ok=True)
        for name in PIECES:
            ob = bpy.data.objects[name]
            if ob.data.materials: ob.data.materials[0].name = name
        for o in bpy.data.objects: o.select_set(o.name in PIECES)
        bpy.context.view_layer.objects.active = bpy.data.objects[PIECES[0]]
        bpy.ops.export_scene.fbx(filepath=FBX, use_selection=True, object_types={'MESH'}, global_scale=0.01, apply_unit_scale=True,
                                 axis_forward='-Z', axis_up='Y', mesh_smooth_type='FACE', path_mode='STRIP', embed_textures=False, bake_anim=False)
        print("  exported", FBX)
print("===== END =====")
