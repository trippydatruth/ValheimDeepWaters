# Makes the bobber's sight antenna glow (night-float style): faces above the body that are antenna-thin get their
# own colours in an emission map; the body stays unlit. Writes <name>_Unity_Emission.png, wires it into the material,
# saves the .blend, re-exports the FBX and renders dark-scene previews.
#   env: VDW_TEX_DIR, VDW_SAVE_TO, VDW_FBX_OUT, VDW_GLOW_PREVIEW, VDW_GLOW_STRENGTH (default 4), VDW_MAX_RADIUS (m)
import bpy, os, math
import numpy as np
from mathutils import Vector

TEX = os.environ["VDW_TEX_DIR"]; STRENGTH = float(os.environ.get("VDW_GLOW_STRENGTH", "4"))
mesh = bpy.data.objects["bobber"]; me = mesh.data
mat = me.materials[0]; nt = mat.node_tree; nodes, links = nt.nodes, nt.links
bsdf = next(n for n in nodes if n.type == 'BSDF_PRINCIPLED')
alb = next(l.from_node.image for l in links if l.to_node == bsdf and l.to_socket.name == "Base Color")
W, H = alb.size; px = np.empty(W * H * 4, dtype=np.float32); alb.pixels.foreach_get(px); px = px.reshape(H, W, 4)

co = np.array([v.co[:] for v in me.vertices]); r = np.hypot(co[:, 0], co[:, 1])
body_r = r.max()
max_r = float(os.environ.get("VDW_MAX_RADIUS") or 0.2 * body_r)          # antenna-thin
z_body_top = co[r > 0.5 * body_r][:, 2].max()                            # top of the egg-shaped body
uv = me.uv_layers.active.data
mask = np.zeros((H, W), dtype=np.float32); nfaces = 0
for poly in me.polygons:
    vs = list(poly.vertices)
    if not all(r[v] < max_r and co[v, 2] > z_body_top - 0.005 for v in vs): continue
    nfaces += 1
    pts = np.array([uv[li].uv[:] for li in poly.loop_indices]) * [W, H]
    x0, y0 = np.floor(pts.min(0)).astype(int); x1, y1 = np.ceil(pts.max(0)).astype(int)
    xs, ys = np.meshgrid(np.arange(max(0, x0 - 2), min(W, x1 + 3)), np.arange(max(0, y0 - 2), min(H, y1 + 3)))
    P = np.stack([xs + 0.5, ys + 0.5], -1)
    for k in range(1, len(pts) - 1):            # fan-triangulate, fill each triangle
        a, b, c = pts[0], pts[k], pts[k + 1]
        def side(p, q, s): return (p[..., 0] - s[0]) * (q[1] - s[1]) - (q[0] - s[0]) * (p[..., 1] - s[1])
        d1, d2, d3 = side(P, a, b), side(P, b, c), side(P, c, a)
        inside = ~(((d1 < 0) | (d2 < 0) | (d3 < 0)) & ((d1 > 0) | (d2 > 0) | (d3 > 0)))
        mask[ys[inside], xs[inside]] = 1.0
# grow by a few pixels so the edges of the UV islands don't show a dark seam
for _ in range(4):
    p = np.pad(mask, 1); mask = np.maximum.reduce([p[1:-1, 1:-1], p[:-2, 1:-1], p[2:, 1:-1], p[1:-1, :-2], p[1:-1, 2:]])
glow = px[:, :, :3] * mask[:, :, None]
peak = np.maximum(glow.max(2, keepdims=True), 1e-6)
glow = np.where(mask[:, :, None] > 0, glow / np.maximum(peak, 0.35), 0)   # vivid, whatever its painted brightness
out = np.ones((H, W, 4), dtype=np.float32); out[:, :, :3] = np.clip(glow, 0, 1)
path = os.path.join(TEX, "bobber_Unity_Emission.png")
em = bpy.data.images.get("bobber_Unity_Emission") or bpy.data.images.new("bobber_Unity_Emission", W, H, alpha=False)
em.pixels.foreach_set(out.ravel()); em.filepath_raw = path; em.file_format = 'PNG'; em.save()
print(f"\n===== GLOW =====\n  antenna: {nfaces} faces above z {z_body_top:.3f} m, thinner than {max_r * 100:.1f} cm; {mask.mean() * 100:.2f}% of the texture glows")
print("  saved", path)
for n in [n for n in nodes if n.type == 'TEX_IMAGE' and n.image and "_Emission" in n.image.name]: nodes.remove(n)
en = nodes.new("ShaderNodeTexImage"); en.image = em; en.location = (-700, -650)
links.new(en.outputs["Color"], bsdf.inputs["Emission Color"]); bsdf.inputs["Emission Strength"].default_value = STRENGTH
nodes.active = next(n for n in nodes if n.type == 'TEX_IMAGE' and n.image == alb)
bpy.ops.wm.save_as_mainfile(filepath=os.environ["VDW_SAVE_TO"]); print("  saved", os.environ["VDW_SAVE_TO"])

FBX = os.environ.get("VDW_FBX_OUT")
if FBX:
    for o in bpy.context.view_layer.objects: o.select_set(False)
    mesh.select_set(True); bpy.context.view_layer.objects.active = mesh
    bpy.ops.export_scene.fbx(filepath=FBX, use_selection=True, object_types={'MESH'}, global_scale=1.0, apply_unit_scale=True,
                             apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y', bake_space_transform=True,
                             mesh_smooth_type='FACE', bake_anim=False, path_mode='COPY', embed_textures=True)
    print("  EXPORTED", FBX, os.path.getsize(FBX), "bytes")

PREV = os.environ.get("VDW_GLOW_PREVIEW")
if PREV:
    sc = bpy.context.scene; sc.render.use_border = False; sc.render.resolution_percentage = 100
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 32
    sc.render.resolution_x, sc.render.resolution_y = 500, 700; sc.view_settings.view_transform = 'Standard'
    wd = bpy.data.worlds.new("night"); wd.use_nodes = True; wd.node_tree.nodes["Background"].inputs[0].default_value = (0.01, 0.015, 0.03, 1); sc.world = wd
    for o in [o for o in bpy.data.objects if o.type in ('LIGHT', 'CAMERA')]: bpy.data.objects.remove(o)
    ld = bpy.data.lights.new("moon", 'SUN'); ld.energy = 0.25; lo = bpy.data.objects.new("moon", ld); sc.collection.objects.link(lo); lo.rotation_euler = (0.9, 0.2, 0.6)
    bpy.ops.mesh.primitive_plane_add(size=1.2, location=(0, 0, 0)); water = bpy.context.object
    wm = bpy.data.materials.new("water"); wm.use_nodes = True; wb = next(n for n in wm.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    wb.inputs["Base Color"].default_value = (0.02, 0.05, 0.08, 1); wb.inputs["Roughness"].default_value = 0.05; water.data.materials.append(wm)
    co2 = np.array([v.co[:] for v in me.vertices]); mid = Vector((0, 0, float(co2[:, 2].mean())))
    cd = bpy.data.cameras.new("C"); cd.type = 'ORTHO'; cd.ortho_scale = 0.62
    cam = bpy.data.objects.new("C", cd); sc.collection.objects.link(cam); sc.camera = cam
    cam.location = mid + Vector((1, -0.5, 0.35)).normalized() * 3; cam.rotation_euler = (mid - cam.location).to_track_quat('-Z', 'Y').to_euler()
    for name, strength in (("off", 0.0), ("on", STRENGTH)):
        bsdf.inputs["Emission Strength"].default_value = strength
        sc.render.filepath = f"{PREV}_{name}.png"; bpy.ops.render.render(write_still=True)
print("===== END =====")
