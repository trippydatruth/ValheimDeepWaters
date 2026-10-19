using Jotunn.Configs;
using Jotunn.Entities;
using Jotunn.Managers;
using System;
using System.Linq;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// The Bog Witch's side of fishing: a fish feast for each of her herb blends (placed with her Serving Tray and shared
    /// by everyone, like vanilla feasts), and her stock - the mod's witchy brews, and each boss lure once you've beaten
    /// its boss, so a failed summoning isn't a whole new trophy hunt. Her other wares (pungent pebbles, seaweed, the love
    /// potion, candle wick, dragon eggshell, toadstool) go into the brews, bait and meads in the data files.
    /// </summary>
    internal static class BogWitch
    {
        private sealed class FeastDef
        {
            public string Id = "", Name = "", Desc = "";
            public int Level;
            public (string item, int amount)[] Recipe = new (string, int)[0];
            public float Health, Stamina, Eitr, Regen, Duration = 2400f;
        }

        private static readonly FeastDef[] Feasts =
        {
            new FeastDef { Id = "forest", Name = "Lakeside Fish Fry", Level = 2, Health = 40, Stamina = 40, Regen = 3,
                Desc = "Lake fish fried in their own oil with forest mushrooms and the witch's woodland herbs. Set it out for everyone.",
                Recipe = new[] { (FishDishes.Fillet, 6), ("VDW_Mat_oil", 2), ("SpiceForests", 1), ("Mushroom", 4) } },
            new FeastDef { Id = "mountain", Name = "Fin and Onion Hotpot", Level = 3, Health = 55, Stamina = 50, Regen = 3,
                Desc = "A great pot of fin broth and onions, peppered hot with mountain peak powder.",
                Recipe = new[] { (FishDishes.Fillet, 6), ("VDW_Mat_fins", 4), ("SpiceMountains", 1), ("Onion", 4) } },
            new FeastDef { Id = "ocean", Name = "Sea-Fish Spread", Level = 3, Health = 50, Stamina = 60, Regen = 4,
                Desc = "Sea fish laid out on fresh seaweed with roe and the seafarer's herbs.",
                Recipe = new[] { (FishDishes.Fillet, 6), ("VDW_Mat_roe", 2), ("SpiceOceans", 1), ("FreshSeaweed", 3) } },
            new FeastDef { Id = "plains", Name = "Roe and Barley Platter", Level = 4, Health = 60, Stamina = 70, Regen = 4,
                Desc = "Bread and brined roe heaped with fillets, dusted with the grasslands herbalist's harvest.",
                Recipe = new[] { (FishDishes.Roe, 4), (FishDishes.Fillet, 4), ("SpicePlains", 1), ("Bread", 2) } },
            new FeastDef { Id = "mistlands", Name = "Abyssal Ink Banquet", Level = 5, Health = 60, Stamina = 45, Eitr = 70, Regen = 5,
                Desc = "Black-inked fish and jotun puffs from the hidden hills. It hums on the table.",
                Recipe = new[] { (FishDishes.Fillet, 6), ("VDW_Mat_ink", 2), ("SpiceMistlands", 1), ("MushroomJotunPuffs", 4) } },
            new FeastDef { Id = "ashlands", Name = "Ember Fish Platter", Level = 5, Health = 85, Stamina = 60, Regen = 6,
                Desc = "Fillets seared on cinder scales and glazed with vineberries and fiery spice.",
                Recipe = new[] { (FishDishes.Fillet, 6), ("VDW_Mat_cinder", 2), ("SpiceAshlands", 1), ("Vineberry", 4) } },
            new FeastDef { Id = "deepnorth", Name = "Rime Fish Smorgasbord", Level = 5, Health = 90, Stamina = 75, Eitr = 35, Regen = 6, Duration = 3000,
                Desc = "Dried and rime-cured fish with lingonberries and northern spice, laid out for a long night.",
                Recipe = new[] { (FishDishes.Dried, 4), ("VDW_Mat_rime", 2), ("SpiceDeepNorth", 1), ("Lingonberry", 4) } },
        };

        /// <summary>What she sells (by prefab), the stack, the price and the world key she waits for.</summary>
        private static readonly (string prefab, int stack, int price, string key)[] Stock =
        {
            ("VDW_Bait_stinkbait", 10, 60, ""),
            ("VDW_Buff_lantern_float", 2, 120, ""),
            ("VDW_Buff_spawning_musk", 1, 250, "defeated_bonemass"),
            ("VDW_Bait_lure_antler", 1, 300, "defeated_eikthyr"),
            ("VDW_Bait_lure_root", 1, 500, "defeated_gdking"),
            ("VDW_Bait_lure_ooze", 1, 700, "defeated_bonemass"),
            ("VDW_Bait_lure_wyrm", 1, 900, "defeated_dragon"),
            ("VDW_Bait_lure_ember", 1, 1200, "defeated_goblinking"),
            ("VDW_Bait_lure_chitin", 1, 1500, "defeated_queen"),
        };

        public static void Register()
        {
            foreach (var f in Feasts)
            {
                try { AddFeast(f); }
                catch (Exception ex) { Plugin.Log.LogError($"Fish feast '{f.Id}' failed: {ex.Message}"); }
            }
            StockTrader();
        }

        /// <summary>
        /// A feast is two prefabs, like vanilla's: the item crafted at the cauldron (it carries the food), and the table
        /// placed with the Serving Tray (a copy of Sailor's Bounty) that everyone eats from.
        /// </summary>
        private static void AddFeast(FeastDef f)
        {
            string itemName = "VDW_Feast_" + f.Id + "_Material";
            var item = new CustomItem(itemName, "FeastOceans_Material", new ItemConfig
            {
                Amount = 1,
                CraftingStation = "piece_cauldron",
                MinStationLevel = f.Level,
                Requirements = f.Recipe.Select(r => new RequirementConfig(r.item, r.amount)).ToArray()
            });
            if (item.ItemDrop == null) { Plugin.Log.LogWarning("Fish feasts: vanilla 'FeastOceans_Material' not found."); return; }
            var s = item.ItemDrop.m_itemData.m_shared;
            string title = Loc.Token("vdw_feast_" + f.Id, f.Name);
            s.m_name = title;
            s.m_description = Loc.Token("vdw_feast_" + f.Id + "_desc", f.Desc + "\n\nSet it down with a Serving Tray.");
            s.m_value = 0;
            ItemManager.Instance.AddItem(item);

            // what each serving is: the game only lets you eat from a feast whose food item is a consumable, and the
            // crafted feast is a material (like vanilla's), so the servings are a food item of their own
            var serving = new CustomItem("VDW_Feast_" + f.Id + "_Serving", "FishWraps");
            if (serving.ItemDrop == null) { Plugin.Log.LogWarning("Fish feasts: vanilla 'FishWraps' not found."); return; }
            var fs = serving.ItemDrop.m_itemData.m_shared;
            fs.m_name = title;
            fs.m_description = Loc.Token("vdw_feast_" + f.Id + "_desc", f.Desc);
            fs.m_itemType = ItemDrop.ItemData.ItemType.Consumable;
            fs.m_food = f.Health; fs.m_foodStamina = f.Stamina; fs.m_foodEitr = f.Eitr; fs.m_foodRegen = f.Regen; fs.m_foodBurnTime = f.Duration;
            fs.m_value = 0;
            ItemIcons.ApplyHandMadeOnly(serving.ItemPrefab, "piece_feast_" + f.Id);
            ItemManager.Instance.AddItem(serving);

            var piece = new CustomPiece("VDW_Feast_" + f.Id, "FeastOceans", new PieceConfig
            {
                Name = title,
                Description = Loc.Token("vdw_feast_" + f.Id + "_desc", f.Desc),
                PieceTable = "_FeasterPieceTable",
                Requirements = new[] { new RequirementConfig(itemName, 1, 0, true) }
            });
            var feast = piece.PiecePrefab.GetComponent<Feast>();
            if (feast != null) feast.m_foodItem = serving.ItemDrop;
            else Plugin.Log.LogWarning($"Fish feast '{f.Id}': the copied table has no Feast component.");

            // its own model in place of Sailor's Bounty: the board stays, the food steps down through three stages as
            // it's eaten (food_full above two thirds, food_half above one third, food_low until the last serving)
            string key = "piece_feast_" + f.Id;
            if (CustomModels.ApplyToPrefab(piece.PiecePrefab, key))
            {
                PieceDressing.Dress(piece.PiecePrefab);
                var model = piece.PiecePrefab.transform.Find("vdw_model");
                GameObject? Stage(string n) => model == null ? null
                    : model.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name.StartsWith(n))?.gameObject;
                GameObject? full = Stage("food_full"), half = Stage("food_half"), low = Stage("food_low");
                if (feast != null && full != null)
                {
                    feast.m_feastParts = new System.Collections.Generic.List<Feast.FeastLevel>
                    {
                        new Feast.FeastLevel { m_onAboveEquals = full, m_threshold = 0.66f },
                        new Feast.FeastLevel { m_onBelow = half, m_threshold = 0.66f, m_thresholdBelowMax = 0.33f },
                        new Feast.FeastLevel { m_onBelow = low, m_threshold = 0.33f, m_thresholdBelowMax = 0.01f },
                    };
                    if (half != null) half.SetActive(false);
                    if (low != null) low.SetActive(false);
                }
            }
            ItemIcons.ApplyHandMadeOnly(item.ItemPrefab, key);
            PieceManager.Instance.AddPiece(piece);
        }

        private static void StockTrader()
        {
            var trader = PrefabManager.Instance.GetPrefab("BogWitch")?.GetComponent<Trader>();
            if (trader == null) { Plugin.Log.LogWarning("Bog Witch not found; her fishing stock isn't added."); return; }
            foreach (var (prefab, stack, price, key) in Stock)
            {
                var drop = PrefabManager.Instance.GetPrefab(prefab)?.GetComponent<ItemDrop>();
                if (drop == null) { Plugin.Log.LogWarning($"Bog Witch: '{prefab}' doesn't exist; not stocked."); continue; }
                trader.m_items.Add(new Trader.TradeItem { m_prefab = drop, m_stack = stack, m_price = price, m_requiredGlobalKey = key });
            }
        }
    }
}
