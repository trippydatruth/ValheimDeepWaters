using Jotunn.Managers;
using System.Collections.Generic;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// The four relics each come from one place, rarely, and take a slot each (they don't stack):
    ///   Horn of Ægir        - Hildir's prize for the 15th fishing bounty
    ///   Pearl of Njord      - logging every species in the catch log
    ///   Golden Hook         - very rarely found inside a legendary fish (Hooks.json Find)
    ///   Jörmungandr's Scale - very rarely dropped by a sea serpent you kill
    /// The Horn and the Pearl are earned once; the Hook and the Scale can turn up again (spares sell to Hildir).
    /// </summary>
    internal static class Relics
    {
        public const string Horn = "VDW_Buff_relic_horn", Pearl = "VDW_Buff_relic_pearl", Scale = "VDW_Buff_relic_scale", GoldenHook = "VDW_Hook_golden";
        private const float SerpentScaleChance = 0.03f;

        private static readonly Dictionary<string, string> Sources = new Dictionary<string, string>
        {
            [Horn] = "Hildir's prize for your 15th fishing bounty.",
            [Pearl] = "Given for logging every species in your catch log.",
            [GoldenHook] = "Very rarely found inside a legendary fish.",
            [Scale] = "Very rarely dropped by a sea serpent.",
        };

        public static bool IsRelic(string prefabName) => Sources.ContainsKey(prefabName);

        /// <summary>The "where it comes from" line for a relic's description, or null for anything else.</summary>
        public static string? SourceText(string prefabName) =>
            Sources.TryGetValue(prefabName, out var s) ? "\n\nCan't be crafted. " + s : null;

        /// <summary>After the items are registered: one per slot, and the Scale joins the sea serpent's drops.</summary>
        public static void Register()
        {
            foreach (var name in Sources.Keys)
            {
                var drop = PrefabManager.Instance.GetPrefab(name)?.GetComponent<ItemDrop>();
                if (drop != null) drop.m_itemData.m_shared.m_maxStackSize = 1;
            }

            var scale = PrefabManager.Instance.GetPrefab(Scale);
            var serpent = PrefabManager.Instance.GetPrefab("Serpent")?.GetComponent<CharacterDrop>();
            if (scale == null || serpent == null) { Plugin.Log.LogWarning("Relics: the sea serpent or Jörmungandr's Scale wasn't found; serpents won't drop it."); return; }
            serpent.m_drops.Add(new CharacterDrop.Drop
            {
                m_prefab = scale, m_amountMin = 1, m_amountMax = 1, m_chance = SerpentScaleChance,
                m_onePerPlayer = false, m_levelMultiplier = false, m_dontScale = true
            });
        }
    }
}
