# Sets up one blend for editing the tackle box tiers' textures by eye: each tier's box with its live materials (the
# Sanctus wood / worn metal / leather worn by Grungit, as bake_tacklebox.py built them) in the front row, and behind
# each, the same box with the textures in the game now, to compare. Bake an edited tier back with
#   blender -b tacklebox_edit_vN.blend --python bake_tacklebox.py   (VDW_EDITED=1 VDW_TIER=t2 VDW_OUT=<new folder>)
# which adds the straps and rim (t2-t4) and the rune line (t4) on top, as before.
#   blender -b --factory-startup --python make_tacklebox_edit.py
#   env: VDW_SRC (folder of tacklebox_<tier>_baked.blend, e.g. Mesh\tacklebox\bake_v3), VDW_GAME (folder of the game's
#        tacklebox_<tier>\tacklebox_<tier>_Unity_*.png), VDW_OUT (new .blend, never overwrites), VDW_TIERS (t1,t2,t3,t4)
import bpy, os

SRC, GAME, OUT = os.environ["VDW_SRC"], os.environ["VDW_GAME"], os.environ["VDW_OUT"]
TIERS = os.environ.get("VDW_TIERS", "t1,t2,t3,t4").split(",")
# VDW_TINTS "t1=r,g,b;...": the wood colour match per tier (multiply), measured with tacklebox_tint.py
TINTS = {k: tuple(float(x) for x in v.split(",")) for k, v in (kv.split("=") for kv in os.environ.get("VDW_TINTS", "").split(";") if kv)}
NAMES = {"t1": "Wooden", "t2": "Iron-Bound", "t3": "Silver", "t4": "Dvergr"}
if os.path.exists(OUT): raise SystemExit("exists, kept: " + OUT)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
sc = bpy.context.scene
STEP = 0.85

def label(text, loc):
    cu = bpy.data.curves.new("label", 'FONT'); cu.body = text; cu.size = 0.07; cu.align_x = 'CENTER'
    ob = bpy.data.objects.new("label_" + text, cu); sc.collection.objects.link(ob); ob.location = loc; ob.rotation_euler = (1.5708, 0, 0)
    ob.hide_render = True

for i, t in enumerate(TIERS):
    path = os.path.join(SRC, f"tacklebox_{t}_baked.blend")
    with bpy.data.libraries.load(path) as (src, dst): dst.objects = ["tacklebox"]
    box = dst.objects[0]; sc.collection.objects.link(box)
    rig = box.parent
    if rig is not None:
        mw = box.matrix_world.copy(); box.parent = None; box.matrix_world = mw
    for md in list(box.modifiers):
        if md.type == 'ARMATURE': box.modifiers.remove(md)
    if rig is not None and rig.name in bpy.data.objects and not rig.users_collection: bpy.data.objects.remove(rig)
    box.name = f"tacklebox_{t}"; box.data.name = f"tacklebox_{t}"
    for m in box.data.materials:
        m.name = f"{m.name}_{t}"
        N, L = m.node_tree.nodes, m.node_tree.links
        out = next(n for n in N if n.type == 'OUTPUT_MATERIAL' and n.is_active_output)
        L.new(N["vdw_bsdf"].outputs["BSDF"], out.inputs["Surface"])          # shown as the shader, not a bake pass
        # the wood's colour match: the last bake darkened the wood afterwards to the tier's colour (VDW_MATCH_DIR); here
        # it's a node in the material, so what's shown is what bakes
        if m.name.startswith("tb_wood") and t in TINTS:
            bs = N["vdw_bsdf"]; src_sock = bs.inputs["Base Color"].links[0].from_socket
            mx = N.new("ShaderNodeMix"); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.name = "vdw_tint"
            mx.label = "Wood colour match (as in game)"; mx.inputs["Factor"].default_value = 1.0
            mx.location = bs.location + __import__("mathutils").Vector((-220, 120))
            L.new(src_sock, mx.inputs[6]); mx.inputs[7].default_value = (*TINTS[t], 1.0)
            L.new(mx.outputs[2], bs.inputs["Base Color"])
            print("TINT", m.name, TINTS[t])
        for n in N: n.select = False
    box.location = (i * STEP, 0, 0)
    # behind it: the same box with the game's textures now
    ref = bpy.data.objects.new(f"ingame_{t}", box.data.copy()); sc.collection.objects.link(ref)
    ref.location = (i * STEP, 0.75, 0)
    m = bpy.data.materials.new(f"ingame_{t}"); m.use_nodes = True; N, L = m.node_tree.nodes, m.node_tree.links
    bs = next(n for n in N if n.type == 'BSDF_PRINCIPLED')
    d = os.path.join(GAME, f"tacklebox_{t}")
    def tex(name, nc):
        p = os.path.join(d, f"tacklebox_{t}_Unity_{name}.png")
        if not os.path.exists(p): return None
        n = N.new("ShaderNodeTexImage"); n.image = bpy.data.images.load(p, check_existing=True)
        if nc: n.image.colorspace_settings.name = 'Non-Color'
        return n
    a = tex("Albedo", False); ms = tex("MetallicSmoothness", True); nm = tex("Normal", True); em = tex("Emission", False)
    L.new(a.outputs["Color"], bs.inputs["Base Color"])
    sep = N.new("ShaderNodeSeparateColor"); L.new(ms.outputs["Color"], sep.inputs[0]); L.new(sep.outputs[0], bs.inputs["Metallic"])
    inv = N.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
    L.new(ms.outputs["Alpha"], inv.inputs[1]); L.new(inv.outputs[0], bs.inputs["Roughness"])
    nmap = N.new("ShaderNodeNormalMap"); L.new(nm.outputs["Color"], nmap.inputs["Color"]); L.new(nmap.outputs["Normal"], bs.inputs["Normal"])
    if em:
        L.new(em.outputs["Color"], bs.inputs["Emission Color"]); bs.inputs["Emission Strength"].default_value = 1.5
    ref.data.materials.clear(); ref.data.materials.append(m)
    for p in ref.data.polygons: p.material_index = 0
    label(f"{t} {NAMES.get(t, '')}: edit", (i * STEP, -0.05, 0.38))
    label(f"{t}: in game now", (i * STEP, 0.7, 0.38))
    print("TIER", t, "materials", [x.name for x in box.data.materials])

for scr in bpy.data.screens:
    for area in scr.areas:
        for sp in area.spaces:
            if sp.type == 'VIEW_3D': sp.shading.type = 'MATERIAL'
txt = bpy.data.texts.new("README_tacklebox")
txt.write("""Tackle box textures
===================
Material Preview (Z > Material Preview). Front row: each tier's box with its live materials - edit these. Back row:
the same box with the textures in the game now, to compare.

Each box has three materials (Shading tab, pick the box, then the material slot):
  tb_wood_<tier>    the Sanctus planks: their group node holds the colours (Color1/Color2), plank size, damage, scale
  tb_metal_<tier>   the latch, and on t2-t4 the straps and rim (added at bake time) and t3/t4's handle
  tb_handle_<tier>  the leather handle (t1, t2)
In each: the Sanctus node -> "Grungit" (edge wear, scratches, cracks, grunge: Global Control, Edge Wear Spread, Scratch
Amount, Cracks Amount, Base Color 2 = the worn edge colour) -> "Grungit Dirt" (Overall Amount, Dirt Base Color) -> the
shader. Change anything you like, add nodes, or paint; keep the nodes named vdw_bsdf, vdw_emit, vdw_target, vdw_mask.

Not shown live: the metal straps round each end and the rim along the lid seam (t2-t4) and the blue rune line (t4) are
added when the box is baked, from the metal material and the wood. Save, then ask Claude to bake (bake_tacklebox.py with
VDW_EDITED=1) - it bakes each tier you changed into new textures and shows you before installing.
""")
bpy.ops.wm.save_as_mainfile(filepath=OUT, relative_remap=True)
print("SAVED", OUT)
