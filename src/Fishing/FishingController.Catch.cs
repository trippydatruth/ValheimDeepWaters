using HarmonyLib;
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Reflection;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>Landing a fish, ending a cast, and the messages that go with them.</summary>
    internal static partial class FishingController
    {
        // ------------------------------------------------------------------
        // Results
        // ------------------------------------------------------------------

        private static void Catch(Player player, FishingSession s)
        {
            string text = Land(player, s, FishPos(player, s), "Caught");
            RodMotion.Trigger(RodEvent.CatchLift);
            FishingFx.Landing(FishPos(player, s));
            Msg(text);
            EndSession();
        }

        /// <summary>
        /// A fish landed, however it was caught (rod or spear, SpearFishing): drops it (weight, size class, variant), any find
        /// inside it, and credits the Fishing skill, catch log, biome sets, mastery, rank and news. Returns the message.
        /// <paramref name="at"/>: where it came out of the water (for the splash).
        /// </summary>
        internal static string Land(Player player, FishingSession s, Vector3 at, string verb)
        {
            string text = $"{verb} {s.Fish.Name}!  ({Units.Kg(s.FishWeight, "0.0")})";

            float range = s.Fish.MaxWeightKg - s.Fish.MinWeightKg;
            float rank = range > 0.001f ? (s.FishWeight - s.Fish.MinWeightKg) / range : 0f;
            bool baitfish = !string.IsNullOrWhiteSpace(s.Fish.CatchBait);
            if (rank >= TrophyThreshold && !baitfish) text += "\nA trophy catch!";

            // Dropped in front of you as a real pickup (vanilla auto-pickup collects it), or straight into your bag
            // when you're fishing from a boat.
            if (baitfish)
            {
                var bait = ContentRegistry.BaitItems.TryGetValue(s.Fish.CatchBait, out var bp) ? bp.GetComponent<ItemDrop>() : null;
                if (bait != null)
                {
                    int n = Mathf.Max(1, s.Fish.CatchAmount);
                    Vector3 dropPos = Drops.CatchPos(player);
                    Drops.Give(player, bait, n, dropPos);
                    text += $"\n+{n} {Loc.Text(bait.m_itemData.m_shared.m_name)}";
                }
            }
            else if (ContentRegistry.DropFor(s.Fish) is ItemDrop drop)
            {
                var data = drop.m_itemData.Clone();
                data.m_stack = 1;
                data.m_customData = new Dictionary<string, string>(data.m_customData ?? new Dictionary<string, string>());
                data.m_customData["vdw_weight_kg"] = s.FishWeight.ToString("0.00", CultureInfo.InvariantCulture);
                data.m_customData["vdw_caught_by"] = player.GetPlayerName();
                // for Hildir's bounties: the weather and time it was caught in
                if (EnvMan.instance != null)
                {
                    data.m_customData["vdw_caught_rain"] = EnvMan.IsWet() ? "1" : "0";
                    data.m_customData["vdw_caught_night"] = EnvMan.IsNight() ? "1" : "0";
                }
                // Size class as the item's quality: shown on the icon, sizes don't stack together (so a
                // trophy keeps its weight), and item stands show bigger classes bigger.
                data.m_quality = FishSize.ClassFor(rank);
                data.m_variant = s.Variant;   // golden / albino: picks its tinted icon, and it never stacks with ordinary ones

                Vector3 dropPos = Drops.CatchPos(player);
                bool inBag = Drops.Give(player, drop, data, 1, dropPos);
                text += inBag ? (Drops.IntoBag ? "\nInto your bag." : "\nLanded!") : Drops.IntoBag ? "\nYour bag is full - it's at your feet." : "\nLanded! Pick it up.";
                if (data.m_quality >= FishSize.MaxClass) text += FishMaterials.GiveTrophyFin(player, Drops.CatchPos(player, 0.4f));

                // Legendaries: a trophy the first time; bosses also leave a material and the news goes out.
                if (s.Fish.Legendary) text += BossFish.OnLanded(player, s.Fish, dropPos);

                // Vanilla fish keep their own extra drops, like vanilla fishing (into the bag too, from a boat).
                if (s.Fish.IsVanilla && ContentRegistry.FishItems.TryGetValue(s.Fish.Id, out var fishPrefab))
                {
                    var extras = fishPrefab.GetComponent<global::Fish>()?.m_extraDrops;
                    if (extras != null)
                        foreach (var extra in extras.GetDropList())
                        {
                            var extraDrop = extra != null ? extra.GetComponent<ItemDrop>() : null;
                            if (extraDrop != null) Drops.Give(player, extraDrop, 1, dropPos + Vector3.up * 0.3f);
                            else if (extra != null) UnityEngine.Object.Instantiate(extra, dropPos + Vector3.up * 0.3f, Quaternion.identity);
                        }
                }

                CountForAchievements(s, data.m_quality);
            }
            else
            {
                Plugin.Log.LogWarning($"No item prefab registered for fish '{s.Fish.Id}'; nothing was dropped.");
            }

            // Rarely, something else comes up inside the fish.
            var find = FishingBuffs.RollFind(s) ?? Rewards.RollFind(s);   // a relic first, else now and then a valuable
            var findDrop = find != null ? find.GetComponent<ItemDrop>() : null;
            if (findDrop != null)
            {
                Vector3 findPos = Drops.CatchPos(player, 0.6f);
                Drops.Give(player, findDrop, 1, findPos);
                text += $"\nSomething glints inside it... {Loc.Text(findDrop.m_itemData.m_shared.m_name)}!";
            }

            // Landing a fish is worth more Fishing skill the harder it fights.
            player.RaiseSkill(Skills.SkillType.Fishing, 1f + Mathf.Max(0f, s.Fish.FightStrength));

            int pointsBefore = AnglerRanks.Points(player);
            int countBefore = Mastery.Count(player, s.Fish.Id);
            CatchLog.Record(player, s.Fish.Id, s.FishWeight, out bool newSpecies, out bool newRecord);
            if (newSpecies) text += "\nNew species logged!";
            if (newSpecies) foreach (var reward in CatchLog.ClaimRewards(player)) text += "\n" + reward;
            bool newBiome = Rewards.RecordCaughtIn(player, s.Fish.Id, s.Biome, s.Ocean, s.Ocean && s.Depth >= DeepOceanDepth);
            if (newSpecies || newBiome) text += Rewards.ClaimBiomeSets(player);
            if (!newSpecies && newRecord)
            {
                Rewards.AddBonusPoints(player, Rewards.PersonalBestPoints);
                text += $"\nNew personal best! (+{Rewards.PersonalBestPoints} rank points)";
            }
            text += Mastery.OnCatch(s.Fish, countBefore, Mastery.Count(player, s.Fish.Id));
            text += AnglerRanks.OnCatch(player, s.FishWeight, rank >= TrophyThreshold && !baitfish, pointsBefore);

            if (s.Fish.Legendary) text = "LEGENDARY!\n" + text;
            if (s.Variant != RareFish.Normal)
            {
                bool first = RareFish.Record(player, s.Fish.Id, s.Variant);
                int pts = s.Variant == RareFish.Golden ? RareFish.GoldenPoints : RareFish.AlbinoPoints;
                Rewards.AddBonusPoints(player, pts);
                text = $"A {RareFish.Name(s.Variant).ToLowerInvariant()} {s.Fish.Name}!" + (first ? " (new in your catch log)" : "") + $" +{pts} rank points\n" + text;
                FishingFx.FishSplash(at, 1.4f);
            }
            CatchNews.Send(player, s.Fish, s.FishWeight, s.Variant);
            if (BossFish.IsBoss(s.Fish.Id))
            {
                Endgame.RefreshLureCosts(player);   // its lure costs a little more next time
                string next = Endgame.NextStep(player);
                if (next.Length > 0) text += "\n" + next;
            }   // players nearby hear of it (a boss: the whole server, in BossFish)
            return text;
        }

        /// <summary>
        /// Counts the catch the way vanilla fishing does (FishingFloat.Catch), so the game's fishing achievements and
        /// stats see it: the fish's name as a picked-up thing, one FishCaught, and the FishCaughtTier stat for its quality.
        /// </summary>
        private static void CountForAchievements(FishingSession s, int quality)
        {
            var game = Game.instance;
            if (game == null) return;
            try
            {
                string? name = ContentRegistry.FishItems.TryGetValue(s.Fish.Id, out var prefab)
                    ? prefab.GetComponent<global::Fish>()?.m_name : null;
                game.GetPlayerProfile()?.IncrementStatPickable(string.IsNullOrEmpty(name) ? s.Fish.Name : name);
                game.IncrementPlayerStat(PlayerStatType.FishCaught);
                if (quality <= 6) game.IncrementPlayerStat((PlayerStatType)(161 + quality));
            }
            catch (Exception e)
            {
                Plugin.Log.LogWarning("Couldn't count the catch for achievements: " + e.Message);
            }
        }

        private static void Finish(Player player, string reason)
        {
            Msg(reason);
            EndSession();
        }

        private static void EndSession()
        {
            var s = _session;
            _session = null;
            _reelingNow = false;
            if (s == null) return;
            // a line that was set down in a holder: what's left of its tackle goes back (to whoever has it, or the holder)
            if (s.Prepaid)
            {
                if (Quiet) PrepaidEnded?.Invoke(s);
                else if (Player.m_localPlayer is Player me && !me.IsDead()) GiveBack(me, PrepaidLeft(s));
            }
            // the pull button held as the fish lands (or the line goes) mustn't start the next cast
            if (ZInput.GetButton("Attack")) _waitAttackRelease = true;

            if (s.Bobber != null) UnityEngine.Object.Destroy(s.Bobber.gameObject);
            if (s.HookedFish != null) UnityEngine.Object.Destroy(s.HookedFish.gameObject);
            if (s.BaitVisual != null) UnityEngine.Object.Destroy(s.BaitVisual.gameObject);
            if (s.Swirl != null) UnityEngine.Object.Destroy(s.Swirl);
            FishApproach.DestroyAll(s);
        }

        // ------------------------------------------------------------------

        private static void Msg(string text)
        {
            if (Quiet) { ParkedLines.Said(text); return; }   // a rod in a holder: its news is shown by the holder
            MessageHud.instance?.ShowMessage(MessageHud.MessageType.Center, Loc.Text(text));
        }
    }
}
