# Vanilla weapon effects (for reuse in Deep Waters)

Found in the rip (`Valheim_DeepWaters\FishingRod\ExportedProject\Assets\GameElements\Items\weapons\`) on 2026-10-12.
Every effect below is a child object of the item prefab, so the mod can reuse it **at runtime** the same way it reuses
the vanilla fishing line and splash: `ObjectDB.instance.GetItemPrefab("<prefab>")`, `transform.Find("<path>")`,
`Instantiate` it under our object (rod tip, lure, fish bone), then fix its scale. Nothing is copied into our bundles.
Hit effects (`fx_*_hit`) and projectiles are separate prefabs in `ZNetScene` and can be played with an `EffectList`.

Paths are from the prefab root. `attach/UpgraderGlow` (a faint blue glow plus a light) is the generic "upgradeable"
sparkle every weapon has, so it is not listed.

## Named weapons

| Weapon (prefab) | Effect | Child path | Material / light |
|---|---|---|---|
| Mistwalker (`SwordMistwalker`) | blue mist motes | `attach/Mistwalker/Particle System` | DraugrFangGlow |
| | blue light | `attach/Mistwalker/Point light` | (0.48, 0.80, 1.0), 1.0, range 6 |
| | glowing blade | `attach/Mistwalker` (mesh) | MistWalker_Mat (emissive) |
| Frostner (`MaceSilver`) | frost cloud | `attach/effects/soft cloud` | frost |
| | falling snowflakes | `attach/effects/vfx_BloodHit 1` | snow_flake |
| | hit burst | prefab `vfx_silvermace_hit` | |
| Draugr Fang (`BowDraugrFang`) | green-teal glow motes | `attach/DraugrFangBow/Particle System` | DraugrFangGlow |
| | teal light | `attach/Point light` | (0, 1, 0.79), 1.0, range 2 |
| Dyrnwyn (`SwordDyrnwyn`) | flames along the blade | `attach/Burny vfx` (+ children `flare`, `fx_Torch_Basic`) | flameball_flipbook_gradient, light_glow |
| | orange light | `attach/Point Light` | (1, 0.57, 0), 1.0, range 10 |

## Ashlands gem weapons (one set per element, shared across weapons)

The three elements use the same particle systems on every weapon. Only the parent path differs.

| Element | Particles | Light | Hit effect | Glow materials |
|---|---|---|---|---|
| **Blood** | `Swirls` (alpha_trail, red wisps), `blood drip` (water_drop_noemissive) | none | `fx_bloodweapon_hit` | *_BloodGlow_Mat |
| **Lightning** | `Lightning` (fireworks_trail, crackling arcs), `Clouds` (wispysmoke) | `Point light` (0.09, 0.71, 0.86), range 7 | `fx_lightningweapon_hit` | *_LightningGlow_Mat |
| **Nature** | `Spores` + `Spores_World` (light_glow_gradient, drifting green spores) | `Point light` (0.09, 0.86, 0.30), range 5 | `fx_natureweapon_hit` | *_NatureGlow_Mat |

Where each weapon keeps them (append the particle name):

| Weapon | Parent path |
|---|---|
| Sword Nidhogg (`SwordNiedhogg{Blood,Lightning,Nature}`) | `attach/default/glow/` |
| Slayer (`THSwordSlayer{...}`) | `attach/default/VFX/` |
| Eldner mace (`MaceEldner{...}`) | `attach/VFX/` |
| Berserkir axes (`AxeBerzerkr{...}`) | `attach/` (also `attach_skin/berzerkr/` when worn) |
| Splitnir spear (`SpearSplitner_{Blood,Lightning,Nature}`) | `attach/default/` (thrown: `projectile_splitner_*`) |
| Ashlands bows (`BowAshlands{Blood,Root,Storm}`) | `attach/{BloodFang,RootFang,StormFang}/vfx/` (Storm: `.../default/`) |
| Ripper crossbow (`CrossbowRipper{...}`) | `attach/` |

The enable sounds are `sfx_weapons_{blood,lightning,nature}_enable` and the impact sounds `..._impact`.

## Staffs

| Staff (prefab) | Equipped effects (path) | Light | Cast / projectile prefabs |
|---|---|---|---|
| Staff of Embers (`StaffFireball`) | `attach/equiped/flames`, `flames_world`, `embers`; `attach/default (1)/effects/flare` | (1, 0.46, 0.16), range 3 | `staff_fireball_projectile` |
| Staff of Frost (`StaffIceShards`) | `attach/default (1)/effects/embers (1)` (snowflakes), `flare` | (0.16, 0.89, 1.0), range 3 | `staff_iceshard_projectile`, `fx_iceshard_launch` |
| Dundr (`StaffLightning`) | `attach/Loaded/Lightning`, `Clouds`, `flare` | red (0.86, 0.02, 0), range 7 | `staff_lightning_projectile`, `vfx_lightningstaff_fire` |
| Staff of Fracturing (`StaffClusterbomb`) | `attach/equiped/flames`, `embers`; `attach/default/effects/flare` | (1, 0.46, 0.16), range 3 | `staff_clusterbombstaff_projectile` |
| Staff of the Wild (`StaffGreenRoots`) | `attach/default/glow/Spores`, `Spores_World`, `flare` | (0.09, 0.86, 0.30), range 5 | `staff_greenroots_projectile`, `staff_greenroots_tentaroot` |
| Dead Raiser (`StaffSkeleton`) | `attach/fi_vil_combs_props_bone_skull/equiped/flames`, `embers` (purple sparks) | purple (0.86, 0.15, 0.89), range 4 | `staff_skeleton_spawn`, `fx_summon_skeleton` |
| Staff of Protection (`StaffShield`) | `attach/equiped/flames` (goblinking_beam) | none | `staff_shield_aoe`, `fx_shield_start` |
| Trollstav (`StaffRedTroll`) | `attach/default/Swirls` (+ `flare`) | red (1, 0, 0), 1.3, range 10 | `staff_redtroll_spawn`, `fx_summon_troll` |
| Frost orbs (`StaffFrostOrbs`) | glowing skull mesh only | (0.58, 0.91, 1.0), range 4 | `staff_FrostOrbs_aoe`, `fx_shield_start_frost` |
| Spirit caller (`StaffSpiritCaller`) | as Dead Raiser (purple flames, sparks) | purple, range 4 | `staff_SpiritCaller_spawn` |
| Thunder blood (`StaffThunderBlood`) | glowing mesh only | none | `staff_thunderblood_projectile`, `fx_redlightning_launch` |
| Orb of Ahri (`StaffOrbofAhri`) | none on the staff | none | `staff_OrbofAhri_projectile` |

## Notes for using them

- **Scale:** the particle systems are sized for a weapon about 1 m long. Under a 20 cm lure or a 3 m fish, scale the
  instance and set `ParticleSystem.main.scalingMode = Hierarchy` (or adjust `startSize`).
- **Simulation space:** the `*_World` systems (`Spores_World`, `flames_world`) simulate in world space and leave a
  trail behind a moving object. The others stay attached.
- **Lights:** each point light costs performance. Keep at most one per effect and turn it off when the effect is out
  of view or far away.
- **Multiplayer:** everything here is client-side visuals. Each client spawns its own copy from its own ObjectDB, so
  nothing needs to sync except the state that turns it on.
- **Copyright:** reuse the game's own prefabs at runtime only. Don't export the meshes, textures or particle settings
  into our files or bundles.

## In use (src/Visuals/VanillaFx.cs, 2026-10-17)

Legendary and boss fish and the top rods only. Shown on the landed/dropped fish, on the fish fighting on the line,
and on the rod in hand. Particles emit from our own model's surface; at most one light per effect.

| Fish / rod | Effect |
|---|---|
| Eikthyr Elver | lightning gem sword's crackles along the body, Dundr's storm puffs (tinted pale blue), sky-blue light |
| Elder Bass | Nature spores (Nidhogg), green light |
| Bonemass Catfish | Draugr Fang's teal motes and light |
| Moder Scale Fish | Frostner's frost cloud and snowflakes |
| Yagluth Gill | Dyrnwyn's flames and orange light |
| Queen Eel | Dead Raiser's purple flames and sparks, purple light |
| Fimbul Salmon | Staff of Frost snowflakes and Frostner's cloud, ice-blue light |
| Odin's Eye | Mistwalker's blue mist motes and light |
| Thor's Hammerhead | Lightning gem arcs and clouds, light |
| Fenringfin | Blood gem swirls and drips |
| Yggdrasil Rod | nature spores |
| Ashwood Rod | Staff of Embers embers |
| Frostwood Rod | Frostner's snowflakes |
| Leviathan Rod | Mistwalker's mist motes |
