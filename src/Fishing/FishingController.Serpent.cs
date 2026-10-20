using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// A sea-serpent boss (the Queen Eel) fights unlike any fish. Fresh, it circles the angler in wide sweeps, its back
    /// rolling up through the surface in humps. Enraged, it also charges straight at them - throwing the line slack, so
    /// they must reel hard or it shakes the hook - and rears up out of the water at the end of the charge, head high,
    /// before crashing down in a burst of spray that spikes the tension; pulling back while it's reared tires it fast.
    /// Desperate, it lashes the water with its tail too, on top of its dives.
    /// </summary>
    internal static partial class FishingController
    {
        private const float SerpentMaxAngle = 110f;    // how far round the angler it can circle (other fish: MaxLineAngle)
        private const float ChargeSpeed = 5.5f;        // m/s it closes in on a charge
        private const float ChargeNearest = 7f;        // it never charges closer than this
        internal const float RearRise = 0.6f, RearHold = 1.4f, RearFall = 0.45f;   // RemoteAnglers rears a watcher's copy the same
        private const float RearPullTire = 3f;         // pulling back on a reared serpent tires it this many times faster

        private static bool IsSerpent(FishingSession s) => s.Boss != null && s.Boss.Serpent;

        /// <summary>One step of a sea-serpent's moves; runs before the run path so its circling drives the line.</summary>
        private static void UpdateSerpent(Player player, FishingSession s, float dt, bool exhausted, bool pulling)
        {
            float now = Time.time;
            float scale = s.Boss!.Scale;
            Vector3 at = FishPos(player, s);
            string name = BossFish.Phrase(s.Fish.Name);

            if (exhausted)
            {
                if (s.Serpent == SerpentMove.Rear && !s.RearCrashed) Crash(player, s, at, scale);
                s.Serpent = SerpentMove.None;
                return;
            }

            switch (s.Serpent)
            {
                case SerpentMove.None:
                    if (now < s.NextSerpentMove) return;
                    float roll = Random.value;
                    if (s.FightPhase == 0 || roll < (s.FightPhase == 1 ? 0.5f : 0.35f)) StartCircle(s, now);
                    else if (s.FightPhase == 2 && roll > 0.75f) TailSlap(player, s, at, scale, now, name);
                    else
                    {
                        s.Serpent = SerpentMove.Charge;
                        s.SerpentStart = now;
                        s.SerpentUntil = now + Random.Range(1.6f, 2.3f);
                        s.Running = false;
                        s.AngleSpeed = 0f;
                        Msg($"{name} charges at you - reel in the slack!");
                        GameCamera.instance?.AddShake(player.transform.position, 30f, 1.2f, false);
                    }
                    return;

                case SerpentMove.Circle:
                    // wide steady sweeps round the angler; RunPath carries the line round and turns it back at the shore
                    s.Running = true;
                    s.StateTimer = Mathf.Max(s.StateTimer, s.SerpentUntil - now);
                    s.AngleSpeed = Mathf.Sign(s.AngleSpeed != 0f ? s.AngleSpeed : s.CircleDir) * (18f + 5f * s.FightPhase);
                    if (now >= s.NextHump)
                    {
                        s.NextHump = now + Random.Range(1.3f, 2.0f);
                        s.HookedFish?.Surface(0.35f * scale, 1.4f);
                        FishingFx.FishSplash(at, 0.7f * scale);
                        AnglerSync.Fx(player, FishFx.Hump, 0.35f * scale);   // after the splash: watchers get the hump (and its splash)
                    }
                    if (now >= s.SerpentUntil)
                    {
                        s.Serpent = SerpentMove.None;
                        s.Running = false;
                        s.StateTimer = Random.Range(1.5f, 2.5f);
                        s.NextSerpentMove = now + Random.Range(2f, 4f);
                    }
                    return;

                case SerpentMove.Charge:
                    // straight at the angler: the line goes slack unless they reel it in as fast as it comes
                    s.Running = false;
                    s.StateTimer = Mathf.Max(s.StateTimer, 1f);
                    s.LineDistance = Mathf.Max(ChargeNearest, s.LineDistance - ChargeSpeed * dt);
                    s.Tension *= Mathf.Exp(-2.5f * dt);
                    if (now >= s.NextHump)
                    {
                        s.NextHump = now + 0.3f;
                        FishingFx.FishSplash(at, 0.6f * scale);      // the bow wave
                    }
                    if (now >= s.SerpentUntil || s.LineDistance <= ChargeNearest)
                    {
                        s.Serpent = SerpentMove.Rear;
                        s.SerpentStart = now;
                        s.SerpentUntil = now + RearRise + RearHold + RearFall;
                        s.RearCrashed = false;
                        s.HookedFish?.Rear(player.transform.position, 0.6f * scale, RearRise, RearHold, RearFall);
                        FishingFx.FishSplash(at, 1.2f * scale);
                        AnglerSync.Fx(player, FishFx.Rear, 0.6f * scale);
                        GameCamera.instance?.AddShake(player.transform.position, 30f, 1.5f, false);
                        MessageHud.instance?.ShowBiomeFoundMsg($"{name} rears out of the water!", false);
                    }
                    return;

                case SerpentMove.Rear:
                    // reared up it can't pull: hauling back on it now tires it fast
                    s.Running = false;
                    s.StateTimer = Mathf.Max(s.StateTimer, 1f);
                    if (pulling && now < s.SerpentStart + RearRise + RearHold)
                        s.FishStamina = Mathf.Max(0f, s.FishStamina - FishStaminaDrain * PullTire * (RearPullTire - 1f) * dt);
                    if (!s.RearCrashed && now >= s.SerpentStart + RearRise + RearHold + RearFall * 0.8f) Crash(player, s, at, scale);
                    if (now >= s.SerpentUntil)
                    {
                        s.Serpent = SerpentMove.None;
                        s.NextSerpentMove = now + Random.Range(2.5f, 4.5f);
                    }
                    return;
            }
        }

        private static void StartCircle(FishingSession s, float now)
        {
            s.Serpent = SerpentMove.Circle;
            s.SerpentStart = now;
            s.SerpentUntil = now + Random.Range(4f, 6.5f);
            s.CircleDir = Random.value < 0.5f ? -1f : 1f;
            s.AngleSpeed = s.CircleDir;
            s.NextHump = now + 0.4f;
        }

        /// <summary>The reared serpent comes crashing down: spray, a shake and a jolt on the line.</summary>
        private static void Crash(Player player, FishingSession s, Vector3 at, float scale)
        {
            s.RearCrashed = true;
            FishingFx.FishSplash(at, 2.2f * scale);
            FishingFx.FishSplash(at + (player.transform.position - at).normalized * 2f, 1.4f * scale);
            AnglerSync.Fx(player, FishFx.Crash, scale);
            GameCamera.instance?.AddShake(player.transform.position, 30f, 2.2f, false);
            s.Tension += 20f;
        }

        /// <summary>Desperate: it lashes the water with its tail - a burst of spray and a hard jolt on the line.</summary>
        private static void TailSlap(Player player, FishingSession s, Vector3 at, float scale, float now, string name)
        {
            s.HookedFish?.Surface(0.25f * scale, 0.6f);
            FishingFx.FishSplash(at, 1.8f * scale);
            AnglerSync.Fx(player, FishFx.TailSlap, 0.25f * scale);
            GameCamera.instance?.AddShake(player.transform.position, 30f, 1f, false);
            s.Tension += 12f;
            s.NextSerpentMove = now + Random.Range(1.5f, 3f);
            Msg($"{name} lashes the water with its tail!");
        }
    }
}
