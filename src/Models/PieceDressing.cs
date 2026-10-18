using System.Linq;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// Dresses a piece model (the Fish Cleaning Table set) in Valheim's own materials, so it lights, weathers and shows
    /// the red "invalid placement" tint like a vanilla build: the meshes named "vdw_wood" / "vdw_darkwood" (UVs in metres)
    /// get Valheim's tiling ship planks, the rest gets the planks' piece shader carrying the model's own painted maps.
    /// Without the vanilla material the model keeps its bundle materials.
    /// </summary>
    internal static class PieceDressing
    {
        private static Material? _wood, _darkWood;

        public static void Dress(GameObject prefab)
        {
            var model = prefab.transform.Find("vdw_model");
            var planks = FishingBoat.FindShipPlanks();
            if (model == null || planks == null) return;

            _wood ??= Planks(planks, "VDW_PieceWood", Color.white);
            _darkWood ??= Planks(planks, "VDW_PieceDarkWood", new Color(0.55f, 0.5f, 0.45f));
            foreach (var r in model.GetComponentsInChildren<Renderer>(true))
            {
                var use = r.name == "vdw_wood" ? _wood : r.name == "vdw_darkwood" ? _darkWood : null;
                r.sharedMaterials = use != null
                    ? Enumerable.Repeat(use, r.sharedMaterials.Length).ToArray()
                    : r.sharedMaterials.Select(m => Painted(planks, m)).ToArray();
            }
        }

        /// <summary>The planks, tiled per metre like the Fishing Boat's hull.</summary>
        private static Material Planks(Material planks, string name, Color tint)
        {
            var m = new Material(planks) { name = name };
            Vector2 vanillaScale = m.mainTextureScale;
            foreach (var prop in m.GetTexturePropertyNames())
                if (m.GetTexture(prop) != null && m.GetTextureScale(prop) == vanillaScale)
                {
                    m.SetTextureScale(prop, FishingBoat.PlankTilingPerMetre);
                    m.SetTextureOffset(prop, Vector2.zero);
                }
            if (m.HasProperty("_Color")) m.SetColor("_Color", tint);
            return m;
        }

        /// <summary>The piece shader with a model's own albedo and normal map in place of the planks.</summary>
        private static Material Painted(Material planks, Material? own)
        {
            var m = new Material(planks) { name = (own != null ? own.name : "piece") + "_vdw" };
            foreach (var prop in m.GetTexturePropertyNames())
            {
                m.SetTextureScale(prop, Vector2.one);
                m.SetTextureOffset(prop, Vector2.zero);
            }
            m.mainTexture = own != null ? own.mainTexture : null;
            if (m.HasProperty("_BumpMap"))
                m.SetTexture("_BumpMap", own != null && own.HasProperty("_BumpMap") ? own.GetTexture("_BumpMap") : null);
            if (m.HasProperty("_Color")) m.SetColor("_Color", Color.white);
            return m;
        }
    }
}
