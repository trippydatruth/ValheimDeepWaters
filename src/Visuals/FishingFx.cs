using System;
using System.Linq;
using UnityEngine;
using UnityEngine.Audio;

namespace ValheimDeepWaters
{
    /// <summary>
    /// Sounds and splashes, borrowed from Valheim's own fishing so they match the game: the vanilla rod's cast
    /// whoosh, the float's water splash, nibble and line-snap effects, and a fish's jump splash. Effects are
    /// played locally (each player hears their own fishing). The reel and drag loops are the mod's own sounds, with
    /// a vanilla reel-like clip as a fallback.
    /// </summary>
    internal static class FishingFx
    {
        private static bool _resolved;
        private static EffectList? _cast, _landSplash, _nibble, _lineBreak, _jump;

        private static AudioSource? _reel;
        private static AudioClip? _reelClip;
        private static AudioMixerGroup? _sfxGroup;

        /// <summary>The game's sound-effects mixer group, so other sounds follow the SFX volume slider.</summary>
        internal static AudioMixerGroup? SfxGroup
        {
            get { Resolve(); return _sfxGroup; }
        }


        private static void Resolve()
        {
            if (_resolved || ObjectDB.instance == null || ZNetScene.instance == null) return;
            _resolved = true;

            try
            {
                var rod = ObjectDB.instance.GetItemPrefab("FishingRod")?.GetComponent<ItemDrop>()?.m_itemData.m_shared.m_attack;
                _cast = rod?.m_startEffect;
                var floatPrefab = rod?.m_attackProjectile;
                var ff = floatPrefab != null ? floatPrefab.GetComponent<FishingFloat>() : null;
                _nibble = ff?.m_nibbleEffect;
                _lineBreak = ff?.m_lineBreakEffect;
                _landSplash = floatPrefab != null ? floatPrefab.GetComponent<Projectile>()?.m_hitWaterEffects : null;
                _jump = ZNetScene.instance.GetPrefab("Fish1")?.GetComponent<global::Fish>()?.m_jumpEffects;

                // Straight from the game's effect prefabs too, in case the rod's own lists came up empty: the swing of
                // the cast and the float's plop into the water.
                _cast = Ensure(_cast, "sfx_fishingrod_swing");
                _landSplash = Ensure(_landSplash, "fx_float_hitwater");
                _nibble = Ensure(_nibble, "fx_float_nibble");
                Plugin.Log.LogDebug($"Effects: cast {(_cast != null && _cast.HasEffects() ? "ok" : "missing")}, splash {(_landSplash != null && _landSplash.HasEffects() ? "ok" : "missing")}, nibble {(_nibble != null && _nibble.HasEffects() ? "ok" : "missing")}.");

                // Route our own audio through the game's SFX mixer so the volume slider applies.
                _sfxGroup = FindMixerGroup(_nibble) ?? FindMixerGroup(_landSplash);
                _reelClip = FindReelClip();
            }
            catch (Exception ex)
            {
                Plugin.Log.LogWarning($"Effects: couldn't find vanilla fishing effects ({ex.Message}); fishing will be quiet.");
            }
        }


        /// <summary>The list as it is, or one made from the named vanilla effect prefab if it's empty.</summary>
        private static EffectList? Ensure(EffectList? list, string prefab)
        {
            if (list != null && list.HasEffects()) return list;
            var go = ZNetScene.instance.GetPrefab(prefab);
            if (go == null) return list;
            return new EffectList { m_effectPrefabs = new[] { new EffectList.EffectData { m_prefab = go, m_enabled = true } } };
        }

        private static AudioMixerGroup? FindMixerGroup(EffectList? list)
        {
            if (list?.m_effectPrefabs == null) return null;
            foreach (var data in list.m_effectPrefabs)
            {
                var src = data?.m_prefab != null ? data.m_prefab.GetComponentInChildren<AudioSource>(true) : null;
                if (src != null && src.outputAudioMixerGroup != null) return src.outputAudioMixerGroup;
            }
            return null;
        }

        /// <summary>Valheim doesn't ship an obvious reel sound; use the first one named like one.</summary>
        private static AudioClip? FindReelClip()
        {
            return Resources.FindObjectsOfTypeAll<AudioClip>().FirstOrDefault(c => c != null && (c.name.IndexOf("reel", StringComparison.OrdinalIgnoreCase) >= 0
                                                        || c.name.IndexOf("winch", StringComparison.OrdinalIgnoreCase) >= 0));
        }

        /// <summary>The effect is picked after Resolve() has run, so even the very first one plays.</summary>
        private static void Play(Func<EffectList?> pick, Vector3 pos, float scale = 1f)
        {
            Resolve();
            var list = pick();
            if (list == null || !list.HasEffects()) return;
            try { list.Create(pos, Quaternion.identity, null, scale); }
            catch (Exception ex) { Plugin.Log.LogWarning($"Effects: failed to play ({ex.Message})."); }
        }

        // ------------------------------------------------------------------ events

        public static void Cast(Player player) => Play(() => _cast, player.transform.position + Vector3.up * 1.5f);
        public static void Landed(Vector3 pos) => Play(() => _landSplash, pos, 0.6f);
        // The local angler's are shared (share: true) so players nearby see and hear them at that line too; a watcher's
        // copies (RemoteAnglers) play with share: false.
        private static void Share(bool share, FishFx kind, float arg = 0f) { if (share) AnglerSync.Fx(Player.m_localPlayer, kind, arg); }

        public static void Nibble(Vector3 pos, bool share = true) { Play(() => _nibble, pos); Share(share, FishFx.Nibble); }
        public static void Bite(Vector3 pos, bool share = true) { Play(() => _nibble, pos); Play(() => _landSplash, pos, 0.8f); Share(share, FishFx.Bite); }
        public static void HookSet(Vector3 pos, bool share = true) { Play(() => _jump, pos, 0.8f); Share(share, FishFx.HookSet); }
        public static void FishSplash(Vector3 pos, float size, bool share = true) { Play(() => _jump, pos, Mathf.Clamp(size, 0.4f, 1.6f)); Share(share, FishFx.Splash, size); }
        public static void LineSnap(Vector3 pos, bool share = true) { Play(() => _lineBreak, pos); Share(share, FishFx.Snap); }
        public static void Landing(Vector3 pos, bool share = true) { Play(() => _jump, pos, 1f); Share(share, FishFx.Landing); }

        /// <summary>A looping reel sound for another angler (RemoteAnglers): its own source, so it doesn't fight the local reel.</summary>
        public static AudioSource? MakeRemoteReel()
        {
            Resolve();
            FindReelSounds();
            return _reelClip != null ? MakeLoop("VDW_RemoteReel", _reelClip) : null;
        }

        private static AudioSource? _drag;
        private static AudioClip? _dragClip;
        private static bool _lookedForSounds;

        /// <summary>
        /// The reel sounds: "fishing_reel" (winding) and "fishing_reel_drag" (the drag slipping), as AudioClips in any
        /// bundle or as .wav files in the Models folder. Without a reel sound of our own, a vanilla reel click is used.
        /// </summary>
        private static void FindReelSounds()
        {
            if (_lookedForSounds) return;
            _lookedForSounds = true;
            var reel = LoadSound("fishing_reel");
            if (reel != null) _reelClip = reel;
            _dragClip = LoadSound("fishing_reel_drag");
            Plugin.Log.LogDebug($"Reel sounds: winding {(reel != null ? "fishing_reel" : _reelClip != null ? "vanilla" : "none")}, drag {(_dragClip != null ? "fishing_reel_drag" : "none")}.");
        }

        private static AudioClip? LoadSound(string name)
        {
            var clip = CustomModels.LoadBundleAsset<AudioClip>(name);
            if (clip != null) return clip;
            string wav = System.IO.Path.Combine(CustomModels.ModelsFolder, name + ".wav");
            return System.IO.File.Exists(wav) ? Wav.Load(wav) : null;
        }

        private static AudioSource MakeLoop(string name, AudioClip clip)
        {
            var go = new GameObject(name);
            UnityEngine.Object.DontDestroyOnLoad(go);
            var src = go.AddComponent<AudioSource>();
            src.clip = clip; src.loop = true; src.spatialBlend = 0.6f; src.outputAudioMixerGroup = _sfxGroup;
            return src;
        }

        /// <summary>
        /// The reel while you wind (a little faster and higher under load), and the drag whenever it slips (slip01: a fish
        /// pulling line out against it, or a drag set too loose to hold) - the drag takes over from the winding as it sings.
        /// </summary>
        public static void UpdateReel(Player? player, bool reeling, float load01, float slip01 = 0f)
        {
            Resolve();
            FindReelSounds();
            float vol = Mathf.Clamp01(VdwConfig.ReelVolume.Value);
            Vector3 at = player != null ? player.transform.position + Vector3.up * 1.2f : Vector3.zero;

            bool winding = player != null && reeling && slip01 < 0.5f && _reelClip != null;
            if (winding)
            {
                _reel ??= MakeLoop("VDW_ReelSound", _reelClip!);
                _reel.transform.position = at;
                _reel.volume = vol * (1f - slip01);
                _reel.pitch = Mathf.Lerp(1f, 1.35f, Mathf.Clamp01(load01));
                if (!_reel.isPlaying) _reel.Play();
            }
            else if (_reel != null && _reel.isPlaying) _reel.Stop();

            bool singing = player != null && slip01 > 0.05f && _dragClip != null;
            if (singing)
            {
                _drag ??= MakeLoop("VDW_DragSound", _dragClip!);
                _drag.transform.position = at;
                _drag.volume = vol * Mathf.Lerp(0.4f, 1f, slip01);
                _drag.pitch = Mathf.Lerp(0.9f, 1.25f, slip01);
                if (!_drag.isPlaying) _drag.Play();
            }
            else if (_drag != null && _drag.isPlaying) _drag.Stop();
        }
    }
}
