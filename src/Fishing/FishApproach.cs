using System;
using System.Collections.Generic;
using UnityEngine;

namespace ValheimDeepWaters
{
    internal enum SuitorState { Wander, Approach, Nibbling, Fleeing, Leaving }

    /// <summary>One simulated fish swimming around the cast, possibly working up to taking the bait.</summary>
    internal sealed class Suitor
    {
        public FishDefinition Fish = null!;
        public HookedFishVisual? Visual;
        public SuitorState State;

        public Vector3 Home;        // wander centre, like vanilla's spawn point
        public Vector3 Pos;         // simulated position; the visual eases toward it
        public Vector3 Waypoint;
        public float NextWaypoint;
        public float Depth;         // metres below the surface it cruises at

        public float DecideTime;    // when it commits to swimming to the bait
        public float WeightKg;      // rolled up front so the hook size can matter before the bite
        public bool TakesBait;      // false = inspects, nibbles once and leaves (vanilla's wrong-bait nibble)
        public bool HookTooSmall;   // why it won't take the bait: it's far too big for the hook
        public int FakeNibblesLeft;
        public bool RetrieveChecked; // behind a lure: has it decided yet whether the retrieve tempts it
        public float NextNibble;
        public float LastNibble = -100f;
        public float LeaveUntil;
        public float FleeUntil;
    }

    /// <summary>
    /// Vanilla-style pre-bite behaviour, modelled on Valheim's own Fish/FishingFloat: fish cruise between
    /// waypoints near where they live, one at a time decides to come to the bait, swims over, nibbles the
    /// float a few times (small dips), then really bites (the big dip that opens the hook window). A fish that
    /// doesn't like the bait nibbles once and swims off, and striking on a nibble spooks the fish away.
    ///
    /// Everything here is client-side simulation driving HookedFishVisual copies - no real creatures, no
    /// networked objects - so it can't reintroduce the ZNetView/ZSyncTransform problems from earlier versions.
    /// </summary>
    internal static class FishApproach
    {
        private const float WanderSpeed = 1.1f;
        private const float ApproachSpeed = 1.7f;
        /// <summary>A fish after a lure chases it down: faster than one nosing up to a still bait (a lure is retrieved at ~1.6 m/s).</summary>
        private static float Chase(FishingSession s) => s.Lure != null ? ApproachSpeed * 2.2f : ApproachSpeed;
        private const float LeaveSpeed = 4f;
        private const float StrikeWindow = 0.6f;  // right click this soon after a nibble = struck too early
        private const float WanderRadius = 6f;    // how far fish cruise around their spot
        private const int FishAroundBait = 2;     // fish around each cast; one at a time comes to the bait
        private const int MinNibbles = 1, MaxNibbles = 3;

        public static void Spawn(FishingSession s, Vector3 bobberPos, float firstDecideDelay, bool quick)
        {
            var player = Player.m_localPlayer;
            int extra = Mathf.RoundToInt(FishingBuffs.Total(player, BuffStat.ExtraFish, s.Spot));
            int fewerNibbles = Mathf.RoundToInt(FishingBuffs.Total(player, BuffStat.Nibbles, s.Spot));
            float interest = FishingBuffs.Total(player, BuffStat.BaitInterest, s.Spot);
            float heavier = FishingBuffs.Total(player, BuffStat.FishWeight, s.Spot);

            // Real fish swimming near the float make their species likelier to come to the bait (see SelectFish).
            s.Nearby = FishingController.ScanNearbyFish(s.Spot);

            int count = Mathf.Clamp(FishAroundBait + extra, 1, 9);
            for (int i = 0; i < count; i++)
            {
                var fish = FishingController.RollSuitorFish(s);
                if (fish == null) continue;

                var sui = new Suitor { Fish = fish, State = SuitorState.Wander };
                // A species that's really swimming nearby comes from where that fish is.
                sui.Home = !quick && s.Nearby.TryGetValue(fish.Id, out var seen) && PointDepth(seen, s.WaterY) >= 1.2f
                    ? new Vector3(seen.x, bobberPos.y, seen.z)
                    : FindSpawnPoint(s, bobberPos, quick && i == 0 ? 2.5f : 0f);
                sui.Depth = UnityEngine.Random.Range(0.5f, Mathf.Max(0.6f, Mathf.Min(1.6f, PointDepth(sui.Home, s.WaterY) - 0.3f)));
                sui.Pos = new Vector3(sui.Home.x, s.WaterY - sui.Depth, sui.Home.z);
                sui.Waypoint = sui.Pos;

                sui.WeightKg = FishingController.RollWeight(fish, heavier);
                sui.HookTooSmall = !quick && FishingController.HookFarTooSmall(s.Hook, sui.WeightKg);
                sui.TakesBait = quick || (!sui.HookTooSmall && UnityEngine.Random.value < FishingController.BaitInterest(fish, s.Bait, s.Trailer) + interest);
                sui.FakeNibblesLeft = quick || s.Lure != null ? 0 : Mathf.Max(0, UnityEngine.Random.Range(MinNibbles, MaxNibbles + 1) - fewerNibbles);

                // First fish commits after the configured wait (minus its swim time, so the bite still lands
                // roughly inside Min/Max Bite Delay); the rest are staggered behind it as backups.
                float travel = Vector3.Distance(sui.Pos, bobberPos) / ApproachSpeed;
                sui.DecideTime = i == 0
                    ? Time.time + Mathf.Max(quick ? 0f : 0.8f, firstDecideDelay - travel)
                    : Time.time + firstDecideDelay + UnityEngine.Random.Range(3f, 8f) * i;

                if (ContentRegistry.FishItems.TryGetValue(fish.Id, out var prefab))
                    sui.Visual = HookedFishVisual.Create(prefab, ContentRegistry.ModelKeyFor(fish), BossFish.ScaleFor(fish.Id));
                if (sui.Visual != null)
                {
                    sui.Visual.StayUnder = 0.15f;
                    sui.Visual.Position = sui.Pos;
                    sui.Visual.Intensity = 0.15f;
                }

                s.Suitors.Add(sui);
            }
            s.NextRespawn = 0f;
        }

        /// <summary>
        /// Advances every fish one frame. Returns the fish that just truly bit, if any. With waiting = false
        /// (bite window open, or fighting) fish only keep swimming - nobody commits, nibbles or bites.
        /// </summary>
        public static Suitor? Update(FishingSession s, BobberVisual? bobber, Vector3 bobberPos, bool waiting)
        {
            float now = Time.time;
            float dt = Time.deltaTime;
            Suitor? biter = null;
            bool someoneCommitted = !waiting;
            foreach (var x in s.Suitors)
                if (x.State == SuitorState.Approach || x.State == SuitorState.Nibbling) someoneCommitted = true;
            for (int i = s.Suitors.Count - 1; i >= 0; i--)
            {
                var f = s.Suitors[i];

                // Vanilla: a fish inside a player's noise range (running, jumping, fighting...) bolts away from
                // them and gives up on the bait. The fish holding the bait in the Bite phase is handled by the
                // controller instead (it loses the bite).
                if (f.State != SuitorState.Leaving && f != s.Biter)
                {
                    var noisy = ScaredBy(f.Pos);
                    if (noisy != null) Flee(f, noisy.transform.position, s.WaterY);
                }

                switch (f.State)
                {
                    case SuitorState.Fleeing:
                    {
                        Vector3 next = Vector3.MoveTowards(f.Pos, f.Waypoint, LeaveSpeed * dt);
                        // Vanilla's avoidLand: stop rather than swim up onto the shore.
                        if (PointDepth(next, s.WaterY) >= f.Depth + 0.2f) f.Pos = next;
                        SetVisual(f, 0.9f);
                        if (now >= f.FleeUntil)
                        {
                            f.State = SuitorState.Wander;
                            f.NextWaypoint = now; // head back toward its usual spot
                        }
                        break;
                    }

                    case SuitorState.Wander:
                        if (!someoneCommitted && now >= f.DecideTime)
                        {
                            f.State = SuitorState.Approach;
                            someoneCommitted = true;
                            break;
                        }
                        if (now >= f.NextWaypoint || FlatDist(f.Pos, f.Waypoint) < 0.3f)
                            PickWanderWaypoint(f, s.WaterY);
                        MoveToward(f, f.Waypoint, WanderSpeed, dt);
                        SetVisual(f, 0.15f);
                        break;

                    case SuitorState.Approach:
                    {
                        Vector3 target = BaitTarget(f, bobberPos);
                        MoveToward(f, target, Chase(s), dt);
                        SetVisual(f, 0.3f);
                        if (Vector3.Distance(f.Pos, target) < 0.3f)
                        {
                            f.State = SuitorState.Nibbling;
                            f.NextNibble = now + UnityEngine.Random.Range(0.4f, 1.0f);
                        }
                        break;
                    }

                    case SuitorState.Nibbling:
                    {
                        Vector3 target = BaitTarget(f, bobberPos);
                        // Back off a touch between nibbles, dart in on each one.
                        float sinceNibble = now - f.LastNibble;
                        Vector3 toBait = (bobberPos - f.Pos); toBait.y = 0f;
                        Vector3 hover = target - (toBait.sqrMagnitude > 0.0001f ? toBait.normalized : Vector3.zero) * (sinceNibble < 0.25f ? 0f : 0.2f);
                        MoveToward(f, hover, Chase(s), dt);
                        SetVisual(f, sinceNibble < 0.3f ? 0.7f : 0.35f);

                        if (!waiting || now < f.NextNibble) break;

                        if (!f.TakesBait)
                        {
                            bobber?.Nibble(f.HookTooSmall ? 0.12f : 0.05f);
                            FishingFx.Nibble(bobberPos);
                            f.LastNibble = now;
                            FishingController.Notify(f.HookTooSmall
                                ? $"Something big mouths the {(s.Lure != null ? "lure" : "bait")}... your hook's far too small for it."
                                : $"Something {(s.Lure != null ? "strikes short at the lure" : "nibbles at the bait")}... and loses interest.");
                            Leave(f, bobberPos);
                        }
                        else if (f.FakeNibblesLeft > 0)
                        {
                            bobber?.Nibble(UnityEngine.Random.Range(0.06f, 0.11f));
                            FishingFx.Nibble(bobberPos);
                            f.Visual?.Dart();
                            f.FakeNibblesLeft--;
                            f.LastNibble = now;
                            f.NextNibble = now + UnityEngine.Random.Range(0.9f, 1.9f);
                        }
                        else if (s.Lure != null && s.Boss == null && !f.RetrieveChecked)
                        {
                            // Behind a lure: whether it strikes depends on how the lure's being worked (Retrieves.cs).
                            f.RetrieveChecked = true;
                            float suits = Retrieves.Factor(f.Fish, s.Lure, s.Style);
                            if (UnityEngine.Random.value < Retrieves.StrikeChance(suits)) biter = f;
                            else
                            {
                                FishingController.Notify($"A {f.Fish.Name} follows your lure... and turns away. ({Retrieves.Name(s.Style)} isn't doing it for this one.)");
                                Leave(f, bobberPos);
                            }
                        }
                        else
                        {
                            biter = f;
                        }
                        break;
                    }

                    case SuitorState.Leaving:
                        MoveToward(f, f.Waypoint, LeaveSpeed, dt);
                        SetVisual(f, 0.9f);
                        if (now >= f.LeaveUntil)
                        {
                            Remove(s, i);
                            continue;
                        }
                        break;
                }
            }

            // Everyone's gone (spooked, picky, or swam off after a miss): new fish wander in after a while.
            if (waiting && biter == null && !AnyActive(s))
            {
                if (s.NextRespawn <= 0f) s.NextRespawn = now + UnityEngine.Random.Range(4f, 9f);
                else if (now >= s.NextRespawn) Spawn(s, bobberPos, FishingController.RollWait(s.Bait, s.Spot), false);
            }

            return biter;
        }

        /// <summary>
        /// The player whose noise reaches this spot, like vanilla's GetPlayerNoiseRange, except that players
        /// with a Stealth buff (the fisher's hats) don't count.
        /// </summary>
        public static Player? ScaredBy(Vector3 pos)
        {
            foreach (var p in Player.GetAllPlayers())
            {
                if (p == null || Vector3.Distance(p.transform.position, pos) >= Mathf.Min(p.GetNoiseRange(), 100f)) continue;
                if (FishingBuffs.Total(p, BuffStat.Stealth) > 0f) continue;
                return p;
            }
            return null;
        }

        /// <summary>Striking within a moment of a nibble spooks that fish. Returns true if this was such a strike.</summary>
        public static bool TryEarlyStrike(FishingSession s, Vector3 bobberPos)
        {
            foreach (var f in s.Suitors)
            {
                if (f.State != SuitorState.Nibbling || Time.time - f.LastNibble > StrikeWindow) continue;
                Leave(f, bobberPos);
                // The commotion makes the others wary for a bit.
                foreach (var o in s.Suitors)
                    if (o.State == SuitorState.Wander) o.DecideTime = Mathf.Max(o.DecideTime, Time.time + UnityEngine.Random.Range(3f, 6f));
                return true;
            }
            return false;
        }

        /// <summary>Called once the biter is hooked or missed: the rest of the fish clear off.</summary>
        public static void ScatterAll(FishingSession s, Vector3 bobberPos, Suitor? except = null)
        {
            foreach (var f in s.Suitors)
                if (f != except && f.State != SuitorState.Leaving) Leave(f, bobberPos);
        }

        /// <summary>
        /// Temporary scare: swims hard away from the noise for a couple of seconds, then wanders back. Unlike
        /// Leave, the fish stays around and can still come to the bait later - just not straight away.
        /// </summary>
        public static void Flee(Suitor f, Vector3 from, float waterY)
        {
            Vector3 away = f.Pos - from; away.y = 0f;
            if (away.sqrMagnitude < 0.01f) away = UnityEngine.Random.insideUnitSphere;
            away.y = 0f;
            f.Waypoint = f.Pos + away.normalized * 8f;
            f.Waypoint.y = waterY - f.Depth;
            f.State = SuitorState.Fleeing;
            f.FleeUntil = Time.time + UnityEngine.Random.Range(1.5f, 3f);
            f.DecideTime = Mathf.Max(f.DecideTime, f.FleeUntil + UnityEngine.Random.Range(2f, 5f));
        }

        public static void Leave(Suitor f, Vector3 bobberPos)
        {
            Vector3 away = f.Pos - bobberPos; away.y = 0f;
            if (away.sqrMagnitude < 0.01f) away = UnityEngine.Random.insideUnitSphere;
            away.y = 0f;
            f.Waypoint = f.Pos + away.normalized * 14f + Vector3.down * 0.5f;
            f.State = SuitorState.Leaving;
            f.LeaveUntil = Time.time + 3.5f;
        }

        public static void Remove(FishingSession s, Suitor f)
        {
            int i = s.Suitors.IndexOf(f);
            if (i >= 0) Remove(s, i);
        }

        private static void Remove(FishingSession s, int i)
        {
            var f = s.Suitors[i];
            if (f.Visual != null) UnityEngine.Object.Destroy(f.Visual.gameObject);
            s.Suitors.RemoveAt(i);
        }

        public static void DestroyAll(FishingSession s)
        {
            foreach (var f in s.Suitors)
                if (f.Visual != null) UnityEngine.Object.Destroy(f.Visual.gameObject);
            s.Suitors.Clear();
        }

        /// <summary>Used by the real-nearby-fish check: brings the next fish's decision forward.</summary>
        public static void SpeedUp(FishingSession s, float seconds)
        {
            foreach (var f in s.Suitors)
                if (f.State == SuitorState.Wander)
                    f.DecideTime = Mathf.Max(Time.time + 0.3f, f.DecideTime - seconds);
        }

        private static bool AnyActive(FishingSession s)
        {
            foreach (var f in s.Suitors)
                if (f.State != SuitorState.Leaving) return true;
            return false;
        }

        // ------------------------------------------------------------------

        private static Vector3 BaitTarget(Suitor f, Vector3 bobberPos)
        {
            // Just under the float, on the side the fish came from, so it faces the bait.
            Vector3 side = f.Pos - bobberPos; side.y = 0f;
            side = side.sqrMagnitude > 0.0001f ? side.normalized : Vector3.forward;
            return bobberPos + side * 0.25f + Vector3.down * 0.45f;
        }

        private static void PickWanderWaypoint(Suitor f, float waterY)
        {
            for (int tries = 0; tries < 6; tries++)
            {
                Vector2 r = UnityEngine.Random.insideUnitCircle * WanderRadius;
                var p = new Vector3(f.Home.x + r.x, waterY - f.Depth, f.Home.z + r.y);
                // Same rule as vanilla: only swim somewhere (and through somewhere) deep enough.
                if (PointDepth(p, waterY) < f.Depth + 0.3f) continue;
                if (PointDepth((p + f.Pos) * 0.5f, waterY) < f.Depth + 0.3f) continue;
                f.Waypoint = p;
                break;
            }
            f.NextWaypoint = Time.time + UnityEngine.Random.Range(3f, 5f);
        }

        private static Vector3 FindSpawnPoint(FishingSession s, Vector3 bobberPos, float fixedDistance)
        {
            for (int tries = 0; tries < 12; tries++)
            {
                float d = fixedDistance > 0f ? fixedDistance : UnityEngine.Random.Range(5f, 10f);
                Vector2 dir = UnityEngine.Random.insideUnitCircle.normalized;
                var p = bobberPos + new Vector3(dir.x, 0f, dir.y) * d;
                if (PointDepth(p, s.WaterY) >= 1.2f) return p;
            }
            Vector2 near = UnityEngine.Random.insideUnitCircle * 2f;
            return bobberPos + new Vector3(near.x, 0f, near.y);
        }

        private static float PointDepth(Vector3 p, float waterY)
        {
            if (ZoneSystem.instance == null) return 0f;
            return waterY - ZoneSystem.instance.GetGroundHeight(p);
        }

        private static void MoveToward(Suitor f, Vector3 target, float speed, float dt)
        {
            f.Pos = Vector3.MoveTowards(f.Pos, target, speed * dt);
        }

        private static float FlatDist(Vector3 a, Vector3 b)
        {
            a.y = 0f; b.y = 0f;
            return Vector3.Distance(a, b);
        }

        private static void SetVisual(Suitor f, float intensity)
        {
            if (f.Visual == null) return;
            f.Visual.Position = f.Pos;
            f.Visual.Intensity = intensity;
        }
    }
}
