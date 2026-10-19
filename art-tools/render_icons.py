# Renders inventory-style icons from the finished models: transparent PNG, the item lying on the diagonal
# (head/tip up-right) with a slight 3D turn, textured with its Unity maps (albedo, metallic/smoothness, normal,
# emission). Reads Assets/DeepWaters/<key>/<key>_model.fbx and the maps next to it.
#   env: VDW_ASSETS (the Assets/DeepWaters folder), VDW_KEYS (comma list), VDW_OUT (folder), VDW_SIZE (px, 256)
import bpy, glob, math, os
import numpy as np
from mathutils import Matrix, Vector

ASSETS = os.environ["VDW_ASSETS"]; OUT = os.environ["VDW_OUT"]; SIZE = int(os.environ.get("VDW_SIZE", "256"))
GLOW = {**{f"bait_lure_{k}": 1.2 for k in ("antler", "root", "ooze", "wyrm", "ember", "chitin")}, "buff_totem_njord": 1.5, "buff_relic_pearl": 0.15, "rod_yggdrasil": 1.5, "rod_ashwood": 1.5, "rod_leviathan": 1.5, "rod_haldor": 1.0, "bobber": 1.5, "hook_golden": 1.0, "buff_totem_fisher": 1.5, "buff_chum_abyssal": 1.5, "buff_angler_major": 1.0, "buff_steady_major": 1.0, "buff_grip_major": 1.0}
# standing pieces (totems): shown upright, turned a little toward the viewer, not on the diagonal
UPRIGHT = {"buff_totem_fisher", "buff_totem_njord", "buff_relic_pearl", "buff_chum_basic", "buff_chum_blood", "buff_chum_abyssal"} | {f"buff_{f}_{t}" for f in ("angler", "steady", "grip") for t in ("minor", "medium", "major")}
# upright ones seen from a little above (degrees), to show what's inside
LOOK_DOWN = {"buff_relic_pearl": 20, "buff_chum_basic": 38, "buff_chum_blood": 38, "buff_chum_abyssal": 38} | {f"buff_{f}_{t}": 12 for f in ("angler", "steady", "grip") for t in ("minor", "medium", "major")}
# Deep North items (2026-10-11)
GLOW.update({"bait_lure_crown": 1.2, "bait_lure_ice_spoon": 0.6, "bait_lure_frostcore_jig": 1.0, "rod_frostwood": 1.5, "hook_fimbul": 1.0, "buff_angler_north": 1.0,
             "fish_rimejaw_cod": 0.6, "fish_glacier_grayling": 1.0, "fish_frost_sculpin": 0.8, "fish_fimbul_salmon": 1.5}, **{f"bossmat_{b}": 1.2 for b in ("eikthyr_elver", "elder_bass", "bonemass_catfish", "moder_scale", "yagluthgill", "queen_eel", "fimbul_salmon")})
GLOW["buff_rune_njord"] = 1.2
GLOW.update({"mat_ink": 1.0, "mat_cinder": 1.5, "mat_rime": 1.0, "mat_legend": 1.2})   # fish materials
GLOW.update({"food_ink_noodles": 0.3, "food_ember_fillet": 1.0, "food_rime_salmon": 0.3})   # cleaning table, dishes
UPRIGHT |= {"piece_cleaning_table", "piece_cleaning_ext1", "piece_cleaning_ext2", "piece_cleaning_ext3"}; LOOK_DOWN.update({"piece_cleaning_table": 32})
GLOW.update({"tacklebox_mistlands": 1.0}); UPRIGHT |= {"tacklebox_swamp", "tacklebox_mountain", "tacklebox_mistlands"}; LOOK_DOWN.update({"tacklebox_swamp": 25, "tacklebox_mountain": 25, "tacklebox_mistlands": 25})   # Hildir's tackle boxes
GLOW.update({"buff_spawning_musk": 1.0, "buff_lantern_float": 1.2, "float_lantern": 1.2}); UPRIGHT |= {"buff_spawning_musk", "buff_chum_seaweed", "buff_lantern_float", "float_lantern"} | {f"piece_feast_{f}" for f in ("forest", "mountain", "ocean", "plains", "mistlands", "ashlands", "deepnorth")}; LOOK_DOWN.update({f"piece_feast_{f}": 42 for f in ("forest", "mountain", "ocean", "plains", "mistlands", "ashlands", "deepnorth")}); LOOK_DOWN.update({"buff_chum_seaweed": 38, "buff_spawning_musk": 12})   # the Bog Witch brews
GLOW.update({"bait_frost_bait": 1.0, "bait_deep_bait": 1.0, "bait_rune_bait": 1.3})   # designed baits
UPRIGHT |= {"buff_rune_njord", "buff_chum_blubber", "buff_angler_north", "fisher_chest", "fisher_coat", "fisher_legs", "fisher_hat"}; LOOK_DOWN.update({"buff_rune_njord": 10, "buff_chum_blubber": 38, "buff_angler_north": 12})
# how each model lies in Blender after import: (long axis pointing at the head/tip, its "up")
FRAME = {"rod": ((0, 0, 1), (0, 1, 0)), "bobber": ((0, 0, 1), (0, -1, 0)), "pickable_worm": None,
         "fish_halibut": ((0, -1, 0), (1, 0, 0))}   # lies flat (eyed side +Z): shown from above
DEFAULT = ((0, -1, 0), (0, 0, 1))
# per-icon touches: LIGHT = (key/fill, rim, ambient) multipliers for dark items; WARM = warmer key light;
# ROLL = how far it turns toward the viewer (default 28 degrees); MARGIN = frame around it (default 1.12)
LIGHT = {"hook_tiny": (1.6, 3.0, 2.2), "hook_large": (1.3, 2.2, 1.6), "hook_heavy": (1.5, 2.6, 2.0), "hook_giant": (1.8, 3.4, 2.6)}
WARM = {"pickable_worm"}
FOOD_VIEW = 38                                 # degrees the dishes tip toward the camera
FOOD_TURN = {"prep_dried": 0}
ROLL = {"fish_queen_eel": 62, "fishing_boat": -40, "bait_lure_antler": -35, "bait_lure_wyrm": -35}
MARGIN = {"rod": 1.0, "fish_queen_eel": 1.0}
# mirrored across the bottom-left/top-right diagonal after rendering: same diagonal, reel and line on the other side
# (the user's choice for the rod)
DIAGONAL_MIRROR = {"rod"}
# Long bodies in COIL (eel rig: Head + Spine, Spine1.. head to tail) are rendered coiled up like a resting snake, seen
# from above at an angle; "<key>:coil" coils any other one, "<key>:straight" keeps one of these straight.
# (total spiral turn in degrees, head lift in degrees)
COIL = {"bait_worm": (560, 35), "fish_queen_eel": (600, 30)}
COIL_VIEW = float(os.environ.get("VDW_COIL_VIEW", "55"))
os.makedirs(OUT, exist_ok=True)

def maps(folder, prefix=None):
    out = {}
    for f in glob.glob(os.path.join(folder, "*_Unity_*")):
        if f.endswith(".meta"): continue
        n = os.path.splitext(os.path.basename(f))[0]
        if prefix and not n.startswith(prefix + "_Unity_"): continue
        for k in ("Albedo", "MetallicSmoothness", "Normal", "Emission"):
            if n.endswith("_" + k): out.setdefault(k, f)
    return out

def material(name, m, glow=0.0, fade=False):
    mat = bpy.data.materials.new(name); mat.use_nodes = True; mat.use_backface_culling = True   # as Unity's Standard shader
    nt = mat.node_tree; b = nt.nodes["Principled BSDF"]; L = nt.links.new
    def img(path, color=True):
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(path)
        if not color: t.image.colorspace_settings.name = "Non-Color"
        return t
    if "Albedo" in m:
        a = img(m["Albedo"]); L(a.outputs["Color"], b.inputs["Base Color"])
        if fade:
            L(a.outputs["Alpha"], b.inputs["Alpha"]); mat.blend_method = 'BLEND'
    if "MetallicSmoothness" in m:
        t = img(m["MetallicSmoothness"], False)
        sep = nt.nodes.new("ShaderNodeSeparateColor"); L(t.outputs["Color"], sep.inputs["Color"]); L(sep.outputs["Red"], b.inputs["Metallic"])
        inv = nt.nodes.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
        L(t.outputs["Alpha"], inv.inputs[1]); L(inv.outputs[0], b.inputs["Roughness"])
    if "Normal" in m:
        t = img(m["Normal"], False); nm = nt.nodes.new("ShaderNodeNormalMap")
        L(t.outputs["Color"], nm.inputs["Color"]); L(nm.outputs["Normal"], b.inputs["Normal"])
    if "Emission" in m and glow > 0:
        t = img(m["Emission"]); L(t.outputs["Color"], b.inputs["Emission Color"]); b.inputs["Emission Strength"].default_value = glow * 2.0
    return mat

PLANKS = r"C:\Users\tripp\Desktop\Valheim_DeepWaters\FishingRod\ExportedProject\Assets\3rd party\ADG_Textures\Plank Textures\Planks5\textures\Planks5c_worn.png"
def planks_material(dark):
    """Stand-in for Valheim's worn_shipplank (the rip's low-res copy), tiled per metre like the mod does (0.4, 0.7)."""
    mat = bpy.data.materials.new("planks_dark" if dark else "planks"); mat.use_nodes = True; mat.use_backface_culling = True
    nt = mat.node_tree; b = nt.nodes["Principled BSDF"]; L = nt.links.new
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(PLANKS)
    mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (0.4, 0.7, 1.0)
    tc = nt.nodes.new("ShaderNodeTexCoord"); L(tc.outputs["UV"], mp.inputs["Vector"]); L(mp.outputs["Vector"], t.inputs["Vector"])
    if dark:
        mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs["Factor"].default_value = 1.0
        mx.inputs[7].default_value = (0.55, 0.5, 0.45, 1.0); L(t.outputs["Color"], mx.inputs[6]); L(mx.outputs[2], b.inputs["Base Color"])
    else: L(t.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.85
    return mat

for entry in [k.strip() for k in os.environ["VDW_KEYS"].split(",") if k.strip()]:
    key, _, mode = entry.partition(":")
    coiled = mode == "coil" or (key in COIL and mode != "straight")
    folder = os.path.join(ASSETS, key)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=os.path.join(folder, key + "_model.fbx"))
    sc = bpy.context.scene
    for a in bpy.data.objects:
        if a.type == 'ARMATURE':
            if a.animation_data: a.animation_data.action = None
            for pb in a.pose.bones: pb.matrix_basis = Matrix()
            if coiled:
                from mathutils import Quaternion
                total, lift = COIL[key]
                def num(n): s = n[5:]; return int(s) if s else 0
                spine = sorted([pb for pb in a.pose.bones if pb.name.startswith("Spine")], key=lambda pb: num(pb.name))
                w = [1 + 2.2 * i / max(1, len(spine) - 1) for i in range(len(spine))]   # tighter toward the tail
                def turn(pb, axis, deg):
                    rest = (a.matrix_world.to_3x3() @ pb.bone.matrix_local.to_3x3()).inverted()
                    pb.rotation_mode = 'QUATERNION'
                    pb.rotation_quaternion = Quaternion((rest @ Vector(axis)).normalized(), math.radians(deg)) @ pb.rotation_quaternion
                for pb, wi in zip(spine, w): turn(pb, (0, 0, 1), total * wi / sum(w))
                if "Head" in a.pose.bones: turn(a.pose.bones["Head"], (1, 0, 0), -lift)
    for o in [o for o in bpy.data.objects if o.name.startswith("fitref")]: bpy.data.objects.remove(o)   # gear's body reference
    for o in [o for o in bpy.data.objects if o.name.startswith(("food_half", "food_low"))]: bpy.data.objects.remove(o)   # a feast shows full
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    glow = GLOW.get(key, 2.0 if key.startswith("fish_") else 0.0)
    for o in meshes:
        if o.name.startswith(("vdw_wood", "vdw_darkwood")):     # the mod dresses these in Valheim's tiling ship planks
            o.data.materials.clear(); o.data.materials.append(planks_material(o.name.startswith("vdw_darkwood"))); continue
        own = maps(folder, o.name.split(".")[0])
        m = own or maps(folder)
        o.data.materials.clear()
        o.data.materials.append(material(key + "_" + o.name, m, glow))
        if key == "bait_fly":     # second slot: see-through wings
            o.data.materials.append(material(key + "_wings", m, 0, fade=True))
            for poly in o.data.polygons: pass
    # the fly's wing faces were slot 1 in the export; FBX import keeps the slot indices, so nothing else to do

    # one parent to turn the whole model
    piv = bpy.data.objects.new("pivot", None); sc.collection.objects.link(piv)
    for o in bpy.data.objects:
        if o.parent is None and o is not piv: o.parent = piv
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    def world_pts():
        pts = []
        for o in meshes:
            ev = o.evaluated_get(dg); me = ev.to_mesh(); pts.append(np.array([ev.matrix_world @ v.co for v in me.vertices])); ev.to_mesh_clear()
        return np.concatenate(pts)
    c = world_pts(); centre = (c.min(0) + c.max(0)) / 2

    look = "rod" if key.startswith("rod_") else key   # every rod lies and shows like the wooden one
    fr = FRAME.get(look, DEFAULT)
    if key in UPRIGHT:
        R = Matrix.Rotation(math.radians(LOOK_DOWN.get(key, 0)), 4, 'X') @ Matrix.Rotation(math.radians(-28), 4, 'Z')
    elif key.startswith(("food_", "prep_")):   # dishes and prepared food: level, long side across, seen from the front and above
        R = Matrix.Rotation(math.radians(FOOD_VIEW), 4, 'X') @ Matrix.Rotation(math.radians(FOOD_TURN.get(key, 0)), 4, 'Z')
    elif coiled:       # lying in a coil: seen from above at an angle
        R = Matrix.Rotation(math.radians(COIL_VIEW), 4, 'X') @ Matrix.Rotation(math.radians(20), 4, 'Z')
    elif fr is None:   # the worm mound: seen from the front and above, not on a diagonal
        R = Matrix.Rotation(math.radians(-38), 4, 'X') @ Matrix.Rotation(math.radians(25), 4, 'Z')
    else:
        long, up = Vector(fr[0]), Vector(fr[1])
        side = long.cross(up)
        src = Matrix((long, up, side)).transposed()                         # columns: model frame
        d1 = Vector((0.707, 0, 0.707)); d2 = Vector((-0.707, 0, 0.707)); d3 = d1.cross(d2)
        dst = Matrix((d1, d2, d3)).transposed()                               # where they go on screen
        # roll toward the viewer: a bit of 3D. A positive roll tilts the top AWAY from the camera (the underside showed),
        # so lying items default to -28 and show their top; the rods and bobber keep the +28 the user chose for them.
        turn = Matrix.Rotation(math.radians(-ROLL.get(key, 28 if look in ("rod", "bobber") else -28)), 3, d1)
        R = (turn @ dst @ src.inverted()).to_4x4()
    piv.matrix_world = R @ Matrix.Translation(-Vector(centre))
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
    c = world_pts(); lo, hi = c.min(0), c.max(0); mid = (lo + hi) / 2

    cd = bpy.data.cameras.new("C"); cd.type = 'ORTHO'
    cd.ortho_scale = max(hi[0] - lo[0], hi[2] - lo[2]) * MARGIN.get(look, 1.12)
    span = float((hi - lo).max()); cd.clip_start = span * 0.01; cd.clip_end = span * 20
    cam = bpy.data.objects.new("C", cd); sc.collection.objects.link(cam); sc.camera = cam
    cam.location = Vector((mid[0], lo[1] - span * 3, mid[2])); cam.rotation_euler = (math.radians(90), 0, 0)

    # lighting: warm key from the upper left, cool fill, rim from behind
    kf, rf, af = LIGHT.get(key, (1.0, 1.0, 1.0))
    keycol = (1.0, 0.72, 0.45) if key in WARM else (1.0, 0.92, 0.8)
    keyE = 6.0 if key in WARM else 4.0
    for name, rot, e, col in (("key", (50, 0, -40), keyE * kf, keycol), ("fill", (70, 0, 60), 1.2 * kf, (0.7, 0.8, 1.0)), ("rim", (-50, 0, 180), 3.0 * rf, (1.0, 1.0, 1.0))):
        ld = bpy.data.lights.new(name, 'SUN'); ld.energy = e; ld.color = col
        lo_ = bpy.data.objects.new(name, ld); lo_.rotation_euler = [math.radians(x) for x in rot]; sc.collection.objects.link(lo_)
    sc.world = bpy.data.worlds.new("W"); sc.world.use_nodes = True
    sc.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.35, 0.33, 0.3, 1); sc.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6 * af

    sc.render.engine = 'BLENDER_EEVEE_NEXT'
    sc.render.film_transparent = True
    sc.render.resolution_x = sc.render.resolution_y = SIZE
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'
    sc.view_settings.view_transform = 'Standard'
    sc.render.filepath = os.path.join(OUT, key + ".png")
    bpy.ops.render.render(write_still=True)
    if look in DIAGONAL_MIRROR:
        img = bpy.data.images.load(sc.render.filepath); w, h = img.size
        px = np.array(img.pixels[:]).reshape(h, w, 4).transpose(1, 0, 2)   # rows are bottom-up: (x, y) -> (y, x)
        img.pixels[:] = px.ravel(); img.filepath_raw = sc.render.filepath; img.file_format = 'PNG'; img.save()
    print("ICON", key)
