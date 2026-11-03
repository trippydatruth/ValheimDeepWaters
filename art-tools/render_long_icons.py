# Diagonal full-length icons for long items (the leisters): transparent, the whole spear corner to corner, head top right.
#   blender --factory-startup -b --python render_long_icons.py      env: VDW_ASSETS (folder of <key>\), VDW_KEYS, VDW_OUT, VDW_SIZE
import bpy, os, math, mathutils
ASSETS = os.environ["VDW_ASSETS"]; OUT = os.environ["VDW_OUT"]; KEYS = os.environ["VDW_KEYS"].split(","); SIZE = int(os.environ.get("VDW_SIZE", "512"))
os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene
eng = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
sc.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in eng else "BLENDER_EEVEE"
sc.render.film_transparent = True; sc.render.resolution_x = sc.render.resolution_y = SIZE
sc.view_settings.view_transform = "Standard"
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (0.6, 0.62, 0.66, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.6
def light(name, energy, rot):
    o = bpy.data.objects.new(name, bpy.data.lights.new(name, "SUN")); sc.collection.objects.link(o); o.data.energy = energy; o.rotation_euler = rot
light("key", 3.0, (math.radians(40), math.radians(10), math.radians(25))); light("fill", 1.0, (math.radians(65), 0, math.radians(-140)))
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "ORTHO"; cam.location = (0, -6, 0); cam.rotation_euler = (math.radians(90), 0, 0)
def mat(folder, key):
    m = bpy.data.materials.new(key); m.use_nodes = True; N, L = m.node_tree.nodes, m.node_tree.links; b = N["Principled BSDF"]
    def tex(kind, data=False):
        p = os.path.join(folder, f"{key}_Unity_{kind}.png")
        if not os.path.exists(p): return None
        t = N.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(p)
        if data: t.image.colorspace_settings.name = "Non-Color"
        return t
    a, e, n, ms = tex("Albedo"), tex("Emission"), tex("Normal", True), tex("MetallicSmoothness", True)
    if a: L.new(a.outputs["Color"], b.inputs["Base Color"])
    if e: L.new(e.outputs["Color"], b.inputs["Emission Color"]); b.inputs["Emission Strength"].default_value = 1.5
    if n: nm = N.new("ShaderNodeNormalMap"); L.new(n.outputs["Color"], nm.inputs["Color"]); L.new(nm.outputs["Normal"], b.inputs["Normal"])
    if ms:
        L.new(ms.outputs["Color"], b.inputs["Metallic"]); inv = N.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1
        L.new(ms.outputs["Alpha"], inv.inputs[1]); L.new(inv.outputs[0], b.inputs["Roughness"])
    return m
for key in KEYS:
    for o in [o for o in sc.objects if o.type in ("MESH", "EMPTY")]: bpy.data.objects.remove(o)
    folder = os.path.join(ASSETS, key); before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(folder, key + "_model.fbx"))
    new = [o for o in bpy.data.objects if o not in before]; m = mat(folder, key)
    meshes = [o for o in new if o.type == "MESH"]
    for o in meshes: o.data.materials.clear(); o.data.materials.append(m)
    root = [o for o in new if o.parent is None][0]
    bpy.context.view_layer.update()
    # stand it up (long axis to Z, head = wider end up), then tip it 45 degrees in the picture plane: head top right
    pts = [o.matrix_world @ v.co for o in meshes for v in o.data.vertices]
    ext = [max(p[i] for p in pts) - min(p[i] for p in pts) for i in range(3)]; ax = ext.index(max(ext))
    if ax == 1: root.rotation_euler = (math.radians(-90), 0, 0)
    elif ax == 0: root.rotation_euler = (0, math.radians(90), 0)
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ v.co for o in meshes for v in o.data.vertices]
    zs = [p.z for p in pts]; lo, hi = min(zs), max(zs)
    def width(sel): return max(abs(p.x) for p in sel) if sel else 0
    if width([p for p in pts if p.z < lo + 0.15 * (hi - lo)]) > width([p for p in pts if p.z > hi - 0.15 * (hi - lo)]):
        root.rotation_euler.rotate(mathutils.Euler((math.radians(180), 0, 0)))
    root.rotation_euler.rotate(mathutils.Euler((0, math.radians(45), 0)))   # head toward +X+Z: top right as the camera sees it
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ v.co for o in meshes for v in o.data.vertices]
    xs = [p.x for p in pts]; zs = [p.z for p in pts]
    cx, cz = (min(xs) + max(xs)) / 2, (min(zs) + max(zs)) / 2
    cam.location = (cx, -6, cz); cam.data.ortho_scale = max(max(xs) - min(xs), max(zs) - min(zs)) * 1.06
    sc.render.filepath = os.path.join(OUT, key + ".png"); bpy.ops.render.render(write_still=True)
    print("ICON", key)