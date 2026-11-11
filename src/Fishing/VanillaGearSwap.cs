using System.Collections.Generic;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// Vanilla fishing gear found lying in the world (the rod and bait in frost caves, or one a player drops) turns
    /// into Deep Waters gear when it loads: the rod becomes the Wooden Fishing Rod and each vanilla bait the
    /// Deep Waters bait closest to it, the same number of them.
    /// </summary>
    [HarmonyLib.HarmonyPatch(typeof(ItemDrop), "Start")]
    internal static class VanillaGearSwap
    {
        private static readonly Dictionary<string, string> Baits = new()
        {
            { "FishingBait", "worm" },
            { "FishingBaitForest", "worm" },
            { "FishingBaitSwamp", "leech" },
            { "FishingBaitOcean", "shrimp" },
            { "FishingBaitCave", "frost_bait" },
            { "FishingBaitDeepNorth", "frost_bait" },
            { "FishingBaitPlains", "minnow" },
        };

        private static string? Replacement(string name)
        {
            if (name == "FishingRod") return "VDW_FishingRod";
            if (!name.StartsWith("FishingBait")) return null;
            return "VDW_Bait_" + (Baits.TryGetValue(name, out var id) ? id : "worm");
        }

        private static void Postfix(ItemDrop __instance)
        {
            if (!VdwConfig.Enabled.Value || ZNetScene.instance == null) return;
            var nview = __instance.GetComponent<ZNetView>();
            if (nview == null || !nview.IsValid() || !nview.IsOwner()) return;

            string? swap = Replacement(Utils.GetPrefabName(__instance.gameObject));
            if (swap == null) return;
            var prefab = ZNetScene.instance.GetPrefab(swap);
            if (prefab == null) return;

            var t = __instance.transform;
            var made = Object.Instantiate(prefab, t.position, t.rotation).GetComponent<ItemDrop>();
            if (made != null && made.m_itemData.m_shared.m_maxStackSize > 1)
                made.SetStack(Mathf.Clamp(__instance.m_itemData.m_stack, 1, made.m_itemData.m_shared.m_maxStackSize));
            ZNetScene.instance.Destroy(__instance.gameObject);
        }
    }
}
