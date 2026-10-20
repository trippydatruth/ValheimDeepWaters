using HarmonyLib;
using System.Collections.Generic;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// Other anglers' fishing as everyone else sees it (roadmap #29): for each player fishing nearby, their line from the
    /// rod tip to the water, the float (or lure) on it, the fish on the hook once one is - its own model at its size,
    /// running, leaping and thrashing - with their splashes, bites and line snaps, and their reel winding. All of it is
    /// drawn here from what they share (AnglerSync); nothing is networked but those few values.
    /// </summary>
    internal static class RemoteAnglers
    {
        private const float ShowWithin = 90f;   // metres: further anglers' lines aren't drawn

        private sealed class Line
        {
            public BobberVisual? Bobber;
            public HookedFishVisual? Fish;
            public string FishId = "";
            public AudioSource? Reel;
            public Vector3 At;
            public bool HasAt;
        }

        private static readonly Dictionary<int, Line> Lines = new Dictionary<int, Line>();
        private static readonly List<int> Gone = new List<int>();

        /// <summary>Every frame, after the other anglers' rods have been posed (RodMotion.ApplyOthers).</summary>
        public static void Update(Player local)
        {
            Gone.Clear();
            Gone.AddRange(Lines.Keys);
            foreach (var p in Player.GetAllPlayers())
            {
                if (p == null || p == local) continue;
                int id = p.GetInstanceID();
                var st = AnglerSync.Read(p, out _);
                bool active = st.RodOut && st.Phase >= 1 && st.HasTarget && !p.IsDead() && ContentRegistry.IsRod(p.GetCurrentWeapon())
                              && Vector3.Distance(p.transform.position, local.transform.position) < ShowWithin;
                if (!active) continue;
                Gone.Remove(id);
                if (!Lines.TryGetValue(id, out var line)) Lines[id] = line = new Line();
                Draw(p, line, st);
            }
            foreach (int id in Gone) { Clear(Lines[id]); Lines.Remove(id); }
        }

        private static void Draw(Player p, Line line, in AnglerState st)
        {
            var (floatId, fishId, scale) = AnglerSync.ReadLook(p);
            int variant = 0;                                   // "pike#1": a golden pike
            int hash = fishId.IndexOf('#');
            if (hash >= 0) { int.TryParse(fishId.Substring(hash + 1), out variant); fishId = fishId.Substring(0, hash); }

            // where their line meets the water, sent ten times a second: eased so it glides rather than steps
            if (!line.HasAt) { line.At = st.Target; line.HasAt = true; }
            else line.At = Vector3.Lerp(line.At, st.Target, 1f - Mathf.Exp(-Time.deltaTime * 8f));
            Vector3 tip = RodMotion.TryGetTip(p, out var t) ? t : p.transform.position + Vector3.up * 1.5f + p.transform.forward * 1.5f;

            if (line.Bobber == null)
            {
                FishingBuffs.Buffs.TryGetValue(floatId, out var floatDef);
                line.Bobber = BobberVisual.Create(tip, st.Lure, remote: true, remoteFloat: floatDef);
                line.Bobber.BeginCastTravel(tip, st.Target);
            }
            var b = line.Bobber;
            b.Position = line.At;
            b.Slack = st.Phase == 3 ? 0f : 0.12f;
            b.Dipped = st.Phase == 2;
            b.Thrashing = st.Phase == 3 && st.Running;
            b.Refresh(p, tip);

            // the fish on the hook
            if (st.Phase == 3 && fishId.Length > 0)
            {
                if (line.Fish == null || line.FishId != fishId)
                {
                    if (line.Fish != null) Object.Destroy(line.Fish.gameObject);
                    line.Fish = null;
                    if (ContentRegistry.Fish.TryGetValue(fishId, out var fish) && ContentRegistry.FishItems.TryGetValue(fishId, out var prefab))
                    {
                        line.Fish = HookedFishVisual.Create(prefab, ContentRegistry.ModelKeyFor(fish), scale);
                        if (line.Fish != null) line.Fish.StayUnder = 0.05f;
                        RareFish.TintModel(line.Fish?.gameObject, variant);
                    }
                    line.FishId = fishId;
                }
                if (line.Fish != null)
                {
                    line.Fish.Position = line.At + Vector3.down * 0.15f;
                    line.Fish.Intensity = st.Running ? 1f : 0.25f;
                }
            }
            else if (line.Fish != null)
            {
                Object.Destroy(line.Fish.gameObject);
                line.Fish = null;
                line.FishId = "";
            }

            // their splashes, bites and snaps, at their line
            var fx = AnglerSync.ReadFx(p, out float arg);
            switch (fx)
            {
                case FishFx.Bite: FishingFx.Bite(line.At, share: false); break;
                case FishFx.Nibble: FishingFx.Nibble(line.At, share: false); b.Nibble(0.08f); break;
                case FishFx.HookSet: FishingFx.HookSet(line.At, share: false); break;
                case FishFx.Splash: FishingFx.FishSplash(line.At, arg, share: false); break;
                case FishFx.Leap:
                    line.Fish?.Leap(arg, Mathf.Lerp(0.7f, 1.2f, arg / 2f));
                    FishingFx.FishSplash(line.At, 0.5f + arg * 0.4f, share: false);
                    break;
                case FishFx.Snap: FishingFx.LineSnap(line.At, share: false); break;
                case FishFx.Landing: FishingFx.Landing(line.At, share: false); break;

                // a sea serpent boss's moves (the Queen Eel), as the angler sees them
                case FishFx.Hump:
                    line.Fish?.Surface(arg, 1.4f);
                    FishingFx.FishSplash(line.At, arg * 2f, share: false);
                    break;
                case FishFx.TailSlap:
                    line.Fish?.Surface(arg, 0.6f);
                    FishingFx.FishSplash(line.At, arg * 7.2f, share: false);
                    Shake(line.At, 0.6f);
                    break;
                case FishFx.Rear:
                    line.Fish?.Rear(p.transform.position, arg, FishingController.RearRise, FishingController.RearHold, FishingController.RearFall);
                    FishingFx.FishSplash(line.At, arg * 2f, share: false);
                    Shake(line.At, 0.8f);
                    break;
                case FishFx.Crash:
                    FishingFx.FishSplash(line.At, 2.2f * arg, share: false);
                    FishingFx.FishSplash(line.At + (p.transform.position - line.At).normalized * 2f, 1.4f * arg, share: false);
                    Shake(line.At, 1.2f);
                    break;
            }

            // their reel, winding as they reel in
            if (st.Reeling)
            {
                line.Reel ??= FishingFx.MakeRemoteReel();
                if (line.Reel != null)
                {
                    line.Reel.transform.position = p.transform.position + Vector3.up * 1.2f;
                    line.Reel.volume = Mathf.Clamp01(VdwConfig.ReelVolume.Value) * 0.8f;
                    line.Reel.pitch = Mathf.Lerp(1f, 1.35f, Mathf.Clamp01(st.Load));
                    if (!line.Reel.isPlaying) line.Reel.Play();
                }
            }
            else if (line.Reel != null && line.Reel.isPlaying) line.Reel.Stop();
        }

        /// <summary>A rumble for watchers close to a serpent's big moves - gentler than the angler's own, and only nearby.</summary>
        private static void Shake(Vector3 at, float strength) => GameCamera.instance?.AddShake(at, 25f, strength, false);

        private static void Clear(Line line)
        {
            if (line.Bobber != null) Object.Destroy(line.Bobber.gameObject);
            if (line.Fish != null) Object.Destroy(line.Fish.gameObject);
            if (line.Reel != null) Object.Destroy(line.Reel.gameObject);
        }
    }

    /// <summary>
    /// A landed fish is news for the players around the angler (within 50 m) - "Tripp landed a 12.4 kg Pike!". Boss fish
    /// are announced to the whole server already (BossFish.OnLanded).
    /// </summary>
    internal static class CatchNews
    {
        private const string Rpc = "VDW_Landed";
        private const float NearbyMetres = 50f;

        public static void Send(Player player, FishDefinition fish, float kg, int variant = 0)
        {
            if (ZRoutedRpc.instance == null || BossFish.IsBoss(fish.Id) || !string.IsNullOrWhiteSpace(fish.CatchBait)) return;
            string kind = variant != 0 ? RareFish.Name(variant).ToLowerInvariant() + " " : "";
            string text = $"{player.GetPlayerName()} landed a {kg:0.0} kg {kind}{fish.Name}!";
            ZRoutedRpc.instance.InvokeRoutedRPC(ZRoutedRpc.Everybody, Rpc, text, player.transform.position);
        }

        private static void OnLanded(long sender, string text, Vector3 at)
        {
            var me = Player.m_localPlayer;
            if (me == null || sender == ZNet.GetUID()) return;   // not your own catch
            if (Vector3.Distance(me.transform.position, at) > NearbyMetres) return;
            me.Message(MessageHud.MessageType.TopLeft, text);
        }

        [HarmonyPatch(typeof(Game), "Start")]
        private static class RegisterRpc
        {
            private static void Postfix() => ZRoutedRpc.instance?.Register<string, Vector3>(Rpc, OnLanded);
        }
    }
}
