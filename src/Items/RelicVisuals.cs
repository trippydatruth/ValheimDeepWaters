using HarmonyLib;
using System.Linq;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// How the two worn relics look. Jörmungandr's Scale is the vanilla linen cape with serpent-scale maps
    /// (buff_relic_scale_cape_Albedo / _Normal / _MetallicSmoothness / _Emission textures in a bundle) on both the
    /// dropped cloth and the worn cape. The Pearl of Njord is a whole belt with the pearl in front (the
    /// buff_relic_pearl model): worn, it takes the vanilla belt's place round the wearer's hips; everyone sees it,
    /// since the belt a player wears is synced and this runs on every client.
    /// </summary>
    internal static class RelicVisuals
    {
        private const string ScaleCape = "buff_relic_scale_cape";
        private const string PearlModel = "buff_relic_pearl";
        private const string PearlItem = "VDW_Buff_relic_pearl";

        public static void Apply(GameObject prefab, string baseName)
        {
            if (baseName == "buff_relic_scale") RetextureCape(prefab);
            if (baseName == PearlModel) HideWornBelt(prefab);
        }

        /// <summary>The pearl replaces the belt it's cloned from: the vanilla belt (attach_skin) isn't shown when worn.</summary>
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
                Plugin.Log.LogInfo($"Jörmungandr's Scale: no '{ScaleCape}_Albedo' texture in the bundles; it stays a linen cape.");
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
            Plugin.Log.LogInfo($"Jörmungandr's Scale: linen cape retextured ({made.Count} material(s)).");
        }

        // ------------------------------------------------------------------ the pearl on the belt
        private static int _pearlHash;
        private static int PearlHash => _pearlHash != 0 ? _pearlHash : _pearlHash = PearlItem.GetStableHashCode();
        private static readonly System.Reflection.FieldInfo? UtilityHash = AccessTools.Field(typeof(VisEquipment), "m_currentUtilityItemHash");

        [HarmonyPatch(typeof(VisEquipment), "UpdateEquipmentVisuals")]
        private static class UpdatePatch
        {
            private static void Postfix(VisEquipment __instance)
            {
                if (UtilityHash == null || __instance.m_bodyModel == null) return;
                bool wearing = UtilityHash.GetValue(__instance) is int h && h == PearlHash;
                var have = __instance.GetComponent<PearlOnBelt>();
                if (wearing && have == null) __instance.gameObject.AddComponent<PearlOnBelt>().Attach(__instance);
                else if (!wearing && have != null) have.Remove();
                if (wearing) __instance.GetComponent<PearlOnBelt>()?.HideBelt(__instance);
            }
        }

        // How the belt sits: y up from the hips bone, z forward from it (metres), w its scale. The model is 38 cm across
        // (build_pearl_belt.py); vdw_debug pearlfit changes this in game.
        private static Vector4 Fit = new Vector4(0f, 0.29f, 0.0f, 1f);

        /// <summary>vdw_debug pearlfit: sets the belt's scale, height and forward offset, and refits it on everyone.</summary>
        internal static string PearlFit(float scale, float up, float forward)
        {
            Fit = new Vector4(0f, up, forward, scale);
            int n = 0;
            foreach (var p in Object.FindObjectsByType<PearlOnBelt>(FindObjectsSortMode.None)) { p.Refit(); n++; }
            return $"Pearl belt: scale {scale:0.00}, up {up:0.00}, forward {forward:0.00} (refitted on {n} wearer(s)).";
        }

        private sealed class PearlOnBelt : MonoBehaviour
        {
            private GameObject? _pearl;
            private GameObject? _hiddenBelt;

            /// <summary>Hides the worn vanilla belt once per belt instance Valheim spawns.</summary>
            public void HideBelt(VisEquipment vis)
            {
                if (!(UtilityInstances?.GetValue(vis) is System.Collections.Generic.List<GameObject> list) || list.Count == 0) return;
                if (list[0] == _hiddenBelt) return;
                HideWornInstances(vis);
                _hiddenBelt = list[0];
            }

            public void Attach(VisEquipment vis)
            {
                var model = CustomModels.GetBundlePrefab(PearlModel);
                var hips = vis.m_bodyModel.bones.FirstOrDefault(b => b != null && b.name == "Hips");
                if (model == null || hips == null) return;
                _pearl = Instantiate(model);
                _pearl.name = "VDW_PearlOnBelt";
                foreach (var c in _pearl.GetComponentsInChildren<Collider>(true)) Destroy(c);
                foreach (var rb in _pearl.GetComponentsInChildren<Rigidbody>(true)) Destroy(rb);
                // Round the hips at the vanilla belt line, the pearl to the front. Placed against the character (not the
                // hips' own axes, which differ by rig) and then carried along by the hips.
                var root = vis.transform;
                _pearl.transform.SetPositionAndRotation(hips.position + root.forward * Fit.z + root.up * Fit.y,
                    Quaternion.LookRotation(root.forward, root.up));
                _pearl.transform.localScale = Vector3.one * Fit.w;
                _pearl.transform.SetParent(hips, true);
                _vis = vis;
            }

            private VisEquipment? _vis;

            /// <summary>Puts the belt back with the current fit (vdw_debug pearlfit).</summary>
            public void Refit()
            {
                if (_vis == null || _pearl == null) return;
                Destroy(_pearl);
                Attach(_vis);
            }

            public void Remove()
            {
                if (_pearl != null) Destroy(_pearl);
                Destroy(this);
            }

            private void OnDestroy() { if (_pearl != null) Destroy(_pearl); }
        }
    }
}
