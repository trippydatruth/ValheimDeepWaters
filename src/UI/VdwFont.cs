using Jotunn.Managers;
using System;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>Best-effort access to Valheim's own UI font (AveriaSerif Bold) via Jotunn's GUIManager, so the
    /// HUD doesn't fall back to Unity's default font. Safe to call even if GUIManager isn't ready yet.</summary>
    internal static class VdwFont
    {
        private static Font? _font;
        private static bool _logged;

        public static Font? Get()
        {
            if (_font != null) return _font;

            try
            {
                _font = GUIManager.Instance != null ? GUIManager.Instance.AveriaSerifBold : null;
            }
            catch (Exception ex)
            {
                if (!_logged)
                {
                    _logged = true;
                    Plugin.Log.LogWarning($"Fishing HUD: could not get Valheim's font from GUIManager ({ex.Message}); using the default GUI font instead.");
                }
            }

            return _font;
        }
    }
}
