# Prepares the bobber (stick float) for the game:
#   - upright along +Z (Unity +Y), sized to VDW_HEIGHT metres tall (default 0.45: about 3x real so it reads at range)
#   - origin on the axis at the waterline (VDW_WATERLINE of its height from the bottom, default 0.55): it rocks
#     around the water surface, and the mod floats it with that much below water
#   - Unity maps from the Substance export (Albedo = bobber.png, MetallicSmoothness from OcclusionRoughnessMetallic,
#     Normal = normal.png), static FBX, preview renders
#   env: VDW_OBJ, VDW_TEX_DIR, VDW_SAVE_TO, VDW_FBX_OUT, VDW_RENDER (png prefix)
import bpy, os, math
import numpy as np
from mathutils import Vector

H = float(os.environ.get("VDW_HEIGHT", "0.45")); WL = float(os.environ.get("VDW_WATERLINE", "0.55"))
TEX = os.environ["VDW_TEX_DIR"]
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
bpy.ops.wm.obj_import(filepath=os.environ["VDW_OBJ"])
mesh = next(o for o in bpy.data.objects if o.type == 'MESH'); mesh.name = "bobber"; me = mesh.data
for o in bpy.context.view_layer.objects: o.select_set(False)
mesh.select_set(True); bpy.context.view_layer.objects.active = mesh
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

def load(name, nc=False):
    p = os.path.join(TEX, name)
    if not os.path.exists(p): return None
    im = bpy.data.images.load(p)
    if nc: im.colorspace_settings.name = 'Non-Color'
    return im
alb = load(os.environ.get("VDW_ALB", "bobber.png")); orm = load("OcclusionRoughnessMetallic.png", True); nrm = load(os.environ.get("VDW_NRM", "normal.png"), True)

# Which end is up: the bright orange sight tip should be at the top.
W_, H_ = alb.size; px = np.empty(W_ * H_ * 4, dtype=np.float32); alb.pixels.foreach_get(px); px = px.reshape(H_, W_, 4)
co = np.array([v.co[:] for v in me.vertices])
vcol = np.zeros((len(co), 3)); cnt = np.zeros(len(co))
uv = me.uv_layers.active.data
for poly in me.polygons:
    for li in poly.loop_indices:
        u, v = uv[li].uv; vi = me.loops[li].vertex_index
        vcol[vi] += px[min(H_ - 1, int(v * H_)), min(W_ - 1, int(u * W_)), :3]; cnt[vi] += 1
vcol /= np.maximum(cnt, 1)[:, None]
orange = (vcol[:, 0] > 0.7) & (vcol[:, 1] > 0.15) & (vcol[:, 1] < 0.6) & (vcol[:, 2] < 0.35)
lo, hi = co.min(0), co.max(0)
print("\n===== BOBBER =====")
for k in range(6):
    z0 = lo[2] + (hi[2] - lo[2]) * k / 6; z1 = lo[2] + (hi[2] - lo[2]) * (k + 1) / 6
    sel = (co[:, 2] >= z0) & (co[:, 2] <= z1)
    if sel.any(): print(f"  band {k} (bottom->top): mean colour {tuple(vcol[sel].mean(0).round(2))}, orange {orange[sel].mean() * 100:.0f}%")
oz = co[orange][:, 2].mean() if orange.any() else hi[2]
flip = oz < (lo[2] + hi[2]) / 2
print(f"  orange sight tip is at the {'BOTTOM - flipping upright' if flip else 'top - already upright'}")
if flip:
    mesh.rotation_euler = (math.pi, 0, 0); bpy.ops.object.transform_apply(rotation=True)
    co = np.array([v.co[:] for v in me.vertices]); lo, hi = co.min(0), co.max(0)

# size, origin at the waterline on the axis
s = H / (hi[2] - lo[2])
centre = Vector(((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2] + WL * (hi[2] - lo[2])))
for v in me.vertices: v.co = (v.co - centre) * s
me.update()
co = np.array([v.co[:] for v in me.vertices]); lo, hi = co.min(0), co.max(0)
body = co[np.abs(co[:, 2]) < 0.1 * H]
print(f"  size {tuple((hi - lo).round(3))} m (scale x{s:.4f}), body {body[:, 0].ptp() * 100:.1f} cm across, waterline at {WL * 100:.0f}% of the height (origin)")
print(f"  above water: {hi[2] * 100:.1f} cm, below: {-lo[2] * 100:.1f} cm")

# Unity maps + material
ms = None
if orm:
    w, h = orm.size; p = np.empty(w * h * 4, dtype=np.float32); orm.pixels.foreach_get(p); p = p.reshape(-1, 4)
    out = np.empty_like(p); out[:, 0] = out[:, 1] = out[:, 2] = p[:, 2]; out[:, 3] = 1.0 - p[:, 1]
    path = os.path.join(TEX, "bobber_Unity_MetallicSmoothness.png")
    ms = bpy.data.images.new("bobber_Unity_MetallicSmoothness", w, h, alpha=True); ms.colorspace_settings.name = 'Non-Color'
    ms.pixels.foreach_set(out.ravel()); ms.filepath_raw = path; ms.file_format = 'PNG'
    if not os.path.exists(path): ms.save(); print("  saved", path)
mat = bpy.data.materials.new("bobber"); mat.use_nodes = True; nt = mat.node_tree; nodes, links = nt.nodes, nt.links
bsdf = next(n for n in nodes if n.type == 'BSDF_PRINCIPLED')
def tex(img, x, y):
    t = nodes.new("ShaderNodeTexImage"); t.image = img; t.location = (x, y); return t
a = tex(alb, -700, 300); links.new(a.outputs["Color"], bsdf.inputs["Base Color"])
if ms:
    sn = tex(ms, -700, 0); links.new(sn.outputs["Color"], bsdf.inputs["Metallic"])
    inv = nodes.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
    links.new(sn.outputs["Alpha"], inv.inputs[1]); links.new(inv.outputs["Value"], bsdf.inputs["Roughness"])
if nrm:
    nn = tex(nrm, -700, -320); nm = nodes.new("ShaderNodeNormalMap")
    links.new(nn.outputs["Color"], nm.inputs["Color"]); links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
nodes.active = a
me.materials.clear(); me.materials.append(mat)
for img in list(bpy.data.images):
    if img.users == 0: bpy.data.images.remove(img)

bpy.ops.wm.save_as_mainfile(filepath=os.environ["VDW_SAVE_TO"]); print("  saved", os.environ["VDW_SAVE_TO"])
FBX = os.environ.get("VDW_FBX_OUT")
if FBX:
    for o in bpy.context.view_layer.objects: o.select_set(False)
    mesh.select_set(True); bpy.context.view_layer.objects.active = mesh
    bpy.ops.export_scene.fbx(filepath=FBX, use_selection=True, object_types={'MESH'}, global_scale=1.0, apply_unit_scale=True,
                             apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y', bake_space_transform=True,
                             mesh_smooth_type='FACE', bake_anim=False, path_mode='COPY', embed_textures=True)
    print("  EXPORTED", FBX, os.path.getsize(FBX), "bytes")

R = os.environ.get("VDW_RENDER")
if R:
    sc = bpy.context.scene; sc.render.use_border = False; sc.render.resolution_percentage = 100
    sc.render.engine = 'BLENDER_WORKBENCH'; sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'TEXTURE'
    sc.render.resolution_x, sc.render.resolution_y = 500, 700
    # a translucent water plane at the waterline
    bpy.ops.mesh.primitive_plane_add(size=0.5, location=(0, 0, 0)); water = bpy.context.object
    wm = bpy.data.materials.new("water"); wm.diffuse_color = (0.15, 0.35, 0.55, 0.55); water.data.materials.append(wm)
    sc.display.shading.color_type = 'TEXTURE'
    cd = bpy.data.cameras.new("C"); cd.type = 'ORTHO'; cd.ortho_scale = H * 1.25
    cam = bpy.data.objects.new("C", cd); sc.collection.objects.link(cam); sc.camera = cam
    mid = Vector((0, 0, (hi[2] + lo[2]) / 2))
    for name, d in (("side", (1, -0.3, 0.12)), ("high", (1, -1, 1.1))):
        cam.location = mid + Vector(d).normalized() * 3; cam.rotation_euler = (mid - cam.location).to_track_quat('-Z', 'Y').to_euler()
        water.hide_render = name != "high"
        sc.render.filepath = f"{R}_{name}.png"; bpy.ops.render.render(write_still=True)
    water.hide_render = True
    sc.render.filepath = f"{R}_plain.png"; cam.location = mid + Vector((1, -0.3, 0.12)).normalized() * 3
    cam.rotation_euler = (mid - cam.location).to_track_quat('-Z', 'Y').to_euler(); bpy.ops.render.render(write_still=True)
print("===== END =====")
