using HarmonyLib;
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Reflection;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>From the first nibble to the end of the fight: bites, the hookset, hook sizes, tension, wear and the line.</summary>
    internal static partial class FishingController
    {
        // ------------------------------------------------------------------
        // Hook size against fish size
        // ------------------------------------------------------------------

        private const float HookTooBigChance = 0.25f;   // hook chance multiplier when the fish is under the hook's range
        private const float HookRefuseFactor = 2.5f;     // fish this many times over the hook's max won't take it
        private const float HookStraightenRate = 0.04f;  // per second, per 100% overload, at tension 50

        /// <summary>The fish is so far over the hook's size that it won't take the bait at all.</summary>
        internal static bool HookFarTooSmall(HookDefinition? hook, float weightKg) =>
            hook != null && weightKg > hook.MaxKg * HookRefuseFactor;

        private static bool HookTooBig(HookDefinition? hook, float weightKg) => hook != null && weightKg < hook.MinKg;

        /// <summary>0 when the hook is big enough, rising as the fish outweighs it.</summary>
        private static float HookOverload(HookDefinition? hook, float weightKg) =>
            hook == null || hook.MaxKg <= 0f ? 0f : Mathf.Max(0f, weightKg / hook.MaxKg - 1f);

        /// <summary>The hook that's on the line goes with it when the line snaps, the rod breaks or the hook gives.</summary>
        private static void LoseHook(Player player, FishingSession s)
        {
            if (s.Lure != null)
            {
                // A lure goes with the line - unless it was already spent when the fish took it (boss lures).
                if (!LureUsedOnBite(s.Lure) && Tackle.LureOn(player)?.Id == s.Lure.Id) Tackle.UseOne(player, Tackle.HookSlot);
                if (s.Trailer != null) UseTrailer(player, s);
                return;
            }
            if (s.Hook != null && s.Hook.KeepChance > 0f && UnityEngine.Random.value < s.Hook.KeepChance)
            {
                player.Message(MessageHud.MessageType.TopLeft, $"Your {s.Hook.Name} held on.");
                return;
            }
            if (s.Hook != null && Tackle.ItemIn(player, Tackle.HookSlot)?.m_shared.m_name == ContentRegistry.HookDisplayName(s.Hook))
                Tackle.UseOne(player, Tackle.HookSlot);
        }

        internal static void Notify(string text) => Msg(text);

        /// <summary>
        /// Where the end of the line is: the float (or lure) where it lies in the water while waiting, or the hooked fish
        /// along the line during the fight.
        /// </summary>
        internal static Vector3 LineEnd(Player player, FishingSession s)
        {
            var pos = s.Phase == FishingPhase.Fighting ? player.transform.position + s.LineDir * s.LineDistance : s.FloatPos;
            pos.y = s.WaterY;
            return pos;
        }

        private static float FlatDistance(Vector3 a, Vector3 b) { a.y = b.y = 0f; return Vector3.Distance(a, b); }

        private const float MaxLineSlack = 0.3f;

        /// <summary>
        /// The float stays where it lies while you move about, like vanilla's: walk toward it and the line goes slack;
        /// walk (or reel) past the line you've let out and it's dragged after you. LineDistance is the line let out.
        /// </summary>
        private static void KeepFloat(Player player, FishingSession s)
        {
            Vector3 from = player.transform.position;
            Vector3 v = s.FloatPos - from; v.y = 0f;
            float d = v.magnitude;
            if (d > s.LineDistance && d > 0.01f)
            {
                var pulled = from + v / d * s.LineDistance;
                s.FloatPos = new Vector3(pulled.x, s.FloatPos.y, pulled.z);
                d = s.LineDistance;
            }
            if (d > 0.01f) { s.CastDir = v / Mathf.Max(d, 0.01f); s.Angle = 0f; }
            // vanilla's slack: none while the line is tight, up to 0.3 once you're half the line's length away or closer
            float L = Mathf.Max(0.1f, s.LineDistance);
            s.Slack = (1f - Mathf.Clamp01(Mathf.InverseLerp(L * 0.5f, L, d))) * MaxLineSlack;
        }

        /// <summary>Where the hooked fish (the end of the line) is right now.</summary>
        private static Vector3 FishPos(Player player, FishingSession s)
        {
            var pos = player.transform.position + s.LineDir * s.LineDistance;
            pos.y = s.WaterY;
            return pos;
        }

        private static float WaterLevel()
        {
            if (WaterLevelField != null && ZoneSystem.instance != null)
            {
                try { return (float)WaterLevelField.GetValue(ZoneSystem.instance); }
                catch { }
            }
            return FallbackWaterLevel;
        }

        private static bool TryFindWater(Player player, float maxDistanceOverride, out Vector3 dir, out Vector3 spot, out float distance, out float depth)
        {
            dir = player.GetLookDir();
            dir.y = 0f;
            if (dir.sqrMagnitude < 0.01f) dir = player.transform.forward;
            dir.y = 0f;
            dir.Normalize();

            spot = player.transform.position;
            distance = 0f;
            depth = 0f;

            if (ZoneSystem.instance == null) return false;

            float water = WaterLevel();
            float max = Mathf.Max(3.5f, maxDistanceOverride);

            for (float d = max; d >= 3f; d -= 1.5f)
            {
                Vector3 p = player.transform.position + dir * d;
                float ground = ZoneSystem.instance.GetGroundHeight(p);
                float dpt = water - ground;
                if (dpt >= MinCastDepth)
                {
                    spot = new Vector3(p.x, water, p.z);
                    distance = d;
                    depth = dpt;
                    return true;
                }
            }

            return false;
        }

        /// <summary>
        /// Valheim only reports the Ocean biome well clear of shore, so a cast at the coastline also counts as
        /// ocean if open ocean lies a short way further out along the cast direction.
        /// </summary>
        private static bool IsOceanAt(Vector3 landingSpot, Vector3 dir)
        {
            if (WorldGenerator.instance == null) return false;
            if (WorldGenerator.instance.GetBiome(landingSpot) == Heightmap.Biome.Ocean) return true;

            foreach (float frac in CoastalProbeFractions)
                if (WorldGenerator.instance.GetBiome(landingSpot + dir * (CoastalProbeDistance * frac)) == Heightmap.Biome.Ocean)
                    return true;

            return false;
        }


        // ------------------------------------------------------------------
        // Session tick
        // ------------------------------------------------------------------

        private static void Tick(Player player, FishingSession s, bool blocked)
        {
            // Right click ("Block") strikes and reels. Attack is avoided because the rod's base weapon plays
            // its own animation on it.
            bool blockDown = !blocked && ZInput.GetButtonDown("Block");

            if (s.Phase != FishingPhase.Fighting) { KeepFloat(player, s); _reelingNow = false; s.DragSlip = 0f; }
            Vector3 bobberPos = LineEnd(player, s);

            switch (s.Phase)
            {
                case FishingPhase.Waiting:
                    // Right click on a nibble is a strike too early; otherwise holding it works the line back in.
                    if (blockDown && FishApproach.TryEarlyStrike(s, bobberPos))
                    {
                        Msg("Too early! You spooked it.");
                    }
                    else if (!blocked && ZInput.GetButton("Block"))
                    {
                        _reelingNow = true;                    // the reel clicks while you work the line back too
                        if (!Retrieve(player, s)) return;
                        bobberPos = LineEnd(player, s);
                    }
                    if (s.Boss != null)
                    {
                        UpdateOmen(player, s, bobberPos);
                        if (_session == null || s.Phase != FishingPhase.Waiting) break;
                    }
                    CheckRealNearbyFish(bobberPos, s);
                    // A lure left sitting still draws no strikes: fish follow it but only hit it while it moves.
                    bool live = s.Lure == null || s.Boss != null || Time.time - s.LastMoved < LurePause;   // (a boss comes when it comes)
                    var biter = FishApproach.Update(s, s.Bobber, bobberPos, waiting: live);
                    if (biter != null)
                    {
                        s.Biter = biter;
                        SetBiterFish(s, biter.Fish, biter.WeightKg);
                        s.Phase = FishingPhase.Bite;
                        s.HookDeadline = Time.time + HookWindowSeconds * (1f + FishingBuffs.Total(player, BuffStat.HookWindow) + SkillHookWindow * Skill(player));
                        FishingFx.Bite(bobberPos);
                        Msg("FISH ON!  Right click to set the hook!");
                    }
                    break;

                case FishingPhase.Bite:
                    FishApproach.Update(s, s.Bobber, bobberPos, waiting: false);
                    if (blockDown)
                    {
                        TryHook(player, s, bobberPos);
                        if (_session == null) return;
                    }
                    else if (s.Biter != null && FishApproach.ScaredBy(s.Biter.Pos) != null)
                    {
                        LoseBiter(s, bobberPos, "Too much noise - the fish spat the bait.");
                    }
                    else if (Time.time > s.HookDeadline)
                    {
                        LoseBiter(s, bobberPos, "Too slow - the fish let go.");
                    }
                    break;

                case FishingPhase.Fighting:
                    FishApproach.Update(s, s.Bobber, bobberPos, waiting: false);
                    if (!Fight(player, s, blocked)) return;
                    break;
            }

            UpdateBobber(player, s);
        }

        /// <summary>
        /// Reels the line in with nothing on it (right click held while waiting): the float or lure comes back
        /// through the water. Ends the cast when it reaches you or the shallows. Returns false if the cast ended.
        /// </summary>
        private static bool Retrieve(Player player, FishingSession s)
        {
            // Run (Shift) held: wind straight in at full speed. A lure ripped in that fast draws no strikes.
            bool fast = ZInput.GetButton("Run");
            float speed = s.Rod.ReelSpeed * (fast ? 1f : RetrieveFraction) * (1f + FishingBuffs.Total(player, BuffStat.ReelSpeed));
            // Reeling takes up the slack first; only once the line is tight does the float (or lure) come in.
            s.LineDistance -= speed * Time.deltaTime;
            var before = s.FloatPos;
            KeepFloat(player, s);
            bool moved = (s.FloatPos - before).sqrMagnitude > 1e-6f;
            if (moved && !fast) s.LastMoved = Time.time;
            else if (fast && s.Lure != null) s.LastMoved = -100f;
            if (FlatDistance(player.transform.position, s.FloatPos) <= RetrieveEndDistance)
            {
                Finish(player, s.Lure != null ? "You work the lure all the way in." : "You reel in your line.");
                return false;
            }
            var p = s.FloatPos;
            if (ZoneSystem.instance != null)
            {
                float depth = WaterLevel() - ZoneSystem.instance.GetGroundHeight(p);
                if (depth < 0.4f)
                {
                    Finish(player, s.Lure != null ? "Your lure comes in to the shallows." : "You reel in your line.");
                    return false;
                }
                s.Depth = depth;
            }
            return true;
        }

        private static float _nextRealFishScan;

        /// <summary>A vanilla fish swimming near the float brings the next bite forward. Only reads positions.</summary>
        private static void CheckRealNearbyFish(Vector3 bobberPos, FishingSession s)
        {
            if (Time.time < _nextRealFishScan) return;
            _nextRealFishScan = Time.time + 1f;

            foreach (var updater in global::Fish.Instances)
            {
                if (updater is not global::Fish fish || fish == null) continue;
                if (Vector3.Distance(fish.transform.position, bobberPos) > RealFishNoticeRadius) continue;

                FishApproach.SpeedUp(s, RealFishBiteSpeedup);
                break;
            }
        }

        private static void TryHook(Player player, FishingSession s, Vector3 bobberPos)
        {
            float bonus = s.Bait?.HookBonus ?? 0f;
            float chance = Mathf.Clamp01(BaseHookChance + bonus + s.Rod.HookBonus + FishingBuffs.Total(player, BuffStat.HookChance) + SkillHookChance * Skill(player));
            bool tooBig = HookTooBig(s.Hook, s.FishWeight);
            if (tooBig) chance *= HookTooBigChance;
            if (s.Boss != null) { chance = 1f; tooBig = false; }

            if (UnityEngine.Random.value <= chance)
            {
                s.Phase = FishingPhase.Fighting;
                // From here the fight runs along the line from you to where the float is now.
                var toFloat = s.FloatPos - player.transform.position; toFloat.y = 0f;
                if (toFloat.sqrMagnitude > 0.01f) { s.CastDir = toFloat.normalized; s.Angle = 0f; s.LineDistance = toFloat.magnitude; }
                s.Tension = 18f;
                s.Running = false;
                s.StateTimer = UnityEngine.Random.Range(0.8f, 1.6f);

                // The biter's swimming visual hands over to the hooked-fish visual; everything else scatters.
                if (s.Biter != null) FishApproach.Remove(s, s.Biter);
                s.Biter = null;
                FishApproach.ScatterAll(s, bobberPos);

                if (ContentRegistry.FishItems.TryGetValue(s.Fish.Id, out var fishPrefab))
                {
                    s.HookedFish = HookedFishVisual.Create(fishPrefab, "fish_" + s.Fish.Id);
                    if (s.HookedFish != null) s.HookedFish.StayUnder = 0.05f;
                }

                if (s.BaitVisual != null)
                {
                    UnityEngine.Object.Destroy(s.BaitVisual.gameObject);
                    s.BaitVisual = null;
                }

                ConsumeBait(player, s);
                FishingFx.HookSet(bobberPos);
                if (s.Swirl != null) { UnityEngine.Object.Destroy(s.Swirl); s.Swirl = null; }
                s.FightPhase = 0;
                Msg(s.Boss != null ? $"{BossFish.Phrase(s.Fish.Name)} is hooked!" : "Hook set!");
            }
            else
            {
                LoseBiter(s, bobberPos, tooBig ? "Missed. The hook's too big for a fish that small." : "Missed the hook.");
            }
        }

        /// <summary>
        /// Same as vanilla: bait is only used up once a fish is actually hooked, so reeling in, a picky fish,
        /// a spooked fish or a missed bite all leave it on the hook. Takes one from the bait slot if it still
        /// holds the bait this cast was made with (the slot refills from the inventory when it runs out).
        /// </summary>
        private static void ConsumeBait(Player player, FishingSession s)
        {
            if (s.Bait == null) return;
            if (s.Lure != null)
            {
                // A boss lure is spent when its fish takes it; a trailer is eaten off any lure that gets a bite.
                if (LureUsedOnBite(s.Lure) && Tackle.LureOn(player)?.Id == s.Lure.Id) Tackle.UseOne(player, Tackle.HookSlot);
                if (s.Trailer != null) UseTrailer(player, s);
                return;
            }

            var item = Tackle.ItemIn(player, Tackle.BaitSlot);
            if (item != null && ContentRegistry.BaitByItemName.TryGetValue(item.m_shared.m_name, out var b) && b.Id == s.Bait.Id)
                Tackle.UseOne(player, Tackle.BaitSlot);
        }

        /// <summary>Takes one of the trailer this cast was made with from the bait slot, if it's still there.</summary>
        private static void UseTrailer(Player player, FishingSession s)
        {
            var item = Tackle.ItemIn(player, Tackle.BaitSlot);
            if (item != null && ContentRegistry.BaitByItemName.TryGetValue(item.m_shared.m_name, out var b) && b.Id == s.Trailer!.Id)
                Tackle.UseOne(player, Tackle.BaitSlot);
            s.Trailer = null;
        }

        /// <summary>
        /// A missed bite doesn't end the cast, same as vanilla: the fish that had the bait swims off and the
        /// line keeps fishing - any other fish around can still come in, or new ones wander up later.
        /// </summary>
        private static void LoseBiter(FishingSession s, Vector3 bobberPos, string reason)
        {
            if (s.Biter != null) FishApproach.Leave(s.Biter, bobberPos);
            s.Biter = null;
            s.Phase = FishingPhase.Waiting;
            if (s.Boss != null)
            {
                reason = $"{BossFish.Phrase(s.Fish.Name)} spits the lure and sinks back into the deep.";
                BossGone(s);
            }
            foreach (var o in s.Suitors)
                if (o.State == SuitorState.Wander) o.DecideTime = Mathf.Max(o.DecideTime, Time.time + UnityEngine.Random.Range(2f, 5f));
            Msg(reason);
        }

        /// <summary>
        /// Rod wear while a fish is on: heavier fish and higher tension wear it faster, a stronger rod (Power)
        /// slower, so loose drag is kinder to the rod. Roughly: an 8 kg pike costs a wooden rod ~8 durability,
        /// a 90 kg tuna about 55 from an Ashwood rod. Returns true if the rod just broke.
        /// </summary>
        private static bool WearRod(FishingSession s, float dt)
        {
            var item = s.RodItem;
            if (item == null || !item.m_shared.m_useDurability || VdwConfig.RodWear.Value <= 0f) return false;

            float wear = RodWearPerKgSecond * VdwConfig.RodWear.Value * FishingBuffs.Reduction(Player.m_localPlayer, BuffStat.RodWear) * s.FishWeight / Mathf.Max(0.1f, s.Rod.Power) * (s.Tension / 50f);
            item.m_durability = Mathf.Max(0f, item.m_durability - wear * dt);

            if (!s.WornWarned && item.m_durability < item.GetMaxDurability() * 0.2f)
            {
                s.WornWarned = true;
                Msg("Your rod is creaking. It won't take much more.");
            }
            return item.m_durability <= 0f;
        }

        private const float MaxLineAngle = 55f;          // how far off the cast line a fish can drag it
        private const float LeapChancePerSecond = 0.08f; // while running, scaled up for stronger fish

        /// <summary>
        /// Runs pull the fish off to one side, so the line swings instead of only tugging straight out; it
        /// turns away from the bank. Big runs can end in a leap clear of the water with a head shake that
        /// spikes the tension.
        /// </summary>
        private static void UpdateRunPath(Player player, FishingSession s, float dt, bool exhausted)
        {
            float strength = Mathf.Max(0.1f, s.Fish.FightStrength);

            if (s.Running)
            {
                if (Mathf.Abs(s.AngleSpeed) < 1f) // a new run: pick a side
                    s.AngleSpeed = (UnityEngine.Random.value < 0.5f ? -1f : 1f) * UnityEngine.Random.Range(6f, 12f) * Mathf.Sqrt(strength);
            }
            else
            {
                // Resting: the line slowly swings back in line with you.
                s.AngleSpeed = 0f;
                s.Angle = Mathf.MoveTowards(s.Angle, 0f, 4f * dt);
            }

            if (s.AngleSpeed != 0f)
            {
                float next = Mathf.Clamp(s.Angle + s.AngleSpeed * dt, -MaxLineAngle, MaxLineAngle);
                var p = player.transform.position + Quaternion.AngleAxis(next, Vector3.up) * s.CastDir * s.LineDistance;
                bool shore = ZoneSystem.instance != null && ZoneSystem.instance.GetGroundHeight(p) > s.WaterY - 0.6f;
                if (shore || Mathf.Abs(next) >= MaxLineAngle) s.AngleSpeed = -s.AngleSpeed;
                else s.Angle = next;
            }

            if (s.LeapEnd > 0f && Time.time >= s.LeapEnd)
            {
                s.LeapEnd = 0f;
                FishingFx.FishSplash(FishPos(player, s), 0.6f + s.FishWeight / 15f);
            }
            if (s.LeapEnd <= 0f && s.Running && !exhausted && UnityEngine.Random.value < LeapChancePerSecond * Mathf.Sqrt(strength) * PhaseLeap(s) * dt)
            {
                float height = Mathf.Clamp(0.6f + s.FishWeight / 30f, 0.6f, 2f);
                float duration = Mathf.Lerp(0.7f, 1.2f, height / 2f);
                s.LeapEnd = Time.time + duration;
                s.HookedFish?.Leap(height, duration);
                s.Tension += 8f; // head shake at the top of the leap
                FishingFx.FishSplash(FishPos(player, s), 0.5f + s.FishWeight / 20f);
            }
        }

        /// <summary>Runs one fight step. Returns false if the session ended.</summary>
        private static bool Fight(Player player, FishingSession s, bool blocked)
        {
            float dt = Time.deltaTime;
            float strength = Mathf.Max(0.1f, s.Fish.FightStrength);

            bool reeling = !blocked && ZInput.GetButton("Block");

            // Reeling costs your own stamina, more for stronger fish; you can't reel with none left.
            if (reeling && player.GetStamina() > 0.01f)
            {
                player.UseStamina((PlayerStaminaDrain + strength * PlayerStaminaPerStrength) * s.Rod.StaminaUse * FishingBuffs.Reduction(player, BuffStat.ReelStamina) * Mathf.Lerp(1f, SkillMinStamina, Skill(player)) * dt);
            }
            else if (reeling)
            {
                reeling = false;
            }

            _reelingNow = reeling;
            bool exhausted = s.FishStamina <= 0f;
            float drag = Mathf.Clamp01(s.Drag);

            // Fish alternates between resting and making a run.
            s.StateTimer -= dt;
            if (s.StateTimer <= 0f)
            {
                s.Running = !s.Running && !exhausted;
                if (s.Running) FishingFx.FishSplash(FishPos(player, s), 0.5f + s.FishWeight / 20f);
                s.StateTimer = s.Running ? UnityEngine.Random.Range(1.5f, 3.0f) : UnityEngine.Random.Range(2.0f, 4.0f);
            }
            if (exhausted) s.Running = false;

            if (s.Running && Time.time >= s.NextSplash)
            {
                s.NextSplash = Time.time + UnityEngine.Random.Range(0.8f, 1.8f);
                FishingFx.FishSplash(FishPos(player, s), 0.4f + s.FishWeight / 25f);
            }

            if (s.Fish.Legendary)
                UpdateLegendaryPhase(player, s, s.FishStaminaMax > 0f ? Mathf.Clamp01(s.FishStamina / s.FishStaminaMax) : 0f, exhausted, strength);

            UpdateRunPath(player, s, dt, exhausted);

            float tensionMult = Mathf.Lerp(DragTensionLoose, DragTensionTight, drag);
            float reelMult = Mathf.Lerp(DragReelLoose, DragReelTight, drag);
            float staminaMult = Mathf.Lerp(DragStaminaLoose, DragStaminaTight, drag);
            float runLineMult = Mathf.Lerp(DragRunLineLoose, DragRunLineTight, drag);

            // Tension
            float pull = s.Running ? (6f + strength * 4f) : (1f + strength * 1.2f);
            if (exhausted) pull *= 0.3f;
            pull *= PhasePull(s);
            pull *= tensionMult * FishingBuffs.Reduction(player, BuffStat.Tension) / Mathf.Max(0.1f, s.Rod.Power);

            float delta = pull - LineRelaxRate;
            if (reeling) delta += ReelTensionLoad;

            s.Tension = Mathf.Clamp(s.Tension + delta * dt, 0f, MaxTension);

            if (WearRod(s, dt))
            {
                RodMotion.Trigger(RodEvent.Snap);
                FishingFx.LineSnap(FishPos(player, s));
                LoseHook(player, s);
                Finish(player, $"Your rod broke! The {s.Fish.Name} got away.");
                return false;
            }

            // A fish heavier than the hook is rated for can straighten it; the harder it pulls, the likelier.
            float overload = HookOverload(s.Hook, s.FishWeight);
            float straighten = s.Hook != null && s.Hook.NeverStraightens ? 0f : HookStraightenRate * Mathf.Max(0f, 1f - FishingBuffs.Total(player, BuffStat.HookStraighten));
            if (overload > 0f && UnityEngine.Random.value < straighten * overload * (s.Tension / 50f) * dt)
            {
                FishingFx.LineSnap(FishPos(player, s));
                LoseHook(player, s);
                Finish(player, $"The hook straightened! The {s.Fish.Name} was too big for it.");
                return false;
            }

            // Line and stamina
            float freshness = s.FishStaminaMax > 0f ? Mathf.Clamp01(s.FishStamina / s.FishStaminaMax) : 0f;

            if (reeling)
            {
                float eff = Mathf.Lerp(1f, 0.35f, freshness) * reelMult;
                if (s.Running) eff *= 0.4f;
                s.LineDistance -= s.Rod.ReelSpeed * (1f + FishingBuffs.Total(player, BuffStat.ReelSpeed)) * Mathf.Lerp(1f, SkillMaxReel, Skill(player)) * eff * dt;

                // Vanilla raises Fishing every second of reeling, twice as fast with a fish on.
                s.SkillTimer += dt * 2f;
                if (s.SkillTimer >= 1f)
                {
                    s.SkillTimer = 0f;
                    player.RaiseSkill(Skills.SkillType.Fishing);
                }

                float drain = FishStaminaDrain * (0.5f + s.Tension / 50f) * (s.Running ? 1.5f : 1f) * staminaMult;
                s.FishStamina = Mathf.Max(0f, s.FishStamina - drain * dt);
            }
            else
            {
                // Resting on the line lets a fish get its wind back; a legendary on a slack line recovers fast.
                float recover = 0.5f + (s.Fish.Legendary && s.Tension < 10f ? 2.5f : 0f);
                s.FishStamina = Mathf.Min(s.FishStaminaMax, s.FishStamina + recover * dt);
            }

            float payout = s.Running ? strength * 1.2f * runLineMult : 0f;
            if (s.Running) s.LineDistance += payout * dt;
            // the drag sings: a running fish pulling line out against it, or reeling with the drag set too loose to hold
            float loose = reeling ? Mathf.Clamp01((0.35f - drag) / 0.35f) : 0f;
            s.DragSlip = Mathf.Max(Mathf.Clamp01(payout / 2.5f), loose);
            s.LineDistance = Mathf.Max(0f, s.LineDistance);

            // Slack line lets a fresh fish throw the hook.
            if (s.Tension < 5f && !exhausted) s.SlackTime += dt; else s.SlackTime = 0f;

            if (s.Tension >= s.Rod.BreakTension)
            {
                RodMotion.Trigger(RodEvent.Snap);
                FishingFx.LineSnap(FishPos(player, s));
                LoseHook(player, s);
                Finish(player, "The line snapped! You lost the hook.");
                return false;
            }
            if (s.SlackTime > 5f)
            {
                Finish(player, "The hook slipped free.");
                return false;
            }
            if (s.LineDistance > s.MaxLine)
            {
                RodMotion.Trigger(RodEvent.Snap);
                FishingFx.LineSnap(FishPos(player, s));
                LoseHook(player, s);
                Finish(player, "The fish took all your line, hook and all.");
                return false;
            }
            // Landed when it's close, or when reeling has dragged it out of the water onto the bank (from a high bank
            // the last couple of metres would otherwise be under the ground at your feet).
            var fishAt = player.transform.position + s.LineDir * s.LineDistance;
            bool ashore = reeling && ZoneSystem.instance != null && ZoneSystem.instance.GetGroundHeight(fishAt) > s.WaterY - 0.3f;
            if (s.LineDistance <= 2f || ashore)
            {
                // Whatever happens while handing out the catch, the cast ends (else it would retry every frame).
                try { Catch(player, s); }
                catch { EndSession(); throw; }
                return false;
            }

            return true;
        }

        private static void UpdateBobber(Player player, FishingSession s)
        {
            Vector3 pos = LineEnd(player, s);

            if (s.Bobber != null)
            {
                s.Bobber.Position = pos;
                s.Bobber.Slack = s.Phase == FishingPhase.Fighting ? 0f : s.Slack;
                s.Bobber.Dipped = s.Phase == FishingPhase.Bite || Time.time < s.ShudderUntil;
                s.Bobber.Thrashing = s.Phase == FishingPhase.Fighting && s.Running;
            }

            if (s.HookedFish != null)
            {
                s.HookedFish.Position = pos + Vector3.down * 0.15f;
                s.HookedFish.Intensity = s.Running ? 1f : 0.25f;
            }

            if (s.BaitVisual != null)
            {
                s.BaitVisual.Position = pos + Vector3.down * 0.15f;
                s.BaitVisual.Intensity = 0.1f;
            }
        }

    }
}
