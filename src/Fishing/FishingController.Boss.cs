using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// Boss fish (summoned with a lure, see BossFish) and the harder fight every legendary puts up: it enrages at two
    /// thirds of its stamina and turns desperate at one third, diving for the deep and recovering fast on a slack
    /// line. Bosses announce all this; mini-bosses just fight.
    /// </summary>
    internal static partial class FishingController
    {
        private const float OmenStrikeAfter = 7.5f;   // seconds from the omen to the strike
        private const float BossHookWindowMult = 2f;  // it takes the lure hard: more time to set the hook

        /// <summary>vdw_debug boss: the next cast summons this boss, wherever and whatever the bait.</summary>
        internal static string? DebugBoss;

        /// <summary>Lure cast: returns the boss if it answers here and now, else says why not (and returns null).</summary>
        private static BossInfo? SummonedBoss(BossInfo lureBoss, Vector3 spot, bool ocean, float depth, Heightmap.Biome biome)
        {
            if (lureBoss.Conditions(spot, ocean, depth, biome)) return lureBoss;
            var bait = ContentRegistry.Baits.TryGetValue(lureBoss.LureId, out var b) ? b : null;
            Msg($"Nothing answers the {Loc.Text(bait?.Name ?? "lure")} here.\n{lureBoss.Hint}");
            return null;
        }

        /// <summary>The omen: the water goes still, a sign, a few seconds of dread, then it strikes.</summary>
        private static void UpdateOmen(Player player, FishingSession s, Vector3 bobberPos)
        {
            if (s.Boss == null || s.Phase != FishingPhase.Waiting || s.OmenStep >= 2) return;
            float t = Time.time - s.OmenStart;
            if (t < 0f) return;

            if (s.OmenStep == 0)
            {
                s.OmenStep = 1;
                s.Swirl = OmenSwirl.Create(bobberPos);
                MessageHud.instance?.ShowBiomeFoundMsg(s.Boss.Omen, true);
                GameCamera.instance?.AddShake(player.transform.position, 30f, 1.2f, false);
                s.NextSplash = Time.time + 2f;
                return;
            }

            // Bubbles rise, the float shudders, and it builds toward the strike.
            if (Time.time >= s.NextSplash)
            {
                float build = Mathf.Clamp01(t / OmenStrikeAfter);
                s.NextSplash = Time.time + Mathf.Lerp(1.2f, 0.4f, build);
                Vector2 off = Random.insideUnitCircle * Mathf.Lerp(2.5f, 1f, build);
                FishingFx.Nibble(bobberPos + new Vector3(off.x, 0f, off.y));
                if (Random.value < build) s.ShudderUntil = Time.time + 0.25f;
                if (build > 0.6f) GameCamera.instance?.AddShake(player.transform.position, 30f, 0.5f * build, false);
            }

            if (t >= OmenStrikeAfter)
            {
                s.OmenStep = 2;
                BossStrike(player, s, bobberPos);
            }
        }

        private static void BossStrike(Player player, FishingSession s, Vector3 bobberPos)
        {
            float weight = RollWeight(s.Fish, 0.6f); // summoned giants run big
            if (HookFarTooSmall(s.Hook, weight))
            {
                FishingFx.FishSplash(bobberPos, 1.6f);
                Finish(player, $"{BossFish.Phrase(s.Fish.Name)} snaps at your hook and turns away - it's far too small for this beast.");
                return;
            }

            SetBiterFish(s, s.Fish, weight);
            s.Phase = FishingPhase.Bite;
            s.HookDeadline = Time.time + HookWindowSeconds * BossHookWindowMult * (1f + FishingBuffs.Total(player, BuffStat.HookWindow) + SkillHookWindow * Skill(player));
            FishingFx.Bite(bobberPos);
            FishingFx.FishSplash(bobberPos, 1.8f);
            GameCamera.instance?.AddShake(player.transform.position, 30f, 2f, false);
            Msg("FISH ON!");
        }

        /// <summary>Clears the boss from a cast that missed it: it sinks back into the deep.</summary>
        private static void BossGone(FishingSession s)
        {
            s.Boss = null;
            if (s.Swirl != null) Object.Destroy(s.Swirl);
            s.Swirl = null;
        }

        /// <summary>A legendary enrages at two thirds of its stamina and turns desperate at a third.</summary>
        private static void UpdateLegendaryPhase(Player player, FishingSession s, float freshness, bool exhausted, float strength)
        {
            int target = freshness < 0.33f ? 2 : freshness < 0.66f ? 1 : 0;
            if (target > s.FightPhase)
            {
                s.FightPhase = target;
                s.Running = true;
                s.StateTimer = Random.Range(1.5f, 2.5f);
                FishingFx.FishSplash(FishPos(player, s), 1.4f);
                s.HookedFish?.Leap(2f, 1.1f);
                s.Tension += 10f;
                if (target == 2) s.NextDive = Time.time + Random.Range(2f, 4f);
                if (s.Boss != null)
                {
                    string name = BossFish.Phrase(s.Fish.Name);
                    MessageHud.instance?.ShowBiomeFoundMsg(target == 1 ? $"{name} thrashes in fury!" : $"{name} dives for the deep!", false);
                    GameCamera.instance?.AddShake(player.transform.position, 30f, target == 1 ? 1.5f : 2.2f, false);
                }
            }

            // Desperate: sudden dives that rip line off the reel and spike the tension.
            if (s.FightPhase == 2 && !exhausted && Time.time >= s.NextDive)
            {
                s.NextDive = Time.time + Random.Range(5f, 9f);
                s.LineDistance += 2.5f + strength;
                s.Tension += 14f;
                s.Running = true;
                s.StateTimer = 1.5f;
                FishingFx.FishSplash(FishPos(player, s), 1.2f);
                if (s.Boss != null) GameCamera.instance?.AddShake(player.transform.position, 30f, 1.2f, false);
            }
        }

        /// <summary>How hard a legendary pulls in its current phase.</summary>
        private static float PhasePull(FishingSession s) => !s.Fish.Legendary ? 1f : s.FightPhase == 1 ? 1.35f : s.FightPhase == 2 ? 1.2f : 1f;

        /// <summary>How much likelier a legendary is to leap once it's enraged.</summary>
        private static float PhaseLeap(FishingSession s) => s.Fish.Legendary && s.FightPhase > 0 ? 2.5f : 1f;

        /// <summary>A boss fish is hooked and fighting: the boss bar shows and its music plays.</summary>
        internal static bool BossFightNow => _session?.Boss != null && _session.Phase == FishingPhase.Fighting;
    }
}
