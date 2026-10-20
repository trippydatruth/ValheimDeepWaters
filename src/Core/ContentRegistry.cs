using Jotunn.Configs;
using Jotunn.Entities;
using Jotunn.Managers;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;

namespace ValheimDeepWaters
{
    internal static class ContentRegistry
    {
        public static readonly Dictionary<string, FishDefinition> Fish = new();
        public static readonly Dictionary<string, BaitDefinition> Baits = new();
        public static readonly Dictionary<string, GameObject> FishItems = new();
        public static readonly Dictionary<string, GameObject> BaitItems = new();
        public static readonly Dictionary<string, BaitDefinition> BaitByItemName = new();
        public static readonly Dictionary<string, HookDefinition> Hooks = new();
        public static readonly Dictionary<string, HookDefinition> HookByItemName = new();
        public static readonly List<RodDefinition> Rods = new();
        public static readonly Dictionary<string, RodDefinition> RodByItemName = new();
        private static readonly Dictionary<string, ItemDrop> RodItems = new();

        public static bool IsRod(ItemDrop.ItemData? item) => GetRod(item) != null;

        public static RodDefinition? GetRod(ItemDrop.ItemData? item) =>
            item?.m_shared != null && RodByItemName.TryGetValue(item.m_shared.m_name, out var rod) ? rod : null;

        /// <summary>
        /// Prefab name for a rod. The first rod keeps the old single rod's prefab name so rods already in
        /// players' inventories carry over (as that tier) instead of disappearing.
        /// </summary>
        public static string RodPrefabName(RodDefinition rod) =>
            Rods.Count > 0 && rod == Rods[0] ? "VDW_FishingRod" : "VDW_Rod_" + rod.Id;

        public static void Initialize()
        {
            EnsureDataFiles();
            LoadData();

            try
            {
                RegisterRods();
                SetUpHaldor();
                RegisterHooks();
                FishingBuffs.Register();
                RegisterBaits();
                RegisterFish();
                BossFish.Register();
                try { FishMaterials.Register(); } catch (Exception ex) { Plugin.Log.LogError($"Fish materials failed: {ex}"); }
                try { FishDishes.Register(); } catch (Exception ex) { Plugin.Log.LogError($"Fish dishes failed: {ex}"); }
                try { BogWitch.Register(); } catch (Exception ex) { Plugin.Log.LogError($"Bog Witch content failed: {ex}"); }
                try { Hildir.Register(); } catch (Exception ex) { Plugin.Log.LogError($"Hildir content failed: {ex}"); }
                TraderPanel.Ensure();
                // Fisherman's gear: the remade set (new_gear_rig.blend, painted weights)
                try { FisherGear.Register(); } catch (Exception ex) { Plugin.Log.LogError($"Fisherman's gear failed: {ex}"); }
                RemoveVanillaFishingGear();
                BaitSources.Register();
                try { FishSize.RegisterTrophyMount(); } catch (Exception ex) { Plugin.Log.LogError($"Trophy mount failed: {ex.Message}"); }
                try { RareFish.RegisterIcons(); } catch (Exception ex) { Plugin.Log.LogError($"Rare fish icons failed: {ex}"); }
                try { Relics.Register(); } catch (Exception ex) { Plugin.Log.LogError($"Relics failed: {ex}"); }
                try { Mastery.RegisterPlaques(); } catch (Exception ex) { Plugin.Log.LogError($"Gold plaques failed: {ex}"); }
                try { FishingBoat.Register(); } catch (Exception ex) { Plugin.Log.LogError($"Fishing Boat failed: {ex}"); }
            }
            catch (Exception ex)
            {
                Plugin.Log.LogError($"Content registration failed: {ex}");
            }
        }

        private static void EnsureDataFiles()
        {
            if (!File.Exists(VdwConfig.FishFile))
                File.WriteAllText(VdwConfig.FishFile, DefaultData.FishJson);

            if (!File.Exists(VdwConfig.BaitFile))
                File.WriteAllText(VdwConfig.BaitFile, DefaultData.BaitJson);

            if (!File.Exists(VdwConfig.RodsFile))
                File.WriteAllText(VdwConfig.RodsFile, DefaultData.RodsJson);

            if (!File.Exists(VdwConfig.HooksFile))
                File.WriteAllText(VdwConfig.HooksFile, DefaultData.HooksJson);

            if (!File.Exists(VdwConfig.BuffsFile))
                File.WriteAllText(VdwConfig.BuffsFile, DefaultData.BuffsJson);

            var offered = LoadOffered();
            MergeDefaults(VdwConfig.FishFile, DefaultData.FishJson, "Fish", offered);
            MergeDefaults(VdwConfig.BaitFile, DefaultData.BaitJson, "Baits", offered);
            MergeDefaults(VdwConfig.RodsFile, DefaultData.RodsJson, "Rods", offered);
            MergeDefaults(VdwConfig.HooksFile, DefaultData.HooksJson, "Hooks", offered);
            MergeDefaults(VdwConfig.BuffsFile, DefaultData.BuffsJson, "Buffs", offered);
            try { File.WriteAllText(OfferedFile, offered.ToString(Formatting.Indented)); }
            catch (Exception ex) { Plugin.Log.LogWarning($"Could not save {OfferedFile} ({ex.Message})."); }
        }

        // Which default ids each data file has already been given, so an entry a player deletes stays deleted.
        private static string OfferedFile => Path.Combine(Plugin.ConfigDirectory, "defaults_offered.json");

        private static JObject LoadOffered()
        {
            try { return File.Exists(OfferedFile) ? JObject.Parse(File.ReadAllText(OfferedFile)) : new JObject(); }
            catch { return new JObject(); }
        }

        /// <summary>Default entries whose old text is replaced if the player never changed it: (file, id, old name).</summary>
        private static readonly (string kind, string id, string oldName)[] RenamedDefaults =
        {
            ("Baits", "fly", "Feather Fly"),
            ("Buffs", "relic_horn", "Horn of Ægir"),       // drunk -> blown
            ("Baits", "lure_wyrm", "Wyrm Lure"),           // now a silver scale with a dragon tear
        };

        /// <summary>
        /// Default recipes that changed: a file entry still on the old recipe (the player never changed it) gets the new
        /// recipe and crafting station. (file, id, old recipe as "Item:Amount,Item:Amount").
        /// </summary>
        private static readonly (string kind, string id, string oldRecipe)[] UpdatedRecipes =
        {
            // the Leviathan needs two of every boss fish's material, the Fimbul Salmon's too (0.15.0, roadmap #24)
            ("Rods", "leviathan", "VDW_BossMat_eikthyr_elver:1,VDW_BossMat_elder_bass:1,VDW_BossMat_bonemass_catfish:1,VDW_BossMat_moder_scale:1,VDW_BossMat_yagluthgill:1,VDW_BossMat_queen_eel:1,YggdrasilWood:10,FlametalNew:6"),
            // boss lures: the boss's own drops where it gives several, crafted at the biome's station (0.14.0)
            ("Baits", "lure_antler", "TrophyEikthyr:1,HardAntler:1"),
            ("Baits", "lure_root", "TrophyTheElder:1,Root:1"),
            ("Baits", "lure_ooze", "TrophyBonemass:1,Ooze:2"),
            ("Baits", "lure_wyrm", "TrophyDragonQueen:1,FreezeGland:2"),
            ("Baits", "lure_ember", "TrophyGoblinKing:1,SurtlingCore:1"),
            ("Baits", "lure_chitin", "TrophySeekerQueen:1,Carapace:2"),
            // the Bog Witch's stock in the top meads (0.15.0)
            ("Buffs", "steady_major", "Honey:2,Cloudberry:4,Eitr:1,VDW_Mat_ink:1"),
            ("Buffs", "grip_major", "Honey:2,Barley:4,LoxMeat:1,VDW_Mat_roe:2"),
            // fish materials in lure, bait, mead, chum and totem recipes (0.15.0)
            ("Baits", "lure_feather_fly", "Feathers:2,Resin:1"),
            ("Baits", "lure_flint_spinner", "Flint:1,Feathers:1,Wood:1"),
            ("Baits", "lure_leather_grub", "LeatherScraps:2,Resin:1"),
            ("Baits", "lure_bronze_spoon", "Bronze:1,LeatherScraps:1"),
            ("Baits", "lure_finewood_crank", "FineWood:1,Resin:1,BronzeNails:2"),
            ("Baits", "lure_guck_crawler", "Guck:1,Resin:2,IronNails:1"),
            ("Baits", "lure_bone_jig", "Iron:1,BoneFragments:2,Feathers:1"),
            ("Baits", "lure_silver_swimbait", "Silver:1,LeatherScraps:2,FreezeGland:1"),
            ("Baits", "lure_linen_popper", "FineWood:1,Feathers:2,LinenThread:1"),
            ("Baits", "lure_ice_spoon", "Ice:1,Silver:1"),
            ("Baits", "lure_frostcore_jig", "FrostCore:1,Iron:1,BarkaBranch:1"),
            ("Baits", "lure_antler", "HardAntler:1,LeatherScraps:2,Flint:1"),
            ("Baits", "lure_root", "TrophyTheElder:1,AncientSeed:1,Resin:3"),
            ("Baits", "lure_ooze", "TrophyBonemass:1,Ooze:3,WitheredBone:2"),
            ("Baits", "lure_wyrm", "DragonTear:2,Silver:1,FreezeGland:1"),
            ("Baits", "lure_ember", "YagluthDrop:1,BlackMetal:1,SurtlingCore:1"),
            ("Baits", "lure_chitin", "QueenDrop:1,Carapace:2,Eitr:1"),
            ("Baits", "lure_crown", "CrownJewel:1,FrostCore:2,Silver:1"),
            ("Baits", "deep_bait", "Entrails:1,Ooze:1,Bloodbag:1"),
            ("Baits", "frost_bait", "FreezeGland:1,WolfMeat:1"),
            ("Baits", "rune_bait", "Silver:1,Eitr:1,SerpentScale:1"),
            ("Baits", "northern_bait", "SealBlubber:1,Lingonberry:2"),
            ("Buffs", "angler_minor", "Honey:2,Raspberry:4"),
            ("Buffs", "angler_medium", "Honey:2,Bloodbag:2,Blueberries:4"),
            ("Buffs", "angler_major", "Honey:2,Sap:2,RoyalJelly:1"),
            ("Buffs", "angler_north", "Honey:2,Lingonberry:6,Ice:1"),
            ("Buffs", "steady_minor", "Honey:2,Thistle:2,Dandelion:2"),
            ("Buffs", "steady_medium", "Honey:2,Onion:2,Crystal:1"),
            ("Buffs", "steady_major", "Honey:2,Cloudberry:4,Eitr:1"),
            ("Buffs", "grip_medium", "Honey:2,WolfFang:2,Onion:2"),
            ("Buffs", "grip_major", "Honey:2,Barley:4,LoxMeat:1"),
            ("Buffs", "chum_basic", "NeckTail:2,RawMeat:1"),
            ("Buffs", "chum_blood", "Bloodbag:2,Entrails:2"),
            ("Buffs", "chum_abyssal", "Bloodbag:2,Sap:2,Ooze:2"),
            ("Buffs", "chum_blubber", "SealBlubber:2,Lingonberry:4"),
            ("Buffs", "rune_njord", "Silver:4,Crystal:2,SerpentScale:2"),
            ("Buffs", "totem_fisher", "FineWood:10,ElderBark:4,Guck:2"),
            ("Buffs", "totem_njord", "YggdrasilWood:10,Silver:4,Eitr:4"),
        };

        /// <summary>
        /// Default numbers that changed: a file entry still on the old value (the player never changed it) gets the new
        /// default. (file, id, field, old value)
        /// </summary>
        /// <summary>Text fields changed in the defaults: replaced only where a data file still has the old wording.</summary>
        private static readonly (string kind, string id, string field, string oldText)[] UpdatedText =
        {
            // Njord's Regalia got its own crown model: bronze, runes and stones, not silver (0.15.0)
            ("Buffs", "regalia_njord", "Description", "The four relics of the sea - the Pearl, the Scale, the Horn and the Golden Hook - set in one silver crown. Whoever wears it is the sea god's own angler."),
        };

        private static readonly (string kind, string id, string field, double oldValue)[] UpdatedStats =
        {
            // more line on every rod past the first, the most on the best (0.14.0)
            ("Rods", "copper", "LineCapacity", 40), ("Rods", "finewood", "LineCapacity", 50),
            ("Rods", "ancientbark", "LineCapacity", 60), ("Rods", "silver", "LineCapacity", 70),
            ("Rods", "blackmetal", "LineCapacity", 85), ("Rods", "yggdrasil", "LineCapacity", 100),
            ("Rods", "ashwood", "LineCapacity", 120), ("Rods", "frostwood", "LineCapacity", 135),
            ("Rods", "haldor", "LineCapacity", 140), ("Rods", "leviathan", "LineCapacity", 160),
            // the Fimbul Hook is for big fish only (25 kg up); the Golden Hook stays the one that suits any fish (0.15.0)
            ("Hooks", "fimbul", "MinKg", 0),
        };

        /// <summary>
        /// Fields added to existing entries after an update: a default entry's field is copied into the player's entry
        /// of the same id if it doesn't have one (once, so a field deleted on purpose stays deleted). (file, field)
        /// </summary>
        private static readonly (string kind, string field)[] AddedFields =
        {
            ("Fish", "Material"),      // fish materials from cleaning (0.15.0)
            ("Rods", "Upgrade"),       // rod upgrade levels (0.15.0)
            ("Buffs", "FloatModel"),   // floats your line wears (0.15.0)
            ("Buffs", "FloatLight"),
            ("Hooks", "HookBonus"),    // the Golden Hook's edge in the strike (0.15.0)
            ("Hooks", "HookWindow"),
        };

        /// <summary>
        /// Fields whose defaults were reworked: once (by tag), the player's entry takes the default's value, edited or not -
        /// for a rework the old values no longer fit. (file, field, tag)
        /// </summary>
        private static readonly (string kind, string field, string tag)[] ReplacedFields =
        {
            ("Baits", "TargetFish", "bait_targets_1"),       // each bait goes for a few fish (roadmap #26)
            ("Fish", "PreferredBaits", "bait_targets_1"),
            ("Fish", "PreferredBaits", "bluegill_bait_1"),   // the bluegill is a baitfish for catfish, bass and pike
            ("Fish", "CatchBait", "bluegill_bait_1"),
            ("Fish", "CatchAmount", "bluegill_bait_1"),
            ("Fish", "ForbiddenBaits", "bluegill_bait_1"),
            ("Buffs", "Find", "relics_1"),                   // relics: one source each (roadmap #30) - the Horn is no longer found in fish
            ("Hooks", "Find", "relics_1"),                   // ...and the Golden Hook is, rarely, in legendaries
        };

        private static string RecipeKey(JToken? recipe) =>
            recipe is JArray a ? string.Join(",", a.OfType<JObject>().Select(r => $"{(string?)r["Item"]}:{(int?)r["Amount"] ?? 1}")) : "";

        /// <summary>
        /// Default entries the mod no longer has: taken out of the player's data file once (recorded, so one added back
        /// on purpose stays). Items of these already in an inventory disappear.
        /// </summary>
        private static readonly (string kind, string id)[] RetiredDefaults =
        {
            ("Buffs", "hat_leather"), ("Buffs", "hat_troll"), ("Buffs", "hat_seafarer"),
            ("Buffs", "cape_seawolf"), ("Buffs", "cape_netweaver"), ("Buffs", "cape_ashen"),
            ("Fish", "cod"), ("Fish", "trolltrout"), ("Fish", "ashscale"),     // too close to vanilla fish
            ("Fish", "dvergr_dace"),                                         // dropped (0.14.0)
        };

        /// <summary>Retired fish, and the vanilla fish that takes their place in a bait's TargetFish.</summary>
        private static readonly Dictionary<string, string> RetiredFishStandIn = new()
        {
            ["cod"] = "coral_cod", ["trolltrout"] = "trollfish", ["ashscale"] = "magmafish", ["dvergr_dace"] = "trout",
        };

        /// <summary>
        /// Brings a data file up to date after an update: default entries that are new since the file was made are
        /// added (each one only once, so deleting an entry sticks), and defaults whose text changed are refreshed if
        /// the player never edited them. Everything else in the file - edits, extra fields, order - is kept.
        /// </summary>
        private static void MergeDefaults(string path, string defaultsJson, string kind, JObject offered)
        {
            try
            {
                var file = JArray.Parse(File.ReadAllText(path));
                var defaults = JArray.Parse(defaultsJson);
                var seen = offered[kind] as JArray ?? new JArray();
                offered[kind] = seen;
                var seenIds = new HashSet<string>(seen.Values<string>().Where(s => s != null)!);
                var byId = file.OfType<JObject>().Where(o => o["Id"] != null).ToDictionary(o => (string)o["Id"]!, o => o);
                bool changed = false;

                foreach (var d in defaults.OfType<JObject>())
                {
                    string? id = (string?)d["Id"];
                    if (id == null) continue;
                    if (!byId.ContainsKey(id) && !seenIds.Contains(id))
                    {
                        file.Add(d.DeepClone());
                        changed = true;
                    }
                    if (seenIds.Add(id)) seen.Add(id);
                }

                var retired = offered[kind + "_retired"] as JArray ?? new JArray();
                offered[kind + "_retired"] = retired;
                var retiredIds = new HashSet<string>(retired.Values<string>().Where(s => s != null)!);
                foreach (var (k, id) in RetiredDefaults)
                {
                    if (k != kind || retiredIds.Contains(id)) continue;
                    if (byId.TryGetValue(id, out var gone)) { gone.Remove(); changed = true; }
                    retired.Add(id);
                }

                if (kind == "Baits")
                    foreach (var targets in file.OfType<JObject>().Select(o => o["TargetFish"]).OfType<JArray>())
                        foreach (var t in targets.ToList())
                            if ((string?)t is string fid && RetiredFishStandIn.TryGetValue(fid, out var standIn))
                            {
                                if (targets.Any(x => (string?)x == standIn)) t.Remove(); else t.Replace(standIn);
                                changed = true;
                            }

                foreach (var (k, id, oldRecipe) in UpdatedRecipes)
                {
                    if (k != kind || !byId.TryGetValue(id, out var entry) || RecipeKey(entry["Recipe"]) != oldRecipe) continue;
                    var d = defaults.OfType<JObject>().FirstOrDefault(o => (string?)o["Id"] == id);
                    if (d == null) continue;
                    foreach (var field in new[] { "Recipe", "CraftingStation", "StationLevel", "CraftAmount" })
                        if (d[field] != null) entry[field] = d[field]!.DeepClone();
                    changed = true;
                }

                foreach (var (k, id, field, oldValue) in UpdatedStats)
                {
                    if (k != kind || !byId.TryGetValue(id, out var entry) || entry[field] == null) continue;
                    if (Math.Abs((double)entry[field]! - oldValue) > 1e-6) continue;
                    var d = defaults.OfType<JObject>().FirstOrDefault(o => (string?)o["Id"] == id);
                    if (d?[field] == null) continue;
                    entry[field] = d[field]!.DeepClone();
                    changed = true;
                }

                foreach (var (k, id, field, oldText) in UpdatedText)
                {
                    if (k != kind || !byId.TryGetValue(id, out var entry) || (string?)entry[field] != oldText) continue;
                    var d = defaults.OfType<JObject>().FirstOrDefault(o => (string?)o["Id"] == id);
                    if (d?[field] == null) continue;
                    entry[field] = d[field]!.DeepClone();
                    changed = true;
                }

                var filled = offered[kind + "_fields"] as JArray ?? new JArray();
                offered[kind + "_fields"] = filled;
                var filledKeys = new HashSet<string>(filled.Values<string>().Where(s => s != null)!);
                foreach (var (k, field) in AddedFields)
                {
                    if (k != kind) continue;
                    foreach (var d in defaults.OfType<JObject>())
                    {
                        string? id = (string?)d["Id"];
                        if (id == null || d[field] == null || !filledKeys.Add(id + "." + field)) continue;
                        filled.Add(id + "." + field);
                        if (byId.TryGetValue(id, out var entry) && entry[field] == null) { entry[field] = d[field]!.DeepClone(); changed = true; }
                    }
                }

                var replaced = offered[kind + "_replaced"] as JArray ?? new JArray();
                offered[kind + "_replaced"] = replaced;
                var replacedKeys = new HashSet<string>(replaced.Values<string>().Where(s => s != null)!);
                foreach (var (k, field, tag) in ReplacedFields)
                {
                    if (k != kind || !replacedKeys.Add(tag + "." + field)) continue;
                    replaced.Add(tag + "." + field);
                    foreach (var d in defaults.OfType<JObject>())
                    {
                        string? id = (string?)d["Id"];
                        if (id == null || !byId.TryGetValue(id, out var entry)) continue;
                        if (d[field] == null) { if (entry[field] != null) { entry.Remove(field); changed = true; } continue; }   // gone from the default: gone here too
                        if (!JToken.DeepEquals(entry[field], d[field])) { entry[field] = d[field]!.DeepClone(); changed = true; }
                    }
                    Plugin.Log.LogInfo($"{Path.GetFileName(path)}: {field} brought up to the new defaults ({tag}).");
                }

                foreach (var (k, id, oldName) in RenamedDefaults)
                {
                    if (k != kind || !byId.TryGetValue(id, out var entry) || (string?)entry["Name"] != oldName) continue;
                    var d = defaults.OfType<JObject>().FirstOrDefault(o => (string?)o["Id"] == id);
                    if (d == null || ((string?)entry["Name"] == (string?)d["Name"] && (string?)entry["Description"] == (string?)d["Description"])) continue;
                    entry["Name"] = d["Name"];
                    entry["Description"] = d["Description"];
                    changed = true;
                }

                if (changed) File.WriteAllText(path, file.ToString(Formatting.Indented));
            }
            catch (Exception ex)
            {
                Plugin.Log.LogWarning($"Could not update {Path.GetFileName(path)} with new defaults ({ex.Message}); it's used as it is.");
            }
        }

        private static void LoadData()
        {
            Fish.Clear();
            Baits.Clear();

            var fish = JsonConvert.DeserializeObject<List<FishDefinition>>(File.ReadAllText(VdwConfig.FishFile)) ?? new();
            foreach (var f in fish)
                if (!string.IsNullOrWhiteSpace(f.Id))
                    Fish[f.Id] = f;
            AddVanillaFish();

            var baits = JsonConvert.DeserializeObject<List<BaitDefinition>>(File.ReadAllText(VdwConfig.BaitFile)) ?? new();
            foreach (var b in baits)
                if (!string.IsNullOrWhiteSpace(b.Id))
                    Baits[b.Id] = b;

            Rods.Clear();
            var rods = JsonConvert.DeserializeObject<List<RodDefinition>>(File.ReadAllText(VdwConfig.RodsFile)) ?? new();
            foreach (var r in rods)
                if (!string.IsNullOrWhiteSpace(r.Id))
                    Rods.Add(r);

            Hooks.Clear();
            var hooks = JsonConvert.DeserializeObject<List<HookDefinition>>(File.ReadAllText(VdwConfig.HooksFile)) ?? new();
            foreach (var h in hooks)
                if (!string.IsNullOrWhiteSpace(h.Id))
                    Hooks[h.Id] = h;

            FishingBuffs.Load(JsonConvert.DeserializeObject<List<BuffDefinition>>(File.ReadAllText(VdwConfig.BuffsFile)) ?? new());

            Plugin.Log.LogInfo($"Loaded {Fish.Count} fish, {Baits.Count} baits, {Hooks.Count} hooks, {Rods.Count} rods and {FishingBuffs.Buffs.Count} buff items.");
        }

        /// <summary>
        /// Brings an older Fish.json up to date with the vanilla fish: entries that now stand for a vanilla fish
        /// (Perch, Pike...) are replaced with the vanilla-linked default, and missing vanilla fish are added. Other
        /// entries are left exactly as they are. The file is rewritten only if something changed.
        /// </summary>
        private static void AddVanillaFish()
        {
            var defaults = JsonConvert.DeserializeObject<List<FishDefinition>>(DefaultData.FishJson) ?? new();
            bool changed = false;
            foreach (var d in defaults.Where(d => d.IsVanilla))
            {
                if (Fish.TryGetValue(d.Id, out var existing) && existing.IsVanilla) continue;
                Fish[d.Id] = d;
                changed = true;
            }
            if (!changed) return;

            try { File.WriteAllText(VdwConfig.FishFile, JsonConvert.SerializeObject(Fish.Values.ToList(), Formatting.Indented, new Newtonsoft.Json.Converters.StringEnumConverter())); }
            catch (Exception ex) { Plugin.Log.LogWarning($"Could not update {VdwConfig.FishFile} with the vanilla fish ({ex.Message})."); }
        }

        /// <summary>Which fish species a swimming fish is, by its prefab name ("Fish1", "VDW_Fish_trout").</summary>
        public static readonly Dictionary<string, string> FishIdByPrefab = new();

        /// <summary>
        /// The custom model a fish swims and fights as: its own "fish_&lt;id&gt;", or for a baitfish (which lands as bait)
        /// its bait's "bait_&lt;id&gt;" - without that, minnows swam up as the vanilla bait mesh their bait item is cloned from.
        /// </summary>
        public static string ModelKeyFor(FishDefinition fish) =>
            string.IsNullOrWhiteSpace(fish.CatchBait) ? "fish_" + fish.Id : "bait_" + fish.CatchBait;

        /// <summary>The item a landed fish gives: vanilla's pickup item for vanilla fish, else the fish's own item.</summary>
        public static ItemDrop? DropFor(FishDefinition fish)
        {
            if (!FishItems.TryGetValue(fish.Id, out var prefab) || prefab == null) return null;
            var pickup = prefab.GetComponent<global::Fish>()?.m_pickupItem;
            return (pickup != null ? pickup.GetComponent<ItemDrop>() : null) ?? prefab.GetComponent<ItemDrop>();
        }

        public static string HookDisplayName(HookDefinition h) => Loc.Token("vdw_hook_" + h.Id,
            (string.IsNullOrWhiteSpace(h.Name) ? h.Id : h.Name) + (string.IsNullOrWhiteSpace(h.Label) ? "" : " " + h.Label));

        private static void RegisterHooks()
        {
            foreach (var hook in Hooks.Values)
            {
                try
                {
                    string basePrefab = ResolveBasePrefab(hook.VanillaFallbackPrefab, "BronzeNails");
                    var item = hook.Craftable && hook.Recipe.Count > 0
                        ? new CustomItem("VDW_Hook_" + hook.Id, basePrefab, new ItemConfig
                        {
                            Amount = Math.Max(1, hook.CraftAmount),
                            CraftingStation = hook.CraftingStation,
                            MinStationLevel = Math.Max(1, hook.StationLevel),
                            Requirements = hook.Recipe.Select(r => new RequirementConfig(r.Item, r.Amount)).ToArray()
                        })
                        : new CustomItem("VDW_Hook_" + hook.Id, basePrefab);
                    var shared = item.ItemDrop.m_itemData.m_shared;
                    string name = HookDisplayName(hook);
                    shared.m_name = name;
                    shared.m_description = Loc.Token("vdw_hook_" + hook.Id + "_desc", $"{hook.Description}\n\nSuits fish of {hook.MinKg:0.#}–{hook.MaxKg:0.#} kg. " +
                                           (hook.NeverStraightens ? "Never straightens. " : "Smaller fish struggle to take it; bigger ones can straighten it, and much bigger ones won't bite. ") +
                                           (hook.KeepChance > 0f ? $"{hook.KeepChance * 100f:0}% chance to survive a snapped line. " : "") +
                                           (hook.HookBonus > 0f ? $"Hook chance +{hook.HookBonus * 100f:0}%. " : "") +
                                           (hook.HookWindow > 0f ? $"Hook window +{hook.HookWindow * 100f:0}%. " : "") +
                                           (hook.Craftable ? ""
                                               : Relics.SourceText("VDW_Hook_" + hook.Id) ?? "\n\nCan't be crafted. Sometimes found inside a fish."));
                    shared.m_weight = 0.05f;
                    shared.m_maxStackSize = 50;

                    if (CustomModels.ApplyToPrefab(item.ItemPrefab, "hook_" + hook.Id))
                        GroundPose.FitCollider(item.ItemPrefab);
                    else
                        Plugin.Log.LogWarning($"Hook '{hook.Id}': no hook_{hook.Id} model found; it keeps the stand-in look.");

                    ItemManager.Instance.AddItem(item);
                    HookByItemName[name] = hook;
                }
                catch (Exception ex)
                {
                    Plugin.Log.LogError($"Failed to register hook '{hook.Id}': {ex.Message}");
                }
            }
        }

        private static void RegisterRods()
        {
            foreach (var rod in Rods)
            {
                try
                {
                    // A rod that isn't craftable (e.g. sold by Haldor) keeps its recipe switched off: it never shows
                    // for crafting, but Valheim repairs items at their recipe's station, so it can still be repaired.
                    // Upgrade levels: the base recipe's items only count for crafting, the Upgrade list's per level.
                    // A rod you can't craft but can upgrade (Haldor's) keeps an upgrade-only recipe.
                    bool upgradable = rod.Upgrade.Count > 0;
                    var config = new ItemConfig
                    {
                        Enabled = rod.Craftable || upgradable,
                        CraftingStation = rod.CraftingStation,
                        MinStationLevel = Math.Max(1, rod.StationLevel),
                        Requirements = rod.Recipe.Select(r => new RequirementConfig(r.Item, r.Amount))
                            .Concat(rod.Upgrade.Select(r => new RequirementConfig(r.Item, 0, r.Amount))).ToArray()
                    };

                    var item = new CustomItem(RodPrefabName(rod), "FishingRod", config);
                    var shared = item.ItemDrop.m_itemData.m_shared;
                    string name = Loc.Token("vdw_rod_" + rod.Id, string.IsNullOrWhiteSpace(rod.Name) ? rod.Id : rod.Name);
                    shared.m_itemType = ItemDrop.ItemData.ItemType.OneHandedWeapon;
                    shared.m_name = name;
                    string source = rod.TraderPrice > 0 && !rod.Craftable ? $"\n\nSold only by Haldor ({rod.TraderPrice} coins)." : "";
                    // the stats go in the tooltip (RodUpgrades), for the rod's own upgrade level
                    shared.m_description = Loc.Token("vdw_rod_" + rod.Id + "_desc", $"{rod.Description}{source}");
                    shared.m_maxQuality = upgradable ? RodUpgrades.MaxLevel : 1;
                    RodItems[rod.Id] = item.ItemDrop;
                    shared.m_weight = 2f;

                    // Vanilla durability: shows the bar, and the rod is repaired at its recipe's station.
                    shared.m_useDurability = rod.Durability > 0f;
                    shared.m_maxDurability = rod.Durability;
                    shared.m_durabilityPerLevel = upgradable ? rod.Durability * RodUpgrades.DurabilityPerLevel : 0f;
                    shared.m_useDurabilityDrain = 0f;
                    shared.m_canBeReparied = true;
                    shared.m_destroyBroken = false;
                    item.ItemDrop.m_itemData.m_durability = rod.Durability;

                    // A model just for this rod (rod_<id>) if there is one, else the shared rod model.
                    if (!CustomModels.ApplyToPrefab(item.ItemPrefab, "rod_" + rod.Id))
                        CustomModels.ApplyToPrefab(item.ItemPrefab, "rod");
                    VanillaFx.AttachToRod(item.ItemPrefab, rod.Id);            // the top rods only

                    if (!rod.Craftable && item.Recipe?.Recipe != null) item.Recipe.Recipe.m_noCraftOnlyUpgrade = true;
                    ItemManager.Instance.AddItem(item);
                    RodByItemName[name] = rod;
                }
                catch (Exception ex)
                {
                    Plugin.Log.LogError($"Failed to register rod '{rod.Id}': {ex.Message}");
                }
            }
        }

        /// <summary>
        /// Haldor sells any rod with a TraderPrice (the vanilla rod is taken out in RemoveVanillaFishingGear).
        /// </summary>
        private static void SetUpHaldor()
        {
            var trader = PrefabManager.Instance.GetPrefab("Haldor")?.GetComponent<Trader>();
            if (trader == null)
            {
                Plugin.Log.LogWarning("Haldor not found; his rods are unchanged.");
                return;
            }

            foreach (var rod in Rods.Where(r => r.TraderPrice > 0))
            {
                if (!RodItems.TryGetValue(rod.Id, out var drop)) continue;
                trader.m_items.Add(new Trader.TradeItem
                {
                    m_prefab = drop,
                    m_stack = 1,
                    m_price = rod.TraderPrice,
                    m_requiredGlobalKey = rod.TraderRequiredKey ?? ""
                });
            }
        }


        /// <summary>
        /// Finds a vanilla prefab to clone. Tries the requested name, a "_cave" variant (vanilla names the
        /// fourth fish "Fish4_cave"), then the fallback, so a bad name in the JSON can never abort registration.
        /// </summary>
        private static string ResolveBasePrefab(string wanted, string fallback)
        {
            foreach (var candidate in new[] { wanted, wanted + "_cave", fallback })
            {
                if (string.IsNullOrWhiteSpace(candidate)) continue;
                if (PrefabManager.Instance.GetPrefab(candidate) == null) continue;

                if (candidate != wanted)
                    Plugin.Log.LogWarning($"Base prefab '{wanted}' not found; using '{candidate}' instead.");
                return candidate;
            }

            return fallback;
        }

        /// <summary>
        /// A bait's model: its own "bait_<id>", else - for a baitfish's live bait without one (the bluegill) - the model of
        /// the fish it comes from.
        /// </summary>
        private static string BaitModelKey(string baitId)
        {
            string own = "bait_" + baitId;
            if (CustomModels.HasModel(own)) return own;
            var source = Fish.Values.FirstOrDefault(f => f.CatchBait == baitId);
            return source != null && CustomModels.HasModel("fish_" + source.Id) ? "fish_" + source.Id : own;
        }

        private static void RegisterBaits()
        {
            foreach (var bait in Baits.Values)
            {
                try
                {
                    string basePrefab = ResolveBasePrefab(bait.VanillaFallbackPrefab, "FishingBait");
                    // Only baits with no natural source (see BaitSources) carry a recipe.
                    var item = bait.Recipe.Count > 0
                        ? new CustomItem("VDW_Bait_" + bait.Id, basePrefab, new ItemConfig
                        {
                            Amount = Math.Max(1, bait.CraftAmount),
                            CraftingStation = bait.CraftingStation,
                            MinStationLevel = Math.Max(1, bait.StationLevel),
                            Requirements = bait.Recipe.Select(r => new RequirementConfig(r.Item, r.Amount)).ToArray()
                        })
                        : new CustomItem("VDW_Bait_" + bait.Id, basePrefab);
                    if (item.ItemPrefab == null || item.ItemDrop == null)
                    {
                        Plugin.Log.LogWarning($"Could not create bait '{bait.Id}' from '{basePrefab}'.");
                        continue;
                    }

                    string itemName = Loc.Token("vdw_bait_" + bait.Id, string.IsNullOrWhiteSpace(bait.Name) ? bait.Id : bait.Name);
                    item.ItemDrop.m_itemData.m_shared.m_name = itemName;
                    item.ItemDrop.m_itemData.m_shared.m_description = Loc.Token("vdw_bait_" + bait.Id + "_desc", bait.Description);
                    item.ItemDrop.m_itemData.m_shared.m_weight = 0.1f;
                    ItemManager.Instance.AddItem(item);
                    BaitItems[bait.Id] = item.ItemPrefab;
                    if (CustomModels.ApplyToPrefab(item.ItemPrefab, BaitModelKey(bait.Id)))
                        GroundPose.FitCollider(item.ItemPrefab);
                    BaitByItemName[itemName] = bait;
                }
                catch (Exception ex)
                {
                    Plugin.Log.LogError($"Failed to register bait '{bait.Id}': {ex.Message}");
                }
            }
        }

        /// <summary>
        /// A vanilla fish is used as it is: its prefab swims and is shown on the hook, landing it gives its vanilla
        /// item (so vanilla cooking, recipes and food all apply), and its name comes from the game. Nothing about
        /// the vanilla prefab is changed except allowing the size classes as quality.
        /// </summary>
        private static void RegisterVanillaFish(FishDefinition fish)
        {
            var prefab = PrefabManager.Instance.GetPrefab(fish.VanillaPrefab);
            if (prefab == null || prefab.GetComponent<global::Fish>() == null)
            {
                Plugin.Log.LogWarning($"Fish '{fish.Id}': vanilla fish '{fish.VanillaPrefab}' not found; it can't be caught.");
                return;
            }

            FishItems[fish.Id] = prefab;
            FishIdByPrefab[prefab.name] = fish.Id;

            var drop = DropFor(fish);
            if (drop != null)
            {
                var shared = drop.m_itemData.m_shared;
                shared.m_maxQuality = Math.Max(shared.m_maxQuality, FishSize.MaxClass);
                if (Localization.instance != null) fish.Name = Localization.instance.Localize(shared.m_name);
            }

            // It takes Deep Waters bait (PreferredBaits in Fish.json); its vanilla baits are taken out of the game.
            foreach (var setting in prefab.GetComponent<global::Fish>().m_baits)
                if (setting?.m_bait != null) VanillaFishingGear.Add(setting.m_bait.name);
        }

        /// <summary>Vanilla fishing items Deep Waters replaces: the vanilla rod and every vanilla fishing bait.</summary>
        private static readonly HashSet<string> VanillaFishingGear = new() { "FishingRod" };

        private static bool IsVanillaFishingGear(GameObject? prefab) =>
            prefab != null && (VanillaFishingGear.Contains(prefab.name) || prefab.name.StartsWith("FishingBait"));

        /// <summary>
        /// Takes the vanilla rod and baits out of the game: no trader sells them and they can't be crafted.
        /// Traders are cleaned now; recipes each time the ObjectDB is (re)built.
        /// </summary>
        private static void RemoveVanillaFishingGear()
        {
            foreach (var name in new[] { "Haldor", "Hildir", "BogWitch" })
            {
                var trader = PrefabManager.Instance.GetPrefab(name)?.GetComponent<Trader>();
                trader?.m_items.RemoveAll(t => t.m_prefab != null && IsVanillaFishingGear(t.m_prefab.gameObject));
            }

            ItemManager.OnItemsRegistered -= RemoveVanillaFishingRecipes;
            ItemManager.OnItemsRegistered += RemoveVanillaFishingRecipes;
            ItemManager.OnItemsRegistered -= AddFishToRawFishRecipe;
            ItemManager.OnItemsRegistered += AddFishToRawFishRecipe;
        }

        /// <summary>
        /// Vanilla makes Raw fish (for Fish Wraps, Fish Soup and the rest) from any one caught fish at the food
        /// preparation table, more from a fish of higher quality. Deep Waters fish join that list, so they go into
        /// vanilla's fish dishes too; their size class is their quality, so bigger catches give more.
        /// </summary>
        private static void AddFishToRawFishRecipe()
        {
            var recipe = ObjectDB.instance?.m_recipes.FirstOrDefault(r => r != null && r.m_item != null && r.m_item.gameObject.name == "FishRaw");
            if (recipe == null)
            {
                Plugin.Log.LogWarning("Raw fish recipe not found; Deep Waters fish can't be made into Raw fish.");
                return;
            }
            var have = new HashSet<string>(recipe.m_resources.Where(r => r?.m_resItem != null).Select(r => r.m_resItem.gameObject.name));
            var add = new List<Piece.Requirement>();
            foreach (var fish in Fish.Values)
            {
                if (fish.IsVanilla || !string.IsNullOrWhiteSpace(fish.CatchBait)) continue;   // vanilla's own / bait, not food
                if (!FishItems.TryGetValue(fish.Id, out var prefab) || prefab == null || have.Contains(prefab.name)) continue;
                var drop = prefab.GetComponent<ItemDrop>();
                if (drop == null) continue;
                add.Add(new Piece.Requirement { m_resItem = drop, m_amount = 1, m_amountPerLevel = 1, m_recover = true });
            }
            if (add.Count == 0) return;
            recipe.m_resources = recipe.m_resources.Concat(add).ToArray();
            Plugin.Log.LogDebug($"Raw fish: {add.Count} Deep Waters fish can be made into Raw fish at the preparation table.");
        }

        private static void RemoveVanillaFishingRecipes()
        {
            ObjectDB.instance?.m_recipes.RemoveAll(r => r != null && r.m_item != null && IsVanillaFishingGear(r.m_item.gameObject));
        }

        /// <summary>The swimming creature for each baitfish (by fish id), spawned in the world in schools (FishSpawns).</summary>
        public static readonly Dictionary<string, GameObject> SwimmingBaitfish = new();

        /// <summary>
        /// A baitfish swimming in the world: vanilla's swimming perch with the bait's own model, and no item of its own,
        /// so one picked up when it flops onto land gives its bait (as many as a catch does).
        /// </summary>
        private static void RegisterSwimmingBaitfish(FishDefinition fish, GameObject baitPrefab)
        {
            string name = "VDW_Swim_" + fish.Id;
            var swim = PrefabManager.Instance.CreateClonedPrefab(name, "Fish1");
            if (swim == null) return;
            var item = swim.GetComponent<ItemDrop>();
            if (item != null) UnityEngine.Object.DestroyImmediate(item);
            var f = swim.GetComponent<global::Fish>();
            if (f != null)
            {
                f.m_name = baitPrefab.GetComponent<ItemDrop>()?.m_itemData.m_shared.m_name ?? fish.Name;
                f.m_pickupItem = baitPrefab;
                f.m_pickupItemStackSize = Mathf.Max(1, fish.CatchAmount);
            }
            CustomModels.ApplyToPrefab(swim, BaitModelKey(fish.CatchBait));
            PrefabManager.Instance.AddPrefab(swim);
            SwimmingBaitfish[fish.Id] = swim;
            FishIdByPrefab[name] = fish.Id;
        }

        private static void RegisterFish()
        {
            foreach (var fish in Fish.Values)
            {
                try
                {
                    // Baitfish land as bait, so they have no fish item of their own; the bait item doubles as
                    // their swimming and hooked visual.
                    if (!string.IsNullOrWhiteSpace(fish.CatchBait))
                    {
                        if (BaitItems.TryGetValue(fish.CatchBait, out var baitPrefab))
                        {
                            FishItems[fish.Id] = baitPrefab;
                            RegisterSwimmingBaitfish(fish, baitPrefab);
                        }
                        else Plugin.Log.LogWarning($"Fish '{fish.Id}': CatchBait '{fish.CatchBait}' isn't a bait id.");
                        continue;
                    }

                    if (fish.IsVanilla)
                    {
                        RegisterVanillaFish(fish);
                        continue;
                    }
                    FishIdByPrefab["VDW_Fish_" + fish.Id] = fish.Id;

                    string basePrefab = ResolveBasePrefab(fish.VanillaFallbackPrefab, "Fish1");
                    var item = new CustomItem("VDW_Fish_" + fish.Id, basePrefab);
                    if (item.ItemPrefab == null || item.ItemDrop == null)
                    {
                        Plugin.Log.LogWarning($"Could not create fish '{fish.Id}' from '{basePrefab}'.");
                        continue;
                    }

                    item.ItemDrop.m_itemData.m_shared.m_name = Loc.Token("vdw_fish_" + fish.Id, string.IsNullOrWhiteSpace(fish.Name) ? fish.Id : fish.Name);
                    item.ItemDrop.m_itemData.m_shared.m_description = Loc.Token("vdw_fish_" + fish.Id + "_desc", fish.Description);
                    item.ItemDrop.m_itemData.m_shared.m_maxQuality = FishSize.MaxClass; // size classes (see FishSize)
                    ItemManager.Instance.AddItem(item);
                    FishItems[fish.Id] = item.ItemPrefab;
                    if (CustomModels.ApplyToPrefab(item.ItemPrefab, "fish_" + fish.Id))
                        GroundPose.FitCollider(item.ItemPrefab);
                    GroundPose.PrepareFishPrefab(item.ItemPrefab);
                    VanillaFx.AttachToFish(item.ItemPrefab, fish.Id);          // legendary and boss fish only
                    Cooking.PriceRawFish(fish, item.ItemPrefab);

                    try { Cooking.RegisterCookedFish(fish, item.ItemPrefab); }
                    catch (Exception ex) { Plugin.Log.LogError($"Failed to register cooked item for '{fish.Id}': {ex.Message}"); }
                }
                catch (Exception ex)
                {
                    Plugin.Log.LogError($"Failed to register fish '{fish.Id}': {ex.Message}");
                }
            }
        }
    }
}
