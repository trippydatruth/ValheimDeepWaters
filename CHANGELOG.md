# Changelog

## 1.0.4
Ice fishing: drill a hole in the frozen lakes of the Deep North and the Mountain, fish down it for three new fish,
and do it from one of three shelters. Rod holders and a rod rack, and the fixes from the November playtest.

### Added
- **Ice fishing**: the lakes and rivers of the Deep North (and the Mountain's frozen lakes) are walkable ice, and
  nothing can be cast onto it. Drill a hole and fish down it.
  - **Ice Auger** (forge 3): stand on the ice and attack. You set the auger upright and twist its T-handle until the
    bit breaks through, and a real hole opens in the ice. It needs at least 1 m of water underneath.
  - A hole freezes over after 20 minutes, skinning over in the last two. Press `E` to scoop out the slush and keep it
    open as long again.
  - **Ice Fishing Rod** (forge 3): a short rod with a bloodgold reel and an Elaking-fur grip. It fishes only through a
    hole, with a longer hook window there (any other rod works in a hole at half the window). Click at a hole to drop
    the line straight in; hold the click to let it down further. Click with no hole in front and it just says so.
  - **Three fish that bite only under the ice**, each with its own model: the **Lake Whitefish** (5 kg), the
    **Burbot** (8 kg, at night, on the bottom) and the legendary **Ice King Trout** (40 kg, dark slate with ice-white
    markings and glowing eyes). The cold-water fish of the place bite through a hole too.
  - **Two jigs** for them: the **Grub Jig** (forge 3) and the **Rime Jig** (black forge 2).
  - The **Ice Angler's Watch Cap** also makes fish bite 30% sooner through the ice.
- **Ice shelters**, built with the hammer near a workbench. Walk in: each counts as shelter for resting, the camera
  stops at its walls, and a fire inside doesn't smoke you out. Drill a hole inside and the fish bite sooner.
  - **Hide Lavvu** (+10%): a cone of poles under sewn hides, open at the top.
  - **Ice Shelter** (+15%): an igloo of Valheim's own ice blocks with a vent at the top, and an ice bench round its
    back wall under a deer hide, with three seats.
  - **Ship-Tent** (+20%): a Viking ship's tent with dragon-head gables and its own campfire at the back.
  - They can be set down on the lake ice as well as on the ground.
- **Rod Holder** (workbench): a forked stake for the bank or the ice. Set a rod in it with its line out and it keeps
  fishing while you do something else; run several at once. When a fish bites everyone nearby is told, a circle hook
  sets itself, and anyone can take the rod up and fight it. The HUD shows the tackle on that line.
- **Rod Rack** (workbench): stores ten rods.
- A **Weight Unit** setting: catches in pounds or kilograms.
- Deep Waters catches count for **Valheim's own fishing achievements**.

### Changed
- **Mead bottles** are see-through glass, with the mead glowing inside.
- **Boss fish** stir a bigger swirl in the water (16 m, more for the biggest).
- The Cork float is now the **Cork-and-Bone Float**, made with bone fragments instead of a boss item.
- With bait out (no lure), a left click tugs the rod and draws the bait in a little.
- Vanilla fishing rods and baits found in the world (in the frost caves, or dropped) turn into Deep Waters gear.
- Fireflies glow at night, with a small pulsing light.
- Textures are 1K at most, so the download is smaller.

### Fixed
- After looting your grave, equipped items and tackle go back to their own slots.
- The tackle screen's loadouts use tackle boxes you carry, wear, or set down and open; applying a loadout empties the
  slots that weren't in it.
- A fish's extra drops go into your bag when you catch it from a boat.

## 1.0.3
The tackle screen with reels, lines and floats, hook kinds, spear fishing, coolers, Hildir's recipes, and new models
for the baits, hooks, tackle boxes and coolers.

### Added
- **Tackle screen**: the whole rod pictured, with eight slots - rod, reel, line, float, hook, bait (or lure), weight
  and leader - and the rig's stats beside it in sections you can open and close. New slots are added at the end, so
  your saved tackle keeps its place.
  - **Reels** (Bronze to Frostcore, 7 tiers) reel faster, ease the tension and save stamina; **lines** (Leather to
    Moose Sinew, 6 tiers) add line on top of the rod's own. Haldor and Hildir buy old ones.
  - **Three loadouts**: Shift+click one to save your tackle to it, click it to put that tackle on again.
  - **Reels, Lines and Floats** setting (set by the server): turn it off to fish with the rod's own reel and line,
    with floats used like a mead.
- **Eight floats**, one per biome, each with its own model, for the float slot: Quill (fewer nibbles), Cork-and-Antler
  (rivers and lakes), Bone (fish don't flee), Frost (cold water), Linen Bob (longer hook window), Eitr (deep water,
  a violet light after dark), Ember (the Ashlands, an orange light) and Rime (less tension).
- **Hook kinds**: from Small to Giant every hook size also comes as a **circle** hook (three times as long to strike,
  and left alone it sets itself), an **EWG** hook (straightens half as easily, better with worms) and a **treble** hook
  (better with soft baits and on the bottom, but bends out sooner). The tooltip says what each does.
- **Spear fishing**: stab a fish near the surface, or throw a spear at it from the bank.
  - Every vanilla spear works, by its tier (the Abyssal Harpoon best of them); eight **leisters**, the Norse fish
    spears, one per era (Flint to Frostcore), are made for it and take fish up to 3-100 kg.
  - A speared fish goes straight into your bag and counts like a rod catch (catch log, mastery, rank, Fishing skill),
    a little lighter, and trains the Spears skill. Fish deeper than 5 m, legendaries and boss fish need a rod.
- **Coolers** in three tiers, to keep your catch fresh: Wooden Cooler (workbench 2, 12 slots), Iron-Banded Cooler
  (forge 2, 15) and Frost Cooler (forge 4, 24). They hold only your catch: fish, raw fish, fillets, roe and dried fish.
  - Right-click one in your inventory to set it down. `E` opens it (the lid lifts, and frost curls inside while it's
    open) and `Shift+E` picks it up with everything inside. Coolers aren't worn.
  - Nothing spoils. Fish in a cooler, carried or set down, stay **fresh** for 10 / 20 / 45 minutes after they come
    out. A fresh fish sells for 25% more and gives one more material at the Cleaning Table. The tooltip shows how
    long it stays fresh.
  - A cooler weighs what's in it, and keeps its contents wherever it goes.
- **Hildir's stock in recipes**:
  - **Sparkler Popper** (forge 1): a topwater lure; after dark it fizzes and lights the water, and fish bite 40% sooner.
  - **Angler's Flare** (workbench 2): carry one and it goes up by itself when you hook a boss fish - a firework over
    you, a ping on everyone's map and a shout naming the boss.
  - **Ice Angler's Watch Cap** (+15% hook window, keeps the frost off) and **Sun Angler's Cap** (fish bite 25% sooner
    by day), made from her caps and worn on their own.
- **Cut Bait**: cut at the Fish Cleaning Table from any one baitfish, three at a time. It draws catfish, bass,
  halibut, lingcod, sea bass and coral cod.
- **Tackle boxes follow the biomes**: four crafted (Meadows to the Plains, with a new Black-Metal Tackle Box) and three
  from Hildir (Dvergr-Mended, Charred and Rime-Crusted), each with its own look and a faint biome effect. Her lost
  boxes turn up in the Mistlands, Ashlands and Deep North.

### Changed
- **New models**: every bait (restyled, the snowy Frost Bait and a new Northern Bait), lures with real J, treble,
  circle and EWG hooks, the hooks, the tackle boxes (painted wooden boxes with a tray), the coolers (a wooden ice
  chest), the reels and lines, the cleaning table, and the Angler's Flare.
- **Mead bases are made at the Mead Ketill**, like vanilla's (level 1), then fermented as before.
- **The chum buckets** each need 2 Cut Bait. An existing save's recipes update too, unless you changed them.
- **Cooked fish** look like their raw fish, browned and grill-marked, and eat like cooked meat. The health a very
  big fish gives levels off instead of running into the hundreds.
- **A quick tap of the cast** drops the bait about 3 m in front of you, for fish you can see.
- **The Fisherman's coat** no longer clips when you crouch, sneak or sit; the overalls and coat have new folds and
  shaded edges.
- Faster checks in the code that runs every frame.

### Fixed
- The bait or lure flies out with the float and goes into the water when the cast lands, not as you let go.
- Dropped baits, lures, hooks and weights show one model, at a size you can see (they showed a bunch of tiny copies).
- The **Runed Lure** is a lure: it carries its own hook and no longer asks for one.
- Topwater lures float level on the surface instead of standing on end under it.
- The Bullet Weight and Egg Sinker have real holes bored through.
- Dishes show at their real size on the ground and on item stands, and feasts set side by side no longer push each
  other around.
- The tackle screen's slots could come out a row low.

## 1.0.2
The Fisherman's gear remade so it no longer clips, and the knife rack goes on walls.

### Changed
- **Fisherman's gear is painted onto the body**, the way Valheim's own armour is, so it bends with you and can't clip:
  - **Striped Fisher's Shirt**: the stripes are painted on; no separate shirt, no gap at the armpits.
  - **Oilskin Overalls**: overalls and rubber boots painted on, drawn over the shirt, with a short rubber cuff round
    each boot top.
  - **Oilskin Coat**: the sleeves and body are painted on over the shirt and overalls; the collar and the skirt are
    the only parts left as a model, matched to the paint. A wide belt with a brass buckle sits at the waist and cuffs
    finish the sleeves. The skirt follows your legs, swings in the wind and trails a little as you move.
  - The coat and overalls have folds and wrinkles, so they keep their shape and volume.
  - **Sou'wester**: smooth-shaded, and lit the same way as the coat.
  - Dropped on the ground, each piece still shows its folded model.
- **Filleting Knife Rack** can be hung on a wall, above the Cleaning Table.

## 1.0.1
Fixes from playtesting (mostly multiplayer), a rod slot, weights and leaders, and tackle boxes.

### Added
- **Rod slot**: the tackle panel now has Rod, Bait, Hook, Weight and Leader slots. A rod in the rod slot takes no inventory space;
  right-click it or press Alt+F (Rod Key in the config) to take it in hand or put it away. Right-clicking a rod in
  the inventory moves it into the slot and takes it in hand. It repairs at its station from the slot, and moves into
  the inventory by itself when you upgrade it. The panel shows the rod's level, line, cast and wear.
- **Weights and leaders** (Tackle.json, two new tackle slots): fish now bite best at the depth they feed at, and the
  rig decides how deep your bait sits.
  - **Leader Line**: with a float, the bait hangs at the leader's length - set it with - and + on the tackle panel.
    Without one it hangs about a metre down.
  - **Weights** take the bait to the bottom with no float, and cast further: Split Shot, Bullet Weight (the Texas rig:
    on a soft lure it works the bottom), Egg Sinker (the Carolina rig: with a leader the bait drifts just off the
    bottom and fish take it more readily) and Pyramid Sinker.
  - Bottom feeders (catfish, cod, halibut, lingcod, grouper, gobies, sculpin and more) want bait on or near the bottom.
  - Water moves a weight that's too light for it: waves, wind and storms drag it along the bottom, and nothing takes a
    bait that's being dragged. Heavy weights hold.
  - Weights and leaders are lost only when the line snaps. Each has its own model and icon.
- **Tackle boxes** in four tiers: Tackle Box (workbench, 8 slots), Iron-Bound (forge, 12), Silver (forge, 16) and
  Dvergr (black forge, 24). They hold tackle only (bait, hooks, lures, weights, leaders, floats) and keep it inside
  wherever the box goes.
  - Wear one in the utility slot: it's carried by the handle in your right hand when that hand's free, at your hip
    otherwise. K opens it; Shift+K sets it down as a chest whose lid opens for anyone using it; Shift+E picks it up.
  - Your bait, hook, weight and leader slots refill from the box you're wearing, and B / H cycle through it too.
  - A box weighs what's in it.
- **Move the tackle panel**: drag it by its wood to wherever you like in the inventory screen; it stays there.
  Double-click it to put it back under the inventory.
### Fixed
- **Other players' fishing shows again**: their line, float or lure, the fish on their hook and their rod's bend
  (the game doesn't load other players' inventories, so the mod now goes by the rod they're holding).
- **Rowing for other players**: the rower stays on the bench and their arms follow the oars on everyone's screen.
- **Flies are the same for everyone**: nearby players see the same swarms, and a fly someone catches or spooks is gone
  for everyone.
- The Fishing Boat no longer takes damage when you cast from it in deep water; only a storm's big waves wear it.
- Logging out while seated in the Fishing Boat no longer drops you into the water under it when you log back in.
- A rod you didn't craft yourself (bought, given or found) now shows in its station's Upgrade tab.
- `defaults_offered.json` is now `defaults_offered.dat`, so mod managers' config pages list only the files you edit (it moves over by itself).
- Boss fish no longer swim about on their own: they only come when their lure summons them.
- Bluegill bait (on the hook and swimming) uses the bluegill's own model.
- The pufferfish no longer looks like a different fish in the water.
- The Fish Cleaning Table has its icon in the crafting panel.
- The Fisherman's Hat hides your hair (no more hair poking through it).
- The tackle panel (bait and hook slots) is no longer hidden behind the inventory when another mod makes the inventory bigger.
- Mod managers' config pages show only the settings: the models now install beside the mod in `BepInEx/plugins`
  (your own models still go in `BepInEx/config/ValheimDeepWaters/Models` and win over the shipped ones).

### Changed
- **Lures are mid-game**: made at the forge, each with a hook (a Large Hook for most, Heavy or Giant for the late ones, a Small Hook for the Feather Fly), and fewer at a time.
  Boss lures need a hook too. Your Baits.json updates unless you changed a lure's recipe yourself.
- **Worm mounds can be cleared**: one hit from any weapon or tool breaks one up, and hoeing or digging the ground
  under it does too.
## 1.0.0
The first public release. Everything from the development builds below is in it; these are the changes since 0.14.0.

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

- **Endgame**: boss lures cost more each time you land their boss (and the Bog Witch charges more); the Leviathan needs
  two materials from each of the seven boss fish; the Allfather's Rod (every boss landed) and Njord's Regalia, a crown
  made from the four relics (every boss landed three times): a runed bronze crown set with green and blue stones, worn on
  the head. The Allfather's Rod is a hand-made model:
  red wood, gold guards and reel, glowing runes, Mistwalker mist, snowflakes and ribbon lightning.
- **Rod effects follow the bend**: the top rods carry their effects along the rod as it bends. The Ashwood Rod now has
  Dyrnwyn's flames, the Frostwood Rod snowflakes and a frost cloud.
- **Rare variants**: golden (1 in 300) and albino (1 in 150) versions of every ordinary species, with tinted icons and
  models; they don't stack with ordinary fish, give rank points, sell for more and are tracked in the catch log.
- **Fights everyone can see**: players nearby see your line, float or lure and the fish on your hook (its own model,
  running, leaping, thrashing; a boss at its size, the Queen Eel circling, rearing and lashing its tail), with the splashes, bites and line snaps, and hear your reel; landing a fish tells the
  players around you.
- **Rewards rework**: catch log rewards every five species, biome sets (catch every fish of a biome in that biome for
  its bait, coins and rank points), the odd valuable inside a catch (amber, rubies, silver necklaces by where you fish), rank points for a
  personal best, a gift at each angler rank, and Hildir's bounty prizes are now a Yule Hat, Thunder Stone, the Horn of
  Ægir, a Dverger Circlet and Megingjord.
- **Catch log redrawn**: a sidebar with your rank (and what the next one unlocks), the reward ladder and biome sets;
  species cards with the bait on its own line, the count to the next mastery tier and the record. The cursor is free
  while it's open: click a biome to filter, the arrows or the mouse wheel to turn pages.
- **Fimbul Hook** is for big fish only (25–300 kg); the Golden Hook stays the one hook that suits every fish, and now
  sets the hook more easily too (+5% hook chance, +15% hook window). Hooks can carry a HookBonus and HookWindow in Hooks.json.
- **Relics**: each comes from one place and takes its own slot (no stacking): the Horn of Ægir from Hildir's 15th bounty,
  the Pearl of Njord for a full catch log, the Golden Hook rarely from inside legendary fish, and Jörmungandr's Scale
  rarely from sea serpents you kill. Boss fish no longer drop relics; the Horn is no longer found in fish.
- **Dyed gear repairs**: Hildir's Bog-, Frost- and Mist-Dyed Fisherman's gear repairs at the workbench like the rest of the set (it still can't be crafted).
- **No accidental recast**: still holding the pull (left click) as a fish lands no longer casts again straight away; let go and press again to cast.
- **Bait targets fish**: each bait and lure goes for a few fish (other fish take it only rarely), so you choose your
  bait for the fish you want. Bait tooltips list what they catch, the catch log shows each species' bait, and a cast
  says when nothing there goes for yours. Data files take the new bait lists once. The vanilla rod can't be used.
- **Species mastery**: 10 / 25 / 50 of a species (1 / 3 / 5 for legendary and boss fish) for Bronze, Silver and Gold - it
  bites more readily, fights weaker, then runs bigger for you - with rank points for each tier and a Gold Trophy Plaque
  (a wall piece with the species mounted on it, gold-plated) to build at Gold. The catch log shows each species' tier.
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

## 0.14.0 (development build)
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

## 0.13.0 (development build)
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
