# Sets up a blend for adjusting the painted gear's cloth wrinkles by eye (the folds baked into the overalls' and coat's
# normal maps). The pieces show their colour, their own normal map and the wrinkles live in Material Preview; every
# material has a "VDW Wrinkles" node whose inputs are the settings, plus an image to paint folds in by hand.
# bake_wrinkles.py then bakes exactly that onto the game body.
#   blender -b new_gear_rig_coatpaint_v6_paintsrc.blend --python make_wrinkle_edit.py
#   env: VDW_OUT (new .blend, never overwrites; the paint images go next to it),
#        VDW_MAPS "overalls=<albedo>|<normal>;boot=...;coat=..." the maps each material shows
import bpy, os
from mathutils import Vector

OUT = os.environ["VDW_OUT"]
if os.path.exists(OUT): raise SystemExit("exists, kept: " + OUT)
DIR = os.path.dirname(OUT); os.makedirs(DIR, exist_ok=True)
PIECES = ("overalls", "coat_paint")
# VDW_MAPS "material=albedo|normal;...": the colour and normal maps each material shows (the ones the paint bake used)
MAPS = {k: tuple(v.split("|")) for k, v in (kv.split("=", 1) for kv in os.environ.get("VDW_MAPS", "").split(";") if kv)}
arm = bpy.data.objects["Armature"]
arm.animation_data_clear()
for pb in arm.pose.bones: pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.rotation_euler = (0, 0, 0); pb.scale = (1, 1, 1)
bpy.context.view_layer.update()

# --- the wrinkle node group
g = bpy.data.node_groups.new("VDW Wrinkles", "ShaderNodeTree")
def sock(name, kind, default=None, lo=None, hi=None, desc=""):
    s = g.interface.new_socket(name, in_out='INPUT', socket_type=kind); s.description = desc
    if default is not None: s.default_value = default
    if lo is not None: s.min_value = lo
    if hi is not None: s.max_value = hi
    return s
sock("Normal", "NodeSocketVector", desc="the piece's own normal map (from its Normal Map node)").hide_value = True
sock("Strength", "NodeSocketFloat", 0.3, 0, 3, "how strong the wrinkles are (0 = none)")
sock("Fold Size (cm)", "NodeSocketFloat", 15.0, 0.5, 50, "how big one fold is: bigger = fewer, wider folds")
sock("Stretch", "NodeSocketFloat", 3.0, 1, 15, "how long the folds are compared with their width (1 = blotchy, high = long creases)")
sock("Creases", "NodeSocketFloat", 0.4, 0, 1, "0 = only soft rolling folds, 1 = only sharp crease lines")
sock("Crease Width", "NodeSocketFloat", 0.04, 0.005, 0.5, "how wide the crease lines are")
sock("Patchiness", "NodeSocketFloat", 0.7, 0, 1, "0 = creases spread evenly everywhere, 1 = creases only in patches")
sock("Waviness", "NodeSocketFloat", 0.3, 0, 3, "how much the folds bend and wander (0 = straight)")
sock("Detail", "NodeSocketFloat", 3.0, 0, 15, "small wrinkles on top of the soft folds")
sock("Detail Roughness", "NodeSocketFloat", 0.5, 0, 1, "how strong those small wrinkles are")
sock("Fold Depth (cm)", "NodeSocketFloat", 1.0, 0.05, 10, "how deep the folds look")
sock("Fold Direction", "NodeSocketVector", (0, 0, 0), desc="turns the folds (degrees X, Y, Z); (0,0,0) = folds running round the legs and body").subtype = 'EULER'
sock("Seed", "NodeSocketFloat", 0.0, -1000, 1000, "change for a different random pattern")
sock("Painted Folds", "NodeSocketFloat", 1.0, 0, 5, "strength of the folds painted by hand in the Painted Height image")
sock("Painted Height", "NodeSocketColor", (0.5, 0.5, 0.5, 1), desc="hand-painted folds: grey = flat, lighter = raised, darker = sunk")
sock("Units per metre", "NodeSocketFloat", 1.0, desc="leave at 1: set by bake_wrinkles.py for the game body's units")
g.interface.new_socket("Normal", in_out='OUTPUT', socket_type="NodeSocketVector")
N = g.nodes; L = g.links
gi = N.new("NodeGroupInput"); go = N.new("NodeGroupOutput"); gi.location = (-1600, 0); go.location = (900, 0)
def math(op, a, b, x, y):
    m = N.new("ShaderNodeMath"); m.operation = op; m.location = (x, y)
    for i, v in enumerate((a, b)):
        if isinstance(v, (int, float)): m.inputs[i].default_value = v
        else: L.new(v, m.inputs[i])
    return m.outputs[0]
def vmath(op, a, b, x, y):
    m = N.new("ShaderNodeVectorMath"); m.operation = op; m.location = (x, y)
    L.new(a, m.inputs[0])
    if op == 'SCALE': L.new(b, m.inputs["Scale"])
    else: L.new(b, m.inputs[1])
    return m.outputs["Vector"]
# Cloth wrinkles, not a wave: crease lines (ridged noise) and soft rolling folds (noise), both
# stretched along the fold direction so they run as long folds, and bent by noise so no two are alike.
at = N.new("ShaderNodeAttribute"); at.attribute_name = "vdw_rest"; at.location = (-1600, 400)   # rest-pose position, metres
freq = math('DIVIDE', 100.0, gi.outputs["Fold Size (cm)"], -1400, -300)                           # folds per metre
# bend: the position pushed about by a noise, up to Waviness folds
wn = N.new("ShaderNodeTexNoise"); wn.noise_dimensions = '4D'; wn.location = (-1350, 500)
L.new(at.outputs["Vector"], wn.inputs["Vector"]); L.new(gi.outputs["Seed"], wn.inputs["W"])
L.new(math('MULTIPLY', freq, 0.35, -1250, -300), wn.inputs["Scale"]); wn.inputs["Detail"].default_value = 1
sub = N.new("ShaderNodeVectorMath"); sub.operation = 'SUBTRACT'; sub.location = (-1150, 500)   # noise colour -0.5..0.5
L.new(wn.outputs["Color"], sub.inputs[0]); sub.inputs[1].default_value = (0.5, 0.5, 0.5); off = sub.outputs["Vector"]
amp = math('DIVIDE', gi.outputs["Waviness"], freq, -1150, -300)
bent = vmath('ADD', at.outputs["Vector"], vmath('SCALE', off, math('MULTIPLY', amp, 2.0, -1000, -300), -1000, 500), -850, 450)
# turn, then squeeze across the folds (Stretch) so they come out long
mp = N.new("ShaderNodeMapping"); mp.location = (-650, 450)
L.new(bent, mp.inputs["Vector"]); L.new(gi.outputs["Fold Direction"], mp.inputs["Rotation"])
cx = N.new("ShaderNodeCombineXYZ"); cx.location = (-850, 250); cx.inputs[0].default_value = 1; cx.inputs[1].default_value = 1
L.new(gi.outputs["Stretch"], cx.inputs[2]); L.new(cx.outputs[0], mp.inputs["Scale"])
uvw = vmath('SCALE', mp.outputs["Vector"], freq, -450, 450)
# crease lines: ridged noise (where a noise crosses its middle), open lines that run, fork and fade out like folds
# do (a Voronoi's cell edges closed up into a snakeskin of cells)
cn = N.new("ShaderNodeTexNoise"); cn.noise_dimensions = '4D'; cn.location = (-250, 600)
L.new(uvw, cn.inputs["Vector"]); L.new(gi.outputs["Seed"], cn.inputs["W"]); cn.inputs["Scale"].default_value = 1
cn.inputs["Detail"].default_value = 1; cn.inputs["Roughness"].default_value = 0.4
ridge = math('ABSOLUTE', math('SUBTRACT', cn.outputs["Fac"], 0.5, -50, 650), 0, 100, 650)        # 0 on the crease
mr = N.new("ShaderNodeMapRange"); mr.interpolation_type = 'SMOOTHSTEP'; mr.location = (250, 600)
L.new(ridge, mr.inputs["Value"]); L.new(gi.outputs["Crease Width"], mr.inputs["From Max"])
mr.inputs["From Min"].default_value = 0; mr.inputs["To Min"].default_value = 1; mr.inputs["To Max"].default_value = 0
# soft folds: a larger noise, with Detail for small wrinkles on top
sn = N.new("ShaderNodeTexNoise"); sn.noise_dimensions = '4D'; sn.location = (-250, 250)
L.new(uvw, sn.inputs["Vector"]); L.new(math('ADD', gi.outputs["Seed"], 17.0, -450, 200), sn.inputs["W"]); sn.inputs["Scale"].default_value = 0.6
L.new(gi.outputs["Detail"], sn.inputs["Detail"]); L.new(gi.outputs["Detail Roughness"], sn.inputs["Roughness"])
# patches: the creases gather in some places and fade out in others (a much larger noise), as on worn cloth
pn = N.new("ShaderNodeTexNoise"); pn.noise_dimensions = '4D'; pn.location = (-250, 900)
L.new(at.outputs["Vector"], pn.inputs["Vector"]); L.new(math('ADD', gi.outputs["Seed"], 41.0, -450, 900), pn.inputs["W"])
L.new(math('MULTIPLY', freq, 0.25, -450, 1000), pn.inputs["Scale"]); pn.inputs["Detail"].default_value = 0
pm = N.new("ShaderNodeMapRange"); pm.interpolation_type = 'SMOOTHSTEP'; pm.location = (-50, 900)
L.new(pn.outputs["Fac"], pm.inputs["Value"]); pm.inputs["From Min"].default_value = 0.42; pm.inputs["From Max"].default_value = 0.62
pmix = N.new("ShaderNodeMix"); pmix.data_type = 'FLOAT'; pmix.location = (150, 900); pmix.inputs["A"].default_value = 1.0
L.new(gi.outputs["Patchiness"], pmix.inputs["Factor"]); L.new(pm.outputs["Result"], pmix.inputs["B"])
crease = math('MULTIPLY', mr.outputs["Result"], pmix.outputs["Result"], 350, 700)
mx = N.new("ShaderNodeMix"); mx.data_type = 'FLOAT'; mx.location = (500, 450)
L.new(gi.outputs["Creases"], mx.inputs["Factor"]); L.new(sn.outputs["Fac"], mx.inputs["A"]); L.new(crease, mx.inputs["B"])
m1 = math('MULTIPLY', mx.outputs["Result"], gi.outputs["Strength"], 300, 300)
# + (painted - 0.5) * Painted Folds, one height
sep = N.new("ShaderNodeRGBToBW"); sep.location = (-250, -150); L.new(gi.outputs["Painted Height"], sep.inputs[0])
m3 = math('MULTIPLY', math('SUBTRACT', sep.outputs[0], 0.5, -50, -150), gi.outputs["Painted Folds"], 150, -150)
height = math('ADD', m1, m3, 450, 200)
# bump distance in the mesh's own units: Fold Depth cm * units per metre (the game body is far smaller than metres)
d1 = N.new("ShaderNodeMath"); d1.operation = 'MULTIPLY'; d1.location = (300, -350); L.new(gi.outputs["Fold Depth (cm)"], d1.inputs[0]); d1.inputs[1].default_value = 0.01
d2 = N.new("ShaderNodeMath"); d2.operation = 'MULTIPLY'; d2.location = (450, -350); L.new(d1.outputs[0], d2.inputs[0]); L.new(gi.outputs["Units per metre"], d2.inputs[1])
bp = N.new("ShaderNodeBump"); bp.location = (650, 0); bp.inputs["Strength"].default_value = 1.0
L.new(height, bp.inputs["Height"]); L.new(d2.outputs[0], bp.inputs["Distance"]); L.new(gi.outputs["Normal"], bp.inputs["Normal"])
L.new(bp.outputs["Normal"], go.inputs["Normal"])

# --- each piece's materials get the node between their normal map and the shader, and a paint image
done = set()
for name in PIECES:
    ob = bpy.data.objects[name]
    # the rest-pose position (metres, the rig's world: Z up) as an attribute, so the folds stay put when it's posed and
    # when the bake moves it onto the game body
    dg = bpy.context.evaluated_depsgraph_get(); ev = ob.evaluated_get(dg); em = ev.to_mesh()
    rest = [tuple(ev.matrix_world @ v.co) for v in em.vertices]; ev.to_mesh_clear()
    a = ob.data.attributes.get("vdw_rest") or ob.data.attributes.new("vdw_rest", 'FLOAT_VECTOR', 'POINT')
    for i, p in enumerate(rest): a.data[i].vector = p
    for m in ob.data.materials:
        if m is None or m.name in done: continue
        done.add(m.name); nt = m.node_tree
        bs = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
        if m.name in MAPS:                               # the maps the bake uses (the blend's own links had gone stale)
            alb, nrm = MAPS[m.name]
            for n in nt.nodes:
                if n.type != 'TEX_IMAGE': continue
                to = [l.to_node for l in n.outputs["Color"].links]
                if any(t == bs for t in to): n.image = bpy.data.images.load(alb, check_existing=True)
                elif any(t.type == 'NORMAL_MAP' for t in to):
                    n.image = bpy.data.images.load(nrm, check_existing=True); n.image.colorspace_settings.name = 'Non-Color'
        lk = bs.inputs["Normal"].links
        src = lk[0].from_socket if lk else None
        gn = nt.nodes.new("ShaderNodeGroup"); gn.node_tree = g; gn.name = gn.label = "VDW Wrinkles"
        gn.location = bs.location + Vector((-250, -350)); gn.width = 220
        if src: nt.links.new(src, gn.inputs["Normal"])
        nt.links.new(gn.outputs["Normal"], bs.inputs["Normal"])
        path = os.path.join(DIR, f"wrinkle_paint_{m.name}.png")
        im = bpy.data.images.new(f"wrinkle_paint_{m.name}", 1024, 1024); im.generated_color = (0.5, 0.5, 0.5, 1)
        im.filepath_raw = path; im.file_format = 'PNG'; im.save(); im.filepath = path; im.source = 'FILE'
        tx = nt.nodes.new("ShaderNodeTexImage"); tx.image = im; tx.label = "paint folds here (Texture Paint)"
        tx.location = gn.location + Vector((-320, -150))
        nt.links.new(tx.outputs["Color"], gn.inputs["Painted Height"])
        for n in nt.nodes: n.select = False
        tx.select = True; nt.nodes.active = tx          # Texture Paint paints the active image node
        print("WRINKLES on material", m.name)

# --- what's shown: the two painted pieces, in Material Preview
for o in bpy.data.objects:
    if o.type == 'MESH': o.hide_set(o.name not in PIECES)
for scr in bpy.data.screens:
    for area in scr.areas:
        for sp in area.spaces:
            if sp.type == 'VIEW_3D': sp.shading.type = 'MATERIAL'
txt = bpy.data.texts.new("README_wrinkles")
txt.write("""Wrinkles on the painted overalls and coat
==========================================
Look in Material Preview (Z > Material Preview). The overalls and coat_paint objects show their colour, their own
normal map and the wrinkles as they'll be baked onto the body.

Adjust: Shading tab, pick a piece, select the "VDW Wrinkles" node. Each material has its own (overalls, boot, coat),
so the overalls, boots and coat can differ:
  Strength          how strong the wrinkles are (0 = none)
  Fold Size (cm)    how big one fold is
  Stretch           how long the folds are for their width (1 = blotchy, high = long creases)
  Creases           0 = only soft rolling folds, 1 = only sharp crease lines
  Crease Width      how wide the crease lines are
  Patchiness        0 = creases spread evenly everywhere, 1 = creases only in patches
  Waviness          how much the folds bend and wander (0 = straight)
  Detail / Detail Roughness   small wrinkles on top of the soft folds
  Fold Depth (cm)   how deep they look
  Fold Direction    turns the folds (degrees); 0,0,0 = folds running round the legs and body
  Seed              a different random pattern
  Painted Folds     strength of hand-painted folds

Paint folds by hand: Texture Paint mode on a piece paints its wrinkle_paint_<material> image (grey = flat, lighter =
raised, darker = sunk). Save the images (Image > Save All Images) as well as the blend.

Leave "Units per metre" at 1. Save the blend, then ask Claude to bake it (art-tools/bake_wrinkles.py).
""")
bpy.ops.wm.save_as_mainfile(filepath=OUT, copy=True)
print("SAVED", OUT)
