# Deep Waters: wish list

Things to do later, in the order they were listed (2026-10-10). Not a schedule; pick from it.

1. **New Pearl of Njord mesh.** Replace the current pearl with the remade `pearl_relic.fbx`. *Done: the pearl belt model is in.*
2. **Retrieves for lures.** *Done: six retrieves read from how you reel, Alt+wheel reel speed, Shift full speed (to test).* Different retrieve styles that draw different fish, so you can target fish better.
   Add a reel speed setting alongside drag, and keep Shift as the full-speed reel key.
3. **More lures and trailers.**
4. **Food.** Make sure caught vanilla fish still work in vanilla food recipes, and that the custom fish can be used
   too. Add the mod's own foods. *Checked: vanilla catches are vanilla items and work in vanilla recipes; custom fish now make Raw fish at the preparation table. Own foods still to do.*
5. **Vanilla fishing gear.** Make the vanilla fishing hat and other vanilla fishing buff items work with this mod. *Checked: the Fishing Hat's +20 Fishing already counts (reel stamina and speed, hook chance and window); it's the only vanilla fishing buff item.*
6. **Deep North content.** Add things from the new Deep North update. *Done: Fimbul Salmon boss, three fish, Northern Bait, Frostwood rod, two lures, Fimbul Hook, chum and mead.*
   *Done: Fimbul Salmon boss, three fish, Northern Bait, Frostwood rod, two lures, Fimbul Hook, chum and mead.*
7. **Bait models.** Give the Frost and Abyssal bait (and any other item still without one) a designed model.
   *Rune of Njord done: a necklace.*
8. **More custom fish.**
9. **Boss fight music.** It didn't play for the whole fight. *Fixed: it plays from the omen to the end of the fight. (The silence in testing was the game's music volume at 5%.)*
10. **Weather in boss fights.** Weather effects during some fights, synced across players if needed. *Done: each boss brings its boss's weather and music, shared with players nearby.*
    *Done: each boss brings its namesake boss's weather and music to everyone within 150 m.*
11. **Valheim style.** Restyle models and textures to fit Valheim's look better.
    *Done 2026-10-18: tone pass + pixel-and-blur on baits, rods, buffs, hooks, boss materials and the brightest fish; 512 textures; audit brightness 0.39 vs vanilla 0.35.*
12. **Queen Eel.** Make the model larger and the fight feel like a sea serpent fight. *Done: 7.5 m sea serpent with circle, charge, rear and tail-slap moves.*
    *Done: shown at 7.5 m, with a sea-serpent fight (circling, charges, rearing up, tail slaps).*
13. **Anything that makes the mod feel more fleshed out.**
14. **Fisherman's gear.** *Done 2026-10-17: the remade set (Mesh\Fishermen gear\Blender Files\new_gear_rig.blend) is back in the build, weighted from the player body, with the coat skirt swinging.*
15. **Models for the stand-in fish.** Each needs its own model of its kind of fish - no borrowing another species' model (the bass, sea bass and catfish models are kept for those fish, to be added later). *Done: twelve on 2026-10-12 from Sketchfab models (Mesh\Sourced, tools\prep_sourced_fish.py), and Rimejaw Cod, Glacier Grayling, Lingcod, Fenringfin and Mistfin on 2026-10-17 from Tripo models. The Dvergr Dace was dropped instead.*
16. **Bass, bluegill, sea bass and catfish.** *Done: all four are in the game on their own models.* Add them as fish, on their own models (Mesh\Bass, Mesh\bluegill, Mesh\perch, Mesh\catfish).
    *Done 2026-10-17: all four on their own models - the bass and bluegill on their downloads' own rigs and swim cycles with jaws, the sea bass and channel catfish on the Deep Waters rig with the user's weights.*
## Progression and replayability plan (2026-10-18)

Goal: a grind that lasts to the end of the game and uses every biome's items. In the order to build it:

17. **Fish materials and rod upgrades.** *Done 2026-10-18 (0.15.0): eight materials from cleaning and the Trophy Fin,
    with models and icons; every rod upgrades to level 4; the Fish Cleaning Table with three add-ons; the materials in
    every lure, the baits, meads, chum and totems; Fish Fillets, Brined Roe and Dried Fish from the table's add-ons, and eight fish dishes at the cooking station, cauldron and food preparation table. Still to do: new items for the unused vanilla
    materials (razor hooks, fine hooks, ember spoon and the rest - with #3).* Cleaning a catch gives its biome's material (scales, fins, roe, oil,
    bones; rarer ones from legendaries and boss fish). They go into rods, lures, meads and food. Every rod upgrades
    to level 4 with fish materials plus late-biome materials (level 4 needs a Trophy-size catch's material), and
    each level strengthens the line, made from leather scraps → deer hide → linen → jute → morgen sinew → moose sinew.
    Unused vanilla items get uses: greydwarf eyes (lure eyes), obsidian (razor hooks), deathsquito needles (fine
    hooks), tar (waterproof line), soft tissue and royal jelly (Mistlands bait), bilebags (chum), charred bone (jigs),
    celestial feathers (flies), molten core (ember spoon).
18. **Bog Witch.** *Done 2026-10-18: Stinkbait, Seaweed Chum, Lantern Float, Spawning Musk, eggshell and toadstool in the top meads, seven fish feasts with their own models (eaten down in three stages), her stock of brews and boss lures. Buying from you moves to #19.* Her stock in recipes: Pungent Pebbles (stinkbait), Fresh Seaweed (ocean chum), Seafarer's Herbs
    (sea-fish feast), Candle Wick (lantern float for night fishing), Powdered Dragon Eggshell (top Steady-Hand
    Tonic), Toadstool (top Troll-Grip Mead), Love Potion (spawning musk: legendaries likelier for a while). One fish
    feast per biome with her Serving Tray and herb blends. She sells the mod's witchy brews and a boss-summoning
    ingredient. She buys roe, fish oil, leeches, eels and swamp / Mistlands fish.
19. **Per-trader selling.** *Done 2026-10-18: each trader's buy list and prices (TraderSales.cs), and a button beside Sell to pick what to sell. Golden variants join Hildir's list with #23.* Haldor buys ordinary and cooked fish and treasure; Hildir buys Trophy-size fish, golden
    variants and spare relics at a premium; the Bog Witch as above. A way to pick what to sell (vanilla sells the
    first valuable).
20. **Hildir.** *Done 2026-10-18: daily bounties (coins, bait, relics at 5/15/30) and the three tackle boxes (Bog-, Frost- and Mist-Dyed gear and tackle), in the trade panel. Her Sparkler / hats / fireworks recipes are planned for after the first release (below).* Fishing bounties (e.g. "a pike over 8 kg in the rain") for coins and unique items. Three lost
    tackle boxes in Sunken Crypts, Frost Caves and Infested Mines, each adding lures and dyed Fisherman's gear to her
    shop. Her stock in recipes: Sparkler (glowing night popper), Straw Hat / Fur Cap (summer and ice-fishing angler
    hats), Basic Fireworks (a flare marking a boss fish for friends).
21. **Angler ranks.** *Done 2026-10-18: ten ranks (AnglerRanks.cs), the rank, progress bar and next unlocks in the catch log; rank-locked top rods, lures and table recipes are hidden until reached.* Ranks from species caught, Trophy-size catches and weight landed; the top recipes need a rank.
22. **Species mastery.** *Done 2026-10-18: Bronze / Silver / Gold at 10 / 25 / 50 (legendary and boss 1 / 3 / 5): bites more readily, fights weaker, runs bigger; rank points per tier; a Gold Trophy Plaque wall piece per species (Mastery.cs); tiers and counts in the catch log.* 10 / 25 / 50 of a species for a small perk or a gold trophy plaque; record weights in the
    catch log.
23. **Rare variants.** *Done 2026-10-19 (RareFish.cs): golden 1/300, albino 1/150 on ordinary species; Valheim's item variant picks a tinted copy of the fish's own icon; tinted models dropped, mounted and on the line (watchers too); no stacking with ordinary fish; rank points; Haldor 5x/3x, Hildir 6x/4x; catch log marks and count.* Golden / albino version of each species (about 1 in 300), valuable and collectable.
24. **Endgame.** *Done 2026-10-19 (Endgame.cs), boss lure ingredients +1 per landing of their boss up to 3x, Bog Witch price +50% a landing up to 3x; Leviathan 2 of each of 7 boss materials; Allfather's Rod (Leviathan + 3 of each, every boss landed once; its own model, build_rod_model.py allfather); Njord's Regalia crown (the four relics + 2 of each, every boss landed 3 times; its own crown model worn on the head, RelicVisuals.cs). Models and icons for both still to make.* Boss lures cost more each time; the Leviathan needs 2-3 of each boss material; a final rod and the
    "Njord's Regalia" relic set need all seven boss fish several times and every relic.
25. **Floats.** A float is a buff item (Buffs.json `FloatModel`, optional `FloatLight`): use it and the line wears that
    float model for its Duration - no slot, one float at a time. *The Lantern Float is the first (2026-10-18).* *Built 2026-11-03, being tested: all eight below, with models and icons (build_lures float_<k>), and FreshBite / ColdBite / DeepBite / AshBite stats; the Eitr and Ember floats light up in their own colours.* Planned,
    one or two per era, each with its own model and a small effect suited to it:
    - **Quill Float** (Meadows: feathers, resin) - light and twitchy, fewer missed nibbles (Nibbles).
    - **Cork-and-Antler Float** (Black Forest: hard antler, fine wood) - sits steady in current (river fish keener).
    - **Bone Float** (Swamp: withered bone, guck) - rides low and dark, fish less wary (Stealth).
    - **Frost Float** (Mountain: freeze gland, crystal) - doesn't ice over, cold-water fish keener.
    - **Linen Bob** (Plains: linen, barley straw) - bright and big, longer hook window (HookWindow).
    - **Eitr Float** (Mistlands: eitr, sap) - glows faintly like the lantern float, for deep water (FloatLight).
    - **Ember Float** (Ashlands: charred bone, sulfur) - won't burn in hot water, Ashlands fish keener.
    - **Rime Float** (Deep North: frostcore, moose sinew) - a heavy float for heavy fish (Tension).
    Effects that need a condition (river, cold water, deep water) get their own stat, like the lantern float's NightBite.

## Polish pass (2026-10-19)

Improvements first, new content last, in this order:

26. **Bait targets fish.** *Done 2026-10-19: a fish not on a bait's list is 1/100 as likely and rarely bites (strays ~2% where nothing takes it); new bait table; tooltips, catch log and a cast hint show what takes what; data files updated once (ReplacedFields); vanilla rod blocked.* Rework the bait system so each bait and lure only works for a select few fish, so players
    pick their bait for the fish they want.
27. **Rewards rework.** *Done 2026-10-19 (Rewards.cs): catch log rewards every 5 species (no boss lures), biome sets (bait, coins, +25 rank points), rare valuables inside catches (1-4%), +5 rank points for a personal best, a gift at each angler rank, Hildir's prizes from Haldor's uncraftable items (Yule Hat, Thunder Stone, Horn, Dverger Circlet, Megingjord); the catch log redrawn (sidebar with rank and unlocks, reward ladder, biome sets; species cards with biome filters). Custom rewards (biome pennants, angler caps) to be handed out once modelled.* Rework the rewards for the catch log and for regular catches.
28. **Dyed gear repair.** *Done 2026-10-19: each dyed piece has a disabled workbench recipe - repair only needs a recipe to exist, the craft list only shows enabled ones - so it repairs at workbench 2 but can't be crafted.* Hildir's dyed Fisherman's gear (bought, so it has no recipe) can't be repaired - give it a way.
29. **Fights everyone can see.** *Step 1 done 2026-10-19 (RemoteAnglers.cs, AnglerSync): line, float/lure, hooked fish with runs and leaps, splashes/bites/snaps, reel sound for players within 90 m; "landed a fish" news within 50 m (bosses server-wide). Step 2 done 2026-10-19: boss fights - the boss at its size, and the Queen Eel's humps, rearing, crash and tail slaps (with a camera rumble close by) for watchers.* Other players see the fish fight - the line, the hooked fish and the angler.
30. **Relics.** *Done 2026-10-19 (Relics.cs): Horn = Hildir's 15th bounty, Pearl = full catch log, Golden Hook ~2% per legendary landed, Scale ~3% from sea serpents killed; stack size 1; boss relic drops and the Horn's fish find removed; data files updated once.* Relics don't stack, turn up only very rarely, and each comes from a different place.
31. **No accidental recast.** *Done 2026-10-19: a cast that ends with the pull (left click) still held waits for it to be let go before a new cast can charge.* Reeling and pulling the rod (left click) as the fish lands shouldn't cast again straight away.
32. **Crab traps and crustaceans.** Traps set in the water, and crabs, lobsters and other crustaceans to catch in them.
33. **Catch sea serpents.** Vanilla sea serpents near your bait can take it and be hooked, in the Queen Eel's serpent fight. Could become another source of Jörmungandr's Scale.
34. **Ice fishing.** Fishing through a hole in the ice on frozen water, with fish that only bite there.
35. **Fly fishing.** A fly rod and flies, cast and worked on the surface for river fish.
36. **Different hooks.** More kinds of hook with their own uses, alongside the sizes already in. *Built 2026-11-03, being tested: circle (sets itself), EWG (holds big fish) and treble (soft baits, on the bottom) hooks, Small to Giant.*
37. **Terminal tackle and depth.** *Done 1.0.1: Tackle.json weights (split shot, bullet/Texas, egg/Carolina, pyramid) and the leader, Weight and Leader slots, leader length on the tackle panel, fish feeding depths (FeedMinDepth/FeedMaxDepth/Bottom), water dragging light weights.* Sinker weights, leaders and leader length, and a way to choose the depth you fish
    at (float stop or sinker), with fish that hold at different depths.
38. **Tackle inventory.** *Started 1.0.1: a rod slot (rod takes no inventory space, Alt+F to use it), rod stats on the panel, and the panel can be dragged anywhere.* A Fishing Planet-style tackle screen: the rod in the middle with a slot for each piece
    of equipment (reel, line, leader, weight, hook, float, bait or lure) instead of the inventory bait slot.
    *Built 2026-11-02, being tested: the screen with the whole rod pictured, eight slots, three loadouts (Shift+click
    saves), collapsible stats; 7 reels and 6 lines (craftable, sellable to Haldor and Hildir); a setting to play without
    separate reels, lines and floats.*
39. **Meads from mead bases.** *Done and tested 2026-11-02: a mead base at the cauldron, fermented into 6 meads.* The fishing meads made like vanilla meads: a mead base at the cauldron, fermented in
    the fermenter into several meads.
40. **Cooler box.** *Done 2026-10-25: three coolers (Coolers.cs) on the user's ice chest model, set down not worn, no spoilage; fresh fish +25% sale and +1 when cleaned; frost effect inside while open.* A box for your catch, like the tackle boxes but for fish: keeps them fresh (slower spoiling or none),
    carried or set down. (The tackle boxes are in: 1.0.1, TackleBoxes.cs.)
## Next, in order (2026-11-02; released on Thunderstore 2026-10-26)

1. #38 the tackle screen. 2. Hildir's stock in recipes (below). 3. #7 bait models, and restyle the bait models
already made (more stylized, better looking). 4. #25 the floats. 5. #27 the custom rewards (pennants, angler caps).

## Playtest notes (2026-11-07) - all built, in Test, to test (docs/TO_TEST.md)

Bugs:
- Built: equipped items and tackle go back to their own slots after looting your grave (Tackle.cs GraveReturn).
- Built: the tackle screen's loadouts use tackle boxes carried, worn or set down and open; applying one empties the
  slots that weren't in it.
- Built: a fish's extra drops go into the bag when caught from a boat.
- Built: fireflies at night glow, with a small pulsing light (FireflyGlow).
- Built: vanilla rods and baits found in the world (frost caves) turn into Deep Waters gear (VanillaGearSwap.cs).
- Built: left click with bait out (no lure) tugs the rod and draws the bait in a little (PullBait).

Ideas:
- Built: a lbs / kg setting (4 Interface > Weight Unit).
- Built: the Rod Holder - a bank stake; set a rod in it with the line out and it keeps fishing, tells for everyone,
  circle hooks set themselves, anyone can take the rod and fight the fish; several at once (RodHolders.cs,
  FishingController.Parked.cs). And the Rod Rack - ten rods, storage only.
- Built: a bigger water swirl for boss fish (16 m, more for the biggest).
- Built: the Cork float is the Cork-and-Bone Float (bone fragments, no boss item).
- Built: mead bottles with see-through glass, a glowing fake-liquid mesh inside, and the user's fixed cork and twine
  (Mesh\mead bottle\v4; export_mead.py), glow 2.5x / 3.5x.
- Built: Deep Waters catches count for the vanilla fishing achievements (FishCaught and the tier stats).
- Built: the HUD shows the tackle on the line for a rod taken up from a holder.
## Hildir's stock (was "after the first release")

- **Hildir's stock in recipes** (the rest of #20). Checked in the game files: Sparkler (`Sparkler`), Basic Fireworks
  (`FireworksRocket_White`), her caps `HelmetHat1`-`10` (Brown Fur Cap = `HelmetHat3`, Grey Fur Cap = `HelmetHat8`,
  Simple Red Cap = `HelmetHat5`); vanilla has no straw hat.
  - **Sparkler Popper** - a topwater lure (Sparkler 1, fine wood 2, fish scales 2, a Medium Hook -> 1 at the forge, like the other lures since 1.0.1) with its own
    model and icon: at night it lights the float like the Lantern Float and fish bite sooner (~+40%).
  - **Ice Angler's Fur Cap** (Grey Fur Cap, wolf pelt, rime scales): frost resistance and a longer hook window.
  - **Sun Angler's Cap** (Simple Red Cap, feathers, fish scales): fish bite sooner by day. Open: keep her caps' look or
    tint them (new icons); model a real straw hat instead?
  - **Angler's Flare** (Basic Fireworks, fish oil): hooking a boss fish while carrying one fires it - a firework over
    you, a map ping for everyone and a shout naming the boss. Open: automatic, or fired by hand.

## Spear fishing (2026-11-03)

41. **Spear fishing.** Stab or throw a spear at fish near the surface. *Built 2026-11-03, being tested: SpearFishing.cs, eight leisters (Flint to Frostcore) on vanilla spear looks; any vanilla spear works on small fish. Leister models and icons in 2026-11-03 (build_lures.py leister_<tier>, fitted onto the vanilla spear). The thrown spear wears the leister model too.*

## Ice fishing (#34) - design, 2026-11-03 (build next)

Fish through a hole drilled in the ice, for fish that only bite there. Mountain and Deep North lakes, where the water is
frozen over (or snow-covered ice at the shore).

**Seen in game (2026-11-03 clip):** yes - in the Deep North, rivers and lakes are covered in solid walkable ice sheets
(a whole river channel frozen bank to bank, flat frozen lakes), ending in broken ice plates beside dark open water.
So the Ice Hole goes on those sheets. Still to find out in code: what the sheets are - terrain, a static piece, or an
"ice" water material? `vdw_debug` a ray
down from the player standing on lake ice: hit collider name/layer, Floating.GetLiquidLevel there, WorldGenerator biome.
If there's no real frozen water, fall back to: the hole works on Mountain / Deep North lakes' shallow edges, as a piece
placed on the water's surface (like the Fishing Boat's spot checks).

**Items**
| Item | Kind | Made at | Recipe | Notes |
|---|---|---|---|---|
| Ice Auger | tool (secondary attack drills) | Forge 3 | Iron 4, Fine Wood 2, Silver 2 | Drills an Ice Hole in front of you on ice over at least 1.5 m of water; durability, repairs at the forge |
| Ice Hole | piece (spawned by the auger, not built) | - | - | A 0.5 m hole with a slush ring; refreezes after 20 min (ZDO timestamp); one per player at a time |
| Ice Fishing Rod | rod (Rods.json) | Forge 3 | Fine Wood 4, Silver 3, Wolf Pelt 1 | Short (cast 0, line straight down the hole), +25% hook window, reels fast; only works in an Ice Hole (any rod works in a hole too, at -50% hook window) |
| Ice shelters (built 2026-11-08, to test) | pieces (hammer) | Workbench | Hide Lavvu: Wood 20, Wolf Pelt 6, Leather Scraps 8, Stone 5 / Ice Shelter (igloo): Ice 30, Stone 5 / Ship-Tent: Fine Wood 12, Elaking Hair Bundle 4, Lox Pelt 4, Iron 2, Stone 5 | Walk-in shelters with a vent for a fire's smoke (the Lavvu and Ship-Tent come with a campfire; the igloo doesn't); comfort, shelter, and +10/15/20% bite through a hole inside (IceShelters.cs; art build_shelters.py, Mesh/ice fishing/shelter_v6) |
| Grub Jig / Rime Jig | lures (Baits.json, kind Jig) | Forge 3 / Black forge 2 | small jig + hook | Jigged in place (Hop retrieve without reeling) - the ice-fishing way |

The Ice Angler's Watch Cap gets **IceBite** (+30%: fish bite sooner through the ice) on top of its hook window.

**Fish (only bite through an Ice Hole; one model each - Sketchfab/Tripo, per the one-model-per-species rule)**
| Fish | Biomes | Max | Bait | Material |
|---|---|---|---|---|
| Burbot | Mountain, Deep North | 8 kg | worm, cut bait | rime |
| Lake Whitefish | Mountain, Deep North | 5 kg | grub, Grub Jig | fins |
| Arctic Grayling (ice) - or reuse Frost Char's niche | Deep North | 3 kg | fly, grub | rime |
| Lake Trout (legendary-ish "Ice King Trout", mini-boss like Fenringfin) | Deep North | 40 kg | Rime Jig | legend |
Frost Char and Frost Sculpin also bite through the ice (they already live there).

**Code (files to change)**
- New `src/Fishing/IceFishing.cs`: the auger's drill (Harmony postfix on the tool's attack hit like SpearFishing's
  StabPatch), the IceHole piece (ZNetView, refreeze timer, slush VFX, removed when frozen), `IsIceHole(spot)`.
- `FishingController.Casting.cs`: `TryFindWater` accepts an Ice Hole within 2 m in front (spot = hole centre, depth
  from the water below); a cast there is a straight drop (no arc - BobberVisual.BeginCastTravel with a tiny arc);
  `FishingSession.IceHole` flag.
- Fish data: `FishDefinition.IceOnly` (bool, merged field: add to ContentRegistry's new-fields list) - `Matches()` only
  lets IceOnly fish come to an Ice Hole cast, and an Ice Hole cast only draws IceOnly fish plus the cold-water fish.
- `Buffs.cs`: `BuffStat.IceBite` (added to BiteSpeed when s.IceHole, like PlaceBite). FisherGear.cs: the cap's IceBite.
- `DefaultData.cs`: the rod, two jigs, the four fish (new ids only: existing saves pick them up); Rods.json gets an
  `IceRod` flag (no cast distance).
- `FishSpawns.cs`: IceOnly fish don't swim free in the world (they're under the ice).
- Catch log / Rewards: an "Under the Ice" biome set (all IceOnly fish) - Rewards.cs RecordCaughtIn.
- README section, wiki page (wiki_from_readme.py picks it up), sheet: Fish rows, an Ice Fishing tab.

**Art (all Sanctus + Grungit, previews first)**
- Ice Auger (spiral bit, T-handle, wrapped grip) - build_lures-style procedural, or a hand model.
- Ice Hole: a round hole with a slush ring and chipped ice around it (procedural, a flat ring mesh + ice chunks).
- Ice Fishing Rod (short, stubby, a small reel) - build_rod_model.py / convert_user_rod.py; icon + rod_ice_full.png.
- Ice Shelter (hide stretched over a bent-pole frame) - procedural or Tripo.
- Grub Jig, Rime Jig - build_lures.py (jig head + treble).
- The four fish: Sketchfab/Tripo downloads -> prep_sourced_fish.py -> rig/seam/export chain (fish-model-pipeline).
- Icons for all of them; sheet icons pushed to the sheet-icons branch.

**Built 2026-11-07 (first pass, in Test, to test):** IceFishing.cs - ice found by its slippery collider or an "ice"-named object (the props are IceSheet / Icepond / IceShore, from the asset rip) with water under it; `vdw_debug ice` reports what's there; the Ice Auger (PickaxeIron clone, no damage) drills a VDW_IceHole (networked, refreezes after 20 min); casts onto ice are refused, a hole in front takes the cast; IceOnly fish (Burbot, Lake Whitefish, Ice King Trout) only there and never spawned free; the Ice Fishing Rod (IceRod) and the hole hook window; Grub Jig and Rime Jig; IceBite on the Ice Angler's Watch Cap. Still to do: the "Under the Ice" catch-log set, art (auger, hole, rod, jigs, shelter, three fish models), README/wiki/sheet.

**Order to build:** 1. the in-game ice check; 2. Ice Hole + auger (code, placeholder models) and casting into it;
3. IceOnly fish with stand-in models to test; 4. the rod, jigs, IceBite; 5. art; 6. README/wiki/sheet; 7. 1.0.4.

## Crab traps and crustaceans (#32) - design, 2026-11-03

Set a baited trap in the water, leave it, come back to crabs, lobsters and other shellfish. Passive fishing: no rod, no
fight - the trap fills over in-game time while you do other things, like vanilla's beehives and fermenters.

**How it works**
- Build a trap with the hammer, standing in shallow water (0.5-6 m; the placement ghost turns red elsewhere) or drop it
  off a boat or dock into deeper water (crab pots: 4-30 m). It sinks to the bottom; a cork marker buoy floats above it.
- Put bait in it (one stack; `E` opens it like a small chest). It checks every in-game hour: each check, if baited, rolls
  one catch from what lives there (biome, water depth, sea or fresh, time of day), using up one bait.
- Holds up to its capacity, then stops. `E` on the buoy hauls it up: take the catch, re-bait, leave it.
- Traps wear (durability per haul) and repair at the workbench. Sea serpents and storms can't move them; nothing else
  takes from them - other players can (it's a chest), unless set in a ward.
- Bait matters: Cut Bait and fish scraps for crabs, Stinkbait for crayfish, Blubber for the Deep North.

**Pieces (hammer)**
| Trap | Station | Recipe | Water | Capacity | Notes |
|---|---|---|---|---|---|
| Wicker Crayfish Trap | Workbench 1 | Wood 6, Resin 2, Leather Scraps 2 | fresh, 0.5-4 m | 4 | rivers and lakes |
| Crab Pot | Workbench 2 | Fine Wood 8, Deer Hide 2, Bronze Nails 10 | sea, 2-15 m | 6 | the coast |
| Iron Lobster Pot | Forge 2 | Fine Wood 6, Iron 4, Fish Oil 2 | sea, 6-30 m | 8 | lobsters, deeper |
| Rime Pot | Forge 4 | Frostwood 6, Silver 4, Rime Scales 2 | Deep North, any | 10 | cold-water catches; doesn't ice over |

**Catches (one model each)**
| Catch | Where | Rarity | Use |
|---|---|---|---|
| Crayfish | Meadows / Black Forest fresh water | common | cook (small food), bait (Crayfish Bait: pike, bass, catfish) |
| Shore Crab | sea, any coast | common | cook, Crab Meat for chum and dishes |
| Brown Crab | sea, 4 m+ | uncommon | bigger food, sells |
| Lobster | sea, 8 m+, night likelier | uncommon | top shellfish food, sells well (Haldor 2x) |
| Spider Crab | Mistlands / deep sea | rare | its shell -> Carapace-like lure parts |
| Ember Crab | Ashlands sea | rare | glowing shell, Cinder material |
| Rime Lobster | Deep North | rare | Rime material, the best food |
| Golden Lobster | any sea pot | 1 in 300 (like rare fish) | trophy, sells 10x, catch log mark |
Also from pots now and then: a sea shell, amber, a waterlogged chest (coins / a random tackle item), old boots (junk).

**Uses (so the catches matter)**
- Food at the cauldron: Crab Cakes, Lobster Stew, Crayfish Boil (cauldron 2-5), with Valheim's own ingredients.
- Bait: Crayfish Bait, Crab Meat in chum (an alternative to Cut Bait).
- The catch log: a "Shellfish" page (each species, its record, how many) and a Shellfish set reward; mastery tiers count.
- Traders: Haldor buys shellfish; Hildir pays well for the Golden Lobster and the rare ones.
- A **Lobster Trophy** mount (like the fish trophy mount).

**Code (files to change)**
- New `src/Fishing/CrabTraps.cs`: the trap pieces (Container like the coolers' set-down boxes, plus a ZDO "last check"
  time), the hourly roll (run by the trap's owner on load and on a timer, so time passed while away still counts -
  like vanilla's Beehive), the bait use, the buoy (a child object that floats at the surface: Floating.GetLiquidLevel),
  placement rules (depth under the ghost, fresh vs sea - reuse FishingController.IsOceanAt).
- New data `Shellfish.json` (DefaultData.ShellfishJson): id, name, biomes, water, depth range, rarity, night/day,
  food values, sell value, material - merged like Fish.json; ContentRegistry registers them as items (clone a vanilla
  food) with models and icons.
- Recipes for the dishes (FishDishes.cs) and Crayfish Bait (Baits.json, new id).
- CatchLog.cs / Rewards.cs / Mastery.cs: shellfish species and their set; TraderSales.cs: who buys them.
- RareFish.cs: the Golden Lobster as a shellfish variant.
- README section, wiki page, sheet tab (Shellfish).

**Art (Sanctus + Grungit, previews first)**
- The four traps: wicker (woven), wooden crab pot with netting, iron-banded lobster pot, frosted rime pot; each with a
  cork-and-rope marker buoy. Procedural (build_wood_*.py style) - netting as a mesh grid with alpha.
- The eight catches: Sketchfab/Tripo crab and lobster models (one per species), cleaned and baked; the Golden Lobster
  a tinted copy (like golden fish).
- Three dishes (bowl + contents, like the fish dishes), Crayfish Bait, the Lobster Trophy mount; icons for all.

**Also worth adding with it (small)**
- **Fish trap / weir** (fresh water): a stake fence that catches small baitfish over time - a passive source of minnows.
- **Clam digging**: wriggling-soil-like spots on beaches at low... (Valheim has no tides) - skip unless wanted.
- **Ward-safe**: traps in your ward can't be opened by others.

**Order to build:** 1. one trap (Crab Pot) with placement, bait, the hourly roll and the buoy, with stand-in models;
2. the catches as data + items (stand-ins); 3. the other three traps; 4. food, bait, catch log, traders; 5. art;
6. README/wiki/sheet. After ice fishing (1.0.4) - this as 1.0.5.
