# Valheim: Deep Waters

A fishing overhaul for Valheim. Fish swim up to your bait, nibble and then bite, and you play the fight with
line tension, drag and stamina. There are rods for every era, hook sizes, bait you gather from the world,
buffs, trophies and a catch log.

Requires BepInEx 5 and Jötunn 2.30 or newer. Built for Valheim 1.0.20.

## Features

- All 12 vanilla fish plus 31 new ones, including 10 legendaries, each with its own biomes, depth,
  favourite bait, time of day and weather
- Fish you can see swim up to your bait, nibble the float, then bite. Strike too early and you spook them;
  make noise and they flee
- A real fight: line tension, drag on the mouse wheel, sideways runs, leaps and snapped lines
- Twelve rods, one for each era plus special ones, that wear out with use and upgrade to level 4, and hooks in eight kinds
- Bait from the world: worms, grubs, flies, leeches and baitfish
- Tackle slots for your bait and hook under the inventory
- Lures you cast far and retrieve (spoons, spinners, crankbaits, jigs, soft baits, swimbaits, poppers and flies),
  with trailers, and seven boss lures
- A Fishing Boat you row, with a passenger seat and a bow holdfast
- Fishing meads, chum, totems, rare relics and a Fisherman's armour set
- Seven boss fish you summon with boss lures, each with its own weather, music and fight
- Angler ranks, species mastery with Gold Trophy Plaques, and rare golden and albino catches
- A Fish Cleaning Table, fish materials, dishes and feasts, and traders who each buy their own catch
- An endgame: the Allfather's Rod and Njord's Regalia, earned by landing every boss fish
- Size classes, a trophy mount, cooking, selling, a catch log with rewards, and Valheim's Fishing skill
- In multiplayer, players nearby see your line, the fish you're fighting and the catch

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
| Drag | Mouse wheel (configurable) |
| Reel speed | Alt + mouse wheel (configurable; Shift: full speed) |
| Twitch a lure | Left click while retrieving |
| Pull back on a fish | Hold left click |
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
| Frostwood | Black forge 3 | Timberwood 10, Frostcore 3, Moose sinew 4 |
| Leviathan | Black forge 2 | Two materials from each of the seven boss fish, Yggdrasil wood 10, Flametal 6 |
| Allfather's Rod | Black forge 3 | The Leviathan Rod and three materials from each boss fish; shows once you've landed every boss fish |
| Haldor's Gilded Rod | Haldor only | 6000 coins |

Rods wear while a fish is on the line, faster with heavy fish and high tension. A broken rod loses the fish
and must be repaired where it was crafted.

### Upgrading rods

Every rod upgrades to level 4 at its crafting station, like vanilla gear. Each level adds cast distance, line,
line strength, reel speed, power, hook bonus and durability, and eases reeling stamina; a fully upgraded rod sits
about halfway to the next one. Upgrades cost fish materials (see below), the line of the rod's era (leather
scraps, deer hide, linen, jute, morgen sinew, moose sinew) and some of each biome's oddments: greydwarf eyes,
obsidian, tar, deathsquito needles, sap, charred bone, celestial feathers. The last level also needs a
**Trophy Fin**. The tooltip shows the rod's stats at its level.

## Fish materials

Clean a catch at the **Fish Cleaning Table** for its material. Bigger fish give more: a Trophy-size fish gives four
times what a Small one does. The table (hammer, near a workbench: 10 wood, 4 flint, 4 resin) cleans the common fish;
its three add-ons, built beside it, let it handle the rarer ones:

| Level | Add-on | Cleans for | Prepares | Cost |
|---|---|---|---|---|
| 1 | Fish Cleaning Table | Fish Scales, Fish Oil | | 10 wood, 4 flint, 4 resin |
| 2 | Filleting Knife Rack | Spiny Fins, Fish Roe | Fish Fillets (from any fish) | 4 fine wood, 2 bronze, 10 Fish Scales |
| 3 | Brining Barrel | Abyssal Ink, Legendary Scales | Brined Roe (3 roe, 1 oil) | 6 fine wood, 2 iron, 10 Fish Oil |
| 4 | Drying Line | Cinder Scales, Rime Scales | Dried Fish (3 fillets) | 6 fine wood, 3 red jute, 10 Abyssal Ink |

Cleaning fish raises your Fishing skill.

The materials go into rod upgrades, every lure (the boss lures take three of their biome's material), the crafted
baits, the meads, chum, the Rune of Njord and the totems.

### Fish dishes

Made from the cleaning table's prepared ingredients at Valheim's own food stations:

| Dish | Where | Ingredients | Health / Stamina / Eitr |
|---|---|---|---|
| Grilled Fish Fillet | Cooking station | A Fish Fillet | 25 / 22 |
| Fisherman's Stew | Cauldron 1 | Fish Fillets, Fish Oil, 2 carrots | 35 / 40 |
| Spiny Fin Soup | Cauldron 2 | Fish Fillets, 2 Spiny Fins, 2 onions | 50 / 45 |
| Roe Flatbread | Cauldron 3 | Bread, 2 Brined Roe, 2 cloudberries | 40 / 75 |
| Ink-Black Noodles | Cauldron 4 | Fish Fillets, Abyssal Ink, 2 jotun puffs | 45 / 30 / 75 |
| Ember-Grilled Fillet | Cauldron 5 | 2 Fish Fillets, Cinder Scales, 2 vineberries | 85 / 50 |
| Rime-Cured Salmon | Food preparation table | 2 Fish Fillets, Rime Scales, 2 lingonberries | 80 / 70 / 30 |
| Fisherman's Rations | Food preparation table | 2 Dried Fish, 2 cloudberries, honey | 35 / 35, lasts an hour |

| Material | From |
|---|---|
| Fish Scales | Perch, Bluegill, Trout, Largemouth Bass, Greydwarf Goby, Pike |
| Fish Oil | Trollfish, Channel Catfish, Mackerel, Sea Bass, Giant Herring, Surtling Sardine |
| Spiny Fins | Tetra, Frost Char, Coral Cod, Pufferfish, Serpentfin |
| Fish Roe | Tuna, Grouper, Halibut, Lingcod |
| Abyssal Ink | Anglerfish, Mistfin, Bonemaw, Jotunn Perch |
| Cinder Scales | Magmafish |
| Rime Scales | Northern Salmon, Rimejaw Cod, Glacier Grayling, Frost Sculpin |
| Legendary Scale | Any legendary or boss fish |

Landing a **Trophy-size** fish of any kind also gives a **Trophy Fin**.

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
| Fimbul 12/0 | 25–300 kg, never bends, kept half the time the line breaks | Forge 5 | Rimefrost Fin 1, Silver 2 (1) |
| Golden 10/0 | Any fish (0–300 kg), never bends, kept three times in four when the line breaks, +5% hook chance and +15% hook window | Can't be crafted | A relic: very rarely inside a legendary fish |

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

28 new fish to catch and eat, plus 3 bait fish. Weights are each species' maximum. Ocean and deep-ocean fish
bite in any sea; fresh-water fish only in their biomes.

**Fresh water**

| Fish | Water | Biomes | Max |
|---|---|---|---|
| Bluegill | Lake | Meadows | 0.6 kg |
| Greydwarf Goby | Lake | Black Forest | 1.5 kg |
| Trout | River | Meadows, Black Forest, Mountain | 4 kg |
| Largemouth Bass | Lake | Meadows, Black Forest | 5 kg |
| Frost Char | Lake | Mountain, Deep North | 6 kg |
| Mistfin | Lake | Swamp, Mistlands | 12 kg |
| Channel Catfish | Lake, river | Black Forest, Swamp | 20 kg |
| Glacier Grayling | River | Deep North | 3 kg |
| Frost Sculpin | Lake | Deep North | 4 kg |

**Ocean**

| Fish | Max |
|---|---|
| Surtling Sardine | 2 kg |
| Mackerel | 3 kg |
| Sea Bass | 9 kg |
| Serpentfin | 28 kg |
| Rimejaw Cod (Deep North coasts and deep lakes) | 18 kg |

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
| Fimbul Salmon | Deep North river | 250 kg |

**Bait fish** (land as bait instead of food; use a Tiny hook)

| Fish | Water | Gives |
|---|---|---|
| Minnow | River | Live Minnow |
| Baitfish | Any | Large Live Baitfish |
| Sea Shrimp | Ocean | Shrimp Bait |

## Boss fish

Seven legendaries are named after Valheim's bosses, and they're boss fights. They never bite by chance: you
summon one with a **lure** carved from that boss's trophy (or, for Kall Fimbulbringer, his Crown Jewel), cast in the
right water at the right time.

| Boss fish | Lure | Where | When |
|---|---|---|---|
| Eikthyr Elver | Antler Lure (Eikthyr trophy) | Meadows river | Thunderstorm |
| Elder Bass | Root Lure (The Elder trophy) | Black Forest lake | Night |
| Bonemass Catfish | Ooze Lure (Bonemass trophy) | Swamp water | Rain |
| Moder Scale Fish | Wyrm Lure (Moder trophy) | Sea off the Deep North | Storm or snow |
| Yagluth Gill | Ember Lure (Yagluth trophy) | Deep sea off the Plains | Night |
| Queen Eel | Chitin Lure (The Queen trophy) | Deep sea off the Mistlands | Any time |
| Fimbul Salmon | Crown Lure (Kall Fimbulbringer's Crown Jewel, black forge) | Deep North river or lake | Night |

Cast the lure in the right place and an **omen** begins: the water goes still, a dark swirl spreads around the
float, a sign appears, bubbles rise and the float shudders - then it strikes. You get twice the usual time to
set the hook. Reeling in during the omen calls it off and keeps the lure; it's only used up once the fish is
hooked. In the wrong place nothing answers, and you're told where it hunts.

From the omen to the end of the fight the boss brings **its namesake boss's weather** - Eikthyr's storm, the
Elder's mist, Bonemass's rot, Moder's blizzard, Yagluth's embers, the Queen's gloom. Everyone within about 150 m
sees it and hears the boss music, so friends can come and watch.

The **Queen Eel** fights like a sea serpent: a 7.5 m monster that circles you, its back humping through the waves;
once enraged it charges straight at you - reel hard to keep the line tight - and rears out of the water before
crashing down. Pull back while it's reared up: that's when it tires fastest.

The fight brings up a **boss bar** with its name - its stamina, which drains faster the harder you fight it
(tight drag, high tension) and recovers if you give it slack, so no two fights are alike. It plays its boss's
**music** and goes through **phases**: at two thirds it's enraged (pulls harder, leaps more), at one third
desperate (dives that tear line off the reel). An empty bar means it's beaten; then reel it in. Landing one
drops its **trophy** the first time and a **boss material** every time, and tells the whole server. Two materials
from each of the seven string the **Leviathan Rod** (black forge).

**The endgame:**
- **Boss lures cost more each time** you land their boss: every ingredient but the boss part needs one more per
  landing, up to three times the first cost, and the Bog Witch's price rises the same way. It's per character.
- **Allfather's Rod:** once you've landed every boss fish, remake the Leviathan Rod with three materials from each -
  the best rod there is.
- **Njord's Regalia:** once you've landed every boss fish three times, set the Pearl, the Scale, the Horn and the
  Golden Hook in one crown (they're used up), with two materials from each boss: every relic's blessing in one helm.
- The catch log's sidebar shows how many boss fish you've landed and what the next unlock needs.

Fenringfin, Thor's Hammerhead and Odin's Eye are **mini-bosses**: they still bite by luck and fight the same
way (phases and all), with no bar, music or messages, and drop their trophy the first time.

## Bait

| Bait | Where to get it |
|---|---|
| Worms | Dig up **wriggling soil** in forests where red mushrooms grow (it regrows), usually 1 worm and sometimes 2 or 3. When it rains, worms come up out of the ground around you |
| Grubs | Sometimes found when you chop up a log |
| Flies | Swarms along rivers, lakes and the coast in dry weather (fireflies at night); walk up and use one to catch it |
| Leeches | Dropped by swamp leeches |
| Minnows, Large Baitfish, Shrimp, Live Bluegill | Catch them as small fish with worms, grubs or flies on a Tiny hook; they swim in schools where they live (bluegill in Meadows lakes, on worms and grubs) |
| Abyssal, Frost and Runed bait | Crafted at the cauldron or forge |
| Northern Bait | Crafted at the cauldron (seal blubber and lingonberries); the Deep North's fish want it |

Wriggling soil only grows in parts of the world generated after installing the mod.

Each bait goes for a few fish, so pick it for the fish you're after; anything else takes it only now and then. A bait's
tooltip lists what it catches (species you haven't caught show as ???), the catch log shows each species' bait, and a
cast tells you when nothing in that water goes for yours. You need bait (or a lure) to cast.

| Bait | Catches |
|---|---|
| Worm | Perch, Bluegill, Greydwarf Goby, Catfish |
| Grub | Trout, Bass, Perch, Bluegill |
| Fly | Trout, Frost Char, Glacier Grayling, Tetra |
| Minnow | Pike, Bass, Mackerel, Sea Bass |
| Large Baitfish | Tuna, Lingcod, Serpentfin, Grouper |
| Live Bluegill | Catfish, Bass, Pike |
| Leech | Catfish, Mistfin, Trollfish, Pike |
| Stinkbait | Catfish, Trollfish, Mistfin |
| Shrimp | Coral Cod, Herring, Pufferfish, Sea Bass, Halibut |
| Abyssal Bait | Anglerfish, Bonemaw, Jotunn Perch, Magmafish, Halibut |
| Frost Bait | Tetra, Frost Char, Salmon, Fenringfin |
| Northern Bait | Salmon, Rimejaw Cod, Glacier Grayling, Frost Sculpin |
| Runed Bait | Odin's Eye, Thor's Hammerhead, Moder Scale Fish, Yagluth Gill, Fenringfin |

Deep Waters replaces vanilla fishing: the vanilla rod and baits aren't sold or crafted, and the vanilla rod can't be used.

## Lures and trailers

A **lure** goes in the hook slot and needs no hook or bait. The bait slot then takes an optional **trailer**. With a
lure there's no float: cast it further than bait, then work it back in. Fish only strike while the lure is moving; a
lure left sitting draws nothing. Each kind of lure draws its own fish and mostly gets ignored by the rest.

**Retrieves.** How you work the lure is a retrieve, and the HUD names the one you're doing (green when it suits the
lure):

| Retrieve | How | Suits | Draws |
|---|---|---|---|
| Slow Roll | Hold right click at a low reel speed | Spinners, soft baits, Texas rigs, swimbaits, flies | Perch, trout, char, grouper, halibut |
| Steady | Hold right click at a medium speed | Spoons, spinners, crankbaits, swimbaits | Trout, salmon, herring, tetra |
| Burn | High reel speed, or hold Shift | Spoons, crankbaits | Pike, mackerel, tuna, salmon |
| Stop & Go | Reel, pause, reel, pause | Spoons, crankbaits, soft baits, poppers, flies | Pike, trollfish, mistfin, lingcod |
| Twitch | Tap left click while reeling | Poppers, flies, jigs | Trout, tetra, mackerel, trollfish |
| Hop | Tap left click with pauses, without reeling | Jigs, Texas rigs, soft baits | Coral cod, lingcod, halibut, grouper, pufferfish |

The right retrieve brings the fish it draws more often and makes them likelier to strike; with the wrong one, fish
follow the lure and turn away. **Alt + mouse wheel** sets the reel speed (also in a fight, where a slower reel
strains the line less); Shift reels at full speed.

| Lure | Kind | Fish | Made at |
|---|---|---|---|
| Feather Fly | Fly | Trout, char, grayling (0.05–3 kg) | Workbench |
| Flint Spinner | Spinner, takes a trailer | Perch, trout, pike (0.1–4 kg) | Workbench |
| Leather Grub | Soft bait | Perch, trout, gobies (0.1–5 kg) | Workbench 2 |
| Bronze Spoon | Spoon | Pike, trout, salmon, mackerel (0.3–10 kg) | Forge |
| Finewood Crankbait | Crankbait | Pike, perch, trollfish (0.5–12 kg) | Workbench 3 |
| Guck Crawler | Texas rig | Trollfish, pike, mistfin (0.5–15 kg) | Workbench 3 |
| Bone Jig | Jig, takes a trailer | Lingcod, halibut, grouper (1–30 kg) | Forge 2 |
| Silver Swimbait | Swimbait | Big pike, tuna, grouper, halibut (2–40 kg) | Forge 3 |
| Linen Popper | Topwater | Pike, trollfish, mackerel (0.5–20 kg) | Workbench 4 |
| Ice Spoon | Spoon | Salmon, grayling, char (0.5–20 kg) | Forge 4 |
| Frostcore Jig | Jig, takes a trailer | Rimejaw cod, sculpin (1–60 kg) | Black forge 2 |

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
- **Lingonberry Angler's Mead** (cauldron 5): a strong all-rounder for the Deep North - faster bites, easier hookset
  and longer fights.
- **Rune of Njord** (forge, worn as a belt): bigger fish, more legendaries.
- **Chum** (cauldron): set the bucket down on the bank to draw more, less picky fish to the water around it for
  5 minutes, for anyone fishing there.
  **Blubber Chum** (seal blubber, lingonberries) is the strongest and lasts 6 minutes.
- **Totems** (hammer): the Fisherman's Totem and Shrine of Njord buff anyone fishing nearby.
- **Relics** (can't be crafted, and each takes a slot of its own - they don't stack). Each comes from one place:

  | Relic | Where it comes from |
  |---|---|
  | Horn of Ægir | Hildir's prize for your 15th fishing bounty |
  | Pearl of Njord | Logging every species in the catch log |
  | Golden Hook | Very rarely (about 1 in 50) found inside a legendary fish you land |
  | Jörmungandr's Scale | Very rarely (about 1 in 33) dropped by a sea serpent you kill |

  The Hook and the Scale can turn up again; Hildir buys spares.

## The Bog Witch

Her wares go into fishing:

| Her ware | Goes into |
|---|---|
| Pungent Pebbles | **Stinkbait** (cauldron): catfish, trollfish, pike, mistfin and bass love it |
| Fresh Seaweed | **Seaweed Chum** (cauldron 2): more, keener fish for 6 minutes |
| Candle Wick | **Lantern Float** (workbench 2): use it and your line wears a candle-lit float for 20 minutes; fish bite 50% sooner at night |
| Love Potion | **Spawning Musk** (cauldron 3): legendary fish 50% more likely for 10 minutes |
| Powdered Dragon Eggshell | Major Steady-Hand Tonic |
| Toadstool | Major Troll-Grip Mead |
| Her herb blends | The fish feasts |

**Fish feasts** are made in the cauldron and set down with her **Serving Tray**, like vanilla feasts, for
everyone to eat from:

| Feast | Cauldron | Herbs | Health / Stamina / Eitr |
|---|---|---|---|
| Lakeside Fish Fry | 2 | Woodland Herb Blend | 40 / 40 |
| Fin and Onion Hotpot | 3 | Mountain Peak Pepper Powder | 55 / 50 |
| Sea-Fish Spread | 3 | Seafarer's Herbs | 50 / 60 |
| Roe and Barley Platter | 4 | Grasslands Herbalist Harvest | 60 / 70 |
| Abyssal Ink Banquet | 5 | Herbs of the Hidden Hills | 60 / 45 / 70 |
| Ember Fish Platter | 5 | Fiery Spice Powder | 85 / 60 |
| Rime Fish Smorgasbord | 5 | the Deep North spice | 90 / 75 / 35 |

She also sells Stinkbait, Lantern Floats and (after Bonemass) Spawning Musk, and each **boss lure** once you've
beaten that boss, so a failed summoning doesn't mean hunting a new trophy.

### Floats

Some items are floats: use one like a mead and your line wears that float instead of the usual one until it runs
out. There's no slot to fill, and only one float at a time. The Lantern Float is the first; its candle lights up
after dark.

## Hildir

**Fishing bounties.** Hildir posts one bounty a day for a species you've caught: at least so heavy, sometimes caught in
the rain, at night or Trophy-size. Hand the fish in from the trade panel for coins and bait. Your 5th, 15th and 30th
bounties earn a Yule Hat, the Horn of Ægir and Megingjord, with a Thunder Stone at 10 and a Dverger Circlet at 20.

**Lost tackle boxes.** Three of Hildir's tackle boxes turn up in dungeon chests. Give one back (use it on her, or from
the trade panel) and her shop gains more:

| Box | Found in | Hildir starts selling |
|---|---|---|
| Mossy Tackle Box | Sunken Crypts | Bog-Dyed Fisherman's gear, Guck Crawlers, Leather Grubs |
| Frosted Tackle Box | Frost Caves | Frost-Dyed Fisherman's gear, Silver Swimbaits, Frost Bait |
| Dvergr-Mended Tackle Box | Mistlands dvergr ruins | Mist-Dyed Fisherman's gear, Bone Jigs, Abyssal Bait |

The dyed gear is bought, not crafted, but repairs at the workbench (level 2) like the rest of the set.

## Fisherman's gear

A light armour set made at the workbench (level 2): the **Sou'wester**, **Oilskin Coat** (worn as a cape), **Striped
Fisher's Shirt** and **Oilskin Overalls** with rubber boots. Wearing all four keeps the rain off (you never get Wet)
and makes reeling cheaper and the hookset window longer.

## Your catch

- **Size class:** each fish is Small, Medium, Large or Trophy, with its weight and catcher in the tooltip.
- **Rare variants:** any ordinary species can come up **golden** (about 1 in 300) or **albino** (about 1 in 150), its
  icon and model tinted to match. They never stack with ordinary fish, earn rank points (+10 golden, +5 albino), sell
  for more (Haldor 5x / 3x, Hildir 6x / 4x) and each species' card in the catch log marks which you've caught.
- **Trophy Mount** (hammer: fine wood, resin): hang a fish on the wall.
- **Cook and sell:** cook fish on a cooking station, and sell your catch to the traders. Each buys their own kind:

  | Trader | Buys |
  |---|---|
  | Haldor | Raw and cooked fish, at their value |
  | Hildir | Trophy-size fish (2.5x) and legendary fish (1.5x) for her collection, and spare relics (400) |
  | Bog Witch | Roe, fish oil, abyssal ink, brined roe, leeches, and swamp, Mistlands and eel-like fish (1.4x) |

  Your catch sells from the **Sell your catch** panel beside the store window (it works alongside trader UI mods);
  click a row to pick what to sell, or Sell all. The store's own sell button sells vanilla valuables, as in vanilla.
- **Catch log** (`J`): records every species you catch, with your angler rank, the reward ladder and biome sets in a
  sidebar and each species as a card (its bait, mastery and record). The mouse is free while it's open: click a biome to filter, the arrows or the wheel to turn pages, Close (or J / Escape) to shut it.
  - **Rewards** every 5 species (hooks, meads, chum, a Lantern Float, a Trophy Fin, coins) and the Pearl of Njord for
    all of them.
  - **Biome sets:** catch every non-legendary fish of a biome *in that biome* for 10 of its bait, some coins and 25
    rank points. A fish that lives in two biomes (pike: Black Forest and Swamp) has to be caught in each to count for both.
  - **Finds:** now and then a catch has a valuable inside (amber, amber pearls, rubies, silver necklaces, by where you
    fish): rarely in small, common fish, more often in big or rare ones.
  - **Personal best:** +5 rank points. **Each angler rank** comes with a small gift.
- **Species mastery:** catch enough of one species and it gets easier for you. Each tier also gives angler rank
  points (10 / 20 / 40), and the catch log shows a bronze, silver or gold mark and the count to the next tier.

  | Tier | Catches (legendary / boss) | For that species |
  |---|---|---|
  | Bronze | 10 (1) | It comes to your bait more often and takes it more readily |
  | Silver | 25 (3) | It pulls and lasts 10% less |
  | Gold | 50 (5) | It runs bigger, and you can build its **Gold Trophy Plaque** with the hammer (fine wood, bronze, resin) |

  Baitfish only go to Bronze. A plaque is a wall piece with a gold-plated fish of that species mounted on it and its name on a gold nameplate (a boss fish is mounted at 80% of its true size on a board grown to fit it, for 10 fine wood, 3 bronze and 5 resin); turn it to face out from the wall.
- **Angler ranks:** ten ranks, shown at the top of the catch log with a bar to the next rank and what it unlocks.
  Points: 10 per new species (40 for a legendary), 1 per fish landed, 5 per Trophy-size catch, 1 per 10 kg landed and
  10 / 20 / 40 for each species' mastery tiers.
  The top rods, lures and Fish Cleaning Table recipes stay hidden from the crafting list until you reach their rank.
  (The Bog Witch still sells boss lures to anyone.)

  | Rank | Points | Unlocks |
  |---|---|---|
  | Thrall of the Shallows | 0 | - |
  | Minnow-Karl | 40 | Antler Lure |
  | Net-Weaver | 100 | Root Lure, Silver Swimbait |
  | Riverwarden | 200 | Silver Fishing Rod, Ooze Lure, Brined Roe |
  | Fjord-Farer | 350 | Wyrm Lure, Linen Popper, Ice Spoon, cleaning for Legendary Scales |
  | Skerry-Reaver | 550 | Black Metal Fishing Rod, Dried Fish |
  | Wave-Jarl | 800 | Yggdrasil Fishing Rod, Ember Lure |
  | Serpent-Slayer | 1,100 | Ashwood Fishing Rod, Chitin Lure, Frostcore Jig, cleaning for Cinder Scales |
  | Ægir's Hand | 1,500 | Frostwood Fishing Rod, cleaning for Rime Scales |
  | Chosen of Njord | 2,000 | Crown Lure |
- **Fishing skill:** Valheim's Fishing skill rises as you reel and land fish. It makes reeling cheaper and
  faster and setting the hook easier.

## Settings

The config is `BepInEx/config/valheimdeepwaters.cfg`.

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
| Drag Control / Reel Speed Control | Mouse Wheel / Alt + Mouse Wheel | Either can be the mouse wheel, Alt + mouse wheel or the mouse side buttons (Mouse 5 up, Mouse 4 down) |

## Console commands (server admins)

These need `devcommands`, like Valheim's own spawn command.

- `vdw_give <item> [amount]`: gives an item, for example `rod_copper`, `hook_small`, `buff_angler_minor`,
  `worm` or a fish id.
- `vdw_debug listrods | listhooks | listbait | listfish | listbuffs`: lists the item ids.
- `vdw_debug resetlog`: clears your catch log.
- `vdw_debug tokens`: exports the mod's text for translating (see Translations below).

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
models forward along +Z. With debug logging on (see Troubleshooting), the log shows each model's final size in metres.

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
`Translations/<Language>/vdw.json` inside the mod's folder in `BepInEx/plugins` (any folder named `Translations` there works).

## Multiplayer

Every player needs the mod, the same version as the server (the game checks when you join).
- **Server rules:** the gameplay settings (marked "Set by the server" in the config) come from the server, so
  everyone plays by the same rules. HUD, sound and keys stay each player's own.
- **Shared:** caught fish, worm mounds, totems and trophy mounts are normal world objects that everyone sees.
- **Watching others fish:** players within 90 m see your line, float or lure, the fish on your hook (running, leaping,
  thrashing - a boss too, the Queen Eel's humps, rearing and tail slaps included), the splashes and bites, and hear your reel. A fish you land is news for players within 50 m; a boss fish
  is announced to the whole server.
- **Per player:** the fight HUD, flies and rain worms only show for the player who has them.

## Troubleshooting

The mod writes a few lines to the BepInEx log when it starts, plus warnings if something is missing. For a
detailed log (every model loaded, and more), add `Debug` to `LogLevels` under `[Logging.Disk]` in
`BepInEx/config/BepInEx.cfg`.

## Credits

Several fish are built on models from Sketchfab, used under their licences:

| Fish | Model | Author | Licence |
|---|---|---|---|
| Bonemaw | [Pacific Viperfish](https://sketchfab.com/3d-models/pacific-viperfish-21368fef466343b4b9d0ca11f2cff468) | redsonder1000 | CC BY |
| Frost Char | [White-spotted Charr](https://sketchfab.com/3d-models/cc0-white-spotted-charr-605079fc074f451db012579f67457629) | ffish.asia / floraZia.com | CC0 |
| Frost Sculpin | [Roughskin Sculpin](https://sketchfab.com/3d-models/cc0-roughskin-sculpin-t-fasciatus-dda1cde382f146eeb8f767e09d475ec5) | ffish.asia / floraZia.com | CC0 |
| Greydwarf Goby | [Freshwater Goby No.1](https://sketchfab.com/3d-models/freshwater-goby-no1-5b637be8e9ca4bd0ac6e71657c9d75d5) | Thomas Flynn | CC BY |
| Halibut | [Bastard Halibut](https://sketchfab.com/3d-models/cc0-bastard-halibut-p-olivaceus-abaafcb174bc44f1a0206e267925bc8f) | ffish.asia / floraZia.com | CC0 |
| Jotunn Perch | [European Perch](https://sketchfab.com/3d-models/european-perch-ca1bef303691418f9788a5b1ca1870d5) | doublesob | CC BY-NC |
| Mackerel | [Atlantic Mackerel](https://sketchfab.com/3d-models/atlantic-mackerel-e4a92741c16448e38a0be59845ab369b) | NewViStudios | CC BY |
| Odin's Eye | [Opah fish](https://sketchfab.com/3d-models/opah-fish-d5bd15eb103e4e909fe91efe37c65f50) | Batton | CC BY |
| Serpentfin | [Oarfish](https://sketchfab.com/3d-models/oarfish-7a60a4df5af940e58ff1f300609e7ee2) | TheoBaldeteBRID | CC BY |
| Surtling Sardine | [Sardine](https://sketchfab.com/3d-models/sardine-d7a2d0bd2a524d35b01e0d898b026479) | Drake | CC BY |
| Thor's Hammerhead | [Scalloped Hammerhead Juvenile](https://sketchfab.com/3d-models/scalloped-hammerhead-juvenile-low-poly-f5adc17c922b48feae76aaea98552dd4) | sharkingaround | CC BY |
| Trout | [Rainbow Trout - Redband](https://sketchfab.com/3d-models/rainbow-trout-redband-442ab10476d0486e8eb689941bc4ad6e) | eb78 | CC BY |
| Largemouth Bass | [Model 67A - Largemouth Bass](https://sketchfab.com/3d-models/model-67a-largemouth-bass-e60c457636b640629747c19feac4906c) | DigitalLife3D | CC BY-NC |
| Bluegill | [Model 70A - Bluegill](https://sketchfab.com/3d-models/model-70a-bluegill-3f4665f558fc4bcab1b460e5f33666d3) | DigitalLife3D | CC BY-NC |
| Sea Bass | [Perch Weever Sea Bass Fish](https://sketchfab.com/3d-models/perch-weever-sea-bass-fish-88a88ea2e8954f99ac153231e3a25d01) | boxgizmo | Sketchfab Standard |

Other models used:

| Item | Model | Author | Licence |
|---|---|---|---|
| Filleting Knife Rack (blades) | [Kitchen Knife Set - Asset Pack](https://sketchfab.com/3d-models/kitchen-knife-set-asset-pack-c55d34d4f1974b16a8a8cb6cd4ee49f3) | Falxxx | CC BY |
| Dried Fish | [Hanged Dried Fish](https://www.cgtrader.com/free-3d-models/exterior/other/hanged-dried-fish) | CGTrader | Royalty Free |
| Earthworm bait | [Earth_ Worm](https://sketchfab.com/3d-models/earth--worm-63ad4a2dfed44f209bc7b174f5d0cb84) | mj.artsi | CC BY |
| Fly bait | [Low Poly House Fly (Diptera)](https://sketchfab.com/3d-models/low-poly-house-fly-diptera-2baa84955f704a4091a274ef4acec24a) | Glowbox 3D | CC BY |
| Shrimp bait | [Shrimp (Low Poly)](https://sketchfab.com/3d-models/shrimp-low-poly-652650059ff949b39bbed3bfc34d5e87) | Fecalis | CC BY |
| Chum buckets | [Bucket](https://sketchfab.com/3d-models/bucket-0be255e1fefe489ab07ec468adafb82e) | dmitryartist | CC BY |
| Horn of Ægir | [Viking Horns](https://sketchfab.com/3d-models/viking-horns-95d68ebbdb374613955c2575e33c83a4) | Vetech82 | CC BY |
| Allfather's Rod textures | Metal007, Wood018, Fabric022, Rope001 | [ambientCG](https://ambientcg.com) | CC0 |

Several fish (Catfish, Fenringfin, Glacier Grayling, Lingcod, Mistfin, Rimejaw Cod) and the Njord's Regalia crown were
started from models generated with [Tripo](https://www.tripo3d.ai) and finished by hand. The glowing effects on the top
rods and on the legendary and boss fish are Valheim's own weapon effects, borrowed from the game while it runs.

The models were rigged, retextured and restyled for Valheim. Licences:
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/),
[CC0](https://creativecommons.org/publicdomain/zero/1.0/).
