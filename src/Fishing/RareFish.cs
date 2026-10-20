using HarmonyLib;
using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// Rare variants (roadmap #23): any catch of an ordinary species can come up golden (about 1 in 300) or albino (about
    /// 1 in 150). It's the same fish item with its variant set - Valheim's own per-item variant, which picks the item's
    /// icon - so each fish carries two extra icons, its own icon tinted gold and pale, and its model is tinted to match
    /// on the ground, on a Trophy Mount and on the line. Variants never stack with ordinary fish, sell for more, earn rank
    /// points, and the catch log keeps track of which you've caught.
    /// </summary>
    internal static class RareFish
    {
        public const int Normal = 0, Golden = 1, Albino = 2;
        private const float GoldenChance = 1f / 300f, AlbinoChance = 1f / 150f;
        public const int GoldenPoints = 10, AlbinoPoints = 5;
        public const float GoldenPrice = 5f, AlbinoPrice = 3f;          // Haldor's multipliers
        public const float HildirGolden = 6f, HildirAlbino = 4f;        // Hildir collects them

        public static string Name(int variant) => variant == Golden ? "Golden" : variant == Albino ? "Albino" : "";

        /// <summary>Ordinary species only: no legendaries or bosses (they're rare already) and no baitfish.</summary>
        public static bool Eligible(FishDefinition f) =>
            !f.Legendary && !BossFish.IsBoss(f.Id) && string.IsNullOrWhiteSpace(f.CatchBait);

        /// <summary>Rolled when a fish takes the bait, so the right colours show on the line during the fight.</summary>
        public static int Roll(FishDefinition f)
        {
            if (!Eligible(f)) return Normal;
            float r = UnityEngine.Random.value;
            return r < GoldenChance ? Golden : r < GoldenChance + AlbinoChance ? Albino : Normal;
        }

        public static bool IsFishItem(ItemDrop.ItemData? item) =>
            item?.m_dropPrefab != null && ContentRegistry.FishIdByPrefab.ContainsKey(item.m_dropPrefab.name);

        public static FishDefinition? FishOf(ItemDrop.ItemData? item) =>
            item?.m_dropPrefab != null && ContentRegistry.FishIdByPrefab.TryGetValue(item.m_dropPrefab.name, out var id)
            && ContentRegistry.Fish.TryGetValue(id, out var f) ? f : null;

        // ------------------------------------------------------------------ icons

        /// <summary>After the fish items exist: each eligible fish gets its own icon tinted gold and pale as variants 1 and 2.</summary>
        public static void RegisterIcons()
        {
            int done = 0;
            foreach (var f in ContentRegistry.Fish.Values.Where(Eligible))
            {
                if (!ContentRegistry.FishItems.TryGetValue(f.Id, out var prefab)) continue;
                var shared = prefab.GetComponent<ItemDrop>()?.m_itemData.m_shared;
                if (shared == null || shared.m_icons == null || shared.m_icons.Length == 0 || shared.m_icons[0] == null) continue;
                try
                {
                    var baseIcon = shared.m_icons[0];
                    shared.m_icons = new[] { baseIcon, TintSprite(baseIcon, Golden), TintSprite(baseIcon, Albino) };
                    // Valheim resets an item's variant to 0 when it's past m_variants (ItemDrop.EnsureValid, as it spawns):
                    // without this a golden fish turned ordinary the moment it was dropped. Fish aren't crafted, so the
                    // crafting menu's variant picker never shows for them.
                    shared.m_variants = Math.Max(shared.m_variants, 3);
                    done++;
                }
                catch (Exception ex) { Plugin.Log.LogWarning($"Rare fish: couldn't tint the {f.Name} icon ({ex.Message})."); }
            }
            Plugin.Log.LogInfo($"Rare fish: golden and albino icons for {done} species.");
        }

        /// <summary>A tinted copy of an icon (read back through a render texture, as game icons aren't readable).</summary>
        private static Sprite TintSprite(Sprite src, int variant)
        {
            var tex = src.texture;
            var r = src.textureRect;
            var rt = RenderTexture.GetTemporary(tex.width, tex.height, 0, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB);
            var prev = RenderTexture.active;
            Graphics.Blit(tex, rt);
            RenderTexture.active = rt;
            var copy = new Texture2D((int)r.width, (int)r.height, TextureFormat.RGBA32, false);
            copy.ReadPixels(new Rect(r.x, r.y, r.width, r.height), 0, 0);
            RenderTexture.active = prev;
            RenderTexture.ReleaseTemporary(rt);

            var px = copy.GetPixels();
            for (int i = 0; i < px.Length; i++)
            {
                var c = px[i];
                if (c.a <= 0.01f) continue;
                float lum = c.r * 0.3f + c.g * 0.59f + c.b * 0.11f;
                Color t;
                if (variant == Golden)
                {
                    // dark gold in the shadows to bright gold in the light, a touch of shine on the brightest
                    t = Color.Lerp(new Color(0.34f, 0.18f, 0.02f), new Color(0.97f, 0.68f, 0.2f), Mathf.Pow(lum, 0.85f));
                    if (lum > 0.8f) t = Color.Lerp(t, new Color(1f, 0.86f, 0.5f), (lum - 0.8f) * 2.5f);
                }
                else
                {
                    // pale and pinkish, the darkest bits (the eye) a soft red
                    t = lum < 0.12f ? new Color(0.8f, 0.32f, 0.38f) : Color.Lerp(new Color(0.86f, 0.78f, 0.78f), new Color(1f, 0.97f, 0.96f), lum);
                }
                t.a = c.a;
                px[i] = t;
            }
            copy.SetPixels(px);
            copy.Apply();
            copy.name = src.name + "_" + Name(variant).ToLowerInvariant();
            return Sprite.Create(copy, new Rect(0, 0, copy.width, copy.height), new Vector2(0.5f, 0.5f), src.pixelsPerUnit);
        }

        // ------------------------------------------------------------------ models

        private static readonly Dictionary<(Material, int), Material> TintCache = new Dictionary<(Material, int), Material>();
        // a deep, warm gold: it washed out to cream in bright daylight when lighter
        private static readonly Color GoldColor = new Color(0.93f, 0.62f, 0.16f), PaleColor = new Color(0.95f, 0.88f, 0.88f);

        /// <summary>
        /// A fish's material in the variant's colours: gold (metallic, a faint glow, as the trophy plaques) or pale. Its
        /// painted skin gives way to the plain colour; its normal map stays, so the scales still show.
        /// </summary>
        private static Material Tinted(Material own, int variant)
        {
            if (TintCache.TryGetValue((own, variant), out var m) && m != null) return m;
            // Valheim's own fish (perch, pike...) use its creature shader, which has no plain colour to set: those get a
            // Standard material instead, keeping their normal map. The mod's own fish models are Standard already.
            var standard = StandardShader();
            if (standard != null && own.shader != standard && own.shader.name != "Standard")
            {
                m = new Material(standard) { name = own.name + "_" + Name(variant).ToLowerInvariant() };
                foreach (var bump in new[] { "_BumpMap", "_NormalMap" })
                    if (own.HasProperty(bump) && own.GetTexture(bump) != null) { m.SetTexture("_BumpMap", own.GetTexture(bump)); m.EnableKeyword("_NORMALMAP"); break; }
            }
            else m = new Material(own) { name = own.name + "_" + Name(variant).ToLowerInvariant() };
            if (m.HasProperty("_MainTex")) m.SetTexture("_MainTex", null);
            if (m.HasProperty("_Color")) m.SetColor("_Color", variant == Golden ? GoldColor : PaleColor);
            if (m.HasProperty("_MetallicGlossMap")) { m.SetTexture("_MetallicGlossMap", null); m.DisableKeyword("_METALLICGLOSSMAP"); }
            if (variant == Golden)
            {
                if (m.HasProperty("_Metallic")) m.SetFloat("_Metallic", 0.65f);
                if (m.HasProperty("_Glossiness")) m.SetFloat("_Glossiness", 0.72f);
                if (m.HasProperty("_EmissionColor")) { m.SetTexture("_EmissionMap", null); m.SetColor("_EmissionColor", GoldColor * 0.1f); m.EnableKeyword("_EMISSION"); }
            }
            else
            {
                if (m.HasProperty("_Metallic")) m.SetFloat("_Metallic", 0f);
                if (m.HasProperty("_Glossiness")) m.SetFloat("_Glossiness", 0.45f);
                if (m.HasProperty("_EmissionColor")) { m.SetColor("_EmissionColor", Color.black); m.DisableKeyword("_EMISSION"); }
            }
            TintCache[(own, variant)] = m;
            return m;
        }

        private static Shader? _standard;

        /// <summary>Unity's Standard shader: by name, else from one of the mod's own bundle materials (they all use it).</summary>
        private static Shader? StandardShader()
        {
            if (_standard != null) return _standard;
            _standard = Shader.Find("Standard");
            if (_standard == null && CustomModels.TryGetCustom("bobber", out _, out var mat) && mat != null) _standard = mat.shader;
            if (_standard == null) Plugin.Log.LogWarning("Rare fish: no Standard shader found; vanilla fish can't be tinted.");
            return _standard;
        }

        /// <summary>Tints every renderer under a fish model (a dropped fish, a mounted one, the one on the line).</summary>
        public static void TintModel(GameObject? go, int variant)
        {
            if (go == null || variant == Normal) return;
            foreach (var r in go.GetComponentsInChildren<Renderer>(true))
            {
                if (r is ParticleSystemRenderer) continue;
                r.sharedMaterials = r.sharedMaterials.Select(mat => mat == null ? mat : Tinted(mat, variant)).ToArray();
            }
        }

        [HarmonyPatch(typeof(ItemDrop), "Start")]
        private static class DroppedTint
        {
            private static void Postfix(ItemDrop __instance)
            {
                var item = __instance.m_itemData;
                if (item != null && item.m_variant != Normal && IsFishItem(item)) TintModel(__instance.gameObject, item.m_variant);
            }
        }

        private static readonly AccessTools.FieldRef<ItemStand, GameObject> VisualItem = AccessTools.FieldRefAccess<ItemStand, GameObject>("m_visualItem");
        private static readonly AccessTools.FieldRef<ItemStand, ItemDrop> VisualDrop = AccessTools.FieldRefAccess<ItemStand, ItemDrop>("m_visualItemDrop");

        [HarmonyPatch(typeof(ItemStand), "SetVisualItem")]
        private static class MountedTint
        {
            private static void Postfix(ItemStand __instance, int variant)
            {
                if (variant == Normal) return;
                var drop = VisualDrop(__instance);
                if (drop != null && IsFishItem(drop.m_itemData)) TintModel(VisualItem(__instance), variant);
            }
        }

        // ------------------------------------------------------------------ never stacking with ordinary fish

        [ThreadStatic] private static ItemDrop.ItemData? _adding;
        private static readonly AccessTools.FieldRef<Inventory, List<ItemDrop.ItemData>> InvItems = AccessTools.FieldRefAccess<Inventory, List<ItemDrop.ItemData>>("m_inventory");

        [HarmonyPatch(typeof(Inventory), nameof(Inventory.AddItem), typeof(ItemDrop.ItemData))]
        private static class AddingItem
        {
            private static void Prefix(ItemDrop.ItemData item) => _adding = item;
            private static void Finalizer() => _adding = null;
        }

        [HarmonyPatch(typeof(Inventory), nameof(Inventory.CanAddItem), typeof(ItemDrop.ItemData), typeof(int))]
        private static class CheckingItem
        {
            private static void Prefix(ItemDrop.ItemData item) => _adding = item;
            private static void Finalizer() => _adding = null;
        }

        /// <summary>A free stack for a fish is one of the same variant (Valheim only matches the name and quality).</summary>
        [HarmonyPatch(typeof(Inventory), "FindFreeStackItem")]
        private static class SameVariantStack
        {
            private static void Postfix(Inventory __instance, string name, int quality, float worldLevel, ref ItemDrop.ItemData? __result)
            {
                var adding = _adding;
                if (__result == null || adding == null || !IsFishItem(adding) || __result.m_variant == adding.m_variant) return;
                __result = InvItems(__instance).FirstOrDefault(i => i.m_shared.m_name == name && i.m_quality == quality && i.m_worldLevel == worldLevel
                                                                && i.m_variant == adding.m_variant && i.m_stack < i.m_shared.m_maxStackSize);
            }
        }

        /// <summary>Dragging one fish onto another only stacks them when they're the same variant.</summary>
        [HarmonyPatch(typeof(ItemDrop.ItemData), nameof(ItemDrop.ItemData.IsSameType))]
        private static class SameVariantType
        {
            private static void Postfix(ItemDrop.ItemData __instance, ItemDrop.ItemData other, ref bool __result)
            {
                if (__result && other != null && __instance.m_variant != other.m_variant && IsFishItem(__instance)) __result = false;
            }
        }

        /// <summary>Fish lying on the ground don't merge into one stack (a golden one would be swallowed by its plain neighbours).</summary>
        [HarmonyPatch(typeof(ItemDrop), "AutoStackItems")]
        private static class NoAutoStack
        {
            private static bool Prefix(ItemDrop __instance) => !IsFishItem(__instance.m_itemData);
        }

        // ------------------------------------------------------------------ the catch log's record

        private const string CaughtKey = "vdw_variants";   // "pike:1|2;perch:2"

        public static Dictionary<string, HashSet<int>> Caught(Player p)
        {
            var map = new Dictionary<string, HashSet<int>>();
            if (!p.m_customData.TryGetValue(CaughtKey, out var raw) || string.IsNullOrEmpty(raw)) return map;
            foreach (var part in raw.Split(new[] { ';' }, StringSplitOptions.RemoveEmptyEntries))
            {
                var kv = part.Split(':');
                if (kv.Length != 2) continue;
                var set = new HashSet<int>();
                foreach (var v in kv[1].Split('|')) if (int.TryParse(v, out var n)) set.Add(n);
                map[kv[0]] = set;
            }
            return map;
        }

        /// <summary>Notes a variant caught; true the first time for this species.</summary>
        public static bool Record(Player p, string fishId, int variant)
        {
            if (variant == Normal) return false;
            var map = Caught(p);
            if (!map.TryGetValue(fishId, out var set)) map[fishId] = set = new HashSet<int>();
            if (!set.Add(variant)) return false;
            p.m_customData[CaughtKey] = string.Join(";", map.Select(kv => kv.Key + ":" + string.Join("|", kv.Value)));
            return true;
        }

        public static int EligibleCount() => ContentRegistry.Fish.Values.Count(Eligible);
    }
}
