using HarmonyLib;
using System.Collections.Generic;
using System.Runtime.CompilerServices;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// The Oilskin Coat's sleeves and upper body painted onto the wearer's body (its collar and skirt stay a model,
    /// FisherGear). Valheim only paints chest and legs items onto the body, and the body has only those two layers, so
    /// while the coat is worn the coat's paint is laid over whatever the legs layer shows (the overalls, another legs
    /// armour, or the bare underwear) - the legs layer draws on top of the chest layer, so the coat covers the shirt and
    /// the overalls' bib as a coat should. Taking the coat off puts the legs layer back.
    /// </summary>
    internal static class CoatPaint
    {
        private static readonly int LegsTex = Shader.PropertyToID("_LegsTex"), LegsBump = Shader.PropertyToID("_LegsBumpMap");
        private static int _coatHash;
        private static Texture? _paint, _normals;
        private static Color32[]? _paintPx;
        private const int Size = 1024;
        private static readonly Dictionary<int, Texture2D> Composites = new();   // by the legs texture underneath

        private sealed class State { public bool Applied; public Texture? Base, Shown, BaseBump, ShownBump; }
        private static readonly Dictionary<int, Texture2D> BumpComposites = new();   // by the legs normal map underneath
        private static readonly ConditionalWeakTable<VisEquipment, State> States = new();

        private static readonly AccessTools.FieldRef<VisEquipment, int> ShoulderHash = AccessTools.FieldRefAccess<VisEquipment, int>("m_currentShoulderItemHash");
        private static readonly AccessTools.FieldRef<VisEquipment, int> LegHash = AccessTools.FieldRefAccess<VisEquipment, int>("m_currentLegItemHash");
        private static readonly AccessTools.FieldRef<VisEquipment, Texture> EmptyLegs = AccessTools.FieldRefAccess<VisEquipment, Texture>("m_emptyLegsTexture");

        /// <summary>Turns it on for this item (the coat), painting this texture.</summary>
        /// <param name="normals">the coat's folds and wrinkles in the body's tangent space (flat outside the coat), or null.
        /// Written as rgb = normal, alpha 1, which Unity's normal unpacking reads either way.</param>
        public static void Enable(string itemPrefab, Texture paint, Texture? normals)
        {
            _coatHash = itemPrefab.GetStableHashCode();
            _paint = paint;
            _normals = normals;
        }

        [HarmonyPatch(typeof(VisEquipment), "UpdateEquipmentVisuals")]
        private static class Apply
        {
            private static void Postfix(VisEquipment __instance)
            {
                if (_coatHash == 0 || __instance.m_bodyModel == null) return;
                var st = States.GetOrCreateValue(__instance);
                var mat = __instance.m_bodyModel.material;
                var now = mat.GetTexture(LegsTex);
                bool worn = ShoulderHash(__instance) == _coatHash;
                if (!worn)
                {
                    if (st.Applied)
                    {
                        if (now == st.Shown) mat.SetTexture(LegsTex, st.Base);
                        if (st.ShownBump != null && mat.GetTexture(LegsBump) == st.ShownBump) mat.SetTexture(LegsBump, st.BaseBump);
                        st.Applied = false;
                    }
                    return;
                }
                if (st.Applied && now == st.Shown) return;                      // nothing changed underneath
                // what the legs layer would show without the coat: the legs armour's, or the bare body's
                Texture? under = now != null && now != st.Shown ? now : BaseLegs(__instance);
                var shown = Composite(under);
                if (shown == null) return;
                var bump = mat.GetTexture(LegsBump);
                st.Base = under; st.Shown = shown; st.Applied = true;
                if (bump == null || bump != st.ShownBump) st.BaseBump = bump;
                mat.SetTexture(LegsTex, shown);
                // the coat's folds over the legs layer's: the painted overalls' wrinkles are kept where the coat isn't
                // (another legs armour's own normal map can't be read the same way: the coat's alone is used then)
                if (_normals != null) { st.ShownBump = BumpComposite(st.BaseBump); mat.SetTexture(LegsBump, st.ShownBump); }
            }
        }

        private static Texture? BaseLegs(VisEquipment ve)
        {
            int legs = LegHash(ve);
            if (legs != 0)
            {
                var m = ObjectDB.instance?.GetItemPrefab(legs)?.GetComponent<ItemDrop>()?.m_itemData.m_shared.m_armorMaterial;
                if (m != null && m.HasProperty(LegsTex)) return m.GetTexture(LegsTex);
            }
            return EmptyLegs(ve);
        }

        /// <summary>The coat's paint over this legs texture (cached per texture). Null if the paint can't be read.</summary>
        private static Texture2D? Composite(Texture? under)
        {
            int key = under != null ? under.GetInstanceID() : 0;
            if (Composites.TryGetValue(key, out var done) && done != null) return done;
            _paintPx ??= _paint != null ? Read(_paint) : null;
            if (_paintPx == null) return null;
            var basePx = under != null ? Read(under) : new Color32[Size * Size];
            var outPx = new Color32[Size * Size];
            for (int i = 0; i < outPx.Length; i++)
            {
                var c = _paintPx[i]; var b = basePx[i];
                if (c.a >= 250) { outPx[i] = new Color32(c.r, c.g, c.b, 255); continue; }
                if (c.a <= 5) { outPx[i] = b; continue; }
                float a = c.a / 255f;
                outPx[i] = new Color32((byte)(b.r + (c.r - b.r) * a), (byte)(b.g + (c.g - b.g) * a), (byte)(b.b + (c.b - b.b) * a), (byte)Mathf.Max(b.a, c.a));
            }
            var tex = new Texture2D(Size, Size, TextureFormat.RGBA32, true) { name = "vdw_coat_over_" + (under != null ? under.name : "none") };
            tex.SetPixels32(outPx); tex.Apply(true, true);                     // mip maps, then no longer readable (frees the copy)
            Composites[key] = tex;
            return tex;
        }

        private static Color32[]? _normalsPx;

        /// <summary>
        /// The coat's normal map over the one underneath where the coat is painted (cached per map underneath). Only the
        /// mod's own painted normal maps (*_paint_*_nrm, plain rgb) can be read for that; anything else gets the coat's alone.
        /// </summary>
        private static Texture BumpComposite(Texture? under)
        {
            if (_normals == null) return under!;
            if (under == null || !under.name.Contains("_paint_") || !under.name.EndsWith("_nrm")) return _normals;
            int key = under.GetInstanceID();
            if (BumpComposites.TryGetValue(key, out var done) && done != null) return done;
            _paintPx ??= _paint != null ? Read(_paint) : null;
            _normalsPx ??= Read(_normals, true);
            if (_paintPx == null) return _normals;
            var basePx = Read(under, true); var outPx = new Color32[Size * Size];
            for (int i = 0; i < outPx.Length; i++)
            {
                float a = _paintPx[i].a / 255f; var c = _normalsPx[i]; var b = basePx[i];
                outPx[i] = new Color32((byte)(b.r + (c.r - b.r) * a), (byte)(b.g + (c.g - b.g) * a), (byte)(b.b + (c.b - b.b) * a), 255);
            }
            var tex = new Texture2D(Size, Size, TextureFormat.RGBA32, true, true) { name = "vdw_coat_nrm_over_" + under.name };
            tex.SetPixels32(outPx); tex.Apply(true, true);
            BumpComposites[key] = tex;
            return tex;
        }

        /// <summary>Any texture's pixels at Size x Size (through a render texture, so it needn't be readable).</summary>
        private static Color32[] Read(Texture tx, bool linear = false)
        {
            var rt = RenderTexture.GetTemporary(Size, Size, 0, RenderTextureFormat.ARGB32, linear ? RenderTextureReadWrite.Linear : RenderTextureReadWrite.sRGB);
            Graphics.Blit(tx, rt);
            var prev = RenderTexture.active; RenderTexture.active = rt;
            var t = new Texture2D(Size, Size, TextureFormat.RGBA32, false);
            t.ReadPixels(new Rect(0, 0, Size, Size), 0, 0); t.Apply();
            RenderTexture.active = prev; RenderTexture.ReleaseTemporary(rt);
            var px = t.GetPixels32(); Object.Destroy(t);
            return px;
        }
    }
}
