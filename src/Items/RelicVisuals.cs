using System;
using HarmonyLib;
using System.Linq;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// How the two worn relics look. Jörmungandr's Scale is the vanilla linen cape with serpent-scale maps
    /// (buff_relic_scale_cape_Albedo / _Normal / _MetallicSmoothness / _Emission textures in a bundle) on both the
    /// dropped cloth and the worn cape. The Pearl of Njord is a whole belt with the pearl in front (the
    /// buff_relic_pearl model): worn, it takes the vanilla belt's place round the wearer's hips. The Rune of Njord is a
    /// necklace (buff_rune_njord) hung at the base of the neck. Njord's Regalia (buff_regalia_njord, cloned from the
    /// Dverger circlet) is a crown on the head, in the circlet's place. Everyone sees them, since the belt a player wears is
    /// synced and this runs on every client.
    /// </summary>
    internal static class RelicVisuals
    {
        private const string ScaleCape = "buff_relic_scale_cape";
        private const string PearlModel = "buff_relic_pearl";
        private const string PearlItem = "VDW_Buff_relic_pearl";
        private const string RuneModel = "buff_rune_njord";
        private const string RuneItem = "VDW_Buff_rune_njord";

        public static void Apply(GameObject prefab, string baseName)
        {
            if (baseName == "buff_relic_scale") RetextureCape(prefab);
            if (baseName == PearlModel || baseName == RuneModel || baseName == "buff_regalia_njord") HideWornBelt(prefab);
        }

        /// <summary>The pearl and the rune replace the belt they're cloned from: the vanilla belt (attach_skin) isn't shown when worn.</summary>
        private static void HideWornBelt(GameObject prefab)
        {
            var skin = prefab.transform.Find("attach_skin");
            if (skin == null) return;
            foreach (var r in skin.GetComponentsInChildren<Renderer>(true)) r.enabled = false;
        }

        private static readonly System.Reflection.FieldInfo? UtilityInstances = AccessTools.Field(typeof(VisEquipment), "m_utilityItemInstances");

        /// <summary>Hides whatever Valheim spawned on the body for the worn belt (in case it turned the renderers back on).</summary>
        private static void HideWornInstances(VisEquipment vis)
        {
            if (UtilityInstances?.GetValue(vis) is System.Collections.Generic.List<GameObject> list)
                foreach (var go in list)
                    if (go != null)
                        foreach (var r in go.GetComponentsInChildren<Renderer>(true))
                            if (r.enabled) r.enabled = false;
        }

        private static void RetextureCape(GameObject prefab)
        {
            var albedo = CustomModels.LoadBundleAsset<Texture2D>(ScaleCape + "_Albedo");
            if (albedo == null)
            {
                Plugin.Log.LogWarning($"Jörmungandr's Scale: no '{ScaleCape}_Albedo' texture in the bundles; it stays a linen cape.");
                return;
            }
            var normal = CustomModels.LoadBundleAsset<Texture2D>(ScaleCape + "_Normal");
            var metal = CustomModels.LoadBundleAsset<Texture2D>(ScaleCape + "_MetallicSmoothness");
            var glow = CustomModels.LoadBundleAsset<Texture2D>(ScaleCape + "_Emission");

            var made = new System.Collections.Generic.Dictionary<Material, Material>();
            foreach (var r in prefab.GetComponentsInChildren<Renderer>(true))
            {
                if (r is ParticleSystemRenderer) continue;
                var mats = r.sharedMaterials;
                bool changed = false;
                for (int i = 0; i < mats.Length; i++)
                {
                    var src = mats[i];
                    if (src == null || !src.HasProperty("_MainTex")) continue;
                    if (!made.TryGetValue(src, out var m))
                    {
                        m = new Material(src) { name = "VDW_JormungandrScale" };
                        m.SetTexture("_MainTex", albedo);
                        m.SetColor("_Color", Color.white);
                        // The linen cape takes its colour from a style palette; the scales carry their own.
                        if (m.HasProperty("_UseStyles")) m.SetFloat("_UseStyles", 0f);
                        if (m.HasProperty("_StyleTex")) m.SetTexture("_StyleTex", Texture2D.whiteTexture);
                        if (normal != null && m.HasProperty("_BumpMap")) { m.SetTexture("_BumpMap", normal); m.EnableKeyword("_NORMALMAP"); }
                        if (metal != null && m.HasProperty("_MetallicGlossMap"))
                        {
                            m.SetTexture("_MetallicGlossMap", metal);
                            if (m.HasProperty("_Metallic")) m.SetFloat("_Metallic", 1f);
                            if (m.HasProperty("_UseGlossmap")) m.SetFloat("_UseGlossmap", 1f);
                            if (m.HasProperty("_Glossiness")) m.SetFloat("_Glossiness", 1f);
                            if (m.HasProperty("_MetalGloss")) m.SetFloat("_MetalGloss", 1f);
                        }
                        if (glow != null && m.HasProperty("_EmissionMap"))
                        {
                            m.SetTexture("_EmissionMap", glow);
                            m.SetColor("_EmissionColor", Color.white * 1.2f);
                            m.EnableKeyword("_EMISSION");
                        }
                        made[src] = m;
                    }
                    mats[i] = m; changed = true;
                }
                if (changed) r.sharedMaterials = mats;
            }
            var shared = prefab.GetComponent<ItemDrop>()?.m_itemData.m_shared;
            if (shared != null) shared.m_variants = 0;   // no linen colour picker
            Plugin.Log.LogDebug($"Jörmungandr's Scale: linen cape retextured ({made.Count} material(s)).");
        }


        // ------------------------------------------------------------------ relics worn on the body
        /// <summary>
        /// A relic shown on whoever wears it, in place of the vanilla belt it's cloned from: its model is placed against
        /// one bone in the skeleton's rest pose (Fit: y up and z forward of it, metres; w its scale; Shape stretches it
        /// across, tall and front to back), then skinned to the body's bones so it bends with it (WornSkinning) - or, if that
        /// can't be done, carried rigidly by one bone.
        /// </summary>
        private sealed class Worn
        {
            public string Item = "", Model = "", Label = "";
            public string[] Anchor = { "Hips" };      // placed against the first of these the skeleton has
            public string Parent = "Hips";            // and moves with this one, if it can't be skinned
            public string[] Bones = { "Hips" };       // skinned to these (see WornSkinning)
            public float Strength = 1f;               // how fully it follows them (0: rigid on Parent, 1: fully skinned)
            public Vector4 Fit;                       // x right, y up, z forward of the anchor (metres), w scale
            public Vector3 Rot;                       // turned by these (degrees: pitch about right, yaw about up, roll about forward)
            public Vector3 Shape = Vector3.one;
            public bool Helmet;                       // worn in the helmet slot (in place of the vanilla helmet) rather than the belt
            private int _hash;
            public int Hash => _hash != 0 ? _hash : _hash = Item.GetStableHashCode();
        }

        // The pearl: a whole belt round the hips (38 cm across, build_pearl_belt.py), a little taller and deeper than the
        // model so it doesn't clip into the body. Fitted in game.
        private static readonly Worn Pearl = new Worn
        {
            Item = PearlItem, Model = PearlModel, Label = "Pearl belt",
            Fit = new Vector4(0f, 0.29f, 0.01f, 1f), Shape = new Vector3(1f, 1.1f, 1.1f),
            Bones = new[] { "Hips", "Spine", "Spine1", "LeftUpLeg", "RightUpLeg" },
        };
        // The Rune of Njord: a necklace (cord loop 20 cm across, build_rune_necklace.py) whose back lies at the base of the
        // neck, moving with the upper chest so it doesn't swing with every turn of the head.
        private static readonly Worn Rune = new Worn
        {
            Item = RuneItem, Model = RuneModel, Label = "Rune necklace",
            Anchor = new[] { "Neck", "Spine2" }, Parent = "Spine2",
            Bones = new[] { "Spine1", "Spine2", "Neck", "LeftShoulder", "RightShoulder" },
            Strength = 0.5f,                          // half: it bends with the chest without denting at every vertex
            Fit = new Vector4(0f, 0.09f, 0.06f, 1.2f), Shape = new Vector3(1f, 1f, 1.15f),   // fitted in game
        };
        // Njord's Regalia (roadmap #24): a crown (22 cm across, build_cleaning_table.py) sitting round the brow, moving with
        // the head. Fitted in game.
        private static readonly Worn Regalia = new Worn
        {
            Item = Endgame.Regalia, Model = "buff_regalia_njord", Label = "Regalia crown", Helmet = true,
            Anchor = new[] { "Head" }, Parent = "Head", Bones = new[] { "Head" },
            Fit = new Vector4(0.005f, 0.15f, 0.07f, 1f), Rot = new Vector3(-10f, 0f, 0f), Shape = new Vector3(0.8f, 1f, 1f),   // tuned in game (vdw_debug wear)
        };
        private static readonly Worn[] WornRelics = { Pearl, Rune, Regalia };

        // ------------------------------------------------------------------ fitting by hand (vdw_debug wear)
        /// <summary>The worn relics by short name, for the fitting command: crown, pearl, rune.</summary>
        public static string WornNames => "crown, pearl, rune";
        private static Worn? WornByName(string name) =>
            name.StartsWith("c", StringComparison.OrdinalIgnoreCase) ? Regalia : name.StartsWith("p", StringComparison.OrdinalIgnoreCase) ? Pearl
          : name.StartsWith("r", StringComparison.OrdinalIgnoreCase) ? Rune : null;

        /// <summary>
        /// Sets (or nudges) one of a worn relic's placement values and puts it on again so the change shows at once:
        /// x / y / z (metres right, up, forward), scale, pitch / yaw / roll (degrees). Returns its values as code to keep.
        /// </summary>
        public static string Tune(Player p, string relic, string axis, float value, bool nudge)
        {
            LoadFits();
            var w = WornByName(relic);
            if (w == null) return $"Unknown relic '{relic}' ({WornNames}).";
            float Apply(float old) => nudge ? old + value : value;
            switch (axis.ToLowerInvariant())
            {
                case "x": w.Fit.x = Apply(w.Fit.x); break;
                case "y": w.Fit.y = Apply(w.Fit.y); break;
                case "z": w.Fit.z = Apply(w.Fit.z); break;
                case "scale": case "s": w.Fit.w = Apply(w.Fit.w); break;
                case "pitch": w.Rot.x = Apply(w.Rot.x); break;
                case "yaw": w.Rot.y = Apply(w.Rot.y); break;
                case "roll": w.Rot.z = Apply(w.Rot.z); break;
                case "sx": case "width": w.Shape.x = Apply(w.Shape.x); break;
                case "sy": case "height": w.Shape.y = Apply(w.Shape.y); break;
                case "sz": case "depth": w.Shape.z = Apply(w.Shape.z); break;
                case "show": break;
                default: return "Axis: x, y, z, scale, pitch, yaw, roll, sx (width), sy (height), sz (depth)";
            }
            Refit(p);
            SaveFits();
            string line = Describe(w);
            Plugin.Log.LogInfo("Worn fit: " + line);
            return line;
        }

        // the hand-tuned placements, kept between sessions (BepInEx/config/ValheimDeepWaters/worn_fit.txt)
        private static string FitFile => System.IO.Path.Combine(BepInEx.Paths.ConfigPath, "ValheimDeepWaters", "worn_fit.txt");
        private static string Key(Worn w) => w == Regalia ? "crown" : w == Pearl ? "pearl" : "rune";
        private static readonly System.Globalization.CultureInfo Inv = System.Globalization.CultureInfo.InvariantCulture;

        private static void SaveFits()
        {
            try
            {
                var lines = new[] { Regalia, Pearl, Rune }.Select(w => string.Join(" ", new[] { Key(w) }.Concat(
                    new[] { w.Fit.x, w.Fit.y, w.Fit.z, w.Fit.w, w.Rot.x, w.Rot.y, w.Rot.z, w.Shape.x, w.Shape.y, w.Shape.z }.Select(v => v.ToString("0.####", Inv)))));
                System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(FitFile));
                System.IO.File.WriteAllLines(FitFile, lines);
            }
            catch (Exception e) { Plugin.Log.LogWarning("Worn fit: couldn't save " + FitFile + ": " + e.Message); }
        }

        private static bool _fitsLoaded;
        /// <summary>Applies the saved hand-tuned placements, if any (once).</summary>
        private static void LoadFits()
        {
            if (_fitsLoaded) return;
            _fitsLoaded = true;
            try
            {
                if (!System.IO.File.Exists(FitFile)) return;
                foreach (var line in System.IO.File.ReadAllLines(FitFile))
                {
                    var parts = line.Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries);
                    var w = parts.Length == 11 ? WornByName(parts[0]) : null;
                    if (w == null) continue;
                    var v = parts.Skip(1).Select(s => float.Parse(s, Inv)).ToArray();
                    w.Fit = new Vector4(v[0], v[1], v[2], v[3]); w.Rot = new Vector3(v[4], v[5], v[6]); w.Shape = new Vector3(v[7], v[8], v[9]);
                }
                Plugin.Log.LogInfo("Worn fit: hand-tuned placements loaded from " + FitFile);
            }
            catch (Exception e) { Plugin.Log.LogWarning("Worn fit: couldn't read " + FitFile + ": " + e.Message); }
        }

        public static string Describe(string relic) { LoadFits(); var w = WornByName(relic); return w == null ? $"Unknown relic '{relic}' ({WornNames})." : Describe(w); }
        private static string Describe(Worn w) =>
            $"{w.Label}: x {w.Fit.x:0.000} y {w.Fit.y:0.000} z {w.Fit.z:0.000} | scale {w.Fit.w:0.00} sx {w.Shape.x:0.00} sy {w.Shape.y:0.00} sz {w.Shape.z:0.00} | pitch {w.Rot.x:0.0} yaw {w.Rot.y:0.0} roll {w.Rot.z:0.0}";

        /// <summary>Takes the worn relics off this player's model so they're put on again (with any new placement) next frame.</summary>
        private static void Refit(Player p)
        {
            var vis = p.GetComponent<VisEquipment>();
            if (vis == null) return;
            foreach (var w in vis.GetComponents<WornRelic>()) w.Remove();
        }

        private static readonly System.Reflection.FieldInfo? UtilityHash = AccessTools.Field(typeof(VisEquipment), "m_currentUtilityItemHash");
        private static readonly System.Reflection.FieldInfo? HelmetHash = AccessTools.Field(typeof(VisEquipment), "m_currentHelmetItemHash");
        private static readonly System.Reflection.FieldInfo? HelmetInstance = AccessTools.Field(typeof(VisEquipment), "m_helmetItemInstance");

        [HarmonyPatch(typeof(VisEquipment), "UpdateEquipmentVisuals")]
        private static class UpdatePatch
        {
            private static void Postfix(VisEquipment __instance)
            {
                if (UtilityHash == null || __instance.m_bodyModel == null) return;
                LoadFits();
                int worn = UtilityHash.GetValue(__instance) is int h ? h : 0;
                int head = HelmetHash?.GetValue(__instance) is int hh ? hh : 0;
                foreach (var spec in WornRelics)
                {
                    bool wearing = (spec.Helmet ? head : worn) == spec.Hash;
                    var have = __instance.GetComponents<WornRelic>().FirstOrDefault(w => w.Spec == spec);
                    if (wearing && have == null) (have = __instance.gameObject.AddComponent<WornRelic>()).Attach(__instance, spec);
                    else if (!wearing && have != null) { have.Remove(); have = null; }
                    if (have != null) have.HideBelt(__instance);
                }
            }
        }

        private sealed class WornRelic : MonoBehaviour
        {
            public Worn? Spec;
            private GameObject? _model;
            private GameObject? _hiddenBelt;
            private VisEquipment? _vis;

            /// <summary>Hides the worn vanilla belt (or helmet) once per instance Valheim spawns.</summary>
            public void HideBelt(VisEquipment vis)
            {
                if (Spec != null && Spec.Helmet)
                {
                    if (!(HelmetInstance?.GetValue(vis) is GameObject helmet) || helmet == _hiddenBelt) return;
                    foreach (var r in helmet.GetComponentsInChildren<Renderer>(true)) r.enabled = false;
                    _hiddenBelt = helmet;
                    return;
                }
                if (!(UtilityInstances?.GetValue(vis) is System.Collections.Generic.List<GameObject> list) || list.Count == 0) return;
                if (list[0] == _hiddenBelt) return;
                HideWornInstances(vis);
                _hiddenBelt = list[0];
            }

            public void Attach(VisEquipment vis, Worn spec)
            {
                Spec = spec;
                _vis = vis;
                var model = CustomModels.GetBundlePrefab(spec.Model);
                Transform? Find(string name) => vis.m_bodyModel.bones.FirstOrDefault(b => b != null && b.name == name);
                var anchor = spec.Anchor.Select(Find).FirstOrDefault(b => b != null);
                var parent = Find(spec.Parent);
                if (model == null || anchor == null || parent == null) return;
                _model = Instantiate(model);
                _model.name = "VDW_Worn_" + spec.Model;
                foreach (var c in _model.GetComponentsInChildren<Collider>(true)) Destroy(c);
                foreach (var rb in _model.GetComponentsInChildren<Rigidbody>(true)) Destroy(rb);
                // Placed against the anchor bone and squared to the character - worked out in the skeleton's rest pose (not
                // wherever the walk or idle has twisted the bones right now, which left the belt turned), then carried
                // along by the parent bone as it moves.
                var root = vis.transform;
                var at = RestBone(vis.m_bodyModel, anchor);
                var carry = RestBone(vis.m_bodyModel, parent);
                var frame = new GameObject("vdw_rest_bone").transform;
                frame.SetPositionAndRotation(carry.pos, carry.rot);
                frame.localScale = parent.lossyScale;
                _model.transform.SetPositionAndRotation(at.pos + root.right * spec.Fit.x + root.forward * spec.Fit.z + root.up * spec.Fit.y,
                    Quaternion.LookRotation(root.forward, root.up) * Quaternion.Euler(spec.Rot));
                _model.transform.localScale = spec.Shape * spec.Fit.w;
                // Skinned to the body so it bends with it; if that can't be done, carried rigidly by the parent bone.
                var skinned = WornSkinning.Skin(vis.m_bodyModel, _model,
                    $"{spec.Model}|{spec.Fit:F4}|{spec.Rot:F1}|{spec.Shape}|{spec.Strength}", spec.Bones, spec.Parent, spec.Strength);
                if (skinned != null)
                {
                    Destroy(frame.gameObject);
                    Destroy(_model);
                    _model = skinned;
                    return;
                }
                _model.transform.SetParent(frame, true);
                Vector3 lp = _model.transform.localPosition, ls = _model.transform.localScale;
                Quaternion lr = _model.transform.localRotation;
                _model.transform.SetParent(parent, false);
                _model.transform.localPosition = lp; _model.transform.localRotation = lr; _model.transform.localScale = ls;
                Destroy(frame.gameObject);
            }

            /// <summary>Where a bone would be in the rest pose (from the skin's bind poses), as the body stands now.</summary>
            private static (Vector3 pos, Quaternion rot) RestBone(SkinnedMeshRenderer body, Transform bone)
            {
                int i = System.Array.IndexOf(body.bones, bone);
                var bind = body.sharedMesh != null ? body.sharedMesh.bindposes : null;
                if (i < 0 || bind == null || i >= bind.Length) return (bone.position, bone.rotation);
                var m = body.transform.localToWorldMatrix * bind[i].inverse;
                return (m.GetColumn(3), m.rotation);
            }

            public void Remove()
            {
                if (_model != null) Destroy(_model);
                Destroy(this);
            }

            private void OnDestroy() { if (_model != null) Destroy(_model); }
        }
    }
}
