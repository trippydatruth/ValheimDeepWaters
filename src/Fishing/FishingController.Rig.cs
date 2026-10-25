using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// Terminal tackle (Tackle.json, the Weight and Leader tackle slots): what's on the line decides how deep the bait
    /// sits, and fish bite best at the depth they feed at (FeedMinDepth/FeedMaxDepth, Bottom in Fish.json).
    ///   float, no leader - the bait hangs about a metre down
    ///   float + leader   - the bait hangs at the leader's length (set on the tackle panel)
    ///   weight           - no float: the bait lies on the bottom, and the cast goes further
    ///   egg sinker + leader (Carolina) - the bait drifts just off the bottom, and fish take it more readily
    ///   bullet weight + a soft lure (Texas) - the lure works along the bottom
    /// Water moves a weight that's too light for it: waves, wind and storms drag it over the bottom, and nothing takes a
    /// bait that's being dragged. Heavy weights hold.
    /// </summary>
    internal static partial class FishingController
    {
        private const float FloatHangDepth = 1f;         // a float with no leader
        private const float CarolinaLift = 0.6f;         // how far off the bottom a Carolina-rigged bait drifts
        private const float NearBottom = 1.5f;           // within this of the bottom counts as on it

        /// <summary>Lure kinds a weight goes on (the Texas rig): soft lures, not hard baits.</summary>
        private static bool TakesWeight(BaitDefinition lure) =>
            lure.LureKind == "Soft bait" || lure.LureKind == "Texas rig" || lure.LureKind == "Swimbait";

        /// <summary>The weight that will be used with this rig, if any (a hard lure leaves it off).</summary>
        internal static TackleDefinition? RigWeight(Player player, BaitDefinition? lure)
        {
            var w = Tackle.WeightOn(player);
            if (w == null) return null;
            return lure == null || TakesWeight(lure) ? w : null;
        }

        /// <summary>Works out the rig at the cast: bait depth, its name, any extra interest.</summary>
        private static void SetUpRig(Player player, FishingSession s, BaitDefinition? lure, float waterDepth)
        {
            s.Weight = RigWeight(player, lure);
            s.Leader = Tackle.LeaderOn(player) != null;
            float leaderLen = Tackle.LeaderLength(player);
            float bottom = Mathf.Max(0.3f, waterDepth - 0.2f);

            if (lure != null)
            {
                if (s.Weight != null) { s.BaitDepth = bottom; s.RigName = "Texas rig"; s.RigInterest = s.Weight.Rig == "Texas" ? 0.1f : 0f; }
                else { s.BaitDepth = -1f; s.RigName = ""; }
                if (Tackle.WeightOn(player) != null && s.Weight == null) Msg($"A {lure.LureKind.ToLowerInvariant()} doesn't take a weight; it's left off.");
                return;
            }
            if (s.Weight != null)
            {
                bool carolina = s.Leader && s.Weight.Rig == "Carolina";
                s.BaitDepth = carolina ? Mathf.Max(0.3f, bottom - CarolinaLift) : bottom;
                s.RigName = carolina ? "Carolina rig" : "Bottom rig";
                s.RigInterest = carolina ? 0.15f : 0f;
                return;
            }
            s.BaitDepth = Mathf.Min(s.Leader ? leaderLen : FloatHangDepth, bottom);
            s.RigName = s.Leader ? "Float and leader" : "Float";
        }

        /// <summary>
        /// How much likelier (or not) a fish is to come to a bait at this depth: twice as likely where it feeds, much less
        /// far from it; bottom feeders want it on or near the bottom. 1 when the depth doesn't count (a plain lure, a boss).
        /// </summary>
        internal static float DepthFactor(FishDefinition f, float baitDepth, float waterDepth)
        {
            if (baitDepth < 0f || BossFish.IsBoss(f.Id)) return 1f;
            if (f.Bottom) return waterDepth - baitDepth <= NearBottom ? 2.5f : 0.4f;
            if (f.FeedMaxDepth <= 0f) return 1f;                        // no feeding depth given: anywhere
            if (baitDepth >= f.FeedMinDepth && baitDepth <= f.FeedMaxDepth) return 2f;
            float miss = baitDepth < f.FeedMinDepth ? f.FeedMinDepth - baitDepth : baitDepth - f.FeedMaxDepth;
            return Mathf.Lerp(0.6f, 0.15f, Mathf.Clamp01(miss / 8f));
        }

        // ------------------------------------------------------------------ the water moving a weight

        /// <summary>How hard the water pushes on a rig here and now: waves at sea, wind on the surface, more in a storm.</summary>
        internal static float WaterPush(FishingSession s)
        {
            if (EnvMan.instance == null) return 0f;
            float wind = Mathf.Clamp01(EnvMan.instance.GetWindIntensity());
            float push = s.Ocean ? 0.6f + 1.2f * wind : 0.15f + 0.4f * wind;
            if (EnvMan.IsWet() && wind > 0.6f) push *= 1.5f;           // a storm
            return push;
        }

        /// <summary>Each frame while waiting: a weight too light for the water is dragged downwind. Returns false if the cast ended.</summary>
        private static bool UpdateDrift(Player player, FishingSession s)
        {
            if (s.Weight == null || EnvMan.instance == null)
            {
                s.Dragged = false;
                return true;
            }
            float over = WaterPush(s) - s.Weight.Hold;
            bool dragged = over > 0f && !_reelingNow;
            if (dragged && !s.Dragged && Time.time > s.DragWarnedAt + 20f)
            {
                s.DragWarnedAt = Time.time;
                Msg($"The water's dragging your {Loc.Text(s.Weight.Name)} along the bottom - a heavier weight would hold.");
            }
            s.Dragged = dragged;
            if (!dragged) return true;

            Vector3 dir = EnvMan.instance.GetWindDir(); dir.y = 0f;
            if (dir.sqrMagnitude < 1e-4f) return true;
            float speed = Mathf.Min(1.5f, over * 0.6f);
            var before = s.FloatPos;
            s.FloatPos += dir.normalized * speed * Time.deltaTime;
            KeepFloat(player, s);
            if (ZoneSystem.instance != null)
            {
                float depth = WaterLevel() - ZoneSystem.instance.GetGroundHeight(s.FloatPos);
                if (depth < 0.4f) { s.FloatPos = before; s.Dragged = false; return true; }   // washed up against the shallows: it stays
                s.Depth = depth;
                s.BaitDepth = Mathf.Max(0.3f, depth - 0.2f - (s.RigName == "Carolina rig" ? CarolinaLift : 0f));
            }
            return true;
        }

        /// <summary>The weight and leader go with the line when it snaps, like the hook.</summary>
        private static void LoseRig(Player player, FishingSession s)
        {
            if (s.Weight != null && Tackle.WeightOn(player)?.Id == s.Weight.Id) Tackle.UseOne(player, Tackle.WeightSlot);
            if (s.Leader && Tackle.LeaderOn(player) != null) Tackle.UseOne(player, Tackle.LeaderSlot);
        }

        /// <summary>For the HUD: the rig and how deep it fishes, before or during a cast.</summary>
        internal static string RigSummary(Player player)
        {
            var s = _session;
            if (s != null && s.BaitDepth >= 0f)
                return $"{s.RigName} · {(s.Weight != null && s.RigName != "Carolina rig" ? "on the bottom" : $"{s.BaitDepth:0.#} m down")}" +
                       (s.Dragged ? " · dragging" : "");
            if (s != null) return "";
            var lure = Tackle.LureOn(player);
            var weight = RigWeight(player, lure);
            bool leader = Tackle.LeaderOn(player) != null;
            if (lure != null) return weight != null ? $"Texas rig · {Loc.Text(weight.Name)}" : "";
            if (weight != null) return leader && weight.Rig == "Carolina" ? "Carolina rig · just off the bottom" : $"Bottom rig · {Loc.Text(weight.Name)}";
            return leader ? $"Float and leader · {Tackle.LeaderLength(player):0.#} m" : $"Float · {FloatHangDepth:0} m";
        }
    }
}
