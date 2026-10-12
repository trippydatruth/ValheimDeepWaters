using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// The oilskin coat's skirt: FisherGear hands the coat below the hips to a ring of extra bones round the hips. This
    /// puts those bones on the wearer's skeleton (Valheim gives worn armour only the body's own bones) and swings them:
    /// the hem trails behind as you move, sways in Valheim's wind, and flutters a little. Each bone only swings along its
    /// own direction out from the body, mostly outward, so the front panels don't fold back into the legs.
    /// </summary>
    internal sealed class FisherSkirt : MonoBehaviour
    {
        public string HipsName = "Hips";

        // tunables (vdw_debug coatflow)
        internal static float Trail = 0.07f;        // seconds of movement the hem lags behind
        internal static float Wind = 0.18f;         // metres of hem sway in a full gale
        internal static float MaxAngle = 32f;       // degrees
        private const float Radius = 0.55f;         // hips to hem, metres
        private const float Stiffness = 28f, Damping = 7f;

        private SkinnedMeshRenderer? _smr;
        private Transform? _hips;
        private Transform[] _bones = new Transform[0];
        private Vector3 _lastHips, _vel, _offset, _offsetVel;
        private float _seed;

        private void Start()
        {
            _smr = GetComponent<SkinnedMeshRenderer>();
            _seed = Random.value * 100f;
        }

        private bool EnsureBones()
        {
            if (_smr == null || _smr.sharedMesh == null) return false;
            int want = _smr.sharedMesh.bindposes.Length;
            var bones = _smr.bones;
            if (bones.Length == want && _bones.Length > 0 && _bones[0] != null) return true;
            if (bones.Length + FisherGear.SkirtBones != want && bones.Length != want) return false;
            int bodyCount = want - FisherGear.SkirtBones;
            _hips = null;
            for (int i = 0; i < bodyCount && i < bones.Length; i++) if (bones[i] != null && bones[i].name == HipsName) { _hips = bones[i]; break; }
            if (_hips == null) return false;
            var all = new Transform[want];
            System.Array.Copy(bones, all, bodyCount);
            _bones = new Transform[FisherGear.SkirtBones];
            for (int i = 0; i < _bones.Length; i++)
            {
                var b = new GameObject("vdw_skirt" + i).transform;
                b.SetParent(_hips, false);              // where the hips are, so their bind pose (the hips') fits
                _bones[i] = b; all[bodyCount + i] = b;
            }
            _smr.bones = all;
            _lastHips = _hips.position;
            return true;
        }

        private void LateUpdate()
        {
            if (!EnsureBones() || _hips == null || _smr == null) return;
            float dt = Mathf.Max(Time.deltaTime, 1e-4f);

            // how the hips are moving (smoothed), and where that and the wind push the hem
            Vector3 v = (_hips.position - _lastHips) / dt; _lastHips = _hips.position;
            if (v.sqrMagnitude > 400f) v = Vector3.zero;                         // a teleport, not a step
            _vel = Vector3.Lerp(_vel, v, 1f - Mathf.Exp(-dt * 10f));
            Vector3 target = -_vel * Trail;
            if (EnvMan.instance != null)
            {
                float gust = 0.75f + 0.25f * Mathf.Sin(Time.time * 1.7f + _seed) * Mathf.Sin(Time.time * 0.63f + _seed * 2f);
                target += EnvMan.instance.GetWindDir() * (EnvMan.instance.GetWindIntensity() * Wind * gust);
            }
            target.y = 0f;
            // a spring toward it, so the hem swings and settles instead of snapping
            _offsetVel += ((target - _offset) * Stiffness - _offsetVel * Damping) * dt;
            _offset += _offsetVel * dt;

            float swing = Mathf.Min(MaxAngle, _offset.magnitude / Radius * Mathf.Rad2Deg);
            Vector3 dir = _offset.sqrMagnitude > 1e-8f ? _offset.normalized : Vector3.zero;
            var meshSpace = _smr.transform;
            for (int i = 0; i < _bones.Length; i++)
            {
                if (_bones[i] == null) continue;
                // this bone's direction out from the body, in the world
                float a = (i + 0.5f) / _bones.Length * 2f * Mathf.PI;
                Vector3 outward = meshSpace.TransformDirection(new Vector3(Mathf.Cos(a), Mathf.Sin(a), 0f));
                outward = Vector3.ProjectOnPlane(outward, Vector3.up).normalized;
                float along = Mathf.Clamp(Vector3.Dot(dir, outward), -0.15f, 1f);
                float flutter = Mathf.Sin(Time.time * 3.1f + i * 1.3f + _seed) * 1.5f * (EnvMan.instance != null ? EnvMan.instance.GetWindIntensity() : 0f);
                Vector3 axis = Vector3.Cross(Vector3.down, outward);
                _bones[i].rotation = Quaternion.AngleAxis(swing * along + flutter, axis) * _hips.rotation;
            }
        }

        private void OnDestroy()
        {
            foreach (var b in _bones) if (b != null) Destroy(b.gameObject);
        }
    }
}
