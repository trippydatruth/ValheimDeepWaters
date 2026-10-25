# To check in game

Things built and installed to the Test profile that haven't been tried in game yet. Tick them off (or delete the line)
once they work.

- [ ] **Tackle models and icons:** Split Shot, Bullet Weight, Egg Sinker, Pyramid Sinker and Leader Line show their own
  icons in the inventory and tackle slots, and their own models when dropped on the ground (not nails / leather scraps).
  Check their size on the ground reads well (they're shown 1.5x life size).
- [ ] **1.0.1 multiplayer - needs a second player:**
  - Watching your friend fish you now see their line, float, hooked fish and rod bending (this was invisible before).
  - Your friend rowing the Fishing Boat: they sit on the bench (no sliding), their arms follow the oars as they row.
  - Flies: stand near your friend on a shore; you both see the same fly swarms in the same places. One of you catches
    a fly, it's gone for the other. Spook one (run at it), it flies off for both.
- [ ] **Fights everyone can see (#29) - needs a second player.** You fish, your friend watches from nearby (then swap):
  - They see your line from your rod tip to the water, and your float on it (the Lantern Float glows at night if you
    have it on). With a lure there's no float, just the line going in.
  - A nibble twitches your float for them; a bite dunks it with a splash.
  - Once hooked they see the fish on the end of your line: the right species, about the right size, running, leaping
    and splashing; your line snapping, and the landing splash.
  - They hear your reel while you wind.
  - When you land a fish they get "<you> landed a 1.2 kg Perch!" top left (only within 50 m - try from far away too:
    nothing). A boss fish is announced to the whole server as before.
  - Nothing's left floating after you stop fishing, walk off, put the rod away or log out.
- [ ] **Boss fights for watchers (#29 step 2) - needs a second player.** Summon a boss fish (`vdw_debug boss queen_eel` then
      cast in deep water off the Mistlands, or any boss) while your friend watches:
  - They see the boss on your line at its full size, leaping and splashing as you see it.
  - Queen Eel: they see its back humping up as it circles, its charge's bow wave, it rearing up out of the water and
    crashing down, and its tail slaps - with a short camera rumble if they're within ~25 m.
  - The landing is announced to the whole server.
- [ ] **Rare variants (#23):**
  - (Golden confirmed 2026-10-19: on the line, on the ground, its gold icon and tooltip.) Still to try: `vdw_debug variant
    albino` - pale on the line and the ground, pale icon, +5 rank points; and a golden one of the mod's own species
    (bass, catfish, trout).
  - It doesn't stack with ordinary fish of the same size (pick both up, drag one onto the other); two golden ones do.
  - Dropped on the ground and hung on a Trophy Mount it stays golden / pale.
  - Catch log: the species' card lights its gold / pale mark; the sidebar's "Rare variants: x of y" goes up.
  - Sell panel: Haldor offers 5x (golden) / 3x (albino); Hildir 6x / 4x. `vdw_debug rarefish perch golden` gives one
    to try with a vanilla species too.
  - (With your friend: they see it golden on your line too, and the landed message says "golden".)
- [ ] **Endgame (#24):** (`vdw_debug master <boss fish id> <count>` sets how many times you've landed a boss: ids eikthyr_elver,
      elder_bass, bonemass_catfish, moder_scale, yagluthgill, queen_eel, fimbul_salmon)
  - Lure costs: at the workbench, note the Antler Lure's recipe; `vdw_debug master eikthyr_elver 1` - everything but the
    Hard Antler needs one more; at 5 it stops at three times the first amounts. The Bog Witch's price for it goes up too.
  - The Leviathan Rod now asks for two of each of the seven boss materials (Rimefrost Fin included).
  - The Allfather's Rod isn't in the black forge list until every boss is at 1; then it shows (Leviathan Rod + 3 of
    each material) and crafts. It's your Fishing+Rod model now: red wood with gold flame guards, gold guides and the
    octagonal gold reel with its line running up through the guides to the tip, plus glowing blue runes carved between the guides, blue guide inserts, a glowing gem on the
    reel and a faint glow on the spear tip. Check: the hand holds it just below
    the reel, the crank turns while reeling, the rod bends, the line leaves from the tip, and it isn't too big or small
    in the hand (it was scaled from 5 m to the usual 2.85 m). Fixed since the first try: no white sheet between the line
    and the blank when it bends against a fish, the crank on the other side, effects: Mistwalker mist, snowflakes and ribbon lightning joined point to point, all following the rod as it bends (no streaks across the sky), brighter gold,
    and bolder runes you can read.
  - Njord's Regalia isn't in the list until every boss is at 3; then it takes the Pearl, Scale, Horn and Golden Hook
    (gone after) + 2 of each material. Its own model and icon (the bronze runed crown).
    Worn, it sits round the brow in place of the circlet (no circlet showing) and moves with the head; the front
    pearl faces forward. If it floats, sinks into the head or sits backwards, tell me which and I'll refit it.
    It shows the same on a friend. All its effects are in the tooltip.
  - Catch log: "Boss fish landed: x of 7" and the next unlock's line in the sidebar; boss cards say "Landed x3".
- [ ] **Rod effects follow the bend:** the Ashwood Rod now has Dyrnwyn's flames (orange light), the Frostwood Rod the Staff
      of Frost's snowflakes (ice-blue light). On every top rod (Yggdrasil, Ashwood, Frostwood, Leviathan, Allfather) the
      effects should stay on the rod and curve with it while fighting a fish, not trail off behind you or float straight.
      Thinned since the first try: half as much on every rod, Allfather's lightning bigger (confirmed good). Ashwood's flames now patchy
      (a different size on each segment) and much lighter; Frostwood uses the Allfather's snowfall, slightly more,
      plus Frostner's frost cloud; Ashwood's flames turned up a little.
- [ ] **Njord's Regalia, new crown model** (your edited crown, finished by art-tools/finish_crown.py): your row of four gems
      copied to all four sections (16, green and blue), clean unwrap, painted bronze with copper edges, crisp runes round
      the rim, on the shield and on each diamond point, scaled fish. Check it on the ground, in the icon and worn: it should
      sit round the brow - placement tuned in game and now built in (a fresh install, like your friend's,
      should show it the same way).
