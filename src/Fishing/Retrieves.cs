using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>How a lure is being worked, read from what the player does (see <see cref="RetrieveTracker"/>).</summary>
    internal enum RetrieveStyle
    {
        None,       // sitting still: draws nothing
        SlowRoll,   // reeling steadily at a low speed
        Steady,     // reeling steadily at a medium speed
        Burn,       // reeling fast (high speed, or Shift)
        StopAndGo,  // reel, pause, reel, pause
        Twitch,     // rod twitches while reeling
        Hop,        // rod twitches with pauses and no reeling: the lure hops along the bottom
    }

    /// <summary>
    /// Reads the retrieve from the last few seconds of input: reeling (and at what speed), pauses between bursts of
    /// reeling, and rod twitches (left click). Hop and Twitch win over Stop &amp; Go, which wins over plain reeling.
    /// </summary>
    internal sealed class RetrieveTracker
    {
        private const float TwitchWindow = 3f, StopGoWindow = 4.5f, MinPause = 0.35f, MaxPause = 2f;
        private readonly List<float> _twitches = new();
        private readonly List<float> _pauses = new();   // when each pause of the right length ended (reeling resumed)
        private bool _wasReeling;
        private float _stoppedAt = -100f;
        private float _reelShare;                      // how much of the last couple of seconds was spent reeling, 0..1
        private float _level;
        private bool _fast;

        public void Twitch(float now) => _twitches.Add(now);

        /// <summary>Called every frame the line is out with a lure on.</summary>
        public void Update(bool reeling, bool fast, float level, float now, float dt)
        {
            _reelShare = Mathf.MoveTowards(_reelShare, reeling ? 1f : 0f, dt / 2f);
            if (reeling)
            {
                _level = level;
                _fast = fast;
                if (!_wasReeling)
                {
                    float pause = now - _stoppedAt;
                    if (pause >= MinPause && pause <= MaxPause) _pauses.Add(now);
                }
            }
            else if (_wasReeling) _stoppedAt = now;
            _wasReeling = reeling;
            _twitches.RemoveAll(t => now - t > TwitchWindow);
            _pauses.RemoveAll(t => now - t > StopGoWindow);
        }

        public RetrieveStyle Style(float now, float stillAfter)
        {
            if (_twitches.Count >= 2) return _reelShare < 0.25f ? RetrieveStyle.Hop : RetrieveStyle.Twitch;
            if (_pauses.Count >= 2) return RetrieveStyle.StopAndGo;
            if (!_wasReeling && now - _stoppedAt > stillAfter && (_twitches.Count == 0 || now - _twitches[_twitches.Count - 1] > stillAfter))
                return RetrieveStyle.None;
            if (_fast || _level >= 0.85f) return RetrieveStyle.Burn;
            return _level < 0.45f ? RetrieveStyle.SlowRoll : RetrieveStyle.Steady;
        }
    }

    /// <summary>
    /// What each retrieve does: every lure kind has retrieves it swims right on, and every retrieve draws certain fish
    /// (fast fish chase a burned lure, bottom fish take a hopped one). A good match brings the right fish more often
    /// and makes them likelier to strike; a poor one gets follows that turn away.
    /// </summary>
    internal static class Retrieves
    {
        public static string Name(RetrieveStyle s) => s switch
        {
            RetrieveStyle.SlowRoll => "Slow Roll",
            RetrieveStyle.Steady => "Steady",
            RetrieveStyle.Burn => "Burn",
            RetrieveStyle.StopAndGo => "Stop & Go",
            RetrieveStyle.Twitch => "Twitch",
            RetrieveStyle.Hop => "Hop",
            _ => "Still",
        };

        /// <summary>The retrieves each kind of lure works best with.</summary>
        internal static readonly Dictionary<LureKind, RetrieveStyle[]> Natural = new()
        {
            [LureKind.Spoon] = new[] { RetrieveStyle.Steady, RetrieveStyle.Burn, RetrieveStyle.StopAndGo },
            [LureKind.Spinner] = new[] { RetrieveStyle.SlowRoll, RetrieveStyle.Steady },
            [LureKind.Crankbait] = new[] { RetrieveStyle.Steady, RetrieveStyle.Burn, RetrieveStyle.StopAndGo },
            [LureKind.Jig] = new[] { RetrieveStyle.Hop, RetrieveStyle.Twitch },
            [LureKind.SoftPlastic] = new[] { RetrieveStyle.SlowRoll, RetrieveStyle.Hop, RetrieveStyle.StopAndGo },
            [LureKind.TexasRig] = new[] { RetrieveStyle.Hop, RetrieveStyle.SlowRoll },
            [LureKind.Swimbait] = new[] { RetrieveStyle.SlowRoll, RetrieveStyle.Steady },
            [LureKind.Topwater] = new[] { RetrieveStyle.Twitch, RetrieveStyle.StopAndGo },
            [LureKind.Fly] = new[] { RetrieveStyle.Twitch, RetrieveStyle.StopAndGo, RetrieveStyle.SlowRoll },
        };

        /// <summary>The fish each retrieve draws, by fish id.</summary>
        internal static readonly Dictionary<RetrieveStyle, string[]> Targets = new()
        {
            [RetrieveStyle.SlowRoll] = new[] { "perch", "trout", "frostchar", "grouper", "halibut", "anglerfish", "fenringfin", "bonemaw" },
            [RetrieveStyle.Steady] = new[] { "trout", "salmon", "herring", "perch", "tetra", "dvergr_dace", "serpentfin" },
            [RetrieveStyle.Burn] = new[] { "pike", "mackerel", "tuna", "salmon", "odinfin", "surtling_sardine", "magmafish" },
            [RetrieveStyle.StopAndGo] = new[] { "pike", "trollfish", "mistfin", "greydwarf_goby", "lingcod", "jotunnperch" },
            [RetrieveStyle.Twitch] = new[] { "trout", "tetra", "dvergr_dace", "mackerel", "trollfish", "frostchar" },
            [RetrieveStyle.Hop] = new[] { "coral_cod", "lingcod", "halibut", "grouper", "pufferfish", "greydwarf_goby", "bonemaw", "jotunnperch" },
        };

        private const float NaturalBoost = 1.35f, WrongKind = 0.65f, FishLikes = 1.6f;

        public static bool IsNatural(BaitDefinition lure, RetrieveStyle style) =>
            Natural.TryGetValue(Lures.KindOf(lure), out var ok) && ok.Contains(style);

        public static bool Draws(RetrieveStyle style, FishDefinition fish) =>
            Targets.TryGetValue(style, out var ids) && ids.Contains(fish.Id);

        /// <summary>How well this retrieve suits this lure and this fish: around 0.65 (poor) to 2.2 (just right).</summary>
        public static float Factor(FishDefinition fish, BaitDefinition lure, RetrieveStyle style)
        {
            if (style == RetrieveStyle.None) return 1f;
            float f = IsNatural(lure, style) ? NaturalBoost : WrongKind;
            if (Draws(style, fish)) f *= FishLikes;
            return f;
        }

        /// <summary>Chance a fish that comes up behind a lure strikes it, for how well it's being worked.</summary>
        public static float StrikeChance(float factor) => Mathf.Clamp01(0.3f + 0.35f * factor);
    }
}
