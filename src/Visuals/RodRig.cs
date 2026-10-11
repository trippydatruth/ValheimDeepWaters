using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// A rigged rod model (see rig_rod.py): the blank bends and the reel turns, posed every frame by RodMotion.
    /// Bones it looks for: Rod.1 .. Rod.N up the blank (butt to tip), Rod.Tip (where the line leaves the rod),
    /// Rod.BendDir (marker on the side the rod normally bends toward), Reel.Spool (the turning reel part) and
    /// Reel.Axis (marker along the spool's axle) and Rod.Grip (where the right hand holds it). Any of them can be
    /// missing; that part just doesn't move.
    /// </summary>
    internal sealed class RodRig : MonoBehaviour
    {
        private Transform[] _blank = new Transform[0];
        private Quaternion[] _blankRest = new Quaternion[0];
        private float[] _share = new float[0];
        private Transform? _tip, _bendDir, _spool, _grip;
        private Quaternion _spoolRest;
        private Vector3 _spoolAxis = Vector3.right;
        private float _spin;
        private bool _ready;

        public Transform? Tip { get { Init(); return _tip; } }

        /// <summary>Where the rod is held (marker Rod.Grip), if the model has one.</summary>
        public Transform? Grip { get { Init(); return _grip; } }

        /// <summary>The reel's turning part (Reel.Spool), if the model has one.</summary>
        public Transform? Spool { get { Init(); return _spool; } }

        /// <summary>The reel's axle in world space, and how far it has turned (degrees).</summary>
        public Vector3 SpoolAxis
        {
            get
            {
                Init();
                if (_spool == null) return Vector3.right;
                // turning about its own axle leaves the axle where it is: parent * rest * axis
                var parent = _spool.parent != null ? _spool.parent.rotation : Quaternion.identity;
                return (parent * (_spoolRest * _spoolAxis)).normalized;
            }
        }
        public float Spin => _spin;

        private void Init()
        {
            if (_ready) return;
            _ready = true;
            var all = GetComponentsInChildren<Transform>(true);
            Transform? Named(string n) => all.FirstOrDefault(t => t.name == n);

            var blank = new List<(int n, Transform t)>();
            foreach (var t in all)
                if (t.name.StartsWith("Rod.") && int.TryParse(t.name.Substring(4), out int k)) blank.Add((k, t));
            _blank = blank.OrderBy(b => b.n).Select(b => b.t).ToArray();
            _blankRest = _blank.Select(t => t.localRotation).ToArray();
            // More of the bend toward the tip, like a real blank.
            _share = Enumerable.Range(0, _blank.Length).Select(i => Mathf.Pow((i + 1f) / _blank.Length, 1.6f)).ToArray();
            float sum = _share.Sum();
            for (int i = 0; i < _share.Length; i++) _share[i] /= Mathf.Max(sum, 1e-4f);

            _tip = Named("Rod.Tip") ?? (_blank.Length > 0 ? _blank[_blank.Length - 1] : null);
            _bendDir = Named("Rod.BendDir");
            _grip = Named("Rod.Grip");
            // The handle doesn't bend: segments starting at or behind the grip (and just ahead of it, where the hands and
            // reel are) keep still, so the bend can't swing the handle out of the angler's hands.
            if (_grip != null && _tip != null && _blank.Length > 0)
            {
                Vector3 axisDir = _tip.position - _blank[0].position;
                float scale = Mathf.Max(1e-4f, transform.lossyScale.x);
                if (axisDir.sqrMagnitude > 1e-8f)
                {
                    axisDir.Normalize();
                    float gripAt = Vector3.Dot(_grip.position - _blank[0].position, axisDir);
                    for (int i = 0; i < _blank.Length; i++)
                        if (Vector3.Dot(_blank[i].position - _blank[0].position, axisDir) < gripAt + 0.12f * scale) _share[i] = 0f;
                    float kept = _share.Sum();
                    if (kept > 1e-4f) for (int i = 0; i < _share.Length; i++) _share[i] /= kept;
                }
            }
            _spool = Named("Reel.Spool");
            var axis = Named("Reel.Axis");
            if (_spool != null)
            {
                _spoolRest = _spool.localRotation;
                if (axis != null && (axis.position - _spool.position).sqrMagnitude > 1e-8f)
                    _spoolAxis = Quaternion.Inverse(_spool.rotation) * (axis.position - _spool.position).normalized;
            }
        }

        /// <summary>Back to the modelled pose.</summary>
        public void Rest()
        {
            Init();
            for (int i = 0; i < _blank.Length; i++) if (_blank[i] != null) _blank[i].localRotation = _blankRest[i];
            if (_spool != null) _spool.localRotation = _spoolRest * Quaternion.AngleAxis(_spin, _spoolAxis);
        }

        /// <summary>
        /// Bends the blank by <paramref name="bendDegrees"/> in total (how far the tip turns) toward the world point
        /// <paramref name="toward"/> (negative bends away from it), and turns the reel by <paramref name="spinDegrees"/>.
        /// </summary>
        public void Pose(float bendDegrees, Vector3? toward, float spinDegrees)
        {
            Init();
            _spin = Mathf.Repeat(_spin + spinDegrees, 360f);
            Rest();
            if (_blank.Length == 0 || _tip == null || Mathf.Abs(bendDegrees) < 0.01f) return;

            Vector3 rodDir = _tip.position - _blank[0].position;
            if (rodDir.sqrMagnitude < 1e-8f) return;
            rodDir.Normalize();
            // Bend toward the line; without one, toward the model's own bend side (or downward).
            Vector3 pull = toward.HasValue ? toward.Value - _tip.position
                         : _bendDir != null ? _bendDir.position - _tip.position : Vector3.down;
            Vector3 side = Vector3.ProjectOnPlane(pull, rodDir);
            if (side.sqrMagnitude < 1e-8f) side = Vector3.ProjectOnPlane(Vector3.down, rodDir);
            if (side.sqrMagnitude < 1e-8f) return;
            Vector3 axis = Vector3.Cross(rodDir, side.normalized).normalized;
            // Base to tip, each segment turned about the same world axis: the bends add up along the blank.
            for (int i = 0; i < _blank.Length; i++)
                _blank[i].rotation = Quaternion.AngleAxis(bendDegrees * _share[i], axis) * _blank[i].rotation;
        }
    }

    internal static partial class CustomModels
    {
        private static readonly Dictionary<string, GameObject?> RiggedRodCache = new();

        /// <summary>The rod model's prefab if it's rigged (has a skinned mesh), else null.</summary>
        private static GameObject? GetRiggedRod(string baseName)
        {
            if (RiggedRodCache.TryGetValue(baseName, out var cached)) return cached;
            var prefab = FindBundlePrefab(baseName, out var source);
            GameObject? result = prefab != null && prefab.GetComponentInChildren<SkinnedMeshRenderer>(true) != null ? prefab : null;
            if (result != null) Plugin.Log.LogInfo($"Custom models: '{baseName}' is a rigged rod (from '{source}') - it bends and its reel turns.");
            RiggedRodCache[baseName] = result;
            return result;
        }

        /// <summary>
        /// Puts a rigged rod in place of every rod renderer on the item prefab (the held "attach" copy included), in
        /// the same spot the static model would take. Its bones are posed by RodMotion, so any Animator is removed.
        /// </summary>
        private static void ApplyRiggedRod(GameObject prefab, GameObject model, string baseName)
        {
            var rotation = RotationFor(baseName);
            foreach (var mf in prefab.GetComponentsInChildren<MeshFilter>(true).ToList())
            {
                var mr = mf.GetComponent<MeshRenderer>();
                if (mr == null) continue;
                var go = Object.Instantiate(model, mf.transform, false);
                go.name = "vdw_rod_rig";
                go.transform.localPosition = Vector3.zero;
                go.transform.localRotation = rotation;
                go.transform.localScale = model.transform.localScale; // exactly as big as it is in Unity
                foreach (var c in go.GetComponentsInChildren<Collider>(true)) Object.DestroyImmediate(c);
                foreach (var rb in go.GetComponentsInChildren<Rigidbody>(true)) Object.DestroyImmediate(rb);
                foreach (var an in go.GetComponentsInChildren<Animator>(true)) Object.DestroyImmediate(an);
                foreach (var an in go.GetComponentsInChildren<Animation>(true)) Object.DestroyImmediate(an);
                foreach (var smr in go.GetComponentsInChildren<SkinnedMeshRenderer>(true)) smr.updateWhenOffscreen = true; // it bends past its bounds

                // The hand holds the item's "attach" point: put the rod's grip (marker bone Rod.Grip) right there,
                // keeping the vanilla rod's direction. Without the marker, the rod's origin sits at the vanilla pivot.
                var attach = mf.transform;
                while (attach != null && attach.name != "attach") attach = attach.parent;
                var grip = go.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name == "Rod.Grip");
                if (attach != null && grip != null) go.transform.position += attach.position - grip.position;

                go.AddComponent<RodRig>();
                mr.enabled = false;
            }
        }
    }
}
