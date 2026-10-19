using HarmonyLib;
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// Angler ranks: rank points come from the species in your catch log (legendaries count four times), every fish
    /// landed, Trophy-size catches and the total weight you've landed. Ten ranks, each unlocking some of the top rods,
    /// lures and Fish Cleaning Table recipes - which stay hidden from the crafting list until you reach it.
    /// </summary>
    internal static class AnglerRanks
    {
        private const string TrophiesKey = "vdw_rank_trophies", KgKey = "vdw_rank_kg";
        public const int SpeciesPoints = 10, LegendaryPoints = 40, CatchPoints = 1, TrophyPoints = 5;
        public const float KgPerPoint = 10f;

        public sealed class Rank
        {
            public string Name = "";
            public int Points;
            /// <summary>The recipes it unlocks, by the prefab they make.</summary>
            public string[] Unlocks = Array.Empty<string>();
        }

        public static readonly Rank[] Ranks =
        {
            new Rank { Name = "Thrall of the Shallows", Points = 0 },
            new Rank { Name = "Minnow-Karl", Points = 40, Unlocks = new[] { "VDW_Bait_lure_antler" } },
            new Rank { Name = "Net-Weaver", Points = 100, Unlocks = new[] { "VDW_Bait_lure_root", "VDW_Bait_lure_silver_swimbait" } },
            new Rank { Name = "Riverwarden", Points = 200, Unlocks = new[] { "VDW_Rod_silver", "VDW_Bait_lure_ooze", FishDishes.Roe } },
            new Rank { Name = "Fjord-Farer", Points = 350, Unlocks = new[] { "VDW_Bait_lure_wyrm", "VDW_Bait_lure_linen_popper", "VDW_Bait_lure_ice_spoon", "VDW_Mat_legend" } },
            new Rank { Name = "Skerry-Reaver", Points = 550, Unlocks = new[] { "VDW_Rod_blackmetal", FishDishes.Dried } },
            new Rank { Name = "Wave-Jarl", Points = 800, Unlocks = new[] { "VDW_Rod_yggdrasil", "VDW_Bait_lure_ember" } },
            new Rank { Name = "Serpent-Slayer", Points = 1100, Unlocks = new[] { "VDW_Rod_ashwood", "VDW_Bait_lure_chitin", "VDW_Bait_lure_frostcore_jig", "VDW_Mat_cinder" } },
            new Rank { Name = "Ægir's Hand", Points = 1500, Unlocks = new[] { "VDW_Rod_frostwood", "VDW_Mat_rime" } },
            new Rank { Name = "Chosen of Njord", Points = 2000, Unlocks = new[] { "VDW_Bait_lure_crown" } },
        };

        /// <summary>Prefab -> the rank index that unlocks it.</summary>
        private static readonly Dictionary<string, int> LockedBy = Ranks
            .SelectMany((r, i) => r.Unlocks.Select(p => (p, i)))
            .ToDictionary(x => x.p, x => x.i);

        // ------------------------------------------------------------------ points

        private static float GetFloat(Player p, string key) =>
            p.m_customData.TryGetValue(key, out var raw) && float.TryParse(raw, NumberStyles.Float, CultureInfo.InvariantCulture, out var v) ? v : 0f;

        public static int Trophies(Player p) => Mathf.RoundToInt(GetFloat(p, TrophiesKey));
        public static float KgLanded(Player p) => GetFloat(p, KgKey);

        public static int Points(Player p)
        {
            int pts = 0;
            foreach (var kv in CatchLog.Load(p))
            {
                bool legendary = ContentRegistry.Fish.TryGetValue(kv.Key, out var f) && f.Legendary;
                pts += (legendary ? LegendaryPoints : SpeciesPoints) + kv.Value.Count * CatchPoints;
            }
            return pts + Trophies(p) * TrophyPoints + Mathf.FloorToInt(KgLanded(p) / KgPerPoint);
        }

        public static int RankIndex(int points)
        {
            int r = 0;
            for (int i = 0; i < Ranks.Length; i++) if (points >= Ranks[i].Points) r = i;
            return r;
        }

        public static int RankIndex(Player p) => RankIndex(Points(p));

        /// <summary>The name a crafting recipe's item shows ("Silver Fishing Rod"), for the unlock lists.</summary>
        public static string ItemName(string prefab)
        {
            var drop = ObjectDB.instance?.GetItemPrefab(prefab)?.GetComponent<ItemDrop>();
            string name = drop != null ? Localization.instance.Localize(drop.m_itemData.m_shared.m_name) : prefab;
            return prefab.StartsWith("VDW_Mat_", StringComparison.Ordinal) ? name + " (cleaning)" : name;
        }

        public static Sprite? ItemIcon(string prefab)
        {
            var drop = ObjectDB.instance?.GetItemPrefab(prefab)?.GetComponent<ItemDrop>();
            return drop != null && drop.m_itemData.m_shared.m_icons.Length > 0 ? drop.m_itemData.m_shared.m_icons[0] : null;
        }

        /// <summary>
        /// Called on every catch, after the catch log has it: adds the trophy and the weight, and returns the line for
        /// the catch message ("+14 rank points"), with a rank-up if there was one.
        /// </summary>
        public static string OnCatch(Player player, float kg, bool trophy, int pointsBefore)
        {
            if (trophy) player.m_customData[TrophiesKey] = (Trophies(player) + 1).ToString(CultureInfo.InvariantCulture);
            player.m_customData[KgKey] = (KgLanded(player) + Mathf.Max(0f, kg)).ToString("0.00", CultureInfo.InvariantCulture);
            int after = Points(player);
            string text = after > pointsBefore ? $"\n+{after - pointsBefore} rank points" : "";
            int before = RankIndex(pointsBefore), now = RankIndex(after);
            for (int i = before + 1; i <= now; i++)
            {
                var r = Ranks[i];
                text += $"\nAngler rank: {r.Name}!";
                string unlocks = r.Unlocks.Length > 0 ? "Unlocks " + string.Join(", ", r.Unlocks.Select(ItemName)) : "";
                MessageHud.instance?.QueueUnlockMsg(r.Unlocks.Length > 0 ? ItemIcon(r.Unlocks[0]) : null, "Angler rank: " + r.Name, unlocks);
            }
            return text;
        }

        /// <summary>vdw_debug rank: adds points (as weight landed), with the rank-up popups.</summary>
        public static string DebugAdd(Player player, int points) =>
            OnCatch(player, points * KgPerPoint, false, Points(player));

        public static void Reset(Player player)
        {
            player.m_customData.Remove(TrophiesKey);
            player.m_customData.Remove(KgKey);
        }

        // ------------------------------------------------------------------ locking recipes

        public static bool Locked(Player? player, Recipe? recipe)
        {
            if (player == null || recipe == null || recipe.m_item == null) return false;
            return LockedBy.TryGetValue(recipe.m_item.gameObject.name, out int need) && RankIndex(player) < need;
        }

        /// <summary>Locked recipes aren't discovered (no "new recipe" popup) until you have the rank.</summary>
        [HarmonyPatch(typeof(Player), nameof(Player.HaveRequirements), typeof(Recipe), typeof(bool), typeof(int), typeof(int))]
        private static class NotDiscovered
        {
            private static bool Prefix(Player __instance, Recipe recipe, bool discover, ref bool __result)
            {
                if (!discover || !Locked(__instance, recipe)) return true;
                __result = false;
                return false;
            }
        }

        /// <summary>...and never show in the crafting list, even if they were known already.</summary>
        [HarmonyPatch(typeof(Player), nameof(Player.GetAvailableRecipes))]
        private static class Hidden
        {
            private static void Postfix(Player __instance, ref List<Recipe> available)
            {
                if (LockedBy.Count == 0) return;
                int rank = RankIndex(__instance);
                available.RemoveAll(r => r != null && r.m_item != null && LockedBy.TryGetValue(r.m_item.gameObject.name, out int need) && rank < need);
            }
        }
    }
}
