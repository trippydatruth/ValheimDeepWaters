using Jotunn.Configs;
using Jotunn.Entities;
using Jotunn.Managers;
using System;
using System.Linq;

namespace ValheimDeepWaters
{
    /// <summary>
    /// Fish food. The Fish Cleaning Table's add-ons let it prepare three ingredients - Fish Fillets (knife rack), Brined
    /// Roe (brining barrel) and Dried Fish (drying line) - and the dishes are made from them at Valheim's own food
    /// stations: the cooking station grills fillets, the cauldron makes the stews, soups and plates, and the food
    /// preparation table cures fish and packs travel rations.
    /// </summary>
    internal static class FishDishes
    {
        private sealed class Food
        {
            public string Id = "", Name = "", Desc = "", Station = "piece_cauldron";
            public int Level = 1, Amount = 1;
            public (string item, int amount)[] Recipe = new (string, int)[0];
            public float Health, Stamina, Eitr, Regen, Duration = 1800f;
        }

        public const string Fillet = "VDW_Prep_fillet", Roe = "VDW_Prep_roe", Dried = "VDW_Prep_dried";

        private static readonly Food[] Dishes =
        {
            new Food { Id = "fishermans_stew", Name = "Fisherman's Stew", Level = 1, Health = 35, Stamina = 40, Regen = 3, Duration = 1500,
                Desc = "A whole fish stewed with carrots in a thick red broth. Every fishing camp's supper.",
                Recipe = new[] { (Fillet, 1), ("VDW_Mat_oil", 1), ("Carrot", 2) } },
            new Food { Id = "fin_soup", Name = "Spiny Fin Soup", Level = 2, Health = 50, Stamina = 45, Regen = 3,
                Desc = "Clear golden broth boiled from fin rays, with fillets, carrots and onions in it. Mind the bones.",
                Recipe = new[] { (Fillet, 1), ("VDW_Mat_fins", 2), ("Onion", 2) } },
            new Food { Id = "roe_flatbread", Name = "Roe Flatbread", Level = 3, Health = 40, Stamina = 75, Regen = 4,
                Desc = "Slices of bread spread thick with cream and heaped with brined roe and cloudberries.",
                Recipe = new[] { ("Bread", 1), (Roe, 2), ("Cloudberry", 2) } },
            new Food { Id = "ink_noodles", Name = "Ink-Black Noodles", Level = 4, Health = 45, Stamina = 30, Eitr = 75, Regen = 4,
                Desc = "Noodles dyed black with abyssal ink, in a dark broth with fish and jotun puffs. They hum faintly.",
                Recipe = new[] { (Fillet, 1), ("VDW_Mat_ink", 1), ("MushroomJotunPuffs", 2) } },
            new Food { Id = "ember_fillet", Name = "Ember-Grilled Fillet", Level = 5, Health = 85, Stamina = 50, Regen = 6,
                Desc = "Thick fillets seared on glowing cinder scales and glazed with vineberries.",
                Recipe = new[] { (Fillet, 2), ("VDW_Mat_cinder", 1), ("Vineberry", 2) } },
            new Food { Id = "rime_salmon", Name = "Rime-Cured Salmon", Station = "piece_preptable", Level = 1, Health = 80, Stamina = 70, Eitr = 30, Regen = 6, Duration = 2000,
                Desc = "Fillets cured cold in rime scales and lingonberries, sliced thin. It keeps forever and tastes of the north.",
                Recipe = new[] { (Fillet, 2), ("VDW_Mat_rime", 1), ("Lingonberry", 2) } },
            new Food { Id = "travel_rations", Name = "Fisherman's Rations", Station = "piece_preptable", Level = 1, Health = 35, Stamina = 35, Regen = 2, Duration = 3600,
                Desc = "Dried fish, cloudberries and honey wrapped in a cloth. Light, and it lasts a long voyage.",
                Recipe = new[] { (Dried, 2), ("Cloudberry", 2), ("Honey", 1) } },
        };

        /// <summary>Grilled on a cooking station (or the iron one) from a fish fillet.</summary>
        private static readonly Food Grilled = new Food { Id = "grilled_fillet", Name = "Grilled Fish Fillet", Health = 25, Stamina = 22, Regen = 2, Duration = 1200,
            Desc = "A fillet grilled over the fire, skin crisp and flaking." };

        public static void Register()
        {
            RegisterIngredients();
            foreach (var d in Dishes) AddFood(d, new ItemConfig
            {
                Amount = d.Amount,
                CraftingStation = d.Station,
                MinStationLevel = d.Level,
                Requirements = d.Recipe.Select(r => new RequirementConfig(r.item, r.amount)).ToArray()
            });
            AddFood(Grilled, null);
            foreach (var station in new[] { "piece_cookingstation", "piece_cookingstation_iron" })
            {
                try
                {
                    ItemManager.Instance.AddItemConversion(new CustomItemConversion(new CookingConversionConfig
                    { Station = station, FromItem = Fillet, ToItem = "VDW_Dish_" + Grilled.Id, CookTime = 25f }));
                }
                catch (Exception ex) { Plugin.Log.LogWarning($"Grilled fillet on {station} failed ({ex.Message})."); }
            }
        }

        /// <summary>The three prepared ingredients, made at the Fish Cleaning Table once it has the add-on for each.</summary>
        private static void RegisterIngredients()
        {
            // fillets: from any one food fish (not baitfish or legendaries), more from a bigger one
            var fish = ContentRegistry.Fish.Values
                .Where(f => !f.Legendary && string.IsNullOrWhiteSpace(f.CatchBait) && !string.IsNullOrWhiteSpace(f.Material))
                .Select(f => ContentRegistry.DropFor(f)).Where(d => d != null).Select(d => d!.gameObject.name).Distinct().ToList();
            AddIngredient(Fillet, "fillet", "Fish Fillets", "Boneless fillets cut at a cleaning table with a filleting knife rack. Grill them, or cook them into stews and soups.", "FishRaw",
                new RecipeConfig { Amount = 2, CraftingStation = FishMaterials.Table, MinStationLevel = 2, RequireOnlyOneIngredient = true, QualityResultAmountMultiplier = 1,
                    Requirements = fish.Select(f => new RequirementConfig(f, 1, 0, false)).ToArray() });
            AddIngredient(Roe, "roe", "Brined Roe", "Fish roe soaked in a brining barrel until it pops. For roe flatbread.", "Honey",
                new RecipeConfig { Amount = 2, CraftingStation = FishMaterials.Table, MinStationLevel = 3,
                    Requirements = new[] { new RequirementConfig("VDW_Mat_roe", 3), new RequirementConfig("VDW_Mat_oil", 1) } });
            AddIngredient(Dried, "dried", "Dried Fish", "Fillets hung on a drying line until they're hard as wood. They keep for a whole voyage.", "FishRaw",
                new RecipeConfig { Amount = 2, CraftingStation = FishMaterials.Table, MinStationLevel = 4,
                    Requirements = new[] { new RequirementConfig(Fillet, 3) } });
        }

        private static void AddIngredient(string prefab, string id, string name, string desc, string standIn, RecipeConfig recipe)
        {
            var item = new CustomItem(prefab, standIn);
            if (item.ItemDrop == null) { Plugin.Log.LogWarning($"Ingredient '{id}': stand-in '{standIn}' not found."); return; }
            var s = item.ItemDrop.m_itemData.m_shared;
            s.m_name = Loc.Token("vdw_prep_" + id, name);
            s.m_description = Loc.Token("vdw_prep_" + id + "_desc", desc);
            s.m_itemType = ItemDrop.ItemData.ItemType.Material;
            s.m_food = 0; s.m_foodStamina = 0; s.m_foodEitr = 0;
            s.m_weight = 0.2f; s.m_maxStackSize = 50; s.m_value = 0; s.m_teleportable = true;
            if (CustomModels.ApplyToPrefab(item.ItemPrefab, "prep_" + id)) GroundPose.FitCollider(item.ItemPrefab);
            ItemManager.Instance.AddItem(item);
            recipe.Name = "Recipe_" + prefab;
            recipe.Item = prefab;
            ItemManager.Instance.AddRecipe(new CustomRecipe(recipe));
        }

        private static void AddFood(Food d, ItemConfig? config)
        {
            var item = config != null ? new CustomItem("VDW_Dish_" + d.Id, "FishWraps", config) : new CustomItem("VDW_Dish_" + d.Id, "FishWraps");
            if (item.ItemDrop == null) { Plugin.Log.LogWarning($"Dish '{d.Id}': vanilla 'FishWraps' not found."); return; }
            var s = item.ItemDrop.m_itemData.m_shared;
            s.m_name = Loc.Token("vdw_dish_" + d.Id, d.Name);
            s.m_description = Loc.Token("vdw_dish_" + d.Id + "_desc", d.Desc);
            s.m_food = d.Health; s.m_foodStamina = d.Stamina; s.m_foodEitr = d.Eitr;
            s.m_foodRegen = d.Regen; s.m_foodBurnTime = d.Duration;
            s.m_value = 0;
            if (CustomModels.ApplyToPrefab(item.ItemPrefab, "food_" + d.Id)) GroundPose.FitCollider(item.ItemPrefab);
            ItemManager.Instance.AddItem(item);
        }
    }
}
