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
            string text = $"Caught {s.Fish.Name}!  ({s.FishWeight:0.0} kg)";

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
                Drops.Give(player, drop, data, 1, dropPos);
                text += Drops.Aboard(player) ? "\nLanded!" : "\nLanded! Pick it up.";
                if (data.m_quality >= FishSize.MaxClass) text += FishMaterials.GiveTrophyFin(player, Drops.CatchPos(player, 0.4f));

                // Legendaries: a trophy the first time; bosses also leave a material and the news goes out.
                if (s.Fish.Legendary) text += BossFish.OnLanded(player, s.Fish, dropPos);

                // Vanilla fish keep their own extra drops, like vanilla fishing.
                if (s.Fish.IsVanilla && ContentRegistry.FishItems.TryGetValue(s.Fish.Id, out var fishPrefab))
                {
                    var extras = fishPrefab.GetComponent<global::Fish>()?.m_extraDrops;
                    if (extras != null)
                        foreach (var extra in extras.GetDropList())
                            UnityEngine.Object.Instantiate(extra, dropPos + Vector3.up * 0.3f, Quaternion.identity);
                }
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
                FishingFx.FishSplash(FishPos(player, s), 1.4f);
            }
            CatchNews.Send(player, s.Fish, s.FishWeight, s.Variant);
            if (BossFish.IsBoss(s.Fish.Id))
            {
                Endgame.RefreshLureCosts(player);   // its lure costs a little more next time
                string next = Endgame.NextStep(player);
                if (next.Length > 0) text += "\n" + next;
            }   // players nearby hear of it (a boss: the whole server, in BossFish)
            RodMotion.Trigger(RodEvent.CatchLift);
            FishingFx.Landing(FishPos(player, s));
            Msg(text);
            EndSession();
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
            MessageHud.instance?.ShowMessage(MessageHud.MessageType.Center, Loc.Text(text));
        }
    }
}
