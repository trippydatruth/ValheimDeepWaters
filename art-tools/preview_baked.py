# Preview of baked pieces (build_lures.py -> restyle_lure.py -> bake_wood_cooler.py VDW_KIND=lure): each baked "bait"
# object with its Unity maps, placed and turned as told, on a ground of the chosen look, from one or more cameras.
#   blender -b --factory-startup --python preview_baked.py
#   env: VDW_BAKE (the bake folder), VDW_PREVIEW (png out; shots add _<name>), VDW_GROUND (ice | dirt),
#        VDW_ITEMS: tier@x,y,z@rx,ry,rz@scale;...   VDW_SHOTS: name@camx,camy,camz@lookx,looky,lookz@lens;...
#        VDW_ALPHA=1: the albedo's alpha cuts the surface (hair cards)
import bpy, os, math
from mathutils import Vector

BAKE = os.environ["VDW_BAKE"]; OUT = os.environ["VDW_PREVIEW"]
if os.path.exists(OUT.replace(".png", ".blend")): raise SystemExit("exists, kept: " + OUT)
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
def vec(s): return Vector(tuple(float(x) for x in s.split(",")))

def tex(N, p, nc=False):
    n = N.new("ShaderNodeTexImage"); n.image = bpy.data.images.load(p)
    if nc: n.image.colorspace_settings.name = 'Non-Color'
    return n

for entry in [e for e in os.environ["VDW_ITEMS"].split(";") if e]:
    tier, at, rot, scale = entry.split("@")
    with bpy.data.libraries.load(os.path.join(BAKE, f"bait_{tier}_baked.blend")) as (src, dst): dst.objects = ["bait"]
    ob = dst.objects[0]; bpy.context.scene.collection.objects.link(ob); ob.data = ob.data.copy(); ob.name = tier
    for md in list(ob.modifiers): ob.modifiers.remove(md)
    ob.parent = None
    me = ob.data
    if "Grain" in me.uv_layers: me.uv_layers.remove(me.uv_layers["Grain"])
    td, key = os.path.join(BAKE, f"bait_{tier}"), f"bait_{tier}"
    m = bpy.data.materials.new(tier); m.use_nodes = True; N, L = m.node_tree.nodes, m.node_tree.links; b = N["Principled BSDF"]
    al = tex(N, os.path.join(td, f"{key}_Unity_Albedo.png")); L.new(al.outputs["Color"], b.inputs["Base Color"])
    if os.environ.get("VDW_ALPHA") == "1": L.new(al.outputs["Alpha"], b.inputs["Alpha"])   # cut-out parts (hair cards)
    ms = tex(N, os.path.join(td, f"{key}_Unity_MetallicSmoothness.png"), True)
    sep = N.new("ShaderNodeSeparateColor"); L.new(ms.outputs["Color"], sep.inputs["Color"]); L.new(sep.outputs["Red"], b.inputs["Metallic"])
    inv = N.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
    L.new(ms.outputs["Alpha"], inv.inputs[1]); L.new(inv.outputs[0], b.inputs["Roughness"])
    nm = N.new("ShaderNodeNormalMap"); L.new(tex(N, os.path.join(td, f"{key}_Unity_Normal.png"), True).outputs["Color"], nm.inputs["Color"]); L.new(nm.outputs["Normal"], b.inputs["Normal"])
    em = os.path.join(td, f"{key}_Unity_Emission.png")
    if os.path.exists(em): L.new(tex(N, em).outputs["Color"], b.inputs["Emission Color"]); b.inputs["Emission Strength"].default_value = 2.0
    me.materials.clear(); me.materials.append(m)
    for p in me.polygons: p.material_index = 0
    for s in ob.material_slots: s.link = 'DATA'
    ob.matrix_world.identity()
    ob.location = vec(at); ob.rotation_euler = tuple(math.radians(a) for a in vec(rot)); ob.scale = (float(scale),) * 3

ground = os.environ.get("VDW_GROUND", "ice")
bpy.ops.mesh.primitive_plane_add(size=8); g = bpy.context.object
gm = bpy.data.materials.new("ground"); gm.use_nodes = True; gb = gm.node_tree.nodes["Principled BSDF"]
if ground == "ice":
    gb.inputs["Base Color"].default_value = (0.55, 0.68, 0.78, 1); gb.inputs["Roughness"].default_value = 0.12
    nz = gm.node_tree.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 3.0
    mix = gm.node_tree.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'
    gm.node_tree.links.new(nz.outputs["Fac"], mix.inputs["Factor"])
    mix.inputs[6].default_value = (0.42, 0.56, 0.68, 1); mix.inputs[7].default_value = (0.86, 0.9, 0.94, 1)
    gm.node_tree.links.new(mix.outputs[2], gb.inputs["Base Color"])
else:
    gb.inputs["Base Color"].default_value = (0.12, 0.1, 0.08, 1); gb.inputs["Roughness"].default_value = 0.9
g.data.materials.append(gm)
w = bpy.data.worlds.new("w"); w.use_nodes = True; w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.55, 0.62, 0.72, 1)
w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.7; bpy.context.scene.world = w
bpy.ops.object.light_add(type='SUN', rotation=(math.radians(50), 0, math.radians(30))); s = bpy.context.object; s.data.energy = 3.0; s.data.color = (1.0, 0.96, 0.9)
sc = bpy.context.scene
names = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]
sc.render.engine = 'BLENDER_EEVEE' if 'BLENDER_EEVEE' in names else 'BLENDER_EEVEE_NEXT'
vt = [v.identifier for v in sc.view_settings.bl_rna.properties['view_transform'].enum_items]
sc.view_settings.view_transform = 'AgX' if 'AgX' in vt else 'Filmic'
for shot in [e for e in os.environ["VDW_SHOTS"].split(";") if e]:
    name, loc, look, lens = shot.split("@")
    bpy.ops.object.camera_add(location=vec(loc)); c = bpy.context.object
    c.rotation_euler = (vec(look) - vec(loc)).to_track_quat('-Z', 'Y').to_euler(); c.data.lens = float(lens); c.data.clip_start = 0.005; sc.camera = c
    sc.render.resolution_x, sc.render.resolution_y = 1200, 1200
    sc.render.filepath = OUT.replace(".png", f"_{name}.png"); bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT.replace(".png", ".blend"))
print("PREVIEW", OUT)
