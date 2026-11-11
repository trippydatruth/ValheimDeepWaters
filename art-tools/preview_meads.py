# Preview of the mead bottles (build_lures mead, baked by bake_wood_cooler.py VDW_KIND=lure): each baked bottle in a row,
# the glass see-through as it will be in game (its own faces, alpha VDW_GLASS_ALPHA) and the mead glowing through it.
#   blender -b --factory-startup --python preview_meads.py
#   env: VDW_BAKED (baked .blend files, comma separated), VDW_PREVIEW (png out), VDW_GLASS_ALPHA (0.3)
import bpy, os, math
from mathutils import Vector

FILES = [f for f in os.environ["VDW_BAKED"].split(",") if f]
OUT = os.environ["VDW_PREVIEW"]
if os.path.exists(OUT): raise SystemExit("exists, kept: " + OUT)
ALPHA = float(os.environ.get("VDW_GLASS_ALPHA", "0.3"))
for o in list(bpy.data.objects): bpy.data.objects.remove(o)

def tex(N, path, non_color=False):
    n = N.new("ShaderNodeTexImage"); n.image = bpy.data.images.load(path, check_existing=True)
    if non_color: n.image.colorspace_settings.name = 'Non-Color'
    return n

def material(name, texdir, key, glass):
    m = bpy.data.materials.new(name); m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links; b = N["Principled BSDF"]
    alb = tex(N, os.path.join(texdir, f"{key}_Unity_Albedo.png")); L.new(alb.outputs["Color"], b.inputs["Base Color"])
    ms = tex(N, os.path.join(texdir, f"{key}_Unity_MetallicSmoothness.png"), True)
    inv = N.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
    L.new(ms.outputs["Alpha"], inv.inputs[1]); L.new(inv.outputs[0], b.inputs["Roughness"])
    em = os.path.join(texdir, f"{key}_Unity_Emission.png")
    if glass:
        b.inputs["Alpha"].default_value = ALPHA
        if hasattr(m, "surface_render_method"): m.surface_render_method = 'BLENDED'
        else: m.blend_method = 'BLEND'
        m.use_backface_culling = False
    elif os.path.exists(em) and key != "cork":
        e = tex(N, em); L.new(e.outputs["Color"], b.inputs["Emission Color"]); b.inputs["Emission Strength"].default_value = 2.5
    return m

# FILES: the exported bottles (export_mead.py: <key>/<key>_model.fbx and its texture sets), each part with its own set
for i, f in enumerate(FILES):
    key = os.path.basename(os.path.dirname(f)); texdir = os.path.dirname(f)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=f)
    parts = [o for o in bpy.data.objects if o not in before]
    root = bpy.data.objects.new(key, None); bpy.context.scene.collection.objects.link(root)
    for o in parts:
        if o.type != 'MESH': continue
        part = o.name.split(".")[0]
        setname = {"glass": "glass", "cork": "cork"}.get(part, key)
        m = material(f"{key}_{part}", texdir, setname, part == "glass")
        o.data.materials.clear(); o.data.materials.append(m)
        for s in o.material_slots: s.link = 'DATA'
        if o.parent is None: o.parent = root
    root.location = ((i - (len(FILES) - 1) / 2) * 0.24, 0, 0); root.rotation_euler = (0, 0, math.radians(20))
# a dark wooden floor, a dim blue night, one warm lamp
bpy.ops.mesh.primitive_plane_add(size=4); fl = bpy.context.object
fm = bpy.data.materials.new("floor"); fm.use_nodes = True; fm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.05, 0.035, 0.025, 1)
fl.data.materials.append(fm)
w = bpy.data.worlds.new("w"); w.use_nodes = True; w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.012, 0.015, 0.025, 1)
bpy.context.scene.world = w
bpy.ops.object.light_add(type='AREA', location=(0.4, -0.8, 0.9)); lt = bpy.context.object; lt.data.energy = 60; lt.data.size = 1.2
lt.rotation_euler = (math.radians(50), 0, math.radians(25)); lt.data.color = (1.0, 0.9, 0.78)
dist = 1.0 + 0.32 * len(FILES)
bpy.ops.object.camera_add(location=(0, -dist, 0.38)); cam = bpy.context.object
d = Vector((0, 0, 0.15)) - cam.location; cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
cam.data.lens = 50
sc = bpy.context.scene; sc.camera = cam
sc.render.engine = 'BLENDER_EEVEE' if 'BLENDER_EEVEE' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE_NEXT'
sc.render.resolution_x, sc.render.resolution_y = 1600, 800
sc.view_settings.view_transform = 'AgX' if 'AgX' in [v.identifier for v in sc.view_settings.bl_rna.properties['view_transform'].enum_items] else 'Filmic'
try: sc.eevee.use_bloom = True
except Exception: pass
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT.replace(".png", ".blend"))
print("PREVIEW", OUT)
