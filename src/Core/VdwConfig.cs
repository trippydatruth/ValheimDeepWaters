using BepInEx.Configuration;
using System.IO;
using UnityEngine;

namespace ValheimDeepWaters
{
    internal static class VdwConfig
    {
        public static ConfigEntry<bool> Enabled = null!;
        public static ConfigEntry<bool> ShowHud = null!;
        public static ConfigEntry<float> HudScale = null!;
        public static ConfigEntry<float> ReelVolume = null!;
        public static ConfigEntry<float> RodWear = null!;

        public static ConfigEntry<bool> SpawnSwimmingFish = null!;
        public static ConfigEntry<float> SwimmingFishDensity = null!;
        public static ConfigEntry<bool> SpawnWormMounds = null!;
        public static ConfigEntry<float> WormMoundDensity = null!;
        public static ConfigEntry<bool> RainWorms = null!;
        public static ConfigEntry<bool> SpawnFlies = null!;

        public static ConfigEntry<KeyboardShortcut> CycleBaitKey = null!;
        public static ConfigEntry<KeyboardShortcut> CycleHookKey = null!;
        public static ConfigEntry<KeyboardShortcut> LogKey = null!;
        public static ConfigEntry<KeyboardShortcut> RodKey = null!;
        public static ConfigEntry<KeyboardShortcut> TackleBoxKey = null!;
        public static ConfigEntry<KeyboardShortcut> TackleBoxSetDownKey = null!;
        public static ConfigEntry<string> TacklePanelPosition = null!;
        public static ConfigEntry<StepControl> DragControl = null!;
        public static ConfigEntry<StepControl> ReelSpeedControl = null!;

        public static string FishFile => Path.Combine(Plugin.ConfigDirectory, "Fish.json");
        public static string BaitFile => Path.Combine(Plugin.ConfigDirectory, "Baits.json");
        public static string RodsFile => Path.Combine(Plugin.ConfigDirectory, "Rods.json");
        public static string HooksFile => Path.Combine(Plugin.ConfigDirectory, "Hooks.json");
        public static string TackleFile => Path.Combine(Plugin.ConfigDirectory, "Tackle.json");
        public static string BuffsFile => Path.Combine(Plugin.ConfigDirectory, "Buffs.json");

        /// <summary>
        /// A gameplay setting: on a server, the server's value is used for everyone (synced by Jotunn when they join)
        /// so players can't give themselves different rules.
        /// </summary>
        private static ConfigEntry<T> Server<T>(ConfigFile cfg, string section, string key, T value, string description) =>
            cfg.Bind(section, key, value, new ConfigDescription(description + " (Set by the server in multiplayer.)", null,
                new ConfigurationManagerAttributes { IsAdminOnly = true }));

        public static void Load(ConfigFile cfg)
        {
            Enabled = Server(cfg, "1 General", "Enabled", true, "Master toggle for the mod.");
            ShowHud = cfg.Bind("1 General", "Show Fishing HUD", true, "Show the bait, tension, line and drag HUD.");
            HudScale = cfg.Bind("1 General", "HUD Scale", 0.85f, "Size of the fishing HUD and catch log. 1 = same scale as Valheim's own UI.");
            ReelVolume = cfg.Bind("1 General", "Reel Sound Volume", 0.5f, "Volume of the reel clicking while you reel (0-1).");
            RodWear = Server(cfg, "1 General", "Rod Wear", 1f, "How fast rods lose durability while fighting a fish. 0 = rods never wear.");

            SpawnSwimmingFish = Server(cfg, "2 World", "Spawn Swimming Fish", true, "Deep Waters fish swim in lakes, rivers and the sea in their own biomes. Species seen near your float are likelier to bite.");
            SwimmingFishDensity = Server(cfg, "2 World", "Swimming Fish Density", 1f, "Multiplies how often Deep Waters fish spawn in the world.");
            SpawnWormMounds = Server(cfg, "2 World", "Spawn Worm Mounds", true, "Wriggling soil you can dig up for worms, growing where red mushrooms do. Only appears in newly generated areas.");
            WormMoundDensity = Server(cfg, "2 World", "Worm Mound Density", 0.5f, "How many worm mounds grow compared to red mushrooms (1 = as many, 0.5 = half as many). Newly generated areas only.");
            RainWorms = Server(cfg, "2 World", "Rain Worms", true, "When it rains, worms come up out of the ground around you to pick up.");
            SpawnFlies = Server(cfg, "2 World", "Spawn Flies", true, "Flies buzz along shorelines in dry weather (fireflies at night); walk up and use them to catch fly bait.");

            CycleBaitKey = cfg.Bind("3 Controls", "Cycle Bait Key", new KeyboardShortcut(KeyCode.B), "Swaps in the next bait you're carrying.");
            CycleHookKey = cfg.Bind("3 Controls", "Cycle Hook Key", new KeyboardShortcut(KeyCode.H), "Swaps in the next hook you're carrying.");
            LogKey = cfg.Bind("3 Controls", "Catch Log Key", new KeyboardShortcut(KeyCode.J), "Opens the catch log.");
            RodKey = cfg.Bind("3 Controls", "Rod Key", new KeyboardShortcut(KeyCode.F, KeyCode.LeftAlt), "Takes the rod in your tackle's rod slot in hand, or puts it away.");
            TackleBoxKey = cfg.Bind("3 Controls", "Tackle Box Key", new KeyboardShortcut(KeyCode.K), "Opens (or closes) the tackle box you're wearing.");
            TackleBoxSetDownKey = cfg.Bind("3 Controls", "Tackle Box Set Down Key", new KeyboardShortcut(KeyCode.K, KeyCode.LeftShift), "Sets the tackle box you're wearing down as a chest (Shift+E on it picks it up again).");
            TacklePanelPosition = cfg.Bind("4 Interface", "Tackle Panel Position", "", "Where the tackle panel sits in the inventory screen, set by dragging it. Empty: under the inventory. Double-clicking the panel also resets it.");
            DragControl = cfg.Bind("3 Controls", "Drag Control", StepControl.MouseWheel, "What sets the drag while the rod is out: the mouse wheel, Alt + mouse wheel, or the mouse side buttons (Mouse 5 up, Mouse 4 down). If drag and reel speed use the same control, drag gets it.");
            ReelSpeedControl = cfg.Bind("3 Controls", "Reel Speed Control", StepControl.AltMouseWheel, "What sets the reel speed while the rod is out: the mouse wheel, Alt + mouse wheel, or the mouse side buttons (Mouse 5 up, Mouse 4 down). Shift always reels at full speed.");
        }
    }
}

namespace ValheimDeepWaters
{
    /// <summary>A control that steps a setting (drag, reel speed) up and down.</summary>
    public enum StepControl
    {
        MouseWheel,      // wheel up = more
        AltMouseWheel,   // Alt held + wheel
        MouseSideButtons // Mouse 5 (forward) = more, Mouse 4 (back) = less
    }
}
