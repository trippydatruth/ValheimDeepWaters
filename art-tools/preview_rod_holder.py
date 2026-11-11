# Preview of the rod holder (build_rod_racks.py rod_holder, baked) with one of the mod's rods resting in its fork at an
# angle, like a bank rod holder: the foregrip in the fork, the reel in front of it, the butt behind and off the ground.
#   blender -b --factory-startup --python preview_rod_holder.py
#   env: VDW_DIR (the holder's version folder), VDW_ROD (Assets/DeepWaters/rod_<id> folder), VDW_PREVIEW (png out),
#        VDW_ANGLE (degrees above level, 25), VDW_REST (how high the rod lies in the fork, m), VDW_GRIP (m of rod behind the fork)
import bpy, os, math, glob
from mathutils import Vector, Matrix

D = os.environ["VDW_DIR"]; ROD = os.environ["VDW_ROD"]; OUT = os.environ["VDW_PREVIEW"]
ANGLE = math.radians(float(os.environ.get("VDW_ANGLE", "25"))); REST = float(os.environ.get("VDW_REST", "0.665"))
GRIP = float(os.environ.get("VDW_GRIP", "0.42"))
# VDW_GROUNDED=1: the butt set on the ground and the rod leaned into the fork - how far back the butt sits follows from the angle
if os.environ.get("VDW_GROUNDED") == "1": GRIP = (REST - 0.016) / math.sin(ANGLE)
if os.path.exists(OUT): raise SystemExit("exists, kept: " + OUT)
for o in list(bpy.data.objects): bpy.data.objects.remove(o)

def tex(N, p, nc=False):
    n = N.new("ShaderNodeTexImage"); n.image = bpy.data.images.load(p)
    if nc: n.image.colorspace_settings.name = 'Non-Color'
    return n

def material(name, maps, glow=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; N, L = m.node_tree.nodes, m.node_tree.links; b = N["Principled BSDF"]
    L.new(tex(N, maps["Albedo"]).outputs["Color"], b.inputs["Base Color"])
    if "MetallicSmoothness" in maps:
        ms = tex(N, maps["MetallicSmoothness"], True)
        sep = N.new("ShaderNodeSeparateColor"); L.new(ms.outputs["Color"], sep.inputs["Color"]); L.new(sep.outputs["Red"], b.inputs["Metallic"])
        inv = N.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
        L.new(ms.outputs["Alpha"], inv.inputs[1]); L.new(inv.outputs[0], b.inputs["Roughness"])
    if "Normal" in maps:
        nm = N.new("ShaderNodeNormalMap"); L.new(tex(N, maps["Normal"], True).outputs["Color"], nm.inputs["Color"]); L.new(nm.outputs["Normal"], b.inputs["Normal"])
    if "Emission" in maps and glow:
        L.new(tex(N, maps["Emission"]).outputs["Color"], b.inputs["Emission Color"]); b.inputs["Emission Strength"].default_value = glow
    return m

def maps_in(folder, prefix):
    out = {}
    for k in ("Albedo", "MetallicSmoothness", "Normal", "Emission"):
        f = os.path.join(folder, f"{prefix}_Unity_{k}.png")
        if os.path.exists(f): out[k] = f
    return out

# the holder, as baked
with bpy.data.libraries.load(os.path.join(D, "bake", "bait_rod_holder_baked.blend")) as (src, dst): dst.objects = ["bait"]
h = dst.objects[0]; bpy.context.scene.collection.objects.link(h); h.data = h.data.copy()
for md in list(h.modifiers): h.modifiers.remove(md)
h.parent = None; h.matrix_world.identity()
if "Grain" in h.data.uv_layers: h.data.uv_layers.remove(h.data.uv_layers["Grain"])
hm = material("holder", maps_in(os.path.join(D, "bake", "bait_rod_holder"), "bait_rod_holder"))
h.data.materials.clear(); h.data.materials.append(hm)
for p in h.data.polygons: p.material_index = 0
for s in h.material_slots: s.link = 'DATA'

# the rod (render_icons: after import its tip points +Z and its "up" is +Y), at rest in its pose
key = os.path.basename(ROD.rstrip("\\/"))
before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=os.path.join(ROD, f"{key}_model.fbx"))
parts = [o for o in bpy.data.objects if o not in before]
rm = material(key, maps_in(ROD, key), 1.0)
for o in parts:
    if o.type == 'ARMATURE':
        if o.animation_data: o.animation_data.action = None
        o.data.pose_position = 'REST'
    if o.type == 'MESH':
        o.data.materials.clear(); o.data.materials.append(rm)
        for s in o.material_slots: s.link = 'DATA'
bpy.context.view_layer.update()
pts = [o.matrix_world @ v.co for o in parts if o.type == 'MESH' for v in o.data.vertices]
zmin = min(p.z for p in pts); zmax = max(p.z for p in pts)
print(f"ROD {key}: {zmax - zmin:.2f} m long")
# where the reel hangs: the side the mesh bulges to near the butt, so it can hang under the rod
near = [p for p in pts if p.z < zmin + 0.45 * (zmax - zmin)]
cy = sum(p.y for p in near) / len(near); cx = sum(p.x for p in near) / len(near)
reel = Vector((cx, cy, 0)).normalized() if Vector((cx, cy, 0)).length > 1e-4 else Vector((0, 1, 0))
root = bpy.data.objects.new("rod", None); bpy.context.scene.collection.objects.link(root)
for o in parts:
    if o.parent is None: o.parent = root
# rod axis: from the butt toward the tip, up through the fork at ANGLE; the reel turned to hang underneath
d = Vector((0, math.cos(ANGLE), math.sin(ANGLE)))
down = Vector((0, math.sin(ANGLE), -math.cos(ANGLE)))     # perpendicular to the rod, pointing down
side = d.cross(down)
# local frame: +Z -> d, the reel's side -> down
rz = Vector((0, 0, 1)); rr = reel; rx = rr.cross(rz)
R_local = Matrix((rx, rr, rz)).transposed()                 # columns: rx, reel, z
R_world = Matrix((down.cross(d), down, d)).transposed()     # columns: the same axes in the world
rot = (R_world @ R_local.inverted()).to_4x4()
fork = Vector((0, 0, REST))
butt = fork - d * GRIP
ROLL = math.radians(float(os.environ.get("VDW_ROLL", "0")))   # a turn about the rod's own length, if the reel still isn't under it
root.matrix_world = Matrix.Translation(butt) @ Matrix.Rotation(ROLL, 4, d) @ rot @ Matrix.Translation(Vector((0, 0, -zmin)))
print(f"ROD butt at {tuple(round(c, 3) for c in butt)}, {math.degrees(ANGLE):.0f} degrees, reel side {tuple(round(c, 2) for c in reel)}")

def flat(name, col, rough=0.9):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*col, 1); b.inputs["Roughness"].default_value = rough; return m
bpy.ops.mesh.primitive_plane_add(size=8); bpy.context.object.data.materials.append(flat("ground", (0.12, 0.16, 0.06)))
w = bpy.data.worlds.new("w"); w.use_nodes = True; w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.42, 0.5, 0.58, 1)
w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.7; bpy.context.scene.world = w
bpy.ops.object.light_add(type='SUN', rotation=(math.radians(45), 0, math.radians(-40))); s = bpy.context.object; s.data.energy = 3.0
sc = bpy.context.scene
names = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]
sc.render.engine = 'BLENDER_EEVEE' if 'BLENDER_EEVEE' in names else 'BLENDER_EEVEE_NEXT'
vt = [v.identifier for v in sc.view_settings.bl_rna.properties['view_transform'].enum_items]
sc.view_settings.view_transform = 'AgX' if 'AgX' in vt else 'Filmic'
for name, loc, look, lens in (("side", (-2.9, -0.2, 1.0), (0, 0.15, 0.6), 30), ("close", (-1.1, -0.9, 0.7), (0, -0.4, 0.35), 32)):
    bpy.ops.object.camera_add(location=loc); c = bpy.context.object
    c.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); c.data.lens = lens; sc.camera = c
    sc.render.resolution_x, sc.render.resolution_y = 1200, 1200
    sc.render.filepath = OUT.replace(".png", f"_{name}.png"); bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT.replace(".png", ".blend"))
print("PREVIEW", OUT)
