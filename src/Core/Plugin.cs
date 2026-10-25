using BepInEx;
using BepInEx.Logging;
using HarmonyLib;
using Jotunn.Managers;
using Jotunn.Utils;
using System;
using System.IO;

namespace ValheimDeepWaters
{
    [BepInPlugin(Guid, Name, Version)]
    [BepInDependency(Jotunn.Main.ModGuid, "2.30.0")]
    // Everyone on a server needs the same version (items, fish and spawns must match), and the server's gameplay
    // settings are pushed to every player.
    [NetworkCompatibility(CompatibilityLevel.EveryoneMustHaveMod, VersionStrictness.Minor)]
    public sealed class Plugin : BaseUnityPlugin
    {
        public const string Guid = "valheimdeepwaters";   // also the config file's name: BepInEx/config/valheimdeepwaters.cfg
        public const string Name = "Valheim: Deep Waters";
        public const string Version = "1.0.1";

        internal static ManualLogSource Log = null!;
        internal static string ConfigDirectory = null!;

        private Harmony? _harmony;

        private void Awake()
        {
            Log = Logger;
            ConfigDirectory = Path.Combine(BepInEx.Paths.ConfigPath, "ValheimDeepWaters");
            Directory.CreateDirectory(ConfigDirectory);
            CustomModels.EnsureFolder();

            bool moved = MoveOldConfig();
            VdwConfig.Load(Config);
            if (moved) DropRemovedSettings();

            // Items can only be cloned once vanilla prefabs are loaded.
            PrefabManager.OnVanillaPrefabsAvailable += RegisterContent;

            // Patch each class on its own so one bad patch can never abort Awake().
            _harmony = new Harmony(Guid);
            foreach (var type in typeof(Plugin).Assembly.GetTypes())
            {
                if (type.GetCustomAttributes(typeof(HarmonyPatch), true).Length == 0) continue;
                try { _harmony.CreateClassProcessor(type).Patch(); }
                catch (Exception ex) { Log.LogError($"Failed to apply patch {type.Name}: {ex.Message}"); }
            }

            try { CommandRegistry.Initialize(); }
            catch (Exception ex) { Log.LogError($"Failed to register console commands: {ex.Message}"); }

            Log.LogInfo($"{Name} {Version} loaded.");
        }

        /// <summary>Before 0.14 the config was trippy.valheimdeepwaters.cfg: carry its settings over once.</summary>
        private bool MoveOldConfig()
        {
            try
            {
                string old = Path.Combine(BepInEx.Paths.ConfigPath, "trippy.valheimdeepwaters.cfg");
                if (!File.Exists(old) || File.Exists(Config.ConfigFilePath)) return false;
                File.Move(old, Config.ConfigFilePath);
                Config.Reload();
                Log.LogInfo("Settings moved from trippy.valheimdeepwaters.cfg to valheimdeepwaters.cfg.");
                return true;
            }
            catch (Exception ex) { Log.LogWarning($"Could not move the old config file: {ex.Message}"); return false; }
        }

        /// <summary>Clears settings from older versions that no longer exist, so the moved file only lists current ones.</summary>
        private void DropRemovedSettings()
        {
            if (AccessTools.Property(typeof(BepInEx.Configuration.ConfigFile), "OrphanedEntries")?.GetValue(Config) is System.Collections.IDictionary orphans && orphans.Count > 0)
            {
                orphans.Clear();
                Config.Save();
            }
        }

        private void LateUpdate()
        {
            try { FishingController.LateUpdateVisuals(); FlySwarm.Update(); RainWorms.Update(); TackleBoxes.UpdateLocal(); }
            catch (Exception ex) { FishingController.ReportError(ex); }
        }

        private void OnGUI()
        {
            try { FishingController.ProcessScrollEvent(); FishingHud.Draw(); }
            catch (Exception ex) { FishingController.ReportError(ex); }
        }

        private void RegisterContent()
        {
            PrefabManager.OnVanillaPrefabsAvailable -= RegisterContent;
            try { ContentRegistry.Initialize(); }
            catch (Exception ex) { Log.LogError($"Failed to initialize content registry: {ex}"); }
        }

        private void OnDestroy()
        {
            PrefabManager.OnVanillaPrefabsAvailable -= RegisterContent;
            FishingController.Shutdown();
            _harmony?.UnpatchSelf();
        }
    }
}
