using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// Zeroes the player's arm/attack Animator layers while the rod is equipped, so the cloned base weapon's own
    /// charge pose doesn't fight Deep Waters' rod motion. Layers are picked by name; the base layer (index 0)
    /// and locomotion layers are never touched. The layer list is logged once to help tune the name lists.
    /// </summary>
    internal static class AnimationOverride
    {
        private static readonly string[] SuppressNameHints =
            { "arm", "attack", "weapon", "tool", "upper", "fullbody", "full body", "charge", "aim", "draw", "combat" };

        private static readonly string[] KeepNameHints =
            { "base", "locomotion", "movement", "walk", "run", "idle root", "full" };

        private static Animator? _animator;
        private static float[]? _originalWeights;
        private static int[]? _suppressedLayers;
        private static bool _active;

        public static void Reset()
        {
            Apply(false);
            _animator = null;
            _originalWeights = null;
            _suppressedLayers = null;
            _active = false;
        }

        public static void SetActive(Player player, bool wantActive)
        {
            if (_animator == null)
            {
                if (!wantActive) return;
                _animator = player.GetComponentInChildren<Animator>();
                if (_animator == null) return;
                ReadLayers(_animator);
            }

            if (wantActive == _active) return;
            _active = wantActive;
            Apply(wantActive);
        }

        private static void ReadLayers(Animator animator)
        {
            int count = animator.layerCount;
            _originalWeights = new float[count];
            var suppress = new List<int>();

            for (int i = 0; i < count; i++)
            {
                string name = animator.GetLayerName(i);
                _originalWeights[i] = animator.GetLayerWeight(i);
                if (i == 0) continue;

                string lower = name.ToLowerInvariant();
                if (!KeepNameHints.Any(lower.Contains) && SuppressNameHints.Any(lower.Contains))
                    suppress.Add(i);
            }

            _suppressedLayers = suppress.ToArray();        }

        private static void Apply(bool suppress)
        {
            if (_animator == null || _suppressedLayers == null || _originalWeights == null) return;
            foreach (var i in _suppressedLayers)
                _animator.SetLayerWeight(i, suppress ? 0f : _originalWeights[i]);
        }
    }
}
