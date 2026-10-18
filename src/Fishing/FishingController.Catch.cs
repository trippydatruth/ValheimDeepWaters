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
                // Size class as the item's quality: shown on the icon, sizes don't stack together (so a
                // trophy keeps its weight), and item stands show bigger classes bigger.
                data.m_quality = FishSize.ClassFor(rank);

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
            var find = FishingBuffs.RollFind(s);
            var findDrop = find != null ? find.GetComponent<ItemDrop>() : null;
            if (findDrop != null)
            {
                Vector3 findPos = Drops.CatchPos(player, 0.6f);
                Drops.Give(player, findDrop, 1, findPos);
                text += $"\nSomething glints inside it... {Loc.Text(findDrop.m_itemData.m_shared.m_name)}!";
            }

            // Landing a fish is worth more Fishing skill the harder it fights.
            player.RaiseSkill(Skills.SkillType.Fishing, 1f + Mathf.Max(0f, s.Fish.FightStrength));

            CatchLog.Record(player, s.Fish.Id, s.FishWeight, out bool newSpecies, out bool newRecord);
            if (newSpecies) text += "\nNew species logged!";
            if (newSpecies) foreach (var reward in CatchLog.ClaimRewards(player)) text += "\n" + reward;
            else if (newRecord) text += "\nNew personal best!";

            if (s.Fish.Legendary) text = "LEGENDARY!\n" + text;
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
