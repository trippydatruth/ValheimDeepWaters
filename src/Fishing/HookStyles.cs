namespace ValheimDeepWaters
{
    /// <summary>
    /// The kinds of hook (Hooks.json "Style"), each fished the way the real one is:
    ///   J       - the all-rounder: you set it yourself. The baseline.
    ///   Circle  - for live and cut bait left alone: the fish turns and the hook slides into the corner of its mouth and
    ///             sets itself. Three times the strike window, and if you don't strike it sets itself when the window
    ///             runs out; a hooked fish's head shakes pull at it half as hard; but a strike in the first moment yanks
    ///             it out of the fish's mouth (lower hook chance).
    ///   EWG     - extra wide gap, heavy wire, for worms and soft baits rigged weedless: straightens half as easily,
    ///             head shakes pull at it less, and a better hookset with worms, grubs and leeches.
    ///   Treble  - three points for soft dough, stink and cut baits on the bottom: a better hookset, more so on a
    ///             weighted bottom rig and with soft baits; but the thin wire bends out sooner on heavy fish.
    /// </summary>
    internal static class HookStyles
    {
        public const string J = "J", Circle = "Circle", Ewg = "EWG", Treble = "Treble";

        private static bool Is(HookDefinition? h, string style) => h != null && string.Equals(h.Style, style, System.StringComparison.OrdinalIgnoreCase);

        /// <summary>Baits a treble holds (soft, mushy, stinky) and an EWG suits (worm-like).</summary>
        private static readonly System.Collections.Generic.HashSet<string> SoftBaits = new() { "stinkbait", "cut_bait", "northern_bait", "deep_bait", "frost_bait", "shrimp" };
        private static readonly System.Collections.Generic.HashSet<string> WormBaits = new() { "worm", "grub", "leech" };

        public static float WindowMult(HookDefinition? h) => Is(h, Circle) ? 3f : 1f;

        /// <summary>A circle hook left alone sets itself when the strike window runs out.</summary>
        public static bool SetsItself(HookDefinition? h) => Is(h, Circle);

        /// <summary>Added to the hook chance. <paramref name="early"/>: struck in the first moment after the bite.</summary>
        public static float ChanceBonus(HookDefinition? h, FishingSession s, bool early)
        {
            string bait = s.Bait?.Id ?? "";
            if (Is(h, Circle)) return early ? -0.15f : 0f;
            if (Is(h, Ewg)) return WormBaits.Contains(bait) ? 0.1f : 0f;
            if (Is(h, Treble)) return 0.06f + (s.Weight != null ? 0.08f : 0f) + (SoftBaits.Contains(bait) ? 0.08f : 0f);
            return 0f;
        }

        /// <summary>How readily a fish too heavy for it bends the hook out.</summary>
        public static float StraightenMult(HookDefinition? h) => Is(h, Ewg) ? 0.5f : Is(h, Treble) ? 1.6f : 1f;

        /// <summary>How hard a leaping fish's head shake pulls on the line.</summary>
        public static float ShakeMult(HookDefinition? h) => Is(h, Circle) ? 0.5f : Is(h, Ewg) ? 0.6f : 1f;

        /// <summary>The hook's kind and what it's good for, for its tooltip.</summary>
        public static string Describe(HookDefinition h)
        {
            if (Is(h, Circle)) return "Circle hook: for live and cut bait. Three times as long to strike, and left alone it sets itself; hooked fish shake it less. Striking the instant it bites can pull it free.";
            if (Is(h, Ewg)) return "EWG hook: wide gap, heavy wire. Straightens half as easily, holds through head shakes, and hooks better with worms, grubs and leeches.";
            if (Is(h, Treble)) return "Treble hook: three points. Hooks better, more on a weighted bottom rig and with soft baits (stinkbait, cut bait, blubber, shrimp); bends out sooner on heavy fish.";
            return "J hook: the all-rounder. Set it yourself when the fish bites.";
        }
    }
}
