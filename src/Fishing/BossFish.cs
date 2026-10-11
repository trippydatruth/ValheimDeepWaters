using HarmonyLib;
using Jotunn.Entities;
using Jotunn.Managers;
using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>One of the six boss fish: how it's summoned, how it's announced, and what it leaves behind.</summary>
    internal sealed class BossInfo
    {
        public string FishId = "";
        public string Title = "";          // shown under its name on the boss bar
        public string BossPrefab = "";     // the boss it's named after: its music plays during the fight
        public string LureId = "";         // the bait that summons it
        public string Omen = "";           // the big message when it comes
        public string Hint = "";           // where and when, shown if the lure is cast in the wrong place
        public string MaterialName = "", MaterialBase = "", MaterialDescription = "";
        public Func<Vector3, bool, float, Heightmap.Biome, bool> Conditions = (_, _, _, _) => true;
        public string? Music;              // resolved from the boss's own event the first time it's needed
        public string[] Weathers = { "ThunderStorm" };   // the weather it brings: the first of these the world has (BossWeather)
        public string? Environment;        // which one that is, found the first time it's needed
    }

    /// <summary>
    /// The six legendary fish named after Valheim's bosses are boss fights. Each is summoned with a lure carved
    /// from that boss's trophy, cast in the right water at the right time; an omen plays, then it strikes. The
    /// fight gets a boss bar (the fish's stamina), the boss's music and phase messages, and landing it drops a
    /// trophy the first time and a crafting material every time, and tells the whole server. The other three
    /// legendaries are mini-bosses: the same harder fight but none of the fanfare, and a trophy the first time.
    /// </summary>
    internal static class BossFish
    {
        public static readonly List<BossInfo> All = new()
        {
            new BossInfo
            {
                FishId = "eikthyr_elver", Title = "Stormcaller of the Rivers", BossPrefab = "Eikthyr", LureId = "lure_antler",
                Omen = "Lightning stirs beneath the river...", Hint = "It hunts the rivers of the Meadows while thunder rolls.",
                MaterialName = "Storm Barbel", MaterialBase = "HardAntler",
                Weathers = new[] { "Eikthyr", "ThunderStorm" },
                Conditions = (spot, ocean, depth, biome) => !ocean && biome == Heightmap.Biome.Meadows && Weather("Thunder"),
            },
            new BossInfo
            {
                FishId = "elder_bass", Title = "Ancient of the Black Lakes", BossPrefab = "gd_king", LureId = "lure_root",
                Omen = "The roots beneath the lake are moving...", Hint = "It rises in the lakes of the Black Forest, at night.",
                MaterialName = "Elder Scale", MaterialBase = "Root",
                Weathers = new[] { "GDKing", "DeepForest Mist", "Misty" },
                Conditions = (spot, ocean, depth, biome) => !ocean && biome == Heightmap.Biome.BlackForest && EnvMan.IsNight(),
            },
            new BossInfo
            {
                FishId = "bonemass_catfish", Title = "Rot of the Mire", BossPrefab = "Bonemass", LureId = "lure_ooze",
                Omen = "Something foul rises from the mire...", Hint = "It stirs in the waters of the Swamp when the rain falls.",
                MaterialName = "Mire Whisker", MaterialBase = "Ooze",
                Weathers = new[] { "Bonemass", "SwampRain", "Rain" },
                Conditions = (spot, ocean, depth, biome) => !ocean && biome == Heightmap.Biome.Swamp && EnvMan.IsWet(),
            },
            new BossInfo
            {
                FishId = "moder_scale", Title = "Wyrm of the Deep", BossPrefab = "Dragon", LureId = "lure_wyrm",
                Omen = "The cold deep stirs...", Hint = "It hunts the cold seas off the Deep North, in storms and snow.",
                MaterialName = "Frostwyrm Scale", MaterialBase = "FreezeGland",
                Weathers = new[] { "Moder", "SnowStorm", "Twilight_SnowStorm" },
                Conditions = (spot, ocean, depth, biome) => ocean && Near(spot, Heightmap.Biome.DeepNorth) && Weather("Snow", "Storm", "Thunder"),
            },
            new BossInfo
            {
                FishId = "yagluthgill", Title = "Ember of the Drowned King", BossPrefab = "GoblinKing", LureId = "lure_ember",
                Omen = "Embers glow beneath the waves...", Hint = "It rises in the deep sea off the Plains, at night.",
                MaterialName = "Ember Gill", MaterialBase = "SurtlingCore",
                Weathers = new[] { "GoblinKing", "Ashrain", "ThunderStorm" },
                Conditions = (spot, ocean, depth, biome) => ocean && depth >= DeepWater && Near(spot, Heightmap.Biome.Plains) && EnvMan.IsNight(),
            },
            new BossInfo
            {
                FishId = "queen_eel", Title = "Mother of the Abyss", BossPrefab = "SeekerQueen", LureId = "lure_chitin",
                Omen = "Something vast uncoils in the deep...", Hint = "It hunts the deep sea off the Mistlands.",
                MaterialName = "Queen's Fang", MaterialBase = "Carapace",
                Weathers = new[] { "Queen", "Mistlands_thunder", "Mistlands_rain" },
                Conditions = (spot, ocean, depth, biome) => ocean && depth >= DeepWater && Near(spot, Heightmap.Biome.Mistlands),
            },
        };

        private const float DeepWater = 15f;        // the same depth that counts as deep ocean for fishing
        private const float NearRadius = 300f;      // how far off the coast a biome still counts as "off" it
        private const string TrophiesKey = "vdw_trophies";
        private const string RelicsKey = "vdw_boss_relics";

        /// <summary>The relics only bosses leave behind (never found in other fish): Pearl, Scale, Golden Hook.</summary>
        private static readonly string[] BossRelics = { "VDW_Buff_relic_pearl", "VDW_Buff_relic_scale", "VDW_Hook_golden" };
        private const float BossRelicChance = 0.25f;

        public static bool IsBossRelic(string prefabName) => System.Array.IndexOf(BossRelics, prefabName) >= 0;

        public static readonly Dictionary<string, GameObject> Trophies = new();   // by fish id, every legendary
        public static readonly Dictionary<string, GameObject> Materials = new();  // by fish id, bosses only

        public static BossInfo? ForFish(string fishId) => All.FirstOrDefault(b => b.FishId == fishId);
        public static BossInfo? ForLure(string baitId) => All.FirstOrDefault(b => b.LureId == baitId);
        public static bool IsBoss(string fishId) => All.Any(b => b.FishId == fishId);

        public static string Phrase(string name) => name.StartsWith("The ", StringComparison.OrdinalIgnoreCase) ? name : "The " + name;

        // ------------------------------------------------------------------ conditions

        private static bool Weather(params string[] keys)
        {
            string env = EnvMan.instance?.GetCurrentEnvironment()?.m_name ?? "";
            return keys.Any(k => env.IndexOf(k, StringComparison.OrdinalIgnoreCase) >= 0);
        }

        /// <summary>The spot, or somewhere within a few hundred metres of it, is in this biome.</summary>
        private static bool Near(Vector3 spot, Heightmap.Biome biome)
        {
            var world = WorldGenerator.instance;
            if (world == null) return false;
            if (world.GetBiome(spot) == biome) return true;
            for (int ring = 1; ring <= 2; ring++)
                for (int i = 0; i < 12; i++)
                {
                    float a = i / 12f * Mathf.PI * 2f, r = NearRadius * ring / 2f;
                    if (world.GetBiome(spot + new Vector3(Mathf.Cos(a) * r, 0f, Mathf.Sin(a) * r)) == biome) return true;
                }
            return false;
        }

        // ------------------------------------------------------------------ items

        /// <summary>Trophies for every legendary and the bosses' materials. Call after the fish are registered.</summary>
        public static void Register()
        {
            foreach (var fish in ContentRegistry.Fish.Values.Where(f => f.Legendary && !f.IsVanilla))
            {
                try { RegisterTrophy(fish); }
                catch (Exception ex) { Plugin.Log.LogError($"Trophy for '{fish.Id}' failed: {ex.Message}"); }
            }
            foreach (var boss in All)
            {
                try { RegisterMaterial(boss); }
                catch (Exception ex) { Plugin.Log.LogError($"Boss material for '{boss.FishId}' failed: {ex.Message}"); }
            }
        }

        private static void RegisterTrophy(FishDefinition fish)
        {
            if (!ContentRegistry.FishItems.TryGetValue(fish.Id, out var fishPrefab)) return;
            var prefab = PrefabManager.Instance.CreateClonedPrefab("VDW_Trophy_" + fish.Id, fishPrefab);
            // A trophy shouldn't swim off when dropped in water.
            var swim = prefab.GetComponent<global::Fish>();
            if (swim != null) UnityEngine.Object.DestroyImmediate(swim);

            var shared = prefab.GetComponent<ItemDrop>().m_itemData.m_shared;
            shared.m_name = Loc.Token("vdw_trophy_" + fish.Id, fish.Name + " Trophy");
            shared.m_description = Loc.Token("vdw_trophy_" + fish.Id + "_desc",
                IsBoss(fish.Id) ? $"Proof you beat the {fish.Name}. Hang it on a Trophy Mount." : $"Proof you landed the {fish.Name}. Hang it on a Trophy Mount.");
            shared.m_itemType = ItemDrop.ItemData.ItemType.Trophy;
            shared.m_maxStackSize = 20;
            shared.m_maxQuality = 1;
            shared.m_weight = 2f;
            shared.m_value = 0;
            shared.m_consumeStatusEffect = null;
            shared.m_food = shared.m_foodStamina = shared.m_foodEitr = 0f;

            ItemManager.Instance.AddItem(new CustomItem(prefab, fixReference: false));
            Trophies[fish.Id] = prefab;
        }

        private static void RegisterMaterial(BossInfo boss)
        {
            var fish = ContentRegistry.Fish.TryGetValue(boss.FishId, out var f) ? f : null;
            if (fish == null || PrefabManager.Instance.GetPrefab(boss.MaterialBase) == null) return;
            var item = new CustomItem("VDW_BossMat_" + boss.FishId, boss.MaterialBase);
            var shared = item.ItemDrop.m_itemData.m_shared;
            shared.m_name = Loc.Token("vdw_bossmat_" + boss.FishId, boss.MaterialName);
            shared.m_description = Loc.Token("vdw_bossmat_" + boss.FishId + "_desc",
                $"Taken from the {fish.Name}. One from each of the six great fish strings the Leviathan Rod.");
            shared.m_itemType = ItemDrop.ItemData.ItemType.Material;
            shared.m_maxStackSize = 20;
            shared.m_weight = 1f;
            shared.m_consumeStatusEffect = null;
            shared.m_food = shared.m_foodStamina = shared.m_foodEitr = 0f;
            CustomModels.ApplyToPrefab(item.ItemPrefab, "bossmat_" + boss.FishId);
            ItemManager.Instance.AddItem(item);
            Materials[boss.FishId] = item.ItemPrefab;
        }

        // ------------------------------------------------------------------ landing one

        /// <summary>A legendary was landed: its trophy the first time, a boss's material every time, and the news.</summary>
        public static string OnLanded(Player player, FishDefinition fish, Vector3 dropPos)
        {
            string text = "";
            var boss = ForFish(fish.Id);

            if (Trophies.TryGetValue(fish.Id, out var trophy) && ClaimFirst(player, fish.Id))
            {
                Drop(player, trophy, 1, dropPos);
                text += $"\n+ {Loc.Text(trophy.GetComponent<ItemDrop>().m_itemData.m_shared.m_name)}";
            }

            if (boss == null) return text;

            if (Materials.TryGetValue(fish.Id, out var mat))
            {
                int n = UnityEngine.Random.value < 0.5f ? 2 : 1;
                Drop(player, mat, n, dropPos);
                text += $"\n+ {n} {Loc.Text(mat.GetComponent<ItemDrop>().m_itemData.m_shared.m_name)}";
            }

            // Sometimes one of the boss relics, one the player doesn't have yet if there is one.
            if (UnityEngine.Random.value < BossRelicChance && PickRelic(player) is GameObject relic)
            {
                Drop(player, relic, 1, dropPos);
                text += $"\nSomething glints in its belly... {Loc.Text(relic.GetComponent<ItemDrop>().m_itemData.m_shared.m_name)}!";
            }

            MessageHud.instance?.MessageAll(MessageHud.MessageType.Center, $"{player.GetPlayerName()} has landed the {fish.Name}!");
            return text;
        }

        private static void Drop(Player player, GameObject prefab, int amount, Vector3 pos)
        {
            var drop = prefab.GetComponent<ItemDrop>();
            if (drop != null) Drops.Give(player, drop, amount, pos + Vector3.up * 0.4f);
        }

        private static GameObject? PickRelic(Player player)
        {
            player.m_customData.TryGetValue(RelicsKey, out var raw);
            var got = new HashSet<string>((raw ?? "").Split(new[] { ',' }, StringSplitOptions.RemoveEmptyEntries));
            var available = BossRelics.Where(p => ZNetScene.instance?.GetPrefab(p) != null).ToList();
            if (available.Count == 0) return null;
            var fresh = available.Where(p => !got.Contains(p)).ToList();
            string pick = (fresh.Count > 0 ? fresh : available)[UnityEngine.Random.Range(0, fresh.Count > 0 ? fresh.Count : available.Count)];
            got.Add(pick);
            player.m_customData[RelicsKey] = string.Join(",", got);
            return ZNetScene.instance!.GetPrefab(pick);
        }

        /// <summary>True the first time this player lands this legendary.</summary>
        private static bool ClaimFirst(Player player, string fishId)
        {
            player.m_customData.TryGetValue(TrophiesKey, out var raw);
            var got = new HashSet<string>((raw ?? "").Split(new[] { ',' }, StringSplitOptions.RemoveEmptyEntries));
            if (!got.Add(fishId)) return false;
            player.m_customData[TrophiesKey] = string.Join(",", got);
            return true;
        }

        // ------------------------------------------------------------------ music

        /// <summary>The music of the boss this fish is named after, from the boss's own event.</summary>
        public static string? MusicFor(BossInfo boss)
        {
            if (boss.Music != null) return boss.Music.Length > 0 ? boss.Music : null;
            var character = PrefabManager.Instance.GetPrefab(boss.BossPrefab)?.GetComponent<Character>();
            boss.Music = character?.m_bossEvent ?? "";
            return boss.Music.Length > 0 ? boss.Music : null;
        }

        /// <summary>
        /// Boss music for a boss fish, through the same override vanilla uses for its bosses: from the omen on the water,
        /// through the strike, to the end of the fight (the track loops on its own), for everyone near the encounter. It
        /// plays at Valheim's music volume.
        /// </summary>
        [HarmonyPatch(typeof(RandEventSystem), nameof(RandEventSystem.GetMusicOverride))]
        private static class MusicPatch
        {
            private static string? _playing;

            private static void Postfix(ref string __result)
            {
                // the nearest boss encounter, the local angler's or anyone else's nearby (BossWeather shares them)
                var near = BossWeather.Near();
                string? boss = __result == null && near != null ? MusicFor(near) : null;
                if (boss != null) __result = boss;
                if (boss != _playing)
                {
                    Plugin.Log.LogInfo(boss != null
                        ? $"Boss music: {boss} ({near!.FishId})."
                        : $"Boss music stopped: {(near == null ? "no boss encounter near" : "another event's music took over")}.");
                    _playing = boss;
                }
            }
        }
    }

    /// <summary>The dark swirl that spreads on the water while a boss circles the float.</summary>
    internal sealed class OmenSwirl : MonoBehaviour
    {
        private static Material? _material;
        private float _born;

        public static GameObject Create(Vector3 pos)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Quad);
            go.name = "VDW_OmenSwirl";
            DestroyImmediate(go.GetComponent<Collider>());
            go.transform.position = pos + Vector3.up * 0.03f;
            go.transform.rotation = Quaternion.Euler(90f, 0f, 0f);
            go.transform.localScale = Vector3.one * 0.5f;
            var renderer = go.GetComponent<Renderer>();
            renderer.sharedMaterial = _material ??= MakeMaterial();
            renderer.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            go.AddComponent<OmenSwirl>()._born = Time.time;
            return go;
        }

        private void Update()
        {
            float age = Time.time - _born;
            float size = Mathf.Lerp(0.5f, 7f, Mathf.SmoothStep(0f, 1f, age / 3f)) * (1f + 0.04f * Mathf.Sin(age * 3f));
            transform.localScale = new Vector3(size, size, 1f);
            transform.Rotate(0f, 0f, (40f + age * 12f) * Time.deltaTime, Space.Self); // winds tighter as it builds
        }

        /// <summary>A dark spiral fading out toward the rim.</summary>
        private static Material MakeMaterial()
        {
            const int n = 128;
            var tex = new Texture2D(n, n, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp };
            var px = new Color32[n * n];
            for (int y = 0; y < n; y++)
                for (int x = 0; x < n; x++)
                {
                    float dx = (x + 0.5f) / n * 2f - 1f, dy = (y + 0.5f) / n * 2f - 1f;
                    float r = Mathf.Sqrt(dx * dx + dy * dy), a = Mathf.Atan2(dy, dx);
                    float arms = 0.5f + 0.5f * Mathf.Sin(a * 3f + r * 14f);
                    float alpha = Mathf.Clamp01(1f - r) * (0.35f + 0.45f * arms) * Mathf.Clamp01(r * 4f + 0.4f);
                    px[y * n + x] = new Color(0.01f, 0.05f, 0.07f, alpha);
                }
            tex.SetPixels32(px);
            tex.Apply();
            var shader = Shader.Find("Sprites/Default") ?? Shader.Find("Standard");
            return new Material(shader) { mainTexture = tex };
        }
    }
}
