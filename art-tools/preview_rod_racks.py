# Preview of the rod rack and rod holder (build_rod_racks.py, baked by bake_wood_cooler.py VDW_KIND=lure): both on a
# patch of ground with plain stand-in rods (a cork grip and a dark blank, not the mod's rod models) to show how they hold.
#   blender -b --factory-startup --python preview_rod_racks.py   env: VDW_DIR (the v1 folder), VDW_PREVIEW (png out)
import bpy, os, math
from mathutils import Vector

D = os.environ["VDW_DIR"]; OUT = os.environ["VDW_PREVIEW"]
if os.path.exists(OUT): raise SystemExit("exists, kept: " + OUT)
for o in list(bpy.data.objects): bpy.data.objects.remove(o)

def tex(N, p, nc=False):
    n = N.new("ShaderNodeTexImage"); n.image = bpy.data.images.load(p)
    if nc: n.image.colorspace_settings.name = 'Non-Color'
    return n

def baked(tier, at, turn=0.0):
    with bpy.data.libraries.load(os.path.join(D, "bake", f"bait_{tier}_baked.blend")) as (src, dst): dst.objects = ["bait"]
    ob = dst.objects[0]; bpy.context.scene.collection.objects.link(ob); ob.data = ob.data.copy()
    for md in list(ob.modifiers): ob.modifiers.remove(md)
    ob.parent = None
    me = ob.data
    if "Grain" in me.uv_layers: me.uv_layers.remove(me.uv_layers["Grain"])
    td = os.path.join(D, "bake", f"bait_{tier}"); key = f"bait_{tier}"
    m = bpy.data.materials.new(tier); m.use_nodes = True; N, L = m.node_tree.nodes, m.node_tree.links; b = N["Principled BSDF"]
    L.new(tex(N, os.path.join(td, f"{key}_Unity_Albedo.png")).outputs["Color"], b.inputs["Base Color"])
    ms = tex(N, os.path.join(td, f"{key}_Unity_MetallicSmoothness.png"), True)
    sep = N.new("ShaderNodeSeparateColor"); L.new(ms.outputs["Color"], sep.inputs["Color"]); L.new(sep.outputs["Red"], b.inputs["Metallic"])
    inv = N.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
    L.new(ms.outputs["Alpha"], inv.inputs[1]); L.new(inv.outputs[0], b.inputs["Roughness"])
    nm = N.new("ShaderNodeNormalMap"); L.new(tex(N, os.path.join(td, f"{key}_Unity_Normal.png"), True).outputs["Color"], nm.inputs["Color"]); L.new(nm.outputs["Normal"], b.inputs["Normal"])
    me.materials.clear(); me.materials.append(m)
    for p in me.polygons: p.material_index = 0
    for s in ob.material_slots: s.link = 'DATA'
    ob.matrix_world.identity(); ob.location = at; ob.rotation_euler = (0, 0, turn)
    return ob

def flat(name, col, rough=0.5, metal=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*col, 1); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    return m
CORK, BLANK, REEL = flat("cork", (0.55, 0.40, 0.24), 0.8), flat("blank", (0.04, 0.035, 0.03), 0.3), flat("reel", (0.5, 0.5, 0.52), 0.35, 1.0)

def cyl(a, b, r, mat, r2=None):
    a, b = Vector(a), Vector(b); d = b - a
    bpy.ops.mesh.primitive_cone_add(vertices=12, radius1=r, radius2=r2 if r2 is not None else r, depth=d.length, location=(a + b) / 2)
    o = bpy.context.object; o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler(); o.data.materials.append(mat)
    return o

RODS = os.environ.get("VDW_RODS", "1") == "1"   # 0: the pieces empty, as they're placed
def rod(butt, lean_dir, lean, length=1.9):
    """A stand-in rod from its butt, leaning off vertical by lean (radians) toward lean_dir."""
    if not RODS: return
    d = (Vector((0, 0, 1)) * math.cos(lean) + Vector(lean_dir).normalized() * math.sin(lean)).normalized()
    b = Vector(butt)
    cyl(b, b + d * 0.32, 0.0135, CORK)
    cyl(b + d * 0.32, b + d * length, 0.008, BLANK, 0.0025)
    side = d.cross(Vector((0, 0, 1))).normalized() if abs(d.z) < 0.999 else Vector((1, 0, 0))
    bpy.ops.mesh.primitive_cylinder_add(vertices=14, radius=0.03, depth=0.035, location=b + d * 0.24 + side * 0.045)
    r = bpy.context.object; r.rotation_euler = side.to_track_quat('Z', 'Y').to_euler(); r.data.materials.append(REEL)

rack = baked("rack_round", (-0.45, 0, 0), 0.15)
SLOTS, SLOT_R, BASE_H = 10, 0.30, 0.075
for k in range(SLOTS):
    if k in (3, 7): continue                       # a couple of empty slots
    a = 2 * math.pi * k / SLOTS + 0.15
    u = Vector((math.cos(a), math.sin(a), 0))
    rod(Vector((-0.45, 0, BASE_H + 0.003)) + u * SLOT_R, u, 0.03)
holder = baked("rod_holder", (0.55, -0.1, 0), 0.4)
# a rod resting in the holder's fork, its butt by the iron ring
fork = Vector((0.55, -0.1, 0.72)); butt = Vector((0.55, -0.1, 0)) + Vector((0.0, -0.1, 0.0)).normalized() * 0.0
d = Vector((0.15, 1.0, 0.0)).normalized()
rod_butt = fork - d * 0.55 - Vector((0, 0, 0.6)); rod_butt.z = max(rod_butt.z, 0.02)
dirv = (fork - rod_butt).normalized()
lean = math.acos(max(-1.0, min(1.0, dirv.z))); hd = Vector((dirv.x, dirv.y, 0))
rod(rod_butt, hd, lean, 2.0)

bpy.ops.mesh.primitive_plane_add(size=6); g = bpy.context.object
g.data.materials.append(flat("ground", (0.10, 0.085, 0.06), 0.95))
w = bpy.data.worlds.new("w"); w.use_nodes = True; w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.35, 0.42, 0.5, 1)
w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6; bpy.context.scene.world = w
bpy.ops.object.light_add(type='SUN', rotation=(math.radians(50), 0, math.radians(35))); s = bpy.context.object; s.data.energy = 3.0; s.data.color = (1.0, 0.93, 0.82)
sc = bpy.context.scene
names = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]
sc.render.engine = 'BLENDER_EEVEE' if 'BLENDER_EEVEE' in names else 'BLENDER_EEVEE_NEXT'
vt = [v.identifier for v in sc.view_settings.bl_rna.properties['view_transform'].enum_items]
sc.view_settings.view_transform = 'AgX' if 'AgX' in vt else 'Filmic'
shots = [("wide", (0.1, -3.2, 1.35), (0.05, 0, 0.85), 40), ("rack_close", (-0.45 + 0.9, -1.0, 1.25), (-0.45, 0, 0.55), 45),
         ("holder_close", (0.55 + 0.55, -0.1 - 0.75, 0.75), (0.55, -0.1, 0.45), 50)]
for name, loc, look, lens in shots:
    bpy.ops.object.camera_add(location=loc); c = bpy.context.object
    c.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); c.data.lens = lens; sc.camera = c
    sc.render.resolution_x, sc.render.resolution_y = (1600, 1000) if name == "wide" else (1000, 1000)
    sc.render.filepath = OUT.replace(".png", f"_{name}.png"); bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT.replace(".png", ".blend"))
print("PREVIEW", OUT)
