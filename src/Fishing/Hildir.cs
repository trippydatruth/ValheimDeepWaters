using Jotunn.Configs;
using Jotunn.Entities;
using Jotunn.Managers;
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// Hildir's fishing side.
    ///   Lost tackle boxes - three of hers, lost in Sunken Crypts, Frost Caves and the dvergr ruins of the Mistlands, turning
    ///   up in their chests. Give one back (use it on her like her lost chests, or from the trade panel) and her shop gains
    ///   a dyed set of the Fisherman's gear and some tackle.
    ///   Bounties - one a day: a species you've caught, at least so heavy, sometimes caught in the rain, at night or
    ///   Trophy-size. Hand the fish in at the trade panel for coins and bait; the 5th, 15th and 30th earn relics.
    /// </summary>
    internal static class Hildir
    {
        private sealed class Box
        {
            public string Id = "", Name = "", Where = "", Key = "", Dye = "", Line = "";
            public string[] Chests = new string[0];
            public Color Tint;
            public (string prefab, int stack, int price)[] Tackle = new (string, int, int)[0];
        }

        private static readonly Box[] Boxes =
        {
            new Box { Id = "swamp", Name = "Hildir's Mossy Tackle Box", Where = "Sunken Crypts", Key = "vdw_tacklebox_swamp",
                Dye = "Bog-Dyed", Tint = new Color(0.62f, 0.85f, 0.5f), Chests = new[] { "TreasureChest_sunkencrypt" },
                Line = "My tackle box! I dropped it running from the draugr. Here - I've had these dyed in bog moss for you.",
                Tackle = new[] { ("VDW_Bait_lure_guck_crawler", 3, 150), ("VDW_Bait_lure_leather_grub", 5, 90) } },
            new Box { Id = "mountain", Name = "Hildir's Frosted Tackle Box", Where = "Frost Caves", Key = "vdw_tacklebox_mountain",
                Dye = "Frost-Dyed", Tint = new Color(0.78f, 0.88f, 1.05f), Chests = new[] { "TreasureChest_mountaincave" },
                Line = "You went into the caves for this? It's frozen solid. Have the frost-dyed set, and my good swimbaits.",
                Tackle = new[] { ("VDW_Bait_lure_silver_swimbait", 2, 240), ("VDW_Bait_frost_bait", 10, 160) } },
            new Box { Id = "mistlands", Name = "Hildir's Dvergr-Mended Tackle Box", Where = "the dvergr ruins of the Mistlands", Key = "vdw_tacklebox_mistlands",
                Dye = "Mist-Dyed", Tint = new Color(0.78f, 0.64f, 0.98f), Chests = new[] { "TreasureChest_dvergrtown", "TreasureChest_dvergrtower" },
                Line = "The dvergr mended it! Look at these hinges. The mist-dyed set is yours to buy, and the deep-water tackle.",
                Tackle = new[] { ("VDW_Bait_lure_bone_jig", 3, 220), ("VDW_Bait_deep_bait", 10, 200) } },
        };

        private static readonly (string prefab, string piece, int price)[] Gear =
        {
            ("VDW_FisherHat", "Sou'wester", 250), ("VDW_FisherCoat", "Oilskin Coat", 450),
            ("VDW_FisherShirt", "Striped Fisher's Shirt", 300), ("VDW_FisherOveralls", "Oilskin Overalls", 450),
        };

        private static string BoxPrefab(Box b) => "VDW_TackleBox_" + b.Id;

        public static void Register()
        {
            var trader = PrefabManager.Instance.GetPrefab("Hildir")?.GetComponent<Trader>();
            if (trader == null) { Plugin.Log.LogWarning("Hildir not found; her fishing quests aren't added."); return; }
            foreach (var b in Boxes)
            {
                try
                {
                    var box = AddBox(b);
                    if (box == null) continue;
                    trader.m_useItems.Add(new Trader.TraderUseItem { m_prefab = box, m_setsGlobalKey = b.Key, m_removesItem = true, m_dialog = b.Line });
                    foreach (var chest in b.Chests) AddToChest(chest, box.gameObject);
                    foreach (var (prefab, stack, price) in b.Tackle)
                    {
                        var drop = PrefabManager.Instance.GetPrefab(prefab)?.GetComponent<ItemDrop>();
                        if (drop != null) trader.m_items.Add(new Trader.TradeItem { m_prefab = drop, m_stack = stack, m_price = price, m_requiredGlobalKey = b.Key });
                    }
                    foreach (var (prefab, piece, price) in Gear)
                    {
                        var dyed = AddDyed(prefab, b, piece);
                        if (dyed != null) trader.m_items.Add(new Trader.TradeItem { m_prefab = dyed, m_stack = 1, m_price = price, m_requiredGlobalKey = b.Key });
                    }
                }
                catch (Exception ex) { Plugin.Log.LogError($"Hildir's tackle box '{b.Id}' failed: {ex.Message}"); }
            }
            TraderPanel.ExtraSection = Section;
        }

        private static ItemDrop? AddBox(Box b)
        {
            var item = new CustomItem(BoxPrefab(b), "Ruby");
            if (item.ItemDrop == null) return null;
            var s = item.ItemDrop.m_itemData.m_shared;
            s.m_name = Loc.Token("vdw_tacklebox_" + b.Id, b.Name);
            s.m_description = Loc.Token("vdw_tacklebox_" + b.Id + "_desc", $"A battered tackle box with Hildir's mark on the lid, lost in the {b.Where}. She'd want it back.");
            s.m_itemType = ItemDrop.ItemData.ItemType.Material;
            s.m_value = 0; s.m_maxStackSize = 1; s.m_weight = 3f; s.m_teleportable = true;
            if (CustomModels.ApplyToPrefab(item.ItemPrefab, "tacklebox_" + b.Id)) GroundPose.FitCollider(item.ItemPrefab);
            ItemManager.Instance.AddItem(item);
            return item.ItemDrop;
        }

        /// <summary>The box joins a dungeon chest's loot: about one chest in four holds it.</summary>
        private static void AddToChest(string chestName, GameObject box)
        {
            var c = PrefabManager.Instance.GetPrefab(chestName)?.GetComponent<Container>();
            if (c == null) { Plugin.Log.LogWarning($"Hildir: chest '{chestName}' not found; its tackle box can't turn up there."); return; }
            var table = c.m_defaultItems;
            float sum = table.m_drops.Sum(d => d.m_weight);
            float picks = Mathf.Max(1f, (table.m_dropMin + table.m_dropMax) / 2f);
            float share = Mathf.Clamp(1f - Mathf.Pow(1f - 0.25f, 1f / picks), 0.02f, 0.5f);   // per pick, so ~25% per chest
            table.m_drops.Add(new DropTable.DropData { m_item = box, m_stackMin = 1, m_stackMax = 1, m_weight = sum > 0 ? sum * share / (1f - share) : 1f, m_dontScale = true });
        }

        /// <summary>A dyed copy of a Fisherman's gear piece: the same item and set, its materials tinted.</summary>
        private static ItemDrop? AddDyed(string basePrefab, Box b, string piece)
        {
            if (PrefabManager.Instance.GetPrefab(basePrefab) == null) return null;
            var item = new CustomItem(basePrefab + "_" + b.Id, basePrefab);
            if (item.ItemDrop == null) return null;
            var s = item.ItemDrop.m_itemData.m_shared;
            s.m_name = Loc.Token($"vdw_{basePrefab.ToLowerInvariant()}_{b.Id}", $"{b.Dye} {piece}");
            foreach (var r in item.ItemPrefab.GetComponentsInChildren<Renderer>(true))
            {
                r.sharedMaterials = r.sharedMaterials.Select(m =>
                {
                    if (m == null) return m;
                    var t = new Material(m) { name = m.name + "_" + b.Id };
                    if (t.HasProperty("_Color")) t.SetColor("_Color", t.GetColor("_Color") * b.Tint);
                    return t;
                }).ToArray();
            }
            ItemManager.Instance.AddItem(item);

            // Repair needs a recipe for the item at the station - but not an enabled one, and only enabled recipes show
            // in the crafting list. So this one makes the dyed gear repairable at the workbench (level 2, like the
            // Fisherman's set) without it ever being craftable: Hildir is still the only way to get it.
            ItemManager.Instance.AddRecipe(new CustomRecipe(new RecipeConfig
            {
                Name = "Recipe_" + item.ItemPrefab.name,
                Item = item.ItemPrefab.name,
                CraftingStation = "piece_workbench",
                RepairStation = "piece_workbench",
                MinStationLevel = 2,
                Enabled = false,
                Requirements = new[] { new RequirementConfig(basePrefab, 1) }
            }));
            return item.ItemDrop;
        }

        // ------------------------------------------------------------------ bounties

        private const string DoneKey = "vdw_bounty_done_day", CountKey = "vdw_bounties";
        // her prizes: the things Haldor sells that can't be crafted, and the Horn, her relic (roadmaps #27, #30);
        // vanilla items by their name token, so a renamed prefab can't break them
        private static readonly (int count, string prefab, int amount, string name)[] Milestones =
        {
            (5, "$item_helmet_yule", 1, "a Yule Hat"), (10, "$item_thunderstone", 1, "a Thunder Stone"), (15, Relics.Horn, 1, "the Horn of Ægir"),
            (20, "$item_helmet_dverger", 1, "a Dverger Circlet"), (30, "$item_beltstrength", 1, "Megingjord"),
        };

        private sealed class Bounty
        {
            public FishDefinition Fish = null!;
            public float MinKg;
            public string Condition = "";          // "", "rain", "night", "trophy"
            public int Coins;
            public string Text => $"Bring me a {Fish.Name} of at least {MinKg:0.#} kg" + Condition switch
            {
                "rain" => ", caught in the rain.",
                "night" => ", caught at night.",
                "trophy" => " - a Trophy-size one.",
                _ => "."
            };
        }

        private static int Day() => EnvMan.instance != null ? EnvMan.instance.GetDay(ZNet.instance != null ? ZNet.instance.GetTimeSeconds() : 0) : 0;

        /// <summary>Today's bounty for this player: one of the species they've caught (the same all day).</summary>
        private static Bounty? Today(Player player)
        {
            var caught = CatchLog.Load(player).Keys
                .Select(id => ContentRegistry.Fish.TryGetValue(id, out var f) ? f : null)
                .Where(f => f != null && !f.Legendary && string.IsNullOrWhiteSpace(f!.CatchBait)).Select(f => f!).OrderBy(f => f.Id).ToList();
            if (caught.Count == 0) return null;
            var rnd = new System.Random(Day() * 7919 + (int)(player.GetPlayerID() & 0x7fffffff));
            var fish = caught[rnd.Next(caught.Count)];
            string cond = new[] { "", "", "rain", "night", "trophy" }[rnd.Next(5)];
            if (cond == "night" && string.Equals(fish.ActiveTime, "Day", StringComparison.OrdinalIgnoreCase)) cond = "";
            float frac = cond == "trophy" ? FishingController.TrophyThreshold : 0.35f + 0.3f * (float)rnd.NextDouble();
            float kg = fish.MinWeightKg + (fish.MaxWeightKg - fish.MinWeightKg) * frac;
            int coins = Mathf.RoundToInt((60f + fish.MaxWeightKg * 4f + fish.FightStrength * 25f) * (cond == "" ? 1f : 1.5f) / 10f) * 10;
            return new Bounty { Fish = fish, MinKg = kg, Condition = cond, Coins = coins };
        }

        private static bool Meets(ItemDrop.ItemData item, Bounty b)
        {
            if (item.m_dropPrefab == null || ContentRegistry.DropFor(b.Fish)?.gameObject.name != item.m_dropPrefab.name) return false;
            var data = item.m_customData;
            if (data == null || !data.TryGetValue("vdw_weight_kg", out var raw) || !float.TryParse(raw, NumberStyles.Float, CultureInfo.InvariantCulture, out var kg)) return false;
            if (kg < b.MinKg) return false;
            return b.Condition switch
            {
                "rain" => data.TryGetValue("vdw_caught_rain", out var r) && r == "1",
                "night" => data.TryGetValue("vdw_caught_night", out var n) && n == "1",
                "trophy" => item.m_quality >= FishSize.MaxClass,
                _ => true
            };
        }

        private static float WeightOf(ItemDrop.ItemData item) =>
            item.m_customData != null && item.m_customData.TryGetValue("vdw_weight_kg", out var raw)
            && float.TryParse(raw, NumberStyles.Float, CultureInfo.InvariantCulture, out var kg) ? kg : 0f;

        private static string BaitFor(FishDefinition fish) => fish.PreferredBaits.FirstOrDefault(id => ContentRegistry.Baits.ContainsKey(id)) ?? "worm";

        /// <summary>Why the best fish of the right kind you carry doesn't count ("" when none of that kind).</summary>
        private static string WhyNot(Player player, Bounty b)
        {
            string prefab = ContentRegistry.DropFor(b.Fish)?.gameObject.name ?? "";
            var mine = player.GetInventory().GetAllItems().Where(i => i.m_dropPrefab != null && i.m_dropPrefab.name == prefab).OrderByDescending(WeightOf).ToList();
            if (mine.Count == 0) return "";
            var best = mine[0];
            float kg = WeightOf(best);
            if (kg < b.MinKg) return $"Your biggest {b.Fish.Name} is {kg:0.##} kg - too light.";
            return b.Condition switch
            {
                "rain" => $"Your {b.Fish.Name} wasn't caught in the rain.",
                "night" => $"Your {b.Fish.Name} wasn't caught at night.",
                "trophy" => $"Your {b.Fish.Name} isn't Trophy-size.",
                _ => $"Your {b.Fish.Name} doesn't count."
            };
        }

        /// <summary>The panel's Hildir section: a tackle box to give back first, else today's bounty.</summary>
        private static PanelSection? Section(Player player, Trader trader)
        {
            if (TraderSales.KeyOf(trader) != "Hildir") return null;
            var inv = player.GetInventory();
            foreach (var b in Boxes)
            {
                var box = inv.GetAllItems().FirstOrDefault(i => i.m_dropPrefab != null && i.m_dropPrefab.name == BoxPrefab(b));
                if (box == null) continue;
                bool had = ZoneSystem.instance != null && ZoneSystem.instance.GetGlobalKey(b.Key);
                return new PanelSection
                {
                    Title = Localization.instance.Localize(box.m_shared.m_name),
                    Icon = box.GetIcon(),
                    Body = had ? "Another of my tackle boxes? I've had this one back already - keep it as a keepsake."
                               : $"That's my tackle box, lost in the {b.Where}! Give it back and I'll sell you the {b.Dye} gear and tackle that was in it.",
                    Button = had ? "" : "Give it back", CanPress = !had,
                    Press = () => trader.UseItem(player, box)
                };
            }

            int done = player.m_customData.TryGetValue(CountKey, out var c) && int.TryParse(c, out var n) ? n : 0;
            var next = Milestones.Where(m => m.count > done).Select(m => (int?)m.count).FirstOrDefault();
            string progress = $"Bounties done: <color=#ffcc55>{done}</color>"
                + (next != null ? $"  -  {next - done} more for {Milestones.First(m => m.count == next).name}" : "  -  you've won all her prizes");
            var bounty = Today(player);
            if (bounty == null)
                return new PanelSection { Title = "Hildir's bounty", Body = "Catch me something first - I only ask for fish you know.\n" + progress };

            var drop = ContentRegistry.DropFor(bounty.Fish);
            string baitId = BaitFor(bounty.Fish);
            string baitName = ContentRegistry.Baits.TryGetValue(baitId, out var bait) ? bait.Name : baitId;
            string cond = bounty.Condition switch { "rain" => "\nCaught in the rain", "night" => "\nCaught at night", "trophy" => "\nTrophy-size", _ => "" };
            var sec = new PanelSection
            {
                Title = $"Hildir's bounty - day {Day()}",
                Icon = drop != null ? drop.m_itemData.GetIcon() : null,
                Body = $"<b>{bounty.Fish.Name}</b>, at least <color=#ffcc55>{bounty.MinKg:0.##} kg</color><color=#9fd4ff>{cond}</color>\n"
                     + $"Reward: <color=#ffcc55>{bounty.Coins} coins</color> and 10 {baitName}\n{progress}"
            };
            if (player.m_customData.TryGetValue(DoneKey, out var d) && d == Day().ToString(CultureInfo.InvariantCulture))
            {
                sec.Body = $"<b>Done for today.</b> Come back tomorrow for a new one.\n{progress}";
                sec.Icon = null;
                return sec;
            }
            var fish = inv.GetAllItems().Where(i => Meets(i, bounty)).OrderBy(WeightOf).FirstOrDefault();   // the lightest that counts
            if (fish != null)
            {
                sec.Status = $"Your {WeightOf(fish):0.##} kg {bounty.Fish.Name} will do.";
                sec.StatusColor = TraderPanel.Good;
                sec.Button = "Hand it in"; sec.CanPress = true;
                sec.Press = () => TurnIn(player, trader, bounty, fish);
            }
            else
            {
                string why = WhyNot(player, bounty);
                sec.Status = why != "" ? why : $"You aren't carrying a {bounty.Fish.Name}.";
                sec.StatusColor = why != "" ? TraderPanel.Bad : TraderPanel.Plain;
            }
            return sec;
        }

        private static void TurnIn(Player player, Trader trader, Bounty b, ItemDrop.ItemData fish)
        {
            if (fish == null || !Meets(fish, b)) return;
            var inv = player.GetInventory();
            inv.RemoveItem(fish, 1);
            void Give(string prefab, int n)
            {
                var drop = ObjectDB.instance?.GetItemPrefab(prefab)?.GetComponent<ItemDrop>();
                if (drop == null) return;
                if (!inv.CanAddItem(drop.m_itemData, n)) { var d = UnityEngine.Object.Instantiate(drop.gameObject, player.transform.position + Vector3.up, Quaternion.identity); d.GetComponent<ItemDrop>().SetStack(n); }
                else inv.AddItem(prefab, n, 1, 0, 0L, "", false);
            }
            Give("Coins", b.Coins);
            Give("VDW_Bait_" + BaitFor(b.Fish), 10);
            int done = (player.m_customData.TryGetValue(CountKey, out var c) && int.TryParse(c, out var n) ? n : 0) + 1;
            player.m_customData[CountKey] = done.ToString(CultureInfo.InvariantCulture);
            player.m_customData[DoneKey] = Day().ToString(CultureInfo.InvariantCulture);
            string msg = $"Bounty done: {b.Coins} coins and bait.";
            foreach (var m in Milestones.Where(m => m.count == done)) { Rewards.Give(player, m.prefab, m.amount); msg += $"\nHildir gives you {m.name} for {done} bounties!"; }
            player.Message(MessageHud.MessageType.Center, msg);
            trader.OnSold();
        }
    }
}
