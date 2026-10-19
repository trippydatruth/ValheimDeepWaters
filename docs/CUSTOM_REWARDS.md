# Custom rewards (designed, not modelled yet)

The rewards rework (roadmap #27) already hands these out by prefab name; anything not in the game yet is skipped, so
each one starts dropping as soon as its item is registered under the name below. Each needs a model and an icon, made
the usual way (art-tools builder or a sourced model, then the Unity importer).

Keep them small and few: they're keepsakes and a little money, not a new stack of things to carry.

## Finds inside a catch (`Rewards.FindTables`)

Rolled when a catch holds something (about 1% in small, common fish, up to 4% in big or rare ones), alongside the
vanilla valuables of the place it was caught. Weights are per place in `Rewards.FindTables`.

| Prefab | Name | Where | What it is / does |
|---|---|---|---|
| `VDW_Find_old_ring` | Fish-Swallowed Ring | Meadows, Black Forest, Deep North | A tarnished silver ring. A valuable: Haldor pays ~40. |
| `VDW_Find_sea_glass` | Sea-Glass | Ocean | A frosted green pebble of glass. A valuable: ~15. Could later go into a lantern float. |
| `VDW_Find_dvergr_coin` | Old Dvergr Coin | Plains, Mistlands | A square coin with a rune hole. A valuable: ~60; Hildir might collect them. |
| `VDW_Find_lost_lure` | Lost Lure | Swamp, Mountain | A rusted lure still on its hook. Using it gives a random lure of the area's tier (code to add). |
| `VDW_Find_bottle` | Message in a Bottle | Ocean | A corked bottle. Using it marks a buried chest on the map nearby (code to add). |

## Biome pennants (`Rewards.ClaimBiomeSets`)

`VDW_Pennant_<biome>` for each biome set: a small wall banner (a hammer piece, or an item for an item stand) showing
the biome's fish, given once when the set is complete. Biomes: Meadows, BlackForest, Swamp, Mountain, Ocean, Plains,
DeepOcean, Mistlands, AshLands, DeepNorth (`Rewards.BiomeOrder`).

## Angler's caps (`Rewards.RankGift`)

`VDW_AnglerCap_4`, `VDW_AnglerCap_7`, `VDW_AnglerCap_10`: a cap for reaching angler ranks 4 (Riverwarden),
7 (Wave-Jarl) and 10 (Chosen of Njord). Cosmetic helmets, the later ones a little better (a small fishing bonus like
the Fisherman's set), each its own look:

- Riverwarden's Cap: a felt cap with a heron feather.
- Wave-Jarl's Helm: a leather sea-cap with a silver fish badge.
- Njord's Crown of Kelp: a woven circlet of kelp and pearls, faintly glowing.
