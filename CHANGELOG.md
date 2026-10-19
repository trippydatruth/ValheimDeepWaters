# Changelog

## 0.15.0
### Added
- **Fish Cleaning Table**: a crafting station of its own, with three add-ons (Filleting Knife Rack, Brining Barrel,
  Drying Line) that raise its level for the rarer fish and let it prepare Fish Fillets, Brined Roe and Dried Fish.
  Cleaning fish raises your Fishing skill.
- **Fish dishes**: eight dishes made from the prepared ingredients at Valheim's own food stations - a grilled fillet
  on the cooking station, stews, soups and plates in the cauldron, and cured salmon and travel rations at the food
  preparation table.
- Fish materials go into every lure, the crafted baits, the meads, chum, the Rune of Njord and the totems. Data files
  still on the old recipes get the new ones.
- **Fish materials**: clean a catch at the Fish Cleaning Table for its biome's material - Fish Scales, Fish Oil, Spiny Fins,
  Fish Roe, Abyssal Ink, Cinder Scales, Rime Scales, or a Legendary Scale from a legendary fish. Bigger fish give
  more. Landing a Trophy-size fish also gives a Trophy Fin. Each has its own model and icon.
- **Rod upgrades**: every rod upgrades to level 4 with fish materials, its era's line material and some of each
  biome's unused oddments. Each level improves every stat; the last level needs a Trophy Fin. Upgrades never ask for a
  higher station level than the station can reach.
- Rod tooltips show the stats for the rod's level.
- A warning in the log names any recipe item the game doesn't have (a typo in a data file).

- **Angler ranks**: ten ranks (Thrall of the Shallows to Chosen of Njord) from species, catches, Trophy-size fish and
  weight landed, shown in the catch log with a progress bar and the next rank's unlocks. The top rods, lures and Fish
  Cleaning Table recipes stay hidden until you reach their rank.
- **Each trader buys their own catch**: Haldor ordinary and cooked fish, Hildir Trophy-size and legendary fish at a
  premium and spare relics, the Bog Witch roe, oil, ink, leeches and swamp and Mistlands fish - from a "Sell your
  catch" panel beside the store (pick from a list, or sell all) that works alongside trader UI mods.
- **Hildir's bounties**: a fishing bounty a day for coins and bait, with relics at 5, 15 and 30 bounties. The panel shows
  the fish, the conditions and the reward, and tells you whether the fish you carry counts.
- **Hildir's lost tackle boxes**: three, in Sunken Crypts, Frost Caves and the Mistlands dvergr ruins. Each one returned
  adds a dyed set of the Fisherman's gear and more tackle to her shop.
- **Floats**: an item can be a float - use it and your line wears that float for a while, no slot needed. The Lantern Float is the first: a candle-lit float that glows after dark, and fish bite sooner at night.
- **The Bog Witch**: her wares go into fishing - Stinkbait, Seaweed Chum, the Lantern Float,
  Spawning Musk (legendaries likelier) and the top Steady-Hand and Troll-Grip meads. Seven fish feasts made with her
  herb blends, each with its own model that's eaten down as it's shared, set down with her Serving Tray. She sells the brews, and each boss lure once you've beaten
  its boss.

### Fixed
- Lures and hooks in the tackle slots survived death when the inventory was full; they now go into the tombstone.

## 0.14.0
### Added
- **All 12 vanilla fish can be caught** with Deep Waters rods. Landing one gives the real vanilla item, so vanilla
  cooking and recipes work, and they bite Deep Waters bait.
- **Boss fish**: seven legendaries named after Valheim's bosses, each summoned with a lure carved from that boss's
  trophy, in the right water and weather. An omen comes first, then a fight with a boss bar, the boss's music and
  weather (shared with everyone within about 150 m), and enraged and desperate phases. They drop a trophy, a boss
  material and sometimes a relic. The six materials craft the new **Leviathan Rod**.
- **The Queen Eel fights like a sea serpent**: a 7.5 m monster that circles, charges, rears out of the water and
  lashes its tail.
- **Deep North**: the **Fimbul Salmon** boss (summoned with a Crown Lure), three new fish (Rimejaw Cod, Glacier
  Grayling, Frost Sculpin), Northern Bait, the Frostwood Rod, the Ice Spoon and Frostcore Jig lures, the Fimbul Hook,
  Blubber Chum and Lingonberry Angler's Mead.
- **Four new fish**: Bluegill, Largemouth Bass, Sea Bass and Channel Catfish.
- **Lures and trailers**: nine lures (fly, spinner, soft bait, spoon, crankbait, Texas rig, jig, swimbait and
  popper) plus three trailers. Cast them further than bait and work them back in; each kind draws its own fish.
- **Retrieves**: Slow Roll, Steady, Burn, Stop & Go, Twitch and Hop. The right retrieve for the lure brings more
  fish and more strikes. Reel speed is on Alt + mouse wheel, and Shift reels at full speed.
- **Pull back** on a fish (hold left click) to tire it faster, at the cost of line strain and stamina.
- **Fishing Boat**: a one-person rowing boat with a passenger seat at the stern and a holdfast in the bow. Fish
  caught from any boat go straight into your inventory.
- **Fisherman's gear**: Sou'wester, Oilskin Coat, Striped Fisher's Shirt and Oilskin Overalls. The full set keeps
  you dry and helps with reeling and setting the hook. The coat swings as you move.
- **New models** for nearly every fish, all rods (they bend under load and their reels turn), hooks, baits, lures,
  meads, chum buckets, totems, relics and boss materials, with icons rendered from the models.
- **Legendary and boss fish shimmer with effects** borrowed from vanilla weapons (storm crackles, frost, flames,
  mist and more). The top rods glow too.
- **Fish are as big as they weigh**: a heavier fish of a species is visibly bigger.
- **Baitfish swim in the world** in schools, and **rain worms** come up around you when it rains.
- **Chum buckets** are set down on the bank and chum the water around them for everyone fishing there.
- The **Horn of Ægir** is blown rather than drunk, and can be blown again after a day's rest.
- **Angler animations** everyone can see: casting, reeling, setting the hook, twitching a lure and fighting a fish.
- Deep Waters fish can be made into vanilla **Raw fish** at the food preparation table.
- Better rods hold much more line, from 45 m on the Copper rod to 260 m on the Leviathan.

### Changed
- Relics (Pearl of Njord, Jörmungandr's Scale, Golden Hook) now come only from boss fish; the Horn of Ægir is
  still found inside fish, rarely.
- The Deep Waters Perch, Pike, Tuna, Herring, Abyssal Angler, Salmon, Cod, Troll Trout and Ashscale are gone,
  replaced by their vanilla counterparts. The Dvergr Dace is gone too. Any already in an inventory disappear.
- The fishing hats and capes from 0.13 are gone (replaced by the Fisherman's gear).
- The vanilla fishing rod and baits can no longer be bought or crafted.
- In multiplayer, the server's gameplay settings apply to everyone, and every player needs the same version.
- Updates now add new fish, bait, rods, hooks and buffs to your existing data files and keep your edits.
- The config is down to what players need.
- Custom models are used at exactly their size in Unity (1 unit = 1 metre); `ModelScale` and `ModelLength` in the
  data files no longer do anything.
- Much quieter log at startup.
- The config file is now `valheimdeepwaters.cfg`. An existing `trippy.valheimdeepwaters.cfg` is moved over the first
  time the game starts, keeping your settings and dropping the ones that no longer exist.

- **Floats**: an item can be a float - use it and your line wears that float for a while, no slot needed. The Lantern Float is the first: a candle-lit float that glows after dark, and fish bite sooner at night.
- **The Bog Witch**: her wares go into fishing - Stinkbait, Seaweed Chum, the Lantern Float,
  Spawning Musk (legendaries likelier) and the top Steady-Hand and Troll-Grip meads. Seven fish feasts made with her
  herb blends, each with its own model that's eaten down as it's shared, set down with her Serving Tray. She sells the brews, and each boss lure once you've beaten
  its boss.

### Fixed
- Landing a fish could fail and leave it stuck on the line at your feet.
- A fish reeled in from a high bank could get stuck in the ground.
- Worm mounds weren't saved and disappeared when you came back to an area.
- Flies fled before you could get close.
- Ctrl+click on bait or a hook dropped it instead of putting it in its tackle slot.
- Boss music only played during the fight; it now plays from the omen to the end.
- The float's nibble splash never played.
- `vdw_give` and `vdw_debug` worked without `devcommands`; they now need it.

## 0.13.0
### Added
- **Rods for every era**: eight craftable rods from Wooden to Ashwood, each better than the last, plus
  Haldor's Gilded Rod (sold only by Haldor). Rods wear out while fighting fish and are repaired where they
  were crafted.
- **Hooks** in six sizes. The wrong size misses small fish or gets straightened by big ones.
- **Tackle slots** for bait and a hook, under the inventory.
- **Fishing buffs**: meads, hats, capes, the Rune of Njord, chum, totems, and rare relics found inside fish.
  (The hats and capes were removed in 0.14.0.)
- **Bait from the world**: grubs from chopped logs, catchable flies, leeches from swamp leeches, and baitfish
  caught as small fish. Only Abyssal, Frost and Runed bait are crafted.
- **Fish in the world**: Deep Waters fish swim in their own biomes, and fish swimming near your float are
  likelier to bite.
- **The fight**: fish run sideways and leap. Vanilla fishing sounds and splashes.
- **Fishing skill**: uses and raises Valheim's Fishing skill.
- **Your catch**: size classes from Small to Trophy, a Trophy Mount, and catch-log rewards.
- Translation support for every item, piece and buff name.

### Changed
- Bait is only used up when a fish is hooked.

## 0.12.2 and earlier
The fishing overhaul itself: vanilla-style fish that swim up, nibble and bite; the tension, drag and stamina
fight; 30 fish across fresh water, ocean, deep ocean and legendaries; the catch log; cooking and selling; the
fishing HUD; and custom model support (bundles and .obj).
