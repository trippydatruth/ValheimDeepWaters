# Adds a back fade and a centre-back seam to a wrinkle edit blend's "VDW Wrinkles" node (make_wrinkle_edit.py).
# The game body's texture is mirrored left/right, so folds beside the spine meet their own mirror image at the seam
# down the back. The fade smooths the folds (and the piece's own fabric normal map) over the middle of the back; the
# seam is a soft sewn groove down the centre, so the left/right match reads as two panels sewn together.
# New node inputs (off by default; turned on per material with VDW_MATERIALS):
#   Back Fade Width (cm)  how far either side of the spine the folds fade (full at the spine, none past it)
#   Back Fade             0..1 how smooth the middle of the back gets (1 = flat)
#   Back Seam             depth of the centre-back seam (0 = none)
#   Seam Width (cm)       how wide the seam groove is
#   Seam Fade Top (cm)    the seam fades in over this far below the neck
#   Seam Fade Bottom (cm) and fades out over this far above the coat's lower edge at the waist
#   blender -b fisher_wrinkles_edit_vN.blend --python add_back_fade.py
#   env: VDW_OUT (new .blend, never overwrites), VDW_MATERIALS (default "coat"),
#        VDW_FADE_CM (12), VDW_FADE (1), VDW_SEAM (0.35), VDW_SEAM_CM (0.8), VDW_SEAM_TOP_CM (8), VDW_SEAM_BOTTOM_CM (8):
#        the values set on those materials; VDW_SEAM_END_Z where the seam ends at the bottom (the rig's metres;
#        default the coat's lowest point at the back - set it to the belt's top, 1.285, so it fades out above the belt)
import bpy, os

OUT = os.environ["VDW_OUT"]
if os.path.exists(OUT): raise SystemExit("exists, kept: " + OUT)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
MATS = os.environ.get("VDW_MATERIALS", "coat").split(",")
g = bpy.data.node_groups["VDW Wrinkles"]
if "Back Fade" in [s.name for s in g.interface.items_tree if getattr(s, "in_out", "") == 'INPUT']:
    raise SystemExit("this blend already has the back fade")
arm = bpy.data.objects["Armature"]
spine = arm.matrix_world @ arm.data.bones["Spine1"].head_local
def sock(name, default, lo, hi, desc):
    s = g.interface.new_socket(name, in_out='INPUT', socket_type="NodeSocketFloat"); s.default_value = default
    s.min_value = lo; s.max_value = hi; s.description = desc; return s
sock("Back Fade Width (cm)", 12.0, 0, 40, "how far either side of the spine the folds fade out (the back's mirror seam)")
sock("Back Fade", 0.0, 0, 1, "how smooth the middle of the back gets: 0 = off, 1 = flat at the spine")
sock("Back Seam", 0.0, 0, 2, "depth of a sewn seam down the centre of the back (0 = none)")
sock("Seam Width (cm)", 0.8, 0.1, 5, "how wide the seam groove is")
sock("Seam Fade Top (cm)", 8.0, 0, 40, "the seam fades in over this far below the neck")
sock("Seam Fade Bottom (cm)", 8.0, 0, 40, "the seam fades out over this far above where it ends at the waist (the belt)")
# where the seam starts and ends: the neck, and the coat's lowest point at the back
NECK_Z = (arm.matrix_world @ arm.data.bones["Neck"].head_local).z
cp = bpy.data.objects["coat_paint"]; cz = [(cp.matrix_world @ v.co) for v in cp.data.vertices]
HEM_Z = float(os.environ.get("VDW_SEAM_END_Z", "0") or 0) or min(p.z for p in cz if p.y > spine.y)
print(f"SEAM from the neck {NECK_Z:.3f} to the hem {HEM_Z:.3f}")
N, L = g.nodes, g.links
gi = next(n for n in N if n.type == 'GROUP_INPUT'); bp = next(n for n in N if n.type == 'BUMP')
at = next(n for n in N if n.type == 'ATTRIBUTE' and n.attribute_name == "vdw_rest")
def math(op, a, b, loc, clamp=False):
    m = N.new("ShaderNodeMath"); m.operation = op; m.location = loc; m.use_clamp = clamp
    for i, v in enumerate((a, b)):
        if v is None: continue
        if isinstance(v, (int, float)): m.inputs[i].default_value = v
        else: L.new(v, m.inputs[i])
    return m.outputs[0]
def smooth(v, lo, hi, loc, invert=False):
    mr = N.new("ShaderNodeMapRange"); mr.interpolation_type = 'SMOOTHSTEP'; mr.location = loc
    L.new(v, mr.inputs["Value"])
    for k, x in (("From Min", lo), ("From Max", hi)):
        if isinstance(x, (int, float)): mr.inputs[k].default_value = x
        else: L.new(x, mr.inputs[k])
    mr.inputs["To Min"].default_value = 1.0 if invert else 0.0; mr.inputs["To Max"].default_value = 0.0 if invert else 1.0
    return mr.outputs["Result"]
X0, Y0 = 600, -900
sep = N.new("ShaderNodeSeparateXYZ"); sep.location = (X0 - 600, Y0); L.new(at.outputs["Vector"], sep.inputs[0])
ax = math('ABSOLUTE', sep.outputs["X"], None, (X0 - 400, Y0))                              # metres from the body's middle
# the back: behind the spine's line (the rig's +y is the back), faded in over 4 cm
back = smooth(sep.outputs["Y"], spine.y - 0.01, spine.y + 0.03, (X0 - 400, Y0 - 200))
w = math('MULTIPLY', gi.outputs["Back Fade Width (cm)"], 0.01, (X0 - 400, Y0 - 400))
near = smooth(ax, math('MULTIPLY', w, 0.25, (X0 - 200, Y0 - 450)), w, (X0 - 200, Y0 - 300), invert=True)   # 1 at the spine
fade = math('MULTIPLY', math('MULTIPLY', back, near, (X0, Y0 - 250)), gi.outputs["Back Fade"], (X0 + 150, Y0 - 250), True)
keep = math('SUBTRACT', 1.0, fade, (X0 + 300, Y0 - 250))
# the folds' height, scaled down near the spine
hsrc = bp.inputs["Height"].links[0].from_socket
h = math('MULTIPLY', hsrc, keep, (X0 + 450, Y0 - 100))
# the seam: a soft groove at the middle with a slight raised edge either side (the sewn-over cloth)
sw = math('MULTIPLY', gi.outputs["Seam Width (cm)"], 0.01, (X0 - 400, Y0 - 650))
groove = smooth(ax, 0.0, sw, (X0 - 200, Y0 - 650), invert=True)
edge_d = math('ABSOLUTE', math('SUBTRACT', ax, math('MULTIPLY', sw, 1.6, (X0 - 400, Y0 - 800)), (X0 - 200, Y0 - 800)), None, (X0, Y0 - 800))
ridge = smooth(edge_d, 0.0, sw, (X0 + 150, Y0 - 800), invert=True)
seam = math('SUBTRACT', math('MULTIPLY', ridge, 0.35, (X0 + 300, Y0 - 800)), groove, (X0 + 300, Y0 - 650))
# soft ends: full between, fading to nothing at the neck and at the waist
top_cm = math('MULTIPLY', gi.outputs["Seam Fade Top (cm)"], 0.01, (X0 - 400, Y0 - 1000))
bot_cm = math('MULTIPLY', gi.outputs["Seam Fade Bottom (cm)"], 0.01, (X0 - 400, Y0 - 1150))
from_top = math('SUBTRACT', NECK_Z, sep.outputs["Z"], (X0 - 200, Y0 - 1000))              # metres below the neck
from_bot = math('SUBTRACT', sep.outputs["Z"], HEM_Z, (X0 - 200, Y0 - 1150))              # metres above the hem
ends = math('MULTIPLY', smooth(from_top, 0.0, top_cm, (X0, Y0 - 1000)), smooth(from_bot, 0.0, bot_cm, (X0, Y0 - 1150)), (X0 + 150, Y0 - 1050))
seam = math('MULTIPLY', math('MULTIPLY', seam, back, (X0 + 450, Y0 - 650)), gi.outputs["Back Seam"], (X0 + 600, Y0 - 650))
seam = math('MULTIPLY', seam, ends, (X0 + 600, Y0 - 800))
h = math('ADD', h, seam, (X0 + 650, Y0 - 100))
L.new(h, bp.inputs["Height"])
# the piece's own fabric normal map, eased toward the plain surface by the same fade
nsrc = bp.inputs["Normal"].links[0].from_socket if bp.inputs["Normal"].links else None
if nsrc is not None:
    geo = N.new("ShaderNodeNewGeometry"); geo.location = (X0 + 300, Y0 + 150)
    mx = N.new("ShaderNodeMix"); mx.data_type = 'VECTOR'; mx.location = (X0 + 500, Y0 + 150)
    L.new(fade, mx.inputs["Factor"]); L.new(nsrc, mx.inputs[4]); L.new(geo.outputs["Normal"], mx.inputs[5])
    nz = N.new("ShaderNodeVectorMath"); nz.operation = 'NORMALIZE'; nz.location = (X0 + 700, Y0 + 150)
    L.new(mx.outputs[1], nz.inputs[0]); L.new(nz.outputs[0], bp.inputs["Normal"])
vals = {"Back Fade Width (cm)": float(os.environ.get("VDW_FADE_CM", "12")), "Back Fade": float(os.environ.get("VDW_FADE", "1")),
        "Back Seam": float(os.environ.get("VDW_SEAM", "0.35")), "Seam Width (cm)": float(os.environ.get("VDW_SEAM_CM", "0.8")),
        "Seam Fade Top (cm)": float(os.environ.get("VDW_SEAM_TOP_CM", "8")), "Seam Fade Bottom (cm)": float(os.environ.get("VDW_SEAM_BOTTOM_CM", "8"))}
for m in MATS:
    for n in bpy.data.materials[m].node_tree.nodes:
        if n.type == 'GROUP' and n.node_tree == g:
            for k, v in vals.items(): n.inputs[k].default_value = v
            print("BACK FADE on", m, vals)
txt = bpy.data.texts.get("README_wrinkles")
if txt: txt.write("""
Back (coat): the body's texture is mirrored left/right, so folds by the spine meet their mirror image down the back.
  Back Fade Width (cm)  how far either side of the spine the folds fade out
  Back Fade             0 = off, 1 = smooth at the spine
  Back Seam             a sewn seam down the centre of the back (0 = none)
  Seam Width (cm)       the seam's width
  Seam Fade Top / Bottom (cm)   how far the seam fades in below the neck and out above the waist
""")
bpy.ops.wm.save_as_mainfile(filepath=OUT, copy=True, relative_remap=True); print("SAVED", OUT)
