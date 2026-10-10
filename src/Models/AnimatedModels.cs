using System.Collections.Generic;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// Animated models. A bundle prefab with a rigged (skinned) mesh and an Animator - or a legacy Animation - is
    /// used whole instead of only its mesh, and FishModelAnimator plays its clips: "Swim", "Thrash" and "Flop",
    /// with an optional float parameter "Speed". Static models keep working exactly as before.
    /// </summary>
    internal static partial class CustomModels
    {
        private static readonly Dictionary<string, GameObject?> AnimatedCache = new();

        /// <summary>The model's prefab if it's an animated (rigged) one, else null.</summary>
        public static GameObject? GetAnimated(string baseName)
        {
            if (AnimatedCache.TryGetValue(baseName, out var cached)) return cached;
            GameObject? result = null;
            var prefab = FindBundlePrefab(baseName, out var source);
            if (prefab != null && prefab.GetComponentInChildren<SkinnedMeshRenderer>(true) != null &&
                (prefab.GetComponentInChildren<Animator>(true) != null || prefab.GetComponentInChildren<Animation>(true) != null))
            {
                result = prefab;
                Plugin.Log.LogInfo($"Custom models: '{baseName}' is animated (from '{source}').");
            }
            AnimatedCache[baseName] = result;
            return result;
        }

        /// <summary>A live copy of the animated model under <paramref name="parent"/>, with its animation driver.</summary>
        public static FishModelAnimator SpawnAnimated(GameObject model, Transform parent)
        {
            var go = Object.Instantiate(model, parent, false);
            go.name = "vdw_model";
            go.transform.localPosition = Vector3.zero;
            go.transform.localRotation = Quaternion.identity;
            go.transform.localScale = model.transform.localScale; // exactly as big as it is in Unity
            // Only the look is wanted: no physics or colliders from the model.
            foreach (var c in go.GetComponentsInChildren<Collider>(true)) Object.DestroyImmediate(c);
            foreach (var rb in go.GetComponentsInChildren<Rigidbody>(true)) Object.DestroyImmediate(rb);
            foreach (var smr in go.GetComponentsInChildren<SkinnedMeshRenderer>(true)) smr.updateWhenOffscreen = false;
            return go.AddComponent<FishModelAnimator>();
        }

        /// <summary>
        /// Puts an animated model on an item prefab (a fish): it swims, thrashes or flops in the world, while the
        /// "attach" copy item stands display keeps a still pose. The prefab's own renderers are hidden.
        /// </summary>
        private static void ApplyAnimated(GameObject prefab, GameObject model)
        {
            var attach = prefab.transform.Find("attach");
            foreach (var r in prefab.GetComponentsInChildren<Renderer>(true)) r.enabled = false;

            SpawnAnimated(model, prefab.transform);

            // Item stands show the "attach" child: give it the model's mesh in its rest pose.
            if (attach != null)
            {
                var smr = model.GetComponentInChildren<SkinnedMeshRenderer>(true);
                if (smr != null && smr.sharedMesh != null)
                {
                    // Item stands copy only the "attachobj" child when an attach has one (vanilla fish do), so the still
                    // model goes in there; its long axis matches the vanilla fish mesh's in that space.
                    var standRoot = attach.Find("attachobj") ?? attach;
                    var still = new GameObject("vdw_model_still");
                    still.transform.SetParent(standRoot, false);
                    still.transform.localScale = smr.transform.lossyScale;
                    still.AddComponent<MeshFilter>().sharedMesh = smr.sharedMesh;
                    still.AddComponent<MeshRenderer>().sharedMaterials = smr.sharedMaterials;
                    still.AddComponent<StandOnlyModel>();
                }
            }
        }
    }

    /// <summary>
    /// The still copy of an animated model under an item's "attach" child is for item stands (which show only that
    /// child). On the item itself, lying in the world, the animated model is showing already, so it hides.
    /// </summary>
    internal sealed class StandOnlyModel : MonoBehaviour
    {
        private void Start()
        {
            if (GetComponentInParent<ItemDrop>() != null && GetComponent<Renderer>() is Renderer r) r.enabled = false;
        }
    }

    /// <summary>
    /// Plays an animated fish model's clips. Driven from outside (Driven = true) by the hooked and approaching fish
    /// visuals, which set Intensity; otherwise it reads its fish: "Swim" in water (faster as it moves), "Flop" on
    /// land, and nothing at all for a trophy (no Fish component), which holds still.
    /// </summary>
    internal sealed class FishModelAnimator : MonoBehaviour
    {
        public bool Driven;
        public float Intensity = 0.2f;   // 0 calm .. 1 thrashing, when driven
        public float Burst;              // seconds left of a quick dart (a nibble)
        public bool OnHook;              // bait on the hook: plays "Hooked" (dangling) instead of "Swim" if the model has it

        private Animator? _animator;
        private Animation? _legacy;
        private int _speedParam;
        private bool _hasSpeed;
        private string _state = "";
        private global::Fish? _fish;
        private Rigidbody? _body;
        private static readonly int SpeedHash = Animator.StringToHash("Speed");

        private void Start()
        {
            _animator = GetComponentInChildren<Animator>();
            _legacy = _animator == null ? GetComponentInChildren<Animation>() : null;
            if (_animator != null)
            {
                _animator.applyRootMotion = false;
                _animator.cullingMode = AnimatorCullingMode.CullUpdateTransforms;
                foreach (var p in _animator.parameters)
                    if (p.nameHash == SpeedHash && p.type == AnimatorControllerParameterType.Float) { _hasSpeed = true; _speedParam = p.nameHash; }
            }
            _fish = GetComponentInParent<global::Fish>();
            _body = GetComponentInParent<Rigidbody>();
        }

        private void Update()
        {
            string state;
            float speed;
            if (Driven)
            {
                if (Burst > 0f) Burst -= Time.deltaTime;
                float i = Mathf.Clamp01(Intensity + (Burst > 0f ? 0.7f : 0f));
                state = i > 0.6f ? "Thrash" : OnHook && Has("Hooked") ? "Hooked" : "Swim";
                speed = 0.6f + i * 1.6f;
            }
            else if (_fish != null)
            {
                float v = _body != null ? _body.linearVelocity.magnitude : 0f;
                if (InWater()) { state = "Swim"; speed = Mathf.Clamp(0.6f + v * 0.5f, 0.6f, 2.5f); }
                else { state = "Flop"; speed = 1f; }
            }
            else
            {
                Hold(); // a trophy (or anything that isn't a fish): keep still
                return;
            }
            Play(state, speed);
        }

        private bool InWater()
        {
            float level = Floating.GetLiquidLevel(transform.position);
            return level > -1000f && level > transform.position.y - 0.3f;
        }

        private void Play(string state, float speed)
        {
            // Missing clips fall back: no Thrash = a fast Swim, no Flop = a quick Swim.
            if (state != "Swim" && !Has(state)) { speed *= state == "Flop" ? 1.8f : 1.5f; state = "Swim"; }

            if (_animator != null)
            {
                _animator.enabled = true;
                if (_hasSpeed) { _animator.SetFloat(_speedParam, speed); _animator.speed = 1f; }
                else _animator.speed = speed;
                if (state != _state && Has(state)) _animator.CrossFadeInFixedTime(state, 0.25f);
            }
            else if (_legacy != null)
            {
                if (state != _state && _legacy[state] != null) _legacy.CrossFade(state, 0.25f);
                foreach (AnimationState s in _legacy) s.speed = speed;
            }
            _state = state;
        }

        private bool Has(string state) =>
            _animator != null ? _animator.HasState(0, Animator.StringToHash(state)) : _legacy != null && _legacy[state] != null;

        private void Hold()
        {
            if (_animator != null) _animator.enabled = false;
            else if (_legacy != null) _legacy.Stop();
        }
    }
}
