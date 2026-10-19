using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text;
using UnityEngine;

namespace ValheimDeepWaters
{
    internal sealed class CatchEntry
    {
        public int Count;
        public float BestKg;
    }

    /// <summary>
    /// Per-character catch records, stored in Player.m_customData so they are saved with the character.
    /// Format: "id:count:bestKg;id:count:bestKg"
    /// </summary>
    internal static class CatchLog
    {
        private const string Key = "vdw_catchlog";

        public static Dictionary<string, CatchEntry> Load(Player player)
        {
            var result = new Dictionary<string, CatchEntry>();
            if (player == null || player.m_customData == null) return result;
            if (!player.m_customData.TryGetValue(Key, out var raw) || string.IsNullOrEmpty(raw)) return result;
            // The HUD reads the log every frame while it's open; only re-parse when it changed.
            if (ReferenceEquals(raw, _lastRaw) && _lastParsed != null) return new Dictionary<string, CatchEntry>(_lastParsed);

            foreach (var part in raw.Split(new[] { ';' }, StringSplitOptions.RemoveEmptyEntries))
            {
                var f = part.Split(':');
                if (f.Length != 3) continue;
                if (!int.TryParse(f[1], NumberStyles.Integer, CultureInfo.InvariantCulture, out var count)) continue;
                if (!float.TryParse(f[2], NumberStyles.Float, CultureInfo.InvariantCulture, out var best)) continue;
                result[f[0]] = new CatchEntry { Count = count, BestKg = best };
            }
            _lastRaw = raw;
            _lastParsed = new Dictionary<string, CatchEntry>(result);
            return result;
        }

        private static string? _lastRaw;
        private static Dictionary<string, CatchEntry>? _lastParsed;

        private static void Save(Player player, Dictionary<string, CatchEntry> data)
        {
            var sb = new StringBuilder();
            foreach (var kv in data)
            {
                if (sb.Length > 0) sb.Append(';');
                sb.Append(kv.Key).Append(':')
                  .Append(kv.Value.Count.ToString(CultureInfo.InvariantCulture)).Append(':')
                  .Append(kv.Value.BestKg.ToString("0.00", CultureInfo.InvariantCulture));
            }
            player.m_customData[Key] = sb.ToString();
        }

        // ------------------------------------------------------------------ rewards

        private const string RewardsKey = "vdw_rewards";
        private const int AllSpecies = -1;

        private sealed class Milestone
        {
            public int Species;           // species logged; AllSpecies = every fish in Fish.json
            public string Label = "";
            public (string prefab, int amount)[] Items = Array.Empty<(string, int)>();
        }

        private static readonly Milestone[] Milestones =
        {
            // every five species, small and useful for the next few (roadmap #27); never boss lures - those you work for
            new Milestone { Species = 5,  Label = "3 Small Hooks",                       Items = new[] { ("VDW_Hook_small", 3) } },
            new Milestone { Species = 10, Label = "2 Angler's Meads",                    Items = new[] { ("VDW_Buff_angler_medium", 2) } },
            new Milestone { Species = 15, Label = "2 Chum Buckets and a Lantern Float",  Items = new[] { ("VDW_Buff_chum_basic", 2), ("VDW_Buff_lantern_float", 1) } },
            new Milestone { Species = 20, Label = "3 Large Hooks and 10 Shrimp Bait",    Items = new[] { ("VDW_Hook_large", 3), ("VDW_Bait_shrimp", 10) } },
            new Milestone { Species = 25, Label = "2 Steady-Hand Tonics",                Items = new[] { ("VDW_Buff_steady_medium", 2) } },
            new Milestone { Species = 30, Label = "a Trophy Fin and 500 coins",          Items = new[] { ("VDW_Mat_trophy", 1), ("Coins", 500) } },
            new Milestone { Species = 35, Label = "1,000 coins",                         Items = new[] { ("Coins", 1000) } },
            new Milestone { Species = AllSpecies, Label = "the Pearl of Njord",          Items = new[] { ("VDW_Buff_relic_pearl", 1) } },
        };

        private static int Needed(Milestone m) => m.Species == AllSpecies ? ContentRegistry.Fish.Count : m.Species;

        private static HashSet<string> Claimed(Player player) =>
            player.m_customData.TryGetValue(RewardsKey, out var raw) && !string.IsNullOrEmpty(raw)
                ? new HashSet<string>(raw.Split(','))
                : new HashSet<string>();

        /// <summary>Hands out any catch-log milestones newly reached. Returns what was given, for the catch message.</summary>
        public static List<string> ClaimRewards(Player player)
        {
            var given = new List<string>();
            int logged = Load(player).Count;
            var claimed = Claimed(player);

            foreach (var m in Milestones)
            {
                string key = m.Species.ToString(CultureInfo.InvariantCulture);
                if (claimed.Contains(key) || logged < Needed(m)) continue;

                foreach (var (prefabName, amount) in m.Items)
                {
                    var drop = ZNetScene.instance != null ? ZNetScene.instance.GetPrefab(prefabName)?.GetComponent<ItemDrop>() : null;
                    if (drop == null) continue;
                    if (player.GetInventory().CanAddItem(drop.m_itemData, amount))
                        player.GetInventory().AddItem(prefabName, amount, 1, 0, 0L, "", false);
                    else
                        Drops.Spawn(drop, amount, player.transform.position + Vector3.up);
                }
                claimed.Add(key);
                given.Add($"Catch log: {Needed(m)} species! You receive {m.Label}.");
            }

            player.m_customData[RewardsKey] = string.Join(",", claimed);
            return given;
        }

        /// <summary>The milestone ladder for the catch log: each step's species count ("All" for every one), its reward and whether it's earned.</summary>
        public static List<(string at, string label, bool done)> Ladder(Player player)
        {
            var claimed = Claimed(player);
            return Milestones.Select(m => (m.Species == AllSpecies ? "All" : m.Species.ToString(CultureInfo.InvariantCulture), m.Label,
                                           claimed.Contains(m.Species.ToString(CultureInfo.InvariantCulture)))).ToList();
        }

        /// <summary>"Next reward: ..." for the catch log, or null when everything's been earned.</summary>
        public static string? NextReward(Player player)
        {
            var claimed = Claimed(player);
            int logged = Load(player).Count;
            var next = Milestones.Where(m => !claimed.Contains(m.Species.ToString(CultureInfo.InvariantCulture)))
                                 .OrderBy(Needed).FirstOrDefault();
            return next == null ? null : $"Next reward at {Needed(next)} species ({logged}/{Needed(next)}): {next.Label}";
        }

        public static void Record(Player player, string fishId, float weightKg, out bool newSpecies, out bool newRecord)
        {
            var data = Load(player);
            newSpecies = !data.TryGetValue(fishId, out var entry);
            newRecord = false;

            if (entry == null)
            {
                entry = new CatchEntry { Count = 0, BestKg = 0f };
                data[fishId] = entry;
            }

            entry.Count++;
            if (weightKg > entry.BestKg)
            {
                newRecord = !newSpecies; // the first catch is a discovery, not a "record"
                entry.BestKg = weightKg;
            }

            Save(player, data);
        }

        /// <summary>vdw_debug master: sets a species' catch count (logging it if it isn't yet).</summary>
        public static void SetCount(Player player, string fishId, int count)
        {
            var data = Load(player);
            if (!data.TryGetValue(fishId, out var entry)) data[fishId] = entry = new CatchEntry { Count = 0, BestKg = 0f };
            entry.Count = Mathf.Max(0, count);
            Save(player, data);
        }
    }
}
