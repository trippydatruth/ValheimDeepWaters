using HarmonyLib;
using Jotunn.Managers;
using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// The endgame (roadmap #24), built on how many times you've landed each boss fish (its catch log count):
    ///   - each boss lure costs more every time you've landed its boss: every ingredient but the boss part (the first)
    ///     needs one more per landing, up to three times the original; the Bog Witch's price rises 50% a landing, to 3x
    ///   - the Allfather's Rod (the Leviathan Rod remade) is hidden until every boss fish has been landed once
    ///   - Njord's Regalia, a crown made from the four relics, is hidden until every boss fish has been landed 3 times
    /// It's all per character: a friend's first summon is still cheap.
    /// </summary>
    internal static class Endgame
    {
        public const string AllfatherRod = "VDW_Rod_allfather", Regalia = "VDW_Buff_regalia_njord";
        public const int RodLandings = 1, RegaliaLandings = 3;
        private const int MaxCostFactor = 3;
        private const float PricePerLanding = 0.5f;

        private static IEnumerable<FishDefinition> Bosses => ContentRegistry.Fish.Values.Where(f => BossFish.IsBoss(f.Id));
        public static int BossCount => Bosses.Count();

        /// <summary>Times this player has landed this boss fish (its catch log count).</summary>
        public static int Landed(Player p, string fishId) => Mastery.Count(p, fishId);

        /// <summary>How many of the boss fish this player has landed at least <paramref name="times"/> times.</summary>
        public static int BossesAtLeast(Player p, int times) => Bosses.Count(f => Landed(p, f.Id) >= times);

        /// <summary>Whether an endgame recipe is still out of reach for this player (hidden from the crafting list).</summary>
        public static bool Locked(Player p, string prefabName) =>
            prefabName == AllfatherRod ? BossesAtLeast(p, RodLandings) < BossCount
          : prefabName == Regalia ? BossesAtLeast(p, RegaliaLandings) < BossCount
          : false;

        // ------------------------------------------------------------------ boss lures cost more each time

        private static readonly Dictionary<string, int[]> BaseAmounts = new Dictionary<string, int[]>();   // by lure prefab
        private static readonly Dictionary<string, int> BasePrices = new Dictionary<string, int>();

        private static IEnumerable<(FishDefinition boss, string lurePrefab)> BossLures() =>
            Bosses.Select(f => (f, BossFish.ForFish(f.Id)?.LureId)).Where(x => !string.IsNullOrEmpty(x.Item2)).Select(x => (x.f, "VDW_Bait_" + x.Item2));

        /// <summary>Sets this player's boss lure recipes to what they cost them now (on spawning, and after each boss landing).</summary>
        public static void RefreshLureCosts(Player p)
        {
            if (ObjectDB.instance == null) return;
            foreach (var (boss, prefab) in BossLures())
            {
                var recipe = ObjectDB.instance.m_recipes.FirstOrDefault(r => r != null && r.m_item != null && r.m_item.gameObject.name == prefab);
                if (recipe == null || recipe.m_resources == null) continue;
                if (!BaseAmounts.TryGetValue(prefab, out var baseAmounts) || baseAmounts.Length != recipe.m_resources.Length)
                    BaseAmounts[prefab] = baseAmounts = recipe.m_resources.Select(r => r.m_amount).ToArray();
                int landed = Landed(p, boss.Id);
                for (int i = 1; i < recipe.m_resources.Length; i++)   // the first, the boss part, always stays as it is
                    recipe.m_resources[i].m_amount = Math.Min(baseAmounts[i] + landed, baseAmounts[i] * MaxCostFactor);
            }
        }

        /// <summary>The Bog Witch's price for a boss lure, raised for each time this player has landed its boss.</summary>
        private static void RaiseWitchPrices(Trader trader, Player p)
        {
            if (TraderSales.KeyOf(trader) != "BogWitch") return;
            foreach (var (boss, prefab) in BossLures())
                foreach (var t in trader.m_items.Where(t => t.m_prefab != null && t.m_prefab.gameObject.name == prefab))
                {
                    if (!BasePrices.TryGetValue(prefab, out int basePrice)) BasePrices[prefab] = basePrice = t.m_price;
                    float factor = Mathf.Min(1f + PricePerLanding * Landed(p, boss.Id), MaxCostFactor);
                    t.m_price = Mathf.RoundToInt(basePrice * factor / 10f) * 10;
                }
        }

        [HarmonyPatch(typeof(StoreGui), nameof(StoreGui.Show))]
        private static class WitchPrices
        {
            private static void Prefix(Trader trader)
            {
                if (trader != null && Player.m_localPlayer != null) RaiseWitchPrices(trader, Player.m_localPlayer);
            }
        }

        [HarmonyPatch(typeof(Player), nameof(Player.OnSpawned))]
        private static class OnSpawn
        {
            private static void Postfix(Player __instance)
            {
                if (__instance == Player.m_localPlayer) RefreshLureCosts(__instance);
            }
        }

        // ------------------------------------------------------------------ the catch log's line

        /// <summary>What the next endgame unlock needs, for the catch log ("" once everything's open).</summary>
        public static string NextStep(Player p)
        {
            int once = BossesAtLeast(p, RodLandings), thrice = BossesAtLeast(p, RegaliaLandings), all = BossCount;
            if (once < all) return $"Allfather's Rod: land every boss fish ({once} of {all})";
            if (thrice < all) return $"Njord's Regalia: land every boss fish 3 times ({thrice} of {all})";
            return "";
        }
    }
}
