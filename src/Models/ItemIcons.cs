using Jotunn.Managers;
using System;
using System.IO;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// Inventory icons for items with custom models. A hand-made icon wins if there is one (a "&lt;model&gt;_icon.png"
    /// in the Models folder, or a sprite/texture named "&lt;model&gt;_icon" in any bundle there); otherwise the custom
    /// model is rendered to an icon at Valheim's usual inventory angle when the game starts.
    /// </summary>
    internal static class ItemIcons
    {
        private const int Size = 128;

        // Prefabs that already got a hand-made icon; a later render (e.g. a rod falling back to the shared
        // "rod" model) mustn't replace it.
        private static readonly System.Collections.Generic.HashSet<GameObject> HandMade = new();

        /// <summary>For an item with no custom model: use a hand-made icon if one exists, else leave vanilla's.</summary>
        public static void ApplyHandMadeOnly(GameObject prefab, string modelKey)
        {
            if (HandMade.Contains(prefab)) return;
            if (prefab.GetComponent<ItemDrop>() == null && prefab.GetComponent<Piece>() == null) return;
            var handMade = LoadHandMade(modelKey);
            if (handMade == null) return;
            SetIcon(prefab, handMade);
            HandMade.Add(prefab);
        }

        /// <summary>Called once a custom model has been put on an item or piece prefab.</summary>
        public static void Apply(GameObject prefab, string modelKey)
        {
            if (HandMade.Contains(prefab)) return;
            // Only inventory items and buildable pieces show an icon (not the worm mound, bobber and so on).
            if (prefab.GetComponent<ItemDrop>() == null && prefab.GetComponent<Piece>() == null) return;
            try
            {
                var handMade = LoadHandMade(modelKey);
                if (handMade != null)
                {
                    SetIcon(prefab, handMade);
                    HandMade.Add(prefab);
                    return;
                }

                // Rendered fresh each launch (no cache), so a re-exported model always gets a matching icon.
                var request = new RenderManager.RenderRequest(prefab)
                {
                    Rotation = RenderManager.IsometricRotation,
                    Width = Size,
                    Height = Size,
                    UseCache = false
                };
                var sprite = RenderManager.Instance.Render(request);
                if (sprite != null) SetIcon(prefab, sprite);
                else Plugin.Log.LogWarning($"Icons: rendering '{modelKey}' failed; it keeps its vanilla icon.");
            }
            catch (Exception ex)
            {
                Plugin.Log.LogWarning($"Icons: '{modelKey}' failed ({ex.Message}); it keeps its vanilla icon.");
            }
        }

        private static void SetIcon(GameObject prefab, Sprite sprite)
        {
            var drop = prefab.GetComponent<ItemDrop>();
            if (drop != null)
            {
                var shared = drop.m_itemData.m_shared;
                shared.m_icons = new[] { sprite };
                // Buff items show the same picture in the status-effect bar.
                if (shared.m_consumeStatusEffect is SE_FishingBuff consumed) consumed.m_icon = sprite;
                if (shared.m_equipStatusEffect is SE_FishingBuff equipped) equipped.m_icon = sprite;
            }

            var piece = prefab.GetComponent<Piece>();
            if (piece != null) piece.m_icon = sprite;
        }

        private static Sprite? LoadHandMade(string modelKey)
        {
            string name = modelKey + "_icon";

            string? png = CustomModels.FindFile(name + ".png");
            if (png != null)
            {
                var tex = new Texture2D(2, 2, TextureFormat.RGBA32, false) { name = name };
                if (tex.LoadImage(File.ReadAllBytes(png)))
                    return Sprite.Create(tex, new Rect(0, 0, tex.width, tex.height), new Vector2(0.5f, 0.5f));
            }

            return CustomModels.LoadBundleSprite(name);
        }
    }
}
