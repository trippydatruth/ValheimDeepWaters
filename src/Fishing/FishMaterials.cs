using HarmonyLib;
using Jotunn.Configs;
using Jotunn.Entities;
using Jotunn.Managers;
using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// Cleaning a catch at the Fish Cleaning Table gives its biome's material (Fish.json "Material"); bigger size classes
    /// give more. The table's add-ons (knife rack, brining barrel, drying line) raise its level, and the later materials
    /// need a higher level. The materials go into rod upgrades, lures, baits, meads, chum, totems and dishes. A
    /// Trophy-size catch also gives a Trophy Fin, which only a rod's last upgrade level asks for.
    /// </summary>
    internal static class FishMaterials
    {
        private sealed class Material
        {
            public string Id = "", Name = "", Desc = "", StandIn = "";
            public int Amount = 2;            // per Small fish; each size class above adds as many again
            public int Level = 1;             // the cleaning table level it needs
        }

        private static readonly Material[] All =
        {
            new Material { Id = "scales", Name = "Fish Scales", StandIn = "SerpentScale",
                Desc = "Scraped from the freshwater fish of the Meadows and Black Forest." },
            new Material { Id = "oil", Name = "Fish Oil", StandIn = "Ooze",
                Desc = "Rendered from oily swamp and coastal fish. It smells as you'd expect." },
            new Material { Id = "fins", Level = 2, Name = "Spiny Fins", StandIn = "BoneFragments",
                Desc = "Sharp fin rays cut from mountain and reef fish." },
            new Material { Id = "roe", Level = 2, Name = "Fish Roe", StandIn = "Entrails",
                Desc = "Eggs from the big fish of the open sea." },
            new Material { Id = "ink", Level = 3, Name = "Abyssal Ink", StandIn = "Guck",
                Desc = "Black ink from deep-sea and Mistlands fish. It stains everything." },
            new Material { Id = "cinder", Level = 4, Name = "Cinder Scales", StandIn = "Coal",
                Desc = "Still warm. Scraped from the fish of the Ashlands." },
            new Material { Id = "rime", Level = 4, Name = "Rime Scales", StandIn = "FreezeGland",
                Desc = "Frost-hard scales from the fish of the Deep North." },
            new Material { Id = "legend", Level = 3, Name = "Legendary Scale", StandIn = "SerpentScale", Amount = 1,
                Desc = "A single great scale from a legendary fish." },
        };

        public const string TrophyFin = "VDW_Mat_trophy";

        public static string PrefabName(string id) => "VDW_Mat_" + id;

        public const string Table = "VDW_CleaningTable";

        public static void Register()
        {
            foreach (var m in All) AddItem(m.Id, m.Name, m.Desc, m.StandIn);
            RegisterTable();
            AddItem("trophy", "Trophy Fin", "Kept from a Trophy-size catch: proof of a fish worth bragging about. Rods need one for their last upgrade.", "Feathers");

            // one cleaning recipe per material: any one fish of its kind, more from a bigger one
            foreach (var m in All)
            {
                var fish = ContentRegistry.Fish.Values
                    .Where(f => string.Equals(f.Material, m.Id, StringComparison.OrdinalIgnoreCase) && string.IsNullOrWhiteSpace(f.CatchBait))
                    .Select(f => ContentRegistry.DropFor(f)).Where(d => d != null).Select(d => d!.gameObject.name)
                    .Distinct().ToList();
                if (fish.Count == 0) continue;
                ItemManager.Instance.AddRecipe(new CustomRecipe(new RecipeConfig
                {
                    Name = "Recipe_VDW_Clean_" + m.Id,
                    Item = PrefabName(m.Id),
                    Amount = m.Amount,
                    CraftingStation = Table,
                    MinStationLevel = m.Level,
                    RequireOnlyOneIngredient = true,
                    QualityResultAmountMultiplier = 1,
                    Requirements = fish.Select(f => new RequirementConfig(f, 1, 0, false)).ToArray()
                }));
            }

            ItemManager.OnItemsRegistered -= CheckRecipeItems;
            ItemManager.OnItemsRegistered += CheckRecipeItems;
        }

        /// <summary>
        /// The Fish Cleaning Table: a crafting station of its own (a copy of the workbench, without its roof, building
        /// rights or repairs), raised a level by each of its three add-ons, which stand within a few metres of it.
        /// </summary>
        private static void RegisterTable()
        {
            var table = new CustomPiece(Table, "piece_workbench", new PieceConfig
            {
                Name = Loc.Token("vdw_piece_cleaning_table", "Fish Cleaning Table"),
                Description = Loc.Token("vdw_piece_cleaning_table_desc", "A gutting table for cleaning your catch into scales, oil, fins and more. Its add-ons let it handle the rarer fish and prepare fillets, brined roe and dried fish for cooking."),
                PieceTable = "Hammer",
                Category = "Crafting",
                CraftingStation = "piece_workbench",
                Requirements = new[] { new RequirementConfig("Wood", 10), new RequirementConfig("Flint", 4), new RequirementConfig("Resin", 4) }
            });
            var station = table.PiecePrefab.GetComponent<CraftingStation>();
            if (station != null)
            {
                station.m_name = Loc.Token("vdw_piece_cleaning_table", "Fish Cleaning Table");
                station.m_craftRequireRoof = false;
                station.m_craftRequireFire = false;
                station.m_showBasicRecipies = false;
                station.m_canRepair = false;
                station.m_rangeBuild = 6f;                     // only for placing its add-ons
                station.m_craftingSkill = Skills.SkillType.Fishing;
            }
            if (CustomModels.ApplyToPrefab(table.PiecePrefab, "piece_cleaning_table")) PieceDressing.Dress(table.PiecePrefab);
            // the station's own icon (crafting panel, "station level" popup) is separate from the build menu's
            if (station != null && table.Piece.m_icon != null) station.m_icon = table.Piece.m_icon;
            PieceManager.Instance.AddPiece(table);

            AddExtension(1, "Filleting Knife Rack", "Thin knives for filleting. Fish Cleaning Table level 2: cleans for Spiny Fins and Fish Roe, and cuts Fish Fillets.",
                new RequirementConfig("FineWood", 4), new RequirementConfig("Bronze", 2), new RequirementConfig(PrefabName("scales"), 10));
            AddExtension(2, "Brining Barrel", "An iron-bound barrel of brine. Fish Cleaning Table level 3: cleans for Abyssal Ink and Legendary Scales, and brines roe.",
                new RequirementConfig("FineWood", 6), new RequirementConfig("Iron", 2), new RequirementConfig(PrefabName("oil"), 10));
            AddExtension(3, "Drying Line", "A pole frame strung with jute for hanging fish to dry. Fish Cleaning Table level 4: cleans for Cinder and Rime Scales, and dries fish.",
                new RequirementConfig("FineWood", 6), new RequirementConfig("JuteRed", 3), new RequirementConfig(PrefabName("ink"), 10));
        }

        private static void AddExtension(int n, string name, string desc, params RequirementConfig[] reqs)
        {
            var ext = new CustomPiece(Table + "_ext" + n, "piece_workbench_ext1", new PieceConfig
            {
                Name = Loc.Token($"vdw_piece_cleaning_ext{n}", name),
                Description = Loc.Token($"vdw_piece_cleaning_ext{n}_desc", desc),
                PieceTable = "Hammer",
                Category = "Crafting",
                CraftingStation = Table,
                ExtendStation = Table,
                Requirements = reqs
            });
            if (CustomModels.ApplyToPrefab(ext.PiecePrefab, "piece_cleaning_ext" + n)) PieceDressing.Dress(ext.PiecePrefab);
            if (n == 1)
            {
                // the knife rack can hang on a wall (above the table) as well as stand on the floor
                var p = ext.Piece;
                p.m_groundOnly = false;
                p.m_groundPiece = false;
                p.m_cultivatedGroundOnly = false;
                p.m_notOnTiltingSurface = false;
                p.m_notOnFloor = false;
                p.m_clipGround = false;
            }
            PieceManager.Instance.AddPiece(ext);
        }

        private static void AddItem(string id, string name, string desc, string standIn)
        {
            var item = new CustomItem(PrefabName(id), standIn);
            if (item.ItemDrop == null) { Plugin.Log.LogWarning($"Fish material '{id}': stand-in '{standIn}' not found."); return; }
            var shared = item.ItemDrop.m_itemData.m_shared;
            shared.m_name = Loc.Token("vdw_mat_" + id, name);
            shared.m_description = Loc.Token("vdw_mat_" + id + "_desc", desc);
            shared.m_itemType = ItemDrop.ItemData.ItemType.Material;
            shared.m_weight = 0.1f;
            shared.m_maxStackSize = 50;
            shared.m_value = 0;
            shared.m_teleportable = true;
            if (CustomModels.ApplyToPrefab(item.ItemPrefab, "mat_" + id)) GroundPose.FitCollider(item.ItemPrefab);
            ItemManager.Instance.AddItem(item);
        }

        /// <summary>A Trophy-size catch also gives a Trophy Fin. Returns the line for the catch message, or "".</summary>
        public static string GiveTrophyFin(Player player, Vector3 pos)
        {
            var fin = PrefabManager.Instance.GetPrefab(TrophyFin)?.GetComponent<ItemDrop>();
            if (fin == null) return "";
            Drops.Give(player, fin, 1, pos);
            return $"\n+1 {Loc.Text(fin.m_itemData.m_shared.m_name)}";
        }

        /// <summary>
        /// The Trophy Fin in a rod's Upgrade list is only asked for at the last level (vanilla would ask for it at every
        /// level, 1, 2 and 4 of them).
        /// </summary>
        [HarmonyPatch(typeof(Piece.Requirement), nameof(Piece.Requirement.GetAmount))]
        private static class TrophyFinLastLevel
        {
            private static void Postfix(Piece.Requirement __instance, int qualityLevel, ref int __result)
            {
                if (__instance.m_amount != 0 || __instance.m_resItem == null || __instance.m_resItem.gameObject.name != TrophyFin) return;
                __result = qualityLevel >= RodUpgrades.MaxLevel ? __instance.m_amountPerLevel : 0;
            }
        }

        /// <summary>A recipe item the game doesn't know (a typo in a data file, or an item from a newer game) is named in the log.</summary>
        private static void CheckRecipeItems()
        {
            ItemManager.OnItemsRegistered -= CheckRecipeItems;
            if (ObjectDB.instance == null) return;
            var names = ContentRegistry.Rods.SelectMany(r => r.Recipe.Concat(r.Upgrade)).Select(r => r.Item)
                .Concat(ContentRegistry.Baits.Values.SelectMany(b => b.Recipe).Select(r => r.Item))
                .Concat(ContentRegistry.Hooks.Values.SelectMany(h => h.Recipe).Select(r => r.Item))
                .Concat(ContentRegistry.Tackle.Values.SelectMany(g => g.Recipe).Select(r => r.Item))
                .Concat(FishingBuffs.Buffs.Values.SelectMany(b => b.Recipe).Select(r => r.Item))
                .Distinct();
            var missing = names.Where(n => !string.IsNullOrWhiteSpace(n) && ObjectDB.instance.GetItemPrefab(n) == null).ToList();
            if (missing.Count > 0) Plugin.Log.LogWarning($"Recipe items the game doesn't have: {string.Join(", ", missing)}.");
        }
    }
}
