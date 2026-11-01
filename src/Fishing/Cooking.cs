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

        internal static int SellValue(FishDefinition f, bool cooked)
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
                health = CapHealth(health);
            }

        }

        /// <summary>
        /// Big fish would otherwise give hundreds of health (it grows with their weight). Up to 40 it's kept as it is;
        /// above that each extra point counts for less, levelling off at 110, so the heaviest top out around 95-110.
        /// </summary>
        internal static float CapHealth(float health)
        {
            const float keep = 40f, cap = 110f, ease = 150f;
            if (health <= keep) return health;
            return keep + (cap - keep) * (1f - Mathf.Exp(-(health - keep) / ease));

        }

        /// <summary>Sets the raw fish's sell value. Call once the raw item is registered.</summary>
        public static void PriceRawFish(FishDefinition fish, GameObject rawPrefab)
        {
            var drop = rawPrefab.GetComponent<ItemDrop>();
            if (drop != null) drop.m_itemData.m_shared.m_value = SellValue(fish, cooked: false);
        }

        /// <summary>Creates "Cooked <fish>": the raw fish's own model, browned and grill-marked (CookedLook), made a
        /// food like cooked meat, with Food stats, a sell value and a cooking-station conversion from the raw fish.
        /// Call it before anything else (glow effects) is added to the raw prefab. Safe if Jotunn's conversion API
        /// rejects the config: the cooked item still exists (usable via console) and only the conversion is skipped.</summary>
        public static void RegisterCookedFish(FishDefinition fish, GameObject rawPrefab)
        {
            string cookedId = "VDW_CookedFish_" + fish.Id;
            var meat = PrefabManager.Instance.GetPrefab(FoodBasePrefab);
            var meatShared = meat != null ? meat.GetComponent<ItemDrop>()?.m_itemData.m_shared : null;

            var clone = PrefabManager.Instance.CreateClonedPrefab(cookedId, rawPrefab);
            var item = clone != null ? new CustomItem(clone, false) : null;
            if (item?.ItemPrefab == null || item.ItemDrop == null)
            {
                Plugin.Log.LogWarning($"Could not create cooked item for fish '{fish.Id}'; that fish won't be cookable.");
                return;
            }
            // a cooked fish doesn't swim off when dropped in water
            if (clone!.GetComponent<global::Fish>() is global::Fish live) UnityEngine.Object.DestroyImmediate(live);
            CookedLook.ApplyToModel(clone);
            if (meat != null)
                foreach (Transform fx in meat.transform)
                    if (fx.name.StartsWith("fx_FoodSteam"))
                        UnityEngine.Object.Instantiate(fx.gameObject, clone.transform, false).name = fx.name;

            var shared = item.ItemDrop.m_itemData.m_shared;
            if (meatShared != null)
            {
                shared.m_itemType = meatShared.m_itemType;
                shared.m_maxStackSize = meatShared.m_maxStackSize;
                shared.m_weight = meatShared.m_weight;
                shared.m_foodBurnTime = meatShared.m_foodBurnTime;
                shared.m_foodRegen = meatShared.m_foodRegen;
                shared.m_foodEitr = 0f;
                shared.m_consumeStatusEffect = meatShared.m_consumeStatusEffect;
            }
            shared.m_maxQuality = 1;
            shared.m_teleportable = true;
            if (shared.m_icons != null && shared.m_icons.Length > 0 && CookedLook.Icon(shared.m_icons[0]) is Sprite icon)
                shared.m_icons = new[] { icon };
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
