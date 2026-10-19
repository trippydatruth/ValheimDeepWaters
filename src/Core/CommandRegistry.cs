using Jotunn.Entities;
using Jotunn.Managers;
using System;
using System.Linq;

namespace ValheimDeepWaters
{
    internal static class CommandRegistry
    {
        public static void Initialize()
        {
            CommandManager.Instance.AddConsoleCommand(new VdwGiveCommand());
            CommandManager.Instance.AddConsoleCommand(new VdwDebugCommand());
        }

        private class VdwGiveCommand : ConsoleCommand
        {
            public override string Name => "vdw_give";
            public override bool IsCheat => true; // needs devcommands, like vanilla's spawn
            public override string Help => "Give Deep Waters fishing content. Usage: vdw_give [rod|rod_<id>|hook_<id>|buff_<id>|bait_id|fish_id] [amount]  (ids come from vdw_debug listrods / listhooks / listbuffs / listbait / listfish)";

            public override void Run(string[] args)
            {
                if (args.Length < 1)
                {
                    Console.instance.Print("Usage: vdw_give rod 1 | vdw_give worm 20 | vdw_give trout 1");
                    return;
                }

                var player = Player.m_localPlayer;
                if (player == null) return;

                string what = args[0];
                int amount = 1;
                if (args.Length >= 2) int.TryParse(args[1], out amount);
                amount = Math.Max(1, amount);

                string prefabName;
                RodDefinition? rod = null;
                if (what.Equals("rod", StringComparison.OrdinalIgnoreCase))
                    rod = ContentRegistry.Rods.FirstOrDefault();
                else if (what.StartsWith("rod_", StringComparison.OrdinalIgnoreCase))
                    rod = ContentRegistry.Rods.FirstOrDefault(r => r.Id.Equals(what.Substring(4), StringComparison.OrdinalIgnoreCase));

                if (rod != null)
                    prefabName = ContentRegistry.RodPrefabName(rod);
                else if (what.StartsWith("hook_", StringComparison.OrdinalIgnoreCase) && ContentRegistry.Hooks.ContainsKey(what.Substring(5)))
                    prefabName = "VDW_Hook_" + what.Substring(5);
                else if (what.StartsWith("buff_", StringComparison.OrdinalIgnoreCase) && FishingBuffs.Buffs.ContainsKey(what.Substring(5)))
                    prefabName = "VDW_Buff_" + what.Substring(5);
                else if (ContentRegistry.Baits.ContainsKey(what))
                    prefabName = "VDW_Bait_" + what;
                else if (ContentRegistry.Fish.ContainsKey(what))
                    prefabName = "VDW_Fish_" + what;
                else
                {
                    Console.instance.Print("Unknown item. See vdw_debug listfish / listbait / listrods / listhooks / listbuffs.");
                    return;
                }

                var prefab = ZNetScene.instance.GetPrefab(prefabName);
                var drop = prefab?.GetComponent<ItemDrop>();
                if (drop == null)
                {
                    Console.instance.Print("Prefab is not available yet: " + prefabName);
                    return;
                }

                // Inventory.AddItem(string, ...) looks the item up by PREFAB name, not the display name.
                player.GetInventory().AddItem(prefabName, amount, 1, 0, 0L, "", false);
                Console.instance.Print($"Added {prefabName} x{amount}");
            }
        }

        private class VdwDebugCommand : ConsoleCommand
        {
            public override string Name => "vdw_debug";
            public override bool IsCheat => true;
            public override string Help => "Deep Waters testing tools. Usage: vdw_debug [bite | boss <fish> | worms | horn | resetlog | rank <points> | resetrank | tokens | listrods | listhooks | listbuffs | listfish | listbait]";

            public override void Run(string[] args)
            {
                if (args.Length < 1) { Console.instance.Print(Help); return; }

                if (args[0].Equals("bite", StringComparison.OrdinalIgnoreCase))
                {
                    FishingController.DebugQuickBite = true;
                    Console.instance.Print("Next cast: a fish starts right by the bait and bites with no nibbles.");
                }
                else if (args[0].Equals("boss", StringComparison.OrdinalIgnoreCase))
                {
                    // Skips the lure and the conditions, to try a boss fight anywhere.
                    var ids = string.Join(", ", BossFish.All.Select(b => b.FishId));
                    if (args.Length < 2 || BossFish.ForFish(args[1]) == null)
                    {
                        Console.instance.Print($"Usage: vdw_debug boss <fish id>   ({ids})");
                        return;
                    }
                    FishingController.DebugBoss = args[1];
                    Console.instance.Print($"Next cast summons {args[1]}, wherever you are and whatever the bait.");
                }
                else if (args[0].Equals("worms", StringComparison.OrdinalIgnoreCase))
                {
                    Console.instance.Print(BaitSources.DescribeNearby());
                }
                else if (args[0].Equals("horn", StringComparison.OrdinalIgnoreCase))
                {
                    int n = Player.m_localPlayer != null ? HornOfAegir.ResetRest(Player.m_localPlayer) : 0;
                    Console.instance.Print(n > 0 ? "The Horn of Ægir is rested and can be blown again." : "No resting Horn of Ægir in your inventory.");
                }
                else if (args[0].Equals("resetlog", StringComparison.OrdinalIgnoreCase))
                {
                    if (Player.m_localPlayer != null) Player.m_localPlayer.m_customData.Remove("vdw_catchlog");
                    Console.instance.Print("Catch log cleared.");
                }
                else if (args[0].Equals("rank", StringComparison.OrdinalIgnoreCase))
                {
                    var p = Player.m_localPlayer;
                    if (p == null) return;
                    int add = args.Length > 1 && int.TryParse(args[1], out var n) ? n : 100;
                    string msg = AnglerRanks.DebugAdd(p, add);
                    Console.instance.Print($"Rank points: {AnglerRanks.Points(p)} ({AnglerRanks.Ranks[AnglerRanks.RankIndex(p)].Name}).{msg.Replace("\n", " ")}");
                }
                else if (args[0].Equals("resetrank", StringComparison.OrdinalIgnoreCase))
                {
                    if (Player.m_localPlayer != null) AnglerRanks.Reset(Player.m_localPlayer);
                    Console.instance.Print("Rank trophies and weight landed cleared (species and catches still count; resetlog clears those).");
                }
                else if (args[0].Equals("listbait", StringComparison.OrdinalIgnoreCase))
                {
                    Console.instance.Print(string.Join(", ", ContentRegistry.Baits.Keys.OrderBy(x => x)));
                }
                else if (args[0].Equals("listfish", StringComparison.OrdinalIgnoreCase))
                {
                    Console.instance.Print(string.Join(", ", ContentRegistry.Fish.Keys.OrderBy(x => x)));
                }
                else if (args[0].Equals("listrods", StringComparison.OrdinalIgnoreCase))
                {
                    Console.instance.Print(string.Join(", ", ContentRegistry.Rods.Select(r => "rod_" + r.Id)));
                }
                else if (args[0].Equals("tokens", StringComparison.OrdinalIgnoreCase))
                {
                    // A ready-to-translate copy of every Deep Waters text token and its English.
                    string path = System.IO.Path.Combine(Plugin.ConfigDirectory, "translation_template_English.json");
                    var lines = Loc.English.Select(kv => "  \"" + kv.Key + "\": \"" + kv.Value.Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\n", "\\n") + "\"");
                    System.IO.File.WriteAllText(path, "{\n" + string.Join(",\n", lines) + "\n}\n");
                    Console.instance.Print($"Wrote {Loc.English.Count} tokens to {path}. Translate the values and save as Translations/<Language>/vdw.json inside the mod's folder in BepInEx/plugins.");
                }
                else if (args[0].Equals("listbuffs", StringComparison.OrdinalIgnoreCase))
                {
                    Console.instance.Print(string.Join(", ", FishingBuffs.Buffs.Values.OrderBy(b => b.Tier).Select(b => $"buff_{b.Id} ({b.Kind} T{b.Tier})")));
                }
                else if (args[0].Equals("listhooks", StringComparison.OrdinalIgnoreCase))
                {
                    Console.instance.Print(string.Join(", ", ContentRegistry.Hooks.Values.Select(h => $"hook_{h.Id} ({h.MinKg:0.#}-{h.MaxKg:0.#} kg)")));
                }
            }
        }
    }
}
