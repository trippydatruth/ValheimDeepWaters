# Textures a tier of the wooden ice chest (build_wood_cooler.py) from the user's add-ons, like bake_tacklebox.py:
# Sanctus materials (generic wood for the boards and grips - its grain following each board's long side through the
# model's "Grain" UVs - worn metal for iron or silver, rough gold for brass) worn by Grungit (edge wear, scratches,
# cracks) and Grungit Dirt (dirt or frost in the cavities), baked to Unity maps on the "UVMap" atlas.
#   c1 Wooden Cooler: oak, dark iron, brass        c2 Iron-Banded Cooler: dark tarred wood, worn steel, brass
#   c3 Frost Cooler: pale frosted wood, silver fittings, frost in the cracks
# VDW_KIND=tacklebox: the wooden tackle box (build_wood_tacklebox.py; wood, tray and iron), tiers t1 Wooden (oak,
#   dark iron), t2 Iron-Bound (dark stained wood, steel), t3 Silver (pale birch, silver), t4 Black-Metal (the Plains:
#   oak, black metal); each painted (green, oxblood, cream, ochre) and worn back to the wood (VDW_PAINT=0 for bare
#   wood); and Hildir's late-biome boxes (mistlands, swamp = the Ashlands, mountain = the Deep North)
# Writes <out>/cooler_<tier>/cooler_<tier>_Unity_{Albedo,MetallicSmoothness,Normal}.png, the mask, and
# <out>/cooler_<tier>_baked.blend (the live materials, for editing and rebaking). New files only.
#   blender -b cooler_wood_v1.blend --factory-startup --python bake_wood_cooler.py
#   env: VDW_OUT, VDW_TIER (c1), VDW_SIZE (2048), VDW_SAMPLES (32)
import bpy, os
import numpy as np

OUT = os.environ["VDW_OUT"]; TIER = os.environ.get("VDW_TIER", "c1")
KIND = os.environ.get("VDW_KIND", "cooler"); PREFIX = {"tacklebox": "tacklebox", "gear": "tackle", "lure": "bait", "cap": "fisher"}.get(KIND, "cooler")
SIZE = int(os.environ.get("VDW_SIZE", "2048")); SAMPLES = int(os.environ.get("VDW_SAMPLES", "32"))
SANCTUS = os.path.join(os.environ["APPDATA"], r"Blender Foundation\Blender\5.2\extensions\user_default\sanctus_library_starter\lib\materials")
GRUNGIT = os.path.join(os.environ["APPDATA"], r"Blender Foundation\Blender\5.2\scripts\addons\Grungit\grungit_data\Materials.blend")
TEXDIR = os.path.join(OUT, f"{PREFIX}_{TIER}")
if os.path.exists(os.path.join(TEXDIR, f"{PREFIX}_{TIER}_Unity_Albedo.png")): raise SystemExit("exists, kept: " + TEXDIR)
os.makedirs(TEXDIR, exist_ok=True)

WOOD, METAL, GOLD = r"Wood\generic_wood.blend", r"Metals Worn\basic_worn_metal.blend", r"Metals Worn\gold_rough.blend"
COPPER = r"Metals Worn\hammered_copper.blend"
# per material slot: (Sanctus file, material, its inputs, the worn colour Grungit wears edges to, metallic of the wear,
#   wear amount, dirt colour, dirt amount)
TIERS = {
    "c1": dict(
        wood=(WOOD, "generic_wood_01", {"Light Color": (0.52, 0.34, 0.18, 1), "Dark Color": (0.30, 0.18, 0.09, 1), "Knots": 0.4, "Damage": 0.25, "Roughness": 0.7, "Clearcoat": 0.0, "Bump": 0.4}, (0.62, 0.45, 0.28, 1), 0.0, 0.35, (0.18, 0.12, 0.07, 1), 0.3),
        grip=(WOOD, "generic_wood_01", {"Light Color": (0.66, 0.48, 0.30, 1), "Dark Color": (0.45, 0.30, 0.17, 1), "Knots": 0.0, "Damage": 0.1, "Roughness": 0.6, "Clearcoat": 0.0}, (0.75, 0.6, 0.42, 1), 0.0, 0.3, (0.18, 0.12, 0.07, 1), 0.2),
        iron=(METAL, "basic_worn_metal_01", {"Color": (0.13, 0.13, 0.14, 1), "Roughness": 0.55}, (0.30, 0.30, 0.32, 1), 1.0, 0.36, (0.20, 0.13, 0.08, 1), 0.35),
        brass=(GOLD, "gold_rough", {"Color": (0.72, 0.52, 0.24, 1), "Roughness": 0.35}, (0.9, 0.75, 0.45, 1), 1.0, 0.3, (0.20, 0.17, 0.08, 1), 0.3)),
    "c2": dict(   # the swamp: tarred wood, nearly black, and brighter iron
        wood=(WOOD, "generic_wood_01", {"Light Color": (0.13, 0.08, 0.045, 1), "Dark Color": (0.045, 0.027, 0.015, 1), "Knots": 0.5, "Damage": 0.35, "Roughness": 0.45, "Clearcoat": 0.0, "Bump": 0.45}, (0.17, 0.11, 0.065, 1), 0.0, 0.4, (0.08, 0.09, 0.05, 1), 0.4),
        grip=(WOOD, "generic_wood_01", {"Light Color": (0.30, 0.20, 0.12, 1), "Dark Color": (0.15, 0.09, 0.05, 1), "Knots": 0.0, "Damage": 0.15, "Roughness": 0.55, "Clearcoat": 0.0}, (0.42, 0.30, 0.19, 1), 0.0, 0.35, (0.08, 0.09, 0.05, 1), 0.3),
        iron=(METAL, "basic_worn_metal_01", {"Color": (0.27, 0.28, 0.30, 1), "Roughness": 0.45}, (0.62, 0.62, 0.64, 1), 1.0, 0.55, (0.14, 0.12, 0.06, 1), 0.4),
        brass=(GOLD, "gold_rough", {"Color": (0.62, 0.45, 0.22, 1), "Roughness": 0.4}, (0.85, 0.7, 0.42, 1), 1.0, 0.35, (0.14, 0.12, 0.06, 1), 0.4)),
    "c3": dict(   # the mountains: grey weathered wood, bright silver, frost in the cracks
        wood=(WOOD, "generic_wood_01", {"Light Color": (0.36, 0.38, 0.41, 1), "Dark Color": (0.19, 0.21, 0.24, 1), "Knots": 0.3, "Damage": 0.2, "Roughness": 0.6, "Clearcoat": 0.0, "Bump": 0.35}, (0.52, 0.56, 0.60, 1), 0.0, 0.35, (0.85, 0.92, 1.0, 1), 0.4),
        grip=(WOOD, "generic_wood_01", {"Light Color": (0.45, 0.47, 0.50, 1), "Dark Color": (0.27, 0.29, 0.32, 1), "Knots": 0.0, "Damage": 0.1, "Roughness": 0.55, "Clearcoat": 0.0}, (0.6, 0.63, 0.66, 1), 0.0, 0.3, (0.85, 0.92, 1.0, 1), 0.3),
        iron=(METAL, "basic_worn_metal_01", {"Color": (0.74, 0.77, 0.80, 1), "Roughness": 0.3}, (0.92, 0.93, 0.95, 1), 1.0, 0.4, (0.93, 0.97, 1.0, 1), 0.35),
        brass=(METAL, "basic_worn_metal_01", {"Color": (0.62, 0.74, 0.86, 1), "Roughness": 0.3}, (0.88, 0.93, 1.0, 1), 1.0, 0.35, (0.93, 0.97, 1.0, 1), 0.35)),
}
TB_TIERS = {
    "t1": dict(
        wood=(WOOD, "generic_wood_01", {"Light Color": (0.52, 0.34, 0.18, 1), "Dark Color": (0.30, 0.18, 0.09, 1), "Knots": 0.4, "Damage": 0.25, "Roughness": 0.7, "Clearcoat": 0.0, "Bump": 0.4}, (0.62, 0.45, 0.28, 1), 0.0, 0.35, (0.18, 0.12, 0.07, 1), 0.3),
        tray=(WOOD, "generic_wood_01", {"Light Color": (0.66, 0.48, 0.30, 1), "Dark Color": (0.45, 0.30, 0.17, 1), "Knots": 0.0, "Damage": 0.1, "Roughness": 0.6, "Clearcoat": 0.0}, (0.75, 0.6, 0.42, 1), 0.0, 0.25, (0.18, 0.12, 0.07, 1), 0.2),
        iron=(METAL, "basic_worn_metal_01", {"Color": (0.13, 0.13, 0.14, 1), "Roughness": 0.55}, (0.30, 0.30, 0.32, 1), 1.0, 0.36, (0.20, 0.13, 0.08, 1), 0.35)),
    "t2": dict(   # Iron-Bound: dark stained wood, bright steel
        wood=(WOOD, "generic_wood_01", {"Light Color": (0.24, 0.15, 0.08, 1), "Dark Color": (0.11, 0.065, 0.035, 1), "Knots": 0.5, "Damage": 0.3, "Roughness": 0.55, "Clearcoat": 0.0, "Bump": 0.45}, (0.32, 0.21, 0.12, 1), 0.0, 0.35, (0.10, 0.09, 0.05, 1), 0.35),
        tray=(WOOD, "generic_wood_01", {"Light Color": (0.42, 0.28, 0.16, 1), "Dark Color": (0.24, 0.15, 0.08, 1), "Knots": 0.0, "Damage": 0.1, "Roughness": 0.55, "Clearcoat": 0.0}, (0.5, 0.36, 0.22, 1), 0.0, 0.25, (0.10, 0.09, 0.05, 1), 0.25),
        iron=(METAL, "basic_worn_metal_01", {"Color": (0.27, 0.28, 0.30, 1), "Roughness": 0.45}, (0.62, 0.62, 0.64, 1), 1.0, 0.5, (0.14, 0.12, 0.06, 1), 0.35)),
    "t3": dict(   # Silver: pale birch, silver
        wood=(WOOD, "generic_wood_01", {"Light Color": (0.66, 0.58, 0.44, 1), "Dark Color": (0.48, 0.40, 0.28, 1), "Knots": 0.3, "Damage": 0.2, "Roughness": 0.6, "Clearcoat": 0.0, "Bump": 0.35}, (0.76, 0.69, 0.56, 1), 0.0, 0.3, (0.22, 0.17, 0.10, 1), 0.3),
        tray=(WOOD, "generic_wood_01", {"Light Color": (0.74, 0.66, 0.52, 1), "Dark Color": (0.58, 0.50, 0.37, 1), "Knots": 0.0, "Damage": 0.1, "Roughness": 0.55, "Clearcoat": 0.0}, (0.82, 0.76, 0.64, 1), 0.0, 0.25, (0.22, 0.17, 0.10, 1), 0.2),
        iron=(METAL, "basic_worn_metal_01", {"Color": (0.74, 0.77, 0.80, 1), "Roughness": 0.3}, (0.92, 0.93, 0.95, 1), 1.0, 0.35, (0.20, 0.17, 0.12, 1), 0.3)),
    "t4": dict(   # Black-Metal (the Plains): sun-bleached ochre paint over plains oak, black metal
        wood=(WOOD, "generic_wood_01", {"Light Color": (0.48, 0.34, 0.18, 1), "Dark Color": (0.28, 0.18, 0.09, 1), "Knots": 0.35, "Damage": 0.25, "Roughness": 0.65, "Clearcoat": 0.0, "Bump": 0.4}, (0.58, 0.44, 0.27, 1), 0.0, 0.35, (0.24, 0.18, 0.10, 1), 0.35),
        tray=(WOOD, "generic_wood_01", {"Light Color": (0.6, 0.45, 0.27, 1), "Dark Color": (0.40, 0.28, 0.15, 1), "Knots": 0.0, "Damage": 0.1, "Roughness": 0.6, "Clearcoat": 0.0}, (0.7, 0.56, 0.38, 1), 0.0, 0.25, (0.24, 0.18, 0.10, 1), 0.25),
        iron=(METAL, "basic_worn_metal_01", {"Color": (0.06, 0.06, 0.07, 1), "Roughness": 0.4}, (0.28, 0.28, 0.30, 1), 1.0, 0.35, (0.24, 0.18, 0.10, 1), 0.3)),
}
# Hildir's lost tackle boxes (build_wood_tacklebox.py VDW_HILDIR): the same box, painted and worn, with her red mark and
# what each picked up where it was lost - moss (swamp), ice (mountain), dvergr bands and glowing eitr rivets (mistlands).
# Their extra parts are Sanctus worn metal turned matte (Metallic 0) in the part's colour, worn by Grungit like the rest.
def matte(col, rough, worn, wear, dirt_col, dirt):
    return (METAL, "basic_worn_metal_01", {"Color": (*col, 1), "Metallic": 0.0, "Roughness": rough}, (*worn, 1), 0.0, wear, (*dirt_col, 1), dirt)
_MARK = lambda dirt_col, dirt: matte((0.45, 0.04, 0.03), 0.6, (0.22, 0.08, 0.05), 0.12, dirt_col, dirt * 0.5)
TB_TIERS.update({
    "swamp": dict(   # Hildir's Charred Tackle Box (the Ashlands; "swamp" where it was first lost): scorched red-black paint,
                     # black iron, soot in every crack, embers glowing in the lid and the seams
        wood=(WOOD, "generic_wood_01", {"Light Color": (0.045, 0.03, 0.022, 1), "Dark Color": (0.012, 0.009, 0.007, 1), "Knots": 0.4, "Damage": 0.45, "Roughness": 0.8, "Clearcoat": 0.0, "Bump": 0.5}, (0.06, 0.058, 0.055, 1), 0.0, 0.3, (0.01, 0.01, 0.01, 1), 0.45),
        char=dict(glow=(1.0, 0.36, 0.05), block=(0.075, 0.012), crack=0.06, hot=(0.50, 0.64), ash_col=(0.045, 0.044, 0.042)),   # charred: blocks along the grain, glowing cracks (char_wood)
        tray=(WOOD, "generic_wood_01", {"Light Color": (0.32, 0.22, 0.14, 1), "Dark Color": (0.16, 0.10, 0.06, 1), "Knots": 0.0, "Damage": 0.2, "Roughness": 0.65, "Clearcoat": 0.0}, (0.4, 0.28, 0.18, 1), 0.0, 0.3, (0.03, 0.03, 0.03, 1), 0.5),
        iron=(METAL, "basic_worn_metal_01", {"Color": (0.08, 0.07, 0.07, 1), "Roughness": 0.6}, (0.30, 0.22, 0.18, 1), 1.0, 0.4, (0.03, 0.03, 0.03, 1), 0.5),
        mark=_MARK((0.03, 0.03, 0.03), 0.4),
        ember=matte((0.9, 0.22, 0.02), 0.5, (1.0, 0.45, 0.1), 0.05, (0.15, 0.03, 0.0), 0.05),
        glow_slots={"ember": (1.0, 0.38, 0.06)}),
    "mountain": dict(   # Hildir's Rime-Crusted Tackle Box (the Deep North): pale blue-grey paint, silvery iron, ice and snow, rime in every crack
        wood=(WOOD, "generic_wood_01", {"Light Color": (0.42, 0.36, 0.28, 1), "Dark Color": (0.24, 0.19, 0.13, 1), "Knots": 0.3, "Damage": 0.25, "Roughness": 0.6, "Clearcoat": 0.0, "Bump": 0.4}, (0.55, 0.5, 0.42, 1), 0.0, 0.45, (0.90, 0.95, 1.0, 1), 0.6),
        tray=(WOOD, "generic_wood_01", {"Light Color": (0.5, 0.44, 0.34, 1), "Dark Color": (0.32, 0.26, 0.19, 1), "Knots": 0.0, "Damage": 0.1, "Roughness": 0.55, "Clearcoat": 0.0}, (0.6, 0.55, 0.46, 1), 0.0, 0.25, (0.90, 0.95, 1.0, 1), 0.5),
        iron=(METAL, "basic_worn_metal_01", {"Color": (0.52, 0.55, 0.60, 1), "Roughness": 0.4}, (0.8, 0.82, 0.86, 1), 1.0, 0.35, (0.90, 0.95, 1.0, 1), 0.5),
        mark=_MARK((0.90, 0.95, 1.0), 0.4),
        ice=matte((0.55, 0.75, 0.92), 0.08, (0.80, 0.90, 1.0), 0.04, (0.85, 0.93, 1.0), 0.04),
        snow=matte((0.88, 0.92, 0.97), 0.85, (0.95, 0.97, 1.0), 0.05, (0.80, 0.86, 0.95), 0.15)),
    "mistlands": dict(   # Hildir's Dvergr-Mended Tackle Box: mist-purple paint, dark dvergr iron, glowing eitr rivets
        wood=(WOOD, "generic_wood_01", {"Light Color": (0.30, 0.22, 0.14, 1), "Dark Color": (0.15, 0.10, 0.06, 1), "Knots": 0.3, "Damage": 0.25, "Roughness": 0.6, "Clearcoat": 0.0, "Bump": 0.4}, (0.38, 0.29, 0.19, 1), 0.0, 0.4, (0.08, 0.07, 0.10, 1), 0.35),
        tray=(WOOD, "generic_wood_01", {"Light Color": (0.40, 0.30, 0.20, 1), "Dark Color": (0.24, 0.17, 0.10, 1), "Knots": 0.0, "Damage": 0.1, "Roughness": 0.55, "Clearcoat": 0.0}, (0.5, 0.4, 0.28, 1), 0.0, 0.25, (0.08, 0.07, 0.10, 1), 0.25),
        iron=(METAL, "basic_worn_metal_01", {"Color": (0.18, 0.19, 0.21, 1), "Roughness": 0.45}, (0.42, 0.43, 0.46, 1), 1.0, 0.35, (0.08, 0.07, 0.10, 1), 0.3),
        mark=_MARK((0.08, 0.07, 0.10), 0.3),
        eitr=matte((0.45, 0.20, 0.85), 0.3, (0.7, 0.5, 1.0), 0.1, (0.2, 0.1, 0.3), 0.1),
        web=matte((0.86, 0.86, 0.84), 0.9, (0.9, 0.9, 0.88), 0.0, (0.5, 0.48, 0.52), 0.08),   # cobwebs
        glow_slots={"eitr": (0.6, 0.3, 1.0)}),
})
# Reels and lines (build_gear.py, VDW_KIND=gear): slots plate / flange (wood or metal), metal, grip, line, glow. The line
# is the procedural wood with no knots, its grain fine and squeezed so it reads as fibres wound round the spool.
def WD(light, dark, worn, wear, dirt, amt, rough=0.65, knots=0.3, damage=0.2, scale=8.0, stretch=0.25):
    return (WOOD, "generic_wood_01", {"Light Color": (*light, 1), "Dark Color": (*dark, 1), "Knots": knots, "Damage": damage, "Roughness": rough,
            "Clearcoat": 0.0, "_scale": scale, "_stretch": stretch}, (*worn, 1), 0.0, wear, (*dirt, 1), amt)
def LN(light, dark, rough, dirt, amt): return WD(light, dark, light, 0.05, dirt, amt, rough, 0.0, 0.0, scale=30.0, stretch=0.05)
def MT(col, rough, worn, wear, dirt, amt, lib=METAL, mat="basic_worn_metal_01"):   # (its pattern scaled down: a reel is ~9 cm)
    return (lib, mat, {"Color": (*col, 1), "Roughness": rough, "Scale": float(os.environ.get("VDW_GEAR_METAL_SCALE", "6")), "Overall Scale": float(os.environ.get("VDW_GEAR_METAL_SCALE", "6"))}, (*worn, 1), 1.0, wear, (*dirt, 1), amt)
_D, _SOOT, _RIME = (0.18, 0.12, 0.07), (0.03, 0.03, 0.03), (0.90, 0.95, 1.0)
_OAK = WD((0.52, 0.34, 0.18), (0.30, 0.18, 0.09), (0.62, 0.45, 0.28), 0.3, _D, 0.3)
_GRIP = WD((0.66, 0.48, 0.30), (0.45, 0.30, 0.17), (0.75, 0.6, 0.42), 0.25, _D, 0.2, knots=0.0)
_BIRCH = WD((0.66, 0.58, 0.44), (0.48, 0.40, 0.28), (0.76, 0.69, 0.56), 0.25, _D, 0.2)
_DARKOAK = WD((0.24, 0.15, 0.08), (0.11, 0.065, 0.035), (0.32, 0.21, 0.12), 0.3, (0.10, 0.09, 0.05), 0.35)
_ASHWOOD = WD((0.20, 0.07, 0.05), (0.08, 0.03, 0.02), (0.30, 0.12, 0.08), 0.3, _SOOT, 0.4)
_FROSTWOOD = WD((0.42, 0.46, 0.52), (0.22, 0.25, 0.30), (0.60, 0.65, 0.72), 0.35, _RIME, 0.5)
_BRONZE = MT((0.55, 0.36, 0.16), 0.35, (0.85, 0.65, 0.40), 0.3, _D, 0.3, GOLD, "gold_rough")
_IRON = MT((0.20, 0.20, 0.21), 0.5, (0.50, 0.50, 0.52), 0.35, _D, 0.3)
_SILVER = MT((0.74, 0.77, 0.80), 0.3, (0.92, 0.93, 0.95), 0.35, (0.20, 0.17, 0.12), 0.25)
_BLACK = MT((0.06, 0.06, 0.07), 0.4, (0.28, 0.28, 0.30), 0.35, (0.24, 0.18, 0.10), 0.3)
_DVERGR = MT((0.18, 0.19, 0.21), 0.45, (0.42, 0.43, 0.46), 0.35, (0.08, 0.07, 0.10), 0.3)
_TAN = LN((0.55, 0.45, 0.32), (0.38, 0.29, 0.19), 0.7, _D, 0.15)
_LINEN = LN((0.78, 0.73, 0.60), (0.60, 0.55, 0.44), 0.75, _D, 0.15)
_SINEW = LN((0.34, 0.11, 0.075), (0.19, 0.055, 0.037), 0.55, (0.05, 0.03, 0.03), 0.2)
_MOOSE = LN((0.76, 0.72, 0.64), (0.58, 0.54, 0.47), 0.7, _RIME, 0.35)
FAB, WOOL, LEATH = r"Fabrics\fabric.blend", r"Fabrics\wool_carpet.blend", r"Fabrics\pu_leather.blend"
def FB(lib, mat, inputs, worn, wear, dirt, amt): return (lib, mat, inputs, (*worn, 1), 0.0, wear, (*dirt, 1), amt)   # a fabric
_EITR = matte((0.45, 0.20, 0.85), 0.3, (0.7, 0.5, 1.0), 0.1, (0.2, 0.1, 0.3), 0.1)
_EMBER = matte((0.9, 0.22, 0.02), 0.5, (1.0, 0.45, 0.1), 0.05, (0.15, 0.03, 0.0), 0.05)
_ICE = matte((0.55, 0.80, 0.95), 0.1, (0.85, 0.95, 1.0), 0.04, (0.85, 0.93, 1.0), 0.04)
GEAR_TIERS = {
    "reel_bronze": dict(plate=_OAK, metal=_BRONZE, grip=_GRIP, line=_TAN),
    "reel_iron": dict(plate=_IRON, metal=MT((0.14, 0.14, 0.15), 0.5, (0.40, 0.40, 0.42), 0.35, _D, 0.3), grip=_GRIP, line=_TAN),
    "reel_silver": dict(plate=_SILVER, metal=MT((0.60, 0.63, 0.67), 0.3, (0.90, 0.92, 0.95), 0.3, (0.20, 0.17, 0.12), 0.25), grip=_BIRCH,
                        line=LN((0.70, 0.66, 0.56), (0.52, 0.48, 0.40), 0.7, _D, 0.15)),
    "reel_blackmetal": dict(plate=_BLACK, metal=MT((0.10, 0.10, 0.11), 0.45, (0.32, 0.32, 0.34), 0.35, (0.24, 0.18, 0.10), 0.3), grip=_DARKOAK, line=_LINEN),
    "reel_dvergr": dict(plate=MT((0.62, 0.30, 0.16), 0.35, (0.90, 0.60, 0.40), 0.35, (0.10, 0.12, 0.10), 0.3, GOLD, "gold_rough"), metal=_DVERGR,
                        grip=_DARKOAK, line=_LINEN, glow=_EITR, glow_slots={"glow": (0.6, 0.3, 1.0)}),
    "reel_flametal": dict(plate=MT((0.95, 0.45, 0.10), 0.22, (1.0, 0.80, 0.45), 0.45, (0.05, 0.04, 0.04), 0.3, GOLD, "gold_rough"),
                          metal=MT((0.08, 0.07, 0.07), 0.6, (0.30, 0.22, 0.18), 0.4, _SOOT, 0.4), grip=_ASHWOOD, line=_SINEW,
                          glow=_EMBER, glow_slots={"glow": (1.0, 0.38, 0.06)}),
    "reel_frostcore": dict(plate=_FROSTWOOD, metal=MT((0.60, 0.66, 0.74), 0.3, (0.90, 0.93, 0.97), 0.35, _RIME, 0.4),
                           grip=WD((0.55, 0.58, 0.63), (0.36, 0.39, 0.44), (0.70, 0.74, 0.80), 0.25, _RIME, 0.35, knots=0.0), line=_MOOSE,
                           glow=_ICE, glow_slots={"glow": (0.45, 0.8, 1.0)}),
    "line_leather": dict(flange=_OAK, metal=_BRONZE, line=LN((0.30, 0.17, 0.08), (0.17, 0.09, 0.04), 0.6, _D, 0.2)),
    "line_guck": dict(flange=_DARKOAK, metal=_IRON, line=LN((0.20, 0.25, 0.07), (0.10, 0.13, 0.03), 0.3, (0.08, 0.09, 0.05), 0.3)),
    "line_linen": dict(flange=_BIRCH, metal=_BLACK, line=_LINEN),
    "line_sap": dict(flange=WD((0.35, 0.36, 0.30), (0.18, 0.19, 0.15), (0.45, 0.46, 0.40), 0.3, (0.08, 0.07, 0.10), 0.3), metal=_DVERGR,
                     line=LN((0.62, 0.33, 0.06), (0.38, 0.17, 0.02), 0.25, (0.10, 0.08, 0.05), 0.15)),
    "line_morgen": dict(flange=_ASHWOOD, metal=MT((0.08, 0.07, 0.07), 0.6, (0.30, 0.22, 0.18), 0.4, _SOOT, 0.4), line=_SINEW),
    # the Sparkler Popper (build_popper.py, VDW_KIND=lure): carved finewood painted cream with a red head, worn back to
    # the wood; steel hooks; linen wraps holding Hildir's sparkler on its back, its tip glowing
    "lure_sparkler": dict(wood=WD((0.70, 0.55, 0.36), (0.50, 0.36, 0.20), (0.76, 0.62, 0.42), 0.2, _D, 0.2, knots=0.0, scale=40.0),
                          cream=matte((0.86, 0.80, 0.66), 0.55, (0.62, 0.47, 0.29), 0.35, _D, 0.25),
                          red=matte((0.62, 0.07, 0.04), 0.5, (0.62, 0.47, 0.29), 0.35, _D, 0.25),
                          eye=matte((0.02, 0.02, 0.02), 0.1, (0.9, 0.75, 0.2), 0.0, _D, 0.0),
                          metal=MT((0.55, 0.56, 0.58), 0.3, (0.80, 0.80, 0.82), 0.3, _D, 0.25),
                          thread=LN((0.80, 0.74, 0.60), (0.62, 0.56, 0.44), 0.8, _D, 0.2),
                          feather=LN((0.88, 0.85, 0.78), (0.35, 0.28, 0.22), 0.8, _D, 0.1),
                          spark=matte((0.22, 0.21, 0.20), 0.9, (0.40, 0.38, 0.35), 0.3, _SOOT, 0.4),
                          glow=_EMBER, glow_slots={"glow": (1.0, 0.75, 0.35)}),
    # the angler caps (build_caps.py, VDW_KIND=cap; textures fisher_<tier>_Unity_*): the Ice Angler's Watch Cap in deep
    # blue-grey wool, a leather tag; the Sun Angler's Cap in sun-faded olive cotton, a leather band,
    # cream stitching and the painted tackle on it
    "beanie": dict(wool=FB(WOOL, "wool_carpet_04", {"Base Color": (0.05, 0.09, 0.17, 1), "Color": (0.09, 0.14, 0.24, 1), "Scale": float(os.environ.get("VDW_KNIT_SCALE", "3.0")), "Bump Multiplier": 0.6,
                                                    # the user's tuning in Blender (2026-11-02)
                                                    "Ambient Occlusion": 0.84, "Roughness": 0.8947, "Intensity": 0.2264, "Subsurface Radius": (1.6, 3.7, 1.5)},
                      (0.10, 0.15, 0.25), 0.04, (0.045, 0.075, 0.14), 0.0),
                   leather=FB(LEATH, "pu_leather", {"Base Color": (0.55, 0.32, 0.15, 1), "Roughness": 0.55}, (0.70, 0.48, 0.28), 0.3, _D, 0.1),
                   metal=MT((0.55, 0.56, 0.58), 0.3, (0.80, 0.80, 0.82), 0.3, _D, 0.25)),
    "bucket": dict(cloth=FB(FAB, "fabric_02", {"Fabric Color 1": (0.30, 0.32, 0.14, 1), "Fabric Color 2": (0.20, 0.22, 0.09, 1), "Scale": float(os.environ.get("VDW_CLOTH_SCALE", "45.0")), "Thread Count": 2.0, "Bump": 2.0, "Roughness": 0.9},
                      (0.50, 0.50, 0.30), 0.3, _D, 0.25),
                   leather=FB(LEATH, "pu_leather", {"Base Color": (0.26, 0.14, 0.06, 1), "Roughness": 0.55}, (0.45, 0.30, 0.17), 0.35, _D, 0.25),
                   thread=LN((0.80, 0.74, 0.60), (0.62, 0.56, 0.44), 0.8, _D, 0.2),
                   metal=MT((0.55, 0.56, 0.58), 0.3, (0.80, 0.80, 0.82), 0.3, _D, 0.25),
                   red=matte((0.70, 0.06, 0.04), 0.35, (0.85, 0.75, 0.70), 0.15, _D, 0.1),
                   white=matte((0.88, 0.86, 0.80), 0.35, (0.70, 0.65, 0.55), 0.15, _D, 0.15),
                   lure=matte((0.85, 0.45, 0.08), 0.3, (1.0, 0.85, 0.5), 0.2, _D, 0.1),
                   black=matte((0.02, 0.02, 0.02), 0.15, (0.2, 0.2, 0.2), 0.05, _D, 0.0),
                   feather_b=matte((0.04, 0.50, 0.85), 0.8, (0.5, 0.8, 1.0), 0.1, _D, 0.05),
                   feather_p=matte((0.90, 0.12, 0.50), 0.8, (1.0, 0.6, 0.8), 0.1, _D, 0.05)),
    "line_moose": dict(flange=_FROSTWOOD, metal=MT((0.60, 0.66, 0.74), 0.3, (0.90, 0.93, 0.97), 0.35, _RIME, 0.4), line=_MOOSE),
}
PAINT = {"t1": (0.055, 0.14, 0.075), "t2": (0.20, 0.03, 0.02), "t3": (0.62, 0.58, 0.48), "t4": (0.36, 0.22, 0.03),
         "swamp": (0.045, 0.012, 0.008), "mountain": (0.28, 0.36, 0.44), "mistlands": (0.12, 0.07, 0.19)}
# how worn the paint is per tier: the low tiers mostly bare wood with the colour only clinging on, the high ones kept up
PAINT_WEAR = {"t1": 0.62, "t2": 0.55, "t3": 0.42, "t4": 0.4, "swamp": 0.5, "mountain": 0.45, "mistlands": 0.4}
if KIND == "tacklebox" and os.environ.get("VDW_PAINT", "1") == "1":     # VDW_PAINT=0: bare wood (the first wooden boxes)
    for k, v in PAINT.items():
        if TB_TIERS[k].get("char"): continue          # charred wood: no paint left on it
        TB_TIERS[k]["paint"] = v
        w = list(TB_TIERS[k]["wood"]); w[5] = PAINT_WEAR[k] * float(os.environ.get("VDW_PAINT_WEAR", "1")); TB_TIERS[k]["wood"] = tuple(w)
if KIND == "tacklebox": TIERS = TB_TIERS
elif KIND in ("gear", "lure", "cap"): TIERS = GEAR_TIERS
# The baits from build_lures.py, restyled (restyle_lure.py, VDW_KIND=lure, tier = the bait id: lure_bone_jig, frost_bait):
# one Sanctus + Grungit recipe per atlas material, shared by every bait; what glows glows in its own colour, and "glow"
# in the bait's boss colour (as build_lures.py had it)
_EYE_D = (0.06, 0.05, 0.04)
# clean Sanctus bases for what isn't metal (on a bait the worn-metal "matte" kept the metal's scratched wear - meat and
# paint came out speckled): soft things on rubber, paint on polyethylene, glassy things on resin; Grungit only lightly
RUBBER, POLY, RESIN = r"Synthetics\rubber.blend", r"Synthetics\polyethylene.blend", r"Synthetics\tr4_resin.blend"
def SOFT(col, var=0.3, grime=0.15, bump=0.3, dirt=_D, amt=0.1):
    return (RUBBER, "rubber_04", {"Color": (*col, 1), "Variation": var, "Grime": grime, "Grain": 0.0, "Bump": bump, "Bevel Radius": 0.0, "_no_normal": True},
            (*[min(1.0, c * 1.15) for c in col], 1), 0.0, 0.03, (*dirt, 1), amt)
def PAINT(col, damage, rough=0.35, grime=0.25, wear=0.12, amt=0.1):
    return (POLY, "polyethylene_02", {"Plastic Color": (*col, 1), "Plastic Roughness": rough, "Grimes": grime, "Damage Color": (*damage, 1), "Damage Roughness": 0.6, "Bump": 0.5},
            (*damage, 1), 0.0, wear, (*_D, 1), amt)
def GLASSY(col, rough=0.15, bubbles=0.4, grime=0.1, dirt=_D, amt=0.05):
    return (RESIN, "tr4_resin_04", {"Base Color": (*col, 1), "Roughness": rough, "Surface Bubbles": bubbles, "Grime": grime, "_no_normal": True},
            (*[min(1.0, c * 1.2) for c in col], 1), 0.0, 0.03, (*dirt, 1), amt)
LURE_MATS = dict(
    bone=matte((0.86, 0.80, 0.66), 0.55, (0.96, 0.92, 0.80), 0.25, _D, 0.3),
    hair=LN((0.42, 0.30, 0.18), (0.25, 0.17, 0.10), 0.85, _D, 0.15),
    flint=matte((0.30, 0.28, 0.25), 0.3, (0.52, 0.49, 0.44), 0.35, _D, 0.2),
    bark=WD((0.30, 0.20, 0.12), (0.14, 0.09, 0.05), (0.42, 0.31, 0.20), 0.3, _D, 0.35, scale=20.0, stretch=0.1),
    moss=SOFT((0.22, 0.38, 0.10), var=0.5, grime=0.3, bump=0.6),
    ooze=GLASSY((0.30, 0.52, 0.16), rough=0.2, bubbles=0.8, grime=0.25),
    silver=_SILVER, blackmetal=_BLACK, iron=_IRON, bronze=_BRONZE,
    steel=MT((0.55, 0.56, 0.58), 0.3, (0.80, 0.80, 0.82), 0.3, _D, 0.25),
    gold=MT((0.95, 0.75, 0.30), 0.2, (1.0, 0.9, 0.6), 0.3, _D, 0.2, GOLD, "gold_rough"),
    core=SOFT((0.22, 0.07, 0.03), var=0.5, grime=0.4, bump=0.6, dirt=_SOOT),
    chitin=PAINT((0.16, 0.08, 0.20), (0.36, 0.20, 0.45), rough=0.2),
    red=PAINT((0.62, 0.08, 0.05), (0.82, 0.62, 0.44)),
    feather=LN((0.90, 0.88, 0.82), (0.38, 0.30, 0.24), 0.8, _D, 0.1),
    wood=WD((0.72, 0.56, 0.36), (0.50, 0.36, 0.20), (0.80, 0.66, 0.46), 0.25, _D, 0.2, knots=0.0, scale=40.0),
    crank=PAINT((0.025, 0.11, 0.035), (0.30, 0.42, 0.20), wear=0.12),     # a dark green back (the paint base brightens: set dark)
    belly=PAINT((0.80, 0.60, 0.08), (0.92, 0.84, 0.50), wear=0.08),       # its yellow belly
    resin=GLASSY((0.85, 0.52, 0.12), rough=0.12, bubbles=0.5),
    leather=FB(LEATH, "pu_leather", {"Base Color": (0.20, 0.11, 0.05, 1), "Roughness": 0.6}, (0.36, 0.22, 0.12), 0.15, _D, 0.15),
    guck=SOFT((0.018, 0.038, 0.010), var=0.4, grime=0.3, bump=0.4, dirt=(0.02, 0.04, 0.01)),   # dark guck green (the rubber base brightens: set dark)
    scales=MT((0.88, 0.91, 0.95), 0.18, (0.98, 0.99, 1.0), 0.1, (0.20, 0.28, 0.40), 0.1),     # bright silver fish skin
    white=PAINT((0.90, 0.88, 0.82), (0.62, 0.50, 0.34)),
    linen=_LINEN,
    rind=SOFT((0.42, 0.24, 0.22), var=0.3, grime=0.2, bump=0.5),      # pork rind (the base brightens: set dark)
    curly=SOFT((0.72, 0.84, 0.18), var=0.15, grime=0.05, bump=0.2),
    thread=LN((0.12, 0.10, 0.08), (0.05, 0.04, 0.03), 0.7, _D, 0.1),
    black=PAINT((0.02, 0.02, 0.02), (0.15, 0.15, 0.15), rough=0.1, wear=0.0),
    ice=GLASSY((0.60, 0.84, 0.96), rough=0.05, bubbles=0.6, dirt=_RIME, amt=0.1),
    frostcore=GLASSY((0.06, 0.16, 0.34), rough=0.2, bubbles=0.5, dirt=_RIME, amt=0.1),
    jewel=GLASSY((0.60, 0.88, 1.0), rough=0.03, bubbles=0.2),
    blubber=GLASSY((0.62, 0.52, 0.40), rough=0.25, bubbles=0.15, grime=0.15),   # glossy cream fat, oily
    rim=SOFT((0.62, 0.36, 0.38), var=0.15, grime=0.05, bump=0.2),      # the pale pink ring at the edge of cut fish
    flesh=SOFT((0.30, 0.09, 0.08), var=0.4, grime=0.2, bump=0.4, dirt=(0.14, 0.02, 0.02), amt=0.2),   # raw fish flesh, bloody pink
    back=MT((0.16, 0.20, 0.24), 0.3, (0.40, 0.46, 0.52), 0.1, (0.20, 0.28, 0.40), 0.1),               # a baitfish's dark blue-grey back
    hide=SOFT((0.05, 0.052, 0.058), var=0.9, grime=0.3, bump=0.5, dirt=(0.01, 0.01, 0.012), amt=0.2),   # dark mottled seal hide
    berry=GLASSY((0.22, 0.008, 0.02), rough=0.22, bubbles=0.2, grime=0.3),   # lingonberries, glossy deep red
    barka=WD((0.80, 0.78, 0.72), (0.30, 0.23, 0.18), (0.90, 0.88, 0.84), 0.2, _D, 0.2, knots=0.0, scale=20.0),   # birch bark
    meat=SOFT((0.13, 0.010, 0.020), var=0.5, grime=0.2, bump=0.4, dirt=(0.06, 0.006, 0.01)),   # raw meat, deep crimson (the rubber base brightens: set dark)
    fat=SOFT((0.36, 0.10, 0.13), var=0.3, grime=0.1, bump=0.3),          # its pale pink marbling
    snow=SOFT((0.58, 0.64, 0.74), var=0.2, grime=0.0, bump=0.6),        # snow, a soft blue-white (the base brightens: full white flattened it)
    gland=GLASSY((0.55, 0.85, 1.0), rough=0.1, bubbles=0.5),
    entrail=SOFT((0.50, 0.22, 0.30), var=0.5, grime=0.3, bump=0.5, dirt=(0.20, 0.06, 0.08)),
    bloodsac=GLASSY((0.30, 0.02, 0.03), rough=0.1, bubbles=0.3),
    serpent=PAINT((0.10, 0.36, 0.32), (0.55, 0.74, 0.55), rough=0.3),
    eitr=GLASSY((0.55, 0.30, 1.0), rough=0.1, bubbles=0.6),
    cork=SOFT((0.30, 0.19, 0.09), var=0.6, grime=0.2, bump=0.8, dirt=(0.14, 0.08, 0.04)),     # cork, pitted (the base brightens: set dark)
    sight=PAINT((0.95, 0.28, 0.02), (0.80, 0.60, 0.42), rough=0.3, wear=0.05),               # a float's orange sight tip
    charred=SOFT((0.03, 0.025, 0.022), var=0.6, grime=0.4, bump=0.7, dirt=_SOOT),            # charred bone
    glow=matte((1.0, 1.0, 1.0), 0.3, (1.0, 1.0, 1.0), 0.0, _D, 0.0),
)
_BOSS_GLOW = {"antler": (0.35, 0.9, 1.0), "root": (0.75, 0.95, 0.25), "ooze": (0.45, 1.0, 0.3), "wyrm": (0.4, 0.75, 1.0),
              "ember": (1.0, 0.35, 0.12), "chitin": (0.8, 0.35, 1.0), "crown": (0.55, 0.85, 1.0)}
# the hook items (build_lures hook_circle / hook_ewg / hook_treble, tier e.g. hook_circle_small): their wire in the
# tier's metal, as the J hooks go copper, bronze, iron, silvered iron, black metal
_HOOK_METAL = {"small": MT((0.62, 0.34, 0.20), 0.35, (0.85, 0.55, 0.38), 0.3, _D, 0.25, GOLD, "gold_rough"),
               "medium": _BRONZE, "large": _IRON,
               "heavy": MT((0.62, 0.64, 0.68), 0.3, (0.88, 0.90, 0.93), 0.3, _D, 0.25), "giant": _BLACK}
if KIND == "lure" and TIER not in TIERS:
    _g = _BOSS_GLOW.get(TIER.replace("lure_", ""), (1.0, 1.0, 1.0))
    # (glowing parts in the boss's colour, not white)
    T = dict(LURE_MATS, glow=matte(tuple(c * 0.55 for c in _g), 0.3, _g, 0.0, _D, 0.0), glow_keep_albedo=True, marble=(0.42, 0.16, 0.19), glow_slots={"glow": _g, "core": (0.8, 0.3, 0.06), "jewel": (0.55, 0.85, 1.0), "gland": (0.4, 0.7, 0.85),
                                    "eitr": (0.62, 0.42, 1.0), "frostcore": (0.3, 0.6, 0.8), "ooze": (0.2, 0.45, 0.12)})
    if TIER.startswith("hook_"): T["steel"] = _HOOK_METAL.get(TIER.rsplit("_", 1)[-1], T["steel"])
    # the floats' own looks (roadmap #25; the lures keep theirs): the Eitr Float's vial a deep glowing violet, the Rime
    # Float's frostcore dark as the real thing with only a faint cold light, the Frost Float's ice blue rather than white
    if TIER == "float_eitr":
        T["eitr"] = GLASSY((0.09, 0.01, 0.28), rough=0.1, bubbles=0.5); T["glow_slots"] = dict(T["glow_slots"], eitr=(0.26, 0.03, 0.62))   # (a bright glow washed out to lavender)
    if TIER == "float_rime":
        T["frostcore"] = GLASSY((0.015, 0.04, 0.10), rough=0.25, bubbles=0.4, dirt=_RIME, amt=0.05); T["glow_slots"] = dict(T["glow_slots"], frostcore=(0.03, 0.08, 0.16))
    if TIER == "float_frost":
        T["ice"] = GLASSY((0.14, 0.38, 0.68), rough=0.06, bubbles=0.6, dirt=_RIME, amt=0.02)
else:
    T = TIERS[TIER]
box = bpy.data.objects[PREFIX]; me = box.data
# the parts, as the model's materials (a tackle box may have extras: mark, moss, ice, eitr)
SLOTS = [m.name.split(".")[0] for m in me.materials] if KIND in ("tacklebox", "gear", "lure", "cap") else ["wood", "grip", "iron", "brass"]
me.uv_layers.active = me.uv_layers["UVMap"]; me.uv_layers["UVMap"].active_render = True
co = np.array([v.co[:] for v in me.vertices]); lo, hi = co.min(0), co.max(0); LENGTH = float(hi[0] - lo[0])

def append_material(rel, name):
    with bpy.data.libraries.load(os.path.join(SANCTUS, rel)) as (src, dst): dst.materials = [name]
    return dst.materials[0]
with bpy.data.libraries.load(GRUNGIT) as (src, dst): dst.node_groups = ["Grungit v1.9.1", "Grungit Dirt v1.9.1", "Baker v1.8.3"]
G_MAIN, G_DIRT, G_BAKER = dst.node_groups
mask_img = bpy.data.images.new(f"{PREFIX}_{TIER}_mask", SIZE, SIZE, alpha=False); mask_img.colorspace_settings.name = 'Non-Color'

def char_wood(N, L, grp, g, C):
    """charred wood (the Ashlands box): near-black charcoal split into small blocks along the grain, ash-grey
    highlights, the cracks sunk in, and in patches the cracks and a few grain lines glowing like embers. The glow
    is the node "vdw_char_glow" (0..1), baked to the Emission map later. C: dict(glow colour, block sizes ...)"""
    def node(t, **kw):
        n = N.new(t)
        for k, v in kw.items(): setattr(n, k, v)
        return n
    def vmath(op, a, b):
        n = node("ShaderNodeVectorMath", operation=op); L.new(a, n.inputs[0])
        if isinstance(b, tuple): n.inputs[1].default_value = b
        else: L.new(b, n.inputs[1])
        return n.outputs[0]
    def maprange(sock, f0, f1, t0=0.0, t1=1.0):
        n = node("ShaderNodeMapRange", clamp=True); L.new(sock, n.inputs["Value"])
        n.inputs["From Min"].default_value, n.inputs["From Max"].default_value = f0, f1
        n.inputs["To Min"].default_value, n.inputs["To Max"].default_value = t0, t1
        return n.outputs["Result"]
    def math(op, a, b):
        n = node("ShaderNodeMath", operation=op); L.new(a, n.inputs[0])
        if isinstance(b, float): n.inputs[1].default_value = b
        else: L.new(b, n.inputs[1])
        return n
    def noise(vec, scale, detail=3.0):
        n = node("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = scale; n.inputs["Detail"].default_value = detail
        L.new(vec, n.inputs["Vector"]); return n
    uv = node("ShaderNodeUVMap", uv_map="Grain").outputs["UV"]            # metres, U along the board
    w = noise(uv, 14.0).outputs["Color"]                                 # a little wobble so the blocks aren't regular
    w = vmath('SUBTRACT', w, (0.5, 0.5, 0.5)); s = node("ShaderNodeVectorMath", operation='SCALE'); L.new(w, s.inputs[0]); s.inputs["Scale"].default_value = 0.012
    warped = vmath('ADD', uv, s.outputs[0])
    # the blocks: a Voronoi's edges, stretched along the grain (BLOCK = (length, width) in metres)
    bl, bw = C.get("block", (0.045, 0.014))
    vor = node("ShaderNodeTexVoronoi", feature='DISTANCE_TO_EDGE'); vor.inputs["Scale"].default_value = 1.0
    L.new(vmath('MULTIPLY', warped, (1.0 / bl, 1.0 / bw, 1.0)), vor.inputs["Vector"])
    crack = maprange(vor.outputs["Distance"], 0.0, C.get("crack", 0.07), 1.0, 0.0)    # 1 in the crack
    # where it's still burning: broad patches
    hot = maprange(noise(uv, C.get("patch", 7.0), 2.0).outputs["Fac"], *C.get("hot", (0.47, 0.62)))
    # glowing grain lines running along the board
    wave = node("ShaderNodeTexWave", wave_type='BANDS', bands_direction='Y'); wave.inputs["Scale"].default_value = C.get("lines", 55.0)
    wave.inputs["Distortion"].default_value = 9.0; wave.inputs["Detail"].default_value = 3.0; wave.inputs["Detail Scale"].default_value = 1.5
    L.new(uv, wave.inputs["Vector"])
    lines = maprange(wave.outputs["Fac"], 0.88, 0.98)
    hot_crack = math('MULTIPLY', crack, hot).outputs[0]
    hot_line = math('MULTIPLY', math('MULTIPLY', lines, hot).outputs[0], C.get("line_glow", 0.55)).outputs[0]
    glow = math('MAXIMUM', hot_crack, hot_line); glow.name = "vdw_char_glow"
    # colour: charcoal with ash-grey speckle and streaks, the cracks darker, glowing places tinted ember
    ash = maprange(noise(warped, 70.0, 6.0).outputs["Fac"], 0.55, 0.7)
    base = node("ShaderNodeMix", data_type='RGBA'); L.new(ash, base.inputs["Factor"])
    base.inputs[6].default_value = (*C.get("char_col", (0.018, 0.017, 0.018)), 1); base.inputs[7].default_value = (*C.get("ash_col", (0.09, 0.088, 0.085)), 1)
    dark = node("ShaderNodeMix", data_type='RGBA'); L.new(maprange(crack, 0.0, 1.0, 0.0, 0.85), dark.inputs["Factor"])
    L.new(base.outputs[2], dark.inputs[6]); dark.inputs[7].default_value = (0.004, 0.003, 0.003, 1)
    ember = node("ShaderNodeMix", data_type='RGBA'); L.new(glow.outputs[0], ember.inputs["Factor"])
    L.new(dark.outputs[2], ember.inputs[6]); ember.inputs[7].default_value = (*[c * 0.6 for c in C["glow"]], 1)
    for l in list(g.inputs["Base Color 1"].links): L.remove(l)
    L.new(ember.outputs[2], g.inputs["Base Color 1"])
    for l in list(g.inputs["Roughness 1"].links): L.remove(l)
    g.inputs["Roughness 1"].default_value = 0.9
    # the cracks sunk in
    bump = node("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.8; bump.inputs["Distance"].default_value = 0.004
    L.new(maprange(crack, 0.0, 1.0, 1.0, 0.0), bump.inputs["Height"])
    if "Normal Bake" in grp.outputs: L.new(grp.outputs["Normal Bake"], bump.inputs["Normal"])
    if "Normal" in g.inputs: L.new(bump.outputs["Normal"], g.inputs["Normal"])

def build(slot):
    rel, name, inputs, worn, worn_metal, wear, dirt_col, dirt = T[slot]
    m = append_material(rel, name).copy(); m.name = f"cool_{slot}_{TIER}"
    N, L = m.node_tree.nodes, m.node_tree.links
    grp = next(n for n in N if n.type == 'GROUP' and n.node_tree and any("Bake" in o.name for o in n.outputs))
    inputs = dict(inputs); stretch = inputs.pop("_stretch", None); scale = inputs.pop("_scale", None)   # per-part grain (gear)
    own_normal = not inputs.pop("_no_normal", False)   # rubber and resin: their normal output carried the faces' flat normals (facets)
    for k, v in inputs.items():
        if k in grp.inputs: grp.inputs[k].default_value = v
    if rel == WOOD:      # the grain along each board's long side: its "Grain" UVs (metres), U along the length
        uv = N.new("ShaderNodeUVMap"); uv.uv_map = "Grain"; uv.name = "vdw_grain"
        # stretched 5x along the board (U) so the grain runs straight instead of wavy
        mp = N.new("ShaderNodeMapping"); mp.name = "vdw_grain_stretch"; mp.inputs["Scale"].default_value = (stretch if stretch is not None else float(os.environ.get("VDW_GRAIN_STRETCH", "0.2")), 1.0, 1.0)
        L.new(uv.outputs["UV"], mp.inputs["Vector"]); L.new(mp.outputs["Vector"], grp.inputs["Vector"])
        if "Scale" in grp.inputs: grp.inputs["Scale"].default_value = scale if scale is not None else float(os.environ.get("VDW_WOOD_SCALE", "1.6"))
        # generic_wood's grain runs along V: turned a quarter about Z it runs along U, the board's length
        grp.inputs["Texture Rotation"].default_value = (0.0, 0.0, 1.5708)
    mtex = N.new("ShaderNodeTexImage"); mtex.image = mask_img; mtex.name = "vdw_mask"
    g = N.new("ShaderNodeGroup"); g.node_tree = G_MAIN; g.name = "vdw_grungit"
    L.new(mtex.outputs["Color"], g.inputs["Grungit Mask"])
    L.new(grp.outputs["Color Bake"], g.inputs["Base Color 1"]); L.new(grp.outputs["Roughness Bake"], g.inputs["Roughness 1"])
    if "Metallic Bake" in grp.outputs: L.new(grp.outputs["Metallic Bake"], g.inputs["Metallic 1"])
    else: g.inputs["Metallic 1"].default_value = 0.0
    g.inputs["Base Color 2"].default_value = worn; g.inputs["Metallic 2"].default_value = worn_metal
    if slot == "wood" and T.get("paint"):
        # painted wood (the tackle box): the paint on top with the grain faintly through it, worn back to the bare wood
        # (the Sanctus wood itself, not a flat colour) along the edges and scratches
        mx = N.new("ShaderNodeMix"); mx.data_type = 'RGBA'; mx.blend_type = 'OVERLAY'; mx.name = "vdw_paint"
        mx.inputs["Factor"].default_value = float(os.environ.get("VDW_PAINT_GRAIN", "0.35"))
        mx.inputs[6].default_value = (*T["paint"], 1.0); L.new(grp.outputs["Color Bake"], mx.inputs[7])
        L.new(mx.outputs[2], g.inputs["Base Color 1"]); L.new(grp.outputs["Color Bake"], g.inputs["Base Color 2"])
        for l in list(g.inputs["Roughness 1"].links): L.remove(l)
        g.inputs["Roughness 1"].default_value = 0.5; g.inputs["Roughness 2"].default_value = 0.7
    if not (slot == "wood" and T.get("paint")): g.inputs["Roughness 2"].default_value = 0.35 if worn_metal > 0.5 else 0.7
    g.inputs["Transition Color"].default_value = worn; g.inputs["Transition Amount"].default_value = 0.0
    g.inputs["Global Control"].default_value = wear * 0.7; g.inputs["Edge Wear Spread"].default_value = 0.5
    g.inputs["Scratch Amount"].default_value = 0.6 if worn_metal > 0.5 else 0.3
    g.inputs["Cracks Amount"].default_value = 0.25 if slot == "wood" else 0.0; g.inputs["Grunge Amount"].default_value = float(os.environ.get("VDW_GRUNGE", "0.45"))
    g.inputs["Scale"].default_value = 1.0 / max(LENGTH, 0.1)
    d = N.new("ShaderNodeGroup"); d.node_tree = G_DIRT; d.name = "vdw_dirt"
    L.new(mtex.outputs["Color"], d.inputs["Grungit Mask"])
    for a in ("Base Color", "Metallic", "Roughness", "Normal"):
        if a in g.outputs and a in d.inputs: L.new(g.outputs[a], d.inputs[a])
    if own_normal and "Normal Bake" in grp.outputs and "Normal" in g.inputs: L.new(grp.outputs["Normal Bake"], g.inputs["Normal"])
    if slot in ("meat", "blubber", "hide") and T.get("marble"):
        # fat marbling through raw meat: wavy pale streaks (object space), mixed over the meat's colour - per-face fat
        # came out blocky on a remeshed slab
        tc = N.new("ShaderNodeTexCoord")
        wv = N.new("ShaderNodeTexWave"); wv.wave_type = 'BANDS'; wv.bands_direction = 'DIAGONAL'
        wv.inputs["Scale"].default_value = {"hide": 160.0}.get(slot, 70.0); wv.inputs["Distortion"].default_value = {"hide": 30.0}.get(slot, 10.0); wv.inputs["Detail"].default_value = 3.0
        wv.inputs["Detail Scale"].default_value = 1.4
        L.new(tc.outputs["Object"], wv.inputs["Vector"])
        mr = N.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = 0.88; mr.inputs["From Max"].default_value = 0.96
        L.new(wv.outputs["Fac"], mr.inputs["Value"])
        mx = N.new("ShaderNodeMix"); mx.data_type = 'RGBA'; L.new(mr.outputs["Result"], mx.inputs["Factor"])
        L.new(grp.outputs["Color Bake"], mx.inputs[6]); mx.inputs[7].default_value = (*{"meat": T["marble"], "blubber": (0.78, 0.52, 0.48), "hide": (0.16, 0.16, 0.17)}[slot], 1.0)   # meat: fat; blubber: pinkish layers; hide: pale mottling
        for l in list(g.inputs["Base Color 1"].links): L.remove(l)
        L.new(mx.outputs[2], g.inputs["Base Color 1"])
    ribs = box.get("vdw_ribs") if slot == "wool" else None
    if ribs and "Normal" in g.inputs:
        # a knitted cap's ribs (build_caps.py): rounded ridges running up round the cap's axis, baked into the normal map
        # over the wool's own - the angle round the axis worked out per pixel, so no seam where it wraps
        n_ribs, cx, cy = float(ribs[0]), float(ribs[1]), float(ribs[2])
        tc = N.new("ShaderNodeTexCoord"); sp = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Object"], sp.inputs[0])
        def rm(op, a, b):
            n_ = N.new("ShaderNodeMath"); n_.operation = op
            for i, v in enumerate((a, b)):
                if isinstance(v, (int, float)): n_.inputs[i].default_value = v
                else: L.new(v, n_.inputs[i])
            return n_.outputs[0]
        ang = rm('ARCTAN2', rm('SUBTRACT', sp.outputs["Y"], cy), rm('SUBTRACT', sp.outputs["X"], cx))
        # the normal tipped round the cap by each rib's slope (no bump node: its derivatives tilted whole UV islands in
        # the bake): n + t * a * sin(ribs * angle), t the direction round the cap's axis, on the wool's own normal
        dx = rm('SUBTRACT', sp.outputs["X"], cx); dy = rm('SUBTRACT', sp.outputs["Y"], cy)
        ln = rm('MAXIMUM', rm('SQRT', rm('ADD', rm('MULTIPLY', dx, dx), rm('MULTIPLY', dy, dy)), 0.0), 1e-4)
        cv = N.new("ShaderNodeCombineXYZ"); L.new(rm('DIVIDE', rm('MULTIPLY', dy, -1.0), ln), cv.inputs["X"]); L.new(rm('DIVIDE', dx, ln), cv.inputs["Y"])
        slope = rm('MULTIPLY', rm('SINE', rm('MULTIPLY', ang, n_ribs), 0.0), float(os.environ.get("VDW_RIB_STRENGTH", "0.45")))
        tilt = N.new("ShaderNodeVectorMath"); tilt.operation = 'SCALE'; L.new(cv.outputs[0], tilt.inputs[0]); L.new(slope, tilt.inputs["Scale"])
        geo = N.new("ShaderNodeNewGeometry")
        add = N.new("ShaderNodeVectorMath"); add.operation = 'ADD'
        L.new(grp.outputs["Normal Bake"] if "Normal Bake" in grp.outputs else geo.outputs["Normal"], add.inputs[0]); L.new(tilt.outputs[0], add.inputs[1])
        nrm = N.new("ShaderNodeVectorMath"); nrm.operation = 'NORMALIZE'; L.new(add.outputs[0], nrm.inputs[0])
        L.new(nrm.outputs[0], g.inputs["Normal"])
    d.inputs["Dirt Base Color"].default_value = dirt_col; d.inputs["Overall Amount"].default_value = min(1.0, dirt + float(os.environ.get("VDW_DIRT_ADD", "0.15"))); d.inputs["AO"].default_value = 0.5
    if slot == "wood" and T.get("char"): char_wood(N, L, grp, g, T["char"])
    bs = N.new("ShaderNodeBsdfPrincipled"); bs.name = "vdw_bsdf"
    for a, b in (("Color", "Base Color"), ("Metallic", "Metallic"), ("Roughness", "Roughness"), ("Normal", "Normal")): L.new(d.outputs[a], bs.inputs[b])
    out = next(n for n in N if n.type == 'OUTPUT_MATERIAL' and n.is_active_output); L.new(bs.outputs["BSDF"], out.inputs["Surface"])
    em = N.new("ShaderNodeEmission"); em.name = "vdw_emit"
    tg = N.new("ShaderNodeTexImage"); tg.name = "vdw_target"
    return m

names = [m.name for m in me.materials]
mats = [build(s) for s in SLOTS]
idx = {n: i for i, n in enumerate(names)}
remap = [SLOTS.index(n) if n in SLOTS else 0 for n in names]
before = [remap[p.material_index] for p in me.polygons]          # clearing the slots resets every face to the first
me.materials.clear()
for m in mats: me.materials.append(m)
for p, i in zip(me.polygons, before): p.material_index = i
print(f"BAKE {TIER}: " + ", ".join(f"{s} {sum(1 for p in me.polygons if p.material_index == i)} faces" for i, s in enumerate(SLOTS)))

sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = SAMPLES
sc.render.bake.margin = 8; sc.render.bake.use_clear = True
for o in bpy.context.view_layer.objects: o.select_set(o is box)
bpy.context.view_layer.objects.active = box
if "Armature" in box.modifiers: box.modifiers["Armature"].show_render = False
def set_target(img):
    for m in mats:
        t = m.node_tree.nodes["vdw_target"]; t.image = img
        for n in m.node_tree.nodes: n.select = False
        t.select = True; m.node_tree.nodes.active = t
# The inside of the box: a small closed space, all of it "tucked in" - baked shut, the Grungit mask read it as one deep
# cavity (Grungit Dirt filled it with dirt) and the edge shading went near black. So the surfaces inside the walls get
# their mask and shading baked with the lid open (VDW_AO_OPEN degrees; the tackle box's 105 by default; the shading over
# a shorter VDW_AO_DIST_INSIDE), and everything outside keeps the lid-shut bake (open, the lid's back edge pressed
# against the box and came out smudged).
AO_IN = float(os.environ.get("VDW_AO_DIST_INSIDE", "0.012"))
AO_OPEN = float(os.environ.get("VDW_AO_OPEN", "105" if KIND == "tacklebox" else "0"))
# the inside: within the walls' inner faces, from the floor up to the lid's underside (half sizes and heights, metres)
INSIDE = [float(v) for v in os.environ.get("VDW_INSIDE", "0.2015,0.0915,0.02,0.1775" if KIND == "tacklebox" else "0.272,0.142,0.035,0.3175").split(",")]
def bake_value(make, name, float_buf=True):
    """bakes, on every part, the colour socket make(nodes) gives as emission; returns its rgb"""
    img = bpy.data.images.new(name, SIZE, SIZE, alpha=False, float_buffer=float_buf); img.colorspace_settings.name = 'Non-Color'
    for m in mats:
        N, L = m.node_tree.nodes, m.node_tree.links; em = N["vdw_emit"]; out = next(n for n in N if n.type == 'OUTPUT_MATERIAL' and n.is_active_output)
        for l in list(em.inputs["Color"].links): L.remove(l)
        L.new(make(N), em.inputs["Color"]); L.new(em.outputs["Emission"], out.inputs["Surface"])
    set_target(img); bpy.ops.object.bake(type='EMIT')
    a = np.empty(SIZE * SIZE * 4, np.float32); img.pixels.foreach_get(a); return a.reshape(SIZE, SIZE, 4)[..., :3]
_rig = box.parent if box.parent and box.parent.type == 'ARMATURE' else None
def lid_open(on):
    if not AO_OPEN or _rig is None or "Armature" not in box.modifiers: return False
    pb = _rig.pose.bones["lid"]; pb.rotation_mode = 'XYZ'; pb.rotation_euler = (np.radians(AO_OPEN) if on else 0, 0, 0)
    box.modifiers["Armature"].show_render = on; bpy.context.view_layer.update(); return True
Prest = bake_value(lambda N: N.new("ShaderNodeNewGeometry").outputs["Position"], "bake_pos_rest")   # lid shut
inside = (np.abs(Prest[..., 0]) < INSIDE[0]) & (np.abs(Prest[..., 1]) < INSIDE[1]) & (Prest[..., 2] > INSIDE[2]) & (Prest[..., 2] < INSIDE[3])
# and the rim where lid meets box (the walls' top edges, the lid's underside round its edge): hidden shut, seen open
RIM = [float(v) for v in os.environ.get("VDW_RIM", "0.2275,0.1175,0.171,0.1778" if KIND == "tacklebox" else "0,0,0,0").split(",")]
inside |= (np.abs(Prest[..., 0]) < RIM[0]) & (np.abs(Prest[..., 1]) < RIM[1]) & (Prest[..., 2] > RIM[2]) & (Prest[..., 2] < RIM[3])
if not AO_OPEN: inside[:] = False
print(f"BAKE inside the box: {int(inside.sum())} pixels")
# the Grungit mask (AO / edges / cavities), as the add-on's Baker makes it
mm = bpy.data.materials.new("cool_maskbake"); mm.use_nodes = True; mn, ml = mm.node_tree.nodes, mm.node_tree.links
for n in list(mn):
    if n.type != 'OUTPUT_MATERIAL': mn.remove(n)
bk = mn.new("ShaderNodeGroup"); bk.node_tree = G_BAKER; bk.inputs["Scale"].default_value = 0.5 * LENGTH
ml.new(bk.outputs["Output"], next(n for n in mn if n.type == 'OUTPUT_MATERIAL').inputs["Surface"])
mt = mn.new("ShaderNodeTexImage"); mt.image = mask_img; mn.active = mt
saved = [p.material_index for p in me.polygons]; me.materials.append(mm)
for p in me.polygons: p.material_index = len(me.materials) - 1
bpy.ops.object.bake(type='EMIT')
if inside.any() and lid_open(True):
    shut = np.empty(SIZE * SIZE * 4, np.float32); mask_img.pixels.foreach_get(shut)
    bpy.ops.object.bake(type='EMIT'); lid_open(False)
    opened = np.empty(SIZE * SIZE * 4, np.float32); mask_img.pixels.foreach_get(opened)
    sel = np.repeat(inside.ravel(), 4)
    mask_img.pixels.foreach_set(np.where(sel, opened, shut)); mask_img.update()
print(f"BAKE mask done (inside with the lid open {AO_OPEN:.0f} deg)")
mask_img.filepath_raw = os.path.join(TEXDIR, f"{PREFIX}_{TIER}_GrungitMask.png"); mask_img.file_format = 'PNG'; mask_img.save()
for p, i in zip(me.polygons, saved): p.material_index = i
me.materials.pop(index=len(me.materials) - 1)

def channel(socket):
    img = bpy.data.images.new(f"bake_{socket}", SIZE, SIZE, alpha=False)
    if socket != "Color": img.colorspace_settings.name = 'Non-Color'
    for m in mats:
        N, L = m.node_tree.nodes, m.node_tree.links; em = N["vdw_emit"]; out = next(n for n in N if n.type == 'OUTPUT_MATERIAL' and n.is_active_output)
        for l in list(em.inputs["Color"].links): L.remove(l)
        inp = N["vdw_bsdf"].inputs["Base Color" if socket == "Color" else socket]      # whatever feeds the shader
        if inp.links: L.new(inp.links[0].from_socket, em.inputs["Color"])
        else: v = inp.default_value; em.inputs["Color"].default_value = tuple(v) if hasattr(v, "__len__") else (v, v, v, 1)
        L.new(em.outputs["Emission"], out.inputs["Surface"])
    set_target(img); bpy.ops.object.bake(type='EMIT')
    a = np.empty(SIZE * SIZE * 4, np.float32); img.pixels.foreach_get(a); return a.reshape(SIZE, SIZE, 4)
col = channel("Color"); met = channel("Metallic"); rough = channel("Roughness"); print("BAKE colour, metal, roughness done")
for m in mats:
    N, L = m.node_tree.nodes, m.node_tree.links
    L.new(N["vdw_bsdf"].outputs["BSDF"], next(n for n in N if n.type == 'OUTPUT_MATERIAL' and n.is_active_output).inputs["Surface"])
nimg = bpy.data.images.new("bake_normal", SIZE, SIZE, alpha=False); nimg.colorspace_settings.name = 'Non-Color'
set_target(nimg); sc.render.bake.normal_space = 'TANGENT'; bpy.ops.object.bake(type='NORMAL'); print("BAKE normal done")
nrm = np.empty(SIZE * SIZE * 4, np.float32); nimg.pixels.foreach_get(nrm); nrm = nrm.reshape(SIZE, SIZE, 4)
# edge shading: an ambient occlusion bake (the gaps between boards, where boards meet the posts, under the lid's
# overhang, round the fittings) darkens the colour, so the chest shows its depth in game light too
SHADE = float(os.environ.get("VDW_EDGE_SHADE", "0.6")); AO_DIST = float(os.environ.get("VDW_AO_DIST", "0.04"))
if SHADE > 0:
    def ao_of(dist):
        def make(N):
            ao = N.new("ShaderNodeAmbientOcclusion"); ao.samples = 16; ao.inputs["Distance"].default_value = dist; return ao.outputs["AO"]
        return bake_value(make, f"bake_ao_{dist}")[..., 0]
    aop = ao_of(AO_DIST)                                   # lid shut
    if inside.any() and lid_open(True):
        aop = np.where(inside, ao_of(AO_IN), aop); lid_open(False)
    print(f"BAKE edge shading: lid open {AO_OPEN:.0f} deg, inside {int(inside.sum())} pixels at {AO_IN * 100:.1f} cm")
    shade = 1.0 - SHADE * (1.0 - np.clip(aop, 0, 1))
    # the colour is sRGB values: shade it in linear light
    lin = np.where(col[..., :3] <= 0.04045, col[..., :3] / 12.92, ((col[..., :3] + 0.055) / 1.055) ** 2.4) * shade[..., None]
    col[..., :3] = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(np.maximum(lin, 0), 1 / 2.4) - 0.055)
    for m in mats:
        N, L = m.node_tree.nodes, m.node_tree.links
        L.new(N["vdw_bsdf"].outputs["BSDF"], next(n for n in N if n.type == 'OUTPUT_MATERIAL' and n.is_active_output).inputs["Surface"])
    print(f"BAKE edge shading: AO within {AO_DIST * 100:.0f} cm, {SHADE:.0%} at the darkest; average {shade.mean():.2f}")
# the rune line (t4): a band of marks round the outside of the top rail, glowing - an Emission map, and the albedo
# there in the glow's colour, darker
emit = None
if isinstance(T.get("glow"), tuple) and len(T["glow"]) == 3:   # a rune line's colour (a gear "glow" part is a material)
    def emit_bake(make, name):
        img = bpy.data.images.new(name, SIZE, SIZE, alpha=False, float_buffer=True); img.colorspace_settings.name = 'Non-Color'
        for m in mats:
            N, L = m.node_tree.nodes, m.node_tree.links; em = N["vdw_emit"]; out = next(n for n in N if n.type == 'OUTPUT_MATERIAL' and n.is_active_output)
            for l in list(em.inputs["Color"].links): L.remove(l)
            L.new(make(N), em.inputs["Color"]); L.new(em.outputs["Emission"], out.inputs["Surface"])
        set_target(img); bpy.ops.object.bake(type='EMIT')
        a = np.empty(SIZE * SIZE * 4, np.float32); img.pixels.foreach_get(a); return a.reshape(SIZE, SIZE, 4)[..., :3]
    def pos(N): return N.new("ShaderNodeNewGeometry").outputs["Position"]
    def true_nrm(N): return N.new("ShaderNodeNewGeometry").outputs["True Normal"]
    P = emit_bake(pos, "bake_pos"); Nn = emit_bake(true_nrm, "bake_nrm")
    # which pixels are the box's wood: a bake of 1 on the wood material, 0 elsewhere
    for i, m in enumerate(mats):
        N, L = m.node_tree.nodes, m.node_tree.links; em = N["vdw_emit"]; out = next(n for n in N if n.type == 'OUTPUT_MATERIAL' and n.is_active_output)
        for l in list(em.inputs["Color"].links): L.remove(l)
        em.inputs["Color"].default_value = (1, 1, 1, 1) if i == 0 else (0, 0, 0, 1); L.new(em.outputs["Emission"], out.inputs["Surface"])
    wimg = bpy.data.images.new("bake_woodmask", SIZE, SIZE, alpha=False); wimg.colorspace_settings.name = 'Non-Color'
    set_target(wimg); bpy.ops.object.bake(type='EMIT')
    wa = np.empty(SIZE * SIZE * 4, np.float32); wimg.pixels.foreach_get(wa); wood_px = wa.reshape(SIZE, SIZE, 4)[..., 0] > 0.5
    rail_hi = float(os.environ.get("VDW_RUNE_Z1", "0.170")); rail_lo = float(os.environ.get("VDW_RUNE_Z0", "0.157"))
    side = (np.abs(Nn[..., 2]) < 0.3) & ((P[..., 0] * Nn[..., 0] + P[..., 1] * Nn[..., 1]) > 0)   # outward walls
    band = wood_px & side & (P[..., 2] > rail_lo) & (P[..., 2] < rail_hi)
    along = np.where(np.abs(Nn[..., 0]) > 0.5, P[..., 1], P[..., 0])                              # along each wall
    runes = band & (np.sin(along * 420) > -0.15) & (np.sin(along * 37 + P[..., 2] * 900) > -0.6)
    emit = np.zeros_like(col); emit[..., 3] = 1.0; emit[runes, :3] = T["glow"]
    col[runes, :3] = np.array(T["glow"]) * 0.5
    for m in mats:
        N, L = m.node_tree.nodes, m.node_tree.links
        L.new(N["vdw_bsdf"].outputs["BSDF"], next(n for n in N if n.type == 'OUTPUT_MATERIAL' and n.is_active_output).inputs["Surface"])
    print(f"BAKE rune line: {int(runes.sum())} pixels on the top rail")
# charred wood (the Ashlands box): its cracks and grain lines glowing where the node "vdw_char_glow" says
if T.get("char"):
    def char_glow(N):
        if "vdw_char_glow" in N: return N["vdw_char_glow"].outputs[0]
        v = N.new("ShaderNodeValue"); v.outputs[0].default_value = 0.0; return v.outputs[0]
    gm = np.clip(bake_value(char_glow, "bake_char_glow")[..., :1], 0, 1)
    if emit is None: emit = np.zeros_like(col); emit[..., 3] = 1.0
    emit[..., :3] = np.maximum(emit[..., :3], gm * np.array(T["char"]["glow"]))
    for m in mats:
        N, L = m.node_tree.nodes, m.node_tree.links
        L.new(N["vdw_bsdf"].outputs["BSDF"], next(n for n in N if n.type == 'OUTPUT_MATERIAL' and n.is_active_output).inputs["Surface"])
    print(f"BAKE charred wood glowing: {int((gm[..., 0] > 0.3).sum())} pixels")
# parts that glow (the mistlands box's eitr rivets): an Emission map there, the albedo in the glow's colour
for slot, glow in T.get("glow_slots", {}).items():
    if slot not in SLOTS: continue
    si = SLOTS.index(slot)
    for i, m in enumerate(mats):
        N, L = m.node_tree.nodes, m.node_tree.links; em = N["vdw_emit"]; out = next(n for n in N if n.type == 'OUTPUT_MATERIAL' and n.is_active_output)
        for l in list(em.inputs["Color"].links): L.remove(l)
        em.inputs["Color"].default_value = (1, 1, 1, 1) if i == si else (0, 0, 0, 1); L.new(em.outputs["Emission"], out.inputs["Surface"])
    gimg = bpy.data.images.new("bake_glowmask", SIZE, SIZE, alpha=False); gimg.colorspace_settings.name = 'Non-Color'
    set_target(gimg); bpy.ops.object.bake(type='EMIT')
    ga = np.empty(SIZE * SIZE * 4, np.float32); gimg.pixels.foreach_get(ga); gpx = ga.reshape(SIZE, SIZE, 4)[..., 0] > 0.5
    if emit is None: emit = np.zeros_like(col); emit[..., 3] = 1.0
    emit[gpx, :3] = glow
    if not T.get("glow_keep_albedo"): col[gpx, :3] = np.array(glow) * 0.6   # (baits keep their texture under the glow: a flat colour lost the gland's detail)
    for m in mats:
        N, L = m.node_tree.nodes, m.node_tree.links
        L.new(N["vdw_bsdf"].outputs["BSDF"], next(n for n in N if n.type == 'OUTPUT_MATERIAL' and n.is_active_output).inputs["Surface"])
    print(f"BAKE {slot} glowing: {int(gpx.sum())} pixels")
def save(arr, name, nc):
    im = bpy.data.images.new(name, SIZE, SIZE, alpha=True)
    if nc: im.colorspace_settings.name = 'Non-Color'
    im.pixels.foreach_set(np.ascontiguousarray(arr, np.float32).ravel()); im.filepath_raw = os.path.join(TEXDIR, name); im.file_format = 'PNG'; im.save()
    print("  saved", im.filepath_raw)
save(col, f"{PREFIX}_{TIER}_Unity_Albedo.png", False)
if emit is not None: save(emit, f"{PREFIX}_{TIER}_Unity_Emission.png", False)
ms = np.zeros_like(col); ms[..., :3] = met[..., :1]; ms[..., 3] = 1.0 - rough[..., 0]
save(ms, f"{PREFIX}_{TIER}_Unity_MetallicSmoothness.png", True)
nrm[..., 3] = 1.0; save(nrm, f"{PREFIX}_{TIER}_Unity_Normal.png", True)
if "Armature" in box.modifiers: box.modifiers["Armature"].show_render = True
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f"{PREFIX}_{TIER}_baked.blend"), copy=True)
print("===== END =====")
