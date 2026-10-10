using Jotunn.Managers;

namespace ValheimDeepWaters
{
    /// <summary>
    /// Item, piece and buff names and descriptions are Valheim translation tokens ("$vdw_rod_copper"), with the
    /// English taken from the JSON data files. Other languages can be added without touching code: put a Jotunn
    /// translation file in BepInEx/plugins/ValheimDeepWaters/Translations/&lt;Language&gt;/, e.g. German/vdw.json
    /// containing { "vdw_rod_copper": "Kupferangel", ... }. (Run "vdw_debug tokens" to list every token.)
    /// </summary>
    internal static class Loc
    {
        public static readonly System.Collections.Generic.SortedDictionary<string, string> English = new();

        /// <summary>Registers the English text for a token and returns the token ("$key") to store on the item.</summary>
        public static string Token(string key, string english)
        {
            key = key.ToLowerInvariant();
            English[key] = english;
            LocalizationManager.Instance.GetLocalization().AddTranslation("English", key, english);
            return "$" + key;
        }

        /// <summary>Text with any tokens replaced, for places Valheim doesn't localize for us (our HUD).</summary>
        public static string Text(string? s) =>
            string.IsNullOrEmpty(s) ? "" : Localization.instance != null ? Localization.instance.Localize(s) : s!;
    }
}
