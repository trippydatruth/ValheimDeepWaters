using System;
using System.Collections.Generic;
using System.Globalization;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// A line left out on a rod set in a rod holder (RodHolders.cs). It is an ordinary cast (FishingSession) ticked by
    /// the same code as the one in your hands, but with nobody's input, from the holder's rod tip (s.Anchor), and quiet:
    /// its messages, rod moves and shared effects go to the holder (ParkedLines) instead of the angler. A circle hook
    /// left alone sets itself as usual; a fish hooked with nobody at the rod runs against the drag that was set and,
    /// unless someone picks the rod up, strips the line or throws the hook. Anyone can pick the rod up and carry on.
    /// </summary>
    internal static partial class FishingController
    {
        /// <summary>True while a holder's line is being ticked: messages, rod moves and shared effects are the holder's.</summary>
        internal static bool Quiet { get; private set; }

        /// <summary>The cast in the local player's hands, if any.</summary>
        internal static FishingSession? HandSession => _session;

        /// <summary>A prepaid cast that ended (landed, reeled in, lost): what's left of its tackle, for whoever gets it.</summary>
        internal static Action<FishingSession>? PrepaidEnded;

        /// <summary>
        /// Sets the line in your hands down in a holder: the tackle on it (hook or lure, bait, trailer, weight, leader) is
        /// taken off you now, as it's on the line; the line runs from <paramref name="tip"/> from here on. Null (and a
        /// message) if it can't be: no line out, a fish on, or a boss lure.
        /// </summary>
        internal static FishingSession? Park(Player player, Vector3 tip, out string why)
        {
            why = "";
            var s = _session;
            if (s == null) { why = "No line out."; return null; }
            if (s.Phase == FishingPhase.Fighting) { why = "Not with a fish on!"; return null; }
            if (s.Boss != null || (s.Lure != null && LureUsedOnBite(s.Lure))) { why = "A boss lure has to be fished by hand."; return null; }
            if (s.Bobber != null && s.Bobber.InFlight != null) { why = "Let the cast land first."; return null; }

            string Take(int slot, Func<ItemDrop.ItemData, bool> matches)
            {
                var item = Tackle.ItemIn(player, slot);
                if (item == null || !matches(item)) return "";
                string name = item.m_dropPrefab != null ? item.m_dropPrefab.name : "";
                Tackle.UseOne(player, slot);
                return name;
            }
            if (s.Lure != null)
            {
                s.PaidHook = Take(Tackle.HookSlot, i => Tackle.LureOn(player)?.Id == s.Lure.Id);
                if (s.Trailer != null) s.PaidTrailer = Take(Tackle.BaitSlot, i => ContentRegistry.BaitByItemName.TryGetValue(i.m_shared.m_name, out var b) && b.Id == s.Trailer.Id);
            }
            else
            {
                if (s.Hook != null) s.PaidHook = Take(Tackle.HookSlot, i => i.m_shared.m_name == ContentRegistry.HookDisplayName(s.Hook));
                if (s.Bait != null) s.PaidBait = Take(Tackle.BaitSlot, i => ContentRegistry.BaitByItemName.TryGetValue(i.m_shared.m_name, out var b) && b.Id == s.Bait.Id);
            }
            if (s.Weight != null) s.PaidWeight = Take(Tackle.WeightSlot, i => Tackle.WeightOn(player)?.Id == s.Weight.Id);
            if (s.Leader) s.PaidLeader = Take(Tackle.LeaderSlot, i => true);
            s.Prepaid = true;
            s.Anchor = tip;
            s.RodItem = null;
            s.Pulling = false;
            if (s.Phase == FishingPhase.Bite) s.HookDeadline = Mathf.Max(s.HookDeadline, Time.time + 0.5f);
            _session = null;
            _reelingNow = false;
            return s;
        }

        /// <summary>
        /// One frame of a line left in a holder, ticked by its owner. <paramref name="tip"/>: the holder's rod tip now.
        /// Returns false once the line has ended (landed nothing, lost the fish, snapped) - its tackle has gone to PrepaidEnded.
        /// </summary>
        internal static bool TickParked(Player player, FishingSession s, Vector3 tip)
        {
            var hand = _session; bool reeling = _reelingNow, quiet = Quiet;
            _session = s; Quiet = true;
            try
            {
                s.Anchor = tip;
                if (s.Phase == FishingPhase.Fighting)
                {
                    FishApproach.Update(s, s.Bobber, LineEnd(player, s), waiting: false);
                    UnattendedFight(player, s);
                    if (_session == s) UpdateBobber(player, s);
                }
                else Tick(player, s, blocked: true);
                return _session == s;
            }
            catch (Exception ex) { ReportError(ex); return _session == s; }
            finally { _session = hand; _reelingNow = reeling; Quiet = quiet; }
        }

        /// <summary>
        /// A fish on with nobody at the rod: it runs, taking line against the drag that was set, rests, runs again - and
        /// strips the line if it runs it all out, or throws the hook after a while if nobody comes.
        /// </summary>
        private static void UnattendedFight(Player player, FishingSession s)
        {
            float now = Time.time, dt = Time.deltaTime;
            if (s.UnattendedUntil <= 0f) s.UnattendedUntil = now + UnityEngine.Random.Range(25f, 45f) / Mathf.Max(0.6f, s.Fish.FightStrength);
            s.StateTimer -= dt;
            if (s.StateTimer <= 0f)
            {
                s.Running = !s.Running;
                s.StateTimer = s.Running ? UnityEngine.Random.Range(1.5f, 3.5f) : UnityEngine.Random.Range(1.5f, 4f);
                if (s.Running) { s.AngleSpeed = UnityEngine.Random.Range(-14f, 14f); FishingFx.FishSplash(LineEnd(player, s), 0.6f + 0.3f * s.Fish.FightStrength); }
            }
            s.Tension = s.Running ? 55f : 25f;
            if (s.Running)
            {
                // a loose drag lets it run off freely, a tight one holds it back
                s.LineDistance += dt * (1.5f + s.Fish.FightStrength) * Mathf.Lerp(1.6f, 0.4f, s.Drag);
                s.Angle = Mathf.Clamp(s.Angle + s.AngleSpeed * dt, -60f, 60f);
                s.DragSlip = 1f;
            }
            else s.DragSlip = 0f;

            if (s.LineDistance >= s.MaxLine)
            {
                FishingFx.LineSnap(LineEnd(player, s));
                LoseHook(player, s);
                Finish(player, "It took all the line.");
            }
            else if (now > s.UnattendedUntil)
            {
                FishingFx.FishSplash(LineEnd(player, s), 1f);
                Finish(player, "It threw the hook.");
            }
        }

        /// <summary>
        /// Picks up a rod whose line is out: <paramref name="s"/> becomes the cast in your hands, with
        /// <paramref name="rod"/> (already in hand) as its rod. A fish on is now yours to fight from where you stand.
        /// </summary>
        internal static void TakeOver(Player player, FishingSession s, ItemDrop.ItemData rod)
        {
            Vector3 from = s.Anchor ?? player.transform.position;
            Vector3 end = s.Phase == FishingPhase.Fighting ? from + s.LineDir * s.LineDistance : s.FloatPos;
            s.Anchor = null;
            s.RodItem = rod;
            if (ContentRegistry.GetRod(rod) is RodDefinition def) s.Rod = Tackle.EffectiveRod(player, def, rod.m_quality);
            s.UnattendedUntil = 0f;
            var v = end - player.transform.position; v.y = 0f;
            float d = Mathf.Max(1f, v.magnitude);
            if (v.sqrMagnitude > 0.01f) { s.CastDir = v.normalized; s.Angle = 0f; }
            s.LineDistance = Mathf.Max(s.Phase == FishingPhase.Fighting ? 0f : s.LineDistance, d);
            s.StartDistance = Mathf.Max(s.StartDistance, d);
            if (s.Phase == FishingPhase.Fighting) { s.Tension = 30f; s.Running = false; s.StateTimer = 1f; }
            s.Drag = _dragLevel;
            _session = s;
            Msg(s.Phase == FishingPhase.Fighting ? $"You grab the rod - {s.Fish.Name} on!" : s.Phase == FishingPhase.Bite ? "You grab the rod - strike!" : "You take up the rod.");
        }

        /// <summary>A prepaid cast's tackle that's left (not eaten, lost or snapped off), as prefab names and counts.</summary>
        internal static List<(string prefab, int n)> PrepaidLeft(FishingSession s)
        {
            var left = new List<(string, int)>();
            void Add(string p, bool gone) { if (!gone && !string.IsNullOrEmpty(p)) left.Add((p, 1)); }
            Add(s.PaidHook, s.HookLost);
            Add(s.PaidBait, s.BaitUsed || s.HookLost);
            Add(s.PaidTrailer, s.TrailerUsed || s.HookLost);
            Add(s.PaidWeight, s.RigLost);
            Add(s.PaidLeader, s.RigLost);
            return left;
        }

        /// <summary>Gives tackle back to a player (inventory, else at their feet).</summary>
        internal static void GiveBack(Player player, List<(string prefab, int n)> items)
        {
            foreach (var (prefab, n) in items)
            {
                var go = ObjectDB.instance?.GetItemPrefab(prefab);
                var drop = go != null ? go.GetComponent<ItemDrop>() : null;
                if (drop != null) Drops.Give(player, drop, n, player.transform.position + Vector3.up * 0.5f);
            }
        }

        // ------------------------------------------------------------------ a line, written to and read back from the holder

        /// <summary>Everything needed to carry a line on: what's on it, where it lies, and the fish if one's on.</summary>
        internal static byte[] Save(FishingSession s)
        {
            var p = new ZPackage();
            p.Write(2);   // 2: + IceHole
            p.Write(s.Lure != null ? s.Lure.Id : ""); p.Write(s.Lure == null && s.Bait != null ? s.Bait.Id : ""); p.Write(s.Trailer?.Id ?? "");
            p.Write(s.Lure == null && s.Hook != null ? s.Hook.Id : ""); p.Write(s.Weight?.Id ?? ""); p.Write(s.Leader);
            p.Write(s.BaitDepth); p.Write(s.RigInterest); p.Write(s.RigName ?? "");
            p.Write(s.Spot); p.Write(s.FloatPos); p.Write(s.CastDir); p.Write(s.LineDistance); p.Write(s.StartDistance);
            p.Write(s.WaterY); p.Write(s.Depth); p.Write(s.Ocean); p.Write((int)s.Biome); p.Write(s.Drag);
            p.Write((int)s.Phase); p.Write(s.Fish?.Id ?? ""); p.Write(s.FishWeight); p.Write(s.Variant);
            p.Write(s.FishStamina); p.Write(s.FishStaminaMax); p.Write(s.Angle);
            p.Write(s.PaidHook); p.Write(s.PaidBait); p.Write(s.PaidTrailer); p.Write(s.PaidWeight); p.Write(s.PaidLeader);
            p.Write(s.BaitUsed); p.Write(s.TrailerUsed); p.Write(s.HookLost); p.Write(s.RigLost);
            p.Write(s.IceHole);
            return p.GetArray();
        }

        /// <summary>
        /// A line read back from its holder (another player's, or one left out while nobody was near), with its float,
        /// bait and fish around it again. A bite that was under way is lost; a fish on is still on.
        /// </summary>
        internal static FishingSession? Load(byte[] data, Player player, ItemDrop.ItemData? rodItem, Vector3 tip)
        {
            try
            {
                var p = new ZPackage(data);
                int version = p.ReadInt();
                if (version < 1 || version > 2) return null;
                string lureId = p.ReadString(), baitId = p.ReadString(), trailerId = p.ReadString(), hookId = p.ReadString(), weightId = p.ReadString();
                bool leader = p.ReadBool();
                float baitDepth = p.ReadSingle(), rigInterest = p.ReadSingle(); string rigName = p.ReadString();
                Vector3 spot = p.ReadVector3(), floatPos = p.ReadVector3(), castDir = p.ReadVector3();
                float lineDist = p.ReadSingle(), startDist = p.ReadSingle(), waterY = p.ReadSingle(), depth = p.ReadSingle();
                bool ocean = p.ReadBool(); var biome = (Heightmap.Biome)p.ReadInt(); float drag = p.ReadSingle();
                var phase = (FishingPhase)p.ReadInt(); string fishId = p.ReadString(); float fishW = p.ReadSingle(); int variant = p.ReadInt();
                float stam = p.ReadSingle(), stamMax = p.ReadSingle(), angle = p.ReadSingle();

                ContentRegistry.Baits.TryGetValue(lureId, out var lure);
                ContentRegistry.Baits.TryGetValue(lureId.Length > 0 ? lureId : baitId, out var bait);
                ContentRegistry.Baits.TryGetValue(trailerId, out var trailer);
                ContentRegistry.Hooks.TryGetValue(hookId, out var hook);
                ContentRegistry.Tackle.TryGetValue(weightId, out var weight);
                var rodDef = ContentRegistry.GetRod(rodItem) ?? (ContentRegistry.Rods.Count > 0 ? ContentRegistry.Rods[0] : null);
                if (rodDef == null || !ContentRegistry.Fish.TryGetValue(fishId, out var fish)) return null;

                var s = new FishingSession
                {
                    Fish = fish, Bait = bait, Lure = lure, Trailer = trailer, Hook = lure != null ? LureHook(lure) : hook,
                    Weight = weight, Leader = leader, BaitDepth = baitDepth, RigInterest = rigInterest, RigName = rigName,
                    Rod = rodItem != null ? Tackle.EffectiveRod(player, rodDef, rodItem.m_quality) : rodDef, RodItem = null,
                    Spot = spot, FloatPos = floatPos, CastDir = castDir, LineDistance = lineDist, StartDistance = startDist,
                    WaterY = waterY, Depth = depth, Ocean = ocean, Biome = biome, Drag = drag, LastMoved = Time.time,
                    Phase = phase == FishingPhase.Fighting ? FishingPhase.Fighting : FishingPhase.Waiting,
                    Anchor = tip, Prepaid = true,
                };
                s.PaidHook = p.ReadString(); s.PaidBait = p.ReadString(); s.PaidTrailer = p.ReadString(); s.PaidWeight = p.ReadString(); s.PaidLeader = p.ReadString();
                s.BaitUsed = p.ReadBool(); s.TrailerUsed = p.ReadBool(); s.HookLost = p.ReadBool(); s.RigLost = p.ReadBool();
                if (version >= 2) s.IceHole = p.ReadBool();
                SetBiterFish(s, fish, fishW, standIn: s.Phase != FishingPhase.Fighting);
                s.FishWeight = fishW; s.Variant = variant;
                if (s.Phase == FishingPhase.Fighting) { s.FishStamina = stam; s.FishStaminaMax = stamMax; s.Angle = angle; s.StateTimer = 1f; }

                s.Bobber = BobberVisual.Create(floatPos, hidden: lure != null || weight != null);
                if (s.Phase == FishingPhase.Fighting)
                {
                    if (ContentRegistry.FishItems.TryGetValue(fish.Id, out var fishPrefab))
                    {
                        s.HookedFish = HookedFishVisual.Create(fishPrefab, ContentRegistry.ModelKeyFor(fish), BossFish.ScaleFor(fish.Id) * FishSize.ModelScale(fish, fishW));
                        if (s.HookedFish != null) s.HookedFish.StayUnder = 0.05f;
                        RareFish.TintModel(s.HookedFish?.gameObject, variant);
                    }
                }
                else
                {
                    if (bait != null && !s.BaitUsed && ContentRegistry.BaitItems.TryGetValue(bait.Id, out var baitPrefab))
                    {
                        s.BaitVisual = HookedFishVisual.Create(baitPrefab, ContentRegistry.BaitModelKey(bait.Id));
                        if (s.BaitVisual != null) { s.BaitVisual.StayUnder = weight != null ? 0.6f : lure != null ? 0.3f : 0.05f; s.BaitVisual.SetOnHook(); }
                    }
                    if (!s.BaitUsed || lure != null)
                        FishApproach.Spawn(s, spot, RollWait(bait, spot, trailer, ocean, depth, biome), false);
                }
                return s;
            }
            catch (Exception ex)
            {
                Plugin.Log.LogWarning($"Rod holder: couldn't read its line back ({ex.Message}).");
                return null;
            }
        }

        /// <summary>Drops a line's visuals without ending it (another player has it now, or the holder unloaded).</summary>
        internal static void DropVisuals(FishingSession s)
        {
            if (s.Bobber != null) UnityEngine.Object.Destroy(s.Bobber.gameObject);
            if (s.HookedFish != null) UnityEngine.Object.Destroy(s.HookedFish.gameObject);
            if (s.BaitVisual != null) UnityEngine.Object.Destroy(s.BaitVisual.gameObject);
            if (s.Swirl != null) UnityEngine.Object.Destroy(s.Swirl);
            FishApproach.DestroyAll(s);
            s.Bobber = null; s.HookedFish = null; s.BaitVisual = null; s.Swirl = null;
        }
    }
}
