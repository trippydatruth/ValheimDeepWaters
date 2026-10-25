using HarmonyLib;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// Rods upgrade to level 4 like vanilla gear (Upgrade in Rods.json). Each level adds to the rod's stats, so a fully
    /// upgraded rod sits about halfway to the next tier; the line gets stronger with the materials it's made from.
    /// </summary>
    internal static class RodUpgrades
    {
        public const int MaxLevel = 4;
        public const float DurabilityPerLevel = 0.25f;   // of the base durability, per level

        // per level above the first
        private const float Cast = 0.05f, Line = 0.12f, Strength = 1.5f, Reel = 0.04f, PowerUp = 0.07f, Hook = 0.01f, Stamina = 0.03f;

        /// <summary>The rod's stats at an upgrade level (1 = as crafted). Returns the definition itself at level 1.</summary>
        public static RodDefinition Scaled(RodDefinition rod, int level)
        {
            int up = Mathf.Clamp(level, 1, MaxLevel) - 1;
            if (up == 0) return rod;
            var r = rod.Copy();
            r.CastDistance = rod.CastDistance * (1f + Cast * up);
            r.LineCapacity = rod.LineCapacity * (1f + Line * up);
            r.BreakTension = Mathf.Min(99.5f, rod.BreakTension + Strength * up);
            r.ReelSpeed = rod.ReelSpeed * (1f + Reel * up);
            r.Power = rod.Power * (1f + PowerUp * up);
            r.HookBonus = rod.HookBonus + Hook * up;
            r.StaminaUse = rod.StaminaUse * (1f - Stamina * up);
            return r;
        }

        public static string Stats(RodDefinition r) =>
            $"Cast: {r.CastDistance:0} m\nLine: {r.LineCapacity:0} m\nLine strength: {r.BreakTension:0.#}\n" +
            $"Reel speed: {r.ReelSpeed:0.0} m/s\nPower: {r.Power:0.##}\nHook bonus: +{r.HookBonus * 100f:0}%\n" +
            $"Reel stamina: {r.StaminaUse * 100f:0}%";

        /// <summary>A rod's tooltip lists its stats at the level shown (its own, or the one an upgrade would bring).</summary>
        [HarmonyPatch(typeof(ItemDrop.ItemData), nameof(ItemDrop.ItemData.GetTooltip),
            new[] { typeof(ItemDrop.ItemData), typeof(int), typeof(bool), typeof(float), typeof(int), typeof(bool) })]
        private static class RodTooltip
        {
            private static void Postfix(ItemDrop.ItemData item, int qualityLevel, ref string __result)
            {
                var rod = ContentRegistry.GetRod(item);
                if (rod == null) return;
                __result += "\n\n" + Stats(Scaled(rod, qualityLevel));
                if (rod.Upgrade.Count > 0 && qualityLevel < MaxLevel)
                    __result += $"\n<size=85%>Upgrades to level {MaxLevel}{(qualityLevel == MaxLevel - 1 ? "; the last level needs a Trophy Fin" : "")}.</size>";
            }
        }

        /// <summary>
        /// Vanilla asks one more station level for each upgrade level, with no cap: a rod crafted at forge 5 would need
        /// forge 8 for level 4, which doesn't exist. A rod's upgrades ask for at most the station's highest level.
        /// </summary>
        [HarmonyPatch(typeof(Recipe), nameof(Recipe.GetRequiredStationLevel))]
        private static class StationLevelCap
        {
            private static void Postfix(Recipe __instance, ref int __result)
            {
                if (__instance.m_item == null || __instance.m_craftingStation == null) return;
                if (ContentRegistry.GetRod(__instance.m_item.m_itemData) == null) return;
                __result = Mathf.Min(__result, MaxStationLevel(__instance.m_craftingStation));
            }
        }

        /// <summary>
        /// Valheim's Upgrade tab only goes through recipes the player knows, learned by picking up the materials: a rod
        /// bought, given or found never showed for upgrading. A rod you carry (inventory or rod slot) counts as known.
        /// </summary>
        [HarmonyPatch(typeof(Player), nameof(Player.GetAvailableRecipes))]
        private static class CarriedRodsKnown
        {
            private static readonly System.Reflection.FieldInfo? Known = AccessTools.Field(typeof(Player), "m_knownRecipes");

            private static void Prefix(Player __instance)
            {
                if (__instance != Player.m_localPlayer || ObjectDB.instance == null || !(Known?.GetValue(__instance) is HashSet<string> known)) return;
                var carried = __instance.GetInventory().GetAllItems().Concat(Tackle.Get(__instance).GetAllItems());
                foreach (var item in carried)
                {
                    if (ContentRegistry.GetRod(item) == null || item.m_quality >= item.m_shared.m_maxQuality) continue;
                    var recipe = ObjectDB.instance.GetRecipe(item);
                    if (recipe != null && recipe.m_enabled) known.Add(recipe.name);
                }
            }
        }

        private static readonly Dictionary<string, int> StationMax = new Dictionary<string, int>();

        /// <summary>1 + the station's distinct extensions (the highest level it can reach).</summary>
        private static int MaxStationLevel(CraftingStation station)
        {
            if (StationMax.TryGetValue(station.m_name, out int max)) return max;
            if (ZNetScene.instance == null) return 99;
            int ext = ZNetScene.instance.m_prefabs
                .Select(p => p != null ? p.GetComponent<StationExtension>() : null)
                .Count(e => e != null && e.m_craftingStation != null && e.m_craftingStation.m_name == station.m_name);
            return StationMax[station.m_name] = 1 + ext;
        }
    }

}
