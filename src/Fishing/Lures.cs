using System;
using System.Collections.Generic;
using System.Linq;

namespace ValheimDeepWaters
{
    /// <summary>The kinds of lure. Each draws its own set of fish (see <see cref="Lures.KindTargets"/>).</summary>
    internal enum LureKind
    {
        None,         // not a lure: plain bait on a hook
        Spoon,        // a wobbling, flashing metal spoon
        Spinner,      // a blade spinning round a shaft
        Crankbait,    // a hard diving plug that wobbles on the retrieve
        Jig,          // a weighted head bounced along the bottom
        SoftPlastic,  // a regular soft artificial bait (worm, grub, shad)
        TexasRig,     // a soft bait rigged weedless, for weeds, roots and cover
        Swimbait,     // a big soft fish that swims like one
        Topwater,     // a popper or walker worked on the surface
        Fly,          // an artificial fly
        Boss,         // a boss lure: only its boss fish answers it
    }

    /// <summary>
    /// What a lure (and the trailer on it) draws. A lure's kind brings its own fish, plus any the lure lists itself
    /// (TargetFish); those come far more readily and are keener to bite, and fish it doesn't draw mostly ignore it.
    /// A trailer widens that (its own TargetFish come too) and makes the fish the lure already draws keener still
    /// (TrailerBoost).
    /// </summary>
    internal static class Lures
    {
        /// <summary>The fish each kind of lure draws, by fish id.</summary>
        internal static readonly Dictionary<LureKind, string[]> KindTargets = new()
        {
            [LureKind.Spoon] = new[] { "pike", "trout", "salmon", "frostchar", "glacier_grayling", "rimejaw_cod", "herring", "mackerel", "tuna", "serpentfin", "surtling_sardine" },
            [LureKind.Spinner] = new[] { "perch", "trout", "pike", "tetra", "frostchar", "glacier_grayling", "salmon", "greydwarf_goby" },
            [LureKind.Crankbait] = new[] { "pike", "perch", "trollfish", "mistfin", "grouper", "magmafish" },
            [LureKind.Jig] = new[] { "coral_cod", "lingcod", "halibut", "rimejaw_cod", "frost_sculpin", "grouper", "jotunnperch", "bonemaw", "perch", "pufferfish" },
            [LureKind.SoftPlastic] = new[] { "perch", "trout", "frost_sculpin", "greydwarf_goby", "trollfish", "tetra", "mistfin", "pufferfish" },
            [LureKind.TexasRig] = new[] { "trollfish", "pike", "mistfin", "perch", "anglerfish", "greydwarf_goby" },
            [LureKind.Swimbait] = new[] { "pike", "tuna", "grouper", "lingcod", "halibut", "salmon", "serpentfin", "anglerfish", "fenringfin" },
            [LureKind.Topwater] = new[] { "pike", "trollfish", "mackerel", "tuna", "magmafish", "odinfin" },
            [LureKind.Fly] = new[] { "trout", "salmon", "frostchar", "glacier_grayling", "tetra", "perch" },
        };

        private const float DrawnWeight = 3f;          // a fish the lure draws is this much likelier to be the one that comes
        private const float IgnoredWeight = 0.3f;      // ...and one it doesn't, this much less likely
        private const float WidenedWeight = 2.5f;      // a fish only the trailer draws
        private const float DefaultTrailerBoost = 1.6f;
        private const float DrawnInterest = 0.25f, IgnoredInterest = -0.15f, WidenedInterest = 0.2f, BoostedInterest = 0.15f;

        public static LureKind KindOf(BaitDefinition? bait)
        {
            if (bait == null || !bait.IsLure) return LureKind.None;
            if (BossFish.ForLure(bait.Id) != null) return LureKind.Boss;
            return Enum.TryParse<LureKind>(bait.LureKind, true, out var k) ? k : LureKind.None;
        }

        /// <summary>Whether this lure (its kind or its own list) draws the fish.</summary>
        public static bool Draws(BaitDefinition lure, FishDefinition fish) =>
            (KindTargets.TryGetValue(KindOf(lure), out var ids) && ids.Contains(fish.Id)) ||
            (lure.TargetFish != null && lure.TargetFish.Contains(fish.Id));

        private static bool TrailerDraws(BaitDefinition? trailer, FishDefinition fish) =>
            trailer?.TargetFish != null && trailer.TargetFish.Contains(fish.Id);

        /// <summary>How much likelier this fish is to be the one that comes to a lure (and trailer): a weight factor.</summary>
        public static float WeightFactor(FishDefinition fish, BaitDefinition lure, BaitDefinition? trailer)
        {
            if (Draws(lure, fish))
                return DrawnWeight * (trailer != null ? Boost(trailer) : 1f);
            return TrailerDraws(trailer, fish) ? WidenedWeight : IgnoredWeight;
        }

        /// <summary>How much keener (or less keen) a fish that comes to the lure is to bite it: added to the bite chance.</summary>
        public static float InterestBonus(FishDefinition fish, BaitDefinition lure, BaitDefinition? trailer)
        {
            if (Draws(lure, fish)) return DrawnInterest + (trailer != null ? BoostedInterest : 0f);
            return TrailerDraws(trailer, fish) ? WidenedInterest : IgnoredInterest;
        }

        /// <summary>How fast fish find it: the lure's attraction, raised by its trailer's.</summary>
        public static float Attraction(BaitDefinition lure, BaitDefinition? trailer) =>
            Math.Max(0.5f, lure.Attraction) * (trailer != null ? Math.Max(1f, trailer.Attraction) : 1f);

        private static float Boost(BaitDefinition trailer) => trailer.TrailerBoost > 0f ? trailer.TrailerBoost : DefaultTrailerBoost;
    }
}
