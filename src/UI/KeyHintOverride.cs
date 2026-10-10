using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// Hides Valheim's bottom "KeyHints" bar (Cast / Pull / Dodge) while the rod is out, since Deep Waters
    /// shows its own hints. Re-applied every LateUpdate because Hud turns it back on each frame.
    /// </summary>
    internal static class KeyHintOverride
    {
        private static GameObject? _keyHints;
        private static bool _hidden;

        public static void SetActive(bool hide)
        {
            if (!hide)
            {
                // Hand control back to Hud once, rather than forcing the bar on every frame.
                if (_hidden && _keyHints != null) _keyHints.SetActive(true);
                _hidden = false;
                return;
            }

            // Hud may not have built its hierarchy yet on the first few calls, so keep looking until found.
            if (_keyHints == null)
            {
                var t = Hud.instance != null ? Hud.instance.transform.Find("hudroot/KeyHints") : null;
                if (t == null) return;
                _keyHints = t.gameObject;
            }

            _keyHints.SetActive(false);
            _hidden = true;
        }

        public static void Reset() => SetActive(false);
    }
}
