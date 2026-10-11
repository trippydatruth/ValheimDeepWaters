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
                    Console.instance.Print("Unknown fish/bait/rod.");
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
            public override string Help => "Deep Waters debug tools. Usage: vdw_debug [bite|boss|worms|horn|boatseat|pearlfit|runefit|runeskin|hold|lefthand|righthand|idlehand|idleshift|listrods|listhooks|listbuffs|listfish|listbait|resetlog|tokens]";

            public override void Run(string[] args)
            {
                if (args.Length < 1) return;

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
                else if (args[0].Equals("boatseat", StringComparison.OrdinalIgnoreCase))
                {
                    // vdw_debug boatseat <rower|passenger|holdfast> <right> <up> <forward> [turn]
                    float F(int i) => args.Length > i && float.TryParse(args[i], System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var v) ? v : 0f;
                    string? done = args.Length >= 2 ? FishingBoat.NudgeSeat(args[1], new UnityEngine.Vector3(F(2), F(3), F(4)), F(5)) : null;
                    Console.instance.Print(done ?? "Usage: vdw_debug boatseat <rower|passenger|holdfast> <right> <up> <forward> [turn degrees]   e.g. vdw_debug boatseat rower 0 0.05 -0.1");
                }
                else if (args[0].Equals("pearlfit", StringComparison.OrdinalIgnoreCase))
                {
                    // vdw_debug pearlfit <scale> <up> <forward> [height] [depth]
                    float F(int i, float d) => args.Length > i && float.TryParse(args[i], System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var v) ? v : d;
                    Console.instance.Print(args.Length < 2
                        ? "Usage: vdw_debug pearlfit <scale> <up> <forward> [height] [depth]   (now: 1 0.29 0.01 1.1 1.1)"
                        : RelicVisuals.PearlFit(F(1, 1f), F(2, 0.29f), F(3, 0.01f), F(4, 1.1f), F(5, 1.1f)));
                }
                else if (args[0].Equals("runefit", StringComparison.OrdinalIgnoreCase))
                {
                    // vdw_debug runefit <scale> <up> <forward> [width] [depth]
                    float F(int i, float d) => args.Length > i && float.TryParse(args[i], System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var v) ? v : d;
                    Console.instance.Print(args.Length < 2
                        ? "Usage: vdw_debug runefit <scale> <up> <forward> [width] [depth]   (default: 1.2 0.09 0.06 1 1.15; up/forward from the base of the neck)"
                        : RelicVisuals.RuneFit(F(1, 1.2f), F(2, 0.09f), F(3, 0.06f), F(4, 1f), F(5, 1.15f)));
                }
                else if (args[0].Equals("hold", StringComparison.OrdinalIgnoreCase))
                {
                    // vdw_debug hold <forward> <down> <right>
                    var now = AnglerPose.Hold;
                    float F(int i, float d) => args.Length > i && float.TryParse(args[i], System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var v) ? v : d;
                    var set = AnglerPose.Hold = new UnityEngine.Vector3(F(1, now.x), F(2, now.y), F(3, now.z));
                    string msg = $"Rod hold: reel {set.x:0.00} forward, {set.y:0.00} down, {set.z:0.00} right of the shoulders.";
                    Plugin.Log.LogInfo(msg);
                    Console.instance.Print(msg);
                }
                else if (args[0].Equals("lefthand", StringComparison.OrdinalIgnoreCase))
                {
                    // vdw_debug lefthand <along> [up] [right] [roll] [forward]: the left hand's grip up (+) or down (-) the rod from the
                    // reel, nudged up, right and forward (metres), and rolled round the rod (degrees); values left out stay
                    float G(int i, float d) => args.Length > i && float.TryParse(args[i], System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var v) ? v : d;
                    AnglerPose.LeftAlong = G(1, AnglerPose.LeftAlong);
                    AnglerPose.LeftUp = G(2, AnglerPose.LeftUp);
                    AnglerPose.LeftRight = G(3, AnglerPose.LeftRight);
                    AnglerPose.LeftRoll = G(4, AnglerPose.LeftRoll);
                    AnglerPose.LeftForward = G(5, AnglerPose.LeftForward);
                    string msg = $"Left hand: {AnglerPose.LeftAlong:0.00} m up the rod from the reel, {AnglerPose.LeftUp:0.00} up, {AnglerPose.LeftRight:0.00} right, {AnglerPose.LeftForward:0.00} forward, rolled {AnglerPose.LeftRoll:0} degrees.";
                    Plugin.Log.LogInfo(msg);
                    Console.instance.Print(msg);
                }
                else if (args[0].Equals("runeskin", StringComparison.OrdinalIgnoreCase))
                {
                    // vdw_debug runeskin <0-1>: how fully the worn necklace follows the body
                    float v = args.Length > 1 && float.TryParse(args[1], System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var x) ? x : 0.5f;
                    Console.instance.Print(RelicVisuals.RuneSkin(v));
                }
                else if (args[0].Equals("idleshift", StringComparison.OrdinalIgnoreCase))
                {
                    // vdw_debug idleshift <right> <forward> [up]: moves the whole no-line-out hold (both hands and the rod), metres
                    float F(int i, float d) => args.Length > i && float.TryParse(args[i], System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var v) ? v : d;
                    var sh = AnglerPose.IdleShift;
                    AnglerPose.IdleShift = new UnityEngine.Vector3(F(1, sh.x), F(3, sh.y), F(2, sh.z));
                    string msg = $"Idle hold: moved {AnglerPose.IdleShift.x:0.00} right, {AnglerPose.IdleShift.z:0.00} forward, {AnglerPose.IdleShift.y:0.00} up of Valheim's.";
                    Plugin.Log.LogInfo(msg);
                    Console.instance.Print(msg);
                }
                else if (args[0].Equals("idlehand", StringComparison.OrdinalIgnoreCase))
                {
                    // vdw_debug idlehand <along>: how far up the rod from the reel the left hand holds it with no line out
                    if (args.Length > 1 && float.TryParse(args[1], System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var v)) AnglerPose.IdleLeftAlong = v;
                    string msg = $"Idle left hand: {AnglerPose.IdleLeftAlong:0.00} m up the rod from the reel (less if the arm can't reach).";
                    Plugin.Log.LogInfo(msg);
                    Console.instance.Print(msg);
                }
                else if (args[0].Equals("righthand", StringComparison.OrdinalIgnoreCase))
                {
                    // vdw_debug righthand <along> [up] [right] [roll] [forward]: the right hand on the reel handle, nudged and rolled
                    // (along only counts on a rod without a reel: negative is down the butt)
                    float G(int i, float d) => args.Length > i && float.TryParse(args[i], System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var v) ? v : d;
                    AnglerPose.RightAlong = G(1, AnglerPose.RightAlong);
                    AnglerPose.RightUp = G(2, AnglerPose.RightUp);
                    AnglerPose.RightRight = G(3, AnglerPose.RightRight);
                    AnglerPose.RightRoll = G(4, AnglerPose.RightRoll);
                    AnglerPose.RightForward = G(5, AnglerPose.RightForward);
                    string msg = $"Right hand: {AnglerPose.RightAlong:0.00} m along the rod, {AnglerPose.RightUp:0.00} up, {AnglerPose.RightRight:0.00} right, {AnglerPose.RightForward:0.00} forward, rolled {AnglerPose.RightRoll:0} degrees.";
                    Plugin.Log.LogInfo(msg);
                    Console.instance.Print(msg);
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
                    Console.instance.Print($"Wrote {Loc.English.Count} tokens to {path}. Translate the values and save as BepInEx/plugins/ValheimDeepWaters/Translations/<Language>/vdw.json.");
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
