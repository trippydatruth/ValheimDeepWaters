MISS2
# Valheim: Deep Waters

A fishing overhaul for Valheim. Fish swim up to your bait, nibble and then bite, and you play the fight with
line tension, drag and stamina. There are rods for every era, hook sizes, bait you gather from the world,
buffs, trophies and a catch log.

Requires BepInEx 5 and Jötunn 2.30 or newer. Built for Valheim 1.0.16.

## Features

- All 12 vanilla fish plus 24 new ones, including 9 legendaries, each with its own biomes, depth,
  favourite bait, time of day and weather
- Fish you can see swim up to your bait, nibble the float, then bite. Strike too early and you spook them;
  make noise and they flee
- A real fight: line tension, drag on the mouse wheel, sideways runs, leaps and snapped lines
- Nine rods, one for each era, that wear out with use, and hooks in six sizes
- Bait from the world: worms, grubs, flies, leeches and baitfish
- Tackle slots for your bait and hook under the inventory
- Lures you cast far and retrieve (spoons, spinners, crankbaits, jigs, soft baits, swimbaits, poppers and flies),
  with trailers, and six boss lures
- A Fishing Boat you row, with a passenger seat and a bow holdfast
- Fishing meads, gear, chum, totems and rare relics
- Size classes, a trophy mount, cooking, selling, a catch log with rewards, and Valheim's Fishing skill

## How to fish

1. Craft a **Wooden Fishing Rod** (workbench) and some **Tiny hooks**, and dig up worms from wriggling soil
   in the forest.
2. Put bait and a hook in your **tackle slots** under the inventory (or right-click them there).
3. Face the water, **hold left click** to charge, and release to cast.
4. Fish come to the bait and **nibble** the float with small dips. Don't strike yet.
5. On the real bite (**FISH ON!**, a big dip), **right click** to set the hook.
6. **Hold right click** to reel and use the **mouse wheel** to set the drag. Tighter drag reels faster and
   tires the fish quicker, but risks snapping the line. Reeling costs stamina.

Bait is only used up once a fish is hooked.

| Action | Input |
|---|---|
| Cast | Hold and release left click |
| Set the hook | Right click on the bite |
| Reel in early | Right click while waiting |
| Reel | Hold right click |
| Drag | Mouse wheel |
| Next bait / next hook | `B` / `H` |
| Catch log | `J` |

## Rods

Each rod is better than the last. Every rod lists its stats in its tooltip: cast distance, line, line
strength, reel speed, power, hook bonus, stamina use and durability.

| Rod | Station | Materials |
|---|---|---|
| Wooden | Workbench 1 | Wood 10, Leather scraps 4 |
| Copper | Forge 1 | Wood 6, Copper 5, Deer hide 2 |
| Finewood | Forge 2 | Fine wood 10, Bronze 4, Troll hide 2 |
| Ancient Bark | Forge 2 | Ancient bark 10, Iron 4, Guck 3 |
| Silver | Forge 3 | Fine wood 6, Silver 6, Wolf pelt 2 |
| Black Metal | Forge 5 | Fine wood 6, Black metal 6, Linen thread 6 |
| Yggdrasil | Black forge 1 | Yggdrasil wood 10, Carapace 4, Eitr 2 |
| Ashwood | Black forge 2 | Blackwood 10, Flametal 4, Asksvin hide 2 |
| Leviathan | Black forge 2 | One material from each of the six boss fish, Yggdrasil wood 10, Flametal 6 |
| Haldor's Gilded Rod | Haldor only | 6000 coins |

Rods wear while a fish is on the line, faster with heavy fish and high tension. A broken rod loses the fish
and must be repaired where it was crafted.

## Hooks

You need a hook to cast, and each size suits a range of fish weights.

| Hook | Suits | Station | Recipe (makes) |
|---|---|---|---|
| Tiny #12 | 0–1.5 kg | Workbench 1 | Flint 1, Resin 1 (5) |
| Small #6 | 0.5–5 kg | Forge 1 | Copper 1 (5) |
| Medium #2 | 2–15 kg | Forge 1 | Bronze 1 (5) |
| Large 2/0 | 8–40 kg | Forge 2 | Iron 1 (4) |
| Heavy 5/0 | 25–100 kg | Forge 3 | Iron 1, Silver 1 (3) |
| Giant 8/0 | 60–250 kg | Forge 5 | Black metal 2 (3) |

- **Too big for the fish:** much harder to hook.
- **Too small:** a big fish can straighten it mid-fight, and a fish far too big won't bite at all.

You lose the hook if the line snaps, the rod breaks or the hook straightens.

## Vanilla fish

All 12 vanilla fish can be caught with Deep Waters rods: Perch, Pike, Tuna, Tetra, Trollfish, Giant Herring,
Grouper, Coral Cod, Pufferfish, Anglerfish, Northern Salmon and Magmafish. They live where vanilla spawns
them, and landing one gives the normal vanilla item, so vanilla cooking, recipes and food all work. They
also get a weight and size class, plus any extra drops vanilla gives. They bite Deep Waters bait like every other
fish. The vanilla fishing rod and vanilla fishing baits are taken out of the game: no one sells them and
they can't be crafted.

## Deep Waters fish

24 new fish to catch and eat, plus 3 bait fish. Weights are each species' maximum. Ocean and deep-ocean fish
bite in any sea; fresh-water fish only in their biomes.

**Fresh water**

| Fish | Water | Biomes | Max |
|---|---|---|---|
| Greydwarf Goby | Lake | Black Forest | 1.5 kg |
| Dvergr Dace | River | Mistlands | 1 kg |
| Trout | River | Meadows, Black Forest, Mountain | 4 kg |
| Frost Char | Lake | Mountain, Deep North | 6 kg |
| Mistfin | Lake | Swamp, Mistlands | 12 kg |

**Ocean**

| Fish | Max |
|---|---|
| Surtling Sardine | 2 kg |
| Mackerel | 3 kg |
| Serpentfin | 28 kg |

**Deep ocean** (15 m of water or more)

| Fish | Max |
|---|---|
| Lingcod | 25 kg |
| Halibut | 45 kg |
| Jotunn Perch | 55 kg |
| Bonemaw | 70 kg |

**Legendary** (rare, and they fight hard)

| Fish | Water | Max |
|---|---|---|
| Eikthyr Elver | Meadows river | 12 kg |
| Elder Bass | Black Forest lake | 60 kg |
| Bonemass Catfish | Swamp lake | 85 kg |
| Fenringfin | Ocean | 35 kg |
| Thor's Hammerhead | Ocean | 140 kg |
| Odin's Eye | Deep ocean | 25 kg |
| Queen Eel | Deep ocean | 50 kg |
| Yagluth Gill | Deep ocean | 100 kg |
| Moder Scale Fish | Deep ocean | 180 kg |

**Bait fish** (land as bait instead of food; use a Tiny hook)

| Fish | Water | Gives |
|---|---|---|
| Minnow | River | Live Minnow |
| Baitfish | Any | Large Live Baitfish |
| Sea Shrimp | Ocean | Shrimp Bait |

## Boss fish

Six legendaries are named after Valheim's bosses, and they're boss fights. They never bite by chance: you
summon one with a **lure** carved from that boss's trophy (workbench), cast in the right water at the right time.

| Boss fish | Lure | Where | When |
|---|---|---|---|
| Eikthyr Elver | Antler Lure (Eikthyr trophy) | Meadows river | Thunderstorm |
| Elder Bass | Root Lure (The Elder trophy) | Black Forest lake | Night |
| Bonemass Catfish | Ooze Lure (Bonemass trophy) | Swamp water | Rain |
| Moder Scale Fish | Wyrm Lure (Moder trophy) | Sea off the Deep North | Storm or snow |
| Yagluth Gill | Ember Lure (Yagluth trophy) | Deep sea off the Plains | Night |
| Queen Eel | Chitin Lure (The Queen trophy) | Deep sea off the Mistlands | Any time |

Cast the lure in the right place and an **omen** begins: the water goes still, a dark swirl spreads around the
float, a sign appears, bubbles rise and the float shudders - then it strikes. You get twice the usual time to
set the hook. Reeling in during the omen calls it off and keeps the lure; it's only used up once the fish is
hooked. In the wrong place nothing answers, and you're told where it hunts.

The fight brings up a **boss bar** with its name - its stamina, which drains faster the harder you fight it
(tight drag, high tension) and recovers if you give it slack, so no two fights are alike. It plays its boss's
**music** and goes through **phases**: at two thirds it's enraged (pulls harder, leaps more), at one third
desperate (dives that tear line off the reel). An empty bar means it's beaten; then reel it in. Landing one
drops its **trophy** the first time, a **boss material** every time, sometimes a **relic** (Pearl of Njord,
Jörmungandr's Scale or the Golden Hook), and tells the whole server. One material
from each of the six strings the **Leviathan Rod** (black forge), the best rod there is.

Fenringfin, Thor's Hammerhead and Odin's Eye are **mini-bosses**: they still bite by luck and fight the same
way (phases and all), with no bar, music or messages, and drop their trophy the first time.

## Bait

| Bait | Where to get it |
|---|---|
| Worms | Dig up **wriggling soil** in forests where red mushrooms grow (it regrows), usually 1 worm and sometimes 2 or 3. When it rains, worms come up out of the ground around you |
| Grubs | Sometimes found when you chop up a log |
| Flies | Swarms along rivers, lakes and the coast in dry weather (fireflies at night); walk up and use one to catch it |
| Leeches | Dropped by swamp leeches |
| Minnows, Large Baitfish, Shrimp | Catch them as small fish with worms, grubs or flies on a Tiny hook |
| Abyssal, Frost and Runed bait | Crafted at the cauldron or forge |

Wriggling soil only grows in parts of the world generated after installing the mod.

## Lures and trailers

A **lure** goes in the hook slot and needs no hook or bait. The bait slot then takes an optional **trailer**. With a
lure there's no float: cast it further than bait, then **hold right click to retrieve it**. Fish only strike while
the lure is moving, so keep it coming with pauses; a lure left sitting draws nothing. Each kind of lure draws its own
fish and mostly gets ignored by the rest.

| Lure | Kind | Fish | Made at |
|---|---|---|---|
| Feather Fly | Fly | Trout, char, dace (0.05–3 kg) | Workbench |
| Flint Spinner | Spinner, takes a trailer | Perch, trout, pike (0.1–4 kg) | Workbench |
| Leather Grub | Soft bait | Perch, trout, gobies (0.1–5 kg) | Workbench 2 |
| Bronze Spoon | Spoon | Pike, trout, salmon, mackerel (0.3–10 kg) | Forge |
| Finewood Crankbait | Crankbait | Pike, perch, trollfish (0.5–12 kg) | Workbench 3 |
| Guck Crawler | Texas rig | Trollfish, pike, mistfin (0.5–15 kg) | Workbench 3 |
| Bone Jig | Jig, takes a trailer | Lingcod, halibut, grouper (1–30 kg) | Forge 2 |
| Silver Swimbait | Swimbait | Big pike, tuna, grouper, halibut (2–40 kg) | Forge 3 |
| Linen Popper | Topwater | Pike, trollfish, mackerel (0.5–20 kg) | Workbench 4 |

A **trailer** (Curly Tail, Boar Rind, Feather Skirt) brings fish of its own and makes the lure's fish keener.
Lures and trailers are only used up when a fish is hooked. The boss lures work the same way, but only their boss
answers them.

## Fishing Boat

A small rowing boat built with the hammer at a workbench (24 wood, 8 resin, 4 deer hide). Use the bench to row
(forward and back only; it has no sail, so the wind doesn't move it). It has a passenger seat at the stern, a
holdfast in the bow to stand braced in rough water, and a ladder on the side to climb in from the water. Fish you
land while aboard any ship go straight into your inventory.

## Tackle slots

Two slots under your inventory hold your bait and hook. To fill them, drag items in, or right-click or Ctrl+click them in your
inventory (Ctrl+click a slot to take it back out). While holding the rod, `B` / `H` swaps in the next bait or hook you're carrying. A slot
refills from your inventory when it runs out. Tackle is saved with your character and goes into your
tombstone when you die.

## Fishing buffs

Tiered items that unlock as you progress:

- **Meads** (cauldron): Angler's Mead (faster bites), Steady-Hand Tonic (easier hookset), Troll-Grip Mead
  (reel speed and stamina).
- **Rune of Njord** (forge, worn as a belt): bigger fish, more legendaries.
- **Chum** (cauldron): set the bucket down on the bank to draw more, less picky fish to the water around it for
  5 minutes, for anyone fishing there.
- **Totems** (hammer): the Fisherman's Totem and Shrine of Njord buff anyone fishing nearby.
- **Relics** (can't be crafted): the **Horn of Ægir** is very rarely found inside a landed fish (more often in
  legendaries, never in bait fish). The **Pearl of Njord**, **Jörmungandr's Scale** and the **Golden Hook** are
  only left behind by boss fish: each boss you land has a 1 in 4 chance of one, one you don't have yet first.

## Your catch

- **Size class:** each fish is Small, Medium, Large or Trophy, with its weight and catcher in the tooltip.
- **Trophy Mount** (hammer: fine wood, resin): hang a fish on the wall.
- **Cook and sell:** cook fish on a cooking station or sell them to Haldor.
- **Catch log** (`J`): records every species you catch. New species earn rewards at 5, 10, 15 and 20
  species and for catching them all.
- **Fishing skill:** Valheim's Fishing skill rises as you reel and land fish. It makes reeling cheaper and
  faster and setting the hook easier.

## Settings

The config is `BepInEx/config/trippy.valheimdeepwaters.cfg`.

| Setting | Default | |
|---|---|---|
| Show Fishing HUD / HUD Scale | on / 0.85 | The bait, tension, line and drag display |
| Reel Sound Volume | 0.5 | |
| Rod Wear | 1 | 0 = rods never wear out |
| Spawn Swimming Fish / Swimming Fish Density | on / 1 | Deep Waters fish in the world |
| Spawn Worm Mounds / Worm Mound Density | on / 0.5 | Compared to red mushrooms; new areas only |
| Rain Worms | on | |
| Spawn Flies | on | |
| Cycle Bait / Cycle Hook / Catch Log keys | B / H / J | |

## Console commands

These need `devcommands`.

- `vdw_give <item> [amount]`: spawns an item, for example `rod_copper`, `hook_small`, `buff_angler_minor`,
  `worm` or a fish id.
- `vdw_debug listrods | listhooks | listbait | listfish | listbuffs`: lists the ids.
- `vdw_debug worms`: shows the worm mounds near you and whether flies or rain worms can appear right now.
- `vdw_debug bite`: the next cast bites straight away.
- `vdw_debug boss <fish id>`: the next cast summons that boss fish anywhere, with any bait (for testing).
- `vdw_debug horn`: rests the Horn of Ægir so it can be blown again straight away.
- `vdw_debug boatseat <rower|passenger|holdfast> <right> <up> <forward> [turn]`: moves a Fishing Boat seat (metres,
  degrees) to fit it by eye; prints the running total.
- `vdw_debug resetlog`: clears your catch log.
- `vdw_debug tokens`: exports the text for translating.

## Customising

### Fish, bait, rods, hooks and buffs

These are defined in `Fish.json`, `Baits.json`, `Rods.json`, `Hooks.json` and `Buffs.json` in
`BepInEx/config/ValheimDeepWaters/`. They're created on first run, and your edits are never overwritten. When
an update adds new fish, bait, rods, hooks or buffs, they're added to your files automatically (each one only
once, so an entry you delete stays deleted). Delete a whole file to get its defaults back.

### Custom models

Put model files in `BepInEx/config/ValheimDeepWaters/Models/`:

| Name | Model for |
|---|---|
| `rod` or `rod_<id>` | Rods (one shared model, or one per rod) |
| `bobber` | The float |
| `bait_<id>` / `hook_<id>` / `fish_<id>` | That item (fish models also swim in the world) |
| `pickable_worm` | Wriggling soil |
| `fly` | Flies (without one, Valheim's own flies effect is used) |

The mod looks for each model in this order:
1. `<name>.bundle`
2. A prefab called `<name>` inside any `.bundle` in the folder, so all your baits can share one bundle
3. `<name>.obj` with an optional `<name>.png` texture

Build bundles with Unity 6000.0 and turn on **Read/Write** for the model.

Sizing: every model is used at **exactly its size in Unity** - 1 unit = 1 metre, the mesh times every transform
in its prefab (the root included). Nothing is resized, so build each model at the size you want it in game:
model in metres in Blender (Metric, Unit Scale 1), apply all transforms, export FBX with Apply Scalings "FBX
All", -Z Forward, Y Up and Apply Transform, and import in Unity with Scale Factor 1 and Convert Units on. Face
models forward along +Z. The log shows each model's final size (`final size (x, y, z)`, in metres).

Icons:
- A `<name>_icon.png` in the folder becomes that item's icon.
- Otherwise the icon is rendered from the model.

### Animated fish

A fish model can be rigged and animated instead of static. Make it a prefab in a bundle, like any other
model, with:

- a **skinned mesh** (an armature: a spine chain of 4-6 bones from head to tail, plus fins if you like),
  modelled at real size and facing forward along +Z
- an **Animator** (Rig: Generic) whose controller has states named **`Swim`** (default, looping), **`Thrash`**
  (looping) and optionally **`Flop`**, and optionally a float parameter **`Speed`** that scales them. A legacy
  `Animation` component with clips of those names works too.

The mod then uses the whole prefab: it swims in the world (faster as it moves), darts at your bait when it
nibbles, thrashes when it runs and leaps on the line and swims slowly when it rests, flops when dropped on land,
and holds still as a trophy. Missing clips fall back to `Swim`, and static models keep working as before, so
fish can be animated one at a time. Model it at its real size: it is used exactly as big as it is in Unity.

### Rigged rods

A rod model can have a skeleton so it bends and its reel turns. Make it a prefab in `rod.bundle` (or
`rod_<id>.bundle`) with a **skinned mesh** and these bones (any you leave out just don't move):

- **`Rod.1` .. `Rod.N`**: a chain up the blank from just above the reel to the tip. Most of the bend goes to the
  top segments, like a real blank.
- **`Rod.Tip`**: where the line leaves the rod. The line follows it as the rod bends.
- **`Rod.BendDir`**: a marker beside the tip, on the side the rod bends toward (the guide side).
- **`Reel.Spool`**: the part of the reel that turns (the crank and drum), and **`Reel.Axis`**, a marker along its
  axle.

No Animator is needed: the mod poses the bones itself. The rod bends toward the line, harder as a fish pulls
toward the breaking point. It flexes back as you wind up a cast, whips forward on release and springs back when
the line snaps. The reel winds in while you reel and spins backward as line pays out.

### Translations

Run `vdw_debug tokens`, translate the file it writes, and save it as
`BepInEx/plugins/ValheimDeepWaters/Translations/<Language>/vdw.json`.

## Multiplayer

Every player needs the mod, the same version as the server (the game checks when you join).
- **Server rules:** the gameplay settings (marked "Set by the server" in the config) come from the server, so
  everyone plays by the same rules. HUD, sound and keys stay each player's own.
- **Shared:** caught fish, worm mounds, totems and trophy mounts are normal world objects that everyone sees.
- **Per player:** the fight, the bobber, flies and rain worms only show for the player who has them.

## Building from source

```
dotnet build -c Release
```

The project expects Valheim at `D:\SteamLibrary\steamapps\common\Valheim`; pass `-p:ValheimDir=...` if
yours is elsewhere. `build.ps1` builds the mod and also copies it into your BepInEx plugins folder.
`package.ps1` builds the Thunderstore package into `dist`: the DLL, the models and icons, the manifest and
icon from `thunderstore`, and this README and the CHANGELOG.
