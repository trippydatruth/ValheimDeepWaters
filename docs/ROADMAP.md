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
16. **Bass, bluegill, sea bass and catfish.** Add them as fish, on their own models (Mesh\Bass, Mesh\bluegill, Mesh\perch, Mesh\catfish).
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
20. **Hildir.** *Done 2026-10-18: daily bounties (coins, bait, relics at 5/15/30) and the three tackle boxes (Bog-, Frost- and Mist-Dyed gear and tackle), in the trade panel. Her Sparkler / hats / fireworks recipes are still to do.* Fishing bounties (e.g. "a pike over 8 kg in the rain") for coins and unique items. Three lost
    tackle boxes in Sunken Crypts, Frost Caves and Infested Mines, each adding lures and dyed Fisherman's gear to her
    shop. Her stock in recipes: Sparkler (glowing night popper), Straw Hat / Fur Cap (summer and ice-fishing angler
    hats), Basic Fireworks (a flare marking a boss fish for friends).
21. **Angler ranks.** *Done 2026-10-18: ten ranks (AnglerRanks.cs), the rank, progress bar and next unlocks in the catch log; rank-locked top rods, lures and table recipes are hidden until reached.* Ranks from species caught, Trophy-size catches and weight landed; the top recipes need a rank.
22. **Species mastery.** *Done 2026-10-18: Bronze / Silver / Gold at 10 / 25 / 50 (legendary and boss 1 / 3 / 5): bites more readily, fights weaker, runs bigger; rank points per tier; a Gold Trophy Plaque wall piece per species (Mastery.cs); tiers and counts in the catch log.* 10 / 25 / 50 of a species for a small perk or a gold trophy plaque; record weights in the
    catch log.
23. **Rare variants.** Golden / albino version of each species (about 1 in 300), valuable and collectable.
24. **Endgame.** Boss lures cost more each time; the Leviathan needs 2-3 of each boss material; a final rod and the
    "Njord's Regalia" relic set need all seven boss fish several times and every relic.
25. **Floats.** A float is a buff item (Buffs.json `FloatModel`, optional `FloatLight`): use it and the line wears that
    float model for its Duration - no slot, one float at a time. *The Lantern Float is the first (2026-10-18).* Planned,
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
