using HarmonyLib;
using System.Collections.Generic;
using System.Linq;

namespace ValheimDeepWaters
{
    /// <summary>
    /// Bait and lures each go for a few fish (Lures.Takes); everything else bites them only rarely. So the player can
    /// pick a bait for the fish they're after, a bait's tooltip lists what it catches - species not caught yet as
    /// "???" - and the catch log shows each species' bait once it's been caught.
    /// </summary>
    internal static class BaitTargets
    {
        /// <summary>The species a bait (or lure) is for, boss fish left out unless it's their lure.</summary>
        public static List<FishDefinition> FishFor(BaitDefinition bait)
        {
            var boss = BossFish.ForLure(bait.Id);
            if (boss != null)
                return ContentRegistry.Fish.TryGetValue(boss.FishId, out var bf) ? new List<FishDefinition> { bf } : new List<FishDefinition>();
            return ContentRegistry.Fish.Values
                .Where(f => !BossFish.IsBoss(f.Id) && string.IsNullOrWhiteSpace(f.CatchBait) && Lures.Takes(f, bait, null))
                .OrderBy(f => f.Name).ToList();
        }

        /// <summary>A species' baits by name: its preferred baits, else the first few that go for it.</summary>
        public static string BaitsFor(FishDefinition fish)
        {
            var names = fish.PreferredBaits
                .Where(id => ContentRegistry.Baits.ContainsKey(id))
                .Select(id => ContentRegistry.Baits[id].Name).ToList();
            if (names.Count == 0)
                names = ContentRegistry.Baits.Values.Where(b => Lures.Takes(fish, b, null)).Take(2).Select(b => b.Name).ToList();
            return string.Join(", ", names);
        }

        [HarmonyPatch(typeof(ItemDrop.ItemData), nameof(ItemDrop.ItemData.GetTooltip),
            new[] { typeof(ItemDrop.ItemData), typeof(int), typeof(bool), typeof(float), typeof(int), typeof(bool) })]
        private static class BaitTooltip
        {
            private static void Postfix(ItemDrop.ItemData item, ref string __result)
            {
                var name = item?.m_shared?.m_name;
                if (name == null || !ContentRegistry.BaitByItemName.TryGetValue(name, out var bait) || bait.Trailer) return;
                var fish = FishFor(bait);
                if (fish.Count == 0) return;
                var log = Player.m_localPlayer != null ? CatchLog.Load(Player.m_localPlayer) : new Dictionary<string, CatchEntry>();
                var known = fish.Where(f => log.ContainsKey(f.Id)).Select(f => f.Name).ToList();
                int unknown = fish.Count - known.Count;
                string list = string.Join(", ", known);
                if (unknown > 0) list += (list.Length > 0 ? ", " : "") + (unknown == 1 ? "???" : $"??? ({unknown} more)");
                __result += $"\n\n<color=orange>Catches:</color> {list}\n<size=85%>Other fish only rarely take it.</size>";
            }
        }
    }
}
