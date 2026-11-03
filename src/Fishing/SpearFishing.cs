using HarmonyLib;
using Jotunn.Configs;
using Jotunn.Entities;
using Jotunn.Managers;
using System;
using System.Collections.Generic;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// Spear fishing: stab a fish swimming near the surface, or throw a spear at it from the bank. Any vanilla spear can
    /// take a small fish now and then; the leisters - the old Norse fish spears, many-pronged - are made for it, each tier
    /// taking bigger fish more surely. Deep fish, legendaries and bosses stay rod-only. A speared fish lands like a rod
    /// catch (catch log, mastery, rank, Fishing skill) and raises the Spears skill too, but it comes out lighter.
    /// </summary>
    internal static class SpearFishing
    {
        /// <summary>A fish spear: what it can take and how surely. CloneOf is the vanilla spear's item name token.</summary>
        private sealed class Leister
        {
            public string Prefab = "", CloneOf = "", Name = "", Desc = "", Station = "forge";
            public float MaxKg, Chance;
            public int Level = 1;
            public (string item, int amount)[] Recipe = Array.Empty<(string, int)>();
        }

        // one per era, Meadows to the Deep North (the leister models come later; for now they wear their vanilla spear's look)
        private static readonly Leister[] Leisters =
        {
            new Leister { Prefab = "VDW_Leister_flint", CloneOf = "$item_spear_flint", Name = "Flint Leister", MaxKg = 3f, Chance = 0.55f, Station = "piece_workbench", Level = 1,
                Desc = "Three flint points bound to a light shaft, barbed to hold what they pierce. Made for the fish in the shallows.",
                Recipe = new[] { ("Wood", 4), ("Flint", 3), ("LeatherScraps", 2), ("VDW_Mat_scales", 2) } },
            new Leister { Prefab = "VDW_Leister_bronze", CloneOf = "$item_spear_bronze", Name = "Bronze Leister", MaxKg = 8f, Chance = 0.62f, Level = 1,
                Desc = "Bronze tines, barbed and spread, on a fine-wood shaft.",
                Recipe = new[] { ("Bronze", 4), ("FineWood", 2), ("LeatherScraps", 2), ("VDW_Mat_scales", 3) } },
            new Leister { Prefab = "VDW_Leister_iron", CloneOf = "$item_spear_ancientbark", Name = "Iron Leister", MaxKg = 15f, Chance = 0.68f, Level = 2,
                Desc = "Iron tines on an ancient-bark shaft. It holds a swamp fish that thrashes.",
                Recipe = new[] { ("Iron", 4), ("ElderBark", 2), ("LeatherScraps", 2), ("VDW_Mat_oil", 3) } },
            new Leister { Prefab = "VDW_Leister_silver", CloneOf = "$item_spear_wolffang", Name = "Silver Leister", MaxKg = 25f, Chance = 0.74f, Level = 3,
                Desc = "Silver tines barbed with wolf fang. Quick in cold water.",
                Recipe = new[] { ("Silver", 4), ("ElderBark", 2), ("WolfFang", 2), ("VDW_Mat_fins", 3) } },
            new Leister { Prefab = "VDW_Leister_blackmetal", CloneOf = "$item_spear_wolffang", Name = "Black Metal Leister", MaxKg = 40f, Chance = 0.8f, Level = 5,
                Desc = "Black metal tines on a linen-bound shaft. It takes the big fish of the plains' rivers.",
                Recipe = new[] { ("BlackMetal", 4), ("FineWood", 2), ("LinenThread", 2), ("VDW_Mat_roe", 3) } },
            new Leister { Prefab = "VDW_Leister_carapace", CloneOf = "$item_spear_carapace", Name = "Carapace Leister", MaxKg = 60f, Chance = 0.84f, Station = "blackforge", Level = 1,
                Desc = "Seeker carapace tines on a yggdrasil shaft, light and keen. Made for the misty waters.",
                Recipe = new[] { ("Carapace", 4), ("YggdrasilWood", 2), ("LinenThread", 2), ("VDW_Mat_ink", 3) } },
            new Leister { Prefab = "VDW_Leister_flametal", CloneOf = "$item_spear_splitner", Name = "Flametal Leister", MaxKg = 80f, Chance = 0.87f, Station = "blackforge", Level = 2,
                Desc = "Flametal tines on an ashwood shaft. It doesn't soften in the boiling seas.",
                Recipe = new[] { ("FlametalNew", 4), ("Blackwood", 2), ("LinenThread", 2), ("VDW_Mat_cinder", 3) } },
            new Leister { Prefab = "VDW_Leister_frostcore", CloneOf = "$item_spear_gold", Name = "Frostcore Leister", MaxKg = 100f, Chance = 0.9f, Station = "blackforge", Level = 3,
                Desc = "Frostcore tines on a frostwood shaft, lashed with moose sinew. The finest fish spear there is.",
                Recipe = new[] { ("FrostCore", 2), ("Frostwood", 2), ("MooseSinew", 2), ("VDW_Mat_rime", 3) } },
        };
        private static readonly Dictionary<string, Leister> ByPrefab = new();

        /// <summary>
        /// Every vanilla spear spears fish too, a little better the later its tier, but well short of a leister (by the
        /// item's name token; variants like Splitnir's count as theirs). The Abyssal Harpoon, made for the sea, does better.
        /// </summary>
        private static readonly (string token, float maxKg, float chance)[] VanillaSpears =
        {
            ("$item_spear_wood", 1.5f, 0.2f), ("$item_spear_flint", 2.5f, 0.25f), ("$item_spear_bronze", 4f, 0.28f),
            ("$item_spear_ancientbark", 6f, 0.3f), ("$item_spear_wolffang", 8f, 0.32f), ("$item_spear_chitin", 12f, 0.42f),
            ("$item_spear_carapace", 12f, 0.34f), ("$item_spear_splitner", 16f, 0.36f), ("$item_spear_gold", 20f, 0.38f),
        };
        /// <summary>Any other spear (another mod's): a small fish now and then.</summary>
        private const float PlainSpearMaxKg = 2.5f, PlainSpearChance = 0.25f;
        /// <summary>How far under the surface a fish can be and still be speared, m.</summary>
        private const float ShallowDepth = 5f;
        /// <summary>A stab reaches this far past the spear's own attack range (it's thrust down into the water), m; a thrown
        /// spear takes a fish within this of where it comes down, m.</summary>
        private const float StabReach = 2f, ThrowReach = 1.5f;
        /// <summary>A stab reaches this far past the spear's own attack range (it's thrust down into the water), m; a thrown
        private const float WeightFactor = 0.85f;
        /// <summary>Leisters hit creatures this hard compared with the spear they're made from: they're for fish.</summary>
        private const float CombatFactor = 0.6f;

        /// <summary>The vanilla item prefab whose name token is exactly this ($item_spear_gold, not its _uncooked).</summary>
        private static string? PrefabByToken(string token)
        {
            // Jotunn's cache of every loaded prefab first (ObjectDB may not be filled in yet when content registers)
            try
            {
                foreach (var o in PrefabManager.Cache.GetPrefabs(typeof(ItemDrop)).Values)
                    if (o is ItemDrop d && d.m_itemData?.m_shared?.m_name == token) return d.gameObject.name;
            }
            catch (Exception ex) { Plugin.Log.LogDebug($"Spear fishing: prefab cache ({ex.Message})."); }
            IEnumerable<GameObject>? items = ObjectDB.instance != null && ObjectDB.instance.m_items.Count > 0 ? ObjectDB.instance.m_items
                                           : ZNetScene.instance != null ? ZNetScene.instance.m_prefabs : null;
            if (items == null) return null;
            foreach (var go in items)
                if (go != null && go.GetComponent<ItemDrop>() is ItemDrop d && d.m_itemData.m_shared.m_name == token) return go.name;
            return null;
        }

        public static void Register()
        {
            foreach (var l in Leisters)
            {
                string? baseName = PrefabByToken(l.CloneOf);
                if (baseName == null || PrefabManager.Instance.GetPrefab(baseName) == null) { Plugin.Log.LogWarning($"Spear fishing: no vanilla spear ({l.CloneOf}) to make the {l.Name} from."); continue; }
                var reqs = new List<RequirementConfig>();
                foreach (var (item, amount) in l.Recipe) reqs.Add(new RequirementConfig(item, amount));
                var custom = new CustomItem(l.Prefab, baseName, new ItemConfig
                {
                    Amount = 1,
                    CraftingStation = l.Station,
                    MinStationLevel = l.Level,
                    Requirements = reqs.ToArray()
                });
                var shared = custom.ItemDrop.m_itemData.m_shared;
                shared.m_name = Loc.Token("vdw_" + l.Prefab.ToLowerInvariant(), l.Name);
                shared.m_description = Loc.Token("vdw_" + l.Prefab.ToLowerInvariant() + "_desc",
                    $"{l.Desc}\n\nSpear fish swimming near the surface: stab them, or throw it. Takes fish up to {l.MaxKg:0} kg; they go straight into your bag.");
                shared.m_damages.Modify(CombatFactor);
                shared.m_damagesPerLevel.Modify(CombatFactor);
                // its own model (build_lures.py leister_<tier>), fitted to where the vanilla spear sits in the hand, and its icon
                string modelKey = "leister_" + l.Prefab.Substring("VDW_Leister_".Length);
                CustomModels.ApplyToPrefab(custom.ItemPrefab, modelKey);
                // thrown, a spear is its attack's projectile, shared with the vanilla spear it's cloned from: give the leister
                // its own copy, wearing the leister model (where it lands, the projectile drops the leister item itself)
                var throwAttack = shared.m_secondaryAttack;
                if (throwAttack?.m_attackProjectile != null)
                {
                    var proj = PrefabManager.Instance.CreateClonedPrefab(l.Prefab + "_projectile", throwAttack.m_attackProjectile);
                    if (proj != null && CustomModels.ApplyFittedToVanilla(proj, modelKey))
                    {
                        PrefabManager.Instance.AddPrefab(new CustomPrefab(proj, true));
                        throwAttack.m_attackProjectile = proj;
                    }
                }
                ItemManager.Instance.AddItem(custom);
                ByPrefab[l.Prefab] = l;
            }
        }

        private static (float maxKg, float chance, string? name) SpearStats(ItemDrop.ItemData weapon)
        {
            string prefab = weapon.m_dropPrefab != null ? weapon.m_dropPrefab.name : "";
            if (ByPrefab.TryGetValue(prefab, out var l)) return (l.MaxKg, l.Chance, l.Name);
            string token = weapon.m_shared.m_name ?? "";
            foreach (var (t, kg, chance) in VanillaSpears)
                if (token.StartsWith(t, StringComparison.Ordinal)) return (kg, chance, null);
            return (PlainSpearMaxKg, PlainSpearChance, null);
        }
        private static bool IsSpear(ItemDrop.ItemData? item) => item != null && item.m_shared.m_skillType == Skills.SkillType.Spears;

        // ------------------------------------------------------------------ finding a fish to spear

        /// <summary>The swimming fish nearest <paramref name="at"/> that can be speared, within the reach given.</summary>
        private static global::Fish? FishNear(Vector3 at, float reach, Vector3? facing = null)
        {
            global::Fish? best = null; float bestD = reach;
            foreach (var u in global::Fish.Instances)
            {
                if (!(u is global::Fish f) || f == null || !f.isActiveAndEnabled) continue;
                Vector3 p = f.transform.position;
                Vector3 flat = new Vector3(p.x - at.x, 0f, p.z - at.z);
                float d = flat.magnitude;
                if (d > bestD) continue;
                if (facing is Vector3 dir && d > 0.4f && Vector3.Angle(new Vector3(dir.x, 0f, dir.z), flat) > 60f) continue;
                float surface = Floating.GetLiquidLevel(p);
                if (surface < -1000f || surface - p.y > ShallowDepth || p.y - at.y > 1.5f) continue;   // too deep, or not in the water
                best = f; bestD = d;
            }
            return best;
        }

        private static FishDefinition? Def(global::Fish f) =>
            ContentRegistry.FishIdByPrefab.TryGetValue(Utils.GetPrefabName(f.gameObject), out var id) && ContentRegistry.Fish.TryGetValue(id, out var def) ? def : null;

        // ------------------------------------------------------------------ the strike

        private static void TrySpear(Player player, global::Fish fish, ItemDrop.ItemData weapon, bool thrown)
        {
            var def = Def(fish);
            if (def == null) return;
            if (def.Legendary || BossFish.IsBoss(def.Id) || def.Water == WaterType.DeepOcean)
            {
                player.Message(MessageHud.MessageType.Center, $"The {def.Name} is too wary for a spear. It needs a rod.");
                return;
            }
            var (maxKg, chance, leister) = SpearStats(weapon);
            float weight = Mathf.Max(def.MinWeightKg, FishingController.RollWeight(def) * WeightFactor);
            Vector3 at = fish.transform.position;
            if (weight > maxKg)
            {
                player.Message(MessageHud.MessageType.Center, leister != null
                    ? $"The {def.Name} is too big for the {leister} - it tears free."
                    : $"The {def.Name} is too big for that spear - it tears free.");
                FishingFx.FishSplash(at, 0.8f);
                return;
            }
            float skill = player.GetSkillFactor(Skills.SkillType.Spears) * 0.2f + player.GetSkillFactor(Skills.SkillType.Fishing) * 0.1f;
            chance = Mathf.Clamp01(chance + skill + (thrown ? -0.1f : 0.05f));
            if (UnityEngine.Random.value > chance)
            {
                player.Message(MessageHud.MessageType.Center, thrown ? "A splash - the fish darts away." : "Missed - the fish darts away.");
                FishingFx.FishSplash(at, 0.6f);
                player.RaiseSkill(Skills.SkillType.Spears, 0.2f);
                return;
            }

            // take it out of the water (the fish is a networked object: claim it, then remove it)
            var nview = fish.GetComponent<ZNetView>();
            if (nview == null || !nview.IsValid()) return;
            nview.ClaimOwnership();
            nview.Destroy();

            var biome = WorldGenerator.instance != null ? WorldGenerator.instance.GetBiome(at) : Heightmap.Biome.None;
            float surface = Floating.GetLiquidLevel(at);
            float ground = ZoneSystem.instance != null && ZoneSystem.instance.GetSolidHeight(at, out float h) ? h : surface - 1f;
            var s = new FishingSession
            {
                Fish = def,
                FishWeight = weight,
                Variant = RareFish.Roll(def),
                Biome = biome,
                Ocean = biome == Heightmap.Biome.Ocean,
                Depth = Mathf.Max(0.5f, surface - ground),
                Spot = at,
                WaterY = surface,
            };
            string text;
            Drops.IntoBag = true;   // straight into the bag (at your feet if it's full), never back by the water
            try { text = FishingController.Land(player, s, at, "Speared"); }
            finally { Drops.IntoBag = false; }
            player.RaiseSkill(Skills.SkillType.Spears, 1f + Mathf.Max(0f, def.FightStrength) * 0.5f);
            FishingFx.FishSplash(at, 1.1f);
            player.Message(MessageHud.MessageType.Center, text);
        }

        // ------------------------------------------------------------------ the stab: a spear's hit frame near the water

        [HarmonyPatch(typeof(Attack), nameof(Attack.OnAttackTrigger))]
        private static class StabPatch
        {
            private static readonly AccessTools.FieldRef<Attack, Humanoid> Character = AccessTools.FieldRefAccess<Attack, Humanoid>("m_character");
            private static readonly AccessTools.FieldRef<Attack, ItemDrop.ItemData> Weapon = AccessTools.FieldRefAccess<Attack, ItemDrop.ItemData>("m_weapon");

            private static void Postfix(Attack __instance)
            {
                try
                {
                    if (!VdwConfig.Enabled.Value || __instance.m_attackType == Attack.AttackType.Projectile) return;
                    if (!(Character(__instance) is Player player) || player != Player.m_localPlayer) return;
                    var weapon = Weapon(__instance);
                    if (!IsSpear(weapon)) return;
                    var fish = FishNear(player.transform.position, __instance.m_attackRange + StabReach, player.transform.forward);
                    if (fish != null) TrySpear(player, fish, weapon, thrown: false);
                }
                catch (Exception ex) { Plugin.Log.LogWarning($"Spear fishing (stab): {ex.Message}"); }
            }
        }

        // ------------------------------------------------------------------ the throw: watch a thrown spear until it lands

        [HarmonyPatch(typeof(Projectile), nameof(Projectile.Setup))]
        private static class ThrowPatch
        {
            private static void Postfix(Projectile __instance, Character owner, ItemDrop.ItemData item)
            {
                if (!VdwConfig.Enabled.Value || owner != Player.m_localPlayer || !IsSpear(item)) return;
                var watch = __instance.gameObject.AddComponent<ThrownSpear>();
                watch.Weapon = item;
            }
        }

        /// <summary>On a thrown spear: the first fish it comes down on (within a hand's reach) is the one it's thrown at.</summary>
        private sealed class ThrownSpear : MonoBehaviour
        {
            public ItemDrop.ItemData? Weapon;
            private float _until;

            private void Start() => _until = Time.time + 4f;

            private void Update()
            {
                if (Time.time > _until || Weapon == null || Player.m_localPlayer == null) { Destroy(this); return; }
                Vector3 p = transform.position;
                float surface = Floating.GetLiquidLevel(p);
                if (surface < -1000f || p.y > surface + 0.4f) return;              // still in the air
                Strike(p);
            }

            /// <summary>It's come down (in the water, or hit something by it): one try at the fish under it.</summary>
            public void Strike(Vector3 p)
            {
                if (_done || Weapon == null || Player.m_localPlayer == null) return;
                _done = true;
                var fish = FishNear(p, ThrowReach);
                if (fish != null) TrySpear(Player.m_localPlayer, fish, Weapon, thrown: true);
                Destroy(this);
            }
            private bool _done;
        }

        /// <summary>A thrown spear hitting the water (or the bank) may be gone before the next frame: strike as it hits.</summary>
        [HarmonyPatch(typeof(Projectile), nameof(Projectile.OnHit))]
        private static class ThrowHitPatch
        {
            private static void Prefix(Projectile __instance, Vector3 hitPoint)
            {
                var watch = __instance != null ? __instance.GetComponent<ThrownSpear>() : null;
                if (watch != null) watch.Strike(hitPoint);
            }
        }
    }
}
