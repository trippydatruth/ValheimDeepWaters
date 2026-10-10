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
        public const string Guid = "trippy.valheimdeepwaters";
        public const string Name = "Valheim: Deep Waters";
        public const string Version = "0.14.0";

        internal static ManualLogSource Log = null!;
        internal static string ConfigDirectory = null!;

        private Harmony? _harmony;

        private void Awake()
        {
            Log = Logger;
            ConfigDirectory = Path.Combine(BepInEx.Paths.ConfigPath, "ValheimDeepWaters");
            Directory.CreateDirectory(ConfigDirectory);
            CustomModels.EnsureFolder();

            VdwConfig.Load(Config);

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

        private void LateUpdate()
        {
            try { FishingController.LateUpdateVisuals(); FlySwarm.Update(); RainWorms.Update(); }
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
