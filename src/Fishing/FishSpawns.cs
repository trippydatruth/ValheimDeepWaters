using HarmonyLib;
using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// Puts Deep Waters' fish into Valheim's own world spawning so they swim in lakes, rivers and the sea like
    /// vanilla fish (and are networked the same way). Each fish's spawn rules are copied from a vanilla fish's
    /// (freshwater or ocean) so depth and behaviour match, then given its own biomes, numbers and time of day.
    /// Baitfish swim in schools too (their own swimming creature, see ContentRegistry.RegisterSwimmingBaitfish).
    /// </summary>
    internal static class FishSpawns
    {
        private static SpawnSystemList? _list;
        private static bool _built;

        private const Heightmap.Biome FreshwaterBiomes = Heightmap.Biome.Meadows | Heightmap.Biome.BlackForest | Heightmap.Biome.Swamp |
                                                         Heightmap.Biome.Mountain | Heightmap.Biome.Plains | Heightmap.Biome.Mistlands;

        [HarmonyPatch(typeof(SpawnSystem), "Awake")]
        private static class SpawnSystemAwakePatch
        {
            private static void Postfix(SpawnSystem __instance)
            {
                try
                {
                    if (!_vanillaBiomesRead) ReadVanillaBiomes(__instance);
                    if (!VdwConfig.Enabled.Value || !VdwConfig.SpawnSwimmingFish.Value) return;
                    if (!_built) Build(__instance);
                    if (_list != null && !__instance.m_spawnLists.Contains(_list)) __instance.m_spawnLists.Add(_list);
                }
                catch (Exception ex)
                {
                    _built = true;
                    Plugin.Log.LogError($"Fish spawns: failed ({ex.Message}); fish won't swim in the world.");
                }
            }
        }

        private static void Build(SpawnSystem sys)
        {
            _built = true;

            // Vanilla fish entries to copy from: one freshwater, one ocean.
            SpawnSystem.SpawnData? fresh = null, ocean = null;
            foreach (var data in sys.m_spawnLists.Where(l => l != null).SelectMany(l => l.m_spawners))
            {
                if (data?.m_prefab == null || data.m_prefab.GetComponent<global::Fish>() == null) continue;
                bool isOcean = (data.m_biome & Heightmap.Biome.Ocean) != 0;
                if (isOcean && ocean == null) ocean = data;
                if (!isOcean && fresh == null) fresh = data;
            }
            if (fresh == null && ocean == null)
            {
                Plugin.Log.LogWarning("Fish spawns: no vanilla fish spawns found to copy; Deep Waters fish won't swim in the world.");
                return;
            }

            var go = new GameObject("VDW_FishSpawns");
            UnityEngine.Object.DontDestroyOnLoad(go);
            _list = go.AddComponent<SpawnSystemList>();

            float density = Mathf.Max(0f, VdwConfig.SwimmingFishDensity.Value);
            foreach (var fish in ContentRegistry.Fish.Values)
            {
                if (fish.IsVanilla) continue; // vanilla fish keep vanilla's spawns
                if (BossFish.IsBoss(fish.Id)) continue; // a boss fish only ever comes when its lure summons it
                bool baitfish = !string.IsNullOrWhiteSpace(fish.CatchBait);
                GameObject? prefab = null;
                if (baitfish) ContentRegistry.SwimmingBaitfish.TryGetValue(fish.Id, out prefab);
                else ContentRegistry.FishItems.TryGetValue(fish.Id, out prefab);
                if (prefab == null || prefab.GetComponent<global::Fish>() == null) continue;

                bool sea = fish.Water == WaterType.Ocean || fish.Water == WaterType.DeepOcean;
                var template = sea ? ocean ?? fresh! : fresh ?? ocean!;
                var data = template.Clone();
                data.m_name = "VDW_" + fish.Id;
                data.m_prefab = prefab;
                data.m_enabled = true;
                data.m_biome = sea ? Heightmap.Biome.Ocean : ParseBiomes(fish.Biomes);
                // Common fish come in small schools; rare and legendary ones alone and seldom.
                data.m_maxSpawned = fish.Legendary ? 1 : Mathf.Clamp(Mathf.RoundToInt(1f + fish.BiteWeight / 2f), 1, 4);
                data.m_groupSizeMax = fish.Legendary ? 1 : Mathf.Max(1, data.m_maxSpawned - 1);
                data.m_spawnChance = template.m_spawnChance * Mathf.Clamp(fish.BiteWeight / 4f, 0.02f, 1f) * density;
                if (baitfish)
                {
                    // small fish in bigger, more frequent schools
                    data.m_maxSpawned = 6;
                    data.m_groupSizeMin = 3;
                    data.m_groupSizeMax = 5;
                    data.m_spawnChance = template.m_spawnChance * density;
                }
                data.m_spawnAtDay = !string.Equals(fish.ActiveTime, "Night", StringComparison.OrdinalIgnoreCase);
                data.m_spawnAtNight = !string.Equals(fish.ActiveTime, "Day", StringComparison.OrdinalIgnoreCase);
                if (fish.Water == WaterType.DeepOcean) data.m_minOceanDepth = Mathf.Max(data.m_minOceanDepth, 15f);
                data.m_minLevel = data.m_maxLevel = 1;
                _list.m_spawners.Add(data);
            }
        }

        private static bool _vanillaBiomesRead;

        /// <summary>
        /// Vanilla fish bite where vanilla spawns them: their biomes are read from the game's own spawn lists, replacing
        /// the Biomes in Fish.json (which only stand in if the game's lists don't have the fish).
        /// </summary>
        private static void ReadVanillaBiomes(SpawnSystem sys)
        {
            _vanillaBiomesRead = true;
            var found = new Dictionary<string, Heightmap.Biome>();
            foreach (var data in sys.m_spawnLists.Where(l => l != null).SelectMany(l => l.m_spawners))
            {
                if (data?.m_prefab == null || !ContentRegistry.FishIdByPrefab.TryGetValue(data.m_prefab.name, out var id)) continue;
                found[id] = (found.TryGetValue(id, out var b) ? b : Heightmap.Biome.None) | data.m_biome;
            }

            foreach (var fish in ContentRegistry.Fish.Values)
            {
                if (!fish.IsVanilla || !found.TryGetValue(fish.Id, out var biomes)) continue;
                fish.Biomes.Clear();
                foreach (Heightmap.Biome b in Enum.GetValues(typeof(Heightmap.Biome)))
                    if (b != Heightmap.Biome.None && (biomes & b) == b && Mathf.IsPowerOfTwo((int)b)) fish.Biomes.Add(b.ToString());
            }
        }

        private static Heightmap.Biome ParseBiomes(List<string>? names)
        {
            var biome = Heightmap.Biome.None;
            if (names != null)
                foreach (var n in names)
                    if (Enum.TryParse<Heightmap.Biome>(n, true, out var b)) biome |= b;
            return biome == Heightmap.Biome.None ? FreshwaterBiomes : biome;
        }
    }
}
