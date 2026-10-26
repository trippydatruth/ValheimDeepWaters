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
        internal static float Wind = 0.32f;         // metres of hem sway in a full gale
        internal static float MaxAngle = 40f;       // degrees (wind and trailing)
        internal static float LegPush = 1.1f;       // how far a thigh swinging out takes the skirt over that way (1 = with it)
        private Transform?[] _thighs = new Transform?[0], _knees = new Transform?[0];
        private Vector3[] _dirs = new Vector3[0];
        private int _hipsIdx = -1;
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
            Transform? Find(string n) { for (int i = 0; i < bodyCount && i < bones.Length; i++) if (bones[i] != null && bones[i].name == n) return bones[i]; return null; }
            // each skirt bone's direction out from the hips, from the skirt points on it (in the mesh's bind space; the
            // mesh's own axes aren't the world's - its height is y)
            var mesh = _smr.sharedMesh; var bw = mesh.boneWeights; var verts = mesh.vertices;
            _hipsIdx = System.Array.IndexOf(all, _hips);
            Vector3 hipBind = mesh.bindposes[_hipsIdx].inverse.MultiplyPoint3x4(Vector3.zero);
            _dirs = new Vector3[_bones.Length];
            var sum = new Vector3[_bones.Length]; var wsum = new float[_bones.Length];
            for (int v = 0; v < bw.Length && v < verts.Length; v++)
            {
                void Add(int b, float w) { int k = b - bodyCount; if (k >= 0 && k < _bones.Length && w > 0f) { sum[k] += (verts[v] - hipBind) * w; wsum[k] += w; } }
                Add(bw[v].boneIndex0, bw[v].weight0); Add(bw[v].boneIndex1, bw[v].weight1); Add(bw[v].boneIndex2, bw[v].weight2); Add(bw[v].boneIndex3, bw[v].weight3);
            }
            for (int k = 0; k < _bones.Length; k++) _dirs[k] = wsum[k] > 0f ? sum[k] / wsum[k] : Vector3.zero;
            _thighs = new[] { Find("LeftUpLeg"), Find("RightUpLeg") };
            _knees = new[] { Find("LeftLeg"), Find("RightLeg") };
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
                if (i >= _dirs.Length || _dirs[i].sqrMagnitude < 1e-10f) { _bones[i].rotation = _hips.rotation; continue; }   // no skirt on it
                Matrix4x4 toWorld = _hips.localToWorldMatrix * _smr.sharedMesh.bindposes[_hipsIdx];
                Vector3 outward = Vector3.ProjectOnPlane(toWorld.MultiplyVector(_dirs[i]), Vector3.up);
                if (outward.sqrMagnitude < 1e-10f) { _bones[i].rotation = _hips.rotation; continue; }
                outward.Normalize();
                float along = Mathf.Clamp(Vector3.Dot(dir, outward), -0.15f, 1f);
                float flutter = Mathf.Sin(Time.time * 3.1f + i * 1.3f + _seed) * 1.5f * (EnvMan.instance != null ? EnvMan.instance.GetWindIntensity() : 0f);
                // the legs: a thigh swinging out toward this bone's side (kicked back, raised in a crouch, stepping
                // forward) takes the skirt there with it, so the leg doesn't pass through the cloth
                float leg = 0f;
                for (int t = 0; t < _thighs.Length; t++)
                {
                    if (_thighs[t] == null || _knees[t] == null) continue;
                    Vector3 td = (_knees[t]!.position - _thighs[t]!.position).normalized;
                    Vector3 flat = Vector3.ProjectOnPlane(td, Vector3.up);
                    if (flat.sqrMagnitude < 1e-6f) continue;
                    float toward = Vector3.Dot(flat.normalized, outward);
                    if (toward <= 0f) continue;
                    float ang = Vector3.Angle(Vector3.down, td);                       // how far the thigh is lifted
                    leg = Mathf.Max(leg, ang * toward * LegPush);
                }
                float total = Mathf.Max(swing * along + flutter, Mathf.Min(leg, 110f));
                Vector3 axis = Vector3.Cross(Vector3.down, outward);
                _bones[i].rotation = Quaternion.AngleAxis(total, axis) * _hips.rotation;
            }
        }

        private void OnDestroy()
        {
            foreach (var b in _bones) if (b != null) Destroy(b.gameObject);
        }
    }
}
