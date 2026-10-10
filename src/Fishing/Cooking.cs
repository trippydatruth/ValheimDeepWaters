using Jotunn.Configs;
using Jotunn.Entities;
using Jotunn.Managers;
using System;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// Registers a cooked variant of each fish (cookable on the vanilla cooking station) and sets coin
    /// values on the raw and cooked items so Haldor (or any trader) will buy them. Every fish is handled in
    /// its own try/catch: a problem with one fish's cooked item never stops the rest from registering.
    /// </summary>
    internal static class Cooking
    {
        public const string FoodBasePrefab = "CookedMeat";

        private static int SellValue(FishDefinition f, bool cooked)
        {
            if (f.SellValue > 0)
                return Mathf.Max(1, Mathf.RoundToInt((cooked ? f.SellValue : f.SellValue / 2f)));

            float baseValue = 3f + f.MaxWeightKg * 2.5f + f.FightStrength * 2f;
            if (f.Legendary) baseValue *= 3f;
            if (cooked) baseValue *= 1.8f;

            return Mathf.Max(1, Mathf.RoundToInt(baseValue));
        }

        private static void FoodStats(FishDefinition f, out float health, out float stamina)
        {
            if (f.FoodHealth > 0f || f.FoodStamina > 0f)
            {
                health = f.FoodHealth;
                stamina = f.FoodStamina;
            }
            else
            {
                health = 12f + f.MaxWeightKg * 1.5f + f.FightStrength * 3f;
                stamina = 8f + f.FightStrength * 2f;
                if (f.Legendary)
                {
                    health *= 1.5f;
                    stamina *= 1.5f;
                }
            }

        }

        /// <summary>Sets the raw fish's sell value. Call once the raw item is registered.</summary>
        public static void PriceRawFish(FishDefinition fish, GameObject rawPrefab)
        {
            var drop = rawPrefab.GetComponent<ItemDrop>();
            if (drop != null) drop.m_itemData.m_shared.m_value = SellValue(fish, cooked: false);
        }

        /// <summary>Creates "Cooked <fish>", gives it Food stats and a sell value, and wires a cooking-station
        /// conversion from the raw fish. Safe to call even if Jotunn's conversion API rejects the config;
        /// the cooked item still exists (usable via console) and only the conversion is skipped.</summary>
        public static void RegisterCookedFish(FishDefinition fish, GameObject rawPrefab)
        {
            string cookedId = "VDW_CookedFish_" + fish.Id;

            var item = new CustomItem(cookedId, FoodBasePrefab);
            if (item.ItemPrefab == null || item.ItemDrop == null)
            {
                Plugin.Log.LogWarning($"Could not create cooked item for fish '{fish.Id}'; that fish won't be cookable.");
                return;
            }

            var shared = item.ItemDrop.m_itemData.m_shared;
            string displayName = string.IsNullOrWhiteSpace(fish.Name) ? fish.Id : fish.Name;
            shared.m_name = Loc.Token("vdw_cooked_" + fish.Id, "Cooked " + displayName);
            shared.m_description = Loc.Token("vdw_cooked_" + fish.Id + "_desc", "Cooked " + displayName + ". " + fish.Description);

            FoodStats(fish, out var health, out var stamina);
            shared.m_food = health;
            shared.m_foodStamina = stamina;
            shared.m_value = SellValue(fish, cooked: true);

            ItemManager.Instance.AddItem(item);

            try
            {
                var conversion = new CustomItemConversion(new CookingConversionConfig
                {
                    Station = "piece_cookingstation",
                    FromItem = rawPrefab.name,
                    ToItem = cookedId,
                    CookTime = 20f
                });
                ItemManager.Instance.AddItemConversion(conversion);
            }
            catch (Exception ex)
            {
                Plugin.Log.LogWarning($"Cooking-station conversion for '{fish.Id}' failed ({ex.Message}); " +
                                       "the cooked item exists but must be given directly.");
            }
        }
    }
}
