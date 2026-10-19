using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// What fishing gives besides the fish (roadmap #27), kept small and paced so it never piles up: biome sets in the
    /// catch log, a rare valuable inside a catch, rank points for a personal best and a gift at each angler rank. The
    /// catch log's species milestones are in CatchLog, Hildir's bounty prizes in Hildir.
    /// Items are named by prefab, or by their name token ("$item_thunderstone") for vanilla items whose prefab name we
    /// don't rely on; anything not in the game (custom rewards still to be modelled) is skipped quietly.
    /// </summary>
    internal static class Rewards
    {
        // ------------------------------------------------------------------ giving

        /// <summary>The prefab for a reward: a prefab name, or a "$item_..." name token looked up in the ObjectDB.</summary>
        public static GameObject? Resolve(string id)
        {
            if (ObjectDB.instance == null) return null;
            if (!id.StartsWith("$", StringComparison.Ordinal)) return ObjectDB.instance.GetItemPrefab(id);
            return ObjectDB.instance.m_items.FirstOrDefault(p => p != null && p.GetComponent<ItemDrop>()?.m_itemData.m_shared.m_name == id);
        }

        public static bool Exists(string id) => Resolve(id) != null;

        /// <summary>Gives a reward: into the bag, or at the player's feet when it's full. False if it isn't in the game.</summary>
        public static bool Give(Player player, string id, int amount)
        {
            var drop = Resolve(id)?.GetComponent<ItemDrop>();
            if (drop == null || amount <= 0) return false;
            Drops.Give(player, drop, amount, player.transform.position + Vector3.up * 0.5f);
            return true;
        }

        /// <summary>Gives each part of a bundle; returns the parts given, for the message ("2 Angler's Meads, 300 coins").</summary>
        public static string GiveAll(Player player, IEnumerable<(string id, int amount)> items)
        {
            var given = new List<string>();
            foreach (var (id, amount) in items)
                if (Give(player, id, amount)) given.Add(Describe(id, amount));
            return string.Join(", ", given);
        }

        public static string Describe(string id, int amount)
        {
            var drop = Resolve(id)?.GetComponent<ItemDrop>();
            string name = drop != null ? Localization.instance.Localize(drop.m_itemData.m_shared.m_name) : id;
            if (id == "Coins") return $"{amount:N0} coins";
            return amount > 1 ? $"{amount} {name}" : name;
        }

        // ------------------------------------------------------------------ bonus rank points

        private const string BonusKey = "vdw_rank_bonus";
        public const int PersonalBestPoints = 5, BiomeSetPoints = 25;

        public static int BonusPoints(Player p) =>
            p.m_customData.TryGetValue(BonusKey, out var raw) && int.TryParse(raw, out var n) ? n : 0;

        public static void AddBonusPoints(Player p, int n) =>
            p.m_customData[BonusKey] = (BonusPoints(p) + n).ToString(CultureInfo.InvariantCulture);

        // ------------------------------------------------------------------ biome sets

        public sealed class BiomeSet
        {
            public string Key = "", Name = "";
            public string Bait = "";       // the biome's own bait, ten of them for completing it
            public int Coins;
            public List<FishDefinition> Fish = new List<FishDefinition>();
        }

        // in the order the world opens up; the bait each biome's fish go for most
        private static readonly (string key, string name, string bait, int coins)[] BiomeOrder =
        {
            ("Meadows", "Meadows", "grub", 100), ("BlackForest", "Black Forest", "leech", 150), ("Swamp", "Swamp", "stinkbait", 200),
            ("Mountain", "Mountain", "frost_bait", 250), ("Ocean", "Ocean", "shrimp", 250), ("Plains", "Plains", "large_minnow", 300),
            ("DeepOcean", "Deep Ocean", "deep_bait", 350), ("Mistlands", "Mistlands", "deep_bait", 400), ("AshLands", "Ashlands", "deep_bait", 450),
            ("DeepNorth", "Deep North", "northern_bait", 500),
        };

        private static List<BiomeSet>? _sets;

        /// <summary>Each biome's set: every species living there that isn't legendary (a legendary is a hunt of its own).</summary>
        public static List<BiomeSet> Sets()
        {
            if (_sets != null) return _sets;
            var sets = BiomeOrder.Select(b => new BiomeSet { Key = b.key, Name = b.name, Bait = b.bait, Coins = b.coins }).ToList();
            foreach (var f in ContentRegistry.Fish.Values.Where(f => !f.Legendary && !BossFish.IsBoss(f.Id)))
                foreach (var key in BiomesOf(f))
                    sets.FirstOrDefault(s => s.Key == key)?.Fish.Add(f);
            return _sets = sets.Where(s => s.Fish.Count > 0).ToList();
        }

        /// <summary>The biomes a species counts for: its Biomes list, else its sea (ocean / deep ocean).</summary>
        public static IEnumerable<string> BiomesOf(FishDefinition f)
        {
            if (f.Biomes != null && f.Biomes.Count > 0) return f.Biomes;
            if (f.Water == WaterType.DeepOcean) return new[] { "DeepOcean" };
            if (f.Water == WaterType.Ocean) return new[] { "Ocean" };
            return Array.Empty<string>();
        }

        // ------------------------------------------------------------------ where each species has been caught

        private const string CaughtInKey = "vdw_caught_in";   // "pike:BlackForest|Swamp;tuna:Ocean"

        private static Dictionary<string, HashSet<string>> CaughtInAll(Player p)
        {
            var map = new Dictionary<string, HashSet<string>>();
            if (!p.m_customData.TryGetValue(CaughtInKey, out var raw) || string.IsNullOrEmpty(raw)) return map;
            foreach (var part in raw.Split(new[] { ';' }, StringSplitOptions.RemoveEmptyEntries))
            {
                var kv = part.Split(':');
                if (kv.Length == 2) map[kv[0]] = new HashSet<string>(kv[1].Split(new[] { '|' }, StringSplitOptions.RemoveEmptyEntries));
            }
            return map;
        }

        /// <summary>
        /// Notes the biome a catch came from (a sea catch counts for the ocean, and for the deep ocean when it's deep).
        /// True when it's a biome this species hadn't been caught in before.
        /// </summary>
        public static bool RecordCaughtIn(Player p, string fishId, Heightmap.Biome biome, bool ocean, bool deep)
        {
            var places = new List<string>();
            if (ocean) { places.Add("Ocean"); if (deep) places.Add("DeepOcean"); }
            if (biome != Heightmap.Biome.None && biome != Heightmap.Biome.Ocean) places.Add(biome.ToString());
            var map = CaughtInAll(p);
            if (!map.TryGetValue(fishId, out var set)) map[fishId] = set = new HashSet<string>();
            bool added = false;
            foreach (var place in places) added |= set.Add(place);
            if (added) p.m_customData[CaughtInKey] = string.Join(";", map.Select(kv => kv.Key + ":" + string.Join("|", kv.Value)));
            return added;
        }

        /// <summary>
        /// Whether this species counts as logged for a biome's set: caught in that biome. A species that lives in only one
        /// biome counts once it's in the catch log at all (catches made before biomes were noted).
        /// </summary>
        public static bool LoggedIn(Player p, FishDefinition f, string biomeKey, Dictionary<string, CatchEntry> log)
        {
            if (!log.ContainsKey(f.Id)) return false;
            if (CaughtInAll(p).TryGetValue(f.Id, out var set) && set.Contains(biomeKey)) return true;
            return BiomesOf(f).Count() == 1;
        }

        private const string SetsKey = "vdw_biome_sets";

        private static HashSet<string> SetsDone(Player p) =>
            new HashSet<string>(p.m_customData.TryGetValue(SetsKey, out var raw) && !string.IsNullOrEmpty(raw) ? raw.Split(',') : Array.Empty<string>());

        public static bool SetDone(Player p, BiomeSet s) => SetsDone(p).Contains(s.Key);

        /// <summary>After a species is logged in a new biome: any biome set that completed pays out (once). Returns the message lines.</summary>
        public static string ClaimBiomeSets(Player player)
        {
            var log = CatchLog.Load(player);
            var done = SetsDone(player);
            string text = "";
            foreach (var s in Sets())
            {
                if (done.Contains(s.Key) || !s.Fish.All(f => LoggedIn(player, f, s.Key, log))) continue;
                done.Add(s.Key);
                // plus the biome's pennant, once it's modelled (docs/CUSTOM_REWARDS.md)
                string got = GiveAll(player, new[] { ("VDW_Bait_" + s.Bait, 10), ("Coins", s.Coins), ("VDW_Pennant_" + s.Key, 1) });
                AddBonusPoints(player, BiomeSetPoints);
                text += $"\n{s.Name} set complete! {got}, +{BiomeSetPoints} rank points.";
                MessageHud.instance?.QueueUnlockMsg(null, $"{s.Name} set complete", got);
            }
            player.m_customData[SetsKey] = string.Join(",", done);
            return text;
        }

        // ------------------------------------------------------------------ finds inside a catch

        /// <summary>
        /// What can turn up inside a fish, by where it was caught: vanilla valuables Haldor buys, and the custom finds
        /// still to be modelled (skipped until their prefabs exist). Weights within each place.
        /// </summary>
        private static readonly Dictionary<string, (string id, float weight)[]> FindTables = new Dictionary<string, (string, float)[]>
        {
            ["Meadows"] = new[] { ("Amber", 8f), ("VDW_Find_old_ring", 1f) },
            ["BlackForest"] = new[] { ("Amber", 6f), ("AmberPearl", 2f), ("VDW_Find_old_ring", 1f) },
            ["Swamp"] = new[] { ("AmberPearl", 5f), ("Amber", 3f), ("VDW_Find_lost_lure", 1f) },
            ["Mountain"] = new[] { ("Ruby", 4f), ("Amber", 3f), ("VDW_Find_lost_lure", 1f) },
            ["Plains"] = new[] { ("Ruby", 5f), ("AmberPearl", 2f), ("VDW_Find_dvergr_coin", 1f) },
            ["Mistlands"] = new[] { ("Ruby", 3f), ("SilverNecklace", 2f), ("VDW_Find_dvergr_coin", 2f) },
            ["AshLands"] = new[] { ("Ruby", 3f), ("SilverNecklace", 3f) },
            ["DeepNorth"] = new[] { ("SilverNecklace", 3f), ("Ruby", 2f), ("VDW_Find_old_ring", 1f) },
            ["Ocean"] = new[] { ("SilverNecklace", 4f), ("AmberPearl", 3f), ("VDW_Find_sea_glass", 2f), ("VDW_Find_bottle", 1f) },
        };
        private const float MinFindChance = 0.01f, MaxFindChance = 0.04f;

        /// <summary>The chance a catch holds something: ~1% for small, common fish, up to ~4% for big or rare ones.</summary>
        public static float FindChance(FishDefinition f)
        {
            float size = Mathf.Clamp01(f.MaxWeightKg / 60f);
            float rarity = Mathf.Clamp01(1f - f.BiteWeight / 6f);
            return Mathf.Lerp(MinFindChance, MaxFindChance, Mathf.Max(size, rarity));
        }

        /// <summary>Rolls a find for this catch: the prefab, or null.</summary>
        public static GameObject? RollFind(FishingSession s)
        {
            if (!string.IsNullOrWhiteSpace(s.Fish.CatchBait) || UnityEngine.Random.value >= FindChance(s.Fish)) return null;
            string place = s.Ocean ? "Ocean" : s.Biome.ToString();
            if (!FindTables.TryGetValue(place, out var table)) table = FindTables["Meadows"];
            var options = table.Where(t => Exists(t.id)).ToList();
            if (options.Count == 0) return null;
            float roll = UnityEngine.Random.value * options.Sum(o => o.weight);
            foreach (var (id, weight) in options)
                if ((roll -= weight) <= 0f) return Resolve(id);
            return Resolve(options[options.Count - 1].id);
        }

        // ------------------------------------------------------------------ rank-up gifts

        /// <summary>A small gift for reaching each angler rank: coins (50 x the rank) and something for that stage.</summary>
        private static readonly (string id, int amount)[][] RankGifts =
        {
            Array.Empty<(string, int)>(),                                           // 1: where everyone starts
            new[] { ("VDW_Buff_angler_minor", 2) },
            new[] { ("VDW_Buff_chum_basic", 1), ("VDW_Hook_small", 3) },
            new[] { ("VDW_Buff_steady_minor", 2) },
            new[] { ("VDW_Buff_angler_medium", 2) },
            new[] { ("VDW_Buff_chum_blood", 1), ("VDW_Hook_heavy", 2) },
            new[] { ("VDW_Buff_grip_medium", 2) },
            new[] { ("VDW_Buff_angler_major", 2) },
            new[] { ("VDW_Buff_steady_major", 1), ("VDW_Mat_trophy", 1) },
            new[] { ("VDW_Buff_angler_north", 2) },
        };

        private static readonly int[] CapRanks = { 3, 6, 9 };   // ranks 4, 7 and 10

        public static string RankGift(Player player, int rankIndex)
        {
            if (rankIndex <= 0 || rankIndex >= RankGifts.Length) return "";
            var items = RankGifts[rankIndex].Concat(new[] { ("Coins", 50 * (rankIndex + 1)) });
            // an angler's cap at three of the ranks, once they're modelled (docs/CUSTOM_REWARDS.md)
            if (CapRanks.Contains(rankIndex)) items = items.Concat(new[] { ("VDW_AnglerCap_" + (rankIndex + 1), 1) });
            return GiveAll(player, items);
        }
    }
}
