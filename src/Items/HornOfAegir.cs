using HarmonyLib;
using System;
using System.Globalization;
using System.IO;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// The Horn of Ægir is blown, not drunk, and it's kept: using it raises the horn to your mouth (the drinking motion
    /// with the horn model held there), sounds a horn blast everyone nearby hears, and calls the fish (its effect). Then
    /// it needs a day's rest before it can be blown again; the time it's ready again is stored on the item itself.
    /// The blast is an AudioClip named "horn_of_aegir" in any bundle in the Models folder, or horn_of_aegir.wav there.
    /// </summary>
    internal static class HornOfAegir
    {
        private const string BuffId = "relic_horn";
        private const string ReadyKey = "vdw_horn_ready";
        private const float RestSeconds = 1800f;       // one in-game day
        private const string Rpc = "VDW_HornBlow";

        public static bool IsHorn(ItemDrop.ItemData? item) =>
            item?.m_shared?.m_consumeStatusEffect is SE_FishingBuff se && FishingBuffs.ByStatusName(se.m_name)?.Id == BuffId;

        [HarmonyPatch(typeof(Player), nameof(Player.ConsumeItem))]
        private static class ConsumePatch
        {
            private static bool Prefix(Player __instance, ItemDrop.ItemData item, ref bool __result)
            {
                if (!IsHorn(item)) return true;
                __result = Blow(__instance, item);
                return false; // never drunk, never used up
            }
        }

        private static bool Blow(Player player, ItemDrop.ItemData item)
        {
            double now = ZNet.instance != null ? ZNet.instance.GetTimeSeconds() : Time.time;
            item.m_customData ??= new System.Collections.Generic.Dictionary<string, string>();
            if (item.m_customData.TryGetValue(ReadyKey, out var raw) &&
                double.TryParse(raw, NumberStyles.Float, CultureInfo.InvariantCulture, out double ready) && now < ready)
            {
                int mins = Mathf.CeilToInt((float)(ready - now) / 60f);
                player.Message(MessageHud.MessageType.Center, $"The horn needs to rest. It can be blown again in {mins} min.");
                return false;
            }
            item.m_customData[ReadyKey] = (now + RestSeconds).ToString("0", CultureInfo.InvariantCulture);

            // The fish come.
            player.GetSEMan().AddStatusEffect(item.m_shared.m_consumeStatusEffect, resetTime: true);
            // Everyone sees it raised to the lips (held there for the whole blast) and hears it.
            if (ZRoutedRpc.instance != null) ZRoutedRpc.instance.InvokeRoutedRPC(ZRoutedRpc.Everybody, Rpc, player.GetZDOID());
            else HornBlowVisual.Play(player);
            player.Message(MessageHud.MessageType.Center, "You sound the Horn of Ægir. The fish are coming.");
            return true;
        }

        /// <summary>
        /// Blowing the horn or setting down a chum bucket isn't eating: Valheim's use step plays the eating sound after
        /// a successful consume, so it's swapped for silence while one of these is used.
        /// </summary>
        [HarmonyPatch(typeof(Humanoid), nameof(Humanoid.UseItem))]
        private static class QuietUsePatch
        {
            private static readonly System.Reflection.FieldInfo? EffectsField = AccessTools.Field(typeof(Player), "m_consumeItemEffects");
            private static readonly EffectList Silence = new EffectList();

            private static void Prefix(Humanoid __instance, ItemDrop.ItemData item, ref EffectList? __state)
            {
                if (EffectsField == null || !(__instance is Player) || !(IsHorn(item) || ChumBuckets.IsChum(item))) return;
                __state = EffectsField.GetValue(__instance) as EffectList;
                EffectsField.SetValue(__instance, Silence);
            }

            private static void Postfix(Humanoid __instance, EffectList? __state)
            {
                if (__state != null) EffectsField!.SetValue(__instance, __state);
            }
        }

        /// <summary>Ready to blow again at once (vdw_debug horn).</summary>
        public static int ResetRest(Player player)
        {
            int n = 0;
            foreach (var it in player.GetInventory().GetAllItems())
                if (IsHorn(it) && it.m_customData != null && it.m_customData.Remove(ReadyKey)) n++;
            return n;
        }

        [HarmonyPatch(typeof(Game), "Start")]
        private static class RegisterRpc
        {
            private static void Postfix() => ZRoutedRpc.instance?.Register<ZDOID>(Rpc, OnBlow);
        }

        private static void OnBlow(long sender, ZDOID who)
        {
            foreach (var p in Player.GetAllPlayers())
                if (p != null && p.GetZDOID() == who) { HornBlowVisual.Play(p); return; }
        }

        // ------------------------------------------------------------------ the sound
        private static AudioClip? _clip;
        private static bool _looked;

        public static AudioClip? Clip
        {
            get
            {
                if (_looked) return _clip;
                _looked = true;
                _clip = CustomModels.LoadBundleAsset<AudioClip>("horn_of_aegir");
                if (_clip == null)
                {
                    string? wav = CustomModels.FindFile("horn_of_aegir.wav");
                    if (wav != null) _clip = Wav.Load(wav);
                }
                if (_clip == null) Plugin.Log.LogWarning("Horn of Ægir: no horn sound found (an AudioClip 'horn_of_aegir' in a bundle, or horn_of_aegir.wav in the Models folder); it's blown silently.");
                return _clip;
            }
        }
    }

    /// <summary>The horn held at a player's mouth while they blow it, with the blast. Every client shows its own.</summary>
    internal sealed class HornBlowVisual : MonoBehaviour
    {
        private const float Duration = 2.8f;   // without a sound to time it by
        // the model lies along its forward axis from the mouthpiece (its origin), sagging up to 0.15 m below that line
        // before the bell lifts again: kept upright, and raised a little more than a straight horn would be
        private static readonly Quaternion ModelTurn = Quaternion.identity;
        private Player? _player;
        private float _end;

        public static void Play(Player player)
        {
            var go = new GameObject("VDW_HornBlow");
            var model = CustomModels.GetBundlePrefab("buff_relic_horn");
            if (model != null)
            {
                var horn = Instantiate(model, go.transform, false);
                horn.transform.localPosition = Vector3.zero; horn.transform.localRotation = ModelTurn;
                foreach (var c in horn.GetComponentsInChildren<Collider>(true)) Destroy(c);
                foreach (var rb in horn.GetComponentsInChildren<Rigidbody>(true)) Destroy(rb);
            }
            var v = go.AddComponent<HornBlowVisual>();
            // held up for the whole blast
            v._player = player; v._end = Time.time + (HornOfAegir.Clip is AudioClip blast ? blast.length : Duration);
            v.Place();

            if (HornOfAegir.Clip is AudioClip clip)
            {
                var src = go.AddComponent<AudioSource>();
                src.clip = clip; src.spatialBlend = 1f; src.rolloffMode = AudioRolloffMode.Linear;
                src.minDistance = 6f; src.maxDistance = 160f; src.volume = 1f;
                src.outputAudioMixerGroup = FishingFx.SfxGroup;
                src.Play();
            }
        }

        // where the hands hold it, on the horn itself (points on its centre line measured off horn_of_aegir_v2, in the
        // model's space), the wrists just above so the hands close over it
        private static readonly Vector3 RightGrip = new Vector3(0f, -0.09f, 0.10f), LeftGrip = new Vector3(0f, -0.115f, 0.40f);
        private const float WristAbove = 0.045f, RightWristAbove = 0.0f;

        /// <summary>
        /// The mouthpiece at the lips and the bell raised out ahead, the right hand round it near the mouthpiece and the
        /// left holding it further along, for as long as the blast lasts.
        /// </summary>
        private void Place()
        {
            if (_player == null) return;
            var t = _player.transform;
            var head = FishingBoatOars.Bone(_player, "Head");
            Vector3 headPos = head != null ? head.position : t.position + Vector3.up * 1.65f;
            Vector3 mouth = headPos + t.forward * 0.12f - Vector3.up * 0.03f;
            Vector3 dir = (t.forward * 0.75f + Vector3.up * 0.55f).normalized;          // out and raised, as a horn is blown
            transform.SetPositionAndRotation(mouth, Quaternion.LookRotation(dir, Vector3.up));

            foreach (var (prefix, side, along) in new[] { ("Right", 1f, RightGrip), ("Left", -1f, LeftGrip) })
            {
                var upper = FishingBoatOars.Bone(_player, prefix + "Arm");
                var lower = FishingBoatOars.Bone(_player, prefix + "ForeArm");
                var hand = FishingBoatOars.Bone(_player, prefix + "Hand");
                if (upper == null || lower == null || hand == null) continue;
                // on the horn; the right hand, near the mouthpiece, sat a little high: its wrist rides lower
                Vector3 target = transform.TransformPoint(along) + Vector3.up * (side > 0 ? RightWristAbove : WristAbove) + t.right * (side * 0.02f);
                Vector3 pole = upper.position + t.right * (side * 0.45f) - Vector3.up * 0.35f;   // elbows out and down
                FishingBoatOars.SolveArm(upper, lower, hand, target, pole);
            }
        }

        private void LateUpdate()
        {
            if (_player == null || Time.time > _end + 1.5f) { Destroy(gameObject); return; }
            if (Time.time > _end) { foreach (var r in GetComponentsInChildren<Renderer>()) r.enabled = false; return; } // let the sound finish
            FishingBoatOars.BeginPose(_player);
            try { Place(); }
            finally { FishingBoatOars.EndPose(_player); }
        }
    }

    /// <summary>Reads a PCM .wav (8/16/24/32-bit, any channels) into a mono AudioClip.</summary>
    internal static class Wav
    {
        public static AudioClip? Load(string path)
        {
            try
            {
                var b = File.ReadAllBytes(path);
                int channels = 0, rate = 0, bits = 0, dataPos = -1, dataLen = 0, p = 12;
                while (p + 8 <= b.Length)
                {
                    string id = System.Text.Encoding.ASCII.GetString(b, p, 4); int len = BitConverter.ToInt32(b, p + 4);
                    if (id == "fmt ") { channels = BitConverter.ToInt16(b, p + 10); rate = BitConverter.ToInt32(b, p + 12); bits = BitConverter.ToInt16(b, p + 22); }
                    else if (id == "data") { dataPos = p + 8; dataLen = Math.Min(len, b.Length - dataPos); break; }
                    p += 8 + len + (len & 1);
                }
                if (dataPos < 0 || channels == 0 || bits == 0) return null;
                int bps = bits / 8, n = dataLen / bps;
                var f = new float[n];
                for (int i = 0; i < n; i++)
                {
                    int o = dataPos + i * bps;
                    f[i] = bits switch
                    {
                        8 => (b[o] - 128) / 128f,
                        16 => BitConverter.ToInt16(b, o) / 32768f,
                        24 => ((b[o] | (b[o + 1] << 8) | ((sbyte)b[o + 2] << 16))) / 8388608f,
                        _ => BitConverter.ToInt32(b, o) / 2147483648f,
                    };
                }
                // Mixed down to mono: a sound placed in the world (3D) plays best from one channel.
                int frames = n / channels;
                var mono = new float[frames];
                for (int i = 0; i < frames; i++)
                {
                    float sum = 0f;
                    for (int ch = 0; ch < channels; ch++) sum += f[i * channels + ch];
                    mono[i] = sum / channels;
                }
                var clip = AudioClip.Create(Path.GetFileNameWithoutExtension(path), frames, 1, rate, false);
                clip.SetData(mono, 0);
                return clip;
            }
            catch (Exception ex)
            {
                Plugin.Log.LogWarning($"Couldn't read {path} ({ex.Message}).");
                return null;
            }
        }
    }
}
