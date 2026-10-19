using HarmonyLib;
using Jotunn.Configs;
using Jotunn.Entities;
using Jotunn.Managers;
using System;
using System.Collections.Generic;
using System.Linq;
using TMPro;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// Species mastery: catch enough of one species and it gets easier for you - Bronze (10): it bites more readily,
    /// Silver (25): it fights weaker, Gold (50): it runs bigger and you can build its Gold Trophy Plaque with the hammer.
    /// Legendaries and boss fish count 1 / 3 / 5; baitfish only go to Bronze. Each tier is worth angler rank points.
    /// Counts come from the catch log, so nothing extra is saved.
    /// </summary>
    internal static class Mastery
    {
        public const int None = 0, Bronze = 1, Silver = 2, Gold = 3;
        public static readonly string[] TierNames = { "", "Bronze", "Silver", "Gold" };
        public static readonly int[] TierPoints = { 0, 10, 20, 40 };

        private const float BiteBoost = 1.25f, InterestBoost = 0.1f, FightCut = 0.9f, Heavier = 0.35f;

        public static bool IsBaitfish(FishDefinition f) => !string.IsNullOrWhiteSpace(f.CatchBait);
        private static bool Rare(FishDefinition f) => f.Legendary || BossFish.IsBoss(f.Id);

        /// <summary>The catches each tier needs for this species (baitfish stop at Bronze).</summary>
        public static int[] Thresholds(FishDefinition f) =>
            Rare(f) ? new[] { 0, 1, 3, 5 } : IsBaitfish(f) ? new[] { 0, 10 } : new[] { 0, 10, 25, 50 };

        public static int TierFor(FishDefinition f, int count)
        {
            var t = Thresholds(f);
            int tier = None;
            for (int i = 1; i < t.Length; i++) if (count >= t[i]) tier = i;
            return tier;
        }

        public static int Count(Player? p, string fishId) =>
            p != null && CatchLog.Load(p).TryGetValue(fishId, out var e) ? e.Count : 0;

        public static int Tier(Player? p, FishDefinition f) => p == null ? None : TierFor(f, Count(p, f.Id));

        /// <summary>The rank points every species' mastery tiers add up to.</summary>
        public static int RankPoints(Dictionary<string, CatchEntry> log)
        {
            int pts = 0;
            foreach (var kv in log)
                if (ContentRegistry.Fish.TryGetValue(kv.Key, out var f))
                    for (int i = 1; i <= TierFor(f, kv.Value.Count); i++) pts += TierPoints[i];
            return pts;
        }

        public static string PerkText(int tier) => tier switch
        {
            Bronze => "it bites more readily for you",
            Silver => "it fights weaker for you",
            Gold => "it runs bigger for you, and you can build its Gold Trophy Plaque",
            _ => ""
        };

        // ------------------------------------------------------------------ perks (for the local player)

        private static int LocalTier(FishDefinition f) => Tier(Player.m_localPlayer, f);

        /// <summary>Bronze: this species is likelier to be the fish that comes to your bait.</summary>
        public static float BiteFactor(FishDefinition f) => LocalTier(f) >= Bronze ? BiteBoost : 1f;

        /// <summary>Bronze: ...and likelier to take it.</summary>
        public static float InterestBonus(FishDefinition f) => LocalTier(f) >= Bronze ? InterestBoost : 0f;

        /// <summary>Silver: it pulls and lasts 10% less.</summary>
        public static float FightFactor(FishDefinition f) => LocalTier(f) >= Silver ? FightCut : 1f;

        /// <summary>Gold: the weight roll leans toward the top of its range.</summary>
        public static float HeavierBonus(FishDefinition f) => LocalTier(f) >= Gold ? Heavier : 0f;

        // ------------------------------------------------------------------ catching

        /// <summary>The catch message lines when this catch reached a new tier (and the unlock popup).</summary>
        public static string OnCatch(FishDefinition f, int countBefore, int countAfter)
        {
            int before = TierFor(f, countBefore), after = TierFor(f, countAfter);
            string text = "";
            for (int t = before + 1; t <= after; t++)
            {
                text += $"\n{f.Name} mastery: {TierNames[t]}! {char.ToUpper(PerkText(t)[0])}{PerkText(t).Substring(1)}.";
                var icon = ContentRegistry.DropFor(f)?.m_itemData.GetIcon();
                MessageHud.instance?.QueueUnlockMsg(icon, $"{f.Name} mastery: {TierNames[t]}", char.ToUpper(PerkText(t)[0]) + PerkText(t).Substring(1) + ".");
            }
            return text;
        }

        // ------------------------------------------------------------------ the Gold Trophy Plaques

        public static string PlaquePrefab(FishDefinition f) => "VDW_Plaque_" + f.Id;
        private static readonly Dictionary<string, FishDefinition> PlaqueFish = new Dictionary<string, FishDefinition>();

        /// <summary>
        /// One plaque per species that can reach Gold: a dark board with a gold rim and a brass nameplate (one shared
        /// model), with that species' own model mounted on it when it's placed. Built with the hammer, hidden until Gold.
        /// </summary>
        public static void RegisterPlaques()
        {
            if (PrefabManager.Instance.GetPrefab("itemstand") == null) { Plugin.Log.LogWarning("Plaques: vanilla 'itemstand' not found."); return; }
            foreach (var f in ContentRegistry.Fish.Values.Where(f => !IsBaitfish(f)).OrderBy(f => f.Name))
            {
                try { AddPlaque(f); }
                catch (Exception ex) { Plugin.Log.LogError($"Plaque '{f.Id}' failed: {ex.Message}"); }
            }
        }

        private static void AddPlaque(FishDefinition f)
        {
            bool boss = BossFish.IsBoss(f.Id);
            string name = Loc.Token("vdw_plaque_" + f.Id, f.Name + " Gold Plaque");
            var piece = new CustomPiece(PlaquePrefab(f), "itemstand", new PieceConfig
            {
                Name = name,
                Description = Loc.Token("vdw_plaque_" + f.Id + "_desc", $"A gilded plaque with a {f.Name} mounted on it, for mastering the species."),
                PieceTable = "Hammer",
                Category = "Furniture",
                CraftingStation = "piece_workbench",
                Requirements = boss
                    ? new[] { new RequirementConfig("FineWood", 10, 0, true), new RequirementConfig("Bronze", 3, 0, true), new RequirementConfig("Resin", 5, 0, true) }
                    : new[] { new RequirementConfig("FineWood", 4, 0, true), new RequirementConfig("Bronze", 1, 0, true), new RequirementConfig("Resin", 2, 0, true) }
            });
            var go = piece.PiecePrefab;
            foreach (var stand in go.GetComponentsInChildren<ItemStand>(true)) UnityEngine.Object.DestroyImmediate(stand);
            if (CustomModels.ApplyToPrefab(go, "piece_plaque"))
            {
                PieceDressing.Dress(go, woodOnly: true);     // its rim, studs, ring and nameplate are gilded like the fish
            }
            go.AddComponent<PlaqueFish>().FishId = f.Id;
            var icon = ContentRegistry.DropFor(f)?.m_itemData.GetIcon();
            if (icon != null) piece.Piece.m_icon = icon;
            PlaqueFish[go.name] = f;
            PieceManager.Instance.AddPiece(piece);
        }

        /// <summary>A plaque stays unknown (out of the hammer menu) until its species is at Gold.</summary>
        [HarmonyPatch(typeof(Player), nameof(Player.HaveRequirements), typeof(Piece), typeof(Player.RequirementMode))]
        private static class PlaqueLocked
        {
            private static bool Prefix(Player __instance, Piece piece, ref bool __result)
            {
                if (piece == null || !PlaqueFish.TryGetValue(Utils.GetPrefabName(piece.gameObject), out var f) || Tier(__instance, f) >= Gold) return true;
                __result = false;
                return false;
            }
        }
    }

    /// <summary>
    /// Mounts the species on a placed plaque (and its ghost): a gold-plated copy of the fish item's own model, turned
    /// side-on, its length across the board, scaled to fit and set just in front of it.
    /// </summary>
    internal sealed class PlaqueFish : MonoBehaviour
    {
        public string FishId = "";
        private const float Fill = 0.78f;
        private const float BossShown = 0.8f;   // a boss plaque shows its fish at 80% of the size it swims (a wall-sized board otherwise)
        private static readonly HashSet<string> FlatFish = new HashSet<string> { "halibut" };

        private void Start()
        {
            try { Mount(); }
            catch (Exception ex) { Plugin.Log.LogWarning($"Plaque fish '{FishId}': {ex.Message}"); }
        }

        private static bool ActiveChain(Transform t, Transform root)
        {
            for (var c = t; c != null; c = c.parent) { if (!c.gameObject.activeSelf) return false; if (c == root) break; }
            return true;
        }

        private void Mount()
        {
            if (!ContentRegistry.Fish.TryGetValue(FishId, out var fish)) return;
            var drop = ContentRegistry.DropFor(fish);
            var board = transform.Find("vdw_model");
            if (drop == null || board == null) return;

            // the board, in the plaque's space: its thin axis faces out of the wall, toward where it sits from the origin
            foreach (var r in board.GetComponentsInChildren<Renderer>(true))
                if (r.name != "vdw_wood" && r.name != "vdw_darkwood") r.sharedMaterials = r.sharedMaterials.Select(Gilded).ToArray();
            var bb = LocalBounds(board.GetComponentsInChildren<Renderer>(true), transform);
            if (bb.size == Vector3.zero) return;
            int outAxis = bb.size.x < bb.size.z ? 0 : 2;
            int across = outAxis == 0 ? 2 : 0;
            float outSign = Mathf.Sign(bb.center[outAxis]); if (outSign == 0f) outSign = 1f;

            // the fish: copies of the item's visible meshes (LOD0 only)
            var src = drop.transform;
            var lod0 = new HashSet<Renderer>();
            foreach (var lg in src.GetComponentsInChildren<LODGroup>(true))
            {
                var lods = lg.GetLODs();
                if (lods.Length > 0) foreach (var r in lods[0].renderers) if (r != null) lod0.Add(r);
            }
            bool InLaterLod(Renderer r) => src.GetComponentsInChildren<LODGroup>(true).Any(lg => lg.GetLODs().Skip(1).Any(l => l.renderers.Contains(r))) && !lod0.Contains(r);

            var holder = new GameObject("vdw_plaque_fish").transform;
            holder.SetParent(transform, false);
            var inner = new GameObject("fish").transform;
            inner.SetParent(holder, false);
            var copies = new List<Renderer>();
            // fish carry a still copy of their model under "attach" for item stands, besides the one on the ground: when
            // there is one, that copy alone (what the Trophy Mount shows), so the fish isn't mounted twice
            var attach = src.Find("attach");
            var standCopy = attach != null ? (attach.Find("attachobj") ?? attach) : null;
            var pool = standCopy != null && standCopy.GetComponentsInChildren<Renderer>(true).Any(r => !(r is ParticleSystemRenderer)) ? standCopy : src;
            foreach (var r in pool.GetComponentsInChildren<Renderer>(true))
            {
                // switched-off meshes are the ones the mod hid: under "attach" that's the vanilla fish the species' own
                // still model replaced, which would otherwise overlap it
                if (!r.enabled || !ActiveChain(r.transform, src) || InLaterLod(r) || r is ParticleSystemRenderer) continue;
                Mesh? mesh = r is SkinnedMeshRenderer smr ? smr.sharedMesh : r.GetComponent<MeshFilter>()?.sharedMesh;
                if (mesh == null) continue;
                var part = new GameObject(r.name);
                part.transform.SetParent(inner, false);
                var m = src.worldToLocalMatrix * r.transform.localToWorldMatrix;
                part.transform.localPosition = m.GetColumn(3);
                part.transform.localRotation = m.rotation;
                part.transform.localScale = m.lossyScale;
                part.AddComponent<MeshFilter>().sharedMesh = mesh;
                var mr = part.AddComponent<MeshRenderer>();
                mr.sharedMaterials = r.sharedMaterials.Select(Gilded).ToArray();
                copies.Add(mr);
            }
            if (copies.Count == 0) { Destroy(holder.gameObject); return; }

            // turn it side-on: its longest axis across the board, its "up" (the item's Y unless that's its length) up and
            // its side facing out. Flatfish lie on their side in the water, so theirs is the thinnest axis instead -
            // the wide, flat-headed bottom fish (catfish, sculpin, goby) would otherwise show their backs
            var fb = LocalBounds(copies, inner);
            var size = fb.size;
            int len = size.x >= size.y && size.x >= size.z ? 0 : size.y >= size.z ? 1 : 2;
            int flat, up;
            if (FlatFish.Contains(FishId))
            {
                flat = size.x <= size.y && size.x <= size.z ? 0 : size.y <= size.z ? 1 : 2;
                if (flat == len) flat = (len + 1) % 3;
                up = 3 - len - flat;
            }
            else
            {
                up = len != 1 ? 1 : (size.x >= size.z ? 0 : 2);
                flat = 3 - len - up;
            }
            Vector3 Axis(int i) => i == 0 ? Vector3.right : i == 1 ? Vector3.up : Vector3.forward;
            // inner: the fish's (flat, up) onto the holder's (Z, Y), so its length lies along X; holder: Z out of the
            // board, Y up - which leaves X (the length) across it
            inner.localRotation = Quaternion.Inverse(Quaternion.LookRotation(Axis(flat), Axis(up)));
            holder.localRotation = Quaternion.LookRotation(Axis(outAxis) * outSign, Vector3.up);

            // scale to fill the board's width - except a boss fish, mounted near true size (BossShown of it), with the
            // board and its collider grown to fit it - then centre it a little above the nameplate, just in front
            float boardW = bb.size[across], boardH = bb.size.y;
            float s = Mathf.Min(boardW * Fill / Mathf.Max(0.01f, size[len]), boardH * 0.62f / Mathf.Max(0.01f, size[up]));
            if (BossFish.IsBoss(FishId))
            {
                float trueSize = BossFish.ScaleFor(FishId) * BossShown;
                float grow = Mathf.Max(1f, trueSize / s);
                board.localScale *= grow;
                foreach (var box in GetComponents<BoxCollider>()) { box.center *= grow; box.size *= grow; }
                bb = LocalBounds(board.GetComponentsInChildren<Renderer>(true), transform);
                boardW = bb.size[across]; boardH = bb.size.y;
                s = trueSize;
            }
            holder.localScale = Vector3.one * s;
            var placed = LocalBounds(copies, transform);
            Vector3 target = bb.center; target.y = bb.min.y + boardH * 0.6f;
            target[outAxis] = bb.center[outAxis] + outSign * (bb.size[outAxis] * 0.5f + placed.size[outAxis] * 0.5f + 0.005f);
            holder.localPosition += target - placed.center;

            Nameplate(fish.Name, bb, outAxis, outSign);
        }

        // The board as built (art-tools/build_cleaning_table.py, piece_plaque): 0.61 m from its bottom edge to the top of
        // the hanging ring, the brass nameplate 0.32 x 0.06 m with its middle 0.075 m up and its face 0.063 m out
        private const float BoardTall = 0.609f, PlateUp = 0.085f, PlateW = 0.5f, PlateH = 0.1f;
        private static TMP_FontAsset? _font;

        /// <summary>The species' name on the brass nameplate, in Valheim's own lettering, dark as if engraved.</summary>
        private void Nameplate(string name, Bounds bb, int outAxis, float outSign)
        {
            // the game's Norse display lettering
            _font ??= Resources.FindObjectsOfTypeAll<TMP_FontAsset>().OrderByDescending(f => f.name.IndexOf("Norse", StringComparison.OrdinalIgnoreCase) >= 0)
                .ThenByDescending(f => f.name.IndexOf("Averia", StringComparison.OrdinalIgnoreCase) >= 0).FirstOrDefault();
            if (_font == null) return;
            float s = bb.size.y / BoardTall;                                       // a boss plaque is built bigger
            var go = new GameObject("vdw_plaque_name", typeof(RectTransform));
            go.transform.SetParent(transform, false);
            go.layer = gameObject.layer;
            var text = go.AddComponent<TextMeshPro>();
            text.font = _font;
            text.text = name;
            text.alignment = TextAlignmentOptions.Center;
            text.enableAutoSizing = true; text.fontSizeMin = 0.05f; text.fontSizeMax = 2f;
            text.enableWordWrapping = false;
            text.color = new Color(0.13f, 0.07f, 0.02f);
            text.fontStyle = FontStyles.Bold;
            text.rectTransform.sizeDelta = new Vector2(PlateW * 0.92f, PlateH * 0.9f) * s;
            Vector3 at = bb.center; at.y = bb.min.y + PlateUp * s;
            // a clear centimetre off the plate: any closer and, from a distance or at a slant, the depth test can't tell
            // the two apart and the plate flickers through the letters
            at[outAxis] = (outSign > 0 ? bb.max[outAxis] : bb.min[outAxis]) + outSign * 0.01f * s;
            go.transform.localPosition = at;
            // TextMeshPro reads from its -Z side: face the text's back into the board
            var outDir = (outAxis == 0 ? Vector3.right : Vector3.forward) * outSign;
            go.transform.localRotation = Quaternion.LookRotation(-outDir, Vector3.up);
        }

        private static readonly Color GoldColor = new Color(1f, 0.84f, 0.42f);
        private static readonly Dictionary<Material, Material> GoldCache = new Dictionary<Material, Material>();

        /// <summary>
        /// The fish's material plated in gold: a plain gold colour in place of its painted skin (so every species reads as
        /// the same metal), metallic and glossy, keeping its normal map so the scales and fins still show in the gold.
        /// Only half metallic (fully metallic reads black where there's little to reflect), with a faint glow.
        /// </summary>
        private static Material Gilded(Material? own)
        {
            if (own == null) return own!;
            if (GoldCache.TryGetValue(own, out var cached) && cached != null) return cached;
            var m = new Material(own) { name = own.name + "_gold" };
            if (m.HasProperty("_MainTex")) m.SetTexture("_MainTex", null);
            if (m.HasProperty("_Color")) m.SetColor("_Color", GoldColor);
            if (m.HasProperty("_MetallicGlossMap")) { m.SetTexture("_MetallicGlossMap", null); m.DisableKeyword("_METALLICGLOSSMAP"); }
            if (m.HasProperty("_Metallic")) m.SetFloat("_Metallic", 0.55f);
            if (m.HasProperty("_Glossiness")) m.SetFloat("_Glossiness", 0.8f);
            if (m.HasProperty("_GlossMapScale")) m.SetFloat("_GlossMapScale", 0.8f);
            // a faint warm glow of its own, so it still reads as gold in a dim hall
            if (m.HasProperty("_EmissionColor")) { m.SetTexture("_EmissionMap", null); m.SetColor("_EmissionColor", GoldColor * 0.18f); m.EnableKeyword("_EMISSION"); }
            GoldCache[own] = m;
            return m;
        }

        /// <summary>The box around these renderers' meshes in <paramref name="space"/>'s local coordinates.</summary>
        private static Bounds LocalBounds(IEnumerable<Renderer> renderers, Transform space)
        {
            bool any = false; var b = new Bounds();
            foreach (var r in renderers)
            {
                Mesh? mesh = r is SkinnedMeshRenderer smr ? smr.sharedMesh : r.GetComponent<MeshFilter>()?.sharedMesh;
                if (mesh == null) continue;
                var m = space.worldToLocalMatrix * r.transform.localToWorldMatrix;
                var mb = mesh.bounds;
                for (int i = 0; i < 8; i++)
                {
                    var c = mb.center + Vector3.Scale(mb.extents, new Vector3((i & 1) == 0 ? -1 : 1, (i & 2) == 0 ? -1 : 1, (i & 4) == 0 ? -1 : 1));
                    var p = m.MultiplyPoint3x4(c);
                    if (!any) { b = new Bounds(p, Vector3.zero); any = true; } else b.Encapsulate(p);
                }
            }
            return b;
        }
    }
}
