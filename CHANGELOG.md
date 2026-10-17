# Changelog

## 0.14.0
### Added
- **Twelve fish get their own models**, each its own kind of fish (Sketchfab models, credited in
  Mesh/Sourced/CREDITS.md), rigged and animated like the bosses, with their own icons: Trout, Mackerel, Halibut (swims
  flat), Frost Sculpin, Frost Char, Greydwarf Goby (mossy green), Bonemaw (a viperfish), Jotunn Perch, Odin's Eye (an
  opah), Thor's Hammerhead, Serpentfin (an oarfish) and Surtling Sardine. Five more on Tripo models: Rimejaw Cod (frost-rimed),
  Glacier Grayling (glowing fin dots), Lingcod, Mistfin (pale, misty, faint glowing flecks) and the Fenringfin (a wolffish,
  swimming like an eel). Fish with open mouths keep them shut in the idle swim and snap them open on the line.
### Removed
- **Dvergr Dace**: taken out. It leaves an existing fish.json once, and baits that targeted it lose it (trout takes its
  place where a bait didn't already have it).
- **Boss weather**: from the omen to the end of the fight, a boss fish brings the weather of the boss it's named
  after (Eikthyr's storm, the Elder's mist, Bonemass, Moder, Yagluth, the Queen). It's shared: everyone within about
  150 m of the encounter gets the weather and the boss music, including players who walk up mid-fight.
- **The Queen Eel is a sea serpent**: twice its old size (7.5 m) swimming, hooked and landed, with its own fight. Fresh,
  it circles you in wide sweeps, its back rolling up through the surface. Enraged, it charges straight at you (reel in
  the slack or it shakes the hook) and rears out of the water, head high, before crashing down - pull back while it's
  reared to tire it fast. Desperate, it lashes the water with its tail as well.
- **Deep North**: a seventh boss fish, the **Fimbul Salmon** (Kall Fimbulbringer's), summoned in Deep North rivers at
  night with a **Crown Lure** from his Crown Jewel - the biggest fish in the mod (4.6 m, up to 250 kg), with the
  Frozen King's weather and music; its Rimefrost Fin forges the **Fimbul Hook** (never bends, kept half the time).
  Three new Deep North fish (Rimejaw Cod, Glacier Grayling, Frost Sculpin), **Northern Bait** (seal blubber and
  lingonberries, Valheim's Deep North bait look), the **Frostwood Fishing Rod**, the **Ice Spoon** and
  **Frostcore Jig** lures, **Blubber Chum** and **Lingonberry Angler's Mead**.
- Every Deep North item but the three new fish has its own model and rendered icon: the Crown
  Lure, Ice Spoon, Frostcore Jig, Northern Bait, Frostwood Rod, Fimbul Hook, Blubber Chum and Lingonberry Mead. The
  seven boss materials (Storm Barbel, Elder Scale, Mire Whisker, Frostwyrm Scale, Ember Gill, Queen's Fang,
  Rimefrost Fin) have their own models too, and the Fimbul Salmon its icon.
- Better rods hold much more line: from 45 m on the Copper rod up to 260 m on the Leviathan (Wooden stays 30 m).
  A data file still on the old defaults is updated; line you set yourself is kept.
- **Working jaws** on the boss fish with open mouths (Fimbul Salmon, Moder Scale Fish, Yagluth Gill, Eikthyr Elver):
  they breathe while swimming, snap shut when thrashing and gasp on land.
- **Animated fish models**: a rigged fish with Swim, Thrash and Flop animations swims, thrashes on the line,
  flops on land and holds still as a trophy. Static models still work.
- **Rigged rods**: a rod model with a skeleton (bones `Rod.1`..`Rod.N` up the blank, `Rod.Tip`, `Rod.BendDir`,
  `Reel.Spool`, `Reel.Axis`) bends toward the line as a fish loads it, flexes back on the wind-up and whips on the
  cast, and its reel winds while you reel and spins back as line pays out. The line leaves from the bent tip.
- An animated `bait_worm` model is used for rain worms too: they wriggle with its Swim clip as they crawl.
- An animated `bait_fly` model is used for flies too: they hover with its Swim clip (wings beating) and buzz
  off with Thrash when spooked.
- A totem with a model prefab in a bundle (`buff_totem_fisher`, `buff_totem_njord`) is used whole in place of the
  banner it's built from, with a collider fitted to it. The Fisherman's Totem is now a carved hooded figure with
  glowing runes, and the Shrine of Njord is the same figure in sea-weathered blue-grey driftwood with turquoise
  glowing runes. Totems place like the vanilla ward, work for everyone fishing near them, and show what they do
  (and whether you're in reach) when you hover over them.
- An item model made of several meshes or materials is used whole (the plain model path keeps one mesh). The three
  chum items are now wooden buckets that stand upright on the ground: Chum Bucket packed with minnows, neck tails
  and meat; Bloodbait Chum with minnows, leeches, entrails and a bloodbag in blood; Abyssal Chum with tentacles
  curling over the rim, glowing ooze and roe, and chitin.
- Chum isn't drunk any more: using a chum bucket sets it down on the bank in front of you. Everyone sees it, and
  the water within its radius is chummed for anyone fishing there until it runs out and sinks away (hover over it
  to see the time left). Buckets of the same kind don't stack. It won't go down in the water, on steep ground, or
  where there's no water close enough to reach.
- The Horn of Ægir is blown, not drunk, and you keep it: your viking raises it to their mouth in their hand, everyone nearby
  hears the blast, and the fish come. Then it needs a day's rest before it can be blown again. The sound is an
  AudioClip named `horn_of_aegir` in any bundle, or `horn_of_aegir.wav` in the Models folder.
- The Pearl of Njord is a glowing pearl set in a silver clasp on a piece of belt. Worn, it's pinned to the front of
  your belt, and everyone sees it. Jörmungandr's Scale is now a cloak of dark sea-green serpent scales with
  iridescent rims and a gold serpent's-eye clasp (the linen cape, retextured).
- **Fishing Boat**: a one-man rowing boat built with the hammer at a workbench (24 wood, 8 resin, 4 deer hide).
  Sit on the middle bench facing the stern and row: both oars sweep through the stroke, dipping in on the pull and
  feathering back, and your viking leans into each stroke with their hands on the handles. Turning eases the inside
  oar. No sail, so it goes at rowing speed only. Its hull is planked in the same weathered ship planks as
  the Karve and Longship, with iron oarlocks. A passenger can sit on the stern seat, facing the rower. Stand at the holdfast in the bow, as on the
  Longship, to brace against rough water. Everyone aboard and nearby sees the rowing.
- Meads and tonics are now a corked glass bottle with twine at the neck: amber Angler's Mead, blue Steady-Hand
  Tonic and green Troll-Grip Mead, deeper in colour with each tier, the major ones glowing.
- An animated `pickable_worm` model makes worm mounds wriggle: the worm sticking out of the soil plays its Swim
  clip, and only the worm disappears when picked (the soil stays until it regrows).
- Animated bait on the hook plays a **`Hooked`** clip if the model has one (dangling and curling from the hook),
  falling back to `Swim`; it still plays `Thrash` when a fish nibbles.
- **Lures carry their own hook**: a lure goes in the hook slot (the slot reads "Lure") and needs no bait. The
  bait slot then becomes an optional "Trailer" slot for trailers made to go on a lure. The boss lures never straighten
  or turn their boss away, and are still used up when it bites. A lure already sitting in your bait slot moves over
  by itself.
- **Fishing looks and feels like vanilla**: the float flies from the rod tip in a real throw's arc (higher and longer
  the further you cast) with the rod's swing sound, and lands with vanilla's plop. It then stays where it lies while you
  move about: walk toward it and the line hangs slack, walk away past the line you've let out and it's dragged after you,
  and reeling takes up the slack first. The line is vanilla's own, sagging as it slackens and thinner the further out.
- **Working the line back**: hold right click with nothing on to reel the float or lure back through the water instead
  of ending the cast (Shift as well to wind straight in). Lures cast half again as far, fish find them faster and chase
  them down, and they only strike a lure while it's moving or just after it stops; one left sitting is ignored.
- **Nine lures and three trailers**: the Feather Fly, Flint Spinner, Leather Grub, Bronze Spoon, Finewood Crankbait,
  Guck Crawler (Texas rig), Bone Jig, Silver Swimbait and Linen Popper, from the workbench and forge, each drawing
  its own fish and rated for its own range of fish weights. The spinner and jig take a trailer: a Curly Tail, Boar
  Rind or Feather Skirt. Everyday lures last until the line goes.
- **Kinds of lure**: spoons, spinners, crankbaits, jigs, soft plastics, Texas rigs, swimbaits, topwater lures and flies
  each draw their own fish. The fish a lure draws come far more readily and bite more keenly, and others mostly ignore
  it. A trailer on a lure draws its own fish too, and makes the lure's fish keener still. There's no float when you
  fish a lure: the line runs into the water where the lure swims, and a nibble twitches the line and nods the rod tip.
- **Boss lures**: each of the six now has its own model, glowing in its boss's colour: an antler-tine spoon with a
  lightning rune and a knapped flint hook set into it, a jointed root swimbait, a bone jig in a ball of ooze, a silver dragon-scale spoon set with a frozen
  tear, a black-metal spinner round a surtling core, and a chitin jig with a tentacle skirt. They're crafted from the
  boss's own drops where it gives several (one Moder kill makes five Wyrm Lures), with the trophy only for the Elder
  and Bonemass, at the biome's station: workbench, forge, artisan table and galdr table. Lures in an existing
  `Baits.json` get the new recipes unless you changed them.
- **Boss fish**: the six legendaries named after bosses are summoned with lures made from boss trophies, in
  the right water and weather, after an omen. They fight with a boss bar, their boss's music and enraged and
  desperate phases, and drop a trophy, a boss material and a server-wide announcement. The materials craft the
  new **Leviathan Rod**. The other three legendaries are mini-bosses: the same fight, no fanfare, a trophy.
- **All 12 vanilla fish can be caught**: landing one gives the real vanilla item, so vanilla cooking and
  recipes work. Perch, Pike, Tuna, Giant Herring, Anglerfish and Northern Salmon replace the Deep Waters
  fish of the same kind, and Tetra, Trollfish, Grouper, Coral Cod, Pufferfish and Magmafish are new. Vanilla
  fish bite Deep Waters bait. An existing `Fish.json` is updated automatically.
- **Rain worms**: when it rains, worms come up out of bare ground around you. Pick them up before they
  burrow back down.
- **Worm mounds** (wriggling soil) grow in forests where red mushrooms do and regrow after picking. Each
  gives 1 worm usually, 2 sometimes, 3 rarely, and one more in the rain.
- **Flies** come in swarms along rivers, lakes and the coast, shown with Valheim's own flies effect and
  wing buzz (fireflies at night) until a fly model is added.
- Painted, Valheim-style inventory icons for every rod, hook, bait and buff item. The hooks, baits, boss fish, every
  rod, the chum buckets, meads, totems and relics now use icons rendered from their 3D models (the worm and the
  Queen Eel coiled up).
- `vdw_debug worms` shows the worm mounds near you and whether flies or rain worms can be out right now.
- **Angler animations**, seen by everyone: casting uses Valheim's own draw and throw; with the line out the rod
  is held in the left hand and the right hand winds the reel (Valheim's own reeling pump is gone); setting the hook
  sweeps the rod up and back; a twitch pops the rod tip; a nibble on a lure nods it; a running fish drags the rod toward the water.
  Each player shares their fishing state, so other players see them cast, reel, pull and fight.
- **Pull back** (hold left click with a fish on): the angler hauls the rod up and leans back, bending it hard. It
  tires the fish faster and wins a little line (not while it runs), but strains the line and costs stamina - pump
  with left click, then wind down with right click.
- The drag and reel speed gauges show their setting with lit pips only (DRAG in front, REEL on the bigger dial
  behind); the exact value shows in the middle of the screen as it changes.
- **Retrieves.** How you work a lure matters: Slow Roll, Steady and Burn (by reel speed), Stop & Go (reel and
  pause), Twitch (left-click rod twitches while reeling) and Hop (twitches without reeling). Each lure kind has
  retrieves it swims right on and each retrieve draws certain fish; a good match brings them more and makes them
  likelier to strike, a poor one gets follows that turn away. The HUD names your retrieve (green when it suits the
  lure).
- **Reel speed** on Alt + mouse wheel (or, like drag, the mouse wheel or the mouse side buttons: Drag Control and
  Reel Speed Control in the config), shown as a bigger dial behind the drag gauge: it sets the retrieve speed and the fight reel
  speed (a slower reel strains the line less). Shift reels at full speed, now in fights too, and a lure burned in
  with Shift can still draw strikes.

### Changed
- The bobber floats lower, with 55% of its height under water (was 40%), so a stick float sits with its keel and
  lower body submerged and only the top showing.
- **Models are used at exactly their size in Unity** (1 unit = 1 metre). The automatic sizing is gone: rods no
  longer fit `ModelLength`, the bobber, baits and hooks are no longer scaled down, and `ModelScale` / `ModelLength`
  in the JSON files do nothing. Re-export models at the size you want them in game.
- Relics: the Pearl of Njord, Jörmungandr's Scale and Golden Hook now only come from boss fish (1 in 4 per boss,
  one you don't have yet first). The Horn of Ægir is rarer from legendaries (5%), and bait fish never hold a relic.
- In multiplayer the server's gameplay settings (fish, worm mounds, rain worms, flies, rod wear) apply to
  everyone, and every player must have the same version of the mod.
- Updates now add new fish, bait, rods, hooks and buffs to your existing data files, keeping your edits.
- The vanilla fishing rod and vanilla fishing baits can no longer be bought or crafted.
- The Deep Waters Perch, Pike, Bluefin Tuna, Herring, Abyssal Angler and Salmon items are gone (they're now
  the vanilla fish). Any already in an inventory disappear.
- The Deep Waters Cod, Troll Trout and Ashscale are gone too, being too close to the vanilla Coral Cod, Trollfish and
  Magmafish (baits that targeted them now target those). They're taken out of your `Fish.json`.
- The fishing hats and capes are gone (Fisher's Hat, Angler's Hood, Seafarer's Cap, Sea-Wolf Cape, Netweaver
  Cape, Ashen Angler's Cloak). They're taken out of your `Buffs.json` too, and any already owned disappear.
- The config file is down to what players need: HUD, reel volume, rod wear, keys, and on/off and amount
  settings for fish, worm mounds, rain worms and flies. Fishing balance is now built in. **Delete your old
  `trippy.valheimdeepwaters.cfg`** so it's recreated without the removed settings.
- Worm mounds grow half as often as mushrooms by default (`Worm Mound Density`).
- Much less log output.
- The Pearl of Njord is a new model: a whole leather belt with the pearl set in front, worn in place of the vanilla
  belt. `vdw_debug pearlfit <scale> <up> <forward>` fits it in game.
- The Rune of Njord has its own model: a silver rune pendant on a cord, its blue ring glowing, worn round the neck
  (in place of the vanilla belt look). `vdw_debug runefit <scale> <up> <forward>` fits it in game.
- The worn Pearl of Njord belt and Rune of Njord necklace are skinned to the wearer's skeleton when put on, so they
  bend and twist with the body instead of riding stiffly on one bone.
- Holding a rod with no line out, the left hand now holds the rod over Valheim's own hold animation.
- The release ships its model bundles packed (`.vdwpak`), so asset rippers can't open the meshes and textures
  straight from the Models folder. Plain `.bundle` files still load (and win over a packed copy), so custom models
  work as before. The loose `bobber.obj` is no longer shipped (the bobber is in the rod bundle).

- Baitfish swim in the world too: minnows, large baitfish and sea shrimp school in rivers, lakes and the sea with
  their own animated models. Catch them on a rod as before; one that flops onto land can be picked up as its bait.
- Deep Waters fish can be made into vanilla **Raw fish** at the food preparation table (like vanilla's own fish),
  so they go into Fish Wraps, Fish Soup and the other fish dishes. Bigger size classes give more raw fish.

### Fixed
- Rods other than the Leviathan sat rotated in the idle hold, the butt floating out to the right of the hand: the rod
  turned about its reel instead of the grip in the hand. It now turns about the grip, so every rod sits in the hand.
- Minnows, large baitfish and sea shrimp swam up to the bait and fought on the line as the vanilla bait model; they
  now use their own animated models.
- Boss fish music only played while the fish was being fought; it now plays for the whole encounter, from the omen
  on the water to the end of the fight (at Valheim's music volume).
- The bite message is just "FISH ON!" (the key prompt below already says to right click).
- The float's nibble splash never played (the vanilla rod's float had no nibble effect set); it now uses the game's
  own `fx_float_nibble`.
- The Thunderstore package left out the Horn of Ægir's blast (`horn_of_aegir.wav`), so a packaged horn was silent.
- Fishing Boat: climbing the ladder put you over the far side (it still used the raft's landing spot); it now sets
  you on the floor inside the gunwale, facing in. The rower faces the passenger without a command, sits further onto
  the bench and higher, and no longer shakes while rowing (the animator only reposes on physics steps, and posing on
  top of the last frame's pose stacked up; a holdfast thumb trembled the same way). The bow
  holdfast stands with its front foot up on the bow deck, a little left and turned slightly in, hands in a looser curl. `vdw_debug boatseat
  <rower|passenger|holdfast> <right> <up> <forward> [turn]` nudges a seat in game (replaces `rowerflip`).
- Fishing Boat: the rower's seat is placed when the boat is in the world (the raft's controls didn't keep where
  the prefab put them, so the seat sat at the keel, unturned). Breaking the boat no longer throws out the raft's
  logs and mast: it leaves broken hull planks, plank shards and its two oars tumbling into the water, which clear
  away after a while. Holding fast, the forearms hang from the elbows. Rows about a third faster, and has no sail force at all (wind never moves it).
- Fishing from a boat, the catch (and any bait fish, find or boss drops) goes straight into your inventory, or
  lands at your feet if it's full, instead of dropping over the side.
- Horn of Ægir: no longer upside down; it's raised higher and the hands grip the horn itself.
- Landing some fish failed every frame ("The Object you want to instantiate is null"), leaving the fish stuck on
  the line at your feet. Dropped catches, bait and rewards now always spawn, and a failed catch still ends the cast.
- A fish reeled in from a high bank could get stuck in the ground under your feet and never land. It now lands
  as soon as it's dragged out of the water.
- Animated fish lying on the ground showed a second, still copy of the model (the one meant for item stands).
- Animated rain worms were half buried and hard to spot.
- The Copper, Finewood, Ancient Bark and Silver rods were under half the wooden rod's length. They're now
  rigged like it: 2.85 m long, held by the grip, bending under load, and their reels turn (the centre-pin drum,
  or the spinning reel's crank).
- The Black Metal, Yggdrasil, Ashwood, Haldor's Gilded and Leviathan rods have their own models instead of
  borrowing the wooden rod's: black metal with gold trim and a linen grip; world-tree wood wrapped in roots with
  glowing eitr runes and core; charred blackwood with ember cracks and a flametal conventional reel ringed with
  flame tongues; gilded mahogany with a red grip, a gold conventional reel set with an emerald, and Haldor's mead
  horn; and the Leviathan's scaled blank with an abyssal spinning reel on a curved stem (its spool glowing in the six
  sinew colours and crowned with teeth), a fang at the tip and six glowing sinews, one for each great fish. All bend and reel like the others.
- A rigged rod is now held by its grip (marker bone `Rod.Grip`) instead of at the vanilla rod's pivot, and turns
  slightly so it runs through the left hand too.
- Animated fish and bait on the ground stood on end or hovered: their collider and resting side were measured
  from hidden meshes. They're now measured from the animated model only.
- Worm mounds weren't saved properly and disappeared when you left an area and came back.
- Worm mounds sat so low in the ground that grass hid them.
- Flies bolted before you could get close enough to catch one (any walking counted as noise). Now they only flee
  from running or swinging nearby, rarely from walking right up to them, and never from sneaking. A hovering fly
  also no longer filled the log with "Rotation quaternions must be unit length".
- Flies were a near-invisible dot and only appeared on a very narrow strip of shore.
- The fly showed its see-through wing material on its body (Unity reordered the model's material slots); the wing
  slot is now found from the wing bones.
- The Horn of Ægir was inside out, and so were the leeches in the Bloodbait bucket.
- A totem's buff showed the banner icon instead of the totem's.
- Blowing the horn and setting down a chum bucket no longer play the eating sound.
- Wearing the Pearl of Njord no longer shows the vanilla belt under it.
- The Ashwood and Haldor's Gilded rods have their conventional reels and guides on top of the rod, as real
  baitcasting rods do; the centre-pin and spinning reels still hang below.
- The catch log no longer reloads your whole log every frame while it's open.
- Ctrl+click on bait or a hook threw it on the ground instead of putting it in its tackle slot.
- `vdw_give` and `vdw_debug` worked for any player without `devcommands`; they now need it.

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
