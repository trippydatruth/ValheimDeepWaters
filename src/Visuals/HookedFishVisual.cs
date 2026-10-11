using System;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// Render-only stand-in for a fish or bait item: the swimming fish before a bite, the hooked fish, and the
    /// bait on the hook. Never instantiates the registered item prefab (its ZNetView/ZSyncTransform/ItemDrop
    /// would register with ZNetScene and flood errors once stripped); it only copies the prefab's shared mesh
    /// and material references onto a plain new GameObject.
    /// </summary>
    internal sealed class HookedFishVisual : MonoBehaviour
    {
        public Vector3 Position;
        public float Intensity; // 0 = calm, 1 = thrashing

        /// <summary>Metres the top of the model is kept below the actual wave surface. Negative = no limit.</summary>
        public float StayUnder = -1f;

        private float _topOffset;
        private FishModelAnimator? _anim; // set when the model is animated
        private Vector3 _renderPos;
        private Quaternion _facing = Quaternion.identity;
        private bool _initialized;

        /// <summary>
        /// customModelKey ("fish_&lt;id&gt;" / "bait_&lt;id&gt;") is tried first; without a custom model the
        /// prefab's own meshes are copied. <paramref name="scale"/> shows it bigger (or smaller) than the model.
        /// </summary>
        public static HookedFishVisual? Create(GameObject? prefab, string? customModelKey = null, float scale = 1f)
        {
            var go = new GameObject("VDW_FishVisual");
            bool any = false;
            FishModelAnimator? anim = null;

            try
            {
                // An animated (rigged) model is used whole, and its clips are driven from Intensity.
                if (customModelKey != null && CustomModels.GetAnimated(customModelKey) is GameObject animated)
                {
                    anim = CustomModels.SpawnAnimated(animated, go.transform);
                    anim.Driven = true;
                    any = true;
                }
                else if (customModelKey != null && CustomModels.TryGetCustom(customModelKey, out var customMesh, out var customMat))
                {
                    any = CopyRenderer(go.transform, null, customMesh, new[] { customMat });
                }
                else if (prefab != null)
                {
                    foreach (var mf in prefab.GetComponentsInChildren<MeshFilter>(true))
                    {
                        var mr = mf.GetComponent<MeshRenderer>();
                        if (mf.sharedMesh == null || mr == null) continue;
                        any |= CopyRenderer(go.transform, mf.transform, mf.sharedMesh, mr.sharedMaterials);
                    }

                    // A rigged fish's bind-pose mesh is fine for a non-animated display.
                    foreach (var smr in prefab.GetComponentsInChildren<SkinnedMeshRenderer>(true))
                    {
                        if (smr.sharedMesh == null) continue;
                        any |= CopyRenderer(go.transform, smr.transform, smr.sharedMesh, smr.sharedMaterials);
                    }
                }
            }
            catch (Exception ex)
            {
                Plugin.Log.LogWarning($"Fish visual: failed reading mesh data ({ex.Message}).");
                Destroy(go);
                return null;
            }

            if (!any)
            {
                Plugin.Log.LogWarning($"Fish visual: no mesh found for '{customModelKey ?? prefab?.name ?? "(none)"}'.");
                Destroy(go);
                return null;
            }

            go.transform.localScale = Vector3.one * Mathf.Max(0.01f, scale);   // a boss can be shown bigger than its model
            // go is still at the world origin, so the bounds' top is the model's top relative to its origin.
            var renderers = go.GetComponentsInChildren<Renderer>();
            var bounds = renderers[0].bounds;
            foreach (var r in renderers) bounds.Encapsulate(r.bounds);

            var visual = go.AddComponent<HookedFishVisual>();
            visual._topOffset = bounds.max.y;
            visual._anim = anim;
            return visual;
        }

        /// <summary>The real (wavy) water surface at a point, or null when the point isn't in water.</summary>
        private static float? SurfaceAt(Vector3 p)
        {
            float level = Floating.GetLiquidLevel(p);
            if (level < -1000f) level = Floating.GetLiquidLevel(p + Vector3.down * 2f); // point above a trough
            return level < -1000f ? null : level;
        }

        /// <summary>source is null for a custom mesh (placed at the origin); otherwise the source's local
        /// transform is copied so multi-piece prefabs keep their layout.</summary>
        private static bool CopyRenderer(Transform parent, Transform? source, Mesh sharedMesh, Material[] sharedMaterials)
        {
            var child = new GameObject(source != null ? source.name : "custom");
            child.transform.SetParent(parent, false);
            if (source != null)
            {
                child.transform.localPosition = source.localPosition;
                child.transform.localRotation = source.localRotation;
                child.transform.localScale = source.localScale;
            }

            child.AddComponent<MeshFilter>().sharedMesh = sharedMesh;
            child.AddComponent<MeshRenderer>().sharedMaterials = sharedMaterials;
            return true;
        }

        /// <summary>
        /// Eases toward Position with some lag (less when thrashing), faces its direction of travel, and adds a
        /// tail swish and bob, so it reads as a fish swimming rather than a model pinned to the line.
        /// </summary>
        private void Update()
        {
            if (Player.m_localPlayer == null)
            {
                Destroy(gameObject);
                return;
            }

            if (!_initialized)
            {
                _renderPos = Position;
                _initialized = true;
            }

            Vector3 oldRenderPos = _renderPos;
            float pullRate = Mathf.Lerp(2.0f, 6.5f, Mathf.Clamp01(Intensity));
            _renderPos = Vector3.Lerp(_renderPos, Position, 1f - Mathf.Exp(-pullRate * Time.deltaTime));

            // Facing comes from the smoothed motion only - including the bob would flip it up/down constantly.
            Vector3 moveDir = _renderPos - oldRenderPos;
            if (moveDir.sqrMagnitude > 0.0000001f)
            {
                float turnRate = Mathf.Lerp(2.5f, 8f, Mathf.Clamp01(Intensity));
                _facing = Quaternion.Slerp(_facing, Quaternion.LookRotation(moveDir.normalized, Vector3.up), 1f - Mathf.Exp(-turnRate * Time.deltaTime));
            }

            float wob = Mathf.Sin(Time.time * (4f + Intensity * 12f)) * (0.02f + Intensity * 0.09f);
            // An animated model swims with its own tail; only a little body sway is added on top.
            float swish = Mathf.Sin(Time.time * (4f + Intensity * 18f)) * (5f + Intensity * 38f) * (_anim != null ? 0.15f : 1f);
            if (_anim != null) _anim.Intensity = Intensity;
            Vector3 displayPos = _renderPos + new Vector3(0f, wob, 0f);
            var rotation = _facing * Quaternion.Euler(0f, swish, 0f);

            float leap = Time.time < _leapEnd ? Mathf.InverseLerp(_leapStart, _leapEnd, Time.time) : -1f;
            float rear = Time.time - _rearStart;
            float hump = Time.time < _humpEnd ? Mathf.InverseLerp(_humpStart, _humpEnd, Time.time) : -1f;
            if (rear >= 0f && rear < _rearRise + _rearHold + _rearFall)
            {
                // Reared up out of the water toward the angler, swaying, then crashing back down.
                float up, pitch;
                if (rear < _rearRise) { float k = Mathf.SmoothStep(0f, 1f, rear / _rearRise); up = k; pitch = -65f * k; }
                else if (rear < _rearRise + _rearHold) { up = 1f; pitch = -65f + Mathf.Sin((rear - _rearRise) * 3f) * 6f; }
                else { float k = (rear - _rearRise - _rearHold) / _rearFall; up = 1f - k * k; pitch = Mathf.Lerp(-65f, 20f, k); }
                Vector3 face = _rearFace - displayPos; face.y = 0f;
                if (face.sqrMagnitude > 0.01f) _facing = Quaternion.Slerp(_facing, Quaternion.LookRotation(face.normalized, Vector3.up), 1f - Mathf.Exp(-6f * Time.deltaTime));
                float surface = SurfaceAt(displayPos) ?? displayPos.y;
                displayPos.y = Mathf.Lerp(displayPos.y, surface + _rearHeight, up);
                rotation = _facing * Quaternion.Euler(pitch, 0f, Mathf.Sin(rear * 2.2f) * 8f * up);
            }
            else if (hump >= 0f)
            {
                // A serpent's back rolling up through the surface and down again as it swims.
                float surface = SurfaceAt(displayPos) ?? displayPos.y;
                float k = Mathf.Sin(hump * Mathf.PI);
                displayPos.y = Mathf.Max(displayPos.y, surface - _topOffset + _humpHeight * k - 0.05f);
                rotation *= Quaternion.Euler(Mathf.Lerp(-12f, 12f, hump), 0f, 0f);
            }
            else if (leap >= 0f)
            {
                // Arcs clear of the water, nose up on the way out and down on the way back in.
                displayPos.y = Mathf.Max(displayPos.y, _leapBaseY + 4f * _leapHeight * leap * (1f - leap));
                rotation *= Quaternion.Euler(Mathf.Lerp(-50f, 50f, leap), 0f, 0f);
            }
            // Fish are positioned against flat sea level, but the water moves; never let one poke out of a wave.
            else if (StayUnder >= 0f && SurfaceAt(displayPos) is float surface)
                displayPos.y = Mathf.Min(displayPos.y, surface - StayUnder - _topOffset);

            transform.SetPositionAndRotation(displayPos, rotation);
        }

        private float _leapStart, _leapEnd, _leapHeight, _leapBaseY;
        private float _humpStart, _humpEnd, _humpHeight;
        private float _rearStart = -999f, _rearRise, _rearHold, _rearFall, _rearHeight;
        private Vector3 _rearFace;

        /// <summary>
        /// Rolls its back up through the surface, <paramref name="height"/> metres clear at the top, and down again over
        /// <paramref name="duration"/> seconds (a sea serpent's hump).
        /// </summary>
        public void Surface(float height, float duration)
        {
            _humpStart = Time.time;
            _humpEnd = Time.time + Mathf.Max(0.3f, duration);
            _humpHeight = height;
        }

        /// <summary>
        /// Rears up out of the water facing <paramref name="toward"/>: rises over <paramref name="rise"/> seconds, sways
        /// for <paramref name="hold"/>, crashes down over <paramref name="fall"/>. <paramref name="height"/> lifts its middle
        /// above the surface; tipped nose-up, the front half stands well clear and the rest stays under.
        /// </summary>
        public void Rear(Vector3 toward, float height, float rise, float hold, float fall)
        {
            _rearStart = Time.time;
            _rearFace = toward;
            _rearHeight = height;
            _rearRise = rise; _rearHold = hold; _rearFall = fall;
        }

        /// <summary>Marks this as bait on the hook: an animated model with a "Hooked" clip dangles and wriggles.</summary>
        public void SetOnHook()
        {
            if (_anim != null) _anim.OnHook = true;
        }

        /// <summary>A quick dart (a nibble at the bait): an animated model briefly swims hard.</summary>
        public void Dart()
        {
            if (_anim != null) _anim.Burst = 0.4f;
        }

        /// <summary>Jumps clear of the water: up <paramref name="height"/> metres over <paramref name="duration"/> seconds.</summary>
        public void Leap(float height, float duration)
        {
            _leapStart = Time.time;
            _leapEnd = Time.time + Mathf.Max(0.2f, duration);
            _leapHeight = height;
            _leapBaseY = (SurfaceAt(transform.position) ?? transform.position.y) - 0.1f;
        }
    }
}
