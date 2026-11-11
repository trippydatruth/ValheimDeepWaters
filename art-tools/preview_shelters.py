# Shape preview of the ice-fishing shelters (build_shelters.py) before the bake: plain colours per material slot (the
# igloo's ice like Valheim's ice.mat - pale blue, glossy, its rock normal map), on snowy ice, a 1.8 m stand-in figure
# for scale and a stand-in campfire (a ring of stones and a warm light) where the game's campfire will go.
#   blender -b --factory-startup --python preview_shelters.py   env: VDW_DIR (the shelter_vN folder), VDW_PIECE,
#   VDW_PREVIEW (png out; one file per shot), VDW_BAKED=1: the baked textures (VDW_DIR/bake/bait_<piece>)
import bpy, os, math
from mathutils import Vector

D = os.environ["VDW_DIR"]; PIECE = os.environ["VDW_PIECE"]; OUT = os.environ["VDW_PREVIEW"]
BAKED = os.environ.get("VDW_BAKED") == "1"
RIP = r"C:\Users\tripp\Desktop\Valheim_DeepWaters\Rip\ExportedProject\Assets"
if any(os.path.exists(OUT.replace(".png", f"_{s}.png")) for s in ("out", "heads")): raise SystemExit("exists, kept: " + OUT)
for o in list(bpy.data.objects): bpy.data.objects.remove(o)

src = os.path.join(D, "bake", f"bait_{PIECE}_baked.blend") if BAKED else os.path.join(D, "Blender Files", f"{PIECE}.blend")
with bpy.data.libraries.load(src) as (s, d): d.objects = ["bait"]
ob = d.objects[0]; bpy.context.scene.collection.objects.link(ob); ob.data = ob.data.copy()
for md in list(ob.modifiers): ob.modifiers.remove(md)
ob.parent = None; ob.matrix_world.identity(); me = ob.data

def flat(name, col, rough=0.6, metal=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*col, 1); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    return m

def tex(N, p, nc=False):
    n = N.new("ShaderNodeTexImage"); n.image = bpy.data.images.load(p)
    if nc: n.image.colorspace_settings.name = 'Non-Color'
    return n

def vanilla_ice():
    # Valheim's ice.mat: colour (0.84, 0.97, 1), metallic 0.52, smoothness 1, gouacherock_big_n normal at 0.39, tiled 2x
    m = flat("ice", (0.70, 0.88, 0.97), 0.08, 0.35); N, L = m.node_tree.nodes, m.node_tree.links; b = N["Principled BSDF"]
    co = N.new("ShaderNodeTexCoord"); mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (0.5, 0.5, 0.5)
    L.new(co.outputs["Object"], mp.inputs["Vector"])
    t = tex(N, os.path.join(RIP, r"world\terrain\gouacherock_big_n.png"), True); t.projection = 'BOX'; t.projection_blend = 0.3
    L.new(mp.outputs["Vector"], t.inputs["Vector"])
    nm = N.new("ShaderNodeNormalMap"); nm.inputs["Strength"].default_value = 0.39
    L.new(t.outputs["Color"], nm.inputs["Color"]); L.new(nm.outputs["Normal"], b.inputs["Normal"])
    if "Transmission Weight" in b.inputs: b.inputs["Transmission Weight"].default_value = 0.15
    return m

if BAKED:   # (the igloo too, now it has its own baked ice and snow)
    td = os.path.join(D, "bake", f"bait_{PIECE}"); key = f"bait_{PIECE}"
    m = bpy.data.materials.new(PIECE); m.use_nodes = True; N, L = m.node_tree.nodes, m.node_tree.links; b = N["Principled BSDF"]
    L.new(tex(N, os.path.join(td, f"{key}_Unity_Albedo.png")).outputs["Color"], b.inputs["Base Color"])
    ms = tex(N, os.path.join(td, f"{key}_Unity_MetallicSmoothness.png"), True)
    sep = N.new("ShaderNodeSeparateColor"); L.new(ms.outputs["Color"], sep.inputs["Color"]); L.new(sep.outputs["Red"], b.inputs["Metallic"])
    inv = N.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
    L.new(ms.outputs["Alpha"], inv.inputs[1]); L.new(inv.outputs[0], b.inputs["Roughness"])
    nm = N.new("ShaderNodeNormalMap"); L.new(tex(N, os.path.join(td, f"{key}_Unity_Normal.png"), True).outputs["Color"], nm.inputs["Color"]); L.new(nm.outputs["Normal"], b.inputs["Normal"])
    me.materials.clear(); me.materials.append(m)
    for p in me.polygons: p.material_index = 0
else:
    COLS = {"ice": None, "snow": ((0.86, 0.9, 0.96), 0.85), "hide": ((0.42, 0.30, 0.19), 0.75), "hide2": ((0.55, 0.48, 0.38), 0.8), "wood": ((0.55, 0.42, 0.28), 0.7),
            "bark": ((0.22, 0.16, 0.11), 0.85), "leather": ((0.18, 0.10, 0.05), 0.6), "iron": ((0.2, 0.2, 0.21), 0.45, 1.0),
            "fur": ((0.48, 0.41, 0.32), 0.95), "linen": ((0.72, 0.66, 0.52), 0.8), "red": ((0.55, 0.06, 0.04), 0.5)}
    if PIECE == "ship_tent": COLS["hide"] = ((0.46, 0.40, 0.31), 0.75); COLS["hide2"] = ((0.30, 0.21, 0.13), 0.75); COLS["wood"] = ((0.26, 0.16, 0.08), 0.65)
    for i, s in enumerate(me.materials):
        nm_ = s.name.split(".")[0]
        me.materials[i] = vanilla_ice() if nm_ == "ice" else flat(nm_, *COLS[nm_])

# the Ship-Tent's dragon heads: Valheim's own (the Dragon Head piece's mesh and texture, from the rip), placed as
# IceShelters.AddDragonHeads does in game: each neck's base in its board's iron collar, tipped up 18 degrees so the
# neck runs on along the board, scale 0.25, looking out to that board's side (each gable's pair facing away from
# each other), tinted to the tent's oak
if PIECE == "ship_tent":
    import re, numpy as np
    t = open(os.path.join(RIP, r"GameElements\Pieces\_res\dragonhead\dragonhead.asset"), encoding="utf-8").read()
    n = int(re.search(r"m_VertexCount: (\d+)", t).group(1))
    raw = np.frombuffer(bytes.fromhex(re.search(r"_typelessdata: ([0-9a-f]+)", t).group(1)), np.float32).reshape(n, 12)
    tri = np.frombuffer(bytes.fromhex(re.search(r"m_IndexBuffer: ([0-9a-f]+)", t).group(1)), np.uint16).reshape(-1, 3)
    vs = [(-x, z, y) for x, y, z in raw[:, 0:3]]   # Unity (x, y, z) -> Blender (-x, z, y): the head's +Z to +Y
    dm = bpy.data.meshes.new("dragon"); dm.from_pydata(vs, [], [tuple(int(i) for i in f[::-1]) for f in tri]); dm.update()
    uvl = dm.uv_layers.new()
    for l in dm.loops: uvl.data[l.index].uv = tuple(raw[l.vertex_index, 10:12])
    for pg in dm.polygons: pg.use_smooth = True
    md = bpy.data.materials.new("dragon"); md.use_nodes = True; Nd = md.node_tree.nodes
    tx = tex(Nd, os.path.join(RIP, r"3rd party\ADG_Textures\Plank Textures\Planks5", "textures", "Planks5c_low.png"))
    tint = Nd.new("ShaderNodeMix"); tint.data_type = 'RGBA'; tint.blend_type = 'MULTIPLY'; tint.inputs["Factor"].default_value = 1.0
    tint.inputs[7].default_value = (0.84 ** 2.2, 0.72 ** 2.2, 0.65 ** 2.2, 1)   # HeadTint (a colour set in game is sRGB)
    md.node_tree.links.new(tx.outputs["Color"], tint.inputs[6]); md.node_tree.links.new(tint.outputs[2], Nd["Principled BSDF"].inputs["Base Color"]); dm.materials.append(md)
    for i, (end, side) in enumerate(((1, 1), (1, -1), (-1, 1), (-1, -1))):
        h = bpy.data.objects.new(f"dragon{i}", dm); bpy.context.scene.collection.objects.link(h)
        h.location = (side * 0.1435, end * 3.22, 3.579); h.scale = (0.25,) * 3
        h.rotation_euler = (math.radians(18), 0, -side * math.pi / 2)   # tipped up, then its +Y (forward) out to its board's side
# snowy ice round it
bpy.ops.mesh.primitive_plane_add(size=40); g = bpy.context.object; g.location.z = -0.005
g.data.materials.append(flat("ground", (0.78, 0.84, 0.92), 0.55))
# the stand-in campfire: a ring of stones, a few logs, a warm light
mstone, mlog, memb = flat("stone", (0.3, 0.3, 0.31), 0.8), flat("log", (0.15, 0.1, 0.06), 0.9), flat("ember", (1, 0.4, 0.1), 0.5)
memb.node_tree.nodes["Principled BSDF"].inputs["Emission Color"].default_value = (1, 0.35, 0.08, 1)
memb.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 6
FIRE = PIECE == "ship_tent"   # (only the Ship-Tent comes with a campfire)
FY = -7 * 2 * 3.2 / 30 if PIECE == "ship_tent" else 0.0   # the Ship-Tent's fire is back under its vent (build_shelters VC)
for k in range(9 if FIRE else 0):
    a = 2 * math.pi * k / 9; bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.11, location=(0.42 * math.cos(a), FY + 0.42 * math.sin(a), 0.06))
    o = bpy.context.object; o.scale = (1.2, 1.0, 0.7); o.data.materials.append(mstone)
for k in range(3 if FIRE else 0):
    a = 2 * math.pi * k / 3
    bpy.ops.mesh.primitive_cylinder_add(radius=0.05, depth=0.6, location=(0.1 * math.cos(a), FY + 0.1 * math.sin(a), 0.12))
    o = bpy.context.object; o.rotation_euler = (math.radians(70) * math.cos(a), math.radians(70) * math.sin(a), 0); o.data.materials.append(mlog)
if FIRE: bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.14, location=(0, FY, 0.1)); bpy.context.object.data.materials.append(memb)
mhole = flat("hole", (0.01, 0.025, 0.04), 0.05)
for hx, hy in {"igloo": ((1.45, 0.2), (-1.3, 0.6)), "lavvu": ((0.5, 1.5), (-0.5, -1.5)), "ship_tent": ((0.6, 1.8), (-0.6, -1.8))}[PIECE]:
    bpy.ops.mesh.primitive_cylinder_add(radius=0.27, depth=0.01, location=(hx, hy, 0.006)); bpy.context.object.data.materials.append(mhole)
bpy.ops.object.light_add(type='POINT', location=(0, FY, 0.5)); fl = bpy.context.object; fl.data.energy = 400; fl.data.color = (1.0, 0.55, 0.25); fl.data.shadow_soft_size = 0.3
# a 1.8 m figure for scale, by the door
mfig = flat("figure", (0.25, 0.32, 0.4), 0.7)
door = {"igloo": Vector((0.9, 4.0, 0)), "lavvu": Vector((0.9, 3.2, 0)), "ship_tent": Vector((1.0, 3.9, 0))}[PIECE]
bpy.ops.mesh.primitive_cylinder_add(radius=0.22, depth=1.45, location=door + Vector((0, 0, 0.725))); bpy.context.object.data.materials.append(mfig)
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.14, location=door + Vector((0, 0, 1.63))); bpy.context.object.data.materials.append(mfig)

w = bpy.data.worlds.new("w"); w.use_nodes = True; w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.42, 0.5, 0.62, 1)
w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.7; bpy.context.scene.world = w
bpy.ops.object.light_add(type='SUN', rotation=(math.radians(55), 0, math.radians(-40))); s = bpy.context.object; s.data.energy = 3.0; s.data.color = (1.0, 0.95, 0.88)
sc = bpy.context.scene
names = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]
sc.render.engine = 'BLENDER_EEVEE' if 'BLENDER_EEVEE' in names else 'BLENDER_EEVEE_NEXT'
vt = [v.identifier for v in sc.view_settings.bl_rna.properties['view_transform'].enum_items]
sc.view_settings.view_transform = 'AgX' if 'AgX' in vt else 'Filmic'
H = ob.dimensions.z
shots = [("out", (8.0, 10.5, 3.6), (0, 0.3, H * 0.4), 32), ("back", (-7.5, -9.5, 5.0), (0, 0, H * 0.45), 32),
         ("in", (0.7, 1.2, 1.55), (-0.3, -1.6, 1.2), 18), ("up", (0.4, 0.6, 1.0), (0, -0.1, 3.5), 16)]
if PIECE == "ship_tent":   # close on the front gable's top: where the dragon heads meet the boards
    shots += [("heads", (1.6, 5.4, 4.1), (0, 3.22, 3.55), 55),
              ("collar", (0.95, 4.35, 3.3), (0.28, 3.22, 3.62), 80), ("collar2", (-0.75, 4.1, 4.35), (-0.3, 3.22, 3.65), 80),
              ("vent", (1.7, -1.5, 4.25), (0.15, 0.25, 3.3), 32), ("seam", (2.7, 1.4, 2.1), (1.3, 0.43, 1.5), 45)]
if PIECE == "lavvu":       # close on a seam ring and the hides' joins down the back
    shots += [("seam", (0.9, -3.7, 1.7), (0.3, -2.2, 1.25), 45)]
if os.environ.get("VDW_SHOTS"): shots = [s for s in shots if s[0] in os.environ["VDW_SHOTS"].split(",")]
for name, loc, look, lens in shots:
    bpy.ops.object.camera_add(location=loc); c = bpy.context.object
    c.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); c.data.lens = lens; sc.camera = c
    sc.render.resolution_x, sc.render.resolution_y = 1400, 1000
    sc.render.filepath = OUT.replace(".png", f"_{name}.png"); bpy.ops.render.render(write_still=True)
print("PREVIEW", OUT)
